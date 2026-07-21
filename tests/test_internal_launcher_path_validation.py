from __future__ import annotations

import os
from pathlib import Path

import pytest

from invoice_tool.internal_launcher.path_validation import (
    count_source_pdfs,
    default_internal_deny_paths,
    validate_output_path,
    validate_run_paths,
    validate_source_path,
)


def _touch_pdf(folder: Path, name: str) -> Path:
    path = folder / name
    path.write_bytes(b"%PDF-1.4 test")
    return path


def test_missing_source() -> None:
    result = validate_source_path(None)
    assert not result.ok
    assert "Eingangsordner" in result.messages[0]


def test_non_directory_source(tmp_path: Path) -> None:
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("x", encoding="utf-8")
    result = validate_source_path(file_path)
    assert not result.ok


def test_empty_source(tmp_path: Path) -> None:
    result = validate_source_path(tmp_path)
    assert not result.ok
    assert result.pdf_count == 0


def test_one_pdf(tmp_path: Path) -> None:
    _touch_pdf(tmp_path, "a.pdf")
    result = validate_source_path(tmp_path)
    assert result.ok
    assert result.pdf_count == 1


def test_multiple_pdfs(tmp_path: Path) -> None:
    _touch_pdf(tmp_path, "a.pdf")
    _touch_pdf(tmp_path, "b.pdf")
    result = validate_source_path(tmp_path)
    assert result.ok
    assert result.pdf_count == 2


def test_hidden_pdf_ignored(tmp_path: Path) -> None:
    _touch_pdf(tmp_path, ".hidden.pdf")
    result = validate_source_path(tmp_path)
    assert not result.ok


def test_archived_pdf_ignored(tmp_path: Path) -> None:
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    _touch_pdf(archiv, "old.pdf")
    result = validate_source_path(tmp_path)
    assert not result.ok


def test_identical_source_output(tmp_path: Path) -> None:
    _touch_pdf(tmp_path, "a.pdf")
    source = validate_source_path(tmp_path)
    output = validate_output_path(tmp_path, source=source.resolved_path, deny_paths=())
    assert not output.ok


def test_output_inside_source(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    output_dir = source_dir / "out"
    source_dir.mkdir()
    output_dir.mkdir()
    _touch_pdf(source_dir, "a.pdf")
    source = validate_source_path(source_dir)
    output = validate_output_path(output_dir, source=source.resolved_path, deny_paths=())
    assert not output.ok


def test_source_inside_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    source_dir = output_dir / "nested"
    output_dir.mkdir()
    source_dir.mkdir()
    _touch_pdf(source_dir, "a.pdf")
    source = validate_source_path(source_dir)
    output = validate_output_path(output_dir, source=source.resolved_path, deny_paths=())
    assert not output.ok


def test_protected_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    _touch_pdf(source_dir, "a.pdf")
    denied = tmp_path / "denied"
    denied.mkdir()
    source = validate_source_path(source_dir)
    output = validate_output_path(
        denied,
        source=source.resolved_path,
        deny_paths=(denied,),
    )
    assert not output.ok
    assert "gesperrt" in output.messages[0]


def test_symlink_escape_source(tmp_path: Path) -> None:
    real = tmp_path / "real"
    link = tmp_path / "link"
    real.mkdir()
    _touch_pdf(real, "a.pdf")
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks auf diesem System nicht verfügbar")
    result = validate_source_path(link)
    assert result.ok or "symbolische" in (result.messages[0] if result.messages else "")


def test_unwritable_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    output_dir.mkdir()
    _touch_pdf(source_dir, "a.pdf")
    source = validate_source_path(source_dir)

    def _deny(_path: os.PathLike[str], _mode: int) -> bool:
        return False

    monkeypatch.setattr(os, "access", _deny)
    output = validate_output_path(output_dir, source=source.resolved_path, deny_paths=())
    assert not output.ok


def test_run_paths_ready(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    output_dir.mkdir()
    _touch_pdf(source_dir, "a.pdf")
    source_result, output_result = validate_run_paths(
        source_dir,
        output_dir,
        deny_paths=(),
    )
    assert source_result.ok
    assert output_result.ok


def test_count_source_pdfs_matches_backend_inventory(tmp_path: Path) -> None:
    _touch_pdf(tmp_path, "a.pdf")
    (tmp_path / "archiv").mkdir()
    _touch_pdf(tmp_path / "archiv", "ignored.pdf")
    assert count_source_pdfs(tmp_path) == 1


def test_default_deny_paths_not_empty() -> None:
    deny = default_internal_deny_paths()
    assert len(deny) >= 2
