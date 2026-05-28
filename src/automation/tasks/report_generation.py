import asyncio
import ctypes  # GetSystemMetrics for viewport sizing

from src.automation.pages.home_page import HomePage
from src.automation.pages.senior_login_page import SeniorLoginPage
from src.automation.pages.ts_applications_page import TsApplicationsPage
from src.automation.pages.ts_login_page import TsLoginPage
from src.config.settings import ASSETS_DIR
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import SkipStep
from src.infrastructure.vault import Vault
from src.utils.image_match import find_template
from src.utils.window_utils import maximize_window

_HOME_IMG = ASSETS_DIR / "Senior" / "components" / "sidebar" / "home" / "index.png"
_REPORT_TITLE_IMG = ASSETS_DIR / "Senior" / "pages" / "selecao_modelos_para_execucao" / "window_title.png"


async def _wait_for_home(page, runner=None, timeout_s: float = 120) -> None:
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
    def __init__(self, runner=None):
        self._runner = runner

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
                "options": ["703 | Rot.Conciliação - Tít.não baixados - Proc. Baixa"],
            },
            {
                "name": "empresa",
                "label": "Empresa",
                "type": "string",
                "when": {"relatorio": "703 | Rot.Conciliação - Tít.não baixados - Proc. Baixa"},
            },
            {
                "name": "filial",
                "label": "Filial",
                "type": "string",
                "when": {"relatorio": "703 | Rot.Conciliação - Tít.não baixados - Proc. Baixa"},
            },
            {
                "name": "cliente",
                "label": "Cliente (Adquirente)",
                "type": "string",
                "when": {"relatorio": "703 | Rot.Conciliação - Tít.não baixados - Proc. Baixa"},
            },
            {
                "name": "titulo",
                "label": "Título",
                "type": "string",
                "when": {"relatorio": "703 | Rot.Conciliação - Tít.não baixados - Proc. Baixa"},
            },
            {
                "name": "data_emissao",
                "label": "Data Emissão",
                "type": "string",
                "when": {"relatorio": "703 | Rot.Conciliação - Tít.não baixados - Proc. Baixa"},
            },
            {
                "name": "data_movimento",
                "label": "Data Movimento",
                "type": "string",
                "when": {"relatorio": "703 | Rot.Conciliação - Tít.não baixados - Proc. Baixa"},
            },
            {
                "name": "opcao",
                "label": "Opção",
                "type": "select",
                "default": "V",
                "options": ["V"],
                "when": {"relatorio": "703 | Rot.Conciliação - Tít.não baixados - Proc. Baixa"},
            },
            {
                "name": "analitico_sintetico",
                "label": "Analítico/Sintético",
                "type": "select",
                "default": "A",
                "options": ["A", "S"],
                "when": {"relatorio": "703 | Rot.Conciliação - Tít.não baixados - Proc. Baixa"},
            },
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
                "processando",
            ],
            "Finalização": ["Concluido"],
        }

    @staticmethod
    def _resolve_creds(params: dict, key: str = "credentials") -> dict:
        vault = Vault()
        raw = params.get(key, {})
        if isinstance(raw, dict) and "service" in raw:
            svc = raw["service"]
            users = vault.list_credentials(svc)
            if users:
                username = users[0]["username"]
                password = vault.get_password(svc, username)
                return {"username": username, "password": password or ""}
        return raw if isinstance(raw, dict) else {}

    async def execute(self, params: dict) -> dict:
        from playwright.async_api import async_playwright

        ts_creds = self._resolve_creds(params, "TS Credenciais")
        base_url = params.get("base_url", "")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            context = await browser.new_context(viewport=None)
            page = await context.new_page()
            if self._runner:
                self._runner._page = page
            await asyncio.sleep(1)
            session = await context.new_cdp_session(page)
            window_info = await session.send("Browser.getWindowForTarget")
            await session.send(
                "Browser.setWindowBounds",
                {
                    "windowId": window_info["windowId"],
                    "bounds": {"windowState": "maximized"},
                },
            )
            await session.detach()
            await page.bring_to_front()
            await asyncio.sleep(1)
            try:
                remote_page = None
                senior_login = None
                home = None

                try:
                    if self._runner:
                        await self._runner.report_step("Login TS")
                    login_p = TsLoginPage(page, base_url)
                    await login_p.navigate()
                    async with context.expect_event("page", timeout=60000) as new_page_info:
                        await login_p.login(ts_creds["username"], ts_creds["password"])
                    remote_page = await new_page_info.value
                    if self._runner:
                        self._runner._page = remote_page
                    await remote_page.wait_for_load_state("load", timeout=60000)
                    remote_session = await context.new_cdp_session(remote_page)
                    remote_win = await remote_session.send("Browser.getWindowForTarget")
                    await remote_session.send(
                        "Browser.setWindowBounds",
                        {
                            "windowId": remote_win["windowId"],
                            "bounds": {
                                "left": 0,
                                "top": 0,
                                "width": screen_w,
                                "height": screen_h,
                                "windowState": "normal",
                            },
                        },
                    )
                    await remote_session.send(
                        "Browser.setWindowBounds",
                        {
                            "windowId": remote_win["windowId"],
                            "bounds": {"windowState": "maximized"},
                        },
                    )
                    await remote_session.detach()
                    await remote_page.set_viewport_size({"width": screen_w, "height": screen_h})
                    apps_page = TsApplicationsPage(remote_page, log=self._runner.log if self._runner else None)
                    await apps_page.click_application("Gestão Empresarial", asset_folder="Senior")
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Iniciando Senior")
                    if remote_page:
                        senior_creds = self._resolve_creds(params, "Senior Credenciais")
                        senior_login = SeniorLoginPage(
                            remote_page,
                            log=self._runner.log if self._runner else None,
                            checkpoint=self._runner.checkpoint if self._runner else None,
                        )
                        await senior_login.wait_for_iniciando()
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Login Senior")
                    if senior_login:
                        await senior_login.wait_for_login_screen()
                        await senior_login.fill_and_submit(senior_creds["username"], senior_creds["password"])  # type: ignore[possibly-undefined]
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Maximizando")
                    if remote_page:
                        home = HomePage(remote_page, log=self._runner.log if self._runner else None)
                        await home.maximize()
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Carregando Senior")
                    if remote_page:
                        await _wait_for_home(remote_page, self._runner)
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Gestão Empresarial")
                    if home:
                        await home.click_sidebar_item("gestao_empresarial/index.png")
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Finanças")
                    if home:
                        await home.click_sidebar_item("gestao_empresarial/financas/index.png")
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Gestão Contas Receber")
                    if home:
                        await home.click_sidebar_item("gestao_empresarial/financas/gestao_contas_receber/index.png")
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Contas Receber")
                    if home:
                        await home.click_sidebar_item(
                            "gestao_empresarial/financas/gestao_contas_receber/contas_receber/index.png"
                        )
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Relatórios")
                    if home:
                        await home.click_sidebar_item(
                            "gestao_empresarial/financas/gestao_contas_receber/contas_receber/relatorios/index.png"
                        )
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Maximizando Relatório")
                    if remote_page:
                        await maximize_window(
                            remote_page, self._runner.log if self._runner else None, title_img=_REPORT_TITLE_IMG
                        )
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Digitando Relatório")
                    if remote_page:
                        col_img = (
                            ASSETS_DIR / "Senior" / "pages" / "selecao_modelos_para_execucao" / "coluna_numero.png"
                        )
                        screenshot = await remote_page.screenshot()
                        col_match = find_template(screenshot, col_img, 0.8)
                        if col_match:
                            cx, cy = col_match[0]
                            await remote_page.mouse.click(cx, cy)
                            await asyncio.sleep(0.5)
                        relatorio_raw = params.get("relatorio", "")
                        relatorio_num = relatorio_raw.split("|")[0].strip()
                        await remote_page.keyboard.type(relatorio_num, delay=100)
                except SkipStep:
                    pass

                try:
                    if self._runner:
                        await self._runner.report_step("Maximizando Valores")
                    if remote_page:
                        valores_title = (
                            ASSETS_DIR
                            / "Senior"
                            / "pages"
                            / "selecao_modelos_para_execucao"
                            / "valores_entrada_modelo"
                            / "index.png"
                        )
                        maximizar_img = ASSETS_DIR / "Senior" / "components" / "context_menu" / "maximizar.png"
                        screenshot = await remote_page.screenshot()
                        t_match = find_template(screenshot, valores_title, 0.8)
                        if t_match:
                            cx, cy = t_match[0]
                            await remote_page.mouse.click(cx, cy, button="right")
                            await asyncio.sleep(0.8)
                            screenshot = await remote_page.screenshot()
                            m_match = find_template(screenshot, maximizar_img, 0.8)
                            if m_match:
                                await remote_page.mouse.click(m_match[0][0], m_match[0][1])
                except SkipStep:
                    pass

                if self._runner:
                    await self._runner.report_step("Concluido")

                return {"status": "ok"}
            finally:
                if self._runner:
                    self._runner._page = None
                await context.close()
                await browser.close()
