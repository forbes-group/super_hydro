__doc__ = """SuperHydro Server."""

from collections import deque
from contextlib import contextmanager
import datetime
import functools
import importlib
import inspect
import threading
import queue
import time

import numpy as np

from .. import config, communication, utils, widgets
from ..physics import tracer_particles

# from mmfutils.conexts import nointerrupt
from ..contexts import nointerrupt

from ..interfaces import IServer, implementer, verifyClass


PROFILE = False
if PROFILE:
    import cProfile

    def profile(filename="prof.dat"):
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


__all__ = ["run", "__doc__", "__all__", "ThreadMixin"]


_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task


class ThreadMixin:
    """Couple of useful methods for threads."""

    shutdown = False  # Flag to manually trigger shutdown
    shutdown_time = None  # Time to shut server down.
    name = None
    logger = _LOGGER
    _counters = None

    def heartbeat(self, msg="", timeout=1):
        """Log a heartbeat to show if the server is running."""
        if not self.name:
            raise AttributeError(
                f"{self.__class__.__name__}(ThreadMixin).init(name=) not called."
            )
        tic = getattr(self, "_heartbeat_tic", 0)
        toc = time.time()
        if toc - tic > timeout:
            counters = self._counters
            _msgc = " ".join([f"{c}={counters[c]}" for c in counters])
            for c in list(counters):
                if counters[c] == 0:
                    # If a counter was zero, remove it from future reporting.
                    del counters[c]
                else:
                    counters[c] = 0
            self.logger.debug(f"Alive ({self.name}): {msg} (# {_msgc})")
            self._heartbeat_tic = time.time()

    def _count(self, name):
        self._counters.setdefault(name, 0)
        self._counters[name] += 1

    @property
    def finished(self):
        """Return `True` if the thread should be stopped.

        True if the `shutdown_time` has been exceeded or the `shutdown` flag has been
        set.
        """
        finished = self.shutdown or (
            self.shutdown_time and time.time() > self.shutdown_time
        )
        if finished:
            if self.shutdown:
                self.logger.debug("Shutdown: Explicit shutdown")
            else:
                self.logger.debug("Shutdown: shutdown_time exceed")
        return finished

    def init(self, name, shutdown_min=60):
        """Initialize thread object.

        Arguments
        ---------
        name : str
           Name of object displayed in log messages.  Must be provided or else
           `heartbeat` will raise an `AttributeError`.
        shutdown_min : int, None
           Time after which to shutdown the server.  Default is 1 hour.
        """
        self._counters = {}
        self.shutdown = False
        self.shutdown_time = time.time() + shutdown_min * 60
        self.name = name
        self.logger.debug(
            f"Init: {self.name} will shutdown in "
            + f"{datetime.timedelta(minutes=shutdown_min)} (H:MM:SS)"
        )


