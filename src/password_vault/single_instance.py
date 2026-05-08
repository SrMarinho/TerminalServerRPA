import ctypes
import ctypes.wintypes
import os
import socket
from pathlib import Path

_MUTEX_NAME = "SeniorRPA-{0}".format(
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


def _get_port_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "senior-rpa" / "port.txt"


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
    except (ValueError, OSError):
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
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False
