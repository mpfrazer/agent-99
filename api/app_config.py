"""Load and save ~/.agent99/config.yaml (app-level config, not agent config)."""

import secrets
from pathlib import Path

import yaml
from passlib.context import CryptContext

_CONFIG_DIR = Path.home() / ".agent99"
_CONFIG_FILE = _CONFIG_DIR / "config.yaml"
_RUNS_DIR = _CONFIG_DIR / "runs"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    return pwd_context.verify(plain, h)


def set_password(plain: str) -> None:
    cfg = load_config()
    cfg["password_hash"] = pwd_context.hash(plain)
    save_config(cfg)


def has_password() -> bool:
    return bool(load_config().get("password_hash"))
