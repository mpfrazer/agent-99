"""Gmail OAuth 2.0 endpoints: connect, callback, status, disconnect."""

import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from api.app_config import (
    clear_gmail_tokens,
    get_gmail_client,
    get_gmail_tokens,
    save_gmail_client,
    save_gmail_tokens,
)
from api.auth import require_auth

router = APIRouter(prefix="/gmail", tags=["gmail"])

_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

_API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
_WEB_BASE = os.environ.get("WEB_BASE_URL", "http://localhost:3000")
_REDIRECT_URI = f"{_API_BASE}/api/gmail/callback"

# In-memory CSRF state store  {state: True}
_pending_states: dict[str, bool] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_flow():
    from google_auth_oauthlib.flow import Flow

    creds = get_gmail_client()
    if not creds:
        raise HTTPException(status_code=400, detail="Gmail client credentials not configured. Save them in Settings first.")
    client_id, client_secret = creds
    return Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [_REDIRECT_URI],
            }
        },
        scopes=_SCOPES,
        redirect_uri=_REDIRECT_URI,
    )


def _credentials_to_dict(creds) -> dict:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "scopes": list(creds.scopes or []),
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CredentialsPayload(BaseModel):
    client_id: str
    client_secret: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/credentials")
def save_credentials(body: CredentialsPayload, user: str = Depends(require_auth)):
    """Store Google OAuth client ID and secret."""
    if not body.client_id.strip() or not body.client_secret.strip():
        raise HTTPException(status_code=400, detail="client_id and client_secret must not be empty")
    save_gmail_client(body.client_id.strip(), body.client_secret.strip())
    return {"ok": True}


@router.get("/auth-url")
def get_auth_url(user: str = Depends(require_auth)):
    """Generate and return the Google OAuth consent URL."""
    flow = _build_flow()
    state = secrets.token_urlsafe(32)
    _pending_states[state] = True
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return {"url": auth_url}


@router.get("/callback")
def oauth_callback(code: str, state: str, request: Request):
    """Handle Google OAuth redirect. Exchanges code for tokens, then redirects to /settings."""
    if state not in _pending_states:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    _pending_states.pop(state)

    flow = _build_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    save_gmail_tokens(_credentials_to_dict(creds))
    return RedirectResponse(url=f"{_WEB_BASE}/settings?gmail=connected")


@router.get("/status")
def gmail_status(user: str = Depends(require_auth)):
    """Return whether Gmail is connected and which account."""
    tokens = get_gmail_tokens()
    if not tokens:
        return {"connected": False, "email": None}

    # Try to retrieve the connected email address
    try:

        from google.oauth2.credentials import Credentials as GCreds
        from googleapiclient.discovery import build

        creds = GCreds(
            token=tokens["token"],
            refresh_token=tokens["refresh_token"],
            token_uri=tokens["token_uri"],
            client_id=(get_gmail_client() or ("", ""))[0],
            client_secret=(get_gmail_client() or ("", ""))[1],
            scopes=tokens.get("scopes"),
        )
        service = build("oauth2", "v2", credentials=creds)
        info = service.userinfo().get().execute()
        email = info.get("email")

        # Persist refreshed tokens if they changed
        if creds.token != tokens["token"]:
            save_gmail_tokens(_credentials_to_dict(creds))

        return {"connected": True, "email": email}
    except Exception:
        return {"connected": True, "email": None}


@router.delete("/disconnect")
def disconnect(user: str = Depends(require_auth)):
    """Remove all Gmail credentials and tokens."""
    clear_gmail_tokens()
    return {"ok": True}
