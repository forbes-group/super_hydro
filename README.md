Super_Hydro: Exploring Superfluids
==================================

Welcome to the **super_hydro** superfluid explorer.  This project provides a way to
develop intuition about superfluid dynamics through a series of interactive demonstrates
where you can play with various superfluid demonstrations.  The simplest way to get
started is to install the explorer, then explore the various example notebooks.

For better performance, however, the explored can be run as a client-server application
with the computations being run on a high-performance server (preferably with an Nvidia
GPU) while you interact with the client on your device.

## Installation

The `super_hydro` application can simply be installed with [Pip] using one of the following:

```bash
python3 -m pip install super_hydro        # Install without GPU support
python3 -m pip install super_hydro[fftw]  # Use if you have the FFTW library
python3 -m pip install super_hydro[gpu]   # Use if you have an NVIDIA GPU
```

The `fftw` and `gpu` extras require specific libraries that cannot be installed with [Pip],
but which will improve performance:
* `[fftw]`: Install the [pyFFTW] library which requires the [FFTW] libraries to be
  installed on your system.
* `[gpu]`: Install the [CuPy] library which requires an [NVIDIA] GPU as well as
  the corresponding [CUDA] toolkit to be installed on your system.
  
Optionally, these can be installed using [Conda]:

```bash
conda env create -f environment.cpu.yml  # No GPU support
conda env create -f environment.gpu.yml  # If you have an NVIDIA GPU
```

These will create an environment called `super_hydro` with the [FFTW] or [CUDA]
libraries installed which you can then activate:

```bash
conda activate super_hydro
```
  
For more details, see {ref}`sec:install` for more details.

## Getting Started

The simplest way to get started is to launch a [Jupyter notebook] from the [Demo](Demos)
folder:

```bash
jupyter notebook "Docs/Demonstrations/Contents (Start Here).ipynb"
```

## Remote Server

To run a remote computation server:

1.  Install `super_hydro` on the remote server and setup a virtual environment, either
    using [Conda] or as a virtual environment.
2.  Launch the remote server using SSH while forwarding the appropriate ports.

# Funding {{ nsf_logo }}

This material is based upon work supported by the National Science Foundation under
Grant Number [1707691](https://www.nsf.gov/awardsearch/showAward?AWD_ID=1707691). Any
opinions, findings, and conclusions or recommendations expressed in this material are
those of the author(s) and do not necessarily reflect the views of the National Science
Foundation.

[Pip]: <https://pip.pypa.io/en/stable/> "Package installer for Python"
[Jupyter notebook]: <https://jupyter.org> "Jupyter Notebook"
[pyFFTW]: <https://github.com/pyFFTW/pyFFTW> "pyFFTW: A pythonic python wrapper around FFTW"
[FFTW]: <https://www.fftw.org> "FFTW: The Fastest Fourier Transform in the West"
[CuPy]: <https://cupy.dev> "CuPy: NumPy/SciPy-compatible Array Library for GPU-accelerated Computing with Python"
[NVIDIA]: <https://www.nvidia.com/en-us/> "NVIDIA"
[CUDA]: <https://developer.nvidia.com/cuda-toolkit> "CUDA Toolkit"
[Conda]: <https://docs.conda.io> "Conda"
