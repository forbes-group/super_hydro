__doc__ = """SuperHydro Server."""

from collections import deque
from contextlib import contextmanager
import importlib
import threading
import queue
import time

from matplotlib import cm

import numpy as np

from .. import config, communication, utils, widgets
from ..physics import tracer_particles
from ..contexts import nointerrupt

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


__all__ = ['run', '__doc__', '__all__']


_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task


class Computation(object):
    """Class which manages the actual computation and a queue for
    interacting with the clients.
    """

    pause_timeout = 0.1         # Time to wait when paused.

    def __init__(self, opts,
                 message_queue, density_queue, pot_queue, tracer_queue):
        self.opts = opts
        self.do_reset()
        self.message_queue = message_queue
        self.density_queue = density_queue
        self.tracer_queue = tracer_queue
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
                    self.state.step(self.steps,
                                    tracer_particles=self.tracer_particles)
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

    def do_get_tracer(self):
        self.tracer_queue.put(self.tracer_particles.get_tracer_particles())

    def do_update_finger(self, x, y):
        self.state.set('xy0', (x, y))

    def do_update_cooling_phase(self, cooling_phase):
        self.state.set('cooling_phase', cooling_phase)

    def do_update(self, param, value):
        self.state.set(param, value)

    def do_get_pot(self):
        self.pot_queue.put(self.state.get('pot_z'))

    def do_reset_tracers(self):
        opts = self.opts
        if opts.tracer_particles:
            self.tracer_particles = tracer_particles.TracerParticles(
                state=self.state,
                N_particles=opts.tracer_particles)
        else:
            self.tracer_particles = None

    def do_reset(self):
        opts = self.opts
        self.state = opts.State(opts=opts)
        self.do_reset_tracers()

    def unknown_command(self, msg, *v):
        raise ValueError(f"Unknown Command {msg}(*{v})")


