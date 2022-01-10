---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.10.3
kernelspec:
  display_name: Python 3 (super_hydro)
  language: python
  name: super_hydro
---

```{code-cell} ipython3
%pylab inline --no-import-all
import mmf_setup;mmf_setup.nbinit()
```

For an analytic example, consider the SEQ for an HO in a rotating frame with angular velocity $\Omega = \omega$ equal to the trapping frequency:

$$
  \I\hbar \dot{\psi} = \left\{
    \frac{-\hbar^2\nabla^2}{2m} + \frac{m\omega^2r^2}{2} - \overbrace{\hbar\omega \left(x\pdiff{}{y} - y\pdiff{}{x}\right)}^{\Omega \op{L}_{z}}\right\}\psi.
$$

This should have as a family of solutions:

$$
  \psi(x, y, t) = e^{\I\mu t}\sqrt{\frac{m\omega}{\pi \hbar}}
  \exp\left\{
    -m\omega\frac{(x-R)^2+y^2}{2\hbar}
  \right\}.
$$

```{code-cell} ipython3
from multiprocessing import Process
from mmfutils.contexts import NoInterrupt
from mmfutils.plot import imcontourf
from IPython.display import clear_output
import time

class HOServer(Process):
    """Simple computation with superfluid rotating in an HO trap.
    
    This is an exact solution to test performance etc.
    """
    def __init__(self, Nxy=(256,)*2, Lxy=(10., 10.)):
        self.Nxy = Nxy
        self.Lxy = Lxy
        self.xy = x, y = np.meshgrid(
            *[np.arange(_N) * (_L/_N) - _L/2
              for (_N, _L) in zip(Nxy, Lxy)],
            sparse=True, indexing='ij')
        
        self._z = x + 1j*y
        self.w = 1.0
        self.r0 = 2.5
    
    def get_density(self, t):
        """Return the exact solution at time `t`."""
        r = abs((np.exp(-1j*self.w*t) * self._z - self.r0))
        return np.exp(-r**2)
```

```{code-cell} ipython3
# Check the maximum possible frame-rate
s = HOServer()

ts = np.linspace(0, 10, 100)
tic = time.time()
for t in ts:
    n = s.get_density(t)
toc = time.time()
print(f"maximum {len(ts)/(toc-tic):.2f}fps")
```

```{code-cell} ipython3
# See what we get with mpl
ts = np.linspace(0, 10, 100)
fig = plt.figure(figsize=(5,5))
NoInterrupt.unregister()
with NoInterrupt() as interrupted:
    x, y = s.xy
    tic = time.time()
    frame = 0 
    ax = plt.gca()
    for t in ts:
        if interrupted:
            break
        n = s.get_density(t)
        ax.cla()
        imcontourf(x, y, n)
        ax.set_aspect(1)
        toc = time.time()
        frame += 1
        plt.title(f"t={t:.2f}, {frame/(toc-tic):.2}fps")
        display(fig)
        clear_output(wait=True)
```

```{code-cell} ipython3
from matplotlib import cm
from super_hydro.widgets import Canvas, Label, VBox

def get_rgba(density):
    density = density
    array = cm.viridis(density/density.max())
    array *= int(255/array.max())  # normalize values
    rgba = array.astype(dtype='uint8')
    return rgba
```

```{code-cell} ipython3
# See what we get with Canvas

ts = np.linspace(0, 10, 100)
canvas = Canvas(name='density', width=300, height=300)
msg = Label(name='messages')

NoInterrupt.unregister()
display(VBox([msg, canvas]))
```

```{code-cell} ipython3
with NoInterrupt() as interrupted:
    x, y = s.xy
    tic = time.time()
    frame = 0 
    for t in ts:
        if interrupted:
            break
        n = s.get_density(t)
        canvas.rgba = get_rgba(n)
        toc = time.time()
        frame += 1
        msg.value = f"t={t:.2f}, {frame/(toc-tic):.2f}fps"
```

