"""Flask Client.

The flask client runs a webserver on the client machine, and allows users to run a
selection of models.

For more details see :ref:`flask-client`.
"""

# Standard Library Imports
from collections import OrderedDict
import functools
import importlib
import inspect
import logging
import sys
import time

import numpy as np

# Additional Package Imports
import flask
import flask_socketio

# Project-defined Modules
from super_hydro import config, utils, communication
from super_hydro.server import server

__all__ = ["FlaskClient", "ModelNamespace", "run"]

# This establishes the communication with the server.
_LOGGER = utils.Logger(__name__)

log = _LOGGER.log
log_task = _LOGGER.log_task


###############################################################################
# Network Server Communication clases.
# Taken from 'dumb.py' Dumb server as baseline.
###############################################################################


class _Interrupted:
    """Flag to indicate the ServerProxy has been interrupted.

    Pass as the interrupted flag to the server to allow the client ServerProxy
    to terminate it.
    """

    def __init__(self, server_proxy):
        """Initializes and attaches the ServerProxy to the class.

        Parameters
        ----------
        server_proxy : :obj:
            ServerProxy instance being attached.
        """
        self.server_proxy = server_proxy

    def __bool__(self):
        # Don't check interrupted flag - that might stop the server
        # too early.
        return not self.server_proxy._running


class ServerProxy:
    """ServerProxy allows the user to interact with a computational server.

    Attributes
    ----------
    server : :obj:
        The actual computational server representing either a Local or Network server
        communications object
    """

    server = None

    def __init__(self, opts):
        """Initializes and loads configuration options, then flags as running.

        Parameters
        ----------
        opts : dict
            dict containing configuration options
        """
        self.opts = opts
        self._running = True

    @property
    def interrupted(self):
        """Return a flag that can be used to signal to the server that the
        Server has been interrupted.
        """
        return _Interrupted(server_proxy=self)

    def run(self):
        """Sets the server communication type to NetworkServer if no other
        type established.
        """
        if self.server is None:
            self.server = communication.NetworkServer(opts=self.opts)

    ###########################################################################
    # Server Communication
    #
    # These methods communicate with the server.
    def quit(self):
        """Passes 'quit' command to connected server."""
        self.server.do("quit")
        self._running = False


def route(*v, **kw):
    """Use in class methods where @app.route would be used.

    Allows the constructor to route these.
    """

    def wrapper(f):
        f._routing = (v, kw)
        return f

    return wrapper


