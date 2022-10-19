---
jupytext:
  formats: ipynb,md:myst
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

# Super-Hydro Demonstration List

+++

Here is a list of the existing demonstrations.  The default demonstration should be able to be run here, but follow the link to the appropriate notebook for details and many more examples.  Just execute the cells to run the default demonstration.

*(If parts of the demonstration are hidden in a scrolling output cell, execute the following cell which will disable scrolling making it possible to view the entire explorer.)*

```{code-cell} ipython3
%%javascript
// Execute this cell to suppress Jupyter output scrolling.
IPython.OutputArea.prototype._should_scroll = function(lines) { return false; }
```

## [Breathers.ipynb](Breathers.ipynb)

```{code-cell} ipython3
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.physics import gpe
from super_hydro.clients import notebook
from importlib import reload;reload(notebook)

notebook.run(
    model="gpe.BECBreather",
    R=0.3,
    a_HO=0.04,
    dt_t_scale=0.5,
    Nx=32 * 8,
    Ny=32 * 8,
    Nshape=3,
    cooling=1e-10,
    tracer_particles=100,
    network_server=False,
)
```

```{code-cell} ipython3

```
