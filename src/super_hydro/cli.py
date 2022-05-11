"""Command-line interface
~~~~~~~~~~~~~~~~~~~~~~

The command-line interface (CLI) for the application uses a slightly abuse of the Click_
package where each model is implemented as a "command" with its own arguments.  To see
the possible models, or model parameters, use the `--help` flag::

    super_hydro --help          # Options and a list of known models.
    super_hydro gpe.BEC --help  # Options for the gpe.BEC model.

Parameters can also be specified in the configuration file, again organizing options by
Model.  The models are found dynamically from modules in :mod:``super_hydro.physics`
that support the :interface:`IModel` interface, and from any modules specified by the
user with the `--models` or `-m` command-line options.

Here are some examples::

    super_hydro           # Run client with ability to launch servers.
    super_hydro --server  # Run computation server.

After server/client options are specified, one can specify options for various models.
To make use of click, we allow these to be separate commands::

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

Implementation Details
~~~~~~~~~~~~~~~~~~~~~~
We slightly abuse Click_ using the subcommands to specify model parameters.  To make
this work the man `super_hydro` command really just processes all the arguments, then
the `result_callback` is used to actually execute the program.



.. _Click: https://click.palletsprojects.com/en/8.1.x/documentation/

"""
from typing import Set, List, Optional
from dataclasses import dataclass, field
from functools import partial
from contextlib import suppress
import configparser
import importlib
import pkgutil
import os.path

import click

from .interfaces import IModel
from . import physics

APP_NAME = "super_hydro"


class ConfigParser(configparser.ConfigParser):
    """Custom version that preserves case of options."""

    def optionxform(self, optionstr):
        return optionstr


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


__all__ = ["ModelGroup"]


