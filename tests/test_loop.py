"""Tests for agent99.loop."""

import json
from unittest.mock import MagicMock

import pytest

from agent99.config import AgentConfig
from agent99.loop import AgentLoop
from agent99.memory import NoneMemory, SqliteMemory
from agent99.providers import LLMResponse, ToolCall
from agent99.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(**kwargs) -> AgentConfig:
    defaults = {"name": "test-agent", "model": "ollama/mistral"}
    return AgentConfig(**{**defaults, **kwargs})


def make_text_response(content: str) -> LLMResponse:
    return LLMResponse(content=content, tool_calls=[])


def make_tool_response(*calls: tuple) -> LLMResponse:
    """calls: [(id, name, arguments_dict), ...]"""
    return LLMResponse(
        content=None,
        tool_calls=[ToolCall(id=c[0], name=c[1], arguments=c[2]) for c in calls],
    )


def make_provider(*responses) -> MagicMock:
    provider = MagicMock()
    provider.complete.side_effect = list(responses)
    return provider


# ---------------------------------------------------------------------------
# Single-turn text response
# ---------------------------------------------------------------------------

def test_plain_text_response_returned():
    provider = make_provider(make_text_response("Hello!"))
    loop = AgentLoop(config=make_config(), provider=provider, registry=ToolRegistry())
    assert loop.run("hi") == "Hello!"


def test_empty_content_returns_empty_string():
    provider = make_provider(LLMResponse(content=None, tool_calls=[]))
    loop = AgentLoop(config=make_config(), provider=provider, registry=ToolRegistry())
    assert loop.run("hi") == ""


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def test_system_prompt_included_when_set():
    provider = make_provider(make_text_response("ok"))
    config = make_config(system_prompt="You are helpful.")
    AgentLoop(config=config, provider=provider, registry=ToolRegistry()).run("hi")

    messages = provider.complete.call_args.args[0]
    assert messages[0] == {"role": "system", "content": "You are helpful."}
    assert messages[1]["role"] == "user"


def test_system_prompt_omitted_when_empty():
    provider = make_provider(make_text_response("ok"))
    config = make_config(system_prompt="")
    AgentLoop(config=config, provider=provider, registry=ToolRegistry()).run("hi")

    messages = provider.complete.call_args.args[0]
    assert messages[0]["role"] == "user"


# ---------------------------------------------------------------------------
# Tool calls — use real typed functions so build_schema / get_type_hints work
# ---------------------------------------------------------------------------

def test_single_tool_call_executed():
    calls: list = []

    def read_file(path: str) -> str:
        """Read a file."""
        calls.append(path)
        return "file contents"

    config = make_config(tools=["read_file"])
    provider = make_provider(
        make_tool_response(("c1", "read_file", {"path": "/tmp/f"})),
        make_text_response("The file says: file contents"),
    )
    registry = ToolRegistry()
    registry.register(read_file)

    result = AgentLoop(config=config, provider=provider, registry=registry).run("read /tmp/f")

    assert calls == ["/tmp/f"]
    assert result == "The file says: file contents"


def test_multiple_tool_calls_in_one_response():
    calls_a: list = []
    calls_b: list = []

    def tool_a(x: str) -> str:
        """Tool A."""
        calls_a.append(x)
        return "result_a"

    def tool_b(y: str) -> str:
        """Tool B."""
        calls_b.append(y)
        return "result_b"

    config = make_config(tools=["tool_a", "tool_b"])
    provider = make_provider(
        make_tool_response(("c1", "tool_a", {"x": "1"}), ("c2", "tool_b", {"y": "2"})),
        make_text_response("done"),
    )
    registry = ToolRegistry()
    registry.register(tool_a)
    registry.register(tool_b)

    AgentLoop(config=config, provider=provider, registry=registry).run("go")

    assert calls_a == ["1"]
    assert calls_b == ["2"]


def test_tool_result_appended_as_tool_message():
    def my_tool() -> str:
        """A tool."""
        return "42"

    config = make_config(tools=["my_tool"])
    provider = make_provider(
        make_tool_response(("c1", "my_tool", {})),
        make_text_response("ok"),
    )
    registry = ToolRegistry()
    registry.register(my_tool)

    AgentLoop(config=config, provider=provider, registry=registry).run("go")

    second_messages = provider.complete.call_args_list[1].args[0]
    tool_msg = next(m for m in second_messages if m["role"] == "tool")
    assert tool_msg["tool_call_id"] == "c1"
    assert tool_msg["content"] == "42"


def test_tool_result_converted_to_str():
    def num_tool() -> int:
        """Returns an int."""
        return 12345

    config = make_config(tools=["num_tool"])
    provider = make_provider(
        make_tool_response(("c1", "num_tool", {})),
        make_text_response("ok"),
    )
    registry = ToolRegistry()
    registry.register(num_tool)

    AgentLoop(config=config, provider=provider, registry=registry).run("go")

    second_messages = provider.complete.call_args_list[1].args[0]
    tool_msg = next(m for m in second_messages if m["role"] == "tool")
    assert tool_msg["content"] == "12345"