#############################################################################
# Flask HTML Routes.
#
# These determine which URL-endpoint will be linked to which HTML page.
#############################################################################
class FlaskClient:
    """Encapsulates the Flask app.

    Attributes
    ----------
    app : flask.Flask
        Flask application object.
    opts : argparse.Namespace
        Options object.
    models : dict of Models
        The keys are the model names, and the values should be instances that implement
        the :interface:`super_hydro.interfaces.IModel` interface.    fsh : dict
        Dictionary of information about the running models.  Note: this is a class
        attribute - all instances use the same dictionary.
    """

    app = None
    opts = None
    other_args = None
    models = []
    fsh = {}

    def __init__(self, *args, **kwargs):
        self.app = flask.Flask("flask_client")
        # self.app.config["EXPLAIN_TEMPLATE_LOADING"] = True

        for name, method in inspect.getmembers(self):
            # Run through all routed methods and route them with self.app.
            if hasattr(method, "_routing"):
                v, kw = method._routing
                self.app.route(*v, **kw)(method)

        # Parser to get user loaded file/models, else defaults to included gpe.py models
        parser = config.get_client_parser()
        self.opts, self.other_args = parser.parse_known_args(args=args)
        self.opts.__dict__.update(kwargs)
        print(self.opts)

        self.models = self.get_models()
        self.demonstration = ModelNamespace(flask_client=self, root="/modelpage")

        self.socketio = flask_socketio.SocketIO(self.app, async_mode="eventlet")
        self.socketio.on_namespace(self.demonstration)

        print(f"Running Flask client on http://{self.opts.host}:{self.opts.port}")
        self.socketio.run(
            self.app, host=self.opts.host, port=self.opts.port, debug=self.opts.debug
        )
        self.app.logger.setLevel(logging.DEBUG)

    def shutdown_server(self):
        """Shuts down the Flask-SocketIO instance."""
        print("Shutting down...")
        self.socketio.stop()

    @route("/")
    def index(self):
        """Landing page function.

        Used by Flask HTTP routing for navigation index/landing page for served
        web interface. Transfers model class list as Jinja2 templating variable.

        Parameters
        ----------
        cls : :obj:'list'
            global list of all classes within loaded module.

        Returns
        -------
        flask.render_template('index.html')
            Generated HTML index/landing page for Flask web framework.
        """
        return flask.render_template("index.html", models=self.models)

    @route("/models/<cls>")
    def modelpage(self, cls):
        """Model display function.

        Used by Flask HTTP routing for navigation to model simulatioin pages by
        dynamically generating pages from the 'model.html' template useing Jinja2
        inputs.

        Parameters
        ----------
        cls : str
            Name of the class for the intended physics model to display

        Returns
        -------
        flask.render_template('model.html')
            Generates interactive HTML physics model page for Flask web framework.
        """
        Model = self.models[cls]
        template_vars = {
            "model_name": cls,
            "Title": f"{cls}",
            "info": Model.__doc__,
            "slider": Model.get_sliders(),
            "models": list(self.models),
        }

        return flask.render_template(
            "model.html",
            **template_vars,
        )

    @route("/quit")
    def quit(self):
        """HTTP Route to shutdown the Flask client and running computational
        servers.
        """
        for model in self.fsh:
            if model != "init":
                if self.fsh[model]["server"] is not None:
                    self.fsh[model]["server"].quit()
        self.shutdown_server()
        return flask.render_template("goodbye.html")

    def get_models(self):
        """Return a dictionary of models."""
        # File Pathing for custom model
        if self.opts.file is not None:
            userpath = self.opts.file.split(".")[0]
            tmp = userpath.split("/")
            udfp = tmp[:-1]
            newpath = "/".join(udfp)
            sys.path.insert(0, f"{newpath}")
            modpath = tmp[-1]
            module = importlib.import_module(modpath)
        else:
            modpath = "super_hydro.physics.gpe"
            module = importlib.import_module(modpath)

        clsmembers = inspect.getmembers(module, inspect.isclass)
        # _modname = modpath.split(".")[-1]

        model_names = []
        models = []
        for _x in range(len(clsmembers)):
            model_name = clsmembers[_x][0]
            model_class = model_name.split(".")[-1]
            Model = getattr(module, model_class)

            model_names.append(model_name)
            models.append(Model)
        return OrderedDict(zip(model_names, models))


#############################################################################
# Flask-SocketIO Communication.
#
# Allows communication with JS Socket.io library using the Flask-SocketIO
# extension.
#############################################################################


