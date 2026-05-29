import asyncio
from collections.abc import Callable

from playwright.async_api import Page

from src.automation.pages.contas_receber.reports.base_report import BaseReport
from src.config.settings import ASSETS_DIR
from src.utils.image_match import find_template
from src.utils.window_utils import maximize_window

_TITLE_IMG = ASSETS_DIR / "Senior" / "pages" / "selecao_modelos_para_execucao" / "window_title.png"
_COL_NUMERO_IMG = ASSETS_DIR / "Senior" / "pages" / "selecao_modelos_para_execucao" / "coluna_numero.png"
_MAXIMIZAR_IMG = ASSETS_DIR / "Senior" / "components" / "context_menu" / "maximizar.png"


class SelecaoModelosParaExecucaoPage:
    def __init__(self, page: Page, log: Callable[[str], None] | None = None):
        self._page = page
        self._log = log or (lambda _: None)

    async def maximize(self) -> None:
        await maximize_window(self._page, self._log, title_img=_TITLE_IMG, maximizar_img=_MAXIMIZAR_IMG)

    async def open_report(self, report: BaseReport) -> None:
        screenshot = await self._page.screenshot()
        match = find_template(screenshot, _COL_NUMERO_IMG, 0.8)
        if match:
            cx, cy = match[0]
            self._log(f"coluna_numero matched at ({cx},{cy}), clicking")
            await self._page.mouse.click(cx, cy)
            await asyncio.sleep(2)
        await self._page.keyboard.type(report.code, delay=100)
        await self._page.keyboard.press("Enter")
        self._log(f"report {report.code} typed + Enter")
