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
import ctypes  # GetSystemMetrics for viewport sizing

from src.automation.pages.contas_receber.reports import REPORTS, REPORTS_BY_CODE
from src.automation.pages.contas_receber.selecao_modelos_para_execucao_page import SelecaoModelosParaExecucaoPage
from src.automation.pages.home_page import HomePage
from src.automation.pages.senior_login_page import SeniorLoginPage
from src.automation.pages.ts_applications_page import TsApplicationsPage
from src.automation.pages.ts_login_page import TsLoginPage
from src.automation.pages.valores_entrada_modelo_page import ValoresEntradaModeloPage
from src.config.settings import ASSETS_DIR
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import SkipStep
from src.infrastructure.vault import Vault
from src.utils.image_match import find_template
from src.utils.window_utils import maximize_window

_HOME_IMG = ASSETS_DIR / "Senior" / "components" / "sidebar" / "home" / "index.png"
_REPORT_TITLE_IMG = ASSETS_DIR / "Senior" / "pages" / "selecao_modelos_para_execucao" / "window_title.png"


async def _wait_for_home(page, runner=None, timeout_s: float = 120) -> None:
    """Poll until the Home sidebar template is found or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        screenshot = await page.screenshot()
        if find_template(screenshot, _HOME_IMG, 0.8):
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
    # Schema / metadata (unchanged)
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
            *[{**field, "when": {"relatorio": r.code}} for r in REPORTS for field in r.get_fields()],
        ]

    @staticmethod
    def get_steps():
        return {
            "Login": ["Login TS", "Iniciando Senior", "Login Senior"],
            "Processamento": [
                "Maximizando",
                "Carregando Senior",
                "Gestão Empresarial",
                "Finanças",
                "Gestão Contas Receber",
                "Contas Receber",
                "Relatórios",
                "Maximizando Relatório",
                "Digitando Relatório",
                "Maximizando Valores",
                "Preenchendo Campos",
            ],
            "Finalização": ["Concluido"],
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
        """Report a step to the runner (if attached). Catches SkipStep.

        When *coro* is provided it is awaited inside the same try/except
        so that a single SkipStep from either report_step or the action
        is handled gracefully.
        """
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
    # Browser lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def _get_screen_size() -> tuple[int, int]:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    @staticmethod
    async def _maximize_cdp(context, page, screen_w: int | None = None, screen_h: int | None = None) -> None:
        """Maximise a browser window via Chrome DevTools Protocol.

        When *screen_w* and *screen_h* are provided the window is first
        positioned at (0,0) with the full viewport size before maximising.
        This two-step dance is needed for TS remote sessions.
        """
        session = await context.new_cdp_session(page)
        win_info = await session.send("Browser.getWindowForTarget")
        if screen_w and screen_h:
            await session.send(
                "Browser.setWindowBounds",
                {
                    "windowId": win_info["windowId"],
                    "bounds": {"left": 0, "top": 0, "width": screen_w, "height": screen_h, "windowState": "normal"},
                },
            )
        await session.send(
            "Browser.setWindowBounds",
            {"windowId": win_info["windowId"], "bounds": {"windowState": "maximized"}},
        )
        await session.detach()
        if screen_w and screen_h:
            await page.set_viewport_size({"width": screen_w, "height": screen_h})

    async def _launch_browser(self, playwright):
        """Launch Chromium, create context + page, maximise the local window."""
        browser = await playwright.chromium.launch(headless=False, args=["--start-maximized"])
        screen_w, screen_h = self._get_screen_size()
        context = await browser.new_context(viewport=None)
        page = await context.new_page()
        await self._maximize_cdp(context, page)  # maximise local playback page
        await page.bring_to_front()
        await asyncio.sleep(1)
        return browser, context, page, screen_w, screen_h

    # ------------------------------------------------------------------
    # Phase: TS Login
    # ------------------------------------------------------------------

    async def _phase_login_ts(self, context, page, ts_creds: dict, base_url: str):
        """Log into Terminal Server and capture the remote application page."""
        from playwright.async_api import async_playwright as _  # noqa: F401 — ensure importable

        remote_page = None
        try:
            await self._step("Login TS")
            login_p = TsLoginPage(page, base_url)
            await login_p.navigate()
            async with context.expect_event("page", timeout=60000) as new_page_info:
                await login_p.login(ts_creds["username"], ts_creds["password"])
            remote_page = await new_page_info.value
            await remote_page.wait_for_load_state("load", timeout=60000)
        except SkipStep:
            return None

        # Maximize the remote TS window (two-step CDP for correct sizing)
        screen_w, screen_h = self._get_screen_size()
        await self._maximize_cdp(context, remote_page, screen_w, screen_h)
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
            await self._step("Iniciando Senior")
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
            await self._step("Login Senior")  # report only, no action
            return
        await self._step("Login Senior", senior_login.wait_for_login_screen())
        try:
            await senior_login.fill_and_submit(senior_creds["username"], senior_creds["password"])
        except SkipStep:
            from src.infrastructure.logger import get_logger

            get_logger("TerminalServerRPA.report-generation").warning(
                "step.skipped.submit", step="Login Senior"
            )

    # ------------------------------------------------------------------
    # Phase: Home page setup + sidebar navigation
    # ------------------------------------------------------------------

    async def _phase_home_setup(self, remote_page):
        """Maximise the Senior window and wait for the Home sidebar."""
        home = None
        if remote_page:
            try:
                await self._step("Maximizando")
                home = HomePage(remote_page, log=self._runner.log if self._runner else None)
                await home.maximize()
            except SkipStep:
                pass

            await self._step("Carregando Senior", _wait_for_home(remote_page, self._runner))
        else:
            await self._step("Maximizando")
            await self._step("Carregando Senior")

        return home

    async def _phase_navigate_sidebar(self, home):
        """Click through the sidebar menu tree down to Contas Receber → Relatórios."""
        sidebar_items = [
            ("Gestão Empresarial", "gestao_empresarial/index.png"),
            ("Finanças", "gestao_empresarial/financas/index.png"),
            ("Gestão Contas Receber", "gestao_empresarial/financas/gestao_contas_receber/index.png"),
            (
                "Contas Receber",
                "gestao_empresarial/financas/gestao_contas_receber/contas_receber/index.png",
            ),
            (
                "Relatórios",
                "gestao_empresarial/financas/gestao_contas_receber/contas_receber/relatorios/index.png",
            ),
        ]
        for step_name, img in sidebar_items:
            if home:
                await self._step(step_name, home.click_sidebar_item(img))
            else:
                await self._step(step_name)

    # ------------------------------------------------------------------
    # Phase: Report actions
    # ------------------------------------------------------------------

    async def _phase_report_actions(self, remote_page, relatorio_code: str, params: dict) -> None:
        """Maximise the report window, select a report template, fill fields."""
        if not remote_page:
            for name in ("Maximizando Relatório", "Digitando Relatório", "Maximizando Valores", "Preenchendo Campos"):
                await self._step(name)
            return

        await self._step("Maximizando Relatório", maximize_window(
            remote_page,
            self._runner.log if self._runner else None,
            title_img=_REPORT_TITLE_IMG,
        ))
        await asyncio.sleep(1)

        report = REPORTS_BY_CODE.get(relatorio_code)
        if report:
            await self._step("Digitando Relatório")

            selecao = SelecaoModelosParaExecucaoPage(
                remote_page,
                log=self._runner.log if self._runner else None,
            )
            try:
                await selecao.open_report(report)
            except SkipStep:
                from src.infrastructure.logger import get_logger

                get_logger("TerminalServerRPA.report-generation").warning(
                    "step.skipped.open_report", step="Digitando Relatório"
                )

            valores = ValoresEntradaModeloPage(
                remote_page,
                log=self._runner.log if self._runner else None,
            )
            await self._step("Maximizando Valores", valores.maximize())
            await self._step("Preenchendo Campos", valores.fill(report, params))
        else:
            await self._step("Digitando Relatório")
            await self._step("Maximizando Valores")
            await self._step("Preenchendo Campos")

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
            browser, context, page, _screen_w, _screen_h = await self._launch_browser(p)
            try:
                self._attach_page(page)

                # Phase 1 — Terminal Server login
                remote = await self._phase_login_ts(context, page, ts_creds, base_url)
                self._attach_page(remote)

                # Phase 2 — Senior ERP login
                sl = await self._phase_senior_loading(remote, senior_creds)
                await self._phase_senior_login(remote, sl, senior_creds)

                # Phase 3 — Home page + sidebar
                home = await self._phase_home_setup(remote)
                await self._phase_navigate_sidebar(home)

                # Phase 4 — Report actions
                await self._phase_report_actions(remote, relatorio_code, params)

                await self._step("Concluido")
                return {"status": "ok"}
            finally:
                if self._runner:
                    self._runner._page = None
                await context.close()
                await browser.close()
