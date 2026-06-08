import json
import sqlite3
import threading
import uuid
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path

from src.config.settings import DB_PATH
from src.infrastructure.models import Execution, ExecutionStatus, LogEntry, Step, StepStatus

MAX_EXECUTIONS = 100


def _broadcast_exec_event(event: dict):
    try:
        from src.interfaces.web.websocket import broadcast_event

        broadcast_event(event)
    except RuntimeError:
        from src.infrastructure.logger import get_logger

        get_logger("TerminalServerRPA.execution-manager").debug(
            "broadcast.no_loop", event_type=event.get("type", "unknown")
        )  # no event loop running (e.g., CLI mode)


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # NORMAL is the recommended durability level under WAL: it skips the fsync
    # on every commit (which would stall the asyncio loop on each log line) and
    # only syncs at checkpoints. The DB stays consistent across app crashes.
    conn.execute("PRAGMA synchronous=NORMAL")
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
        CREATE TABLE IF NOT EXISTS breakpoints (
            execution_id TEXT NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
            step TEXT NOT NULL,
            PRIMARY KEY (execution_id, step)
        );
    """)
    with suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE steps ADD COLUMN phase TEXT DEFAULT ''")


class ExecutionManager:
    def __init__(self):
        # The connection is shared with check_same_thread=False, but sqlite3
        # connections are not safe for concurrent use across threads. Serialize
        # every DB access through this lock (reentrant: create() calls _prune()).
        self._lock = threading.RLock()
        self._conn = _get_conn()

    def create(self, task_name: str, params: dict | None = None) -> str:
        exec_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with self._lock:
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
        _broadcast_exec_event(
            {
                "type": "execution:step",
                "execution_id": execution_id,
                "name": step_name,
                "status": status,
                "timestamp": now,
                "phase": self._get_step_phase(execution_id, step_name),
            }
        )

    def _get_step_phase(self, execution_id: str, name: str) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT phase FROM steps WHERE execution_id=? AND name=?", (execution_id, name)
            ).fetchone()
        return row["phase"] if row else ""

    def complete(self, execution_id: str, result: dict | None = None):
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE executions SET status='completed', finished_at=?, result=? WHERE id=?",
                (now, json.dumps(result), execution_id),
            )
            self._conn.commit()
        _broadcast_exec_event(
            {
                "type": "execution:status",
                "execution_id": execution_id,
                "status": "completed",
                "result": result,
            }
        )

    def fail(self, execution_id: str, error: str | None = None):
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE executions SET status='failed', finished_at=?, result=? WHERE id=?",
                (now, json.dumps({"error": error}) if error else "{}", execution_id),
            )
            self._conn.commit()
        _broadcast_exec_event(
            {
                "type": "execution:status",
                "execution_id": execution_id,
                "status": "failed",
                "error": error,
            }
        )

    def cancel(self, execution_id: str):
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE executions SET status='cancelled', finished_at=? WHERE id=?",
                (now, execution_id),
            )
            self._conn.commit()
        _broadcast_exec_event(
            {
                "type": "execution:status",
                "execution_id": execution_id,
                "status": "cancelled",
            }
        )

    def set_status(self, execution_id: str, status: str):
        with self._lock:
            self._conn.execute("UPDATE executions SET status=? WHERE id=?", (status, execution_id))
            self._conn.commit()

    def add_log(self, execution_id: str, message: str, level: str = "info"):
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO logs (execution_id, message, level, timestamp) VALUES (?, ?, ?, ?)",
                (execution_id, message, level, now),
            )
            self._conn.commit()
        _broadcast_exec_event(
            {
                "type": "execution:log",
                "execution_id": execution_id,
                "message": message,
                "level": level,
                "timestamp": now,
            }
        )

    def update_step_status(self, execution_id: str, name: str, status: str):
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE steps SET status=?, timestamp=? WHERE execution_id=? AND name=? AND status='running'",
                (status, now, execution_id, name),
            )
            self._conn.commit()
        _broadcast_exec_event(
            {
                "type": "execution:step",
                "execution_id": execution_id,
                "name": name,
                "status": status,
                "timestamp": now,
                "phase": self._get_step_phase(execution_id, name),
            }
        )

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

    def _prune(self):
        # Caller (create) already holds self._lock; RLock makes this reentrant.
        with self._lock:
            deleted = self._conn.execute(
                "DELETE FROM executions WHERE id NOT IN (SELECT id FROM executions ORDER BY started_at DESC LIMIT ?)",
                (MAX_EXECUTIONS,),
            ).rowcount
            self._conn.commit()
            if deleted:
                # sync breakpoint cache after cascade deletions
                surviving = {row[0] for row in self._conn.execute("SELECT id FROM executions").fetchall()}
                stale = [eid for eid in _breakpoints if eid not in surviving]
                for eid in stale:
                    del _breakpoints[eid]
        _prune_diag()

    def close(self):
        self._conn.close()


_DIAG_DIR = Path("logs/diag")
_DIAG_MAX_DAYS = 7


def _prune_diag() -> None:
    if not _DIAG_DIR.exists():
        return
    cutoff = datetime.now() - timedelta(days=_DIAG_MAX_DAYS)
    for f in _DIAG_DIR.iterdir():
        if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink(missing_ok=True)


_manager: ExecutionManager | None = None
_breakpoints: dict[str, set[str]] = {}  # execution_id -> set of step names (cache)


def _load_breakpoints(mgr: ExecutionManager):
    """Populate breakpoint cache from DB on first manager access."""
    with mgr._lock:
        rows = mgr._conn.execute("SELECT execution_id, step FROM breakpoints").fetchall()
    for exec_id, step in rows:
        _breakpoints.setdefault(exec_id, set()).add(step)


def get_manager() -> ExecutionManager:
    global _manager
    if _manager is None:
        _manager = ExecutionManager()
        _load_breakpoints(_manager)
    return _manager


def close_manager() -> None:
    """Close the singleton connection and reset it so the next access reopens."""
    global _manager
    if _manager is not None:
        _manager.close()
        _manager = None


def set_breakpoint(execution_id: str, step: str, enabled: bool) -> None:
    mgr = get_manager()
    with mgr._lock:
        if enabled:
            _breakpoints.setdefault(execution_id, set()).add(step)
            mgr._conn.execute(
                "INSERT OR IGNORE INTO breakpoints (execution_id, step) VALUES (?, ?)",
                (execution_id, step),
            )
        else:
            _breakpoints.get(execution_id, set()).discard(step)
            mgr._conn.execute(
                "DELETE FROM breakpoints WHERE execution_id = ? AND step = ?",
                (execution_id, step),
            )
        mgr._conn.commit()


def has_breakpoint(execution_id: str, step: str) -> bool:
    return step in _breakpoints.get(execution_id, set())


def get_breakpoints(execution_id: str) -> list[str]:
    return list(_breakpoints.get(execution_id, set()))
