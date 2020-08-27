from gevent import monkey
monkey.patch_all()

#Standard Library Imports
import json
import threading
import importlib

# This is needed to get make sure super_hydro is in the import pathing
import os.path as osp
two_up = osp.abspath(osp.dirname(osp.dirname(osp.dirname(__file__))))
import sys
sys.path.insert(0, f'{two_up}')

#Additional Package Imports
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, Namespace
import numpy as np

#Project-defined Modules
from super_hydro import config, communication, utils, widgets
from super_hydro.server import server
from super_hydro.contexts import nointerrupt, NoInterrupt

#This establishes the communication with the server.
_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task


app = Flask("flask_client")
socketio = SocketIO(app, async_mode='gevent')

class TimeoutError(Exception):
    """Operation timed out."""

def error(msg):
    """Return a JSON serializable quantity signaling an error."""
    return f"Error: {msg}"


"""Flask HTML Routes.

These determine which URL-endpoint will be linked to which HTML page.
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/heatmap')
def heatmap():
    return render_template('base_demo.html')

"""Flask-SocketIO Communications.

Currently modifies the Communications module to register with Javascript's
Socket.io library using the Flask-SocketIO extension.

The general usage is Javascript Socket.IO will 'emit()' messages with specified
tags (ex: 'connect') which are then pathed to appropriate methods via the
'@socketio.on()' method, which will 'emit()' appropriate responses.

Initial functionality uses 'namespaces' (single user identifiers), with intent to
move to Flask-SocketIO 'room' functionality in future.
"""

class ModelServer(object):

    server = None

    def __init__(self, opts):
        self.opts = opts
        self._running = True

    def comm(self):
        if self._running:
            return self.server.comm

    def density(self):
        with log_task("Get density from server."):
            return self.server.get_array("density")

    def run(self):
        if self.server is None:
            self.server = communication.Server(opts=self.opts)

    def quit(self):
        self.server.do("quit")
        self._running = False


class Demonstration(Namespace):
    def on_connect(self):
        print('Client Connected.')

    def on_disconnect(self):
        app2.quit()
        print('Client Disconnected.')

    def on_start_srv(self, data):
        app_name = data['data'][1:]
        app2 = get_app(model=app_name)
        app2.server.run(block=False, interrupted=False)

    def on_get_array(self, data):
        byte_arr = (app2.density()).tobytes()
        byte_arr_char = "".join([chr(i) for i in byte_arr])
        emit('ret_array', byte_arr_char)

socketio.on_namespace(Demonstration('/gpe.BECBase'))
socketio.on_namespace(Demonstration('/gpe.BECSoliton'))
socketio.on_namespace(Demonstration('/gpe.BECVortexRing'))
socketio.on_namespace(Demonstration('/gpe.BECBreather'))
#############################################################################
#End /base_demo socket connections.

_OPTS = None

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

def get_app(**kwargs):
    global _OPTS
    if _OPTS is None:
        with log_task("Reading configuration"):
            parser = config.get_client_parser()
            _OPTS, _other_opts = parser.parse_known_args(args="")
    global app2
    app2 = ModelServer(opts=_OPTS)
    app2.server = get_server(args='', kwargs=kwargs)

    return app2

if __name__ == "__main__":

    socketio.run(app, debug=True)
