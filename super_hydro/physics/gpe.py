import math

import numpy as np
import numpy.fft

from .helpers import ModelBase, FingerMixin

from .. import utils, interfaces
from .. import widgets as w

try:
    import mmfutils.performance.fft
except ImportError:
    mmfutils = None

try:
    import numexpr
except ImportError:
    numexpr = None


_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
warn = _LOGGER.warn
log_task = _LOGGER.log_task


class GPEBase(ModelBase, FingerMixin):
    """Helper class for models.

    This class assumes that the underlying problem is of a quantum
    nature, involving hbar, and solved on a Fourier lattice.  A such,
    some of the requisite calculations are performed in the init()
    method to avoid duplicating code.

    Parameters
    ----------
    hbar : float
       Planck's constant.
    Nx, Ny : int
       Size of the grid.
    dx : float
       Lattice spacing (assumed to be the same in each direction).
    cooling : float
       Amount of cooling to apply to the system during evolution.

    """
    params = dict(
        hbar=1.0,
        Nx=32, Ny=32, dx=1.0,
        cooling=0.01,
    )

    layout = w.VBox([
        w.FloatLogSlider(name='cooling',
                         base=10, min=-10, max=1, step=0.2,
                         description='Cooling'),
        FingerMixin.layout])

    def init(self):
        """Perform any calculations needed when parameters change.
        Provides an alternative to having to define setters for each
        sensitive parameters.
        """
        Nx, Ny = self.Nxy = self.Nx, self.Ny
        Lx, Ly = self.Lxy = np.asarray(self.Nxy)*self.dx
        dx, dy = np.divide(self.Lxy, self.Nxy)
        x = (np.arange(Nx)*dx - Lx/2.0)[:, None]
        y = (np.arange(Ny)*dy - Ly/2.0)[None, :]
        self.xy = (x, y)

        self.kxy = kx, ky = (2*np.pi * np.fft.fftfreq(Nx, dx)[:, None],
                             2*np.pi * np.fft.fftfreq(Ny, dy)[None, :])
        
        cooling_phase = 1+self.cooling*1j
        cooling_phase = cooling_phase/abs(cooling_phase)
        self._phase = -1j/self.hbar/cooling_phase
        
        if mmfutils and False:
            self._fft = mmfutils.performance.fft.get_fftn_pyfftw(self.data)
            self._ifft = mmfutils.performance.fft.get_ifftn_pyfftw(self.data)
        else:
            self._fft = np.fft.fftn
            self._ifft = np.fft.ifftn

        super().init()

    def fft(self, y):
        return self._fft(y, axes=(-1, -2))

    def ifft(self, y):
        return self._ifft(y, axes=(-1, -2))

    def set(self, param, value):
        """Set the param attribute to value.

        This method looks for a `set_{param}` method and uses it
        first, falling back to the standard `setattr` method.

        The init() method is called in case any attributes need updating.
        """
        # print(f"Setting {param}={value}")
        set_param = getattr(self, "set_{}".format(param),
                            lambda _v: setattr(self, param, _v))
        set_param(value)
        self.init()

    def get(self, param):
        return getattr(self, param)

    def step(self, N, tracer_particles=None):
        dt = self.dt
        self.apply_expK(dt=dt, factor=0.5)
        self.t += dt/2.0
        for n in range(N):
            if tracer_particles is not None:
                # Update tracer particle positions.
                # Maybe defer if too expensive
                tracer_particles.update_tracer_velocity(state=self)
                tracer_particles.update_tracer_pos(dt, state=self)

            density = self.get_density()
            if isinstance(self, FingerMixin) and self.t > 0:
                # Don't move finger potential while preparing state.
                self._step_finger_potential(dt=dt, density=density)

            self.apply_expV(dt=dt, factor=1.0, density=density)
            self.apply_expK(dt=dt, factor=1.0)
            self.t += dt

        self.apply_expK(dt=dt, factor=-0.5)
        self.t -= dt/2.0

        # Update tracer particle velocities after each full loop for speed
        # self.update_tracer_velocity()

    ######################################################################
    # Required by subclasses
    dt = NotImplemented
    t = NotImplemented

    def apply_expK(self, dt, factor):
        raise NotImplementedError()

    def apply_expV(self, dt, factor, density):
        raise NotImplementedError()


