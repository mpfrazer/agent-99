"""CRUD endpoints and toggle for agent schedules."""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator, model_validator

from api.auth import require_auth
from api.schedules_db import (
    create_schedule,
    delete_schedule,
    get_schedule,
    list_schedules,
    toggle_schedule,
    update_next_run,
    update_schedule,
)
from api.scheduler_logic import (
    compute_anchor_daily,
    compute_anchor_interval,
    compute_next_run,
    interval_to_timedelta,
)

router = APIRouter(prefix="/schedules", tags=["schedules"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SchedulePayload(BaseModel):
    agent_name: str
    prompt: str
    mode: Literal["interval", "daily"]
    # interval mode
    interval_value: int | None = None
    interval_unit: Literal["minutes", "hours", "days"] | None = None
    # daily mode
    daily_time: str | None = None   # 'HH:MM'
    every_n_days: int | None = None

    @field_validator("agent_name")
    @classmethod
    def agent_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("agent_name must not be empty")
        return v

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt must not be empty")
        return v

    @field_validator("daily_time")
    @classmethod
    def validate_daily_time(cls, v: str | None) -> str | None:
        if v is None:
            return v
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("daily_time must be in HH:MM format")
        try:
            hour, minute = int(parts[0]), int(parts[1])
        except ValueError:
            raise ValueError("daily_time must be in HH:MM format")
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("daily_time hour must be 0-23 and minute 0-59")
        return f"{hour:02d}:{minute:02d}"

    @model_validator(mode="after")
    def check_mode_fields(self) -> "SchedulePayload":
        if self.mode == "interval":
            if self.interval_value is None or self.interval_value < 1:
                raise ValueError("interval_value must be a positive integer for interval mode")
            if self.interval_unit is None:
                raise ValueError("interval_unit is required for interval mode")
        else:  # daily
            if self.daily_time is None:
                raise ValueError("daily_time is required for daily mode")
            if self.every_n_days is None or self.every_n_days < 1:
                raise ValueError("every_n_days must be a positive integer for daily mode")
        return self


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_schedule_row(payload: SchedulePayload, now: datetime) -> dict:
    """Compute anchor + next_run and return the full DB row dict."""
    if payload.mode == "interval":
        anchor = compute_anchor_interval(now)
        interval = interval_to_timedelta(payload.interval_value, payload.interval_unit)  # type: ignore[arg-type]
    else:
        anchor = compute_anchor_daily(now, payload.daily_time)  # type: ignore[arg-type]
        from datetime import timedelta
        interval = timedelta(days=payload.every_n_days)  # type: ignore[arg-type]

    # First execution is one interval after anchor (or at anchor for daily)
    next_run = compute_next_run(anchor, interval, now)

    return {
        "id": str(uuid.uuid4()),
        "agent_name": payload.agent_name,
        "prompt": payload.prompt,
        "mode": payload.mode,
        "interval_value": payload.interval_value,
        "interval_unit": payload.interval_unit,
        "daily_time": payload.daily_time,
        "every_n_days": payload.every_n_days,
        "active": 1,
        "created_at": now.isoformat(),
        "anchor": anchor.isoformat(),
        "next_run": next_run.isoformat(),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
def list_all(user: str = Depends(require_auth)):
    """List all schedules."""
    return list_schedules()


@router.post("")
def create(payload: SchedulePayload, user: str = Depends(require_auth)):
    """Create a new schedule."""
    row = _build_schedule_row(payload, datetime.now())
    create_schedule(row)
    return row


@router.get("/{schedule_id}")
def get_one(schedule_id: str, user: str = Depends(require_auth)):
    """Get a single schedule by ID."""
    row = get_schedule(schedule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return row


@router.put("/{schedule_id}")
def update_one(schedule_id: str, payload: SchedulePayload, user: str = Depends(require_auth)):
    """Update a schedule, recomputing anchor and next_run."""
    if not get_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    now = datetime.now()
    row = _build_schedule_row(payload, now)
    fields = {k: v for k, v in row.items() if k not in ("id", "created_at")}
    update_schedule(schedule_id, fields)
    return get_schedule(schedule_id)


@router.patch("/{schedule_id}/toggle")
def toggle_one(schedule_id: str, user: str = Depends(require_auth)):
    """Toggle a schedule between active and paused."""
    row = toggle_schedule(schedule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return row


@router.delete("/{schedule_id}")
def delete_one(schedule_id: str, user: str = Depends(require_auth)):
    """Delete a schedule permanently."""
    if not delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"deleted": schedule_id}
