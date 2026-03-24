"""litellm wrapper providing a clean Provider interface for all LLM backends."""

import json
from dataclasses import dataclass, field
from typing import Any

import litellm


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = field(default=None, repr=False)


class Provider:
    def __init__(self, model: str, temperature: float = 0.7, **kwargs: Any) -> None:
        self.model = model
        self.temperature = temperature
        self._kwargs = kwargs

    def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            **self._kwargs,
        }
        if tools:
            kwargs["tools"] = tools

        response = litellm.completion(**kwargs)
        return self._parse(response)

    def _parse(self, response: Any) -> LLMResponse:
        message = response.choices[0].message
        content = message.content

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                ))

        return LLMResponse(content=content, tool_calls=tool_calls, raw=response)
