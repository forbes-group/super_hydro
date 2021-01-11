import numpy as np
import argparse
import collections.abc

class Automaton(object):
    '''Baseline testing model for minimal requirements of User-Defined
    Model (UDM).
    '''
    #It appears these all need to be minimally defined to function.
    params = dict(
            Nx=64, Ny=64,
            Nxy=(64,64),
            xy=(np.arange(64),np.arange(64)),
            min=0, max=10,
            data = np.zeros((64, 64)),
            pot_z = 0 + 0j,
            finger_x=0.5,
            finger_y=0.5,
            Lxy=np.asarray([64,64]))

    #Basic slider definition
    sliders = [['max', 'slider', None, 'range', 2, 10, 1]]

    def __init__(self, opts):
        '''Initializes model and parameters.'''
        params = {}

        mro = type(self).mro()
        for kls in reversed(mro):
            params.update(getattr(kls, 'params', {}))

        self.params = {_key: getattr(opts, _key, params[_key])
                        for _key in params}
        
        for _key in self.params:
            setattr(self, _key, self.params[_key])

    def get_density(self):
        '''Gets the density (display) array.'''
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
