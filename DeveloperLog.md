To Do:
* [ ] Client does not accept arguments like `--help` or `--shutdown`.
* [ ] Client-launched servers should maybe shutdown if no clients are connected?
* [ ] Maybe put all flask_client stuff together?  Including js which is now in `static/js`?
* [ ] Autosummary does not include interfaces... see `super_hydro.interfaces.rst` and
      `module.rst`.
* [ ] Another interface for tracer particles with `Lxy` and `xy`?

19 Oct 2022
===========
The FPS counter is about a factor of 2 off of the sync() value.  Need to check.  Mouse
works, but really slows down the interface.


18 Oct 2022
===========
There is a serious install issue on Mac OS X ARM processors.  Somehow `apr shell` subs
out the correct openssl library (osx-64) and replaces it with the arm library, which
fails (since we are using rosetta).  Not sure how to fix.  Manually replacing works:
`conda install pkgs/main/osx-64::openssl`

The key feature of our Canvas widget is that at the end of updating the rgba data in the
Javascript function `update_rgba()`, we process hooks allowing us to callback to
python.  To use the IPyCanvas widget, we need a similar hook.

Here is the current notebook client event loop.  There are three files involved:
* canvas_widget.js: Defines the javascript for the widget.  This calls the python code
  by sending an "update" message.
* canvas_widget.py: Python side of the widget. This allows the notebook client to
  register various handlers.
* notebook.py: The notebook client.  Everything starts with a call to `run()` which
  starts one of two event loops:
  * `browser_control == False`:  Here we just repeatedly call NotebookApp.on_update().
    This will get the data and draw the updates, but locks up the Jupyter Notebook UI so
        there is no way for the use to control things with the widgets.
  * `browser_control == True`: Here we register a callback to Canvas.on_update() with
    the Canvas._density widget.  Then we call Canvas.on_update() which gets the density,
    updating the _density widget, calling NotebookApp.on_update() etc. until done.  We then
    just run a loop that runs kernel.do_one_iteration() until interrupted.
    * MMF: should we unregister Canvas.on_update from Canvas._density when done?

The client is driven by calls to Canvas.on_update() which gets the density array from
the server
  
  


Initialization:
* Canvas.on_msg() -> Canvas._handle_update_request

* Canvas.on_displayed -> Canvas._display_js_callback -> display(canvas_widget.js)  ->
* render() -> start() -> requestAnimationFrame -> send_update_request -> 
* Canvas._handle_update_request -> Canvas.update() -> Canvas._update_handlers()


canvas_widget.js: (js)
canvas_widget.py:


* Canvas._handle_update_request

Comments:
* The key callback in our current loop that enables browser control is the `on_update`
  event on the widget which triggers the callback to Python.  Is there a similar event
  in the IPyCanvas widget?

Recommended changes:
* Since getting the density is a big thing, this should not be hidden in a property.
  Replace with a call get_density().




7 July 2022
===========
* [ ] IPyCanvas is a little slow, but not bad, and very flixible.  Replace our canvas
      widget with something that can use this.  We will need a separate bit of js to do
      the updates.

27 May 2022
===========
* Offline environment fails even though required packages are installed.  Check: `make
  init` might not have been run... also having flask errors.
  ```
  $ apr shell
  Collecting package metadata (current_repodata.json): ...working... failed
  CondaHTTPError: ...
  ...
  missing requirement to run this project: The project needs a Conda environment containing all required packages.
    Conda environment is missing packages: conda-forge::pyfftw, ruamel-yaml
  $ ap list-packages
  Conda packages for environment 'super_hydro':

  anaconda-project>=0.10.1
  conda-forge::pyfftw
  pip
  poetry
  python=3.9

  Pip packages for environment 'super_hydro':

  ruamel-yaml
  $ conda activate envs super_hydro
  $ conda list
  ...
  pyfftw                    0.12.0           py39h047060a_2    conda-forge
  ...
  ruamel-yaml               0.17.21                  pypi_0    pypi
  ...
  ```

  1. Why is this failing?  How can we quickly find out what packages are requested?
  2. How to prevent issues?  (Maybe `anaconda-project archive`?)
  3. Add `make offline` which creates all environments for offline work.

