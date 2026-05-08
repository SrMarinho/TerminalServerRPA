import asyncio
import socket
import webbrowser
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.infrastructure.logger import configure_logger, get_logger, set_ws_queue
from src.infrastructure.single_instance import focus_existing_instance, is_first_instance, save_port
from src.interfaces.web.router import router
from src.interfaces.web.websocket import broadcast_from_queue

log = get_logger("senior-rpa.server")


def find_free_port(start: int = 8080, max_attempts: int = 100) -> int:
    for port in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"no free port found in range {start}-{start + max_attempts}")


def _build_app(ws_queue: asyncio.Queue) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        bg = asyncio.create_task(broadcast_from_queue(ws_queue))
        log.info("ws.broadcast.started")
        yield
        bg.cancel()

    app = FastAPI(title="senior-rpa", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    return app


def run_server(port: int = 8080, open_browser: bool = True):
    if not is_first_instance():
        log.info("instance.duplicate", action="focus_existing")
        if focus_existing_instance():
            return
        log.warning("instance.focus_failed", action="start_anyway")

    configure_logger()
    actual_port = find_free_port(start=port)
    save_port(actual_port)

    if actual_port != port:
        log.warning("port.busy", requested=port, fallback=actual_port)
    log.info("server.starting", port=actual_port)

    ws_queue: asyncio.Queue = asyncio.Queue()
    set_ws_queue(ws_queue)
    app = _build_app(ws_queue)

    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{actual_port}")

    uvicorn.run(app, host="127.0.0.1", port=actual_port, log_level="info")
