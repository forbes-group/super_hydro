"""Server"""

import socket
import json
import os
import sys
import logging

from matplotlib import cm

import numpy as np
from numpy import unravel_index

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from super_hydro import config, communication, utils

import gpe

_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task


class Server(object):
    def __init__(self, opts, **kwargs):
        self.opts = opts
        self.state = gpe.State(
            Nxy=(opts.Nx, opts.Ny),
            V0_mu=opts.V0_mu, test_finger=False,
            healing_length=opts.healing_length,
            dt_t_scale=opts.dt_t_scale)
        self.comm = communication.Server(opts=opts)
        super().__init__(**kwargs)

        
    def start(self):
        while True:
            #decide what kind of information it is, redirect
            client_message = self.comm.recv()
            #print("client:",client_message)

            if client_message == b"Window.size":
                self.comm.send(obj=opts.window_size)
                
            elif client_message == b"Density":
                #send the get_density
                self.send_density()

            elif client_message == b"Vpos":
                #send Vpos
                self.send_Vpos()

            elif client_message == b"OnTouch":
                self.on_touch(self.comm.get())

            elif client_message == b"V0":
                self.state.V0_mu = float(self.comm.get())

            elif client_message == b"Cooling":
                cooling = self.comm.get()
                self.state.cooling_phase = complex(1, 10**int(cooling))

            elif client_message == b"Reset":
                #reset the game
                self.reset_game()
                self.comm.respond(b"Game Reset")

            elif client_message == b"Texture":
                #sends the dimensions of the State class
                self.comm.send(obj=(self.opts.Nx, self.opts.Ny))
                
            else:
                print("Unknown data type")
                print("client message:", client_message)
                self.comm.respond("Unknown Message")

    def send_density(self):
        self.state.step(self.opts.steps)
        n_ = self.state.get_density().T
        array = cm.viridis((n_-n_.min())/(n_.max()-n_.min()))
        array *= int(255/array.max()) #normalize V0_values
        data = array.astype(dtype='uint8')
        data = data.tolist()
        self.comm.send(data)

    def send_Vpos(self):
        if self.state.V0_mu >= 0:
            Vpos = unravel_index(self.state.get_Vext().argmax(),
                                 self.state.get_Vext().shape)
        else:
            Vpos = unravel_index(self.state.get_Vext().argmin(),
                                 self.state.get_Vext().shape)
        Vpos = np.array(Vpos)
        Vpos = Vpos.tolist()
        self.comm.send(Vpos)

    def on_touch(self, touch_pos):
        winx, winy = self.opts.window_size
        Lx, Ly = self.state.Lxy
        self.state.set_xy0((touch_pos[0] - (winx/2)) * (Lx/winx),
                            (touch_pos[1] - (winy/2)) * (Ly/winy))

    def reset_game(self):
        self.state = gpe.State(Nxy=(self.opts.Nx, self.opts.Ny),
                               V0_mu=self.opts.V0_mu, test_finger=False,
                               healing_length=self.opts.healing_length,
                               dt_t_scale=self.opts.dt_t_scale)


if __name__ == "__main__":
    parser = config.get_server_parser()
    opts = parser.parse_args()
    opts.window_size = (opts.window_width, opts.window_width*opts.Ny/opts.Nx)
    Server(opts=opts).start()
