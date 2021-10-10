# Standard Library Imports
import importlib
import time
import numpy as np

# This is needed to make sure super_hydro is in the import pathing
import os.path as osp

two_up = osp.abspath(osp.dirname(osp.dirname(osp.dirname(__file__))))
import sys, inspect

sys.path.insert(0, f"{two_up}")

# Additional Package Imports
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, Namespace, join_room, leave_room, close_room

# Project-defined Modules
from super_hydro import config, utils, communication
from super_hydro.server import server
from super_hydro.physics import gpe

# This establishes the communication with the server.
_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task

# Parser to get user loaded file/models, else defaults to included gpe.py models
args = None
kwargs = {}
parser = config.get_client_parser()
opts, other_args = parser.parse_known_args(args=args)
opts.__dict__.update(kwargs)

# File Pathing for custom model
if opts.file is not None:
    userpath = opts.file.split(".")[0]
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
_modname = modpath.split(".")[-1]
modelcls = [clsmembers[x][0] for x in range(len(clsmembers))]


app = Flask("flask_client")
# app.config['EXPLAIN_TEMPLATE_LOADING'] = True
socketio = SocketIO(app, async_mode="eventlet")

###############################################################################
# Network Server Communication clases.
# Taken from 'dumb.py' Dumb server as baseline.
###############################################################################


class _Interrupted(object):
    """Flag to indicate the App has been interrupted.

    Pass as the interrupted flag to the server to allow the client App
    to terminate it.
    """

    def __init__(self, app):
        """Initializes and attaches the App to the class.

        Parameters
        ----------
        app : :obj:
            App instance being attached.
        """
        self.app = app

    def __bool__(self):
        # Don't check interrupted flag - that might stop the server
        # too early.
        return not self.app._running


class App(object):
    """Dumb application that allows the user to interact with a computational
    server.

    Attributes
    ----------
    server : :obj:
        Attribute determining Local or Network server communications.
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
        App has been interrupted.
        """
        return _Interrupted(app=self)

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


#############################################################################
# Flask HTML Routes.
#
# These determine which URL-endpoint will be linked to which HTML page.
#############################################################################


def shutdown_server():
    """Shuts down the Flask-SocketIO instance."""
    print("Shutting down...")
    socketio.stop()


@app.route("/")
def index():
    """Landing page function.

    Used by Flask HTTP routing for navigation index/landing page for served
    web interface. Transfers model class list as Jinja2 templating variable.

    Parameters
    ----------
    cls : :obj:'list'
        global list of all classes within loaded module.

    Returns
    -------
    render_template('index.html')
        Generated HTML index/landing page for Flask web framework.
    """
    cls = modelcls
    return render_template("index.html", models=cls)


