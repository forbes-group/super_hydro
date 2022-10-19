---
jupytext:
  formats: ipynb,md:myst
  notebook_metadata_filter: metadata
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.13.8
kernelspec:
  display_name: Python 3 (super_hydro)
  language: python
  name: super_hydro
---

```{code-cell} ipython3
import mmf_setup;mmf_setup.nbinit(quiet=True)
%load_ext autoreload

%matplotlib inline
import numpy as np, matplotlib.pyplot as plt
from matplotlib import cm
from super_hydro.physics.testing import HO

%autoreload
from super_hydro.physics.tracer_particles import TracerParticlesBase


class Simulation:
    Nxy = (1280, 720)  # 720p resolution
    Nz = 500  # Number of tracer particles
    t = 0
    dt = 0.1
    seed = 1
    skip = 8  # Skip factor for getting vs

    def __init__(self, **kw):
        for _k in kw:
            if not hasattr(self, _k):
                raise ValueError(f"Unknown parameter {_k}")
            setattr(self, _k, kw[_k])
        self.init()

    def init(self):
        self.ho = ho = HO(Nxy=self.Nxy)
        self.psi = ho.get_psi(t=self.t)
        self.tp = TracerParticlesBase(
            xy=self.ho.xy,
            psi=self.psi,
            N=self.Nz,
            hbar_m=ho.hbar / ho.m,
            seed=self.seed,
            skip=self.skip,
        )
        self.n_max = (abs(self.psi) ** 2).max()

    def evolve(self, steps=1):
        for n in range(steps):
            self.t += self.dt
            self.psi = self.ho.get_psi(t=self.t)
            self.tp.evolve(dt=self.dt, psi=self.psi)

    def n_to_rgba(self, n):
        """Convert the density n to RGBA data"""
        # Transpose so we can use faster canvas.indexing = "xy"
        return cm.viridis(n.T / self.n_max, bytes=True)

import IPython
import time
from super_hydro.contexts import FPS
from traitlets import All

from ipywidgets import Label, VBox, Output
import ipywidgets as widgets
from ipywidgets import Label, VBox, IntSlider
from ipycanvas import Canvas, hold_canvas
from super_hydro.contexts import FPS

sim = Simulation(Nxy=(2*256, 2*128), dt=0.02, Nz=500, skip=2)
canvas = Canvas(width=sim.psi.shape[0], height=sim.psi.shape[1])
canvas.layout.width = '100%'
canvas.layout.height = 'auto'
    
slider = widgets.IntSlider()

msg = Label()
display(VBox([canvas, slider, msg]))

def do_update(fps):
    global sim, canvas, msg, slider
    sim.evolve(2)
    n = abs(sim.psi)**2
    with hold_canvas(canvas):
        canvas.put_image_data(sim.n_to_rgba(n)[..., :3], 0, 0)  # Discard alpha
        ix, iy, vs = sim.tp.inds
        rect = False
        if rect:
            canvas.fill_rects(ix, iy, 1)
        else:
            dth = 0.2
            r0 = 0
            r1 = 5.0
            v0 = r1/sim.dt
            th = np.angle(vs)
            r = r0 + r1 * np.abs(vs)/v0
            xi = 10*np.abs(vs)/v0
            # dth = pi if v = 0
            # dth = 0.2 if v = infty
            dth = 0.2/r + (np.pi-0.2/r)/(1+xi**2)
            canvas.fill_style = "black"
            canvas.global_alpha = 0.5
            canvas.fill_arcs(ix, iy, r, th-np.pi-dth, th-np.pi+dth)

            msg.value = f"{fps=}, {slider.value=}"
```

```{code-cell} ipython3
# No interactions, but fast
with FPS(frames=2000, timeout=200) as fps:
    for frame in fps:
        do_update(fps=fps)
```

```{code-cell} ipython3
# Interactions: works with original ipycanvas code.  Slower.
with FPS(frames=2000, timeout=200) as fps:
    kernel = IPython.get_ipython().kernel
    for frame in fps:
        do_update(fps=fps)
        for n in range(int(np.ceil(1/max(1, fps.fps)/kernel._poll_interval))):
            kernel.do_one_iteration()
```

```{code-cell} ipython3
# Interactions with callback.  Needs my ipycanvas
canvas._use_requestAnimationFrame = False
canvas._use_requestAnimationFrame = True
with FPS(frames=2000, timeout=200) as fps:
    def image_updated(fps=fps):
        if fps:
            do_update(fps=fps)
            fps.frame += 1
        else:
            canvas.on_image_updated(image_updated, remove=True)
    canvas.on_image_updated(image_updated)
    do_update(fps=fps)
    kernel = IPython.get_ipython().kernel
    while fps:
        kernel.do_one_iteration()
```

```{code-cell} ipython3
import mmf_setup;mmf_setup.nbinit(quiet=True)
%load_ext autoreload
```

```{code-cell} ipython3
from ipycanvas import Canvas

canvas = Canvas(width=200, height=200)
canvas
```

```{code-cell} ipython3
%%javascript
// This removes the scroll bars so that they do not interfere with the output
IPython.OutputArea.prototype._should_scroll = function(lines) { return false; }
```

# Tracer Particles

+++

Although dynamical simulations allow one to see some aspects of the fluid flow, there are many cases where the velocity of fluid is not clearly depicted.  A single vortex is a good example where there is persistent flow, but the density is constant in time.

Here we demonstrate a technique for visualizing flow by placing a bunch of "tracer particles" in the system and following their motion.  These particles respond to the local flow velocity $\vect{v}$ which can be deduced from the particle number current $\vect{j} = n\vect{v}$:

\begin{gather*}
  \vect{j}(\vect{x}, t)
  = \frac{n(\vect{x}, t)\vect{p}(\vect{x}, t)}{m} 
  = \psi^\dagger(\vect{x}, t)
     \frac{-\I\hbar\vect{\nabla}}{2m}
     \psi(\vect{x}, t)
     + \text{h.c.}
  = \Im\left(
    \psi^\dagger(\vect{x}, t)
     \frac{\hbar\vect{\nabla}}{m}
     \psi(\vect{x}, t)
   \right)
\end{gather*}

where $\text{h.c.}$ is the complex conjugate of the first term which effectively pulls out the imaginary part $\Im$ of the gadient.

Using the Madelung transformation, it becomes clear that the velocity is related to the gradient of the phase:

\begin{align*}
  \psi(\vect{x}, t) &= \sqrt{n(\vect{x}, t)}e^{\I\phi(\vect{x}, t)},\\
  \vect{\nabla}\psi(\vect{x}, t) 
  &= e^{\I\phi(\vect{x}, t)}\Bigl(
    \vect{\nabla}\sqrt{n(\vect{x}, t)}
  + \sqrt{n(\vect{x}, t)}\I\vect{\nabla}\phi(\vect{x}, t)
  \Bigr)\\
  \psi^\dagger(\vect{x}, t)\vect{\nabla}\psi(\vect{x}, t) 
  &= \sqrt{n(\vect{x}, t)}
    \vect{\nabla}\sqrt{n(\vect{x}, t)}
  + n(\vect{x}, t)\I\vect{\nabla}\phi(\vect{x}, t)\\
  \Im\Bigl(\psi^\dagger(\vect{x}, t)\vect{\nabla}\psi(\vect{x}, t) \Bigr)
  & = n(\vect{x}, t)\vect{\nabla}\phi(\vect{x}, t) = \frac{m}{\hbar}\vect{j}(\vect{x}, t)\\
  \vect{v} = \frac{\vect{j}(\vect{x}, t)}{n(\vect{x}, t)} 
  &= \frac{\hbar}{m}\vect{\nabla}\phi(\vect{x}, t).
