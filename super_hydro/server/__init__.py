"""SuperHydro Server."""

from collections import deque
from contextlib import contextmanager
import threading
import os
import queue
import sys
import time

PROFILE = False
if PROFILE:
    import cProfile
    def profile(filename='prof.dat'):
        def wrap(f):
            def wrapped_f(*v, **kw):
                with log_task("Profiling to {}".format(filename), level=100):
                    pr = cProfile.Profile()
                    pr.enable()
                    try:
                        res = f(*v, **kw)
                    finally:
                        pr.disable()
                        pr.dump_stats(filename)
                    return res
            return wrapped_f
        return wrap
else:
    def profile(filename=None):
        def wrap(f):
            return f
        return wrap

from matplotlib import cm

import numpy as np
from numpy import unravel_index

from .. import config, communication, utils
from . import gpe


_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task


class Computation(object):
    """Class which manages the actual computation and a queue for
    interacting with the clients.
    """

    pause_timeout = 0.1         # Time to wait when paused.

    def __init__(self, opts, message_queue, density_queue, pot_queue):
        self.opts = opts
        self.do_reset()
        self.message_queue = message_queue
        self.density_queue = density_queue
        self.pot_queue = pot_queue
        self.fps = opts.fps
        self.steps = opts.steps
        self.paused = True
        self.running = True

        self._times = deque(maxlen=100)

    @contextmanager
    def sync(self):
        """Provides a context that will wait long enough to not
        exceed `self.fps` frames per second.
        """
        tic = time.perf_counter()
        try:
            yield
        finally:
            dt = (time.perf_counter() - tic)
            self._times.append(dt)
            if PROFILE:
                log("{:.2g}+-{:.2g}ms/step".format(
                    np.mean(self._times)*1000/self.steps,
                    np.std(self._times)*1000/self.steps),
                    level=100)
            time.sleep(max(0, 1./self.fps - dt))

    @profile('prof.dat')
    def run(self):
        """Start the computation."""
        while self.running:
            with self.sync():
                if self.paused:
                    time.sleep(self.pause_timeout)
                else:
                    self.state.step(self.steps)
                self.process_queue()

    def process_queue(self):
        """Process all messages in the queue."""
        try:
            while True:
                self.process_message(*self.message_queue.get_nowait())
        except queue.Empty:
            pass

    def process_message(self, msg, *args):
        """Process a message from the queue calling the appropriate
        command `do_<msg>(*args)`."""
        cmd = getattr(self, f"do_{msg}", None)
        if cmd:
            cmd(*args)
        else:
            self.unknown_command(msg, *args)

    ######################################################################
    # Commands: Requests to the message_queue are dispatched by name.
    def do_quit(self):
        self.running = False

    def do_pause(self):
        print("pausing")
        self.paused = True

    def do_start(self):
        print("running")
        self.paused = False

    def do_get_density(self):
        self.density_queue.put(self.state.get_density())

    def do_update_finger(self, x, y):
        self.state.set_xy0(x, y)

    def do_update_V0_mu(self, V0_mu):
        self.state.V0_mu = V0_mu

    def do_update_cooling_phase(self, cooling_phase):
        self.state.cooling_phase = cooling_phase

    def do_get_pot(self):
        self.pot_queue.put(self.state.pot_z)

    def do_reset(self):
        opts = self.opts
        self.state = gpe.State(
            Nxy=(opts.Nx, opts.Ny),
            V0_mu=opts.V0_mu, test_finger=False,
            healing_length=opts.healing_length,
            dt_t_scale=opts.dt_t_scale)

    def unknown_command(self, *v):
        raise ValueError(f"Unknown Command {msg}(*{v})")


class Server(object):
    def __init__(self, opts, **kwargs):
        self.opts = opts
        self.message_queue = queue.Queue()
        self.density_queue = queue.Queue()
        self.pot_queue = queue.Queue()
        self.computation = Computation(opts=opts,
                                       message_queue=self.message_queue,
                                       density_queue=self.density_queue,
                                       pot_queue=self.pot_queue)
        self.computation_thread = threading.Thread(target=self.computation.run)
        self.comm = communication.Server(opts=opts)
        self.state = gpe.State(
            Nxy=(opts.Nx, opts.Ny),
            V0_mu=opts.V0_mu, test_finger=False,
            healing_length=opts.healing_length,
            dt_t_scale=opts.dt_t_scale)
        super().__init__(**kwargs)

    def start(self):
        finished = False
        self.computation_thread.start()
        self.message_queue.put(("start",))
        try:
            while not finished:
                # decide what kind of information it is, redirect
                client_message = self.comm.recv()
                # print("client:",client_message)

                if client_message == b"Frame":
                    self.send_frame()
                elif client_message == b"Vpos":
                    self.message_queue.put(("get_pot",))
                    pot_z = self.pot_queue.get()
                    xy = self.xy_to_pos((pot_z.real, pot_z.imag))
                    self.comm.send(tuple(xy.tolist()))
                elif client_message == b"OnTouch":
                    self.on_touch(self.comm.get())
                elif client_message == b"V0":
                    V0_mu = float(self.comm.get())
                    self.message_queue.put(("update_V0_mu", V0_mu))
                elif client_message == b"Cooling":
                    cooling = self.comm.get()
                    cooling_phase = complex(1, 10**int(cooling))
                    self.message_queue.put(("update_cooling_phase", cooling_phase))
                elif client_message == b"Reset":
                    self.reset_game()
                    self.comm.respond(b"Game Reset")
                elif client_message == b"Nxy":
                    self.comm.send(obj=(self.opts.Nx, self.opts.Ny))
                elif client_message == b"Start":
                    self.message_queue.put(("start",))
                    self.comm.respond(b"Starting")
                elif client_message == b"Pause":
                    self.message_queue.put(("pause",))
                    self.comm.respond(b"Paused")
                elif client_message == b"Quit":
                    self.comm.respond(b"Quitting")
                    finished = True
                else:
                    print("Unknown data type")
                    print("client message:", client_message)
                    self.comm.respond(b"Unknown Message")
        finally:
            self.message_queue.put(("quit",))
            self.computation_thread.join()

    def send_frame(self):
        """Send the RGB frame to draw."""
        self.message_queue.put(("get_density",))
        n_ = self.density_queue.get().T
        array = cm.viridis((n_-n_.min())/(n_.max()-n_.min()))
        array *= int(255/array.max()) # normalize V0_values
        data = array.astype(dtype='uint8')
        self.comm.send_array(data)

    def pos_to_xy(self, pos):
        """Return the (x, y) coordinates of (pos_x, pos_y) in the frame."""
        return (np.asarray(pos) - 0.5)*self.state.Lxy

    def xy_to_pos(self, xy):
        """Return the frame (pos_x, pos_y) from (x, y) coordinates."""
        return np.asarray(xy)/self.state.Lxy + 0.5

    def on_touch(self, touch_pos):
        x0, y0 = self.pos_to_xy(touch_pos)
        self.message_queue.put(("update_finger", x0, y0))

    def reset_game(self):
        self.message_queue.put(("reset",))
        self.state = gpe.State(Nxy=(self.opts.Nx, self.opts.Ny),
                               V0_mu=self.opts.V0_mu, test_finger=False,
                               healing_length=self.opts.healing_length,
                               dt_t_scale=self.opts.dt_t_scale)


def run():
    """Load the configuration and start the server."""
    parser = config.get_server_parser()
    opts, other_args = parser.parse_known_args()
    Server(opts=opts).start()
