Super_Hydro
===========

Superfluid hydrodynamics explorer. 

This project provides a client-server interface for exploring
superfluid dynamics.  Communication can take place over the network
(using ZMQ) allowing a local client to connect with a computation
server running on a high-performance computer with GPU acceleration.
(The server can also be run locally.)

Installation
------------
Currently both the server and preferred clients require python. The
recommended installation path is with
[conda](https://conda.io/en/latest/) environments:

1. Download and install one of the following:
   * [Miniconda](https://conda.io/en/latest/miniconda.html): Minimal
     conda installation.  If you want the full anaconda stack later,
     you can `conda install anaconda`.
   * [Anaconda](https://www.anaconda.com/distribution/): Rather
     complete conda installation with the full scientific computing
     stack right from the start.
     
   Ensure that the conda base environment is activated before
   continuing.  (The installer will offer to update your
   initialization files.)
2. Create a `super_hydro` environment:

   ```bash
   conda env create -f environment.yml
   ```
   
   This will create a conda environment called `super_hydro` with
   everything needed to run both the client and server.
   
   *Notes: Specialized environments are also available for independent
   server and client applications if needed: `environment.server.yml`
   `environment.client.yml`.  If these are updated, developers should
   use `conda-devenv` which will regenerate `environment.yml` from
   `environment.devenv.yml`, including both client and server
   requirements.  Testing should be done with `conda-devenv -f
   environment.devenv.test.yml`.*
3. (Optional) To run the pure JavaScript client, install the
   appropriate `Node` packages.  This requires
   [`npm`](https://www.npmjs.com) which should be installed the OS
   level.  Once `nmp` is installed, you can run:
   
   ```bash
   make install-js-client
   ```



Javascript Client
-----------------
This directory defines a pure javascript client that can be used when
python is not installed.  To use this:

* Start a server listening on port
* Open index.html


Code Structure
--------------
* `index.html`: Basic webpage with embedded client.
* `client.js`: 
* `canvas_behavior.js`:
* `data.js`:
* `handle_reply.js`:
* `fg_objects.js`:


To Do
-----
* [ ] Replace magic parameters with configurations (how to do this with
  js?)
* 

Questions
---------
* Why is there code in the client for multiple "listeners"?  Wouldn't
  each client webpage be running their own client code?
* 