\end{align*}

+++

To evolve the tracer particles, however, we need to know the velocity at a few arbitrary points, not everywhere on the lattice.

```{code-cell} ipython3
%matplotlib inline
%autoreload
from mmfutils.plot import imcontourf
import numpy as np, matplotlib.pyplot as plt
from super_hydro.physics.testing import HO

%autoreload
import super_hydro.physics.tracer_particles
from super_hydro.physics.tracer_particles import TracerParticlesBase
import warnings

warnings.simplefilter("error", np.VisibleDeprecationWarning)

ho = HO()
x, y = ho.xy
kx, ky = ho.kxy

tp = TracerParticlesBase(xy=(x, y), psi=ho.get_psi(t=0), N=500)
psi = ho.get_psi(t=0)
#n, v = tp.get_n_v(psi=psi, kxy=(kx, ky), hbar_m=ho.hbar / ho.m)
n, v = tp.get_n_v(psi=psi)
zs, vs = tp.init(n=n, v=v)[:2]
zvs = np.vstack([zs, zs + 0.2 * vs / abs(vs)])

fig, axs = plt.subplots(1, 2, figsize=(15, 5), gridspec_kw=dict(width_ratios=[1, 1.25]))
plt.sca(axs[0])
imcontourf(x, y, n, aspect=1)
plt.plot(zs.real, zs.imag, ".k", alpha=0.2)
plt.plot(zvs.real, zvs.imag, "-k", alpha=0.2)
plt.sca(axs[1])
imcontourf(x, y, abs(v), vmax=11, aspect=1)
plt.colorbar()
# for z, v in zip(zs, vs):
#    plt.arrow(z.real, z.imag, 10*v.real, 10*v.imag)
```

## Optimization Case Study

+++

To update the tracer particles, we need to compute their velocity from the wavefunction $\psi(x, y)$ using the previous formula.  Timing our `get_n_v()` routine, however, shows that it is far too slow (at least at 720p resolutions) to obtain decent frame-rates:

```{code-cell} ipython3
from super_hydro.contexts import FPS
args = dict(kxy=(kx, ky), hbar_m=ho.hbar / ho.m)
with FPS(frames=5) as fps:
    for frame in fps:
        psi = ho.get_psi(t=frame)
        %time n, v = tp.get_n_v(psi=psi, **args)
print(f"{fps=}")
```

While the FFT is very efficient, the whole operation is quite slow becuase we are computing the velocity at every point on the lattice.  The situation is even worse, because, we still need to interpolate these velocities to the location of the tracer particle, which may not be on lattice sites once they evolve.

Can we do better?  We might be able to optimize using the PyFFTW:

```{code-cell} ipython3
from mmfutils.performance import fft
args['fft'] = fft.get_fftn_pyfftw(psi)
args['ifft'] = fft.get_ifftn_pyfftw(psi)
with FPS(frames=5) as fps:
    for frame in fps:
        psi = ho.get_psi(t=frame)
        %time n, v = tp.get_n_v(psi=psi, **args)
print(f"{fps=}")
```

Still not sufficient.  Thinking a bit, however, since we actually only need the velocity at $N_z$ distinct locations where we have the $N_z$ tracer particles. Instead of doing the full FFT, we can simply evaluate the wavefunction in the Fourier basis.  For example, consider the wavefunction:

$$
  \psi(x, y) = \sum_{k_x,k_y} \underbrace{\overbrace{\frac{e^{\I (x+x_0) k_x}}{N_x}}^{Q_x}\overbrace{\frac{e^{\I (y+y_0) k_y}}{N_y}}^{Q_y}}_{Q}\tilde{\psi}_{k_x, k_y}
  \propto \sum_{\vect{k}} e^{\I (x k_x + y k_y)}\tilde{\psi}_{\vect{k}}.
$$

(The first form includes normalization and phase factors in the numerical version of the inverse FFT implemented in NumPy and PyFFTW.)

*Note: We store the tracer particle positions in an array `zs` of complex numbers $z = x+\I y$ for each tracer particle.  Hence our notation that we have $N_z$ tracers.*

```{code-cell} ipython3
t = 0
ix, iy = 1+ho.Nxy[0]//2, 2+ho.Nxy[1]//2
x_, y_ = map(np.ravel, ho.xy)
kx_, ky_ = map(np.ravel, ho.kxy)
zs_ = np.ravel([x_[ix] + 1j*y_[iy]])
psi = ho.get_psi(t=t)
x0, y0 = x_[0], y_[0]
psi_t = np.fft.fftn(psi)

# Shape = (nz, nx, ny)
zs_ = zs_[:, None, None]
kx_ = kx_[None, :, None]
ky_ = ky_[None, None, :]
Qx_ = np.exp(1j*kx_ * (zs_.real + x_[0])) / ho.Nxy[0]
Qy_ = np.exp(1j * ky_ * (zs_.imag + y_[0])) / ho.Nxy[1]
Q_ = Qx_*Qy_

%time psi_ = np.einsum("zxy,xy->z", Q_, psi_t)
assert np.allclose(psi_, psi[ix, iy])
Q_.shape
```

Great!  This is fairly fast, and works.  However, if you try it with a list of $N_z=500$ tracer particles... your computer may crash.  That is because the intermediate array `Q_` has shape $(N_z, N_x, N_y)$ which, for 720p video resolutions, is 6.87GB per array.

```{code-cell} ipython3
"{:.2f}GB".format(
    (500 * 1280 * 720)  # Total array size
    * 16  # Bytes per complex number
    / 1024 ** 3  # Convert to GB
)
```

The solution is to first use $Q_y$, then use $Q_x$.  This allows us to keep the intermediate sizes down:

```{code-cell} ipython3
zs_ = np.ravel(zs)[:, None]
kx_ = kx_.ravel()[None, :] # Qx.shape = (Nz, Nx)
ky_ = ky_.ravel()[None, :] # Qy.shape = (Nz, Ny)

Qx = np.exp(1j * kx_ * (zs_.real + x_[0])) / ho.Nxy[0]
Qy = np.exp(1j * ky_ * (zs_.imag + y_[0])) / ho.Nxy[1]

tmp_ = np.einsum("zx,xy->zy", Qx, psi_t)
# This is just tmp_ = Qx.dot(psi_t) = Qx @ psi_t
psi_ = np.einsum("zy,zy->z", Qy, tmp_)
# This is Qy * tmp_ summed over the last axis

def ifft(yt):
    return (Qy * (Qx @ psi_t)).sum(axis=-1)

%time ifft(psi_t)
assert np.allclose(psi_, ifft(psi_t))
```

We have implemented this in our code.  After included the current calculations, things get slow again, but we can speed this to get acceptable frame-rates by downsampling (skipping points):

```{code-cell} ipython3
vs_ = tp.get_vs(zs, psi, xy=ho.xy)
assert np.allclose(vs_, vs, atol=2e-4)  # Not exact because of n_max regularization
vs_ = tp.get_vs(zs, psi, xy=ho.xy, skip=2)
assert np.allclose(vs_, vs, atol=1e-3)  # Not exact because of skipping
vs_ = tp.get_vs(zs, psi, xy=ho.xy, skip=4)
assert np.allclose(vs_, vs, atol=1e-3)  # Not exact because of skipping
```

```{code-cell} ipython3
%timeit tp.get_n_v(psi, kxy=ho.kxy)
%timeit tp.get_vs(zs, psi, xy=ho.xy)
%timeit tp.get_vs(zs, psi, xy=ho.xy, skip=2)
%timeit tp.get_vs(zs, psi, xy=ho.xy, skip=4)
```

