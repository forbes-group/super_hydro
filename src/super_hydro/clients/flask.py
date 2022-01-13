"""Flask Client.

The flask client runs a webserver on the client machine, and allows users to run a
selection of models.

For more details see :ref:`flask-client`.
"""

# Standard Library Imports
from collections import OrderedDict
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
from .. import config, utils, communication
from ..server import server, ThreadMixin
from .mixins import ClientDensityMixin
from .. import widgets as w

__all__ = ["FlaskClient", "ModelNamespace", "run"]

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
class FlaskClient(ClientDensityMixin):
    """Encapsulates the Flask app.

    Attributes
    ----------
    app : flask.Flask
        Flask application object.
    opts : argparse.Namespace
        Options object.
    models : dict of Models
        The keys are the model names, and the values should be instances that implement
        the :interface:`super_hydro.interfaces.IModel` interface.
    running_models : dict
        Dictionary of information about the running models.  Note: this is a class
        attribute - all instances use the same dictionary.  The key is the model name,
        and the values are a dict with the following keys:

        'server' : ServerProxy
            :class:`ServerProxy` object representing the computation server.
        'users' : int
            Number of connected users.  In this context, a user is a different
            window/tab or browser.
        'd_thread' : Thread
            Thread object returned by
            :func:`flask_socketio.SocketIO.start_background_task` that is running the
            computational server.


    """

    app = None
    opts = None
    other_args = None
    models = []
    running_models = {}

    def __init__(self, *args, **kwargs):
        self.app = flask.Flask("flask_client")
        # self.app.config["EXPLAIN_TEMPLATE_LOADING"] = True

        #### Needs testing.
        self.app.logger.setLevel(logging.DEBUG)
        self.logger = utils.Logger(self.app.logger.name)

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

        self.socketio = flask_socketio.SocketIO(self.app, async_handlers=False)
        self.socketio.on_namespace(self.demonstration)

        print(f"Running Flask client on http://{self.opts.host}:{self.opts.port}")
        self.socketio.run(
            self.app, host=self.opts.host, port=self.opts.port, debug=self.opts.debug
        )

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
            "sliders": get_sliders(Model),
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
        for model_name in list(self.running_models):
            # Should we not pop?
            model = self.running_models[model_name]
            if model["server"] is not None:
                model["server"].quit()
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

    def __init__(self, flask_client, root, **kw):
        self.flask_client = flask_client
        self.logger = self.flask_client.logger
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
        """
        opts = self.flask_client.opts

        model_name = data["name"]
        running_models = self.flask_client.running_models
        if (
            model_name not in running_models
            or running_models[model_name]["server"] is None
        ):
            model = dict(server=None, users=0, d_thread=None)
            running_models[model_name] = model
            run_server = not opts.network
            server_args = dict(
                flask_client=self.flask_client,
                run_server=run_server,
                network_server=opts.network,
                steps=opts.steps,
                model_name=model_name,
                Nx=opts.Nx,
                Ny=opts.Ny,
            )
            model["server"] = get_server_proxy(**server_args)
            if run_server:
                model["server"].run()
        else:
            model = running_models[model_name]

        flask_socketio.join_room(model_name)
        model["users"] += 1

        params = model["server"].server.get(data["params"])

        push_thread = PushThread(flask_client=self.flask_client, name=model_name)

        if model["d_thread"] is None:
            model["d_thread"] = self.flask_client.socketio.start_background_task(
                target=push_thread.run,
                namespace="/modelpage",
                server=model["server"],
                room=model_name,
            )
        flask_socketio.emit("update_widgets", params, room=model_name)

    def on_set_params(self, data):
        """Transfers parameter change to computational server.

        Receives parameter change from User-side Javascript and passes it into
        model computational server before updating all connected User pages.

        Sends new parameter value to all Users connected to model's Room.

        Parameters
        ----------
        data : dict
            dict containing model room name, and parameter being modified and new
            value.
        """
        model_name = data["model_name"]
        model = self.flask_client.running_models[model_name]
        params = {key: float(value) for key, value in data["params"].items()}
        model["server"].server.set(params)
        flask_socketio.emit("set_params", params, room=model_name)

    def on_click(self, data):
        """Button clicks.

        Receives and passes server action request to computational server.

        Parameters
        ----------
        data : dict
            dict containing model room name, and the button name (the action request for
            computational server)
        """

        model_name = data["data"]
        model = self.flask_client.running_models[model_name]
        if data["name"] == "reset":
            params = model["server"].server.reset()
            restart = {"name": model_name}
            restart.update({"params": params})
            flask_socketio.leave_room(model_name)
            model["users"] -= 1
            self.on_start_srv(restart)
        else:
            model["server"].server.do(data["name"])

    def on_finger(self, data):
        """Transfers new finger potential position to computational server.

        Passes User set Finger position to computational server.

        Parameters
        ----------
        data : dict
            dict containing model room name, tuple list of User Finger
            coordinates.
        """

        model_name = data["data"]
        model = self.flask_client.running_models[model_name]
        server = model["server"].server
        f_xy = np.asarray(data["f_xy"])
        server.set({"finger_x": f_xy[0], "finger_y": f_xy[1]})

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

        model_name = data["data"]
        model = self.flask_client.running_models[model_name]
        flask_socketio.leave_room(model_name)
        model["users"] -= 1
        if model["users"] == 0:
            model["users"] = 0
            model["server"].quit()
            model["server"] = None
            model["d_thread"].join()
            model["d_thread"] = None

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


class PushThread(ThreadMixin):
    def __init__(self, flask_client, name):
        self.flask_client = flask_client
        self.logger = flask_client.logger
        self.init(name=name)

    def run(self, namespace, server, room):
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
        available_commands = server.server.get_available_commands()
        if "density" not in available_commands["get_array"]:
            self.logger.error('ERROR: Server does not support get_array("density")')
            return

        finger_vars = set(["finger_x", "finger_y", "finger_Vxy"])
        has_finger = finger_vars.issubset(available_commands["get"])

        has_tracers = bool(self.flask_client.opts.tracers)

        if has_tracers:
            if "tracers" not in available_commands["get_array"]:
                self.logger.error(
                    'ERROR: Client asked for tracers, but no server.get_array("tracers")'
                )
            return

        max_fps = self.flask_client.opts.fps
        while server._running:
            start_time = time.time()

            data = {}

            density = server.server.get_array("density")
            rgba = self.flask_client.get_rgba_from_density(density)
            ### Can we avoid this?
            rgba = "".join(map(chr, rgba.tobytes()))

            data["rgba"] = rgba

            if has_finger:
                check_performance = False
                if check_performance:
                    data["f_xy"] = list(map(str, np.random.random(2)))  # ("0.5", "0.5")
                    data["v_xy"] = list(map(str, np.random.random(2)))  # ("0.5", "0.5")
                else:
                    res = server.server.get(finger_vars)
                    data["f_xy"] = (res["finger_x"], res["finger_y"])
                    data["v_xy"] = res["finger_Vxy"]
            if has_tracers:
                data["trace"] = server.server.get_array("tracers").tolist()

            self.flask_client.socketio.emit(
                "update", data, namespace=namespace, room=room
            )

            fps = 1 / (time.time() - start_time)
            wait_time = max(0, 1 / max_fps - 1 / fps)
            self.flask_client.socketio.sleep(wait_time)
            self.heartbeat(f"Current framerate: {fps:.2f}fps")


###############################################################################
# Functions for establishing the server communication object.
###############################################################################


def launch_server(
    flask_client,
    model_name,
    block=True,
    network_server=True,
    interrupted=False,
    args=None,
    kwargs={},
):
    """Start running a server.

    This starts a computational server running on the local computer.  (In the future,
    it may launch a server on a remote computer.)
    Generates a Server object for computation and communication. Loads in a
    series of configuration options as well as the specified computational
    model to run.

    Parameters
    ----------
    flask_client : FlaskClient
        Initialized FlaskClient.
    model_name : str
        Name of the class representing a physical model
    block : bool
        If this is `True`, then the server is run synchronously without threads, and the
        call will block until the server is finished running.  You should only do this
        if you plan to launch a `network_server` and then connect to it over the
        network, sending a `quit` signal to terminate it.

        If `False`, then the server will be run in an independent thread, and
        you can stop it by calling the returned `server.quit()` method.
    network_server : bool
        If `True`, then the server will listen on the specified port for interactions.
    interrupted : bool
        Boolean to flag whether process is interrupted or not
    args : dict
        Additional arguments to be passes for parsing
    kwargs : dict
        Additional keyword arguments to update configuration options

    Returns
    -------
    server : :obj:
        The running server object with loaded configuration options.
    """
    parser = config.get_server_parser()
    opts, other_args = parser.parse_known_args(args=args)
    opts.__dict__.update(kwargs)

    # module = importlib.import_module(modpath)
    # Model = getattr(module, model)
    Model = flask_client.models[model_name]
    opts.Model = Model
    if block and not network_server:
        raise ValueError(
            "Don't start a `block=True` server without `network_server = True` "
            + "(there is no way to stop it!)"
        )
    if network_server:
        server_ = server.NetworkServer(opts=opts)
    else:
        server_ = server.Server(opts=opts)
    server_.run(block=block, interrupted=interrupted)
    return server_


###############################################################################
# Function to establish server communication
###############################################################################
def get_server_proxy(
    flask_client, model_name, run_server=False, network_server=True, **kwargs
):
    """Returns a ServerProxy object with appropriate local server or network
    server communication property.

    Parameters
    ----------
    flask_client : FlaskClient
        Initialized FlaskClient.
    model_name : str
        Name of the model class to load into server object property.
    run_server : bool
        Boolean determining whether to create a local running server object
    network_server : bool
        Boolean determining whether to creat a network communication process
    **kwargs :
        Arbitrary keyword arguments

    Returns
    -------
    server_proxy : obj
        ServerProxy object with either local or network server communication.
    """
    if flask_client.opts is None:
        with flask_client.logger.log_task("Reading Configuration"):
            parser = config.get_client_parser()
            opts, other_opts = parser.parse_known_args(args="")
    else:
        opts = flask_client.opts

    server_proxy = ServerProxy(opts=opts)

    if run_server:
        server_proxy.server = launch_server(
            flask_client=flask_client,
            model_name=model_name,
            args="",
            interrupted=server_proxy.interrupted,
            block=False,
            network_server=network_server,
            kwargs=kwargs,
        )
    return server_proxy


def get_sliders(Model):
    """Return a list of "sliders" from `Model.layout`.

    This is a convenience function for the flask client.  Ultimately, that client
    should parse the layout itself so that the models can customize the display.
    """

    def get_widgets(tree):
        """Return a list of all widgets."""
        widgets = []
        for widget in tree:
            if hasattr(widget, "children"):
                widgets.extend(get_widgets(widget.children))
            else:
                widgets.append(widget)
        return widgets

    sliders = []
    for widget in get_widgets([Model.layout]):
        slider = {
            "id": widget.name,
            "min": None,
            "max": None,
            "step": None,
        }
        if isinstance(widget, w.FloatLogSlider) or isinstance(widget, w.FloatSlider):
            slider.update(
                {
                    "class": "slider",
                    "type": "range",
                    "name": "linear",
                    "min": widget.min,
                    "max": widget.max,
                    "step": widget.step,
                }
            )
            if isinstance(widget, w.FloatLogSlider):
                slider["name"] = "logarithmic"
        elif isinstance(widget, w.Checkbox):
            slider.update(
                {
                    "class": "toggle",
                    "name": None,
                    "type": "checkbox",
                }
            )
        else:
            continue
        sliders.append(slider)
    return sliders


def run(*args, **kwargs):
    """Run the Flask web framework.

    Starts the Flask/Flask-SocketIO web framework self.app, which provides HTML and
    Javascript page rendering/routing and web socket mediation between User
    Javascript requests to a model Computational Server.
    """
    flask_client = FlaskClient(*args, **kwargs)


if __name__ == "__main__":
    run()
