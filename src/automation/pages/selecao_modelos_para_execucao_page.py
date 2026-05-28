from collections.abc import Callable

from playwright.async_api import Page

from src.config.settings import ASSETS_DIR
from src.utils.window_utils import maximize_window

_TITLE_IMG = ASSETS_DIR / "Senior" / "pages" / "selecao_modelos_para_execucao" / "window_title.png"


class SelecaoModelosParaExecucaoPage:
    def __init__(self, page: Page, log: Callable[[str], None] | None = None):
        self._page = page
        self._log = log or (lambda _: None)

    async def maximize(self) -> None:
        await maximize_window(self._page, self._log, title_img=_TITLE_IMG)
