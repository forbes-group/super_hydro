import numpy as np
import numpy.fft


class State(object):
    """
    
    Parameters
    ----------
    V0 : float
       Potential strength
    healing_length

    """
    def __init__(self, Nxy=(32, 32), Lxy=(10., 10.),
                 healing_length=1.0, r0=1.0, V0=0.1,
                 cooling_phase=1.0+0.01j,
                 cooling_steps=100, disp=None,
                 test_finger=False):
        g = hbar = m = 1.0
        self.g = g
        self.hbar = hbar
        self.m = m
        self.r0 = r0
        self.V0 = V0
        self.disp = disp
        self.Nxy = Nx, Ny = Nxy
        self.Lxy = Lx, Ly = Lxy
        self.healing_length = healing_length
        dx, dy = np.divide(Lxy, Nxy)
        x = (np.arange(Nx)*dx - Lx/2.0)[:, None]
        y = (np.arange(Ny)*dy - Ly/2.0)[None, :]
        self.xy = (x, y)

        kx = 2*np.pi * np.fft.fftfreq(Nx, dx)[:, None]
        ky = 2*np.pi * np.fft.fftfreq(Ny, dy)[None, :]
        self.kxy = (kx, ky)
        
        if disp is None:
            self.K = hbar**2*(kx**2 + ky**2)/2.0/m
        if disp is 'SOC':
            _Kx = get_SOC_disp_x(self, k=self.kxy[0],d=0,
                                 delta=0.2, omega=1.0)
            self.K = _Kx + hbar**2*(ky**2)/2.0/m
        
        self.n0 = n0 = hbar**2/2.0/healing_length**2/g
        self.mu = g*n0
        mu_min = max(0, min(self.mu, self.mu - self.V0))
        self.c_s = np.sqrt(self.mu/self.m)
        self.c_min = np.sqrt(mu_min/self.m)
        self.v_max = 4*self.c_s
        self.data = np.ones(Nxy, dtype=complex) * np.sqrt(n0)
        self._N = self.get_density().sum()

        self.test_finger = test_finger
        self.z_finger = 0 + 0j
        self.pot_k_m = 1.0
        self.pot_z = 0 + 0j
        self.pot_v = 0 + 0j
        self.pot_damp = 4.0

        self.t = -10000

        self._phase = -1.0/self.hbar
        self.step(cooling_steps, dt=0.05)
        self.t = 0
        self._phase = -1j/self.hbar/cooling_phase

    def get_density(self):
        return abs(self.data)**2

    def set_xy0(self, x0, y0):
        self.z_finger = x0 + 1j*y0

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
        return self.V0*np.exp(-r2/2.0/self.r0**2)
    
    def get_SOC_disp_x(self, k, d=0, delta=0.2, omega=1.0):
        #set k_r to be a little bit bigger than k_healing
        #must check that both are much larger than 2pi/L
        k_r = 2.1 / self.healing_length
        E_r = (self.hbar * k_r)**2 / 2. / self.m
        
        ks = k / k_r
        D = np.sqrt((ks - delta)**2 + omega**2)
        if d == 0:
            res = (ks**2 + 1)/2.0 - D
        elif d == 1:
            res = ks - (ks - delta) / D
        elif d == 2:
            #print omega**2 /D**3
            res = 1.0 - omega**2 / D**3
        else:
            raise NotImplementedError("Only d=0, 1, or 2 supported. (got d={})"
                                      .format(d))
        return np.asarray(res) * E_r
    
    def apply_expK(self, dt, factor=1.0):
        y = self.data
        self.data[...] = self.ifft(np.exp(self._phase*dt*self.K*factor)
                                   * self.fft(y))

    def apply_expV(self, dt, factor=1.0):
        y = self.data
        n = self.get_density()
        V = self.get_Vext() + self.g*n - self.mu
        self.data[...] = np.exp(self._phase*dt*V*factor) * y
        self.data *= np.sqrt(self._N/n.sum())

    def mod(self, z):
        """Make sure the point z lies in the box."""
        return complex(*[(_x + _L/2) % (_L) - _L/2
                         for _x, _L in zip((z.real, z.imag), self.Lxy)])

    def step(self, N, dt):
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
