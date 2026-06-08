import os
import threading
import time
from typing import Any

import pystray
import webview
from PIL import Image

from src.config.settings import ASSETS_DIR
from src.infrastructure.logger import get_logger
from src.interfaces.base_server import BaseServer
from src.interfaces.web.server import WebServer

log = get_logger("TerminalServerRPA.gui")

_UPDATE_INITIAL_DELAY_S = 5
_UPDATE_POLL_INTERVAL_S = 60

_LOADING_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  :root{--bg-0:#000;--line:#2a2e36;--accent:#4ade80;--accent-glow:rgba(74,222,128,.25);--text-0:#fff;--text-2:#a3a8b5;--text-3:#5a5f6b}
  html,body{height:100%}
  body{
    background:var(--bg-0);
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    height:100vh;
    font-family:'JetBrains Mono',ui-monospace,monospace;
    color:var(--text-2);overflow:hidden;position:relative;
    letter-spacing:-.005em;-webkit-font-smoothing:antialiased;
  }
  body::before{
    content:'';position:fixed;inset:0;
    background-image:linear-gradient(var(--line) 1px,transparent 1px),
      linear-gradient(90deg,var(--line) 1px,transparent 1px);
    background-size:48px 48px;background-position:-1px -1px;opacity:.4;pointer-events:none;
    mask-image:radial-gradient(ellipse at center,black 20%,transparent 75%);
    -webkit-mask-image:radial-gradient(ellipse at center,black 20%,transparent 75%);
  }
  .wrap{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center}
  .tick{width:32px;height:2px;background:var(--accent);margin-bottom:14px;box-shadow:0 0 16px var(--accent-glow)}
  .logo{font-size:2.4rem;font-weight:700;color:var(--text-0);letter-spacing:-.02em}
  .logo .dot{color:var(--accent)}
  .sub{margin-top:10px;font-size:.8rem;color:var(--text-2)}
  .bar{margin-top:32px;width:200px;height:2px;background:var(--line);position:relative;overflow:hidden}
  .bar::after{content:'';position:absolute;top:0;left:0;height:100%;width:40%;
    background:var(--accent);box-shadow:0 0 12px var(--accent-glow);animation:slide 1.2s ease-in-out infinite}
  .msg{margin-top:18px;font-size:.7rem;color:var(--text-3);text-transform:lowercase;letter-spacing:.04em}
  @keyframes slide{0%{left:-40%}100%{left:100%}}
</style>
</head>
<body>
  <div class="wrap">
    <div class="tick"></div>
    <div class="logo">Terminal<span class="dot">&middot;</span>RPA</div>
    <div class="sub">automa&ccedil;&atilde;o rpa para terminal server</div>
    <div class="bar"></div>
    <div class="msg">iniciando servidor...</div>
  </div>
</body>
</html>"""


class GuiServer(BaseServer):
    def __init__(self, port: int = 8080, dev: bool = False) -> None:
        super().__init__(port=port, dev=dev)
        self._window: Any = None
        self._tray: Any = None
        self._tray_started = False
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
            "Terminal Server RPA",
            html=_LOADING_HTML,
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
        threading.Thread(target=self._check_and_prompt_update, daemon=True).start()
        webview.start(icon=str(ASSETS_DIR / "icon.ico"))

    def _wait_and_navigate(self, url: str, port: int) -> None:
        import httpx

        for _ in range(30):
            try:
                httpx.get(f"http://127.0.0.1:{port}/_health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        self._window.load_url(url)

    def _check_and_prompt_update(self) -> None:
        """Scheduling: poll for updates, delegating decision/UI/apply to helpers."""
        from src.config.version import VERSION
        from src.infrastructure.updater import check_for_update

        time.sleep(_UPDATE_INITIAL_DELAY_S)
        rejected: set[str] = set()

        while True:
            release = check_for_update(VERSION)
            if release and release.version not in rejected:
                if self._prompt_update(release.version):
                    self._apply_update(release)
                    return
                rejected.add(release.version)
            time.sleep(_UPDATE_POLL_INTERVAL_S)

    def _prompt_update(self, version: str) -> bool:
        """Presentation: ask the user whether to update now."""
        return self._window.create_confirmation_dialog(
            "Atualização disponível",
            f"Nova versão {version} disponível. Atualizar agora?",
        )

    def _apply_update(self, release: Any) -> None:
        """Action: download, verify and install the release."""
        from src.infrastructure.updater import apply_update

        apply_update(release)

    def _on_closing(self) -> bool:
        if self._tray_started:
            return False
        self._tray_started = True
        self._window.hide()
        threading.Thread(target=self._start_tray, daemon=True).start()
        return False

    def _start_tray(self) -> None:
        image = Image.open(str(ASSETS_DIR / "icon.png"))
        menu = pystray.Menu(
            pystray.MenuItem("Abrir", self._show_window, default=True),
            pystray.MenuItem("Sair", self._quit),
        )
        self._tray = pystray.Icon("TerminalServerRPA", image, "Terminal Server RPA", menu)
        self._tray.run()

    def _show_window(self, icon: Any, _item: Any) -> None:
        icon.stop()
        self._window.show()

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

    def _quit(self, icon: Any, _item: Any) -> None:
        icon.stop()
        self._window.destroy()
        os._exit(0)


def run_server(port: int = 8080, dev: bool = False) -> None:
    GuiServer(port=port, dev=dev).start()
