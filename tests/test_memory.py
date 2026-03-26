"""Tests for agent99.memory."""

from pathlib import Path

import pytest

from agent99.config import MemoryConfig
from agent99.memory import (
    BaseMemory,
    ChromadbMemory,
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
