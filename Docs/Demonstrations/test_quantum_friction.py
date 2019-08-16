import numpy as np
from quantum_friction import StateBase
import pytest


@pytest.fixture(params=[(4,), (3, 4), (3, 4, 5)])
def Nxyz(request):
    yield request.param


class TestStateBase(object):
    def test_1(self, Nxyz):
        s = StateBase(Nxyz=Nxyz)
        r2 = sum(_x**2 for _x in s.xyz)
        psi = 1.0 + s.zero + 0.2*np.exp(-r2/2.0)*np.exp(1j*s.xyz[0])
        H = s.get_H(psi)

        # Check that dy is orthogonal to y so that the norm is
        # conserved (when subtract_mu is True).
        y = s.pack(psi)
        dy = s.compute_dy_dt(t=0, y=y, subtract_mu=True)
        dpsi = s.unpack(dy)
        assert np.allclose(s.dotc(dy, y), 0)

        # Check the get_H() returns the same Hamiltonian that
        # compute_dy_dt computes.
        H = s.get_H(psi)
        Hpsi = H.dot(psi.ravel()).reshape(s.Nxyz)
        mu = s.dotc(psi, Hpsi)/s.dotc(psi, psi)
        Hpsi -= mu*psi

        assert np.allclose(dpsi, s.beta_0*Hpsi/(1j*s.hbar))

        # Check that Hc implements imaginary time cooling.
        s.beta_0 = -1j
        dy = s.compute_dy_dt(t=0, y=y, subtract_mu=True)
        dpsi = s.unpack(dy)

        Hc_ = s.get_Hc(psi)
        assert np.allclose(Hc_.T.conj(), Hc_)
        Hc_psi = Hc_.dot(psi.ravel()).reshape(s.Nxyz)
        assert np.allclose(dpsi, Hc_psi/(1j*s.hbar))

        # Check that Vc is the diagonal of Hc
        Vc_ = s.get_Vc(psi).ravel()
        assert np.allclose(np.diag(Hc_), Vc_)

        # Check that Kc is the diagonal of Hc
        shape2 = tuple(Nxyz)*2
        shape2_ = (np.prod(Nxyz),)*2
        Hc = Hc_.reshape(shape2)
        Kc_ = s.get_Kc(psi).ravel()
        Hc_k = s.ifft(s.fft(Hc).T).T
        Hc_k = np.fft.ifftn(
            np.fft.fftn(Hc, axes=np.arange(s.dim)),
            axes=np.arange(s.dim, 2*s.dim))
        Hc_k_ = Hc_k.reshape(shape2_)
        assert np.allclose(Hc_k_.T.conj(), Hc_k_)
        assert np.allclose(np.diag(Hc_k_), Kc_)
