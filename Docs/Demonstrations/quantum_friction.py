import numpy as np
from scipy.integrate import solve_ivp
from matplotlib import pyplot as plt


class StateBase(object):
    g = hbar = m = w = 1.0

    def __init__(self, Nxyz=(256,), dx=0.1,
                 beta_0=1.0, beta_V=0.0, beta_K=0.0,
                 dt_Emax=1.0):
        """
        Arguments
        ---------
        Nxyz : (float,)
           Specifies the basis size and dimension.
        dx : float
           Lattice spacing.
        dt_Emax : float
           Integrator time-step in terms of Emax.
        beta_0 : complex
           Portion of the original Hamiltonian H to include in evolution.
           Make -1j for imaginary time cooling.
        beta_V : float
           Portion of the position cooling potential V_c.
        beta_K : float
            Portion of the momentum cooling potential K_c.
        """
        self.beta_0 = beta_0
        self.beta_V = beta_V
        self.beta_K = beta_K        
        self.Nxyz = np.asarray(Nxyz)
        self.dx = dx
        self.Lxyz = dx*self.Nxyz
        self.xyz = np.meshgrid(
            *[np.arange(_N)*dx - _N*dx/2.0
              for _N in Nxyz],
            indexing='ij', sparse=True)
        self.kxyz = np.meshgrid(
            *[2*np.pi * np.fft.fftfreq(_N, dx)
              for _N in Nxyz],
            indexing='ij', sparse=True)

        # Pre-compute the kinetic energy
        self._K2 = sum((self.hbar*_k)**2/2/self.m for _k in self.kxyz)
        self.Emax = self._K2.max()
        self.dt = dt_Emax * self.hbar/self.Emax
        self.zero = 0j*sum(self.xyz)

    @property
    def metric(self):
        return self.dx**self.dim

    ######################################################################
    # Members that subclasses might wish to override.
    def get_Vext(self):
        """Return the external potential.

        This version is a harmonic oscillator.
        """
        r2 = sum(_x**2 for _x in self.xyz)
        return self.m * self.w**2 * r2 / 2.0

    def apply_Hc(self, psi, psi0=None):
        """Apply the cooling Hamiltonian."""
        if psi0 is None:
            psi0 = psi
        H_psi = self.apply_H(psi, psi0=psi0)
        Vc_psi = self.get_Vc(psi0)*psi
        Kc_psi = self.ifft(self.get_Kc(psi0)*self.fft(psi))
        return (self.beta_0 * H_psi
                + self.beta_V * Vc_psi
                + self.beta_K * Kc_psi)

    def get_Vc(self, psi):
        n = self.get_density(psi)
        N_tot = n.sum() * self.metric
        Hpsi = self.apply_H(psi)
        Vc = 2*(psi.conj()*Hpsi).imag / N_tot
        return Vc/n
        Vc0 = abs(Vc).max()
        return 2*Vc/(abs(Vc) + 0.0001*Vc0)*Vc0
        return np.sign(Vc)

    def get_Kc(self, psi):
        n = self.get_density(psi)
        N_tot = n.sum() * self.metric
        psi_k = np.fft.fft(psi) * self.metric
        Vol = np.prod(self.Lxyz)
        Hpsi = self.apply_H(psi)
        Vpsi_k = np.fft.fft(Hpsi) * self.metric
        Kc = 2*(psi_k.conj()*Vpsi_k).imag / N_tot / Vol
        return Kc

    ######################################################################
    # These members should be okay, but might need to be changed if a
    # different functional is implemented
    def get_V(self, psi):
        """Return the complete potential including the mean-field."""
        return self.g * self.get_density(psi) + self.get_Vext()

    ######################################################################
    # Utility functions and helpers
    @property
    def dim(self):
        return len(self.Nxyz)

    # The following functions pack and unpack real arguments for the ODE
    # solver into wavefunctions
    def pack(self, psi):
        return np.ascontiguousarray(psi).view(dtype=float).ravel()

    def unpack(self, y):
        return np.ascontiguousarray(y).view(dtype=complex).reshape(self.Nxyz)

    def fft(self, psi):
        return np.fft.fftn(psi, axes=np.arange(self.dim))

    def ifft(self, psi_k):
        return np.fft.ifftn(psi_k, axes=np.arange(self.dim))

    def dotc(self, a, b):
        """Return dot(a.conj(), b) allowing for dim > 1."""
        return np.dot(a.conj().ravel(), b.ravel())

    def get_density(self, psi):
        """Return the density."""
        return abs(psi)**2

    def apply_H(self, psi, psi0=None):
        if psi0 is None:
            psi0 = psi
        psi_k = self.fft(psi)
        Kpsi = self.ifft(self._K2*psi_k)
        Vpsi = self.get_V(psi0)*psi
        return Kpsi + Vpsi

    ######################################################################
    # These functions are used to solve the ODE.
    def compute_dy_dt(self, t, y, subtract_mu=True):
        """Return dy/dt for ODE integration."""
        psi = self.unpack(y=y)
        Hpsi = self.apply_Hc(psi)
        if subtract_mu:
            Hpsi -= self.dotc(psi, Hpsi)/self.dotc(psi, psi)*psi
        return self.pack(Hpsi/(1j*self.hbar))

    def solve(self, psi0, T, **kw):
        y0 = self.pack(psi0)
        res = solve_ivp(fun=self.compute_dy_dt,
                        t_span=(0, T), y0=y0, **kw)
        if not res.success:
            raise Exception(res.message)
        return(res.t, list(map(self.unpack, res.y.T)))

    ######################################################################
    # These functions are for reporting.
    def get_E_N(self, psi):
        """Return the energy and particle number `(E,N)`."""
        K = self.dotc(psi, self.ifft(self._K2*self.fft(psi)))
        n = self.get_density(psi)
        V = (self.g*n**2/2 + self.get_Vext()*n).sum()
        E = (K + V).real * self.metric
        N = n.sum() * self.metric
        return E, N

    ######################################################################
    # Matrix functions: These return full matrices for inspection.
    def get_H(self, psi):
        """Return the Hamiltonian in position space."""
        size = np.prod(self.Nxyz)
        shape2 = tuple(self.Nxyz)*2
        shape2_ = (size,)*2

        U = self.fft(np.eye(size).reshape(shape2))
        U_ = U.reshape(shape2_)
        K = np.linalg.solve(U_,
                            self._K2.ravel()[:, None]*U_).reshape(shape2)
        V = np.diag(self.get_V(psi).reshape(size)).reshape(shape2)
        H_ = (K + V).reshape(shape2_)
        Hpsi = H_.dot(psi.ravel()).reshape(self.Nxyz)
        assert np.allclose(Hpsi, self.apply_H(psi))
        return H_

    def get_Hc(self, psi):
        """Return the full cooling Hamiltonian in position space."""
        size = np.prod(self.Nxyz)

        Hpsi = self.apply_H(psi)
        Hc_ = (1j*psi.reshape(size)[:, None]
               * Hpsi.conj().reshape(size)[None, :])
        Hc_ += Hc_.conj().T
        n = self.get_density(psi=psi)
        Hc_ /= (n.sum() * self.metric)
        return Hc_

    def plot(self, psi, **kw):
        if self.dim == 1:
            x = self.xyz[0].ravel()
            plt.plot(x, abs(psi)**2, **kw)
        elif self.dim == 2:
            from mmfutils import plot as mmfplt
            x, y = self.xyz
            mmfplt.imcontourf(x, y, self.get_density(psi))
            plt.colorbar()
        E, N = self.get_E_N(psi)
        plt.title(f"E={E:.4f}, N={N:.4f}")
        return plt.gcf()