@app.route("/<cls>")
def modelpage(cls):
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
    render_template('model.html')
        Generates interactive HTML physics model page for Flask web framework.
    """
    _class = str(cls.split(".")[-1])
    Model = getattr(module, _class)
    return render_template(
        "model.html",
        model=cls,
        Title=f"{cls}",
        info=Model.__doc__,
        sliders=Model.get_sliders(),
        models=modelcls,
    )


@app.route("/quit")
def quit():
    """HTTP Route to shutdown the Flask client and running computational
    servers.
    """
    for model in Demonstration.fsh:
        if model != "init":
            if Demonstration.fsh[f"{model}"]["server"] is not None:
                Demonstration.fsh[f"{model}"]["server"].quit()
    shutdown_server()


#############################################################################
# Flask-SocketIO Communication.
#
# Allows communication with JS Socket.io library using the Flask-SocketIO
# extension.
#############################################################################


class Demonstration(Namespace):
    """Flask-SocketIO Socket container for models.

    Contains all Python-side web socket communications for operating and
    interacting with a running physics model. Communicates with Javascript
    socket.io API through a static Namespace and uses Flask-SocketIO's Room
    structuring to separate models.

    (https://flask-socketio.readthedocs.io/en/latest)

    Attributes
    ----------
    fsh : dict
        internal container for storing individual model information/computations
    """

    fsh = {}

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
        emit('init')
            Initial model parameters
        """

        model = data["name"]
        if model not in self.fsh or self.fsh[f"{model}"]["server"] is None:
            self.fsh[f"{model}"] = dict.fromkeys(["server", "users", "d_thread"])
            if opts.network == False:
                self.fsh[f"{model}"]["server"] = get_app(
                    run_server=True,
                    network_server=False,
                    steps=opts.steps,
                    model=model,
                    Nx=opts.Nx,
                    Ny=opts.Ny,
                )
            else:
                self.fsh[f"{model}"]["server"] = get_app(
                    run_server=False, network_server=True, steps=opts.steps, model=model
                )
                self.fsh[f"{model}"]["server"].run()
        join_room(model)
        if self.fsh[f"{model}"]["users"] is None:
            self.fsh[f"{model}"]["users"] = 1
        else:
            self.fsh[f"{model}"]["users"] += 1
        self.fsh["init"] = {}
        for param in data["params"]:
            self.fsh["init"].update(
                self.fsh[f"{model}"]["server"].server.get([f"{param}"])
            )
        emit("init", self.fsh["init"], room=model)
        if self.fsh[f"{model}"]["d_thread"] is None:
            self.fsh[f"{model}"]["d_thread"] = socketio.start_background_task(
                target=push_thread,
                namespace="/modelpage",
                server=self.fsh[f"{model}"]["server"],
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
        emit('param_up')
            Sends new parameter value to all Users connected to model's Room.
        """

        model = data["data"]
        for key, value in data["param"].items():
            self.fsh[f"{model}"]["server"].server.set({f"{key}": float(value)})
            data = {"name": key, "param": value}
        emit("param_up", data, room=model)

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
        emit('log_param_up')
            Sends new paramter value to all Users connected to model's Room.
        """

        model = data["data"]
        for key, value in data["param"].items():
            self.fsh[f"{model}"]["server"].server.set({f"{key}": float(value)})
            data = {"name": key, "param": value}
        emit("log_param_up", data, room=model)

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
            params = self.fsh[f"{model}"]["server"].server.reset()
            restart = {"name": model}
            restart.update({"params": params})
            leave_room(model)
            self.fsh[f"{model}"]["users"] -= 1
            self.on_start_srv(restart)
        else:
            self.fsh[f"{model}"]["server"].server.do(data["name"])

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
        server = self.fsh[f"{model}"]["server"].server
        for key, value in data["position"].items():
            Nxy = server.get(["Nxy"])["Nxy"]
            dx = server.get(["dx"])["dx"]
            pos = (np.asarray(data["position"]["xy0"]) - 0.5) * Nxy * dx
            pos = pos.tolist()
            self.fsh[f"{model}"]["server"].server.set({f"{key}": pos})

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
        leave_room(model)
        self.fsh[f"{model}"]["users"] -= 1
        if self.fsh[f"{model}"]["users"] == 0:
            self.fsh[f"{model}"]["users"] = 0
            self.fsh[f"{model}"]["server"].quit()
            self.fsh[f"{model}"]["server"] = None
            self.fsh[f"{model}"]["d_thread"].join()
            self.fsh[f"{model}"]["d_thread"] = None

    def on_disconnect(self):
        """Verifies disconnection from websocket.

        Automatically called when sockeet communication with Javascript socket.io
        is terminated or times out.
        """

        print("Client Disconnected.")


###############################################################################

socketio.on_namespace(Demonstration("/modelpage"))

###############################################################################
# End socket connection section.
###############################################################################


def push_thread(namespace, server, room):
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

        socketio.emit(
            "ret_array",
            {"rgba": rgba, "vxy": vxy, "fxy": fxy},
            namespace=namespace,
            room=room,
        )

        if opts.tracers == True:
            trace = server.server.get_array("tracers").tolist()

            socketio.emit("ret_trace", {"trace": trace}, namespace=namespace, room=room)
        print("Framerate currently is: ", int(1.0 / (time.time() - start_time)))
        socketio.sleep(0)


###############################################################################
# Functions for establishing the server communication object.
###############################################################################


def call_server(
    model, block=True, network_server=True, interrupted=False, args=None, kwargs={}
):
    """Generates a Server object for computation and communication. Loads in a
    series of configuration options as well as the specified computational
    model to run.

    Parameters
    ----------
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

    module = importlib.import_module(modpath)
    opts.State = getattr(module, model)
    if network_server:
        _server = server.NetworkServer(opts=opts)
    else:
        _server = server.Server(opts=opts)
    _server.run(block=block, interrupted=interrupted)
    return _server


###############################################################################
# Function to establish server communication
###############################################################################
_OPTS = None


def get_app(model, run_server=False, network_server=True, **kwargs):
    """Sets the App object with appropriate local server or network
    server communication property.

    Parameters
    ----------
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
    app : :obj:
        Communication object with either local or network server communication.
    """
    global _OPTS
    if _OPTS is None:
        with log_task("Reading Configuration"):
            parser = config.get_client_parser()
            _OPTS, _other_opts = parser.parse_known_args(args="")

    app = App(opts=_OPTS)

    if run_server:
        from super_hydro.server import server

        app.server = call_server(
            model,
            args="",
            interrupted=app.interrupted,
            block=False,
            network_server=network_server,
            kwargs=kwargs,
        )
    return app


def run():
    """Run the Flask web framework.

    Starts the Flask/Flask-SocketIO web framework app, which provides HTML and
    Javascript page rendering/routing and web socket mediation between User
    Javascript requests to a model Computational Server.
    """

    print(f"Running Flask client on http://{opts.host}:{opts.port}")
    socketio.run(app, host=opts.host, port=opts.port, debug=opts.debug)
