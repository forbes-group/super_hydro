import gpe
import socket
import attr
import json

from matplotlib import cm

import numpy as np
from numpy import unravel_index

host = "127.0.0.1"
port = 8888

@attr.s
class Parameters(object):
    Nx = attr.ib(default=128//2)
    Ny = attr.ib(default=64//2)
    window_width = attr.ib(default=1000)
    healing_length = attr.ib(default=0.1)
    dt_t_scale = attr.ib(default=1.0)
    steps = attr.ib(default=20)

    #@property
    def window_size(self):
        return (self.window_width, self.window_width*self.Ny/self.Nx)

    def Nxy(self):
        return (self.Nx,self.Ny)

class Server():
    def __init__(self, **kwargs):
        self.params = Parameters()
        self.state = gpe.State(Nxy=(self.params.Nx, self.params.Ny),
                            V0_mu=0.5, test_finger=False,
                            healing_length=self.params.healing_length,
                            dt_t_scale=self.params.dt_t_scale)
        self.sock = socket.socket()
        self.sock.bind((host,port))
        self.sock.listen(1)
        self.conn, self.addr = self.sock.accept()
        window_size = json.dumps(self.params.window_size())
        self.conn.send(window_size.encode())
        super().__init__(**kwargs)

    def start(self):
        while True:
            #decide what kind of information it is, redirect
            client_message = self.conn.recv(2048).decode()
            #print("client:",client_message)

            if client_message == "Density":
                #send the get_density
                self.send_density()

            elif client_message == "Vpos":
                #send Vpos
                self.send_Vpos()

            elif client_message[:7] == "OnTouch":
                #touch data
                touch_input = json.loads(client_message[7:])
                self.on_touch(touch_input)

            elif client_message[:2] == "V0":
                #update V0
                V0_value = client_message[2:]
                self.state.V0_mu = float(V0_value)
                self.conn.send("success".encode())

            elif client_message[:7] == "Cooling":
                #update cooling value
                cooling = client_message[7:]
                self.state.cooling_phase = complex(1,10**int(cooling))
                self.conn.send("success".encode())

            elif client_message == "Reset":
                #reset the game
                self.reset_game()

            elif client_message == "Texture":
                #sends the dimensions of the State class
                Nxy = json.dumps(self.params.Nxy())
                print(Nxy)
                self.conn.send(Nxy.encode())

            else:
                print("Unkown data type")
                print("client message:", client_message)

    def send_density(self):
        self.state.step(self.params.steps)
        n_ = self.state.get_density().T
        array = cm.viridis((n_-n_.min())/(n_.max()-n_.min()))
        array *= int(255/array.max()) #normalize V0_values
        data = array.astype(dtype='uint8')
        data = data.tolist()
        serialized = json.dumps(data)
        self.conn.send(serialized.encode())

    def send_Vpos(self):
        if self.state.V0_mu >= 0:
            Vpos = unravel_index(self.state.get_Vext().argmax(),
                                 self.state.get_Vext().shape)
        else:
            Vpos = unravel_index(self.state.get_Vext().argmin(),
                                 self.state.get_Vext().shape)
        Vpos = np.array(Vpos)
        Vpos = Vpos.tolist()
        self.conn.send((json.dumps(Vpos).encode()))

    def on_touch(self, touch_pos):
        winx, winy = self.params.window_size()
        Lx, Ly = self.state.Lxy
        self.state.set_xy0((touch_pos[0] - (winx/2)) * (Lx/winx),
                            (touch_pos[1] - (winy/2)) * (Ly/winy))
        self.conn.send("success".encode())

    def reset_game(self):
        self.state = gpe.State(Nxy=(self.params.Nx, self.params.Ny),
                            V0_mu=0.5, test_finger=False,
                            healing_length=self.params.healing_length,
                            dt_t_scale=self.params.dt_t_scale)
        self.conn.send("success".encode())


if __name__ == "__main__":
    Server().start()
