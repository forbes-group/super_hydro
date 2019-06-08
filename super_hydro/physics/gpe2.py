"""Two-component systems.

Here we model two-component systems with spin-orbit coupling along the
x axis.  We assume that the coupling constants g_ab = g_bb = g_ab are
equal which is a good approximation for Rubidium.
"""

import attr

import numpy as np
import numpy.fft

from .. import utils


@attr.s
class Dispersion(object):
    r"""Tools for computing porperties of the lower band dispersion.

    Everything is expressed in dimensionless units with $k/k_r$,
    $d=\delta/4E_R$, $w=\Omega/4E_R$, and $E_\pm/2E_R$.

    Examples
    --------
    >>> E = Dispersion(w=1.5/4, d=0.543/4)
    >>> ks = np.linspace(-3, 3, 500)
    >>> ks_ = (ks[1:] + ks[:-1])/2.0
    >>> ks__ = ks[1:-1]
    >>> Es = E(ks).T
    >>> dEs = E(ks, d=1).T
    >>> ddEs = E(ks, d=2).T
    >>> dEs_ = np.diff(Es, axis=0)/np.diff(ks)[:, None]
    >>> ddEs__ = np.diff(dEs_, axis=0)/np.diff(ks_)[:, None]
    >>> np.allclose((dEs[1:] + dEs[:-1])/2, dEs_, rtol=0.01)
    True
    >>> np.allclose(ddEs[1:-1], ddEs__, rtol=0.04)
    True
    """
    d = attr.ib()
    w = attr.ib()

    def Es(self, k, d=0):
        D = np.sqrt((k-self.d)**2 + self.w**2)
        if d == 0:
            res = (k**2 + 1)/2.0 - D, (k**2 + 1)/2.0 + D
        elif d == 1:
            res = k - (k-self.d)/D, k + (k-self.d)/D
        elif d == 2:
            res = 1.0 - self.w**2/D**3, 1.0 + self.w**2/D**3
        else:
            raise NotImplementedError("Only d=0, 1, or 2 supported. (got d={})"
                                      .format(d))
        return np.asarray(res)

    __call__ = Es

    def newton(self, k):
        return k - self.Es(k, d=1)[0]/self.Es(k, d=2)[0]

    def get_k0(self, N=5):
        """Return the minimum of the lower dispersion branch."""
        # Note that sign(k_0) = -sign(d) for the lower minimum
        k0 = -np.sign(self.d)/2.0
        for n in range(N):
            k0 = self.newton(k0)
        return k0

    def get_ab(self, branch=-1):
        """Return the wavefunction factors `(psi_a, psi_b)` for the
        specified band.

        Parameters
        ----------
        branch : -1 or 1
           1 for upper branch, -1 for lower branch (default).
        """
        d_ = self.d
        C_ = w_ = self.w
        k_ = self.get_k0()

        D_ = -branch*np.sqrt((k_-d_)**2 + w_**2)
        B_ = k_ - d_
        theta = np.arctan2(-B_ - D_, C_)

        return np.cos(theta), np.sin(theta)


