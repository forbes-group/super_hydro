25 Dec 2021
===========
Trying to get a simple `.. autosummary::` entry working for `Dev/Flask.md` but since I
don't want to generate a toctree here (this is done in the `api` section), I can't find
a way to customize the output.  Not sure if this is a bug.  For now, we will need to
manually update the documentation if we add new classes/functions, or just refer to the
API docs.


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
