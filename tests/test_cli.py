from argparse import Namespace

# from contextlib import contextmanager
import importlib
import os.path
import sys
import tempfile
import textwrap

import numpy as np

import pytest

import click.testing

import super_hydro.cli


@pytest.fixture
def runner():
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem() as tmpdirname:
        yield runner
    del tmpdirname


@pytest.fixture
def isolated_filesystem():
    """Create an isolated filesystem, included mock home directory."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        fs = Namespace()
        fs.root = tmpdirname
        fs.home = os.path.join(tmpdirname, "User", "test")
        os.makedirs(fs.home)
        yield fs


CONFIG = """
# General options
[super_hydro]
port = 123456

# Default parameters for all models that support them
[DEFAULT]
steps = 20
Nx = 64
Ny = 68

# Model-specific parameters
[gpe.BEC]
Nx = 73
"""


@pytest.fixture
def config_file(isolated_filesystem):
    fs = isolated_filesystem
    config_file = os.path.join(fs.home, "super_hydro.conf")
    with open(config_file, "w") as f:
        f.write(textwrap.dedent(CONFIG))
    yield config_file


class _TestCLI:
    def test_opts(self, runner):
        """Test setting options in various ways."""
        res = runner.invoke(super_hydro.cli.super_hydro, ["--test-cli"])
        ctx = super_hydro.cli._testing["ctx"]
        del res, ctx


class TestConfiguration:
    def test_1(self, config_file):
        c = super_hydro.cli.Configuration()
        c.add_config_file(config_file)
        opts = c.get_opts()
        assert opts["port"] == 123456

        opts = c.get_opts("gpe.BEC")
        default_opts = c.get_opts("gpe.BEC", no_config=True)
        assert opts["Nx"] == 73 != default_opts["Nx"]
        assert opts["Ny"] == 68 != default_opts["Ny"]

    def test_write(self, config_file):
        c = super_hydro.cli.Configuration()
        c.add_config_file(config_file)

        dirname = os.path.dirname(config_file)
        file1 = os.path.join(dirname, "super_hydro1.conf")
        file2 = os.path.join(dirname, "super_hydro2.conf")
        with open(file1, "w") as f:
            c.get_parser(full=False).write(f)
        with open(file2, "w") as f:
            c.get_parser(full=True).write(f)

        c1 = super_hydro.cli.Configuration()
        c1.add_config_file(file1)
        np.testing.assert_equal(c1._rep, c._rep)
        np.testing.assert_equal(c1._full_rep, c._full_rep)

        c2 = super_hydro.cli.Configuration()
        c2.add_config_file(file2)
        np.testing.assert_equal(c2._full_rep, c._full_rep)

    def test_missing_config_file(self, config_file, capsys):
        """Should ignore missing files."""
        c = super_hydro.cli.Configuration(verbosity=2)
        c.add_config_file(config_file)
        c.add_config_file(config_file + "garbage")
        captured = capsys.readouterr()
        assert captured.out.strip().startswith("Loading configuration from")
        assert captured.out.strip().endswith("/User/test/super_hydro.conf")
        assert not captured.err.strip()

    def test_bad_model(self, isolated_filesystem, capsys):
        BAD_CONFIG = """
        [this_model_does.not.exist]
        Nx=12
        """
        fs = isolated_filesystem
        config_file = os.path.join(fs.home, "super_hydro.conf")
        with open(config_file, "w") as f:
            f.write(textwrap.dedent(BAD_CONFIG))
        c = super_hydro.cli.Configuration(verbosity=2)
        c.add_config_file(config_file)
        c.check()

        captured = capsys.readouterr()
        out = captured.out.strip()
        assert out.startswith("Loading configuration from")
        assert "/User/test/super_hydro.conf" in out
        assert "WARNING: Could not import module=`this_model_does.not.exist`." in out

    def test_multiple_model_modules(self, isolated_filesystem):
        fs = isolated_filesystem
        CONFIGs = [
            """
        [super_hydro]
        model_modules = ['gpe']
        """,
            """
        [super_hydro]
        model_modules = ['testing']
        """,
        ]
        files = []
        for n, _CONFIG in enumerate(CONFIGs):
            config_file = os.path.join(fs.home, f"super_hydro{n}.conf")
            with open(config_file, "w") as f:
                f.write(textwrap.dedent(_CONFIG))
                files.append(config_file)
        c = super_hydro.cli.Configuration()
        list(map(c.add_config_file, files))
        assert set(c.super_hydro_options["model_modules"]) == set(["gpe", "testing"])


class TestConfigurationCoverage:
    """Coverage tests."""

    def test_get_opts_1(self, capsys):
        """Test some exceptions in get_opts"""
        c = super_hydro.cli.Configuration()
        opts = c.get_opts(model_name="model_undefined", check=False)
        assert not opts

        opts = c.get_opts(model_name="model_undefined", check=True)
        assert not opts
        captured = capsys.readouterr()
        out = captured.out.strip()
        assert out == "WARNING: Could not import model_undefined."

    def test_get_opts_2(self, isolated_filesystem, capsys):
        BAD_CONFIG = """
        [testing.HelloWorld]
        param_no_exist = 12

        [testing.HelloWorlds]
        param_no_exist = 12
        """
        fs = isolated_filesystem
        config_file = os.path.join(fs.home, "super_hydro.conf")
        with open(config_file, "w") as f:
            f.write(textwrap.dedent(BAD_CONFIG))
        c = super_hydro.cli.Configuration(verbosity=2)
        c.add_config_file(config_file)
        captured = capsys.readouterr()
        out = captured.out.strip()
        assert out.startswith("Loading configuration from")
        assert "/User/test/super_hydro.conf" in out

        opts = c.get_opts("testing.HelloWorld", check=False)
        assert opts["param_no_exist"] == 12
        captured = capsys.readouterr()
        out = captured.out.strip()
        assert out == ""

        opts = c.get_opts("testing.HelloWorld", check=True)
        captured = capsys.readouterr()
        out = captured.out.strip()
        assert out.startswith(
            "WARNING: param_no_exist not a parameter of testing.HelloWorld"
        )

        # Check that unknown sections are not propagated to the parser.
        parser = c.get_parser()
        assert "testing.HelloWorld" in parser.sections()
        assert "testing.HelloWorlds" not in parser.sections()

    def test__import_model_1(self):
        """Test import exception."""
        c = super_hydro.cli.Configuration()
        Model = c._import_model(model_name="model_undefined", strict=False)
        assert Model is None

        Model = c._import_model(model_name="model.undefined", strict=False)
        assert Model is None

        with pytest.raises(
            ValueError,
            match=r"model_name='model.undefined' must have the form `<module>.<Model>`",
        ):
            Model = c._import_model(model_name="model_undefined", strict=True)

    def test__import_model_2(self, config_file):
        """Test more import exceptions."""
        c = super_hydro.cli.Configuration()
        c.add_config_file(config_file)
        tmpdir = os.path.dirname(config_file)
        with open(os.path.join(tmpdir, "testing.py"), "w") as f:
            f.write(
                textwrap.dedent(
                    """
                    from super_hydro.physics.testing import HelloWorld

                    class HelloWorld(HelloWorld):
                        pass

                    class BadWorld:
                        "Does not implement IModel"
                    """
                )
            )

        sys.path.insert(0, tmpdir)
        ThisModel = importlib.import_module("testing").HelloWorld
        Model = c._import_model(model_name="testing.HelloWorld", strict=False)
        assert Model is ThisModel

        Model = c._import_model(
            model_name="super_hydro.physics.testing.HelloWorld", strict=False
        )
        assert Model is not ThisModel

        with pytest.raises(
            ValueError,
            match=r"Ambiguous models: `\['testing', 'super_hydro.physics.testing'\]`",
        ):
            Model = c._import_model(model_name="testing.HelloWorld", strict=True)

        Model = c._import_model(model_name="testing.HelloWorlds", strict=False)
        assert Model is None

        with pytest.raises(
            AttributeError,
            match=r"Model `testing.HelloWorlds` does not exist.",
        ):
            Model = c._import_model(model_name="testing.HelloWorlds", strict=True)

        Model = c._import_model(model_name="testing.BadWorld", strict=False)
        assert Model is None

        with pytest.raises(
            NotImplementedError,
            match=r"`testing.BadWorld` doesn't implement the IModel interface.",
        ):
            Model = c._import_model(model_name="testing.BadWorld", strict=True)