* `import flask` fails with `ImportError: cannot import name 'escape' from 'jinja2')

**Tracer Particle Enhancements**
* We can get the velocity for a 1024^2 grid while keeping 500fps, so we should ether
  compute the tracer-particles completely on the server, or just get $\psi$ and don't
  slow the server down at all.
* It looks like in the current code, it is the computation of the tracers (server) that
  is slowing things down...  Also suggests doing this on the client.

2 May 2022
==========
* To Do:
  * Make `steps` a model argument rather than passing directly to the server (different
    models may want different steps).
  * Test CLI.

25 Apr 2022
===========
* How to run `ctx = super_hydro(test_cli=True)` for debugging?  Hack:
  
  ```python
  from click.testing import CliRunner
  from super_hydro import cli
  runner = CliRunner()
  result = runner.invoke(cli.super_hydro, ['--test-cli'])
  ctx = cli._testing['ctx']
  kw = cli._testing['kw']
  ```

* Check documentation and think about how clients will connect to or launch servers.
  Currently we have specified that they run locally.  Where does the flask client run?
  Can we use the same port number?
* Allow the following to show model help: `apr super_hydro --help testing.HelloWorld`:
  * This seems [hard to
    do](https://click.palletsprojects.com/en/8.1.x/api/?highlight=invoked_subcommand#click.Context.invoked_subcommand).
    See https://github.com/pallets/click/commit/5fc29baf75897d594fe06ba085955d8068e22554.
    Instead, just enable `add_help_option=True`, then `apr super_hydro
    testing.HelloWorld --help` will work.




13 Jan 2022
===========
* `flask.py`: `res = server.server.get(finger_vars)` drops fps from 50 to 15!  After
  some playing, it is clear that this is due to the `get()` calls, not the `set()`
  calls.  We revamped the server to cache results.  Much better, but still some client
  side issues.
* `flask_socketio.SocketIO(self.app, async_handlers=False)` was very important -
  otherwise emit messages got mucked up.  Not exactly sure why.  Try with BEC to see.

* Performance is still bad: Notebook client runs much faster than Flask client.  Not
  sure why.  Flask client updates more frequently, but seems to block.  Might be because
  parameters like `dt_t_scale` are not properly updated.

12 Jan 2022
===========
* Continue refactoring JS for Flask Client.
  * Created minimal application "Hello World" as a minimal example.
    * Use to get orientation of canvas correct.
      * Python should send an `rgba` array to JS in the correct order.  I.e. whoever converts
        to the `rgba` array should do the transpositions.
    * Finger placement.
    * Framerate throttling.



* Notebook execution in docs messed due to [eventlet issue #670] conflicting with
  `asyncio` in Python 3.9.  Mocking the `eventlet` import fixed this
  [`autodoc_mock_imports = ["eventlet"]`].
  
9 Jan 2022
==========
Goals:
* Refactor Flask client so we can better test and benchmark performance.


The Flask client has two threads, the main client thread which responds to HTTP requests
from the interface, and various actions like button clicks etc., and then the
`push_thread` which calls `server.get_array()` and then uses `socketio.emit()` to send
an rgba array of bytes to the browser.

* `flask.py`: `push_thread()` -> `socket.emit("ret_array")`
* `model.html`: `socket.on('ret_trace')` -> `drawTracer()`

1. Can we get the javascript to run as an independent separate thread instead?


* Interface violations:
  * Flask client needs `get_sliders()` provided by ModelBase.
  * tracer particles needs `model.xy`

* There was an issue executing notebooks because of the global `_LOGGER =
  utils.Logger(__name__)` in `flask.py`.  This caused the following error:

```
WARNING: .../Dev/Flask.md
Traceback (most recent call last):
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/asyncio/selector_events.py", line 261, in _add_reader
    key = self._selector.get_key(fd)
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/selectors.py", line 193, in get_key
    raise KeyError("{!r} is not registered".format(fileobj)) from None
