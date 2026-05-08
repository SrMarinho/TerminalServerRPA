from playwright.async_api import Page


class LoginPage:
    def __init__(self, page: Page, base_url: str = ""):
        self._page = page
        self._base_url = base_url

    async def navigate(self):
        await self._page.goto(f"{self._base_url}/login")

    async def login(self, username: str, password: str):
        await self._page.fill("#username", username)
        await self._page.fill("#password", password)
        await self._page.click("#login-button")
        await self._page.wait_for_selector("#dashboard", timeout=10000)
