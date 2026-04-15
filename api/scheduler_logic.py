"""Pure scheduling logic: interval resolution, anchor computation, next-run calculation.

All functions are side-effect-free and operate on plain datetime objects,
making them straightforward to unit-test without mocking.
"""

import math
from datetime import datetime, timedelta


def interval_to_timedelta(value: int, unit: str) -> timedelta:
    """Convert an interval_value + interval_unit pair to a timedelta.

    Args:
        value: Positive integer quantity.
        unit: One of 'minutes', 'hours', or 'days'.

    Raises:
        ValueError: If unit is not recognised.
    """
    if unit == "minutes":
        return timedelta(minutes=value)
    if unit == "hours":
        return timedelta(hours=value)
    if unit == "days":
        return timedelta(days=value)
    raise ValueError(f"Unknown interval unit: {unit!r}. Must be 'minutes', 'hours', or 'days'.")


def compute_anchor_interval(now: datetime) -> datetime:
    """Return the anchor for an interval-mode schedule.

    For interval mode the anchor is simply the creation instant; the first
    execution is one interval after that.
    """
    return now


def compute_anchor_daily(now: datetime, time_str: str) -> datetime:
    """Return the anchor (first run time) for a daily-mode schedule.

    The anchor is the next occurrence of *time_str* (HH:MM, local time)
    that is strictly in the future relative to *now*.  If that time has
    already passed today, the anchor falls on tomorrow.

    Args:
        now: The current local datetime.
        time_str: A 'HH:MM' string representing the desired time of day.
    """
    hour, minute = (int(x) for x in time_str.split(":"))
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def compute_next_run(anchor: datetime, interval: timedelta, now: datetime) -> datetime:
    """Return the next scheduled run time strictly after *now*.

    Computes the smallest value of  anchor + k * interval  that is
    strictly greater than *now*.  If the anchor is still in the future,
    the anchor itself is returned (k = 0 case).

    This formula ensures that after any period of downtime the scheduler
    snaps back onto the original cadence rather than drifting forward.

    Args:
        anchor: The datetime of the first scheduled execution.
        interval: The recurring interval between executions.
        now: The current datetime (typically datetime.now()).
    """
    if anchor > now:
        return anchor
    elapsed_seconds = (now - anchor).total_seconds()
    interval_seconds = interval.total_seconds()
    k = math.floor(elapsed_seconds / interval_seconds) + 1
    return anchor + k * interval
