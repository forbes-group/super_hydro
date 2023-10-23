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
import os.path
import subprocess
from sphinx.util.fileutil import copy_asset

import mmf_setup

mmf_setup.set_path()

# import sys
# sys.path.insert(0, os.path.abspath('.'))

# https://discourse.jupyter.org/t/debugger-warning-it-seems-that-frozen-modules-are-being-used-python-3-11-0/
# https://stackoverflow.com/questions/76003473
os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"


# This is True if we are building on Read the Docs in case we need to customize.
on_rtd = os.environ.get("READTHEDOCS") == "True"
on_cocalc = "ANACONDA2020" in os.environ

# -- Project information -----------------------------------------------------

import super_hydro

project = "Super_Hydro"
copyright = "2021, Michael McNeil Forbes"
author = "Michael McNeil Forbes"

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
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.ifconfig",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinxcontrib.bibtex",
    "sphinxcontrib.zopeext.autointerface",
    "matplotlib.sphinxext.plot_directive",
    "autodocsumm",
    # From jupyterbook
    # "jupyter_book",
    # "sphinx_thebe",
    # "sphinx_external_toc",
    # "sphinx_comments",  # Hypothes.is comments and annotations
    "sphinx_design",
    "sphinx_togglebutton",
    # "sphinx_panels",
    "sphinx_click",
    #'recommonmark',
    #'IPython.sphinxext.ipython_directive',
    #'IPython.sphinxext.ipython_console_highlighting',
    #'sphinx.ext.inheritance_diagram',
]

# Make sure that .rst comes first or autosummary will fail.  See
# https://github.com/sphinx-doc/sphinx/issues/9891
source_suffix = {  # As of 3.7, dicts are ordered.
    ".rst": "restructuredtext",  # Make sure this is first!
    ".myst": "myst-nb",
    ".md": "myst-nb",
    # '.ipynb': 'myst-nb',  # Ignore notebooks.  Does not work.  See below.
}

# https://myst-parser.readthedocs.io/en/latest/using/syntax-optional.html
# https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#substitutions-with-jinja2
myst_enable_extensions = [
    "amsmath",
    "colon_fence",
    "deflist",
    "dollarmath",
    "html_admonition",
    "html_image",
    # "linkify",
    "replacements",
    "smartquotes",
    "substitution",
    # "tasklist",
]

# https://github.com/mcmtroffaes/sphinxcontrib-bibtex
# BibTeX files
bibtex_bibfiles = [
    "macros.bib",
    "local.bib",
]
bibtex_default_style = "plain"
bibtex_reference_style = "author_year"

# autosummary settings
autosummary_generate = True
autosummary_generate_overwrite = False
autosummary_imported_members = True
add_module_names = False

autoclass_content = "both"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Cache notebook output to speed generation.
# https://myst-nb.readthedocs.io/en/latest/use/execute.html
nb_execution_mode = "cache"
nb_execution_allow_errors = True
nb_execution_timeout = 30
nbsphinx_timeout = 300  # Time in seconds; use -1 for no timeout

execution_excludepatterns = [
    "Dev/Performance.md",
    "Dev/Kivy Summary.md",
    "Dev/JavaScript Client.md",
    "Dev/Testing.md",
    "Dev/NotebookClient.md",
]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_book_theme"  # Theme for JupyterBook
html_logo = "logo.jpg"  # Needed for sidebars

html_theme_options = {
    "repository_url": "https://hg.iscimath.org/mforbes/super_hydro",
    "use_repository_button": True,
}

# Override version number in title... not relevant for docs.
html_title = project

# html_sidebars = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_js_files = ["js/custom.js"]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "Python 3": ("https://docs.python.org/3", None),
    "matplotlib [stable]": ("https://matplotlib.org/stable/", None),
    "numpy [stable]": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
    "sphinx": ("https://www.sphinx-doc.org/", None),
}

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

######################################################################
# Open Graph settings for the sphinxext.opengraph extension
ogp_site_url = "https://readthedocs.org/projects/super-hydro/"

myst_substitutions = {
    "nsf_logo": """```{image} https://www.nsf.gov/images/logos/NSF_4-Color_bitmap_Logo.png
    :alt: National Science Foundation (NSF)
    :width: 10%
    :target: https://www.nsf.gov/
```""",
}

