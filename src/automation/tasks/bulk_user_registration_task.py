from src.automation.pages.login_page import LoginPage
from src.automation.pages.user_registration_page import UserRegistrationPage
from src.core.entities.user import User
from src.core.use_cases.register_users_use_case import RegisterUsersUseCase
from src.infrastructure.task_registry import TaskRegistry


@TaskRegistry.register("bulk-register-users")
class BulkUserRegistrationTask:
    def __init__(self, runner=None):
        self._runner = runner

    async def execute(self, params: dict) -> dict:
        from playwright.async_api import async_playwright

        creds = params.get("credentials", {})
        users_data = params.get("users", [])
        base_url = params.get("base_url", "")
        users = [User(**u) for u in users_data]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                login_p = LoginPage(page, base_url)
                reg_p = UserRegistrationPage(page, base_url)
                use_case = RegisterUsersUseCase()

                await login_p.navigate()
                await login_p.login(creds["username"], creds["password"])

                result = use_case.execute(users)

                for user in result.success:
                    await reg_p.navigate()
                    await reg_p.register(user.username, user.password, user.email, user.full_name)

                return {
                    "registered": len(result.success),
                    "errors": result.errors,
                }
            finally:
                await browser.close()
