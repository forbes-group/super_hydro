---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.10.3
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

```{code-cell} ipython3
import mmf_setup;mmf_setup.nbinit()
```

$$
  \newcommand{\I}{\mathrm{i}}
  \I\hbar \dot{\psi} = \frac{-\hbar^2\nabla^2}{2m}\psi + (gn - \mu)\psi
$$

Length Scales

+++

Phonon Dispersion:

$$
  \psi = \sqrt{n_0}e^{\I \hbar k} \left(1 + u e^{\I (qx - \omega t)} + v^*e^{-\I (qx - \omega t)}\right)
$$

+++

Healing length $\xi_h$:

$$
  \frac{\hbar^2}{2m\xi_h^2} = gn_0
$$

+++

# Split Operator

+++

$$
  \newcommand{\d}{\mathrm{d}}
  \I\hbar \dot{\psi} = H[\psi]\psi = (T + V[\psi])\psi\\
  \d\psi = \frac{H\psi}{\I\hbar}\d{t}\\
  \psi(\d{t}) \approx e^{\d{t} H/\I\hbar}\psi(0)
          = e^{\d{t} (T + V)/\I\hbar}\psi(0)
          \approx e^{\d{t} T/\I\hbar}e^{\d{t} V/\I\hbar}\psi(0)
          \approx e^{\d{t} T/2\I\hbar}e^{\d{t} V/\I\hbar}e^{\d{t} T/2\I\hbar}\psi(0)
$$

$$
  \psi(t) = \left(e^{\d{t} T/2\I\hbar}e^{\d{t} V/\I\hbar}e^{\d{t} T/2\I\hbar}\right)^{N=t/\d{t}}\psi(0)
          = e^{\d{t} T/2\I\hbar}e^{\d{t} V\I\hbar}\left(e^{\d{t} T\I\hbar}e^{\d{t} V/\I\hbar}\right)^{N-1}e^{\d{t} T/2\I\hbar}\psi(0)\\
          = e^{-\d{t} T/2\I\hbar}\left(e^{\d{t} T\I\hbar}e^{\d{t} V/\I\hbar}\right)^{N}e^{\d{t} T/2\I\hbar}\psi(0)
$$

```{code-cell} ipython3
%pylab inline --no-import-all
from importlib import reload
import gpe;reload(gpe)
from gpe import State

s = State()
```

# Demonstration

+++

Here we demonstrate the code without interactions.  We just move the potential in a circle.

```{code-cell} ipython3
%pylab inline --no-import-all
from importlib import reload
import gpe;reload(gpe)
from gpe import State
from IPython.display import display, clear_output
s = State(Nxy=(32*2,32*2), test_finger=True, soc=True)
kx = np.fft.fftshift(s.kxy[0].ravel())
kx2 = np.fft.fftshift(s._kx2).ravel()
plt.plot(kx, kx2)
#plt.plot(kx, s.get_SOC_disp_x(kx))
```

```{code-cell} ipython3
#cooling_phase=1.0)
for n in range(100):
    s.step(100)
    plt.clf()
    s.plot()
    display(plt.gcf())
    clear_output(wait=True)
```

```{code-cell} ipython3
%timeit s.step(20, dt=0.1)
```

```{code-cell} ipython3

```

# SOC

+++

The SOC Hamiltonian is a matrix:

$$
  \op{H} = \begin{pmatrix}
    \frac{\op{p}^2}{2m} + V + gn - \mu - \frac{\delta}{2} & \frac{\Omega}{2}e^{2\I k_R x}\\
     \frac{\Omega}{2}e^{-2\I k_R x} & \frac{\op{p}^2}{2m} + V + gn- \mu + \frac{\delta}{2}
  \end{pmatrix}
$$

```{code-cell} ipython3

```
