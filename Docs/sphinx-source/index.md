<!-- Literally include the README.md file -->
```{include} README.md
```

<!-- This is the main toctree which defines the order of the documentation: it is hidden -->
<!-- so the content does not appear on the first page, but links appear in the sidebar. -->
```{toctree}
:maxdepth: 3
:hidden:

install
Overview
```

```{toctree}
:maxdepth: 3
:caption: System Architecture
:hidden:
:glob:

Dev/*
DeveloperNotes
```

```{toctree}
:maxdepth: 2
:caption: Super_Hydro API
:hidden:

api/modules.rst
flask
```

Indices and Tables
==================

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
