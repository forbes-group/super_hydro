---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.10.3
kernelspec:
  display_name: Python [conda env:super_hydro]
  language: python
  name: conda-env-super_hydro-py
---

+++ {"toc": true}

<h1>Table of Contents<span class="tocSkip"></span></h1>
<div class="toc"><ul class="toc-item"><li><span><a href="#Bose-Einstein-Condensates-with-Spin-Orbit-Coupling" data-toc-modified-id="Bose-Einstein-Condensates-with-Spin-Orbit-Coupling-1"><span class="toc-item-num">1&nbsp;&nbsp;</span>Bose-Einstein Condensates with Spin-Orbit Coupling</a></span><ul class="toc-item"><li><span><a href="#Rotating-Phase-Basis" data-toc-modified-id="Rotating-Phase-Basis-1.1"><span class="toc-item-num">1.1&nbsp;&nbsp;</span>Rotating Phase Basis</a></span></li><li><span><a href="#Homogeneous-Solutions" data-toc-modified-id="Homogeneous-Solutions-1.2"><span class="toc-item-num">1.2&nbsp;&nbsp;</span>Homogeneous Solutions</a></span></li><li><span><a href="#Single-Band-Model" data-toc-modified-id="Single-Band-Model-1.3"><span class="toc-item-num">1.3&nbsp;&nbsp;</span>Single-Band Model</a></span></li></ul></li><li><span><a href="#Demonstrations" data-toc-modified-id="Demonstrations-2"><span class="toc-item-num">2&nbsp;&nbsp;</span>Demonstrations</a></span><ul class="toc-item"><li><span><a href="#Super-Solid" data-toc-modified-id="Super-Solid-2.1"><span class="toc-item-num">2.1&nbsp;&nbsp;</span>Super-Solid</a></span></li></ul></li><li><span><a href="#Technical-Notes" data-toc-modified-id="Technical-Notes-3"><span class="toc-item-num">3&nbsp;&nbsp;</span>Technical Notes</a></span></li></ul></div>

+++

# Bose-Einstein Condensates with Spin-Orbit Coupling

+++

Here we demonstrate the dynamics of a two-component Bose-Einstein condensate (BEC) with Spin-Orbit coupling (SOC) along the x-axis (equal Rashba and Dresselhaus).  The underlying model evolves with the following set of coupled Gross-Pitaevskii equations (GPEs):

