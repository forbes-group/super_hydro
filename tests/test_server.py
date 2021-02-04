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
        param = "unknown_param_a"
        while param in cmds["get"]:
            param = param + "a"
        res = server.get([param])
        assert param in res
        assert res[param] == f"Error: Unknown parameter {param}"
        for param in cmds["get"]:
            res = server.get([param])
            assert param in res
            val = res[param]
            if isinstance(val, str):
                assert not val.startswith("Error: Unknown parameter")
