"""CRUD endpoints for agent YAML files."""

from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agent99.config import AgentConfig
from api.auth import require_auth

router = APIRouter(prefix="/agents", tags=["agents"])

_AGENTS_DIR = Path("agents")


def _agents_dir() -> Path:
    return _AGENTS_DIR


def _agent_path(name: str) -> Path:
    return _agents_dir() / f"{name}.yaml"


def _load_agent(name: str) -> dict:
    path = _agent_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    raw = yaml.safe_load(path.read_text())
    return raw


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AgentPayload(BaseModel):
    name: str
    description: str = ""
    model: str
    system_prompt: str = ""
    tools: list[str] = []
    memory: dict = {"type": "none"}
    max_iterations: int = 20
    temperature: float = 0.7
    api_base: str | None = None
    stream_output: bool = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
def list_agents(user: str = Depends(require_auth)):
    _agents_dir().mkdir(exist_ok=True)
    agents = []
    for f in sorted(_agents_dir().glob("*.yaml")):
        try:
            raw = yaml.safe_load(f.read_text())
            agents.append({
                "name": f.stem,
                "description": raw.get("description", ""),
                "model": raw.get("model", ""),
                "stream_output": raw.get("stream_output", True),
                "tools": raw.get("tools", []),
            })
        except Exception:
            pass
    return agents


@router.get("/{name}")
def get_agent(name: str, user: str = Depends(require_auth)):
    return _load_agent(name)


@router.post("")
def create_agent(payload: AgentPayload, user: str = Depends(require_auth)):
    _agents_dir().mkdir(exist_ok=True)
    path = _agent_path(payload.name)
    if path.exists():
        raise HTTPException(status_code=409, detail=f"Agent '{payload.name}' already exists")
    _validate_and_write(payload, path)
    return {"name": payload.name}


@router.put("/{name}")
def update_agent(name: str, payload: AgentPayload, user: str = Depends(require_auth)):
    path = _agent_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    _validate_and_write(payload, path)
    return {"name": name}


@router.delete("/{name}")
def delete_agent(name: str, user: str = Depends(require_auth)):
    path = _agent_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    path.unlink()
    return {"deleted": name}


def _validate_and_write(payload: AgentPayload, path: Path) -> None:
    data = payload.model_dump(exclude_none=False)
    # Validate via AgentConfig
    try:
        AgentConfig.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    path.write_text(yaml.safe_dump(data, default_flow_style=False, allow_unicode=True))