class Computation(ThreadMixin):
    """Class which manages the actual computation and a queue for
    interacting with the clients.
    """

    pause_timeout = 0.1  # Time to wait when paused.

    def __init__(
        self, opts, message_queue, param_queue, density_queue, pot_queue, tracer_queue
    ):
        self.opts = opts
        self.do_reset()
        self.param_queue = param_queue
        self.message_queue = message_queue
        self.density_queue = density_queue
        self.tracer_queue = tracer_queue
        self.pot_queue = pot_queue
        self.fps = opts.fps
        self.steps = opts.steps
        self.paused = True
        self.logger = _LOGGER

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
            dt = time.perf_counter() - tic
            self._times.append(dt)
            if True or PROFILE:
                dt_ = np.mean(self._times) * 1000 + 1j * np.std(self._times) * 1000
                log(
                    f"{dt.real/self.steps:.2g}+-{dt.imag/self.steps:.2g}ms/step "
                    + f"(max {1/dt.real:.2f}fps)",
                    level=100,
                )
            t_sleep = max(0, 1.0 / self.fps - dt)
            time.sleep(t_sleep)

    @profile("prof.dat")
    def run(self):
        """Start the computation."""
        self.init(name="Computation", shutdown_min=self.opts.shutdown)
        while not self.finished:
            with self.sync():
                self.heartbeat()
                if self.paused:
                    time.sleep(self.pause_timeout)
                else:
                    self.model.step(self.steps, tracer_particles=self.tracer_particles)
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
    def do_set(self, param, value):
        """Generic set method."""
        self.model.set(param, value)

    def do_get(self, param):
        """Generic get method."""
        value = self.model.get(param)
        self.param_queue.put((param, value))

    def do_quit(self):
        log("Quitting!")
        self.shutdown = True

    def do_pause(self):
        print("pausing")
        self.paused = True

    def do_start(self):
        print("running")
        self.paused = False

    def do_get_density(self):
        self.density_queue.put(self.model.get_density())

    def do_get_tracers(self):
        tracers = np.empty(0)
        if self.opts.tracer_particles and "tracer_particles" in self.model.params:
            trpos = self.tracer_particles.get_tracer_particles()
            trinds = self.tracer_particles.get_inds(trpos, model=self.model)
            tracers = np.asarray(trinds)
        self.tracer_queue.put(tracers)

    def do_update_finger(self, x, y):
        self.model.set("xy0", (x, y))

    def do_update_cooling_phase(self, cooling_phase):
        self.model.set("cooling_phase", cooling_phase)

    def do_get_cooling_phase(self):
        return self.model.get("cooling_phase")

    def do_get_pot(self):
        self.pot_queue.put(self.model.get("pot_z"))

    def do_reset_tracers(self):
        opts = self.opts
        if self.opts.tracer_particles and "tracer_particles" in self.model.params:
            self.tracer_particles = tracer_particles.TracerParticles(
                model=self.model, N_particles=opts.tracer_particles
            )
        else:
            self.tracer_particles = None

    def do_reset(self):
        opts = self.opts
        self.model = opts.Model(opts=opts)
        self.do_reset_tracers()

    def unknown_command(self, msg, *v):
        raise ValueError(f"Unknown Command {msg}(*{v})")


# Global list of servers so we can kill them all
_SERVERS = []


