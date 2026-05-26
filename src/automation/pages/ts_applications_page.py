import asyncio
from pathlib import Path

import pyautogui
from playwright.async_api import Page


class TsApplicationsPage:
    _ASSETS = Path(__file__).parents[3] / "assets" / "Senior" / "pages" / "ts_applications"

    def __init__(self, page: Page):
        self._page = page

    async def click_application(self, app_name: str) -> None:
        if await self._try_text(app_name):
            return
        if await self._try_image(app_name):
            return
        raise RuntimeError(f"Application '{app_name}' not found by text or image")

    async def _try_text(self, app_name: str) -> bool:
        try:
            loc = self._page.get_by_text(app_name, exact=False)
            if await loc.count() > 0:
                await loc.first.click()
                await asyncio.sleep(0.5)
                return True
        except Exception:
            pass
        return False

    async def _try_image(self, app_name: str) -> bool:
        img = self._ASSETS / app_name / "index.png"
        if not img.exists():
            return False
        center = pyautogui.locateCenterOnScreen(str(img), confidence=0.8)
        if center is None:
            return False
        pyautogui.click(center)
        await asyncio.sleep(0.5)
        return True
