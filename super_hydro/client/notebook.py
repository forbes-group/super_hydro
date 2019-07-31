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
import threading
import IPython

from matplotlib import cm

import numpy as np

import ipywidgets


from .. import config, communication, utils, widgets
from ..contexts import nointerrupt

_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task


class App(object):
    def __init__(self, opts, width="50%"):
        self.width = width
        self.opts = opts
        with log_task("Connecting to server"):
            self.comm = communication.Client(opts=self.opts)

    @property
    def density(self):
        """Return the density data to plot: initiates call to server."""
        with log_task("Get density from server."):
            density = self.comm.get_array(b"density")
        return density


class NotebookApp(App):
    fmt = 'PNG'
    _running = True
    browser_control = True

    def _get_widget(self):
        layout = self.get_layout()
        (self._interactive_widgets,
         special_widgets) = widgets.get_interactive_and_special_widgets(layout)

        self._density = special_widgets['density']
        self._txt = ipywidgets.Label()
        self._inp = ipywidgets.FloatLogSlider(value=0.01, base=10,
                                              min=-10, max=1,
                                              step=0.2,
                                              description="Cooling")
        self._inp.observe(self.on_value_change, names='value')
        self._msg = ipywidgets.Label()
        self._wid = ipywidgets.VBox([self._inp, self._txt,
                                     self._img, self._msg])
        return self._wid

    def on_value_change(self, change):
        self.comm.send(b"set", (change['owner'].name, change['new']))

    def on_click(self, button):
        if button.name == "quit":
            self._running = False
        self.comm.request(button.name.encode())

    def get_widget(self):
        layout = self.get_layout()
        (self._interactive_widgets, special_widgets) = (
            widgets.get_interactive_and_special_widgets(layout))

        extra_widgets = []

        # Add the density and control widgets if they have not been
        # provided yet.
        if 'density' not in special_widgets:
            extra_widgets.append(widgets.density)
        if 'controls' not in special_widgets:
            extra_widgets.append(widgets.controls)
        if extra_widgets:
            layout = widgets.VBox([layout] + extra_widgets)

        (self._interactive_widgets, special_widgets) = (
            widgets.get_interactive_and_special_widgets(layout))

        self._density = special_widgets['density']
        self._density.width = 500#self.width
        self._reset = special_widgets['reset']
        self._reset.on_click(self.on_click)
        self._reset_tracers = special_widgets['reset_tracers']
        self._reset_tracers.on_click(self.on_click)
        self._quit = special_widgets['quit']
        self._quit.on_click(self.on_click)
        self._fps = special_widgets['fps']
        self._msg = special_widgets['messages']

        # Link fps slider and density fps value.
        _l = ipywidgets.jslink((self._fps, 'value'),
                               (self._density, 'fps'))

        for w in self._interactive_widgets:
            w.observe(self.on_value_change, names='value')

        return layout

    def get_image(self, rgba):
        import PIL
        if self.fmt.lower() == 'jpeg':
            # Discard alpha channel
            rgba = rgba[..., :3]
        img = PIL.Image.fromarray(rgba)
        b = io.BytesIO()
        img.save(b, self.fmt)
        return b.getvalue()

    def get_layout(self):
        """Return the model specified layout."""
        layout = eval(self.comm.get(b"layout"), widgets.__dict__)
        return layout

    def get_tracer_particles(self):
        """Return the location of the tracer particles."""
        return self.comm.get_array(b"tracers")

    @nointerrupt
    def run(self, interrupted):
        from IPython.display import display
        self.Nx, self.Ny = self.comm.get(b"Nxy")
        self._frame = 0
        self._tic0 = time.time()

        display(self.get_widget())

        # Broken!  Fix aspect ratio better with reasonable sliders.
        Nx = max(500, self.Nx)
        Ny = int(self.Ny/self.Nx*Nx)
        self._density.width = Nx
        #self._density.height = Ny

        self._frame = 0
        if self.browser_control:
            self._density.on_update(callback=self.update)
            self.update()
        else:
            while not interrupted and self._running:
                tic0 = time.time()
                with self.sync():
                    self._frame += 1
                    density = self.density
                    rgba = self.get_rgba_from_density(density)
                    self._density.fg_tracer = self._update_fg_object_with_tracer_particles()
                    self._density.rgba = rgba
                toc = time.time()
                self._msg.value = "{:.2f}fps".format(self._frame/(toc-tic0))

    def update(self):
        """Callback to update frame when browser is ready."""
        if self._running:
            with self.sync():
                self._frame += 1
                density = self.density
                self._density.fg_object = self._update_fg_object_with_tracer_particles()
                self._density.rgba = self.get_rgba_from_density(density)

    def get_rgba_from_density(self, density):
        """Convert the density array into an rgba array for display."""
        density = density.T
        # array = cm.viridis((n_-n_.min())/(n_.max()-n_.min()))
        array = cm.viridis(density/density.max())
        array = self._update_frame_with_tracer_particles(array)
        array *= int(255/array.max())  # normalize values
        rgba = array.astype(dtype='uint8')
        return rgba

    def _update_frame_with_tracer_particles(self, array):
        #import pdb;pdb.set_trace()
        tracers = self.get_tracer_particles()
        ix, iy = [np.round(_i).astype(int) for _i in tracers]
        alpha = self.opts.tracer_alpha
        array[iy, ix, ...] = (
            (1-alpha)*array[iy, ix, ...]
            + alpha*np.array(self.opts.tracer_color))
        return array
        
    def _update_fg_object_with_tracer_particles(self):
        tracers = self.get_tracer_particles()
        ix, iy = tracers
        alpha = 1
        color = self.opts.tracer_color
        tracer_container = {"tracer": []}
        _num = 0
        for _i in ix:
            tracer_container["tracer"].append(["tracer", ix[_num], iy[_num], 0.5, color, alpha, 0, 0])
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
            ip = IPython.get_ipython()
            while True:
                ip.kernel.do_one_iteration()
                dt = time.perf_counter() - tic
                t_sleep = min(1./self.opts.fps - dt, ip.kernel._poll_interval)
                if t_sleep <= 0:
                    break
                time.sleep(t_sleep)


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


@nointerrupt
def run(run_server=True, interrupted=False, **kwargs):
    """Start the notebook client.

    Arguments
    ---------
    run_server : bool
       If True, then first run a server, otherwise expect to connect
       to an existing server.
    """
    if run_server:
        # Delay import because server requires many more modules than
        # the client.
        from ..server import server
        server.run(args='', block=False, interrupted=interrupted,
                   kwargs=kwargs)

    return get_app().run()
