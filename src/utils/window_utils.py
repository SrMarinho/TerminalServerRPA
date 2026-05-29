import asyncio
import re
from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page

from src.utils.image_match import find_template

_DIAG_DIR = Path("logs/diag")


async def maximize_window(
    page: Page,
    log: Callable[[str], None] | None = None,
    title_img: Path | None = None,
    maximizar_img: Path | None = None,
    timeout_s: float = 30,
) -> None:
    _log = log or (lambda _: None)
    if title_img is None:
        raise ValueError("title_img required")
    result = await _find_title(page, _log, title_img, timeout_s)
    if result is None:
        _log("title not found — assuming already maximized")
        return
    cx, cy = result
    _log(f"title found at ({cx}, {cy}), right-clicking")
    await page.mouse.click(cx, cy, button="right")
    await asyncio.sleep(0.8)
    await _click_maximize(page, _log, maximizar_img)


async def _find_title(
    page: Page, log: Callable[[str], None], title_img: Path, timeout_s: float = 30
) -> tuple[int, int] | None:
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        screenshot = await page.screenshot()
        match = find_template(screenshot, title_img, 0.8)
        if match:
            log(f"title image matched: confidence={match[1]:.2f}")
            return match[0]
        log("title image: no match, retrying")
        if asyncio.get_event_loop().time() >= deadline:
            return None
        await asyncio.sleep(3)


async def _click_maximize(page: Page, log: Callable[[str], None], maximizar_img: Path | None = None) -> None:
    _DIAG_DIR.mkdir(parents=True, exist_ok=True)
    screenshot = await page.screenshot()
    await page.screenshot(path=str(_DIAG_DIR / "context_menu.png"))

    if maximizar_img and maximizar_img.exists():
        match = find_template(screenshot, maximizar_img, 0.8)
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

    log("maximizar not found — assuming already maximized, closing menu")
    await page.keyboard.press("Escape")
