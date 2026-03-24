"""Agent loop: think → act → observe, repeat."""

import json

from agent99.config import AgentConfig
from agent99.memory import BaseMemory, NoneMemory
from agent99.providers import Provider
from agent99.registry import ToolRegistry


class AgentLoop:
    def __init__(
        self,
        config: AgentConfig,
        provider: Provider,
        registry: ToolRegistry,
        memory: BaseMemory | None = None,
    ) -> None:
        self.config = config
        self.provider = provider
        self.registry = registry
        self.memory = memory if memory is not None else NoneMemory()
        self._tool_schemas = registry.schemas(config.tools) if config.tools else []

    def run(self, user_input: str) -> str:
        """Run the agent loop and return the final text response."""
        messages: list[dict] = []

        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})

        messages.extend(self.memory.history())

        messages.append({"role": "user", "content": user_input})

        for _ in range(self.config.max_iterations):
            response = self.provider.complete(
                messages,
                tools=self._tool_schemas if self._tool_schemas else None,
            )

            if not response.tool_calls:
                result = response.content or ""
                self.memory.add("user", user_input)
                self.memory.add("assistant", result)
                return result

            # Append assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in response.tool_calls
                ],
            })

            # Execute each tool and append its result
            for tc in response.tool_calls:
                try:
                    fn = self.registry.get(tc.name)
                    result = str(fn(**tc.arguments))
                except Exception as e:
                    result = f"Error: {type(e).__name__}: {e}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        raise RuntimeError(
            f"Agent '{self.config.name}' reached max_iterations "
            f"({self.config.max_iterations}) without a final response."
        )
