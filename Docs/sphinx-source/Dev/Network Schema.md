---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.10.3
kernelspec:
  display_name: Python 3 (super_hydro)
  language: python
  name: super_hydro
---

# Network Schema

+++

Server:

Loop:
* Waits to receive a task
* Interprets the received string, or the first X characters of that string, to determine what task to do
* Performs the requested operations
* Ends by sending either:
	* A requested data set
	* "success" if the operation was completed
	* "ERROR" if the received task was unable to be interpreted
    
Client:

* Sends a string that defines what task to do, followed by any necessary data to complete that task.
* Waits for a response from the server; checks if "success" or "ERROR" if not expecting a data set
* Starts next task

```{code-cell} ipython3

```