$$
\newcommand{\vect}[1]{\mathbf{#1}}
\newcommand{\uvect}[1]{\hat{#1}}
\newcommand{\abs}[1]{\lvert#1\rvert}
\newcommand{\norm}[1]{\lVert#1\rVert}
\newcommand{\I}{\mathrm{i}}
\newcommand{\ket}[1]{\left|#1\right\rangle}
\newcommand{\bra}[1]{\left\langle#1\right|}
\newcommand{\braket}[1]{\langle#1\rangle}
\newcommand{\Braket}[1]{\left\langle#1\right\rangle}
\newcommand{\op}[1]{\mathbf{#1}}
\newcommand{\mat}[1]{\mathbf{#1}}
\newcommand{\d}{\mathrm{d}}
\newcommand{\D}[1]{\mathcal{D}[#1]\;}
\newcommand{\pdiff}[3][]{\frac{\partial^{#1} #2}{\partial {#3}^{#1}}}
\newcommand{\diff}[3][]{\frac{\d^{#1} #2}{\d {#3}^{#1}}}
\newcommand{\ddiff}[3][]{\frac{\delta^{#1} #2}{\delta {#3}^{#1}}}
\newcommand{\floor}[1]{\left\lfloor#1\right\rfloor}
\newcommand{\ceil}[1]{\left\lceil#1\right\rceil}
\DeclareMathOperator{\Tr}{Tr}
\DeclareMathOperator{\erf}{erf}
\DeclareMathOperator{\erfi}{erfi}
\DeclareMathOperator{\sech}{sech}
\DeclareMathOperator{\sn}{sn}
\DeclareMathOperator{\cn}{cn}
\DeclareMathOperator{\dn}{dn}
\DeclareMathOperator{\sgn}{sgn}
\DeclareMathOperator{\order}{O}
\DeclareMathOperator{\diag}{diag}
%\newcommand{\a}{\uparrow}
%\newcommand{\b}{\downarrow}
\newcommand{\a}{a}
\newcommand{\b}{b}
  \I \hbar \pdiff{}{t}
  \begin{pmatrix}
    \psi_\a(\vect{r}, t)\\
    \psi_\b(\vect{r}, t)
  \end{pmatrix}
  =
  \begin{pmatrix}
    \frac{\op{p}^2}{2m} - \frac{\delta}{2} + U_\a(\vect{r}, t)
    & \frac{\Omega}{2}e^{2\I k_R x}\\
    \frac{\Omega}{2}e^{-2\I k_R x} 
    & \frac{\op{p}^2}{2m} + \frac{\delta}{2} + U_\b(\vect{r}, t)
  \end{pmatrix}
  \cdot
  \begin{pmatrix}
    \psi_\a(\vect{r}, t)\\
    \psi_\b(\vect{r}, t)
  \end{pmatrix}
$$

where the potentials contain both external and mean-field conteributions:

$$
  U_\a(\vect{r}, t) = V_a(\vect{r}, t) 
    + g_{\a\a}n_\a(\vect{r}, t) + g_{\a\b}n_\b(\vect{r}, t), \qquad
  U_\b(\vect{r}, t) = V_\b(\vect{r}, t) 
  + g_{\b\b}n_\b(\vect{r}, t) + g_{\a\b}n_\a(\vect{r}, t).
$$

The off-diagonal term in this model represents a 2-photon transition induced along the x-axis by a Raman laser.  This laser simultaneously flips the "spin" ($\a$, $b$) of the atoms and giving the particles a quasi-momentum kick of $\pm 2k_R$.  In this sense, the system has a spin-orbit coupling – the momentum (orbital motion) of the particles is coupled with their "spin".  The parameters of the theory are:

* $k_R$: Recoil momentum, transfered by Raman lasers.
* $\delta$: Detuning of the coupling beams from the resonance of each species.  This acts as an effective chemical potential difference between the species.
* $\Omega$: Raman coupling.
* $g_{ij}$: Non-linear coupling constants, related to the scattering lengths: $g_{ij} = 4\pi \hbar ^2 a_{ij}/m$.

+++

## Rotating Phase Basis

+++

Under certain circumstances, one can replace this equation of motion with a simpler model by transforming to a different basis, rotating the phases of the components as follows:

$$
  \begin{pmatrix}
    \psi^R_\a(\vect{r}, t)\\
    \psi^R_\b(\vect{r}, t)
  \end{pmatrix}
  =
  \begin{pmatrix}
    e^{-\I k_R x}\psi_\a(\vect{r}, t)\\
    e^{\I k_R x}\psi_\b(\vect{r}, t)
  \end{pmatrix}\\
  \I \hbar \pdiff{}{t}
  \begin{pmatrix}
    \psi^R_\a(\vect{r}, t)\\
    \psi^R_\b(\vect{r}, t)
  \end{pmatrix}
  =
  \begin{pmatrix}
    \frac{(\op{p}_x + \hbar k_R)^2 + \op{p}_y^2}{2m} - \frac{\delta}{2} + U_\a(\vect{r}, t)
    & \frac{\Omega}{2}\\
    \frac{\Omega}{2} 
    & \frac{(\op{p}_x - \hbar k_R)^2 + \op{p}_y^2}{2m} + \frac{\delta}{2} + U_\b(\vect{r}, t)
  \end{pmatrix}
  \cdot
  \begin{pmatrix}
    \psi^R_\a(\vect{r}, t)\\
    \psi^R_\b(\vect{r}, t)
  \end{pmatrix}
$$

In this form, the dispersion is modified, but the off-diagonal terms are now a simple Rabi coupling that flips the particle spin, but no longer transfers momentum.

+++

## Homogeneous Solutions

+++

In the absence of external potentials, one has plane-wave solutions of the form

$$
  \Psi_{\vect{k}}^{R}(\vect{r}, t)
  = 
  \begin{pmatrix}
    \psi^R_\a(\vect{r}, t)\\
    \psi^R_\b(\vect{r}, t)
  \end{pmatrix}
  =
  e^{\I \vect{k}\cdot\vect{r} - \I\mu t/\hbar}
  \begin{pmatrix}
    \sqrt{n_\a}\\
    \sqrt{n_\b}
  \end{pmatrix}.
$$

where

$$
  \begin{pmatrix}
    \frac{\hbar^2 (k_x + k_R)^2}{2m} - \frac{\delta}{2} + g_{\a\a}n_\a + g_{\a\b}n_\b
    & \frac{\Omega}{2}\\
    \frac{\Omega}{2} 
    & \frac{(k_x - k_R)^2}{2m} + \frac{\delta}{2} + g_{\b\b}n_\b + g_{\a\b}n_\a
  \end{pmatrix}
  \cdot
  \begin{pmatrix}
    \sqrt{n_\a}\\
    \sqrt{n_\b}
  \end{pmatrix}
  = \left(\mu - \frac{\hbar^2k_y^2}{2m}\right)
  \begin{pmatrix}
    \sqrt{n_\a}\\
    \sqrt{n_\b}
  \end{pmatrix}.
$$

If the couplings are equal $g = g_{\a\a} = g_{\b\b} = g_{\a\b}$, then the non-linear terms depend only on the total density $n_+ = n_\a + n_\b$ and this simplifies:

$$
  \begin{pmatrix}
    \frac{\hbar^2 (k_x + k_R)^2}{2m} - \frac{\delta}{2} & \frac{\Omega}{2}\\
    \frac{\Omega}{2} & \frac{(k_x - k_R)^2}{2m} + \frac{\delta}{2}
  \end{pmatrix}
  \cdot
  \begin{pmatrix}
    \sqrt{n_\a}\\
    \sqrt{n_\b}
  \end{pmatrix}
  = \left(\mu - \frac{\hbar^2k_y^2}{2m} - gn_+\right)
  \begin{pmatrix}
    \sqrt{n_\a}\\
    \sqrt{n_\b}
  \end{pmatrix}.
$$

This equation can be diagonalized, giving rise to two independent "bands" with dispersion:

$$
  \frac{E_{\pm}(\hbar k k_R)}{2E_R} = \frac{k^2 + 1}{2} \pm \sqrt{(k-d)^2+w^2}, \\
  E_R = \frac{\hbar^2k_R^2}{2m}, \qquad
  k = \frac{k_x}{k_R}, \qquad
  d = \frac{\delta}{4E_R}, \qquad
  w = \frac{\Omega}{4E_R}.
$$

This dispersion relationship is implemented in the code, and has a minimum at quasi-momentum $k_0$ where $E_-'(\hbar k_0 k_R) = 0$, where $k_0 = (k_0-d)/\sqrt{(k_0-d)^2+w^2}$.

+++

## Single-Band Model

+++

In many cases, if the system is not excited to violently, one can simplify the dynamics by considering a single band theory with a modified dispersion:

$$
  \I\hbar \pdiff{}{t} \psi(\vect{r}, t) 
  = \left(E_-(\op{p}_x) + \frac{\op{p}_y^2}{2m}
    + gn(\vect{r}, t) 
    + V(\vect{r}, t)
  \right)\psi(\vect{r}, t).
$$

To connect this single band model with the two component model, one can use the following spin–quasi-momentum mapping which relates the local quasi-momentum $k$ to the bare-particle densities that make up the homogeneous state with this quasi-momentum.

$$
  n_a = n\cos\theta, \qquad
  n_b = n\sin\theta, \qquad
  \tan\theta = \frac{-(k-d) + \sqrt{(k-d)^2 + w^2}}{w}.
$$

The second important point is that the velocity of the quasi-particles in this system are now given by the dispersion with the phase and group velocities:

$$
  v_p = \frac{E_-(p_x)}{p_x} \qquad
  v_g = E_-'(p_x),\qquad
  p_x = \frac{-\I\hbar}{\psi}\pdiff{\psi}{x},
$$

where $p_x$ is the local quasi-momentum of the state in the $x$ direction.

+++

# Demonstrations

```{code-cell} ipython3
%pylab inline
import time
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.physics import gpe;reload(gpe)
from super_hydro.physics import soc;reload(soc)
from super_hydro.client import canvas_widget;reload(canvas_widget)
from super_hydro.client import notebook;reload(notebook)

notebook.run(#run_server=False,
             dt_t_scale=0.4,
             v_v_c=0.9,
             model='gpe.BECFlow', Nx=256//4, Ny=256//4)
#notebook.run(model='gpe.BECFlow', Nx=256//4, Ny=256//4)
#notebook.run(model='soc.SOC2', Nx=256, Ny=8)
#app = notebook.get_app(model='soc.SOC1', Nx=64, Ny=32)
#app.run()
#notebook.run(model='gpe.BEC', Nx=32, Ny=32)
#app = notebook.get_app()
```

```{code-cell} ipython3
print(app._running)
app._running = False
app._msgs
```

```{code-cell} ipython3
import IPython
ip = IPython.get_ipython()
res = ip.kernel.do_one_iteration()
res.done()
```

```{code-cell} ipython3
import signal
signal.__file__
```

```{code-cell} ipython3
import time
from mmf_setup.set_path import hgroot
from super_hydro.contexts import NoInterrupt
with NoInterrupt() as interrupted:
    while True:
        print("Hi")
        time.sleep(1)
```

```{code-cell} ipython3
import time
print(signal.getsignal(2))
while True:
    print("hi")
    time.sleep(1)
```

```{code-cell} ipython3
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.client import notebook;reload(notebook)
from super_hydro.server import server;reload(server)
from mmfutils.contexts import NoInterrupt
NoInterrupt.register()
interrupted = NoInterrupt()
NoInterrupt.is_registered()
#s = server.run(args='', block=False, interrupted=interrupted)
```

```{code-cell} ipython3
#### Danger Will!  Jupyter mucks with the signals.
import signal
signal.getsignal(2)
#NoInterrupt.is_registered()
```

```{code-cell} ipython3
import time
while True:
    print(interrupted._signal_count)
    time.sleep(1)
```

```{code-cell} ipython3
import signal
signal.getsignal(2)
import pdb
pdb.run('NoInterrupt.register()')
```

```{code-cell} ipython3
import signal
h = signal.getsignal(signal.SIGTERM)
h = interrupted._original_handlers[signal.SIGTERM]
interrupted.unregister()
```

```{code-cell} ipython3
import os, signal
try:
    os.kill(os.getpid(), signal.SIGTERM)
except:
    pass
```

```{code-cell} ipython3
app._density.rgba = app.get_rgba_from_density(app.density)
```

```{code-cell} ipython3
interrupted.unregister()
h = signal.getsignal(signal.SIGTERM)
signal.signal?
```

## Super-Solid

```{code-cell} ipython3
%pylab inline
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.physics import gpe;reload(gpe)
from super_hydro.physics import gpe2;reload(gpe2)
from super_hydro.contexts import NoInterrupt
from super_hydro.client import notebook

notebook.run(model='gpe2.SuperSolid2', Nx=64, Ny=16)
```

# Technical Notes

+++

In order to make sure that the system is strictly periodic, we must make sure that the
