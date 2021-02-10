import pytest

import super_hydro.server
import super_hydro.client.dumb


@pytest.fixture
def server():
    app = super_hydro.client.dumb.run(run_server=True, network_server=False)
    yield app.server
    app.quit()


@pytest.fixture
def network_server():
    app = super_hydro.client.dumb.run(run_server=True, network_server=True)
    yield app.server
    app.quit()
    

class TestServer(object):
    def test_get(self, server):
        """Test that the server can return all parameters"""
        cmds = server.get_available_commands()
        for param in cmds["get"]:
            val = server.get([param])
        assert val is not None


@pytest.mark.skip("Known failure... need to run network_server in it's own process")
class TestNetworkServer(object):
    def test_get(self, network_server):
        """Test that the server can return all parameters"""
        app = super_hydro.client.dumb.run(run_server=False)
        server = app.server
        cmds = server.get_available_commands()
        for param in cmds["get"]:
            val = server.get([param])
        assert val is not None
