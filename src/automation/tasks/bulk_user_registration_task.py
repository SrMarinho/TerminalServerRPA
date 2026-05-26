from src.automation.pages.login_page import LoginPage
from src.automation.pages.user_registration_page import UserRegistrationPage
from src.core.entities.user import User
from src.core.use_cases.register_users_use_case import RegisterUsersUseCase
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.vault import Vault


@TaskRegistry.register("bulk-register-users")
class BulkUserRegistrationTask:
    def __init__(self, runner=None):
        self._runner = runner

    @staticmethod
    def get_schema():
        return [
            {"name": "base_url",  "label": "URL Base",          "type": "string"},
            {"name": "credentials", "label": "Credencial",      "type": "credential"},
            {"name": "users",     "label": "Usuários (JSON)",   "type": "json"},
        ]

    @staticmethod
    def get_steps():
        return ["login", "validar", "cadastrar", "concluido"]

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
        users_data = params.get("users", [])
        base_url = params.get("base_url", "")
        users = [User(**u) for u in users_data]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                if self._runner:
                    await self._runner.report_step("login")
                login_p = LoginPage(page, base_url)
                reg_p = UserRegistrationPage(page, base_url)
                use_case = RegisterUsersUseCase()

                await login_p.navigate()
                await login_p.login(creds["username"], creds["password"])

                if self._runner:
                    await self._runner.report_step("validar")
                result = use_case.execute(users)

                for user in result.success:
                    if self._runner:
                        await self._runner.report_step(f"cadastrar:{user.username}")
                    await reg_p.navigate()
                    await reg_p.register(user.username, user.password, user.email, user.full_name)

                if self._runner:
                    await self._runner.report_step("concluido")

                return {
                    "registered": len(result.success),
                    "errors": result.errors,
                }
            finally:
                await browser.close()
