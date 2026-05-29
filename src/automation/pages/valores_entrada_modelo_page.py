import asyncio
from collections.abc import Callable

from playwright.async_api import Page

from src.automation.pages.contas_receber.reports.base_report import BaseReport
from src.config.settings import ASSETS_DIR
from src.utils.image_match import find_template

_TITLE_IMG = ASSETS_DIR / "Senior" / "pages" / "selecao_modelos_para_execucao" / "valores_entrada_modelo" / "index.png"
_MAXIMIZAR_IMG = ASSETS_DIR / "Senior" / "components" / "context_menu" / "maximizar.png"


class ValoresEntradaModeloPage:
    def __init__(self, page: Page, log: Callable[[str], None] | None = None):
        self._page = page
        self._log = log or (lambda _: None)

    async def maximize(self, timeout_s: float = 10) -> None:
        deadline = asyncio.get_event_loop().time() + timeout_s
        t_match = None
        while not t_match:
            screenshot = await self._page.screenshot()
            t_match = find_template(screenshot, _TITLE_IMG, 0.8)
            if not t_match:
                if asyncio.get_event_loop().time() >= deadline:
                    self._log("valores_entrada_modelo: timeout waiting for window")
                    return
                await asyncio.sleep(1)
        cx, cy = t_match[0]
        self._log(f"title at ({cx},{cy}), right-clicking")
        await self._page.mouse.click(cx, cy, button="right")
        await asyncio.sleep(0.8)
        screenshot = await self._page.screenshot()
        m_match = find_template(screenshot, _MAXIMIZAR_IMG, 0.8)
        if m_match:
            await self._page.mouse.click(m_match[0][0], m_match[0][1])
            self._log("maximized")
        else:
            self._log("maximizar not found — assuming already maximized, closing menu")
            await self._page.keyboard.press("Escape")

    async def fill(self, report: BaseReport, params: dict) -> None:
        await report.fill(self._page, params, self._log)
