from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.automation.tasks.bulk_user_registration_task import BulkUserRegistrationTask


class TestBulkUserRegistrationTask:
    @staticmethod
    def _mock_playwright():
        mock_p = MagicMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        return mock_p, mock_browser, mock_page

    @pytest.mark.asyncio
    @patch("playwright.async_api.async_playwright")
    async def test_execute_returns_result_dict(self, mock_async_pw):
        mock_p, _, _ = self._mock_playwright()
        mock_async_pw.return_value.__aenter__.return_value = mock_p

        task = BulkUserRegistrationTask(runner=None)
        result = await task.execute({
            "credentials": {"username": "admin", "password": "pass"},
            "users": [{"username": "u1", "password": "p1", "email": "e1", "full_name": "U1"}],
            "base_url": "http://test.com",
        })
        assert isinstance(result, dict)
        assert "registered" in result
        assert "errors" in result

    @pytest.mark.asyncio
    @patch("playwright.async_api.async_playwright")
    async def test_execute_empty_params_raises(self, mock_async_pw):
        mock_p, _, _ = self._mock_playwright()
        mock_async_pw.return_value.__aenter__.return_value = mock_p

        task = BulkUserRegistrationTask(runner=None)
        with pytest.raises(KeyError):
            await task.execute({})
