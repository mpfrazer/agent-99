# Plan: Wire memory into loop.py

**Date**: 2026-03-23
**Goal**: Integrate the memory backend into AgentLoop so conversation history persists across turns and is prepended to each request.

---

## Changes required

### loop.py

1. Accept an optional `memory: BaseMemory` parameter in `__init__` (defaults to `NoneMemory()`).
2. At the start of `run()`, prepend `memory.history()` between the system prompt and the user message.
3. After the final text response, call `memory.add("user", user_input)` and `memory.add("assistant", result)`.
4. Do NOT persist intermediate tool call turns — only the user input and final assistant response are stored. This keeps history clean and token-efficient.

Message order in each request:
```
[system prompt (if set)]
[...memory.history()]       ← past user/assistant turns
[user: current input]
```

### cli.py

Update the `run` command to:
1. Import `create_memory` from `agent99.memory`.
2. Build `memory = create_memory(config.memory)` before constructing `AgentLoop`.
3. Pass `memory` to `AgentLoop`.

---

## What does NOT change

- `BaseMemory` interface — no changes.
- `memory.py` — no changes.
- `config.py` — no changes.
- All existing tests — no changes (NoneMemory is the default, so existing loop tests are unaffected).

---

## Implementation steps

### Step 1 — Update loop.py

### Step 2 — Update cli.py

### Step 3 — Update tests/test_loop.py

Add new tests (do not change existing ones):
1. Memory history prepended between system prompt and user message.
2. User input and assistant response saved to memory after successful run.
3. Memory not written to on RuntimeError (max_iterations).
4. Default memory (none provided) behaves as before — history always empty.

### Step 4 — Update tests/test_cli.py

Add one test: `run` command constructs memory from config and passes it to AgentLoop.

### Step 5 — Verification

`pytest tests/ -q` — all 93 + new tests pass.

---

## Approval gates

| # | Action | Requires approval |
|---|--------|-------------------|
| 1 | Update `loop.py` | YES |
| 2 | Update `cli.py` | YES |
| 3 | Update `tests/test_loop.py` | YES |
| 4 | Update `tests/test_cli.py` | YES |
| 5 | Run verification | YES |
