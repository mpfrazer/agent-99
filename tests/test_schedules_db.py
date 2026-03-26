"""Tests for api/schedules_db.py — SQLite CRUD layer."""

import pytest
from datetime import datetime
from pathlib import Path

from api.schedules_db import (
    create_schedule,
    delete_schedule,
    get_due_schedules,
    get_schedule,
    init_db,
    list_schedules,
    toggle_schedule,
    update_next_run,
    update_schedule,
)


@pytest.fixture(autouse=True)
def isolate_db(tmp_path: Path, monkeypatch):
    """Redirect the schedules DB to a temporary file for each test."""
    import api.app_config as ac

    cfg_dir = tmp_path / ".agent99"
    cfg_dir.mkdir()
    monkeypatch.setattr(ac, "_CONFIG_DIR", cfg_dir)
    init_db()


def _row(
    id_="sched-1",
    agent_name="my-agent",
    prompt="Do something",
    mode="interval",
    interval_value=30,
    interval_unit="minutes",
    daily_time=None,
    every_n_days=None,
    active=1,
    created_at="2024-01-15T10:00:00",
    anchor="2024-01-15T10:00:00",
    next_run="2024-01-15T10:30:00",
) -> dict:
    return dict(
        id=id_,
        agent_name=agent_name,
        prompt=prompt,
        mode=mode,
        interval_value=interval_value,
        interval_unit=interval_unit,
        daily_time=daily_time,
        every_n_days=every_n_days,
        active=active,
        created_at=created_at,
        anchor=anchor,
        next_run=next_run,
    )


# ---------------------------------------------------------------------------
# create / get
# ---------------------------------------------------------------------------


def test_create_and_get():
    row = _row()
    create_schedule(row)
    result = get_schedule("sched-1")
    assert result is not None
    assert result["agent_name"] == "my-agent"
    assert result["mode"] == "interval"
    assert result["interval_value"] == 30


def test_get_nonexistent():
    assert get_schedule("no-such-id") is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_list_empty():
    assert list_schedules() == []


def test_list_multiple_ordered_newest_first():
    create_schedule(_row(id_="s1", created_at="2024-01-15T10:00:00"))
    create_schedule(_row(id_="s2", created_at="2024-01-16T10:00:00"))
    result = list_schedules()
    assert [r["id"] for r in result] == ["s2", "s1"]


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_update_schedule():
    create_schedule(_row())
    update_schedule("sched-1", {"prompt": "New prompt", "interval_value": 60})
    updated = get_schedule("sched-1")
    assert updated["prompt"] == "New prompt"
    assert updated["interval_value"] == 60
    # Other fields untouched
    assert updated["interval_unit"] == "minutes"


# ---------------------------------------------------------------------------
# toggle
# ---------------------------------------------------------------------------


def test_toggle_active_to_paused():
    create_schedule(_row(active=1))
    result = toggle_schedule("sched-1")
    assert result is not None
    assert result["active"] == 0


def test_toggle_paused_to_active():
    create_schedule(_row(active=0))
    result = toggle_schedule("sched-1")
    assert result is not None
    assert result["active"] == 1


def test_toggle_nonexistent():
    assert toggle_schedule("no-such-id") is None


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_existing():
    create_schedule(_row())
    assert delete_schedule("sched-1") is True
    assert get_schedule("sched-1") is None


def test_delete_nonexistent():
    assert delete_schedule("no-such-id") is False


# ---------------------------------------------------------------------------
# get_due_schedules
# ---------------------------------------------------------------------------


def test_due_schedules_returns_overdue():
    create_schedule(_row(next_run="2024-01-15T09:00:00"))
    now = datetime(2024, 1, 15, 10, 0, 0)
    due = get_due_schedules(now)
    assert len(due) == 1
    assert due[0]["id"] == "sched-1"


def test_due_schedules_exact_boundary():
    """next_run == now should be included."""
    create_schedule(_row(next_run="2024-01-15T10:00:00"))
    now = datetime(2024, 1, 15, 10, 0, 0)
    assert len(get_due_schedules(now)) == 1


def test_due_schedules_excludes_future():
    create_schedule(_row(next_run="2024-01-15T11:00:00"))
    now = datetime(2024, 1, 15, 10, 0, 0)
    assert get_due_schedules(now) == []


def test_due_schedules_excludes_inactive():
    create_schedule(_row(next_run="2024-01-15T09:00:00", active=0))
    now = datetime(2024, 1, 15, 10, 0, 0)
    assert get_due_schedules(now) == []


def test_due_schedules_mixed():
    create_schedule(_row(id_="s1", next_run="2024-01-15T09:00:00", active=1))
    create_schedule(_row(id_="s2", next_run="2024-01-15T09:00:00", active=0))
    create_schedule(_row(id_="s3", next_run="2024-01-15T11:00:00", active=1))
    now = datetime(2024, 1, 15, 10, 0, 0)
    due = get_due_schedules(now)
    assert len(due) == 1
    assert due[0]["id"] == "s1"


# ---------------------------------------------------------------------------
# update_next_run
# ---------------------------------------------------------------------------


def test_update_next_run():
    create_schedule(_row())
    update_next_run("sched-1", "2024-01-15T11:00:00")
    row = get_schedule("sched-1")
    assert row["next_run"] == "2024-01-15T11:00:00"