class State(object):
    """

    Parameters
    ----------
    r0 : float
       Finger radius.
    soc_w : float
       SOC strength: w=Omega/4/E_R
    soc_d : float
       SOC detuning (chemical potential difference): d=delta/4/E_R
    V0_mu : float
       Potential strength in units of mu
    healing_length

    """
    dim = 2

    def __init__(self, Nxy=(32, 32), dx=0.1,
                 healing_length=1.0,
                 r0=1.0, V0_mu=0.5,
                 cooling_phase=1.0+0.01j,
                 cooling_steps=100, dt_t_scale=0.1,
                 g=1.0, m=1.0, hbar=1.0,
                 # k_R=2.0, soc_d=0.05, soc_w=0.5,
                 k_R=5.0, soc_d=0.5/4.0, soc_w=0.25,
                 test_finger=False):
        self.g = g
        self.hbar = hbar
        self.m = m

        self.Nxy = Nx, Ny = Nxy
        self.dx = dx
        self.Lxy = Lx, Ly = Lxy = np.asarray(Nxy)*dx

        self.r0 = r0
        self.V0_mu = V0_mu
        self.healing_length = healing_length
        self.cooling_phase = cooling_phase
        dx, dy = np.divide(Lxy, Nxy)
        x = (np.arange(Nx)*dx - Lx/2.0)[:, None]
        y = (np.arange(Ny)*dy - Ly/2.0)[None, :]
        self.xy = (x, y)

        kx = 2*np.pi * np.fft.fftfreq(Nx, dy)[:, None]
        ky = 2*np.pi * np.fft.fftfreq(Ny, dx)[None, :]
        self.kxy = (kx, ky)
        self.K = hbar**2*(kx**2 + ky**2)/2.0/self.m

        self.n0 = n0 = hbar**2/2.0/healing_length**2/g
        self.mu = g*n0
        mu_min = max(0, min(self.mu, self.mu*(1-self.V0_mu)))
        self.c_s = np.sqrt(self.mu/self.m)
        self.c_min = np.sqrt(mu_min/self.m)
        # self.v_max = 1.1*self.c_min

        # SOC Parameters
        # Make sure k_R and k0 are lattice momenta
        kx_ = kx.ravel()
        self.k_R = kx_[np.argmin(abs(kx_ - k_R))]
        self.E_R = (hbar*self.k_R)**2/2/m
        self.Omega = soc_w*4*self.E_R
        self.delta = soc_d*4*self.E_R
        self.dispersion = Dispersion(w=soc_w, d=soc_d)
        k0 = self.dispersion.get_k0() * self.k_R
        self.k0 = kx_[np.argmin(abs(kx_ - k0))]

        psi_ab = np.asarray(self.dispersion.get_ab())[self.bcast]

        ka = self.k0 + self.k_R
        kb = self.k0 - self.k_R
        assert np.allclose(0, [abs(ka - kx_).min(),
                               abs(kb - kx_).min()])

        phase = np.exp(1j*np.array([ka, kb])[self.bcast]*(x + 0*y))
        # phase = 1.0
        self.data = (np.ones(Nxy, dtype=complex)[None, ...]
                     * np.sqrt(n0) * psi_ab * phase)
        self._N = self.get_density().sum()

        # Precompute off-diagonal potential for speed.
        self._Vab = self.Omega/2.0 * np.exp(2j*k_R*x) + 0*y

        self.test_finger = test_finger
        self.z_finger = 0 + 0j
        self.pot_k_m = 10.0
        self.pot_z = 0 + 0j
        self.pot_v = 0 + 0j
        self.pot_damp = 4.0

        self.t = -10000
        self.dt = dt_t_scale*self.t_scale
        self._phase = -1.0/self.hbar
        self.step(cooling_steps)
        self.t = 0
        self._phase = -1j/self.hbar/cooling_phase
        self.dt = dt_t_scale*self.t_scale
        self.c_s = np.sqrt(self.mu/self.m)

    @property
    def v_max(self):
        return self.c_s
        c_min = np.sqrt(self.g*self.get_density().min()/self.m)
        return c_min

    def get_densities(self):
        return abs(self.data)**2

    def get_density(self):
        return self.get_densities().sum(axis=0)

    def set_xy0(self, x0, y0):
        self.z_finger = x0 + 1j*y0

    @property
    def t_scale(self):
        return self.hbar/self.K.max()

    @property
    def bcast(self):
        """Return a set of indices suitable for broadcasting masses etc."""
        return (slice(None), ) + (None,)*self.dim

    @property
    def z_finger(self):
        if self.test_finger:
            if self.t >= 0:
                return 3.0*np.exp(1j*self.t/5)
            else:
                return 3.0
        else:
            return self._z_finger

    @z_finger.setter
    def z_finger(self, z_finger):
        self._z_finger = z_finger

    def fft(self, y):
        return np.fft.fftn(y)

    def ifft(self, y):
        return np.fft.ifftn(y)

    def get_Vext(self):
        x, y = self.xy
        x0, y0 = self.pot_z.real, self.pot_z.imag
        Lx, Ly = self.Lxy
        x = (x - x0 + Lx/2) % Lx - Lx/2
        y = (y - y0 + Ly/2) % Ly - Ly/2
        r2 = x**2 + y**2
        return self.V0_mu*self.mu * np.exp(-r2/2.0/self.r0**2)

    def apply_expK(self, dt, factor=1.0):
        y = self.data
        self.data[...] = self.ifft(np.exp(self._phase*dt*self.K*factor)
                                   * self.fft(y))

    def apply_expV(self, dt, factor=1.0):
        y = self.data
        n = self.get_density()
        V = self.get_Vext() + self.g*n - self.mu
        Va = V - self.delta/2.0
        Vb = V + self.delta/2.0
        Vab = self._Vab
        _tmp = self._phase*dt*factor * np.array([[Va, Vab],
                                                 [Vab.conj(), Vb]])
        self.data[...] = utils.dot2(utils.expm2(_tmp), y)
        self.data *= np.sqrt(self._N/n.sum())

    def mod(self, z):
        """Make sure the point z lies in the box."""
        return complex(*[(_x + _L/2) % (_L) - _L/2
                         for _x, _L in zip((z.real, z.imag), self.Lxy)])

    def step(self, N):
        dt = self.dt
        self.apply_expK(dt=dt, factor=0.5)
        self.t += dt/2.0
        for n in range(N):
            self.pot_z += dt * self.pot_v
            pot_a = -self.pot_k_m * (self.pot_z - self.z_finger)
            pot_a += -self.pot_damp * self.pot_v
            self.pot_v += dt * pot_a
            if abs(self.pot_v) > self.v_max:
                self.pot_v *= self.v_max/abs(self.pot_v)

            self.pot_z = self.mod(self.pot_z)
            self.apply_expV(dt=dt, factor=1.0)
            self.apply_expK(dt=dt, factor=1.0)
            self.t += dt
        self.apply_expK(dt=dt, factor=-0.5)
        self.t -= dt/2.0

    def plot(self):
        from matplotlib import pyplot as plt
        n = self.get_density()
        x, y = self.xy
        plt.pcolormesh(x.ravel(), y.ravel(), n.T)
        plt.gca().set_aspect(1)
        plt.plot([self.pot_z.real], [self.pot_z.imag], 'ro')
        plt.plot([self.z_finger.real], [self.z_finger.imag], 'go')
        plt.title("{:.2f}".format(self.t))
        plt.colorbar()
