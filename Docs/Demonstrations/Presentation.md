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

```{code-cell}
:init_cell: true

%%javascript
IPython.OutputArea.prototype._should_scroll = function(lines) { return false; }
```

## Vortex Pinning

```{code-cell}
---
slideshow:
  slide_type: slide
---
from mmf_setup.set_path import hgroot
from super_hydro.clients import notebook

notebook.run(
    model="gpe.BEC",
    Nx=128,
    Ny=128,
    cooling=0.005,
    cooling_steps=100,
    finger_r0=2.0,
    dt_t_scale=2.0,
    finger_V0_mu=0.8,
    finger_x=0.7,
    winding=40,
    #network_server=False,
)
```

## Flow

```{code-cell}
from mmf_setup.set_path import hgroot
from super_hydro.clients import notebook
notebook.run(model='gpe.BECFlow', Nx=128, Ny=32, tracer_particles=0)
```

## Breathers

```{code-cell}
from mmf_setup.set_path import hgroot
from super_hydro.clients import notebook
notebook.run(model='gpe.BECBreather',
             R=0.3, a_HO=0.05, 
             Nx=32*8, Ny=32*8,
             dt_t_scale=2.0,
             tracer_particles=0,
             Nshape=3)
```

```{code-cell}

```
