"""Agent memory backends: none, sqlite, chromadb, markdown."""

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

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
        now = datetime.now(UTC).isoformat()
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


class MarkdownMemory(BaseMemory):
    """Store conversation history in a human-readable Markdown file.

    Each message is written as a level-2 heading with role and timestamp,
    followed by the message content.  Example::

        # Agent Memory

        ## user — 2026-03-26T10:00:00.000000+00:00

        Hello, what can you do?

        ## assistant — 2026-03-26T10:00:01.000000+00:00

        I can help you with many tasks!

    The file is created (with a title heading) if it does not already exist.
    Passing ``path=None`` defaults to ``memory.md`` in the current directory.
    """

    # Matches section dividers written by this class: "## role — ISO-timestamp"
    _SECTION_RE = re.compile(r"\n## ")

    def __init__(self, path: str = "memory.md") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("# Agent Memory\n\n", encoding="utf-8")

    def add(self, role: str, content: str) -> None:
        now = datetime.now(UTC).isoformat()
        entry = f"## {role} — {now}\n\n{content}\n\n"
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(entry)

    def history(self) -> list[dict]:
        text = self._path.read_text(encoding="utf-8")
        # Split on "\n## " — the separator written between entries
        parts = self._SECTION_RE.split(text)
        messages: list[dict] = []
        for part in parts[1:]:  # parts[0] is the "# Agent Memory" title block
            header, _, body = part.partition("\n")
            role = header.split(" — ", 1)[0].strip()
            messages.append({"role": role, "content": body.strip()})
        return messages

    def clear(self) -> None:
        self._path.write_text("# Agent Memory\n\n", encoding="utf-8")


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
    if config.type == "markdown":
        return MarkdownMemory(path=config.path or "memory.md")
    if config.type == "chromadb":
        return ChromadbMemory(path=config.path)
    raise ValueError(f"Unknown memory type: {config.type!r}")  # pragma: no cover
