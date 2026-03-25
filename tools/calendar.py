"""Google Calendar tools: list, create, edit, delete, and respond to events."""

from datetime import datetime, timedelta, timezone


def _get_service():
    """Build an authenticated Google Calendar API service, refreshing tokens if needed."""
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials

    from api.app_config import get_calendar_tokens, get_calendar_client, save_calendar_tokens

    tokens = get_calendar_tokens()
    if not tokens:
        raise RuntimeError(
            "Google Calendar is not connected. Go to Settings and link your Google account first."
        )

    client = get_calendar_client()
    client_id, client_secret = client if client else ("", "")

    creds = Credentials(
        token=tokens["token"],
        refresh_token=tokens["refresh_token"],
        token_uri=tokens.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=client_id,
        client_secret=client_secret,
        scopes=tokens.get("scopes"),
    )

    service = build("calendar", "v3", credentials=creds)

    if creds.token != tokens["token"]:
        save_calendar_tokens({
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "scopes": list(creds.scopes or []),
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        })

    return service


def _to_rfc3339(dt_str: str) -> str:
    """Normalize a datetime string to RFC 3339 with UTC offset."""
    dt_str = dt_str.strip()
    # Already has timezone info
    if "+" in dt_str or dt_str.endswith("Z"):
        return dt_str if dt_str.endswith("Z") else dt_str
    # Date only — treat as start of day UTC
    if len(dt_str) == 10:
        return f"{dt_str}T00:00:00Z"
    # Datetime without timezone — assume UTC
    return f"{dt_str}Z" if not dt_str.endswith("Z") else dt_str


