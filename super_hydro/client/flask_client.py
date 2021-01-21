#Standard Library Imports
import importlib
import time
import numpy as np

#This is needed to make sure super_hydro is in the import pathing
import os.path as osp
two_up = osp.abspath(osp.dirname(osp.dirname(osp.dirname(__file__))))
import sys, inspect
sys.path.insert(0, f'{two_up}')

#Additional Package Imports
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, Namespace, join_room, leave_room, close_room

#Project-defined Modules
from super_hydro import config, utils, communication
from super_hydro.server import server
from super_hydro.physics import gpe

#This establishes the communication with the server.
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
    sys.path.insert(0, f'{newpath}')
    modpath = tmp[-1]
    print(modpath)
    module = importlib.import_module(modpath)
else:
    modpath = "super_hydro.physics.gpe"
    module = importlib.import_module(modpath)

clsmembers = inspect.getmembers(module, inspect.isclass)
modelcls = [clsmembers[x][0] for x in range(len(clsmembers))]

app = Flask("flask_client")
#app.config['EXPLAIN_TEMPLATE_LOADING'] = True
socketio = SocketIO(app, async_mode='eventlet')

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
        self.app = app

    def __bool__(self):
        # Don't check interrupted flag - that might stop the server 
        # too early.
        return not self.app._running

class App(object):
    """Dumb application that allows the user to interact with a computational
    server.
    """

    server = None

    def __init__(self, opts):
        self.opts = opts
        self._running = True

    @property
    def comm(self):
        """Return the communication object, but only if running."""
        if self._running:
            return self.server.comm

    @property
    def density(self):
        """Return the density data to plot: intiates call to server."""
        with log_task("Get density from server."):
            return self.server.get_array("density")

    @property
    def interrupted(self):
        """Return a flag that can be used to signal to the server that the
        App has been interrupted.
        """
        return _Interrupted(app=self)

    def run(self):
        if self.server is None:
            self.server = communication.NetworkServer(opts=self.opts)

    ###########################################################################
    # Server Communication
    # 
    # These methods communicate with the server.
    def quit(self):
        self.server.do("quit")
        self._running = False

#############################################################################
# Flask HTML Routes.
#
# These determine which URL-endpoint will be linked to which HTML page.
#############################################################################

def shutdown_server():
    print("Shutting down...")
    socketio.stop()

@app.route('/')
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
    return render_template('index.html', models=cls)

@app.route('/<cls>')
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
    info = getattr(module, cls)
    return render_template('model.html', model=cls,
                                         Title= f'{cls}',
                                         info= info.__doc__,
                                         sliders=info.sliders,
                                         models=modelcls)

@app.route('/quit')
def quit():
    """HTTP Route to shutdown the Flask client and running computational
    servers.
    """
    for model in Demonstration.fsh:
        if model is not 'init':
            if Demonstration.fsh[f'{model}']['server'] is not None:
                Demonstration.fsh[f'{model}']['server'].quit()
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
        print('Client Connected.')

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

        model = data['name']
        if model not in self.fsh or self.fsh[f'{model}']['server'] is None:
            self.fsh[f'{model}'] = dict.fromkeys(['server', 'users', 'd_thread'])
            if opts.network == False:
                self.fsh[f'{model}']['server'] = get_app(run_server=True, network_server=False, steps=3)
            else:
                self.fsh[f'{model}']['server'] = get_app(run_server=False, network_server=True, steps=5)
        join_room(model)
        if self.fsh[f'{model}']['users'] is None:
            self.fsh[f'{model}']['users'] = 1
        else:
            self.fsh[f'{model}']['users'] += 1
        self.fsh['init'] = {}
        for param in data['params']:
            self.fsh[f'{param}'] = self.fsh[f'{model}']['server'].server._get(param)
            self.fsh['init'].update({f'{param}' : self.fsh[f'{param}']})
            self.fsh.pop(f'{param}')
        emit('init', self.fsh['init'],
                     room=model)
        if self.fsh[f'{model}']['d_thread'] is None:
            self.fsh[f'{model}']['d_thread'] = socketio.start_background_task(
                                                target=push_thread,
                                                namespace='/modelpage',
                                                server=self.fsh[f'{model}']['server'],
                                                room=model)

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

        model = data['data']
        for key, value in data['param'].items():
            self.fsh[f'{model}']['server'].server.set({f'{key}' : float(value)})
            data = {'name' : key, 'param' : value}
        emit('param_up', data, room=model)

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

        model = data['data']
        for key, value in data['param'].items():
            self.fsh[f'{model}']['server'].server.set({f'{key}' : float(value)})
            data = {'name': key, 'param': value}
        emit('log_param_up', data, room=model)

    def on_do_action(self, data):
        """Transfers Server action request to computational server.

        Receives and passes server action request to computational server.

        Parameters
        ----------
        data : dict
            dict containing model room name, action request for computational
            server
        """

        model = data['data']
        if data['name'] == 'reset':
            params = self.fsh[f'{model}']['server'].server.reset()
            restart = {'name': model}
            restart.update({'params': params})
            leave_room(model)
            self.fsh[f'{model}']['users'] -= 1
            self.on_start_srv(restart)
        else:
            self.fsh[f'{model}']['server'].server.do(data['name'])

    def on_finger(self, data):
        """Transfers new finger potential position to computational server.

        Passes User set Finger position to computational server.

        Parameters
        ----------
        data : dict
            dict containing model room name, tuple list of User Finger
            coordinates.
        """

        model = data['data']
        server = self.fsh[f'{model}']['server'].server
        print(data['position']['xy0'])
        for key, value in data['position'].items():
            # Below may be the workaround?
            # Needs to be able to get Lxy, not sure how at the moment.
            Nxy = server.get(['Nxy'])['Nxy']
            dx = server._get('dx')
            print(Nxy, dx)
            pos = (np.asarray(data['position']['xy0']) - 0.5) * Nxy * dx
            self.fsh[f'{model}']['server'].server.set({f'{key}': pos})

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

        model = data['data']
        print(model)
        leave_room(model)
        self.fsh[f'{model}']['users'] -= 1
        if (self.fsh[f'{model}']['users'] == 0):
            self.fsh[f'{model}']['users'] = 0
            self.fsh[f'{model}']['server'].quit()
            self.fsh[f'{model}']['server'] = None
            self.fsh[f'{model}']['d_thread'].join()
            self.fsh[f'{model}']['d_thread'] = None

    def on_disconnect(self):
        """Verifies disconnection from websocket.

        Automatically called when sockeet communication with Javascript socket.io
        is terminated or times out.
        """

        print('Client Disconnected.')

