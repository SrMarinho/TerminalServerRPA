from src.automation.pages.login_page import LoginPage
from src.automation.pages.user_registration_page import UserRegistrationPage
from src.core.entities.user import User
from src.core.use_cases.register_users_use_case import RegisterUsersUseCase


class BulkUserRegistrationTask:
    def __init__(self, login_page: LoginPage, reg_page: UserRegistrationPage, use_case: RegisterUsersUseCase):
        self._login_page = login_page
        self._reg_page = reg_page
        self._use_case = use_case

    async def execute(self, users: list[User], credentials: dict) -> dict:
        await self._login_page.navigate()
        await self._login_page.login(credentials["username"], credentials["password"])

        result = self._use_case.execute(users)

        for user in result.success:
            await self._reg_page.navigate()
            await self._reg_page.register(user.username, user.password, user.email, user.full_name)

        return {
            "registered": len(result.success),
            "errors": result.errors,
        }
