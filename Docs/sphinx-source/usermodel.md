================================
#super\_hydro User Defined Models
================================

##Overview
--------

The Flask-based Web Client (FWC) supports loading and visualizing User 
Defined Models (UDMs) through the configuration option `-f` or `--file` 
followed by the absolute filepath for the UDM Python script.

Example: `-f \home\foo\bar\file.py`

When the FWC is started, it will load the UDM and store both the file 
path and all classes (including inherited classes) as individual physics
models to display.

For this reason, it is recommended to minimize the use of class
inheritance where possible.

##Structure
---------

The computational backend of super\_hydro explorer requires a few 
particular methods and initialized parameters to properly load and use a UDM.

###Parameters
----------

####`params` dict:
The following are required `params` dict keys that need to be minimally defined
for the computational server to appropriately read/operate the model.

- Nx, Ny: Integer values sizing the output array
- Nxy: Integer 2-tuple of (Nx, Ny)
- xy: 2-tuple of 1-D arrays, each of length Nx, Ny respectively
- min, max: Integers
- data: array of shape (Nx, Ny) for storing output data array values
- pot\_z: Complex value of form `x + yj` for value of external (finger) potential
- finger\_x, finger\_y: x,y position values of external potential, between 0 and 1
- Lxy: (Nx, Ny)-shaped array for storing tracer positions (if used)

####`sliders` list:
Nested list, each element sublist containing parameters for sliders/toggle boxes
to provide User interaction elements.

Sub-list element definitions:
- 0: Slider name/id (ex: `Cooling`)
- 1: Class (`slider`, `toggle`)
- 2: Scale (`None`, `logarithmic`)
- 3: Type (`range`, `checkbox`)
- 4: Minimum range value (Integer)
- 5: Maximum range value (Integer)
- 6: Slider step size

####Class Methods
-------------

- `get_density`: Gets the density (display) array
- `get`: Get the value of the requested parameter
- `set`: Set the value of the requested parameter
- `step`: Increment the calculation by one time step

