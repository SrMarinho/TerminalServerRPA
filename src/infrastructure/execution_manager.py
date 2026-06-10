import sqlite3
import threading
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path

from src.config.settings import DB_PATH
from src.infrastructure.breakpoint_store import BreakpointStore
from src.infrastructure.execution_repository import ExecutionRepository
from src.infrastructure.models import Execution

MAX_EXECUTIONS = 100


def _broadcast_exec_event(event: dict) -> None:
    from src.infrastructure import events

    events.publish(event)


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
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
    """Orchestrates execution state: delegates DB to ExecutionRepository, publishes events."""

    def __init__(self):
        self._lock = threading.RLock()
        self._conn = _get_conn()
        self._repo = ExecutionRepository(self._conn, self._lock)
        self.breakpoints = BreakpointStore(self._conn, self._lock)

    def create(self, task_name: str, params: dict | None = None) -> str:
        exec_id = self._repo.create(task_name, params)
        surviving = self._repo.prune(MAX_EXECUTIONS)
        self.breakpoints.retain(surviving)
        _prune_diag()
        return exec_id

    def set_step(self, execution_id: str, step_name: str, status: str = "running") -> None:
        now = self._repo.set_step(execution_id, step_name, status)
        _broadcast_exec_event(
            {
                "type": "execution:step",
                "execution_id": execution_id,
                "name": step_name,
                "status": status,
                "timestamp": now,
                "phase": self._repo.get_step_phase(execution_id, step_name),
            }
        )

    def complete(self, execution_id: str, result: dict | None = None) -> None:
        self._repo.complete(execution_id, result)
        _broadcast_exec_event(
            {
                "type": "execution:status",
                "execution_id": execution_id,
                "status": "completed",
                "result": result,
            }
        )

    def fail(self, execution_id: str, error: str | None = None) -> None:
        self._repo.fail(execution_id, error)
        _broadcast_exec_event(
            {
                "type": "execution:status",
                "execution_id": execution_id,
                "status": "failed",
                "error": error,
            }
        )

    def cancel(self, execution_id: str) -> None:
        self._repo.cancel(execution_id)
        _broadcast_exec_event(
            {
                "type": "execution:status",
                "execution_id": execution_id,
                "status": "cancelled",
            }
        )

    def set_status(self, execution_id: str, status: str) -> None:
        self._repo.set_status(execution_id, status)

    def add_log(self, execution_id: str, message: str, level: str = "info") -> None:
        now = self._repo.add_log(execution_id, message, level)
        _broadcast_exec_event(
            {
                "type": "execution:log",
                "execution_id": execution_id,
                "message": message,
                "level": level,
                "timestamp": now,
            }
        )

    def update_step_status(self, execution_id: str, name: str, status: str) -> None:
        now = self._repo.update_step_status(execution_id, name, status)
        _broadcast_exec_event(
            {
                "type": "execution:step",
                "execution_id": execution_id,
                "name": name,
                "status": status,
                "timestamp": now,
                "phase": self._repo.get_step_phase(execution_id, name),
            }
        )

    def get(self, execution_id: str) -> Execution | None:
        return self._repo.get(execution_id)

    def list_all(self, limit: int = 50) -> list[dict]:
        return self._repo.list_all(limit)

    def close(self) -> None:
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


def get_manager() -> ExecutionManager:
    global _manager
    if _manager is None:
        _manager = ExecutionManager()
    return _manager


def close_manager() -> None:
    global _manager
    if _manager is not None:
        _manager.close()
        _manager = None


def set_breakpoint(execution_id: str, step: str, enabled: bool) -> None:
    get_manager().breakpoints.set(execution_id, step, enabled)


def has_breakpoint(execution_id: str, step: str) -> bool:
    return get_manager().breakpoints.has(execution_id, step)


def get_breakpoints(execution_id: str) -> list[str]:
    return get_manager().breakpoints.list(execution_id)
