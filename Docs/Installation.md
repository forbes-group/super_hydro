---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.10.3
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Installation

+++

To install the `super_hydro` superfluid explorer, we recommend using [Conda](https://anaconda.org/anaconda/conda) to setup an appropriate environment.

+++

## TL;DR

+++

```bash
conda env create -f environment.env
```

+++

The explorer consists of two components: the client and the server.  Both of these can run on the same machine, but one can also run the server on a different machine (ideally a fairly high-performance machine with an Nvidia GPU supporting CUDA).

Two clients are supported:

* Notebook Client: This runs in a Jupyter Notebook.
* Kivy Client: This runs as its own application using the Kivy gaming platform.

+++

## Notebook Client

+++

The notebook client requires some Javascript to be installed, which cannot be done using just Conda.  For this, you must also install a Jupyter Notebook extension.

+++

# Mac OS X

+++

Installing [Kivy] on Mac OS X was a pain.

* There is currently no Anaconda package.
* The App installs nicely, but one cannot easily install matplotlib into that since this is a framework build

* What worked was installing Kivy into a conda environment from the source

```bash
pip install git+https://github.com/kivy/kivy.git
```
  
https://github.com/kivy/kivy/wiki/Connecting-Kivy-with-Anaconda-(OSX)

[Kivy]: https://kivy.org/#home

+++

# Windows 10 WSL

+++

```
sudo apg get mesa
sudo apt get libglew-dev
pip install kivi
```

* [Xming](https://sourceforge.net/projects/xming/)
