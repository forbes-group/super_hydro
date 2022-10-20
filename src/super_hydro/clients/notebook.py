"""Jupyter Notebook interface.

For performance here, we use IPyWidgets and our custom Canvas widget.
This allows reasonable frame-rates, an order of magnitude faster than
using matplotlib.imshow for example.

By stacking various elements, we can allow the user to update
components of the simulation.

Control is driven by alternating between python and javascript.  We
register the update function which the Canvas will then call after the
browser is finished displaying the last frame.
"""
from contextlib import contextmanager
import io
import time
import math

import IPython

from matplotlib import cm

import numpy as np

import ipywidgets

# from mmfutils.contexts import nointerrupt, NoInterrupt
from ..contexts import nointerrupt, NoInterrupt, FPS

from .. import config, communication, utils, widgets

from .mixins import ClientDensityMixin


_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task


class App(object):
    server = None

    def __init__(self, opts, width="50%"):
        self.width = width
        self.opts = opts
        self._running = True

    @property
    def comm(self):
        """Return the communication object, but only if running."""
        if self._running:
            return self.server.comm

    def get_density(self):
        """Return the density data to plot: initiates call to server."""
        with log_task("Get density from server."):
            return self.server.get_array("density")

    @property
    def interrupted(self):
        """Return a flag that can be used to signal the server that
        the App has been interrupted.
        """
        return _Interrupted(app=self)


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


