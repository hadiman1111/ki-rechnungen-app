"""Track-B real Core Dry-Run → UI-v2 result mapping (Prompt 4/34).

Maps ``CoreDryRunResult`` into ``ProcessingRunState`` and honest bucket /
display summaries. Never invents document rows, never enables productive
processing, never mutates files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from invoice_tool.ui_v2.core_dry_run_contract import (
    CoreDryRunResult,
    CoreDryRunStatus,
)
from invoice_tool.ui_v2.processing_state import (
    MSG_ALL_REVIEW_OUTCOME,
    MSG_COMPLETED,
    MSG_COMPLETED_WITH_REVIEW,
    MSG_EMPTY_DRY_RUN,
    MSG_FAILED,
    MSG_MIXED_OUTCOME,
    MSG_PLANNED_DESTINATION_PREVIEW_ONLY,
    MSG_SAFETY_PROOF_COMPACT,
    ExecutionGateStatus,
    OutcomeKind,
    ProcessingErrorItem,
    ProcessingPlannedDestination,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
    ProcessingStatus,
)

BucketName = Literal[
    "recognized",
    "review",
    "errors",
    "warnings",
    "planned_destinations",
    "safety_proof",
]

MSG_SAFETY_PROOF_LINE = MSG_SAFETY_PROOF_COMPACT
MSG_RECOGNIZED_SANDBOX_PLANNED = (
    "Erkannt / sandbox-geplant — nicht produktiv verarbeitet."
)
MSG_REVIEW_NEEDS_HUMAN = "Prüffall — menschliche Entscheidung erforderlich."
MSG_ERROR_DRY_RUN = "Fehler — Dry-Run konnte das Dokument nicht klassifizieren/vorbereiten."
MSG_WARNING_BUCKET = "Hinweise aus dem Dry-Run (keine Dateischreibung)."
MSG_DETAILED_MAPPING_PENDING = (
    "Detailzeilen je Dokument fehlen — nur Aggregatzahlen verfügbar."
)
MSG_NO_FAKE_SUCCESS = "Kein fingierter Erfolg ohne echte Dry-Run-Dokumente."
MSG_EXPORT_REMAINS_PREVIEW = "Export bleibt Vorschau — kein DATEV-/Cloud-Produktivexport."

# Labels that must never appear as enabled productive actions in Track B.
FORBIDDEN_PRODUCTIVE_ACTION_LABELS = (
    "übernehmen",
    "buchen",
    "verschieben",
    "umbenennen",
    "final ausführen",
)


@dataclass(frozen=True)
class ResultBucketSummary:
    """Honest bucket counts + outcome flags for workspace / review display."""

    recognized_count: int = 0
    review_count: int = 0
    error_count: int = 0
    planned_destination_count: int = 0
    warning_count: int = 0
    outcome_kind: OutcomeKind = "idle"
    status: ProcessingStatus = "idle"
    status_label: str = "Leerlauf"
    safety_proof_line: str = MSG_SAFETY_PROOF_LINE
    planned_preview_only: bool = True
    empty: bool = False
    all_review: bool = False
    mixed: bool = False
    failed: bool = False
    blocked: bool = False
    detailed_item_mapping_complete: bool = True
    bucket_labels: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)


def _status_label(status: ProcessingStatus, outcome: OutcomeKind) -> str:
    if outcome == "all_review":
        return "Mit Prüffällen"
    if outcome == "empty":
        return "Leer"
    if outcome == "mixed":
        return "Gemischt"
    if outcome == "failed":
        return "Fehlgeschlagen"
    if outcome == "blocked":
        return "Blockiert"
    if status == "completed":
        return "Abgeschlossen"
    if status == "failed":
        return "Fehlgeschlagen"
    if status == "blocked":
        return "Blockiert"
    if status == "not_configured":
        return "Nicht konfiguriert"
    if status == "running":
        return "Läuft"
    if status == "ready":
        return "Bereit"
    return "Leerlauf"


def derive_outcome_kind(
    *,
    status: ProcessingStatus,
    recognized_count: int,
    review_count: int,
    error_count: int,
) -> OutcomeKind:
    """Derive an honest outcome kind — never invents success from empty data."""

    if status == "idle":
        return "idle"
    if status == "ready":
        return "ready"
    if status == "running":
        return "running"
    if status == "not_configured":
        return "not_configured"
    if status == "blocked":
        return "blocked"
    if status == "failed":
        return "failed"

    # completed (and similar success-ish UI status)
    if recognized_count == 0 and review_count == 0 and error_count == 0:
        return "empty"
    if review_count > 0 and recognized_count == 0 and error_count == 0:
        return "all_review"
    if error_count > 0 and recognized_count == 0 and review_count == 0:
        return "errors_only"
    if recognized_count > 0 and review_count == 0 and error_count == 0:
        return "recognized_only"
    return "mixed"


def map_safety_proof_summary(dry: CoreDryRunResult) -> str | None:
    """Compact safety line when proof is present; never invents mutation claims."""

    proof = dry.safety_proof
    if proof is None:
        return MSG_SAFETY_PROOF_LINE
    if proof.no_original_mutation and proof.productive_mode_disabled:
        return MSG_SAFETY_PROOF_LINE
    # Partial / failed proof — still show the compact policy line honestly.
    return MSG_SAFETY_PROOF_LINE


def _map_processing_status(dry: CoreDryRunResult) -> ProcessingStatus:
    if dry.status == CoreDryRunStatus.BLOCKED:
        return "blocked"
    if dry.status == CoreDryRunStatus.FAILED:
        return "failed"
    if dry.status in {
        CoreDryRunStatus.COMPLETED,
        CoreDryRunStatus.COMPLETED_WITH_REVIEW,
    }:
        return "completed"
    # READY / unexpected — fail closed without inventing success rows.
    return "failed"


def _message_for_outcome(
    dry: CoreDryRunResult,
    *,
    outcome: OutcomeKind,
    status: ProcessingStatus,
) -> str:
    base = (dry.message or "").strip()
    if outcome == "empty":
        text = base or MSG_EMPTY_DRY_RUN
        if MSG_EMPTY_DRY_RUN not in text:
            text = f"{text} {MSG_EMPTY_DRY_RUN}".strip()
        return text
    if outcome == "all_review":
        return base or MSG_ALL_REVIEW_OUTCOME or MSG_COMPLETED_WITH_REVIEW
    if outcome == "mixed":
        return base or MSG_MIXED_OUTCOME or MSG_COMPLETED_WITH_REVIEW
    if status == "failed":
        return base or MSG_FAILED
    if dry.status == CoreDryRunStatus.COMPLETED_WITH_REVIEW:
        return base or MSG_COMPLETED_WITH_REVIEW
    if status == "completed":
        return base or MSG_COMPLETED
    return base or MSG_FAILED


def map_core_dry_run_result_to_processing_run_state(
    dry: CoreDryRunResult,
    *,
    execution_gate: ExecutionGateStatus | None = "ready_for_sandbox_execution",
    dry_run_gate: ExecutionGateStatus | None = "dry_run_available",
    core_dry_run_status: ExecutionGateStatus | None = "dry_run_available",
) -> ProcessingRunState:
    """Map a real ``CoreDryRunResult`` into ``ProcessingRunState`` — no invented rows."""

    results = tuple(
        ProcessingResultSummary(
            document_name=item.document_name,
            document_type=item.document_type,
            classification_status=item.classification_status,
            status_label=item.status_label,
            confidence_label=item.confidence_label,
            target_hint=item.target_hint,
        )
        for item in dry.recognized
    )
    review_items = tuple(
        ProcessingReviewItem(
            document_name=item.document_name,
            reason=item.reason,
            status_label=item.status_label,
            document_id=item.document_id,
            evidence_summary=item.evidence_summary,
            next_action_hint=item.next_action_hint,
        )
        for item in dry.review
    )
    error_items = tuple(
        ProcessingErrorItem(
            document_name=item.document_name,
            error_code=item.error_code,
            message=item.message,
            status_label=item.status_label,
        )
        for item in dry.errors
    )
    error_messages = tuple(
        f"{item.error_code}: {item.message}" if item.error_code else item.message
        for item in dry.errors
    )
    if dry.contract_error_codes:
        error_messages = error_messages + tuple(dry.contract_error_codes)
    planned = tuple(
        ProcessingPlannedDestination(
            document_name=item.document_name,
            planned_path=item.planned_path,
            destination_label=item.destination_label,
            reason=item.reason,
            applied=False,
            preview_only=True,
        )
        for item in dry.planned_destinations
    )

    summary = dry.summary
    recognized_count = len(results) or int(summary.recognized_count or 0)
    review_count = len(review_items) or int(summary.review_count or 0)
    error_count = len(error_items) or int(summary.error_count or 0)
    planned_count = len(planned) or int(summary.planned_destination_count or 0)

    # Honest pending flag when summary claims items but rows are absent.
    detailed_complete = True
    if (
        (summary.recognized_count > len(results))
        or (summary.review_count > len(review_items))
        or (summary.error_count > len(error_items))
        or (summary.planned_destination_count > len(planned))
    ):
        detailed_complete = False

    status = _map_processing_status(dry)
    outcome = derive_outcome_kind(
        status=status,
        recognized_count=recognized_count,
        review_count=review_count,
        error_count=error_count,
    )
    message = _message_for_outcome(dry, outcome=outcome, status=status)
    safety = map_safety_proof_summary(dry)
    if safety and safety not in message:
        message = f"{message} {safety}".strip()

    return ProcessingRunState(
        status=status,
        message=message,
        run_id=dry.run_id,
        results=results,
        review_items=review_items,
        errors=error_messages,
        execution_gate=execution_gate,
        dry_run_gate=dry_run_gate,
        core_dry_run_status=core_dry_run_status,
        warnings=tuple(dry.warnings or ()),
        planned_destination_count=planned_count,
        safety_proof_summary=safety,
        error_items=error_items,
        planned_destinations=planned,
        outcome_kind=outcome,
        detailed_item_mapping_complete=detailed_complete,
    )


def build_result_bucket_summary(
    state: ProcessingRunState | None,
) -> ResultBucketSummary:
    """Build bucket summary from real ``ProcessingRunState`` only."""

    run = state or ProcessingRunState()
    recognized = run.recognized_count
    review = run.review_count
    errors = run.error_count
    planned = int(run.planned_destination_count or len(run.planned_destinations or ()))
    warnings = len(tuple(run.warnings or ()))
    outcome = run.outcome_kind or derive_outcome_kind(
        status=run.status,
        recognized_count=recognized,
        review_count=review,
        error_count=errors,
    )
    notes: list[str] = [
        MSG_RECOGNIZED_SANDBOX_PLANNED,
        MSG_REVIEW_NEEDS_HUMAN,
        MSG_ERROR_DRY_RUN,
        MSG_PLANNED_DESTINATION_PREVIEW_ONLY,
        MSG_SAFETY_PROOF_LINE,
        MSG_EXPORT_REMAINS_PREVIEW,
        MSG_NO_FAKE_SUCCESS,
    ]
    if not run.detailed_item_mapping_complete:
        notes.insert(0, MSG_DETAILED_MAPPING_PENDING)
    if warnings:
        notes.append(MSG_WARNING_BUCKET)
    if outcome == "empty" and run.status == "completed":
        notes.append(MSG_EMPTY_DRY_RUN)
    if outcome == "all_review":
        notes.append(MSG_ALL_REVIEW_OUTCOME)

    return ResultBucketSummary(
        recognized_count=recognized,
        review_count=review,
        error_count=errors,
        planned_destination_count=planned,
        warning_count=warnings,
        outcome_kind=outcome,
        status=run.status,
        status_label=_status_label(run.status, outcome),
        safety_proof_line=(run.safety_proof_summary or MSG_SAFETY_PROOF_LINE),
        planned_preview_only=True,
        empty=outcome == "empty",
        all_review=outcome == "all_review",
        mixed=outcome == "mixed",
        failed=outcome == "failed" or run.status == "failed",
        blocked=outcome == "blocked" or run.status == "blocked",
        detailed_item_mapping_complete=bool(run.detailed_item_mapping_complete),
        bucket_labels=(
            "Erkannt / geplant",
            "Zur Prüfung",
            "Fehler",
            "Warnungen",
            "Sicherheitsnachweis",
        ),
        notes=tuple(dict.fromkeys(notes)),
    )


def planned_destinations_are_preview_only(state: ProcessingRunState | None) -> bool:
    """Always true for Track-B dry-run mapping — destinations are never applied."""

    run = state or ProcessingRunState()
    if not run.planned_destinations:
        return True
    return all(
        (not item.applied) and bool(item.preview_only)
        for item in run.planned_destinations
    )


def productive_actions_exposed(_state: ProcessingRunState | None = None) -> bool:
    """Track-B result mapping never exposes productive write/approve actions."""

    return False


def forbidden_productive_action_labels() -> tuple[str, ...]:
    return FORBIDDEN_PRODUCTIVE_ACTION_LABELS


__all__ = (
    "BucketName",
    "FORBIDDEN_PRODUCTIVE_ACTION_LABELS",
    "MSG_DETAILED_MAPPING_PENDING",
    "MSG_ERROR_DRY_RUN",
    "MSG_EXPORT_REMAINS_PREVIEW",
    "MSG_NO_FAKE_SUCCESS",
    "MSG_RECOGNIZED_SANDBOX_PLANNED",
    "MSG_REVIEW_NEEDS_HUMAN",
    "MSG_SAFETY_PROOF_LINE",
    "MSG_WARNING_BUCKET",
    "ResultBucketSummary",
    "build_result_bucket_summary",
    "derive_outcome_kind",
    "forbidden_productive_action_labels",
    "map_core_dry_run_result_to_processing_run_state",
    "map_safety_proof_summary",
    "planned_destinations_are_preview_only",
    "productive_actions_exposed",
)
