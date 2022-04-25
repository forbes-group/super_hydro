"""Command-line interface
~~~~~~~~~~~~~~~~~~~~~~

This module defines the command-line interface (CLI) for the application.  The CLI
mirrors the structure of the configuration files, organizing options by Model.  The
models are found dynamically from modules in :mod:``super_hydro.physics` that support
the :interface:`IModel` interface, and from any modules specified by the user with the
`--models` or `-m` command-line options.

Here are some examples::

    super_hydro client   # Run client with ability to launch servers as needed.
    super_hydro          # Alias for `super_hydro client`
    super_hydro server   # Run computation server listening on the default port.


After server/client options are specified, one can specify options for various models.
To make use of click, we allow these to be separate commands.

    super_hydro ... gpe.GPE --Nx 64 --Ny 64 gpe.GPEBreather --Nxy 256

Goals:

* Translation between config file and cli.

To Do:
* Check autoenv_prefix... set to SUPER_HYDRO_?
* 

Configuration
~~~~~~~~~~~~~

Options can be specified in a configuration file located.  A typical configuration file
looks like this::

    # General options - relevant for both the client and server
    [super_hydro]
    port = 27372

    # Client specific options
    [client]

    # Server specific options
    [server]

    # Default parameters for all models that support them
    [*]
    Nx = 64
    Ny = 64
    steps = 20

    # Model-specific parameters
    [gpe.BECVortex]
    dt_t_scale = 0.5

    [gpe.BECBreather]
    Nx = 256
    Ny = 256
    dt_t_scale = 0.5
    a_HO = 0.04
"""
from functools import partial
import configparser
import importlib
import pkgutil
import os.path

import click

from .interfaces import IModel
from . import physics

APP_NAME = "super_hydro"


def process_path(path):
    """Return the normalized path with '~' and vars expanded."""
    return os.path.normpath(os.path.expandvars(os.path.expanduser(path)))


# Standard XDG config directory
# https://specifications.freedesktop.org/basedir-spec/basedir-spec-0.6.html
XDG_CONFIG_HOME = process_path(os.environ.get("XDG_CONFIG_HOME", "~/.config"))

# This directory
SUPER_HYDRO_DIR = process_path(os.path.join(os.path.dirname(__file__), ".."))

SUPER_HYDRO_APP_DIR = click.get_app_dir("super_hydro")

CONFIG_FILE_NAME = "super_hydro.conf"

DEFAULT_CONFIG_FILES = [
    process_path(os.path.join(_dir, CONFIG_FILE_NAME))
    for _dir in [
        SUPER_HYDRO_DIR,
        SUPER_HYDRO_APP_DIR,
        "/etc",
        XDG_CONFIG_HOME,
        "~",
        ".",
    ]
]


def get_config_file(config_file_name):
    click.get


__all__ = ["ModelGroup"]


