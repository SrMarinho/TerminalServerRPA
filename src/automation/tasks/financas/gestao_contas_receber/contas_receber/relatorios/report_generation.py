"""Report generation task: log into Terminal Server + Senior ERP, navigate to
Contas Receber reports, fill parameters, and execute.

Phases
------
1. login_ts        — TS login → remote page (new browser tab)
2. senior_loading  — wait for Senior ERP to load
3. senior_login    — log into Senior ERP
4. navigate        — maximize HomePage, wait assets, sidebar clicks
5. report_actions  — open report, fill fields, execute
"""

import asyncio
from datetime import datetime

from src.automation.browser.browser_manager import BrowserManager
from src.config.settings import DOWNLOADS_BASE
from src.automation.pages.contas_receber.reports import REPORTS, REPORTS_BY_CODE
from src.automation.pages.contas_receber.reports.constants import CsvRemoverEspacos, FormatoArquivo
from src.automation.pages.contas_receber.selecao_modelos_para_execucao_page import SelecaoModelosParaExecucaoPage
from src.automation.pages.contas_receber.valores_entrada_modelo_page import ValoresEntradaModeloPage
from src.automation.pages.home_page import HomePage
from src.automation.pages.senior_login_page import SeniorLoginPage
from src.automation.pages.sidebar_navigator import SidebarNavigator
from src.automation.pages.ts_applications_page import TsApplicationsPage
from src.automation.pages.ts_login_page import TsLoginPage
from src.automation.tasks.financas.gestao_contas_receber.contas_receber.relatorios.steps import StepNames
from src.config.settings import ASSETS_DIR
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import SkipStep
from src.infrastructure.vault import Vault
from src.utils.image_match import MatchThreshold, find_template
from src.utils.window_utils import maximize_window

_HOME_IMG = ASSETS_DIR / "Senior" / "components" / "sidebar" / "home" / "index.png"
_REPORT_TITLE_IMG = ASSETS_DIR / "Senior" / "pages" / "selecao_modelos_para_execucao" / "window_title.png"

_SIDEBAR_ITEMS = [
    (StepNames.GESTAO_EMPRESARIAL,    "gestao_empresarial/index.png"),
    (StepNames.FINANCAS,              "gestao_empresarial/financas/index.png"),
    (StepNames.GESTAO_CONTAS_RECEBER, "gestao_empresarial/financas/gestao_contas_receber/index.png"),
    (StepNames.CONTAS_RECEBER,        "gestao_empresarial/financas/gestao_contas_receber/contas_receber/index.png"),
    (StepNames.RELATORIOS,            "gestao_empresarial/financas/gestao_contas_receber/contas_receber/relatorios/index.png"),
]


async def _wait_for_home(page, runner=None, timeout_s: float = 120) -> None:
    """Poll until the Home sidebar template is found or timeout."""
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


@TaskRegistry.register("Relatório Contas Receber")
class GeracaoRelatorio:
    """Automate login into TS → Senior ERP → generate a Contas Receber report."""

    def __init__(self, runner=None, vault=None):
        self._runner = runner
        self._vault = vault or Vault()

    # ------------------------------------------------------------------
    # Schema / metadata
    # ------------------------------------------------------------------

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
            *[{**field, "when": {**field.get("when", {}), "relatorio": r.code}} for r in REPORTS for field in r.get_fields()],
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

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    async def _step(self, name: str, coro=None) -> None:
        """Report a step to the runner (if attached). Catches SkipStep."""
        try:
            if self._runner:
                await self._runner.report_step(name)
            if coro is not None:
                await coro
        except SkipStep:
            from src.infrastructure.logger import get_logger

            get_logger("TerminalServerRPA.report-generation").warning("step.skipped", step=name)

    def _attach_page(self, page) -> None:
        """Expose the active Playwright page to the runner for screenshots."""
        if self._runner:
            self._runner._page = page

    # ------------------------------------------------------------------
    # Phase: TS Login
    # ------------------------------------------------------------------

    async def _phase_login_ts(self, context, page, ts_creds: dict, base_url: str):
        """Log into Terminal Server and capture the remote application page."""
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

    # ------------------------------------------------------------------
    # Phase: Senior loading + login
    # ------------------------------------------------------------------

    async def _phase_senior_loading(self, remote_page, senior_creds: dict):
        """Wait for the Senior ERP init screen."""
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
        """Fill and submit Senior ERP credentials."""
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

    # ------------------------------------------------------------------
    # Phase: Home page setup + sidebar navigation
    # ------------------------------------------------------------------

    async def _phase_home_setup(self, remote_page):
        """Maximise the Senior window and wait for the Home sidebar."""
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
        """Click through the sidebar menu tree down to Contas Receber → Relatórios."""
        nav = SidebarNavigator()
        await nav.navigate(home, _SIDEBAR_ITEMS, self._step)

    # ------------------------------------------------------------------
    # Phase: Report actions
    # ------------------------------------------------------------------

    async def _phase_report_actions(self, remote_page, relatorio_code: str, params: dict) -> str | None:
        """Maximise the report window, select a report template, fill fields."""
        if not remote_page:
            for name in (
                StepNames.MAXIMIZANDO_RELATORIO,
                StepNames.DIGITANDO_RELATORIO,
                StepNames.MAXIMIZANDO_VALORES,
                StepNames.PREENCHENDO_ENTRADA,
                StepNames.PREENCHENDO_SAIDA,
            ):
                await self._step(name)
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
            valores: ValoresEntradaModeloPage | None = None
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
            await asyncio.sleep(1)
            await selecao.close()
            return nome_arquivo
        else:
            await self._step(StepNames.DIGITANDO_RELATORIO)
            await self._step(StepNames.MAXIMIZANDO_VALORES)
            await self._step(StepNames.PREENCHENDO_ENTRADA)
            await self._step(StepNames.PREENCHENDO_SAIDA)
        return None

    # ------------------------------------------------------------------
    # Entry-point
    # ------------------------------------------------------------------

    async def execute(self, params: dict) -> dict:
        """Orchestrate the full report-generation workflow."""
        from playwright.async_api import async_playwright

        ts_creds = self._resolve_creds(params, "TS Credenciais")
        senior_creds = self._resolve_creds(params, "Senior Credenciais")
        base_url = params.get("base_url", "")
        relatorio_code = params.get("relatorio", "")

        async with async_playwright() as p:
            downloads_path = DOWNLOADS_BASE / "financas" / "gestao_contas_receber" / "contas_receber" / "relatorios" / relatorio_code
            browser, context, page, _screen_w, _screen_h = await BrowserManager.launch(p, downloads_path=downloads_path)
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
