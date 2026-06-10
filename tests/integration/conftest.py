"""Integration fixtures: real SQLite file + real event bus, no mocks.

Exercises the actual wiring (ExecutionManager -> ExecutionRepository +
BreakpointStore + migrations, event bus, TaskRunner/TaskPool) against a
temporary on-disk database.
"""

from collections.abc import Iterator

import pytest


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the execution manager at a throwaway DB file and reset the singleton.

    DB_PATH is read at call-time inside _get_conn()/run_migrations, so patching
    the module attribute is enough; resetting _manager forces get_manager() to
    rebuild on the temp path.
    """
    from src.infrastructure import execution_manager as em
    from src.infrastructure.task_registry import TaskRegistry

    db = tmp_path / "executions.db"
    monkeypatch.setattr(em, "DB_PATH", db)
    # Persistence tests target the DB, not discovery: skip the filesystem/plugin
    # scan so create() stays fast and deterministic.
    monkeypatch.setattr(TaskRegistry, "auto_discover", classmethod(lambda cls: None))
    em._manager = None
    yield db
    em.close_manager()


@pytest.fixture
def manager(temp_db):
    """A fresh ExecutionManager backed by the temp DB (closed on teardown)."""
    from src.infrastructure.execution_manager import ExecutionManager

    mgr = ExecutionManager()
    yield mgr
    mgr.close()


@pytest.fixture
def event_sink() -> Iterator[list[dict]]:
    """Collect every event published on the bus during the test."""
    from src.infrastructure import events

    captured: list[dict] = []
    events.subscribe(captured.append)
    yield captured
    events.unsubscribe(captured.append)


@pytest.fixture
def fake_task():
    """Register a controllable async task, unregister on teardown.

    The task reports each step (so breakpoints/steps are exercised) and supports
    an optional asyncio.Event gate to make pause/cancel timing deterministic.
    """
    import asyncio

    from src.infrastructure.task_registry import TaskRegistry
    from src.infrastructure.task_runner import SkipStep

    name = "itest-task"
    state: dict = {"gate": None, "raise_on": None, "ran_steps": [], "skipped": []}

    class FakeTask:
        def __init__(self, runner=None, vault=None):
            self._runner = runner

        @staticmethod
        def get_steps():
            return {"Phase": ["step1", "step2", "step3"]}

        async def execute(self, params: dict) -> dict:
            for step in ("step1", "step2", "step3"):
                try:
                    await self._runner.report_step(step)
                except SkipStep:
                    state["skipped"].append(step)
                    continue
                state["ran_steps"].append(step)
                self._runner.log(f"did {step}")
                if state["raise_on"] == step:
                    raise ValueError(f"boom at {step}")
                gate = state["gate"]
                if gate is not None:
                    await gate.wait()
            return {"ok": True, "params": params}

    TaskRegistry._tasks[name] = FakeTask
    TaskRegistry._discovered = True  # skip filesystem scan during create()
    yield name, state, asyncio
    TaskRegistry._tasks.pop(name, None)
