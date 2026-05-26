import asyncio
from pathlib import Path

import pyautogui
from playwright.sync_api import Page


class SeniorLoginPage:
    def __init__(self, page: Page, base_url: str = ""):
        self._page = page
        self.assets_path = Path(__file__).parent / "assets" / "Senior" / "pages" / "senior_login_page"

    async def login(self, username: str, password: str):
        input_username = pyautogui.locateCenterOnScreen(self.assets_path / "input_username.png", confidence=0.8)
        input_password = pyautogui.locateCenterOnScreen(self.assets_path / "input_password.png", confidence=0.8)
        btn_login = pyautogui.locateCenterOnScreen(self.assets_path / "btn_login.png", confidence=0.8)

        if not all([input_username, input_password, btn_login]):
            raise Exception("Não foi possível localizar os campos de login ou o botão de entrar na tela.")

        if input_username and input_password:
            pyautogui.click(input_username)
            pyautogui.write(username, interval=0.1)
            pyautogui.click(input_password)
            pyautogui.write(password, interval=0.1)

        pyautogui.click(btn_login)
        await asyncio.sleep(5)  # Aguarda o login ser processado, ajuste conforme necessário
