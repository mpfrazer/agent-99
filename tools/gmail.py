"""Gmail tools: read, send, label, and manage email via the Gmail API."""

import base64
from email.mime.text import MIMEText


def _get_service():
    """Build an authenticated Gmail API service, refreshing tokens if needed."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    # Import here to avoid circular dependency at module load time
    from api.app_config import get_gmail_client, get_gmail_tokens, save_gmail_tokens

    tokens = get_gmail_tokens()
    if not tokens:
        raise RuntimeError(
            "Gmail is not connected. Go to Settings and link your Gmail account first."
        )

    client = get_gmail_client()
    client_id, client_secret = client if client else ("", "")

    creds = Credentials(
        token=tokens["token"],
        refresh_token=tokens["refresh_token"],
        token_uri=tokens.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=client_id,
        client_secret=client_secret,
        scopes=tokens.get("scopes"),
    )

    service = build("gmail", "v1", credentials=creds)

    # Persist refreshed token if it changed
    if creds.token != tokens["token"]:
        save_gmail_tokens({
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "scopes": list(creds.scopes or []),
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        })

    return service


def _decode_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")
    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace") if data else ""
    if mime_type.startswith("multipart/"):
        for part in payload.get("parts", []):
            text = _decode_body(part)
            if text:
                return text
    return ""


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def list_emails(query: str = "in:inbox", max_results: int = 10) -> str:
    """Search Gmail and return a list of matching emails with id, subject, sender, and date.

    Args:
        query: Gmail search query, e.g. "is:unread", "from:boss@example.com", "subject:invoice".
        max_results: Maximum number of results to return (1-50).
    """
    service = _get_service()
    max_results = max(1, min(max_results, 50))
    result = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = result.get("messages", [])
    if not messages:
        return f"No emails found for query: {query!r}"

    lines = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()
        headers = detail.get("payload", {}).get("headers", [])
        lines.append(
            f"id={msg['id']}  from={_header(headers, 'From')!r}  "
            f"subject={_header(headers, 'Subject')!r}  date={_header(headers, 'Date')!r}"
        )
    return "\n".join(lines)


def get_email(message_id: str) -> str:
    """Retrieve the full content of an email by its message ID.

    Args:
        message_id: The Gmail message ID (from list_emails).
    """
    service = _get_service()
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    headers = msg.get("payload", {}).get("headers", [])
    body = _decode_body(msg.get("payload", {}))

    return (
        f"From: {_header(headers, 'From')}\n"
        f"To: {_header(headers, 'To')}\n"
        f"Subject: {_header(headers, 'Subject')}\n"
        f"Date: {_header(headers, 'Date')}\n"
        f"Thread-ID: {msg.get('threadId', '')}\n"
        f"\n{body.strip()}"
    )


def get_thread(thread_id: str) -> str:
    """Retrieve all messages in a Gmail thread, oldest first.

    Args:
        thread_id: The Gmail thread ID (visible in get_email output).
    """
    service = _get_service()
    thread = service.users().threads().get(
        userId="me", id=thread_id, format="full"
    ).execute()

    parts = []
    for i, msg in enumerate(thread.get("messages", []), 1):
        headers = msg.get("payload", {}).get("headers", [])
        body = _decode_body(msg.get("payload", {}))
        parts.append(
            f"--- Message {i} ---\n"
            f"From: {_header(headers, 'From')}\n"
            f"Date: {_header(headers, 'Date')}\n"
            f"{body.strip()}"
        )
    return "\n\n".join(parts) if parts else "Thread is empty."


def send_email(to: str, subject: str, body: str) -> str:
    """Send a new email.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
    """
    service = _get_service()
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Email sent to {to!r} with subject {subject!r}"


def reply_to_email(message_id: str, body: str) -> str:
    """Reply to an existing email thread.

    Args:
        message_id: The Gmail message ID to reply to.
        body: Plain-text reply body.
    """
    service = _get_service()
    original = service.users().messages().get(
        userId="me", id=message_id, format="metadata",
        metadataHeaders=["Subject", "From", "To", "Message-ID"]
    ).execute()

    headers = original.get("payload", {}).get("headers", [])
    reply_to = _header(headers, "From") or _header(headers, "To")
    subject = _header(headers, "Subject")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    thread_id = original.get("threadId", "")
    orig_message_id = _header(headers, "Message-ID")

    msg = MIMEText(body)
    msg["to"] = reply_to
    msg["subject"] = subject
    if orig_message_id:
        msg["In-Reply-To"] = orig_message_id
        msg["References"] = orig_message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(
        userId="me", body={"raw": raw, "threadId": thread_id}
    ).execute()
    return f"Reply sent to {reply_to!r}"


def create_draft(to: str, subject: str, body: str) -> str:
    """Create an email draft without sending it.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
    """
    service = _get_service()
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()
    return f"Draft created with id={draft['id']}"


def list_labels() -> str:
    """List all Gmail labels with their IDs and names."""
    service = _get_service()
    result = service.users().labels().list(userId="me").execute()
    labels = result.get("labels", [])
    if not labels:
        return "No labels found."
    return "\n".join(
        f"id={lb['id']}  name={lb['name']!r}"
        for lb in sorted(labels, key=lambda lb: lb["name"])
    )


def move_email(message_id: str, add_label: str, remove_label: str = "") -> str:
    """Apply or remove a label on an email (use label names, not IDs).

    Args:
        message_id: The Gmail message ID.
        add_label: Label name to apply, e.g. "INBOX", "STARRED", or a custom label name.
        remove_label: Label name to remove (optional).
    """
    service = _get_service()

    # Resolve label names to IDs
    all_labels = service.users().labels().list(userId="me").execute().get("labels", [])
    name_to_id = {lb["name"].lower(): lb["id"] for lb in all_labels}

    add_ids = []
    if add_label:
        lid = name_to_id.get(add_label.lower())
        if not lid:
            return f"Label {add_label!r} not found. Use list_labels to see available labels."
        add_ids.append(lid)

    remove_ids = []
    if remove_label:
        lid = name_to_id.get(remove_label.lower())
        if lid:
            remove_ids.append(lid)

    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": add_ids, "removeLabelIds": remove_ids},
    ).execute()

    parts = []
    if add_label:
        parts.append(f"added label {add_label!r}")
    if remove_label:
        parts.append(f"removed label {remove_label!r}")
    return f"Message {message_id}: {', '.join(parts)}"


def mark_read(message_id: str) -> str:
    """Mark an email as read.

    Args:
        message_id: The Gmail message ID.
    """
    service = _get_service()
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()
    return f"Message {message_id} marked as read."


def trash_email(message_id: str) -> str:
    """Move an email to the Trash.

    Args:
        message_id: The Gmail message ID.
    """
    service = _get_service()
    service.users().messages().trash(userId="me", id=message_id).execute()
    return f"Message {message_id} moved to Trash."
