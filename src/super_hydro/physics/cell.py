"""Cellular Automata."""

import numpy as np

from .helpers import ModelBase


class Automaton(ModelBase):
    """Example of a cellular automaton."""

    params = dict(
            Nx=32, Ny=32, Nxy=(32, 32),
            tracer_particles=0,
            xy = (0, 0),
            data = np.zeros(4096))

    layout = None

    def init(self):
        Nx, Ny = self.Nxy = self.Nx, self.Ny

        super().init()


    def get_density(self):
        return self.data

    def get_trace_particles(self):
        """Unused."""
        pass

    def get(self, param):
        """Unused."""
        pass

    def set(self, param, value):
        """Set cell to 'Alive', then update next generation."""
        x, y = param
        self.data[x][y] = value
        self.step()

    def step(self, N=None, tracer_particles=None):
        """Updates each 'generation'."""
        gen = np.zeros(len(self.data))
        arr = (self.data == 1)
        a, b, c, d = 1, 63, 64, 65

        for i in range(len(arr)):
            chk = 0
            if arr[i-a] == True:
                chk += 1
            if arr[i-b] == True:
                chk += 1
            if arr[i-c] == True:
                chk += 1
            if arr[i-d] == True:
                chk += 1

            if (i+a) >= len(arr):
                if arr[i+a-len(arr)] == True:
                    chk+=1
            elif arr[i+a] == True:
                chk += 1

            if (i+b) >= len(arr):
                if arr[i+b-len(arr)] == True:
                    chk += 1
            elif arr[i+b] == True:
                chk += 1

            if (i+c) >= len(arr):
                if arr[i+c-len(arr)] == True:
                    chk += 1
            elif arr[i+c] == True:
                chk += 1

            if (i+d) >= len(arr):
                if arr[i+d-len(arr)] == True:
                    chk += 1
            elif arr[i+d] == True:
                chk += 1

            if (chk == 2) & (arr[i] == True):
                gen[i] = 1
            elif (chk == 3 & arr[i] == False):
                gen[i] = 1
            else :
                gen[i] = 0

        self.data = gen
