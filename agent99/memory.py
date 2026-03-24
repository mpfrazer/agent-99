"""Agent memory backends: none, sqlite, chromadb."""

import sqlite3
from datetime import datetime, timezone

from agent99.config import MemoryConfig


class BaseMemory:
    def add(self, role: str, content: str) -> None:
        raise NotImplementedError

    def history(self) -> list[dict]:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class NoneMemory(BaseMemory):
    def add(self, role: str, content: str) -> None:
        pass

    def history(self) -> list[dict]:
        return []

    def clear(self) -> None:
        pass


class SqliteMemory(BaseMemory):
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def add(self, role: str, content: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
            (role, content, now),
        )
        self._conn.commit()

    def history(self) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT role, content FROM messages ORDER BY id"
        )
        return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

    def clear(self) -> None:
        self._conn.execute("DELETE FROM messages")
        self._conn.commit()


class ChromadbMemory(BaseMemory):
    def __init__(self, path: str | None = None) -> None:
        raise NotImplementedError(
            "ChromaDB memory is not yet implemented. "
            "Use type: none or type: sqlite in your agent config."
        )

    def add(self, role: str, content: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def history(self) -> list[dict]:  # pragma: no cover
        raise NotImplementedError

    def clear(self) -> None:  # pragma: no cover
        raise NotImplementedError


def create_memory(config: MemoryConfig) -> BaseMemory:
    """Instantiate the appropriate memory backend from a MemoryConfig."""
    if config.type == "none":
        return NoneMemory()
    if config.type == "sqlite":
        return SqliteMemory(path=config.path or ":memory:")
    if config.type == "chromadb":
        return ChromadbMemory(path=config.path)
    raise ValueError(f"Unknown memory type: {config.type!r}")  # pragma: no cover