class BEC(GPEBase):
    """Single component BEC.

    Parameters
    ----------
    """
    params = dict(
        g=1.0, m=1.0,
        healing_length=10.0,
        cooling=0.01,
        cooling_steps=100, dt_t_scale=0.1,
        winding=10,
        cylinder=True,
        )

    layout = w.VBox([
        w.Checkbox(True, name='cylinder', description="Trap"),
        GPEBase.layout])

    def __init__(self, opts):
        super().__init__(opts=opts)

        self.mu = self.hbar**2/2.0/self.m/self.healing_length**2
        self.n0 = self.mu/self.g
        mu_min = max(0, min(self.mu, self.mu*(1-self.finger_V0_mu)))
        self.c_s = np.sqrt(self.mu/self.m)
        self.c_min = np.sqrt(mu_min/self.m)
        # self.v_max = 1.1*self.c_min

        self.c_s = np.sqrt(self.mu/self.m)

        self.init()
        self.set_initial_data()
        self._N = self.get_density().sum()

        self.t = 0

    def init(self):
        super().init()
        kx, ky = self.kxy
        self.K = self.hbar**2*(kx**2 + ky**2)/2.0/self.m
        self._V_trap = self.get_V_trap()
        self.dt = self.dt_t_scale*self.t_scale
        
    def set_initial_data(self):
        self.data = np.ones(self.Nxy, dtype=complex) * np.sqrt(self.n0)
        self._N = self.get_density().sum()

        # Cool a bit to remove transients.
        _phase, self._phase = self._phase, -1j/self.hbar
        self.t = -10000
        self.step(self.cooling_steps, tracer_particles=None)
        self.t = 0
        self._phase = self._phase

        if self.cylinder:
            x, y = self.xy
            self.data *= np.exp(1j*self.winding*np.angle(x+1j*y))

    def get_density(self):
        y = self.data
        return (y.conj()*y).real

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
        """Return the maximum speed finger potential will move at."""
        # c_min = 1.0*np.sqrt(self.g*density.min()/self.m)
        c_mean = 1.0*np.sqrt(self.g*density.mean()/self.m)
        return c_mean

    @property
    def t_scale(self):
        return self.hbar/self.K.max()

    def get_V_trap(self):
        """Return any static trapping potential."""
        if self.cylinder:
            x, y = self.xy
            Lx, Ly = self.Lxy
            r2_ = (2*x/Lx)**2 + (2*y/Ly)**2
            return 100*self.mu*utils.mstep(r2_ - 0.8, 0.2)
        else:
            return 0

    def get_Vext(self):
        """Return the full external potential."""
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
        if density is None:
            density = self.get_density()
        n = density
        if numexpr:
            self.data[...] = numexpr.evaluate(
                'exp(f*(V+g*n-mu))*y*sqrt(_n)',
                local_dict=dict(
                    V=self.get_Vext(),
                    g=self.g,
                    n=n,
                    mu=self.mu,
                    _n=self._N/n.sum(),
                    f=self._phase*dt*factor,
                    y=y))
        else:
            V = self.get_Vext() + self.g*n - self.mu
            self.data[...] = np.exp(self._phase*dt*V*factor) * y
            self.data *= np.sqrt(self._N/n.sum())

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


class BECSOC(BEC):
    """Model implementing a BEC with modified dispersion.
    """
    params = dict(
        BEC.params,
        soc=True,
        soc_d=0.05, soc_w=0.5)

    layout = w.VBox([
        w.HBox([w.Checkbox(name="soc", description="SOC"),
                w.FloatSlider(name='soc_d',
                              min=-1, max=1, step=0.01,
                              description='detuning/4E_R'),
                w.FloatSlider(name='soc_w',
                              min=-2, max=2, step=0.01,
                              description='Omega/4E_R')]),
        BEC.layout])

    def __init__(self, opts):
        super().__init__(opts=opts)

    def init(self):
        super().init()
        kx, ky = self.kxy
        if self.soc:
            self._dispersion = Dispersion(d=self.soc_d, w=self.soc_w)
            kR = 3 / self.healing_length
            kR = 1.0/self.r0
            k0 = self._dispersion.get_k0()
            E0 = self._dispersion(k0)[0]
            kx = kx + kR*k0
            kx2 = 2*kR**2 * (self._dispersion(kx/kR) - E0)[0]
        else:
            kx2 = kx**2

        self.kxy = kx, ky
        self.K = self.hbar**2*(kx2 + ky**2)/2.0/self.m


class BECFlow(BEC):
    """Model implementing variable flow in a BEC.

    This model provides a way of demonstrating Landau's critical
    velocity.  This velocity is implemented by shifting the momenta by
    k_B = m*v/hbar
    """
    params = dict(BEC.params, cylinder=False, v_v_c=0)

    layout = w.VBox([
        w.FloatSlider(name='v_v_c',
                      min=-5, max=5, step=0.1,
                      description=r'v/v_c'),
        BEC.layout])

    def init(self):
        super().init()
        kx, ky = self.kxy
        kx, ky = self.kxy = (kx + self.k_B, ky)
        self.K = self.hbar**2*(kx**2 + ky**2)/2.0/self.m

    @property
    def k_B(self):
        """Return the Bloch momentum"""
        v_c = math.sqrt(self.mu/self.m)
        v = self.v_v_c*v_c
        return self.m * v / self.hbar


class BECSoliton(BECFlow):
    """Demonstrate the snaking instability of a dark soliton.

    Here we assume that the box is
    """
    params = dict(BECFlow.params, finger_V0_mu=0.1, v_c=0)

    layout = w.VBox([
        w.FloatSlider(name='v_c',
                      min=-0.99, max=0.99, step=0.01,
                      description='v/c'),
        BECFlow.layout])

    def set(self, param, value):
        super().set(param, value)
        if param in set(['v_c', 'Nx']):
            self.set_initial_data()

    def set_initial_data(self):
        self.data = np.empty(self.Nxy, dtype=complex)

        x, y = self.xy
        v_c = self.v_c
        c_s = np.sqrt(self.g*self.n0/self.m)
        length = self.hbar/self.m/c_s/np.sqrt(1-v_c**2)

        Lx, Ly = self.Lxy

        # Error here...
        # theta_twist = np.arccos(1-2*v_c**2)
        # phase = np.exp(-1j*theta_twist*x/Lx)

        def psi(x):
            return np.sqrt(self.n0)*(
                1j*v_c + np.sqrt(1-v_c**2)*np.tanh(x/length))

        theta = np.angle(psi(Lx/2)/psi(-Lx/2))
        phase = np.exp(1j*theta*x/Lx)
        self.data[...] = psi(x)/phase


interfaces.classImplements(BEC, interfaces.IModel)
interfaces.classImplements(BECFlow, interfaces.IModel)
interfaces.classImplements(BECSoliton, interfaces.IModel)
