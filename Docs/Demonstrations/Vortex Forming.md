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

# Vortex Demonstration

+++

## Introduction

```{code-cell} ipython3
%%javascript
IPython.OutputArea.prototype._should_scroll = function(lines) { return false; }
```

```{code-cell} ipython3
# Does not work on CoLab yet
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.physics import gpe;reload(gpe)
from super_hydro.client import notebook;reload(notebook)
notebook.run(model='gpe.BECVortices',
             Nx=32*4, Ny=32*4, dt_t_scale=1,
             cooling=1,
             bump_N=15,
             bump_h=0.1,
             tracer_particles=0,
             network_server=False,
            )
```

$$
  \I \op{\dot{\psi}} = (\op{H}_0 + \op{H}_c)\ket{\psi}\\
  E = \braket{\psi|\op{\Omega}|\psi}, \qquad
  \op{\Omega} = \op{H}_0 - \Omega \op{L}_z\\
  \\
  \dot{E} = \I\braket{\psi|[(\op{H}_0 + \op{H}_c), \op{\Omega}]|\psi}\\
  \dot{E} = \I\Tr \Bigl(\op{R}[(\op{H}_0 + \op{H}_c), \op{\Omega}]\Bigr)\\
  \dot{E} = \I\Tr \Bigl((\op{H}_0 + \op{H}_c)[\op{\Omega},\op{R}]\Bigr)
  = \I \braket{\psi|[\op{H}_0,\op{\Omega}]|\psi}
  + \I\Tr \Bigl(\op{H}_c[\op{\Omega},\op{R}]\Bigr)
$$

+++

$$
  \op{H}_c = - \I [\op{R}, \op{\Omega}]\\
  \op{H}_c = \op{V}_c + \op{K}_c
$$

+++

$$
  \ket{\psi(t+\d{t})} = e^{(\op{H}+\op{H_c})\d{t}/\I}\ket{\psi} 
  ???????????\approx
  e^{\op{K}\d{t}/2\I}e^{\op{V}\d{t}/\I}e^{\op{K}\d{t}/2\I}\ket{\psi}
$$

+++

$$
  \op{H}_c = \I [\op{H}_0, \ket{\psi}\bra{\psi}]\\
  V_x(x) = \braket{x|[\op{H}, \ket{\psi}\bra{\psi}]|x}
$$

```{code-cell} ipython3

```
