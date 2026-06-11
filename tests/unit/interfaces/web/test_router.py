from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.interfaces.web.router import api_router, get_pool, get_vault, router

app = FastAPI()
app.include_router(router)
app.include_router(api_router)
client = TestClient(app)

AUTH_TOKEN = "test-token-123"


@pytest.fixture(autouse=True)
def mock_token():
    # get_or_create_token is imported by both deps.py (verify_token) and ui.py
    # (index + ws handshake) — patch both bindings.
    with (
        patch("src.interfaces.web.routes.deps.get_or_create_token", return_value=AUTH_TOKEN),
        patch("src.interfaces.web.routes.ui.get_or_create_token", return_value=AUTH_TOKEN),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_vault():
    m = MagicMock()
    m.list_services.return_value = ["svc1"]
    m.list_credentials.return_value = [{"username": "usr1"}]
    m.get_password.return_value = "secret123"
    app.dependency_overrides[get_vault] = lambda: m
    yield m
    app.dependency_overrides.pop(get_vault, None)


@pytest.fixture(autouse=True)
def mock_config():
    with (
        patch("src.interfaces.web.routes.tasks.load_config", return_value={}),
        patch("src.interfaces.web.routes.tasks.save_config") as m,
    ):
        yield m


@pytest.fixture(autouse=True)
def mock_registry():
    # Class-attribute patches: the canonical path affects every module that
    # imported the TaskRegistry class.
    with (
        patch(
            "src.infrastructure.task_registry.TaskRegistry.list",
            return_value=["bulk-register-users"],
        ),
        patch("src.infrastructure.task_registry.TaskRegistry.auto_discover"),
        patch(
            "src.infrastructure.task_registry.TaskRegistry.get_schema",
            return_value=[{"name": "x", "type": "string"}],
        ),
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
        resp = client.get(
            "/api/credentials",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["service"] == "svc1"
        assert data[0]["usernames"] == ["usr1"]

    def test_rejects_without_token(self):
        resp = client.get("/api/credentials")
        assert resp.status_code == 401


class TestSaveCredential:
    def test_saves_valid_credential(self, mock_vault):
        resp = client.post(
            "/api/credentials",
            json={"service": "s", "username": "u", "password": "p"},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        mock_vault.set_password.assert_called_once_with("s", "u", "p")

    def test_rejects_missing_fields(self, mock_vault):
        resp = client.post(
            "/api/credentials",
            json={"service": "s"},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 422  # Pydantic validation (username or password required)

    def test_rejects_empty_service(self, mock_vault):
        resp = client.post(
            "/api/credentials",
            json={"service": "", "username": "u", "password": "p"},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 422


class TestGetCredential:
    def test_returns_credential(self, mock_vault):
        resp = client.get(
            "/api/credentials/svc1?username=usr1",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        assert resp.json()["password"] == "***"

    def test_returns_404_if_missing(self, mock_vault):
        mock_vault.get_password.return_value = None
        resp = client.get(
            "/api/credentials/unknown?username=u",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 404

    def test_requires_username(self, mock_vault):
        resp = client.get(
            "/api/credentials/svc1",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 400


class TestDeleteCredential:
    def test_deletes_service(self, mock_vault):
        resp = client.delete(
            "/api/credentials/svc1",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        mock_vault.delete_password.assert_called_once_with("svc1")


@pytest.fixture(autouse=True)
def mock_pool():
    m = MagicMock()
    m.start.return_value = "abc12345"
    m.list_all.return_value = {}
    m.get.return_value = None
    app.dependency_overrides[get_pool] = lambda: m
    yield m
    app.dependency_overrides.pop(get_pool, None)


class TestTasks:
    def test_list_tasks(self, mock_vault):
        resp = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "bulk-register-users" in data["available"]

    def test_run_task(self, mock_vault, mock_pool):
        resp = client.post(
            "/api/run/bulk-register-users",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert "task_id" in data

    def test_list_running(self, mock_vault, mock_pool):
        resp = client.get(
            "/api/tasks/running",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_pause_by_id_not_found(self, mock_pool):
        resp = client.post(
            "/api/tasks/nonexistent/pause",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 404

    def test_cancel_by_id_not_found(self, mock_pool):
        resp = client.post(
            "/api/tasks/nonexistent/cancel",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 404


class TestTaskConfig:
    def test_get_config_returns_empty_by_default(self, mock_vault, mock_config):
        resp = client.get(
            "/api/tasks/test-task/config",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_save_config(self, mock_vault, mock_config):
        resp = client.post(
            "/api/tasks/test-task/config",
            json={"key": "val"},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "saved"}
        mock_config.assert_called_once_with("test-task", {"key": "val"})

    def test_run_saves_config_when_body_provided(self, mock_vault, mock_config):
        resp = client.post(
            "/api/run/test-task",
            json={"env": "prod"},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        mock_config.assert_called_once_with("test-task", {"env": "prod"})


class TestTaskSchema:
    def test_get_schema(self, mock_vault, mock_registry):
        resp = client.get(
            "/api/tasks/test-task/schema",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200
        assert resp.json() == [{"name": "x", "type": "string"}]


class TestWebSocketAuth:
    def test_ws_rejects_missing_token(self):
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect("/ws"):
            pass
        assert exc.value.code == 1008

    def test_ws_rejects_invalid_token(self):
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect("/ws?token=wrong"):
            pass
        assert exc.value.code == 1008

    def test_ws_accepts_valid_token(self):
        with client.websocket_connect(f"/ws?token={AUTH_TOKEN}") as ws:
            assert ws is not None


class TestShutdown:
    def test_shutdown_requests_graceful_exit(self):
        from unittest.mock import Mock

        mock_server = Mock()
        mock_server.should_exit = False
        app.state.server = mock_server
        try:
            resp = client.post("/api/shutdown", headers={"Authorization": f"Bearer {AUTH_TOKEN}"})
            assert resp.status_code == 200
            assert mock_server.should_exit is True
        finally:
            del app.state.server

    def test_shutdown_without_server_returns_503(self):
        resp = client.post("/api/shutdown", headers={"Authorization": f"Bearer {AUTH_TOKEN}"})
        assert resp.status_code == 503


class TestDevRouterGating:
    def test_snippet_route_absent_without_dev_router(self):
        # The default app (production) does not include dev_router, so the
        # arbitrary-code snippet endpoint does not exist at all.
        resp = client.post(
            "/api/executions/x/snippet",
            json={"code": "print(1)"},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 404

    def test_snippet_route_present_when_dev_router_included(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from src.interfaces.web.router import api_router, dev_router, router

        dev_app = FastAPI()
        dev_app.include_router(router)
        dev_app.include_router(api_router)
        dev_app.include_router(dev_router)
        dev_client = TestClient(dev_app)
        resp = dev_client.post(
            "/api/executions/x/snippet",
            json={"code": "print(1)"},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        # Route exists now; DEV_MODE guard returns 403 (DEV_MODE off in tests).
        assert resp.status_code == 403
