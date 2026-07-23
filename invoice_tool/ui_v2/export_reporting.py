"""Track-B UI-v2 export / reporting preview polish (Prompt 5/34).

Builds honest preview reports from real ProcessingRunState / Track-B result
mapping only. Preview-only — no productive processing, no final file writes
of invoices, no invented rows, no Track-A coupling.
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
    MSG_EMPTY_DRY_RUN,
    MSG_PLANNED_DESTINATION_PREVIEW_ONLY,
    MSG_SAFETY_PROOF_COMPACT,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.result_mapping import (
    MSG_EXPORT_REMAINS_PREVIEW,
    build_result_bucket_summary,
)
from invoice_tool.ui_v2.run_result_display import STATUS_LABELS

EXPORT_KIND = "run_result_export"
EXPORT_SCHEMA_VERSION = 2

REPORT_TITLE = "Export-Vorschau"

SECTION_RECOGNIZED = "Was wurde erkannt?"
SECTION_UNCLEAR = "Was ist unklar?"
SECTION_FAILED = "Was ist fehlgeschlagen?"
SECTION_DESTINATIONS = "Welche Dateien wären wohin gegangen?"
SECTION_SUMMARY = "Welche Zusammenfassung bekommt der Nutzer?"

# Preview-only wording (Prompt 5/34).
MSG_EXPORT_PREVIEW_TITLE = REPORT_TITLE
MSG_NO_SANDBOX_RUN = "Noch kein Sandbox-Lauf vorhanden."
MSG_NO_RUN_PAYLOAD = MSG_NO_SANDBOX_RUN
MSG_EXPORT_FROM_REAL_RUN = MSG_CLARITY_EXPORT_FROM_REAL_RUN
MSG_EXPORT_IS_PREVIEW = MSG_CLARITY_EXPORT_PREVIEW
MSG_NO_FINAL_FILES_WRITTEN = "Keine Dateien wurden final geschrieben."
MSG_ORIGINALS_UNCHANGED = "Originale unverändert."
MSG_PRODUCTIVE_PROCESSING_BLOCKED = "Produktive Verarbeitung gesperrt."
MSG_TARGET_PATHS_VORSCHAU_ONLY = (
    "Zielpfade sind Vorschläge aus dem Sandbox-Dry-Run."
)
# Back-compat alias — do not import this name into workspace.py (guard token).
MSG_TARGET_PATHS_PREVIEW_ONLY = MSG_TARGET_PATHS_VORSCHAU_ONLY
MSG_VORSCHAU_NOT_PRODUCTIVE_RUN = (
    "Diese Vorschau ersetzt keinen finalen Produktivlauf."
)
# Back-compat alias — do not import this name into workspace.py (guard token).
MSG_PREVIEW_NOT_PRODUCTIVE_RUN = MSG_VORSCHAU_NOT_PRODUCTIVE_RUN
MSG_EXPORT_DISCLAIMER_COMPACT = (
    "Exportvorschau · kein produktiver DATEV-/Cloud-Export"
)
MSG_EXPORT_NO_FILE_MUTATION_OF_ORIGINALS = (
    "Der Export verändert keine Originalbelege und startet keine Verarbeitung."
)
MSG_EXPORT_NEEDS_PATH = "Exportpfad fehlt — bitte eine lokale Zieldatei angeben."
MSG_EXPORT_EMPTY = "Kein Laufergebnis vorhanden — Export nicht möglich."
MSG_EXPORT_OK = (
    "Export-Vorschau lokal geschrieben (kein produktiver DATEV-/Cloud-Export)."
)
MSG_DESTINATION_UNKNOWN = "Kein Zielhinweis vorhanden"
MSG_DESTINATION_REVIEW = "Zur Prüfung"
MSG_FAILED_STATUS = "fehlgeschlagen"
MSG_RECOGNIZED_EMPTY = "Keine erkannten Dokumente in diesem Lauf."
MSG_UNCLEAR_EMPTY = "Keine unklaren Fälle in diesem Lauf."
MSG_FAILED_EMPTY = "Keine Fehlschläge in diesem Lauf."
MSG_DESTINATIONS_EMPTY = "Keine Zielhinweise in diesem Lauf."
MSG_WARNINGS_EMPTY = "Keine Warnungen in diesem Lauf."
MSG_EMPTY_RUN_STATE = MSG_EMPTY_DRY_RUN
MSG_ALL_REVIEW_HEAVY = "Sandbox-Lauf mit Prüffällen — überwiegend zur Prüfung."
MSG_PLANNED_DESTINATION_HINT = MSG_TARGET_PATHS_VORSCHAU_ONLY
# After Prompt 6/34 acceptance: sandbox-only local pilot may be accepted,
# but never as productive Local-Pilot-Ready / SaaS-Ready / production-ready.
MSG_LOCAL_PILOT_SANDBOX_ONLY = (
    "Local-Pilot akzeptiert nur Sandbox — nicht produktiv freigegeben."
)
MSG_LOCAL_PILOT_NOT_READY = MSG_LOCAL_PILOT_SANDBOX_ONLY
MSG_SAAS_NOT_READY = "SaaS-Ready ist nicht erreicht."
PRODUCT_STATUS_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY = (
    "TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY"
)
PRODUCT_STATUS_LOCAL_PILOT_PENDING_WITH_BLOCKERS = (
    "TRACK_B_LOCAL_PILOT_ACCEPTANCE_PENDING_WITH_BLOCKERS"
)

MSG_EXPORT_HONEST_COPY = (
    MSG_EXPORT_PREVIEW_TITLE,
    MSG_EXPORT_IS_PREVIEW,
    MSG_NO_FINAL_FILES_WRITTEN,
    MSG_ORIGINALS_UNCHANGED,
    MSG_PRODUCTIVE_PROCESSING_BLOCKED,
    MSG_TARGET_PATHS_PREVIEW_ONLY,
    MSG_PREVIEW_NOT_PRODUCTIVE_RUN,
    MSG_EXPORT_FROM_REAL_RUN,
    MSG_EXPORT_NO_FILE_MUTATION_OF_ORIGINALS,
    MSG_PLANNED_DESTINATION_PREVIEW_ONLY,
    MSG_EXPORT_REMAINS_PREVIEW,
    MSG_CLARITY_BUCKETS_SEPARATED,
    MSG_CLARITY_FILENAME_NOT_TRUTH,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
    MSG_LOCAL_PILOT_NOT_READY,
    MSG_SAAS_NOT_READY,
)

DEFAULT_DOCUMENT_LABEL = "Dokument"
DEFAULT_DOCUMENT_TYPE = "unbekannt"
DEFAULT_STATUS = "unbekannt"
DEFAULT_PATH_DISPLAY = "—"
DEFAULT_PROFILE_DISPLAY = "—"

# Forbidden basenames — same spirit as SaaS draft export guardrails.
_FORBIDDEN_EXPORT_NAMES = frozenset(
    {
        ".env",
        "credentials.json",
        "secrets.json",
        "office_rules.json",
    }
)

# Phrases that must never appear as positive maturity / write claims.
FORBIDDEN_REPORT_CLAIM_MARKERS = (
    "local_pilot_ready",
    "local-pilot-ready",
    "saas ready",
    "saas-ready",
    "saas_ready",
    "final geschrieben",
    "final verarbeitet",
    "produktiv verarbeitet",
    "gebucht",
    "archiviert",
    "verschoben",
    "umbenannt",
    "verbucht",
)


@dataclass(frozen=True)
class ExportPreviewContext:
    """Optional workspace context for preview headers — never invents paths."""

    sandbox_input_path: str | None = None
    sandbox_output_path: str | None = None
    profile_display: str | None = None
    config_display: str | None = None


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
    preview_only_label: str = MSG_TARGET_PATHS_PREVIEW_ONLY


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
    warning_count: int = 0


@dataclass(frozen=True)
class RunReportViewModel:
    """Export-Vorschau shell — testable without a GUI window."""

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
    # Prompt 5/34 preview polish fields
    title: str = REPORT_TITLE
    no_run: bool = False
    outcome_kind: str | None = None
    sandbox_input_path: str | None = None
    sandbox_output_path: str | None = None
    profile_display: str | None = None
    config_display: str | None = None
    recognized_count: int = 0
    review_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    planned_destination_count: int = 0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    safety_proof: str = MSG_SAFETY_PROOF_COMPACT
    review_summary: str = MSG_UNCLEAR_EMPTY
    error_summary: str = MSG_FAILED_EMPTY
    warning_summary: str = MSG_WARNINGS_EMPTY
    preview_only: bool = True
    claims_final_files_written: bool = False
    claims_productive_processing: bool = False
    claims_local_pilot_ready: bool = False
    claims_saas_ready: bool = False


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
        preview_only_label=MSG_TARGET_PATHS_PREVIEW_ONLY,
    )


def _destination_from_review(item: ProcessingReviewItem) -> DestinationItemVM:
    return DestinationItemVM(
        document_name=(item.document_name or "").strip() or DEFAULT_DOCUMENT_LABEL,
        destination_hint=MSG_DESTINATION_REVIEW,
        outcome_label=(item.status_label or "").strip() or "unklar",
        planned_only=True,
        preview_only_label=MSG_TARGET_PATHS_PREVIEW_ONLY,
    )


def _display_path(value: str | None) -> str:
    cleaned = (value or "").strip()
    return cleaned or DEFAULT_PATH_DISPLAY


def _display_profile(value: str | None) -> str:
    cleaned = (value or "").strip()
    return cleaned or DEFAULT_PROFILE_DISPLAY


def _is_no_run(state: ProcessingRunState) -> bool:
    """True when there is no sandbox run payload to report (idle shell)."""

    if (state.run_id or "").strip():
        return False
    if state.status in {"completed", "failed", "blocked"}:
        return False
    if state.results or state.review_items or state.error_items or state.errors:
        return False
    if state.planned_destinations or state.warnings:
        return False
    return state.status in {"idle", "ready", "not_configured", "running"}


def build_user_summary(
    *,
    status: str,
    message: str,
    run_id: str | None,
    recognized_count: int,
    unclear_count: int,
    failed_count: int,
    destination_count: int,
    warning_count: int = 0,
    no_run: bool = False,
    outcome_kind: str | None = None,
) -> UserSummaryVM:
    """Build the plain-language user summary from real counts only."""

    status_label = STATUS_LABELS.get(status, status)  # type: ignore[arg-type]
    if no_run:
        return UserSummaryVM(
            headline=MSG_NO_SANDBOX_RUN,
            detail=MSG_EXPORT_FROM_REAL_RUN,
            recognized_count=0,
            unclear_count=0,
            failed_count=0,
            destination_count=0,
            run_id=run_id,
            status_label=status_label,
            warning_count=0,
        )

    if outcome_kind == "empty" or (
        recognized_count == 0
        and unclear_count == 0
        and failed_count == 0
        and status == "completed"
    ):
        return UserSummaryVM(
            headline=MSG_EMPTY_RUN_STATE,
            detail=(message.strip() or MSG_EMPTY_RUN_STATE),
            recognized_count=0,
            unclear_count=0,
            failed_count=0,
            destination_count=destination_count,
            run_id=run_id,
            status_label=status_label,
            warning_count=warning_count,
        )

    if outcome_kind == "all_review" or (
        unclear_count > 0 and recognized_count == 0 and failed_count == 0
    ):
        headline = MSG_ALL_REVIEW_HEAVY
    elif status == "failed" or outcome_kind == "failed":
        headline = f"{status_label}: {failed_count} fehlgeschlagen."
    else:
        parts = [
            f"{recognized_count} erkannt",
            f"{unclear_count} unklar",
            f"{failed_count} fehlgeschlagen",
        ]
        if warning_count:
            parts.append(f"{warning_count} Warnung(en)")
        headline = f"{status_label}: {', '.join(parts)}."

    detail_bits = [message.strip()] if message.strip() else []
    if destination_count:
        detail_bits.append(
            f"{destination_count} geplante Zielpfad(e) "
            f"({MSG_TARGET_PATHS_PREVIEW_ONLY})"
        )
    detail_bits.extend(
        (
            MSG_NO_FINAL_FILES_WRITTEN,
            MSG_ORIGINALS_UNCHANGED,
            MSG_PRODUCTIVE_PROCESSING_BLOCKED,
        )
    )
    if run_id:
        detail_bits.append(f"Lauf-ID: {run_id}.")
    return UserSummaryVM(
        headline=headline,
        detail=" ".join(detail_bits).strip() or MSG_TARGET_PATHS_PREVIEW_ONLY,
        recognized_count=recognized_count,
        unclear_count=unclear_count,
        failed_count=failed_count,
        destination_count=destination_count,
        run_id=run_id,
        status_label=status_label,
        warning_count=warning_count,
    )


def build_run_report_view_model(
    processing_state: ProcessingRunState | None,
    context: ExportPreviewContext | None = None,
) -> RunReportViewModel:
    """Map ProcessingRunState into the Export-Vorschau — never invent rows."""

    state = processing_state or ProcessingRunState()
    ctx = context or ExportPreviewContext()
    buckets = build_result_bucket_summary(state)
    results = tuple(state.results or ())
    review_items = tuple(state.review_items or ())
    error_messages = tuple(str(item) for item in (state.errors or ()) if str(item).strip())
    warnings = tuple(str(item) for item in (state.warnings or ()) if str(item).strip())

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

    # Failed / blocked runs without structured rows still surface the blocker.
    if state.status in {"failed", "blocked"} and not failed:
        blocker = (state.message or "").strip() or MSG_FAILED_STATUS
        failed.append(FailedItemVM(message=blocker, status_label=MSG_FAILED_STATUS))

    unclear = tuple(_unclear_from_review(item) for item in review_items)

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
                    preview_only_label=MSG_TARGET_PATHS_PREVIEW_ONLY,
                )
            )
    else:
        for item in results:
            destinations.append(_destination_from_result(item))
        for item in review_items:
            destinations.append(_destination_from_review(item))

    run_id = (state.run_id or "").strip() or None
    no_run = _is_no_run(state)
    recognized_count = len(recognized)
    review_count = len(unclear)
    error_count = len(failed)
    warning_count = len(warnings)
    planned_count = int(
        state.planned_destination_count or len(destinations) or buckets.planned_destination_count
    )
    outcome = state.outcome_kind or buckets.outcome_kind

    user_summary = build_user_summary(
        status=state.status,
        message=state.message or "",
        run_id=run_id,
        recognized_count=recognized_count,
        unclear_count=review_count,
        failed_count=error_count,
        destination_count=planned_count,
        warning_count=warning_count,
        no_run=no_run,
        outcome_kind=outcome,
    )

    empty_rows = not recognized and not unclear and not failed and not warnings
    empty = no_run or (
        empty_rows
        and outcome in {None, "idle", "empty", "ready", "not_configured"}
        and state.status not in {"failed", "blocked"}
    )
    # Preview export is available for any real sandbox run — including empty/failed.
    export_available = not no_run

    if unclear:
        review_summary = "; ".join(
            f"{item.document_name}: {item.reason}" for item in unclear[:12]
        )
    elif outcome == "all_review":
        review_summary = MSG_ALL_REVIEW_HEAVY
    else:
        review_summary = MSG_UNCLEAR_EMPTY

    if failed:
        error_summary = "; ".join(
            (
                f"{item.document_name}: {item.message}"
                if item.document_name
                else item.message
            )
            for item in failed[:12]
        )
    else:
        error_summary = MSG_FAILED_EMPTY

    warning_summary = (
        "; ".join(warnings[:12]) if warnings else MSG_WARNINGS_EMPTY
    )
    safety = (
        (state.safety_proof_summary or "").strip()
        or buckets.safety_proof_line
        or MSG_SAFETY_PROOF_COMPACT
    )

    status_label = buckets.status_label
    if outcome == "all_review":
        status_label = "Mit Prüffällen"
    elif outcome == "empty" and state.status == "completed":
        status_label = "Leer"
    elif state.status in STATUS_LABELS and outcome not in {
        "all_review",
        "empty",
        "mixed",
        "failed",
        "blocked",
    }:
        status_label = STATUS_LABELS[state.status]

    profile = _display_profile(ctx.profile_display)
    config = _display_profile(ctx.config_display)
    if profile != DEFAULT_PROFILE_DISPLAY and config != DEFAULT_PROFILE_DISPLAY:
        profile_display = f"{profile} / {config}"
    elif profile != DEFAULT_PROFILE_DISPLAY:
        profile_display = profile
    elif config != DEFAULT_PROFILE_DISPLAY:
        profile_display = config
    else:
        profile_display = DEFAULT_PROFILE_DISPLAY

    return RunReportViewModel(
        empty=empty,
        run_id=run_id,
        status=state.status,
        status_label=status_label,
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
        export_available=export_available,
        mutates_original_files=False,
        starts_processing=False,
        title=REPORT_TITLE,
        no_run=no_run,
        outcome_kind=outcome,
        sandbox_input_path=_display_path(ctx.sandbox_input_path),
        sandbox_output_path=_display_path(ctx.sandbox_output_path),
        profile_display=profile_display,
        config_display=_display_profile(ctx.config_display),
        recognized_count=recognized_count,
        review_count=review_count,
        error_count=error_count,
        warning_count=warning_count,
        planned_destination_count=planned_count,
        warnings=warnings,
        safety_proof=safety,
        review_summary=review_summary,
        error_summary=error_summary,
        warning_summary=warning_summary,
        preview_only=True,
        claims_final_files_written=False,
        claims_productive_processing=False,
        claims_local_pilot_ready=False,
        claims_saas_ready=False,
    )


def build_export_preview_report(
    processing_state: ProcessingRunState | None,
    context: ExportPreviewContext | None = None,
) -> RunReportViewModel:
    """Prompt-5 helper alias — same preview report as ``build_run_report_view_model``."""

    return build_run_report_view_model(processing_state, context)


def render_export_preview_text(report: RunReportViewModel) -> str:
    """In-memory text preview — no filesystem IO."""

    if report.no_run:
        lines = [
            report.title,
            MSG_NO_SANDBOX_RUN,
            MSG_NO_FINAL_FILES_WRITTEN,
            MSG_ORIGINALS_UNCHANGED,
            MSG_PRODUCTIVE_PROCESSING_BLOCKED,
            MSG_VORSCHAU_NOT_PRODUCTIVE_RUN,
        ]
        return "\n".join(lines) + "\n"

    lines = [
        report.title,
        f"Lauf-ID: {report.run_id or DEFAULT_PATH_DISPLAY}",
        f"Status: {report.status_label}",
        f"Sandbox-Quellpfad: {report.sandbox_input_path or DEFAULT_PATH_DISPLAY}",
        f"Sandbox-Zielpfad: {report.sandbox_output_path or DEFAULT_PATH_DISPLAY}",
        f"Profil/Konfiguration: {report.profile_display or DEFAULT_PROFILE_DISPLAY}",
        f"Erkannt: {report.recognized_count}",
        f"Zur Prüfung: {report.review_count}",
        f"Fehler: {report.error_count}",
        f"Warnungen: {report.warning_count}",
        f"Geplante Ziele (Vorschau): {report.planned_destination_count}",
        f"Sicherheitsnachweis: {report.safety_proof}",
        f"Prüffälle: {report.review_summary}",
        f"Fehlerübersicht: {report.error_summary}",
        f"Warnungen: {report.warning_summary}",
        MSG_TARGET_PATHS_PREVIEW_ONLY,
        MSG_NO_FINAL_FILES_WRITTEN,
        MSG_ORIGINALS_UNCHANGED,
        MSG_PRODUCTIVE_PROCESSING_BLOCKED,
        MSG_PREVIEW_NOT_PRODUCTIVE_RUN,
        MSG_LOCAL_PILOT_NOT_READY,
        MSG_SAAS_NOT_READY,
    ]
    if report.destinations:
        lines.append("Geplante Zielpfade (Vorschau):")
        for item in report.destinations[:32]:
            lines.append(
                f"  - {item.document_name} → {item.destination_hint} "
                f"[{item.preview_only_label}]"
            )
    if report.message:
        lines.append(f"Meldung: {report.message}")
    lines.append(f"Zusammenfassung: {report.user_summary.headline}")
    return "\n".join(lines) + "\n"


def build_run_export_payload(report: RunReportViewModel) -> dict[str, Any]:
    """Build a portable JSON-serializable export envelope from a report VM."""

    return {
        "kind": EXPORT_KIND,
        "schema_version": EXPORT_SCHEMA_VERSION,
        "title": report.title,
        "cloud": False,
        "preview": True,
        "preview_only": True,
        "productive_export": False,
        "datev_export": False,
        "cloud_export": False,
        "persistence": "local_export_only",
        "disclaimer": MSG_EXPORT_IS_PREVIEW,
        "preview_disclaimers": [
            MSG_NO_FINAL_FILES_WRITTEN,
            MSG_ORIGINALS_UNCHANGED,
            MSG_PRODUCTIVE_PROCESSING_BLOCKED,
            MSG_TARGET_PATHS_PREVIEW_ONLY,
            MSG_VORSCHAU_NOT_PRODUCTIVE_RUN,
        ],
        "sourced_from_real_dry_run": (not report.no_run) and bool(report.run_id),
        "no_run": report.no_run,
        "run_id": report.run_id,
        "status": report.status,
        "status_label": report.status_label,
        "outcome_kind": report.outcome_kind,
        "message": report.message,
        "sandbox_input_path": report.sandbox_input_path,
        "sandbox_output_path": report.sandbox_output_path,
        "profile_display": report.profile_display,
        "config_display": report.config_display,
        "counts": {
            "recognized": report.recognized_count,
            "review": report.review_count,
            "error": report.error_count,
            "warning": report.warning_count,
            "planned_destination": report.planned_destination_count,
        },
        "safety_proof": report.safety_proof,
        "warnings": list(report.warnings),
        "review_summary": report.review_summary,
        "error_summary": report.error_summary,
        "warning_summary": report.warning_summary,
        "claims": {
            "final_files_written": report.claims_final_files_written,
            "productive_processing": report.claims_productive_processing,
            "local_pilot_ready": report.claims_local_pilot_ready,
            "saas_ready": report.claims_saas_ready,
        },
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
                "preview_only": True,
                "hint": MSG_TARGET_PATHS_PREVIEW_ONLY,
                "items": [
                    {
                        "document_name": item.document_name,
                        "destination_hint": item.destination_hint,
                        "outcome_label": item.outcome_label,
                        "planned_only": item.planned_only,
                        "preview_only_label": item.preview_only_label,
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
                "warning_count": report.user_summary.warning_count,
                "run_id": report.user_summary.run_id,
                "status_label": report.user_summary.status_label,
            },
        },
        "honest_copy": list(report.honest_copy),
        "preview_text": render_export_preview_text(report),
    }


def render_run_export_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n"


def render_run_export_csv(report: RunReportViewModel) -> str:
    """CSV of planned destinations + outcome — complements the JSON export."""

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        (
            "document_name",
            "destination_hint",
            "outcome_label",
            "planned_only",
            "preview_only",
            "bucket",
        )
    )
    for item in report.recognized:
        writer.writerow(
            (
                item.document_name,
                item.target_hint or MSG_DESTINATION_UNKNOWN,
                item.status_label,
                "true",
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
                "true",
                "failed",
            )
        )
    for item in report.destinations:
        writer.writerow(
            (
                item.document_name,
                item.destination_hint,
                item.outcome_label,
                "true",
                "true",
                "planned_destination_preview",
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

    if report.no_run or not report.export_available:
        return RunExportResult(ok=False, status="empty", error=MSG_EXPORT_EMPTY)

    raw = str(export_path or "").strip()
    if not raw:
        return RunExportResult(ok=False, status="missing_path", error=MSG_EXPORT_NEEDS_PATH)

    target = Path(raw)
    if target.suffix.lower() in {"", "."}:
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
    context: ExportPreviewContext | None = None,
) -> RunExportResult:
    """Convenience: build preview report from run state and write to an explicit path."""

    report = build_run_report_view_model(processing_state, context)
    return write_run_report_export(report, export_path, include_csv=include_csv)


def report_contains_forbidden_claims(report: RunReportViewModel) -> bool:
    """Return True if preview text/copy accidentally asserts maturity or final writes."""

    if (
        report.claims_final_files_written
        or report.claims_productive_processing
        or report.claims_local_pilot_ready
        or report.claims_saas_ready
    ):
        return True

    blob = " ".join(
        (
            render_export_preview_text(report),
            " ".join(report.honest_copy),
            report.user_summary.headline,
            report.user_summary.detail,
            report.message,
        )
    ).lower()

    # Explicit negative disclaimers are required and allowed.
    allowed_windows = (
        "keine dateien wurden final geschrieben",
        "local-pilot-ready ist nicht erreicht",
        "saas-ready ist nicht erreicht",
        "produktive verarbeitung gesperrt",
        "produktive verarbeitung ist noch nicht freigegeben",
    )
    scrubbed = blob
    for allowed in allowed_windows:
        scrubbed = scrubbed.replace(allowed, " ")

    for marker in FORBIDDEN_REPORT_CLAIM_MARKERS:
        if marker not in scrubbed:
            continue
        window = scrubbed[
            max(0, scrubbed.find(marker) - 40) : scrubbed.find(marker) + len(marker) + 40
        ]
        if "nicht" in window or "keine" in window or "gesperrt" in window:
            continue
        return True
    return False


__all__ = (
    "DEFAULT_DOCUMENT_LABEL",
    "DEFAULT_DOCUMENT_TYPE",
    "DEFAULT_STATUS",
    "DestinationItemVM",
    "EXPORT_KIND",
    "EXPORT_SCHEMA_VERSION",
    "ExportPreviewContext",
    "FORBIDDEN_REPORT_CLAIM_MARKERS",
    "FailedItemVM",
    "MSG_ALL_REVIEW_HEAVY",
    "MSG_DESTINATION_REVIEW",
    "MSG_DESTINATION_UNKNOWN",
    "MSG_DESTINATIONS_EMPTY",
    "MSG_EMPTY_RUN_STATE",
    "MSG_EXPORT_DISCLAIMER_COMPACT",
    "MSG_EXPORT_EMPTY",
    "MSG_EXPORT_FROM_REAL_RUN",
    "MSG_EXPORT_HONEST_COPY",
    "MSG_EXPORT_IS_PREVIEW",
    "MSG_EXPORT_NEEDS_PATH",
    "MSG_EXPORT_NO_FILE_MUTATION_OF_ORIGINALS",
    "MSG_EXPORT_OK",
    "MSG_EXPORT_PREVIEW_TITLE",
    "MSG_FAILED_EMPTY",
    "MSG_FAILED_STATUS",
    "MSG_LOCAL_PILOT_NOT_READY",
    "MSG_LOCAL_PILOT_SANDBOX_ONLY",
    "PRODUCT_STATUS_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY",
    "PRODUCT_STATUS_LOCAL_PILOT_PENDING_WITH_BLOCKERS",
    "MSG_NO_FINAL_FILES_WRITTEN",
    "MSG_NO_RUN_PAYLOAD",
    "MSG_NO_SANDBOX_RUN",
    "MSG_ORIGINALS_UNCHANGED",
    "MSG_PLANNED_DESTINATION_HINT",
    "MSG_PREVIEW_NOT_PRODUCTIVE_RUN",
    "MSG_VORSCHAU_NOT_PRODUCTIVE_RUN",
    "MSG_PRODUCTIVE_PROCESSING_BLOCKED",
    "MSG_RECOGNIZED_EMPTY",
    "MSG_SAAS_NOT_READY",
    "MSG_TARGET_PATHS_PREVIEW_ONLY",
    "MSG_TARGET_PATHS_VORSCHAU_ONLY",
    "MSG_UNCLEAR_EMPTY",
    "MSG_WARNINGS_EMPTY",
    "REPORT_TITLE",
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
    "build_export_preview_report",
    "build_run_export_payload",
    "build_run_report_view_model",
    "build_user_summary",
    "export_processing_run_state",
    "render_export_preview_text",
    "render_run_export_csv",
    "render_run_export_json",
    "report_contains_forbidden_claims",
    "write_run_report_export",
)
