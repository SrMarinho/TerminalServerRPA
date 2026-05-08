import asyncio

import pytest

from src.infrastructure.task_runner import TaskRunner, TaskStatus


@pytest.fixture
def runner():
    return TaskRunner()


class TestInitialState:
    def test_starts_idle(self, runner):
        assert runner.status == TaskStatus.IDLE


class TestPauseResume:
    def test_pause_sets_paused(self, runner):
        runner._status = TaskStatus.RUNNING
        runner.pause()
        assert runner.status == TaskStatus.PAUSED

    def test_resume_sets_running(self, runner):
        runner._status = TaskStatus.PAUSED
        runner.resume()
        assert runner.status == TaskStatus.RUNNING

    def test_pause_ignored_if_not_running(self, runner):
        runner.pause()
        assert runner.status == TaskStatus.IDLE

    def test_resume_ignored_if_not_paused(self, runner):
        runner.resume()
        assert runner.status == TaskStatus.IDLE


class TestCancel:
    def test_cancel_sets_flag(self, runner):
        runner._status = TaskStatus.RUNNING
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
        runner._status = TaskStatus.PAUSED
        runner._pause_event.clear()

        async def resume_soon():
            await asyncio.sleep(0.01)
            runner._pause_event.set()

        asyncio.create_task(resume_soon())
        await runner.checkpoint("test")


class TestRun:
    @pytest.mark.asyncio
    async def test_run_marks_completed(self, runner):
        await runner.run("noop-task")
        assert runner.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_cancelled_via_checkpoint(self, runner):
        original_checkpoint = runner.checkpoint
        async def cancel_on_first_checkpoint(name):
            runner._cancel_requested = True
            return await original_checkpoint(name)
        runner.checkpoint = cancel_on_first_checkpoint
        await runner.run("noop-task")
        assert runner.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_run_fails_on_exception(self, runner):
        async def raise_error(*a, **kw):
            raise ValueError("simulated failure")
        runner._execute = raise_error
        await runner.run("noop-task")
        assert runner.status == TaskStatus.FAILED


class TestGetRunner:
    def test_get_runner_returns_singleton(self):
        from src.infrastructure.task_runner import get_runner
        r1 = get_runner()
        r2 = get_runner()
        assert r1 is r2
