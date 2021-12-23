<!-- Literally include the README.md file -->
```{include} README.md
```

<!-- This is the main toctree which defines the order of the documentation: it is hidden -->
<!-- so the content does not appear on the first page, but links appear in the sidebar. -->
```{toctree}
:maxdepth: 3
:hidden:

Installation
Overview
Models
Clients
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

api/index.rst
```

```{toctree}
---
maxdepth: 0
caption: "Repeated Includes (for testing with autobuild):"
titlesonly:
hidden:
---
README
```

Indices and Tables
==================

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
