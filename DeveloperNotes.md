Developer Notes
===============

## Install

The install process should be specified in `Makefile`.  Currently this uses [Poetry] to
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
  

## Conda Environment



## Documentation

The main API documentation is in `Docs/sphinx-source` and can be made
by running:

```bash
# If you need to, activate an environment:
poetry env use 3.8
poetry shell

# Now build the documentation.
cd Docs
make html

open _build/html/index.html
```

This uses Sphinx, and should be maintained so that it can be published
at [Read the Docs](https://readthedocs.org).  See [Getting Started
with
Sphinx](https://docs.readthedocs.io/en/stable/intro/getting-started-with-sphinx.html)
for details.

We use the `nbsphinx` extension so that we can include Jupyter
notebooks in the documentation.

### References
* [`numpydoc` format]
  (https://numpydoc.readthedocs.io/en/latest/format.html): We use the
  `numpydoc` format for documenting functions, classes, etc. so that
  they can be automatically included in documentation.
* [Sphinx](https://www.sphinx-doc.org/en/master/)


## Publication Goals

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



Developer Notes
===============

<!-- Links -->
[Nox]: <https://nox.thea.codes> "Nox: Flexible test automation"
[Hypermodern Python]: <https://cjolowicz.github.io/posts/hypermodern-python-01-setup/> "Hypermodern Python"
[`pyenv`]: <https://github.com/pyenv/pyenv> "Simple Python Version Management: pyenv"
[`minconda`]: <https://docs.conda.io/en/latest/miniconda.html> "Miniconda"
[Conda]: <https://docs.conda.io> "Conda"
[Heptapod]: <https://heptapod.net> "Heptapod website"
[pytest]: <https://docs.pytest.org> "pytest"
[PyPI]: <https://pypi.org> "PyPI: The Python Package Index"
[MyPI]: <https://alum.mit.edu/www/mforbes/mypi/> "MyPI: My personal package index"
[Poetry]: <https://python-poetry.org> "Poetry: Python packaging and dependency management made easy""
[`poetry2conda`]: <https://github.com/dojeda/poetry2conda> "poetry2conda"
