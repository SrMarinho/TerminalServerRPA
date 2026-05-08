import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.password_vault.router import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_vault():
    with patch("src.password_vault.router._vault") as m:
        m.list_services.return_value = ["svc1"]
        m.list_credentials.return_value = [{"username": "usr1"}]
        m.get_password.return_value = "secret123"
        yield m


class TestIndex:
    def test_returns_html(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


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


class TestTasks:
    def test_list_tasks(self, mock_vault):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert "bulk-register-users" in data["available"]
        assert data["current_status"] == "idle"

    def test_run_task(self, mock_vault):
        resp = client.post("/api/run/bulk-register-users")
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"

    def test_pause_resume_cancel(self, mock_vault):
        assert client.post("/api/tasks/pause").status_code == 200
        assert client.post("/api/tasks/resume").status_code == 200
        assert client.post("/api/tasks/cancel").status_code == 200
