"""Tests for agent99.memory."""

from pathlib import Path

import pytest

from agent99.config import MemoryConfig
from agent99.memory import (
    BaseMemory,
    ChromadbMemory,
    MarkdownMemory,
    NoneMemory,
    SqliteMemory,
    create_memory,
)

# ---------------------------------------------------------------------------
# NoneMemory
# ---------------------------------------------------------------------------

def test_none_memory_history_is_empty():
    m = NoneMemory()
    assert m.history() == []


def test_none_memory_add_is_noop():
    m = NoneMemory()
    m.add("user", "hello")
    m.add("assistant", "hi")
    assert m.history() == []


def test_none_memory_clear_is_noop():
    m = NoneMemory()
    m.clear()  # should not raise
    assert m.history() == []


def test_none_memory_is_base_memory():
    assert isinstance(NoneMemory(), BaseMemory)


# ---------------------------------------------------------------------------
# SqliteMemory — in-memory DB
# ---------------------------------------------------------------------------

def test_sqlite_history_empty_on_init():
    m = SqliteMemory()
    assert m.history() == []


def test_sqlite_add_and_history():
    m = SqliteMemory()
    m.add("user", "hello")
    m.add("assistant", "hi there")
    assert m.history() == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_sqlite_history_preserves_order():
    m = SqliteMemory()
    for i in range(5):
        m.add("user", str(i))
    contents = [msg["content"] for msg in m.history()]
    assert contents == ["0", "1", "2", "3", "4"]


def test_sqlite_roles_preserved():
    m = SqliteMemory()
    m.add("system", "You are helpful.")
    m.add("user", "question")
    m.add("assistant", "answer")
    roles = [msg["role"] for msg in m.history()]
    assert roles == ["system", "user", "assistant"]


def test_sqlite_clear_empties_history():
    m = SqliteMemory()
    m.add("user", "hello")
    m.add("assistant", "hi")
    m.clear()
    assert m.history() == []


def test_sqlite_add_after_clear():
    m = SqliteMemory()
    m.add("user", "first")
    m.clear()
    m.add("user", "second")
    assert m.history() == [{"role": "user", "content": "second"}]


def test_sqlite_is_base_memory():
    assert isinstance(SqliteMemory(), BaseMemory)


# ---------------------------------------------------------------------------
# SqliteMemory — file-based persistence
# ---------------------------------------------------------------------------

def test_sqlite_persists_to_file(tmp_path: Path):
    db_path = str(tmp_path / "memory.db")

    m1 = SqliteMemory(path=db_path)
    m1.add("user", "persisted message")

    m2 = SqliteMemory(path=db_path)
    assert m2.history() == [{"role": "user", "content": "persisted message"}]


# ---------------------------------------------------------------------------
# MarkdownMemory
# ---------------------------------------------------------------------------


def test_markdown_history_empty_on_init(tmp_path: Path):
    m = MarkdownMemory(path=str(tmp_path / "mem.md"))
    assert m.history() == []


def test_markdown_creates_file_on_init(tmp_path: Path):
    path = tmp_path / "mem.md"
    MarkdownMemory(path=str(path))
    assert path.exists()
    assert "# Agent Memory" in path.read_text()


def test_markdown_add_and_history(tmp_path: Path):
    m = MarkdownMemory(path=str(tmp_path / "mem.md"))
    m.add("user", "hello")
    m.add("assistant", "hi there")
    assert m.history() == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_markdown_history_preserves_order(tmp_path: Path):
    m = MarkdownMemory(path=str(tmp_path / "mem.md"))
    for i in range(5):
        m.add("user", str(i))
    contents = [msg["content"] for msg in m.history()]
    assert contents == ["0", "1", "2", "3", "4"]


def test_markdown_roles_preserved(tmp_path: Path):
    m = MarkdownMemory(path=str(tmp_path / "mem.md"))
    m.add("system", "You are helpful.")
    m.add("user", "question")
    m.add("assistant", "answer")
    roles = [msg["role"] for msg in m.history()]
    assert roles == ["system", "user", "assistant"]


