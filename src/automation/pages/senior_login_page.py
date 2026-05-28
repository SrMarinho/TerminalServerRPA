import asyncio
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from playwright.async_api import Page

from src.config.settings import ASSETS_DIR
from src.utils.image_match import find_template, find_text

_DIAG_DIR = Path("logs/diag")


class SeniorLoginPage:
    _ASSETS = ASSETS_DIR / "Senior" / "pages" / "login_page"

    def __init__(
        self,
        page: Page,
        log: Callable[[str], None] | None = None,
        checkpoint: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ):
        self._page = page
        self._log = log or (lambda _: None)
        self._checkpoint = checkpoint

    async def login(self, username: str, password: str) -> None:
        await self.wait_for_login_screen()
        await self.fill_and_submit(username, password)

    async def wait_for_iniciando(self, timeout_s: float = 180) -> None:
        """Waits for 'Iniciando' text to appear in screenshot then disappear (OCR)."""
        deadline = asyncio.get_event_loop().time() + timeout_s
        appeared = False
        while True:
            screenshot = await self._page.screenshot()
            found, ocr_text = find_text(screenshot, "iniciando", return_text=True)  # type: ignore[misc]
            now = asyncio.get_event_loop().time()
            _DIAG_DIR.mkdir(parents=True, exist_ok=True)
            (_DIAG_DIR / "ocr_last.txt").write_text(ocr_text, encoding="utf-8")
            self._log(f"OCR: {'found' if found else 'not found'} — diag: logs/diag/ocr_last.txt")
            if found:
                if not appeared:
                    self._log("iniciando splash detected via OCR")
                appeared = True
            else:
                if appeared:
                    self._log("iniciando splash gone, proceeding to login screen")
                    return
                if now >= deadline:
                    self._log("iniciando splash never appeared, proceeding anyway")
                    return
            if now >= deadline:
                self._log("iniciando timeout, proceeding anyway")
                return
            if self._checkpoint:
                await self._checkpoint()
            await asyncio.sleep(2)

    async def wait_for_login_screen(self, timeout_s: float = 300) -> None:
        """Blocks until the Senior login screen appears (input_username.png found)."""
        await self._click_template("input_username.png", timeout_s=timeout_s, x_offset=120)
        self._focused_username = True

    async def fill_and_submit(self, username: str, password: str) -> None:
        if not getattr(self, "_focused_username", False):
            await self._click_template("input_username.png", x_offset=120)
        self._focused_username = False
        await self._page.keyboard.type(username, delay=50)
        await self._click_template("input_password.png", x_offset=120)
        await self._page.keyboard.type(password, delay=50)
        await self._click_template("btn_login.png")
        await asyncio.sleep(5)

    async def _click_template(
        self,
        template_name: str,
        confidence: float = 0.8,
        timeout_s: float = 10,
        x_offset: int = 0,
        y_offset: int = 0,
    ) -> None:
        img_path = self._ASSETS / template_name
        deadline = asyncio.get_event_loop().time() + timeout_s
        interval = 5.0
        while True:
            screenshot = await self._page.screenshot()
            _DIAG_DIR.mkdir(parents=True, exist_ok=True)
            await self._page.screenshot(path=str(_DIAG_DIR / f"senior_{template_name}"))
            match = find_template(screenshot, img_path, confidence)
            if match:
                self._log(f"senior template '{template_name}': confidence={match[1]:.2f}")
                break
            self._log(f"senior template '{template_name}': no match")
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise RuntimeError(f"Template '{template_name}' not matched after {timeout_s}s")
            if self._checkpoint:
                await self._checkpoint()
            await asyncio.sleep(min(interval, remaining))

        cx, cy = match[0]
        await self._page.mouse.click(cx + x_offset, cy + y_offset)
        await asyncio.sleep(0.5)
