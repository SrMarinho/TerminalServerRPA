import ctypes
import ctypes.wintypes
import os
import secrets
import socket
from pathlib import Path

import keyring

_MUTEX_NAME = "TerminalServerRPA-{}".format(
    str(Path(__file__).resolve().parent.parent.parent).replace("\\", "_").replace(":", "")
)


def _create_mutex(name: str):
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, name)
    last_error = ctypes.GetLastError()
    return mutex, last_error


def is_first_instance() -> bool:
    _, last_error = _create_mutex(_MUTEX_NAME)
    return last_error != 0xDE  # ERROR_ALREADY_EXISTS


def _get_app_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "TerminalServerRPA"


def _get_port_path() -> Path:
    return _get_app_dir() / "port.txt"


def save_port(port: int):
    path = _get_port_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(port), encoding="utf-8")


def read_port() -> int | None:
    path = _get_port_path()
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except OSError:
        return None
    except ValueError:
        return None


def focus_existing_instance():
    port = read_port()
    if port is None:
        return False
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2) as s:
            s.sendall(b"GET /_focus HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
            s.recv(1024)
        return True
    except OSError:
        # TimeoutError and ConnectionRefusedError are OSError subclasses.
        return False


_TOKEN_SERVICE = "TerminalServerRPA"
_TOKEN_KEY = "_api_token"


def get_or_create_token() -> str:
    """Return the existing API token or generate one, stored in the OS keyring."""
    existing = keyring.get_password(_TOKEN_SERVICE, _TOKEN_KEY)
    if existing:
        return existing
    token = secrets.token_hex(32)
    keyring.set_password(_TOKEN_SERVICE, _TOKEN_KEY, token)
    # Best-effort cleanup of the legacy plaintext token file.
    (_get_app_dir() / "token.txt").unlink(missing_ok=True)
    return token
