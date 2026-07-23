"""Track-B UI-v2 run result display shell — pure view models only.

Maps ProcessingRunState into honest display summaries without inventing results,
without filesystem IO, and without processing-core imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from invoice_tool.ui_v2.processing_state import (
    MSG_DRY_RUN_UNAVAILABLE,
    MSG_EMPTY_DRY_RUN,
    MSG_PLANNED_DESTINATION_PREVIEW_ONLY,
    MSG_SAFETY_PROOF_COMPACT,
    ProcessingErrorItem,
    ProcessingPlannedDestination,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
    ProcessingStatus,
)
from invoice_tool.ui_v2.result_mapping import (
    MSG_EXPORT_REMAINS_PREVIEW,
    MSG_NO_FAKE_SUCCESS,
    ResultBucketSummary,
    build_result_bucket_summary,
)

# Explicit blocked-execution copy for the display shell (generic product UI).
MSG_PRODUCTIVE_HOLD = "Produktive Verarbeitung ist noch nicht freigegeben."
MSG_DRY_RUN_HOLD = MSG_DRY_RUN_UNAVAILABLE
MSG_REVIEW_DETAILS_HINT = "Details unter Zur Prüfung."
MSG_NO_RUN_RESULTS = "Keine Laufergebnisse vorhanden."
MSG_RUN_SUMMARY_SECTION = "Laufstatus"
MSG_RESULTS_SECTION = "Laufergebnisse"
MSG_REVIEW_SUMMARY_SECTION = "Prüffälle"
MSG_ERROR_SUMMARY_SECTION = "Fehler"
MSG_PLANNED_SECTION = "Geplante Ziele (Vorschau)"
MSG_WARNING_SUMMARY_SECTION = "Warnungen"
MSG_SAFETY_SECTION = "Sicherheitsnachweis"
MSG_BUCKET_RECOGNIZED = "Erkannt / geplant"
MSG_BUCKET_REVIEW = "Zur Prüfung"
MSG_BUCKET_ERRORS = "Fehler"
MSG_BUCKET_WARNINGS = "Warnungen"
MSG_BUCKET_SAFETY = "Sicherheitsnachweis"

STATUS_LABELS: dict[ProcessingStatus, str] = {
    "idle": "Leerlauf",
    "not_configured": "Nicht konfiguriert",
    "ready": "Bereit",
    "running": "Läuft",
    "completed": "Abgeschlossen",
    "failed": "Fehlgeschlagen",
    "blocked": "Blockiert",
}


@dataclass(frozen=True)
class ResultRowDisplayVM:
    """Generic result row — fields only from ProcessingResultSummary."""

    document_name: str
    document_type: str
    classification_status: str
    status_label: str
    confidence_label: str | None = None
    target_hint: str | None = None


@dataclass(frozen=True)
class ReviewItemDisplayVM:
    """Generic review summary row — no private classification fields."""

    document_name: str
    reason: str
    status_label: str
    document_id: str | None = None
    evidence_summary: str | None = None
    next_action_hint: str | None = None


@dataclass(frozen=True)
class ErrorItemDisplayVM:
    document_name: str
    error_code: str
    message: str
    status_label: str = "fehler"


@dataclass(frozen=True)
class PlannedDestinationDisplayVM:
    document_name: str
    planned_path: str
    destination_label: str | None = None
    reason: str | None = None
    preview_only: bool = True
    applied: bool = False


@dataclass(frozen=True)
class ReviewSummaryDisplayVM:
    count: int
    items: tuple[ReviewItemDisplayVM, ...] = field(default_factory=tuple)
    details_hint: str | None = None

    @property
    def has_items(self) -> bool:
        return self.count > 0


@dataclass(frozen=True)
class ErrorSummaryDisplayVM:
    count: int
    messages: tuple[str, ...] = field(default_factory=tuple)
    items: tuple[ErrorItemDisplayVM, ...] = field(default_factory=tuple)

    @property
    def has_items(self) -> bool:
        return self.count > 0


@dataclass(frozen=True)
class PlannedDestinationSummaryDisplayVM:
    count: int
    items: tuple[PlannedDestinationDisplayVM, ...] = field(default_factory=tuple)
    preview_only: bool = True
    preview_hint: str = MSG_PLANNED_DESTINATION_PREVIEW_ONLY

    @property
    def has_items(self) -> bool:
        return self.count > 0


@dataclass(frozen=True)
class RunResultDisplayShellVM:
    """Honest run/result/review/error display shell for workspace."""

    status: ProcessingStatus
    status_label: str
    message: str
    run_id: str | None
    results: tuple[ResultRowDisplayVM, ...]
    review: ReviewSummaryDisplayVM
    errors: ErrorSummaryDisplayVM
    blocked_hints: tuple[str, ...]
    empty_results: bool
    show_empty_state: bool
    empty_detail: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    planned: PlannedDestinationSummaryDisplayVM = field(
        default_factory=lambda: PlannedDestinationSummaryDisplayVM(count=0)
    )
    safety_proof_line: str = MSG_SAFETY_PROOF_COMPACT
    bucket_summary: ResultBucketSummary | None = None
    bucket_lines: tuple[str, ...] = field(default_factory=tuple)
    outcome_kind: str | None = None
    fake_success: bool = False
    export_preview_only: bool = True
    productive_actions_exposed: bool = False

    @property
    def result_count(self) -> int:
        return len(self.results)

    @property
    def has_run_payload(self) -> bool:
        return (
            bool(self.results)
            or self.review.has_items
            or self.errors.has_items
            or self.planned.has_items
            or bool(self.warnings)
        )


def result_row_from_summary(item: ProcessingResultSummary) -> ResultRowDisplayVM:
    """Map a provided summary only — never invent payment/account/business fields."""

    return ResultRowDisplayVM(
        document_name=item.document_name,
        document_type=item.document_type,
        classification_status=item.classification_status,
        status_label=item.status_label,
        confidence_label=item.confidence_label,
        target_hint=item.target_hint,
    )


def review_item_from_state(item: ProcessingReviewItem) -> ReviewItemDisplayVM:
    return ReviewItemDisplayVM(
        document_name=item.document_name,
        reason=item.reason,
        status_label=item.status_label,
        document_id=item.document_id,
        evidence_summary=item.evidence_summary,
        next_action_hint=item.next_action_hint,
    )


def error_item_from_state(item: ProcessingErrorItem) -> ErrorItemDisplayVM:
    return ErrorItemDisplayVM(
        document_name=item.document_name,
        error_code=item.error_code,
        message=item.message,
        status_label=item.status_label,
    )


def planned_from_state(item: ProcessingPlannedDestination) -> PlannedDestinationDisplayVM:
    return PlannedDestinationDisplayVM(
        document_name=item.document_name,
        planned_path=item.planned_path,
        destination_label=item.destination_label,
        reason=item.reason,
        preview_only=True,
        applied=False,
    )


def build_blocked_execution_hints(state: ProcessingRunState) -> tuple[str, ...]:
    """Surface honest productive/dry-run hold copy without enabling execution."""

    hints: list[str] = []
    message = state.message or ""
    message_lower = message.lower()

    if (
        state.status == "blocked"
        or state.execution_gate == "productive_blocked"
        or MSG_PRODUCTIVE_HOLD in message
        or "produktive" in message_lower
    ):
        hints.append(MSG_PRODUCTIVE_HOLD)

    if (
        MSG_DRY_RUN_HOLD in message
        or state.dry_run_gate == "unsupported_without_core_change"
        or state.core_dry_run_status == "unsupported_without_core_change"
        or state.execution_gate == "unsupported_without_core_change"
    ) and state.core_dry_run_status != "dry_run_available" and state.dry_run_gate != "dry_run_available":
        hints.append(MSG_DRY_RUN_HOLD)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for hint in hints:
        if hint not in seen:
            seen.add(hint)
            ordered.append(hint)
    return tuple(ordered)


def _bucket_lines(summary: ResultBucketSummary) -> tuple[str, ...]:
    return (
        f"{MSG_BUCKET_RECOGNIZED}: {summary.recognized_count}",
        f"{MSG_BUCKET_REVIEW}: {summary.review_count}",
        f"{MSG_BUCKET_ERRORS}: {summary.error_count}",
        f"{MSG_BUCKET_WARNINGS}: {summary.warning_count}",
        f"Geplant (Vorschau): {summary.planned_destination_count}",
        f"{MSG_BUCKET_SAFETY}: {summary.safety_proof_line}",
        MSG_EXPORT_REMAINS_PREVIEW,
        MSG_NO_FAKE_SUCCESS,
    )


def build_run_result_display_shell(
    processing_state: ProcessingRunState | None,
) -> RunResultDisplayShellVM:
    """Build the run result display shell from real ProcessingRunState only."""

    state = processing_state or ProcessingRunState()
    results = tuple(result_row_from_summary(item) for item in (state.results or ()))
    review_items = tuple(
        review_item_from_state(item) for item in (state.review_items or ())
    )
    error_messages = tuple(str(item) for item in (state.errors or ()) if str(item).strip())
    structured_errors = tuple(
        error_item_from_state(item) for item in (state.error_items or ())
    )
    if not structured_errors and error_messages:
        structured_errors = tuple(
            ErrorItemDisplayVM(
                document_name="",
                error_code="",
                message=message,
            )
            for message in error_messages
        )
    planned_items = tuple(
        planned_from_state(item) for item in (state.planned_destinations or ())
    )
    review = ReviewSummaryDisplayVM(
        count=len(review_items),
        items=review_items,
        details_hint=MSG_REVIEW_DETAILS_HINT if review_items else None,
    )
    errors = ErrorSummaryDisplayVM(
        count=max(len(error_messages), len(structured_errors)),
        messages=error_messages,
        items=structured_errors,
    )
    planned = PlannedDestinationSummaryDisplayVM(
        count=int(state.planned_destination_count or len(planned_items)),
        items=planned_items,
        preview_only=True,
        preview_hint=MSG_PLANNED_DESTINATION_PREVIEW_ONLY,
    )
    buckets = build_result_bucket_summary(state)
    empty_results = not results
    # Honest empty: completed/failed with no document buckets — not fake success.
    show_empty = (
        empty_results
        and not review.has_items
        and not errors.has_items
        and (
            buckets.empty
            or state.status in {"idle", "ready", "not_configured", "blocked"}
            or (state.status == "completed" and buckets.empty)
        )
    )
    empty_detail = MSG_NO_RUN_RESULTS
    if buckets.empty and state.status == "completed":
        empty_detail = MSG_EMPTY_DRY_RUN
    elif state.status == "failed":
        empty_detail = state.message or MSG_NO_RUN_RESULTS
        show_empty = (
            empty_results and not review.has_items and not errors.has_items
        )
    # Keep classic status labels for shell.status_label; outcome nuance lives in buckets.
    status_label = STATUS_LABELS.get(state.status, state.status)
    return RunResultDisplayShellVM(
        status=state.status,
        status_label=status_label,
        message=state.message or "",
        run_id=state.run_id,
        results=results,
        review=review,
        errors=errors,
        blocked_hints=build_blocked_execution_hints(state),
        empty_results=empty_results,
        show_empty_state=show_empty,
        empty_detail=empty_detail if show_empty else None,
        warnings=tuple(state.warnings or ()),
        planned=planned,
        safety_proof_line=(
            state.safety_proof_summary or buckets.safety_proof_line or MSG_SAFETY_PROOF_COMPACT
        ),
        bucket_summary=buckets,
        bucket_lines=_bucket_lines(buckets),
        outcome_kind=buckets.outcome_kind,
        fake_success=False,
        export_preview_only=True,
        productive_actions_exposed=False,
    )
