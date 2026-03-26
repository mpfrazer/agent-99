"""FastAPI application entry point."""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.agents_api import router as agents_router
from api.auth import require_auth
from api.auth import router as auth_router
from api.calendar_auth import router as calendar_router
from api.gmail_auth import router as gmail_router
from api.runs import _build_registry
from api.runs import router as runs_router

app = FastAPI(title="agent-99 API", version="0.1.0")

_WEB_BASE = os.environ.get("WEB_BASE_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_WEB_BASE],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(gmail_router, prefix="/api")
app.include_router(calendar_router, prefix="/api")
app.include_router(runs_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/tools")
def list_tools(user: str = Depends(require_auth)):
    registry = _build_registry()
    result = []
    for name, fn in registry._tools.items():
        from agent99.registry import build_schema
        s = build_schema(fn)
        module_stem = (fn.__module__ or "").split(".")[-1]
        category = module_stem.replace("_", " ").title() if module_stem else "General"
        result.append({
            "name": name,
            "description": s["function"].get("description", ""),
            "category": category,
        })
    return result
