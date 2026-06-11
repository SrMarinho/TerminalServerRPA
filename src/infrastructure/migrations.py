"""Versioned SQLite schema migrations via PRAGMA user_version.

Lightweight alternative to Alembic (no ORM, frozen-binary-safe). Each migration
is atomic; downgrades are supported by an additive-only discipline (never
DROP/RENAME), so an older app version no-ops on a newer schema.
"""

import shutil
import sqlite3
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from src.infrastructure.logger import get_logger

_log = get_logger("TerminalServerRPA.migrations")


@dataclass(frozen=True)
class Migration:
    target: int  # resulting user_version (1, 2, ...)
    statements: tuple[str, ...]


# NEVER reorder/edit a released migration; only append at the end.
# Forward-compatible discipline: additive only (ADD COLUMN nullable, new
# tables/indexes). Never DROP/RENAME — keeps an older app version (downgrade)
# working over a newer schema.
MIGRATIONS: tuple[Migration, ...] = (
    Migration(  # v0 -> v1: baseline (current full schema, phase inline)
        target=1,
        statements=(
            """CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                params TEXT DEFAULT '{}',
                result TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                timestamp TEXT NOT NULL,
                phase TEXT DEFAULT ''
            )""",
            """CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
                message TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'info',
                timestamp TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_steps_exec ON steps(execution_id)",
            "CREATE INDEX IF NOT EXISTS idx_logs_exec ON logs(execution_id)",
            "CREATE INDEX IF NOT EXISTS idx_exec_started ON executions(started_at DESC)",
            """CREATE TABLE IF NOT EXISTS breakpoints (
                execution_id TEXT NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
                step TEXT NOT NULL,
                PRIMARY KEY (execution_id, step)
            )""",
        ),
    ),
    Migration(  # v1 -> v2: task_configs moves under migration control
        # (was created ad-hoc by task_config.py; IF NOT EXISTS keeps field DBs safe)
        target=2,
        statements=(
            """CREATE TABLE IF NOT EXISTS task_configs (
                task_name TEXT PRIMARY KEY,
                params TEXT NOT NULL
            )""",
        ),
    ),
)


class Migrator:
    def __init__(self, conn: sqlite3.Connection, db_path: Path | None = None):
        self._conn = conn
        self._db_path = db_path

    def current_version(self) -> int:
        return self._conn.execute("PRAGMA user_version").fetchone()[0]

    def run(self) -> None:
        version = self.current_version()
        pending = [m for m in MIGRATIONS if m.target > version]
        if not pending:
            return  # already at head — no-op, no backup
        self._backup(version)
        for migration in pending:
            self._apply(migration)

    def _backup(self, version: int) -> None:
        # disaster rollback: restore the .bak. copy2 preserves metadata.
        if self._db_path and self._db_path.exists():
            with suppress(OSError):
                shutil.copy2(self._db_path, self._db_path.with_suffix(f".v{version}.bak"))

    def _apply(self, migration: Migration) -> None:
        # Explicit BEGIN: sqlite3's legacy isolation_level only auto-opens a
        # transaction before DML, not before DDL (CREATE/ALTER), so `with conn:`
        # would leave each CREATE in autocommit. Drive the transaction manually
        # to keep the whole migration atomic (all statements + user_version).
        try:
            self._conn.execute("BEGIN")
            for stmt in migration.statements:
                self._conn.execute(stmt)
            # user_version takes no bound parameter; target is an int from the
            # registry (no injection). The PRAGMA joins the transaction, so it
            # rises together with the schema.
            self._conn.execute(f"PRAGMA user_version = {migration.target}")
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            _log.error("migration.failed", target=migration.target)
            raise  # halts startup; the .bak preserves the prior state


def run_migrations(conn: sqlite3.Connection, db_path: Path | None = None) -> None:
    """Thin facade for the call-site (consistent with get_manager/set_breakpoint)."""
    Migrator(conn, db_path).run()
