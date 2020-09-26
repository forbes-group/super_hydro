#Standard Library Imports
import importlib
from threading import Lock
import time

# This is needed to get make sure super_hydro is in the import pathing
import os.path as osp
two_up = osp.abspath(osp.dirname(osp.dirname(osp.dirname(__file__))))
import sys
sys.path.insert(0, f'{two_up}')

#Additional Package Imports
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, Namespace, join_room, leave_room

#Project-defined Modules
from super_hydro import config, utils
from super_hydro.server import server
from super_hydro.physics import gpe

#This establishes the communication with the server.
_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task

app = Flask("flask_client")
socketio = SocketIO(app, async_mode='eventlet')

###############################################################################
# Flask HTML Routes.
#
# These determine which URL-endpoint will be linked to which HTML page.
###############################################################################

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gpeBEC')
def gpeBEC():
    return render_template('model.html', namespace='/gpe.BEC',
                                         Title = 'BEC',
                                         info = gpe.BEC.__doc__,
                                         sliders='gpeBEC')

@app.route('/gpeBECVortices')
def gpeBECVortices():
    return render_template('model.html', namespace='/gpe.BECVortices',
                                         Title = 'BEC - Vortices',
                                         info = gpe.BECVortices.__doc__,
                                         sliders='gpeBECVortices')

@app.route('/gpeBECFlow')
def gpeBECFlow():
    return render_template('model.html', namespace='/gpe.BECFlow',
                                         Title = 'BEC - Flow',
                                         info = gpe.BECFlow.__doc__,
                                         sliders='gpeBECFlow')

@app.route('/gpeBECVortexRing')
def gpeBECVortexRing():
    return render_template('model.html', namespace='/gpe.BECVortexRing',
                                         Title = 'BEC - Vortex Ring',
                                         info = gpe.BECVortexRing.__doc__,
                                         sliders=None)

@app.route('/gpeBECSoliton')
def gpeBECSoliton():
    return render_template('model.html', namespace='/gpe.BECSoliton',
                                         Title = 'BEC - Soliton',
                                         info = gpe.BECSoliton.__doc__,
                                         sliders='gpeBECSoliton')

@app.route('/gpeBECQuantumFriction')
def gpeBECQuantumFriction():
    return render_template('model.html', namespace='/gpe.BECQuantumFriction',
                                         Title = 'BEC - Quantum Friction',
                                         info = gpe.BECQuantumFriction.__doc__,
                                         sliders='gpeBECQuantumFriction')

@app.route('/gpeBECBreather')
def gpeBECBreather():
    return render_template('model.html', namespace='/gpe.BECBreather',
                                         Title = 'BEC - Breather',
                                         info = gpe.BECBreather.__doc__,
                                         sliders=None)

###############################################################################
# Flask-SocketIO Communications.
#
# Allows communication with JS Socket.io library using the Flask-SocketIO
# extension.
#
# Initial functionality uses 'namespaces' (single user identifiers), with intent
# to move to Flask-SocketIO 'room' functionality in future.
#
###############################################################################
# Namespace class for socket interaction methods between JS/HTML User display
# and Flask/Computational Server processing.
###############################################################################