class ModelGroup(click.Group):
    """Custom group allowing allowing each model to have different arguments.

    This is a slight abuse of the click CLI as these are not actually "commands" but
    allows us to organize the options.  Models are loaded dynamically with their options
    as returned by :func:`IModel.get_params_and_docs`.

    We provide custom formatting as to list the options for each model.  As these are
    dynamically loaded, we need to provide some eager option processing to
    allow the user to specify modules that might contain viable models, and for options
    like verbosity.  These are managed by explicit callbacks.

    References
    ----------

    * https://stackoverflow.com/a/58770064/1088938: Discussion by Stephen Rauch about
      how to display options for chained commands.
    """

    # https://stackoverflow.com/a/58770064/1088938

    models = {}
    config_files = ()
    verbosity = 0

    ######################################################################
    # Callbacks
    #
    # These should be class methods, that store values in the class variables for later
    # processing.
    @classmethod
    def set_verbosity(cls, ctx, param, value):
        cls.verbosity = value

    @classmethod
    def set_model_modules(cls, ctx, param, names):
        """Store all potential models in `self.models`."""
        super_hydro_names = [
            f"{physics.__name__}.{_m.name}"
            for _m in pkgutil.iter_modules(physics.__path__)
        ]

        # Unique list of names with ours first.
        names = dict.fromkeys(super_hydro_names + list(names))
        for name in names:
            try:
                mod = importlib.import_module(name)
            except ImportError:
                click.echo(f"WARNING: Could not import requested `--models={name}`.")
                continue
            cls.models.update(cls.get_models(mod))

    @classmethod
    def set_config_files(cls, ctx, param, config_files=None):
        """Specify and load the specified config file."""
        if config_files:
            config_files = list(map(process_path, config_files))
        else:
            config_files = []

        cls.config_files = list(DEFAULT_CONFIG_FILES) + config_files

    ######################################################################
    # Custom methods
    def load_config_files(cls):
        parser = configparser.ConfigParser()
        files = parser.read(cls.config_files)
        if cls.verbosity > 1 and files:
            click.echo(f"Configuration loaded from {files}")
        cls.config_parser = parser

    def command(self, *args, **kwargs):
        """Gather the command help model"""
        help_model = kwargs.pop("group", "Commands")
        decorator = super().command(*args, **kwargs)

        def wrapper(f):
            cmd = decorator(f)
            cmd.help_model = help_model
            return cmd

        return wrapper

    def format_commands(self, ctx, formatter):
        # Modified fom the base class method

        commands = []
        models = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if subcommand in self.models:
                models.append((subcommand, cmd))
            elif not (cmd is None or cmd.hidden):
                commands.append((subcommand, cmd))

        if commands:
            longest = max(len(cmd[0]) for cmd in commands)
            # allow for 3 times the default spacing
            limit = formatter.width - 6 - longest

            with formatter.section("Commands"):
                rows = []
                for subcommand, cmd in commands:
                    help_str = cmd.get_short_help_str(limit)
                    subcommand += " " * (longest - len(subcommand))
                    rows.append((subcommand, help_str))
                formatter.write_dl(rows)

        if models:
            longest = max(len(cmd[0]) for cmd in models)
            # allow for 3 times the default spacing
            limit = formatter.width - 6 - longest

            with formatter.section("Available Models"):
                rows = []
                for model_name, cmd in models:
                    help_str = cmd.get_short_help_str(limit)
                    model_name += " " * (longest - len(model_name))
                    rows.append((model_name, help_str))
                formatter.write_dl(rows)

        if self.verbosity > 2:
            with formatter.section("Models Parameters"):
                for model_name, cmd in models:
                    formatter.write("\n")
                    formatter.write(model_name)
                    cmd.format_help_text(ctx, formatter)
                    cmd.format_options(ctx, formatter)

    def list_commands(self, ctx):
        return super().list_commands(ctx) + list(self.models.keys())

    def get_command(self, ctx, name):
        if name in self.commands:
            cmd = super().get_command(ctx, name)
        else:
            cmd = self.get_model_command(ctx, name)
        return cmd

    @staticmethod
    def get_models(mod):
        """Return a list of `(name, Model)` for all exported models in module `mod`,

        An exported model is a class that:
        1. Implements the :interface:`interfaces.IModel` interface.
        2. Does not start with an underscore.
        3. Is specified in ``mod.__all__`` if the module has ``__all__``.
        """
        models = [
            (f"{mod.__name__}.{name}", getattr(mod, name))
            for name in getattr(mod, "__all__", mod.__dict__.keys())
            if not name.startswith("_") and hasattr(mod, name)
        ]

        models = [
            (  # Only include full model name if they are not in physics
                name[len(physics.__name__) + 1 :]
                if name.startswith(physics.__name__)
                else name,
                Model,
            )
            for (name, Model) in models
            if isinstance(Model, type) and IModel.implementedBy(Model)
        ]
        return dict(models)

    def invoke_all_models(self, ctx):
        """Call `_callback()` for all models so that the parameters are set."""
        super_hydro = ctx.find_root().command
        model_names = super_hydro.list_commands(ctx)
        for model_name in model_names:
            command = super_hydro.get_command(ctx, model_name)
            ctx.forward(command)

    @staticmethod
    def _callback(*, _model_name, _ctx, **kwargs):
        """Callback that stores the parameters."""
        _ctx.obj[_model_name] = kwargs

    @classmethod
    def get_model_command(cls, ctx, name):
        """Return a class`click.Command` instance for the model."""
        Model = dict(cls.models)[name]
        params = [
            click.Option(
                param_decls=[f"--{_name}"],
                show_default=cls.verbosity > 0,
                type=type(_value),
                default=_value,
                help=_doc,
            )
            for _name, _value, _doc in Model.get_params_and_docs()
        ]
        command = click.Command(
            name=name,
            params=params,
            help=Model.__doc__,
            add_help_option=False,
            callback=partial(cls._callback, _model_name=name, _ctx=ctx),
        )
        return command

    def format_usage(self, ctx, formatter):
        # breakpoint()
        return super().format_usage(ctx, formatter)

    def get_help(self, ctx):
        # breakpoint()
        return super().get_help(ctx)


