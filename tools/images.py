"""Image discovery tools."""

import os

_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".tiff", ".tif", ".svg", ".ico", ".heic", ".heif", ".avif",
}


def find_images(directory: str, recursive: bool = True) -> str:
    """Search a directory for image files and return their paths.

    Args:
        directory: Absolute or relative path to the directory to search.
        recursive: Whether to search subdirectories recursively.
    """
    found = []
    try:
        if recursive:
            for root, dirs, files in os.walk(directory):
                # Skip hidden and system directories to avoid permission errors
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for filename in files:
                    if os.path.splitext(filename)[1].lower() in _IMAGE_EXTENSIONS:
                        found.append(os.path.join(root, filename))
        else:
            for entry in os.scandir(directory):
                if entry.is_file() and os.path.splitext(entry.name)[1].lower() in _IMAGE_EXTENSIONS:
                    found.append(entry.path)
    except PermissionError as e:
        return f"Permission denied: {e}"

    if not found:
        return f"No image files found in {directory!r}"
    return "\n".join(sorted(found))