class Demonstration(Namespace):

    fsh = {}
    d_thread = None
    thread_lock = Lock()

    def on_connect(self):
        print('Client Connected.')
        if 'cooling' and 'v0mu' not in self.fsh:
            self.fsh['cooling'] = 0
            self.fsh['v0mu'] = 0

    def on_start_srv(self, data):
        self.app = data['name'][1:]
        if self.app not in self.fsh or self.fsh[f"{self.app}"]['server'].finished == True:
            self.fsh[f"{self.app}"] = dict.fromkeys(['server', 'users'])
            self.fsh[f"{self.app}"]['server'] = get_app(model=self.app,
                                                        tracer_particles=False,
                                                        steps=5)
            self.fsh[f"{self.app}"]['server'].run(block=False,
                                                  interrupted=False)
        join_room(self.app)
        if self.fsh[f"{self.app}"]['users'] is None:
            self.fsh[f"{self.app}"]['users'] = 1
        else:
            self.fsh[f"{self.app}"]['users'] += 1
        self.fsh['init'] = {}
        for param in data['params']:
            self.fsh[f"{param}"] = self.fsh[f"{self.app}"]['server']._get(param)
            self.fsh['init'].update({f"{param}" : self.fsh[f"{param}"]})
        emit('init', self.fsh['init'],
                      room=self.app)
        if self.d_thread is None:
            self.d_thread = socketio.start_background_task(target=push_thread,
                                        namespace=data['name'],
                                        server=self.fsh[f"{self.app}"]['server'],
                                        room=self.app)

    def on_set_param(self, data):
        for key, value in data['param'].items():
            self.fsh[f"{self.app}"]['server']._set(key, float(value))
            data = {'name': key, 'param': value}
        emit('param_up', data, room=self.app)

    def on_set_log_param(self, data):
        for key, value in data['param'].items():
            self.fsh[f"{self.app}"]['server']._set(key, float(value))
            data = {'name': key, 'param': value}
        emit('log_param_up', data, room=self.app)

    def on_do_action(self, data):
        if data['name'] == 'reset':
            params = self.fsh[f"{self.app}"]['server'].reset()
            restart = {'name': f"/{self.app}"}
            restart.update({'params': params})
            leave_room(self.app)
            self.fsh[f"{self.app}"]['users'] -= 1
            self.on_start_srv(restart)
        else:
            self.fsh[f"{self.app}"]['server'].do(data['name'])

    def on_finger(self, data):
        for key, value in data['position'].items():
            pos = self.fsh[f"{self.app}"]['server']._pos_to_xy(value)
            self.fsh[f"{self.app}"]['server'].set({f"{key}": pos})

    def on_about_model(self):
        doc = self.app.__doc__
        emit('model_info', doc)

    def on_disconnect(self):
        print('Client Disconnected.')
        leave_room(self.app)
        self.fsh[f"{self.app}"]['users'] -= 1
        if (self.fsh[f"{self.app}"]['users'] == 0):
            self.fsh[f"{self.app}"]['users'] = 0
            self.fsh[f"{self.app}"]['server'].do('quit')
            self.d_thread.join()
            self.d_thread = None

###############################################################################
# Namespaces for particular physics models:

socketio.on_namespace(Demonstration('/gpe.BEC'))
socketio.on_namespace(Demonstration('/gpe.BECVortices'))
socketio.on_namespace(Demonstration('/gpe.BECFlow'))
socketio.on_namespace(Demonstration('/gpe.BECSoliton'))
socketio.on_namespace(Demonstration('/gpe.BECVortexRing'))
socketio.on_namespace(Demonstration('/gpe.BECQuantumFriction'))
socketio.on_namespace(Demonstration('/gpe.BECBreather'))

###############################################################################
#End socket connections.
###############################################################################
def push_thread(namespace, server, room):
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
                                    namespace=f"{namespace}",
                                    room=room)
        socketio.sleep(0)
################################################################################

###############################################################################
# Minor re-write of get_server() function from Server module that sidesteps
# NoInterrupt "not main thread" exceptions.
def get_server(args=None, kwargs={}):

    parser = config.get_server_parser()
    opts, other_args = parser.parse_known_args(args=args)
    opts.__dict__.update(kwargs)

    # Get the physics model.
    module = ".".join(['physics'] + opts.model.split(".")[:-1])
    cls = opts.model.split('.')[-1]
    pkg = "super_hydro"
    opts.State = getattr(importlib.import_module("." + module, pkg), cls)
    svr = server.Server(opts=opts)

    return svr

###############################################################################
# Links the Local Computational Server into a model namespace, and loads
# the Local Computational Server with the module/class specified by the
# relevant page socket Namespace (see above).
###############################################################################
def get_app(**kwargs):
    with log_task("Reading configuration"):
        parser = config.get_client_parser()
        _OPTS, _other_opts = parser.parse_known_args(args="")
    svr = get_server(args='', kwargs=kwargs)
    return svr

###############################################################################
# Establishes Flask-SocketIO server to run automatically if __main__ process.
if __name__ == "__main__":

    socketio.run(app, debug=True)