We might be able to save some time by computing partial transforms, but since we need to interpolate, I don't currently see a way to help with this.

```{code-cell} ipython3
def f1(psi):
    psi_x = np.fft.fft(psi, axis=0)
    psi_y = np.fft.fft(psi, axis=1)    
    psi_xy = np.fft.fftn(psi)
    return psi_x, psi_y, psi_xy

def f2(psi):
    psi_x = np.fft.fft(psi, axis=0)
    psi_y = np.fft.fft(psi, axis=1)
    psi_xy = np.fft.fft(psi_x, axis=1)
    return psi_x, psi_y, psi_xy

def f3(psi):
    psi_x = np.fft.fft(psi, axis=0)
    psi_y = np.fft.fft(psi, axis=1)
    psi_xy = np.fft.fft(psi_y, axis=0)
    return psi_x, psi_y, psi_xy

assert np.allclose(f1(psi), f2(psi))
assert np.allclose(f1(psi), f3(psi))
%timeit f1(psi)
%timeit f2(psi)
%timeit f3(psi)
```

## Demonstration

+++

Here we build a custom output with a label in which to display the frames-per-second (fps).

We start with our custom HTML5 canvas widget.

```{code-cell} ipython3
%matplotlib inline
import numpy as np, matplotlib.pyplot as plt
from matplotlib import cm
from super_hydro.physics.testing import HO

%autoreload
from super_hydro.physics.tracer_particles import TracerParticlesBase


class Simulation:
    Nxy = (1280, 720)  # 720p resolution
    Nz = 500  # Number of tracer particles
    t = 0
    dt = 0.1
    seed = 1
    skip = 8  # Skip factor for getting vs

    def __init__(self, **kw):
        for _k in kw:
            if not hasattr(self, _k):
                raise ValueError(f"Unknown parameter {_k}")
            setattr(self, _k, kw[_k])
        self.init()

    def init(self):
        self.ho = ho = HO(Nxy=self.Nxy)
        self.psi = ho.get_psi(t=self.t)
        self.tp = TracerParticlesBase(
            xy=self.ho.xy,
            psi=self.psi,
            N=self.Nz,
            hbar_m=ho.hbar / ho.m,
            seed=self.seed,
            skip=self.skip,
        )
        self.n_max = (abs(self.psi) ** 2).max()

    def evolve(self, steps=1):
        for n in range(steps):
            self.t += self.dt
            self.psi = self.ho.get_psi(t=self.t)
            self.tp.evolve(dt=self.dt, psi=self.psi)

    def n_to_rgba(self, n):
        """Convert the density n to RGBA data"""
        # Transpose so we can use faster canvas.indexing = "xy"
        return cm.viridis(n.T / self.n_max, bytes=True)
```

```{code-cell} ipython3
from importlib import reload
from super_hydro.clients import canvas_widget;reload(canvas_widget)
from super_hydro.contexts import FPS
from ipywidgets import Label, VBox

sim = Simulation(Nxy=(2*256, 2*128), dt=0.02, Nz=500, skip=2)
#canvas = canvas_widget.CanvasIPy()
canvas = canvas_widget.Canvas()
canvas.layout = dict(width="100%", height="auto")
canvas.width, canvas.height = sim.psi.shape

msg = Label()
display(VBox([canvas, msg]))


with FPS(timeout=5, frames=200) as fps:
    for frame in fps:
        sim.evolve(1)
        n = abs(sim.psi)**2
        canvas.rgba = sim.n_to_rgba(n)
        msg.value = f"{fps=}"
```

### ipycanvas

+++

Here is the ipycanvas version.

```{code-cell} ipython3
from super_hydro.contexts import FPS
from traitlets import All

from ipywidgets import Label, VBox
import ipywidgets as widgets
from ipywidgets import Label, VBox, IntSlider
from ipycanvas import Canvas, hold_canvas
from super_hydro.contexts import FPS

sim = Simulation(Nxy=(2*256, 2*128), dt=0.02, Nz=500, skip=2)
canvas = Canvas(name="MyCanvas", width=sim.psi.shape[0], height=sim.psi.shape[1])
canvas.layout.width = '100%'
canvas.layout.height = 'auto'

events = {}
'''
canvas.sync_image_data = True
events_ = []
def save_changes(change):
    global events, events_
    events_.append(change)
    key = change['name']
    events.setdefault(key, 0)
    events[key] += 1
    
canvas.observe(save_changes, All, All)
'''
msg = Label()
display(VBox([canvas, msg]))

def do_update(fps):
    global sim, canvas, msg
    sim.evolve(2)
    n = abs(sim.psi)**2
    with hold_canvas(canvas):
        canvas.put_image_data(sim.n_to_rgba(n)[..., :3], 0, 0)  # Discard alpha
        ix, iy, vs = sim.tp.inds
        rect = False
        if rect:
            canvas.fill_rects(ix, iy, 1)
        else:
            dth = 0.2
            r0 = 0
            r1 = 5.0
            v0 = r1/sim.dt
            th = np.angle(vs)
            r = r0 + r1 * np.abs(vs)/v0
            xi = 10*np.abs(vs)/v0
            # dth = pi if v = 0
            # dth = 0.2 if v = infty
            dth = 0.2/r + (np.pi-0.2/r)/(1+xi**2)
            canvas.fill_style = "black"
            canvas.global_alpha = 0.5
            canvas.fill_arcs(ix, iy, r, th-np.pi-dth, th-np.pi+dth)
    msg.value = f"{fps=}, {events=}"

with FPS(frames=2000, timeout=200) as fps:
    for frame in fps:
        do_update(fps)
```

```{code-cell} ipython3
canvas.global_alpha
```

```{code-cell} ipython3
from super_hydro.contexts import FPS
from ipywidgets import Label, VBox

import ipywidgets as widgets
from ipywidgets import Label, VBox, IntSlider
import ipycanvas.canvas
from ipycanvas import Canvas, hold_canvas
from super_hydro.contexts import FPS

sim = Simulation()
psi0 = sim.ho.get_psi(t=0)
canvas = Canvas(width=psi0.shape[0], height=psi0.shape[1])
canvas.layout.width = "500px"
canvas.layout.height = "auto"

msg = Label()
display(VBox([canvas, msg]))

with FPS(frames=200, timeout=5) as fps:
    for frame in fps:
        t = 0.1 * frame
        psi = sim.ho.get_psi(t=t)
        n = abs(psi) ** 2
        rgba_data = sim.n_to_rgba(n)
        with hold_canvas(canvas):
            # canvas.put_image_data(sim.n_to_rgba(n)[..., :3], 0, 0)  # Discard alpha
            x = y = 0
            #image_buffer = ipycanvas.canvas.binary_image()
            image_buffer = rgba_data.tobytes()
            image_buffer = np.swapaxes(rgba_data, 0, 1).tobytes()
            ipycanvas.canvas._CANVAS_MANAGER.send_draw_command(
                canvas, ipycanvas.canvas.COMMANDS["putImageData"], [x, y], [image_buffer]
            )
        msg.value = f"{fps=}"
        break
```

