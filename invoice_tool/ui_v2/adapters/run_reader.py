"""Read-only run and report data for UI-v2."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from invoice_tool import app_paths
from invoice_tool.ui_v2.adapters.path_display import sanitize_path_for_display
from invoice_tool.ui_v2.view_models import ResultSummaryVM, RunSummaryVM

logger = logging.getLogger(__name__)

_REVIEW_STATUSES = frozenset({"unklar", "error", "failed"})
_SUCCESS_STATUSES = frozenset({"success", "document", "ok"})


def _latest_report_path() -> Path | None:
    runs_root = app_paths.run_support_root()
    if not runs_root.is_dir():
        return None
    candidates = sorted(
        runs_root.glob("*/report.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _load_report_data() -> tuple[dict | None, RunSummaryVM]:
    report_path = _latest_report_path()
    if report_path is None:
        return None, RunSummaryVM(availability="no_run", status_label="Noch kein Lauf")

    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Laufbericht nicht lesbar: %s", exc)
        return None, RunSummaryVM(
            availability="malformed",
            run_id=report_path.parent.name,
            status_label="Laufbericht unvollständig",
            warnings=("Letzter Laufbericht konnte nicht gelesen werden.",),
        )

    if not isinstance(data, dict):
        return None, RunSummaryVM(
            availability="malformed",
            run_id=report_path.parent.name,
            status_label="Laufbericht unvollständig",
            warnings=("Letzter Laufbericht hat ein unerwartetes Format.",),
        )

    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    return data, RunSummaryVM(
        availability="available",
        run_id=str(data.get("run_id") or report_path.parent.name),
        run_timestamp=str(data.get("date") or report_path.parent.name),
        status_label="Abgeschlossen",
        processed_count=_int_or_none(summary.get("processed")),
        success_count=_int_or_none(summary.get("documents")),
        duplicate_count=_int_or_none(summary.get("duplicates")),
        unclear_count=_int_or_none(summary.get("unklar")),
        error_count=_int_or_none(summary.get("errors")),
    )


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def get_latest_run_summary() -> RunSummaryVM:
    _, run = _load_report_data()
    return run


def get_latest_result_summaries(*, limit: int = 12) -> tuple[ResultSummaryVM, ...]:
    data, run = _load_report_data()
    if run.availability != "available" or not isinstance(data, dict):
        return tuple()

    files = data.get("files")
    if not isinstance(files, list):
        return tuple()

    rows: list[ResultSummaryVM] = []
    for item in files[:limit]:
        if not isinstance(item, dict):
            continue
        filename = str(item.get("filename") or "—")
        status = str(item.get("status") or "unknown")
        config_label = str(item.get("type") or "—")
        output = sanitize_path_for_display(str(item.get("output") or ""))
        if output == "Noch nicht konfiguriert":
            output = "—"
        rows.append(
            ResultSummaryVM(
                filename=filename,
                configuration_label=config_label,
                destination_summary=output,
                status_label=status,
            )
        )
    return tuple(rows)


def count_result_items() -> int | None:
    data, run = _load_report_data()
    if run.availability == "no_run":
        return None
    if run.availability == "malformed" or not isinstance(data, dict):
        return None
    files = data.get("files")
    if not isinstance(files, list):
        return None
    return len(files)
