from contextlib import contextmanager
import json
import socket
import logging

def log(msg, level=logging.ERROR):
    """Log msg to the logger."""
    # Get logger each time so handlers are properly dealt with
    logging.getLogger(__name__).log(level=level, msg=msg)


@contextmanager
def log_task(msg, _level=[0]):
    indent = " " * 2 * _level[0]
    msg = indent + msg
    log(msg + "...")
    try:
        _level[0] += 1
        yield
        log(msg + ". Done.")
    except:
        log(msg + ". Failed!", level=logging.ERROR)
        raise
    finally:
        _level[0] -= 1


class Communicator(object):
    def __init__(self, host, port):
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
        
