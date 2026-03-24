"""Typer CLI: run, new, list, tools commands."""

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from agent99.config import AgentConfig
from agent99.loop import AgentLoop
from agent99.memory import create_memory
from agent99.providers import Provider
from agent99.registry import ToolRegistry, build_schema

app = typer.Typer(help="agent-99: a lightweight local AI agent runner.")

# Tool modules auto-registered for every agent run
_TOOL_MODULES: list[str] = ["tools.filesystem"]

_NEW_AGENT_TEMPLATE = """\
name: {name}
description: ""
model: ollama/mistral
system_prompt: |
  You are a helpful assistant.
tools: []
memory:
  type: none
max_iterations: 20
temperature: 0.7
"""


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for module_path in _TOOL_MODULES:
        try:
            import importlib
            module = importlib.import_module(module_path)
            registry.register_module(module)
        except ImportError:
            pass
    return registry


@app.command()
def run(
    agent_file: Annotated[Path, typer.Argument(help="Path to the agent YAML file.")],
    input: Annotated[Optional[str], typer.Option("--input", "-i", help="User input. Reads stdin if omitted.")] = None,
) -> None:
    """Run an agent defined in a YAML file."""
    try:
        config = AgentConfig.from_yaml(agent_file)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    user_input = input if input is not None else sys.stdin.read().strip()

    provider = Provider(
        model=config.model,
        temperature=config.temperature,
        **({"api_base": config.api_base} if config.api_base else {}),
    )
    registry = _build_registry()
    memory = create_memory(config.memory)
    loop = AgentLoop(config=config, provider=provider, registry=registry, memory=memory)

    try:
        result = loop.run(user_input)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    typer.echo(result)


@app.command()
def new(
    name: Annotated[str, typer.Argument(help="Name of the new agent.")],
) -> None:
    """Scaffold a new agent YAML file in the agents/ directory."""
    agents_dir = Path.cwd() / "agents"
    agents_dir.mkdir(exist_ok=True)

    output = agents_dir / f"{name}.yaml"
    if output.exists():
        typer.echo(f"Error: {output} already exists.", err=True)
        raise typer.Exit(code=1)

    output.write_text(_NEW_AGENT_TEMPLATE.format(name=name))
    typer.echo(f"Created {output}")


@app.command(name="list")
def list_agents() -> None:
    """List all agent YAML files in the agents/ directory."""
    agents_dir = Path.cwd() / "agents"
    if not agents_dir.is_dir():
        typer.echo("No agents/ directory found.")
        return

    files = sorted(agents_dir.glob("*.yaml"))
    if not files:
        typer.echo("No agents found in agents/.")
        return

    for f in files:
        typer.echo(f.name)


@app.command()
def tools() -> None:
    """List all built-in tools and their descriptions."""
    registry = _build_registry()
    schemas = registry.all_schemas()
    if not schemas:
        typer.echo("No tools registered.")
        return

    for schema in schemas:
        fn = schema["function"]
        name = fn["name"]
        desc = fn.get("description", "")
        typer.echo(f"  {name:<20} {desc}")


if __name__ == "__main__":
    app()