math_defs_filename = "_static/math_defs.tex"

html_context = {
    "mathjax_defines": "",
}

mathjax3_config = {
    "loader": {"load": ["[tex]/mathtools"]},
    "tex": {"packages": {"[+]": ["mathtools"]}},
}

# Hypothes.is comments and annotations
comments_config = {"hypothesis": True}


def config_inited_handler(app, config):
    """Insert contents of `math_defs_filename` into html_context['mathjax_defines']"""
    global math_defs_filename
    filename = os.path.join(
        "" if os.path.isabs(math_defs_filename) else app.confdir, math_defs_filename
    )

    defines = config.html_context.get("mathjax_defines", "").splitlines()
    try:
        with open(filename, "r") as _f:
            defines.extend(_f.readlines())
    except IOError:
        pass

    config.html_context["mathjax_defines"] = "\n".join(defines)


# Allows us to perform initialization before building the docs.  We use this to install
# the named kernel so we can keep the name in the notebooks.
def my_init(app):
    """Run `anaconda-project run init`, or the equivalent if on RtD.

    We must customize this for RtD because we trick RTD into installing everything from
    `anaconda-project.yaml` as a conda environment.  If we then run `anaconda-project
    run init` as normal, this will create a **whole new conda environment** and install
    the kernel from there.
    """
    mathjax_offline = False
    if on_rtd:
        print(f"On RTD in directory {os.getcwd()}!")
        subprocess.check_call(
            [
                "pip",
                "install",
                "--upgrade",
                "--use-feature=in-tree-build",
                "../..[docs]",
            ]
        )
        subprocess.check_call(
            [
                "python3",
                "-m",
                "ipykernel",
                "install",
                "--user",
                "--name",
                "super_hydro",
                "--display-name",
                "Python 3 (super_hydro)",
            ]
        )
        mathjax_offline = False
    else:
        print("Not On RTD!  Assuming you have run make init.")
        ROOT = str(Path(__file__).parent.parent.parent)
        subprocess.check_call(["make", "-C", ROOT, "init"])

        # Don't reinstall everything each time or this can get really slow.
        # subprocess.check_call(["anaconda-project", "run", "init"])

    if mathjax_offline:
        # For this to work, you need to put mathjax js files in Docs/_static/mathjax
        # Docs/_static/
        # |-- math_defs.tex
        # |-- mathjax
        #     |-- a11y
        #     |-- adaptors
        #     |-- core.js
        #     |-- input
        #      ...
        #     |-- sre
        #      ...
        #     |-- startup.js
        #     |-- tex-chtml-full.js
        #     |-- tex-chtml.js
        #     |-- tex-mml-chtml.js
        #     |-- tex-mml-svg.js
        #     |-- tex-svg-full.js
        #     |-- tex-svg.js
        #     `-- ui
        #
        # Copied from the following to put static mathjax files in place if offline:
        # https://gitlab.com/thomaswucher/sphinx-mathjax-offline/-/blob/master/sphinx-mathjax-offline/__init__.py

        ext_dir = os.path.dirname(os.path.abspath(__file__))
        mathjax_dir = ext_dir + "_static/mathjax"
        copy_asset(mathjax_dir, os.path.join(app.outdir, "_static", "mathjax"))
        app.config.mathjax_path = "mathjax/tex-chtml.js"
        app.config.mathjax_path = "mathjax/tex-svg.js"
        app.config.mathjax_path = "mathjax/tex-chtml.js?config=TeX-AMS-MML_HTMLorMML"

        # I don't know why this is needed, but if it is not turned off, then
        # "mathjax_ignore" is added to the top-level class, preventing local rendering.
        app.config.myst_update_mathjax = False


# https://github.com/eventlet/eventlet/issues/670
# os.environ["EVENTLET_HUB"] = "poll"
autodoc_mock_imports = ["eventlet"]


def setup(app):
    app.connect("config-inited", config_inited_handler)
    # Ignore .ipynb files
    app.registry.source_suffix.pop(".ipynb", None)
    app.add_config_value("on_rtd", on_rtd, "env")
    app.add_config_value("on_cocalc", on_cocalc, "env")
    my_init(app)
