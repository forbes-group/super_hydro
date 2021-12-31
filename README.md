[Super_Hydro]: Exploring Superfluids
====================================

Welcome to the **super_hydro** superfluid explorer.  This project provides a way to
develop intuition about superfluid dynamics through a series of interactive demonstrates
where you can play with various superfluid demonstrations.  The simplest way to get
started is to install the explorer, then explore the various example notebooks.

For better performance, however, the explored can be run as a client-server application
with the computations being run on a high-performance server (preferably with an Nvidia
GPU) while you interact with the client on your device.

## Installing [Super_Hydro]

Although [super_hydro] can be installed directly with [Pip]:

```bash
python3 -m pip install super_hydro
```

it is recommended that you first create a [Conda] environment with any performance
libraries such as the [FFTW] libraries or the [NVIDIA] [CUDA] toolkit *(only if you have
a suitable NVIDIA GPU)*:

```bash
conda env create -n super_hydro -f anaconda-project.yaml
conda install -n super_hydro conda-forge::pyfftw # FFTW support
conda install -n super_hydro conda-forge::cupy   # GPU support
conda activate super_hydro
python3 -m pip install super_hydro[fftw,gpu]     # Choose your options
```

The reason is that [Pip] cannot install the binary dependencies, and there can be subtle
version issues that [Conda] resolves.

If you want to use the notebook demonstrations, then you should also install the
`super_hydro` [Jupyter] kernel:

```bash
python3 -m ipykernel install --user --name "super_hydro" --display-name "Python 3 (super_hydro)"
```

**Source**

If you are working from a source distribution, then all of this can be automated with
[Anaconda Project]:

```bash
anaconda-project run init      # No GPU support (use for client)
# OR
anaconda-project run init_gpu  # If you have an NVIDA GPU
```

This will create and update the appropriate [Conda] environment in `envs/`.  You can
then either activate a shell

```bash
anaconda-project run shell
# OR
anaconda-project run shell_gpu
```

For more details, see {ref}`sec:install` for more details.

## Getting Started

If needed, first activate your environment with one of the following, depending on how you
installed [Super_Hydro]:

```bash
conda activate super_hydro
# OR
conda activate super_hydro_gpu
# OR
anaconda-project run shell
# OR
anaconda-project run shell_gpu
```

The simplest way to get started is to launch the Flask client:

```bash
python bin/client
```

This will start a webserver at [http://localhost:27372](http://localhost:27372) (or on a
similar port depending on your configuration) which you can connect with using your browser.

Alternatively, you can run demons in a [Jupyter notebook] from the
[Demo](Docs/Demonstrations) folder:

```bash
jupyter notebook "Docs/Demonstrations/Contents (Start Here).md"
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

[Anaconda Project]: <https://github.com/Anaconda-Platform/anaconda-project> "Anaconda Project"
[CUDA]: <https://developer.nvidia.com/cuda-toolkit> "CUDA Toolkit"
[Conda]: <https://docs.conda.io> "Conda"
[CuPy]: <https://cupy.dev> "CuPy: NumPy/SciPy-compatible Array Library for GPU-accelerated Computing with Python"
[FFTW]: <https://www.fftw.org> "FFTW: The Fastest Fourier Transform in the West"
[Jupyter notebook]: <https://jupyter.org> "Jupyter Notebook"
[NVIDIA]: <https://www.nvidia.com/en-us/> "NVIDIA"
[Pip]: <https://pip.pypa.io/en/stable/> "Package installer for Python"
[pyFFTW]: <https://github.com/pyFFTW/pyFFTW> "pyFFTW: A pythonic python wrapper around FFTW"
[super_hydro]: <https://alum.mit.edu/www/mforbes/super_hydro> "Super_Hydro homepage"
