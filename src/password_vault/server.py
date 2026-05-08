import socket
import uvicorn
import webbrowser
from fastapi import FastAPI
from src.password_vault.router import router
from src.password_vault.logger import get_logger

log = get_logger("senior-rpa.server")


def find_free_port(start: int = 8080, max_attempts: int = 100) -> int:
    for port in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"no free port found in range {start}-{start + max_attempts}")


def create_app() -> FastAPI:
    app = FastAPI(title="senior-rpa", version="0.1.0")
    app.include_router(router)
    return app


def run_server(port: int = 8080, open_browser: bool = True):
    actual_port = find_free_port(start=port)
    if actual_port != port:
        log.warning("port.busy", requested=port, fallback=actual_port)
    log.info("server.starting", port=actual_port)
    app = create_app()
    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{actual_port}")
    uvicorn.run(app, host="127.0.0.1", port=actual_port, log_level="info")
