import asyncio
from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page

from src.config.settings import ASSETS_DIR
from src.utils.image_match import find_template
from src.utils.window_utils import maximize_window

_DIAG_DIR = Path("logs/diag")


class HomePage:
    _ASSETS = ASSETS_DIR / "Senior" / "components"

    def __init__(self, page: Page, log: Callable[[str], None] | None = None):
        self._page = page
        self._log = log or (lambda _: None)

    async def maximize(self) -> None:
        await maximize_window(self._page, self._log)

    async def click_sidebar_item(self, img_name: str, timeout_s: float = 60) -> None:
        img_path = self._ASSETS / "sidebar" / img_name
        deadline = asyncio.get_event_loop().time() + timeout_s
        while True:
            screenshot = await self._page.screenshot()
            _DIAG_DIR.mkdir(parents=True, exist_ok=True)
            match = find_template(screenshot, img_path, 0.8)
            if match:
                cx, cy = match[0]
                self._log(f"sidebar '{img_name}' matched at ({cx},{cy}), confidence={match[1]:.2f}")
                await self._page.mouse.click(cx, cy)
                return
            self._log(f"sidebar '{img_name}': no match")
            if asyncio.get_event_loop().time() >= deadline:
                raise RuntimeError(f"Sidebar item '{img_name}' not found after {timeout_s}s")
            await asyncio.sleep(3)
