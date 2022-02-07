"""
Testing
=======

Various models for testing.
"""
import matplotlib.font_manager
import PIL.Image
import PIL.ImageFont
import PIL.ImageDraw

import numpy as np

from .. import widgets as w
from .. import interfaces
from ..interfaces import implementer

from .helpers import ModelBase, FingerMixin


@implementer(interfaces.IModel)
class HelloWorldMinimal:
    params = dict(
        Nx=256,
        Ny=128,
    )
    param_docs = {}
    layout = w.density

    @classmethod
    def get_params_and_docs(cls):
        return [
            (param, cls.params[param], cls.param_docs.get(param, ""))
            for param in cls.params
        ]

    @property
    def Nxy(self):
        return (self.params["Nx"], self.params["Ny"])

    def __init__(self, opts):
        super().__init__(opts)
        self.data = self.text_phantom()

    def get_density(self):
        return self.data

    def get_trace_particles(self):
        return []

    def get(self, param):
        return self.params[param]

    def set(self, param, value):
        """Set the specified parameter."""
        self.params[param] = value

    def step(self, N, tracer_particles):
        pass

    def text_phantom(self, text="Hello World!", font="Palatino"):
        """Return an array with the specified text rendered.

        https://stackoverflow.com/a/45948069/1088938
        """
        Nx, Ny = self.Nxy

        # Create font
        pil_font = PIL.ImageFont.truetype(
            matplotlib.font_manager.findfont(font, fontext="ttf"),
            size=Nx // len(text),
            encoding="unic",
        )

        text_width, text_height = pil_font.getsize(text)

        # create a blank canvas with extra space between lines
        canvas = PIL.Image.new("RGB", [Nx, Ny], (255, 255, 255))

        # draw the text onto the canvas
        offset = ((Nx - text_width) // 2, (Ny - text_height) // 2)
        white = "#000000"
        PIL.ImageDraw.Draw(canvas).text(offset, text, font=pil_font, fill=white)

        # Convert the canvas into an array with values in [0, 1]
        image = (255 - np.asarray(canvas)) / 255.0

        # Convert from an image to an array
        data = image.mean(axis=-1)[::-1].T
        return data


@implementer(interfaces.IModel)
class HelloWorld(HelloWorldMinimal, ModelBase, FingerMixin):
    def __init__(self, opts):
        super().__init__(opts)
