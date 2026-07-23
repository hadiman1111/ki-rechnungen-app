"""Track-B UI-v2 review workflow view models — pure helpers only.

Maps ProcessingRunState.review_items into generic display VMs.
No filesystem IO, no PDF processing, no persistence, no processing-core imports.
Never invents review rows, private classification, or filename-as-truth fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from invoice_tool.ui_v2.clarity_copy import (
    MSG_CLARITY_BUCKETS_SEPARATED,
    MSG_CLARITY_FILENAME_NOT_TRUTH,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
    MSG_CLARITY_SANDBOX_COPIED_RUN,
    MSG_CLARITY_UNCLEAR_STAYS_REVIEW,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_preview_state import (
    MSG_BADGE_NO_FINAL_WRITE,
    MSG_BADGE_PREVIEW,
    MSG_BADGE_PRODUCTIVE_BLOCKED,
    MSG_CATEGORY_REVIEW,
    planned_for_document,
    review_item_key,
)

EMPTY_REVIEW_TITLE = "Keine Prüffälle vorhanden."
MSG_REVIEW_FROM_REAL_RUN = "Prüffälle entstehen erst aus einem echten Verarbeitungslauf."
MSG_REVIEW_NO_FILE_MUTATION = "Diese Ansicht verändert keine Dateien."
EMPTY_REVIEW_DETAIL = MSG_REVIEW_FROM_REAL_RUN
MSG_ERRORS_SEPARATED = "Fehler werden getrennt von Prüffällen geführt."
MSG_RESULTS_SEPARATED = "Erfolgreiche Ergebnisse werden getrennt von Prüffällen geführt."
MSG_BUCKETS_SEPARATED = MSG_CLARITY_BUCKETS_SEPARATED
MSG_UNCLEAR_CASES_STAY_REVIEW = MSG_CLARITY_UNCLEAR_STAYS_REVIEW
MSG_ACTION_NOT_CONNECTED = "noch nicht verbunden"
MSG_ACTION_INFORMATIONAL = "nur Hinweis — keine Dateiöffnung"
DEFAULT_NEXT_ACTION_HINT = "Manuell prüfen und Zuordnung im Profil nachziehen."
DEFAULT_EVIDENCE_SUMMARY = "Kein Nachweiszusammenfassung bereitgestellt."
DEFAULT_DOCUMENT_LABEL = "Dokument"
DEFAULT_REASON = "Grund nicht angegeben"
DEFAULT_STATUS = "unklar"
MSG_REVIEW_HONEST_COPY = (
    MSG_REVIEW_FROM_REAL_RUN,
    MSG_REVIEW_NO_FILE_MUTATION,
    MSG_UNCLEAR_CASES_STAY_REVIEW,
    MSG_BUCKETS_SEPARATED,
    MSG_CLARITY_FILENAME_NOT_TRUTH,
    MSG_CLARITY_SANDBOX_COPIED_RUN,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
)

ACTION_MARK_REVIEWED = "Als geprüft markieren"
ACTION_SAVE_LATER = "Entscheidung später speichern"
ACTION_CHECK_EVIDENCE = "Nachweis prüfen"

REVIEW_QUEUE_SUBTITLE = "Dokumente ohne eindeutige Zuordnung oder mit Konflikten."


@dataclass(frozen=True)
class ReviewActionVM:
    """Transient / readiness-only action — never persists and never mutates files."""

    label: str
    enabled: bool
    readiness_label: str
    informational_only: bool = False
    persists: bool = False
    mutates_files: bool = False
    opens_pdf: bool = False


@dataclass(frozen=True)
class ReviewItemViewModel:
    """Generic review item fields — only from provided ProcessingReviewItem + run id."""

    document_label: str
    document_id: str
    reason: str
    suggested_status: str
    evidence_summary: str
    next_action_hint: str
    source_run_id: str | None = None
    severity: str | None = None
    # Prompt 15/34 — list/detail usability fields (preview-only).
    item_key: str = ""
    source_filename: str = ""
    category: str = MSG_CATEGORY_REVIEW
    planned_action: str | None = None
    planned_destination: str | None = None
    preview_only_badge: str = MSG_BADGE_PREVIEW
    no_final_write_badge: str = MSG_BADGE_NO_FINAL_WRITE
    productive_blocked_badge: str = MSG_BADGE_PRODUCTIVE_BLOCKED


@dataclass(frozen=True)
class ReviewQueueViewModel:
    """Queue shell for the Track-B review page — testable without a GUI window."""

    title: str
    subtitle: str
    empty: bool
    empty_title: str | None
    empty_detail: str | None
    review_count: int
    items: tuple[ReviewItemViewModel, ...]
    honest_copy: tuple[str, ...]
    mutates_files: bool
    # Counts from the same ProcessingRunState — never mixed into the review list.
    error_count: int = 0
    result_count: int = 0
    separation_notes: tuple[str, ...] = field(default_factory=tuple)
    actions: tuple[ReviewActionVM, ...] = field(default_factory=tuple)
    source_run_id: str | None = None


def build_review_actions(*, has_items: bool) -> tuple[ReviewActionVM, ...]:
    """Disabled / readiness-only action shells — no persistence, no PDF open."""

    _ = has_items  # Actions stay disabled regardless; presence only affects page layout.
    return (
        ReviewActionVM(
            label=ACTION_MARK_REVIEWED,
            enabled=False,
            readiness_label=MSG_ACTION_NOT_CONNECTED,
            informational_only=False,
            persists=False,
            mutates_files=False,
            opens_pdf=False,
        ),
        ReviewActionVM(
            label=ACTION_SAVE_LATER,
            enabled=False,
            readiness_label=MSG_ACTION_NOT_CONNECTED,
            informational_only=False,
            persists=False,
            mutates_files=False,
            opens_pdf=False,
        ),
        ReviewActionVM(
            label=ACTION_CHECK_EVIDENCE,
            enabled=False,
            readiness_label=MSG_ACTION_INFORMATIONAL,
            informational_only=True,
            persists=False,
            mutates_files=False,
            opens_pdf=False,
        ),
    )


def build_review_item_view_model(
    item: ProcessingReviewItem,
    *,
    source_run_id: str | None = None,
    planned: ProcessingPlannedDestination | None = None,
) -> ReviewItemViewModel:
    """Map a provided review item — never invent private or filename-derived fields."""

    document_label = (item.document_name or "").strip() or DEFAULT_DOCUMENT_LABEL
    document_id = (item.document_id or "").strip() or document_label
    evidence = (item.evidence_summary or "").strip() or DEFAULT_EVIDENCE_SUMMARY
    next_action = (item.next_action_hint or "").strip() or DEFAULT_NEXT_ACTION_HINT
    status = (item.status_label or "").strip() or DEFAULT_STATUS
    key = review_item_key(item)
    planned_path = None
    planned_action = None
    if planned is not None:
        planned_path = (planned.planned_path or "").strip() or None
        planned_action = (planned.destination_label or "").strip() or None
        if not planned_action and planned_path:
            planned_action = "Geplantes Ziel (Vorschau)"
    return ReviewItemViewModel(
        document_label=document_label,
        document_id=document_id,
        reason=(item.reason or "").strip() or DEFAULT_REASON,
        suggested_status=status,
        evidence_summary=evidence,
        next_action_hint=next_action,
        source_run_id=(source_run_id or "").strip() or None,
        severity=status,
        item_key=key,
        source_filename=document_label,
        category=MSG_CATEGORY_REVIEW,
        planned_action=planned_action,
        planned_destination=planned_path,
        preview_only_badge=MSG_BADGE_PREVIEW,
        no_final_write_badge=MSG_BADGE_NO_FINAL_WRITE,
        productive_blocked_badge=MSG_BADGE_PRODUCTIVE_BLOCKED,
    )


def build_review_queue_view_model(
    processing_state: ProcessingRunState | None,
) -> ReviewQueueViewModel:
    """Build the review queue from ProcessingRunState.review_items only."""

    run_state = processing_state or ProcessingRunState()
    raw_items = tuple(run_state.review_items or ())
    source_run_id = (run_state.run_id or "").strip() or None
    planned_rows = tuple(run_state.planned_destinations or ())
    items = tuple(
        build_review_item_view_model(
            item,
            source_run_id=source_run_id,
            planned=planned_for_document(planned_rows, item.document_name),
        )
        for item in raw_items
    )
    error_count = len(tuple(run_state.errors or ()))
    result_count = len(tuple(run_state.results or ()))
    honest_copy = MSG_REVIEW_HONEST_COPY
    # Always keep buckets separated in copy — never mix results/review/errors.
    separation_notes: list[str] = [MSG_BUCKETS_SEPARATED, MSG_UNCLEAR_CASES_STAY_REVIEW]
    if error_count:
        separation_notes.append(MSG_ERRORS_SEPARATED)
    if result_count:
        separation_notes.append(MSG_RESULTS_SEPARATED)
    actions = build_review_actions(has_items=bool(items))

    if not items:
        return ReviewQueueViewModel(
            title="Zur Prüfung",
            subtitle=REVIEW_QUEUE_SUBTITLE,
            empty=True,
            empty_title=EMPTY_REVIEW_TITLE,
            empty_detail=EMPTY_REVIEW_DETAIL,
            review_count=0,
            items=(),
            honest_copy=honest_copy,
            mutates_files=False,
            error_count=error_count,
            result_count=result_count,
            separation_notes=tuple(separation_notes),
            actions=actions,
            source_run_id=source_run_id,
        )

    return ReviewQueueViewModel(
        title="Zur Prüfung",
        subtitle=REVIEW_QUEUE_SUBTITLE,
        empty=False,
        empty_title=None,
        empty_detail=None,
        review_count=len(items),
        items=items,
        honest_copy=honest_copy,
        mutates_files=False,
        error_count=error_count,
        result_count=result_count,
        separation_notes=tuple(separation_notes),
        actions=actions,
        source_run_id=source_run_id,
    )


__all__ = (
    "ACTION_CHECK_EVIDENCE",
    "ACTION_MARK_REVIEWED",
    "ACTION_SAVE_LATER",
    "DEFAULT_DOCUMENT_LABEL",
    "DEFAULT_EVIDENCE_SUMMARY",
    "DEFAULT_NEXT_ACTION_HINT",
    "DEFAULT_REASON",
    "DEFAULT_STATUS",
    "EMPTY_REVIEW_DETAIL",
    "EMPTY_REVIEW_TITLE",
    "MSG_ACTION_INFORMATIONAL",
    "MSG_ACTION_NOT_CONNECTED",
    "MSG_BUCKETS_SEPARATED",
    "MSG_ERRORS_SEPARATED",
    "MSG_RESULTS_SEPARATED",
    "MSG_REVIEW_FROM_REAL_RUN",
    "MSG_REVIEW_HONEST_COPY",
    "MSG_REVIEW_NO_FILE_MUTATION",
    "MSG_UNCLEAR_CASES_STAY_REVIEW",
    "REVIEW_QUEUE_SUBTITLE",
    "ReviewActionVM",
    "ReviewItemViewModel",
    "ReviewQueueViewModel",
    "build_review_actions",
    "build_review_item_view_model",
    "build_review_queue_view_model",
)
