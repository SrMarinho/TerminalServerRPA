"""End-to-end task execution: TaskPool + TaskRunner + ExecutionManager + events,
driving the real async state machine (run / pause / resume / cancel / skip /
breakpoints) against a real SQLite DB."""

import asyncio

import pytest

from src.infrastructure.execution_manager import get_manager
from src.infrastructure.models import ExecutionStatus, StepStatus
from src.infrastructure.task_runner import TaskPool

pytestmark = pytest.mark.asyncio


async def _await_status(runner, status, timeout=2.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if runner.status == status:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"timeout waiting for {status}, got {runner.status}")


class TestHappyPath:
    async def test_full_run_persists_and_broadcasts(self, temp_db, fake_task, event_sink):
        name, state, _ = fake_task
        pool = TaskPool()
        exec_id = pool.start(name, {"x": 1})
        runner = pool.get(exec_id)

        await asyncio.wait_for(runner._task, timeout=3)

        assert runner.status == ExecutionStatus.COMPLETED
        assert state["ran_steps"] == ["step1", "step2", "step3"]

        execution = get_manager().get(exec_id)
        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.result == {"ok": True, "params": {"x": 1}}
        assert all(s.status == StepStatus.COMPLETED for s in execution.steps)
        assert len(execution.logs) == 3

        pool_events = [e for e in event_sink if e["type"] == "pool:update"]
        assert any(e["status"] == "running" for e in pool_events)
        assert any(e["status"] == "completed" for e in pool_events)


class TestBreakpoint:
    async def test_breakpoint_pauses_then_resume_completes(self, temp_db, fake_task):
        name, state, _ = fake_task
        pool = TaskPool()
        exec_id = pool.start(name, {}, breakpoints=["step2"])
        runner = pool.get(exec_id)

        await _await_status(runner, ExecutionStatus.PAUSED)
        # paused entering step2: only step1 finished its body
        assert state["ran_steps"] == ["step1"]
        assert get_manager().get(exec_id).status == ExecutionStatus.PAUSED

        runner.resume()
        await asyncio.wait_for(runner._task, timeout=3)
        assert runner.status == ExecutionStatus.COMPLETED
        assert state["ran_steps"] == ["step1", "step2", "step3"]


class TestCancel:
    async def test_cancel_mid_run(self, temp_db, fake_task):
        name, state, aio = fake_task
        state["gate"] = aio.Event()  # block after each step so we can cancel
        pool = TaskPool()
        exec_id = pool.start(name, {})
        runner = pool.get(exec_id)

        # wait until it has run at least step1 and is blocked on the gate
        deadline = asyncio.get_event_loop().time() + 2
        while not state["ran_steps"] and asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(0.01)
        assert state["ran_steps"], "task never started"

        runner.cancel()
        await asyncio.wait_for(runner._task, timeout=3)
        assert runner.status == ExecutionStatus.CANCELLED
        assert get_manager().get(exec_id).status == ExecutionStatus.CANCELLED


class TestSkip:
    async def test_skip_step_continues(self, temp_db, fake_task):
        name, state, _ = fake_task
        pool = TaskPool()
        exec_id = pool.start(name, {}, breakpoints=["step2"])
        runner = pool.get(exec_id)

        await _await_status(runner, ExecutionStatus.PAUSED)
        runner.skip_step()  # arms skip + resumes
        await asyncio.wait_for(runner._task, timeout=3)

        assert runner.status == ExecutionStatus.COMPLETED
        assert "step2" in state["skipped"]
        assert state["ran_steps"] == ["step1", "step3"]


class TestPoolGuards:
    async def test_single_task_busy_guard(self, temp_db, fake_task):
        name, state, aio = fake_task
        state["gate"] = aio.Event()  # keep first run busy
        pool = TaskPool()
        first = pool.start(name, {})
        runner = pool.get(first)
        try:
            await _await_status(runner, ExecutionStatus.RUNNING)
            assert pool.is_busy()
            with pytest.raises(RuntimeError):
                pool.start(name, {})
        finally:
            runner.cancel()
            await asyncio.wait_for(runner._task, timeout=3)

    async def test_finished_runner_frees_pool(self, temp_db, fake_task):
        name, _state, _ = fake_task
        pool = TaskPool()
        first = pool.start(name, {})
        await asyncio.wait_for(pool.get(first)._task, timeout=3)
        assert not pool.is_busy()
        # a second run is allowed once the first finished
        second = pool.start(name, {})
        await asyncio.wait_for(pool.get(second)._task, timeout=3)
        assert pool.get(second).status == ExecutionStatus.COMPLETED
