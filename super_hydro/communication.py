from contextlib import contextmanager
import json
import zmq

from . import utils

_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task


class Client(object):
    def __init__(self, opts):
        url = "tcp://{0.host}:{0.port}".format(opts)
        with log_task("Connecting to server: {}".format(url)):
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(url)

    def request(self, msg):
        """Request an action of the server."""
        with log_task("Asking server to {}".format(msg)):
            self.socket.send(msg)
            result = self.socket.recv()
        log("Server said: {}".format(result))
                    
    def get(self, msg):
        """Request data from server."""
        with log_task("Getting {} from server".format(msg)):
            self.socket.send(msg)
            return json.loads(self.socket.recv().decode())

    def send(self, msg, obj):
        """Send data to server."""
        with log_task("Sending {} to server".format(msg)):
            self.socket.send(msg)
            self.socket.recv()
            self.socket.send(json.dumps(obj).encode())
            self.socket.recv()

        
class Server(object):
    def __init__(self, opts):
        url = "tcp://*:{0.port}".format(opts)
        with log_task("Starting server socket: {}".format(url)):
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind("tcp://*:{}".format(opts.port))
        log("Server listening on port: {}".format(opts.port))

    def get(self):
        """Get an object from the client."""
        self.socket.send(b"")
        obj = json.loads(self.socket.recv().decode())
        self.socket.send(b"")
        return obj
        
    def recv(self):
        return self.socket.recv()

    def send(self, obj):
        self.socket.send(json.dumps(obj).encode())

    def respond(self, msg):
        self.socket.send(msg)
        
        
class Communicator(object):
    def __init__(self, opts):
        
        self.sock = socket.socket()
        self.sock.connect((host, port))

    def get_raw(self, buffsize):
        return self.sock.recv(buffsize).decode()

    def get_json(self, buffsize):
        return json.loads(self.get_raw(buffsize))

    def send(self, msg):
        try:
            msg = msg.encode()
        except:
            pass
        size = len(msg)
        ####self.sock.send(size)
        self.sock.send(msg)
        
    def recv(self):
        ####size = int(self.sock.recv(1))
        return self.sock.recv(size).decode()

    def request(self, name, user_message=None):
        msg = name.encode()
        self.send(msg)
        
        error_check = self.get_raw(128)
        if error_check == "ERROR":
            if user_message is None:
                user_message = "Request {} unsuccessful".format(name)
            print(user_message)
            return False
        else:
            return True
        
