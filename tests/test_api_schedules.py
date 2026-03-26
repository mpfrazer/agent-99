"""Tests for /api/schedules/* endpoints."""

import pytest
from fastapi.testclient import TestClient

INTERVAL_PAYLOAD = {
    "agent_name": "my-agent",
    "prompt": "Do something useful",
    "mode": "interval",
    "interval_value": 30,
    "interval_unit": "minutes",
}

DAILY_PAYLOAD = {
    "agent_name": "my-agent",
    "prompt": "Daily task",
    "mode": "daily",
    "daily_time": "09:00",
    "every_n_days": 1,
}


@pytest.fixture(autouse=True)
def isolate_db(config_dir, monkeypatch):
    """Ensure each test uses a fresh in-memory-like DB via isolated config dir."""
    import api.schedules_db as sdb
    import api.app_config as ac

    # config_dir fixture already patches _CONFIG_DIR; just init the DB
    sdb.init_db()


# ---------------------------------------------------------------------------
# POST /api/schedules — create
# ---------------------------------------------------------------------------


def test_create_interval_schedule(api_client: TestClient):
    resp = api_client.post("/api/schedules", json=INTERVAL_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_name"] == "my-agent"
    assert data["mode"] == "interval"
    assert data["interval_value"] == 30
    assert data["interval_unit"] == "minutes"
    assert data["active"] == 1
    assert "id" in data
    assert "next_run" in data
    assert "anchor" in data


def test_create_daily_schedule(api_client: TestClient):
    resp = api_client.post("/api/schedules", json=DAILY_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "daily"
    assert data["daily_time"] == "09:00"
    assert data["every_n_days"] == 1


def test_create_schedule_missing_interval_unit(api_client: TestClient):
    payload = {**INTERVAL_PAYLOAD}
    del payload["interval_unit"]
    resp = api_client.post("/api/schedules", json=payload)
    assert resp.status_code == 422


def test_create_schedule_missing_daily_time(api_client: TestClient):
    payload = {**DAILY_PAYLOAD}
    del payload["daily_time"]
    resp = api_client.post("/api/schedules", json=payload)
    assert resp.status_code == 422


def test_create_schedule_interval_value_zero(api_client: TestClient):
    payload = {**INTERVAL_PAYLOAD, "interval_value": 0}
    resp = api_client.post("/api/schedules", json=payload)
    assert resp.status_code == 422


def test_create_schedule_every_n_days_zero(api_client: TestClient):
    payload = {**DAILY_PAYLOAD, "every_n_days": 0}
    resp = api_client.post("/api/schedules", json=payload)
    assert resp.status_code == 422


def test_create_schedule_empty_agent_name(api_client: TestClient):
    payload = {**INTERVAL_PAYLOAD, "agent_name": "  "}
    resp = api_client.post("/api/schedules", json=payload)
    assert resp.status_code == 422


def test_create_schedule_empty_prompt(api_client: TestClient):
    payload = {**INTERVAL_PAYLOAD, "prompt": ""}
    resp = api_client.post("/api/schedules", json=payload)
    assert resp.status_code == 422


def test_create_schedule_invalid_daily_time_format(api_client: TestClient):
    payload = {**DAILY_PAYLOAD, "daily_time": "9am"}
    resp = api_client.post("/api/schedules", json=payload)
    assert resp.status_code == 422


def test_create_schedule_daily_time_out_of_range(api_client: TestClient):
    payload = {**DAILY_PAYLOAD, "daily_time": "25:00"}
    resp = api_client.post("/api/schedules", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/schedules — list
# ---------------------------------------------------------------------------


def test_list_schedules_empty(api_client: TestClient):
    resp = api_client.get("/api/schedules")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_schedules_after_create(api_client: TestClient):
    api_client.post("/api/schedules", json=INTERVAL_PAYLOAD)
    resp = api_client.get("/api/schedules")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# GET /api/schedules/{id} — get one
# ---------------------------------------------------------------------------


def test_get_schedule(api_client: TestClient):
    created = api_client.post("/api/schedules", json=INTERVAL_PAYLOAD).json()
    resp = api_client.get(f"/api/schedules/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_schedule_not_found(api_client: TestClient):
    resp = api_client.get("/api/schedules/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/schedules/{id} — update
# ---------------------------------------------------------------------------


def test_update_schedule(api_client: TestClient):
    created = api_client.post("/api/schedules", json=INTERVAL_PAYLOAD).json()
    updated_payload = {**INTERVAL_PAYLOAD, "interval_value": 60}
    resp = api_client.put(f"/api/schedules/{created['id']}", json=updated_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["interval_value"] == 60


def test_update_schedule_not_found(api_client: TestClient):
    resp = api_client.put("/api/schedules/no-such-id", json=INTERVAL_PAYLOAD)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/schedules/{id}/toggle — toggle
# ---------------------------------------------------------------------------


def test_toggle_schedule(api_client: TestClient):
    created = api_client.post("/api/schedules", json=INTERVAL_PAYLOAD).json()
    assert created["active"] == 1

    resp = api_client.patch(f"/api/schedules/{created['id']}/toggle")
    assert resp.status_code == 200
    assert resp.json()["active"] == 0

    resp = api_client.patch(f"/api/schedules/{created['id']}/toggle")
    assert resp.status_code == 200
    assert resp.json()["active"] == 1


def test_toggle_schedule_not_found(api_client: TestClient):
    resp = api_client.patch("/api/schedules/no-such-id/toggle")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/schedules/{id}
# ---------------------------------------------------------------------------


def test_delete_schedule(api_client: TestClient):
    created = api_client.post("/api/schedules", json=INTERVAL_PAYLOAD).json()
    resp = api_client.delete(f"/api/schedules/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == created["id"]

    resp = api_client.get(f"/api/schedules/{created['id']}")
    assert resp.status_code == 404


def test_delete_schedule_not_found(api_client: TestClient):
    resp = api_client.delete("/api/schedules/no-such-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth — unauthenticated requests
# ---------------------------------------------------------------------------


def test_list_schedules_requires_auth(unauth_client: TestClient):
    resp = unauth_client.get("/api/schedules")
    assert resp.status_code == 401


def test_create_schedule_requires_auth(unauth_client: TestClient):
    resp = unauth_client.post("/api/schedules", json=INTERVAL_PAYLOAD)
    assert resp.status_code == 401
