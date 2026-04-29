"""Tests for scripts/run_smoke_test.py

All tests use tmp_path and synthetic PDFs (created via fitz).
No real invoice PDFs, no OpenAI calls, no network access.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz
import pytest

# Make the scripts package importable from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from run_smoke_test import (
    SmokeResult,
    build_parser,
    check_run_structure,
    check_source_unchanged,
    list_pdfs,
    parse_report_summary,
    validate_source,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf(path: Path, content: str = "Smoke Test PDF") -> Path:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), content)
    doc.save(str(path))
    doc.close()
    return path


def _make_source(tmp_path: Path, count: int = 2) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    for i in range(count):
        _make_pdf(source / f"doc_{i + 1}.pdf")
    return source


def _make_run_structure(run_dir: Path, *, report_data: dict | None = None) -> None:
    """Create a fake but structurally complete run directory."""
    (run_dir / "input_snapshot").mkdir(parents=True)
    (run_dir / "output").mkdir()
    (run_dir / "runtime").mkdir()
    (run_dir / "logs").mkdir()

    runs_subdir = run_dir / "output" / "_runs" / "20260429_120000"
    runs_subdir.mkdir(parents=True)

    (runs_subdir / "report.txt").write_text("Run report\n")
    data = report_data or {
        "run_id": "20260429_120000",
        "summary": {
            "processed": 5,
            "documents": 1,
            "duplicates": 0,
            "unklar": 1,
            "errors": 0,
        }
    }
    (runs_subdir / "report.json").write_text(json.dumps(data, indent=2))
    (runs_subdir / "decision_trace.jsonl").write_text("")
    (runs_subdir / "routing_summary.csv").write_text("col1,col2\n")


# ---------------------------------------------------------------------------
# A. Argument parser
# ---------------------------------------------------------------------------


def test_parser_accepts_source_and_output(tmp_path: Path) -> None:
    source = tmp_path / "src"
    output = tmp_path / "out"
    parser = build_parser()
    args = parser.parse_args(["--source", str(source), "--output", str(output)])
    assert args.source == source
    assert args.output == output
    assert args.skip_pytest is False
    assert args.skip_run is False


def test_parser_accepts_skip_flags(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args([
        "--source", str(tmp_path),
        "--output", str(tmp_path),
        "--skip-pytest",
        "--skip-run",
    ])
    assert args.skip_pytest is True
    assert args.skip_run is True


def test_parser_accepts_config_flag(tmp_path: Path) -> None:
    cfg = tmp_path / "my_config.json"
    parser = build_parser()
    args = parser.parse_args([
        "--source", str(tmp_path),
        "--output", str(tmp_path),
        "--config", str(cfg),
    ])
    assert args.config == cfg


# ---------------------------------------------------------------------------
# B. Source validation – missing folder
# ---------------------------------------------------------------------------


def test_validate_source_nonexistent_returns_error(tmp_path: Path) -> None:
    errors = validate_source(tmp_path / "nonexistent")
    assert errors
    assert any("existiert nicht" in e for e in errors)


def test_validate_source_file_not_dir_returns_error(tmp_path: Path) -> None:
    f = tmp_path / "file.pdf"
    _make_pdf(f)
    errors = validate_source(f)
    assert errors
    assert any("kein Ordner" in e for e in errors)


# ---------------------------------------------------------------------------
# C. Source validation – no PDFs
# ---------------------------------------------------------------------------


def test_validate_source_empty_dir_returns_error(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    errors = validate_source(empty)
    assert errors
    assert any("keine PDF" in e for e in errors)


def test_validate_source_with_pdfs_returns_no_error(tmp_path: Path) -> None:
    source = _make_source(tmp_path, count=1)
    errors = validate_source(source)
    assert errors == []


def test_validate_source_ignores_non_pdfs(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "readme.txt").write_text("no pdfs")
    errors = validate_source(source)
    assert errors  # must report "keine PDF"


# ---------------------------------------------------------------------------
# D. Source unchanged check
# ---------------------------------------------------------------------------


def test_check_source_unchanged_same_list(tmp_path: Path) -> None:
    source = _make_source(tmp_path, count=2)
    original = list_pdfs(source)
    assert check_source_unchanged(source, original) is True


def test_check_source_unchanged_detects_removal(tmp_path: Path) -> None:
    source = _make_source(tmp_path, count=2)
    original = list_pdfs(source)
    # Remove one PDF to simulate a modification
    (source / original[0]).unlink()
    assert check_source_unchanged(source, original) is False


def test_check_source_unchanged_detects_addition(tmp_path: Path) -> None:
    source = _make_source(tmp_path, count=2)
    original = list_pdfs(source)
    _make_pdf(source / "extra.pdf")
    assert check_source_unchanged(source, original) is False


# ---------------------------------------------------------------------------
# E. Report structure check
# ---------------------------------------------------------------------------


def test_check_run_structure_complete(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _make_run_structure(run_dir)
    ok, missing = check_run_structure(run_dir)
    assert ok, f"Expected complete structure, missing: {missing}"
    assert missing == []


def test_check_run_structure_missing_runtime(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _make_run_structure(run_dir)
    import shutil
    shutil.rmtree(run_dir / "runtime")
    ok, missing = check_run_structure(run_dir)
    assert not ok
    assert any("runtime" in m for m in missing)


def test_check_run_structure_missing_report(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _make_run_structure(run_dir)
    (run_dir / "output" / "_runs" / "20260429_120000" / "report.json").unlink()
    ok, missing = check_run_structure(run_dir)
    assert not ok
    assert any("report.json" in m for m in missing)


def test_check_run_structure_no_runs_subdir(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "output").mkdir()
    ok, missing = check_run_structure(run_dir)
    assert not ok


# ---------------------------------------------------------------------------
# F. Summary output: PASS when all requirements met
# ---------------------------------------------------------------------------


def test_smoke_result_pass_when_no_failures() -> None:
    result = SmokeResult()
    result.pytest_status = "passed"
    result.run_executed = True
    result.source_unchanged = True
    result.reports_complete = True
    assert result.ok


def test_smoke_result_fail_with_failures() -> None:
    result = SmokeResult()
    result.fail("something went wrong")
    assert not result.ok


def test_parse_report_summary_reads_fields(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _make_run_structure(run_dir)
    metrics = parse_report_summary(run_dir)
    assert metrics["processed"] == 5
    assert metrics["document"] == 1
    assert metrics["duplicate"] == 0
    assert metrics["unclear"] == 1
    assert metrics["errors"] == 0


def test_parse_report_summary_missing_dir_returns_not_found(tmp_path: Path) -> None:
    run_dir = tmp_path / "no_run"
    run_dir.mkdir()
    metrics = parse_report_summary(run_dir)
    assert metrics["processed"] == "nicht gefunden"


def test_list_pdfs_returns_only_pdfs(tmp_path: Path) -> None:
    source = _make_source(tmp_path, count=3)
    (source / "notes.txt").write_text("ignore")
    pdfs = list_pdfs(source)
    assert len(pdfs) == 3
    assert all(p.lower().endswith(".pdf") for p in pdfs)


def test_list_pdfs_is_sorted(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    _make_pdf(source / "z.pdf")
    _make_pdf(source / "a.pdf")
    result = list_pdfs(source)
    assert result == sorted(result)
