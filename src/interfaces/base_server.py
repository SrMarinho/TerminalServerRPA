import socket
from abc import ABC, abstractmethod

from src.infrastructure.logger import configure_logger, get_logger
from src.infrastructure.single_instance import focus_existing_instance, is_first_instance, save_port

log = get_logger("TerminalServerRPA.server")


_SM_REMOTESESSION = 0x1000  # GetSystemMetrics: running inside an RDP/TS session


def _warn_if_remote_session() -> None:
    """Warn when running inside a Terminal Server / RDP session.

    Loopback is shared across all sessions on the same host: another logged-in
    user could fetch GET / and read the API token. The app is designed for a
    single-user workstation; flag the risky deployment instead of silently
    accepting it.
    """
    import ctypes

    try:
        if ctypes.windll.user32.GetSystemMetrics(_SM_REMOTESESSION):
            log.warning(
                "server.remote_session_detected",
                risk="loopback is shared across sessions; other users on this host can reach the local API",
            )
    except Exception:  # non-Windows or restricted environment — best effort
        pass


def find_free_port(start: int = 8080, max_attempts: int = 100) -> int:
    for port in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"no free port found in range {start}-{start + max_attempts}")


class BaseServer(ABC):
    def __init__(self, port: int = 8080, dev: bool = False) -> None:
        self._port = port
        self._dev = dev

    @abstractmethod
    def start(self) -> None: ...

    def _setup(self) -> int | None:
        """Check single instance, configure logger, find port. Returns actual_port or None if should exit."""
        if not is_first_instance():
            log.info("instance.duplicate", action="focus_existing")
            if focus_existing_instance():
                return None
            log.warning("instance.focus_failed", action="start_anyway")

        configure_logger()
        _warn_if_remote_session()
        actual_port = find_free_port(start=self._port)
        save_port(actual_port)
        return actual_port

    def _enable_dev_mode(self) -> None:
        import src.config.settings as _settings

        _settings.DEV_MODE = True
