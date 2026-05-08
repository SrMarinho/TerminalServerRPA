from unittest.mock import AsyncMock, MagicMock

import pytest

from src.automation.tasks.bulk_user_registration_task import BulkUserRegistrationTask
from src.core.entities.user import User


class TestBulkUserRegistrationTask:
    @pytest.mark.asyncio
    async def test_execute_registers_users(self):
        login_page = AsyncMock()
        reg_page = AsyncMock()
        use_case = MagicMock()
        use_case.execute.return_value = MagicMock(
            success=[User("u1", "p1", "e1", "U1"), User("u2", "p2", "e2", "U2")],
            errors=[],
        )
        task = BulkUserRegistrationTask(login_page, reg_page, use_case)
        result = await task.execute(
            [User("u1", "p1", "e1", "U1"), User("u2", "p2", "e2", "U2")],
            {"username": "admin", "password": "pass"},
        )
        assert result["registered"] == 2
        login_page.navigate.assert_awaited_once()
        login_page.login.assert_awaited_once_with("admin", "pass")
        assert reg_page.navigate.await_count == 2
        assert reg_page.register.await_count == 2

    @pytest.mark.asyncio
    async def test_execute_handles_errors(self):
        login_page = AsyncMock()
        reg_page = AsyncMock()
        use_case = MagicMock()
        use_case.execute.return_value = MagicMock(
            success=[],
            errors=[{"user": "u1", "errors": ["invalid"]}],
        )
        task = BulkUserRegistrationTask(login_page, reg_page, use_case)
        result = await task.execute([], {"username": "admin", "password": "pass"})
        assert result["registered"] == 0
        assert len(result["errors"]) == 1
