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

    Parameters
    ----------
    w, d : float
       SOC parameters.
    k0, E0 : float
       If provided, the dispersion relationship is shifted so that the
       bottom of the lower band is centered here.  Typically one will
       set these as follows:

           dispersion = Dispersion(w=... d=...)
           k0 = dispersion.get_k0()
           E0 = dispersion.Es(k0)[0]
           dispersion.Dispersion(w=... d=..., k0=k0, E0=E0)

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
    def __init__(self, d, w, k0=0, E0=0):
        self.d = d
        self.w = w
        self.k0 = k0
        self.E0 = E0

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

    def get_ab(self, k_=None, branch=-1):
        """Return the wavefunction factors `(psi_a, psi_b)` for the
        specified band.

        Parameters
        ----------
        branch : -1 or 1
           1 for upper branch, -1 for lower branch (default).
        """
        d_ = self.d
        C_ = w_ = self.w
        if k_ is None:
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
        self.v_R = self.hbar*self.k_R/self.m
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
        k_B = self.m * v / self.hbar

        # Round to make sure it is commensurate with box.
        Lx, Ly = self.Lxy
        n = round(Lx*k_B/2/np.pi)
        k_B = 2*np.pi * n / Lx
        return k_B

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
    x-axis (equal Rashba and Dresselhaus terms).  Here we model the
    system with a single band model which is much faster, but misses
    some physics (notably, the phonon dispersion relationship is
    different.)

    Note: This class shifts the dispersion so that the minimum sits at
          k0 = E0 = 0.

    Parameters
    ----------
    soc_w : float
       SOC strength: w=Omega/4/E_R
    soc_d : float
       SOC detuning (chemical potential difference): d=delta/4/E_R
    l_R : float
       SOC lattice spacing.  This sets the scale for the SOC with the
       recoil momentum `k_R = 2*pi/l_R` and energy `E_R = (hbar*k_R)**2/2/m`.

    healing_length : float
       Length-scale on which the kinetic energy and potential are
       similar.  This defines how quickly the gas will vanish near
       boundaries and in the core of vortices etc.  This is used to
       set the chemical potential.
    dx : float
       Basis lattice spacing.  Should be smaller than all other length scales.

    """
    dim = 2

    params = dict(
        m=1.0, hbar=1.0, g=1.0,
        Nx=32, Ny=32, dx=0.1,
        healing_length=1.0,
        coolinge=0.01,
        cooling_steps=100, dt_t_scale=0.1,
        l_R=0.2, soc_d=0.5/4.0, soc_w=0.25)

    layout = w.VBox([
        w.FloatSlider(name='soc_w',
                      min=-3, max=3, step=0.1,
                      description=r'w'),
        w.FloatSlider(name='soc_d',
                      min=-2, max=2, step=0.1,
                      description=r'd'),
        GPEBase.layout])

    def __init__(self, opts):
        super().__init__(opts=opts)

        self.init()
        self.set_initial_data()

        self._N = self.get_density().sum()
        self.t = 0

    def get_psi(self):
        return self.data

    def set_psi(self, psi):
        self.data[...] = psi

    def init(self):
        super().init()
        kx, ky = self.kxy

        # SOC Parameters
        # For the single-band model, we do not need to ensure that k_R
        # is a lattice momentum like we do with the 2-component case.
        self.k_R = 2*np.pi / self.l_R
        self.v_R = self.hbar*self.k_R/self.m
        self.E_R = (self.hbar*self.k_R)**2/2/self.m
        self.Omega = self.soc_w*4*self.E_R
        self.delta = self.soc_d*4*self.E_R

        # Compute the dispersion relationship and shift it so that the
        # initial minimum is at k0 = 0.
        _dispersion = Dispersion(w=self.soc_w, d=self.soc_d)
        k0 = _dispersion.get_k0()
        E0 = _dispersion.Es(k0)[0]
        self.dispersion = Dispersion(w=self.soc_w, d=self.soc_d,
                                     k0=k0, E0=E0)
        self.k0 = 0.0

        # Compute the kinetic energy.
        Ex = 2*self.E_R * self.dispersion.Es(kx/self.k_R)[0]
        kx2 = 2*self.m * Ex / self.hbar**2
        self.K = self.hbar**2*(kx2 + ky**2)/2.0/self.m

        # Precompute potential for speed.
        x, y = self.xy
        self._V_trap = self.get_V_trap()
        self.dt = self.dt_t_scale*self.t_scale

    def set_initial_data(self):
        self.mu = self.hbar**2/2.0/self.m/self.healing_length**2
        self.c_s = np.sqrt(self.mu/self.m)

        mu_eff = self.mu - self.get_V_trap()
        psi0 = np.ma.divide(mu_eff, self.g)
        if not np.isscalar(psi0):
            psi0 = psi0.filled(0)

        self.data = np.ones(self.Nxy, dtype=complex) * psi0
        self._N = self.get_density().sum()

        # Cool a bit.
        self.t = -10000
        _phase, self._phase = self._phase, -1.0/self.hbar
        self.step(self.cooling_steps)
        self.t = 0
        self._phase = _phase

    def get_densities(self):
        """Return the densities (n_a, n_b).

        This version uses the spin-quasi-momentum map.
        """
        kx, ky = self.kxy
        y = self.get_psi()

        # Should formally have y.conj() in both terms, but it cancels.
        k = np.ma.divide(self.ifft(kx * self.fft(y)), y).filled(0).real
        psi_a, psi_b = self.dispersion.get_ab(k_=k/self.k_R)
        return abs(psi_a)**2, abs(psi_b)**2

    def get_density(self):
        return abs(self.get_psi())**2

    def get_v(self, y=None):
        """Return the velocity field as a complex number."""
        if y is None:
            y = self.get_psi()
        yt = self.fft(y)
        kx, ky = self.kxy
        k_x, k_y = np.ma.divide(self.ifft([kx*yt, ky*yt]), y).filled(0).real
        vy = k_y * self.hbar / self.m
        vx = self.dispersion.Es(k_x/self.k_R, d=1)[0]*self.v_R
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
        n = self.get_density()
        V = self.get_Vext() + self.g*n - self.mu
        self.data *= np.exp(self._phase*dt*factor * V)
        self.data *= np.sqrt(self._N/(n).sum())

    def plot(self):
        """Simple plotting for debugging."""
        from mmfutils import plot as mmfplt
        x, y = self.xy
        n = self.get_density()
        mmfplt.imcontourf(x, y, n, aspect=1)


class SuperSolid2(SOC2):
    """SuperSolid Explorer.

    Explore the supersolid phase in a two-component BEC with SOC.

    Parameters
    ----------
    lattice_k_k_R : float
       External lattice potential wavenumber in units of k_R.
    lattice_V0_mu : float
       Strength of external lattice potential in units of the chemical potential.
    lattice_x0 : float
       Center of external lattice potential.
    """
    params = dict(
        SOC2.params,
        lattice_k_k_R=2.0,
        lattice_V0_mu=0.1,
        lattice_x0=0.0,
    )

    layout = w.VBox([
        w.FloatSlider(name='lattice_k_k_R',
                      min=-3, max=3, step=0.1,
                      description=r'k_L/k_R'),
        w.FloatSlider(name='lattice_V0_mu',
                      min=-2, max=2, step=0.1,
                      description=r'V_L'),
        w.FloatSlider(name='lattice_x0',
                      min=-5, max=5, step=0.1,
                      description=r'x_0'),
        SOC2.layout])

    def init(self):
        super().init()

    def get_V_trap(self):
        """Return any static trapping potential."""
        x, y = self.xy
        Lx, Ly = self.Lxy
        k_L = self.lattice_k_k_R * self.k_R
        cells_L = np.round(Lx / (2*np.pi/k_L))
        k_L = 2*np.pi * cells_L / Lx
        V0 = self.lattice_V0_mu * self.mu
        return V0 * np.cos(k_L * (x - self.lattice_x0))