@implementer(IServer)
class Server(ThreadMixin):
    """Server Class.

    This server runs in a separate thread and allows clients to
    interact via the IServer interface.  This can directly used by
    python clients, or encapsulated by the NetworkServer class which
    allows clients to connect through a socket.
    """

    _poll_interval = 0.1
    _tries = 10  # Number of times to try getting a param

    def __init__(self, opts, **kwargs):
        self.opts = opts
        self.message_queue = queue.Queue()
        self.param_queue = queue.Queue()
        self.density_queue = queue.Queue()
        self.tracer_queue = queue.Queue()
        self.pot_queue = queue.Queue()
        self.computation = Computation(
            opts=opts,
            param_queue=self.param_queue,
            message_queue=self.message_queue,
            density_queue=self.density_queue,
            pot_queue=self.pot_queue,
            tracer_queue=self.tracer_queue,
        )
        self._param_cache = {}
        self.computation_thread = threading.Thread(target=self.computation.run)
        self.model = opts.Model(opts=opts)
        self.logger = _LOGGER
        super().__init__(**kwargs)
        global _SERVERS
        _SERVERS.append(self)

    def run(self, interrupted, block=True):
        """Run the server, blocking if desired."""
        self.interrupted = interrupted
        kwargs = dict(interrupted=interrupted)
        if block:
            return self._run_server(**kwargs)
        else:
            self.server_thread = threading.Thread(
                target=self._run_server, kwargs=kwargs
            )
            self.server_thread.start()

    def _run_server(self, interrupted=None):
        self.init(name="Server", shutdown_min=self.opts.shutdown)
        self.computation_thread.start()
        self.message_queue.put(("start",))
        try:
            while not self.finished and not interrupted:
                self.heartbeat()
                time.sleep(min(self._poll_interval, 1 / self.opts.fps))
            print("Done")
        finally:
            self.message_queue.put(("quit",))
            # print(f"finished status is {self.finished} and Interrupted is {interrupted}")
            self.computation_thread.join()

    def _pos_to_xy(self, pos):
        """Return the (x, y) coordinates of (pos_x, pos_y) in the frame."""
        return (np.asarray(pos) - 0.5) * self.model.get("Lxy")

    def _xy_to_pos(self, xy):
        """Return the frame (pos_x, pos_y) from (x, y) coordinates."""
        return np.asarray(xy) / self.model.get("Lxy") + 0.5

    ######################################################################
    # Communication layer.
    def _do_reset(self, client=None):
        """Reset the server."""
        self.message_queue.put(("reset",))
        self.model = self.opts.Model(opts=self.opts)

    def _do_reset_tracers(self, client=None):
        """Reset the tracers."""
        self.message_queue.put(("reset_tracers",))

    def _do_start(self, client=None):
        self.message_queue.put(("start",))

    def _do_pause(self, client=None):
        self.message_queue.put(("pause",))

    def _do_quit(self, client=None):
        self.shutdown = True

    def _get_Vpos(self, client=None):
        """Return the position of the external potential."""
        self.message_queue.put(("get_pot",))
        pot_z = self.pot_queue.get()
        xy = self._xy_to_pos((pot_z.real, pot_z.imag))
        return tuple(xy.tolist())
        # return xy

    def _get_layout(self, client=None):
        """Return the widget layout."""
        layout = self.model.layout
        interactive_widgets = widgets.get_interactive_widgets(layout)
        for w in interactive_widgets:
            w.value = self.model.params[w.name]
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

    def _get(self, param, client=None):
        """Get the specified parameter, waiting for a response."""
        self._get_async(param=param, client=client)
        for n in range(self._tries):
            param_, value = msg = self.param_queue.get()
            if param == param_:
                return value
            else:
                log(f"Asked for {param} but got {param_}.  Trying again.")
                self.param_queue.put(msg)
                time.sleep(self._poll_interval)
        return value

    def _get_async(self, param, client=None):
        """Sent a get request to the computation server.

        When the server gets a chance, it will put the result on the `param_queue`.
        """
        if param not in self.model.params:
            log(f"Error: Attempt to get unknown param={param}")

        self.message_queue.put(("get", param))

    def _set(self, param, value):
        """Generic set."""
        if param not in self.model.params:
            log(f"Error: Attempt to set unknown param={param}")
            return

        self.model.set(param, value)
        self.message_queue.put(("set", param, value))

    def _get_available_commands(self, client=None):
        """Get a dictionary of available commands."""
        do_commands = {
            _name[len("_do_") :]: _val.__doc__
            for _name, _val in inspect.getmembers(self)
            if _name.startswith("_do_")
        }
        get_commands = {
            _name[len("_get_") :]: _val.__doc__
            for _name, _val in inspect.getmembers(self)
            if _name.startswith("_get_") and not _name.startswith("_get_array_")
        }
        set_commands = {
            _name[len("_set_") :]: _val.__doc__
            for _name, _val in inspect.getmembers(self)
            if _name.startswith("_set_")
        }
        get_array_commands = {
            _name[len("_get_array_") :]: _val.__doc__
            for _name, _val in inspect.getmembers(self)
            if _name.startswith("_get_array_")
        }

        # Add all other parameters
        descriptions = widgets.get_descriptions(self.model.layout)
        for _v in self.model.params:
            if _v not in get_commands and _v not in get_array_commands:
                get_commands[_v] = self.model.params_doc.get(
                    _v, descriptions.get(_v, f"Parameter {_v}")
                )
            if _v not in set_commands and _v not in get_array_commands:
                set_commands[_v] = self.model.params_doc.get(
                    _v, descriptions.get(_v, f"Parameter {_v}")
                )

        available_commands = {
            "do": do_commands,
            "get": get_commands,
            "set": set_commands,
            "get_array": get_array_commands,
        }
        return available_commands

    ######################################################################
    # Public interface.  These dispatch to the various methods above.
    def get_available_commands(self, client=None):
        self._count("get_available_commands")
        log(f"Getting available commands")
        return self._get_available_commands(client=client)

    def do(self, action, client=None):
        """Tell the server to perform the specified `action`."""
        self._count("do")
        method = getattr(self, f"_do_{action}", None)
        if not method:
            print("Unknown data type")
            print("client message:", action)
            self.comm.respond(b"Unknown Message")
        else:
            method(client=client)

    def get(self, params, client=None, use_cache=True):
        """Return the specified parameters.

        Parameters
        ----------
        params : [str]
           List of parameters.
        use_cache : bool
           If `True`, then use cached values (may be incorrect).

        Returns
        -------
        param_dict : {param: val}
           Dictionary of values corresponding to specified parameters.
        """
        # log(f"Getting {params}")
        param_dict = {}
        for param in params:
            method = getattr(self, f"_get_{param}", None)
            if not method and not use_cache:
                # Special methods always called synchronously
                method = functools.partial(self._get, param=param)

            if method:
                self._count(f"_get_{param}")
                param_dict[param] = self._param_cache[param] = method(client=client)
            else:
                self._count(f"_get_async")
                self._get_async(param=param, client=client)

        if set(param_dict) == set(params):
            return param_dict

        # Now get all values from the param_queue and store them in the cache
        try:
            while True:
                param, value = self.param_queue.get_nowait()
                self._param_cache[param] = value
        except queue.Empty:
            pass

        for param in params:
            if param in param_dict:
                continue

            if param not in self._param_cache:
                # Get it synchronously
                self._param_cache[param] = self._get(param=param, client=client)
            param_dict[param] = self._param_cache[param]

        return param_dict

    def set(self, param_dict, client=None):
        """Set the specified quantities.

        Parameters
        ----------
        param_vals : {param: val}
           Dictionary of values corresponding to specified parameters.
        """
        self._count("set")
        # log(f"Setting {param_dict}")
        for param in param_dict:
            value = param_dict[param]
            self.message_queue.put(("set", param, value))

    def get_array(self, param, client=None):
        """Get the specified array."""
        self._count("get_array")
        method = getattr(self, f"_get_array_{param}", None)
        if not method:
            print("Unknown data type")
            print("client message:", param)
            self.comm.respond(b"Unknown Message")
        else:
            return method(client=client)

    def reset(self, client=None):
        """Reset server and return default parameters.

        Returns
        -------
        param_vals : {param: val}
           Dictionary of values corresponding to default parameters.
        """
        self._count("reset")
        self._do_reset(client=client)
        return self.model.params

    def quit(self, client=None):
        """Quit server."""
        self._count("quit")
        self._do_quit(client=client)

    @staticmethod
    def quit_all():
        """Quit all running servers."""
        global _SERVERS
        while _SERVERS:
            _SERVERS.pop(0).quit()


