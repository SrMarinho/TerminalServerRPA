import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import Page

from src.automation.pages.contas_receber.reports.base_report import BaseReport, FieldDef
from src.automation.pages.contas_receber.reports.constants import (
    AnaliticoSintetico,
    CsvRemoverEspacos,
    FormatoArquivo,
    OpcaoRelatorio,
)
from src.config.settings import ASSETS_DIR
from src.utils.image_match import MatchThreshold, find_template, find_text_position

_ERROR_IMG = ASSETS_DIR / "Senior" / "components" / "alert" / "error.png"
_FORM_DIR = ASSETS_DIR / "Senior" / "pages" / "selecao_modelos_para_execucao" / "valores_entrada_modelo" / "form"
_FIELD_OFFSET_X = 200       # px right of label centre → wide input fields (1-6)
_FIELD_OFFSET_X_SMALL = 35  # narrow 1-char fields (7-8: Opção, Analítico/Sintético)


def _field_img(prefix: int) -> Path:
    matches = list(_FORM_DIR.glob(f"{prefix}_*.png"))
    return matches[0] if matches else Path()


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
                    {"value": OpcaoRelatorio.BAIXAR,  "label": "B — Baixar Títulos"},
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
                "default": FormatoArquivo.EXCEL,
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

        async def find_pos(img_path: Path, offset_x: int = _FIELD_OFFSET_X) -> tuple[int, int] | None:
            if not img_path.exists():
                return None
            shot = await page.screenshot()
            m = find_template(shot, img_path, MatchThreshold.FIELD)
            if not m:
                return None
            lx, ly = m[0]
            return (lx + offset_x, ly)

        async def find_pos_ocr(keyword: str, offset_x: int = _FIELD_OFFSET_X_SMALL) -> tuple[int, int] | None:
            shot = await page.screenshot()
            pos = find_text_position(shot, keyword)
            if pos is None:
                return None
            return (pos[0] + offset_x, pos[1])

        async def check_error(label_name: str) -> None:
            await asyncio.sleep(0.4)
            shot = await page.screenshot()
            if find_template(shot, _ERROR_IMG, MatchThreshold.DEFAULT):
                clicked = await cancelar() if cancelar else False
                if not clicked:
                    await page.keyboard.press("Escape")
                raise ValueError(f"Senior error after filling '{label_name}' — registro não existe")

        async def fill_field(
            pos: tuple[int, int] | None,
            value: str,
            label_name: str = "",
            prev_label: str = "",
        ) -> None:
            if not value:
                return
            if pos is None:
                _log(f"template not found for '{label_name}' — skipping")
                return
            target_x, target_y = pos
            # first click triggers focusout on previous field → validation fires
            await page.mouse.click(target_x, target_y)
            await asyncio.sleep(0.1)
            if prev_label:
                await check_error(prev_label)
            # second click to select + clear
            await page.mouse.click(target_x, target_y)
            await asyncio.sleep(0.2)
            await page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)
            await page.keyboard.type(value, delay=50)
            _log(f"filled '{label_name}' ({target_x},{target_y}) → {value!r}")

        field_defs: list[FieldDef] = [
            FieldDef(img_prefix=1,    ocr_keyword=None,    param_key="empresa",             default="",                          label="Empresa",             offset=_FIELD_OFFSET_X),
            FieldDef(img_prefix=2,    ocr_keyword=None,    param_key="filial",              default="1",                         label="Filial",              offset=_FIELD_OFFSET_X),
            FieldDef(img_prefix=3,    ocr_keyword=None,    param_key="cliente",             default="",                          label="Cliente",             offset=_FIELD_OFFSET_X),
            FieldDef(img_prefix=4,    ocr_keyword=None,    param_key="titulo",              default="",                          label="Título",              offset=_FIELD_OFFSET_X),
            FieldDef(img_prefix=5,    ocr_keyword=None,    param_key="data_emissao",        default="",                          label="Data Emissão",        offset=_FIELD_OFFSET_X),
            FieldDef(img_prefix=6,    ocr_keyword=None,    param_key="data_movimento",      default="",                          label="Data Movimento",      offset=_FIELD_OFFSET_X),
            FieldDef(img_prefix=None, ocr_keyword="Op",    param_key="opcao",               default=OpcaoRelatorio.VALIDAR,      label="Opção",               offset=_FIELD_OFFSET_X_SMALL),
            FieldDef(img_prefix=None, ocr_keyword="Anali", param_key="analitico_sintetico", default=AnaliticoSintetico.ANALITICO, label="Analítico/Sintético", offset=_FIELD_OFFSET_X_SMALL),
        ]

        prev_label = ""
        for fd in field_defs:
            if fd.img_prefix is not None:
                pos = await find_pos(_field_img(fd.img_prefix), fd.offset)
            else:
                pos = await find_pos_ocr(fd.ocr_keyword, fd.offset)  # type: ignore[arg-type]
            await fill_field(pos, params.get(fd.param_key, fd.default), fd.label, prev_label=prev_label)
            prev_label = fd.label

        # trigger focusout on last field + check its validation
        await page.keyboard.press("Tab")
        await check_error(prev_label)
