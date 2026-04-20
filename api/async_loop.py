"""Async agent loop for the web UI — streams events to an asyncio.Queue."""

import asyncio
import json
import traceback
from dataclasses import dataclass, field
from typing import Any

import litellm

from agent99.config import AgentConfig
from agent99.loop import make_spawn_subagent
from agent99.memory import BaseMemory, NoneMemory
from agent99.registry import ToolRegistry


@dataclass
class LoopEvent:
    type: str  # chunk | tool_call | tool_result | done | error | cancelled | debug
    data: dict = field(default_factory=dict)


async def _dbg(queue: asyncio.Queue, message: str, level: str = "info") -> None:
    """Emit a debug event into the queue."""
    await queue.put(LoopEvent("debug", {"message": message, "level": level}))


async def run_agent_async(
    config: AgentConfig,
    registry: ToolRegistry,
    user_input: str,
    queue: asyncio.Queue,
    memory: BaseMemory | None = None,
    stream: bool = True,
    debug: bool = False,
) -> str:
    """
    Run the agent loop asynchronously, pushing LoopEvents into queue.
    Returns the final text response.
    Raises asyncio.CancelledError if cancelled.
    """
    memory = memory or NoneMemory()
    tool_schemas = registry.schemas(config.tools) if config.tools else []

    if config.allow_subagents:
        spawn_fn = make_spawn_subagent(config, registry)
        extended = ToolRegistry()
        extended._tools = {**registry._tools, "spawn_subagent": spawn_fn}
        registry = extended
        tool_schemas = tool_schemas + registry.schemas(["spawn_subagent"])

    messages: list[dict] = []
    if config.system_prompt:
        messages.append({"role": "system", "content": config.system_prompt})
    messages.extend(memory.history())
    messages.append({"role": "user", "content": user_input})

    # litellm's `ollama/` prefix uses the completion API which silently drops tool
    # calls. `ollama_chat/` uses the chat API and correctly surfaces them.
    effective_model = config.model
    if tool_schemas and effective_model.startswith("ollama/"):
        effective_model = "ollama_chat/" + effective_model[len("ollama/"):]

    base_kwargs: dict[str, Any] = {
        "model": effective_model,
        "temperature": config.temperature,
    }
    if config.api_base:
        base_kwargs["api_base"] = config.api_base
    if tool_schemas:
        base_kwargs["tools"] = tool_schemas

    if debug:
        tool_names = config.tools or []
        model_note = " (rewritten from ollama/ to ollama_chat/ for tool support)" if effective_model != config.model else ""
        await _dbg(queue, (
            f"Agent run starting\n"
            f"  model:          {effective_model}{model_note}\n"
            f"  api_base:       {config.api_base or '(default)'}\n"
            f"  tools:          {len(tool_schemas)} registered ({', '.join(tool_names) or 'none'})\n"
            f"  max_iterations: {config.max_iterations}\n"
            f"  temperature:    {config.temperature}\n"
            f"  system_prompt:  {'yes' if config.system_prompt else 'no'}\n"
            f"  stream:         {stream}"
        ))
        if effective_model != config.model:
            await _dbg(queue, (
                f"NOTE: Model was automatically rewritten from '{config.model}' to '{effective_model}'. "
                f"The 'ollama/' prefix in litellm uses the completion API which does not surface tool calls. "
                f"Update your agent config to use 'ollama_chat/' to suppress this message."
            ), level="warning")

    for i in range(config.max_iterations):
        # Proactive delay between iterations (rate-limit tuning)
        if config.request_delay > 0 and i > 0:
            if debug:
                await _dbg(queue, f"Waiting {config.request_delay}s (request_delay) before next LLM call")
            await asyncio.sleep(config.request_delay)

        # Check for cancellation before each LLM call
        await asyncio.sleep(0)

        if debug:
            await _dbg(queue, f"Iteration {i + 1}/{config.max_iterations} — sending {len(messages)} message(s) to LLM")

        backoff = 5.0
        full_content: str = ""
        tool_calls_raw: list[dict] = []
        while True:
            try:
                if stream:
                    full_content, tool_calls_raw = await _stream_completion(
                        messages, base_kwargs, queue, debug=debug
                    )
                else:
                    response = await litellm.acompletion(messages=messages, **base_kwargs)
                    message = response.choices[0].message
                    full_content = message.content or ""
                    tool_calls_raw = message.tool_calls or []

                    if debug:
                        finish_reason = response.choices[0].finish_reason
                        reasoning = getattr(message, "reasoning_content", None) or ""
                        usage = getattr(response, "usage", None)
                        usage_str = (
                            f", tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out"
                            if usage else ""
                        )
                        await _dbg(queue, (
                            f"LLM response — finish_reason={finish_reason!r}, "
                            f"content={len(full_content)} chars, "
                            f"tool_calls={len(tool_calls_raw)}{usage_str}"
                        ))
                        if reasoning:
                            await _dbg(queue, (
                                f"Model thinking/reasoning content detected ({len(reasoning)} chars). "
                                f"This is internal chain-of-thought output and is NOT included in the "
                                f"final response. If the response appears empty, the model may have "
                                f"spent all its output on reasoning without producing visible text."
                            ), level="warning")
                        if not full_content and not tool_calls_raw:
                            await _dbg(queue, (
                                "LLM returned empty content with no tool calls — the run will complete "
                                "with no output. Possible causes: (1) model is in thinking-only mode "
                                "(qwen3/deepseek-r1 with reasoning disabled in litellm), "
                                "(2) connection reached the model but response body was empty, "
                                "(3) model does not support the tool schema format."
                            ), level="warning")

                    if full_content:
                        await queue.put(LoopEvent("chunk", {"content": full_content}))

                break  # successful call — exit retry loop

            except asyncio.CancelledError:
                raise
            except litellm.RateLimitError:
                await queue.put(LoopEvent("rate_limit", {"retry_in": backoff}))
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 120)
                full_content, tool_calls_raw = "", []  # reset accumulators before retry
            except Exception as exc:
                if debug:
                    await _dbg(queue, (
                        f"LLM call raised {type(exc).__name__}: {exc}\n"
                        f"{traceback.format_exc()}"
                    ), level="error")
                raise

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
    debug: bool = False,
) -> tuple[str, list[dict]]:
    """Stream a litellm completion, pushing chunk events. Returns (content, tool_calls)."""
    full_content = ""
    full_reasoning = ""
    finish_reason: str | None = None
    # Accumulate tool calls: index → {id, name, arguments}
    tool_calls_acc: dict[int, dict] = {}

    response = await litellm.acompletion(messages=messages, stream=True, **kwargs)

    async for chunk in response:
        await asyncio.sleep(0)  # cancellation point
        choice = chunk.choices[0]
        delta = choice.delta

        if choice.finish_reason:
            finish_reason = choice.finish_reason

        if delta.content:
            full_content += delta.content
            await queue.put(LoopEvent("chunk", {"content": delta.content}))

        # Capture thinking/reasoning tokens from models like qwen3, deepseek-r1
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            full_reasoning += reasoning

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

    if debug:
        await _dbg(queue, (
            f"LLM stream complete — finish_reason={finish_reason!r}, "
            f"content={len(full_content)} chars, tool_calls={len(tool_calls)}"
            + (f", reasoning={len(full_reasoning)} chars" if full_reasoning else "")
        ))
        if full_reasoning:
            await _dbg(queue, (
                f"Model thinking/reasoning content detected ({len(full_reasoning)} chars). "
                f"This is internal chain-of-thought output and is NOT included in the "
                f"final response. If the response appears empty, the model may have "
                f"spent all its output on reasoning without producing visible text."
            ), level="warning")
        if not full_content and not tool_calls:
            await _dbg(queue, (
                "LLM returned empty content with no tool calls — the run will complete "
                "with no output. Possible causes: (1) model is in thinking-only mode "
                "(qwen3/deepseek-r1 with reasoning output suppressed by litellm), "
                "(2) connection reached the model but response body was empty, "
                "(3) model does not support the tool schema format sent."
            ), level="warning")

    return full_content, tool_calls
