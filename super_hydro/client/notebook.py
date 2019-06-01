"""Notebook interface using Matplotlib."""
import time

from matplotlib import pyplot as plt

from .. import config, communication, utils

#from mmf_utils.contexts import NoInterrupt

_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task


class App(object):
    def __init__(self, opts):
        self.opts = opts
        with log_task("Connecting to server"):
            self.comm = communication.Client(opts=self.opts)

    @property
    def data(self):
        """Return data to plot: initiates call to server."""
        with log_task("Get density from server."):
            data = self.comm.get_array(b"Frame")
        return data

    def run(self):
        self.Nx, self.Ny = self.comm.get(b"Nxy")
        T = 1./self.opts.fps

        tic = time.time()
        interrupted = False
        fig = plt.figure()
        img = None
        while not interrupted:
            toc = time.time()
            data = self.data
            dt = max(T-toc-tic, 0)
            time.sleep(dt)
            if img is None:
                img = plt.imshow(data)
            else:
                img.set_data(data)
            self.display(fig)
            tic = toc

    def display(fig):
        pass


class NotebookApp(App):
    def display(self, fig):
        from IPython.display import display, clear_output
        display(fig)
        clear_output(wait=True)


_OPTS = None


def get_app(notebook=True):
    global _OPTS
    if _OPTS is None:
        with log_task("Reading configuration"):
            parser = config.get_client_parser()
            _OPTS, _other_opts = parser.parse_known_args(args="")
    if notebook:
        return NotebookApp(opts=_OPTS)
    else:
        return App(opts=_OPTS)


def run():
    get_app().run()
