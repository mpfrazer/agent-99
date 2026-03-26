"""Tests for /api/agents/* CRUD endpoints."""

from fastapi.testclient import TestClient

AGENT_PAYLOAD = {
    "name": "test-agent",
    "description": "A test agent",
    "model": "ollama/mistral",
    "system_prompt": "You are helpful.",
    "tools": ["read_file"],
    "memory": {"type": "none"},
    "max_iterations": 10,
    "temperature": 0.7,
    "api_base": None,
    "stream_output": True,
}


def test_list_agents_empty(api_client: TestClient, tmp_path, monkeypatch):
    import api.agents_api as aa

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    monkeypatch.setattr(aa, "_AGENTS_DIR", agents_dir)

    resp = api_client.get("/api/agents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_and_get_agent(api_client: TestClient, tmp_path, monkeypatch):
    import api.agents_api as aa

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    monkeypatch.setattr(aa, "_AGENTS_DIR", agents_dir)

    resp = api_client.post("/api/agents", json=AGENT_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json() == {"name": "test-agent"}

    resp = api_client.get("/api/agents/test-agent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test-agent"
    assert data["model"] == "ollama/mistral"


def test_create_duplicate_agent(api_client: TestClient, tmp_path, monkeypatch):
    import api.agents_api as aa

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    monkeypatch.setattr(aa, "_AGENTS_DIR", agents_dir)

    api_client.post("/api/agents", json=AGENT_PAYLOAD)
    resp = api_client.post("/api/agents", json=AGENT_PAYLOAD)
    assert resp.status_code == 409


def test_get_missing_agent(api_client: TestClient, tmp_path, monkeypatch):
    import api.agents_api as aa

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    monkeypatch.setattr(aa, "_AGENTS_DIR", agents_dir)

    resp = api_client.get("/api/agents/nonexistent")
    assert resp.status_code == 404


def test_update_agent(api_client: TestClient, tmp_path, monkeypatch):
    import api.agents_api as aa

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    monkeypatch.setattr(aa, "_AGENTS_DIR", agents_dir)

    api_client.post("/api/agents", json=AGENT_PAYLOAD)

    updated = {**AGENT_PAYLOAD, "description": "Updated description"}
    resp = api_client.put("/api/agents/test-agent", json=updated)
    assert resp.status_code == 200

    resp = api_client.get("/api/agents/test-agent")
    assert resp.json()["description"] == "Updated description"


def test_delete_agent(api_client: TestClient, tmp_path, monkeypatch):
    import api.agents_api as aa

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    monkeypatch.setattr(aa, "_AGENTS_DIR", agents_dir)

    api_client.post("/api/agents", json=AGENT_PAYLOAD)
    resp = api_client.delete("/api/agents/test-agent")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": "test-agent"}

    resp = api_client.get("/api/agents/test-agent")
    assert resp.status_code == 404


def test_agents_require_auth(unauth_client: TestClient):
    resp = unauth_client.get("/api/agents")
    assert resp.status_code == 401
