import attr

import numpy as np
import numpy.fft
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


class ModelBase(object):
    """Helper class for models."""
    params = {}

    def __init__(self, opts):
        """Default constructor simply sets attributes defined in params."""
        self._initializing = True
        self.params = {_key: getattr(opts, _key, self.params[_key])
                       for _key in self.params}
        for _key in self.params:
            setattr(self, _key, self.params[_key])
        self._initializing = False

    def init(self):
        """Perform any calculations needed when parameters change.
        Provides an alternative to having to define setters for each
        sensitive parameters.
        """
        pass

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


class BEC(ModelBase):
    """Single component BEC.

    Parameters
    ----------
    V0_mu : float
       Potential strength in units of mu
    healing_length:
    """
    params = dict(
        g=1.0, hbar=1.0, m=1.0,
        Nx=32, Ny=32, dx=1.0,
        healing_length=10.0, r0=10.0, V0_mu=0.5,
        cooling=0.01,
        cooling_steps=100, dt_t_scale=0.1,
        winding=10,
        cylinder=True,
        test_finger=False)

    layout = w.VBox([
        w.FloatLogSlider(name='cooling',
                         base=10, min=-10, max=1, step=0.2,
                         description='Cooling'),
        w.FloatSlider(name='V0_mu',
                      min=-2, max=2, step=0.1,
                      description='V0/mu'),
        w.Checkbox(True, name='cylinder', description="Trap"),
        w.density])

    def __init__(self, opts):
        super().__init__(opts=opts)

        self.Nxy = Nxy = Nx, Ny = self.Nx, self.Ny
        self.Lxy = Lx, Ly = Lxy = np.asarray(self.Nxy)*self.dx
        dx, dy = np.divide(Lxy, Nxy)
        x = (np.arange(Nx)*dx - Lx/2.0)[:, None]
        y = (np.arange(Ny)*dy - Ly/2.0)[None, :]
        self.xy = (x, y)

        self._kxy = kx, ky = (2*np.pi * np.fft.fftfreq(Nx, dx)[:, None],
                              2*np.pi * np.fft.fftfreq(Ny, dy)[None, :])

        self.n0 = n0 = self.hbar**2/2.0/self.healing_length**2/self.g
        self.mu = self.g*n0
        mu_min = max(0, min(self.mu, self.mu*(1-self.V0_mu)))
        self.c_s = np.sqrt(self.mu/self.m)
        self.c_min = np.sqrt(mu_min/self.m)
        # self.v_max = 1.1*self.c_min

        self.data = np.ones(self.Nxy, dtype=complex) * np.sqrt(n0)

        if mmfutils and False:
            self._fft = mmfutils.performance.fft.get_fftn_pyfftw(self.data)
            self._ifft = mmfutils.performance.fft.get_ifftn_pyfftw(self.data)
        else:
            self._fft = np.fft.fftn
            self._ifft = np.fft.ifftn

        self._N = self.get_density().sum()

        self.z_finger = 0 + 0j
        self.pot_k_m = 10.0
        self.pot_z = 0 + 0j
        self.pot_v = 0 + 0j
        self.pot_damp = 4.0

        self.c_s = np.sqrt(self.mu/self.m)

        self.init()

        self.t = -10000
        self.dt = self.dt_t_scale*self.t_scale

        self.cooling_phase, cooling_phase = 1j, self.cooling_phase
        self.step(self.cooling_steps, tracer_particles=None)

        if self.cylinder:
            self.data *= np.exp(1j*self.winding*np.angle(x+1j*y))
        self.t = 0

        self.cooling_phase = cooling_phase

    def init(self):
        cooling_phase = 1+self.cooling*1j
        self.cooling_phase = cooling_phase/abs(cooling_phase)
        kx, ky = self.kxy = self._kxy
        self.K = self.hbar**2*(kx**2 + ky**2)/2.0/self.m
        self._V_trap = self.get_V_trap()
        self.dt = self.dt_t_scale*self.t_scale

    def fft(self, y):
        return self._fft(y, axes=(-1, -2))

    def ifft(self, y):
        return self._ifft(y, axes=(-1, -2))

    def get_density(self):
        y = self.data
        return (y.conj()*y).real

    def get_v(self, y=None):
        """Return the velocity field as a complex number."""
        if y is None:
            y = self.data
        yt = self.fft(y)
        px, py = self.kxy
        vx, vy = (self.ifft([px*yt, py*yt])/y).real / self.m
        return vx + 1j*vy

    # End of interface
    ######################################################################
    def set_xy0(self, xy0):
        x0, y0 = xy0
        self.z_finger = x0 + 1j*y0

    @property
    def _phase(self):
        return -1j/self.hbar/self.cooling_phase

    def get_v_max(self, density):
        # c_min = 1.0*np.sqrt(self.g*density.min()/self.m)
        c_mean = 1.0*np.sqrt(self.g*density.mean()/self.m)
        return c_mean

    @property
    def t_scale(self):
        return self.hbar/self.K.max()

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
        x, y = self.xy
        x0, y0 = self.pot_z.real, self.pot_z.imag
        Lx, Ly = self.Lxy

        # Wrap displaced x and y in periodic box.
        x = (x - x0 + Lx/2) % Lx - Lx/2
        y = (y - y0 + Ly/2) % Ly - Ly/2
        r2 = x**2 + y**2
        return self._V_trap + self.V0_mu*self.mu * np.exp(-r2/2.0/self.r0**2)

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

    def mod(self, z):
        """Make sure the point z lies in the box."""
        return complex(*[(_x + _L/2) % (_L) - _L/2
                         for _x, _L in zip((z.real, z.imag), self.Lxy)])

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
            self.pot_z += dt * self.pot_v
            pot_a = -self.pot_k_m * (self.pot_z - self.z_finger)
            pot_a += -self.pot_damp * self.pot_v
            self.pot_v += dt * pot_a
            v_max = self.get_v_max(density=density)
            if abs(self.pot_v) > v_max:
                self.pot_v *= v_max/abs(self.pot_v)
            self.pot_z = self.mod(self.pot_z)

            self.apply_expV(dt=dt, factor=1.0, density=density)
            self.apply_expK(dt=dt, factor=1.0)
            self.t += dt

        self.apply_expK(dt=dt, factor=-0.5)
        self.t -= dt/2.0

        # Update tracer particle velocities after each full loop for speed
        # self.update_tracer_velocity()

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
        kx, ky = self._kxy
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
    params = dict(BEC.params, cylinder=False, mv_mu=0)

    layout = w.VBox([
        w.FloatSlider(name='mv_mu',
                      min=-5, max=5, step=0.1,
                      description='v/(mu/m)'),
        BEC.layout])

    def init(self):
        super().init()
        kx, ky = self._kxy
        kx, ky = self.kxy = (kx + self.k_B, ky)
        self.K = self.hbar**2*(kx**2 + ky**2)/2.0/self.m

    @property
    def k_B(self):
        """Return the Bloch momentum"""
        mv = self.mv_mu*self.mu
        return mv/self.hbar


interfaces.classImplements(BEC, interfaces.IModel)
interfaces.classImplements(BECFlow, interfaces.IModel)
