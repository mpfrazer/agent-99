"""Tests for agent99.cli."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from agent99.cli import app

runner = CliRunner()

VALID_YAML = """\
name: test-agent
model: ollama/mistral
system_prompt: You are helpful.
tools: []
max_iterations: 5
temperature: 0.5
"""

INVALID_YAML = """\
name: test-agent
temperature: 99
"""


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------

def test_run_with_input_flag(tmp_path: Path):
    agent_file = tmp_path / "agent.yaml"
    agent_file.write_text(VALID_YAML)

    with patch("agent99.cli.AgentLoop") as MockLoop:
        MockLoop.return_value.run.return_value = "The answer is 42."
        result = runner.invoke(app, ["run", str(agent_file), "--input", "What is 6x7?"])

    assert result.exit_code == 0
    assert "The answer is 42." in result.output
    MockLoop.return_value.run.assert_called_once_with("What is 6x7?")


def test_run_reads_stdin_when_no_input(tmp_path: Path):
    agent_file = tmp_path / "agent.yaml"
    agent_file.write_text(VALID_YAML)

    with patch("agent99.cli.AgentLoop") as MockLoop:
        MockLoop.return_value.run.return_value = "stdin response"
        result = runner.invoke(app, ["run", str(agent_file)], input="hello from stdin")

    assert result.exit_code == 0
    MockLoop.return_value.run.assert_called_once_with("hello from stdin")


def test_run_exits_1_on_bad_yaml_config(tmp_path: Path):
    agent_file = tmp_path / "agent.yaml"
    agent_file.write_text(INVALID_YAML)

    result = runner.invoke(app, ["run", str(agent_file), "--input", "hi"])

    assert result.exit_code == 1
    assert result.output == "" or "Invalid" in result.output or result.exit_code == 1


def test_run_exits_1_on_missing_file(tmp_path: Path):
    result = runner.invoke(app, ["run", str(tmp_path / "missing.yaml"), "--input", "hi"])
    assert result.exit_code == 1


def test_run_exits_1_on_runtime_error(tmp_path: Path):
    agent_file = tmp_path / "agent.yaml"
    agent_file.write_text(VALID_YAML)

    with patch("agent99.cli.AgentLoop") as MockLoop:
        MockLoop.return_value.run.side_effect = RuntimeError("max_iterations reached")
        result = runner.invoke(app, ["run", str(agent_file), "--input", "go"])

    assert result.exit_code == 1
    assert "max_iterations" in result.output


# ---------------------------------------------------------------------------
# new command
# ---------------------------------------------------------------------------

def test_new_creates_yaml_file(tmp_path: Path):
    with patch("agent99.cli.Path.cwd", return_value=tmp_path):
        result = runner.invoke(app, ["new", "my-agent"])

    assert result.exit_code == 0
    created = tmp_path / "agents" / "my-agent.yaml"
    assert created.exists()
    content = created.read_text()
    assert "name: my-agent" in content


def test_new_prints_created_path(tmp_path: Path):
    with patch("agent99.cli.Path.cwd", return_value=tmp_path):
        result = runner.invoke(app, ["new", "my-agent"])

    assert "my-agent.yaml" in result.output


def test_new_fails_if_file_exists(tmp_path: Path):
    with patch("agent99.cli.Path.cwd", return_value=tmp_path):
        runner.invoke(app, ["new", "my-agent"])          # first: ok
        result = runner.invoke(app, ["new", "my-agent"]) # second: should fail

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_new_creates_agents_dir_if_missing(tmp_path: Path):
    with patch("agent99.cli.Path.cwd", return_value=tmp_path):
        result = runner.invoke(app, ["new", "fresh"])

    assert result.exit_code == 0
    assert (tmp_path / "agents").is_dir()


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------

def test_list_shows_yaml_files(tmp_path: Path):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "alpha.yaml").write_text("name: alpha\nmodel: x\n")
    (agents_dir / "beta.yaml").write_text("name: beta\nmodel: x\n")

    with patch("agent99.cli.Path.cwd", return_value=tmp_path):
        result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "alpha.yaml" in result.output
    assert "beta.yaml" in result.output


def test_list_friendly_message_when_empty(tmp_path: Path):
    (tmp_path / "agents").mkdir()

    with patch("agent99.cli.Path.cwd", return_value=tmp_path):
        result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No agents" in result.output


def test_list_friendly_message_when_no_dir(tmp_path: Path):
    with patch("agent99.cli.Path.cwd", return_value=tmp_path):
        result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No agents" in result.output


# ---------------------------------------------------------------------------
# tools command
# ---------------------------------------------------------------------------

def test_tools_lists_built_in_tools():
    result = runner.invoke(app, ["tools"])

    assert result.exit_code == 0
    assert "read_file" in result.output
    assert "write_file" in result.output
    assert "list_dir" in result.output


def test_tools_includes_description():
    result = runner.invoke(app, ["tools"])

    assert result.exit_code == 0
    # read_file's description starts with "Read the contents"
    assert "Read" in result.output


# ---------------------------------------------------------------------------
# memory integration
# ---------------------------------------------------------------------------

def test_run_passes_memory_to_agent_loop(tmp_path: Path):
    agent_file = tmp_path / "agent.yaml"
    agent_file.write_text(VALID_YAML)

    with patch("agent99.cli.AgentLoop") as MockLoop, \
         patch("agent99.cli.create_memory") as mock_create_memory:
        MockLoop.return_value.run.return_value = "ok"
        mock_memory = MagicMock()
        mock_create_memory.return_value = mock_memory

        runner.invoke(app, ["run", str(agent_file), "--input", "hi"])

    mock_create_memory.assert_called_once()
    _, kwargs = MockLoop.call_args
    assert kwargs["memory"] is mock_memory
