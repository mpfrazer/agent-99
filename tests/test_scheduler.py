"""Tests for api/scheduler.py — background scheduler logic."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from api.scheduler import _fire_schedule, _schedule_interval, check_and_fire


# ---------------------------------------------------------------------------
# _schedule_interval
# ---------------------------------------------------------------------------


def test_schedule_interval_interval_mode():
    schedule = {"mode": "interval", "interval_value": 30, "interval_unit": "minutes"}
    result = _schedule_interval(schedule)
    assert result == timedelta(minutes=30)


def test_schedule_interval_daily_mode():
    schedule = {"mode": "daily", "every_n_days": 3, "interval_value": None, "interval_unit": None}
    result = _schedule_interval(schedule)
    assert result == timedelta(days=3)


# ---------------------------------------------------------------------------
# _fire_schedule
# ---------------------------------------------------------------------------


def test_fire_schedule_calls_start_run_internal():
    schedule = {
        "id": "sched-1",
        "agent_name": "my-agent",
        "prompt": "Run now",
        "mode": "interval",
        "interval_value": 1,
        "interval_unit": "hours",
        "anchor": "2024-01-15T10:00:00",
    }
    now = datetime(2024, 1, 15, 11, 0, 0)

    mock_run = MagicMock()

    with patch("api.runs.start_run_internal", new=AsyncMock(return_value=mock_run)) as mock_start, \
         patch("api.scheduler.update_next_run") as mock_update:
        asyncio.run(_fire_schedule(schedule, now))

    mock_start.assert_called_once_with(
        agent_name="my-agent",
        user_input="Run now",
        trigger="scheduled",
        schedule_id="sched-1",
    )
    # anchor + 2 * 1h = 12:00
    mock_update.assert_called_once_with("sched-1", "2024-01-15T12:00:00")


def test_fire_schedule_daily_mode():
    schedule = {
        "id": "sched-2",
        "agent_name": "daily-agent",
        "prompt": "Daily",
        "mode": "daily",
        "every_n_days": 1,
        "interval_value": None,
        "interval_unit": None,
        "anchor": "2024-01-15T09:00:00",
    }
    now = datetime(2024, 1, 16, 9, 0, 0)

    mock_run = MagicMock()

    with patch("api.runs.start_run_internal", new=AsyncMock(return_value=mock_run)), \
         patch("api.scheduler.update_next_run") as mock_update:
        asyncio.run(_fire_schedule(schedule, now))

    # anchor + 2 * 1d = Jan 17
    mock_update.assert_called_once_with("sched-2", "2024-01-17T09:00:00")


# ---------------------------------------------------------------------------
# check_and_fire
# ---------------------------------------------------------------------------


def test_check_and_fire_no_due_schedules():
    with patch("api.scheduler.get_due_schedules", return_value=[]) as mock_due:
        now = datetime(2024, 1, 15, 10, 0, 0)
        count = asyncio.run(check_and_fire(now))
    assert count == 0
    mock_due.assert_called_once_with(now)


def test_check_and_fire_fires_due_schedules():
    schedules = [
        {
            "id": "s1",
            "agent_name": "a1",
            "prompt": "p1",
            "mode": "interval",
            "interval_value": 30,
            "interval_unit": "minutes",
            "anchor": "2024-01-15T09:00:00",
        },
        {
            "id": "s2",
            "agent_name": "a2",
            "prompt": "p2",
            "mode": "interval",
            "interval_value": 60,
            "interval_unit": "minutes",
            "anchor": "2024-01-15T09:00:00",
        },
    ]

    mock_run = MagicMock()

    with patch("api.scheduler.get_due_schedules", return_value=schedules), \
         patch("api.runs.start_run_internal", new=AsyncMock(return_value=mock_run)), \
         patch("api.scheduler.update_next_run"):
        now = datetime(2024, 1, 15, 10, 0, 0)
        count = asyncio.run(check_and_fire(now))

    assert count == 2


def test_check_and_fire_uses_current_time_by_default():
    """When called without *now*, it uses datetime.now() and doesn't crash."""
    with patch("api.scheduler.get_due_schedules", return_value=[]):
        count = asyncio.run(check_and_fire())
    assert count == 0


def test_check_and_fire_continues_after_error():
    """A failed schedule should not prevent subsequent ones from firing."""
    schedules = [
        {
            "id": "s1",
            "agent_name": "bad-agent",
            "prompt": "fail",
            "mode": "interval",
            "interval_value": 30,
            "interval_unit": "minutes",
            "anchor": "2024-01-15T09:00:00",
        },
        {
            "id": "s2",
            "agent_name": "good-agent",
            "prompt": "ok",
            "mode": "interval",
            "interval_value": 30,
            "interval_unit": "minutes",
            "anchor": "2024-01-15T09:00:00",
        },
    ]

    call_count = 0

    async def flaky_start(**kwargs):
        nonlocal call_count
        call_count += 1
        if kwargs["agent_name"] == "bad-agent":
            raise RuntimeError("agent config missing")
        return MagicMock()

    with patch("api.scheduler.get_due_schedules", return_value=schedules), \
         patch("api.runs.start_run_internal", new=AsyncMock(side_effect=flaky_start)), \
         patch("api.scheduler.update_next_run"):
        now = datetime(2024, 1, 15, 10, 0, 0)
        count = asyncio.run(check_and_fire(now))

    # Only the successful schedule is counted
    assert count == 1
    assert call_count == 2
