import pytest
from unittest.mock import patch, MagicMock, call
import logging
import asyncio


@pytest.fixture(autouse=True)
def cleanup_logger():
    root = logging.getLogger()
    handlers = root.handlers[:]
    root.handlers.clear()
    import src.password_vault.logger as logger_mod
    logger_mod._configured = False
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

    def test_is_idempotent(self, cleanup_logger):
        from src.password_vault.logger import configure_logger
        configure_logger()
        root = logging.getLogger()
        count = len(root.handlers)
        configure_logger()
        assert len(root.handlers) == count


class TestWsQueue:
    def test_set_queue(self):
        import src.password_vault.logger as logger_mod
        q = asyncio.Queue()
        logger_mod.set_ws_queue(q)
        assert logger_mod._ws_queue is q
        logger_mod.set_ws_queue(None)

    def test_processor_puts_event(self):
        import src.password_vault.logger as logger_mod
        q = asyncio.Queue()
        logger_mod.set_ws_queue(q)
        logger_mod._ws_processor(None, "info", {"event": "test"})
        assert not q.empty()
        assert q.get_nowait() == {"event": "test"}
        logger_mod.set_ws_queue(None)

    def test_processor_skips_when_no_queue(self):
        import src.password_vault.logger as logger_mod
        logger_mod.set_ws_queue(None)
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
