"""End-to-end persistence: ExecutionManager + ExecutionRepository + BreakpointStore
+ migrations against a real SQLite file."""

import sqlite3

from src.infrastructure.execution_manager import ExecutionManager
from src.infrastructure.migrations import MIGRATIONS
from src.infrastructure.models import ExecutionStatus, StepStatus

_HEAD = len(MIGRATIONS)


class TestSchemaOnDisk:
    def test_migrations_applied_on_first_open(self, manager):
        version = manager._conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == _HEAD
        tables = {r[0] for r in manager._conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert {"executions", "steps", "logs", "breakpoints"} <= tables

    def test_foreign_keys_enabled(self, manager):
        assert manager._conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


class TestLifecycle:
    def test_create_then_get_roundtrip(self, manager, fake_task):
        name, _state, _ = fake_task
        exec_id = manager.create(name, {"a": 1})
        execution = manager.get(exec_id)
        assert execution is not None
        assert execution.status == ExecutionStatus.RUNNING
        assert execution.params == {"a": 1}
        assert [s.name for s in execution.steps] == ["step1", "step2", "step3"]
        assert all(s.status == StepStatus.PENDING for s in execution.steps)

    def test_step_and_log_progression(self, manager, fake_task):
        name, _state, _ = fake_task
        exec_id = manager.create(name, {})
        manager.set_step(exec_id, "step1", "running")
        manager.update_step_status(exec_id, "step1", "completed")
        manager.add_log(exec_id, "hello", "info")
        execution = manager.get(exec_id)
        step1 = next(s for s in execution.steps if s.name == "step1")
        assert step1.status == StepStatus.COMPLETED
        assert step1.phase == "Phase"
        assert [(log.message, log.level) for log in execution.logs] == [("hello", "info")]

    def test_complete_stores_result(self, manager, fake_task):
        name, _state, _ = fake_task
        exec_id = manager.create(name, {})
        manager.complete(exec_id, {"rows": 42})
        execution = manager.get(exec_id)
        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.result == {"rows": 42}
        assert execution.finished_at is not None

    def test_fail_stores_error(self, manager, fake_task):
        name, _state, _ = fake_task
        exec_id = manager.create(name, {})
        manager.fail(exec_id, "kaput")
        execution = manager.get(exec_id)
        assert execution.status == ExecutionStatus.FAILED
        assert execution.result == {"error": "kaput"}

    def test_cancel_sets_status(self, manager, fake_task):
        name, _state, _ = fake_task
        exec_id = manager.create(name, {})
        manager.cancel(exec_id)
        assert manager.get(exec_id).status == ExecutionStatus.CANCELLED


class TestDurability:
    def test_data_survives_reopen(self, temp_db, fake_task):
        name, _state, _ = fake_task
        mgr = ExecutionManager()
        exec_id = mgr.create(name, {"persist": True})
        mgr.add_log(exec_id, "before close", "warning")
        mgr.close()

        reopened = ExecutionManager()
        try:
            execution = reopened.get(exec_id)
            assert execution is not None
            assert execution.params == {"persist": True}
            assert execution.logs[0].message == "before close"
            # reopening a populated DB is a clean no-op migration (already at head)
            assert reopened._conn.execute("PRAGMA user_version").fetchone()[0] == _HEAD
        finally:
            reopened.close()


class TestCascadeDelete:
    def test_pruning_cascades_to_steps_logs_breakpoints(self, manager, fake_task, monkeypatch):
        import src.infrastructure.execution_manager as em

        name, _state, _ = fake_task
        monkeypatch.setattr(em, "MAX_EXECUTIONS", 2)

        ids = []
        for i in range(4):
            eid = manager.create(name, {"i": i})
            manager.add_log(eid, f"log {i}")
            manager.breakpoints.set(eid, "step1", True)
            ids.append(eid)

        # only the 2 newest survive
        surviving = {r["id"] for r in manager.list_all()}
        assert len(surviving) == 2
        assert ids[2] in surviving and ids[3] in surviving

        # pruned executions: rows gone + breakpoint cache dropped
        for old in (ids[0], ids[1]):
            assert manager.get(old) is None
            assert manager.breakpoints.has(old, "step1") is False
        # survivors keep their breakpoints
        assert manager.breakpoints.has(ids[3], "step1") is True

    def test_delete_execution_cascades_rows(self, manager, fake_task):
        name, _state, _ = fake_task
        exec_id = manager.create(name, {})
        manager.add_log(exec_id, "x")
        manager._conn.execute("DELETE FROM executions WHERE id=?", (exec_id,))
        manager._conn.commit()
        assert manager._conn.execute("SELECT COUNT(*) FROM steps WHERE execution_id=?", (exec_id,)).fetchone()[0] == 0
        assert manager._conn.execute("SELECT COUNT(*) FROM logs WHERE execution_id=?", (exec_id,)).fetchone()[0] == 0


class TestBreakpointStore:
    def test_set_has_list_unset(self, manager, fake_task):
        name, _state, _ = fake_task
        exec_id = manager.create(name, {})
        manager.breakpoints.set(exec_id, "step2", True)
        assert manager.breakpoints.has(exec_id, "step2")
        assert manager.breakpoints.list(exec_id) == ["step2"]
        manager.breakpoints.set(exec_id, "step2", False)
        assert not manager.breakpoints.has(exec_id, "step2")

    def test_breakpoints_persist_and_reload_into_cache(self, temp_db, fake_task):
        name, _state, _ = fake_task
        mgr = ExecutionManager()
        exec_id = mgr.create(name, {})
        mgr.breakpoints.set(exec_id, "step3", True)
        mgr.close()

        reopened = ExecutionManager()
        try:
            # BreakpointStore._load() rehydrates the cache from disk on construction
            assert reopened.breakpoints.has(exec_id, "step3")
        finally:
            reopened.close()


class TestConnectionConfig:
    def test_wal_mode(self, manager):
        mode = manager._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"

    def test_get_missing_returns_none(self, manager):
        assert manager.get("does-not-exist") is None

    def test_set_step_inserts_when_absent(self, manager, fake_task):
        name, _state, _ = fake_task
        exec_id = manager.create(name, {})
        manager.set_step(exec_id, "adhoc-step", "running")
        execution = manager.get(exec_id)
        assert any(s.name == "adhoc-step" for s in execution.steps)

    def test_invalid_status_value_rejected_by_enum(self, manager, fake_task):
        name, _state, _ = fake_task
        exec_id = manager.create(name, {})
        manager._conn.execute("UPDATE executions SET status='bogus' WHERE id=?", (exec_id,))
        manager._conn.commit()
        try:
            manager.get(exec_id)
            raise AssertionError("expected ValueError from ExecutionStatus enum")
        except ValueError:
            pass
        except sqlite3.Error:
            raise