@implementer(IServer)
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
        self.shutdown = False
        try:
            self.init(name="NetworkServer", shutdown_min=self.opts.shutdown)
            while not self.finished and not interrupted:
                self.heartbeat()
                try:
                    # Do this so we can receive interrupted messages
                    # if the user interrupts.
                    client_message = self.comm.recv(
                        timeout=min(self._poll_interval, 1 / self.opts.fps)
                    )
                except communication.TimeoutError:
                    continue

                if client_message == b"get":
                    params = self.comm.get_params()
                    self.comm.send(self.get(params=params))
                elif client_message == b"do":
                    self.do(action=self.comm.get())
                elif client_message == b"set":
                    self.set(param_dict=self.comm.get())
                elif client_message == b"density":
                    self.comm.send_array(self._get_array_density())
                elif client_message == b"tracers":
                    self.comm.send_array(self._get_array_tracers())
                else:
                    print("Unknown data type")
                    print("client message:", client_message)
                    self.comm.respond(b"Unknown Message")
            print("Done")
        finally:
            self.message_queue.put(("quit",))
            self.computation_thread.join()


@nointerrupt
def run(block=True, network_server=True, interrupted=False, args=None, kwargs={}):
    """Load the configuration and start the server.

    This can also be called programmatically to start a server.

    Parameters
    ----------
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
    module = ".".join(["physics"] + opts.model.split(".")[:-1])
    cls = opts.model.split(".")[-1]
    pkg = "super_hydro"
    opts.Model = getattr(importlib.import_module("." + module, pkg), cls)
    if network_server:
        server = NetworkServer(opts=opts)
    else:
        server = Server(opts=opts)
    server.run(block=block, interrupted=interrupted)
    return server


verifyClass(IServer, Server)
verifyClass(IServer, NetworkServer)
