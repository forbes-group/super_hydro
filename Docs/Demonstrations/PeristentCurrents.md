---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3 (super_hydro)
  language: python
  name: super_hydro
---

# Peristent Currents

+++

## Introduction

Dalibard et al. [Saint-Jalm:2019] demonstrate that in 2D with a harmonic trap, BECs exhibit a scale invariance that allows recurrance in various initial conditions.  In particular, if one prepares a cloud in a triangle, then this will oscillate with high fidelity when placed in a harmonic trap.

[Saint-Jalm:2019]: https://doi.org/10.1103/PhysRevX.9.021035 'R. Saint-Jalm, P. C. M. Castilho, É. Le Cerf, B. Bakkali-Hassani, J.-L. Ville, S. Nascimbene, J. Beugnon, and Jean Dalibard, "Dynamical Symmetry and Breathers in a Two-Dimensional Bose Gas", prx 9(2), 021035 (2019) '

+++

$$
  \newcommand{\I}{\mathrm{i}}
  \newcommand{\d}{\mathrm{d}}
  \newcommand{\vect}[1]{\vec{#1}}
  \newcommand{\op}[1]{\hat{#1}}
  \newcommand{\abs}[1]{\lvert#1\rvert}
  \newcommand{\pdiff}[2]{\frac{\partial #1}{\partial #2}}
  \newcommand{\ket}[1]{\lvert#1\rangle}
  \newcommand{\bra}[1]{\langle#1\rvert}
  \newcommand{\braket}[1]{\langle#1\rangle}
  \DeclareMathOperator{\Tr}{Tr}
  \I \hbar\pdiff{\psi_n}{t} = \op{H}\psi_n.
$$

```{code-cell}
%matplotlib inline
%load_ext autoreload
import numpy as np, matplotlib.pyplot as plt

%autoreload
from super_hydro.physics import gpe

m = gpe.PersistentCurrents(opts=None)
x, y = m.xy
V = m.get_V_trap()
fig, ax = plt.subplots()
ax.pcolormesh(x.ravel(), y.ravel(), V, shading='nearest')
ax.set(aspect=1)
#r = np.linspace(0, 1, 100)
#plt.plot(r, 1- gpe.utils.mstep(r - 0.5, 0.2) + gpe.utils.mstep(r - 0.8, 0.2))
```

```{code-cell}
%%javascript
IPython.OutputArea.prototype._should_scroll = function(lines) { return false; }
```

```{code-cell}
# Does not work on CoLab yet
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.physics import gpe

reload(gpe)
from super_hydro.clients import notebook

reload(notebook)
notebook.run(
    model="gpe.PersistentCurrents",
    R1=0.5,
    R2=0.9,
    dt_t_scale=0.5,
    Nx=32 * 8//4,
    Ny=32 * 8//4,
    cooling=1e-10,
    tracer_particles=300,
    network_server=False,
    random_phase=False,
    cooling_steps=100,
    winding=20
)
```

```{code-cell}
# Does not work on CoLab yet
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.physics import gpe

reload(gpe)
from super_hydro.clients import notebook

reload(notebook)
notebook.run(
    model="gpe.BECBreather",
    R=0.4,
    a_HO=0.04,
    dt_t_scale=0.5,
    Nx=32 * 8,
    Ny=32 * 8,
    Nshape=4,
    cooling=1e-10,
    tracer_particles=0,
    network_server=False,
    random_phase=True,
)
```

```{code-cell}
%pylab inline
import numpy as np
N = 256
L = 10
dx = L/N
x = np.arange(N)*dx - L//2
x, y = np.meshgrid(x, x, indexing='ij', sparse=True)
n = np.where(np.logical_and(abs(x)<1, abs(y) < 1), 1, 0)
fig, axs = plt.subplots(2,1,figsize=(10,5))
nk = np.fft.fftshift(np.fft.fftn(n))

axs[0].imshow(n)
axs[1].imshow(abs(nk))
for ax in axs:
    ax.set(aspect=1)
dn = 20
axs[1].axis([N/2-dn, N/2+dn, N/2-dn, N/2+dn])
```

```{code-cell}

```
