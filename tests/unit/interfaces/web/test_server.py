from unittest.mock import MagicMock, patch

from fastapi import FastAPI


class TestFindFreePort:
    def test_returns_port_when_free(self):
        from src.interfaces.web.server import find_free_port

        with patch("socket.socket") as mock_sock:
            inst = MagicMock()
            inst.connect_ex.return_value = 1
            mock_sock.return_value.__enter__.return_value = inst
            assert find_free_port(9000) == 9000

    def test_falls_back_when_busy(self):
        from src.interfaces.web.server import find_free_port

        def connect_ex_side_effect(addr):
            return 0 if addr[1] == 9000 else 1

        with patch("socket.socket") as mock_sock:
            inst = MagicMock()
            inst.connect_ex.side_effect = connect_ex_side_effect
            mock_sock.return_value.__enter__.return_value = inst
            assert find_free_port(9000) == 9001

    def test_raises_when_all_busy(self):
        import pytest

        from src.interfaces.web.server import find_free_port

        with patch("socket.socket") as mock_sock:
            inst = MagicMock()
            inst.connect_ex.return_value = 0
            mock_sock.return_value.__enter__.return_value = inst
            with pytest.raises(RuntimeError, match="no free port"):
                find_free_port(9000, max_attempts=3)


class TestBuildApp:
    def test_returns_fastapi_app(self):
        from src.interfaces.web.server import WebServer

        app = WebServer._build_app()
        assert isinstance(app, FastAPI)
        assert app.title == "TerminalServerRPA"

    def test_includes_router(self):
        from src.interfaces.web.server import WebServer

        app = WebServer._build_app()
        routes = [r.path for r in app.routes]
        assert "/api/credentials" in routes
        assert "/" in routes


# run_server delegates to WebServer.start(), which runs BaseServer._setup().
# The single-instance / port helpers are resolved in base_server, so patches
# target that module; uvicorn/webbrowser are imported into the server module.
class TestRunServer:
    @patch("src.interfaces.web.server.uvicorn")
    @patch("src.interfaces.web.server.webbrowser")
    @patch("src.interfaces.base_server.save_port")
    @patch("src.interfaces.base_server.configure_logger")
    @patch("src.interfaces.base_server.find_free_port", return_value=8080)
    @patch("src.interfaces.base_server.is_first_instance", return_value=True)
    def test_starts_uvicorn(self, mock_first, mock_port, mock_log, mock_save, mock_web, mock_uvicorn):
        from src.interfaces.web.server import run_server

        run_server(port=8080, open_browser=False)
        mock_uvicorn.Config.assert_called_once()
        assert mock_uvicorn.Config.call_args[1]["port"] == 8080
        mock_uvicorn.Server.return_value.run.assert_called_once()

    @patch("src.interfaces.web.server.uvicorn")
    @patch("src.interfaces.web.server.webbrowser")
    @patch("src.interfaces.base_server.save_port")
    @patch("src.interfaces.base_server.configure_logger")
    @patch("src.interfaces.base_server.find_free_port", return_value=8080)
    @patch("src.interfaces.base_server.is_first_instance", return_value=True)
    def test_opens_browser(self, mock_first, mock_port, mock_log, mock_save, mock_web, mock_uvicorn):
        from src.interfaces.web.server import run_server

        run_server(port=8080, open_browser=True)
        mock_web.open.assert_called_once_with("http://127.0.0.1:8080")

    @patch("src.interfaces.web.server.uvicorn")
    @patch("src.interfaces.web.server.webbrowser")
    @patch("src.interfaces.base_server.save_port")
    @patch("src.interfaces.base_server.configure_logger")
    @patch("src.interfaces.base_server.find_free_port", return_value=8081)
    @patch("src.interfaces.base_server.is_first_instance", return_value=True)
    def test_uses_fallback_port(self, mock_first, mock_port, mock_log, mock_save, mock_web, mock_uvicorn):
        from src.interfaces.web.server import run_server

        run_server(port=8080, open_browser=False)
        mock_uvicorn.Config.assert_called_once()
        assert mock_uvicorn.Config.call_args[1]["port"] == 8081
        mock_uvicorn.Server.return_value.run.assert_called_once()

    @patch("src.interfaces.web.server.uvicorn")
    @patch("src.interfaces.base_server.focus_existing_instance", return_value=True)
    @patch("src.interfaces.base_server.is_first_instance", return_value=False)
    def test_focuses_existing_when_duplicate(self, mock_first, mock_focus, mock_uvicorn):
        from src.interfaces.web.server import run_server

        run_server(port=8080, open_browser=False)
        mock_focus.assert_called_once()
        mock_uvicorn.Server.return_value.run.assert_not_called()
