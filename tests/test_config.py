"""Tests for agent99.config."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from agent99.config import AgentConfig, MemoryConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_DATA = {
    "name": "test-agent",
    "model": "ollama/mistral",
    "description": "A test agent",
    "system_prompt": "You are helpful.",
    "tools": ["read_file"],
    "memory": {"type": "none"},
    "max_iterations": 10,
    "temperature": 0.5,
}


# ---------------------------------------------------------------------------
# MemoryConfig
# ---------------------------------------------------------------------------


def test_memory_defaults():
    m = MemoryConfig()
    assert m.type == "none"
    assert m.path is None


def test_memory_sqlite():
    m = MemoryConfig(type="sqlite", path="/tmp/agent.db")
    assert m.type == "sqlite"
    assert m.path == "/tmp/agent.db"


def test_memory_invalid_type():
    with pytest.raises(ValidationError):
        MemoryConfig(type="redis")


# ---------------------------------------------------------------------------
# AgentConfig — valid
# ---------------------------------------------------------------------------


def test_valid_config_loads():
    cfg = AgentConfig.model_validate(VALID_DATA)
    assert cfg.name == "test-agent"
    assert cfg.model == "ollama/mistral"
    assert cfg.tools == ["read_file"]
    assert cfg.max_iterations == 10
    assert cfg.temperature == 0.5


def test_defaults_applied():
    cfg = AgentConfig(name="minimal", model="ollama/mistral")
    assert cfg.description == ""
    assert cfg.system_prompt == ""
    assert cfg.tools == []
    assert cfg.memory.type == "none"
    assert cfg.max_iterations == 20
    assert cfg.temperature == 0.7


def test_tools_default_is_independent():
    a = AgentConfig(name="a", model="ollama/mistral")
    b = AgentConfig(name="b", model="ollama/mistral")
    a.tools.append("read_file")
    assert b.tools == []


# ---------------------------------------------------------------------------
# AgentConfig — validation failures
# ---------------------------------------------------------------------------


def test_missing_name_raises():
    with pytest.raises(ValidationError):
        AgentConfig(model="ollama/mistral")


def test_empty_name_raises():
    with pytest.raises(ValidationError):
        AgentConfig(name="   ", model="ollama/mistral")


def test_missing_model_raises():
    with pytest.raises(ValidationError):
        AgentConfig(name="agent")


def test_empty_model_raises():
    with pytest.raises(ValidationError):
        AgentConfig(name="agent", model="")


def test_temperature_too_low():
    with pytest.raises(ValidationError):
        AgentConfig(name="agent", model="ollama/mistral", temperature=-0.1)


def test_temperature_too_high():
    with pytest.raises(ValidationError):
        AgentConfig(name="agent", model="ollama/mistral", temperature=2.1)


def test_temperature_boundaries_valid():
    AgentConfig(name="a", model="ollama/mistral", temperature=0.0)
    AgentConfig(name="b", model="ollama/mistral", temperature=2.0)


def test_max_iterations_zero_raises():
    with pytest.raises(ValidationError):
        AgentConfig(name="agent", model="ollama/mistral", max_iterations=0)


def test_max_iterations_negative_raises():
    with pytest.raises(ValidationError):
        AgentConfig(name="agent", model="ollama/mistral", max_iterations=-5)


def test_max_iterations_one_valid():
    cfg = AgentConfig(name="agent", model="ollama/mistral", max_iterations=1)
    assert cfg.max_iterations == 1


# ---------------------------------------------------------------------------
# from_yaml
# ---------------------------------------------------------------------------


def test_from_yaml_round_trip(tmp_path: Path):
    yaml_content = """\
name: yaml-agent
model: ollama/llama3
description: Loaded from YAML
tools:
  - read_file
  - list_dir
memory:
  type: sqlite
  path: /tmp/test.db
max_iterations: 5
temperature: 1.0
"""
    f = tmp_path / "agent.yaml"
    f.write_text(yaml_content)

    cfg = AgentConfig.from_yaml(f)
    assert cfg.name == "yaml-agent"
    assert cfg.model == "ollama/llama3"
    assert cfg.tools == ["read_file", "list_dir"]
    assert cfg.memory.type == "sqlite"
    assert cfg.memory.path == "/tmp/test.db"
    assert cfg.max_iterations == 5
    assert cfg.temperature == 1.0


def test_from_yaml_example_file():
    example = Path(__file__).parent.parent / "agents" / "example.yaml"
    cfg = AgentConfig.from_yaml(example)
    assert cfg.name == "file-reader"
    assert cfg.model == "ollama/mistral"


def test_from_yaml_missing_file():
    with pytest.raises(ValueError, match="not found"):
        AgentConfig.from_yaml("/nonexistent/path/agent.yaml")


def test_from_yaml_invalid_yaml(tmp_path: Path):
    f = tmp_path / "bad.yaml"
    f.write_text("name: [unclosed bracket")
    with pytest.raises(ValueError, match="Invalid YAML"):
        AgentConfig.from_yaml(f)


def test_from_yaml_invalid_config(tmp_path: Path):
    f = tmp_path / "invalid.yaml"
    f.write_text("name: agent\ntemperature: 99\n")
    with pytest.raises(ValueError, match="Invalid agent config"):
        AgentConfig.from_yaml(f)