class ModelNamespace(flask_socketio.Namespace):
    """Flask-SocketIO Socket container for a model.

    This is a :class:`flask_socketio.Namespace` subclass, which allows one to eschew
    the use of the `@socketio.on` decorator to make the events.

    Contains all Python-side web socket communications for operating and
    interacting with a running physics model. Communicates with Javascript
    socket.io API through a static flask_socketio.Namespace and uses Flask-SocketIO's
    Room structuring to separate models.

    (https://flask-socketio.readthedocs.io/en/latest)
    """

    @property
    def fsh(self):
        return self.flask_client.fsh

    def __init__(self, flask_client, root, **kw):
        self.flask_client = flask_client
        super().__init__(root, **kw)

    def on_connect(self):
        """Verifies Client connection.

        User websocket connection to Javascript socket.io. Required by
        Flask-SocketIO. (https://flask-socketio.readthedocs.io/en/latest/)
        """
        print("Client Connected.")

    def on_start_srv(self, data):
        """Python-side Model Initialization.

        Receives initial parameters to connect model HTML page to computational
        server for appropriate model within the model's Room. Checks if model is
        already running, and starts a computational server if needed.

        Establishes interaction parameters, initial values, updates user count,
        starts/connects to server-side data pushing thread.

        Parameters
        ----------
        data : dict
            dict of {str : str}, keys are 'name' and 'params' for model name and
            interaction parameters.

        Returns
        -------
        flask_socketio.emit('init')
            Initial model parameters
        """
        opts = self.flask_client.opts

        model = data["name"]
        if model not in self.fsh or self.fsh[model]["server"] is None:
            self.fsh[model] = dict.fromkeys(["server", "users", "d_thread"])
            if opts.network == False:
                self.fsh[model]["server"] = get_server_proxy(
                    flask_client=self.flask_client,
                    run_server=True,
                    network_server=False,
                    steps=opts.steps,
                    model=model,
                    Nx=opts.Nx,
                    Ny=opts.Ny,
                )
            else:
                self.fsh[model]["server"] = get_server_proxy(
                    flask_client=self.flask_client,
                    run_server=False,
                    network_server=True,
                    steps=opts.steps,
                    model=model,
                )
                self.fsh[model]["server"].run()
        flask_socketio.join_room(model)
        if self.fsh[model]["users"] is None:
            self.fsh[model]["users"] = 1
        else:
            self.fsh[model]["users"] += 1
        self.fsh["init"] = {}
        for param in data["params"]:
            self.fsh["init"].update(self.fsh[model]["server"].server.get([f"{param}"]))
        flask_socketio.emit("init", self.fsh["init"], room=model)
        if self.fsh[model]["d_thread"] is None:
            self.fsh[model][
                "d_thread"
            ] = self.flask_client.socketio.start_background_task(
                target=self.push_thread,
                namespace="/modelpage",
                server=self.fsh[model]["server"],
                room=model,
            )

    def on_set_param(self, data):
        """Transfers parameter change to computational server.

        Receives parameter change from User-side Javascript and passes it into
        model computational server before updating all connected User pages.

        Parameters
        ----------
        data : dict
            dict containing model room name, parameter being modified and new
            value.

        Returns
        -------
        flask_socketio.emit('param_up')
            Sends new parameter value to all Users connected to model's Room.
        """
        model = data["data"]
        for key, value in data["param"].items():
            self.fsh[model]["server"].server.set({f"{key}": float(value)})
            data = {"name": key, "param": value}
        flask_socketio.emit("param_up", data, room=model)

    def on_set_log_param(self, data):
        """Transfers logarithmic parameter change to computational server.

        Receives logarithmic parameter change from User-side Javascript and
        passes it into model computational server before updating all
        connected User pages.

        Parameters
        ----------
        data : dict
            dict containing model room name, parameter being modified and new
            value.

        Returns
        -------
        flask_socketio.emit('log_param_up')
            Sends new paramter value to all Users connected to model's Room.
        """

        model = data["data"]
        for key, value in data["param"].items():
            self.fsh[model]["server"].server.set({f"{key}": float(value)})
            data = {"name": key, "param": value}
        flask_socketio.emit("log_param_up", data, room=model)

    def on_do_action(self, data):
        """Transfers Server action request to computational server.

        Receives and passes server action request to computational server.

        Parameters
        ----------
        data : dict
            dict containing model room name, action request for computational
            server
        """

        model = data["data"]
        if data["name"] == "reset":
            params = self.fsh[model]["server"].server.reset()
            restart = {"name": model}
            restart.update({"params": params})
            flask_socketio.leave_room(model)
            self.fsh[model]["users"] -= 1
            self.on_start_srv(restart)
        else:
            self.fsh[model]["server"].server.do(data["name"])

    def on_finger(self, data):
        """Transfers new finger potential position to computational server.

        Passes User set Finger position to computational server.

        Parameters
        ----------
        data : dict
            dict containing model room name, tuple list of User Finger
            coordinates.
        """

        model = data["data"]
        server = self.fsh[model]["server"].server
        for key, value in data["position"].items():
            Nxy = server.get(["Nxy"])["Nxy"]
            dx = server.get(["dx"])["dx"]
            pos = (np.asarray(data["position"]["xy0"]) - 0.5) * Nxy * dx
            pos = pos.tolist()
            self.fsh[model]["server"].server.set({f"{key}": pos})

    def on_user_exit(self, data):
        """Model Room updating on User exit from page.

        Updates the model Room user count when a User navigates away from the
        model display page. If user count is zero, shuts down the computational
        server.

        Parameters
        ----------
        data : dict
            dict containing model name
        """

        model = data["data"]
        flask_socketio.leave_room(model)
        self.fsh[model]["users"] -= 1
        if self.fsh[model]["users"] == 0:
            self.fsh[model]["users"] = 0
            self.fsh[model]["server"].quit()
            self.fsh[model]["server"] = None
            self.fsh[model]["d_thread"].join()
            self.fsh[model]["d_thread"] = None

    def on_disconnect(self):
        """Verifies disconnection from websocket.

        Automatically called when sockeet communication with Javascript socket.io
        is terminated or times out.
        """

        print("Client Disconnected.")

    ###############################################################################

    ###############################################################################
    # End socket connection section.
    ###############################################################################

    def push_thread(self, namespace, server, room):
        """Continuously updates display information to model page.

        Background thread that continuously queries computational server for
        density array, finger potential position and potential strength. Transmits
        to appropriate model page for display animation.

        Parameters
        ----------
        namespace : str
            Static namespace for the web socket communication.
        server : obj
            Model computational server object.
        room : str
            Model room name destination for display information

        Returns
        -------
        socketio.emit('ret_array')
            Transmits display information to Javascript via web socket connection.
        socketio.emit('ret_trace')
            Transmits tracer particle position data to Javascript via web socket.
        """
        while server._running is True:
            start_time = time.time()
            # Exchange comments to revert display/performance:

            # fxy = [server.server.get(["finger_x"])['finger_x'],
            #        server.server.get(["finger_y"])['finger_y']]
            # vxy = server.server.get(['Vpos'])['Vpos']

            fxy = vxy = [0.5, 0.5]

            density = server.server.get_array("density")

            from matplotlib import cm

            array = cm.viridis(density / density.max())
            array *= int(255 / array.max())  # normalize values
            rgba = "".join(map(chr, array.astype(dtype="uint8").tobytes()))

            self.flask_client.socketio.emit(
                "ret_array",
                {"rgba": rgba, "vxy": vxy, "fxy": fxy},
                namespace=namespace,
                room=room,
            )
            if self.flask_client.opts.tracers == True:
                trace = server.server.get_array("tracers").tolist()

                self.flask_client.socketio.emit(
                    "ret_trace", {"trace": trace}, namespace=namespace, room=room
                )
            print("Framerate currently is: ", int(1.0 / (time.time() - start_time)))
            self.flask_client.socketio.sleep(0)


