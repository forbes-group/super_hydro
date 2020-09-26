"""Super_Hydro: Exploring Superfluids.
"""
# This file is modified from:
#
# https://github.com/pypa/sampleproject/blob/master/setup.py
#
# See this for links and details about the format of what is included here.

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='super_hydro',
    version='0.1.1',
    description='Super_Hydro: Superfluid hydrodynamics explorer.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://labs.wsu.edu/forbes/super_hydro',
    author='Michael McNeil Forbes',
    author_email='m.forbes@wsu.edu',
    classifiers=[      # https://pypi.org/classifiers/
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Scientific/Engineering :: Physics',

        # Pick your license as you wish
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
    ],

    keywords='super_hydro, NSF',

    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.5, <4',

    install_requires=[
        ##################################################
        # Servers
        'attrs',
        'configargparse',
        'scipy',
        'numpy',

        # For performance
        'numexpr',
        'cython',
        'pyfftw',

        # Communication
        'pyzmq',
        'eventlet',
        # 'python-socketio',
        # 'aiohttp'

        # Models
        'zope.interface',
        'matplotlib',

        ##################################################
        # Clients
        # Notebook client
        'ipykernel',
        'ipywidgets',
        #'nb_conda',
        'mmf_setup',
        'mmfutils',

        # Web clients
        'flask',
        'flask-socketio',

        # Who uses these?
        'tzlocal',
        'pillow',
        'pytz',
    ],
    extras_require={
        'gpu': ['cupy'],
        'test': ['pytest-cov', 'pytest-flake8'],
    },

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # `pip` to create the appropriate form of executable for the target
    # platform.
    #
    # For example, the following would provide a command called `sample` which
    # executes the function `main` from this package when invoked:
    entry_points={
        'console_scripts': [
            'sample=super_hydro_server:super_hydro.server.run',
        ],
    },

    project_urls={  # Optional
        'Bug Reports': 'https://github.com/mforbes/super_hydro/issues',
        'Funding': 'https://physics.wsu.edu/give/',
        #'Say Thanks!': 'http://saythanks.io/to/example',
        'Source': 'https://github.com/mforbes/super_hydro',
    },
)
