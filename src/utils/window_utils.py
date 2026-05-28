import asyncio
import re
from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page

from src.config.settings import ASSETS_DIR
from src.utils.image_match import find_template

_ASSETS = ASSETS_DIR / "Senior" / "components"
_DIAG_DIR = Path("logs/diag")


_DEFAULT_TITLE_IMG = _ASSETS / "tittle_bar" / "tittle.png"


async def maximize_window(
    page: Page,
    log: Callable[[str], None] | None = None,
    title_img: Path | None = None,
) -> None:
    _log = log or (lambda _: None)
    cx, cy = await _find_title(page, _log, title_img=title_img or _DEFAULT_TITLE_IMG)
    _log(f"title found at ({cx}, {cy}), right-clicking")
    await page.mouse.click(cx, cy, button="right")
    await asyncio.sleep(0.8)
    await _click_maximize(page, _log)


async def _find_title(
    page: Page, log: Callable[[str], None], title_img: Path, timeout_s: float = 300
) -> tuple[int, int]:
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        screenshot = await page.screenshot()
        match = find_template(screenshot, title_img, 0.8)
        if match:
            log(f"title image matched: confidence={match[1]:.2f}")
            return match[0]
        log("title image: no match, retrying")
        if asyncio.get_event_loop().time() >= deadline:
            raise RuntimeError(f"Title image not found after {timeout_s}s")
        await asyncio.sleep(5)


async def _click_maximize(page: Page, log: Callable[[str], None]) -> None:
    _DIAG_DIR.mkdir(parents=True, exist_ok=True)
    screenshot = await page.screenshot()
    await page.screenshot(path=str(_DIAG_DIR / "context_menu.png"))

    img_path = _ASSETS / "context_menu" / "maximizar.png"
    if img_path.exists():
        match = find_template(screenshot, img_path, 0.8)
        if match:
            log(f"maximizar image matched: confidence={match[1]:.2f}")
            cx, cy = match[0]
            await page.mouse.click(cx, cy)
            return
        log("maximizar image: no match, trying text fallback")

    loc = page.locator("*").filter(has_text=re.compile("Maximizar", re.IGNORECASE))
    count = await loc.count()
    log(f"maximizar text fallback: {count} elements found")
    if count > 0:
        await loc.last.click()
        return

    raise RuntimeError("Maximizar option not found (image + text both failed)")
