"""Tracer particle support.

This module provides support for generating, tracking, and viewing
tracer particles to track the flow during a simulation.
"""
import math
import numpy as np


class TracerParticlesBase:
    """

    Attributes
    ----------
    hbar_m : float
        Constant `hbar/m`.
    seed : int
        Seed for random number generator.
    skip : int
        Used to downsample the FFT for speed.
    eps : float
        If the density vanishes, then the velocity can diverge.  To prevent this, we
        use `n + eps*n.max()` as the denominator.
    """

    def __init__(self, xy, psi, N=100, hbar_m=1.0, eps=1e-4, seed=1, skip=1):
        self.N = N
        self.xy = x, y = xy
        self.z0 = x.ravel()[0] + 1j * y.ravel()[0]
        self.dxy = tuple(_x.ravel()[1] - _x.ravel()[0] for _x in xy)
        self.Nxy = tuple(len(_x.ravel()) for _x in xy)
        self.Lxy = tuple(_d * _N for _d, _N in zip(self.dxy, self.Nxy))
        self.kxy = np.meshgrid(
            *[2 * np.pi * np.fft.fftfreq(_N, _d) for _N, _d in zip(self.Nxy, self.dxy)],
            indexing="ij",
            sparse=True
        )
        self.hbar_m = hbar_m
        self.seed = seed
        self.eps = eps
        self.zs, self.vs = self.get_zs_vs(psi=psi)[:2]
        self.skip = skip

    def get_zs_vs(self, psi):
        """Return lists `(zs, vs, ixys)` with positions and velocities of N particles sampling
        the density.

        Arguments
        ---------
        psi : complex array
            Wavefunction

        Returns
        -------
        zs : complex array
            Locations of the tracer particles
        vs : complex array
            Velocities of the tracer particles
        ixys : List((int, int))
            Indexes of the corresponding particles in the array.
        """
        rng = np.random.default_rng(seed=self.seed)
        x, y = map(np.ravel, self.xy)
        Nx, Ny = self.Nxy
        n, v = self.get_n_v(psi=psi)
        n_max = n.max()

        ixys = []
        zs = []
        vs = []
        while len(zs) < self.N:
            ix, iy = rng.integers(Nx), rng.integers(Ny)

            if rng.random() * n_max <= n[ix, iy]:
                ixys.append((ix, iy))
                zs.append(x[ix] + 1j * y[iy])
                vs.append(v[ix, iy])
        zs, vs = map(np.asarray, [zs, vs])
        return zs, vs, ixys

    def get_n_v(self, psi, fft=None, ifft=None):
        """Return `(n, v)`, the density and velocity from `psi`.

        Arguments
        ---------
        psis : array-like
            Complex array of wavefunctions.  Velocities are extracted as the gradient of
            the phase.
        kxy : (array-like, array-like)
            Wave-vectors `kx` and `ky`.
        """
        if fft is None:
            fft, ifft = np.fft.fftn, np.fft.ifftn

        kx, ky = self.kxy

        psi_c = psi.conj()
        n = (psi_c * psi).real
        psi_t = fft(psi)
        j = (psi_c * ifft(kx * psi_t)).real + 1j * (psi_c * ifft(ky * psi_t)).real
        v = self.hbar_m * j / (n + self.eps * n.max())
        return (n, v)

    def get_vs(self, zs, psi, fftn=None):
        """Return the velocities at the points `zs`.

        Arguments
        ---------
        psi : array-like
            Complex array of wavefunctions.  Velocities are extracted as the gradient of
            the phase.
        """
        psi = psi[:: self.skip, :: self.skip]
        x, y = map(np.ravel, self.xy)
        x0, y0 = x[0], y[0]
        dxy = (self.skip * (x[1] - x0), self.skip * (y[1] - y0))
        Nxy = psi.shape
        kx, ky = np.meshgrid(
            *[2 * np.pi * np.fft.fftfreq(_N, _d) for _N, _d in zip(Nxy, dxy)],
            indexing="ij",
            sparse=True
        )

        if fftn is None:
            fftn = np.fft.fftn

        psi_t = fftn(psi)

        zs = np.ravel(zs)[:, None]
        Qx = np.exp(1j * kx.ravel()[None, :] * (zs.real + x0)) / Nxy[0]
        Qy = np.exp(1j * ky.ravel()[None, :] * (zs.imag + y0)) / Nxy[1]

        def ifftn(yt):
            """Return the ifft of yt at zs."""
            return (Qy * (Qx @ yt)).sum(axis=-1)

        psis = ifftn(psi_t)
        # assert np.allclose(np.einsum("zx,zy,xy->z", Qx, Qy, psi_t), ifft(psi_t))
        psis_c = psis.conj()
        js = (psis_c * ifftn(kx * psi_t)).real + 1j * (psis_c * ifftn(ky * psi_t)).real
        ns = (psis_c * psis).real
        vs = self.hbar_m * js / (ns + self.eps * ns.max())
        return vs

    @property
    def inds(self):
        """Return the indices and angles `(ix, iy, vs)` on the grid.

        Note: these are floating point values.  We keep them as floats
        so that the clients can display with higher accuracy if desired.
        """
        Lx, Ly = self.Lxy
        Nx, Ny = self.Nxy
        zs = self.zs - self.z0
        ix = (zs.real % Lx) / Lx * (Nx - 1)
        iy = (zs.imag % Ly) / Ly * (Ny - 1)
        vs = self.vs / Lx * (Nx - 1)
        return (ix, iy, vs)

    def evolve(self, psi, dt):
        """Update the `zs` and `vs` from psi."""
        # Use a leapfrog integrator - evaluate vs halfway through
        zs = self.zs + self.vs * dt / 2
        self.vs = self.get_vs(zs, psi=psi)
        self.zs += self.vs * dt


class TracerParticles(TracerParticlesBase):
    def __init__(self, model, N_particles=1000):
        self.N_particles = N_particles
        self.model = model
        self._par_pos = self.tracer_particles_create(self.model)

    def tracer_particles_create(self, model):
        zs, vs = self.init(density=model.get_density())[:2]
        return zs

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
