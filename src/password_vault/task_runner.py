import asyncio
from enum import StrEnum


class TaskStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRunner:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._cancel_requested = False
        self._status = TaskStatus.IDLE
        self._page = None
        self._result = None

    @property
    def status(self) -> TaskStatus:
        return self._status

    async def run(self, task_name: str, params: dict | None = None):
        self._status = TaskStatus.RUNNING
        self._cancel_requested = False
        self._pause_event.set()
        try:
            await self._execute(task_name, params or {})
            if not self._cancel_requested:
                self._status = TaskStatus.COMPLETED
        except asyncio.CancelledError:
            self._status = TaskStatus.CANCELLED
        except Exception:
            self._status = TaskStatus.FAILED

    async def _execute(self, task_name: str, params: dict):
        tasks = {
            "bulk-register-users": self._bulk_register_users,
        }
        handler = tasks.get(task_name)
        if handler:
            await handler(params)
        else:
            await self.checkpoint("unknown")

    async def _bulk_register_users(self, params: dict):
        from playwright.async_api import async_playwright

        from src.automation.pages.login_page import LoginPage
        from src.automation.pages.user_registration_page import UserRegistrationPage
        from src.automation.tasks.bulk_user_registration_task import BulkUserRegistrationTask
        from src.core.entities.user import User
        from src.core.use_cases.register_users_use_case import RegisterUsersUseCase

        users_data = params.get("users", [])
        creds = params.get("credentials", {})
        base_url = params.get("base_url", "")
        users = [User(**u) for u in users_data]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            self._page = page
            try:
                login_p = LoginPage(page, base_url)
                reg_p = UserRegistrationPage(page, base_url)
                use_case = RegisterUsersUseCase()
                task = BulkUserRegistrationTask(login_p, reg_p, use_case)
                result = await task.execute(users, creds)
                self._result = result
            finally:
                await browser.close()

    async def checkpoint(self, name: str):
        if self._cancel_requested:
            raise asyncio.CancelledError()
        await self._pause_event.wait()

    def pause(self):
        if self._status == TaskStatus.RUNNING:
            self._status = TaskStatus.PAUSED
            self._pause_event.clear()

    def resume(self):
        if self._status == TaskStatus.PAUSED:
            self._status = TaskStatus.RUNNING
            self._pause_event.set()

    def cancel(self):
        if self._status in (TaskStatus.RUNNING, TaskStatus.PAUSED):
            self._cancel_requested = True
            self._pause_event.set()


_task_runner = TaskRunner()


def get_runner() -> TaskRunner:
    return _task_runner
