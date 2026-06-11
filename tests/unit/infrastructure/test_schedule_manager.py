import contextlib
from unittest.mock import MagicMock, patch

import pytest

import src.infrastructure.schedule_manager as sm
from src.infrastructure.schedule_manager import ScheduleManager


@pytest.fixture
def temp_sched_db(tmp_path, monkeypatch):
    monkeypatch.setattr(sm, "DB_PATH", tmp_path / "executions.db")


@pytest.fixture
def manager(temp_sched_db):
    m = ScheduleManager()
    yield m
    # If a test started the scheduler it must also shut it down inside its own
    # event loop; here the loop is already closed, so only guard against leaks.
    if m._scheduler.running:  # pragma: no cover - safety net
        with contextlib.suppress(RuntimeError):
            m.shutdown()


class TestCrud:
    def test_create_and_list(self, manager):
        created = manager.create("plug:report", "0 7 * * *")
        assert created["id"] >= 1
        rows = manager.list_all()
        assert len(rows) == 1
        assert rows[0]["task_name"] == "plug:report"
        assert rows[0]["cron"] == "0 7 * * *"
        assert rows[0]["enabled"] is True
        assert rows[0]["last_run"] is None

    def test_create_rejects_invalid_cron(self, manager):
        with pytest.raises(ValueError):
            manager.create("t", "not a cron")
        assert manager.list_all() == []

    def test_delete(self, manager):
        sid = manager.create("t", "* * * * *")["id"]
        assert manager.delete(sid) is True
        assert manager.list_all() == []
        assert manager.delete(sid) is False

    def test_toggle(self, manager):
        sid = manager.create("t", "* * * * *")["id"]
        assert manager.set_enabled(sid, False) is True
        assert manager.list_all()[0]["enabled"] is False
        assert manager.set_enabled(sid, True) is True
        assert manager.list_all()[0]["enabled"] is True

    def test_toggle_missing_returns_false(self, manager):
        assert manager.set_enabled(999, True) is False


class TestJobSync:
    # async: AsyncIOScheduler.start() requires a running event loop

    async def test_start_registers_only_enabled(self, manager):
        manager.create("a", "0 7 * * *")
        disabled = manager.create("b", "0 8 * * *")["id"]
        manager.set_enabled(disabled, False)
        manager.start()
        jobs = {j.id for j in manager._scheduler.get_jobs()}
        assert len(jobs) == 1
        manager.shutdown()

    async def test_create_after_start_registers_job(self, manager):
        manager.start()
        sid = manager.create("c", "0 9 * * *")["id"]
        assert manager._scheduler.get_job(str(sid)) is not None
        manager.shutdown()

    async def test_disable_removes_job(self, manager):
        manager.start()
        sid = manager.create("d", "0 9 * * *")["id"]
        manager.set_enabled(sid, False)
        assert manager._scheduler.get_job(str(sid)) is None
        manager.shutdown()

    async def test_delete_removes_job(self, manager):
        manager.start()
        sid = manager.create("e", "0 9 * * *")["id"]
        manager.delete(sid)
        assert manager._scheduler.get_job(str(sid)) is None
        manager.shutdown()


class TestFire:
    @pytest.mark.asyncio
    async def test_fire_starts_task_and_records_last_run(self, manager):
        sid = manager.create("plug:report", "0 7 * * *")["id"]
        pool = MagicMock()
        pool.start_or_enqueue.return_value = {"queued": False, "task_id": "x"}
        with (
            patch("src.infrastructure.task_runner.get_pool", return_value=pool),
            patch("src.infrastructure.task_config.load_config", return_value={"a": 1}),
        ):
            await manager._fire(sid, "plug:report")
        pool.start_or_enqueue.assert_called_once_with("plug:report", {"a": 1})
        assert manager.list_all()[0]["last_run"] is not None

    @pytest.mark.asyncio
    async def test_fire_never_raises(self, manager):
        sid = manager.create("plug:report", "0 7 * * *")["id"]
        with patch("src.infrastructure.task_runner.get_pool", side_effect=RuntimeError("boom")):
            await manager._fire(sid, "plug:report")  # must not raise
