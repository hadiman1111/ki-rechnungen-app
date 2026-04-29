"""Tests for invoice_tool/run.py – Run Manager MVP.

All tests use tmp_path and synthetic PDFs (created via fitz).
No real invoice PDFs, no OpenAI calls, no network access.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import pytest

from invoice_tool.run import (
    RunError,
    _validate_source_and_output,
    build_run_config,
    create_run_dir,
    create_run_snapshot,
)


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

def _make_pdf(path: Path, content: str = "Test PDF") -> Path:
    """Create a minimal valid PDF at path."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), content)
    doc.save(str(path))
    doc.close()
    return path


def _make_source_with_pdfs(tmp_path: Path, count: int = 2) -> Path:
    """Create a source directory with `count` PDFs."""
    source = tmp_path / "source"
    source.mkdir()
    for i in range(count):
        _make_pdf(source / f"rechnung_{i + 1}.pdf", f"Rechnung {i + 1}")
    return source


def _make_run_config_path(tmp_path: Path) -> Path:
    """Create a minimal valid invoice_config.json in tmp_path.

    Replicates the logic of make_test_setup from test_invoice_tool.py
    without importing from the tests package.
    """
    input_dir = tmp_path / "input"
    input_dir.mkdir(exist_ok=True)
    output_dir = tmp_path / "output"
    documents_dir = tmp_path / "documents"
    runtime_dir = tmp_path / "runtime"
    logs_dir = tmp_path / "logs"

    rules_data = json.loads(Path("office_rules.json").read_text(encoding="utf-8"))
    rules_data["presets"]["office_default"]["dokumente"]["basis_pfad"] = str(documents_dir)
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(rules_data), encoding="utf-8")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({
            "eingangsordner": str(input_dir),
            "ausgangsordner": str(output_dir),
            "api_key_pfad": "$HOME/Library/Application Support/KI-Rechnungen-Umbenennen/.env",
            "archiv_aktiv": True,
            "regeln_datei": str(rules_path),
            "aktives_preset": "office_default",
            "runtime_ordner": str(runtime_dir),
            "log_ordner": str(logs_dir),
        }),
        encoding="utf-8",
    )
    return config_path


# ---------------------------------------------------------------------------
# A. create_run_snapshot: copies PDFs without modifying source
# ---------------------------------------------------------------------------


def test_create_run_snapshot_copies_pdfs_without_modifying_source(tmp_path: Path) -> None:
    """PDFs must appear in the snapshot; originals in source must be unchanged."""
    source = _make_source_with_pdfs(tmp_path, count=2)
    run_dir = tmp_path / "runs" / "20260429_000000"
    run_dir.mkdir(parents=True)

    original_names = {p.name for p in source.iterdir() if p.is_file()}
    original_sizes = {p.name: p.stat().st_size for p in source.iterdir() if p.is_file()}

    snapshot_dir = create_run_snapshot(source, run_dir)

    # Snapshot exists and contains the PDFs
    assert snapshot_dir.exists()
    snapshot_names = {p.name for p in snapshot_dir.iterdir() if p.is_file()}
    assert snapshot_names == original_names

    # Originals in source are still present and unchanged
    source_names_after = {p.name for p in source.iterdir() if p.is_file()}
    assert source_names_after == original_names
    for name, size in original_sizes.items():
        assert (source / name).stat().st_size == size, (
            f"Original file {name} was modified"
        )


def test_create_run_snapshot_returns_snapshot_dir_path(tmp_path: Path) -> None:
    source = _make_source_with_pdfs(tmp_path, count=1)
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    snapshot_dir = create_run_snapshot(source, run_dir)

    assert snapshot_dir == run_dir / "input_snapshot"
    assert snapshot_dir.is_dir()


# ---------------------------------------------------------------------------
# B. create_run_snapshot: excludes non-PDF files
# ---------------------------------------------------------------------------


