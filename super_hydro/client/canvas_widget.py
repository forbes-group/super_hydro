"""Initial version of a Canvas-based widget.

This version displays the required javascript in the notebook so does
not require any installation.
"""
import os.path

import numpy as np

from traitlets import Unicode, Bool, validate, TraitError, Instance, Int, Bytes
from ipywidgets import DOMWidget, register
from ipywidgets.widgets.trait_types import bytes_serialization


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

    # Attributes
    width = Int(0, help="Width of canvas").tag(sync=True)
    height = Int(0, help="Height of canvas").tag(sync=True)
    clicks = Int(0, help="Number of clicks").tag(sync=True)

    indexing = Unicode(
        'xy', help="Indexing: 'xy' (faster) or 'ij'.  See np.meshgrid")

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


def display_js():
    from IPython.display import Javascript, display
    with open(_JS_FILE) as f:
        display(Javascript(f.read()))
