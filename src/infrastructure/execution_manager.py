import json
import sqlite3
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

DB_DIR = Path(".local")
DB_PATH = DB_DIR / "executions.db"
MAX_EXECUTIONS = 100


def _broadcast_exec_event(event: dict):
    try:
        from src.interfaces.web.websocket import broadcast_event
        broadcast_event(event)
    except RuntimeError:
        pass  # no event loop running (e.g., CLI mode)


def _get_conn() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS executions (
            id TEXT PRIMARY KEY,
            task_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            params TEXT DEFAULT '{}',
            result TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT
        );
        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            timestamp TEXT NOT NULL,
            phase TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'info',
            timestamp TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_steps_exec ON steps(execution_id);
        CREATE INDEX IF NOT EXISTS idx_logs_exec ON logs(execution_id);
        CREATE INDEX IF NOT EXISTS idx_exec_started ON executions(started_at DESC);
    """)
    with suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE steps ADD COLUMN phase TEXT DEFAULT ''")


class ExecutionManager:
    def __init__(self):
        self._conn = _get_conn()

    def create(self, task_name: str, params: dict | None = None) -> str:
        exec_id = str(uuid.uuid4())[:8]
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "INSERT INTO executions (id, task_name, status, params, started_at) VALUES (?, ?, 'running', ?, ?)",
            (exec_id, task_name, json.dumps(params or {}), now),
        )
        steps = self._get_task_steps(task_name)
        for phase, step_name in steps:
            self._conn.execute(
                "INSERT INTO steps (execution_id, name, phase, status, timestamp) VALUES (?, ?, ?, 'pending', ?)",
                (exec_id, step_name, phase, now),
            )
        self._conn.commit()
        self._prune()
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

    def set_step(self, execution_id: str, step_name: str, status: str = "running"):
        now = datetime.now(UTC).isoformat()
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
        _broadcast_exec_event({
            "type": "execution:step",
            "execution_id": execution_id,
            "name": step_name,
            "status": status,
            "timestamp": now,
            "phase": self._get_step_phase(execution_id, step_name),
        })

    def _get_step_phase(self, execution_id: str, name: str) -> str:
        row = self._conn.execute(
            "SELECT phase FROM steps WHERE execution_id=? AND name=?", (execution_id, name)
        ).fetchone()
        return row["phase"] if row else ""

    def complete(self, execution_id: str, result: dict | None = None):
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "UPDATE executions SET status='completed', finished_at=?, result=? WHERE id=?",
            (now, json.dumps(result), execution_id),
        )
        self._conn.commit()
        _broadcast_exec_event({
            "type": "execution:status",
            "execution_id": execution_id,
            "status": "completed",
            "result": result,
        })

    def fail(self, execution_id: str, error: str | None = None):
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "UPDATE executions SET status='failed', finished_at=?, result=? WHERE id=?",
            (now, json.dumps({"error": error}) if error else "{}", execution_id),
        )
        self._conn.commit()
        _broadcast_exec_event({
            "type": "execution:status",
            "execution_id": execution_id,
            "status": "failed",
            "error": error,
        })

    def cancel(self, execution_id: str):
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "UPDATE executions SET status='cancelled', finished_at=? WHERE id=?",
            (now, execution_id),
        )
        self._conn.commit()
        _broadcast_exec_event({
            "type": "execution:status",
            "execution_id": execution_id,
            "status": "cancelled",
        })

    def add_log(self, execution_id: str, message: str, level: str = "info"):
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "INSERT INTO logs (execution_id, message, level, timestamp) VALUES (?, ?, ?, ?)",
            (execution_id, message, level, now),
        )
        self._conn.commit()
        _broadcast_exec_event({
            "type": "execution:log",
            "execution_id": execution_id,
            "message": message,
            "level": level,
            "timestamp": now,
        })

    def update_step_status(self, execution_id: str, name: str, status: str):
        self._conn.execute(
            "UPDATE steps SET status=? WHERE execution_id=? AND name=? AND status='running'",
            (status, execution_id, name),
        )
        self._conn.commit()

    def get(self, execution_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, task_name, status, params, result, started_at, finished_at FROM executions WHERE id=?",
            (execution_id,),
        ).fetchone()
        if row is None:
            return None
        entry = dict(row)
        entry["params"] = json.loads(entry["params"]) if entry["params"] else {}
        entry["result"] = json.loads(entry["result"]) if entry["result"] else None
        entry["steps"] = [
            dict(s) for s in self._conn.execute(
                "SELECT name, phase, status, timestamp FROM steps WHERE execution_id=? ORDER BY id",
                (execution_id,),
            ).fetchall()
        ]
        entry["logs"] = [
            dict(ln) for ln in self._conn.execute(
                "SELECT message, level, timestamp FROM logs WHERE execution_id=? ORDER BY id",
                (execution_id,),
            ).fetchall()
        ]
        return entry

    def list_all(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, task_name, status, started_at, finished_at FROM executions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _prune(self):
        self._conn.execute(
            "DELETE FROM executions WHERE id NOT IN (SELECT id FROM executions ORDER BY started_at DESC LIMIT ?)",
            (MAX_EXECUTIONS,),
        )
        self._conn.commit()

    def close(self):
        self._conn.close()


_manager = ExecutionManager()


def get_manager() -> ExecutionManager:
    return _manager
