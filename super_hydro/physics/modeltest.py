import numpy as np

from .helpers import ModelBase


class Automaton(ModelBase):

    params = dict(
            Nx=64, Ny=64,
            min=0, max=10,
            data = np.zeros(4096),
            pot_z = 0 + 0j,
            finger_x=0.5,
            finger_y=0.5,
            Lxy=(0.5, 0.5))

    layout = None

    sliders = [['max', 'slider', None, 'range', 1, 10, 1]]

    def init(self):
        Nx, Ny = self.Nxy = self.Nx, self.Ny
        super().init()

    def get_density(self):
        return self.data

    def get(self, param):
        """Gets the value of requested parameter"""
        return getattr(self, param)

    def set(self, param, value):
        """Set maximum value for randomizer."""
        setattr(self, param, value)

    def step(self, N=None, tracer_particles=None):
        """Creates a new randomized array."""
        self.data = np.random.randint(self.min, high=self.max, size=(self.Nx, self.Ny))
