# Plan: Implement providers.py

**Date**: 2026-03-23
**Goal**: Wrap litellm with a clean Provider interface that the agent loop can use uniformly across Ollama, Anthropic, and OpenAI backends.

---

## Context

litellm exposes a single `litellm.completion()` call that accepts any model string (e.g. `"ollama/mistral"`, `"anthropic/claude-3-5-sonnet-20241022"`, `"openai/gpt-4o"`). Our job is to wrap this behind a minimal interface so `loop.py` never imports litellm directly.

---

## Design

### Data types

```python
class Message(TypedDict):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None
    # tool_calls and tool_call_id added when needed (kept as plain dicts for
    # litellm compatibility — no custom classes needed at this stage)
```

We will NOT define a custom `Message` class — litellm already accepts plain
dicts. Using `TypedDict` gives type hints without adding a class hierarchy.

### ToolCall / LLMResponse

```python
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict  # parsed from JSON

@dataclass
class LLMResponse:
    content: str | None          # text content (None when tool_calls present)
    tool_calls: list[ToolCall]   # empty list if no tool calls
    raw: Any                     # the raw litellm response (for debugging)
```

### Provider class

```python
class Provider:
    def __init__(self, model: str, temperature: float = 0.7, **kwargs): ...

    def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,   # JSON schemas from registry
    ) -> LLMResponse: ...
```

- `complete()` calls `litellm.completion()` and normalises the response into
  `LLMResponse`.
- `tools` is passed through as-is to litellm's `tools` parameter (OpenAI tool-
  calling format, which litellm translates for each backend).
- Any litellm exception propagates as-is — no silent swallowing.

---

## Implementation steps

### Step 1 — Write providers.py

File: `agent99/providers.py`

Contents:
1. Imports: `json`, `dataclasses`, `typing`, `Any`, `litellm`
2. `ToolCall` dataclass
3. `LLMResponse` dataclass
4. `Provider` class with `__init__` and `complete`

### Step 2 — Write tests/test_providers.py

Tests use `unittest.mock.patch` to mock `litellm.completion` — we do NOT make
real API calls in tests.

Cover:
1. Plain text response (no tool calls) → `LLMResponse.content` set, `tool_calls` empty.
2. Tool call response → `ToolCall` objects populated, `content` is None.
3. Multiple tool calls in one response.
4. `Provider` passes `model` and `temperature` through to litellm.
5. `Provider` passes `tools` schema through to litellm when provided.
6. litellm exception propagates unchanged.

### Step 3 — Verification

Run `pytest tests/test_providers.py -v` — all tests must pass.

---

## Approval gates

| # | Action | Requires approval |
|---|--------|-------------------|
| 1 | Implement `providers.py` | YES |
| 2 | Write `tests/test_providers.py` | YES |
| 3 | Run verification | YES |
