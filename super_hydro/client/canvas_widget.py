"""Initial version of a Canvas-based widget.

This version displays the required javascript in the notebook so does
not require any installation.
"""
import os.path

import numpy as np

import traitlets
from traitlets import Unicode, Bool, validate, TraitError, Instance, Int, Bytes, Dict, List

from ipywidgets import DOMWidget, register
from ipywidgets.widgets.trait_types import bytes_serialization
from ipywidgets.widgets.widget import CallbackDispatcher

import json

_JS_FILE = __file__[:-3] + '.js'


@register
class Canvas(DOMWidget):
    """HTML5 Canvas Object.

    Examples
    --------
    >>> from matplotlib import cm
    >>> canvas = Canvas()
    >>> display(canvas)
    >>> A = np.random.random((64, 32))
    >>> canvas.rgba = cm.viridis(A.T, bytes=True)
    """
    _view_name = Unicode('CanvasView').tag(sync=True)
    _view_module = Unicode('canvas_widget').tag(sync=True)
    _view_module_version = Unicode('0.1.0').tag(sync=True)

    _rgba = Bytes(help="RGBA image data").tag(sync=True, **bytes_serialization)
    _image_width = Int(help="Image width").tag(sync=True)
    _fg_object = Unicode(help="Foreground object information").tag(sync=True)

    # Attributes
    name = traitlets.ObjectName("_").tag(sync=True)
    fps = Int(20, help="Maximum fps for update requests.").tag(sync=True)
    width = Int(0, help="Width of canvas").tag(sync=True)
    height = Int(0, help="Height of canvas").tag(sync=True)
    tracer_size = Unicode(
        help="Tracer particle size relative to image in pixels").tag(sync=True)

    mouse_event_data = Dict(help="Data from mouse event").tag(sync=True)
    key_event_data = Dict(help="Data from key event").tag(sync=True)

    indexing = Unicode(
        'xy', help="Indexing: 'xy' (faster) or 'ij'.  See np.meshgrid")

    def __init__(self, *v, **kw):
        super().__init__(*v, **kw)

        self._update_handlers = CallbackDispatcher()
        self.on_msg(self._handle_update_request)

        # Until we properly install this, display the javascript to
        # load the widget in the notebook.
        display_js()

    @property
    def rgba(self):
        """RGBA bytes array from a colormap.

        Note: This should should be in ij imaging with axis 0
        corresponding to x (wide) and axis 1 corresponding to y
        (height).

        For example:

            canvas.rgba = cm.viridis(data, bytes=True)
        """
        return self._rgba_data

    @rgba.setter
    def rgba(self, rgba_data):
        self._rgba_data = rgba_data
        if self.indexing == 'ij':
            self._image_width = rgba_data.shape[0]
            # Swap axes to go from ij indexing to HTML convention.
            self._rgba = np.swapaxes(rgba_data, 0, 1).tobytes()
        else:
            self._image_width = rgba_data.shape[1]
            self._rgba = rgba_data.tobytes()

    @property
    def fg_object(self):
        return self._fg_object_data

    @fg_object.setter
    def fg_object(self, value):
        self._fg_object_data = value
        self._fg_object = json.dumps(self._fg_object_data)

    def on_update(self, callback, remove=False):
        """Register a callback to execute when the browser is ready
        for an update.

        Parameters
        ----------
        remove: bool (optional)
            Set to true to remove the callback from the list of callbacks.
        """
        self._update_handlers.register_callback(callback, remove=remove)

    def update(self):
        self._update_handlers()

    def _handle_update_request(self, canvas, content, buffers):
        if content.get('request', '') == 'update':
            self.update()


def display_js():
    from IPython.display import Javascript, display
    with open(_JS_FILE) as f:
        display(Javascript(f.read()))
