#import attr

import numpy as np
#import numpy.fft
from pycuda.compiler import SourceModule
import reikna.cluda.api
from reikna import cluda
from reikna.fft import FFT
from pycuda.tools import make_default_context
import pycuda.gpuarray as gpuarray    
from .gpe import State 

class StateGPU(State):
    #def __init__(self, Nxy=(32, 32), dx=1.0,
    #             healing_length=10.0, r0=10.0, V0_mu=0.5,
    #              cooling_phase=1.0+0.01j,
    #             cooling_steps=100, dt_t_scale=0.1,
    #             soc=False,
    #             soc_d=0.05, soc_w=0.5,
    #             test_finger=True): 
    def __init__(self, **kw): 
        kw.update(test_finger=True)    
        State.__init__(self,cooling_steps=0, **kw)
        api = cluda.get_api('cuda')
        thread = api.Thread.create()
        state_in = self.data
        GPU_container = thread.empty_like(state_in)#allocate space for data
        self.gpu_data = thread.to_device(state_in)   #put the data in the allocated space
        self._the_fft_doer = FFT(self.gpu_data).compile(thread)
        self.dt = 0.1

    #pycuda.fft somehow
    @property
    def v_max(self):
        return np.inf
     
    def get_density(self):
        return abs(self.data)**2
 
    def fft(self, y):
        #return np.fft.fftn(y)
        return self._the_fft_doer(y)
    
    def ifft(self, y):
        #return np.fft.ifftn(y)
        return self_the_fft_doer(y,inverse=True)
    
    #ultimately to be put on the gpu
    def get_Vext(self):
        x, y = self.xy
        x0, y0 = self.pot_z.real, self.pot_z.imag
        Lx, Ly = self.Lxy

        # Wrap displaced x and y in periodic box.
        x = (x - x0 + Lx/2) % Lx - Lx/2
        y = (y - y0 + Ly/2) % Ly - Ly/2
        r2 = x**2 + y**2
        return self.V0_mu*self.mu * np.exp(-r2/2.0/self.r0**2)

    def apply_expK(self, dt, factor):
        #y = self.data
        y = self.gpu_data
        #this method needs to be done on the gpu
        #data->gpu, ifft data, apply thing to data, fft data->cpu
        #self.data[...] = self.ifft(np.exp(self._phase*dt*self.K*factor)* self.fft(y))
        self.gpu_data[...] = self._the_fft_doer(np.exp(self._phase*dt*self.K*factor)*self._the_fft_doer(y),inverse=True)
        
    def apply_expV(self, dt, factor=1.0):
        y = self.gpu_data
        n = self.get_density()
        V = self.get_Vext() + self.g*n - self.mu
        #this method needs to be done on the gpu
        self.gpu_data[...] = np.exp(self._phase*dt*V*factor) * y
        self.gpu_data *= np.sqrt(self._N/n.sum())
