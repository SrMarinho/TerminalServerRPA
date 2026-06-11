import json
import sqlite3
from contextlib import closing

from src.config.settings import DB_PATH as _DB_PATH
from src.infrastructure.migrations import run_migrations


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    # Schema lives in migrations.py; idempotent no-op when already at head.
    run_migrations(conn)
    return conn


def load_config(task_name: str) -> dict:
    # closing() releases the connection; sqlite3's `with conn` only commits.
    with closing(_conn()) as conn:
        row = conn.execute("SELECT params FROM task_configs WHERE task_name = ?", (task_name,)).fetchone()
    return json.loads(row[0]) if row else {}


def save_config(task_name: str, params: dict):
    with closing(_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO task_configs (task_name, params) VALUES (?, ?)"
            " ON CONFLICT(task_name) DO UPDATE SET params = excluded.params",
            (task_name, json.dumps(params, ensure_ascii=False)),
        )
