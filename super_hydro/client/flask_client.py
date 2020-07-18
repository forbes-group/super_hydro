#Standard Library Imports
import json


# This is needed to get make sure super_hydro is in the import pathing
import os.path as osp
two_up = osp.abspath(osp.dirname(osp.dirname(osp.dirname(__file__))))
import sys
sys.path.insert(0, f'{two_up}')

#Additional Package Imports
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import numpy as np

async_mode = None

#Project-defined Modules
from super_hydro import config, communication, utils, widgets
from super_hydro.server import server

#This establishes the communication with the server.
_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task

parser = config.get_client_parser()
OPTS, _other_opts = parser.parse_known_args(args="")

app = Flask("flask_client")
socketio = SocketIO(app, async_mode=async_mode)

#Establish HTML page routes.

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/heatmap')
def heatmap():
    return render_template('base_demo.html')

#Establish /base_demo socket connections.

@socketio.on('connect', namespace='/base_demo')
def heat_connect():
    print('Connection made.')

@socketio.on('demo_run', namespace='/base_demo')
def svg_startup(startup):
    dens = (app2.get_array('density')).tolist()
    if startup['data'] == 'start':
        emit('building', dens)
    else:
        emit('running', dens)

@socketio.on('disconnect', namespace='/base_demo')
def heat_disconnect():
    print('Client disconnected.')

#End /base_demo socket connections.
if __name__ == "__main__":
    app2 = communication.NetworkServer(opts=OPTS)
    socketio.run(app, debug=True)
