"""Two-component systems.

Here we model two-component systems with spin-orbit coupling along the
x axis.  We assume that the coupling constants g_ab = g_bb = g_ab are
equal which is a good approximation for Rubidium.
"""
import math

import numpy as np
import numpy.fft

try:
    import numexpr
except ImportError:
    numexpr = None

from .. import utils, interfaces
from .. import widgets as w

from .helpers import FingerMixin
from .gpe import GPEBase


class Dispersion(object):
    r"""Tools for computing properties of the lower band dispersion.

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
    def __init__(self, d, w):
        self.d = d
        self.w = w

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


class SOC2(GPEBase):
    """Two-component BEC with spin orbit coupling (SOC) along the
    x-axis (equal Rashba and Dresselhaus terms).

    Parameters
    ----------
    r0 : float
       Finger radius.
    soc_w : float
       SOC strength: w=Omega/4/E_R
    soc_d : float
       SOC detuning (chemical potential difference): d=delta/4/E_R
    healing_length
    mv_mu : float
       Velocity of the moving frame in units of the chemical potential.
    """
    dim = 2

    params = dict(
        m=1.0, hbar=1.0,
        finger_r0=1.0,
        g_aa=1.0, g_bb=1.0, g_ab=1.0,
        Nx=32, Ny=32, dx=0.1,
        healing_length=1.0,
        coolinge=0.01,
        cooling_steps=100, dt_t_scale=0.1,
        k_R=5.0, soc_d=0.5/4.0, soc_w=0.25,
        v_v_c=0,
    )

    layout = w.VBox([
        w.FloatSlider(name='v_v_c',
                      min=-5, max=5, step=0.1,
                      description=r'v/v_c'),
        GPEBase.layout])

    def __init__(self, opts):
        super().__init__(opts=opts)

        self.mu = self.hbar**2/2.0/self.m/self.healing_length**2
        self.init()
        self.set_initial_data()

        self._N = self.get_density().sum()
        self.t = 0

    def init(self):
        super().init()
        kx, ky = self.kxy

        # Add flow
        kx, ky = self.kxy = (kx + self.k_B, ky)

        # SOC Parameters
        # Make sure k_R and k0 are lattice momenta
        kx_ = kx.ravel()
        self.k_R = kx_[np.argmin(abs(kx_ - self.k_R))]
        self.E_R = (self.hbar*self.k_R)**2/2/self.m
        self.Omega = self.soc_w*4*self.E_R
        self.delta = self.soc_d*4*self.E_R
        self.dispersion = Dispersion(w=self.soc_w, d=self.soc_d)
        k0 = self.dispersion.get_k0() * self.k_R
        self.k0 = kx_[np.argmin(abs(kx_ - k0))]
        self.K = self.hbar**2*(kx**2 + ky**2)/2.0/self.m

        # Precompute potential for speed.
        x, y = self.xy
        self._Vab = self.Omega/2.0 * np.exp(2j*self.k_R*x) + 0*y
        self._V_trap = self.get_V_trap()
        self.dt = self.dt_t_scale*self.t_scale

    def set_initial_data(self):
        psi_ab = np.asarray(self.dispersion.get_ab())[self.bcast]

        x, y = self.xy
        kx, ky = self.kxy
        kx_ = kx.ravel()

        ka = self.k0 + self.k_R
        kb = self.k0 - self.k_R
        assert np.allclose(0, [abs(ka - kx_).min(),
                               abs(kb - kx_).min()])

        phase = np.exp(1j*np.array([ka, kb])[self.bcast]*(x + 0*y))
        # phase = 1.0

        na0, nb0 = self.mu/self.g_aa, self.mu/self.g_bb
        n0 = na0 + nb0
        self.c_s = np.sqrt(self.mu/self.m)

        self.data = (np.ones(self.Nxy, dtype=complex)[None, ...]
                     * np.sqrt(n0) * psi_ab * phase)
        self._N = self.get_density().sum()

        self.t = -10000
        _phase, self._phase = self._phase, -1.0/self.hbar
        self.step(self.cooling_steps)
        self.t = 0
        self._phase = _phase

    def get_densities(self):
        return abs(self.data)**2

    def get_density(self):
        return self.get_densities().sum(axis=0)

    def get_v(self, y=None):
        """Return the velocity field as a complex number."""
        if y is None:
            y = self.data[0]
        yt = self.fft(y)
        kx, ky = self.kxy
        vx, vy = (self.ifft([kx*yt, ky*yt])/y).real * self.hbar / self.m
        return vx + 1j*vy

    # End of interface
    ######################################################################
    @property
    def k_B(self):
        """Return the Bloch momentum.  This implements an overall flow."""
        v_c = math.sqrt(self.mu/self.m)
        v = self.v_v_c*v_c
        return self.m * v / self.hbar

    def get_v_max(self, density):
        return self.c_s
        c_min = np.sqrt(self.g*density.min()/self.m)
        c_mean = 1.0*np.sqrt(self.g*density.mean()/self.m)
        return c_mean        
        return c_min

    @property
    def t_scale(self):
        return self.hbar/self.K.max()

    @property
    def bcast(self):
        """Return a set of indices suitable for broadcasting masses etc."""
        return (slice(None), ) + (None,)*self.dim

    def get_V_trap(self):
        """Return any static trapping potential."""
        if False and self.cylinder:
            x, y = self.xy
            Lx, Ly = self.Lxy
            r2_ = (2*x/Lx)**2 + (2*y/Ly)**2
            return 100*self.mu*utils.mstep(r2_ - 0.8, 0.2)
        else:
            return 0

    def get_Vext(self):
        return self._V_trap + super().get_Vext()

    def apply_expK(self, dt, factor=1.0):
        y = self.data
        if numexpr:
            yt = self.fft(y)
            self.data[...] = self.ifft(
                numexpr.evaluate(
                    'exp(f*K)*y',
                    local_dict=dict(
                        f=self._phase*dt*factor,
                        K=self.K,
                        y=yt)))
        else:
            self.data[...] = self.ifft(np.exp(self._phase*dt*self.K*factor)
                                       * self.fft(y))

    def apply_expV(self, dt, factor=1.0, density=None):
        y = self.data
        n_a, n_b = self.get_densities()
        V = self.get_Vext()
        Va = V + self.g_aa*n_a + self.g_ab*n_b - self.mu - self.delta/2.0
        Vb = V + self.g_bb*n_b + self.g_ab*n_a - self.mu + self.delta/2.0
        Vab = self._Vab
        _tmp = self._phase*dt*factor * np.array([[Va, Vab],
                                                 [Vab.conj(), Vb]])
        self.data[...] = utils.dot2(utils.expm2(_tmp), y)
        self.data *= np.sqrt(self._N/(n_a + n_b).sum())

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


class SOC1(GPEBase):
    """Two-component BEC with spin orbit coupling (SOC) along the
    x-axis (equal Rashba and Dresselhaus terms).

    Parameters
    ----------
    soc_w : float
       SOC strength: w=Omega/4/E_R
    soc_d : float
       SOC detuning (chemical potential difference): d=delta/4/E_R
    healing_length
    single_band : bool
       If `True`, then a single component is modeled with an
       appropriately modified dispersion.  This is significantly
       faster but misses physics if the second band is occupied.
    """
    dim = 2

    params = dict(
        m=1.0, hbar=1.0, g=1.0,
        Nx=32, Ny=32, dx=0.1,
        healing_length=1.0,
        coolinge=0.01,
        cooling_steps=100, dt_t_scale=0.1,
        k_R=5.0, soc_d=0.5/4.0, soc_w=0.25)

    def __init__(self, opts):
        super().__init__(opts=opts)

        self.init()
        self.set_initial_data()

        self._N = self.get_density().sum()
        self.t = 0

    def init(self):
        super().init()
        kx, ky = self.kxy

        # SOC Parameters
        # Make sure k_R and k0 are lattice momenta
        kx_ = kx.ravel()
        self.k_R = kx_[np.argmin(abs(kx_ - self.k_R))]
        self.E_R = (self.hbar*self.k_R)**2/2/self.m
        self.Omega = self.soc_w*4*self.E_R
        self.delta = self.soc_d*4*self.E_R
        self.dispersion = Dispersion(w=self.soc_w, d=self.soc_d)
        k0 = self.dispersion.get_k0() * self.k_R
        self.k0 = kx_[np.argmin(abs(kx_ - k0))]

        Ex = 2*self.E_R * self.dispersion(self.kx/self.k_R)[0]
        kx2 = 2*self.m * Ex / self.hbar**2
        self.K = self.hbar**2*(kx2 + ky**2)/2.0/self.m

        # Precompute potential for speed.
        x, y = self.xy
        self._V_trap = self.get_V_trap()
        self.dt = self.dt_t_scale*self.t_scale

    def set_initial_data(self):
        psi_ab = np.asarray(self.dispersion.get_ab())[self.bcast]

        x, y = self.xy
        kx, ky = self.kxy
        kx_ = kx.ravel()

        ka = self.k0 + self.k_R
        kb = self.k0 - self.k_R
        assert np.allclose(0, [abs(ka - kx_).min(),
                               abs(kb - kx_).min()])

        self.mu = self.hbar**2/2.0/self.m/self.healing_length**2
        n0 = self.mu/self.g
        self.c_s = np.sqrt(self.mu/self.m)

        self.data = np.ones(self.Nxy, dtype=complex) * np.sqrt(n0)
        self._N = self.get_density().sum()

        self.t = -10000
        _phase, self._phase = self._phase, -1.0/self.hbar
        self.step(self.cooling_steps)
        self.t = 0
        self._phase = _phase

    def get_densities(self):
        """Return the densities (n_a, n_b)."""
        raise NotImplementedError()

    def get_density(self):
        return abs(self.get_psi())**2

    def get_v(self, y=None):
        """Return the velocity field as a complex number."""
        if y is None:
            y = self.data
        yt = self.fft(y)
        kx, ky = self.kxy
        vx, vy = (self.ifft([kx*yt, ky*yt])/y).real * self.hbar / self.m
        return vx + 1j*vy

    # End of interface
    ######################################################################
    def get_finger_v_max(self, density):
        return self.c_s
        c_min = np.sqrt(self.g*density.min()/self.m)
        c_mean = 1.0*np.sqrt(self.g*density.mean()/self.m)
        return c_mean        
        return c_min

    @property
    def t_scale(self):
        return self.hbar/self.K.max()

    @property
    def bcast(self):
        """Return a set of indices suitable for broadcasting masses etc."""
        return (slice(None), ) + (None,)*self.dim

    def get_V_trap(self):
        """Return any static trapping potential."""
        if False and self.cylinder:
            x, y = self.xy
            Lx, Ly = self.Lxy
            r2_ = (2*x/Lx)**2 + (2*y/Ly)**2
            return 100*self.mu*utils.mstep(r2_ - 0.8, 0.2)
        else:
            return 0

    def get_Vext(self):
        return self._V_trap + super().get_Vext()

    def apply_expK(self, dt, factor=1.0):
        y = self.data
        if numexpr:
            yt = self.fft(y)
            self.data[...] = self.ifft(
                numexpr.evaluate(
                    'exp(f*K)*y',
                    local_dict=dict(
                        f=self._phase*dt*factor,
                        K=self.K,
                        y=yt)))
        else:
            self.data[...] = self.ifft(np.exp(self._phase*dt*self.K*factor)
                                       * self.fft(y))

    def apply_expV(self, dt, factor=1.0, density=None):
        y = self.data
        n_a, n_b = self.get_densities()
        V = self.get_Vext()
        Va = V + self.g_aa*n_a + self.g_ab*n_b - self.mu - self.delta/2.0
        Vb = V + self.g_bb*n_b + self.g_ab*n_a - self.mu + self.delta/2.0
        Vab = self._Vab
        _tmp = self._phase*dt*factor * np.array([[Va, Vab],
                                                 [Vab.conj(), Vb]])
        self.data[...] = utils.dot2(utils.expm2(_tmp), y)
        self.data *= np.sqrt(self._N/(n_a + n_b).sum())

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
