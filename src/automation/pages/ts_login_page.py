import asyncio

from playwright.async_api import Page


class TsLoginPage:
    def __init__(self, page: Page, base_url: str = ""):
        self._page = page
        self._base_url = base_url

    async def navigate(self):
        await self._page.goto(f"{self._base_url}")

    async def login(self, username: str, password: str):
        await self._page.fill("#Editbox1", username)
        await self._page.fill("#Editbox2", password)
        await asyncio.sleep(0.4)  # Pequena pausa para garantir que os campos foram preenchidos
        await self._page.get_by_text("Entrar").click(click_count=2, delay=100)
        # await self._page.wait_for_selector("#dashboard", timeout=10000)
