import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.infrastructure.logger import get_logger
from src.interfaces.base_server import BaseServer, find_free_port
from src.interfaces.web.router import api_router, dev_router, router

log = get_logger("TerminalServerRPA.server")

STATIC_DIR = Path(__file__).parent / "static"


class WebServer(BaseServer):
    def __init__(self, port: int = 8080, open_browser: bool = True, dev: bool = False) -> None:
        super().__init__(port=port, dev=dev)
        self._open_browser = open_browser

    def start(self) -> None:
        actual_port = self._setup()
        if actual_port is None:
            return

        if actual_port != self._port:
            log.warning("port.busy", requested=self._port, fallback=actual_port)

        if self._dev:
            self._enable_dev_mode()
            log.info("server.dev_mode", reload_dirs="templates, static")

        (log.debug if self._dev else log.info)("server.starting", port=actual_port)

        app = self._build_app()

        if self._open_browser:
            webbrowser.open(f"http://127.0.0.1:{actual_port}")

        config = uvicorn.Config(
            app, host="127.0.0.1", port=actual_port, log_config=self._uvicorn_log_config(), access_log=False
        )
        server = uvicorn.Server(config)
        app.state.server = server
        server.run()

    def start_in_thread(self, app: FastAPI, actual_port: int) -> uvicorn.Server:
        config = uvicorn.Config(
            app, host="127.0.0.1", port=actual_port, log_config=self._uvicorn_log_config(), access_log=False
        )
        server = uvicorn.Server(config)
        threading.Thread(target=server.run, daemon=True).start()
        return server

    def build_app(self) -> tuple[FastAPI, int]:
        actual_port = find_free_port(start=self._port)
        if self._dev:
            self._enable_dev_mode()
        return self._build_app(), actual_port

    @staticmethod
    def _build_app() -> FastAPI:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            import asyncio

            from src.config.settings import PLUGINS_DIRS
            from src.infrastructure import events
            from src.infrastructure.schedule_manager import get_schedule_manager
            from src.infrastructure.task_registry import TaskRegistry
            from src.interfaces.web.websocket import broadcast_event, capture_loop

            try:
                TaskRegistry.auto_discover()
            except Exception:
                log.exception("lifespan.auto_discover_failed")
            capture_loop()
            events.subscribe(broadcast_event)
            try:
                get_schedule_manager().start()
            except Exception:
                log.exception("lifespan.scheduler_start_failed")
            WebServer._check_for_update()

            watcher_task = asyncio.create_task(WebServer._watch_plugins(PLUGINS_DIRS))
            log.info("plugin.watcher_started", dirs=[str(d) for d in PLUGINS_DIRS])

            yield

            watcher_task.cancel()
            get_schedule_manager().shutdown()
            events.unsubscribe(broadcast_event)

            from src.infrastructure.execution_manager import close_manager
            from src.infrastructure.task_runner import get_pool

            get_pool().shutdown()
            close_manager()
            log.info("server.shutdown.cleanup_done")

        app = FastAPI(title="TerminalServerRPA", version="0.1.0", lifespan=lifespan)
        if STATIC_DIR.exists():
            app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        from src.config.settings import ASSETS_DIR

        if ASSETS_DIR.exists():
            app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

        app.include_router(router)
        app.include_router(api_router)

        import src.config.settings as _settings

        if _settings.DEV_MODE:
            app.include_router(dev_router)

        return app

    @staticmethod
    async def _watch_plugins(plugins_dirs: list[Path]) -> None:
        import asyncio

        from watchfiles import awatch

        from src.infrastructure.plugin_loader import reload_plugins

        watch_paths = [str(d) for d in plugins_dirs if d.exists()]
        if not watch_paths:
            return
        try:
            async for changes in awatch(*watch_paths, watch_filter=lambda _, p: p.endswith(".py")):
                changed_files = {c[1] for c in changes}
                log.info("plugin.changed", files=list(changed_files))
                await asyncio.sleep(0.1)  # debounce
                try:
                    reloaded = reload_plugins()
                    log.info("plugin.reloaded", plugins=reloaded)
                except Exception:
                    log.exception("plugin.reload_failed")
        except asyncio.CancelledError:
            pass

    @staticmethod
    def _check_for_update() -> None:
        from src.config.version import VERSION
        from src.infrastructure.updater import check_for_update

        def _run():
            try:
                check_for_update(VERSION)
            except Exception:
                log.exception("update.background_check_failed")

        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def _uvicorn_log_config() -> dict:
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


def run_server(port: int = 8080, open_browser: bool = True, dev: bool = False) -> None:
    WebServer(port=port, open_browser=open_browser, dev=dev).start()
