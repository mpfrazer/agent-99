"""Tests for tools/filesystem.py — read_file, write_file, list_dir."""

from pathlib import Path

import pytest

from tools.filesystem import list_dir, read_file, write_file


def test_read_file(tmp_path: Path):
    f = tmp_path / "hello.txt"
    f.write_text("hello world")
    assert read_file(str(f)) == "hello world"


def test_read_file_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        read_file(str(tmp_path / "nonexistent.txt"))


def test_read_file_encoding(tmp_path: Path):
    f = tmp_path / "unicode.txt"
    f.write_text("héllo wörld", encoding="utf-8")
    assert read_file(str(f)) == "héllo wörld"


def test_write_file_creates(tmp_path: Path):
    path = str(tmp_path / "new.txt")
    result = write_file(path, "content here")
    assert "Written" in result
    assert Path(path).read_text() == "content here"


def test_write_file_overwrites(tmp_path: Path):
    f = tmp_path / "existing.txt"
    f.write_text("old content")
    write_file(str(f), "new content")
    assert f.read_text() == "new content"


def test_write_file_reports_chars(tmp_path: Path):
    path = str(tmp_path / "out.txt")
    result = write_file(path, "abc")
    assert "3" in result


def test_list_dir(tmp_path: Path):
    (tmp_path / "alpha.txt").write_text("")
    (tmp_path / "beta.txt").write_text("")
    (tmp_path / "subdir").mkdir()

    result = list_dir(str(tmp_path))
    lines = result.split("\n")
    assert "alpha.txt" in lines
    assert "beta.txt" in lines
    assert "subdir" in lines


def test_list_dir_empty(tmp_path: Path):
    assert list_dir(str(tmp_path)) == ""


def test_list_dir_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        list_dir(str(tmp_path / "nonexistent"))
