"""Tests for /api/auth/* endpoints."""

from fastapi.testclient import TestClient


def test_login_success(unauth_client: TestClient, config_with_password):
    resp = unauth_client.post(
        "/api/auth/login", json={"password": config_with_password["password"]}
    )
    assert resp.status_code == 200
    assert resp.json() == {"authenticated": True}
    assert "agent99_session" in resp.cookies


def test_login_wrong_password(unauth_client: TestClient):
    resp = unauth_client.post("/api/auth/login", json={"password": "wrongpassword"})
    assert resp.status_code == 401


def test_me_authenticated(api_client: TestClient):
    resp = api_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is True


def test_me_unauthenticated(unauth_client: TestClient):
    resp = unauth_client.get("/api/auth/me")
    assert resp.status_code == 401


def test_logout(api_client: TestClient):
    resp = api_client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json() == {"authenticated": False}


def test_me_after_logout(api_client: TestClient):
    api_client.post("/api/auth/logout")
    resp = api_client.get("/api/auth/me")
    assert resp.status_code == 401


def test_change_password(api_client: TestClient):
    resp = api_client.post("/api/auth/password", json={"password": "newpassword456"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_change_password_empty(api_client: TestClient):
    resp = api_client.post("/api/auth/password", json={"password": "   "})
    assert resp.status_code == 400


def test_health(unauth_client: TestClient):
    resp = unauth_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
