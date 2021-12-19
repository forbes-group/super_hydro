import sys
import time

import numpy as np

import pytest

import super_hydro.server
import super_hydro.client.minimal


@pytest.fixture
def server():
    app = super_hydro.client.minimal.run(run_server=True, network_server=False)
    yield app.server
    app.quit()


@pytest.fixture
def network_server():
    app = super_hydro.client.minimal.run(run_server=True, network_server=True)
    yield app.server
    app.quit()


class TestServer(object):
    def test_get(self, server):
        """Test that the server can return all parameters"""
        cmds = server.get_available_commands()
        for param in cmds["get"]:
            val = server.get([param])
        assert val is not None

    def test_server_timeout(self, shutdown_seconds=2.0):
        """Test that server stops on time."""
        tic = time.time()
        shutdown = shutdown_seconds / 60.0
        server = super_hydro.server.run(block=True, kwargs=dict(shutdown=shutdown))
        assert server.opts.shutdown == shutdown
        toc = time.time()
        assert np.allclose(toc - tic, shutdown_seconds, atol=1.0)

    def test_opts(self, tmp_path):
        """Test setting options in various ways."""
        kw = dict(block=True, network_server=False, kwargs=dict(shutdown=0))
        server = super_hydro.server.run(**kw)
        assert server.opts.shutdown == 0
        steps_ = server.opts.steps
        steps = steps_ + 2

        # Through a config file specified at the command line
        config_file = tmp_path / "super_hydro.conf"
        with open(config_file, "w") as f:
            f.write("\n".join(["[Parameters]", f"steps = {steps}"]))

        sys.argv.extend(["--config_file", str(config_file)])
        server = super_hydro.server.run(**kw)
        assert server.opts.steps == steps
        steps += 2

        # Through the command line should override config file:
        sys.argv.extend(["--steps", f"{steps}"])
        server = super_hydro.server.run(**kw)
        assert server.opts.steps == steps
        steps += 2

        # Passed in directly should override
        kw["kwargs"]["steps"] = steps
        server = super_hydro.server.run(**kw)
        assert server.opts.steps == steps


@pytest.mark.skip("Known failure... need to run network_server in it's own process")
class TestNetworkServer(object):
    def test_get(self, network_server):
        """Test that the server can return all parameters"""
        app = super_hydro.client.minimal.run(run_server=False)
        server = app.server
        cmds = server.get_available_commands()
        for param in cmds["get"]:
            val = server.get([param])
        assert val is not None
