import asyncio
import traceback

from src.infrastructure.execution_manager import _broadcast_exec_event, get_manager, has_breakpoint
from src.infrastructure.models import ExecutionStatus
from src.infrastructure.task_registry import TaskRegistry


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
        self._page: object | None = None

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
        TaskRegistry.auto_discover()
        task_cls = TaskRegistry.get(task_name)
        if task_cls is None:
            await self.checkpoint("unknown")
            return
        from src.infrastructure.vault import Vault

        from src.automation.param_resolvers import resolve_params

        task = task_cls(runner=self, vault=Vault())
        self._result = await task.execute(resolve_params(params or {}))

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


class TaskPool:
    def __init__(self):
        self._runners: dict[str, TaskRunner] = {}

    def is_busy(self) -> bool:
        return any(r.status in (ExecutionStatus.RUNNING, ExecutionStatus.PAUSED) for r in self._runners.values())

    def start(self, task_name: str, params: dict | None = None, breakpoints: list[str] | None = None) -> str:
        from src.infrastructure.execution_manager import set_breakpoint

        if self.is_busy():
            raise RuntimeError("Uma execução já está em andamento. Aguarde ou cancele antes de iniciar.")

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

    async def _run(self, task_id: str, task_name: str, params: dict):
        runner = self._runners[task_id]
        await runner.run(task_name, params)
        _broadcast_exec_event({"type": "pool:update", "task_id": task_id, "status": runner.status.value})

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
_screenshot_subscribers: dict[str, int] = {}
_screenshot_tasks: dict[str, asyncio.Task] = {}
_screenshot_last: dict[str, tuple[str, str]] = {}  # exec_id -> (mime, b64)
_screenshot_last_hash: dict[str, int] = {}


async def _screenshot_loop(exec_id: str):
    import base64

    import cv2  # type: ignore[import-untyped]
    import numpy as np  # type: ignore[import-untyped]

    try:
        while _screenshot_subscribers.get(exec_id, 0) > 0:
            runner = _pool.get(exec_id)
            if runner and runner._page:
                try:
                    raw = await runner._page.screenshot()  # type: ignore[attr-defined]
                    h = hash(raw)
                    if h != _screenshot_last_hash.get(exec_id):
                        _screenshot_last_hash[exec_id] = h
                        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
                        if img is None:
                            continue
                        ih, iw = img.shape[:2]
                        img = cv2.resize(img, (int(iw * 0.75), int(ih * 0.75)), interpolation=cv2.INTER_LANCZOS4)
                        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 88])
                        if ok:
                            b64 = base64.b64encode(buf.tobytes()).decode()
                            _screenshot_last[exec_id] = ("image/jpeg", b64)
                            _broadcast_exec_event(
                                {
                                    "type": "execution:screenshot",
                                    "execution_id": exec_id,
                                    "data": b64,
                                    "mime": "image/jpeg",
                                }
                            )
                except Exception as _exc:
                    from src.infrastructure.logger import get_logger

                    get_logger("TerminalServerRPA.screenshot-loop").warning("screenshot.error", error=str(_exc))
            await asyncio.sleep(0.25)
    finally:
        _screenshot_tasks.pop(exec_id, None)
        _screenshot_last_hash.pop(exec_id, None)


def subscribe_screenshot(exec_id: str):
    _screenshot_subscribers[exec_id] = _screenshot_subscribers.get(exec_id, 0) + 1
    cached = _screenshot_last.get(exec_id)
    if cached:
        _broadcast_exec_event(
            {
                "type": "execution:screenshot",
                "execution_id": exec_id,
                "data": cached[1],
                "mime": cached[0],
            }
        )
    if exec_id not in _screenshot_tasks:
        _screenshot_tasks[exec_id] = asyncio.create_task(_screenshot_loop(exec_id))


def unsubscribe_screenshot(exec_id: str):
    count = _screenshot_subscribers.get(exec_id, 0) - 1
    if count <= 0:
        _screenshot_subscribers.pop(exec_id, None)
    else:
        _screenshot_subscribers[exec_id] = count


def get_pool() -> TaskPool:
    return _pool
