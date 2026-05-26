from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.interfaces.web.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_vault():
    with patch("src.interfaces.web.router._vault") as m:
        m.list_services.return_value = ["svc1"]
        m.list_credentials.return_value = [{"username": "usr1"}]
        m.get_password.return_value = "secret123"
        yield m


@pytest.fixture(autouse=True)
def mock_config():
    with (
        patch("src.interfaces.web.router.load_config", return_value={}),
        patch("src.interfaces.web.router.save_config") as m,
    ):
        yield m


@pytest.fixture(autouse=True)
def mock_registry():
    with (
        patch("src.interfaces.web.router.TaskRegistry.list", return_value=["bulk-register-users"]),
        patch("src.interfaces.web.router.TaskRegistry.auto_discover"),
        patch("src.interfaces.web.router.TaskRegistry.get_schema", return_value=[{"name": "x", "type": "string"}]),
    ):
        yield


class TestIndex:
    def test_returns_html(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


class TestFocus:
    def test_focus_returns_ok(self):
        resp = client.get("/_focus")
        assert resp.status_code == 200
        assert resp.json() == {"status": "focused"}


class TestListCredentials:
    def test_returns_service_list(self, mock_vault):
        resp = client.get("/api/credentials")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["service"] == "svc1"
        assert data[0]["usernames"] == ["usr1"]


class TestSaveCredential:
    def test_saves_valid_credential(self, mock_vault):
        resp = client.post("/api/credentials", json={"service": "s", "username": "u", "password": "p"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        mock_vault.set_password.assert_called_once_with("s", "u", "p")

    def test_rejects_missing_fields(self, mock_vault):
        resp = client.post("/api/credentials", json={"service": "s"})
        assert resp.status_code == 400


class TestGetCredential:
    def test_returns_credential(self, mock_vault):
        resp = client.get("/api/credentials/svc1?username=usr1")
        assert resp.status_code == 200
        assert resp.json()["password"] == "secret123"

    def test_returns_404_if_missing(self, mock_vault):
        mock_vault.get_password.return_value = None
        resp = client.get("/api/credentials/unknown?username=u")
        assert resp.status_code == 404

    def test_requires_username(self, mock_vault):
        resp = client.get("/api/credentials/svc1")
        assert resp.status_code == 400


class TestDeleteCredential:
    def test_deletes_service(self, mock_vault):
        resp = client.delete("/api/credentials/svc1")
        assert resp.status_code == 200
        mock_vault.delete_password.assert_called_once_with("svc1")


@pytest.fixture(autouse=True)
def mock_pool():
    with patch("src.interfaces.web.router._pool") as m:
        m.start.return_value = "abc12345"
        m.list_all.return_value = {}
        m.get.return_value = None
        yield m


class TestTasks:
    def test_list_tasks(self, mock_vault):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert "bulk-register-users" in data["available"]
        assert "current_status" not in data

    def test_run_task(self, mock_vault, mock_pool):
        resp = client.post("/api/run/bulk-register-users")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert "task_id" in data

    def test_list_running(self, mock_vault, mock_pool):
        resp = client.get("/api/tasks/running")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_pause_by_id_not_found(self, mock_pool):
        resp = client.post("/api/tasks/nonexistent/pause")
        assert resp.status_code == 404

    def test_cancel_by_id_not_found(self, mock_pool):
        resp = client.post("/api/tasks/nonexistent/cancel")
        assert resp.status_code == 404


class TestTaskConfig:
    def test_get_config_returns_empty_by_default(self, mock_vault, mock_config):
        resp = client.get("/api/tasks/test-task/config")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_save_config(self, mock_vault, mock_config):
        resp = client.post("/api/tasks/test-task/config", json={"key": "val"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "saved"}
        mock_config.assert_called_once_with("test-task", {"key": "val"})

    def test_run_saves_config_when_body_provided(self, mock_vault, mock_config):
        resp = client.post("/api/run/test-task", json={"env": "prod"})
        assert resp.status_code == 200
        mock_config.assert_called_once_with("test-task", {"env": "prod"})


class TestTaskSchema:
    def test_get_schema(self, mock_vault, mock_registry):
        resp = client.get("/api/tasks/test-task/schema")
        assert resp.status_code == 200
        assert resp.json() == [{"name": "x", "type": "string"}]
