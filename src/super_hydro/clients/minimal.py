"""Minimal clients for benchmarking.

These are minimal clients for testing and benchmarking.  They are minimal, intended to
be run in a terminal, and do not actually display anything, but can be used to interact
with a server.
"""
from .. import config, communication, utils

_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task


class _Interrupted(object):
    """Flag to indicate the the App has been interrupted.

    Pass as the interrupted flag to the server to allow the client App
    to terminate it.
    """

    def __init__(self, app):
        self.app = app

    def __bool__(self):
        # Don't check interrupted flag - that might stop the server
        # too early.
        return not self.app._running


class App(object):
    """Dumb application that allows the user to interact with a
    computational server.
    """

    server = None

    def __init__(self, opts):
        self.opts = opts
        self._running = True

    @property
    def comm(self):
        """Return the communication object, but only if running."""
        if self._running:
            return self.server.comm

    @property
    def density(self):
        """Return the density data to plot: initiates call to server."""
        with log_task("Get density from server."):
            return self.server.get_array("density")

    @property
    def interrupted(self):
        """Return a flag that can be used to signal the server that
        the App has been interrupted.
        """
        return _Interrupted(app=self)

    def run(self):
        if self.server is None:
            self.server = communication.NetworkServer(opts=self.opts)

    ######################################################################
    # Server Communication
    #
    # These methods communicate with the server.
    def quit(self):
        self.server.do("quit")
        self._running = False


_OPTS = None


def get_app(run_server=False, network_server=True, opts=None, **kwargs):
    global _OPTS
    if _OPTS is None:
        with log_task("Reading configuration"):
            parser = config.get_client_parser()
            _OPTS, _other_opts = parser.parse_known_args(args="")

    if opts:
        vars(_OPTS).update(opts)
    app = App(opts=_OPTS)

    if run_server:
        # Delay import because server requires many more modules than
        # the client.
        from ..server import server

        app.server = server.run(
            args="",
            interrupted=app.interrupted,
            block=False,
            network_server=network_server,
            kwargs=kwargs,
        )
    return app


def run(run_server=False, network_server=False, **kwargs):
    """Start the dumb client.

    Parameters
    ----------
    run_server : bool
       If True, then first run a server, otherwise expect to connect
       to an existing server.
    network_server : bool
       Specifies the type of server to run if run_server is True.
       If True, then run the server as a separate process and
       communicate through sockets, otherwise, directly connect to a
       server.
    """
    app = get_app(run_server=run_server, network_server=network_server, **kwargs)
    app.run()
    return app
