import asyncio
from collections.abc import Callable
from pathlib import Path

from playwright.async_api import Page

from src.config.settings import ASSETS_DIR
from src.utils.image_match import MatchThreshold, find_template, find_text_position

from .reports.base_report import BaseReport
from .reports.constants import FormatoArquivo

_PLUGIN_ASSETS = Path(__file__).parent.parent / "assets"
_TITLE_IMG = _PLUGIN_ASSETS / "selecao_modelos_para_execucao" / "valores_entrada_modelo" / "index.png"
_MAXIMIZAR_IMG = ASSETS_DIR / "Senior" / "components" / "context_menu" / "maximizar.png"
_SAIDA_DIR = _PLUGIN_ASSETS / "selecao_modelos_para_execucao" / "valores_entrada_modelo" / "form" / "saida"
_ARQUIVO_NOT_MARKED = _SAIDA_DIR / "arquivo_not_marked.png"
_ARQUIVO_MARKED = _SAIDA_DIR / "arquivo_marked.png"
_ARQUIVO_MARKED_FOCUSED = _SAIDA_DIR / "arquivo_marked_focused.png"
_BTN_OK = _SAIDA_DIR / "btn_ok.png"


class ValoresEntradaModeloPage:
    def __init__(self, page: Page, log: Callable[[str], None] | None = None):
        self._page = page
        self._log = log or (lambda _: None)

    async def maximize(self, timeout_s: float = 10) -> None:
        deadline = asyncio.get_event_loop().time() + timeout_s
        t_match = None
        while not t_match:
            screenshot = await self._page.screenshot()
            t_match = find_template(screenshot, _TITLE_IMG, MatchThreshold.DEFAULT)
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
        m_match = find_template(screenshot, _MAXIMIZAR_IMG, MatchThreshold.DEFAULT)
        if m_match:
            await self._page.mouse.click(m_match[0][0], m_match[0][1])
            self._log("maximized")
        else:
            self._log("maximizar not found — assuming already maximized, closing menu")
            await self._page.keyboard.press("Escape")

    async def _ocr_find(self, *keywords: str) -> tuple[int, int] | None:
        """Find a word matching any keyword via OCR. Returns screen coords or None."""
        shot = await self._page.screenshot()
        return find_text_position(shot, *keywords)

    async def click_saida_tab(self) -> bool:
        """Click the 'Saída' tab. Returns True if clicked."""
        pos = await self._ocr_find("Saída", "Sada", "Saida")
        if pos:
            await self._page.mouse.click(pos[0], pos[1])
            await asyncio.sleep(0.5)
            self._log(f"clicked Saída tab at {pos}")
            return True
        self._log("Saída tab not found via OCR")
        return False

    _FORMATO_INDEX: dict[FormatoArquivo, int] = {
        FormatoArquivo.PADRAO: 0,
        FormatoArquivo.BITMAP: 1,
        FormatoArquivo.JPEG: 2,
        FormatoArquivo.ARQUIVO_TEXTO_WINDOWS: 3,
        FormatoArquivo.EXPORTACAO_WINDOWS: 4,
        FormatoArquivo.ARQUIVO_TEXTO_DOS: 5,
        FormatoArquivo.EXPORTACAO_DOS: 6,
        FormatoArquivo.HTML: 7,
        FormatoArquivo.EXPORTACAO_SAGA: 8,
        FormatoArquivo.EXPORTACAO_EXCEL: 9,
        FormatoArquivo.EXCEL: 10,
        FormatoArquivo.EXCEL_OPENXML: 11,
        FormatoArquivo.WORD_OPENXML: 12,
        FormatoArquivo.PDF: 13,
        FormatoArquivo.CSV: 14,
        FormatoArquivo.PDF_A: 15,
    }

    async def select_formato_arquivo(self, value: FormatoArquivo = FormatoArquivo.EXCEL) -> bool:
        """Click the 'Formato de Arquivo' select and navigate to option by index."""
        idx = self._FORMATO_INDEX.get(value)
        if idx is None:
            self._log(f"Formato de Arquivo unknown option '{value}'")
            return False
        pos = await self._ocr_find("Formato", "Formato:")
        if not pos:
            self._log("Formato de Arquivo label not found")
            return False
        fx, fy = pos[0], pos[1] + 20
        await self._page.mouse.click(fx, fy)
        await asyncio.sleep(0.2)
        await self._page.keyboard.press("Backspace")
        await asyncio.sleep(0.1)
        await self._page.keyboard.press("ArrowDown")
        await asyncio.sleep(0.1)
        for _ in range(idx):
            await self._page.keyboard.press("ArrowDown")
            await asyncio.sleep(0.1)
        self._log(f"Formato de Arquivo set to '{value}' (idx={idx}) at ({fx},{fy})")
        return True

    async def fill_tab_field(self, value: str) -> None:
        """Tab to next field, clear it and type value."""
        await self._page.keyboard.press("Tab")
        await asyncio.sleep(0.2)
        await self._page.keyboard.press("Backspace")
        await asyncio.sleep(0.1)
        await self._page.keyboard.type(value, delay=50)
        self._log(f"fill_tab_field: '{value}'")

    async def click_ocr_label(self, keyword: str) -> bool:
        """Find a word via OCR and click directly on it (no offset)."""
        pos = await self._ocr_find(keyword)
        if not pos:
            self._log(f"label '{keyword}' not found for click")
            return False
        await self._page.mouse.click(pos[0], pos[1])
        await asyncio.sleep(0.2)
        self._log(f"clicked '{keyword}' at {pos}")
        return True

    async def fill_saida_label_field(self, label_keyword: str, value: str, offset_y: int = 20) -> bool:
        """Find a label via OCR and fill the field offset_y pixels below it."""
        pos = await self._ocr_find(label_keyword)
        if not pos:
            self._log(f"label '{label_keyword}' not found")
            return False
        fx, fy = pos[0], pos[1] + offset_y
        await self._page.mouse.click(fx, fy)
        await asyncio.sleep(0.2)
        await self._page.keyboard.press("Control+a")
        await asyncio.sleep(0.1)
        await self._page.keyboard.press("Backspace")
        await asyncio.sleep(0.1)
        await self._page.keyboard.type(value, delay=50)
        self._log(f"'{label_keyword}' field set to '{value}' at ({fx},{fy})")
        return True

    async def select_arquivo_checkbox(self) -> bool:
        """Ensure the 'Arquivo' checkbox is checked. Returns True if already/now checked."""
        shot = await self._page.screenshot()
        if find_template(shot, _ARQUIVO_MARKED, MatchThreshold.CHECKBOX) or find_template(
            shot, _ARQUIVO_MARKED_FOCUSED, MatchThreshold.CHECKBOX
        ):
            self._log("Arquivo already checked")
            return True
        m = find_template(shot, _ARQUIVO_NOT_MARKED, MatchThreshold.CHECKBOX)
        if m:
            cx, cy = m[0]
            await self._page.mouse.click(cx, cy)
            await asyncio.sleep(0.3)
            self._log(f"Arquivo checked at ({cx},{cy})")
            return True
        self._log("Arquivo checkbox not found")
        return False

    async def click_ok(self) -> bool:
        """Click the OK button in the saída form. Returns True if found and clicked."""
        shot = await self._page.screenshot()
        m = find_template(shot, _BTN_OK, MatchThreshold.DEFAULT)
        if m:
            cx, cy = m[0]
            await self._page.mouse.click(cx, cy)
            self._log(f"clicked OK at ({cx},{cy})")
            return True
        self._log("OK button not found")
        return False

    async def close(self) -> None:
        await self._page.keyboard.press("Escape")
        self._log("valores_entrada_modelo: closed")

    async def click_cancelar(self) -> bool:
        """OCR the current screen to find and click 'Cancelar'. Returns True if clicked."""
        pos = await self._ocr_find("Cancelar", "Cancear")
        if pos:
            self._log(f"clicking Cancelar at {pos}")
            await self._page.mouse.click(pos[0], pos[1])
            await asyncio.sleep(0.3)
            return True
        return False

    async def fill(self, report: BaseReport, params: dict) -> None:
        await report.fill(self._page, params, self._log, cancelar=self.click_cancelar)
