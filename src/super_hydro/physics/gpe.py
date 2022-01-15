"""
GPE: Gross-Pitaevski Equation
=============================

This modules provides classes for implemented the Gross-Pitaevski
equation (GPE) for simulating Bose-Einstein condensates (BECs).
"""
import math

import numpy as np
import numpy.fft

from .helpers import ModelBase, FingerMixin

from .. import utils, interfaces
from ..interfaces import implementer
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
warning = _LOGGER.warning
log_task = _LOGGER.log_task

from .testing import HelloWorld


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
        Nx=32,
        Ny=32,
        dx=1.0,
        cooling=0.01,
    )

    layout = w.VBox(
        [
            w.FloatLogSlider(
                name="cooling", base=10, min=-10, max=1, step=0.2, description="Cooling"
            ),
            FingerMixin.layout,
        ]
    )

    def init(self):
        """Perform any calculations needed when parameters change.
        Provides an alternative to having to define setters for each
        sensitive parameters.
        """
        Nx, Ny = self.Nxy = self.Nx, self.Ny
        Lx, Ly = self.Lxy = np.asarray(self.Nxy) * self.dx
        dx, dy = np.divide(self.Lxy, self.Nxy)
        x = (np.arange(Nx) * dx - Lx / 2.0)[:, None]
        y = (np.arange(Ny) * dy - Ly / 2.0)[None, :]
        self.xy = (x, y)

        self.kxy = kx, ky = (
            2 * np.pi * np.fft.fftfreq(Nx, dx)[:, None],
            2 * np.pi * np.fft.fftfreq(Ny, dy)[None, :],
        )

        cooling_phase = 1 + self.cooling * 1j
        cooling_phase = cooling_phase / abs(cooling_phase)
        self._phase = -1j / self.hbar / cooling_phase

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
        set_param = getattr(
            self, "set_{}".format(param), lambda _v: setattr(self, param, _v)
        )
        set_param(value)
        self.init()

    def get(self, param):
        return getattr(self, param)

    def step(self, N, tracer_particles=None):
        dt = self.dt
        self.apply_expK(dt=dt, factor=0.5)
        self.t += dt / 2.0
        for n in range(N):
            if tracer_particles is not None:
                # Update tracer particle positions.
                # Maybe defer if too expensive
                tracer_particles.update_tracer_velocity(model=self)
                tracer_particles.update_tracer_pos(dt, model=self)

            density = self.get_density()
            if isinstance(self, FingerMixin) and self.t > 0:
                # Don't move finger potential while preparing the state.
                self._step_finger_potential(dt=dt, density=density)

            self.apply_expV(dt=dt, factor=1.0, density=density)
            self.apply_expK(dt=dt, factor=1.0)
            self.t += dt

        self.apply_expK(dt=dt, factor=-0.5)
        self.t -= dt / 2.0

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


