import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import Page

from tsrpa import ASSETS_DIR, MatchThreshold, find_template

from .base_report import BaseReport
from .constants import AnaliticoSintetico, CsvRemoverEspacos, FormatoArquivo, OpcaoRelatorio

_PLUGIN_ASSETS = Path(__file__).parent.parent.parent / "assets"
_ERROR_IMG = ASSETS_DIR / "Senior" / "components" / "alert" / "error.png"
_VALS_DIR = _PLUGIN_ASSETS / "selecao_modelos_para_execucao" / "valores_entrada_modelo"


class R703RotConciliacao(BaseReport):
    @property
    def code(self) -> str:
        return "703"

    @property
    def description(self) -> str:
        return "Rot.Conciliação - Tít.não baixados - Proc. Baixa"

    def get_fields(self) -> list[dict]:
        return [
            {"name": "empresa", "label": "Empresa", "type": "string", "default": "5"},
            {"name": "filial", "label": "Filial", "type": "string", "default": "1"},
            {"name": "cliente", "label": "Cliente (Adquirente)", "type": "string"},
            {"name": "titulo", "label": "Título", "type": "string"},
            {"name": "data_emissao", "label": "Data Emissão", "type": "string"},
            {"name": "data_movimento", "label": "Data Movimento", "type": "string"},
            {
                "name": "opcao",
                "label": "Opção",
                "type": "select",
                "default": OpcaoRelatorio.VALIDAR,
                "options": [
                    {"value": OpcaoRelatorio.VALIDAR, "label": "V — Validar"},
                    {"value": OpcaoRelatorio.BAIXAR, "label": "B — Baixar Títulos"},
                ],
            },
            {
                "name": "analitico_sintetico",
                "label": "Analítico/Sintético",
                "type": "select",
                "default": AnaliticoSintetico.ANALITICO,
                "options": list(AnaliticoSintetico),
            },
            {
                "name": "formato_arquivo",
                "label": "Formato de Arquivo",
                "type": "select",
                "default": FormatoArquivo.PADRAO,
                "options": list(FormatoArquivo),
            },
            {
                "name": "csv_separador",
                "label": "Separador",
                "type": "string",
                "default": ",",
                "when": {"formato_arquivo": FormatoArquivo.CSV},
            },
            {
                "name": "csv_delimitador",
                "label": "Delimitador de Texto",
                "type": "string",
                "default": '"',
                "when": {"formato_arquivo": FormatoArquivo.CSV},
            },
            {
                "name": "csv_remover_espacos",
                "label": "Remover espaços antes e depois de cada valor",
                "type": "select",
                "default": CsvRemoverEspacos.NAO,
                "options": [
                    {"value": CsvRemoverEspacos.NAO, "label": "Não"},
                    {"value": CsvRemoverEspacos.SIM, "label": "Sim"},
                ],
                "when": {"formato_arquivo": FormatoArquivo.CSV},
            },
        ]

    async def fill(
        self,
        page: Page,
        params: dict,
        log: Callable[[str], None] | None = None,
        cancelar: Callable[[], Awaitable[bool]] | None = None,
    ) -> None:
        _log = log or (lambda _: None)

        async def check_error(label_name: str) -> None:
            await asyncio.sleep(0.4)
            shot = await page.screenshot()
            if find_template(shot, _ERROR_IMG, MatchThreshold.DEFAULT):
                clicked = await cancelar() if cancelar else False
                if not clicked:
                    await page.keyboard.press("Escape")
                raise ValueError(f"Senior error after filling '{label_name}' — registro não existe")

        async def tab_fill(value: str, label: str, prev_label: str = "") -> None:
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.3)
            if prev_label:
                await check_error(prev_label)
            if value:
                await page.keyboard.type(value, delay=50)
                _log(f"filled '{label}' → {value!r}")
            await asyncio.sleep(0.2)

        shot = await page.screenshot()
        m = find_template(shot, _VALS_DIR / "tab_entrada.png", MatchThreshold.DEFAULT)
        if not m:
            raise RuntimeError("tab_entrada not found — form not ready")
        await page.mouse.click(*m[0])
        await asyncio.sleep(0.3)

        fields: list[tuple[str, str, str]] = [
            ("empresa", "Empresa", ""),
            ("filial", "Filial", "1"),
            ("cliente", "Cliente", ""),
            ("titulo", "Título", ""),
            ("data_emissao", "Data Emissão", ""),
            ("data_movimento", "Data Movimento", ""),
            ("opcao", "Opção", OpcaoRelatorio.VALIDAR),
            ("analitico_sintetico", "Analítico/Sintético", AnaliticoSintetico.ANALITICO),
        ]

        prev_label = ""
        for param_key, label, default in fields:
            value = params.get(param_key, default) or ""
            await tab_fill(value, label, prev_label)
            prev_label = label

        await page.keyboard.press("Tab")
        await check_error(prev_label)
