import os
import threading
import time
from typing import Any

import webview

from src.config.settings import ASSETS_DIR
from src.config.version import VERSION
from src.infrastructure.logger import get_logger
from src.interfaces.base_server import BaseServer
from src.interfaces.gui.tray import TrayIcon
from src.interfaces.gui.update_flow import UpdateFlow
from src.interfaces.gui.webview_assets import load_asset
from src.interfaces.web.server import WebServer

log = get_logger("TerminalServerRPA.gui")


class GuiServer(BaseServer):
    """Native window lifecycle: pywebview window + wiring of tray/update threads."""

    def __init__(self, port: int = 8080, dev: bool = False) -> None:
        super().__init__(port=port, dev=dev)
        self._window: Any = None
        self._web = WebServer(port=port, open_browser=False, dev=dev)

    def start(self) -> None:
        from src.infrastructure.playwright_setup import ensure_playwright_driver

        ensure_playwright_driver()

        actual_port = self._setup()
        if actual_port is None:
            return

        if self._dev:
            self._enable_dev_mode()

        app, actual_port = self._web.build_app()
        app_url = f"http://127.0.0.1:{actual_port}"

        uvicorn_server = self._web.start_in_thread(app, actual_port)
        app.state.server = uvicorn_server

        self._window = webview.create_window(
            f"Terminal Server RPA v{VERSION}",
            html=load_asset("loading.html").replace("__VERSION__", f"v{VERSION}"),
            width=1280,
            height=800,
            min_size=(900, 600),
            maximized=True,
        )
        app.state.window = self._window
        self._window.events.closing += self._on_closing

        try:
            import pyi_splash

            pyi_splash.close()
        except ImportError:
            pass

        self._install_ctrl_c_handler()
        threading.Thread(target=self._wait_and_navigate, args=(app_url, actual_port), daemon=True).start()
        threading.Thread(target=UpdateFlow(self._window).run, daemon=True).start()
        threading.Thread(target=TrayIcon(self._window).run, daemon=True).start()
        webview.start(icon=str(ASSETS_DIR / "icon.ico"), debug=self._dev)

    def _wait_and_navigate(self, url: str, port: int) -> None:
        import httpx

        for _ in range(30):
            try:
                httpx.get(f"http://127.0.0.1:{port}/_health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        self._window.load_url(url)

    def _on_closing(self) -> bool:
        # Never actually close on the window's X button — just hide to tray.
        # Quitting is done from the tray's "Sair" menu item.
        self._window.hide()
        return False

    @staticmethod
    def _install_ctrl_c_handler() -> None:
        if os.name != "nt":
            return
        import ctypes

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
        def _handler(ctrl_type: int) -> bool:
            if ctrl_type in (0, 1):  # CTRL_C_EVENT, CTRL_BREAK_EVENT
                os._exit(0)
            return False

        ctypes.windll.kernel32.SetConsoleCtrlHandler(_handler, True)


def run_server(port: int = 8080, dev: bool = False) -> None:
    GuiServer(port=port, dev=dev).start()