@implementer(interfaces.IModel)
class BEC(GPEBase):
    """Single component BEC.

    Parameters
    ----------
    """

    params = dict(
        g=1.0,
        m=1.0,
        healing_length=10.0,
        cooling=0.01,
        cooling_steps=100,
        dt_t_scale=0.1,
        winding=10,
        cylinder=True,
        random_phase=False,
    )

    layout = w.VBox(
        [w.Checkbox(True, name="cylinder", description="Trap"), GPEBase.layout]
    )

    def __init__(self, opts):
        super().__init__(opts=opts)

        self.t = 0

        self.mu = self.hbar ** 2 / 2.0 / self.m / self.healing_length ** 2
        self.n0 = self.mu / self.g
        mu_min = max(0, min(self.mu, self.mu * (1 - self.finger_V0_mu)))
        self.c_s = np.sqrt(self.mu / self.m)
        self.c_min = np.sqrt(mu_min / self.m)
        # self.v_max = 1.1*self.c_min

        self.c_s = np.sqrt(self.mu / self.m)

        self.init()
        self.set_initial_data()
        self._N = self.get_density().sum()

    def init(self):
        super().init()
        kx, ky = self.kxy
        self.K = self.hbar ** 2 * (kx ** 2 + ky ** 2) / 2.0 / self.m
        self._V_trap = self.get_V_trap()
        self.dt = self.dt_t_scale * self.t_scale

    def set_initial_data(self):
        self.data = np.ones(self.Nxy, dtype=complex) * np.sqrt(self.n0)
        self._N = self.get_density().sum()

        # Cool a bit to remove transients.
        _phase, self._phase = self._phase, -1j / self.hbar
        self.t = -10000
        self.step(self.cooling_steps, tracer_particles=None)
        self.t = 0
        self._phase = _phase

        if self.cylinder:
            x, y = self.xy
            self.data *= np.exp(1j * self.winding * np.angle(x + 1j * y))
        if self.random_phase:
            phase = 2 * np.pi * np.random.random(self.Nxy)
            self.data *= np.exp(1j * phase)

    def get_density(self):
        y = self.data
        return (y.conj() * y).real

    def get_v(self, y=None):
        """Return the velocity field as a complex number."""
        if y is None:
            y = self.data
        yt = self.fft(y)
        kx, ky = self.kxy
        vx, vy = (self.ifft([kx * yt, ky * yt]) / y).real * self.hbar / self.m
        return vx + 1j * vy

    # End of interface
    ######################################################################
    def get_finger_v_max(self, density):
        """Return the maximum speed finger potential will move at."""
        # c_min = 1.0*np.sqrt(self.g*density.min()/self.m)
        c_mean = 1.0 * np.sqrt(self.g * density.mean() / self.m)
        return c_mean

    @property
    def t_scale(self):
        return self.hbar / self.K.max()

    def get_V_trap(self):
        """Return any static trapping potential."""
        if self.cylinder:
            x, y = self.xy
            Lx, Ly = self.Lxy
            r2_ = (2 * x / Lx) ** 2 + (2 * y / Ly) ** 2
            V_ = utils.mstep(r2_ - 0.8, 0.2)
            # V_ += -x / Lx - 0.2 * y / Ly
            return 100 * self.mu * V_
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
                    "exp(f*K)*y",
                    local_dict=dict(f=self._phase * dt * factor, K=self.K, y=yt),
                )
            )
        else:
            self.data[...] = self.ifft(
                np.exp(self._phase * dt * self.K * factor) * self.fft(y)
            )

    def apply_expV(self, dt, factor=1.0, density=None):
        y = self.data
        if density is None:
            density = self.get_density()
        n = density
        if numexpr:
            self.data[...] = numexpr.evaluate(
                "exp(f*(V+g*n-mu))*y*sqrt(_n)",
                local_dict=dict(
                    V=self.get_Vext(),
                    g=self.g,
                    n=n,
                    mu=self.mu,
                    _n=self._N / n.sum(),
                    f=self._phase * dt * factor,
                    y=y,
                ),
            )
        else:
            V = self.get_Vext() + self.g * n - self.mu
            self.data[...] = np.exp(self._phase * dt * V * factor) * y
            self.data *= np.sqrt(self._N / n.sum())

    def plot(self):
        from matplotlib import pyplot as plt

        n = self.get_density()
        x, y = self.xy
        plt.pcolormesh(x.ravel(), y.ravel(), n.T)
        plt.gca().set_aspect(1)
        plt.plot([self.pot_z.real], [self.pot_z.imag], "ro")
        plt.plot([self.z_finger.real], [self.z_finger.imag], "go")
        plt.title("{:.2f}".format(self.t))
        plt.colorbar()


@implementer(interfaces.IModel)
class BECVortices(BEC):
    params = dict(BEC.params, N_vortex=0.0, bump_N=1, bump_h=0.1, cylinder=True)

    layout = w.VBox(
        [
            w.FloatSlider(
                name="bump_h", min=0, max=0.5, step=0.01, description=r"bump size"
            ),
            w.FloatSlider(
                name="N_vortex",
                min=-100,
                max=100,
                step=0.1,
                description=r"Target number of vortices",
            ),
            w.IntSlider(name="bump_N", min=0, max=100, description=r"Number of bumps"),
            BEC.layout,
        ]
    )

    def init(self):
        self.Omega = 0
        super().init()
        A = 0.8 ** 2 * np.prod(self.Lxy)
        self.Omega = self.N_vortex * self.hbar * np.pi / self.m / A

    def get_V_trap(self):
        """Return any static trapping potential."""
        if self.cylinder:
            x, y = self.xy
            Lx, Ly = self.Lxy
            theta = np.angle(x + 1j * y)
            theta0 = self.Omega * self.t
            r2_ = ((2 * x / Lx) ** 2 + (2 * y / Ly) ** 2) * (
                1 - self.bump_h * np.cos(self.bump_N * (theta - theta0))
            )
            return 100 * self.mu * utils.mstep(r2_ - 0.8, 0.2)
        else:
            return 0

    def get_Vext(self):
        """Return the full external potential."""
        # Don't use cache
        return self.get_V_trap() + super().get_Vext()


