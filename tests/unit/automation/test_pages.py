from unittest.mock import AsyncMock, patch

import pytest


class TestLoginPage:
    @pytest.mark.asyncio
    async def test_navigate_calls_goto(self):
        from src.automation.pages.login_page import LoginPage

        page = AsyncMock()
        lp = LoginPage(page, base_url="http://test.com")
        await lp.navigate()
        page.goto.assert_awaited_once_with("http://test.com/login")

    @pytest.mark.asyncio
    async def test_login_fills_and_submits(self):
        from src.automation.pages.login_page import LoginPage

        page = AsyncMock()
        lp = LoginPage(page)
        await lp.login("admin", "secret")
        page.fill.assert_any_await("#username", "admin")
        page.fill.assert_any_await("#password", "secret")
        page.click.assert_awaited_once_with("#login-button")
        page.wait_for_selector.assert_awaited_once_with("#dashboard", timeout=10000)


class TestUserRegistrationPage:
    @pytest.mark.asyncio
    async def test_navigate_calls_goto(self):
        from src.automation.pages.user_registration_page import UserRegistrationPage

        page = AsyncMock()
        rp = UserRegistrationPage(page, base_url="http://test.com")
        await rp.navigate()
        page.goto.assert_awaited_once_with("http://test.com/users/new")

    @pytest.mark.asyncio
    async def test_register_fills_form(self):
        from src.automation.pages.user_registration_page import UserRegistrationPage

        page = AsyncMock()
        rp = UserRegistrationPage(page)
        await rp.register("user1", "pass", "u@t.com", "User One")
        page.fill.assert_any_await("#username", "user1")
        page.fill.assert_any_await("#password", "pass")
        page.fill.assert_any_await("#email", "u@t.com")
        page.fill.assert_any_await("#full-name", "User One")
        page.click.assert_awaited_once_with("#save-button")

    @pytest.mark.asyncio
    async def test_is_success(self):
        from src.automation.pages.user_registration_page import UserRegistrationPage

        page = AsyncMock()
        page.is_visible.return_value = True
        rp = UserRegistrationPage(page)
        assert await rp.is_success() is True
        page.is_visible.assert_awaited_once_with(".success-message")


class TestTsLoginPage:
    @pytest.mark.asyncio
    async def test_navigate_calls_goto(self):
        from src.automation.pages.ts_login_page import TsLoginPage

        page = AsyncMock()
        lp = TsLoginPage(page, base_url="https://sistema.nazaria.com.br/")
        await lp.navigate()
        page.goto.assert_awaited_once_with("https://sistema.nazaria.com.br/")

    @pytest.mark.asyncio
    async def test_login_fills_selectors(self):
        from unittest.mock import MagicMock

        from src.automation.pages.ts_login_page import TsLoginPage

        page = AsyncMock()
        page.get_by_text = MagicMock(return_value=AsyncMock())
        lp = TsLoginPage(page)
        await lp.login("myuser", "mypass")
        page.fill.assert_any_await("#Editbox1", "myuser")
        page.fill.assert_any_await("#Editbox2", "mypass")
        page.get_by_text.assert_called_once_with("Entrar")
        page.get_by_text.return_value.click.assert_called_once_with(click_count=2, delay=100)


class TestTsApplicationsPage:
    @pytest.mark.asyncio
    async def test_click_application_uses_image_match(self):
        from src.automation.pages.ts_applications_page import TsApplicationsPage

        page = AsyncMock()
        page.screenshot.return_value = b"fake_image_bytes"
        ap = TsApplicationsPage(page)
        ap._dump = AsyncMock()
        ap._log = lambda _: None

        with (
            patch("src.automation.pages.ts_applications_page.find_template") as mock_find,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_find.return_value = ((500, 300), 0.95)
            await ap.click_application("Gestão Empresarial", asset_folder="Senior")

        page.mouse.click.assert_awaited_once_with(500, 300)
