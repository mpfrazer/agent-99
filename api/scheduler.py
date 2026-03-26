"""Background scheduler: polls active schedules and fires due agent runs."""

import asyncio
import logging
from datetime import datetime, timedelta

from api.schedules_db import get_due_schedules, update_next_run
from api.scheduler_logic import (
    compute_next_run,
    interval_to_timedelta,
)

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30


def _schedule_interval(schedule: dict) -> timedelta:
    """Return the timedelta for a schedule row, regardless of mode."""
    if schedule["mode"] == "interval":
        return interval_to_timedelta(schedule["interval_value"], schedule["interval_unit"])
    # daily mode
    return timedelta(days=schedule["every_n_days"])


async def _fire_schedule(schedule: dict, now: datetime) -> None:
    """Trigger a single due schedule and update its next_run."""
    from api.runs import start_run_internal

    await start_run_internal(
        agent_name=schedule["agent_name"],
        user_input=schedule["prompt"],
        trigger="scheduled",
        schedule_id=schedule["id"],
    )
    interval = _schedule_interval(schedule)
    anchor = datetime.fromisoformat(schedule["anchor"])
    next_run = compute_next_run(anchor, interval, now)
    update_next_run(schedule["id"], next_run.isoformat())


async def check_and_fire(now: datetime | None = None) -> int:
    """Check for due schedules and fire them.  Returns the count fired.

    Exposed as a standalone coroutine so tests can call it directly.
    """
    if now is None:
        now = datetime.now()

    due = get_due_schedules(now)
    fired = 0
    for schedule in due:
        try:
            await _fire_schedule(schedule, now)
            fired += 1
        except Exception:
            logger.exception("Failed to fire schedule %s", schedule["id"])
    return fired


async def scheduler_loop() -> None:  # pragma: no cover
    """Run forever, polling for due schedules every POLL_INTERVAL_SECONDS seconds."""
    logger.info("Scheduler started (poll interval: %ds)", POLL_INTERVAL_SECONDS)
    while True:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        try:
            fired = await check_and_fire()
            if fired:
                logger.info("Scheduler fired %d schedule(s)", fired)
        except Exception:
            logger.exception("Unexpected scheduler error")