def test_create_run_snapshot_excludes_non_pdfs(tmp_path: Path) -> None:
    """Only .pdf/.PDF files must be copied; other files must be ignored."""
    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "invoice.pdf")
    (source / "notes.txt").write_text("ignore me")
    (source / "data.csv").write_text("a,b,c")
    (source / "IMAGE.PDF").write_bytes(b"%PDF-1.4\n")  # uppercase extension

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    snapshot_dir = create_run_snapshot(source, run_dir)

    snapshot_files = {p.name for p in snapshot_dir.iterdir() if p.is_file()}
    assert "invoice.pdf" in snapshot_files
    assert "IMAGE.PDF" in snapshot_files
    assert "notes.txt" not in snapshot_files
    assert "data.csv" not in snapshot_files


# ---------------------------------------------------------------------------
# C. create_run_dir: unique per run
# ---------------------------------------------------------------------------


def test_create_run_dir_is_unique_when_timestamp_collides(tmp_path: Path) -> None:
    """Two calls that produce the same timestamp must get distinct directories."""
    output = tmp_path / "runs"

    # Force timestamp collision by pre-creating the expected dir
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (output / ts).mkdir(parents=True)

    run_dir = create_run_dir(output)

    assert run_dir.exists()
    assert run_dir != output / ts, "Expected a unique suffixed directory"
    # The new directory must be a child of output
    assert run_dir.parent == output


def test_create_run_dir_creates_dir(tmp_path: Path) -> None:
    output = tmp_path / "runs"
    run_dir = create_run_dir(output)
    assert run_dir.exists()
    assert run_dir.is_dir()
    assert run_dir.parent == output


# ---------------------------------------------------------------------------
# D. build_run_config: isolates paths
# ---------------------------------------------------------------------------


def test_build_run_config_isolates_paths(tmp_path: Path) -> None:
    """build_run_config must override the four path fields; other fields unchanged."""
    import json as _json
    from invoice_tool.config import load_app_config

    # Build a minimal invoice_config.json in tmp_path
    api_key_file = tmp_path / ".env"
    api_key_file.write_text("OPENAI_API_KEY=test-key")
    rules_file = tmp_path / "office_rules.json"
    shutil.copy(Path("office_rules.json").resolve(), rules_file)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    config_file = tmp_path / "invoice_config.json"
    config_file.write_text(_json.dumps({
        "eingangsordner": str(input_dir),
        "ausgangsordner": str(output_dir),
        "api_key_pfad": str(api_key_file),
        "archiv_aktiv": True,
        "regeln_datei": str(rules_file),
        "openai_model": "gpt-4.1",
        "stale_lock_seconds": 21600,
        "runtime_ordner": str(tmp_path / "runtime"),
        "log_ordner": str(tmp_path / "logs"),
        "zielgroesse_kb": 200,
    }))
    base_config = load_app_config(config_file)

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    snapshot_dir = run_dir / "input_snapshot"
    snapshot_dir.mkdir()

    run_config = build_run_config(base_config, run_dir, snapshot_dir)

    assert run_config.eingangsordner == snapshot_dir
    assert run_config.ausgangsordner == run_dir / "output"
    assert run_config.runtime_ordner == run_dir / "runtime"
    assert run_config.log_ordner == run_dir / "logs"

    # All other fields must be identical to base_config
    assert run_config.api_key_pfad == base_config.api_key_pfad
    assert run_config.archiv_aktiv == base_config.archiv_aktiv
    assert run_config.regeln_datei == base_config.regeln_datei
    assert run_config.openai_model == base_config.openai_model
    assert run_config.stale_lock_seconds == base_config.stale_lock_seconds
    assert run_config.zielgroesse_kb == base_config.zielgroesse_kb


# ---------------------------------------------------------------------------
# E. Validation: source == output raises
# ---------------------------------------------------------------------------


def test_validate_source_equals_output_raises(tmp_path: Path) -> None:
    same = tmp_path / "dir"
    same.mkdir()
    _make_pdf(same / "a.pdf")

    with pytest.raises(RunError, match="identisch"):
        _validate_source_and_output(same, same)


# ---------------------------------------------------------------------------
# F. Validation: nested paths raise
# ---------------------------------------------------------------------------


