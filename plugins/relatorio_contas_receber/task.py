import asyncio
from datetime import datetime
from pathlib import Path

from tsrpa import (
    ASSETS_DIR,
    DOWNLOADS_BASE,
    BrowserManager,
    HomePage,
    MatchThreshold,
    SeniorLoginPage,
    SidebarNavigator,
    SkipStep,
    TsApplicationsPage,
    TsLoginPage,
    Vault,
    find_template,
    maximize_window,
    register,
)

from .pages.reports import REPORTS, REPORTS_BY_CODE
from .pages.reports.constants import CsvRemoverEspacos, FormatoArquivo
from .pages.selecao_modelos_para_execucao_page import SelecaoModelosParaExecucaoPage
from .pages.valores_entrada_modelo_page import ValoresEntradaModeloPage
from .steps import StepNames

_PLUGIN_ASSETS = Path(__file__).parent / "assets"
_HOME_IMG = ASSETS_DIR / "Senior" / "components" / "sidebar" / "home" / "index.png"
_REPORT_TITLE_IMG = _PLUGIN_ASSETS / "selecao_modelos_para_execucao" / "window_title.png"
_OUTPUT_LOADING_DIR = _PLUGIN_ASSETS / "selecao_modelos_para_execucao" / "valores_entrada_modelo" / "output_loading"
_IMG_SELECIONANDO = _OUTPUT_LOADING_DIR / "selecionando_informacoes.png"
_IMG_AGUARDANDO = _OUTPUT_LOADING_DIR / "aguarde_preparando_solicitacao.png"

_SIDEBAR_ITEMS = [
    (StepNames.GESTAO_EMPRESARIAL, "gestao_empresarial/index.png"),
    (StepNames.FINANCAS, "gestao_empresarial/financas/index.png"),
    (StepNames.GESTAO_CONTAS_RECEBER, "gestao_empresarial/financas/gestao_contas_receber/index.png"),
    (StepNames.CONTAS_RECEBER, "gestao_empresarial/financas/gestao_contas_receber/contas_receber/index.png"),
    (
        StepNames.RELATORIOS,
        "gestao_empresarial/financas/gestao_contas_receber/contas_receber/relatorios/index.png",
    ),
]


async def _wait_for_home(page, runner=None, timeout_s: float = 120) -> None:
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        screenshot = await page.screenshot()
        if find_template(screenshot, _HOME_IMG, MatchThreshold.DEFAULT):
            return
        if asyncio.get_event_loop().time() >= deadline:
            return
        if runner:
            await runner.checkpoint()
        await asyncio.sleep(3)