###############################################################################
# Functions for establishing the server communication object.
###############################################################################


def get_server(
    flask_client,
    model,
    block=True,
    network_server=True,
    interrupted=False,
    args=None,
    kwargs={},
):
    """Generates a Server object for computation and communication. Loads in a
    series of configuration options as well as the specified computational
    model to run.

    Parameters
    ----------
    flask_client : FlaskClient
        Initialized FlaskClient.
    model : str
        Name of the class representing a physical model
    block : bool
        Boolean for Asynchronous/Synchronous thread running.
    network_server : bool
        Boolean determining whether creating a local or network server
    interrupted : bool
        Boolean to flag whether process is interrupted or not
    args : dict
        Additional arguments to be passes for parsing
    kwargs : dict
        Additional keyword arguments to update configuration options

    Returns
    -------
    _server : :obj:
        The running server object with loaded configuration options.
    """
    parser = config.get_server_parser()
    opts, other_args = parser.parse_known_args(args=args)
    opts.__dict__.update(kwargs)

    # module = importlib.import_module(modpath)
    # Model = getattr(module, model)
    Model = flask_client.models[model]
    opts.State = Model
    if network_server:
        _server = server.NetworkServer(opts=opts)
    else:
        _server = server.Server(opts=opts)
    _server.run(block=block, interrupted=interrupted)
    return _server


###############################################################################
# Function to establish server communication
###############################################################################
def get_server_proxy(
    flask_client, model, run_server=False, network_server=True, **kwargs
):
    """Returns a ServerProxy object with appropriate local server or network
    server communication property.

    Parameters
    ----------
    flask_client : FlaskClient
        Initialized FlaskClient.
    model : str
        Name of the model class to load into server object property.
    run_server : bool
        Boolean determining whether to create a local running server object
    network_server : bool
        Boolean determining whether to creat a network communication process
    **kwargs :
        Arbitrary keyword arguments

    Returns
    -------
    server_proxy : :obj:
        ServerProxy object with either local or network server communication.
    """
    if flask_client.opts is None:
        with log_task("Reading Configuration"):
            parser = config.get_client_parser()
            opts, other_opts = parser.parse_known_args(args="")
    else:
        opts = flask_client.opts

    server_proxy = ServerProxy(opts=opts)

    if run_server:
        # Delay import becuase clients may not have all of the dependencies needed
        # to run the server.
        from super_hydro.server import server

        server_proxy.server = get_server(
            flask_client=flask_client,
            model=model,
            args="",
            interrupted=server_proxy.interrupted,
            block=False,
            network_server=network_server,
            kwargs=kwargs,
        )
    return server_proxy


def run(*args, **kwargs):
    """Run the Flask web framework.

    Starts the Flask/Flask-SocketIO web framework self.app, which provides HTML and
    Javascript page rendering/routing and web socket mediation between User
    Javascript requests to a model Computational Server.
    """
    flask_client = FlaskClient(*args, **kwargs)


if __name__ == "__main__":
    run()
