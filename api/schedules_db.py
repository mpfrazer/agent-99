"""SQLite persistence for agent schedules."""

import sqlite3
from datetime import datetime

from api.app_config import schedules_db_path


def _connect() -> sqlite3.Connection:
    path = schedules_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create the schedules table if it does not already exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id              TEXT PRIMARY KEY,
                agent_name      TEXT NOT NULL,
                prompt          TEXT NOT NULL,
                mode            TEXT NOT NULL,
                interval_value  INTEGER,
                interval_unit   TEXT,
                daily_time      TEXT,
                every_n_days    INTEGER,
                active          INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT NOT NULL,
                anchor          TEXT NOT NULL,
                next_run        TEXT NOT NULL
            )
        """)
        conn.commit()


def create_schedule(schedule: dict) -> None:
    """Insert a new schedule row."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO schedules
                (id, agent_name, prompt, mode, interval_value, interval_unit,
                 daily_time, every_n_days, active, created_at, anchor, next_run)
            VALUES
                (:id, :agent_name, :prompt, :mode, :interval_value, :interval_unit,
                 :daily_time, :every_n_days, :active, :created_at, :anchor, :next_run)
            """,
            schedule,
        )
        conn.commit()


def get_schedule(schedule_id: str) -> dict | None:
    """Return the schedule row with *schedule_id*, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM schedules WHERE id = ?", (schedule_id,)
        ).fetchone()
        return dict(row) if row else None


def list_schedules() -> list[dict]:
    """Return all schedules ordered by creation time (newest first)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM schedules ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_schedule(schedule_id: str, fields: dict) -> None:
    """Update specific columns on an existing schedule."""
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    params = {**fields, "_id": schedule_id}
    with _connect() as conn:
        conn.execute(
            f"UPDATE schedules SET {set_clause} WHERE id = :_id", params
        )
        conn.commit()


def toggle_schedule(schedule_id: str) -> dict | None:
    """Flip the active flag on a schedule; return the updated row or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT active FROM schedules WHERE id = ?", (schedule_id,)
        ).fetchone()
        if not row:
            return None
        new_active = 0 if row["active"] else 1
        conn.execute(
            "UPDATE schedules SET active = ? WHERE id = ?",
            (new_active, schedule_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM schedules WHERE id = ?", (schedule_id,)
        ).fetchone()
        return dict(updated)


def delete_schedule(schedule_id: str) -> bool:
    """Delete a schedule; return True if a row was removed."""
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM schedules WHERE id = ?", (schedule_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_due_schedules(now: datetime) -> list[dict]:
    """Return active schedules whose next_run is on or before *now*."""
    now_str = now.isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM schedules WHERE active = 1 AND next_run <= ?",
            (now_str,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_next_run(schedule_id: str, next_run: str) -> None:
    """Persist the recomputed next_run ISO string for a schedule."""
    with _connect() as conn:
        conn.execute(
            "UPDATE schedules SET next_run = ? WHERE id = ?",
            (next_run, schedule_id),
        )
        conn.commit()
