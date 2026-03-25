"""Load and save ~/.agent99/config.yaml (app-level config, not agent config)."""

import base64
import hashlib
import secrets
from pathlib import Path

import bcrypt
import yaml
from cryptography.fernet import Fernet, InvalidToken

_CONFIG_DIR = Path.home() / ".agent99"
_CONFIG_FILE = _CONFIG_DIR / "config.yaml"
_RUNS_DIR = _CONFIG_DIR / "runs"


def config_dir() -> Path:
    return _CONFIG_DIR


def runs_dir() -> Path:
    return _RUNS_DIR


def _defaults(secret_key: str) -> dict:
    return {
        "password_hash": None,
        "secret_key": secret_key,
        "runs_dir": str(_RUNS_DIR),
    }


def load_config() -> dict:
    """Load ~/.agent99/config.yaml, creating defaults if missing."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)

    if not _CONFIG_FILE.exists():
        cfg = _defaults(secrets.token_hex(32))
        _CONFIG_FILE.write_text(yaml.safe_dump(cfg))
        return cfg

    return yaml.safe_load(_CONFIG_FILE.read_text()) or _defaults(secrets.token_hex(32))


def save_config(cfg: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(yaml.safe_dump(cfg))


def get_secret_key() -> str:
    return load_config().get("secret_key") or secrets.token_hex(32)


def verify_password(plain: str) -> bool:
    cfg = load_config()
    h = cfg.get("password_hash")
    if not h:
        return False
    return bcrypt.checkpw(plain.encode(), h.encode())


def set_password(plain: str) -> None:
    cfg = load_config()
    cfg["password_hash"] = bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    save_config(cfg)


def has_password() -> bool:
    return bool(load_config().get("password_hash"))


# ---------------------------------------------------------------------------
# Encryption helpers (Fernet, key derived from secret_key)
# ---------------------------------------------------------------------------

def _fernet() -> Fernet:
    """Return a Fernet instance keyed from the app secret_key."""
    raw = get_secret_key().encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def _encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt value — secret_key may have changed") from e


# ---------------------------------------------------------------------------
# Gmail credential / token storage
# ---------------------------------------------------------------------------

def save_gmail_client(client_id: str, client_secret: str) -> None:
    """Store the Google OAuth client ID (plaintext) and secret (encrypted)."""
    cfg = load_config()
    cfg["gmail_client_id"] = client_id
    cfg["gmail_client_secret"] = _encrypt(client_secret)
    save_config(cfg)


def get_gmail_client() -> tuple[str, str] | None:
    """Return (client_id, client_secret) or None if not configured."""
    cfg = load_config()
    client_id = cfg.get("gmail_client_id")
    encrypted_secret = cfg.get("gmail_client_secret")
    if not client_id or not encrypted_secret:
        return None
    return client_id, _decrypt(encrypted_secret)


def save_gmail_tokens(token_dict: dict) -> None:
    """Store Gmail OAuth tokens, encrypting the sensitive fields."""
    cfg = load_config()
    stored = token_dict.copy()
    stored["token"] = _encrypt(token_dict["token"])
    stored["refresh_token"] = _encrypt(token_dict["refresh_token"])
    cfg["gmail_token"] = stored
    save_config(cfg)


def get_gmail_tokens() -> dict | None:
    """Return decrypted Gmail token dict or None if not connected."""
    cfg = load_config()
    stored = cfg.get("gmail_token")
    if not stored:
        return None
    decrypted = stored.copy()
    decrypted["token"] = _decrypt(stored["token"])
    decrypted["refresh_token"] = _decrypt(stored["refresh_token"])
    return decrypted


def clear_gmail_tokens() -> None:
    """Remove all Gmail credentials and tokens from config."""
    cfg = load_config()
    for key in ("gmail_client_id", "gmail_client_secret", "gmail_token"):
        cfg.pop(key, None)
    save_config(cfg)


# ---------------------------------------------------------------------------
# Google Calendar credential / token storage
# ---------------------------------------------------------------------------

def save_calendar_client(client_id: str, client_secret: str) -> None:
    """Store the Google OAuth client ID (plaintext) and secret (encrypted)."""
    cfg = load_config()
    cfg["calendar_client_id"] = client_id
    cfg["calendar_client_secret"] = _encrypt(client_secret)
    save_config(cfg)


def get_calendar_client() -> tuple[str, str] | None:
    """Return (client_id, client_secret) or None if not configured."""
    cfg = load_config()
    client_id = cfg.get("calendar_client_id")
    encrypted_secret = cfg.get("calendar_client_secret")
    if not client_id or not encrypted_secret:
        return None
    return client_id, _decrypt(encrypted_secret)


def save_calendar_tokens(token_dict: dict) -> None:
    """Store Google Calendar OAuth tokens, encrypting the sensitive fields."""
    cfg = load_config()
    stored = token_dict.copy()
    stored["token"] = _encrypt(token_dict["token"])
    stored["refresh_token"] = _encrypt(token_dict["refresh_token"])
    cfg["calendar_token"] = stored
    save_config(cfg)


def get_calendar_tokens() -> dict | None:
    """Return decrypted Calendar token dict or None if not connected."""
    cfg = load_config()
    stored = cfg.get("calendar_token")
    if not stored:
        return None
    decrypted = stored.copy()
    decrypted["token"] = _decrypt(stored["token"])
    decrypted["refresh_token"] = _decrypt(stored["refresh_token"])
    return decrypted


def clear_calendar_tokens() -> None:
    """Remove all Calendar credentials and tokens from config."""
    cfg = load_config()
    for key in ("calendar_client_id", "calendar_client_secret", "calendar_token"):
        cfg.pop(key, None)
    save_config(cfg)