# ---------------------------------------------------------------------------
# Tool errors
# ---------------------------------------------------------------------------

def test_tool_exception_becomes_error_observation():
    def read_file(path: str) -> str:
        """Read a file."""
        raise FileNotFoundError("no such file")

    config = make_config(tools=["read_file"])
    provider = make_provider(
        make_tool_response(("c1", "read_file", {"path": "/missing"})),
        make_text_response("I could not find the file."),
    )
    registry = ToolRegistry()
    registry.register(read_file)

    result = AgentLoop(config=config, provider=provider, registry=registry).run("read /missing")

    second_messages = provider.complete.call_args_list[1].args[0]
    tool_msg = next(m for m in second_messages if m["role"] == "tool")
    assert "FileNotFoundError" in tool_msg["content"]
    assert "no such file" in tool_msg["content"]
    assert result == "I could not find the file."


# ---------------------------------------------------------------------------
# Max iterations
# ---------------------------------------------------------------------------

def test_max_iterations_raises_runtime_error():
    def looping_tool() -> str:
        """Always called."""
        return "result"

    config = make_config(tools=["looping_tool"], max_iterations=3)
    provider = MagicMock()
    provider.complete.return_value = make_tool_response(("c1", "looping_tool", {}))

    registry = ToolRegistry()
    registry.register(looping_tool)

    with pytest.raises(RuntimeError, match="max_iterations"):
        AgentLoop(config=config, provider=provider, registry=registry).run("go forever")

    assert provider.complete.call_count == 3


# ---------------------------------------------------------------------------
# Tools schema forwarding
# ---------------------------------------------------------------------------

def test_no_tools_in_config_passes_none_to_provider():
    provider = make_provider(make_text_response("ok"))
    config = make_config(tools=[])
    AgentLoop(config=config, provider=provider, registry=ToolRegistry()).run("hi")

    _, kwargs = provider.complete.call_args
    assert kwargs.get("tools") is None


def test_tools_schema_passed_to_provider():
    def my_tool(x: str) -> str:
        """A tool."""

    provider = make_provider(make_text_response("ok"))
    config = make_config(tools=["my_tool"])
    registry = ToolRegistry()
    registry.register(my_tool)

    AgentLoop(config=config, provider=provider, registry=registry).run("hi")

    _, kwargs = provider.complete.call_args
    assert kwargs.get("tools") is not None
    assert kwargs["tools"][0]["function"]["name"] == "my_tool"


# ---------------------------------------------------------------------------
# Memory integration
# ---------------------------------------------------------------------------

def test_default_memory_is_none_memory():
    provider = make_provider(make_text_response("ok"))
    loop = AgentLoop(config=make_config(), provider=provider, registry=ToolRegistry())
    assert isinstance(loop.memory, NoneMemory)


def test_memory_history_prepended_after_system_prompt():
    memory = SqliteMemory()
    memory.add("user", "previous question")
    memory.add("assistant", "previous answer")

    provider = make_provider(make_text_response("new answer"))
    config = make_config(system_prompt="You are helpful.")
    AgentLoop(config=config, provider=provider, registry=ToolRegistry(), memory=memory).run("new question")

    messages = provider.complete.call_args.args[0]
    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "previous question"}
    assert messages[2] == {"role": "assistant", "content": "previous answer"}
    assert messages[3] == {"role": "user", "content": "new question"}


def test_memory_history_prepended_without_system_prompt():
    memory = SqliteMemory()
    memory.add("user", "old input")
    memory.add("assistant", "old output")

    provider = make_provider(make_text_response("ok"))
    AgentLoop(config=make_config(), provider=provider, registry=ToolRegistry(), memory=memory).run("hi")

    messages = provider.complete.call_args.args[0]
    assert messages[0] == {"role": "user", "content": "old input"}
    assert messages[1] == {"role": "assistant", "content": "old output"}
    assert messages[2] == {"role": "user", "content": "hi"}


def test_memory_saves_user_and_assistant_after_run():
    memory = SqliteMemory()
    provider = make_provider(make_text_response("the answer"))
    AgentLoop(config=make_config(), provider=provider, registry=ToolRegistry(), memory=memory).run("the question")

    assert memory.history() == [
        {"role": "user", "content": "the question"},
        {"role": "assistant", "content": "the answer"},
    ]


def test_memory_not_written_on_max_iterations():
    def looping_tool() -> str:
        """Loops."""
        return "x"

    memory = SqliteMemory()
    config = make_config(tools=["looping_tool"], max_iterations=2)
    provider = MagicMock()
    provider.complete.return_value = make_tool_response(("c1", "looping_tool", {}))

    registry = ToolRegistry()
    registry.register(looping_tool)

    with pytest.raises(RuntimeError):
        AgentLoop(config=config, provider=provider, registry=registry, memory=memory).run("go")

    assert memory.history() == []
