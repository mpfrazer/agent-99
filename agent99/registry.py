"""Tool auto-discovery and JSON schema generation from function signatures."""

import inspect
import re
from types import ModuleType
from typing import Callable, get_type_hints

# Mapping from Python types to JSON Schema types
_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _json_type(annotation: type) -> str:
    return _TYPE_MAP.get(annotation, "string")


def _parse_docstring(fn: Callable) -> tuple[str, dict[str, str]]:
    """Return (summary, {param_name: description}) parsed from a docstring."""
    doc = inspect.getdoc(fn) or ""
    if not doc:
        return "", {}

    # Summary: everything before the first blank line
    summary_lines = []
    for line in doc.splitlines():
        if line.strip() == "":
            break
        summary_lines.append(line.strip())
    summary = " ".join(summary_lines)

    # Google-style Args block: "Args:\n    name: description\n    ..."
    param_descs: dict[str, str] = {}
    args_match = re.search(r"Args:\s*\n((?:[ \t]+\S.*\n?)*)", doc)
    if args_match:
        for line in args_match.group(1).splitlines():
            m = re.match(r"[ \t]+(\w+)\s*:\s*(.*)", line)
            if m:
                param_descs[m.group(1)] = m.group(2).strip()

    return summary, param_descs


def build_schema(fn: Callable) -> dict:
    """Build an OpenAI-compatible tool schema from a plain Python function."""
    summary, param_descs = _parse_docstring(fn)
    hints = get_type_hints(fn)
    sig = inspect.signature(fn)

    properties: dict[str, dict] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name == "self" or param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        annotation = hints.get(name, str)
        prop: dict = {"type": _json_type(annotation)}
        desc = param_descs.get(name, "")
        if desc:
            prop["description"] = desc

        properties[name] = prop

        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": summary,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable] = {}

    def register(self, fn: Callable) -> None:
        self._tools[fn.__name__] = fn

    def register_module(self, module: ModuleType) -> None:
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("_") and obj.__module__ == module.__name__:
                self.register(obj)

    def get(self, name: str) -> Callable:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name!r}")
        return self._tools[name]

    def schemas(self, names: list[str]) -> list[dict]:
        return [build_schema(self.get(name)) for name in names]

    def all_schemas(self) -> list[dict]:
        return [build_schema(fn) for fn in self._tools.values()]
