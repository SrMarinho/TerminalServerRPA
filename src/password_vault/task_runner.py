from enum import Enum
import asyncio
from typing import Optional


class TaskStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRunner:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._cancel_requested = False
        self._status = TaskStatus.IDLE

    @property
    def status(self) -> TaskStatus:
        return self._status

    async def run(self, task_name: str, params: Optional[dict] = None):
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
        steps = {
            "bulk-register-users": ["login", "read_file", "register", "logout"],
        }
        for step in steps.get(task_name, ["unknown"]):
            await self.checkpoint(step)

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
