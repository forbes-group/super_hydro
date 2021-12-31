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

# Vortex "Ring"

```{code-cell}
%%javascript
IPython.OutputArea.prototype._should_scroll = function(lines) { return false; }
```

```{code-cell}
# Does not work on CoLab yet
from mmf_setup.set_path import hgroot
from super_hydro.clients import notebook
notebook.run(model='gpe.BECVortexRing', Nx=64, Ny=64, 
             tracer_particles=100, finger_V0_mu=0,
             random_phase=False)
```

```{code-cell}

```
