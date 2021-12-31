The GPE in 5 Steps
==================

Here we describe how to numerically solve time-dependent Schrödinger-like equations:

\begin{gather*}
  \I\hbar \pdiff{}{t}\psi(\vect{r}, t) = \left(
    \frac{-\hbar^2\vect{\nabla}^2}{2m}
    +
    V(\vect{r}, t; \psi)
  \right)\psi(\vect{r}, t)
\end{gather*}

Here we describe the superfluid with a "condensate wavefunction" $\psi(\vect{r}, t)$ which has
the following hydrodynamic interpretation:

\begin{gather*}
  \psi(\vect{r}, t) = \sqrt{n(\vect{r}, t)} e^{\I \phi(\vect{r}, t)}.
\end{gather*}

Here $n(\vect{r}, t)$ is the number density of particles at position $\vect{r}$ and time
$t$.  The gradient of the phase of the condensate wavefunction is related to the
group-velocity of the superfluid:

\begin{gather*}
  \vect{v}_{\text{group}} = \frac{\hbar}{m}\vect{\nabla}\phi(\vect{r}, t).
\end{gather*}

Expressing the condensate wavefunction in this way, we effect a [Madelung
transformation] and obtain the following equivalent hydrodynamic description:

\begin{gather*}
  \pdiff{}{t}n(\vect{r}, t) + \vect{\nabla}\cdot\vect{j}(\vect{r}, t),\\
  m D_t \vect{v}(\vect{r}, t) = -\vect{\nabla}\left(
    \frac{-\hbar^2}{2m}\frac{\vect{\nabla}\sqrt{n(\vect{r}, t)}}{\sqrt{n(\vect{r}, t)}}
    + 
    V(\vect{r}, t)
  \right)
\end{gather*}

where $\vect{j}(\vect{r}, t)$ is the particle number current:

\begin{gather*}
  \vect{j}(\vect{r}, t) = n(\vect{r}, t) \vect{v}(\vect{r}, t),  
\end{gather*}

and $D_t$ is the "material derivative" or "covariant derivative" which simply accounts
for the fact that the fluid is moving:

\begin{gather*}
  D_t f(\vect{r}, t) = \pdiff{}{t}f(\vect{r}, t) 
  + \vect{v}(\vect{r}, t)\cdot\vect{\nabla}f(\vect{r}, t).
\end{gather*}

The first equation in the hydrodynamic formulation is simply the statement of
conservation: particles are neither created nor destroyed.  The second is simply the
hydrodynamic form of Newton's law $m\vect{a} = \vect{F} = - \vect{\nabla}V$.  Since we
work at $T=0$, the effective potential $V(\vect{r}, t)$ includes both any external
potentials, as well as the $gn(\vect{r}, t) \equiv \mu(\vect{r}, t) = \mathcal{E}'(n)$,
which is the thermodynamic chemical potential -- the derivative of the energy density
$\mathcal{E}(n) = gn^2/2$.  At finite temperature, this term should be replaced by the
appropriate enthalpy.

All of the quantum effects are contained in the remaining term

\begin{gather*}
  Q = \frac{-\hbar^2}{2m}\frac{\vect{\nabla}\sqrt{n(\vect{r}, t)}}{\sqrt{n(\vect{r}, t)}}
\end{gather*}

which is sometimes called the [quantum pressure]. For example, as we shall see in many
of the demonstrations, superfluid vortices have quantized circulation where the
wavefunction phase winds by integer multiples of $2\pi$.  This property is manifest in
the wavefunction formulation where $\psi(\vect{r}, t)$ must be single-valued and
smooth.  A vortex at the origin would thus have the general form

\begin{gather*}
    \psi(\vect{r}) \propto f(r) e^{\I n \theta}
\end{gather*}

where $n$ is the integer circulation, and $f(r) \propto r$ vanishes at the core,
otherwise the wavefunction could not smoothly be single-valued.

This quantization seems to be missing from the hydrodynamic formulation, but is present
in the fact that the quantum pressure $Q \propto 1/r$ diverges in the vortex core.
These divergences must exactly cancel similar divergences in the velocity $v \propto
1/r$: this matching and cancellation of divergences enforces vortex quantization, but is
tricky to manage in the hydrodynamic formulation.  It follows naturally from the
wavefunction evolution.

[quantum pressure]: 
[enthalpy]: 
