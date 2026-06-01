"""Shared typed models for the TerminalServerRPA domain.

These models live in infrastructure because they are primarily data-transfer
objects used across the infra layer (SQLite, runners) and interfaces (API,
CLI).  They are *not* a domain/entity layer — that would be `src/core/`, which
was removed by ADR-0003 as YAGNI.  If a shared business rule emerges across
multiple tasks, *then* a proper core layer should be recreated.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────


class ExecutionStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Value objects ────────────────────────────────────────────────────


class Step(BaseModel):
    """A single step within an execution."""

    name: str
    status: StepStatus = StepStatus.PENDING
    timestamp: str = ""
    phase: str = ""

    def dict_with_iso_timestamp(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "timestamp": self.timestamp or datetime.now().isoformat(),
            "phase": self.phase,
        }


class LogEntry(BaseModel):
    """A single log line attached to an execution."""

    message: str
    level: str = "info"
    timestamp: str = ""


class Breakpoint(BaseModel):
    """A pause-at-step marker for a running execution."""

    execution_id: str
    step: str


class TaskInfo(BaseModel):
    """Metadata about a registered task."""

    name: str
    display_name: str = ""
    steps: dict[str, list[str]] = Field(default_factory=dict)
    schema_fields: list[dict[str, Any]] = Field(default_factory=list)


class PoolEntry(BaseModel):
    """A runner's visible state in the pool."""

    task_id: str
    status: ExecutionStatus


# ── Aggregate ────────────────────────────────────────────────────────


class Execution(BaseModel):
    """Full execution record with steps and logs."""

    id: str = ""
    task_name: str = ""
    status: ExecutionStatus = ExecutionStatus.IDLE
    params: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    started_at: str = ""
    finished_at: str | None = None
    steps: list[Step] = Field(default_factory=list)
    logs: list[LogEntry] = Field(default_factory=list)
