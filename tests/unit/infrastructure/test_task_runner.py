import asyncio

import pytest

from src.infrastructure.models import ExecutionStatus
from src.infrastructure.task_runner import TaskRunner


@pytest.fixture
def runner():
    return TaskRunner()


class TestInitialState:
    def test_starts_idle(self, runner):
        assert runner.status == ExecutionStatus.IDLE


class TestPauseResume:
    def test_pause_sets_paused(self, runner):
        runner._status = ExecutionStatus.RUNNING
        runner.pause()
        assert runner.status == ExecutionStatus.PAUSED

    def test_resume_sets_running(self, runner):
        runner._status = ExecutionStatus.PAUSED
        runner.resume()
        assert runner.status == ExecutionStatus.RUNNING

    def test_pause_ignored_if_not_running(self, runner):
        runner.pause()
        assert runner.status == ExecutionStatus.IDLE

    def test_resume_ignored_if_not_paused(self, runner):
        runner.resume()
        assert runner.status == ExecutionStatus.IDLE


class TestCancel:
    def test_cancel_sets_flag(self, runner):
        runner._status = ExecutionStatus.RUNNING
        runner.cancel()
        assert runner._cancel_requested is True

    def test_cancel_ignored_if_idle(self, runner):
        runner.cancel()
        assert runner._cancel_requested is False


class TestCheckpoint:
    @pytest.mark.asyncio
    async def test_checkpoint_raises_when_cancelled(self, runner):
        runner._cancel_requested = True
        with pytest.raises(asyncio.CancelledError):
            await runner.checkpoint("test")

    @pytest.mark.asyncio
    async def test_checkpoint_pauses_when_paused(self, runner):
        runner._status = ExecutionStatus.PAUSED
        runner._pause_event.clear()

        async def resume_soon():
            await asyncio.sleep(0.01)
            runner._pause_event.set()

        asyncio.create_task(resume_soon())
        await runner.checkpoint("test")


class TestRun:
    @pytest.mark.asyncio
    async def test_run_marks_completed(self, runner):
        async def noop(*a, **kw):
            return None

        runner._execute = noop
        await runner.run("noop-task")
        assert runner.status == ExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_cancelled_via_checkpoint(self, runner):
        original_checkpoint = runner.checkpoint

        async def cancel_on_first_checkpoint(name):
            runner._cancel_requested = True
            return await original_checkpoint(name)

        async def execute_with_checkpoint(*a, **kw):
            await runner.checkpoint("step")

        runner.checkpoint = cancel_on_first_checkpoint
        runner._execute = execute_with_checkpoint
        await runner.run("noop-task")
        assert runner.status == ExecutionStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_run_fails_on_exception(self, runner):
        async def raise_error(*a, **kw):
            raise ValueError("simulated failure")

        runner._execute = raise_error
        await runner.run("noop-task")
        assert runner.status == ExecutionStatus.FAILED


class TestGetPool:
    def test_get_pool_returns_singleton(self):
        from src.infrastructure.task_runner import get_pool

        p1 = get_pool()
        p2 = get_pool()
        assert p1 is p2
