Installation Details
====================

It is recommended to install `super_hydro` in a virtual environment.  Here are details
about how to do this.

## Virtual Environments ([`venv`])

You can use standard virtual environments as provided for by the Python [`venv`] module
as follows:

```bash
python3 -m venv ./_env
source ./_env/bin/activate
python3 -m pip install super_hydro
```

This will create a virtual environment in the folder `./_env`, then activate it, install
`super_hydro`, then run the Javascript client.

## [Conda]

We do not yet officially support a [Conda] package, but you can create an environment
with `super_hydro` installed from our Anaconda cloud environment:
https://anaconda.org/mforbes/super_hydro


If you do not already have [Conda] installed, download and install one of the
following: 
*   [Miniconda](https://conda.io/en/latest/miniconda.html): Minimal conda
    installation.  If you want the full anaconda stack later, you can `conda install
    anaconda`.
*   [Anaconda](https://www.anaconda.com/distribution/): Rather complete conda
    installation with the full scientific computing stack right from the start.

Ensure that the conda base environment is activated before continuing, (the
installer will offer to update your initialization files,) and install the
[`anaconda-client`] module:
    
```bash
conda install anaconda-client
```

Now you can create a `super_hydro` environment:

```bash
conda env create -n super_hydro mforbes/super_hydro
conda activate super_hydro
```

If you are installing from source, you can automatically create an environment using the
Makefile:

```bash
make conda-env
make conda-env-gpu    # If you have a GPU: this will install cupy
```

## [Poetry]

If you have a copy of the source and have [Poetry] installed, then you can use it to
manage the virtual environment:

```bash
cd super_hydro
poetry use env 3.9
poetry install
# poetry install -E gpu   # Do this if you have an Nvidia GPU
poetry shell
python3 bin/client
```

## Jupyter Kernel

If you run [Jupyter notebook] from an environment where you installed `super_hydro`,
then you can just visit the [Demo](Demos) notebooks.  If you launch [Jupyter] from
another environment, however, then you will need to install a `super_hydro` kernel.
This can be done by activating the virtual environment, then running:

```bash
python3 -m ipykernel install --user --name super_hydro --display-name super_hydro
```

You can then select the `super_hydro` kernel.  To remove the kernel, run:

```bash
jupyter kernelspec remove super_hydro
```



[Jupyter notebook]: <https://jupyter.org> "Jupyter Notebook"
[Conda]: <https://docs.conda.io> "Conda"
[Miniconda]: <https://docs.conda.io/en/latest/miniconda.html> "Miniconda"
[`venv`]: <https://docs.python.org/3/library/venv.html> "Creation of virtual environments"
[`anaconda-client`]: <https://github.com/Anaconda-Platform/anaconda-client> "Anaconda Client"
[Poetry]: <https://python-poetry.org> "Poetry: Python packaging and dependency management made easy"