###############################################################################

socketio.on_namespace(Demonstration('/modelpage'))

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
    """

    while server._running is True:
        fxy = [server.server._get('finger_x'), server.server._get('finger_y')]
        vxy = (server.server._get_Vpos()).tobytes()
        vxy_char = "".join([chr(i) for i in vxy])

        print("Getting Density array...")
        density = server.server.get_array('density')

        from matplotlib import cm
        array = cm.viridis(density/density.max())
        array *= int(255/array.max()) # normalize values
        rgba = "".join(map(chr, array.astype(dtype='uint8').tobytes()))

        socketio.emit('ret_array', {'rgba' : rgba,
                                    'vxy' : vxy_char,
                                    'fxy' : fxy},
                                    namespace=namespace,
                                    room=room)
        # Need to figure out the tracers or dump it altogether.
        if opts.tracers == True:
            print('Getting Tracers...')
            trace = server.server.get_array('tracers')
            trgba = 0
            socketio.emit('ret_trace', {'trgba': trgba},
                                        namespace=namespace,
                                        room=room)
        socketio.sleep(0)

###############################################################################
# Minor re-write of the get_server() function from Server module that sidesteps
# NoInterrupt 'not main thread' exceptions.
###############################################################################

def get_server(model, tracer_particles=None, steps=5, args=None, kwargs={}):
    """Establishes Server object for a particular model.

    Reads configuration options and keyword arguments to create a computational
    server object for a particular model.

    Parameters
    ----------
    args : optional
        Variable length argument list
    kwargs : optional
        Arbitrary keyword arguments.

    Returns
    -------
    svr : obj
        Computational server object with attached physics model.
    """
    print("Getting model from", modpath)
    module = importlib.import_module(modpath)

    opts.State = getattr(module, model)
    opts.tracer_particles = tracer_particles
    opts.steps = steps
    svr = server.Server(opts=opts)

    return svr

###############################################################################
# Function to establish server communication
###############################################################################
_OPTS = None

def get_app(run_server=False, network_server=True, **kwargs):
    global _OPTS
    if _OPTS is None:
        with log_task("Reading Configuration"):
            parser = config.get_client_parser()
            _OPTS, _other_opts = parser.parse_known_args(args="")

    app = App(opts=_OPTS)

    if run_server:
        from super_hydro.server import server
        app.server = server.run(args='', interrupted=app.interrupted,
                                block=False,
                                network_server=network_server,
                                kwargs=kwargs)
    return app

def run():
    """Run the Flask web framework.

    Starts the Flask/Flask-SocketIO web framework app, which provides HTML and
    Javascript page rendering/routing and web socket mediation between User 
    Javascript requests to a model Computational Server.
    """

    socketio.run(app, host=opts.host, port=opts.port, debug=opts.debug)
