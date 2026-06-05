import asyncio
from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page

from src.config.settings import ASSETS_DIR
from src.utils.image_match import MatchThreshold, find_template
from src.utils.window_utils import maximize_window

from .reports.base_report import BaseReport
from .valores_entrada_modelo_page import ValoresEntradaModeloPage

_PLUGIN_ASSETS = Path(__file__).parent.parent / "assets"
_TITLE_IMG = _PLUGIN_ASSETS / "selecao_modelos_para_execucao" / "window_title.png"
_COL_NUMERO_IMG = _PLUGIN_ASSETS / "selecao_modelos_para_execucao" / "coluna_numero.png"
_MAXIMIZAR_IMG = ASSETS_DIR / "Senior" / "components" / "context_menu" / "maximizar.png"
_FORM_TITLE_IMG = _PLUGIN_ASSETS / "selecao_modelos_para_execucao" / "valores_entrada_modelo" / "index.png"


class SelecaoModelosParaExecucaoPage:
    def __init__(self, page: Page, log: Callable[[str], None] | None = None):
        self._page = page
        self._log = log or (lambda _: None)

    async def close(self) -> None:
        """Close valores_entrada_modelo (Escape) then selecao (Escape)."""
        await self._page.keyboard.press("Escape")
        await asyncio.sleep(0.3)
        await self._page.keyboard.press("Escape")
        self._log("selecao_modelos_para_execucao: closed")

    async def maximize(self) -> None:
        await maximize_window(self._page, self._log, title_img=_TITLE_IMG, maximizar_img=_MAXIMIZAR_IMG)

    async def open_report(self, report: BaseReport, timeout_s: float = 30) -> ValoresEntradaModeloPage:
        screenshot = await self._page.screenshot()
        match = find_template(screenshot, _COL_NUMERO_IMG, MatchThreshold.DEFAULT)
        if match:
            cx, cy = match[0]
            self._log(f"coluna_numero matched at ({cx},{cy}), clicking")
            await self._page.mouse.click(cx, cy)
            await asyncio.sleep(2)
        await self._page.keyboard.type(report.code, delay=100)
        await self._page.keyboard.press("Enter")
        self._log(f"report {report.code} typed + Enter")
        # wait for valores_entrada_modelo window to appear
        deadline = asyncio.get_event_loop().time() + timeout_s
        while True:
            shot = await self._page.screenshot()
            if find_template(shot, _FORM_TITLE_IMG, MatchThreshold.DEFAULT):
                self._log("valores_entrada_modelo window detected")
                break
            if asyncio.get_event_loop().time() >= deadline:
                self._log("timeout waiting for valores_entrada_modelo — proceeding anyway")
                break
            await asyncio.sleep(1)
        return ValoresEntradaModeloPage(self._page, log=self._log)