```{code-cell} ipython3
Nxy = (1280, 720)  # 720p resolution
#canvas_widget.display_js()   # Load javascript
canvas = canvas_widget.Canvas()
canvas.width = 500
canvas.height = 0
canvas.tracer_size = "1"
proxy = 1

canvas.fg_object = {
    "tracer": [["tracer", 1280, 720, 20, "red", 0.5, 0, 0],
    ["tracer", 400, 50, 300, "green", 0.5, -1, 1]]
}

proxy_2 = canvas.fg_object

msg = Label()
display(VBox([canvas, msg]))

def n_to_rgba(n):
    """Convert the density n to RGBA data"""
    return cm.viridis(n.T, bytes=True)

ho = HO()
tp = TracerParticlesBase(xy=ho.xy, N=500)
n_max = (abs(ho.get_psi(t=0))**2).max()

with FPS(timeout=5, frames=200) as fps:
    for frame in fps:
        t = 0.1*frame
        psi = ho.get_psi(t=t)
        #n, v = tp.get_n_v(psi=psi, kxy=ho.kxy, hbar_m=ho.hbar / ho.m)
        n = abs(psi)**2
        canvas.rgba = n_to_rgba(n/n_max)
        #proxy_2["tracer"][0][1] -= 10
        #proxy_2["tracer"][1][7] += 0.01
        #canvas.fg_object = proxy_2
        #proxy += 1
        #canvas.tracer_size = str(proxy)
        msg.value = f"{fps=}"
```

## Interactions

```{code-cell} ipython3
from super_hydro.contexts import FPS
from traitlets import All

from ipywidgets import Label, VBox, Output
import ipywidgets as widgets
from ipywidgets import Label, VBox, IntSlider
from ipycanvas import Canvas, hold_canvas
from super_hydro.contexts import FPS

sim = Simulation(Nxy=(2*256, 2*128), dt=0.02, Nz=500, skip=2)
canvas = Canvas(width=sim.psi.shape[0], height=sim.psi.shape[1])
canvas.layout.width = '100%'
canvas.layout.height = 'auto'
    
slider = widgets.IntSlider()

msg = Label()
display(VBox([canvas, slider, msg]))

def do_update(fps):
    global sim, canvas, msg, slider
    sim.evolve(2)
    n = abs(sim.psi)**2
    with hold_canvas(canvas):
        canvas.put_image_data(sim.n_to_rgba(n)[..., :3], 0, 0)  # Discard alpha
        ix, iy, vs = sim.tp.inds
        rect = False
        if rect:
            canvas.fill_rects(ix, iy, 1)
        else:
            dth = 0.2
            r0 = 0
            r1 = 5.0
            v0 = r1/sim.dt
            th = np.angle(vs)
            r = r0 + r1 * np.abs(vs)/v0
            xi = 10*np.abs(vs)/v0
            # dth = pi if v = 0
            # dth = 0.2 if v = infty
            dth = 0.2/r + (np.pi-0.2/r)/(1+xi**2)
            canvas.fill_style = "black"
            canvas.global_alpha = 0.5
            canvas.fill_arcs(ix, iy, r, th-np.pi-dth, th-np.pi+dth)
    msg.value = f"{fps=}, {slider.value=}"

with FPS(frames=2000, timeout=200) as fps:
    for frame in fps:
        do_update(fps)
        for n in range(int(np.ceil(1/max(1, fps.fps)/kernel._poll_interval))):
            kernel.do_one_iteration()
```

```{code-cell} ipython3

```

```{code-cell} ipython3
#display(VBox([canvas, msg]))


    
with FPS(frames=2000, timeout=200) as fps:
    for frame in fps:
        do_update(fps)
        kernel.do_one_iteration()
```

```{code-cell} ipython3

```

```{code-cell} ipython3
# This does not work:  The slider never updates in Python
from super_hydro.contexts import FPS
from traitlets import All

from ipywidgets import Label, VBox
import ipywidgets as widgets
from ipywidgets import Label, VBox, IntSlider
from ipycanvas import Canvas, hold_canvas
from super_hydro.contexts import FPS

sim = Simulation(Nxy=(2*256, 2*128), dt=0.02, Nz=500, skip=2)
canvas = Canvas(width=sim.psi.shape[0], height=sim.psi.shape[1])
canvas.layout.width = '100%'
canvas.layout.height = 'auto'

int_slider = widgets.IntSlider()

msg = Label()
display(VBox([canvas, int_slider, msg]))
#display(VBox([canvas, msg]))

with FPS(frames=2000, timeout=200) as fps:
    for frame in fps:
        sim.evolve(2)
        n = abs(sim.psi)**2
        with hold_canvas(canvas):
            canvas.put_image_data(sim.n_to_rgba(n)[..., :3], 0, 0)  # Discard alpha
            ix, iy, vs = sim.tp.inds
            rect = False
            if rect:
                canvas.fill_rects(ix, iy, 1)
            else:
                dth = 0.2
                r0 = 0
                r1 = 5.0
                v0 = r1/sim.dt
                th = np.angle(vs)
                r = r0 + r1 * np.abs(vs)/v0
                xi = 10*np.abs(vs)/v0
                # dth = pi if v = 0
                # dth = 0.2 if v = infty
                dth = 0.2/r + (np.pi-0.2/r)/(1+xi**2)
                canvas.fill_style = "black"
                canvas.global_alpha = 0.5
                canvas.fill_arcs(ix, iy, r, th-np.pi-dth, th-np.pi+dth)
        msg.value = f"{fps=}, {int_slider.value=}"
```

```{code-cell} ipython3
N = 10
dx = 0.2
k = np.fft.fftfreq(N, dx)
k[1], 1/N/dx
```

For a single vortex at the origin, $\phi = \theta = \tan^{-1}(y/x)$ is the angle, so $\vect{\nabla}\phi = \uvect{\theta}/r = (y/r^2, -x/r^2)$.  Thus, if vortices are separated by distance $d$, the whole lattice should rotate at roughly

\begin{gather*}
  \omega = \frac{2\pi \hbar }{m d}.
\end{gather*}

Here we implement a "fake" vortex lattice using these ideas to test the tracer-particle code.

```{code-cell} ipython3
%matplotlib inline
%autoreload
from mmfutils.plot import imcontourf
import numpy as np, matplotlib.pyplot as plt
from super_hydro.physics.gpe_utils import get_vortex_factor

hbar = m = 1.0
healing_length = 1.0
n0 = 1.0  # Background density
Lx = 50.0  # Box length
R = 0.8 * Lx / 2  # Radius of trap
vortex_sep = 0.5 * R

# Estimate angular velocity of the vortex lattice
w = 2 * np.pi * hbar / m / vortex_sep

Nx = 256*2  # Number of points along x
dx = Lx / Nx

# Make grid
Nxy = (Nx,) * 2
x, y = np.meshgrid(
    *[(np.arange(_N) - _N / 2) * dx for _N in Nxy], sparse=True, indexing="ij"
)
kx, ky = np.meshgrid(
    *[2 * np.pi * np.fft.fftfreq(_N, dx) for _N in Nxy], sparse=True, indexing="ij"
)

z = x + 1j * y
r = abs(z)

# Location of vortices at time t = 0
z0s = np.concatenate([[0j], vortex_sep * np.exp(2j * np.pi / 6 * np.arange(6))])


def get_psi(t=0, z=z, w=1.0):
    """Return a sample wavefunction for a rotating vortex lattice."""
    n = n0 * np.exp(-((r / R) ** 40))

    # Two time-dependent factors.  First, rotate the vortex cores.
    z0s_ = np.exp(-1j * w * t) * z0s

    return n * np.prod([get_vortex_factor(z - z0) for z0 in z0s_], axis=0)
```

