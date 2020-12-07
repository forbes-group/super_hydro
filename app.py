#import zmq

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
#from threading import Thread

import json

from static.python.add import addition
from static.python.genarray import gen_array

async_mode = None

app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode)

@app.route('/_add_numbers')
def add_numbers():
    a, b = request.args.get('a', 0, type=int), request.args.get('b', 0, type=int)
    result = addition(a,b)
    return jsonify(result=result)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/d3test')
def d3test():
    return render_template('d3test.html', async_mode=socketio.async_mode)

#These are for d3test.html
@socketio.on('connect', namespace='/test')
def test_connect():
    print('Connection made.')
    emit('my_response', {'data': 'Connected'})

@socketio.on('my_event', namespace='/test')
def test_message(message):
    data = message['data']
    print(f"slide to {data}")
    emit('my_response', {'data': message['data']})

@socketio.on('connect_check', namespace='/test')
def check_connect(message):
    print(message['data'])
    emit('my_response', {'data': message})

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')
#end d3test.html sockets

@app.route('/heatmap')
def heatmap():
    return render_template('heat.html')

#These are for heat.html
@socketio.on('connect', namespace='/heat_sock')
def heat_connect():
    print('Connection made.')

@socketio.on('startup', namespace='/heat_sock')
def svg_startup(data):
    in_val = data['data']
    start_data = json.loads(gen_array(in_val))
    emit('build_rects', start_data)

@socketio.on('slider', namespace='/heat_sock')
def heat_slide(slider):
    slide_val = int(slider['data'])
    heat_data = json.loads(gen_array(slide_val))
    emit('new_heat', heat_data)

@socketio.on('disconnect', namespace='/heat_sock')
def heat_disconnect():
    print('Client disconnected.')

#End heat.html sockets

if __name__ == '__main__':
    socketio.run(app, debug=True)