KeyError: '6 is not registered'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/site-packages/jupyter_cache/executors/basic.py", line 141, in execute
    yield self.execute_single(
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/site-packages/jupyter_cache/executors/basic.py", line 154, in execute_single
    result = single_nb_execution(
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/site-packages/jupyter_cache/executors/utils.py", line 51, in single_nb_execution
    executenb(
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/site-packages/nbclient/client.py", line 1093, in execute
    return NotebookClient(nb=nb, resources=resources, km=km, **kwargs).execute()
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/site-packages/nbclient/util.py", line 84, in wrapped
    return just_run(coro(*args, **kwargs))
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/site-packages/nbclient/util.py", line 47, in just_run
    loop = asyncio.get_event_loop()
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/asyncio/events.py", line 639, in get_event_loop
    self.set_event_loop(self.new_event_loop())
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/asyncio/events.py", line 659, in new_event_loop
    return self._loop_factory()
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/asyncio/unix_events.py", line 54, in __init__
    super().__init__(selector)
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/asyncio/selector_events.py", line 61, in __init__
    self._make_self_pipe()
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/asyncio/selector_events.py", line 112, in _make_self_pipe
    self._add_reader(self._ssock.fileno(), self._read_from_self)
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/asyncio/selector_events.py", line 263, in _add_reader
    self._selector.register(fd, selectors.EVENT_READ,
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/selectors.py", line 523, in register
    self._selector.control([kev], 0, 0)
TypeError: changelist must be an iterable of select.kevent objects
WARNING: autodoc: failed to import module 'notebook' from module 'super_hydro.clients'; the following exception was raised:
cannot import name 'DensityMixin' from 'super_hydro.clients.mixins' (/Users/mforbes/work/mmfbb/gpe-explorer/src/super_hydro/clients/mixins.py)
Exception ignored in: <function BaseEventLoop.__del__ at 0x10b58aaf0>
Traceback (most recent call last):
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/asyncio/base_events.py", line 683, in __del__
    self.close()
  File "/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/asyncio/unix_events.py", line 60, in close
    for sig in list(self._signal_handlers):
AttributeError: '_UnixSelectorEventLoop' object has no attribute '_signal_handlers'
/Users/mforbes/work/mmfbb/gpe-explorer/envs/super_hydro/lib/python3.9/site-packages/sphinx/util/logging.py:184: RuntimeWarning: coroutine 'NotebookClient.async_execute' was never awaited
  self.buffer = []
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
```


26 Dec 2021
===========
Need to include local versions so that we can work offline:
* [socket.io.js](https://cdnjs.cloudflare.com/ajax/libs/socket.io/3.0.4/socket.io.js)
* [math.min.js](https://cdnjs.cloudflare.com/ajax/libs/mathjs/3.3.0/math.min.js)
* [MathJax]


25 Dec 2021
===========
* Trying to get a simple `.. autosummary::` entry working for `Dev/Flask.md` but since I
  don't want to generate a toctree here (this is done in the `api` section), I can't
  find a way to customize the output.  Not sure if this is a bug.  For now, we will need
  to manually update the documentation if we add new classes/functions, or just refer to
  the API docs.
  
  After some exploration, it seems this is not possible.  There is an
  [autodocsumm](https://autodocsumm.readthedocs.io) module that helps, but it includes
  too much.  Maybe some combination of this and custom templates would work.



24 Dec 2021
===========
* The `templates` and `static` directories used are currently in the top level of the
  project.  Would like to change this, but for now it works.  I put the favicon there
  and modified the template.
  
23 Dec 2021
===========
* Running the flask client, I get an error `KeyError: 'favicon.ico'` from the code
  `Model = APP._models[cls]`.  This happens because browsers [often request
  `favicon.ico`](https://en.wikipedia.org/wiki/Favicon) to display.
  
  The default routing falls back to the model, which is why this error is happening
  here.  We should have a better fallback, and [provide a
  favicon](https://flask.palletsprojects.com/en/2.0.x/patterns/favicon/).
  
  I used [https://favicon.io/favicon-converter/](https://favicon.io/favicon-converter/)
  with our main vortex image.

22 Dec 2021
===========
* Autosummary generates summaries, but not the actual documentation for classes or
  functions... still need to figure out how to do this.
  
18 Dec 2021
===========
Tasks:
* Get documentation working.
* Understand and document architecture including Flask.
* Profile communications etc.
* Include GPE-based example (the module with pytimeode etc.)
* Simple 5-step to GPE (basis for video):
  * Finite Difference
  * Split Operator
  * Profile
  * FFT
  * CUDA
* SSH launch of server on penguin.
* Flask UI issues
  * Visual representation of potential.
  * Tracers (poor performance... draw on server.)
  * Interactivity (there is currently a lag between things like adjusting the cooling
    phase and the system responding).

Sat 9 Oct 2021
==============
Working on dependency resolution etc.  We should support the following cases:
1. Plain install with pip and poetry with `tests`, `docs`, `gpu`, and `fftw` options.
   These will only install with pip, so the user will be required to install other
   dependencies like CUDA for using the gpu.
2. Use [Conda] to install binary backends such as `cupy`, then pip/poetry on this.

   * Poetry can use the Conda environment.  Perhaps this could work, but there must be
     explicit instructions to first activate the conda environment, then to run poetry.
     Some questions:
     
     * Can we use `poetry env use` somehow to specify the conda environment for
       development?  I tried linking `.venvs -> envs/super_hydro`, the latter being
       created with `anaconda-project` but poetry complains:
       
       ```bash
       bash: .../.venv/bin/activate: No such file or directory
       ```
       
3. Anaconda-project is nice.  Can we also support this?
   * I can't seem to put `.` in the pip section.

Thu 16 July 2020
================
* Need to complete the IModel interface.
* Check the init() chain for Models
* Ignore "physics" in model name if provided.

Fri 25 Sept 2020
================
Made into an installable python package.

Tue 08 Dec 2020
===============
Flask Client loads class models for user-entered scripts via config file.
Finger Potential Click interaction implemented, "Pause"/"Start"/"Reset" work.
Shutdown issues appear to be corrected.
Beginning Flask Client documentation.

Remaining issues:
* preserve aspect ratio
* drag finger potential interaction
* sane cooling range and interpretation
* Running at high latency can result in overspooling computational servers


[eventlet issue #670]: <https://github.com/eventlet/eventlet/issues/670>
[`autodoc_mock_imports = ["eventlet"]`]: <https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html?highlight=mock#confval-autodoc_mock_imports>
