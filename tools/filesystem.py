"""Filesystem tools: read_file, write_file, list_dir."""

import os


def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read the contents of a file and return them as a string.

    Args:
        path: Absolute or relative path to the file.
        encoding: File encoding to use when reading.
    """
    with open(path, encoding=encoding) as f:
        return f.read()


def write_file(path: str, content: str, encoding: str = "utf-8") -> str:
    """Write content to a file, creating it if it does not exist.

    Args:
        path: Absolute or relative path to the file.
        content: Text content to write.
        encoding: File encoding to use when writing.
    """
    with open(path, "w", encoding=encoding) as f:
        f.write(content)
    return f"Written {len(content)} characters to {path}"


def list_dir(path: str) -> str:
    """List the files and directories inside a directory.

    Args:
        path: Absolute or relative path to the directory.
    """
    entries = sorted(os.listdir(path))
    return "\n".join(entries)
