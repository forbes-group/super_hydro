Developer Notes
===============

## Developer Install

We use [Poetry] to manage environments and dependencies, however, [Conda] can be useful,
especially when trying to install GPU dependencies.  For primary development work you
should try to use [Poetry], falling back to [Conda] if needed for speed or to get binary
dependencies.

1. Install a virtual environment.  This can either be pure pure python or with [Conda]:
    * Pure Python:

        ```bash
        poetry env use python3.9
        ```
   * [Conda]:  If you want to use [Conda], first create an environment and activate it.
       We have an `anaconda-project.yaml` file which can be used to create appropriate
       [Conda] environments:

       ```bash
       anaconda-project prepare --refresh
       conda activate envs/super_hydro
       ```
      
       or

       ```bash
       anaconda-project prepare --env-spec super_hydro_gpu   # If you have an NVIDIA GPU
       conda activate envs/super_hydro_gpu
       ```

2. Use [Poetry] to install `super_hydro` with the `tests` and `docs` extras and
    optionally with the `fftw` or `gpu` extras if you have the FFTW libraries and/or
    NVIDIA Cuda libraries installed: 

    ```bash
    poetry install -E tests -E docs
    poetry install -E tests -E docs -E fftw  # If you have the FFTW libraries
    poetry install -E tests -E docs -E gpu   # If you have an NVIDIA GPU
    ```

    Note: If you are using [Conda], be sure to first `conda activate` the appropriate
    environment.  I do not know a way to get `poetry env use` to do this by default.

3. Run a shell and use `super_hydro`:

    ```bash
    poetry shell                     # If using pure poetry
    conda activate envs/super_hydro  # If using Conda
    ```


````{admonition} Jupyter Kernel
If you run [Jupyter] outside of the virtual environment, then you should install the `super_hydro`
kernel so it is available with your version of [Jupyter].  For example, the following
will register a kernel named `super_hydro` in your personal Jupyter configuration folder.

   ```
   jupyter kernelspec install $(poetry env info -p) --user --name=super_hydro
   ```

````

```
poetry run python3 -m ipykernel install --sys-prefix
```

If you need to add dependencies, use `poetry add` and then correct in `pyproject.toml`:

```bash
poetry add uncertainties
poetry add -D sphinx-autobuild
poetry update           # Update lock file
poetry install
```

You can then activate this with `poetry shell` for development work.





The development install process is specified in the [`Makefile`], but needs a few tools
installed:

* [Conda]: We use this for installing binary packages (makes working with the GPU easier
  for example).  I install a fairly minimal [Miniconda] base environment.
