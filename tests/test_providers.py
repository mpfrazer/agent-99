"""Tests for agent99.providers."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent99.providers import LLMResponse, Provider, ToolCall


# ---------------------------------------------------------------------------
# Helpers — build fake litellm response objects
# ---------------------------------------------------------------------------

def make_response(content=None, tool_calls=None):
    """Build a minimal fake litellm response."""
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def make_tool_call(id, name, arguments: dict):
    return SimpleNamespace(
        id=id,
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        ),
    )


# ---------------------------------------------------------------------------
# LLMResponse / ToolCall construction
# ---------------------------------------------------------------------------

def test_tool_call_fields():
    tc = ToolCall(id="call_1", name="read_file", arguments={"path": "/tmp/f"})
    assert tc.id == "call_1"
    assert tc.name == "read_file"
    assert tc.arguments == {"path": "/tmp/f"}


def test_llm_response_defaults():
    r = LLMResponse(content="hello")
    assert r.content == "hello"
    assert r.tool_calls == []
    assert r.raw is None


# ---------------------------------------------------------------------------
# Provider.complete — text response
# ---------------------------------------------------------------------------

def test_plain_text_response():
    fake = make_response(content="Hello, world!")
    with patch("agent99.providers.litellm.completion", return_value=fake) as mock:
        provider = Provider(model="ollama/mistral")
        result = provider.complete([{"role": "user", "content": "hi"}])

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello, world!"
    assert result.tool_calls == []
    assert result.raw is fake


def test_model_and_temperature_forwarded():
    fake = make_response(content="ok")
    with patch("agent99.providers.litellm.completion", return_value=fake) as mock:
        Provider(model="anthropic/claude-3-5-sonnet-20241022", temperature=0.2).complete(
            [{"role": "user", "content": "hi"}]
        )

    call_kwargs = mock.call_args.kwargs
    assert call_kwargs["model"] == "anthropic/claude-3-5-sonnet-20241022"
    assert call_kwargs["temperature"] == 0.2


def test_extra_kwargs_forwarded():
    fake = make_response(content="ok")
    with patch("agent99.providers.litellm.completion", return_value=fake) as mock:
        Provider(model="ollama/mistral", max_tokens=512).complete(
            [{"role": "user", "content": "hi"}]
        )

    assert mock.call_args.kwargs["max_tokens"] == 512


# ---------------------------------------------------------------------------
# Provider.complete — tool call response
# ---------------------------------------------------------------------------

def test_single_tool_call():
    tc = make_tool_call("call_abc", "read_file", {"path": "/etc/hosts"})
    fake = make_response(content=None, tool_calls=[tc])

    with patch("agent99.providers.litellm.completion", return_value=fake):
        result = Provider(model="ollama/mistral").complete(
            [{"role": "user", "content": "read /etc/hosts"}],
            tools=[{"type": "function", "function": {"name": "read_file"}}],
        )

    assert result.content is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_abc"
    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[0].arguments == {"path": "/etc/hosts"}


def test_multiple_tool_calls():
    tcs = [
        make_tool_call("c1", "read_file", {"path": "/a"}),
        make_tool_call("c2", "list_dir", {"path": "/tmp"}),
    ]
    fake = make_response(content=None, tool_calls=tcs)

    with patch("agent99.providers.litellm.completion", return_value=fake):
        result = Provider(model="ollama/mistral").complete([])

    assert len(result.tool_calls) == 2
    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[1].name == "list_dir"


def test_tools_schema_forwarded_to_litellm():
    fake = make_response(content="ok")
    schema = [{"type": "function", "function": {"name": "read_file"}}]

    with patch("agent99.providers.litellm.completion", return_value=fake) as mock:
        Provider(model="ollama/mistral").complete([], tools=schema)

    assert mock.call_args.kwargs["tools"] == schema


def test_tools_not_forwarded_when_none():
    fake = make_response(content="ok")

    with patch("agent99.providers.litellm.completion", return_value=fake) as mock:
        Provider(model="ollama/mistral").complete([])

    assert "tools" not in mock.call_args.kwargs


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------

def test_litellm_exception_propagates():
    with patch("agent99.providers.litellm.completion", side_effect=RuntimeError("timeout")):
        with pytest.raises(RuntimeError, match="timeout"):
            Provider(model="ollama/mistral").complete([])