```{code-cell} ipython3
%autoreload
import super_hydro.physics.tracer_particles
from super_hydro.physics.tracer_particles import TracerParticlesBase
tp = TracerParticlesBase(xy=(x, y), N=500)
psi = get_psi()
n, v = tp.get_n_v(psi=psi, kxy=(kx, ky), hbar_m=hbar/m)
zs, vs = tp.init(n=n, v=v)[:3]
zvs = np.vstack([zs, zs+vs/abs(vs)])

fig, axs = plt.subplots(1, 2, figsize=(10,5))
plt.sca(axs[0])
imcontourf(x, y, n, aspect=1)
plt.plot(zs.real, zs.imag, '.k')
plt.plot(zvs.real, zvs.imag, '-k');
plt.sca(axs[1])
imcontourf(x, y, abs(v), vmax=1, aspect=1)
plt.colorbar()
#for z, v in zip(zs, vs):
#    plt.arrow(z.real, z.imag, 10*v.real, 10*v.imag)
```

```{code-cell} ipython3
from IPython.display import display, clear_output
from mmfutils.contexts import NoInterrupt

fig, ax = plt.subplots()
NoInterrupt.unregister()
with NoInterrupt() as interrupted:
    for t in np.linspace(0, 100):
        if interrupted:
            break
        psi = get_psi(t=t)
        ax.cla()
        imcontourf(x, y, abs(psi) ** 2, aspect=1)
        display(fig)
        clear_output(wait=True)
```

# Computation

+++

Here is a brief sample code to show how long the computations take.  Here we animate 10 steps at a couple of resolutions:

On my 2015 Macbook Pro with NumPy for the FFT:

```
Nxy=(1280, 720)   # 1fps
1.1 s ± 12.4 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
Nxy=(256, 256)    # 17fps
59.5 ms ± 1.1 ms per loop (mean ± std. dev. of 7 runs, 10 loops each)
Nxy=(128, 128)    # 67fps
14.9 ms ± 187 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
Nxy=(64, 64)      # 232fps
4.31 ms ± 113 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
Nxy=(32, 32)      # 685fps
1.46 ms ± 10.7 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)
```

On Penguin with NumPy:
```
Nxy=(1280, 720)   # 2fps
606 ms ± 1.57 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
Nxy=(256, 256)    # 25fps
39.4 ms ± 20.5 µs per loop (mean ± std. dev. of 7 runs, 10 loops each)
Nxy=(128, 128)    # 115fps
8.67 ms ± 2.18 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
Nxy=(64, 64)      # 485fps
2.06 ms ± 1.35 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
Nxy=(32, 32)      # 1661fps
602 µs ± 642 ns per loop (mean ± std. dev. of 7 runs, 1,000 loops each)
```

On Penguin with PyFFTW:
```
Nxy=(1280, 720)   # 3fps
364 ms ± 5.77 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
Nxy=(256, 256)    # 42fps
23.9 ms ± 36.1 µs per loop (mean ± std. dev. of 7 runs, 10 loops each)
Nxy=(128, 128)    # 152fps
6.57 ms ± 75.2 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
Nxy=(64, 64)      # 535fps
1.87 ms ± 37 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)
Nxy=(32, 32)     # 1297fps
771 µs ± 21.4 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)
```

```{code-cell} ipython3
print(np.divide(1000, [1100., 59.5, 14.9, 4.31, 1.46]).round(0).astype(int))
print(np.divide(1000, [606., 39.4, 8.67, 2.06, 0.602]).round(0).astype(int))
print(np.divide(1000, [364., 23.9, 6.57, 1.87, 0.771]).round(0).astype(int))
```

```{code-cell} ipython3
import numpy as np

for Nxy in [(1280, 720), (256,)*2, (128,)*2, (64,)*2, (32,)*2]:
    dx = 0.1
    Lxy = np.multiply(dx, Nxy)
    rng = np.random.default_rng(seed=1)
    psi = (rng.random(Nxy + (2,)) - 0.5).view(dtype=complex).reshape(Nxy)
    xy = np.meshgrid(
        *(np.arange(_N) * dx - _L / 2 for _N, _L in zip(Nxy, Lxy)),
        indexing="ij",
        sparse=True
    )
    kxy = np.meshgrid(
        *(2*np.pi * np.fft.fftfreq(_N,  dx) for _N in Nxy),
        indexing="ij",
        sparse=True
    )
    g = hbar = m = w = 1
    V = sum(m*(w*_x)**2/2 for _x in xy)
    K = sum((hbar*_k)**2/2/m for _k in kxy)
    try:
        from mmfutils.performance import fft as mmfft
        fftn = mmfft.get_fftn_pyfftw(psi.copy())
        ifftn = mmfft.get_ifftn_pyfftw(psi.copy())
    except:
        fftn, ifftn = np.fft.fftn, np.fft.ifftn
        
    def step(psi, dt=1.0, steps=10):
        """Compute 1 step using split operator."""
        factor = dt/(1j*hbar)
        K_factor = np.exp(factor*K)
        psi *= np.exp(factor * (g*(psi.conj() * psi) + V) / 2)
        for n in np.arange(steps-1):
            psi = ifftn(K_factor*fftn(psi))
            psi *= np.exp(factor * (g*(psi.conj() * psi) + V))
        psi = ifftn(K_factor*fftn(psi))
        psi *= np.exp(factor * (g*(psi.conj() * psi) + V) / 2)
        return psi

    print(f"{Nxy=}")
    %timeit step(psi)
```

# Display

The main visual element of the program is the rapid update of an image from the server.
Here we explore some options for updating in a notebook to see what performance we can
get.  For demonstration purposes we update a random frame at 720p resolution.  First we time the conversion
from raw data to an image format that can be displayed to determine the maximum possible
framerate.

```{code-cell} ipython3
:init_cell: true

%%javascript
// This removes the scroll bars so that they do not interfere with the output
IPython.OutputArea.prototype._should_scroll = function(lines) { return false; }
```

```{code-cell} ipython3
:init_cell: true

import io
import time
from PIL import Image
import numpy as np
from matplotlib import cm
Nxy = (1280, 720)  # 720p resolution
#Nxy = (512, 512)

def get_data(t=None, Nxy=Nxy, t_=[0.0], dt=0.1):
    Nx, Ny = Nxy
    if t is None:
        t_[0] += dt
        t = t_[0]
    x = np.linspace(-2,2,Nx)[:, None]
    y = np.linspace(-2,2,Ny)[None, :]
    n = np.exp(-x**2 - np.cos(np.log(1+t)*x)**2*(y**2 - np.sin(3*t)*x)**2)
    return n
    #data = cm.viridis(n, bytes=True)
    #psi = np.random.random(Nxy + (2,)).view(dtype=complex).reshape(Nxy)-0.5-0.5j
    #n = abs(psi)**2
    return n/n.max()

def data_to_rgba(data):
    """Convert the data to RGBA data"""
    return cm.viridis(data.T, bytes=True)

def rgba_to_png(rgba, size=None):
    b = io.BytesIO()
    img = Image.fromarray(rgba)
    if size is not None:
        img = img.resize(size)
    img.save(b, 'PNG')
    return b.getvalue()
    
def rgba_to_jpeg(rgba, size=None):
    """JPEG formatter, but discards alpha"""
    b = io.BytesIO()
    img = Image.fromarray(rgba[..., :3])
    if size is not None:
        img = img.resize(size)
    img.save(b, 'JPEG')
    return b.getvalue()

def fps(f, N=10):
    tic = time.time()
    for n in range(N):
        f()
    toc = time.time()
    fps = N/(toc-tic)
    print(f"{fps:.1f}fps")
    return fps
```

