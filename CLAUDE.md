# Agent Runner — Project Context

## What We're Building

A lightweight, open-source local AI agent runner. The goal is to make creating and deploying agents as simple as writing a YAML file — no deep framework knowledge required. This is a deliberate alternative to heavy tools like LangChain or AutoGen, prioritizing simplicity and hackability over features.

**North star**: A developer should be able to define, run, and understand a new agent in under 10 minutes.

---

## Core Architecture

The system has four layers:

```
Interface layer       →  CLI (primary), YAML/JSON config, optional web dashboard
Agent runtime         →  Agent loop + Tool registry + Memory manager
Provider backends     →  Ollama (local), Anthropic/OpenAI (remote), Custom adapters
Storage layer         →  Agent state (SQLite), Vector memory (ChromaDB), Tool logs
```

### The Agent Loop

Every agent runs this cycle until the LLM returns no tool call:

1. **Think** — send messages + tool schemas to LLM, get response
2. **Act** — if response contains a tool call, execute it
3. **Observe** — append tool result to message history
4. **Repeat** — until done or `max_iterations` reached

This loop is the heart of the system. Keep it simple and explicit — do not abstract it away.

---

## Design Principles

1. **Config over code** — agents are defined in YAML, not Python classes
2. **Tools are plain functions** — docstrings + type hints auto-generate JSON schemas; no decorators or special classes
3. **Provider-agnostic** — one interface, swap models with one config line
4. **Local-first** — defaults to Ollama (free); remote APIs are opt-in
5. **Transparent** — the loop, tool calls, and memory should be observable/loggable by default
6. **~500–800 lines of core Python** — if it grows beyond this, something is wrong

---

## Tech Stack

| Concern | Choice | Reason |
|---|---|---|
| Language | Python | Universal, best LLM ecosystem |
| Provider abstraction | `litellm` | Handles 100+ models with one interface |
| CLI | `typer` | Clean, minimal |
| Agent config | YAML | Human-readable, no Python required |
| Session persistence | SQLite | Zero infra, built into Python |
| Vector memory | ChromaDB | Pure Python, no server, local |
| Type hints | Python 3.10+ dataclasses / Pydantic | Keep it lightweight |

---

## Agent Config Schema (YAML)

```yaml
name: my-agent
description: "What this agent does"
model: ollama/llama3          # or anthropic/claude-sonnet-4-5, openai/gpt-4o, etc.
system_prompt: |
  You are a helpful assistant that...
tools:
  - web_search
  - read_file
  - write_file
memory: sqlite                # none | sqlite | chromadb
max_iterations: 10
max_tokens: 4096
```

---

## Provider Interface

All providers implement this interface:

```python
class Provider:
    def complete(self, messages: list[dict], tools: list[dict]) -> Response: ...
```

Use `litellm` as the underlying library — it normalizes API differences across Ollama, Anthropic, OpenAI, Gemini, etc. The `model` field in the YAML maps directly to litellm's model string format (`provider/model-name`).

---

## Tool System

Tools are plain Python functions. The registry inspects signatures and docstrings to auto-generate JSON schemas:

```python
def web_search(query: str) -> str:
    """Search the web and return a summary of results."""
    ...

def read_file(path: str) -> str:
    """Read the contents of a file at the given path."""
    ...
```

- No decorators required
- Type hints are mandatory (used for schema generation)
- Docstring becomes the tool description sent to the LLM
- Tools live in a `tools/` directory and are auto-discovered

---

## Memory Tiers

| Tier | Backend | Use case |
|---|---|---|
| `none` | — | Stateless, one-shot tasks |
| `sqlite` | SQLite | Persist conversation history across sessions |
| `chromadb` | ChromaDB | Semantic search over large knowledge bases |

Short-term (in-context) memory is always active — last N messages kept in context window.

---

## Cost Control

- Default model is local Ollama — $0 for dev/test
- `max_iterations` prevents runaway loops
- `max_tokens` caps per-turn spend
- Cache tool results within a session (same call + args = return cached result)
- Future: tiered routing (small model for simple steps, frontier model for hard ones)

---

## Project Structure (Target)

```
agent-runner/
├── CLAUDE.md               ← this file
├── README.md
├── pyproject.toml
├── agent_runner/
│   ├── __init__.py
│   ├── loop.py             ← the agent loop
│   ├── registry.py         ← tool registry + schema generation
│   ├── memory.py           ← memory manager (none/sqlite/chromadb)
│   ├── providers.py        ← litellm wrapper + provider abstraction
│   ├── config.py           ← YAML config loading + validation
│   └── cli.py              ← typer CLI (run, list, new)
├── tools/
│   ├── web_search.py
│   ├── read_file.py
│   ├── write_file.py
│   └── shell.py
├── agents/
│   └── example.yaml        ← example agent config
└── tests/
    ├── test_loop.py
    ├── test_registry.py
    └── test_memory.py
```

---

## CLI Commands (Target API)

```bash
agent run agents/my-agent.yaml          # run an agent
agent run agents/my-agent.yaml --watch  # stream output
agent new my-agent                      # scaffold a new agent YAML
agent list                              # list available agents
agent tools                             # list registered tools
```

---

## What to Build First

Recommended order:

1. `config.py` — YAML loading and validation (Pydantic model)
2. `providers.py` — litellm wrapper with the `Provider` interface
3. `registry.py` — tool discovery and JSON schema generation
4. `loop.py` — the agent loop (think/act/observe)
5. `cli.py` — typer CLI wiring it together
6. `memory.py` — start with `none`, add sqlite, then chromadb

Get a working end-to-end loop with a single tool before adding memory or multi-provider support.

---

## What This Is NOT

- Not a replacement for Ollama (we use Ollama as a backend)
- Not trying to replicate all of LangChain's features
- Not a hosted/cloud product — fully local
- Not opinionated about what agents do — just how they run
