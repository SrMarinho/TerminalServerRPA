import asyncio

from src.automation.pages.ts_login_page import TsLoginPage
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.vault import Vault


@TaskRegistry.register("geracao-relatorio")
class GeracaoRelatorio:
    def __init__(self, runner=None):
        self._runner = runner

    @staticmethod
    def get_schema():
        return [
            {"name": "base_url",  "label": "URL Base",          "type": "string"},
            {"name": "credentials", "label": "Credencial",      "type": "credential"},
        ]

    @staticmethod
    def _resolve_creds(params: dict) -> dict:
        vault = Vault()
        raw = params.get("credentials", {})
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

        creds = self._resolve_creds(params)
        base_url = params.get("base_url", "")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            try:
                if self._runner:
                    await self._runner.report_step("login")
                login_p = TsLoginPage(page, base_url)
                await login_p.navigate()
                await login_p.login(creds["username"], creds["password"])

                if self._runner:
                    await self._runner.report_step("aguardando")
                await asyncio.sleep(10)
                    

                if self._runner:
                    await self._runner.report_step("concluido")

                return {"status": "ok"}
            finally:
                await browser.close()