@register("Relatório Contas Receber")
class GeracaoRelatorio:
    def __init__(self, runner=None, vault=None):
        self._runner = runner
        self._vault = vault or Vault()

    @staticmethod
    def get_schema():
        return [
            {"name": "base_url", "label": "URL Base", "type": "string", "default": "https://sistema.nazaria.com.br/"},
            {"name": "TS Credenciais", "label": "TS Credenciais", "type": "credential"},
            {"name": "Senior Credenciais", "label": "Senior Credenciais", "type": "credential"},
            {
                "name": "relatorio",
                "label": "Relatório",
                "type": "select",
                "options": [{"value": r.code, "label": r.label} for r in REPORTS],
            },
            *[
                {**field, "when": {**field.get("when", {}), "relatorio": r.code}}
                for r in REPORTS
                for field in r.get_fields()
            ],
        ]

    @staticmethod
    def get_steps():
        return {
            "Login": [StepNames.LOGIN_TS, StepNames.INICIANDO_SENIOR, StepNames.LOGIN_SENIOR],
            "Processamento": [
                StepNames.MAXIMIZANDO,
                StepNames.CARREGANDO_SENIOR,
                StepNames.GESTAO_EMPRESARIAL,
                StepNames.FINANCAS,
                StepNames.GESTAO_CONTAS_RECEBER,
                StepNames.CONTAS_RECEBER,
                StepNames.RELATORIOS,
                StepNames.MAXIMIZANDO_RELATORIO,
                StepNames.DIGITANDO_RELATORIO,
                StepNames.MAXIMIZANDO_VALORES,
                StepNames.PREENCHENDO_ENTRADA,
                StepNames.PREENCHENDO_SAIDA,
                StepNames.SELECIONANDO_INFORMACOES,
                StepNames.AGUARDANDO_SOLICITACAO,
            ],
            "Finalização": [StepNames.CONCLUIDO],
        }

    def _resolve_creds(self, params: dict, key: str = "credentials") -> dict:
        raw = params.get(key, {})
        if isinstance(raw, dict) and "service" in raw:
            svc = raw["service"]
            users = self._vault.list_credentials(svc)
            if users:
                username = users[0]["username"]
                password = self._vault.get_password(svc, username)
                return {"username": username, "password": password or ""}
        return raw if isinstance(raw, dict) else {}

    async def _step(self, name: str, coro=None) -> None:
        try:
            if self._runner:
                await self._runner.report_step(name)
            if coro is not None:
                await coro
        except SkipStep:
            from src.infrastructure.logger import get_logger

            get_logger("TerminalServerRPA.report-generation").warning("step.skipped", step=name)

    async def _replay_steps(self, *names: str) -> None:
        for name in names:
            await self._step(name)

    def _attach_page(self, page) -> None:
        if self._runner:
            self._runner._page = page

    async def _wait_loading(self, page, img_path, step_name, appear_timeout: float = 5.0, next_img_path=None) -> None:
        await self._step(step_name)
        deadline_appear = asyncio.get_event_loop().time() + appear_timeout
        while asyncio.get_event_loop().time() < deadline_appear:
            shot = await page.screenshot()
            if find_template(shot, img_path, MatchThreshold.DEFAULT):
                break
            await asyncio.sleep(0.3)
        while True:
            shot = await page.screenshot()
            if not find_template(shot, img_path, MatchThreshold.DEFAULT):
                return
            if next_img_path and find_template(shot, next_img_path, MatchThreshold.DEFAULT):
                return
            await asyncio.sleep(0.5)

    async def _phase_login_ts(self, context, page, ts_creds: dict, base_url: str):
        remote_page = None
        try:
            await self._step(StepNames.LOGIN_TS)
            login_p = TsLoginPage(page, base_url)
            await login_p.navigate()
            async with context.expect_event("page", timeout=60000) as new_page_info:
                await login_p.login(ts_creds["username"], ts_creds["password"])
            remote_page = await new_page_info.value
            await remote_page.wait_for_load_state("load", timeout=60000)
        except SkipStep:
            return None

        screen_w, screen_h = BrowserManager.get_screen_size()
        await BrowserManager.maximize_cdp(context, remote_page, screen_w, screen_h)
        apps_page = TsApplicationsPage(remote_page, log=self._runner.log if self._runner else None)
        await apps_page.click_application("Gestão Empresarial", asset_folder="Senior")
        return remote_page

    async def _phase_senior_loading(self, remote_page, senior_creds: dict):
        if not remote_page:
            return None
        try:
            await self._step(StepNames.INICIANDO_SENIOR)
            senior_login = SeniorLoginPage(
                remote_page,
                log=self._runner.log if self._runner else None,
                checkpoint=self._runner.checkpoint if self._runner else None,
            )
            await senior_login.wait_for_iniciando()
            return senior_login
        except SkipStep:
            return None

    async def _phase_senior_login(self, remote_page, senior_login, senior_creds: dict) -> None:
        if not remote_page or not senior_login:
            await self._step(StepNames.LOGIN_SENIOR)
            return
        await self._step(StepNames.LOGIN_SENIOR, senior_login.wait_for_login_screen())
        try:
            await senior_login.fill_and_submit(senior_creds["username"], senior_creds["password"])
        except SkipStep:
            from src.infrastructure.logger import get_logger

            get_logger("TerminalServerRPA.report-generation").warning(
                "step.skipped.submit", step=StepNames.LOGIN_SENIOR
            )

    async def _phase_home_setup(self, remote_page):
        home = None
        if remote_page:
            try:
                await self._step(StepNames.MAXIMIZANDO)
                home = HomePage(remote_page, log=self._runner.log if self._runner else None)
                await home.maximize()
            except SkipStep:
                pass
            await self._step(StepNames.CARREGANDO_SENIOR, _wait_for_home(remote_page, self._runner))
        else:
            await self._step(StepNames.MAXIMIZANDO)
            await self._step(StepNames.CARREGANDO_SENIOR)
        return home

    async def _phase_navigate_sidebar(self, home) -> None:
        nav = SidebarNavigator()
        await nav.navigate(home, _SIDEBAR_ITEMS, self._step)

    async def _phase_report_actions(self, remote_page, relatorio_code: str, params: dict) -> str | None:
        if not remote_page:
            await self._replay_steps(
                StepNames.MAXIMIZANDO_RELATORIO,
                StepNames.DIGITANDO_RELATORIO,
                StepNames.MAXIMIZANDO_VALORES,
                StepNames.PREENCHENDO_ENTRADA,
                StepNames.PREENCHENDO_SAIDA,
                StepNames.SELECIONANDO_INFORMACOES,
                StepNames.AGUARDANDO_SOLICITACAO,
            )
            return

        await self._step(
            StepNames.MAXIMIZANDO_RELATORIO,
            maximize_window(
                remote_page,
                self._runner.log if self._runner else None,
                title_img=_REPORT_TITLE_IMG,
            ),
        )
        await asyncio.sleep(1)

        report = REPORTS_BY_CODE.get(relatorio_code)
        if report:
            await self._step(StepNames.DIGITANDO_RELATORIO)

            selecao = SelecaoModelosParaExecucaoPage(
                remote_page,
                log=self._runner.log if self._runner else None,
            )
            valores = None
            try:
                valores = await selecao.open_report(report)
            except SkipStep:
                from src.infrastructure.logger import get_logger

                get_logger("TerminalServerRPA.report-generation").warning(
                    "step.skipped.open_report", step=StepNames.DIGITANDO_RELATORIO
                )

            if valores is None:
                valores = ValoresEntradaModeloPage(
                    remote_page,
                    log=self._runner.log if self._runner else None,
                )
            await self._step(StepNames.MAXIMIZANDO_VALORES, valores.maximize())
            await self._step(StepNames.PREENCHENDO_ENTRADA, valores.fill(report, params))
            await self._step(StepNames.PREENCHENDO_SAIDA)
            await asyncio.sleep(0.5)
            await valores.click_saida_tab()
            await asyncio.sleep(0.5)
            await valores.select_arquivo_checkbox()
            await asyncio.sleep(0.3)
            await valores.select_formato_arquivo(params.get("formato_arquivo", FormatoArquivo.EXCEL))
            await asyncio.sleep(0.3)
            await valores.fill_saida_label_field("Caminho", r"\\tsclient\WebFile")
            await asyncio.sleep(0.2)
            nome_arquivo = f"rel_{relatorio_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            await valores.fill_saida_label_field("Nome", nome_arquivo)
            await asyncio.sleep(0.2)
            if params.get("formato_arquivo") == FormatoArquivo.CSV:
                await valores.fill_saida_label_field("Separador", params.get("csv_separador", ","))
                await asyncio.sleep(0.2)
                await valores.fill_saida_label_field("Delimitador", params.get("csv_delimitador", '"'))
                await asyncio.sleep(0.2)
                if params.get("csv_remover_espacos") == CsvRemoverEspacos.SIM:
                    await valores.click_ocr_label("Remover")
                    await asyncio.sleep(0.2)
            await asyncio.sleep(0.3)
            await valores.click_ok()
            await self._wait_loading(
                remote_page, _IMG_SELECIONANDO, StepNames.SELECIONANDO_INFORMACOES, next_img_path=_IMG_AGUARDANDO
            )
            await self._wait_loading(remote_page, _IMG_AGUARDANDO, StepNames.AGUARDANDO_SOLICITACAO)
            await selecao.close()
            return nome_arquivo
        else:
            await self._replay_steps(
                StepNames.DIGITANDO_RELATORIO,
                StepNames.MAXIMIZANDO_VALORES,
                StepNames.PREENCHENDO_ENTRADA,
                StepNames.PREENCHENDO_SAIDA,
            )
        return None

    async def execute(self, params: dict) -> dict:
        from playwright.async_api import async_playwright

        ts_creds = self._resolve_creds(params, "TS Credenciais")
        senior_creds = self._resolve_creds(params, "Senior Credenciais")
        base_url = params.get("base_url", "")
        relatorio_code = params.get("relatorio", "")

        async with async_playwright() as p:
            downloads_path = (
                DOWNLOADS_BASE / "financas" / "gestao_contas_receber" / "contas_receber" / "relatorios" / relatorio_code
            )
            browser, context, page, _w, _h = await BrowserManager.launch(p, downloads_path=downloads_path)
            try:
                self._attach_page(page)
                remote = await self._phase_login_ts(context, page, ts_creds, base_url)
                self._attach_page(remote)
                sl = await self._phase_senior_loading(remote, senior_creds)
                await self._phase_senior_login(remote, sl, senior_creds)
                home = await self._phase_home_setup(remote)
                await self._phase_navigate_sidebar(home)
                arquivo = await self._phase_report_actions(remote, relatorio_code, params)
                await self._step(StepNames.CONCLUIDO)
                return {"status": "ok", **({"arquivo": arquivo} if arquivo else {})}
            finally:
                if self._runner:
                    self._runner._page = None
                await context.close()
                await browser.close()
