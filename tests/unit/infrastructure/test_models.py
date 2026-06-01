"""Unit tests for src/infrastructure/models.py."""

from src.infrastructure.models import (
    Breakpoint,
    Execution,
    ExecutionStatus,
    LogEntry,
    PoolEntry,
    Step,
    StepStatus,
    TaskInfo,
)


class TestEnums:
    def test_execution_status_values(self):
        assert ExecutionStatus.IDLE == "idle"
        assert ExecutionStatus.RUNNING == "running"
        assert ExecutionStatus.PAUSED == "paused"
        assert ExecutionStatus.COMPLETED == "completed"
        assert ExecutionStatus.FAILED == "failed"
        assert ExecutionStatus.CANCELLED == "cancelled"

    def test_step_status_values(self):
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.COMPLETED == "completed"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.CANCELLED == "cancelled"


class TestStep:
    def test_minimal(self):
        s = Step(name="login")
        assert s.name == "login"
        assert s.status == StepStatus.PENDING
        assert s.phase == ""

    def test_full(self):
        s = Step(name="download", status=StepStatus.RUNNING, phase="process", timestamp="2026-01-01T00:00:00")
        assert s.name == "download"
        assert s.status == StepStatus.RUNNING
        assert s.phase == "process"

    def test_dict_with_iso_timestamp(self):
        s = Step(name="test", timestamp="2026-06-01T10:00:00")
        d = s.dict_with_iso_timestamp()
        assert d["name"] == "test"
        assert d["timestamp"] == "2026-06-01T10:00:00"
        assert d["status"] == "pending"
        assert d["phase"] == ""

    def test_dict_with_auto_timestamp(self):
        s = Step(name="auto")
        d = s.dict_with_iso_timestamp()
        assert d["name"] == "auto"
        assert d["timestamp"] != ""  # auto-generated


class TestLogEntry:
    def test_minimal(self):
        log = LogEntry(message="started")
        assert log.message == "started"
        assert log.level == "info"

    def test_full(self):
        log = LogEntry(message="error!", level="error", timestamp="2026-01-01")
        assert log.level == "error"
        assert log.timestamp == "2026-01-01"


class TestBreakpoint:
    def test_fields(self):
        bp = Breakpoint(execution_id="abc123", step="login")
        assert bp.execution_id == "abc123"
        assert bp.step == "login"


class TestTaskInfo:
    def test_minimal(self):
        info = TaskInfo(name="relatorio")
        assert info.name == "relatorio"
        assert info.display_name == ""
        assert info.steps == {}
        assert info.schema_fields == []

    def test_full(self):
        info = TaskInfo(
            name="relatorio",
            display_name="Relatório Contas Receber",
            steps={"Login": ["step1"], "Processamento": ["step2"]},
            schema_fields=[{"name": "url", "type": "string"}],
        )
        assert info.display_name == "Relatório Contas Receber"
        assert len(info.steps["Login"]) == 1


class TestPoolEntry:
    def test_fields(self):
        entry = PoolEntry(task_id="abc", status=ExecutionStatus.RUNNING)
        assert entry.task_id == "abc"
        assert entry.status == ExecutionStatus.RUNNING
        assert entry.status.value == "running"


class TestExecution:
    def test_empty(self):
        exec_ = Execution()
        assert exec_.status == ExecutionStatus.IDLE
        assert exec_.steps == []
        assert exec_.logs == []
        assert exec_.params == {}

    def test_full(self):
        exec_ = Execution(
            id="abc123",
            task_name="Relatório Contas Receber",
            status=ExecutionStatus.COMPLETED,
            params={"url": "https://example.com"},
            result={"status": "ok"},
            started_at="2026-01-01T00:00:00",
            finished_at="2026-01-01T01:00:00",
            steps=[Step(name="login", status=StepStatus.COMPLETED)],
            logs=[LogEntry(message="done", level="info")],
        )
        assert exec_.id == "abc123"
        assert exec_.status == ExecutionStatus.COMPLETED
        assert len(exec_.steps) == 1
        assert exec_.steps[0].name == "login"
        assert exec_.result == {"status": "ok"}
        assert exec_.finished_at == "2026-01-01T01:00:00"

    def test_pydantic_serialization(self):
        """Execution should round-trip through model_dump() for FastAPI."""
        exec_ = Execution(
            id="x1",
            task_name="test",
            status=ExecutionStatus.RUNNING,
            steps=[Step(name="s1")],
        )
        dumped = exec_.model_dump(mode="json")
        assert dumped["id"] == "x1"
        assert dumped["status"] == "running"
        assert dumped["steps"][0]["name"] == "s1"
        assert dumped["steps"][0]["status"] == "pending"

    def test_list_of_executions_serializable(self):
        """FastAPI should be able to serialize list[Execution]."""
        exes = [
            Execution(id="a", task_name="t1", status=ExecutionStatus.COMPLETED),
            Execution(id="b", task_name="t2", status=ExecutionStatus.FAILED),
        ]
        dumped = [e.model_dump(mode="json") for e in exes]
        assert len(dumped) == 2
        assert dumped[0]["id"] == "a"
        assert dumped[1]["status"] == "failed"
