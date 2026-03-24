# agent-99

A lightweight, open-source local AI agent runner. Define agents in YAML, run them from the CLI or web UI. No framework required.

---

## Requirements

| Dependency | Version | Notes |
|---|---|---|
| Python | 3.11+ | |
| Node.js | 18+ | Web UI only |
| Ollama | any | For local models (free). Remote APIs also supported. |

---

## Quick start

### 1. Clone

```bash
git clone https://github.com/mpfrazer/agent-99
cd agent-99
```

### 2. Install

```bash
python install.py
```

This will:
- Create a Python virtual environment (`.venv/`)
- Install all Python and Node.js dependencies
- Build the Next.js frontend
- Create `~/.agent99/` and prompt you to set a password for the web UI

### 3. Run

**Web UI** (recommended):

```bash
python start.py
```

Opens `http://localhost:3000` in your browser. FastAPI runs on `:8000`, Next.js on `:3000`. Press `Ctrl+C` to stop both.

**CLI only** (no Node.js required):

```bash
# Activate the virtual environment
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# Run an agent
agent99 run agents/example.yaml --input "List the files in /tmp"

# Or pipe input
echo "What is 2 + 2?" | agent99 run agents/example.yaml
```

---

## CLI reference

```
agent99 run <agent.yaml> [--input TEXT]   Run an agent
agent99 new  <name>                       Scaffold a new agent YAML
agent99 list                              List agents in agents/
agent99 tools                             List available built-in tools
```

---

## Defining an agent

Agents are plain YAML files. Drop them in `agents/` or anywhere you like:

```yaml
name: file-reader
description: Reads files and answers questions about them.
model: ollama/mistral           # any litellm model string
system_prompt: |
  You are a helpful assistant. Use tools when appropriate.
tools:
  - read_file
  - list_dir
memory:
  type: none                    # none | sqlite | chromadb
max_iterations: 20
temperature: 0.7
stream_output: true             # stream tokens live in the web UI

# Optional: point at a remote Ollama instance
api_base: http://192.168.2.107:11434
```

### Supported models

The `model` field maps directly to [litellm's model string format](https://docs.litellm.ai/docs/providers):

| Provider | Example model string |
|---|---|
| Ollama (local) | `ollama/mistral`, `ollama/llama3` |
| Anthropic | `anthropic/claude-sonnet-4-5` |
| OpenAI | `openai/gpt-4o` |
| Gemini | `gemini/gemini-1.5-pro` |

Remote providers require the relevant API key set as an environment variable (e.g. `ANTHROPIC_API_KEY`).

---

## Built-in tools

| Tool | Description |
|---|---|
| `read_file` | Read the contents of a file |
| `write_file` | Write content to a file |
| `list_dir` | List files and directories |

Add your own by dropping a `.py` file in `tools/` — any public function with type hints and a docstring is auto-registered. No decorators needed.

---

## Memory

| Type | Backend | Use case |
|---|---|---|
| `none` | — | Stateless, one-shot tasks |
| `sqlite` | SQLite (stdlib) | Persist conversation history across sessions |
| `chromadb` | ChromaDB | Semantic search (coming soon) |

SQLite memory stores conversation history to a local DB file. Each `agent99 run` call continues the same conversation:

```yaml
memory:
  type: sqlite
  path: ~/.agent99/my-agent.db   # optional, defaults to in-memory
```

---

## Web UI

After running `python start.py`:

| Page | What it does |
|---|---|
| Dashboard | Overview of agents and recent runs |
| Agents | Create, edit, and delete agents |
| Agent detail | Run an agent with optional per-run overrides |
| Run history | Browse all past runs, filter by status |
| Run detail | Full input/output with tool call accordion |
| Settings | Change the web UI password |

Runs are saved as Markdown files in `~/.agent99/runs/` with YAML frontmatter — human-readable and git-friendly.

**Active runs bar**: A sticky bar at the bottom of every page shows all running agents. You can navigate freely while agents run in the background, and cancel them at any time.

---

## Project structure

```
agent-99/
├── agent99/          Python package (config, loop, registry, providers, memory, CLI)
├── api/              FastAPI backend for the web UI
├── web/              Next.js frontend
├── tools/            Built-in tool functions (plain Python)
├── agents/           Agent YAML definitions
├── tests/            pytest test suite
├── install.py        One-shot installer (cross-platform)
└── start.py          Web UI launcher (cross-platform)
```

---

## Development

```bash
# Install in editable mode with web deps
pip install -e ".[web]"

# Run tests
pytest tests/

# Start FastAPI dev server (auto-reload)
uvicorn api.main:app --reload

# Start Next.js dev server
cd web && npm run dev
```

---

## License

MIT
