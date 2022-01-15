"""
Helpers
=======

Some tools to make writing models easier.
"""
import argparse
import collections.abc
import inspect

import numpy as np

from .. import widgets as w

__all__ = ["ModelBase", "FingerMixin"]


class ModelBase(object):
    """Helper class for models."""

    params_doc = {}

    def __init__(self, opts):
        """Default constructor simply sets attributes defined in params."""
        self._initializing = True

        # Sometimes a user might pass in a dictionary instead of a
        # Namespace for opts:
        if isinstance(opts, collections.abc.Mapping):
            opts = argparse.Namespace(**opts)

        # Collect all parameters from base classes
        params = {}
        mro = type(self).mro()
        for kls in reversed(mro):
            params.update(getattr(kls, "params", {}))

        # Update any of the parameters from opts if provided.
        self.params = {_key: getattr(opts, _key, params[_key]) for _key in params}

        # Set the attributes, allowing customized setters to be used.
        for _key in self.params:
            setattr(self, _key, self.params[_key])

        self._initializing = False

    def init(self):
        """Overload this to provide any initialization.

        Note: your class should call init() when it is ready.
        """


class FingerMixin:
    """Support for the location of a user's finger and an associated potential.

    The actual potential is connected to the finger with a spring, and
    limited to move at maximum speed `get_finger_v_max()`.

    Parameters
    ----------
    finger_k_m : float
       Spring constant of the finger-potential spring.
    finger_damp : float
       Damping of the finger-potential spring.
    test_finger : bool
       If True, then artificially move the finger to test the behaviour.
    finger_x, finger_y : float
       Relative position of finger on the display.  Note: finger_y
       goes from top to bottom.
    finger_V0_mu : float
       Potential strength in units of mu healing_length:
    finger_r0 : float
       Size of the finger potential
    """

    pot_v = 0 + 0j

    params = dict(
        finger_x=0.5,
        finger_y=0.5,
        finger_Vxy=(0.5, 0.5),
        finger_k_m=10.0,
        finger_damp=4.0,
        finger_r0=10.0,
        finger_V0_mu=0.5,
        test_finger=False,
    )

    # Broken!  Fix the layout of the sliders.
    layout = w.VBox(
        [
            w.FloatSlider(
                name="finger_V0_mu", min=-2, max=2, step=0.1, description="V0/mu"
            ),
            w.FloatSlider(name="finger_x", min=0, max=1, step=0.01, readout=False),
            w.HBox(
                [
                    w.density,
                    w.FloatSlider(
                        name="finger_y",
                        min=0,
                        max=1,
                        step=0.01,
                        readout=False,
                        orientation="vertical",
                    ),
                ]
            ),
        ]
    )

    def init(self):
        self.pot_v = 0 + 0j

    @property
    def z_finger(self):
        if self.test_finger:
            if self.t >= 0:
                return 3.0 * np.exp(1j * self.t / 5)
            else:
                return 3.0
        else:
            Lx, Ly = self.Lxy
            x0 = Lx * (self.finger_x - 0.5)
            y0 = Ly * (self.finger_y - 0.5)
            return x0 + 1j * y0

    @z_finger.setter
    def z_finger(self, z_finger):
        Lx, Ly = self.Lxy
        self.finger_x = z_finger.real / Lx + 0.5
        self.finger_y = z_finger.imag / Ly - 0.5

    @property
    def pot_z(self):
        Lx, Ly = self.Lxy
        x = Lx * (self.finger_Vxy[0] - 0.5)
        y = Ly * (self.finger_Vxy[1] - 0.5)
        pot_z = x + 1j * y
        return pot_z

    @pot_z.setter
    def pot_z(self, pot_z):
        Lx, Ly = self.Lxy
        self.finger_Vxy = (
            pot_z.real / Lx + 0.5,
            pot_z.imag / Ly + 0.5,
        )

    def get_Vext(self):
        """Return the full external potential."""
        x, y = self.xy
        z0 = self.pot_z
        x0, y0 = z0.real, z0.imag
        Lx, Ly = self.Lxy

        # Wrap displaced x and y in periodic box.
        x = (x - x0 + Lx / 2) % Lx - Lx / 2
        y = (y - y0 + Ly / 2) % Ly - Ly / 2
        r2 = x ** 2 + y ** 2
        V0 = self.finger_V0_mu * self.mu
        return V0 * np.exp(-r2 / 2.0 / self.finger_r0 ** 2)

    def get_finger_v_max(self, density):
        """Return the maximum speed finger potential will move at."""
        return np.inf

    def _step_finger_potential(self, dt, density=None):
        pot_z = self.pot_z
        pot_z += dt * self.pot_v
        pot_a = -self.finger_k_m * (pot_z - self.z_finger)
        pot_a += -self.finger_damp * self.pot_v
        self.pot_v += dt * pot_a
        v_max = self.get_finger_v_max(density=density)
        if abs(self.pot_v) > v_max:
            self.pot_v *= v_max / abs(self.pot_v)
        self.pot_z = self.mod(pot_z)

    def mod(self, z):
        """Make sure the point z lies in the box."""
        return complex(
            *[
                (_x + _L / 2) % (_L) - _L / 2
                for _x, _L in zip((z.real, z.imag), self.Lxy)
            ]
        )

    ######################################################################
    # Required by subclasses
    Lxy = NotImplemented
