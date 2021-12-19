# Old Notes

This is a collection of older documentation and notes.  No longer directly relevant, but
might contain useful links and info.

## Installation

### [Conda]
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

### [Poetry]

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