def test_markdown_clear_empties_history(tmp_path: Path):
    m = MarkdownMemory(path=str(tmp_path / "mem.md"))
    m.add("user", "hello")
    m.add("assistant", "hi")
    m.clear()
    assert m.history() == []


def test_markdown_clear_keeps_file(tmp_path: Path):
    path = tmp_path / "mem.md"
    m = MarkdownMemory(path=str(path))
    m.add("user", "hello")
    m.clear()
    assert path.exists()
    assert "# Agent Memory" in path.read_text()


def test_markdown_add_after_clear(tmp_path: Path):
    m = MarkdownMemory(path=str(tmp_path / "mem.md"))
    m.add("user", "first")
    m.clear()
    m.add("user", "second")
    assert m.history() == [{"role": "user", "content": "second"}]


def test_markdown_multiline_content(tmp_path: Path):
    m = MarkdownMemory(path=str(tmp_path / "mem.md"))
    content = "line one\nline two\nline three"
    m.add("user", content)
    assert m.history() == [{"role": "user", "content": content}]


def test_markdown_persists_across_instances(tmp_path: Path):
    path = str(tmp_path / "mem.md")
    m1 = MarkdownMemory(path=path)
    m1.add("user", "persisted message")

    m2 = MarkdownMemory(path=path)
    assert m2.history() == [{"role": "user", "content": "persisted message"}]


def test_markdown_opens_existing_file(tmp_path: Path):
    """Opening a pre-existing memory file should not reset its contents."""
    path = str(tmp_path / "mem.md")
    m1 = MarkdownMemory(path=path)
    m1.add("user", "first")
    m1.add("assistant", "second")

    m2 = MarkdownMemory(path=path)
    assert len(m2.history()) == 2


def test_markdown_creates_parent_dirs(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "mem.md"
    m = MarkdownMemory(path=str(nested))
    m.add("user", "hello")
    assert nested.exists()
    assert m.history() == [{"role": "user", "content": "hello"}]


def test_markdown_is_base_memory(tmp_path: Path):
    m = MarkdownMemory(path=str(tmp_path / "mem.md"))
    assert isinstance(m, BaseMemory)


def test_markdown_file_is_human_readable(tmp_path: Path):
    path = tmp_path / "mem.md"
    m = MarkdownMemory(path=str(path))
    m.add("user", "What is the weather?")
    m.add("assistant", "It is sunny.")
    text = path.read_text()
    assert "## user" in text
    assert "## assistant" in text
    assert "What is the weather?" in text
    assert "It is sunny." in text


# ---------------------------------------------------------------------------
# ChromadbMemory
# ---------------------------------------------------------------------------

def test_chromadb_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="not yet implemented"):
        ChromadbMemory()


# ---------------------------------------------------------------------------
# create_memory factory
# ---------------------------------------------------------------------------

def test_factory_none():
    config = MemoryConfig(type="none")
    m = create_memory(config)
    assert isinstance(m, NoneMemory)


def test_factory_sqlite_default_path():
    config = MemoryConfig(type="sqlite")
    m = create_memory(config)
    assert isinstance(m, SqliteMemory)


def test_factory_sqlite_with_path(tmp_path: Path):
    db_path = str(tmp_path / "agent.db")
    config = MemoryConfig(type="sqlite", path=db_path)
    m = create_memory(config)
    assert isinstance(m, SqliteMemory)
    m.add("user", "hi")
    assert len(m.history()) == 1


def test_factory_chromadb_raises():
    config = MemoryConfig(type="chromadb")
    with pytest.raises(NotImplementedError):
        create_memory(config)


def test_factory_markdown_default_path(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = MemoryConfig(type="markdown")
    m = create_memory(config)
    assert isinstance(m, MarkdownMemory)
    assert (tmp_path / "memory.md").exists()


def test_factory_markdown_with_path(tmp_path: Path):
    md_path = str(tmp_path / "agent.md")
    config = MemoryConfig(type="markdown", path=md_path)
    m = create_memory(config)
    assert isinstance(m, MarkdownMemory)
    m.add("user", "hi")
    assert len(m.history()) == 1


def test_config_rejects_invalid_memory_type():
    with pytest.raises(Exception):
        MemoryConfig(type="invalid")  # type: ignore[arg-type]
