(sec:install)=
Installing [Super_Hydro]
========================

## TL;DR

Simple installation (no performance boosts)

```bash
python3 -m pip install super_hydro
```

Including the [FFTW]:

```bash
conda env create -n super_hydro -f anaconda-project.yaml
conda install -n super_hydro conda-forge::pyfftw # FFTW support
conda activate super_hydro
python3 -m pip install super_hydro[fftw]
```

If you have an NVIDIA GPU:

```bash
conda env create -n super_hydro -f anaconda-project.yaml
conda install -n super_hydro conda-forge::pyfftw conda-forge::cupy
conda activate super_hydro
python3 -m pip install super_hydro[fftw,gpu] # Choose your options
```

For notebook support, install the `super_hydro` [Jupyter] kernel:

```bash
python3 -m ipykernel install --user --name "super_hydro" --display-name "Python 3 (super_hydro)"
```

From source, you can use [Anaconda Project]:

```bash
anaconda-project run init      # No GPU support (use for client)
# OR
anaconda-project run init_gpu  # If you have an NVIDA GPU
```

## Details

### [Pip]

The `super_hydro` application can be installed with [Pip] using one of the following:

```bash
python3 -m pip install super_hydro       # Install basic version
python3 -m pip install super_hydro[fftw] # Needs FFTW libraries
python3 -m pip install super_hydro[gpu]  # Needs CUDA toolkit
```

but the `fftw` and `gpu` extras that improve performance require specific libraries that
cannot be installed with [Pip]:
* `[fftw]`: Install the [pyFFTW] library which requires the [FFTW] libraries to be
  installed on your system.
* `[gpu]`: Install the [CuPy] library which requires an [NVIDIA] GPU as well as
  the corresponding [CUDA] toolkit to be installed on your system.
  
Installing these performance version with [pip] can be a bit problematic because you
must manually manage the correct underlying [FFTW] and [CUDA] libraries.

### [Conda]

Instead, you can use [Conda] to first create an environment with appropriate versions of
these binary libraries, then install the reset using [Pip].

If you do not already have [Conda] installed, download and install one of the
following: 
*   [Miniconda](https://conda.io/en/latest/miniconda.html): Minimal conda
    installation.  If you want the full anaconda stack later, you can `conda install
    anaconda`.
*   [Anaconda](https://www.anaconda.com/distribution/): Rather complete conda
    installation with the full scientific computing stack right from the start.

```bash
conda env create -n super_hydro -f anaconda-project.yaml
conda install -n super_hydro conda-forge::pyfftw # FFTW support
conda install -n super_hydro conda-forge::cupy   # GPU support
conda activate super_hydro
python3 -m pip install super_hydro[fftw,gpu]     # Choose your options
```

### [Anaconda Project]

Alternatively, you can do all of this with [Anaconda Project] if you have access to the
source:

```bash
anaconda-project run init      # No GPU support or client
# OR
anaconda-project run init_gpu  # If you have an NVIDA GPU
```

These are roughly equivalent to, but more convenient than, the following [Conda] commands:

```bash
conda env create -p envs/super_hydro -f anaconda-project.yaml
conda activate envs/super_hydro
pip install --use-feature=in-tree-build .[docs,tests,fftw]
python3 -m ipykernel install --user --name "super_hydro" --display-name "Python 3 (super_hydro)"
jupyter nbextensions_configurator enable --user
```

or, if you have an NVIDIA GPU and want to use it:

```bash
conda env create -p envs/super_hydro_gpu -f anaconda-project.yaml
conda activate envs/super_hydro_gpu
conda install conda-forge::cupy
pip install --use-feature=in-tree-build .[docs,tests,fftw,gpu]
python3 -m ipykernel install --user --name "super_hydro_gpu" --display-name "Python 3 (super_hydro_gpu)"
jupyter nbextensions_configurator enable --user
```

These create [Conda] environments in `envs/conda_env` or `envs/conda_env_gpu` with the
appropriate [FFTW] or [CUDA] binary libraries, then use `pip` to install the
remaining dependencies.  Finally, a jupyter kernel is created so that the notebook
examples can find the correct environment.  (All of our documentation uses the
`super_hydro` kernel, but you can change this to use the `super_hydro_gpu` kernel if you
are running the server locally and want the performance benefits.)

Once these are done, you can run various commands with

```bash
anaconda-project run server   # Start a server
anaconda-project run client   # Start a client
anaconda-project run shell    # Start a shell
```

The last command starts a [Bash] shell with the appropriate environment activated,
similar to what you would get above with

```bash
conda activate super_hydro
```

### Jupyter Kernel

If you run [Jupyter notebook] from an environment where you installed `super_hydro`,
then you can just visit the [Demo](Demonstrations) notebooks.  If you launch [Jupyter] from
another environment, however, then you will need to install a `super_hydro` kernel.
This can be done by activating the virtual environment, then running:

```bash
python3 -m ipykernel install --user --name super_hydro --display-name super_hydro
```

You can then select the `super_hydro` kernel.  To remove the kernel, run:

```bash
jupyter kernelspec remove super_hydro
```

You can install multiple kernels, for example, if you have both `super_hydro` and
`super_hydro_gpu` environments:

```bash
conda activate super_hydro
python3 -m ipykernel install --user --name super_hydro --display-name super_hydro
conda activate super_hydro_gput
python3 -m ipykernel install --user --name super_hydro_gput --display-name super_hydro_gpu
```

If you use [Anaconda Project], this is done by the following commands, which will create
both environments and kernels.

```bash
anaconda-project run init
anaconda-project run init_gpu
```



[Anaconda Project]: <https://github.com/Anaconda-Platform/anaconda-project> "Anaconda Project"
[CUDA]: <https://developer.nvidia.com/cuda-toolkit> "CUDA Toolkit"
[Conda]: <https://docs.conda.io> "Conda"
[CuPy]: <https://cupy.dev> "CuPy: NumPy/SciPy-compatible Array Library for GPU-accelerated Computing with Python"
[FFTW]: <https://www.fftw.org> "FFTW: The Fastest Fourier Transform in the West"
[Jupyter notebook]: <https://jupyter.org> "Jupyter Notebook"
[Miniconda]: <https://docs.conda.io/en/latest/miniconda.html> "Miniconda"
[NVIDIA]: <https://www.nvidia.com/en-us/> "NVIDIA"
[Pip]: <https://pip.pypa.io/en/stable/> "Package installer for Python"
[Poetry]: <https://python-poetry.org> "Poetry: Python packaging and dependency management made easy"
[`anaconda-client`]: <https://github.com/Anaconda-Platform/anaconda-client> "Anaconda Client"
[`venv`]: <https://docs.python.org/3/library/venv.html> "Creation of virtual environments"
[pyFFTW]: <https://github.com/pyFFTW/pyFFTW> "pyFFTW: A pythonic python wrapper around FFTW"
[super_hydro]: <https://alum.mit.edu/www/mforbes/super_hydro> "Super_Hydro homepage"