class NotebookApp(ClientDensityMixin, App):
    """Application for the notebook client.

    Attributes
    ----------
    browser_control : bool
        If `True`, then register a callback with the browse (through Javascript) to
        initiate the frame updates.  This repeatedly switches control from python to the
        browser, and allows the ipwidgets to update, but is more complicated.  Sometimes
        when canceling, this can hang the client.

        If `False`, then control is maintained by a loop in python which is simple, but
        locks up the interface and is only good for running non-interactive demos.
    """

    fmt = "PNG"
    browser_control = True
    server = None
    frames = 10000
    timeout = 30 * 60

    def _get_widget(self):
        layout = self.get_layout()
        (
            self._interactive_widgets,
            special_widgets,
        ) = widgets.get_interactive_and_special_widgets(layout)

        self._density = special_widgets["density"]
        self._txt = ipywidgets.Label()
        self._inp = ipywidgets.FloatLogSlider(
            value=0.01, base=10, min=-10, max=1, step=0.2, description="Cooling"
        )
        self._inp.observe(self.on_value_change, names="value")
        self._msg = ipywidgets.Label()
        self._wid = ipywidgets.VBox([self._inp, self._txt, self._img, self._msg])
        return self._wid

    ######################################################################
    # Event Handlers and Callbacks.
    #
    # These allow the Javascript to drive the application, but should
    # only function if running.
    def on_value_change(self, change):
        if not self._running:
            return
        self.server.set({change["owner"].name: change["new"]})

    def on_click(self, button):
        if not self._running:
            return
        if button.name == "quit":
            self.quit()
        else:
            self.server.do(button.name)

    def update_frame(self):
        """Callback to update frame when browser is ready."""
        if not self._running:
            return
        with self.sync():
            self._frame += 1
            density = self.get_density()
            self._density.rgba = self.get_rgba_from_density(density)
            # self._density.fg_objects = self._update_fg_objects()

    ######################################################################
    # Server Communication
    #
    # These methods communicate with the server.
    def quit(self):
        self.server.do("quit")
        self._running = False

    def get_widget(self):
        layout = self.get_layout()
        (
            self._interactive_widgets,
            special_widgets,
        ) = widgets.get_interactive_and_special_widgets(layout)

        extra_widgets = []

        # Add the density and control widgets if they have not been
        # provided yet.
        if "density" not in special_widgets:
            extra_widgets.append(widgets.density)
        if "controls" not in special_widgets:
            extra_widgets.append(widgets.controls)
        if extra_widgets:
            layout = widgets.VBox([layout] + extra_widgets)

        (
            self._interactive_widgets,
            special_widgets,
        ) = widgets.get_interactive_and_special_widgets(layout)

        self._density = special_widgets["density"]
        self._density.width = 500  # self.width
        self._reset = special_widgets["reset"]
        self._reset.on_click(self.on_click)
        self._reset_tracers = special_widgets["reset_tracers"]
        self._reset_tracers.on_click(self.on_click)
        self._quit = special_widgets["quit"]
        self._quit.on_click(self.on_click)
        self._fps = special_widgets["fps"]
        self._msg = special_widgets["messages"]

        # Link fps slider and density fps value.
        _l = ipywidgets.jslink((self._fps, "value"), (self._density, "fps"))

        for w in self._interactive_widgets:
            w.observe(self.on_value_change, names="value")

        return layout

    def get_image(self, rgba):
        if not self._running:
            return
        import PIL

        if self.fmt.lower() == "jpeg":
            # Discard alpha channel
            rgba = rgba[..., :3]
        img = PIL.Image.fromarray(rgba)
        b = io.BytesIO()
        img.save(b, self.fmt)
        return b.getvalue()

    def get_layout(self):
        """Return the model specified layout."""
        layout = eval(self.server.get(["layout"])["layout"], widgets.__dict__)
        return layout

    def get_tracer_particles(self):
        """Return the location of the tracer particles."""
        return self.server.get_array("tracers")

    ######################################################################
    # Client Application
    def run(self):
        if self.server is None:
            self.server = communication.LocalNetworkServer(opts=self.opts)
        from IPython.display import display

        _res = self.server.get(["Nx", "Ny"])
        self.Nx, self.Ny = _res["Nx"], _res["Ny"]
        self._frame = 0
        self._tic0 = time.time()

        display(self.get_widget())

        # Broken!  Fix aspect ratio better with reasonable sliders.
        Nx = max(500, self.Nx)
        Ny = int(self.Ny / self.Nx * Nx)
        self._density.width = Nx
        # self._density.height = Ny

        self._frame = 0
        kernel = IPython.get_ipython().kernel
        if self.browser_control:
            self._density.on_update(callback=self.update_frame)
            self.update_frame()
            with NoInterrupt(timeout=self.timeout) as interrupted:
                while not interrupted and self._running:
                    # This should not strictly be needed since the
                    # javascript will drive the handlers, but due to
                    # issues with interrupts etc. we can't seem to rely on
                    # being able to catch an interrupt if we return.  So
                    # we do a dummy event loop here.
                    kernel.do_one_iteration()
                    time.sleep(kernel._poll_interval)
        else:
            with FPS(frames=self.frames, timeout=self.timeout) as fps:
                for frame in fps:
                    if not self._running:
                        break
                    self.update_frame()
                    self._msg.value = f"{fps}fps"
                    for n in range(
                        int(math.ceil(1 / max(1, fps.fps) / kernel._poll_interval))
                    ):
                        kernel.do_one_iteration()
        if self._running:
            self.quit()

    def _update_frame_with_tracer_particles(self, array):
        tracers = self.get_tracer_particles()
        ix, iy = [np.round(_i).astype(int) for _i in tracers]
        alpha = self.opts.tracer_alpha
        array[iy, ix, ...] = (1 - alpha) * array[iy, ix, ...] + alpha * np.array(
            self.opts.tracer_color
        )
        return array

    def _update_fg_objects(self):
        tracer_container = {"tracer": []}
        tracers = self.get_tracer_particles()
        if tracers is not None and len(tracers) > 0:
            ix, iy = tracers
            alpha = 1
            color = self.opts.tracer_color
            _num = 0
            for _i in ix:
                tracer_container["tracer"].append(
                    ["tracer", ix[_num], iy[_num], 0.5, color, alpha, 0, 0]
                )
                _num += 1
        return tracer_container

    @contextmanager
    def sync(self):
        """Provides a context that will wait long enough to not
        exceed `self.opts.fps` frames per second.  Also executes the
        ipython event loop to ensure widgets are updated.
        """
        tic = time.perf_counter()
        try:
            yield
        finally:
            dt = time.perf_counter() - tic
            t_sleep = 1.0 / self.opts.fps - dt
            if t_sleep > 0:
                time.sleep(t_sleep)
        return


_OPTS = None


def get_app(run_server=True, network_server=False, notebook=True, **kwargs):
    NoInterrupt.unregister()
    global _OPTS
    if _OPTS is None:
        with log_task("Reading configuration"):
            parser = config.get_client_parser()
            _OPTS, _other_opts = parser.parse_known_args(args="")
    if notebook:
        app = NotebookApp(opts=_OPTS)
    else:
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


def run(run_server=True, network_server=True, browser_control=True, **kwargs):
    """Start the notebook client.

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
    app.browser_control = browser_control
    return app.run()