######################################################################
# Methods for debugging and testing.
def inspect_ctx(ctx):
    """ """
    from pprint import pprint

    root = ctx.find_root()
    super_hydro = root.command
    # models = super_hydro.commands
    model_names = super_hydro.list_commands(ctx)
    print("Models:")
    pprint(list(model_names))
    for model_name in model_names:
        model = super_hydro.get_command(ctx, model_name)


######################################################################
# super_hydro
#
# This is the definition of the super_hydro command.
#
# fmt: off
# May be no point in using this: it breaks in some cases like:
# super_hydro --test-cli
# https://github.com/click-contrib/click-default-group/issues/17
@click.group(cls=ModelGroup, invoke_without_command=True,
             subcommand_metavar='MODEL [ARGS]... MODEL [ARGS]...',
             no_args_is_help=False)
@click.version_option()
@click.option(
    "--models", "-m", multiple=True, is_eager=True,
    help="Importable module containing models.",
    callback=ModelGroup.set_model_modules)
@click.option(
    "--config", "-c", multiple=True, is_eager=True, expose_value=False,
    help="Config file.",
    callback=ModelGroup.set_config_files)
@click.option(
    "--port", "-p", default=9000, show_default=True, envvar="PORT", show_envvar=True,
    help="Port used for communication by the server and client")
@click.option(
    "--host", default="localhost", envvar="HOST",
    help="URL where the server is listening")
@click.option(
    "--server", is_flag=True,
    help="Start a local computation server")
@click.option(
    "--client", is_flag=True,
    help="Start a local flask client")
@click.option(
    "--verbose", "-v", count=True, is_eager=True, expose_value=False,
    help="Increase verbosity (-vvv to see all models)",
    callback=ModelGroup.set_verbosity)
@click.option(
    "--fps", default=80.0,
    help="Maximum framerate (frames-per-second)")
@click.option(
    "--shutdown", "-s", default=60.0,
    help="Server timeout (minutes)")
@click.option(
    "--test-cli", is_flag=True, hidden=True,
    help="Just process arguments, don't run anything. (For testing).")
@click.pass_context
def super_hydro(ctx, **kw):
    """Superfluid hydrodynamics explorer.

    Model parameters can be defined in configuration files, or by passing the appropriate
    parameters after the model name.  These parameters will be used as default values when
    the client or server starts the appropriate model.

    Server: If you start a server with the `--server` option, then this process will run
    a local computation server will be started, listening on the specified `--port` for
    clients to connect and launch computations.  For security reasons, this sever will
    only list on the local host -- to connect to a remote server, use SSH and forward
    the appropriate port.  This can be done as follows:

       ssh -L <port>:localhost:<port> <remote> 'super_hydro --server -p <port>'

    This could also be specified in your ssh_config file:

       \b
       # ~/.ssh/config
       Host <remote>_super_hydro
         LocalForward <port> localhost:<port>
         RemoteCommand='super_hydro --server --port <port>'
       Host <remote>*
         User <username>
         Hostname <remote>

    Client: If you start a client with the `--client` option, then this process will run
    a webserver listening on http://localhost:<port>.  Connect to this with a
    web-browser to view or run simulations.
    """
    # Make sure we have ctx.obj which will store the model parameters.
    print("Calling super_hydro")
    ctx.ensure_object(dict)
    ctx.obj['super_hydro'] = kw
    ctx.command.invoke_all_models(ctx=ctx)
    
    if kw.get('test_cli', False):
        global _testing
        _testing['ctx'] = ctx
        _testing['kw'] = kw
        inspect_ctx(ctx)

_testing = {}

if __name__ == "__main__":
    super_hydro()
