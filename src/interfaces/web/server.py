import asyncio
import socket
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.infrastructure.logger import configure_logger, get_logger, set_ws_queue
from src.infrastructure.single_instance import focus_existing_instance, is_first_instance, save_port
from src.interfaces.web.router import api_router, dev_router, router
from src.interfaces.web.websocket import broadcast_from_queue

log = get_logger("TerminalServerRPA.server")

STATIC_DIR = Path(__file__).parent / "static"


def _check_for_update() -> None:
    """Check GitHub for a newer release and prompt the user via the UI."""
    import threading

    from src.config.version import VERSION
    from src.infrastructure.updater import check_for_update

    def _run():
        try:
            release = check_for_update(VERSION)
            if release is None:
                return
            log.info("update.available", version=release.version, url=release.html_url)
            # In a full UI this would show a notification.  For now the
            # user can always trigger the update via GET /api/update.
        except Exception:
            log.exception("update.background_check_failed")

    threading.Thread(target=_run, daemon=True).start()


def find_free_port(start: int = 8080, max_attempts: int = 100) -> int:
    for port in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"no free port found in range {start}-{start + max_attempts}")


def _build_app(ws_queue: asyncio.Queue) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from src.infrastructure.task_registry import TaskRegistry

        TaskRegistry.auto_discover()  # scan tasks once at startup
        bg = asyncio.create_task(broadcast_from_queue(ws_queue))
        log.info("ws.broadcast.started")

        # Check for updates in the background (fire-and-forget).
        _check_for_update()

        yield
        bg.cancel()
        from src.infrastructure.execution_manager import close_manager
        from src.infrastructure.task_runner import get_pool

        get_pool().shutdown()
        close_manager()
        log.info("server.shutdown.cleanup_done")

    app = FastAPI(title="TerminalServerRPA", version="0.1.0", lifespan=lifespan)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(router)
    app.include_router(api_router)
    import src.config.settings as _settings

    if _settings.DEV_MODE:
        app.include_router(dev_router)
    return app


def _uvicorn_log_config():
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"null": {"class": "logging.NullHandler"}},
        "loggers": {
            "uvicorn": {"handlers": ["null"], "propagate": False, "level": "ERROR"},
            "uvicorn.access": {"handlers": ["null"], "propagate": False},
            "uvicorn.error": {"handlers": ["null"], "propagate": False},
        },
    }


def run_server(port: int = 8080, open_browser: bool = True, dev: bool = False):
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
    (log.debug if dev else log.info)("server.starting", port=actual_port)

    # Enable dev mode before building the app so dev-only routes register.
    if dev:
        import src.config.settings as _settings

        _settings.DEV_MODE = True
        log.info("server.dev_mode", reload_dirs="templates, static")

    ws_queue: asyncio.Queue = asyncio.Queue()
    set_ws_queue(ws_queue)
    app = _build_app(ws_queue)

    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{actual_port}")

    config = uvicorn.Config(app, host="127.0.0.1", port=actual_port, log_config=_uvicorn_log_config(), access_log=False)
    server = uvicorn.Server(config)
    app.state.server = server
    server.run()
