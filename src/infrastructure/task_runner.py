import asyncio
import traceback
from collections import deque
from typing import TYPE_CHECKING

from src.infrastructure.execution_manager import _broadcast_exec_event, get_manager, has_breakpoint
from src.infrastructure.models import ExecutionStatus
from src.infrastructure.screenshot_manager import ScreenshotManager
from src.infrastructure.task_registry import TaskRegistry

if TYPE_CHECKING:
    from playwright.async_api import Page


class SkipStep(Exception):  # noqa: N818
    pass


class TaskRunner:
    def __init__(self, execution_id: str = ""):
        self._execution_id = execution_id
        self._current_step: str = ""
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._cancel_requested = False
        self._skip_current = False
        self._status = ExecutionStatus.IDLE
        self._result = None
        self._task: asyncio.Task | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page | None:
        return self._page

    @page.setter
    def page(self, value: Page | None) -> None:
        self._page = value

    @property
    def status(self) -> ExecutionStatus:
        return self._status

    @property
    def execution_id(self) -> str:
        return self._execution_id

    async def run(self, task_name: str, params: dict | None = None):
        self._status = ExecutionStatus.RUNNING
        self._cancel_requested = False
        self._pause_event.set()
        try:
            await self._execute(task_name, params or {})
            if not self._cancel_requested:
                self._status = ExecutionStatus.COMPLETED
                if self._current_step:
                    get_manager().update_step_status(self._execution_id, self._current_step, "completed")
                get_manager().complete(self._execution_id, self._result)
        except asyncio.CancelledError:
            self._status = ExecutionStatus.CANCELLED
            if self._current_step:
                get_manager().update_step_status(self._execution_id, self._current_step, "cancelled")
            get_manager().cancel(self._execution_id)
        except Exception as e:
            self._status = ExecutionStatus.FAILED
            if self._current_step:
                get_manager().update_step_status(self._execution_id, self._current_step, "failed")
            get_manager().fail(self._execution_id, str(e) + "\n" + traceback.format_exc())

    async def _execute(self, task_name: str, params: dict):
        from structlog.contextvars import bind_contextvars, clear_contextvars

        if self._execution_id:
            bind_contextvars(execution_id=self._execution_id)
        try:
            TaskRegistry.auto_discover()
            task_cls = TaskRegistry.get(task_name)
            if task_cls is None:
                raise ValueError(f"Unknown task: {task_name}")
            from src.automation.param_resolvers import resolve_params
            from src.infrastructure.vault import get_vault

            task = task_cls(runner=self, vault=get_vault())
            self._result = await task.execute(resolve_params(params or {}))
        finally:
            clear_contextvars()

    def log(self, message: str, level: str = "info"):
        if self._execution_id:
            get_manager().add_log(self._execution_id, message, level)
        else:
            from src.infrastructure.logger import get_logger

            get_logger("TerminalServerRPA.task-runner").log(
                level.upper() if isinstance(level, str) else "INFO", message
            )

    async def report_step(self, name: str):
        if self._execution_id:
            if self._current_step:
                get_manager().update_step_status(self._execution_id, self._current_step, "completed")
            self._current_step = name
            get_manager().set_step(self._execution_id, name, "running")
            if has_breakpoint(self._execution_id, name):
                self.pause()
        await self.checkpoint(name)
        if self._skip_current:
            self._skip_current = False
            self.log(f"Step skipped: {name}", "warning")
            if self._execution_id:
                get_manager().update_step_status(self._execution_id, name, "completed")
            raise SkipStep(name)

    async def checkpoint(self, name: str = ""):
        if self._cancel_requested:
            raise asyncio.CancelledError()
        await self._pause_event.wait()

    def pause(self):
        if self._status == ExecutionStatus.RUNNING:
            self._status = ExecutionStatus.PAUSED
            self._pause_event.clear()
            if self._execution_id:
                get_manager().set_status(self._execution_id, "paused")
                _broadcast_exec_event(
                    {"type": "execution:status", "execution_id": self._execution_id, "status": "paused"}
                )

    def resume(self):
        if self._status == ExecutionStatus.PAUSED:
            self._status = ExecutionStatus.RUNNING
            self._pause_event.set()
            if self._execution_id:
                get_manager().set_status(self._execution_id, "running")
                _broadcast_exec_event(
                    {"type": "execution:status", "execution_id": self._execution_id, "status": "running"}
                )

    def skip_step(self):
        if self._status == ExecutionStatus.PAUSED:
            self._skip_current = True
            self.resume()

    def cancel(self):
        if self._status in (ExecutionStatus.RUNNING, ExecutionStatus.PAUSED):
            self._cancel_requested = True
            self._pause_event.set()
            if self._task and not self._task.done():
                self._task.cancel()


