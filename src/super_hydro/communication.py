"""Communications Module.

The communication layer has a Client and a Server.  These manage the
socket connections (with zmq).  Requests and the actual network
protocol are manged by Request objects which have a specialized
`request()` method (for the Client to use) and a specialized
`respond()` method (for the Server to use).

The general usage is that the server should call `recv()` which will
return an appropriate `Request` object.  The server should then
respond by calling the `Request.respond()` method with appropriate
objects.

Unless otherwise specified, messages should by bytes objects.
"""
import time

import numpy as np

import zmq

from . import utils

from .interfaces import IServer, implementer, verifyClass


__all__ = ["Client", "Server", "TimeoutError", "error"]

_LOGGER = utils.Logger(__name__.split(".")[-1])
log = _LOGGER.log
log_task = _LOGGER.log_task


class TimeoutError(Exception):
    """Operation timed out."""


def error(msg):
    """Return a JSON serializable quantity signaling an error."""
    return f"Error: {msg}"


######################################################################
# Client and Server base communicators.  These classes define a simple
# protocol for sending and receiving data based on the REQ and REP
# models of zmq.  With this model, the client must make a request
# (REQ) of the server, which then responds (REP).  For each of these
# transactions the client must send() and recv() while the server must
# recv() and then send().
class Client(object):
    """Basic communication class for the client."""

    def __init__(self, opts):
        self.logger = _LOGGER
        self.log_task = self.logger.log_task

        url = "tcp://{0.host}:{0.port}".format(opts)
        with self.log_task("Connecting to server: {}".format(url)):
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(url)

    def reset(self):
        """Special reset method that returns the param_dict."""
        with self.self.log_task("Reset"):
            self.socket.send(msg)
            return self.socket.recv_json()

    def do(self, action):
        """Request an action of the server."""
        with self.log_task(f"Do: {action}"):
            self.socket.send(action.encode())
            return self.socket.recv()

    def get(self, params):
        """Request data from server."""
        with self.log_task(f"Getting {params} from server"):
            self.socket.send(b"get")
            response = self.socket.recv()
            if response != b"ok":
                raise IOError(f"Server declined request to get saying {response}")
            self.socket.send_json(params)
            return self.socket.recv_json()

    def send(self, msg, obj):
        """Send data to server."""
        with self.log_task("Sending {} to server".format(msg)):
            self.socket.send(msg)
            response = self.socket.recv()
            if response != b"ok":
                raise IOError(
                    "Server declined request to send {} saying {}".format(msg, response)
                )
            self.socket.send_json(obj)
            return self.socket.recv()

    def get_array(self, msg, flags=0, copy=True, track=False):
        """Request a numpy array."""
        # https://pyzmq.readthedocs.io/en/latest/serialization.html
        with self.log_task("Getting {} from server".format(msg)):
            self.socket.send(msg)
            md = self.socket.recv_json(flags=flags)
            msg = self.socket.recv(flags=flags, copy=copy, track=track)
            return np.frombuffer(msg, dtype=md["dtype"]).reshape(md["shape"])

    def send_array(self, msg, A, flags=0, copy=True, track=False):
        """Request a numpy array."""
        # https://pyzmq.readthedocs.io/en/latest/serialization.html
        with self.log_task("Sending array {} to server".format(msg)):
            md = dict(dtype=str(A.dtype), shape=A.shape)

            # Somewhat convoluted since each send() requires a recv()
            self.socket.send(msg)
            response = self.socket.recv()
            if response != b"ok":
                raise IOError(
                    "Server declined request to send {} saying {}".format(msg, response)
                )
            self.socket.send_json(md, flags | zmq.SNDMORE)
            self.socket.send(A, flags, copy=copy, track=track)
            return self.socket.recv()


class Server(object):
    def __init__(self, opts):
        self.logger = _LOGGER
        self.log_task = self.logger.log_task

        url = "tcp://*:{0.port}".format(opts)
        with self.log_task("Starting server socket: {}".format(url)):
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind("tcp://*:{}".format(opts.port))
        self.logger.info("Server listening on port: {}".format(opts.port))

    def recv(self, timeout=None):
        """Listen for incoming requests from clients.

        Parameters
        ----------
        timeout : None, float
           If provided, then recv() will only block for this period of
           time.  If no message is received, the it will raise a
           TimeoutError exception.
        """
        if timeout is None:
            return self.socket.recv()

        # Non-blocking behavior
        try:
            return self.socket.recv(flags=zmq.NOBLOCK)
        except zmq.ZMQError:
            pass

        time.sleep(timeout)
        try:
            return self.socket.recv(flags=zmq.NOBLOCK)
        except zmq.ZMQError:
            raise TimeoutError()

    def respond(self, msg):
        """Send simple responds to a request."""
        self.socket.send(msg)

    def send(self, obj):
        """Send requested JSON encoded object."""
        self.socket.send_json(obj)

    def get_params(self):
        """Receive a JSON encoded list of params.

        This method could in principle be replaced by a call to get(), but then we need
        to insert a complete set of send-recv pairs.
        """
        self.socket.send(b"ok")
        return self.socket.recv_json()

    def get(self, response=b"ok"):
        """Receive a JSON encoded object and return the decoded object."""
        self.socket.send(b"ok")
        obj = self.socket.recv_json()
        self.socket.send(response)
        return obj

    def send_array(self, A, flags=0, copy=True, track=False):
        """Send a numpy array."""
        # https://pyzmq.readthedocs.io/en/latest/serialization.html
        md = dict(dtype=str(A.dtype), shape=A.shape)
        self.socket.send_json(md, flags | zmq.SNDMORE)
        self.socket.send(A, flags, copy=copy, track=track)

    def get_array(self, response=b"", flags=0, copy=True, track=False):
        """Receive and return a numpy array."""
        # https://pyzmq.readthedocs.io/en/latest/serialization.html
        self.socket.send(b"ok")
        md = self.socket.recv_json(flags=flags)
        data = self.socket.recv(flags=flags, copy=copy, track=track)
        self.socket.send(response)
        return np.frombuffer(data, dtype=md["dtype"]).reshape(md["shape"])


@implementer(IServer)
class LocalNetworkServer:
    """Wrapper for the `server.Server` class.

    This is used locally as a proxy for a remote server, allowing local clients to
    interact with the remote server through this proxy.
    """

    def __init__(self, opts):
        self.logger = _LOGGER
        self.log_task = self.logger.log_task

        self.opts = opts
        with self.log_task("Connecting to server"):
            self.comm = Client(opts=self.opts)

    def get_available_commands(self, client=None):
        return self.comm.get(params=["available_commands"])["available_commands"]

    def do(self, action, client=None):
        self.comm.do(action)

    def get(self, params, client=None):
        return self.comm.get(params=params)

        param_dict = {param: self.comm.get(param.encode()) for param in params}
        return param_dict

    def set(self, param_dict, client=None):
        """Set specified parameter."""
        self.comm.send(b"set", param_dict)

    def get_array(self, param, client=None):
        return self.comm.get_array(param.encode())

    def reset(self, client=None):
        """Reset the server."""
        self.do("reset")

    def quit(self, client=None):
        """Quit the server."""
        self.do("quit")


verifyClass(IServer, LocalNetworkServer)
