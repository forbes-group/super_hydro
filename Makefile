# Need to specify bash in order for conda activate to work.
SHELL=/bin/bash

ENV ?= super_hydro
CONDA_EXE ?= conda
#CONDA_EXE = mamba

# Note that the extra activate is needed to ensure that the activate floats env to the front of PATH
CONDA_ACTIVATE=source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate base; conda activate

CONDA_ENVS = ./.conda/envs
CONDA_FLAGS = --prefix $(CONDA_ENVS)/$(ENV)

RUN = $(CONDA_EXE) run $(CONDA_FLAGS)
#RUN = $(ANACONDA_PROJECT) run

conda-env: environment-cpu.yaml
	$(CONDA_EXE) env create $(CONDA_FLAGS) -f $<
	$(RUN) python3 -m pip install .
	$(CONDA_EXE) config --append envs_dirs $(CONDA_ENVS)

conda-env-gpu: environment-gpu.yaml
	$(CONDA_EXE) env create $(CONDA_FLAGS) -f $<
	$(RUN) python3 -m pip install .[gpu]
	$(CONDA_EXE) config --append envs_dirs $(CONDA_ENVS)

environment-cpu.yaml: pyproject.toml
	poetry2conda -E docs -E tests $< $@

environment-gpu.yaml: pyproject.toml
	poetry2conda -E gpu -E docs -E tests $< $@

install: Jupyter_Canvas_Widget jupyter-canvas-widget

doc-server:
	$(RUN) sphinx-autobuild --ignore '*/Docs/_build/*' Docs Docs/_build/html

sync:
	find . -name ".ipynb_checkpoints" -prune -o \
	       -name "_ext" -prune -o \
	       -name "envs" -prune -o \
	       -name "*.ipynb" -o -name "*.md" \
	       -exec jupytext --sync {} + 2> >(grep -v "is not a paired notebook" 1>&2)
# See https://stackoverflow.com/a/15936384/1088938 for details

clean:
	rm -rf .nox
	rm -rf .conda
	-conda config --remove env_dirs $(CONDA_ENVS)

real-clean: clean
	conda clean -y --all

# Old stuff
jupyter-canvas-widget:
	. /data/apps/conda/etc/profile.d/conda.sh                          && \
	conda activate jupyter                                             && \
	pip install -e _ext/jupyter-canvas-widget                          && \
	jupyter nbextension install --py --symlink --sys-prefix fastcanvas && \
	jupyter nbextension enable --py --sys-prefix fastcanvas            && \
	pip uninstall fastcanvas                                           && \
	conda deactivate
	. /data/apps/conda/etc/profile.d/conda.sh                          && \
	conda activate $(ENV)                                              && \
	pip install -e _ext/jupyter-canvas-widget                          && \
	conda deactivate

Jupyter_Canvas_Widget:
	. /data/apps/conda/etc/profile.d/conda.sh                          && \
	conda activate jupyter                                             && \
	pip install -e _ext/Jupyter_Canvas_Widget                          && \
	jupyter nbextension install --py --symlink --sys-prefix jpy_canvas && \
	jupyter nbextension enable --py --sys-prefix jpy_canvas            && \
	pip uninstall jpy_canvas                                           && \
	conda deactivate
	. /data/apps/conda/etc/profile.d/conda.sh                          && \
	conda activate $(ENV)                                              && \
	pip install -e _ext/Jupyter_Canvas_Widget                          && \
	conda deactivate

uninstall:
	. /data/apps/conda/etc/profile.d/conda.sh                          && \
	conda activate jupyter                                             && \
	jupyter nbextension uninstall --sys-prefix fastcanvas              && \
	jupyter nbextension uninstall --sys-prefix jpy_canvas              && \
	conda deactivate
	. /data/apps/conda/etc/profile.d/conda.sh                          && \
	conda activate $(ENV)                                              && \
	pip uninstall fastcanvas jpy_canvas                                && \
	conda deactivate


.PHONY: sync real-clean clean install uninstall jupyter-canvas-widget Jupyter_Canvas_Widget conda-env

# Default prints a help message
help:
	@make usage


usage:
	@echo "$$HELP_MESSAGE"

.PHONY: help, usage
# ----- Usage -----

define HELP_MESSAGE

This Makefile provides several tools to help initialize the project.  It is primarly designed
to help get a CoCalc project up an runnning, but should work on other platforms.

Variables:
   ANACONDA2020: (= "$(ANACONDA2020)")
                     If defined, then we assume we are on CoCalc and use this to activate
                     the conda base envrionment. Otherwise, you must make sure that the ACTIVATE
                     command works properly.
   ACTIVATE: (= "$(ACTIVATE)")
                     Command to activate a conda environment as `$$(ACTIVATE) <env name>`
                     Defaults to `conda activate`.
   ANACONDA_PROJECT: (= "$(ANACONDA_PROJECT)")
                     Command to run the `anaconda-project` command.  If you need to first
                     activate an environment (as on CoCalc), then this should do that.
                     Defaults to `anaconda-project`.
   ENV: (= "$(ENV)")
                     Name of the conda environment user by the project.
                     (Customizations have not been tested.)
                     Defaults to `phys-581-2021`.
   ENV_PATH: (= "$(ENV_PATH)")
                     Path to the conda environment user by the project.
                     (Customizations have not been tested.)
                     Defaults to `envs/$$(ENV)`.
   ACTIVATE_PROJECT: (= "$(ACTIVATE_PROJECT)")
                     Command to activate the project environment in the shell.
                     Defaults to `$$(ACTIVATE)  $$(ENV)`.

Initialization:
   make init         Initialize the environment and kernel.  On CoCalc we do specific things
                     like install mmf-setup, and activate the environment in ~/.bash_aliases.
                     This is done by `make init` if ANACONDA2020 is defined.

Testing:
   make test         Runs the general tests.

Maintenance:
   make clean        Call conda clean --all: saves disk space.
   make reallyclean  delete the environments and kernel as well.

Documentation:
   make doc-server   Build the html documentation server on http://localhost:8000
                     Uses Sphinx autobuild
endef
export HELP_MESSAGE
