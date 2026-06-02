import asyncio
from collections.abc import Callable

import cv2  # type: ignore[import-untyped]
import numpy as np  # type: ignore[import-untyped]
import pytesseract  # type: ignore[import-untyped]
from playwright.async_api import Page

from src.automation.pages.contas_receber.reports.base_report import BaseReport
from src.utils.image_match import _find_tesseract


class RotConciliacao703(BaseReport):
    @property
    def code(self) -> str:
        return "703"

    @property
    def description(self) -> str:
        return "Rot.Conciliação - Tít.não baixados - Proc. Baixa"

    def get_fields(self) -> list[dict]:
        return [
            {"name": "empresa", "label": "Empresa", "type": "string", "default": "5"},
            {"name": "filial", "label": "Filial", "type": "string"},
            {"name": "cliente", "label": "Cliente (Adquirente)", "type": "string"},
            {"name": "titulo", "label": "Título", "type": "string"},
            {"name": "data_emissao", "label": "Data Emissão", "type": "string"},
            {"name": "data_movimento", "label": "Data Movimento", "type": "string"},
            {
                "name": "opcao",
                "label": "Opção",
                "type": "select",
                "default": "V",
                "options": [
                    {"value": "V", "label": "V — Validar"},
                    {"value": "B", "label": "B — Baixar Títulos"},
                ],
            },
            {
                "name": "analitico_sintetico",
                "label": "Analítico/Sintético",
                "type": "select",
                "default": "A",
                "options": ["A", "S"],
            },
        ]

    async def fill(self, page: Page, params: dict, log: Callable[[str], None] | None = None) -> None:
        _log = log or (lambda _: None)
        pytesseract.pytesseract.tesseract_cmd = _find_tesseract()

        screenshot = await page.screenshot()
        img = cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_COLOR)
        ocr = pytesseract.image_to_data(img, lang="por", output_type=pytesseract.Output.DICT)

        def find_field_pos(*keywords: str) -> tuple[int, int] | None:
            """Find label by keywords via OCR. Returns (click_x, click_y) just to the right of the label,
            or None if not found."""
            best = None
            best_i = None
            for i, word in enumerate(ocr["text"]):
                word = word.strip()
                if not word:
                    continue
                for kw in keywords:
                    if kw.lower() in word.lower():
                        candidate = ocr["top"][i] + ocr["height"][i] // 2
                        if best is None or candidate < best:
                            best = candidate
                            best_i = i
                        break
            if best_i is None or best is None:
                return None
            left = ocr["left"][best_i]
            width = ocr["width"][best_i]
            click_x = left + width + 15
            return (click_x, best)

        async def fill_field(pos: tuple[int, int] | None, value: str, label_name: str = "") -> None:
            if not value:
                return
            if pos is None:
                _log(f"OCR did not find '{label_name}' — skipping (no fallback)")
                return
            target_x, target_y = pos
            await page.mouse.click(target_x, target_y)
            await asyncio.sleep(0.1)
            await page.mouse.click(target_x, target_y)
            await asyncio.sleep(0.2)
            await page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)
            await page.keyboard.type(value, delay=50)
            _log(f"filled ({target_x},{target_y}) → {value!r}")

        await fill_field(find_field_pos("Empresa"), params.get("empresa", ""), "Empresa")
        await fill_field(find_field_pos("Filial"), params.get("filial", ""), "Filial")
        await fill_field(find_field_pos("Adquirente", "Cliente"), params.get("cliente", ""), "Cliente")
        await fill_field(find_field_pos("Titulo", "Titulor"), params.get("titulo", ""), "Título")
        await fill_field(find_field_pos("Emiss"), params.get("data_emissao", ""), "Data Emissão")
        await fill_field(find_field_pos("Movimento"), params.get("data_movimento", ""), "Data Movimento")
        await fill_field(find_field_pos("Op"), params.get("opcao", "V"), "Opção")
        await fill_field(
            find_field_pos("Anali", "Sintet"), params.get("analitico_sintetico", "A"), "Analítico/Sintético"
        )
