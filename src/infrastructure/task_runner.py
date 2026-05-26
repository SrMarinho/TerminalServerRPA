import asyncio
import traceback
from enum import StrEnum

from src.infrastructure.execution_manager import get_manager
from src.infrastructure.task_registry import TaskRegistry


class TaskStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRunner:
    def __init__(self, execution_id: str = ""):
        self._execution_id = execution_id
        self._current_step: str = ""
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._cancel_requested = False
        self._status = TaskStatus.IDLE
        self._result = None

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def execution_id(self) -> str:
        return self._execution_id

    async def run(self, task_name: str, params: dict | None = None):
        self._status = TaskStatus.RUNNING
        self._cancel_requested = False
        self._pause_event.set()
        try:
            await self._execute(task_name, params or {})
            if not self._cancel_requested:
                self._status = TaskStatus.COMPLETED
                if self._current_step:
                    get_manager().update_step_status(self._execution_id, self._current_step, "completed")
                get_manager().complete(self._execution_id, self._result)
        except asyncio.CancelledError:
            self._status = TaskStatus.CANCELLED
            if self._current_step:
                get_manager().update_step_status(self._execution_id, self._current_step, "cancelled")
            get_manager().cancel(self._execution_id)
        except Exception as e:
            self._status = TaskStatus.FAILED
            if self._current_step:
                get_manager().update_step_status(self._execution_id, self._current_step, "failed")
            get_manager().fail(self._execution_id, str(e) + "\n" + traceback.format_exc())

    async def _execute(self, task_name: str, params: dict):
        TaskRegistry.auto_discover()
        task_cls = TaskRegistry.get(task_name)
        if task_cls is None:
            await self.checkpoint("unknown")
            return
        task = task_cls(runner=self)
        self._result = await task.execute(params)

    def log(self, message: str, level: str = "info"):
        if self._execution_id:
            get_manager().add_log(self._execution_id, message, level)

    async def report_step(self, name: str):
        if self._execution_id:
            if self._current_step:
                get_manager().update_step_status(self._execution_id, self._current_step, "completed")
            self._current_step = name
            get_manager().set_step(self._execution_id, name, "running")
        await self.checkpoint(name)

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


class TaskPool:
    def __init__(self):
        self._runners: dict[str, TaskRunner] = {}

    def start(self, task_name: str, params: dict | None = None) -> str:
        mgr = get_manager()
        exec_id = mgr.create(task_name, params)
        runner = TaskRunner(execution_id=exec_id)
        self._runners[exec_id] = runner
        asyncio.create_task(self._run(exec_id, task_name, params or {}))
        return exec_id

    async def _run(self, task_id: str, task_name: str, params: dict):
        await self._runners[task_id].run(task_name, params)

    def get(self, task_id: str) -> TaskRunner | None:
        return self._runners.get(task_id)

    def list_all(self) -> dict[str, dict]:
        return {tid: {"task_id": tid, "status": r.status.value} for tid, r in self._runners.items()}

    def cleanup_done(self):
        done = [tid for tid, r in self._runners.items() if r.status not in (TaskStatus.RUNNING, TaskStatus.PAUSED)]
        for tid in done:
            del self._runners[tid]


_pool = TaskPool()


def get_pool() -> TaskPool:
    return _pool
