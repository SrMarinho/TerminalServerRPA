import pytest
from unittest.mock import patch, MagicMock, call
import logging


@pytest.fixture(autouse=True)
def cleanup_logger():
    root = logging.getLogger()
    handlers = root.handlers[:]
    root.handlers.clear()
    yield
    root.handlers.clear()
    root.handlers.extend(handlers)


class TestConfigureLogger:
    def test_adds_file_and_console_handlers(self, cleanup_logger):
        from src.password_vault.logger import configure_logger
        configure_logger()
        root = logging.getLogger()
        handler_types = [type(h).__name__ for h in root.handlers]
        assert "RotatingFileHandler" in handler_types
        assert "StreamHandler" in handler_types

    def test_respects_custom_level(self, cleanup_logger):
        from src.password_vault.logger import configure_logger
        configure_logger(level=logging.WARNING)
        root = logging.getLogger()
        assert root.level == logging.WARNING


class TestWsBridge:
    def test_set_bridge(self):
        import src.password_vault.logger as logger_mod
        mock_bridge = MagicMock()
        logger_mod.set_ws_bridge(mock_bridge)
        assert logger_mod._ws_bridge == mock_bridge
        logger_mod.set_ws_bridge(None)

    def test_ws_processor_calls_send_when_bridge_set(self):
        import src.password_vault.logger as logger_mod
        mock_bridge = MagicMock()
        logger_mod.set_ws_bridge(mock_bridge)
        result = logger_mod._ws_processor(None, "info", {"event": "test"})
        mock_bridge.send.assert_called_once_with({"event": "test"})
        assert result == {"event": "test"}
        logger_mod.set_ws_bridge(None)

    def test_ws_processor_skips_when_no_bridge(self):
        import src.password_vault.logger as logger_mod
        logger_mod.set_ws_bridge(None)
        result = logger_mod._ws_processor(None, "info", {"event": "test"})
        assert result == {"event": "test"}


class TestGetLogger:
    def test_returns_logger_with_standard_methods(self):
        from src.password_vault.logger import get_logger
        log = get_logger("test-module")
        assert hasattr(log, "info")
        assert hasattr(log, "error")
        assert hasattr(log, "warn")
        assert hasattr(log, "bind")
