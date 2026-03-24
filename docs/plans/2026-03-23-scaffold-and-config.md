# Plan: Scaffold Project Structure and Implement config.py

**Date**: 2026-03-23
**Goal**: Establish the Python project layout and implement the Pydantic-based agent config model.

---

## Repository Review

Current state: empty repo with only `CLAUDE.md`, `README.md`, and `docs/plans/`.
No source code, no `pyproject.toml`, no dependencies installed.

---

## Step 1 — Create project directory structure

Create the following layout (no implementation yet, just empty files / `__init__.py`s):

```
agent-99/
├── agent99/                  # main package
│   ├── __init__.py
│   ├── config.py             # step 1 (this plan)
│   ├── providers.py          # step 2
│   ├── registry.py           # step 3
│   ├── loop.py               # step 4
│   ├── cli.py                # step 5
│   └── memory.py             # step 6
├── tools/                    # built-in tool functions (plain Python)
│   ├── __init__.py
│   └── filesystem.py         # read_file, write_file, list_dir
├── agents/                   # example YAML agent definitions
│   └── example.yaml
├── tests/
│   └── test_config.py
├── pyproject.toml
└── .gitignore
```

**Stub files** (`providers.py`, `registry.py`, `loop.py`, `cli.py`, `memory.py`) will contain only a module docstring and a `# TODO` comment — no implementation.

---

## Step 2 — Write pyproject.toml

Minimal `pyproject.toml` using `[project]` table (PEP 621). Dependencies:

```
pydantic>=2.0
pyyaml
litellm
typer
```

No optional extras yet. No build backend beyond `hatchling` (simple, zero-config).

---

## Step 3 — Implement config.py

### What it models

A YAML agent definition looks like this:

```yaml
name: file-reader
description: An agent that reads files and answers questions about them.
model: ollama/mistral
system_prompt: |
  You are a helpful assistant. Use tools when appropriate.
tools:
  - read_file
  - list_dir
memory:
  type: none          # none | sqlite | chromadb
max_iterations: 20
temperature: 0.7
```

### Pydantic model design

```python
class MemoryConfig(BaseModel):
    type: Literal["none", "sqlite", "chromadb"] = "none"
    path: str | None = None          # DB path for sqlite/chromadb

class AgentConfig(BaseModel):
    name: str
    description: str = ""
    model: str                        # litellm model string, e.g. "ollama/mistral"
    system_prompt: str = ""
    tools: list[str] = []             # tool names; resolved by registry at runtime
    memory: MemoryConfig = MemoryConfig()
    max_iterations: int = 20
    temperature: float = 0.7

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AgentConfig": ...
```

Validation rules:
- `name` must be non-empty.
- `max_iterations` must be >= 1.
- `temperature` must be 0.0–2.0.
- `model` must be non-empty.

### from_yaml

Reads the file, parses YAML, passes dict to `model_validate`. Raises a clean `ValueError` (wrapping Pydantic's `ValidationError`) with the file path included in the message.

---

## Step 4 — Write test_config.py

Cover:
1. Valid config loads correctly.
2. Missing required fields (`name`, `model`) raise `ValidationError`.
3. Out-of-range `temperature` raises `ValidationError`.
4. `max_iterations < 1` raises `ValidationError`.
5. `from_yaml` round-trip with the example YAML.

---

## Step 5 — Verification

- `python -m pytest tests/test_config.py -v` passes all tests.
- `python -c "from agent99.config import AgentConfig; print('ok')"` succeeds.

---

## Approval gates

| # | Action | Requires approval |
|---|--------|-------------------|
| 1 | Create directory structure + stub files | YES |
| 2 | Write `pyproject.toml` | YES |
| 3 | Implement `config.py` | YES |
| 4 | Write `tests/test_config.py` + `agents/example.yaml` | YES |
| 5 | Run verification commands | YES |
