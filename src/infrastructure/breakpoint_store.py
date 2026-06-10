"""Breakpoint persistence + in-memory cache.

Extracted from ExecutionManager: breakpoints are a distinct concern (which steps
should pause an execution) that happened to share the executions DB. The store
shares the manager's connection + lock but owns its own table and cache.
"""

import sqlite3
import threading


class BreakpointStore:
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        self._conn = conn
        self._lock = lock
        self._cache: dict[str, set[str]] = {}  # execution_id -> set of step names
        self._load()

    def _load(self) -> None:
        with self._lock:
            rows = self._conn.execute("SELECT execution_id, step FROM breakpoints").fetchall()
        for exec_id, step in rows:
            self._cache.setdefault(exec_id, set()).add(step)

    def set(self, execution_id: str, step: str, enabled: bool) -> None:
        with self._lock:
            if enabled:
                self._cache.setdefault(execution_id, set()).add(step)
                self._conn.execute(
                    "INSERT OR IGNORE INTO breakpoints (execution_id, step) VALUES (?, ?)",
                    (execution_id, step),
                )
            else:
                self._cache.get(execution_id, set()).discard(step)
                self._conn.execute(
                    "DELETE FROM breakpoints WHERE execution_id = ? AND step = ?",
                    (execution_id, step),
                )
            self._conn.commit()

    def has(self, execution_id: str, step: str) -> bool:
        return step in self._cache.get(execution_id, set())

    def list(self, execution_id: str) -> list[str]:
        return list(self._cache.get(execution_id, set()))

    def retain(self, surviving_ids: set[str]) -> None:
        """Drop cache entries for executions that no longer exist (after pruning)."""
        for eid in [e for e in self._cache if e not in surviving_ids]:
            del self._cache[eid]
