"""Track-B UI-v2 run result display shell — pure view models only.

Maps ProcessingRunState into honest display summaries without inventing results,
without filesystem IO, and without processing-core imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from invoice_tool.ui_v2.processing_state import (
    MSG_DRY_RUN_UNAVAILABLE,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
    ProcessingStatus,
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

    @property
    def result_count(self) -> int:
        return len(self.results)

    @property
    def has_run_payload(self) -> bool:
        return bool(self.results) or self.review.has_items or self.errors.has_items


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
    review = ReviewSummaryDisplayVM(
        count=len(review_items),
        items=review_items,
        details_hint=MSG_REVIEW_DETAILS_HINT if review_items else None,
    )
    errors = ErrorSummaryDisplayVM(count=len(error_messages), messages=error_messages)
    empty_results = not results
    show_empty = empty_results and not review.has_items and not errors.has_items
    status = state.status
    return RunResultDisplayShellVM(
        status=status,
        status_label=STATUS_LABELS.get(status, status),
        message=state.message or "",
        run_id=state.run_id,
        results=results,
        review=review,
        errors=errors,
        blocked_hints=build_blocked_execution_hints(state),
        empty_results=empty_results,
        show_empty_state=show_empty,
        empty_detail=MSG_NO_RUN_RESULTS if show_empty else None,
    )
