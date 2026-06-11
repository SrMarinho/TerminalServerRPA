"""Update UX for the GUI: poll for releases, prompt in-webview, apply with progress.

Extracted from GuiServer (SRP): this class owns the whole update journey; the
server only schedules `UpdateFlow(window).run` on a daemon thread.
"""

import time
from typing import Any

from src.interfaces.gui.webview_assets import js_escape, load_asset

_INITIAL_DELAY_S = 5
_POLL_INTERVAL_S = 60


class UpdateFlow:
    def __init__(self, window: Any) -> None:
        self._window = window

    def run(self) -> None:
        """Poll for updates; on acceptance the process is replaced by the installer."""
        from src.config.version import VERSION
        from src.infrastructure.updater import check_for_update

        time.sleep(_INITIAL_DELAY_S)
        rejected: set[str] = set()

        while True:
            release = check_for_update(VERSION)
            if release and release.version not in rejected:
                if self._prompt(release.version):
                    self._apply(release)
                    return
                rejected.add(release.version)
            time.sleep(_POLL_INTERVAL_S)

    def _prompt(self, version: str) -> bool:
        """Inject a styled HTML modal into the webview and poll for user response.

        Native MessageBox appears behind the maximized window and freezes the GUI
        loop. window.confirm() is functional but visually inconsistent. An injected
        modal is always in-front, styled to match the app, and non-blocking for the
        webview main thread.
        """
        self._window.show()
        html = load_asset("update_modal.html").replace("__VERSION__", f"versão {version}")
        self._window.evaluate_js(load_asset("update_modal.js").replace("__HTML__", js_escape(html)))
        while True:
            choice = self._window.evaluate_js("window._upd_choice")
            if choice is not None:
                return choice == "yes"
            time.sleep(0.2)

    def _apply(self, release: Any) -> None:
        """Show the progress overlay, then download, verify and install the release."""
        from src.infrastructure.updater import apply_update

        overlay = load_asset("update_overlay.html")
        self._window.evaluate_js(load_asset("inject.js").replace("__HTML__", js_escape(overlay)))
        apply_update(release, progress_cb=self._on_progress)

    def _on_progress(self, downloaded: int, total: int) -> None:
        if total <= 0:
            return
        pct = int(downloaded * 100 / total)
        text = f"{pct}% — {downloaded / 1_048_576:.1f} / {total / 1_048_576:.1f} MB"
        js = load_asset("update_progress.js").replace("__PCT__", str(pct)).replace("__TEXT__", js_escape(text))
        self._window.evaluate_js(js)
