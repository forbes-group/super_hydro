import pytest

import super_hydro.server
import super_hydro.client.dumb


@pytest.fixture
def server():
    app = super_hydro.client.dumb.run(run_server=True, network_server=False)
    yield app.server
    app.quit()


class TestServer(object):
    def test_get(self, server):
        """Test that the server can return all parameters"""
        cmds = server.get_available_commands()
        for param in cmds["get"]:
            val = server.get([param])
        assert val is not None