* [Poetry]: The [recommended approach](https://python-poetry.org/docs/#installation) for
    installing this is actually outside of the environment: 
    ```bash
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
    ```
* [`poetry2conda`]: This can then be installed with pip (optionally in your user folder
    with `--user` so it is available with multiple environments:
    ```bash
    python3 -m pip --user install poetry2conda
    ```


.  Currently this uses [Poetry] to
specify dependencies etc. in `pyproject.toml`, then uses [`poetry2conda`] to generate an
`environment-*.yml` file which can be used to create a [Conda] `super_hydro`
environment:

```bash
make conda-env
make conda-env-gpu    # Add cupy
```

### Conda

Some issues/questions related to the [Conda] `super_hydro` environment:

* Where should we create this?  Probably not in the user's base installation (which
  might be write-only), so we should probably allow the `--prefix ${CONDA_PREFIX}`
  option to be set.  (Maybe provide a `configure` script which allows this to be set?).
  To be able to activate this environment by name we need to run something like:
  
  ```bash
  conda config --append envs_dirs ${CONDA_PREFIX}
  ```
  
  Unfortunately, this update the global
  [env_dirs](https://docs.conda.io/projects/conda/en/latest/user-guide/configuration/use-condarc.html#specify-env-directories)
  path, which is the hard to remove (uninstall).  We should probably just rely on
  setting `CONDA_ENVS_PATH` as part of the environment.

````{admonition} Environment Activation
In the remainder of the documentation, we shall assume that the appropriate environment
is first activated with one of the following:

   ```
   poetry shell                # If using poetry
   conda activate super_hydro  # If using conda
   ```

````

## Running the Server

There are several options for running the computation server.

### Notebook Client

With the notebook interface, you can launch a server and view the results from a Jupyter
notebook.  Start a jupyter notebook server and visit
[Docs/Demonstrations/Contents%20(Start%20Here).ipynb](Docs/Demonstrations/Contents%20(Start%20Here).ipynb):

```bash
conda activate super_hydro
jupyter notebook "Docs/Demonstrations/Contents (Start Here).ipynb"
```

### Standalone Server

The computation server can also be started independently by running:

```bash
conda activate super_hydro
python bin/server
```

This will start a server listening on the port specified in `super_hydro.conf` (by
default `27372`).  You can then connect to this port with any of the clients.  By
default, for security, the server only listens for connection from the same computer
(`localhost`).  To run a server on another machine, first setup an ssh tunnel to the
server forwarding the port.  For example:

```bash
<local > $ ssh <user@remote.machine.edu> -L 27372:27372
<remote> $ cd super_hydro
<remote> $ conda activate super_hydro # or poetry shell as needed
<remote> $ python bin/server
```

### [Flask] Client

The simplest approach is to just run the [Flask] client:

```bash
poetry run python bin/client              # If using pure python
anaconda-project run python bin/client    # If using conda
```

This will start a [Flask] webserver listening on the specified port.  Connecting a
browser to this will allow you to select the various demonstrations from a menu, which
will then launch a server, allowing you to run the simulation.

## Details

These are my attempts to understand the structure of Kyle's [Flask] code.


* `templates/`


## Conda Environment



## Documentation

The main API documentation is in `Docs/sphinx-source` and can be made by running:

```bash
# If you need to, activate an environment:
poetry env use 3.8
poetry shell

# Now build the documentation.
cd Docs
make html

open _build/html/index.html
```

If you are working on documentation, you can have it auto-build when you save changes by
running:

```bash
make auto
```

then visiting http://127.0.0.1:8000.

### Sphinx/Jupyter Book

The documentation uses [Sphinx], following the approach of [Jupyter Book] without
explicitly using the Jupyter Book tools as discussed in the section [Jupyter Book is a
distribution of
Sphinx](https://jupyterbook.org/explain/sphinx.html#jupyter-book-is-a-distribution-of-sphinx).


### Read the Docs
The documentation nd should be maintained so that it can be published at [Read the
Docs].  See [Getting Started with
Sphinx](https://docs.readthedocs.io/en/stable/intro/getting-started-with-sphinx.html)
for details.

### Structure

The documentation is defined in the [`Docs/sphinx-source`](Docs/sphinx-source) folder
with the following files:

* [`conf.py`](Docs/sphinx-source/conf.py): Configuration of Sphinx and the documentation
  in general.
* [`index.md`](Docs/sphinx-source/index.md): Master file.  This defines the landing page
  and the overall structure through `{toctree}` statements.  The file is written in the
  [MyST] format which is an extension of [Markdown] with special syntax to support
  ReStructure text features used by [Sphinx].
* [`README.md`](README.md): Symlink to the top-level README file.  This is currently
   directly included in [`index.md`](Docs/sphinx-source/index.md) and so should be
   maintained so that it displays properly on GitHub and GitLab repos.  (See [this SO
   question](https://stackoverflow.com/questions/9331281/how-can-i-test-what-my-readme-md-file-will-look-like-before-committing-to-github)
   for some suggestions on how to validate your page.)
* 


We use the `nbsphinx` extension so that we can include Jupyter
notebooks in the documentation.

### Citations

Citations to academic references can be included in
[`master.bib`](sphinx-source/master.bib) and included as described in the [Jupyter{book}
documentation](https://jupyterbook.org/content/citations.html): 

``{cite}`Saint-Jalm:2019` ``: results in {cite}`Saint-Jalm:2019`


### References


*   [`numpydoc` format](https://numpydoc.readthedocs.io/en/latest/format.html): We use the
    `numpydoc` format for documenting functions, classes, etc. so that they can be
    automatically included in documentation. 
* [Sphinx](https://www.sphinx-doc.org/en/master/)

# Architecture

## Asynchronous Code

To achieve good performance and a responsive user interface, we must use some sort of
asynchronous execution.  For example:

*   Computation Server: This should run as fast as possible, without being slowed down
    by network communications or the user interface.  Ideally, the computation should be
    run in a separate process (even on a separate machine), but for debugging purposes,
    it can be useful to run it in the same process space as the main code.  We structure
    our code so that the computation engine can be run either as a separate thread or a
    separate process.
*   User Interface: The user interface should be run in a separate thread or process so
    that it remains responsive.

### Threading

One option for asynchronous execution is to use multiple threads through the
[`threading`](https://docs.python.org/3/library/threading.html) standard library module.
This allows the separate threads to execute asynchronously, but because of the [global
interpreter lock
(GIL)](https://docs.python.org/3/c-api/init.html#thread-state-and-the-global-interpreter-lock)
this does not allow you to take advantage of multiple cores.  This is a good option if
all but one of the threads spend most of their time listening for events, and is the
approach taken in the [Server](#Server). 


## Server

The server process runs the following two threads:

*   `super_hydro.server.Computation`: Main computation thread.  This does the actual
    computations, and should be run on a computer with high performance characteristics
    such as a GPU.  For example, this might be run on `swan.physics.wsu.edu`.
*   `super_hydro.server.Server(IServer)`: This thread manages communication between the
    `Computation` thread and clients using the `queue.Queue` class.  This implementation
    is designed to be used directly from the same process as the client (mainly for
    debugging purposes).
*   `super_hydro.server.NetworkServer(IServer)`: Subclass of `super_hydro.server.Server`
     that listens for network connections and sends communications across the network.
     
# Publication Goals

* Installation:

  Currently we have a bunch of environment files for various
  configurations such as client, server, and testing.  Is there a
  point?  Maybe these should be hidden in a directory and a single
  file provided.

  [ ] Test all installation paths with nox.
  [ ] Make sure this is downloadable from anaconda cloud from my
      channel.
  [ ] Test install on various platforms.
  [ ] Integrate CI.

* Testing:

* Documentation:

  [ ] Full docs should be published on [Read the
      Docs](https://readthedocs.org).
  [ ] Document installation.
  [ ] Document running.
  [ ] Document making new models.

* Models and Examples:

* Clients:

  [ ] Jupyter Notebook Client.
      * Does not have mouse support.
      * Still has issues with interrupts.
  [ ] Flask Client.

  * Other clients might be useful as demonstration about how to
    interact with server.
  [ ] Kivi Client. (Do we still need?)
  [ ] Node Client. (Do we still need?)

* Configuration:

  * Current configuration is not so flexible.  We are using a
    combination of


## Deployment

* Update version number in:

  * `pyproject.toml`

# To Do

* Remove unnecessary dependencies:
  * Definitely scipy (used for sinc...)
  * Possibly matplotlib.
* Add tests and make them pass, the complete coverage.
* Clean up repo - remove old clients and organize everything in proper
  folders.
* Complete documentation from start to finish and helper scripts.
* Upload to PyPI and Anaconda Cloud.
  * Clean up environment file.

* Flask Client
  * Read list of models from a config file.
  * Preserve aspect ratio.
  * Click and drag finger.
  * "Go", "Pause", "Reset"
  * Don't cache pause.
  * Sane cooling range and interpretation (low priority).
  * Running and shutdown issues.


Issues
------
* Default config file in server directory.
  * Load this first, then read user's file.
* Don't fail if no config file exists, make one.
* Simple strategy for locating the config file: use the `__file__`
  variable.

  `os.path.dirname(__file__)`

* Choose better port - with some sort of resolution if it is used.

   ```bash
   # Set the NBPORT variable for the user from /etc/nbports
   export NBPORT=$(sed -n -e "s/${USER}: //p" /etc/nbports)
   if [ -z "$NBPORT" ]; then
      # https://unix.stackexchange.com/a/132524/37813
      export NBPORT=$(python - <<-END
           import socket
           s = socket.socket()
           s.bind(("", 0))
           print(s.getsockname()[1])
           s.close()
           END
   )
      >&2 echo "Warning: ${USER} not in /etc/nbports.  Using random port ${NBPORT}"
   fi
   ```

   Put a default port (not 8888) in config file, then search forward
   incrementally until a free port is found.

MMF: Make simple logger.

* Refactor socket communication making sure that messages are properly
  sent and buffered.

Dependencies
============
* Consider two different clients - a lite client that has minimal
  imports (but requires the server to compute everything) and a more
  full-bodied client that can perform some computations such as the
  tracer particles to reduce server load.  The idea is to keep the
  lite client for mobile devices which cannot import numpy/scipy etc.

To Do
=====
When running the network_server from the notebook client, Quit does
not release zmq sockets, so one gets ZMQError: Address already in use
when trying to restart.

*   Is there any way to rename the `ipykernel` to `super_hydro`?  This could be done by
    running the following after install, but such behavior is not permitted by the new
    python packaging system.
    
        python3 -m ipykernel install --sys-prefix --name super_hydro --display-name super_hydro

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

Lobby Display
=============
Iteration 0: Run everything on penguin (or swan).
* Install SSH.
* Generate a key, and save in a non-privileged account on penguin.
* Configure to forward appropriate port.
* SSH and run server + flask.
* Open http://localhost:<port> in fullscreen browser.

* Implement a timeout on the server.
* Single command to start both computation and flask server.

Issues
======
 * [Cupy] is not available for Mac OS X from [conda-forge].

<!-- Links -->
[`Makefile`]: Makefile
[Nox]: <https://nox.thea.codes> "Nox: Flexible test automation"
[Hypermodern Python]: <https://cjolowicz.github.io/posts/hypermodern-python-01-setup/> "Hypermodern Python"
[`pyenv`]: <https://github.com/pyenv/pyenv> "Simple Python Version Management: pyenv"
[Conda]: <https://docs.conda.io> "Conda"
[Miniconda]: <https://docs.conda.io/en/latest/miniconda.html> "Miniconda"
[Jupyter]: <https://jupyter.org> "Jupyter"
[Heptapod]: <https://heptapod.net> "Heptapod website"
[pytest]: <https://docs.pytest.org> "pytest"
[PyPI]: <https://pypi.org> "PyPI: The Python Package Index"
[MyPI]: <https://alum.mit.edu/www/mforbes/mypi/> "MyPI: My personal package index"
[Poetry]: <https://python-poetry.org> "Poetry: Python packaging and dependency management made easy"
[`poetry2conda`]: <https://github.com/dojeda/poetry2conda> "poetry2conda"
[Jupyter Book]: <https://jupyterbook.org> "Jupyter Book"
[Read the Docs]: <https://readthedocs.org> "Read the Docs"
[MyST]: <https://myst-parser.readthedocs.io> "MyST - Markedly Structured Text"
[Cupy]: <https://cupy.dev/> "NumPy/SciPy-compatible Array Library for GPU-accelerated Computing with Python"
[Flask]: <https://flask.palletsprojects.com>

Bibliography
============

```{bibliography}
```
