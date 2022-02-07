"""Command-line interface.

Here are some examples::

    super_hydro client   # Run client with ability to launch servers as needed.
    super_hydro          # Alias for `super_hydro client`
    super_hydro server   # Run computation server listening on the default port.


After server/client options are specified, one can specify options for various models.
To make use of click, we allow these to be separate commands.

    super_hydro ... GPE --Nx 64 --Ny 64 GPEBreather --Nxy 256

Goals:
* Translation between config file and cli.


"""

import importlib
import pkgutil

import click
from click_default_group import DefaultGroup

from .interfaces import IModel
from . import physics


# https://stackoverflow.com/a/58770064/1088938
class ModelGroup(DefaultGroup):
    """Group of models as commands allowing each model to have different arguments."""

    models = {}

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

    @classmethod
    def set_verbosity(cls, ctx, param, value):
        cls.verbosity = value

    @classmethod
    def add_model_modules(cls, ctx, param, names):
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
            name=name, params=params, help=Model.__doc__, add_help_option=False
        )
        return command


# May be no point in using this: it breaks in some cases like:
# super_hydro --test-cli
# https://github.com/click-contrib/click-default-group/issues/17
@click.group(cls=ModelGroup, default="client", default_if_no_args=True)
@click.version_option()
@click.option(
    "--test-cli",
    is_flag=True,
    help="Just process arguments, don't run anything. (For testing).",
)
@click.option(
    "--models",
    "-m",
    multiple=True,
    help="Importable module containing models.",
    is_eager=True,
    callback=ModelGroup.add_model_modules,
)
@click.option(
    "--verbose",
    "-v",
    help="Increase verbosity (-vvv to see all models)",
    count=True,
    is_eager=True,
    callback=ModelGroup.set_verbosity,
)
@click.pass_context
def super_hydro(ctx, models, **kw):
    print(f"{models}")
    click.echo(f"Main app with context {ctx.params}!")
    pass


@super_hydro.command()
@click.pass_context
def client(ctx, **kw):
    click.echo(f"Running Client with context {ctx.params}!")


@super_hydro.command()
@click.pass_context
def server(ctx):
    click.echo(f"Running Server with context {ctx.params}!")


if __name__ == "__main__":
    super_hydro()
