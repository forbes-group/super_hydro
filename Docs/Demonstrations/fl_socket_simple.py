# Full documentation with light-tutorial introduction:
# https://flask-socketio.readthedocs.io/en/latest/
####################################################

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, Namespace

####################################################
# The following initializes the Flask instance, and
# then connects it into Flask-SocketIO.
####################################################

app = Flask(__name__)
socketio = SocketIO(app)

####################################################
# The following connects a URL to the app routing
# for navigation.
# When a user navigates to this URL, the Flask app
# will be call the function decorated.
####################################################

@app.route('/')
def index():
    # Have the Flask app render a static HTML page
    return render_template('index.html')

####################################################
# The following is a Flask-SocketIO Namespace Class.
# When a socket event is registered, 'socketio' will
# search within this Class for a method following the
# convention:
# 'on_'+'<event_name>'
# If no method matches the above form, the event is
# ignored; otherwise, the method is called.
####################################################

class BasicSockets(Namespace):

    def on_connect(self):
        ############################################
        # This is a standard event name for Flask-
        # SocketIO, and must always be included.
        ############################################
        # When a socket connection is made, send a
        # basic notification to the terminal.

        return print('Client Connected.')

    def on_disconnect(self):
        ############################################
        # This is a standard event name for Flask-
        # SocketIO, and must always be included.
        ############################################
        # When the socket connection is closed, send
        # a basic notification to the terminal.

        return print('Client Disconnected.')

    def on_custom_event(self, data):
        ############################################
        # This is an example of a custom event name.
        ############################################
        # When 'custom_event' is triggered, take the
        # 'data' and increment by 1, then 'emit' the
        # new value back to the JS/HTML page.

        print(f'Received {data}.')
        data = int(data)
        data += 1
        print(f'Sending {data}')
        emit('custom_response', data)

####################################################
# The following defines which Namespaces are valid
# for Flask-SocketIO to listen for.
####################################################
socketio.on_namespace(BasicSockets('/index'))

####################################################
# Finally, Flask-SocketIO starts up a server at the
# address //localhost:5000 (default) automatically
# if it is __main__.
#
# Pass the argument 'debug=True' into run() for dynamic
# server restarts when it detects changes to the main
# code.

if __name__ == '__main__':
    socketio.run(app, debug=False)