@implementer(interfaces.IModel)
class BECFlow(BEC):
    """Model implementing variable flow in a BEC.

    This model provides a way of demonstrating Landau's critical
    velocity.  This velocity is implemented by shifting the momenta by
    kv = m*v/hbar
    """

    params = dict(BEC.params, cylinder=False, v_v_c=0)

    layout = w.VBox(
        [
            w.FloatSlider(name="v_v_c", min=-5, max=5, step=0.1, description=r"v/v_c"),
            BEC.layout,
        ]
    )

    def init(self):
        super().init()
        kx, ky = self.kxy
        self.K = self.hbar ** 2 * (kx ** 2 + kx * self.kv + ky ** 2) / 2.0 / self.m

    @property
    def kv(self):
        """Return the Bloch momentum"""
        v_c = math.sqrt(self.mu / self.m)
        v = self.v_v_c * v_c
        return self.m * v / self.hbar


@implementer(interfaces.IModel)
class BECVortexRing(BECFlow):
    """Model implementing variable flow in a BEC with imprinted vortex
    "rings"."""

    params = dict(BEC.params, cylinder=False, v_v_c=0, R=0.5)
    t = 0.0

    layout = w.VBox([BECFlow.layout])

    def init(self):
        super().init()
        kx, ky = self.kxy
        self.K = self.hbar ** 2 * (kx ** 2 + kx * self.kv + ky ** 2) / 2.0 / self.m

    @property
    def kv(self):
        """Return the Bloch momentum"""
        v_c = math.sqrt(self.mu / self.m)
        v = self.v_v_c * v_c
        return self.m * v / self.hbar

    def get_V_trap(self):
        """Return any static trapping potential."""
        x, y = self.xy
        Lx, Ly = self.Lxy
        r2_ = 0 * x + (2 * y / Ly) ** 2
        return 100 * self.mu * utils.mstep(r2_ - 0.8, 0.2)

    def set_initial_data(self):
        super().set_initial_data()
        x, y = self.xy
        Lx, Ly = self.Lxy
        z0 = x + 1j * (y - self.R * Ly / 2)
        z1 = x - 1j * (y + self.R * Ly / 2)
        self.data *= np.exp(1j * np.angle(z0 * z1))


@implementer(interfaces.IModel)
class BECSoliton(BECFlow):
    """Demonstrate the snaking instability of a dark soliton.

    Here we assume that the box is
    """

    params = dict(BECFlow.params, finger_V0_mu=0.1, v_c=0)

    layout = w.VBox(
        [
            w.FloatSlider(
                name="v_c", min=-0.99, max=0.99, step=0.01, description="v/c"
            ),
            BECFlow.layout,
        ]
    )

    def set(self, param, value):
        super().set(param, value)
        if param in set(["v_c", "Nx"]):
            self.set_initial_data()

    def set_initial_data(self):
        self.data = np.empty(self.Nxy, dtype=complex)

        x, y = self.xy
        v_c = self.v_c
        c_s = np.sqrt(self.g * self.n0 / self.m)
        length = self.hbar / self.m / c_s / np.sqrt(1 - v_c ** 2)

        Lx, Ly = self.Lxy

        # Error here...
        # theta_twist = np.arccos(1-2*v_c**2)
        # phase = np.exp(-1j*theta_twist*x/Lx)

        def psi(x):
            return np.sqrt(self.n0) * (
                1j * v_c + np.sqrt(1 - v_c ** 2) * np.tanh(x / length)
            )

        theta = np.angle(psi(Lx / 2) / psi(-Lx / 2))
        phase = np.exp(1j * theta * x / Lx)
        self.data[...] = psi(x) / phase


@implementer(interfaces.IModel)
class BECQuantumFriction(BEC):
    """Class with local quantum friction."""

    params = dict(BEC.params, Omega=0.0, Vc_cooling=0.0, Kc_cooling=0.0)

    layout = w.VBox(
        [
            w.FloatLogSlider(
                name="Vc_cooling",
                base=10,
                min=-10,
                max=1,
                step=0.2,
                description="Vc Cooling",
            ),
            BEC.layout,
        ]
    )

    def get_Kc(self):
        raise NotImplementedError()

    def apply_H(self, psi):
        """compute dy/dt=H psi"""
        psi_k = self.fft(psi)
        n = (psi.conj() * psi).real
        V = super().get_Vext() + self.g * n - self.mu
        Hpsi = self.ifft(self.K * psi_k) + V * psi
        Hpsi = Hpsi / np.sqrt(self._N)
        return Hpsi

    def get_Vc(self):
        """implement the Vc local cooling potential"""
        psi = self.data
        Hpsi = self.apply_H(psi)
        return self.Vc_cooling * 2 * (psi.conj() * Hpsi).imag

    def get_Vext(self):
        return super().get_Vext() + self.get_Vc()


