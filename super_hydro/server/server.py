__doc__ = """SuperHydro Server."""

from collections import deque
from contextlib import contextmanager
import importlib
import inspect
import threading
import queue
import time

import numpy as np

from .. import config, communication, utils, widgets
from ..physics import tracer_particles
#from mmfutils.conexts import nointerrupt
from ..contexts import nointerrupt

from ..interfaces import IServer, implementer, verifyClass


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


class ThreadMixin(object):
    """Couple of useful methods for threads."""
    def heartbeat(self, msg="", timeout=1):
        """Log a heartbeat to show if the server is running."""
        tic = getattr(self, '_heartbeat_tic', 0)
        toc = time.time()
        if toc - tic > timeout:
            _LOGGER.debug(f"Alive: {msg}")
            self._heartbeat_tic = time.time()


class Computation(ThreadMixin):
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
            t_sleep = max(0, 1./self.fps - dt)
            time.sleep(t_sleep)

    @profile('prof.dat')
    def run(self):
        """Start the computation."""
        while self.running:
            with self.sync():
                self.heartbeat("Computation")
                if self.paused:
                    time.sleep(self.pause_timeout)
                else:
                    self.state.step(self.steps,
                                    tracer_particles=self.tracer_particles)
                self.process_queue()
        log("Computation Finished.", level=100)

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

    def do_get_tracers(self):
        tracers = np.empty(0)
        if self.opts.tracer_particles:
            trpos = self.tracer_particles.get_tracer_particles()
            trinds = self.tracer_particles.get_inds(trpos,
                                                    state=self.state)
            tracers = np.asarray(trinds)
        self.tracer_queue.put(tracers)

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


@implementer(IServer)
class Server(ThreadMixin):
    """Server Class.

    This server runs in a separate thread and allows clients to
    interact via the IServer interface.  This can directly used by
    python clients, or encapsulated by the NetworkServer class which
    allows clients to connect through a socket.
    """
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
        self.state = opts.State(opts=opts)
        super().__init__(**kwargs)

    def run(self, interrupted, block=True):
        """Run the server, blocking if desired."""
        self.interrupted = interrupted
        kwargs = dict(interrupted=interrupted)
        if block:
            return self.run_server(**kwargs)
        else:
            self.server_thread = threading.Thread(
                target=self._run_server, kwargs=kwargs)
            self.server_thread.start()

    def _run_server(self, interrupted=None):
        finished = False
        self.computation_thread.start()
        self.message_queue.put(("start",))
        self.finished = False
        try:
            while not self.finished and not interrupted:
                self.heartbeat("Server")
                time.sleep(min(self._poll_interval, 1/self.opts.fps))
            print("Done")
        finally:
            self.message_queue.put(("quit",))
            self.computation_thread.join()

    def _pos_to_xy(self, pos):
        """Return the (x, y) coordinates of (pos_x, pos_y) in the frame."""
        return (np.asarray(pos) - 0.5)*self.state.get('Lxy')

    def _xy_to_pos(self, xy):
        """Return the frame (pos_x, pos_y) from (x, y) coordinates."""
        return np.asarray(xy)/self.state.get('Lxy') + 0.5

    ######################################################################
    # Communication layer.
    def _do_reset(self, client=None):
        """Reset the server."""
        self.message_queue.put(("reset",))
        self.state = self.opts.State(opts=self.opts)

    def _do_reset_tracers(self, client=None):
        """Reset the tracers."""
        self.message_queue.put(("reset_tracers",))

    def _do_start(self, client=None):
        self.message_queue.put(("start",))

    def _do_pause(self, client=None):
        self.message_queue.put(("pause",))

    def _do_quit(self, client=None):
        self.finished = True

    def _get_Vpos(self, client=None):
        """Return the position of the external potential."""
        self.message_queue.put(("get_pot",))
        pot_z = self.pot_queue.get()
        xy = self.xy_to_pos((pot_z.real, pot_z.imag))
        return tuple(xy.tolist())

    def _get_layout(self, client=None):
        """Return the widget layout."""
        layout = self.state.layout
        interactive_widgets = widgets.get_interactive_widgets(layout)
        for w in interactive_widgets:
            w.value = self.state.params[w.name]
        return repr(layout)

    def _get_Nxy(self, client=None):
        """Return the size of the frame."""
        return (self.opts.Nx, self.opts.Ny)

    def _get_array_tracers(self, client=None):
        """Return the positions of the tracers."""
        self.message_queue.put(("get_tracers",))
        trdata = self.tracer_queue.get()
        return trdata

    def _get_array_density(self, client=None):
        """Return the density data."""
        self.message_queue.put(("get_density",))
        density = np.ascontiguousarray(self.density_queue.get())
        return density

    def _set_touch_pos(self, touch_pos, client=None):
        """Set the coordinates of the user's touch."""
        x0, y0 = self.pos_to_xy(touch_pos)
        self.message_queue.put(("update_finger", x0, y0))

    def _set_cooling(self, cooling, client=None):
        """Set the cooling power."""
        cooling_phase = complex(1, 10**float(cooling))
        self.message_queue.put(("update_cooling_phase", cooling_phase))

    def _get_available_commands(self, client=None):
        """Get a dictionary of available commands."""
        do_commands = {
            _name[len('_do_'):]: _val.__doc__
            for _name, _val in inspect.getmembers(self)
            if _name.startswith('_do_')}
        get_commands = {
            _name[len('_get_'):]: _val.__doc__
            for _name, _val in inspect.getmembers(self)
            if _name.startswith('_get_')
            and not _name.startswith('_get_array_')}
        set_commands = {
            _name[len('_set_'):]: _val.__doc__
            for _name, _val in inspect.getmembers(self)
            if _name.startswith('_set_')}
        get_array_commands = {
            _name[len('_get_array_'):]: _val.__doc__
            for _name, _val in inspect.getmembers(self)
            if _name.startswith('_get_array_')}
        available_commands = {
            'do': do_commands,
            'get': get_commands,
            'set': set_commands,
            'get_array': get_array_commands,
        }
        return available_commands

    ######################################################################
    # Public interface.  These dispatch to the various methods above.
    def get_available_commands(self, client=None):
        log(f"Getting available commands")
        return self._get_available_commands(client=client)

    def reset(self, client=None):
        """Reset server and return default parameters.

        Returns
        -------
        param_vals : {param: val}
           Dictionary of values corresponding to default parameters.
        """
        self._do_reset(client=client)
        return self.state.params

    def set(self, param_dict, client=None):
        """Set the specified quantities.

        Arguments
        ---------
        param_vals : {param: val}
           Dictionary of values corresponding to specified parameters.
        """
        log(f"Setting {param_dict}")
        for param in param_dict:
            value = param_dict[param]
            self.message_queue.put(("update", param, value))

    def do(self, action, client=None):
        """Tell the server to perform the specified `action`."""
        method = getattr(self, f"_do_{action}", None)
        if not method:
            print("Unknown data type")
            print("client message:", action)
            self.comm.respond(b"Unknown Message")
        else:
            method(client=client)

    def get(self, params, client=None):
        """Return the specified parameters.

        Arguments
        ---------
        params : [str]
           List of parameters.

        Returns
        -------
        param_dict : {param: val}
           Dictionary of values corresponding to specified parameters.
        """
        log(f"Getting {params}")
        param_dict = {}
        for param in params:
            method = getattr(self, f"_get_{param}", None)
            if not method:
                err_message = f"Unknown parameter {param}"
                log(err_message)
                val = communication.error(err_message)
            else:
                val = method(client=client)
            param_dict[param] = val
        return param_dict

    def get_array(self, param, client=None):
        """Get the specified array."""
        method = getattr(self, f"_get_array_{param}", None)
        if not method:
            print("Unknown data type")
            print("client message:", param)
            self.comm.respond(b"Unknown Message")
        else:
            return method(client=client)


