from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

from core.event_bus import EventBus


class PersistentScheduler:
    """SQLite-backed scheduler that survives process restarts."""

    def __init__(self, event_bus: EventBus, db_path: str = ".black_memory/scheduler.db") -> None:
        self.event_bus = event_bus
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def register_job(self, name: str, interval_seconds: int, payload: Dict[str, Any] | None = None) -> None:
        next_run = datetime.now(timezone.utc) + timedelta(seconds=max(1, interval_seconds))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO scheduled_jobs(name, interval_seconds, next_run_at, payload_json, run_count)
                VALUES(?, ?, ?, ?, COALESCE((SELECT run_count FROM scheduled_jobs WHERE name = ?), 0))
                ON CONFLICT(name) DO UPDATE SET
                    interval_seconds = excluded.interval_seconds,
                    next_run_at = excluded.next_run_at,
                    payload_json = excluded.payload_json
                """,
                (name, interval_seconds, next_run.isoformat(), self._to_json(payload or {}), name),
            )
            conn.commit()
        self.event_bus.publish("scheduler.job.registered", {"name": name, "interval_seconds": interval_seconds})

    def run_due_jobs(self, callback: Callable[[Dict[str, Any]], Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        due_jobs = self._due_jobs(now)
        results: List[Dict[str, Any]] = []
        for job in due_jobs:
            self.event_bus.publish("scheduler.job.started", job)
            result = callback(job)
            self._mark_job_ran(job)
            summary = {"job": job, "result": result}
            results.append(summary)
            self.event_bus.publish("scheduler.job.completed", summary)
        return results

    def _due_jobs(self, now: datetime) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT name, interval_seconds, next_run_at, payload_json, run_count FROM scheduled_jobs WHERE next_run_at <= ?",
                (now.isoformat(),),
            ).fetchall()

        return [
            {
                "name": row[0],
                "interval_seconds": int(row[1]),
                "next_run_at": row[2],
                "payload": self._from_json(row[3]),
                "run_count": int(row[4]),
            }
            for row in rows
        ]

    def _mark_job_ran(self, job: Dict[str, Any]) -> None:
        next_run = datetime.now(timezone.utc) + timedelta(seconds=int(job["interval_seconds"]))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scheduled_jobs
                SET next_run_at = ?, run_count = run_count + 1, last_run_at = ?
                WHERE name = ?
                """,
                (next_run.isoformat(), datetime.now(timezone.utc).isoformat(), job["name"]),
            )
            conn.commit()

    def _initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_jobs(
                    name TEXT PRIMARY KEY,
                    interval_seconds INTEGER NOT NULL,
                    next_run_at TEXT NOT NULL,
                    last_run_at TEXT,
                    payload_json TEXT NOT NULL,
                    run_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()

    @staticmethod
    def _to_json(data: Dict[str, Any]) -> str:
        import json

        return json.dumps(data)

    @staticmethod
    def _from_json(data: str) -> Dict[str, Any]:
        import json

        return json.loads(data)
