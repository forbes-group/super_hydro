---
substitutions:
  nsf_logo: |
    ```{image} https://www.nsf.gov/images/logos/NSF_4-Color_bitmap_Logo.png
    :alt: National Science Foundation (NSF)
    :width: 10%
    :target: https://www.nsf.gov/
    ```
---

<!-- Literally include the README.md file -->
```{include} README.md
```

<!-- This is the main toctree which defines the order of the documentation: it is hidden -->
<!-- so the content does not appear on the first page, but links appear in the sidebar. -->
```{toctree}
:maxdepth: 3
:hidden:

install
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