# WebSockets

```{code-cell} ipython3
%%HTML
 <!DOCTYPE html>
  <meta charset="utf-8" />
  <title>WebSocket Test</title>
  <script language="javascript" type="text/javascript">

  var wsUri = "wss://echo.websocket.org/";
  var output;

  function init()
  {
    output = document.getElementById("output");
    testWebSocket();
  }

  function testWebSocket()
  {
    websocket = new WebSocket(wsUri);
    websocket.onopen = function(evt) { onOpen(evt) };
    websocket.onclose = function(evt) { onClose(evt) };
    websocket.onmessage = function(evt) { onMessage(evt) };
    websocket.onerror = function(evt) { onError(evt) };
  }

  function onOpen(evt)
  {
    writeToScreen("CONNECTED");
    doSend("WebSocket rocks");
  }

  function onClose(evt)
  {
    writeToScreen("DISCONNECTED");
  }

  function onMessage(evt)
  {
    writeToScreen('<span style="color: blue;">RESPONSE: ' + evt.data+'</span>');
    websocket.close();
  }

  function onError(evt)
  {
    writeToScreen('<span style="color: red;">ERROR:</span> ' + evt.data);
  }

  function doSend(message)
  {
    writeToScreen("SENT: " + message);
    websocket.send(message);
  }

  function writeToScreen(message)
  {
    var pre = document.createElement("p");
    pre.style.wordWrap = "break-word";
    pre.innerHTML = message;
    output.appendChild(pre);
  }

  window.addEventListener("load", init, false);

  </script>

  <h2>WebSocket Test</h2>

  <div id="output"></div>
```

```{code-cell} ipython3
%%javascript
var wsUri = "wss://echo.websocket.org/";
var output;
var websocket;

function init(){
  output = document.getElementById("my_output");
  testWebSocket();
}

function testWebSocket(){
  debugger;
  websocket = new WebSocket(wsUri);
  websocket.onopen = function(evt) { onOpen(evt) };
  websocket.onclose = function(evt) { onClose(evt) };
  websocket.onmessage = function(evt) { onMessage(evt) };
  websocket.onerror = function(evt) { onError(evt) };
}

function onOpen(evt){
  writeToScreen("CONNECTED");
  doSend("WebSocket rocks");
}

function onClose(evt){
  writeToScreen("DISCONNECTED");
}

function onMessage(evt){
  writeToScreen('<span style="color: blue;">RESPONSE: ' + evt.data+'</span>');
  websocket.close();
}

function onError(evt){
  writeToScreen('<span style="color: red;">ERROR:</span> ' + evt.data);
}

function doSend(message){
  writeToScreen("SENT: " + message);
  websocket.send(message);
}

function writeToScreen(message){
  var pre = document.createElement("p");
  pre.style.wordWrap = "break-word";
  pre.innerHTML = message;
  output.appendChild(pre);
}

//window.addEventListener("load", init, false);
init();
```

```{code-cell} ipython3
%%javascript
var wsUri = "wss://echo.websocket.org/";
new WebSocket(wsUri);
```

<div id="my_output"></div>

```{code-cell} ipython3
%%javascript
function writeToScreen(message){
  var pre = document.createElement("p");
  pre.style.wordWrap = "break-word";
  pre.innerHTML = message;
  output.appendChild(pre);
}
//init();
element.text("helo");
element.text("hell");
//pre.innerHTML = "Hello";
var pre = document.createElement("p");
pre.style.wordWrap = "break-word";
pre.innerHTML = "Hi";
element.appendChild(pre);
```

```{code-cell} ipython3
from IPython.display import HTML
s = HTML(r"""
<!DOCTYPE html>
<meta charset="utf-8" />
<title>WebSocket Test</title>
<h2>WebSocket Test</h2>
<div id="output"></div>
<script language="javascript" type="text/javascript">
init();
element.text("Hell");
</script>
""")
display(s)
```

```{code-cell} ipython3

```
