"""Run lifecycle management: start, stream (SSE), cancel, list, persist."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent99.config import AgentConfig
from agent99.memory import create_memory
from agent99.registry import ToolRegistry
from api.agents_api import _load_agent
from api.async_loop import LoopEvent, run_agent_async
from api.auth import require_auth
from api.app_config import runs_dir

import importlib

router = APIRouter(prefix="/runs", tags=["runs"])

_TOOL_MODULES = ["tools.filesystem"]

# In-memory active runs
_active: dict[str, "RunState"] = {}


# ---------------------------------------------------------------------------
# RunState
# ---------------------------------------------------------------------------

@dataclass
class RunState:
    id: str
    agent_name: str
    user_input: str
    stream: bool
    status: str  # running | completed | cancelled | error
    events: list[dict] = field(default_factory=list)  # accumulated for late-joiners
    final_output: str = ""
    error: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    task: asyncio.Task | None = None
    model: str = ""
    tool_calls: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StartRunRequest(BaseModel):
    agent_name: str
    user_input: str
    stream: bool | None = None          # override agent default
    model: str | None = None            # override
    temperature: float | None = None    # override
    max_iterations: int | None = None   # override


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for mod_path in _TOOL_MODULES:
        try:
            module = importlib.import_module(mod_path)
            registry.register_module(module)
        except ImportError:
            pass
    return registry


def _save_run(run: RunState, agent_raw: dict) -> None:
    rdir = runs_dir()
    rdir.mkdir(parents=True, exist_ok=True)
    ts = run.started_at[:19].replace(":", "-").replace("T", "-")
    filename = f"{ts}-{run.agent_name}.md"
    path = rdir / filename

    frontmatter = {
        "id": run.id,
        "agent": run.agent_name,
        "model": run.model,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "status": run.status,
        "tool_calls": run.tool_calls,
    }
    if agent_raw.get("api_base"):
        frontmatter["api_base"] = agent_raw["api_base"]

    content = f"---\n{yaml.safe_dump(frontmatter, default_flow_style=False)}---\n\n"
    content += f"## Input\n\n{run.user_input}\n\n"
    content += f"## Output\n\n{run.final_output}\n"

    path.write_text(content)


def _parse_run_file(path: Path) -> dict | None:
    try:
        text = path.read_text()
        if not text.startswith("---"):
            return None
        _, fm_text, body = text.split("---", 2)
        fm = yaml.safe_load(fm_text) or {}
        # Extract output from body
        output = ""
        if "## Output" in body:
            output = body.split("## Output", 1)[1].strip()
        input_text = ""
        if "## Input" in body:
            input_text = body.split("## Input", 1)[1].split("## Output")[0].strip()
        return {**fm, "user_input": input_text, "final_output": output}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Background task runner
# ---------------------------------------------------------------------------

async def _run_task(run: RunState, config: AgentConfig, agent_raw: dict) -> None:
    registry = _build_registry()
    memory = create_memory(config.memory)
    try:
        result = await run_agent_async(
            config=config,
            registry=registry,
            user_input=run.user_input,
            queue=run.queue,
            memory=memory,
            stream=run.stream,
        )
        run.final_output = result
        run.status = "completed"
    except asyncio.CancelledError:
        run.status = "cancelled"
        await run.queue.put(LoopEvent("cancelled", {}))
    except Exception as e:
        run.status = "error"
        run.error = str(e)
        await run.queue.put(LoopEvent("error", {"message": str(e)}))
    finally:
        run.completed_at = datetime.now(timezone.utc).isoformat()
        _save_run(run, agent_raw)
        # sentinel to close SSE streams
        await run.queue.put(None)
        _active.pop(run.id, None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("")
async def start_run(body: StartRunRequest, user: str = Depends(require_auth)):
    agent_raw = _load_agent(body.agent_name)
    config = AgentConfig.model_validate(agent_raw)

    # Apply per-run overrides
    if body.model:
        config.model = body.model
    if body.temperature is not None:
        config.temperature = body.temperature
    if body.max_iterations is not None:
        config.max_iterations = body.max_iterations

    stream = body.stream if body.stream is not None else config.stream_output

    run = RunState(
        id=str(uuid.uuid4()),
        agent_name=body.agent_name,
        user_input=body.user_input,
        stream=stream,
        status="running",
        model=config.model,
    )
    _active[run.id] = run
    run.task = asyncio.create_task(_run_task(run, config, agent_raw))

    return {
        "run_id": run.id,
        "agent_name": run.agent_name,
        "status": run.status,
        "stream": stream,
    }


@router.get("/{run_id}/stream")
async def stream_run(run_id: str, user: str = Depends(require_auth)):
    run = _active.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found or already completed")

    async def event_generator():
        # Replay accumulated events for late-joiners
        for evt in run.events:
            yield {"data": __import__("json").dumps(evt)}

        # Stream live events
        while True:
            evt = await run.queue.get()
            if evt is None:
                break
            event_dict = {"type": evt.type, **evt.data}
            run.events.append(event_dict)
            # Track tool calls for persistence
            if evt.type == "tool_call":
                run.tool_calls.append({
                    "name": evt.data.get("name"),
                    "arguments": evt.data.get("arguments"),
                    "result": None,
                })
            elif evt.type == "tool_result" and run.tool_calls:
                for tc in reversed(run.tool_calls):
                    if tc["name"] == evt.data.get("name") and tc["result"] is None:
                        tc["result"] = evt.data.get("result")
                        break
            yield {"data": __import__("json").dumps(event_dict)}
            if evt.type in ("done", "error", "cancelled"):
                break

    return EventSourceResponse(event_generator())


@router.delete("/{run_id}")
async def cancel_run(run_id: str, user: str = Depends(require_auth)):
    run = _active.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found or already completed")
    if run.task and not run.task.done():
        run.task.cancel()
    return {"cancelled": run_id}


@router.get("")
def list_runs(
    status: str | None = None,
    limit: int = 50,
    user: str = Depends(require_auth),
):
    results = []

    # Active (in-memory) runs
    for run in _active.values():
        if status and run.status != status:
            continue
        results.append({
            "id": run.id,
            "agent_name": run.agent_name,
            "status": run.status,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "model": run.model,
            "user_input": run.user_input[:100],
        })

    # Persisted runs (files)
    if status != "running":
        rdir = runs_dir()
        if rdir.exists():
            files = sorted(rdir.glob("*.md"), reverse=True)
            for f in files[:limit]:
                parsed = _parse_run_file(f)
                if parsed and parsed.get("id") not in {r["id"] for r in results}:
                    if status and parsed.get("status") != status:
                        continue
                    results.append({
                        "id": parsed.get("id", f.stem),
                        "agent_name": parsed.get("agent", ""),
                        "status": parsed.get("status", "unknown"),
                        "started_at": str(parsed.get("started_at", "")),
                        "completed_at": str(parsed.get("completed_at", "")),
                        "model": parsed.get("model", ""),
                        "user_input": parsed.get("user_input", "")[:100],
                    })

    results.sort(key=lambda r: r.get("started_at", ""), reverse=True)
    return results[:limit]


@router.get("/{run_id}")
def get_run(run_id: str, user: str = Depends(require_auth)):
    # Check active
    if run_id in _active:
        run = _active[run_id]
        return {
            "id": run.id,
            "agent_name": run.agent_name,
            "status": run.status,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "model": run.model,
            "user_input": run.user_input,
            "final_output": run.final_output,
            "tool_calls": run.tool_calls,
            "events": run.events,
            "error": run.error,
        }

    # Check files
    rdir = runs_dir()
    if rdir.exists():
        for f in rdir.glob("*.md"):
            parsed = _parse_run_file(f)
            if parsed and parsed.get("id") == run_id:
                return parsed

    raise HTTPException(status_code=404, detail="Run not found")
