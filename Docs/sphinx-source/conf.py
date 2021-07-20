# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('../../src/super_hydro'))
import super_hydro


# -- Project information -----------------------------------------------------

project = "Super_Hydro"
copyright = "2020, Michael McNeil Forbes"
author = "Michael McNeil Forbes"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = super_hydro.__version__
# The full version, including alpha/beta/rc tags.
release = super_hydro.__version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_nb",
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinxcontrib.zopeext.autointerface",
    "sphinxcontrib.bibtex",
    # From jupyterbook
    # "jupyter_book",
    # "sphinx_thebe",
    # "sphinx_comments",
    # "sphinx_external_toc",
    "sphinx_panels",
    "sphinx_book_theme",
    #'recommonmark',
    #'sphinx_rtd_theme',
    "matplotlib.sphinxext.plot_directive",
    #'IPython.sphinxext.ipython_directive',
    #'IPython.sphinxext.ipython_console_highlighting',
    #'sphinx.ext.inheritance_diagram',
]

myst_enable_extensions = [
    "substitution",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for references and citations through sphinxext-bibtex -----------
bibtex_bibfiles = ["macros.bib", "master.bib"]
bibtex_reference_style = "author_year"
bibtex_default_style = "plain"
bibtex_reference_style = "author_year"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"
html_theme = "sphinx_rtd_theme"
html_theme = "sphinx_book_theme"
html_logo = "logo.jpg"

html_theme_options = {
    "repository_url": "https://hg.iscimath.org/mforbes/super_hydro",
}

html_sidebars = {}


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {"https://docs.python.org/": None}

# Napoleon settings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
