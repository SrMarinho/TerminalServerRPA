"""System-tray icon owning the app lifetime: restore the window or quit.

Extracted from GuiServer (SRP). The tray runs for the whole app lifetime;
closing the window only hides it — quitting happens from the "Sair" item.
"""

import os
from typing import Any

import pystray
from PIL import Image

from src.config.settings import ASSETS_DIR


class TrayIcon:
    def __init__(self, window: Any) -> None:
        self._window = window
        self._started = False

    def run(self) -> None:
        if self._started:
            return
        self._started = True
        image = Image.open(str(ASSETS_DIR / "icon.png"))
        menu = pystray.Menu(
            pystray.MenuItem("Abrir", self._show_window, default=True),
            pystray.MenuItem("Sair", self._quit),
        )
        pystray.Icon("TerminalServerRPA", image, "Terminal Server RPA", menu).run()

    def _show_window(self, _icon: Any, _item: Any) -> None:
        # Keep the tray alive; only restore the window.
        self._window.show()

    def _quit(self, icon: Any, _item: Any) -> None:
        icon.stop()
        self._window.destroy()
        os._exit(0)
