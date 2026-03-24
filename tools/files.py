"""Generic file discovery tools."""

import os


def find_files(directory: str, extensions: str, recursive: bool = True) -> str:
    """Search a directory for files matching the given extensions.

    Args:
        directory: Absolute or relative path to the directory to search.
        extensions: Comma-separated list of file extensions to match, e.g. "pdf,docx,txt".
        recursive: Whether to search subdirectories recursively.
    """
    exts = {
        f".{e.strip().lstrip('.')}" .lower()
        for e in extensions.split(",")
        if e.strip()
    }
    if not exts:
        return "No extensions provided."

    found = []
    try:
        if recursive:
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for filename in files:
                    if os.path.splitext(filename)[1].lower() in exts:
                        found.append(os.path.join(root, filename))
        else:
            for entry in os.scandir(directory):
                if entry.is_file() and os.path.splitext(entry.name)[1].lower() in exts:
                    found.append(entry.path)
    except PermissionError as e:
        return f"Permission denied: {e}"

    if not found:
        return f"No files matching {extensions!r} found in {directory!r}"
    return "\n".join(sorted(found))
