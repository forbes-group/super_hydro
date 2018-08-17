import json
import socket
import logging

def log(msg, level=logging.ERROR):
    """Log msg to the logger."""
    # Get logger each time so handlers are properly dealt with
    logging.getLogger(__name__).log(level=level, msg=msg)


class Communicator(object):
    def __init__(self, host, port):
        self.sock = socket.socket()
        self.sock.connect((host, port))

    def get_raw(self, buffsize):
        return self.sock.recv(buffsize).decode()

    def get_json(self, buffsize):
        return json.loads(self.get_raw(buffsize))

    def send(self, msg):
        self.sock.send(msg.encode())
        
    def request(self, name, msg=None):
        self.sock.send(name.encode())
        error_check = self.get_raw(128)
        if error_check == "ERROR":
            if msg is None:
                msg = "Request {} unsuccessful".format(name)
            print(msg)
            return False
        else:
            return True
        