def test_validate_source_inside_output_raises(tmp_path: Path) -> None:
    output = tmp_path / "output"
    source = output / "nested_source"
    source.mkdir(parents=True)
    _make_pdf(source / "a.pdf")

    with pytest.raises(RunError, match="innerhalb"):
        _validate_source_and_output(source, output)


def test_validate_output_inside_source_raises(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = source / "nested_output"
    source.mkdir()
    output.mkdir()
    _make_pdf(source / "a.pdf")

    with pytest.raises(RunError, match="innerhalb"):
        _validate_source_and_output(source, output)


# ---------------------------------------------------------------------------
# G. Validation: missing / non-PDF / empty source
# ---------------------------------------------------------------------------


def test_validate_source_does_not_exist_raises(tmp_path: Path) -> None:
    source = tmp_path / "nonexistent"
    output = tmp_path / "output"
    output.mkdir()

    with pytest.raises(RunError, match="existiert nicht"):
        _validate_source_and_output(source, output)


def test_validate_source_is_not_dir_raises(tmp_path: Path) -> None:
    source = tmp_path / "file.pdf"
    _make_pdf(source)
    output = tmp_path / "output"
    output.mkdir()

    with pytest.raises(RunError, match="kein Ordner"):
        _validate_source_and_output(source, output)


def test_validate_source_contains_no_pdfs_raises(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "readme.txt").write_text("no pdfs here")
    output = tmp_path / "output"

    with pytest.raises(RunError, match="keine PDF"):
        _validate_source_and_output(source, output)


# ---------------------------------------------------------------------------
# H. run_once: structure test with mocked InvoiceProcessor
# ---------------------------------------------------------------------------


def test_run_once_creates_expected_structure(tmp_path: Path) -> None:
    """run_once must create run_dir/input_snapshot, /output, /runtime, /logs
    when InvoiceProcessor is mocked to avoid real API calls."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)

    # Source: a separate folder with PDFs
    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "test1.pdf")
    _make_pdf(source / "test2.pdf")

    output_base = tmp_path / "runs"

    with patch("invoice_tool.run.InvoiceProcessor") as mock_processor_cls:
        mock_processor_cls.return_value.process_all.return_value = []
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_dir = run_once(
                        source=source,
                        output=output_base,
                        config_path=config_path,
                    )

    assert run_dir.exists(), "Run directory must be created"
    assert (run_dir / "input_snapshot").is_dir(), "input_snapshot must exist"
    assert (run_dir / "input_snapshot" / "test1.pdf").exists(), "PDF must be in snapshot"
    assert (run_dir / "input_snapshot" / "test2.pdf").exists(), "PDF must be in snapshot"

    # Originals unchanged
    assert (source / "test1.pdf").exists(), "Original must not be moved"
    assert (source / "test2.pdf").exists(), "Original must not be moved"


def test_run_once_copies_profile_snapshot(tmp_path: Path) -> None:
    """When --profile is given, profile must be copied to run_dir/profile_snapshot.json."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "invoice.pdf")

    profile = tmp_path / "my_profile.json"
    profile.write_text(json.dumps({"schema_version": "1.0", "profile_name": "Test"}))

    output_base = tmp_path / "runs"

    with patch("invoice_tool.run.InvoiceProcessor") as mock_cls:
        mock_cls.return_value.process_all.return_value = []
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_dir = run_once(
                        source=source,
                        output=output_base,
                        config_path=config_path,
                        profile_path=profile,
                    )

    profile_snap = run_dir / "profile_snapshot.json"
    assert profile_snap.exists(), "profile_snapshot.json must be created"
    data = json.loads(profile_snap.read_text())
    assert data["profile_name"] == "Test"


def test_run_once_rules_path_raises(tmp_path: Path) -> None:
    """rules_path must raise RunError in this MVP."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "invoice.pdf")

    with pytest.raises(RunError, match="nicht unterstützt"):
        run_once(
            source=source,
            output=tmp_path / "runs",
            config_path=config_path,
            rules_path=tmp_path / "office_rules.json",
        )
