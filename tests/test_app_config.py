"""Tests for api/app_config.py — config I/O and encryption."""

import secrets
from pathlib import Path

import pytest
import yaml


def test_load_config_creates_defaults(config_dir: Path):
    import api.app_config as ac

    cfg = ac.load_config()
    assert "secret_key" in cfg
    assert "password_hash" in cfg
    assert (config_dir / "config.yaml").exists()


def test_load_config_idempotent(config_dir: Path):
    import api.app_config as ac

    cfg1 = ac.load_config()
    cfg2 = ac.load_config()
    assert cfg1["secret_key"] == cfg2["secret_key"]


def test_save_and_reload_config(config_dir: Path):
    import api.app_config as ac

    cfg = ac.load_config()
    cfg["custom_key"] = "custom_value"
    ac.save_config(cfg)

    reloaded = ac.load_config()
    assert reloaded["custom_key"] == "custom_value"


def test_verify_password(config_with_password):
    import api.app_config as ac

    assert ac.verify_password(config_with_password["password"]) is True
    assert ac.verify_password("wrongpassword") is False


def test_set_password(config_dir: Path):
    import api.app_config as ac

    ac.load_config()  # initialise config
    ac.set_password("mynewpassword")
    assert ac.verify_password("mynewpassword") is True
    assert ac.verify_password("wrongpassword") is False


def test_has_password_false_before_set(config_dir: Path):
    import api.app_config as ac

    ac.load_config()
    assert ac.has_password() is False


def test_has_password_true_after_set(config_dir: Path):
    import api.app_config as ac

    ac.load_config()
    ac.set_password("password123")
    assert ac.has_password() is True


def test_encrypt_decrypt_roundtrip(config_with_password):
    import api.app_config as ac

    plaintext = "super_secret_value"
    encrypted = ac._encrypt(plaintext)
    assert encrypted != plaintext
    assert ac._decrypt(encrypted) == plaintext


def test_gmail_client_roundtrip(config_with_password):
    import api.app_config as ac

    ac.save_gmail_client("client-id-123", "client-secret-abc")
    result = ac.get_gmail_client()
    assert result is not None
    assert result[0] == "client-id-123"
    assert result[1] == "client-secret-abc"


def test_gmail_tokens_roundtrip(config_with_password):
    import api.app_config as ac

    tokens = {
        "token": "access-token-xyz",
        "refresh_token": "refresh-token-xyz",
        "token_uri": "https://oauth2.googleapis.com/token",
        "scopes": ["https://mail.google.com/"],
        "expiry": None,
    }
    ac.save_gmail_tokens(tokens)
    result = ac.get_gmail_tokens()
    assert result is not None
    assert result["token"] == "access-token-xyz"
    assert result["refresh_token"] == "refresh-token-xyz"


def test_clear_gmail_tokens(config_with_password):
    import api.app_config as ac

    ac.save_gmail_client("id", "secret")
    ac.save_gmail_tokens({
        "token": "t", "refresh_token": "r",
        "token_uri": "", "scopes": [], "expiry": None,
    })
    ac.clear_gmail_tokens()
    assert ac.get_gmail_tokens() is None
    assert ac.get_gmail_client() is None


def test_calendar_client_roundtrip(config_with_password):
    import api.app_config as ac

    ac.save_calendar_client("cal-client-id", "cal-client-secret")
    result = ac.get_calendar_client()
    assert result is not None
    assert result[0] == "cal-client-id"
    assert result[1] == "cal-client-secret"


def test_calendar_tokens_roundtrip(config_with_password):
    import api.app_config as ac

    tokens = {
        "token": "cal-access-token",
        "refresh_token": "cal-refresh-token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/calendar"],
        "expiry": None,
    }
    ac.save_calendar_tokens(tokens)
    result = ac.get_calendar_tokens()
    assert result is not None
    assert result["token"] == "cal-access-token"
    assert result["refresh_token"] == "cal-refresh-token"


def test_clear_calendar_tokens(config_with_password):
    import api.app_config as ac

    ac.save_calendar_client("id", "secret")
    ac.save_calendar_tokens({
        "token": "t", "refresh_token": "r",
        "token_uri": "", "scopes": [], "expiry": None,
    })
    ac.clear_calendar_tokens()
    assert ac.get_calendar_tokens() is None
    assert ac.get_calendar_client() is None
