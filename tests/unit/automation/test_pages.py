from unittest.mock import AsyncMock

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
