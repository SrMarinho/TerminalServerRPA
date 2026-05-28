import asyncio
import re
from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page

from src.config.settings import ASSETS_DIR
from src.utils.image_match import find_template

_DIAG_DIR = Path("logs/diag")


class TsApplicationsPage:
    ASSETS_PATH = ASSETS_DIR

    def __init__(self, page: Page, log: Callable[[str], None] | None = None):
        self._page = page
        self._log = log or (lambda _: None)

    async def _dump(self, label: str) -> None:
        _DIAG_DIR.mkdir(parents=True, exist_ok=True)
        await self._page.screenshot(path=str(_DIAG_DIR / f"{label}.png"))
        html = await self._page.content()
        (_DIAG_DIR / f"{label}.html").write_text(html, encoding="utf-8")
        self._log(f"diag saved: logs/diag/{label}.*")

    async def click_application(self, app_name: str, asset_folder: str | None = None) -> None:
        folder = asset_folder or app_name
        if await self._try_image(folder):
            return
        raise RuntimeError(f"Application '{app_name}' not found: {folder}/index.png")

    async def _try_text(self, app_name: str) -> bool:
        try:
            await self._dump("before_text_match")
            pattern = re.compile(r"\s+".join(re.escape(w) for w in app_name.split()), re.IGNORECASE)
            loc = self._page.locator("*").filter(has_text=pattern)
            count = await loc.count()
            self._log(f"text match '{app_name}': {count} elements found")
            if count > 0:
                await loc.last.click()
                await asyncio.sleep(0.5)
                return True
        except Exception as e:
            self._log(f"text match error: {e}")
        return False

    async def _try_image(self, folder: str, confidence: float = 0.8, timeout_s: float = 300) -> bool:
        img_path = self.ASSETS_PATH / folder / "index.png"
        if not img_path.exists():
            self._log(f"image not found: {img_path}")
            return False

        deadline = asyncio.get_event_loop().time() + timeout_s
        interval = 5.0
        while True:
            await self._dump(f"image_match_{folder}")
            screenshot = await self._page.screenshot()
            match = find_template(screenshot, img_path, confidence)
            if match:
                self._log(f"image match '{folder}': confidence={match[1]:.2f}")
                cx, cy = match[0]
                await self._page.mouse.click(cx, cy)
                await asyncio.sleep(0.5)
                return True
            self._log(f"image match '{folder}': no match")
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                return False
            await asyncio.sleep(min(interval, remaining))
