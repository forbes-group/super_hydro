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

# To Do and Ideas

+++

## Top Priority

+++

* [ ] Full-screen display client.
  * For the physics department entrance, we need a way of launching a full-screen application that will run and allow people to interact with the program.  The current Jupyter client is not really good for this because it requires scrolling etc.  I don't think I want to go back to Kivy, but maybe.  Suggestions?  How hard would it be to make a complete Javascript client?  I think that Node.js has an SSH server.  Maybe we just make a simple Full-Screen display client with limited functionality  (basically connecting and showing stuff).
  * [Connecting to Remote SSH Server via Node.js HTML5 Console](https://stackoverflow.com/questions/38689707/connecting-to-remote-ssh-server-via-node-js-html5-console)
  * [ZeroMQ for Node.js](http://zeromq.github.io/zeromq.js/)
  * There will be a touchscreen that people can use, but I am not sure how well we can interact with it.  One caveat is that all of this has to run on Windows... any ideas?  
  * The complete system should have some buttons on the touchscreen that people can use to switch between a power-point presentation with physics department stuff and our application.  Once our application is activated, we need to display it, allow the user to interact (lower priority), and then eventually switch back to the powerpoint kiosk.
  * The display should be active within the next couple of weeks, so this is fairly urgent.  Any ideas on how we could get something working?
  * One idea?  Notebook + Fullscreen + RISE + Initialization Cell for autostart?
* [ ] GPU backend. (MMF)
* [ ] Complete some applications for demonstration.
* [ ] Add timeouts so that if server is not running, client does not hang.  (Or if network connection goes down.)
* [ ] Think carefully about clients killing server.  Want multiple clients.

+++

## Medium Priority

+++

* [ ] Make work on CoLaboratory.
* [ ] Make tracer particles into arrows or something similar that have static direction information.
* [ ] Add a physical "boat".  I.e. something that has a certain geometry like the finger potential.  Calculate the force and torque on this object and then update it's position and orientation appropriately.  This would be interesting because it will generally not flow with the fluid, but will respond to buoyant forces.  Demonstrates flow-without-resistance.
* [ ] Add a toolbar of possible mouse behaviours including:
  * Finger potential.
  * Local cooling (we should talk about the math).
  * Add vortex, then local cooling while you hold the position.
  * Placement/manipulation of boats?
* [ ] When the client is paused, provide an launch screen where the user has an input field to specify the URL or IP address of the server (just the port for a server running on `localhost`) and a menu for starting a local server.  Perhaps a brief scan could be made to find all locally running servers.
* [ ] More applications.
* [ ] Option processing: Clarify and properly implement the option hierarchy. The current issue is that `Model.params` cannot override the defaults specified in `config.py`. From lowest to highest, the priority should be:
   1. Defaults coded in `config.py` etc.
   2. Defaults coded in `Model.params` in physics etc.
   3. Environmental variables.
   4. Configuration files.
   5. Command-line options/Server options.

```{code-cell} ipython3

```
