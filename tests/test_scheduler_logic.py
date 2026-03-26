"""Tests for api/scheduler_logic.py — pure scheduling functions."""

import pytest
from datetime import datetime, timedelta

from api.scheduler_logic import (
    compute_anchor_daily,
    compute_anchor_interval,
    compute_next_run,
    interval_to_timedelta,
)


# ---------------------------------------------------------------------------
# interval_to_timedelta
# ---------------------------------------------------------------------------


def test_interval_minutes():
    assert interval_to_timedelta(30, "minutes") == timedelta(minutes=30)


def test_interval_hours():
    assert interval_to_timedelta(2, "hours") == timedelta(hours=2)


def test_interval_days():
    assert interval_to_timedelta(7, "days") == timedelta(days=7)


def test_interval_unknown_unit():
    with pytest.raises(ValueError, match="Unknown interval unit"):
        interval_to_timedelta(5, "weeks")


# ---------------------------------------------------------------------------
# compute_anchor_interval
# ---------------------------------------------------------------------------


def test_compute_anchor_interval_returns_now():
    now = datetime(2024, 1, 15, 12, 0, 0)
    assert compute_anchor_interval(now) == now


# ---------------------------------------------------------------------------
# compute_anchor_daily
# ---------------------------------------------------------------------------


def test_compute_anchor_daily_future_today():
    """If the target time is still ahead today, anchor is today at that time."""
    now = datetime(2024, 1, 15, 8, 0, 0)
    anchor = compute_anchor_daily(now, "09:00")
    assert anchor == datetime(2024, 1, 15, 9, 0, 0)


def test_compute_anchor_daily_past_today():
    """If the target time has passed today, anchor moves to tomorrow."""
    now = datetime(2024, 1, 15, 10, 0, 0)
    anchor = compute_anchor_daily(now, "09:00")
    assert anchor == datetime(2024, 1, 16, 9, 0, 0)


def test_compute_anchor_daily_exact_now():
    """If now == target time, it is NOT strictly in the future → moves to tomorrow."""
    now = datetime(2024, 1, 15, 9, 0, 0)
    anchor = compute_anchor_daily(now, "09:00")
    assert anchor == datetime(2024, 1, 16, 9, 0, 0)


def test_compute_anchor_daily_midnight():
    now = datetime(2024, 1, 15, 23, 59, 0)
    anchor = compute_anchor_daily(now, "00:00")
    assert anchor == datetime(2024, 1, 16, 0, 0, 0)


def test_compute_anchor_daily_seconds_ignored():
    """Anchor always has second=0, microsecond=0 regardless of *now*."""
    now = datetime(2024, 1, 15, 8, 30, 45, 123456)
    anchor = compute_anchor_daily(now, "09:15")
    assert anchor.second == 0
    assert anchor.microsecond == 0


# ---------------------------------------------------------------------------
# compute_next_run
# ---------------------------------------------------------------------------


def test_compute_next_run_anchor_in_future():
    """If anchor hasn't been reached yet, return anchor (k=0 case)."""
    now = datetime(2024, 1, 15, 10, 0, 0)
    anchor = datetime(2024, 1, 15, 11, 0, 0)
    interval = timedelta(hours=1)
    assert compute_next_run(anchor, interval, now) == anchor


def test_compute_next_run_exactly_at_anchor():
    """anchor == now → not strictly future → k=1."""
    now = datetime(2024, 1, 15, 10, 0, 0)
    anchor = now
    interval = timedelta(hours=1)
    result = compute_next_run(anchor, interval, now)
    assert result == datetime(2024, 1, 15, 11, 0, 0)


def test_compute_next_run_one_interval_elapsed():
    now = datetime(2024, 1, 15, 11, 0, 0)
    anchor = datetime(2024, 1, 15, 10, 0, 0)
    interval = timedelta(hours=1)
    # elapsed = 1h = exactly 1 interval; k = floor(1)+1 = 2 → anchor + 2h
    result = compute_next_run(anchor, interval, now)
    assert result == datetime(2024, 1, 15, 12, 0, 0)


def test_compute_next_run_many_intervals_elapsed():
    """Simulates restarting after a long downtime (e.g. 2.5 intervals)."""
    now = datetime(2024, 1, 15, 12, 30, 0)
    anchor = datetime(2024, 1, 15, 10, 0, 0)
    interval = timedelta(hours=1)
    # elapsed = 2.5h → k = floor(2.5)+1 = 3 → anchor + 3h = 13:00
    result = compute_next_run(anchor, interval, now)
    assert result == datetime(2024, 1, 15, 13, 0, 0)


def test_compute_next_run_daily_mode():
    anchor = datetime(2024, 1, 10, 9, 0, 0)
    interval = timedelta(days=1)
    now = datetime(2024, 1, 14, 9, 0, 0)
    # elapsed = 4 days exactly → k = floor(4)+1 = 5 → anchor + 5d = Jan 15
    result = compute_next_run(anchor, interval, now)
    assert result == datetime(2024, 1, 15, 9, 0, 0)


def test_compute_next_run_preserves_cadence():
    """After downtime the schedule snaps to the original cadence, not from restart."""
    anchor = datetime(2024, 1, 1, 0, 0, 0)
    interval = timedelta(hours=24)
    # Server was down for 3.7 days
    now = datetime(2024, 1, 4, 16, 48, 0)
    result = compute_next_run(anchor, interval, now)
    # k = floor(3.7)+1 = 4 → anchor + 4 days = Jan 5 midnight
    assert result == datetime(2024, 1, 5, 0, 0, 0)
