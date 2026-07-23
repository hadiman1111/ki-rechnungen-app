"""Track-B UI-v2 export / reporting — pure view models + explicit-path export.

Answers five user questions from ProcessingRunState only:
1. Was wurde erkannt?
2. Was ist unklar?
3. Was ist fehlgeschlagen?
4. Welche Dateien wären wohin gegangen?
5. Welche Zusammenfassung bekommt der Nutzer?

No processing-core imports, no folder scan, no productive execution,
no invented results or private tenant defaults.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from invoice_tool.ui_v2.clarity_copy import (
    MSG_CLARITY_BUCKETS_SEPARATED,
    MSG_CLARITY_EXPORT_FROM_REAL_RUN,
    MSG_CLARITY_EXPORT_PREVIEW,
    MSG_CLARITY_FILENAME_NOT_TRUTH,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.run_result_display import STATUS_LABELS

EXPORT_KIND = "run_result_export"
EXPORT_SCHEMA_VERSION = 1

SECTION_RECOGNIZED = "Was wurde erkannt?"
SECTION_UNCLEAR = "Was ist unklar?"
SECTION_FAILED = "Was ist fehlgeschlagen?"
SECTION_DESTINATIONS = "Welche Dateien wären wohin gegangen?"
SECTION_SUMMARY = "Welche Zusammenfassung bekommt der Nutzer?"

MSG_NO_RUN_PAYLOAD = "Noch kein Laufergebnis zum Berichten vorhanden."
MSG_EXPORT_FROM_REAL_RUN = MSG_CLARITY_EXPORT_FROM_REAL_RUN
MSG_EXPORT_IS_PREVIEW = MSG_CLARITY_EXPORT_PREVIEW
MSG_EXPORT_DISCLAIMER_COMPACT = (
    "Exportvorschau · kein produktiver DATEV-/Cloud-Export"
)
MSG_EXPORT_NO_FILE_MUTATION_OF_ORIGINALS = (
    "Der Export verändert keine Originalbelege und startet keine Verarbeitung."
)
MSG_EXPORT_NEEDS_PATH = "Exportpfad fehlt — bitte eine lokale Zieldatei angeben."
MSG_EXPORT_EMPTY = "Kein Laufergebnis vorhanden — Export nicht möglich."
MSG_EXPORT_OK = "Laufergebnis-Vorschau lokal exportiert (kein produktiver DATEV-/Cloud-Export)."
MSG_DESTINATION_UNKNOWN = "Kein Zielhinweis vorhanden"
MSG_DESTINATION_REVIEW = "Zur Prüfung"
MSG_FAILED_STATUS = "fehlgeschlagen"
MSG_RECOGNIZED_EMPTY = "Keine erkannten Dokumente in diesem Lauf."
MSG_UNCLEAR_EMPTY = "Keine unklaren Fälle in diesem Lauf."
MSG_FAILED_EMPTY = "Keine Fehlschläge in diesem Lauf."
MSG_DESTINATIONS_EMPTY = "Keine Zielhinweise in diesem Lauf."
MSG_PLANNED_DESTINATION_HINT = (
    "Zielhinweise beschreiben die geplante Zuordnung aus dem Laufzustand; "
    "ohne freigegebene Ausführung werden keine Dateien verschoben."
)
MSG_EXPORT_HONEST_COPY = (
    MSG_EXPORT_IS_PREVIEW,
    MSG_EXPORT_FROM_REAL_RUN,
    MSG_EXPORT_NO_FILE_MUTATION_OF_ORIGINALS,
    MSG_PLANNED_DESTINATION_HINT,
    MSG_CLARITY_BUCKETS_SEPARATED,
    MSG_CLARITY_FILENAME_NOT_TRUTH,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
)

DEFAULT_DOCUMENT_LABEL = "Dokument"
DEFAULT_DOCUMENT_TYPE = "unbekannt"
DEFAULT_STATUS = "unbekannt"

# Forbidden basenames — same spirit as SaaS draft export guardrails.
_FORBIDDEN_EXPORT_NAMES = frozenset(
    {
        ".env",
        "credentials.json",
        "secrets.json",
        "office_rules.json",
    }
)


@dataclass(frozen=True)
class RecognizedItemVM:
    document_name: str
    document_type: str
    classification_status: str
    status_label: str
    confidence_label: str | None = None
    target_hint: str | None = None


@dataclass(frozen=True)
class UnclearItemVM:
    document_name: str
    reason: str
    status_label: str
    evidence_summary: str | None = None
    next_action_hint: str | None = None
    document_id: str | None = None


@dataclass(frozen=True)
class FailedItemVM:
    message: str
    document_name: str | None = None
    status_label: str = MSG_FAILED_STATUS


@dataclass(frozen=True)
class DestinationItemVM:
    """Planned destination hint — never invents private folder defaults."""

    document_name: str
    destination_hint: str
    outcome_label: str
    planned_only: bool = True


@dataclass(frozen=True)
class UserSummaryVM:
    """Plain-language summary for the end user."""

    headline: str
    detail: str
    recognized_count: int
    unclear_count: int
    failed_count: int
    destination_count: int
    run_id: str | None
    status_label: str


@dataclass(frozen=True)
class RunReportViewModel:
    """Five-question run report shell — testable without a GUI window."""

    empty: bool
    run_id: str | None
    status: str
    status_label: str
    message: str
    recognized: tuple[RecognizedItemVM, ...]
    unclear: tuple[UnclearItemVM, ...]
    failed: tuple[FailedItemVM, ...]
    destinations: tuple[DestinationItemVM, ...]
    user_summary: UserSummaryVM
    section_titles: tuple[str, ...]
    honest_copy: tuple[str, ...]
    export_available: bool
    mutates_original_files: bool = False
    starts_processing: bool = False


@dataclass(frozen=True)
class RunExportResult:
    ok: bool
    status: str
    path: Path | None = None
    error: str | None = None
    written_files: tuple[str, ...] = field(default_factory=tuple)


def _is_failed_result(item: ProcessingResultSummary) -> bool:
    status = (item.status_label or "").lower()
    classification = (item.classification_status or "").lower()
    return (
        "fehl" in status
        or "error" in status
        or "fail" in status
        or "fail" in classification
        or "error" in classification
    )


def _recognized_from_result(item: ProcessingResultSummary) -> RecognizedItemVM:
    return RecognizedItemVM(
        document_name=(item.document_name or "").strip() or DEFAULT_DOCUMENT_LABEL,
        document_type=(item.document_type or "").strip() or DEFAULT_DOCUMENT_TYPE,
        classification_status=(item.classification_status or "").strip() or DEFAULT_STATUS,
        status_label=(item.status_label or "").strip() or DEFAULT_STATUS,
        confidence_label=(item.confidence_label or "").strip() or None,
        target_hint=(item.target_hint or "").strip() or None,
    )


def _unclear_from_review(item: ProcessingReviewItem) -> UnclearItemVM:
    return UnclearItemVM(
        document_name=(item.document_name or "").strip() or DEFAULT_DOCUMENT_LABEL,
        reason=(item.reason or "").strip() or "Grund nicht angegeben",
        status_label=(item.status_label or "").strip() or "unklar",
        evidence_summary=(item.evidence_summary or "").strip() or None,
        next_action_hint=(item.next_action_hint or "").strip() or None,
        document_id=(item.document_id or "").strip() or None,
    )


def _destination_from_result(item: ProcessingResultSummary) -> DestinationItemVM:
    failed = _is_failed_result(item)
    hint = (item.target_hint or "").strip() or MSG_DESTINATION_UNKNOWN
    return DestinationItemVM(
        document_name=(item.document_name or "").strip() or DEFAULT_DOCUMENT_LABEL,
        destination_hint=hint,
        outcome_label=MSG_FAILED_STATUS if failed else (item.status_label or "erkannt"),
        planned_only=True,
    )


def _destination_from_review(item: ProcessingReviewItem) -> DestinationItemVM:
    return DestinationItemVM(
        document_name=(item.document_name or "").strip() or DEFAULT_DOCUMENT_LABEL,
        destination_hint=MSG_DESTINATION_REVIEW,
        outcome_label=(item.status_label or "").strip() or "unklar",
        planned_only=True,
    )


def build_user_summary(
    *,
    status: str,
    message: str,
    run_id: str | None,
    recognized_count: int,
    unclear_count: int,
    failed_count: int,
    destination_count: int,
) -> UserSummaryVM:
    """Build the plain-language user summary from real counts only."""

    status_label = STATUS_LABELS.get(status, status)  # type: ignore[arg-type]
    if recognized_count == 0 and unclear_count == 0 and failed_count == 0:
        return UserSummaryVM(
            headline=MSG_NO_RUN_PAYLOAD,
            detail=MSG_EXPORT_FROM_REAL_RUN,
            recognized_count=0,
            unclear_count=0,
            failed_count=0,
            destination_count=0,
            run_id=run_id,
            status_label=status_label,
        )

    parts = [
        f"{recognized_count} erkannt",
        f"{unclear_count} unklar",
        f"{failed_count} fehlgeschlagen",
    ]
    headline = f"{status_label}: {', '.join(parts)}."
    detail_bits = [message.strip()] if message.strip() else []
    if destination_count:
        detail_bits.append(
            f"{destination_count} Datei(en) mit Zielhinweis "
            f"(geplante Zuordnung, keine automatische Verschiebung)."
        )
    if run_id:
        detail_bits.append(f"Lauf-ID: {run_id}.")
    return UserSummaryVM(
        headline=headline,
        detail=" ".join(detail_bits).strip() or MSG_PLANNED_DESTINATION_HINT,
        recognized_count=recognized_count,
        unclear_count=unclear_count,
        failed_count=failed_count,
        destination_count=destination_count,
        run_id=run_id,
        status_label=status_label,
    )


def build_run_report_view_model(
    processing_state: ProcessingRunState | None,
) -> RunReportViewModel:
    """Map ProcessingRunState into the five-question report — never invent rows."""

    state = processing_state or ProcessingRunState()
    results = tuple(state.results or ())
    review_items = tuple(state.review_items or ())
    error_messages = tuple(str(item) for item in (state.errors or ()) if str(item).strip())

    recognized: list[RecognizedItemVM] = []
    failed: list[FailedItemVM] = []
    destinations: list[DestinationItemVM] = []

    for item in results:
        if _is_failed_result(item):
            failed.append(
                FailedItemVM(
                    message=(item.status_label or MSG_FAILED_STATUS).strip(),
                    document_name=(item.document_name or "").strip() or None,
                    status_label=(item.status_label or MSG_FAILED_STATUS).strip(),
                )
            )
        else:
            recognized.append(_recognized_from_result(item))

    if state.error_items:
        for item in state.error_items:
            failed.append(
                FailedItemVM(
                    message=item.message,
                    document_name=(item.document_name or "").strip() or None,
                    status_label=item.status_label or MSG_FAILED_STATUS,
                )
            )
    else:
        for message in error_messages:
            failed.append(FailedItemVM(message=message))

    unclear = tuple(_unclear_from_review(item) for item in review_items)

    # Prefer structured planned destinations from dry-run mapping (preview-only).
    if state.planned_destinations:
        for item in state.planned_destinations:
            destinations.append(
                DestinationItemVM(
                    document_name=(item.document_name or "").strip()
                    or DEFAULT_DOCUMENT_LABEL,
                    destination_hint=(item.planned_path or "").strip()
                    or MSG_DESTINATION_UNKNOWN,
                    outcome_label=(item.destination_label or "geplant").strip(),
                    planned_only=True,
                )
            )
    else:
        for item in results:
            destinations.append(_destination_from_result(item))
        for item in review_items:
            destinations.append(_destination_from_review(item))

    run_id = (state.run_id or "").strip() or None
    user_summary = build_user_summary(
        status=state.status,
        message=state.message or "",
        run_id=run_id,
        recognized_count=len(recognized),
        unclear_count=len(unclear),
        failed_count=len(failed),
        destination_count=len(destinations),
    )
    empty = not recognized and not unclear and not failed
    return RunReportViewModel(
        empty=empty,
        run_id=run_id,
        status=state.status,
        status_label=STATUS_LABELS.get(state.status, state.status),  # type: ignore[arg-type]
        message=state.message or "",
        recognized=tuple(recognized),
        unclear=unclear,
        failed=tuple(failed),
        destinations=tuple(destinations),
        user_summary=user_summary,
        section_titles=(
            SECTION_RECOGNIZED,
            SECTION_UNCLEAR,
            SECTION_FAILED,
            SECTION_DESTINATIONS,
            SECTION_SUMMARY,
        ),
        honest_copy=MSG_EXPORT_HONEST_COPY,
        export_available=not empty,
        mutates_original_files=False,
        starts_processing=False,
    )


def build_run_export_payload(report: RunReportViewModel) -> dict[str, Any]:
    """Build a portable JSON-serializable export envelope from a report VM."""

    return {
        "kind": EXPORT_KIND,
        "schema_version": EXPORT_SCHEMA_VERSION,
        "cloud": False,
        "preview": True,
        "productive_export": False,
        "datev_export": False,
        "cloud_export": False,
        "persistence": "local_export_only",
        "disclaimer": MSG_EXPORT_IS_PREVIEW,
        # Preview may reflect a real Core Dry-Run ProcessingRunState when present.
        "sourced_from_real_dry_run": bool(report.run_id) and not report.empty,
        "run_id": report.run_id,
        "status": report.status,
        "status_label": report.status_label,
        "message": report.message,
        "questions": {
            "recognized": {
                "title": SECTION_RECOGNIZED,
                "count": len(report.recognized),
                "empty_detail": MSG_RECOGNIZED_EMPTY,
                "items": [
                    {
                        "document_name": item.document_name,
                        "document_type": item.document_type,
                        "classification_status": item.classification_status,
                        "status_label": item.status_label,
                        "confidence_label": item.confidence_label,
                        "target_hint": item.target_hint,
                    }
                    for item in report.recognized
                ],
            },
            "unclear": {
                "title": SECTION_UNCLEAR,
                "count": len(report.unclear),
                "empty_detail": MSG_UNCLEAR_EMPTY,
                "items": [
                    {
                        "document_name": item.document_name,
                        "reason": item.reason,
                        "status_label": item.status_label,
                        "evidence_summary": item.evidence_summary,
                        "next_action_hint": item.next_action_hint,
                        "document_id": item.document_id,
                    }
                    for item in report.unclear
                ],
            },
            "failed": {
                "title": SECTION_FAILED,
                "count": len(report.failed),
                "empty_detail": MSG_FAILED_EMPTY,
                "items": [
                    {
                        "message": item.message,
                        "document_name": item.document_name,
                        "status_label": item.status_label,
                    }
                    for item in report.failed
                ],
            },
            "destinations": {
                "title": SECTION_DESTINATIONS,
                "count": len(report.destinations),
                "empty_detail": MSG_DESTINATIONS_EMPTY,
                "planned_only": True,
                "hint": MSG_PLANNED_DESTINATION_HINT,
                "items": [
                    {
                        "document_name": item.document_name,
                        "destination_hint": item.destination_hint,
                        "outcome_label": item.outcome_label,
                        "planned_only": item.planned_only,
                    }
                    for item in report.destinations
                ],
            },
            "user_summary": {
                "title": SECTION_SUMMARY,
                "headline": report.user_summary.headline,
                "detail": report.user_summary.detail,
                "recognized_count": report.user_summary.recognized_count,
                "unclear_count": report.user_summary.unclear_count,
                "failed_count": report.user_summary.failed_count,
                "destination_count": report.user_summary.destination_count,
                "run_id": report.user_summary.run_id,
                "status_label": report.user_summary.status_label,
            },
        },
        "honest_copy": list(report.honest_copy),
    }


def render_run_export_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n"


def render_run_export_csv(report: RunReportViewModel) -> str:
    """CSV of planned destinations + outcome — complements the JSON export."""

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ("document_name", "destination_hint", "outcome_label", "planned_only", "bucket")
    )
    for item in report.recognized:
        writer.writerow(
            (
                item.document_name,
                item.target_hint or MSG_DESTINATION_UNKNOWN,
                item.status_label,
                "true",
                "recognized",
            )
        )
    for item in report.unclear:
        writer.writerow(
            (
                item.document_name,
                MSG_DESTINATION_REVIEW,
                item.status_label,
                "true",
                "unclear",
            )
        )
    for item in report.failed:
        writer.writerow(
            (
                item.document_name or "",
                MSG_DESTINATION_UNKNOWN,
                item.status_label,
                "true",
                "failed",
            )
        )
    return buffer.getvalue()


def _validate_export_target(path: Path) -> str | None:
    name = path.name.strip()
    if not name:
        return MSG_EXPORT_NEEDS_PATH
    if name in _FORBIDDEN_EXPORT_NAMES:
        return f"Verbotener Exportzielname: {name}"
    return None


def write_run_report_export(
    report: RunReportViewModel,
    export_path: Path | str,
    *,
    include_csv: bool = True,
) -> RunExportResult:
    """Write run report JSON (and optional CSV) to an explicit local path only."""

    if report.empty or not report.export_available:
        return RunExportResult(ok=False, status="empty", error=MSG_EXPORT_EMPTY)

    raw = str(export_path or "").strip()
    if not raw:
        return RunExportResult(ok=False, status="missing_path", error=MSG_EXPORT_NEEDS_PATH)

    target = Path(raw)
    if target.suffix.lower() in {"", "."}:
        # Directory-like target → default filenames inside it.
        json_path = target / "laufbericht.json"
        csv_path = target / "laufbericht_routing.csv"
    elif target.suffix.lower() == ".csv":
        json_path = target.with_suffix(".json")
        csv_path = target
    else:
        json_path = target if target.suffix else target.with_suffix(".json")
        csv_path = json_path.with_name(json_path.stem + "_routing.csv")

    for candidate in (json_path, csv_path):
        err = _validate_export_target(candidate)
        if err:
            return RunExportResult(ok=False, status="blocked", path=candidate, error=err)

    payload = build_run_export_payload(report)
    written: list[str] = []
    try:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(render_run_export_json(payload), encoding="utf-8")
        written.append(str(json_path))
        if include_csv:
            csv_path.write_text(render_run_export_csv(report), encoding="utf-8")
            written.append(str(csv_path))
    except OSError as exc:
        return RunExportResult(
            ok=False,
            status="failed",
            path=json_path,
            error=f"Export fehlgeschlagen: {exc}",
        )

    return RunExportResult(
        ok=True,
        status="exported",
        path=json_path,
        written_files=tuple(written),
    )


def export_processing_run_state(
    processing_state: ProcessingRunState | None,
    export_path: Path | str,
    *,
    include_csv: bool = True,
) -> RunExportResult:
    """Convenience: build report from run state and write to an explicit path."""

    report = build_run_report_view_model(processing_state)
    return write_run_report_export(report, export_path, include_csv=include_csv)


__all__ = (
    "DEFAULT_DOCUMENT_LABEL",
    "DEFAULT_DOCUMENT_TYPE",
    "DEFAULT_STATUS",
    "DestinationItemVM",
    "EXPORT_KIND",
    "EXPORT_SCHEMA_VERSION",
    "FailedItemVM",
    "MSG_DESTINATION_REVIEW",
    "MSG_DESTINATION_UNKNOWN",
    "MSG_DESTINATIONS_EMPTY",
    "MSG_EXPORT_EMPTY",
    "MSG_EXPORT_FROM_REAL_RUN",
    "MSG_EXPORT_HONEST_COPY",
    "MSG_EXPORT_IS_PREVIEW",
    "MSG_EXPORT_NEEDS_PATH",
    "MSG_EXPORT_NO_FILE_MUTATION_OF_ORIGINALS",
    "MSG_EXPORT_OK",
    "MSG_FAILED_EMPTY",
    "MSG_FAILED_STATUS",
    "MSG_NO_RUN_PAYLOAD",
    "MSG_PLANNED_DESTINATION_HINT",
    "MSG_RECOGNIZED_EMPTY",
    "MSG_UNCLEAR_EMPTY",
    "RecognizedItemVM",
    "RunExportResult",
    "RunReportViewModel",
    "SECTION_DESTINATIONS",
    "SECTION_FAILED",
    "SECTION_RECOGNIZED",
    "SECTION_SUMMARY",
    "SECTION_UNCLEAR",
    "UnclearItemVM",
    "UserSummaryVM",
    "build_run_export_payload",
    "build_run_report_view_model",
    "build_user_summary",
    "export_processing_run_state",
    "render_run_export_csv",
    "render_run_export_json",
    "write_run_report_export",
)