```{code-cell} ipython3
display(Image.fromarray(data_to_rgba(get_data())))

print("data: ", end='');fps(lambda: get_data());
print("rgba: ", end='');fps(lambda: data_to_rgba(get_data()));
print("png: ", end='');fps(lambda: rgba_to_png(data_to_rgba(get_data())));
print("jpeg: ", end='');fps(lambda: rgba_to_jpeg(data_to_rgba(get_data())));
print("Image: ", end='');fps(lambda: Image.fromarray(data_to_rgba(get_data())));
```

On my computer, generating random data at this resolution and converting it to an array for display is fast enough to get ~20fps.  Converting to an image with PNG is prohibatively slow, but JPEG is marginal.  Now we look into displaying this.

+++

## HTML5 Canvas

+++

Here is our custom HTML5 Canvas widget.  It is currently fast enough, though performance could probably be improved (at least with modern browsers that support ImageBitmaps).

```{code-cell} ipython3
import mmf_setup.set_path.hgroot
import ipywidgets as widgets
from ipywidgets import Label, VBox, IntSlider
from importlib import reload
from super_hydro.clients import canvas_widget;reload(canvas_widget)
from super_hydro.contexts import NoInterrupt
canvas_widget.display_js()   # Load javascript
canvas = canvas_widget.Canvas()
canvas.width = 500
canvas.height = 0
canvas.tracer_size = "1"
proxy = 1

canvas.fg_object = {
    "tracer": [["tracer", 1280, 720, 20, "red", 0.5, 0, 0],
    ["tracer", 400, 50, 300, "green", 0.5, -1, 1]]
}

proxy_2 = canvas.fg_object

msg = Label()
display(VBox([canvas, msg]))

NoInterrupt.unregister()   # Needed for notebooks which muck with signals
with NoInterrupt() as interrupted:
    tic = time.time()
    toc = 0
    frame = 0
    while frame < 200 and not interrupted:
        canvas.rgba = data_to_rgba(get_data())
        toc = time.time()
        frame += 1
        proxy_2["tracer"][0][1] -= 10
        proxy_2["tracer"][1][7] += 0.01
        canvas.fg_object = proxy_2
        proxy += 1
        canvas.tracer_size = str(proxy)
        msg.value = f"{frame/(toc-tic):.2f}fps"
        
```

```{code-cell} ipython3
from super_hydro.clients import canvas_widget;reload(canvas_widget)
canvas_widget.display_js()   # Load javascript
canvas = canvas_widget.Canvas()
canvas.rgba = data_to_rgba(get_data())
display(canvas)
```

```{code-cell} ipython3
print(canvas.fg_object["tracer"][0][6])
```

## IPyCanvas

* https://github.com/martinRenou/ipycanvas/

```{code-cell} ipython3
import mmf_setup.set_path.hgroot
import ipywidgets as widgets
from ipywidgets import Label, VBox, IntSlider
from ipycanvas import Canvas, hold_canvas
from super_hydro.contexts import NoInterrupt

_data0 = get_data()
canvas = Canvas(width=_data0.shape[0], height=_data0.shape[1])
canvas.layout.width = '500px'
canvas.layout.height = 'auto'
msg = Label()
display(VBox([canvas, msg]))

NoInterrupt.unregister()   # Needed for notebooks which muck with signals
with NoInterrupt() as interrupted:
    tic = time.time()
    toc = 0
    frame = 0
    while frame < 200 and not interrupted:
        with hold_canvas(canvas):
            canvas.put_image_data(data_to_rgba(get_data()), 0, 0)
        toc = time.time()
        frame += 1
        msg.value = f"{frame/(toc-tic):.2f}fps"
```

## Pillow

+++

Here is a straightfoward attempt with the pillow (PIL) library:

```{code-cell} ipython3
import time
from mmf_setup.set_path import hgroot
from super_hydro.contexts import NoInterrupt
from PIL import Image
from IPython.display import display, clear_output
with NoInterrupt() as interrupted:
    tic = time.time()
    toc = 0
    frame = 0
    while frame < 10 and not interrupted:
        display(Image.fromarray(data_to_rgba(get_data())))
        toc = time.time()
        frame += 1
        clear_output(wait=True)
    print("{:.2f}fps".format(frame/(toc-tic)))
```

Clearly this is too slow.

+++

## IPyWidgets

+++

