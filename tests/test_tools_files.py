"""Tests for tools/files.py — find_files."""

from pathlib import Path

from tools.files import find_files


def _make_tree(tmp_path: Path):
    """Create a small directory tree for testing."""
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.pdf").write_text("")
    (tmp_path / "c.jpg").write_text("")
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "d.txt").write_text("")
    (sub / "e.docx").write_text("")
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "f.txt").write_text("")  # should be skipped
    return tmp_path


def test_finds_txt_files_recursive(tmp_path: Path):
    _make_tree(tmp_path)
    result = find_files(str(tmp_path), "txt")
    lines = result.strip().split("\n")
    names = [Path(p).name for p in lines]
    assert "a.txt" in names
    assert "d.txt" in names
    assert "f.txt" not in names  # inside hidden dir


def test_finds_multiple_extensions(tmp_path: Path):
    _make_tree(tmp_path)
    result = find_files(str(tmp_path), "pdf,jpg")
    lines = result.strip().split("\n")
    names = [Path(p).name for p in lines]
    assert "b.pdf" in names
    assert "c.jpg" in names
    assert "a.txt" not in names


def test_non_recursive(tmp_path: Path):
    _make_tree(tmp_path)
    result = find_files(str(tmp_path), "txt", recursive=False)
    lines = result.strip().split("\n")
    names = [Path(p).name for p in lines]
    assert "a.txt" in names
    assert "d.txt" not in names  # in subdir, not found non-recursively


def test_no_match_returns_message(tmp_path: Path):
    _make_tree(tmp_path)
    result = find_files(str(tmp_path), "xyz")
    assert "No files" in result


def test_empty_extensions_returns_message(tmp_path: Path):
    _make_tree(tmp_path)
    result = find_files(str(tmp_path), "  ,  ")
    assert "No extensions" in result


def test_extension_with_dot_prefix(tmp_path: Path):
    """Extensions like '.txt' and 'txt' should both work."""
    _make_tree(tmp_path)
    result_with_dot = find_files(str(tmp_path), ".txt")
    result_without = find_files(str(tmp_path), "txt")
    assert result_with_dot == result_without


def test_mixed_case_extension(tmp_path: Path):
    (tmp_path / "IMAGE.PNG").write_text("")
    result = find_files(str(tmp_path), "png")
    assert "IMAGE.PNG" in result


def test_missing_directory():
    result = find_files("/nonexistent/path", "txt")
    assert "Permission denied" in result or "No files" in result or "not" in result.lower()
