import numpy as np
import numpy.fft


class State(object):
    def __init__(self, Nxy=(32, 32), Lxy=(10., 10.), 
                 healing_length=1.0, r0=1.0, V0=-1.0, 
                 cooling_phase=1.0+0.001j):
        g = hbar = m = 1.0
        self.g = g
        self.hbar = hbar
        self.m = m
        self.r0 = r0
        self.V0 = V0
        Nx, Ny = Nxy
        Lx, Ly = Lxy
        dxy = dx, dy = np.divide(Lxy, Nxy)
        x = (np.arange(Nx)*dx - Lx/2.0)[:, None]
        y = (np.arange(Ny)*dy - Ly/2.0)[None, :]
        self.xy = (x, y)
        
        kx = 2*np.pi * np.fft.fftfreq(Nx, dx)[:, None]
        ky = 2*np.pi * np.fft.fftfreq(Ny, dy)[None, :]
        self.kxy = (kx, ky)
        
        self.K = hbar**2*(kx**2 + ky**2)/2.0/m
        
        n0 = hbar**2/2.0/healing_length**2/g
        self.mu = g*n0
        self.data = np.ones(Nxy, dtype=complex) * np.sqrt(n0)
        self._N = self.get_density().sum()
        
        self.x0 = self.y0 = 0
        
        self._phase = -1j/self.hbar/cooling_phase

    def get_density(self):
        return abs(self.data)**2
    
    def set_xy0(self, x0, y0):
        self.x0 = x0
        self.y0 = y0
        
    def fft(self, y):
        return np.fft.fftn(y)

    def ifft(self, y):
        return np.fft.ifftn(y)
    
    def get_Vext(self):
        x, y = self.xy
        r2 = (x - self.x0)**2 + (y - self.y0)**2
        return self.V0*np.exp(-r2/2.0/self.r0**2)
    
    def apply_expK(self, dt, factor=1.0):
        y = self.data
        self.data[...] = self.ifft(np.exp(self._phase*dt*self.K*factor) * self.fft(y))
    
    def apply_expV(self, dt, factor=1.0):
        y = self.data
        n = self.get_density()
        V = self.get_Vext() + self.g*n - self.mu
        self.data[...] = np.exp(self._phase*dt*V*factor) * y
        self.data *= np.sqrt(self._N/n.sum())
    
    def step(self, N, dt):
        self.apply_expK(dt=dt, factor=0.5)
        for n in range(N):
            self.apply_expV(dt=dt, factor=1.0)
            self.apply_expK(dt=dt, factor=1.0)
        self.apply_expK(dt=dt, factor=-0.5)
        
    def plot(self):
        from matplotlib import pyplot as plt
        n = self.get_density()
        x, y = self.xy
        plt.pcolormesh(x.ravel(), y.ravel(), n)
        plt.colorbar()        