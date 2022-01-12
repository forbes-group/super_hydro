"""Tracer particle support.

This module provides support for generating, tracking, and viewing
tracer particles to track the flow during a simulation.
"""
import numpy as np


class TracerParticles(object):
    def __init__(self, model, N_particles=1000):
        self.N_particles = N_particles
        self.model = model
        self._par_pos = self.tracer_particles_create(self.model)

    def tracer_particles_create(self, model):
        N_particles = self.N_particles
        np.random.seed(1)
        Nx, Ny = model.Nx, model.Ny
        x, y = model.xy
        x, y = np.ravel(x), np.ravel(y)
        n = model.get_density()
        n_max = n.max()

        particles = []
        while len(particles) < N_particles:
            ix = np.random.randint(Nx)
            iy = np.random.randint(Ny)

            if np.random.random() * n_max <= n[ix, iy]:
                particles.append(x[ix] + 1j * y[iy])
        return np.asarray(particles)

    def get_inds(self, pos, model):
        """Return the indices (ix, iy) on the grid.

        Note: these are floating point values.  We keep them as floats
        so that the clients can display with higher accuracy if desired.
        """
        x, y = model.xy
        Lx, Ly = model.Lxy
        Nx, Ny = model.Nx, model.Ny
        pos = pos + (Lx + 1j * Ly) / 2.0
        ix = (pos.real % Lx) / Lx * (Nx - 1)
        iy = (pos.imag % Ly) / Ly * (Ny - 1)
        return (ix, iy)

    def update_tracer_velocity(self, model):
        """Define the velocity field for the particles"""
        # px, py = self.kxy
        # px *= self.hbar
        # py *= self.hbar
        # m = self.m
        # n = self.data.conj()*self.data
        # self._data_fft == self.fft(self.data)
        # v_x = (self.ifft(px*self.fft(self.data)) / self.data / m).real
        # v_y = (self.ifft(py*self.fft(self.data)) / self.data / m).real
        self.v_trace = model.get_v()

    def update_tracer_pos(self, dt, model):
        """Applies the velocity field to the particle positions and
        updates with time dt"""
        if not hasattr(self, "_par_pos"):
            return
        if not hasattr(self, "v_trace"):
            self.update_tracer_velocity()
        pos = self._par_pos
        ix, iy = [np.round(_i).astype(int) for _i in self.get_inds(pos, model=model)]
        v = self.v_trace[ix, iy]
        pos += dt * v

    def get_tracer_particles(self):
        """Return the tracer particle positions.

        This is a 1D complex array of the particle positions in data
        coordinates."""
        return getattr(self, "_par_pos", [])
