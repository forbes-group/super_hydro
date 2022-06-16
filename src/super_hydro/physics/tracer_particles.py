"""Tracer particle support.

This module provides support for generating, tracking, and viewing
tracer particles to track the flow during a simulation.
"""
import math
import numpy as np


class TracerParticlesBase:
    def __init__(self, xy, N=100):
        self.xy = xy
        self.N = N

    def init(self, n, v, seed=None):
        """Return lists `(zs, vs)` with positions and velocities of N particles sampling
        the density.

        Arguments
        ---------
        n : array-like
            Array of densities.
        v : array-like
            Complex array of velocities.
        seed : int
            Seed for random number generator.
        """
        rng = np.random.default_rng(seed=seed)
        x, y = map(np.ravel, self.xy)
        Nx, Ny = len(x), len(y)
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
        return ixys, zs, vs

    def get_n_v(self, psi, kxy, hbar_m=1.0, eps=1e-4, fft=None, ifft=None):
        """Return `(n, v)`, the density and velocity from `psi`.

        Arguments
        ---------
        psis : array-like
            Complex array of wavefunctions.  Velocities are extracted as the gradient of
            the phase.
        kxy : (array-like, array-like)
            Wave-vectors `kx` and `ky`.
        hbar_m : float
            Constant `hbar/m`.
        eps : float
            If the density vanishes, then the velocity can diverge.  To prevent this, we
            use `n + eps*n.max()` as the denominator.
        """
        if fft is None:
            fft, ifft = np.fft.fftn, np.fft.ifftn
        kx, ky = kxy

        psi_c = psi.conj()
        n = (psi_c * psi).real
        psi_t = fft(psi)
        j = (psi_c * ifft(kx * psi_t)).real + 1j * (psi_c * ifft(ky * psi_t)).real
        v = hbar_m * j / (n + eps * n.max())
        return (n, v)

    def get_vs(self, zs, psi, xy, hbar_m=1.0, eps=1e-4, skip=1):
        """Return the velocities at the points `zs`.

        Arguments
        ---------
        psis : array-like
            Complex array of wavefunctions.  Velocities are extracted as the gradient of
            the phase.
        xy : (array-like, array-like)
            Lattice.
        hbar_m : float
            Constant `hbar/m`.
        eps : float
            If the density vanishes, then the velocity can diverge.  To prevent this, we
            use `n + eps*n.max()` as the denominator.
        skip : int
            Used to downsample the FFT for speed.
        """
        psi = psi[::skip, ::skip]
        x, y = map(np.ravel, xy)
        x0, y0 = x[0], y[0]
        dxy = (skip * (x[1] - x0), skip * (y[1] - y0))
        Nxy = psi.shape
        kx, ky = np.meshgrid(
            *[2 * np.pi * np.fft.fftfreq(_N, _d) for _N, _d in zip(Nxy, dxy)],
            indexing="ij",
            sparse=True
        )

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
        vs = hbar_m * js / (ns + eps * ns.max())
        return vs


class TracerParticles(TracerParticlesBase):
    def __init__(self, model, N_particles=1000):
        self.N_particles = N_particles
        self.model = model
        self._par_pos = self.tracer_particles_create(self.model)

    def tracer_particles_create(self, model):
        zs, vs = self.init(density=model.get_density())
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
