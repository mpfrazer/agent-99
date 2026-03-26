"""Tests for agent99.registry and tools/filesystem.py schema generation."""

import sys
from pathlib import Path

import pytest

# Make the tools/ package importable from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.filesystem as filesystem_module
from agent99.registry import ToolRegistry, build_schema

# ---------------------------------------------------------------------------
# Fixture functions used as test subjects
# ---------------------------------------------------------------------------

def simple(x: str, y: int = 0) -> str:
    """Do something simple.

    Args:
        x: The input string.
        y: An optional integer.
    """
    return x


def no_doc(a: str, b: float) -> bool:
    pass


def all_types(s: str, i: int, f: float, b: bool, u) -> None:
    """All types.

    Args:
        s: A string.
        i: An integer.
        f: A float.
        b: A boolean.
        u: Unknown type.
    """


def no_params() -> str:
    """A function with no parameters."""


# ---------------------------------------------------------------------------
# build_schema — structure
# ---------------------------------------------------------------------------

def test_schema_top_level_structure():
    schema = build_schema(simple)
    assert schema["type"] == "function"
    assert "function" in schema
    fn = schema["function"]
    assert fn["name"] == "simple"
    assert "description" in fn
    assert "parameters" in fn
    assert fn["parameters"]["type"] == "object"


def test_schema_description_from_first_docstring_line():
    schema = build_schema(simple)
    assert schema["function"]["description"] == "Do something simple."


def test_schema_no_docstring_gives_empty_description():
    schema = build_schema(no_doc)
    assert schema["function"]["description"] == ""


# ---------------------------------------------------------------------------
# build_schema — required vs optional
# ---------------------------------------------------------------------------

def test_required_includes_params_without_defaults():
    schema = build_schema(simple)
    assert "x" in schema["function"]["parameters"]["required"]


def test_required_excludes_params_with_defaults():
    schema = build_schema(simple)
    assert "y" not in schema["function"]["parameters"]["required"]


def test_all_required_when_no_defaults():
    schema = build_schema(no_doc)
    required = schema["function"]["parameters"]["required"]
    assert "a" in required
    assert "b" in required


def test_empty_required_when_no_params():
    schema = build_schema(no_params)
    assert schema["function"]["parameters"]["required"] == []
    assert schema["function"]["parameters"]["properties"] == {}


# ---------------------------------------------------------------------------
# build_schema — type mapping
# ---------------------------------------------------------------------------

def test_type_mapping():
    schema = build_schema(all_types)
    props = schema["function"]["parameters"]["properties"]
    assert props["s"]["type"] == "string"
    assert props["i"]["type"] == "integer"
    assert props["f"]["type"] == "number"
    assert props["b"]["type"] == "boolean"
    assert props["u"]["type"] == "string"   # unknown → string fallback


# ---------------------------------------------------------------------------
# build_schema — per-param descriptions
# ---------------------------------------------------------------------------

def test_param_descriptions_from_args_block():
    schema = build_schema(simple)
    props = schema["function"]["parameters"]["properties"]
    assert props["x"]["description"] == "The input string."
    assert props["y"]["description"] == "An optional integer."


def test_no_description_key_when_no_args_block():
    schema = build_schema(no_doc)
    props = schema["function"]["parameters"]["properties"]
    assert "description" not in props["a"]
    assert "description" not in props["b"]


# ---------------------------------------------------------------------------
# ToolRegistry — register / get
# ---------------------------------------------------------------------------

def test_register_and_get():
    reg = ToolRegistry()
    reg.register(simple)
    assert reg.get("simple") is simple


def test_get_unknown_raises_key_error():
    reg = ToolRegistry()
    with pytest.raises(KeyError, match="unknown_tool"):
        reg.get("unknown_tool")


# ---------------------------------------------------------------------------
# ToolRegistry — register_module
# ---------------------------------------------------------------------------

def test_register_module_picks_up_public_functions():
    reg = ToolRegistry()
    reg.register_module(filesystem_module)
    assert reg.get("read_file") is filesystem_module.read_file
    assert reg.get("write_file") is filesystem_module.write_file
    assert reg.get("list_dir") is filesystem_module.list_dir


def test_register_module_excludes_private_functions():
    reg = ToolRegistry()
    reg.register_module(filesystem_module)
    for name in reg._tools:
        assert not name.startswith("_")


# ---------------------------------------------------------------------------
# ToolRegistry — schemas / all_schemas
# ---------------------------------------------------------------------------

def test_schemas_returns_subset():
    reg = ToolRegistry()
    reg.register(simple)
    reg.register(no_params)
    result = reg.schemas(["simple"])
    assert len(result) == 1
    assert result[0]["function"]["name"] == "simple"


def test_all_schemas_returns_every_tool():
    reg = ToolRegistry()
    reg.register(simple)
    reg.register(no_params)
    result = reg.all_schemas()
    names = {s["function"]["name"] for s in result}
    assert names == {"simple", "no_params"}


def test_schemas_unknown_name_raises():
    reg = ToolRegistry()
    with pytest.raises(KeyError):
        reg.schemas(["nonexistent"])


# ---------------------------------------------------------------------------
# Integration — filesystem tool schemas are valid
# ---------------------------------------------------------------------------

def test_read_file_schema():
    schema = build_schema(filesystem_module.read_file)
    fn = schema["function"]
    assert fn["name"] == "read_file"
    props = fn["parameters"]["properties"]
    assert "path" in props
    assert "encoding" in props
    assert props["path"]["type"] == "string"
    assert "path" in fn["parameters"]["required"]
    assert "encoding" not in fn["parameters"]["required"]


def test_list_dir_schema():
    schema = build_schema(filesystem_module.list_dir)
    fn = schema["function"]
    assert fn["name"] == "list_dir"
    assert "path" in fn["parameters"]["required"]
