"""
Testing
=======

Various models for testing.
"""
import math

import numpy as np

from scipy.special import hermite, factorial

import matplotlib.font_manager
import PIL.Image
import PIL.ImageFont
import PIL.ImageDraw


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


class HO:
    """Exact solution to the 2D Schrodinger equation with a HO potential.

    Attributes
    ----------
    hbar, m : float
        Physical coefficients.
    wx : float
        Trap frequency (angular) along x.
    Lx : float
        Size of box along x.
    Nxy : (int, int)
        Number of points.
    coeffs : [((nx, ny), a)]
        List of coefficients for the eigenstate with quantum numbers (nx, ny).  The
        time-dependent solution is a sum of these.
    """

    hbar = 1
    m = 1
    Nxy = (1280, 720)
    wx = 1.0
    Lx = 10.0

    # List of ((nx, na), coeff)
    coeffs = (
        ((1, 0), 1),
        ((0, 1), 1j),
        ((2, 0), 1),
        ((1, 1), -1j),
        ((0, 2), 2j),
    )

    def __init__(self, **kw):
        for _k in kw:
            if not hasattr(self, _k):
                raise ValueError(f"Unknown parameter {_k}")
            setattr(self, _k, kw[_k])
        self.init()

    def init(self):
        self.dx = self.Lx / self.Nxy[0]
        Ly = self.dx * self.Nxy[1]
        self.dxy = (self.dx, self.dx)
        self.Lxy = (self.Lx, Ly)
        self.ws = (self.wx, (self.Lx / Ly) ** 2)
        self.xy = np.meshgrid(
            *[(np.arange(_N) - _N / 2) * self.dx for _N in self.Nxy],
            sparse=True,
            indexing="ij",
        )
        self.kxy = np.meshgrid(
            *[2 * np.pi * np.fft.fftfreq(_N, self.dx) for _N in self.Nxy],
            sparse=True,
            indexing="ij",
        )

        # Oscillator lengths
        self.rxy = np.sqrt(np.divide(self.hbar / self.m, self.ws))

        self.V = self.m / 2 * sum((_w * _x) ** 2 for _w, _x in zip(self.ws, self.xy))

        _phases = []
        _psis = []
        for (nx, ny), a in self.coeffs:
            E, psi = self.get_eigenstate(nx, ny)
            _phases.append(E / self.hbar / 1j)
            _psis.append(a * psi)
        self._phases_psis = (np.array(_phases), np.array(_psis).T)

    def get_psi(self, t):
        """Return the wavefunction at time `t`."""
        phases, psisT = self._phases_psis
        return (psisT @ np.exp(phases * t)).T

    def get_eigenstate(self, nx, ny):
        """Return `(E, psi)` for the `nxy = (nx, ny)` eigenstate for the HO"""
        E = self.hbar * sum((_n + 0.5) * _w for _n, _w in zip((nx, ny), self.ws))
        norm = (
            1
            / np.sqrt(np.pi * math.prod(self.rxy))
            / math.prod([np.sqrt(2 ** _n * factorial(_n)) for _n in (nx, ny)])
        )
        psi = norm * math.prod(
            [
                hermite(_n)(_x / _r) * np.exp(-((_x / _r) ** 2) / 2)
                for _n, _x, _r in zip((nx, ny), self.xy, self.rxy)
            ]
        )
        return E, psi
