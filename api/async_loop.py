"""Async agent loop for the web UI — streams events to an asyncio.Queue."""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

import litellm

from agent99.config import AgentConfig
from agent99.memory import BaseMemory, NoneMemory
from agent99.registry import ToolRegistry


@dataclass
class LoopEvent:
    type: str  # chunk | tool_call | tool_result | done | error | cancelled
    data: dict = field(default_factory=dict)


async def run_agent_async(
    config: AgentConfig,
    registry: ToolRegistry,
    user_input: str,
    queue: asyncio.Queue,
    memory: BaseMemory | None = None,
    stream: bool = True,
) -> str:
    """
    Run the agent loop asynchronously, pushing LoopEvents into queue.
    Returns the final text response.
    Raises asyncio.CancelledError if cancelled.
    """
    memory = memory or NoneMemory()
    tool_schemas = registry.schemas(config.tools) if config.tools else []

    messages: list[dict] = []
    if config.system_prompt:
        messages.append({"role": "system", "content": config.system_prompt})
    messages.extend(memory.history())
    messages.append({"role": "user", "content": user_input})

    base_kwargs: dict[str, Any] = {
        "model": config.model,
        "temperature": config.temperature,
    }
    if config.api_base:
        base_kwargs["api_base"] = config.api_base
    if tool_schemas:
        base_kwargs["tools"] = tool_schemas

    for _ in range(config.max_iterations):
        # Check for cancellation before each LLM call
        await asyncio.sleep(0)

        if stream:
            full_content, tool_calls_raw = await _stream_completion(
                messages, base_kwargs, queue
            )
        else:
            response = await litellm.acompletion(messages=messages, **base_kwargs)
            message = response.choices[0].message
            full_content = message.content or ""
            tool_calls_raw = message.tool_calls or []
            if full_content:
                await queue.put(LoopEvent("chunk", {"content": full_content}))

        if not tool_calls_raw:
            memory.add("user", user_input)
            memory.add("assistant", full_content)
            await queue.put(LoopEvent("done", {"content": full_content}))
            return full_content

        # Build assistant message
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                }
                for tc in tool_calls_raw
            ],
        })

        # Execute tools
        for tc in tool_calls_raw:
            await queue.put(LoopEvent("tool_call", {
                "id": tc["id"],
                "name": tc["name"],
                "arguments": tc["arguments"],
            }))
            try:
                fn = registry.get(tc["name"])
                result = str(fn(**tc["arguments"]))
            except Exception as e:
                result = f"Error: {type(e).__name__}: {e}"

            await queue.put(LoopEvent("tool_result", {
                "id": tc["id"],
                "name": tc["name"],
                "result": result,
            }))
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    await queue.put(LoopEvent("error", {"message": "max_iterations reached"}))
    raise RuntimeError(f"max_iterations ({config.max_iterations}) reached")


async def _stream_completion(
    messages: list[dict],
    kwargs: dict,
    queue: asyncio.Queue,
) -> tuple[str, list[dict]]:
    """Stream a litellm completion, pushing chunk events. Returns (content, tool_calls)."""
    full_content = ""
    # Accumulate tool calls: index → {id, name, arguments}
    tool_calls_acc: dict[int, dict] = {}

    response = await litellm.acompletion(messages=messages, stream=True, **kwargs)

    async for chunk in response:
        await asyncio.sleep(0)  # cancellation point
        delta = chunk.choices[0].delta

        if delta.content:
            full_content += delta.content
            await queue.put(LoopEvent("chunk", {"content": delta.content}))

        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                if tc_delta.id:
                    tool_calls_acc[idx]["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        tool_calls_acc[idx]["name"] += tc_delta.function.name
                    if tc_delta.function.arguments:
                        tool_calls_acc[idx]["arguments"] += tc_delta.function.arguments

    # Parse accumulated tool calls
    tool_calls = []
    for idx in sorted(tool_calls_acc):
        tc = tool_calls_acc[idx]
        try:
            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
        except json.JSONDecodeError:
            args = {"_raw": tc["arguments"]}
        tool_calls.append({"id": tc["id"], "name": tc["name"], "arguments": args})

    return full_content, tool_calls
