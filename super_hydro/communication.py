from contextlib import contextmanager

import numpy as np

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
            return self.socket.recv_json()

    def send(self, msg, obj):
        """Send data to server."""
        with log_task("Sending {} to server".format(msg)):
            self.socket.send(msg)
            self.socket.recv()
            self.socket.send_json(obj)
            self.socket.recv()

    def get_array(self, msg, flags=0, copy=True, track=False):
        """Request a numpy array."""
        # https://pyzmq.readthedocs.io/en/latest/serialization.html
        with log_task("Getting {} from server".format(msg)):
            self.socket.send(msg)
            md = self.socket.recv_json(flags=flags)
            msg = self.socket.recv(flags=flags, copy=copy, track=track)
            A = np.frombuffer(msg, dtype=md['dtype']).reshape(md['shape'])
        return A

def recv_array(socket, flags=0, copy=True, track=False):
    """recv a numpy array"""
        
class Server(object):
    def __init__(self, opts):
        url = "tcp://*:{0.port}".format(opts)
        with log_task("Starting server socket: {}".format(url)):
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind("tcp://*:{}".format(opts.port))
        log("Server listening on port: {}".format(opts.port), level=100)

    def get(self):
        """Get an object from the client."""
        self.socket.send(b"")
        obj = self.socket.recv_json()
        self.socket.send(b"")
        return obj
        
    def recv(self):
        return self.socket.recv()

    def send(self, obj):
        self.socket.send_json(obj)

    def send_array(self, A, flags=0, copy=True, track=False):
        """Send a numpy array."""
        # https://pyzmq.readthedocs.io/en/latest/serialization.html
        md = dict(
            dtype = str(A.dtype),
            shape = A.shape,
        )
        
        self.socket.send_json(md, flags|zmq.SNDMORE)
        self.socket.send(A, flags, copy=copy, track=track)
        
    def respond(self, msg):
        self.socket.send(msg)
