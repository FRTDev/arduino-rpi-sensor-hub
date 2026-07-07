import importlib
import sys

import pytest


@pytest.fixture()
def server_module(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_USERNAME", "tester")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "test-password")
    monkeypatch.setenv("GATEWAY_API_KEY", "test-gateway-key")
    monkeypatch.setenv("IOT_DB_PATH", str(tmp_path / "test.db"))

    sys.modules.pop("serveur.server", None)
    import serveur.server as server

    server = importlib.reload(server)
    server.init_db()
    server.app.config.update(TESTING=True)
    return server


@pytest.fixture()
def client(server_module):
    return server_module.app.test_client()