Using an image (the `PIL` or `pillow` library) is fast enough (~20fps using the JPEG format with a 512x512 grid).  As [mentioned in this blog](https://medium.com/@kostal91/displaying-real-time-webcam-stream-in-ipython-at-relatively-high-framerate-8e67428ac522), using a JPEG format is much faster than using PNG (though the alpha-channel must be dealt with.  Here we discard it since our data rarely uses it.).

```{code-cell} ipython3
import io
class MyImage(object):
    def __init__(self, data, size=None,
                 fmt='PNG'):
        self.data = data
        if size is None:
            size = data.shape[:2][::-1]  # Images are flipped
        self.size = size
        if fmt == 'PNG':
            self._repr_png_ = self.__repr_png_
        elif fmt == 'JPEG':
            self._repr_jpeg_ = self.__repr_jpeg_
        
    @property
    def _metadata(self):
        return dict(width=f"{self.size[0]:d}px", 
                    height=f"{self.size[1]:d}px")
    
    def __repr_png_(self):
        b = io.BytesIO()
        img = Image.fromarray(self.data)
        img = img.resize(self.size)
        img.save(b, 'PNG')
        return (b.getvalue(), self._metadata)
    def __repr_jpeg_(self):
        """JPEG formatter, but discards alpha"""
        b = io.BytesIO()
        img = Image.fromarray(self.data[..., :3])
        #img = img.resize(self.size)
        img.save(b, 'JPEG')
        return (b.getvalue(), self._metadata)
MyImage(data_to_rgba(get_data()))
```

Converting to PNG is too slow, converting to JPEG is marginally acceptable.

+++

### Output

+++

Here we use the `Output` widget to capture the results of display.  This provides a marginally acceptable solution with a reasonable ~10fps framerate.

```{code-cell} ipython3
import time
import ipywidgets
from ipywidgets import interact
from super_hydro.contexts import NoInterrupt
from IPython.display import display, clear_output
from PIL import Image
#frame = ipywidgets.
#out = ipywidgets.Output(layout=dict(width=f'{Nxy[0]}px', 
#                                    height=f'{Nxy[1]+100}px'))
out = ipywidgets.Output()
inp = ipywidgets.IntSlider()
msg = ipywidgets.Label()
wid = ipywidgets.VBox([inp, out, msg])
display(wid)
tic = time.time()
toc = 0
frame = 0
data = get_data()
with out:
    NoInterrupt.unregister()
    with NoInterrupt() as interrupted:        
        while not interrupted:
            data = data_to_rgba(get_data())
            #img = Image.fromarray(data[..., :3])
            myimg = MyImage(data, fmt='JPEG')#, size=(256,)*2)
            display(myimg)
            # The Output() widget allows you to print, but it is slightly
            # faster to use a pre-defined Label()
            # print(f"{frame/(toc-tic):.2f}fps")
            msg.value = f"{frame/(toc-tic):.2f}fps"
            toc = time.time()
            frame += 1
            clear_output(wait=True)
```

This is a working demonstration with marginal performance characteristics.

+++

### Image

+++

Here we try using the `Image` widget.

```{code-cell} ipython3
import time
import ipywidgets
from ipywidgets import interact
from super_hydro.contexts import NoInterrupt
from IPython.display import display, clear_output
from PIL import Image
img = ipywidgets.Image(format='jpeg')#, width=2*256)
inp = ipywidgets.IntSlider()
msg = ipywidgets.Label()
wid = ipywidgets.VBox([inp, img, msg])
display(wid)
tic = time.time()
toc = 0
frame = 0
data = get_data()
NoInterrupt.unregister()
with NoInterrupt() as interrupted:        
     while not interrupted:
        data = data_to_rgba(get_data())
        #img = Image.fromarray(data[..., :3])
        img.value = MyImage(data, fmt='JPEG')._MyImage__repr_jpeg_()[0]
        #display(myimg)
        msg.value = "{:.2f}fps".format(frame/(toc-tic))
        toc = time.time()
        frame += 1
        # clear_output(wait=True)
```

# HTML5 Canvas

+++

Here are some references:

* [Is `putImageData` faster than `drawImage`?](https://stackoverflow.com/questions/7721898/is-putimagedata-faster-than-drawimage)

```{code-cell} ipython3
%%html
<style type="text/css">
    canvas {
        border: 1px solid black;
    }
</style>
<canvas></canvas>
```

```{code-cell} ipython3
from traitlets import Unicode, Bool, validate, TraitError, Instance, Int, Bytes
from ipywidgets import DOMWidget, register
from ipywidgets.widgets.trait_types import bytes_serialization


@register
class Canvas(DOMWidget):
    _view_name = Unicode('CanvasView').tag(sync=True)
    _view_module = Unicode('canvas_widget').tag(sync=True)
    _view_module_version = Unicode('0.1.0').tag(sync=True)
 
    _rgba_data = Bytes(help="RGBA image data").tag(sync=True, **bytes_serialization)
    _image_width = Int(help="Image width").tag(sync=True)
    _image_height = Int(help="Image height").tag(sync=True)

    # Attributes
    width = Int(100, help="Width of canvas").tag(sync=True)
    height = Int(200, help="Height of canvas").tag(sync=True)
    
    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data
        #self._compressed_data = rgba_to_jpeg(data_to_rgba(data))
        self._image_width, self._image_height = data.shape[:2]
        self._rgba_data = data_to_rgba(data).tobytes()
```

```{code-cell} ipython3
%%javascript
require.undef('canvas_widget');

define('canvas_widget', ["@jupyter-widgets/base"], function(widgets) {
    
    var CanvasView = widgets.DOMWidgetView.extend({

        // Render the view.
        render: function() {
            this.canvas = document.createElement("canvas");
            this.ctx = this.canvas.getContext('2d');
            this.canvas.width = this.model.get('width');
            this.canvas.height = this.model.get('height');
            this.el.appendChild(this.canvas);
            this.update()

            // Python -> JavaScript update
            this.model.on('change:width', this.update, this);
            this.model.on('change:height', this.update, this);
            this.model.on('change:value', this.update, this);
            
            // JavaScript -> Python update
            //this.value.onchange = this.value_changed.bind(this);
        },

        update: function() {
            var options = {'type': 'image/jpeg'};
            var _data = this.model.get('_rgba_data')
            var _raw_data = new Uint8ClampedArray(_data.buffer);
            var _width = this.model.get('_image_width');
            //debugger;
            this._image = new ImageData(_raw_data, _width);
            requestAnimationFrame(this.draw.bind(this));
            //this.draw();
            //var blob = new Blob([this.model.get('_compressed_data')], options);
            //var promise = createImageBitmap(blob);
            //promise.then(this.draw.bind(this));
        },
        
        draw: function() {
            //debugger;
            var image = this._image;
            this.canvas.width = image.width;
            this.canvas.height = image.height;
            this.ctx.putImageData(image, 0, 0)
            //this.ctx.drawImage(image, 0, 0);            
        }
    });

    return {
        CanvasView: CanvasView
    };
});
```

```{code-cell} ipython3
canvas = Canvas(data=get_data())
canvas.data = get_data()
display(canvas)
```

```{code-cell} ipython3
import time
tic = time.time()
for n in range(10):
    canvas.data = get_data()
10/(time.time() - tic)
```

With this I can get 15+fps on Chrome (but it stalls on Safari).

```{code-cell} ipython3
import mmf_setup.set_path.hgroot
from IPython.display import clear_output
from super_hydro.contexts import NoInterrupt
tic = time.time()
frames = 0
NoInterrupt.unregister()
with NoInterrupt() as interrupted:
    while not interrupted:
        canvas.data = get_data()
        frames += 1
        toc = time.time()
        display(frames/(toc-tic))
        clear_output(wait=True)
```

## Matplotlib

+++

Here are some miscellaneous Matplotlib tools.  This is too slow.

```{code-cell} ipython3
import matplotlib.pyplot as plt
import matplotlib.animation
import numpy as np

t = np.linspace(0,2*np.pi)
x = np.sin(t)

fig, ax = plt.subplots()
ax.axis([0,2*np.pi,-1,1])
l, = ax.plot([],[])

def animate(i):
    l.set_data(t[:i], x[:i])

ani = matplotlib.animation.FuncAnimation(fig, animate, frames=len(t))

from IPython.display import HTML
display(HTML(ani.to_jshtml()))
plt.close('all')
```

```{code-cell} ipython3
play = ipywidgets.Play(
    interval=10,
    value=50,
    min=0,
    max=10000,
    step=1,
    description="Press play",
    show_repeat=False,
    disabled=False
)

def on_change(change):
    print(change)

play.observe(on_change, names="value")

slider = ipywidgets.IntSlider()
ipywidgets.jslink((play, 'value'), (slider, 'value'))
ipywidgets.HBox([play, slider])
```

```{code-cell} ipython3
play._playing = False
```

```{code-cell} ipython3
import ipywidgets
import time
import numpy as np

play = ipywidgets.Play(
    interval=200,
    value=50,
    min=0,
    max=10,
    step=1,
    description="Press play",
    show_repeat=False,    
    disabled=False
)
wid = ipywidgets.IntSlider()
txt = ipywidgets.Label()
display(ipywidgets.VBox([wid, txt, play]))

def on_value_change(change):
    play.value = play.value % play.max
    wid.value += 1
    txt.value = str(play.value)
import traitlets
play.observe(on_value_change, names="value")
```

```{code-cell} ipython3
Image.fromarray(cm.viridis(np.random.random(Nxy), bytes=True))
```

```{code-cell} ipython3
%pylab inline --no-import-all
#%pylab notebook --no-import-all
#%matplotlib ipyml


from matplotlib import cm
Nxy = (1024//2, 1024//2)

np.random.seed(2)
def get_data(Nxy=Nxy):
    """Basic routine done on server to generate view data."""
    psi = np.random.random(Nxy + (2,)).view(dtype=complex).reshape(Nxy)-0.5-0.5j
    n = abs(psi)**2
    array = cm.viridis((n-n.min())/(n.max()-n.min()))
    array *= int(255/array.max())  # normalize V0_values
    data = array.astype(dtype='uint8')
    return data
```

```{code-cell} ipython3
%timeit data = get_data()
```

On my computer, this takes 64ms, meaning we should be able to get a 15fps frame-rate.

```{code-cell} ipython3
import time
from mmfutils.contexts import NoInterrupt
from IPython.display import display, clear_output
NoInterrupt.unregister()
with NoInterrupt() as interrupted:
    fig = plt.figure(figsize=(5, 5))
    img = plt.imshow(get_data())
    fig.canvas.draw()
    tic = time.time()
    toc = 0
    frame = 0
    #display(fig)
    time.sleep(1)
    while not interrupted:
        img.set_data(get_data())
        fig.canvas.draw()
        #print("{:.2f}fps".format(frame/(toc-tic)))
        #clear_output(wait=True)
        toc = time.time()
        frame += 1
```

```{code-cell} ipython3
with NoInterrupt() as interrupted:
    tic = time.time()
    toc = 0
    frame = 0
    while not interrupted:
        img.set_data(get_data())
        fig.canvas.draw()
        print("{:.2f}fps".format(frame/(toc-tic)))
        clear_output(wait=True)
        toc = time.time()
        frame += 1
```

# FFT

+++

## Computing Currents

+++

To compute the flow velocity, we need:

$$
  \newcommand{\I}{\mathrm{i}}
  \DeclareMathOperator{\FT}{FT}
  v_x = \frac{1}{m}\Re\frac{-\I\hbar\nabla_x \psi}{\psi}
      = \frac{\hbar}{m}\Re\frac{\FT^{-1}\Bigl(k_x\FT(\psi)\Bigr)}{\psi}.
$$

We want to compute this in 2D as a complex number, so we really want:

$$
  v = v_x + \I v_y.
$$

```{code-cell} ipython3
import numpy as np
Nx, Ny = Nxy = (32, 32)
Nx, Ny = Nxy = (2*1024, 2*1024)
np.random.seed(1)
y = np.random.random((Nx, Ny*2)).view(dtype=complex) - 0.5 - 0.5j
kx, ky = ks = np.fft.fftfreq(Nx)[:, None], np.fft.fftfreq(Ny)[None, :]

def j1(y, ks):
    yt = np.fft.fftn(y)
    return ((np.fft.ifftn(ks[0]*yt)/y).real +
        +1j*(np.fft.ifftn(ks[1]*yt)/y).real)

def j2(y, ks):
    yt = np.fft.fftn(y)
    res = (np.fft.ifftn([ks[0]*yt, ks[1]*yt], 
                        axes=(1,2))/y).real
    return res[0] + 1j*res[1]

np.allclose(j1(y, ks), j2(y, ks))
%timeit j1(y, ks)
%timeit j2(y, ks)
```

On my Mac, with $1024^2$, this takes <3ms/iteration, meaning that if we do this on the client, we could support 500 fps.  Probably best just to send $\psi$ and be done with it if needed.  Even $2046^2$ is <9ms (`j1`).

+++

# D3

+++

In the code above, we use python to convert the density array into an image (applying a colormap etc.)  This requires python on the client's computer OR requires server-side processing then additional transmission of the data.  The latter might be acceptable, but another option is to use [D3](https://d3js.org) to process everything in javascript on the client.

```{code-cell} ipython3
%%javascript
alert("Hi!");
```

```{code-cell} ipython3
%%html
<!-- <script src="https://d3js.org/d3.v5.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/2.3.0/socket.io.js"></script>
-->
<style type="text/css">
    canvas {
        border: 1px solid black;
    }
</style>

<script>
    requirejs.config({
        paths: {
            d3: 'https://d3js.org/d3.v5',
            io: 'https://cdnjs.cloudflare.com/ajax/libs/socket.io/2.3.0/socket.io',
        }
    });

    require(['d3'], function(d3) {
        window.d3 = d3;
    });

    require(['io'], function(io) {
        window.io = io;
    });
</script>
```

```{code-cell} ipython3
%%html
<canvas id="d3_canvas" height=10 width=10></canvas>

<script>
var mmf = {};
mmf.canvas = d3.select("canvas#d3_canvas").node();
mmf.ctx = mmf.canvas.getContext("2d");
mmf.ctx.fillStyle = "#fcb";
mmf.ctx.rect(0,0,10,10);
mmf.ctx.fill();
mmf.socket = io('localhost:50938');
io;
</script>
```

https://pypi.org/project/trio-websocket/

```{code-cell} ipython3
import trio
from sys import stderr
from trio_websocket import open_websocket_url

async def main():
    try:
        async with open_websocket_url(url='wss://127.0.0.1:50938') as ws:
            await ws.send_message('hello world!')
            message = await ws.get_message()
            print('Received message: %s' % message)
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)

trio.run(main)
```

```{code-cell} ipython3
import trio
from trio_websocket import serve_websocket, ConnectionClosed

async def echo_server(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            await ws.send_message(message)
        except ConnectionClosed:
            break

async def main():
    await serve_websocket(echo_server, '127.0.0.1', 50938, ssl_context=None)

trio.run(main)
```

```{code-cell} ipython3
from aiohttp import web
import socketio
sio = socketio.AsyncServer()
app = web.Application?
```

```{code-cell} ipython3
#()
sio.attach(app)

@sio.event
def connect(sid, environ):
    print("connect ", sid)
    
@sio.event
def disconnect(sid):
    print('disconnect ', sid)

web.run_app(app)
```

```{code-cell} ipython3
from ipywidgets import Text
msg = Text()
msg
```

```{code-cell} ipython3
import mmf_setup.set_path.hgroot
from importlib import reload
from super_hydro.contexts import NoInterrupt

NoInterrupt.unregister()   # Needed for notebooks which muck with signals
with NoInterrupt() as interrupted:
    tic = time.time()
    toc = 0
    frame = 0
    while frame < 200 and not interrupted:
        data_to_rgba(get_data())  #???
        toc = time.time()
        frame += 1
        #proxy_2["tracer"][0][1] -= 10
        #proxy_2["tracer"][1][7] += 0.01
        #canvas.fg_object = proxy_2
        #proxy += 1
        #canvas.tracer_size = str(proxy)
        msg.value = f"{frame/(toc-tic):.2f}fps"
```

# flask-SocketIO

```{code-cell} ipython3
%%html
    <h1>Here is a basic example of using Flask-SocketIO!</h1>

    <!-- Here is a basic interaction object for custom socket events. -->
    <button type="button" id="button">Click</button>
    <div id="value">0</div>

    <!-- include JS socket.io API -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/2.3.0/socket.io.js"></script>

    <script>
      // Establish the socket namespace for this page.
      var socket = io('/index');

      // When page connection is made place a basic alert in the JS console.
      socket.on('connect', function() {
        console.log("Connection Made.")
      });

      // When the button HTML object is clicked, get the <div> value and
      // send that to Python under the 'custom_event' event tag.
      document.getElementById("button").onclick = function() {
        var data = document.getElementById('value').innerHTML
        console.log(data)
        socket.emit('custom_event', data);
      };

      // When 'custom_response' event tag is received, update the <div> value
      // with the received data.
      socket.on('custom_response', function(data){
        document.getElementById('value').innerHTML = data;
      });

    </script>
```

```{code-cell} ipython3
import json
import numpy as np

np.random.seed(7)

A = get_data()
```

```{code-cell} ipython3
%timeit L = json.loads(json.dumps(A.tolist()))
```

```{code-cell} ipython3
%timeit A.tobytes()
```

```{code-cell} ipython3
%timeit np.frombuffer(A.tobytes(), dtype=A.dtype).reshape(Nxy)
```

```{code-cell} ipython3
np.frombuffer(A.tobytes(), dtype=A.dtype).reshape(Nxy)
```

```{code-cell} ipython3
%%html
<div id="data"></div><br>
<script type="text/javascript" src="{{ url_for('static', filename='js/app_func.js') }}"></script>
```

```{code-cell} ipython3
from flask import Flask
from flask_socketio import SocketIO, emit

app = Flask("perf_test")
socketio = SocketIO(app)

@socketio.on('testing')
def testing(msg):
    
```

```{code-cell} ipython3
%%javascript
namespace
```

```{code-cell} ipython3
import threading
import time
def run():
    n = 1
    while n < 10:
        print(n)
        time.sleep(1)
        n += 1
t = threading.Thread(target=run)
t.start()
#t.join()
```

```{code-cell} ipython3
1+3
```

```{code-cell} ipython3

```
