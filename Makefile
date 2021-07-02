# Need to specify bash in order for conda activate to work.
SHELL=/bin/bash
# Note that the extra activate is needed to ensure that the activate floats env to the front of PATH
CONDA_ACTIVATE=source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate base; conda activate

CONDA=conda
#CONDA=mamba
CONDA_ENVS=./.conda/envs
CONDA_FLAGS=--prefix $(CONDA_ENVS)/super_hydro

conda-env: environment-cpu.yml
	$(CONDA) env create $(CONDA_FLAGS) -f $<
	$(CONDA) run $(CONDA_FLAGS) python3 -m pip install .
	$(CONDA) config --append envs_dirs $(CONDA_ENVS)

conda-env-gpu: environment-gpu.yml
	$(CONDA) env create $(CONDA_FLAGS) -f $<
	$(CONDA) run $(CONDA_FLAGS) python3 -m pip install .[gpu]
	$(CONDA) config --append envs_dirs $(CONDA_ENVS)

environment-cpu.yml: pyproject.toml
	poetry2conda $< $@

environment-gpu.yml: pyproject.toml
	poetry2conda -E gpu $< $@

install: Jupyter_Canvas_Widget jupyter-canvas-widget

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
	conda activate super_hydro                                         && \
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
	conda activate super_hydro                                         && \
	pip install -e _ext/Jupyter_Canvas_Widget                          && \
	conda deactivate

uninstall:
	. /data/apps/conda/etc/profile.d/conda.sh                          && \
	conda activate jupyter                                             && \
	jupyter nbextension uninstall --sys-prefix fastcanvas              && \
	jupyter nbextension uninstall --sys-prefix jpy_canvas              && \
	conda deactivate
	. /data/apps/conda/etc/profile.d/conda.sh                          && \
	conda activate super_hydro                                         && \
	pip uninstall fastcanvas jpy_canvas                                && \
	conda deactivate


.PHONY: real-clean clean install uninstall jupyter-canvas-widget Jupyter_Canvas_Widget conda-env

