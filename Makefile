install: Jupyter_Canvas_Widget jupyter-canvas-widget

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

.PHONY: install uninstall jupyter-canvas-widget Jupyter_Canvas_Widget

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