class Server(object):
    _poll_interval = 0.1

    def __init__(self, opts, **kwargs):
        self.opts = opts
        self.message_queue = queue.Queue()
        self.density_queue = queue.Queue()
        self.tracer_queue = queue.Queue()
        self.pot_queue = queue.Queue()
        self.computation = Computation(opts=opts,
                                       message_queue=self.message_queue,
                                       density_queue=self.density_queue,
                                       pot_queue=self.pot_queue,
                                       tracer_queue=self.tracer_queue)
        self.computation_thread = threading.Thread(target=self.computation.run)
        self.comm = communication.Server(opts=opts)
        self.state = opts.State(opts=opts)
        super().__init__(**kwargs)

    @nointerrupt
    def run(self, interrupted, block=True):
        """Run the server, blocking if desired."""
        kwargs = dict(interrupted=interrupted)
        if block:
            return self.run_server(**kwargs)
        else:
            self.server_thread = threading.Thread(
                target=self.run_server, kwargs=kwargs)
            self.server_thread.start()

    def run_server(self, interrupted=None):
        finished = False
        self.computation_thread.start()
        self.message_queue.put(("start",))
        try:
            while not finished and not interrupted:
                try:
                    # Do this so we can receive interrupted messages
                    # if the user interrupts.
                    client_message = self.comm.recv(
                        timeout=self._poll_interval)
                except communication.TimeoutError:
                    continue

                if client_message == b"Frame":
                    self.send_frame()
                elif client_message == b"Vpos":
                    self.message_queue.put(("get_pot",))
                    pot_z = self.pot_queue.get()
                    xy = self.xy_to_pos((pot_z.real, pot_z.imag))
                    self.comm.send(tuple(xy.tolist()))
                elif client_message == b"layout":
                    self.send_layout()
                elif client_message == b"OnTouch":
                    self.on_touch(self.comm.get())
                elif client_message == b"set":
                    param, value = self.comm.get()
                    log("Got set {}={}".format(param, value))
                    self.on_set(param=param, value=value)
                elif client_message == b"Cooling":
                    cooling = self.comm.get()
                    cooling_phase = complex(1, 10**int(cooling))
                    self.message_queue.put(("update_cooling_phase",
                                            cooling_phase))
                elif client_message == b"reset":
                    self.reset_game()
                    self.comm.respond(b"Game Reset")
                elif client_message == b"reset_tracers":
                    self.message_queue.put(("reset_tracers",))
                    self.comm.respond(b"Tracers Reset")
                elif client_message == b"Nxy":
                    self.comm.send(obj=(self.opts.Nx, self.opts.Ny))
                elif client_message == b"Start":
                    self.message_queue.put(("start",))
                    self.comm.respond(b"Starting")
                elif client_message == b"Pause":
                    self.message_queue.put(("pause",))
                    self.comm.respond(b"Paused")
                elif client_message == b"quit":
                    self.comm.respond(b"Quitting")
                    finished = True
                elif client_message == b"Tracer":
                    self.send_tracer()
                else:
                    print("Unknown data type")
                    print("client message:", client_message)
                    self.comm.respond(b"Unknown Message")
        finally:
            self.message_queue.put(("quit",))
            self.computation_thread.join()

    def send_layout(self):
        """Send the layout to the client."""
        layout = self.state.layout
        interactive_widgets = widgets.get_interactive_widgets(layout)
        for w in interactive_widgets:
            w.value = self.state.params[w.name]
        self.comm.send(repr(layout))

    def send_frame(self):
        """Send the RGB frame to draw."""
        self.message_queue.put(("get_density",))
        n_ = self.density_queue.get().T
        # array = cm.viridis((n_-n_.min())/(n_.max()-n_.min()))
        array = cm.viridis(n_/n_.max())

        array = self._update_frame_with_tracer_particles(array)

        array *= int(255/array.max())  # normalize values
        data = array.astype(dtype='uint8')
        self.comm.send_array(data)

    def send_tracer(self):
        self.message_queue.put(("get_tracer",))
        trpos = self.tracer_queue.get()
        i = 0
        while i < len(trpos):
            xy = self.xy_to_pos((trpos[i].real, trpos[i].imag))
            trpos[i] = xy
            i = i + 1
        array = trpos
        trdata = array.astype(dtype='uint8')
        self.comm.send_array(trdata)

    def _update_frame_with_tracer_particles(self, array):
        # Note: array has x and y swapped...
        self.message_queue.put(("get_tracer",))
        pos = self.tracer_queue.get()  # Complex array of positions

        ix, iy = self.computation.tracer_particles.get_inds(
            pos, state=self.state)
        alpha = self.opts.tracer_alpha
        array[iy, ix, ...] = (
            (1-alpha)*array[iy, ix, ...]
            + alpha*np.array(self.opts.tracer_color))
        return array

    def pos_to_xy(self, pos):
        """Return the (x, y) coordinates of (pos_x, pos_y) in the frame."""
        return (np.asarray(pos) - 0.5)*self.state.get('Lxy')

    def xy_to_pos(self, xy):
        """Return the frame (pos_x, pos_y) from (x, y) coordinates."""
        return np.asarray(xy)/self.state.get('Lxy') + 0.5

    def on_set(self, param, value):
        self.message_queue.put(("update", param, value))

    def on_touch(self, touch_pos):
        x0, y0 = self.pos_to_xy(touch_pos)
        self.message_queue.put(("update_finger", x0, y0))

    def reset_game(self):
        self.message_queue.put(("reset",))
        self.state = self.opts.State(opts=self.opts)


@nointerrupt
def run(block=True, args=None, interrupted=False, kwargs={}):
    """Load the configuration and start the server.

    This can also be called programmatically to start a server.

    Arguments
    =========
    block : bool
       If True, then block until the server is finished.
    kwargs : dict
       Overrides loaded configuration options.  Note: no checks are
       performed, so make sure that these are valid options.
    args : str
       If specified, then use these arguments rather than those passed
       on the command line.  This is useful if starting the server
       from another application where the command line arguments might
       instead be for the outer app (like jupyter notebook).
    """
    parser = config.get_server_parser()
    opts, other_args = parser.parse_known_args(args=args)
    opts.__dict__.update(kwargs)

    # Get the physics model.
    module = ".".join(['physics'] + opts.model.split(".")[:-1])
    cls = opts.model.split('.')[-1]
    pkg = "super_hydro"
    opts.State = getattr(importlib.import_module("." + module, pkg), cls)
    Server(opts=opts).run(block=block, interrupted=interrupted)
