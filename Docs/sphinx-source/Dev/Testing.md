---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.13.8
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

Testing
=======

# Server

The server can be started from the command-line.

As follows:

```bash

```

# Minimal Example

As a minimal example, we launch and start a server, then connect with a minimal client,
then terminate the server from the client.

```bash
```


This document has some tests that can be run as a notebook.

```{code-cell} ipython3
:init_cell: true

%load_ext autoreload
import mmf_setup;mmf_setup.nbinit()
```

```{code-cell} ipython3
%autoreload
import pprint
import super_hydro.server.server
import super_hydro.clients.minimal
```

```{code-cell} ipython3
# Start a local server
app = super_hydro.clients.minimal.run(run_server=True, network_server=False)
try:
    pprint.pprint(app.server.get_available_commands())
finally:
    app.quit()
```

```{code-cell} ipython3
# Start a local server
app = super_hydro.clients.minimal.run(run_server=True, network_server=False)
cmds = app.server.get_available_commands()
try:
    for param in cmds["get"]:
        val = app.server.get([param])
        assert val is not None
        print(f"{param}={val}"")
finally:
    app.quit()
```

```{code-cell} ipython3
# Connect to a running network server
app = super_hydro.clients.minimal.run(run_server=False, network_server=True,
                                      opts=dict(port=27372))
```

```{code-cell} ipython3
app.opts
```

```{code-cell} ipython3
app.server.get_available_commands()
```

```{code-cell} ipython3
from super_hydro.physics import gpe
from super_hydro.server import server
parser = server.config.get_server_parser()
opts, other_args = parser.parse_known_args(args=[])
opts.State = gpe.BEC
s = server.Server(opts=opts)
s.get_available_commands()
```

```{code-cell} ipython3
notebook.run(model='gpe.BECFlow',
             R=0.3, a_HO=0.04,
             dt_t_scale=0.5,
             Nx=32*8, Ny=32*8, 
             Nshape=5,
             cooling=1e-10,
             tracer_particles=0,
             #network_server=False,
             random_phase=True,
            )
```

```{code-cell} ipython3
%%javascript
IPython.OutputArea.prototype._should_scroll = function(lines) { return false; }
```

```{code-cell} ipython3
# Does not work on CoLab yet
from mmf_setup.set_path import hgroot
from importlib import reload
from super_hydro.physics import gpe;reload(gpe)
from super_hydro.clients import notebook;reload(notebook)
```

```{code-cell} ipython3
notebook.run(network_server=True,
             run_server=False,
             )
```

```{code-cell} ipython3

```
