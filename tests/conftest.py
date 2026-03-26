"""Shared pytest fixtures for agent-99 tests."""

import secrets
from pathlib import Path

import bcrypt
import pytest
import yaml
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Config isolation
# ---------------------------------------------------------------------------


@pytest.fixture()
def config_dir(tmp_path: Path, monkeypatch):
    """Point app_config at a temporary directory so tests never touch ~/.agent99."""
    cfg_dir = tmp_path / ".agent99"
    cfg_dir.mkdir()
    runs = cfg_dir / "runs"
    runs.mkdir()

    import api.app_config as ac

    monkeypatch.setattr(ac, "_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(ac, "_CONFIG_FILE", cfg_dir / "config.yaml")
    monkeypatch.setattr(ac, "_RUNS_DIR", runs)

    return cfg_dir


@pytest.fixture()
def config_with_password(config_dir: Path):
    """Write a config.yaml with a known password hash and secret key."""
    secret = secrets.token_hex(32)
    password = "testpassword123"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    cfg = {
        "secret_key": secret,
        "password_hash": password_hash,
        "runs_dir": str(config_dir / "runs"),
    }
    (config_dir / "config.yaml").write_text(yaml.safe_dump(cfg))

    return {"password": password, "secret": secret, "cfg_dir": config_dir}


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------


@pytest.fixture()
def api_client(config_with_password):
    """Return an authenticated TestClient for the FastAPI app."""
    from api.main import app

    with TestClient(app, raise_server_exceptions=True) as client:
        # Log in to get session cookie
        resp = client.post("/api/auth/login", json={"password": config_with_password["password"]})
        assert resp.status_code == 200
        yield client


@pytest.fixture()
def unauth_client(config_with_password):
    """Return an unauthenticated TestClient."""
    from api.main import app

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
