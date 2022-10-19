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

Here we explore properties of the HTML5 Canvas.

```{code-cell} ipython3
%%javascript
IPython.OutputArea.prototype._should_scroll = function(lines) { return false; }
```

# Explicit

+++

We start with some explicit manipulations of a canvas.  This works, but I don't know how to get the data from python to javascript easily.  I can do it with `display(Javascript(...))` but this is slow.

```{code-cell} ipython3
%matplotlib inline
import numpy as np, matplotlib.pyplot as plt
from matplotlib import cm
x = np.linspace(-3,3,200)[:, None]
y = np.linspace(-1.5,1.5,100)[None, :]
z = np.exp(-(x**2-1)**2 - 2*(y**2-0.5)**2 - (x-0.2)*y)
plt.pcolormesh(x.flat, y.flat, z.T)
```

```{code-cell} ipython3
%%html
<style type="text/css">
    canvas {
        border: 1px solid black;
    }
</style>
<canvas></canvas>
```

Here is some minimal code to draw an image to this canvas.  Note: for this to work, the canvas size must match the data.

```{code-cell} ipython3
from IPython.display import Javascript
template = """
var canvas = document.querySelector('{selector:s}');
canvas.width = {width};
canvas.height = {height};
var ctx = canvas.getContext('2d');
var raw_data = new Uint8ClampedArray([{int_data}])
var image_data = new ImageData(raw_data, {Nx})
ctx.imageSmoothingQuality = "high"
ctx.imageSmoothingEnabled = false
ctx.putImageData(image_data, 0, 0);
ctx.drawImage(canvas, 
              0, 0, {Nx}, {Ny}, // Use full source image.
              0, 0,             // Put it in the upper left corner
              {width}, {height} // Scale up if needed
              );
"""

def display_js(z, 
               width=None, height=None,
               selector='canvas',
               colormap=cm.viridis):
    Nx , Ny = z.shape
    if width is None: width = Nx
    else: assert width >= Nx
    if height is None: height = Ny
    else: assert height >= Ny
    # Here s how we get the data for the image.  We need to flip along y
    # and take the transpose.
    data = colormap(z[:, ::-1].T/z.max(), bytes=True).astype(int).ravel()
    int_data = ",".join(map(str, data))
    return Javascript(
        template.format(selector=selector, int_data=int_data, 
                        Nx=Nx, Ny=Ny,
                        width=width, height=height))

js = display_js(z, width=200)
display(js)
```

* https://gist.github.com/sanbor/e9c8b57c5759d1ff382a

```{code-cell} ipython3
%%html
<style type="text/css">
    canvas {
        border: 1px solid black;
    }
</style>
<canvas class="mycanvas"></canvas>
```

```{code-cell} ipython3
from super_hydro.physics.testing import HO
from super_hydro.contexts import FPS
ho = HO(Nxy=(256,64))
with FPS() as fps:
    for frame in fps:
        t = 0.1*frame
        psi = ho.get_psi(t=t)
        n = abs(psi)**2
        display(display_js(n, selector="canvas.mycanvas"))
fps
```

```{code-cell} ipython3
%%javascript
var canvas = document.querySelector('canvas');
canvas.width = 200;
canvas.height = 200;
var ctx = canvas.getContext('2d');
var raw_data = new Uint8ClampedArray([255,0,0,255, 0,255,0,255, 0,0,255,255, 
                                      255,255,0,255, 0,255,255,255, 255,0,255,255, 
                                      255,255,255,255, 0,255,0,255, 0,0,255,255])
var image_data = new ImageData(raw_data, 3)
canvas.width = 100;
canvas.height = 100;
ctx.imageSmoothingQuality = "high"
ctx.imageSmoothingEnabled = false
ctx.putImageData(image_data, 0, 0);
ctx.drawImage(canvas, 
              0, 0, 3, 3, 
              0, 0, canvas.width, canvas.height);
```

```{code-cell} ipython3
%%javascript
var kernel = IPython.notebook.kernel;
function handle_output(data) {
    console.log(data.msg_type);
    debugger;
    raw_data = data.content.text;
}
var callbacks = {iopub : {output : handle_output,}}
kernel.execute("print(_data)", callbacks)
```

```{code-cell} ipython3
%%javascript
debugger;
var data = new kernel.execute('print(data)');
var image_data = new ImageData(raw_data, 100);
ctx.putImageData(image_data, 0, 0);
```

# Widget

+++

Here is our widget.  This is not installed - we load and execute all of the javascript explicitly.

```{code-cell} ipython3
import mmf_setup.set_path.hgroot
from importlib import reload
from super_hydro.clients import canvas_widget
```

```{code-cell} ipython3
reload(canvas_widget)
#canvas_widget.display_js()   # Load javascript
canvas = canvas_widget.Canvas()
display(canvas)

from matplotlib import cm
import numpy as np
x = np.linspace(-2,2,200)[:, None]
y = np.linspace(-2,2,100)[None, :]
z = np.exp(-x**2 - (y**2-x)**2)
data = cm.viridis(z, bytes=True)
canvas.width = 1000
canvas.height = 1000
canvas.rgba = data
```

```{code-cell} ipython3
import time
from matplotlib import cm
import numpy as np
Nx, Ny = (512, 512)
x = np.linspace(-2,2,Nx)[:, None]
y = np.linspace(-2,2,Ny)[None, :]

def get_data(t):
    z = np.exp(-x**2 - (y**2-x*np.cos(t))**2)
    return cm.viridis(z, bytes=True)

tic = time.time()
Nt = 100
for t in np.linspace(0, 10*np.pi, Nt):
    canvas.rgba = get_data(t)
print(f"{Nt/(time.time() - tic):.1f}fps")
    
```

```{code-cell} ipython3

```

```{code-cell} ipython3
from super_hydro.physics.testing import HO
from super_hydro.contexts import FPS
from matplotlib import cm
import numpy as np

Nx, Ny = (512, 512)
x = np.linspace(-2,2,Nx)[:, None]
y = np.linspace(-2,2,Ny)[None, :]

def get_data(t):
    z = np.exp(-x**2 - (y**2-x*np.cos(t))**2)
    return cm.viridis(z, bytes=True)

tic = time.time()
Nt = 100
ts = np.linspace(0, 10*np.pi, Nt)
with FPS(frames=Nt) as fps:
    for frame in fps:
        t in :
    canvas.rgba = get_data(t)
print(f"{Nt/(time.time() - tic):.1f}fps")
    
```

```{code-cell} ipython3
from matplotlib import cm
import numpy as np
x = np.linspace(-2,2,100)[:, None]
y = np.linspace(-2,2,100)[None, :]
z = np.exp(-x**2 - (y**2-x)**2)
data = cm.viridis(z, bytes=True)
canvas.width = 256
canvas.height = 256
canvas.rgba = data
```

# ipycanvas

```{code-cell} ipython3

```
