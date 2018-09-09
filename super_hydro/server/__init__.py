"""SuperHydro Server."""

import os
import sys

from matplotlib import cm

import numpy as np
from numpy import unravel_index

from .. import config, communication, utils
from . import gpe


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

            if client_message == b"Frame":
                self.send_frame()

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

            elif client_message == b"Nxy":
                self.comm.send(obj=(self.opts.Nx, self.opts.Ny))
                
            else:
                print("Unknown data type")
                print("client message:", client_message)
                self.comm.respond("Unknown Message")

    def send_frame(self):
        """Send the RGB frame to draw."""
        self.state.step(self.opts.steps)
        n_ = self.state.get_density().T
        array = cm.viridis((n_-n_.min())/(n_.max()-n_.min()))
        array *= int(255/array.max()) # normalize V0_values
        data = array.astype(dtype='uint8')
        self.comm.send_array(data)

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
        x0, y0 = (np.asarray(touch_pos) - 0.5)*self.state.Lxy
        self.state.set_xy0(x0, y0)

    def reset_game(self):
        self.state = gpe.State(Nxy=(self.opts.Nx, self.opts.Ny),
                               V0_mu=self.opts.V0_mu, test_finger=False,
                               healing_length=self.opts.healing_length,
                               dt_t_scale=self.opts.dt_t_scale)

def run():
    """Load the configuration and start the server."""
    parser = config.get_server_parser()
    opts, other_args = parser.parse_known_args()
    Server(opts=opts).start()