MAX_RUNNERS = 50


class TaskPool:
    def __init__(self):
        self._runners: dict[str, TaskRunner] = {}
        # FIFO of (task_name, params, breakpoints) waiting for the single slot.
        self._queue: deque[tuple[str, dict | None, list[str] | None]] = deque()

    def is_busy(self) -> bool:
        return any(r.status in (ExecutionStatus.RUNNING, ExecutionStatus.PAUSED) for r in self._runners.values())

    def _prune_finished(self) -> None:
        """Drop the oldest finished runners once the pool exceeds MAX_RUNNERS.

        Active (running/paused) runners are always kept; permanent history lives
        in the DB, so dropping finished runners only frees in-memory state.
        """
        if len(self._runners) <= MAX_RUNNERS:
            return
        finished = [
            tid for tid, r in self._runners.items() if r.status not in (ExecutionStatus.RUNNING, ExecutionStatus.PAUSED)
        ]
        # dict preserves insertion order → oldest first
        for tid in finished[: len(self._runners) - MAX_RUNNERS]:
            del self._runners[tid]

    def start(self, task_name: str, params: dict | None = None, breakpoints: list[str] | None = None) -> str:
        from src.infrastructure.execution_manager import set_breakpoint

        if self.is_busy():
            raise RuntimeError("Uma execução já está em andamento. Aguarde ou cancele antes de iniciar.")

        self._prune_finished()
        mgr = get_manager()
        exec_id = mgr.create(task_name, params)
        runner = TaskRunner(execution_id=exec_id)
        self._runners[exec_id] = runner
        for bp in breakpoints or []:
            set_breakpoint(exec_id, bp, True)
        _broadcast_exec_event({"type": "pool:update", "task_id": exec_id, "task_name": task_name, "status": "running"})
        task = asyncio.create_task(self._run(exec_id, task_name, params or {}))
        runner._task = task
        return exec_id

    def start_or_enqueue(
        self, task_name: str, params: dict | None = None, breakpoints: list[str] | None = None
    ) -> dict:
        """Start now if the slot is free, otherwise queue (FIFO) instead of failing."""
        if self.is_busy():
            self._queue.append((task_name, params, breakpoints))
            _broadcast_exec_event({"type": "pool:queue", "size": len(self._queue)})
            return {"queued": True, "position": len(self._queue), "task": task_name}
        return {"queued": False, "task_id": self.start(task_name, params, breakpoints)}

    def queue_info(self) -> list[dict]:
        return [{"position": i + 1, "task_name": name} for i, (name, _p, _b) in enumerate(self._queue)]

    def _drain_queue(self) -> None:
        if not self._queue or self.is_busy():
            return
        task_name, params, bps = self._queue.popleft()
        _broadcast_exec_event({"type": "pool:queue", "size": len(self._queue)})
        try:
            self.start(task_name, params, bps)
        except RuntimeError:
            # Raced with a concurrent start — put it back at the front.
            self._queue.appendleft((task_name, params, bps))

    async def _run(self, task_id: str, task_name: str, params: dict):
        runner = self._runners[task_id]
        await runner.run(task_name, params)
        _broadcast_exec_event({"type": "pool:update", "task_id": task_id, "status": runner.status.value})
        self._drain_queue()

    def get(self, task_id: str) -> TaskRunner | None:
        return self._runners.get(task_id)

    def list_all(self) -> dict[str, dict]:
        return {tid: {"task_id": tid, "status": r.status.value} for tid, r in self._runners.items()}

    def cleanup_done(self):
        done = [
            tid for tid, r in self._runners.items() if r.status not in (ExecutionStatus.RUNNING, ExecutionStatus.PAUSED)
        ]
        for tid in done:
            del self._runners[tid]

    def shutdown(self):
        """Cancel every active runner so the process can exit cleanly."""
        for runner in self._runners.values():
            if runner.status in (ExecutionStatus.RUNNING, ExecutionStatus.PAUSED):
                runner.cancel()


_pool = TaskPool()


def _page_of(exec_id: str) -> Page | None:
    runner = _pool.get(exec_id)
    return runner.page if runner else None


_screenshots = ScreenshotManager(_page_of)


def subscribe_screenshot(exec_id: str) -> None:
    _screenshots.subscribe(exec_id)


def unsubscribe_screenshot(exec_id: str) -> None:
    _screenshots.unsubscribe(exec_id)


def get_pool() -> TaskPool:
    return _pool
