---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Solitons in a BEC

+++

Here we demonstrate some of the behaviour exhibited by solutions in a Bose-Einstein Condensate (BEC) as described by the Gross-Pitaevskii equation (GPE):

$$
  \newcommand{\I}{\mathrm{i}}
  \newcommand{\abs}[1]{\lvert#1\rvert}
  \I \dot{\psi}(x, t) = \frac{-\hbar^2\nabla^2 \psi(x, t)}{2m} 
    + \Bigl(gn(x,t) - \mu\Bigr)\psi(x, t), \qquad
    n(x,t) = \abs{\psi(x, t)}^2.
$$

These equations admit the following exact solution for what is known as a grey soliton [Tsuzuki:1971]:

$$
  \psi(x, t) = \sqrt{n}\left[\I \frac{v}{c} + \sqrt{1-\frac{v^2}{c^2}}\tanh\frac{x-vt}{l}\right],\\
  l = \frac{\hbar}{m \sqrt{c^2-v^2}} = \frac{\sqrt{2}\xi}{\sqrt{1-\frac{v^2}{c^2}}}, \qquad
  \mu = gn = mc^2.
$$

This formula is for grey  solitons (of infinite size) traveling with velocity $v$ on a background density of $n$.  The speed $\abs{v} \leq c$ is less than the speed of sound $c = \sqrt{gn/m}$ and the density at the center of the solution is:

$$
  n_{\min} = \frac{v^2}{c^2}n.
$$

Hence, stationary solutions have zero density (so-called dark solitons) which has width $l=\sqrt{2}\xi$ where $\xi$ is the healing length of the system.  Moving solutions have finite density in the core (grey solitons) and are wider.

[Tsuzuki:1971]: http://dx.doi.org/10.1007/BF00628744 'Toshio Tsuzuki, "Nonlinear waves in the Pitaevskii-Gross equation", J. Low Temp. Phys. 4(4), 441-457 (1971) '

+++

## Implementation Note

+++

To implement the soliton in a finite box, we must account for the fact that the boundary conditions are not periodic.  We assume that the box is much larger than the soliton width $L \gg l$.  In this case, the wavefunction picks up the following phase twist:

$$
  \frac{\psi(L/2, t)}{\psi(-L/2, t)}
  = \frac{\I v + \sqrt{c^2-v^2}}{\I v - \sqrt{c^2-v^2}},
  = e^{\I \theta}, \qquad
  \cos\theta = 1 - 2\frac{v^2}{c^2}.
$$


*Note: the GPE is actually integrable and one can find explicit forms for all solitons, including those of finite length, but we restrict ourselves here to solitons of infinite length for simplicity.*

+++

# Demonstration

+++

Here we run a demonstration where we start with a soliton in the presence of a very small potential finger.  This is enough to break the symmetry so that if the soliton is wide enough, it will snake.

*Note: rather than implement twisted boundary conditions, we simply multiply the wavefunction by an appropriate factor $e^{\I \theta x/L}$.  This is equivalent to boosting to a moving frame so the apparent velocity will be slightly different than chosen speed $v/c$ with the difference getting smaller as the box gets longer.*

```{code-cell}
%pylab inline
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.physics import gpe;reload(gpe)
from super_hydro.contexts import NoInterrupt
from super_hydro.server import server; reload(server)
from super_hydro.clients import notebook; reload(notebook); reload(notebook.widgets)

f = 2  # Increase scale factor to increase resolution.
d = 4  # Increase d to increase box width. d>=2 will snake.
notebook.run(model='gpe.BECSoliton', v_c=0.0, V0_mu=0.1, dx=1.0/f, Nx=32*f, Ny=8*d*f)
#notebook.run(model='gpe.BEC', Nx=32, Ny=32)
#notebook.run(run_server=False)
```

```{code-cell}
%pylab inline
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.physics import gpe;reload(gpe)
from super_hydro.contexts import NoInterrupt
from super_hydro.server import server; reload(server)
from super_hydro.clients import notebook; reload(notebook); reload(notebook.widgets)

f = 2  # Increase scale factor to increase resolution.
d = 2  # Increase d to increase box width. d>=2 will snake.
notebook.run(model='gpe.BECSoliton', tracer_particles=0, v_c=0.0, V0_mu=0.1, dx=1.0/f, Nx=32*f, Ny=8*d*f)
#notebook.run(model='gpe.BEC', Nx=32, Ny=32)
#notebook.run(run_server=False)
```

```{code-cell}

```