def _format_event(event: dict) -> str:
    """Format a Calendar event dict as a readable string."""
    start = event.get("start", {})
    end = event.get("end", {})
    start_str = start.get("dateTime") or start.get("date", "")
    end_str = end.get("dateTime") or end.get("date", "")

    attendees = event.get("attendees", [])
    attendee_str = ", ".join(
        f"{a.get('email', '')} ({a.get('responseStatus', 'unknown')})"
        for a in attendees
    ) if attendees else "None"

    recurrence = event.get("recurrence", [])
    recurrence_str = "; ".join(recurrence) if recurrence else "None"

    return (
        f"id={event.get('id', '')}\n"
        f"  Title:       {event.get('summary', '(no title)')}\n"
        f"  Start:       {start_str}\n"
        f"  End:         {end_str}\n"
        f"  Location:    {event.get('location', 'None')}\n"
        f"  Description: {event.get('description', 'None')}\n"
        f"  Attendees:   {attendee_str}\n"
        f"  Recurrence:  {recurrence_str}\n"
        f"  Status:      {event.get('status', '')}\n"
        f"  Link:        {event.get('htmlLink', '')}"
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def list_calendars() -> str:
    """List all calendars in the connected Google account.

    Returns each calendar's ID, name, and access role.
    """
    service = _get_service()
    result = service.calendarList().list().execute()
    items = result.get("items", [])
    if not items:
        return "No calendars found."
    return "\n".join(
        f"id={c['id']!r}  name={c.get('summary', '')!r}  role={c.get('accessRole', '')}"
        for c in items
    )


def list_events(
    calendar_id: str = "primary",
    time_min: str = "",
    time_max: str = "",
    max_results: int = 10,
    query: str = "",
) -> str:
    """List events from a calendar within an optional date range.

    Args:
        calendar_id: Calendar ID (use "primary" for the main calendar).
        time_min: Start of date range, e.g. "2026-03-25" or "2026-03-25T09:00:00Z".
        time_max: End of date range, e.g. "2026-04-01".
        max_results: Maximum number of events to return (1–100).
        query: Free-text search query to filter events by title/description.
    """
    service = _get_service()
    now = datetime.now(timezone.utc).isoformat()

    params: dict = {
        "calendarId": calendar_id,
        "maxResults": max(1, min(max_results, 100)),
        "singleEvents": True,
        "orderBy": "startTime",
        "timeMin": _to_rfc3339(time_min) if time_min else now,
    }
    if time_max:
        params["timeMax"] = _to_rfc3339(time_max)
    if query:
        params["q"] = query

    result = service.events().list(**params).execute()
    events = result.get("items", [])
    if not events:
        return "No events found."
    return "\n\n".join(_format_event(e) for e in events)


def get_event(event_id: str, calendar_id: str = "primary") -> str:
    """Retrieve full details of a specific calendar event.

    Args:
        event_id: The event ID (from list_events output).
        calendar_id: Calendar ID containing the event (default: "primary").
    """
    service = _get_service()
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    return _format_event(event)


def create_event(
    title: str,
    start: str,
    end: str,
    calendar_id: str = "primary",
    description: str = "",
    location: str = "",
    attendees: str = "",
) -> str:
    """Create a new calendar event.

    Args:
        title: Event title/summary.
        start: Start datetime, e.g. "2026-03-25T14:00:00Z" or "2026-03-25".
        end: End datetime, e.g. "2026-03-25T15:00:00Z" or "2026-03-25".
        calendar_id: Calendar to add the event to (default: "primary").
        description: Optional event description or notes.
        location: Optional location string.
        attendees: Comma-separated list of attendee email addresses.
    """
    service = _get_service()

    # Determine if all-day (date) or timed (dateTime) event
    def _time_field(s: str) -> dict:
        s = s.strip()
        if len(s) == 10:
            return {"date": s}
        return {"dateTime": _to_rfc3339(s), "timeZone": "UTC"}

    body: dict = {
        "summary": title,
        "start": _time_field(start),
        "end": _time_field(end),
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if attendees:
        body["attendees"] = [
            {"email": e.strip()} for e in attendees.split(",") if e.strip()
        ]

    event = service.events().insert(calendarId=calendar_id, body=body, sendUpdates="all").execute()
    return f"Event created: id={event['id']!r}  link={event.get('htmlLink', '')}"


def update_event(
    event_id: str,
    calendar_id: str = "primary",
    title: str = "",
    start: str = "",
    end: str = "",
    description: str = "",
    location: str = "",
    attendees: str = "",
) -> str:
    """Update fields on an existing calendar event. Only provided fields are changed.

    Args:
        event_id: The event ID to update.
        calendar_id: Calendar ID containing the event (default: "primary").
        title: New event title (leave empty to keep current).
        start: New start datetime (leave empty to keep current).
        end: New end datetime (leave empty to keep current).
        description: New description (leave empty to keep current).
        location: New location (leave empty to keep current).
        attendees: Comma-separated attendee emails (leave empty to keep current).
    """
    service = _get_service()
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    if title:
        event["summary"] = title
    if description:
        event["description"] = description
    if location:
        event["location"] = location

    def _time_field(s: str) -> dict:
        s = s.strip()
        if len(s) == 10:
            return {"date": s}
        return {"dateTime": _to_rfc3339(s), "timeZone": "UTC"}

    if start:
        event["start"] = _time_field(start)
    if end:
        event["end"] = _time_field(end)
    if attendees:
        event["attendees"] = [
            {"email": e.strip()} for e in attendees.split(",") if e.strip()
        ]

    updated = service.events().update(
        calendarId=calendar_id, eventId=event_id, body=event, sendUpdates="all"
    ).execute()
    return f"Event updated: id={updated['id']!r}  link={updated.get('htmlLink', '')}"


def delete_event(event_id: str, calendar_id: str = "primary") -> str:
    """Delete a calendar event permanently.

    Args:
        event_id: The event ID to delete.
        calendar_id: Calendar ID containing the event (default: "primary").
    """
    service = _get_service()
    service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates="all").execute()
    return f"Event {event_id!r} deleted."


def respond_to_event(
    event_id: str,
    response: str,
    calendar_id: str = "primary",
) -> str:
    """RSVP to a calendar event invitation.

    Args:
        event_id: The event ID to respond to.
        response: Your response — one of "accepted", "declined", or "tentative".
        calendar_id: Calendar ID containing the event (default: "primary").
    """
    valid = {"accepted", "declined", "tentative"}
    if response not in valid:
        return f"Invalid response {response!r}. Must be one of: {', '.join(sorted(valid))}"

    service = _get_service()
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    # Find self in attendees and update response status
    attendees = event.get("attendees", [])
    me = service.calendars().get(calendarId="primary").execute().get("id", "")
    updated = False
    for attendee in attendees:
        if attendee.get("self") or attendee.get("email", "").lower() == me.lower():
            attendee["responseStatus"] = response
            updated = True
            break

    if not updated:
        return f"Could not find your attendance record on event {event_id!r}."

    event["attendees"] = attendees
    service.events().patch(
        calendarId=calendar_id, eventId=event_id,
        body={"attendees": attendees}, sendUpdates="all"
    ).execute()
    return f"RSVP for event {event_id!r} set to {response!r}."


def find_free_slots(
    date: str,
    duration_minutes: int = 60,
    calendar_id: str = "primary",
    start_hour: int = 9,
    end_hour: int = 18,
) -> str:
    """Find available time slots on a given day with no overlapping events.

    Args:
        date: The date to search, e.g. "2026-03-25".
        duration_minutes: Required slot duration in minutes (default 60).
        calendar_id: Calendar ID to check (default: "primary").
        start_hour: Earliest hour to consider (24h, default 9).
        end_hour: Latest hour to consider (24h, default 18).
    """
    service = _get_service()

    day_start = datetime.fromisoformat(f"{date}T{start_hour:02d}:00:00").replace(tzinfo=timezone.utc)
    day_end = datetime.fromisoformat(f"{date}T{end_hour:02d}:00:00").replace(tzinfo=timezone.utc)

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    busy = []
    for e in events:
        s = e.get("start", {})
        en = e.get("end", {})
        s_dt = datetime.fromisoformat((s.get("dateTime") or f"{s.get('date')}T00:00:00Z").replace("Z", "+00:00"))
        e_dt = datetime.fromisoformat((en.get("dateTime") or f"{en.get('date')}T23:59:59Z").replace("Z", "+00:00"))
        busy.append((s_dt, e_dt))

    slot_duration = timedelta(minutes=duration_minutes)
    free = []
    cursor = day_start

    for b_start, b_end in sorted(busy):
        if cursor + slot_duration <= b_start:
            free.append(f"  {cursor.strftime('%H:%M')} – {b_start.strftime('%H:%M')}")
        cursor = max(cursor, b_end)

    if cursor + slot_duration <= day_end:
        free.append(f"  {cursor.strftime('%H:%M')} – {day_end.strftime('%H:%M')}")

    if not free:
        return f"No free slots of {duration_minutes}+ minutes on {date}."
    return f"Free slots on {date} (≥{duration_minutes} min):\n" + "\n".join(free)


def create_recurring_event(
    title: str,
    start: str,
    end: str,
    recurrence: str,
    calendar_id: str = "primary",
    description: str = "",
    location: str = "",
) -> str:
    """Create a recurring calendar event using an RRULE.

    Args:
        title: Event title/summary.
        start: Start datetime of the first occurrence, e.g. "2026-03-25T14:00:00Z".
        end: End datetime of the first occurrence, e.g. "2026-03-25T15:00:00Z".
        recurrence: RRULE string, e.g. "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR" or
            "RRULE:FREQ=DAILY;COUNT=10" or "RRULE:FREQ=MONTHLY;UNTIL=20261231T000000Z".
        calendar_id: Calendar to add the event to (default: "primary").
        description: Optional event description.
        location: Optional location string.
    """
    service = _get_service()

    rrule = recurrence if recurrence.startswith("RRULE:") else f"RRULE:{recurrence}"

    def _time_field(s: str) -> dict:
        s = s.strip()
        if len(s) == 10:
            return {"date": s}
        return {"dateTime": _to_rfc3339(s), "timeZone": "UTC"}

    body: dict = {
        "summary": title,
        "start": _time_field(start),
        "end": _time_field(end),
        "recurrence": [rrule],
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location

    event = service.events().insert(calendarId=calendar_id, body=body).execute()
    return f"Recurring event created: id={event['id']!r}  link={event.get('htmlLink', '')}"


def get_upcoming_events(
    calendar_id: str = "primary",
    days_ahead: int = 7,
    max_results: int = 10,
) -> str:
    """Get upcoming calendar events for the next N days.

    Args:
        calendar_id: Calendar ID to query (default: "primary").
        days_ahead: Number of days to look ahead (default 7).
        max_results: Maximum number of events to return (default 10).
    """
    now = datetime.now(timezone.utc)
    until = now + timedelta(days=days_ahead)

    service = _get_service()
    result = service.events().list(
        calendarId=calendar_id,
        timeMin=now.isoformat(),
        timeMax=until.isoformat(),
        maxResults=max(1, min(max_results, 100)),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    if not events:
        return f"No upcoming events in the next {days_ahead} days."
    return "\n\n".join(_format_event(e) for e in events)
