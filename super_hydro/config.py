"""Configuration options for both client and server."""
import os.path

import configargparse


def process_path(path):
    """Return the normalized path with '~' and vars expanded."""
    return os.path.normpath(os.path.expandvars(os.path.expanduser(path)))

# Standard XDG config directory
# https://specifications.freedesktop.org/basedir-spec/basedir-spec-0.6.html
XDG_CONFIG_HOME = process_path(os.environ.get(
    'XDG_CONFIG_HOME', '~/.config'))

# This directory
SUPER_HYDRO_DIR = process_path(os.path.join(os.path.dirname(__file__), '..'))

PARSER = configargparse.get_argument_parser(
    default_config_files=list(map(process_path, [
        # Default config file next to this. Make sure it is installed
        # by setup.py
        os.path.join(SUPER_HYDRO_DIR, 'super_hydro.conf'),

        # System-wide config file.
        '/etc/super_hydro.conf',

        # XDG standard user-specific config file.
        os.path.join(XDG_CONFIG_HOME, "super_hydro.conf"),

        # Some users expect this:
        '~/.super_hydro.conf',

        # Config file in the same directory application is run from
        './super_hydro.conf'
    ])))


######################################################################
# Common Options for both Server and Clients
PARSER.add('-c', '--config_file', is_config_file=True,
           help='Config file')
PARSER.add('-p', '--port', default=9000, type=int, env_var='SUPER_HYDRO_PORT',
           help='Port used for communication by the server and client')
PARSER.add('--host', default="localhost", env_var='SUPER_HYDRO_HOST',
           help='URL where the server is listening')
PARSER.add('-fps', '--fps', default=80.0, type=float,
           help="Maximum framerate (frames-per-second)")


def get_server_parser():
    """Return the parser with server configuration"""
    PARSER.add('--Nx', default=64, type=int,
               help="Horizontal grid resolution")
    PARSER.add('--Ny', default=32, type=int,
               help="Vertical grid resolution")
    PARSER.add('--healing_length', default=1.0, type=float,
               help="Healing length (in lattice units)")
    PARSER.add('--dt_t_scale', default=0.1, type=float,
               help="Integration timestep in units of t_scale=hbar/E_max")
    PARSER.add('--V0_mu', default=0.5, type=float,
               help="Finger potential depth in units of the chemical potential")
    PARSER.add('--steps', default=20, type=int,
               help="Number of integration steps between display updates")
    return PARSER


def get_client_parser():
    """Return the parser with client configuration"""
    PARSER.add('--window_width',
               help="Window width (pixels)",
               default=600, type=int)
    return PARSER
