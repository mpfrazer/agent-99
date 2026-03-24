"""JWT authentication: endpoints and FastAPI dependency."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from jose import JWTError, jwt
from pydantic import BaseModel

from api.app_config import get_secret_key, has_password, set_password, verify_password

ALGORITHM = "HS256"
COOKIE_NAME = "agent99_session"
FLAG_COOKIE = "agent99_logged_in"
EXPIRE_DAYS = 30

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _create_token(secret: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=EXPIRE_DAYS)
    return jwt.encode({"sub": "user", "exp": exp}, secret, algorithm=ALGORITHM)


def _set_auth_cookies(response: Response, token: str) -> None:
    max_age = EXPIRE_DAYS * 24 * 3600
    response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=max_age, samesite="lax")
    response.set_cookie(FLAG_COOKIE, "1", httponly=False, max_age=max_age, samesite="lax")


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)
    response.delete_cookie(FLAG_COOKIE)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def require_auth(agent99_session: str | None = Cookie(default=None)) -> str:
    if not agent99_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(agent99_session, get_secret_key(), algorithms=[ALGORITHM])
        if payload.get("sub") != "user":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    password: str


class SetPasswordRequest(BaseModel):
    password: str


@router.post("/login")
def login(body: LoginRequest, response: Response):
    if not has_password():
        raise HTTPException(status_code=400, detail="No password set. Run install.py first.")
    if not verify_password(body.password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    token = _create_token(get_secret_key())
    _set_auth_cookies(response, token)
    return {"authenticated": True}


@router.post("/logout")
def logout(response: Response):
    _clear_auth_cookies(response)
    return {"authenticated": False}


@router.get("/me")
def me(user: str = Depends(require_auth)):
    return {"authenticated": True, "user": user}


@router.post("/password")
def change_password(body: SetPasswordRequest, user: str = Depends(require_auth)):
    if not body.password.strip():
        raise HTTPException(status_code=400, detail="Password must not be empty")
    set_password(body.password)
    return {"ok": True}
