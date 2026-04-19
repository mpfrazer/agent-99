"""Agent loop: think → act → observe, repeat."""

import json
import time
from collections.abc import Callable

from agent99.config import AgentConfig
from agent99.memory import BaseMemory, NoneMemory
from agent99.providers import Provider
from agent99.registry import ToolRegistry


def make_spawn_subagent(parent_config: AgentConfig, parent_registry: ToolRegistry) -> Callable:
    """Return a spawn_subagent tool function bound to the parent agent's context."""

    def spawn_subagent(
        task: str,
        system_prompt: str = "",
        tools: str = "",
        name: str = "subagent",
        model: str = "",
    ) -> str:
        """Create and run a focused subagent to complete a specific task. Returns the subagent's final response.

        Args:
            task: The task description or prompt to send to the subagent.
            system_prompt: Optional system prompt to define the subagent's behavior and focus.
            tools: Comma-separated tool names the subagent can use (e.g. "read_file,search_google"). Leave empty for no tools.
            name: A short descriptive label for this subagent.
            model: Model override for the subagent. Leave empty to inherit from the parent agent.
        """
        sub_config = AgentConfig(
            name=name or "subagent",
            model=model.strip() or parent_config.model,
            system_prompt=system_prompt,
            tools=[t.strip() for t in tools.split(",") if t.strip()],
            max_iterations=max(1, parent_config.max_iterations // 2),
            temperature=parent_config.temperature,
            api_base=parent_config.api_base,
        )

        sub_registry = ToolRegistry()
        for tool_name in sub_config.tools:
            try:
                sub_registry.register(parent_registry.get(tool_name))
            except KeyError:
                pass

        provider = Provider(
            model=sub_config.model,
            temperature=sub_config.temperature,
            **({"api_base": sub_config.api_base} if sub_config.api_base else {}),
        )

        try:
            return AgentLoop(config=sub_config, provider=provider, registry=sub_registry).run(task)
        except RuntimeError as e:
            return f"Subagent '{sub_config.name}' error: {e}"

    return spawn_subagent


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
        self.memory = memory if memory is not None else NoneMemory()
        self._tool_schemas = registry.schemas(config.tools) if config.tools else []

        if config.allow_subagents:
            spawn_fn = make_spawn_subagent(config, registry)
            extended = ToolRegistry()
            extended._tools = {**registry._tools, "spawn_subagent": spawn_fn}
            self.registry = extended
            self._tool_schemas = self._tool_schemas + extended.schemas(["spawn_subagent"])
        else:
            self.registry = registry

    def run(self, user_input: str) -> str:
        """Run the agent loop and return the final text response."""
        messages: list[dict] = []

        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})

        messages.extend(self.memory.history())

        messages.append({"role": "user", "content": user_input})

        for i in range(self.config.max_iterations):
            if self.config.request_delay > 0 and i > 0:
                time.sleep(self.config.request_delay)

            backoff = 5.0
            while True:
                try:
                    response = self.provider.complete(
                        messages,
                        tools=self._tool_schemas if self._tool_schemas else None,
                    )
                    break
                except Exception as exc:
                    import litellm
                    if isinstance(exc, litellm.RateLimitError):
                        print(f"Rate limit hit — retrying in {backoff:.0f}s")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 120)
                    else:
                        raise

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