@dataclass
class Configuration:
    """Represent the configuration.

    The internal dictionaries contain pairs `(value, source)` where `source` is the file
    (or command line) where the parameter was defined.

    Attributes
    ----------
    defaults : dict[str, str]
        Dictionary of default values for the models.  Corresponds to the `[DEFAULT]`
        section of the config file.  If a parameters is used by a model but not defined
        in the specific section, then a value here (if defined) will be used.
    model_options : dict[str, dict[str]]
        Dictionary of specific configurations.  Each entry is a dictionary of options
        corresponding to the specified model (the key is the import path).
    super_hydro_options : dict[str, str]
        Dictionary of options for the application.
    config_file : List[str]
        List of config files.
    Dictionary of application configurations in the `[super_hydro]` section of the
        config file.
    flies : [str]
        List of config files.  Should exist and be readable.
    """

    model_modules: Set[str] = field(default_factory=set)
    config_files: List[str] = field(default_factory=list)
    model_options: dict[str, dict[str, str]] = field(default_factory=dict)
    super_hydro_options: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)
    test_cli: bool = False
    verbosity: int = 0

    def check(self, strict=False):
        """Check that the models can be imported."""
        for model_name in self.model_options:
            try:
                Model = self._import_model(model_name, strict=True)
            except Exception as e:
                sources = set(
                    _v[1] for (_k, _v) in self.model_options[model_name].items()
                )
                click.echo(f"WARNING: {e} (Referenced in {sources})")

    def add_config_file(self, file):
        """Load the specified config file and add it's content.

        Results
        -------
        Name of the file if it is successfully loaded, otherwise None.
        """
        parser = ConfigParser()
        if not parser.read(file):
            return None
        elif self.verbosity > 1:
            click.echo(f"Loading configuration from {file}")

        options = {section: dict(parser[section]) for section in parser}
        self.defaults.update(
            {_k: (_v, file) for (_k, _v) in options.pop("DEFAULT", {}).items()}
        )

        super_hydro_options = options.pop("super_hydro", {})
        # The 'model_modules' parameter is special: it is additive
        if "model_modules" in super_hydro_options:
            self.super_hydro_options.setdefault("model_modules", []).extend(
                self._eval(super_hydro_options.pop("model_modules"))
            )

        self.super_hydro_options.update(
            {_k: (_v, file) for (_k, _v) in super_hydro_options.items()}
        )
        for section in list(options):
            self.model_options.setdefault(section, {})
            self.model_options[section].update(
                {_k: (_v, file) for (_k, _v) in options.pop(section).items()}
            )
        return file

    def update_model_cli(self, model, options):
        """Update the specified model dictionary from the command line."""
        model_options = self.model_options.setdefault(model, {})
        for option, value in options.items():
            model_options[option] = (self._repr(value), "CLI")

    def get_models(self, check=True):
        """Return a dictionary of Models by name."""
        super_hydro_names = [
            f"{physics.__name__}.{_m.name}"
            for _m in pkgutil.iter_modules(physics.__path__)
        ]

        # Unique list of names with ours first.
        names = dict.fromkeys(
            super_hydro_names + self.super_hydro_options.get("model_modules", [])
        )

        models = {}
        for name in names:
            try:
                mod = importlib.import_module(name)
            except ImportError:
                if check:
                    click.echo(
                        f"WARNING: Could not import requested `--models={name}`."
                    )
                continue
            models.update(self._get_models(mod))
        return models

    @staticmethod
    def _get_models(mod):
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

    def _import_model(self, model_name, strict=False):
        """Return `Model` class.

        Arguments
        ---------
        model_name : str
            Importable model name, relative to `super_hydro.physics` or absolutely
            importable.
        strict : bool
            If True, then raise exceptions.

        Raises
        ------
        ImportError
            If no module is importable.
        ValueError
            If the model name is ambiguous
        AttributeError
            If the module is importable but has no model attribute.
        NotImplementedError
            If the Model class does not implement the IModel interface.
        """
        if "." not in model_name:
            if strict:
                raise ValueError(f"{model_name=} must have the form `<module>.<Model>`")
            else:
                return None

        mod, model = model_name.rsplit(".", 1)
        mods = [mod, f"{physics.__name__}.{mod}"]
        modules = []
        for _m in mods:
            with suppress(ImportError):
                modules.append(importlib.import_module(_m))
        if not modules:
            if strict:
                raise ImportError(f"Could not import module=`{model_name}`.")
            return None
        if 2 == len(modules) and all(hasattr(_m, model) for _m in modules):

            # If there are two, we use the first one which is the unqualified
            # name.  This allows users to specify the local one if needed with a
            # fully qualified name `super_hydro.physics.<mod>`.

            if strict:
                raise ValueError(f"Ambiguous models: `{mods}`: using `{mods[0]}`.")
        module = modules[0]

        try:
            Model = getattr(module, model)
        except AttributeError:
            if strict:
                raise AttributeError(f"Model `{model_name}` does not exist.")
            return None

        if not IModel.implementedBy(Model):
            if strict:
                raise NotImplementedError(
                    f"`{model_name}` doesn't implement the IModel interface."
                )
            return None

        return Model

    def _unpack(self, d, eval_=False):
        """Return the unpacked version of the dictionary d without sources."""
        if eval_:
            eval_ = self._eval
        else:
            eval_ = lambda x: x
        return {key: eval_(value) for key, (value, _source) in d.items()}

    def _eval(self, repr_):
        """Return the evaluated version of value.  Inverse of `repr()`."""
        return eval(repr_)

    def _repr(self, value):
        """Return the string representation of value. Inverse of `eval()`."""
        return repr(value)

    def get_opts(self, model_name=None, no_config=False, check=True):
        """Return the full option dictionary of the specified model.

        This dictionary has the evaluated values, and follows the prescribed order or
        precedence:

        1. Value as returned by `Model.get_params_and_docs()`.

        If `not no_config`, then the following are used:

        2. Values as defined in the `DEFAULTS` section of the config files.
        3. Value as defined in a specific model section of config files.
        4. Value as passed to the CLI.

        Arguments
        ---------
        model_name : str, None
            Importable model name, relative to `super_hydro.physics` or absolutely
            importable.  If `None` then return the application options.
        no_config : bool:
            If `True`, then only get the values as defined in the Model class, and
            ignore any configuration or CLI values.
        check : bool
            If `True`, then import the model and use it for the base defaults.
        """
        if model_name is None:
            opts = self._unpack(self.super_hydro_options, eval_=True)
            return opts

        Model = self._import_model(model_name=model_name)
        if not Model:
            if check:
                click.echo(f"WARNING: Could not import {model_name}.")
            return {}

        opts = {_name: _value for _name, _value, _doc in Model.get_params_and_docs()}
        if no_config:
            return opts

        for _key in self.defaults:
            if _key in opts:
                _repr, _source = self.defaults[_key]
                opts[_key] = self._eval(_repr)
        model_opts = self.model_options.get(model_name, {})
        for option in model_opts:
            repr_, source = model_opts[option]
            if check and option not in opts:
                msg = f"{option} not a parameter of {model_name} (from {source})"
                click.echo(f"WARNING: {msg}")
                continue
            opts[option] = self._eval(repr_)
        return opts

    def get_parser(self, full=False):
        """Return a ConfigParser instance that can be used to save the parameters.

        Arguments
        ---------
        full : bool
            If `True`, then include all parameters, otherwise, only include parameters
            that differ from the class defaults.
        """
        defaults = self._unpack(self.defaults)
        parser = ConfigParser(defaults=defaults)
        # parser.optionxform = str  # Prevent conversion to lowercase
        if self.super_hydro_options:
            section = "super_hydro"
            parser.add_section(section)
            for option, (value, _source) in self.super_hydro_options.items():
                parser.set(section=section, option=option, value=value)

        for section in self.model_options:
            base_opts = self.get_opts(section, no_config=True, check=True)
            if not base_opts:
                continue

            parser.add_section(section)
            model_opts = self._unpack(self.model_options[section])
            for option, value in base_opts.items():
                default_repr_ = defaults.get(option, self._repr(value))
                repr_ = model_opts.get(option, default_repr_)
                if full or repr_ != default_repr_:
                    parser.set(section=section, option=option, value=repr_)
        return parser

    @property
    def _rep(self):
        """Return a representation for testing."""
        return [
            self._unpack(self.defaults),
            self._unpack(self.super_hydro_options),
            {
                model: self._unpack(self.model_options[model])
                for model in self.model_options
            },
        ]

    @property
    def _full_rep(self):
        """Return a representation for testing."""
        return [
            self._unpack(self.defaults),
            self._unpack(self.super_hydro_options),
            {
                model: {
                    key: self._repr(value)
                    for key, value in self.get_opts(model).items()
                }
                for model in self.model_options
            },
        ]


