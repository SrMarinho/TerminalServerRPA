"""Pure SQLite CRUD for executions, steps, and logs.

No event publishing. No domain orchestration. Only data access.
"""

import json
import sqlite3
import threading
import uuid
from datetime import datetime

from src.infrastructure.models import Execution, ExecutionStatus, LogEntry, Step, StepStatus


class ExecutionRepository:
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        self._conn = conn
        self._lock = lock

    def create(self, task_name: str, params: dict | None = None) -> str:
        exec_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO executions (id, task_name, status, params, started_at) VALUES (?, ?, 'running', ?, ?)",
                (exec_id, task_name, json.dumps(params or {}), now),
            )
            for phase, step_name in self._get_task_steps(task_name):
                self._conn.execute(
                    "INSERT INTO steps (execution_id, name, phase, status, timestamp) VALUES (?, ?, ?, 'pending', ?)",
                    (exec_id, step_name, phase, now),
                )
            self._conn.commit()
        return exec_id

    @staticmethod
    def _get_task_steps(task_name: str) -> list[tuple[str, str]]:
        from src.infrastructure.task_registry import TaskRegistry

        TaskRegistry.auto_discover()
        task_cls = TaskRegistry.get(task_name)
        if not task_cls or not hasattr(task_cls, "get_steps"):
            return []
        steps = task_cls.get_steps()
        if isinstance(steps, dict):
            return [(phase, name) for phase, names in steps.items() for name in names]
        if isinstance(steps, list):
            return [("", name) for name in steps]
        return []

    def get(self, execution_id: str) -> Execution | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, task_name, status, params, result, started_at, finished_at FROM executions WHERE id=?",
                (execution_id,),
            ).fetchone()
            if row is None:
                return None
            params = json.loads(row["params"]) if row["params"] else {}
            result = json.loads(row["result"]) if row["result"] else None
            steps = [
                Step(
                    name=s["name"],
                    phase=s["phase"],
                    status=StepStatus(s["status"]),
                    timestamp=s["timestamp"],
                )
                for s in self._conn.execute(
                    "SELECT name, phase, status, timestamp FROM steps WHERE execution_id=? ORDER BY id",
                    (execution_id,),
                ).fetchall()
            ]
            logs = [
                LogEntry(
                    message=ln["message"],
                    level=ln["level"],
                    timestamp=ln["timestamp"],
                )
                for ln in self._conn.execute(
                    "SELECT message, level, timestamp FROM logs WHERE execution_id=? ORDER BY id",
                    (execution_id,),
                ).fetchall()
            ]
        return Execution(
            id=row["id"],
            task_name=row["task_name"],
            status=ExecutionStatus(row["status"]),
            params=params,
            result=result,
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            steps=steps,
            logs=logs,
        )

    def list_all(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, task_name, status, started_at, finished_at "
                "FROM executions ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def complete(self, execution_id: str, result: dict | None = None) -> str:
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE executions SET status='completed', finished_at=?, result=? WHERE id=?",
                (now, json.dumps(result), execution_id),
            )
            self._conn.commit()
        return now

    def fail(self, execution_id: str, error: str | None = None) -> str:
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE executions SET status='failed', finished_at=?, result=? WHERE id=?",
                (now, json.dumps({"error": error}) if error else "{}", execution_id),
            )
            self._conn.commit()
        return now

    def cancel(self, execution_id: str) -> str:
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE executions SET status='cancelled', finished_at=? WHERE id=?",
                (now, execution_id),
            )
            self._conn.commit()
        return now

    def set_status(self, execution_id: str, status: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE executions SET status=? WHERE id=?", (status, execution_id))
            self._conn.commit()

    def set_step(self, execution_id: str, step_name: str, status: str = "running") -> str:
        now = datetime.now().isoformat()
        with self._lock:
            updated = self._conn.execute(
                "UPDATE steps SET status=?, timestamp=? WHERE execution_id=? AND name=?",
                (status, now, execution_id, step_name),
            ).rowcount
            if updated == 0:
                self._conn.execute(
                    "INSERT INTO steps (execution_id, name, status, timestamp) VALUES (?, ?, ?, ?)",
                    (execution_id, step_name, status, now),
                )
            self._conn.commit()
        return now

    def update_step_status(self, execution_id: str, name: str, status: str) -> str:
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE steps SET status=?, timestamp=? WHERE execution_id=? AND name=? AND status='running'",
                (status, now, execution_id, name),
            )
            self._conn.commit()
        return now

    def get_step_phase(self, execution_id: str, name: str) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT phase FROM steps WHERE execution_id=? AND name=?", (execution_id, name)
            ).fetchone()
        return row["phase"] if row else ""

    def add_log(self, execution_id: str, message: str, level: str = "info") -> str:
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO logs (execution_id, message, level, timestamp) VALUES (?, ?, ?, ?)",
                (execution_id, message, level, now),
            )
            self._conn.commit()
        return now

    def prune(self, max_executions: int) -> set[str]:
        """Delete oldest executions beyond limit. Returns surviving IDs."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM executions WHERE id NOT IN (SELECT id FROM executions ORDER BY started_at DESC LIMIT ?)",
                (max_executions,),
            )
            self._conn.commit()
            surviving = {row[0] for row in self._conn.execute("SELECT id FROM executions").fetchall()}
        return surviving

    def close(self) -> None:
        self._conn.close()