class NetworkServer(Server):
    """Network Server.

    Wraps the Server class, provding all interface through sockets so
    that non-python clients can interact with the server.
    """
    def __init__(self, opts, **kwargs):
        self.comm = communication.Server(opts=opts)
        super().__init__(opts=opts, **kwargs)

    def run_server(self, interrupted=None):
        self.computation_thread.start()
        self.message_queue.put(("start",))
        self.finished = False
        try:
            while not self.finished and not interrupted:
                self.heartbeat("Server")
                try:
                    # Do this so we can receive interrupted messages
                    # if the user interrupts.
                    client_message = self.comm.recv(
                        timeout=min(self._poll_interval, 1/self.opts.fps))
                except communication.TimeoutError:
                    continue

                if client_message == b"_get":
                    params = self.comm.get_params()
                    self.comm.send(self.get(params))
                elif client_message == b"tracers":
                    self.comm.send_array(self._get_array_tracers())
                elif client_message == b"density":
                    self.comm.send_array(self._get_array_density())
                elif client_message == b"set":
                    param, value = self.comm.get()
                    self.set(param=param, value=value)
                #elif client_message == b"Vpos":
                #    self.comm.send(self._get_Vpos())
                #elif client_message == b"layout":
                #    self.comm.send(self._get_layout())
                elif client_message == b"OnTouch":
                    self.set_touch_pos(self.comm.get())
                #elif client_message == b"Cooling":
                #    self._set_cooling(self.comm.get())
                elif client_message == b"reset":
                    param_vals = self._do_reset()
                    self.comm.send(param_vals)
                elif client_message == b"reset_tracers":
                    self._do_reset_tracers()
                    self.comm.respond(b"Tracers Reset")
                #elif client_message == b"Nxy":
                #    self.comm.send(self._get_Nxy())
                elif client_message == b"Start":
                    self._do_start()
                    self.comm.respond(b"Starting")
                elif client_message == b"Pause":
                    self._do_pause()
                    self.comm.respond(b"Paused")
                elif client_message == b"quit":
                    self._do_quit()
                else:
                    print("Unknown data type")
                    print("client message:", client_message)
                    self.comm.respond(b"Unknown Message")
            print("Done")
        finally:
            self.message_queue.put(("quit",))
            self.computation_thread.join()


@nointerrupt
def run(block=True, network_server=True, interrupted=False,
        args=None, kwargs={}):
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
    network_server : bool
       If True, then run a NetworkServer instance that listens for
       connections from the network, otherwise, directly run a Server.
    """
    parser = config.get_server_parser()
    opts, other_args = parser.parse_known_args(args=args)
    opts.__dict__.update(kwargs)

    # Get the physics model.
    module = ".".join(['physics'] + opts.model.split(".")[:-1])
    cls = opts.model.split('.')[-1]
    pkg = "super_hydro"
    opts.State = getattr(importlib.import_module("." + module, pkg), cls)
    if network_server:
        server = NetworkServer(opts=opts)
    else:
        server = Server(opts=opts)
    server.run(block=block, interrupted=interrupted)
    return server


verifyClass(IServer, Server)
verifyClass(IServer, NetworkServer)
