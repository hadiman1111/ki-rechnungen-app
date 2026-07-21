from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from invoice_tool.internal_launcher.result_reader import detect_new_run_dir, read_run_result
from invoice_tool.internal_launcher.run_controller import RunOutcome


def _outcome(*, exit_code: int = 0, stdout: str = "", stderr: str = "", run_dir: Path | None = None) -> RunOutcome:
    now = datetime.now(timezone.utc)
    return RunOutcome(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=1.0,
        log_path=Path("/tmp/log.json"),
        command=("python", "-m", "invoice_tool.run"),
        started_at=now,
        finished_at=now,
        run_dir=run_dir,
    )


def test_successful_report(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260714_120000"
    run_dir.mkdir()
    report = {
        "run_id": "20260714_120000",
        "summary": {"processed": 5, "errors": 0, "unklar": 0},
        "files": [],
    }
    (run_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    (run_dir / "report.txt").write_text("ok", encoding="utf-8")
    output_root = tmp_path / "output"
    output_root.mkdir()

    result = read_run_result(_outcome(run_dir=run_dir), output_root=output_root)
    assert result.ok
    assert result.processed_count == 5
    assert result.error_count == 0
    assert result.report_json_path is not None


def test_errors_present(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    report = {"summary": {"processed": 2, "errors": 1, "unklar": 0}, "files": []}
    (run_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    result = read_run_result(_outcome(run_dir=run_dir), output_root=tmp_path / "out")
    assert not result.ok
    assert result.error_count == 1


def test_unklar_present(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    output_root = tmp_path / "output"
    unklar = output_root / "unklar"
    unklar.mkdir(parents=True)
    run_dir.mkdir()
    report = {
        "summary": {"processed": 1, "errors": 0, "unklar": 1},
        "files": [{"status": "success", "output": str(unklar / "file.pdf")}],
    }
    (run_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    result = read_run_result(_outcome(run_dir=run_dir), output_root=output_root)
    assert result.review_count >= 1
    assert result.unklar_folder_path == unklar


def test_missing_optional_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    report = {"summary": {"processed": 1, "errors": 0, "unklar": 0}, "files": []}
    (run_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    result = read_run_result(_outcome(run_dir=run_dir), output_root=tmp_path / "out")
    assert result.report_txt_path is None
    assert any("report.txt" in warning for warning in result.warnings)


def test_ambiguous_multiple_new_runs(tmp_path: Path) -> None:
    before = {tmp_path / "a", tmp_path / "b"}
    after = {tmp_path / "a", tmp_path / "b", tmp_path / "c", tmp_path / "d"}
    assert detect_new_run_dir(before, after) is None
    result = read_run_result(
        _outcome(exit_code=0),
        output_root=tmp_path / "out",
        before_run_dirs=before,
    )
    assert result.ambiguous


def test_output_mapping_parsing(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "report.json").write_text(
        json.dumps({"summary": {"processed": 1, "errors": 0, "unklar": 0}, "files": []}),
        encoding="utf-8",
    )
    (run_dir / "output_mapping.json").write_text(
        json.dumps({"run_id": "run", "mappings": []}),
        encoding="utf-8",
    )
    result = read_run_result(_outcome(run_dir=run_dir), output_root=tmp_path / "out")
    assert result.output_mapping_path is not None


def test_nested_report_path(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260714_120000"
    nested = run_dir / "_runs" / "20260714_120000"
    nested.mkdir(parents=True)
    report = {"run_id": "20260714_120000", "summary": {"processed": 5, "errors": 0, "unklar": 0}, "files": []}
    (nested / "report.json").write_text(json.dumps(report), encoding="utf-8")
    (run_dir / "output_mapping.json").write_text(json.dumps({"run_id": "x", "mappings": []}), encoding="utf-8")
    result = read_run_result(_outcome(run_dir=run_dir), output_root=tmp_path / "out")
    assert result.processed_count == 5
    assert result.report_json_path == nested / "report.json"


def test_non_zero_exit(tmp_path: Path) -> None:
    result = read_run_result(
        _outcome(exit_code=1, stderr="Fehler: kaputt"),
        output_root=tmp_path / "out",
    )
    assert not result.ok
    assert result.stderr_summary == "Fehler: kaputt"
