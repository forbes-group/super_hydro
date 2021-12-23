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
%%javascript
IPython.OutputArea.prototype._should_scroll = function(lines) { return false; }
```

```{code-cell} ipython3
# Does not work on CoLab yet
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.clients import notebook;reload(notebook)
#notebook.run(model='gpe.BEC', Nx=64, Ny=64, random_phase=False)
notebook.run(run_server=False)
```

```{code-cell} ipython3

```
