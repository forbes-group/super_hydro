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

