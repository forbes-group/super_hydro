import gpe
import socket
import attr

from matplotlib import cm

import numpy as np
from numpy import unravel_index

host = "127.0.0.1"
port = 19873

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
        super().__init__(**kwargs)

    def start(self):
        self.sock = socket.socket()
        self.sock.bind((host,port))
        self.sock.listen(1)
        self.conn, self.addr = self.sock.accept()

        #making it an np array makes sending across the buffer easier
        window_size = np.array(self.params.window_size())
        print("window size: ", window_size)
        self.conn.send(window_size)

        while True:
            #decide what kind of information it is, redirect
            client_message = self.conn.recv(1024).decode()
            #print("client:",client_message)

            if client_message == "Density":
                #send the get_density
                self.send_density()

            elif client_message == "Vpos":
                #send Vpos
                self.send_Vpos()

            elif client_message == "OnTouch":
                #touch data
                self.on_touch()

            elif client_message == "V0":
                #update V0
                self.update_V0()

            elif client_message == "Cooling":
                #update cooling value
                self.update_cooling()

            elif client_message == "Reset":
                #reset the game
                self.reset_game()

            elif client_message == "Texture":
                #sends the dimensions of the State class
                Nxy = np.array(self.params.Nxy())
                self.conn.send(Nxy)

            else:
                print("Unkown data type")
                print("client message:", client_message)
                self.conn.send("Unknown data type".encode())

    def send_density(self):
        self.state.step(self.params.steps)
        n_ = self.state.get_density().T
        array = cm.viridis((n_-n_.min())/(n_.max()-n_.min()))
        array *= int(255/array.max()) #normalize V0_values
        self.conn.send(array)
        self.conn.recv(1024).decode()
        self.conn.send("Go".encode())

    def send_Vpos(self):
        if self.state.V0_mu >= 0:
            Vpos = unravel_index(self.state.get_Vext().argmax(),
                                 self.state.get_Vext().shape)
        else:
            Vpos = unravel_index(self.state.get_Vext().argmin(),
                                 self.state.get_Vext().shape)
        #print("Vpos:", Vpos)
        self.conn.send(np.array(Vpos, dtype='int'))

    def on_touch(self):
        #print("touched")
        self.conn.send("SendTouch".encode())
        touch_pos = np.frombuffer(self.conn.recv(128),dtype='float')
        winx, winy = self.params.window_size()
        Lx, Ly = self.state.Lxy
        self.state.set_xy0((touch_pos[0] - (winx/2)) * (Lx/winx),
                            (touch_pos[1] - (winy/2)) * (Ly/winy))
        self.conn.send("Continue".encode())

    def reset_game(self):
        self.state = gpe.State(Nxy=(self.params.Nx, self.params.Ny),
                            V0_mu=0.5, test_finger=False,
                            healing_length=self.params.healing_length,
                            dt_t_scale=self.params.dt_t_scale)
        self.conn.send("continue".encode())

    def update_V0(self):
        self.conn.send("SendV0".encode())
        response = self.conn.recv(128).decode()
        self.state.V0_mu = float(response)
        print("V0:", self.state.V0_mu)
        self.conn.send("V0".encode())

    def update_cooling(self):
        self.conn.send("SendCooling".encode())
        cooling = self.conn.recv(128).decode()
        self.state.cooling_phase = complex(1,10**int(cooling))
        #print("Cool:", self.state.cooling_phase)
        self.conn.send("cooling".encode())

if __name__ == "__main__":
    Server().start()
