"""Recurring task schedules: SQLite-persisted cron entries driving the TaskPool.

APScheduler (AsyncIOScheduler) runs in the server's event loop; each enabled
schedule row becomes one cron job. Firing a job starts the task — or queues it
if the single execution slot is busy. CLI mode never instantiates this.
"""

import json
import sqlite3
from contextlib import closing
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import DB_PATH
from src.infrastructure.logger import get_logger
from src.infrastructure.migrations import run_migrations

_log = get_logger("TerminalServerRPA.scheduler")


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    return conn


class ScheduleManager:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Load persisted schedules and start firing. Call from the server lifespan."""
        self._scheduler.start()
        for row in self.list_all():
            if row["enabled"]:
                self._add_job(row["id"], row["task_name"], row["cron"])
        _log.info("scheduler.started", jobs=len(self._scheduler.get_jobs()))

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    # -- CRUD (persisted) ----------------------------------------------------

    def create(self, task_name: str, cron: str) -> dict:
        CronTrigger.from_crontab(cron)  # validate early — raises ValueError on bad cron
        now = datetime.now().isoformat()
        with closing(_conn()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO schedules (task_name, cron, enabled, created_at) VALUES (?, ?, 1, ?)",
                (task_name, cron, now),
            )
            schedule_id = cur.lastrowid
        assert schedule_id is not None
        if self._scheduler.running:
            self._add_job(schedule_id, task_name, cron)
        _log.info("schedule.created", id=schedule_id, task=task_name, cron=cron)
        return {"id": schedule_id, "task_name": task_name, "cron": cron, "enabled": True}

    def delete(self, schedule_id: int) -> bool:
        with closing(_conn()) as conn, conn:
            deleted = conn.execute("DELETE FROM schedules WHERE id=?", (schedule_id,)).rowcount
        self._remove_job(schedule_id)
        return deleted > 0

    def set_enabled(self, schedule_id: int, enabled: bool) -> bool:
        with closing(_conn()) as conn, conn:
            updated = conn.execute(
                "UPDATE schedules SET enabled=? WHERE id=?", (1 if enabled else 0, schedule_id)
            ).rowcount
            row = conn.execute("SELECT task_name, cron FROM schedules WHERE id=?", (schedule_id,)).fetchone()
        if updated == 0 or row is None:
            return False
        if enabled and self._scheduler.running:
            self._add_job(schedule_id, row["task_name"], row["cron"])
        else:
            self._remove_job(schedule_id)
        return True

    def list_all(self) -> list[dict]:
        with closing(_conn()) as conn:
            rows = conn.execute(
                "SELECT id, task_name, cron, enabled, last_run, created_at FROM schedules ORDER BY id"
            ).fetchall()
        return [dict(r) | {"enabled": bool(r["enabled"])} for r in rows]

    # -- firing ----------------------------------------------------------------

    def _add_job(self, schedule_id: int, task_name: str, cron: str) -> None:
        self._scheduler.add_job(
            self._fire,
            CronTrigger.from_crontab(cron),
            args=[schedule_id, task_name],
            id=str(schedule_id),
            replace_existing=True,
        )

    def _remove_job(self, schedule_id: int) -> None:
        job = self._scheduler.get_job(str(schedule_id))
        if job is not None:
            job.remove()

    async def _fire(self, schedule_id: int, task_name: str) -> None:
        """Job callback: start (or queue) the task with its saved params. Never raises."""
        try:
            from src.infrastructure.task_config import load_config
            from src.infrastructure.task_runner import get_pool

            params = load_config(task_name) or None
            result = get_pool().start_or_enqueue(task_name, params)
            with closing(_conn()) as conn, conn:
                conn.execute(
                    "UPDATE schedules SET last_run=? WHERE id=?",
                    (datetime.now().isoformat(), schedule_id),
                )
            _log.info("schedule.fired", id=schedule_id, task=task_name, result=json.dumps(result))
        except Exception:
            _log.exception("schedule.fire_failed", id=schedule_id, task=task_name)


_manager: ScheduleManager | None = None


def get_schedule_manager() -> ScheduleManager:
    global _manager
    if _manager is None:
        _manager = ScheduleManager()
    return _manager
