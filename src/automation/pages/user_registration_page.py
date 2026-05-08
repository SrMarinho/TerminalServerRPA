from playwright.async_api import Page


class UserRegistrationPage:
    def __init__(self, page: Page, base_url: str = ""):
        self._page = page
        self._base_url = base_url

    async def navigate(self):
        await self._page.goto(f"{self._base_url}/users/new")

    async def register(self, username: str, password: str, email: str, full_name: str):
        await self._page.fill("#username", username)
        await self._page.fill("#password", password)
        await self._page.fill("#email", email)
        await self._page.fill("#full-name", full_name)
        await self._page.click("#save-button")
        await self._page.wait_for_selector(".success-message", timeout=10000)

    async def is_success(self) -> bool:
        return await self._page.is_visible(".success-message")
