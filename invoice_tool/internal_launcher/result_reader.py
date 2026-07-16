"""Run result reading for the internal SOMAA launcher."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from invoice_tool.app_paths import run_support_root
from invoice_tool.internal_launcher.run_controller import RunOutcome, parse_run_dir_from_stdout


@dataclass(frozen=True)
class RunResultSummary:
    ok: bool
    ambiguous: bool
    run_id: str | None
    run_dir: Path | None
    output_root: Path | None
    processed_count: int
    error_count: int
    review_count: int
    report_json_path: Path | None
    report_txt_path: Path | None
    output_mapping_path: Path | None
    unklar_folder_path: Path | None
    warnings: tuple[str, ...]
    status_label: str
    stderr_summary: str | None = None
    exit_code: int | None = None


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _list_run_dirs() -> set[Path]:
    root = run_support_root()
    if not root.is_dir():
        return set()
    return {path.resolve() for path in root.iterdir() if path.is_dir()}


def detect_new_run_dir(before: set[Path], after: set[Path]) -> Path | None:
    created = sorted(after - before, key=lambda path: path.name)
    if len(created) == 1:
        return created[0]
    return None


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _resolve_report_paths(run_dir: Path | None) -> tuple[Path | None, Path | None, Path | None]:
    if run_dir is None:
        return None, None, None

    candidates_json = [
        run_dir / "report.json",
        run_dir / "_runs" / run_dir.name / "report.json",
    ]
    nested = sorted(
        run_dir.glob("_runs/*/report.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if nested:
        candidates_json.insert(0, nested[0])

    report_json_path = next((path for path in candidates_json if path.is_file()), None)
    report_txt_path = report_json_path.with_name("report.txt") if report_json_path else None
    if report_txt_path is not None and not report_txt_path.is_file():
        report_txt_path = None

    output_mapping_path = run_dir / "output_mapping.json"
    if not output_mapping_path.is_file():
        output_mapping_path = None

    return report_json_path, report_txt_path, output_mapping_path


def _derive_unklar_folder(output_root: Path | None, report_data: dict | None) -> Path | None:
    if output_root is None:
        return None
    candidate = output_root / "unklar"
    if candidate.is_dir():
        return candidate
    if not isinstance(report_data, dict):
        return None
    files = report_data.get("files")
    if not isinstance(files, list):
        return None
    for item in files:
        if not isinstance(item, dict):
            continue
        output = item.get("output")
        if not isinstance(output, str) or not output.strip():
            continue
        output_path = Path(output)
        parts = {part.lower() for part in output_path.parts}
        if "unklar" in parts:
            return output_path.parent
    return None


def _count_review_from_files(report_data: dict | None) -> int:
    if not isinstance(report_data, dict):
        return 0
    files = report_data.get("files")
    if not isinstance(files, list):
        return 0
    count = 0
    for item in files:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").lower()
        output = str(item.get("output") or "").lower()
        if status in {"error", "failed"} or "/unklar/" in output.replace("\\", "/"):
            count += 1
    return count


def read_run_result(
    outcome: RunOutcome,
    *,
    output_root: Path | None,
    before_run_dirs: set[Path] | None = None,
) -> RunResultSummary:
    """Resolve run artifacts for the current launcher invocation."""
    run_dir = outcome.run_dir or parse_run_dir_from_stdout(outcome.stdout)
    ambiguous = False

    if run_dir is None and before_run_dirs is not None:
        after = _list_run_dirs()
        detected = detect_new_run_dir(before_run_dirs, after)
        if detected is None:
            ambiguous = len(after - before_run_dirs) != 1
        else:
            run_dir = detected

    report_json_path, report_txt_path, output_mapping_path = _resolve_report_paths(run_dir)
    report_data = _read_json(report_json_path) if report_json_path else None
    summary = report_data.get("summary") if isinstance(report_data, dict) else {}
    if not isinstance(summary, dict):
        summary = {}

    processed_count = _int_value(summary.get("processed"))
    error_count = _int_value(summary.get("errors"))
    review_count = max(_int_value(summary.get("unklar")), _count_review_from_files(report_data))

    run_id = None
    if isinstance(report_data, dict):
        run_id = str(report_data.get("run_id") or "") or None
    if run_id is None and run_dir is not None:
        run_id = run_dir.name

    warnings: list[str] = []
    if ambiguous:
        warnings.append("Der Lauf konnte nicht eindeutig zugeordnet werden.")
    if run_dir is not None and report_json_path is None:
        warnings.append("report.json fehlt im Run-Ordner.")
    if run_dir is not None and report_txt_path is None:
        warnings.append("report.txt fehlt optional im Run-Ordner.")
    if run_dir is not None and output_mapping_path is None:
        warnings.append("output_mapping.json fehlt optional im Run-Ordner.")

    unklar_folder = _derive_unklar_folder(output_root, report_data)

    if outcome.exit_code != 0:
        status_label = "Verarbeitung mit Fehlern beendet"
        ok = False
    elif error_count > 0:
        status_label = "Verarbeitung mit Fehlern beendet"
        ok = False
    elif ambiguous:
        status_label = "Ergebnis mehrdeutig"
        ok = False
    elif review_count > 0:
        status_label = "Verarbeitung abgeschlossen – Prüfung erforderlich"
        ok = True
    else:
        status_label = "Verarbeitung abgeschlossen"
        ok = True

    stderr_summary = (outcome.stderr or "").strip() or None
    if stderr_summary and len(stderr_summary) > 500:
        stderr_summary = stderr_summary[:497] + "..."

    return RunResultSummary(
        ok=ok,
        ambiguous=ambiguous,
        run_id=run_id,
        run_dir=run_dir,
        output_root=output_root.resolve() if output_root else None,
        processed_count=processed_count,
        error_count=error_count,
        review_count=review_count,
        report_json_path=report_json_path,
        report_txt_path=report_txt_path,
        output_mapping_path=output_mapping_path,
        unklar_folder_path=unklar_folder,
        warnings=tuple(warnings),
        status_label=status_label,
        stderr_summary=stderr_summary,
        exit_code=outcome.exit_code,
    )