@implementer(interfaces.IModel)
class BECBreather(BEC):
    """Demonstrate scale-invariant breathing solutions.

    Dalibard et al.: PRX 9, 021035 (2019)
    """

    params = dict(
        BECFlow.params,
        Nx=32 * 8,
        Ny=32 * 8,
        # a_HO=0.125,  # Fraction of Lx/2
        # R=0.5,  # Fraction of Lx/2
        a_HO=0.04,  # Fraction of Lx/2
        dt_t_scale=0.5,
        R=0.3,
        Nshape=3,
        cooling=1e-10,
        tracer_particles=0,
        finger_V0_mu=0.0,
    )

    layout = w.VBox([BEC.layout])

    def get_V_trap(self):
        """Return any static trapping potential."""
        x, y = self.xy
        r2 = x ** 2 + y ** 2
        Lx, Ly = self.Lxy
        a_HO = self.a_HO * Lx / 2.0
        mw2 = self.hbar ** 2 / a_HO ** 4 / self.m

        return mw2 * r2 / 2.0

    def _set(self, param, value):
        super().set(param, value)
        if param in set(["v_c", "Nx"]):
            self.set_initial_data()

    def set_initial_data(self):
        self.data = np.empty(self.Nxy, dtype=complex)
        x, y = self.xy
        Lx, Ly = self.Lxy
        z = x + 1j * y
        r = abs(z)
        theta = (np.angle(z) + np.pi) % (2 * np.pi / self.Nshape) - np.pi / self.Nshape
        n = np.where((r * np.exp(1j * theta)).real <= self.R * Lx / 2, self.n0, 0)
        self.data[...] = np.sqrt(n)


@implementer(interfaces.IModel)
class PersistentCurrents(BEC):
    """Model of a ring trap to explore dynamical generation of persistent currents.

    Persistent currents are one of the hallmarks of superfluidity.  If you can establish
    a flow around a ring, that flow will persist for long periods of time due to the
    lack of viscous dissipation.

    However, for the same reason, establishing a persistent current can be challenging.
    This demonstration explores various ways of generating currents in a ring trap.
    """

    params = dict(
        BEC.params,
        R1=0.5,  # Fraction of Lx/2
        R2=0.9,  # Fraction of Lx/2
        dR=0.1,  # Thickness of barrier in fraction of Lx/2
        cooling=1e-10,
        tracer_particles=100,
        finger_V0_mu=0.0,
        winding=0,  # Number of windings
    )

    layout = w.VBox([BEC.layout])

    def set_initial_data(self):
        """Set the initial state.

        Here we start with particles in the ground state with `winding` of circulation.
        """
        V = self.get_V_trap()
        n0 = np.where(V < self.mu, (self.mu - V) / self.g, 0)
        self.data = np.ones(self.Nxy, dtype=complex) * np.sqrt(n0)
        self._N = self.get_density().sum()

        # Cool a bit to remove transients.
        _phase, self._phase = self._phase, -1 / self.hbar
        self.t = -10000
        self.step(self.cooling_steps, tracer_particles=None)
        self.t = 0
        self._phase = _phase

        x, y = self.xy
        self.data *= np.exp(1j * self.winding * np.angle(x + 1j * y))

        if self.random_phase:
            phase = 2 * np.pi * np.random.random(self.Nxy)
            self.data *= np.exp(1j * phase)

    def get_V_trap(self):
        """Return any static trapping potential.

        Here we generate a ring potential.
        """
        x, y = self.xy
        Lx, Ly = self.Lxy
        r2_ = (2 * x / Lx) ** 2 + (2 * y / Ly) ** 2
        step = (
            1
            - utils.mstep(r2_ - self.R1 ** 2, self.dR ** 2)
            + utils.mstep(r2_ - self.R2 ** 2, self.dR ** 2)
        )
        return 100 * self.mu * step
