import pytest
import click.testing

import super_hydro.cli


@pytest.fixture
def runner():
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem():
        yield runner


class TestCLI:
    def test_opts(self, runner):
        """Test setting options in various ways."""
        res = runner.invoke(super_hydro.cli.super_hydro, ["--test-cli"])
        ctx = super_hydro.cli._testing["ctx"]
