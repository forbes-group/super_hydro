#Standard Library Imports
import importlib
from threading import Lock
import time

# This is needed to get make sure super_hydro is in the import pathing
import os.path as osp
two_up = osp.abspath(osp.dirname(osp.dirname(osp.dirname(__file__))))
import sys, inspect
sys.path.insert(0, f'{two_up}')

#Additional Package Imports
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, Namespace, join_room, leave_room, close_room

#Project-defined Modules
from super_hydro import config, utils
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
modpath = ".".join(['physics'] + [opts.module])

module = importlib.import_module("." + modpath, "super_hydro")
clsmembers = inspect.getmembers(module, inspect.isclass)
modelcls = [clsmembers[x][0] for x in range(len(clsmembers))]

app = Flask("flask_client")
#app.config['EXPLAIN_TEMPLATE_LOADING'] = True
socketio = SocketIO(app, async_mode='eventlet')

###############################################################################
# Flask HTML Routes.
#
# These determine which URL-endpoint will be linked to which HTML page.
###############################################################################

@app.route('/')
def index():
    cls = modelcls
    return render_template('index.html', models=cls)

@app.route('/<cls>')
def modelpage(cls):
    info = getattr(module, cls)
    return render_template('model.html', model=cls,
                                         Title= f'{cls}',
                                         info= info.__doc__,
                                         sliders=info.sliders,
                                         models=modelcls)
###############################################################################
# Flask-SocketIO Communications.
#
# Allows communication with JS Socket.io library using the Flask-SocketIO
# extension.
###############################################################################

class Demonstration(Namespace):
    '''Container for managing independent models.'''
    fsh = {}
    thread_lock = Lock()

    def on_connect(self):
        '''Verifies Socket connection'''
        print('Client Connected.')
        if 'cooling' and 'v0mu' not in self.fsh:
            self.fsh['cooling'] = 0
            self.fsh['v0mu'] = 0

    def on_start_srv(self, data):
        '''Establishes physics model server and UI communication Room'''
        model = data['name']
        if model not in self.fsh or self.fsh[f"{model}"]['server'].finished == True:
            self.fsh[f"{model}"] = dict.fromkeys(['server', 'users', 'd_thread'])
            self.fsh[f"{model}"]['server'] = get_app(model=model,
                                                        tracer_particles=False,
                                                        steps=5)
            self.fsh[f"{model}"]['server'].run(block=False,
                                                  interrupted=False)
        join_room(model)
        if self.fsh[f"{model}"]['users'] is None:
            self.fsh[f"{model}"]['users'] = 1
        else:
            self.fsh[f"{model}"]['users'] += 1
        self.fsh['init'] = {}
        for param in data['params']:
            self.fsh[f"{param}"] = self.fsh[f"{model}"]['server']._get(param)
            self.fsh['init'].update({f"{param}" : self.fsh[f"{param}"]})
        emit('init', self.fsh['init'],
                     room=model)
        if self.fsh[f"{model}"]['d_thread'] is None:
            self.fsh[f"{model}"]['d_thread'] = socketio.start_background_task(target=push_thread,
                                        namespace='/modelpage',
                                        server=self.fsh[f"{model}"]['server'],
                                        room=model)

    def on_set_param(self, data):
        '''Passes parameter values to computational server'''
        model = data['data']
        for key, value in data['param'].items():
            self.fsh[f"{model}"]['server']._set(key, float(value))
            data = {'name': key, 'param': value}
        emit('param_up', data, room=model)

    def on_set_log_param(self, data):
        '''Passes logarithmic parameter values to computational server.'''
        model = data['data']
        for key, value in data['param'].items():
            self.fsh[f"{model}"]['server']._set(key, float(value))
            data = {'name': key, 'param': value}
        emit('log_param_up', data, room=model)

    def on_do_action(self, data):
        '''Passes directions to computational server.'''
        model = data['data']
        if data['name'] == 'reset':
            params = self.fsh[f"{model}"]['server'].reset()
            restart = {'name': f"{model}"}
            restart.update({'params': params})
            leave_room(model)
            self.fsh[f"{model}"]['users'] -= 1
            self.on_start_srv(restart)
        else:
            self.fsh[f"{model}"]['server'].do(data['name'])

    def on_finger(self, data):
        '''Passes updated finger potential postioning.'''
        model = data['data']
        for key, value in data['position'].items():
            pos = self.fsh[f"{model}"]['server']._pos_to_xy(value)
            self.fsh[f"{model}"]['server'].set({f"{key}": pos})

    def on_user_exit(self, data):
        '''Removes user from current Room and closes Room/Server if empty.'''
        model = data['data']
        print(model)
        leave_room(model)
        self.fsh[f"{model}"]['users'] -= 1
        if (self.fsh[f"{model}"]['users'] == 0):
            self.fsh[f"{model}"]['users'] = 0
            self.fsh[f"{model}"]['server'].do('quit')
            self.fsh[f"{model}"]['d_thread'].join()
            self.fsh[f"{model}"]['d_thread'] = None

    def on_disconnect(self):
        print('Client Disconnected.')

###############################################################################

socketio.on_namespace(Demonstration('/modelpage'))

###############################################################################
#End socket connections.
###############################################################################
def push_thread(namespace, server, room):
    '''Continuously queues and pushes display information to Client.'''
    while not server.finished:
        fxy = [server._get('finger_x'), server._get('finger_y')]
        vxy = (server._get_Vpos()).tobytes()
        vxy_char = "".join([chr(i) for i in vxy])

        density = server.get_array("density")

        from matplotlib import cm
        array = cm.viridis(density/density.max())
        array *= int(255/array.max())  # normalize values
        rgba = "".join(map(chr, array.astype(dtype='uint8').tobytes()))

        socketio.emit('ret_array', {'rgba': rgba,
                                    'vxy': vxy_char,
                                    'fxy': fxy},
                                    namespace=namespace,
                                    room=room)
        socketio.sleep(0)
################################################################################

###############################################################################
# Minor re-write of get_server() function from Server module that sidesteps
# NoInterrupt "not main thread" exceptions.
def get_server(args=None, kwargs={}):
    '''Initializes local computational server for a given model.'''
    parser = config.get_server_parser()
    opts, other_args = parser.parse_known_args(args=args)
    opts.__dict__.update(kwargs)

    # Get the physics model.
    module = ".".join(['physics'] + [opts.module])# + opts.model.split(".")[:-1])
    cls = opts.model.split('.')[-1]
    print(cls)
    pkg = "super_hydro"
    opts.State = getattr(importlib.import_module("." + module, pkg), cls)
    svr = server.Server(opts=opts)

    return svr

###############################################################################
# Links the Local Computational Server into a model namespace, and loads
# the Local Computational Server with the module/class specified by the
# relevant socket Room (see above).
###############################################################################
def get_app(**kwargs):
    '''Reads configuration options and gets computational server.'''
    with log_task("Reading configuration"):
        parser = config.get_client_parser()
        _OPTS, _other_opts = parser.parse_known_args(args="")
    svr = get_server(args='', kwargs=kwargs)
    return svr

###############################################################################
def run():
    '''Starts the Client backend Flask service.'''
    socketio.run(app, debug=True)
