"""FastAPI application entry point."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from api.auth import require_auth, router as auth_router
from api.agents_api import router as agents_router
from api.runs import _build_registry
from api.runs import router as runs_router

app = FastAPI(title="agent-99 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(runs_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/tools")
def list_tools(user: str = Depends(require_auth)):
    registry = _build_registry()
    return [
        {
            "name": s["function"]["name"],
            "description": s["function"].get("description", ""),
        }
        for s in registry.all_schemas()
    ]