class ModelGroup(click.Group):
    """Custom group allowing allowing each model to have different arguments.

    This is mainly to define the help messages, and is a slight abuse of the click CLI
    as these are not actually "commands" but allows us to organize the options.  Models
    are loaded dynamically with their options as returned by
    :func:`IModel.get_params_and_docs`.

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

    config_files = ()
    verbosity = 0

    ######################################################################
    # Customizations of methods
    def list_commands(self, ctx):
        config = ctx.ensure_object(Configuration)
        models = config.get_models()
        return super().list_commands(ctx) + list(models.keys())

    def format_commands(self, ctx, formatter):
        # Modified fom the base class method

        commands = []
        models = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if subcommand in ctx.obj.models:
                models.append((subcommand, cmd))
            elif not (cmd is None or cmd.hidden):
                commands.append((subcommand, cmd))

        if commands:
            longest = max(len(cmd[0]) for cmd in commands)
            # allow for 3 times the default spacing
            limit = formatter.width - 6 - longest

            with formatter.section("Models:"):
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

    def get_command(self, ctx, name):
        if name in self.commands:
            cmd = super().get_command(ctx, name)
        else:
            cmd = self._get_model_command(ctx, name)
        return cmd

    ######################################################################
    # Helper methods not part of click.
    @staticmethod
    def _callback(*, _model_name, _ctx, **kwargs):
        """Callback that stores the parameters."""
        ctx = _ctx.find_root()
        config = ctx.ensure_object(Configuration)
        if config.test_cli:
            click.echo(f"{_model_name=} invoked with {kwargs=}")
        config.update_model_cli(_model_name, kwargs)

    @classmethod
    def _get_model_command(cls, ctx, name):
        """Return a class`click.Command` instance for the model."""
        config = ctx.ensure_object(Configuration)
        models = config.get_models(check=True)
        if name not in models:
            ctx.fail(f"Model {name} not found. (Try `super_hydro --help`)")

        Model = models[name]

        params = [
            click.Option(
                param_decls=[f"--{_name}", f"{_name}"],
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
            add_help_option=True,
            no_args_is_help=True,
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
# Callbacks
def set_param(ctx, param, value):
    config = ctx.ensure_object(Configuration)
    setattr(config, param.name, value)


def set_config_files(ctx, param, value):
    """Specify and load the specified config file."""
    config = ctx.ensure_object(Configuration)
    config_files = []
    if value:
        config_files = value = list(map(process_path, value))

    config_files = list(DEFAULT_CONFIG_FILES) + config_files
    for file in config_files:
        config.add_config_file(file)


def set_model_modules(ctx, param, value):
    """Store all potential models in `ctx.obj.models`."""
    group = ctx.command
    config = ctx.ensure_object(Configuration)
    for name in value:
        try:
            mod = importlib.import_module(name)
        except ImportError:
            click.echo(f"WARNING: Could not import requested `--models={name}`.")
            continue
    config.model_modules.update(value)


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
             chain=True, # Allow multi-command chaining
             subcommand_metavar='MODEL [ARGS]... MODEL [ARGS]...',
             no_args_is_help=False)
@click.version_option()
@click.option(
    "--models", "-m", multiple=True, is_eager=True,
    help="Importable module containing models.",
    callback=set_model_modules)
@click.option(
    "--config", "-c", multiple=True,
    type=click.Path(dir_okay=False),
    help="Additional config files.",
    callback=set_config_files)
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
    callback=set_param)
@click.option(
    "--fps", default=80.0,
    help="Maximum framerate (frames-per-second)")
@click.option(
    "--shutdown", "-s", default=60.0,
    help="Server timeout (minutes)")
@click.option(
    "--test-cli", is_flag=True, hidden=True, is_eager=True,
    help="Just process arguments, don't run anything. (For testing).",
    callback=set_param)    
@click.pass_context
# fmt: on
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

    For help on an available model, call:

       super_hydro MODEL --help
    """
    config = ctx.ensure_object(Configuration)
    if config.test_cli:
        click.echo("Calling super_hydro")
    return ctx


@super_hydro.result_callback()
@click.pass_context
def run_super_hydro(ctx, results, **kw):
    """Actually run the application."""
    config = ctx.ensure_object(Configuration)
    if config.test_cli:
        click.echo(f"Running super_hydro with {ctx=}, {results=}, {kw=}")
    print(config)


_testing = {}

if __name__ == "__main__":
    super_hydro()
