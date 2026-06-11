import sqlite3

import pytest

from src.infrastructure.migrations import MIGRATIONS, Migration, Migrator, run_migrations

_HEAD = len(MIGRATIONS)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r["name"] for r in rows}


class TestFreshDb:
    def test_version_rises_to_head(self, conn):
        run_migrations(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == _HEAD

    def test_baseline_tables_created(self, conn):
        run_migrations(conn)
        assert {"executions", "steps", "logs", "breakpoints", "task_configs"} <= _tables(conn)

    def test_steps_has_phase_column(self, conn):
        run_migrations(conn)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(steps)").fetchall()}
        assert "phase" in cols


class TestIdempotency:
    def test_rerun_is_noop(self, conn):
        run_migrations(conn)
        run_migrations(conn)  # must not raise / recreate
        assert conn.execute("PRAGMA user_version").fetchone()[0] == _HEAD

    def test_no_backup_when_at_head(self, tmp_path):
        db = tmp_path / "executions.db"
        c = sqlite3.connect(str(db))
        try:
            run_migrations(c, db)  # v0 -> head, writes .v0.bak only if file existed
            # second run is no-op: no new backup files for the head version
            before = set(tmp_path.iterdir())
            run_migrations(c, db)
            assert set(tmp_path.iterdir()) == before
        finally:
            c.close()


class TestExistingDb:
    def test_legacy_schema_at_version_zero_is_safe(self, conn):
        # Simulate a field DB: schema already present (IF NOT EXISTS style) but
        # user_version still 0. Baseline must no-op and bump to head.
        conn.executescript(
            "CREATE TABLE executions (id TEXT PRIMARY KEY, task_name TEXT NOT NULL, "
            "status TEXT, params TEXT, result TEXT, started_at TEXT NOT NULL, finished_at TEXT);"
            "CREATE TABLE steps (id INTEGER PRIMARY KEY AUTOINCREMENT, execution_id TEXT, "
            "name TEXT NOT NULL, status TEXT, timestamp TEXT NOT NULL, phase TEXT DEFAULT '');"
        )
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        run_migrations(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == _HEAD


class TestAtomicRollback:
    def test_invalid_statement_rolls_back_version(self, conn, monkeypatch):
        bad = (Migration(target=1, statements=("CREATE TABLE ok (id INTEGER)", "THIS IS NOT SQL")),)
        monkeypatch.setattr("src.infrastructure.migrations.MIGRATIONS", bad)
        with pytest.raises(sqlite3.OperationalError):
            Migrator(conn).run()
        # version unchanged and the partial table rolled back
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert "ok" not in _tables(conn)
