"""Track-B review flow state derived from real ProcessingRunState (Prompt 4/34).

Review-needed items come only from dry-run review buckets. Errors stay separate.
Recognized items are never pushed into review. Planned destinations are
preview-only. No final approve / write / rename / move actions are enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from invoice_tool.ui_v2.processing_state import (
    MSG_PLANNED_DESTINATION_PREVIEW_ONLY,
    MSG_SAFETY_PROOF_COMPACT,
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.result_mapping import (
    FORBIDDEN_PRODUCTIVE_ACTION_LABELS,
    MSG_EXPORT_REMAINS_PREVIEW,
    MSG_SAFETY_PROOF_LINE,
    ResultBucketSummary,
    build_result_bucket_summary,
    productive_actions_exposed,
)
from invoice_tool.ui_v2.review_workflow import (
    MSG_BUCKETS_SEPARATED,
    MSG_ERRORS_SEPARATED,
    MSG_RESULTS_SEPARATED,
    MSG_REVIEW_FROM_REAL_RUN,
    MSG_REVIEW_NO_FILE_MUTATION,
    ReviewActionVM,
    ReviewItemViewModel,
    ReviewQueueViewModel,
    build_review_actions,
    build_review_item_view_model,
    build_review_queue_view_model,
)

MSG_REVIEW_FROM_DRY_RUN = "Prüffälle stammen aus dem echten Sandbox-Dry-Run."
MSG_ERRORS_NOT_IN_REVIEW = "Fehlerfälle erscheinen getrennt und nicht in der Prüfliste."
MSG_RECOGNIZED_NOT_IN_REVIEW = (
    "Erkannte / geplante Dokumente werden nicht als Prüffälle geführt."
)
MSG_PLANNED_INSPECT_PREVIEW = (
    "Geplante Ziele können nur als Vorschau eingesehen werden."
)
MSG_NO_FINAL_APPROVAL = (
    "Keine Übernehmen-/Buchen-/Verschieben-/Umbenennen-/Final-ausführen-Aktion verfügbar."
)


@dataclass(frozen=True)
class ReviewFlowErrorVM:
    document_name: str
    error_code: str
    message: str
    status_label: str = "fehler"


@dataclass(frozen=True)
class ReviewFlowPlannedVM:
    document_name: str
    planned_path: str
    destination_label: str | None = None
    preview_only: bool = True
    applied: bool = False


@dataclass(frozen=True)
class ReviewFlowState:
    """Shared review-area state for Track B — same run state as workspace."""

    source_run_id: str | None
    review_items: tuple[ProcessingReviewItem, ...]
    review_view_items: tuple[ReviewItemViewModel, ...]
    error_items: tuple[ReviewFlowErrorVM, ...]
    recognized_count: int
    review_count: int
    error_count: int
    planned_destinations: tuple[ReviewFlowPlannedVM, ...]
    planned_preview_only: bool
    safety_proof_line: str
    bucket_summary: ResultBucketSummary
    queue: ReviewQueueViewModel
    actions: tuple[ReviewActionVM, ...]
    actions_disabled: bool
    productive_actions_exposed: bool
    forbidden_action_labels: tuple[str, ...]
    honest_copy: tuple[str, ...]
    separation_notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def empty(self) -> bool:
        return self.review_count == 0


def _error_vms(state: ProcessingRunState) -> tuple[ReviewFlowErrorVM, ...]:
    if state.error_items:
        return tuple(
            ReviewFlowErrorVM(
                document_name=item.document_name,
                error_code=item.error_code,
                message=item.message,
                status_label=item.status_label,
            )
            for item in state.error_items
        )
    return tuple(
        ReviewFlowErrorVM(document_name="", error_code="", message=str(message))
        for message in (state.errors or ())
        if str(message).strip()
    )


def _planned_vms(state: ProcessingRunState) -> tuple[ReviewFlowPlannedVM, ...]:
    items: tuple[ProcessingPlannedDestination, ...] = tuple(
        state.planned_destinations or ()
    )
    return tuple(
        ReviewFlowPlannedVM(
            document_name=item.document_name,
            planned_path=item.planned_path,
            destination_label=item.destination_label,
            preview_only=True,
            applied=False,
        )
        for item in items
    )


def build_review_flow_state(
    processing_state: ProcessingRunState | None,
) -> ReviewFlowState:
    """Build review flow from the same ProcessingRunState as the workspace."""

    run = processing_state or ProcessingRunState()
    queue = build_review_queue_view_model(run)
    review_raw = tuple(run.review_items or ())
    review_vms = tuple(
        build_review_item_view_model(item, source_run_id=run.run_id)
        for item in review_raw
    )
    errors = _error_vms(run)
    planned = _planned_vms(run)
    buckets = build_result_bucket_summary(run)
    actions = build_review_actions(has_items=bool(review_raw))
    honest = (
        MSG_REVIEW_FROM_REAL_RUN,
        MSG_REVIEW_FROM_DRY_RUN,
        MSG_REVIEW_NO_FILE_MUTATION,
        MSG_ERRORS_NOT_IN_REVIEW,
        MSG_RECOGNIZED_NOT_IN_REVIEW,
        MSG_PLANNED_INSPECT_PREVIEW,
        MSG_PLANNED_DESTINATION_PREVIEW_ONLY,
        MSG_SAFETY_PROOF_LINE,
        MSG_EXPORT_REMAINS_PREVIEW,
        MSG_NO_FINAL_APPROVAL,
        MSG_BUCKETS_SEPARATED,
    )
    separation = [
        MSG_BUCKETS_SEPARATED,
        MSG_ERRORS_NOT_IN_REVIEW,
        MSG_RECOGNIZED_NOT_IN_REVIEW,
    ]
    if errors:
        separation.append(MSG_ERRORS_SEPARATED)
    if run.results:
        separation.append(MSG_RESULTS_SEPARATED)

    return ReviewFlowState(
        source_run_id=(run.run_id or "").strip() or None,
        review_items=review_raw,
        review_view_items=review_vms,
        error_items=errors,
        recognized_count=len(tuple(run.results or ())),
        review_count=len(review_raw),
        error_count=len(errors),
        planned_destinations=planned,
        planned_preview_only=True,
        safety_proof_line=(
            run.safety_proof_summary or MSG_SAFETY_PROOF_COMPACT or MSG_SAFETY_PROOF_LINE
        ),
        bucket_summary=buckets,
        queue=queue,
        actions=actions,
        actions_disabled=True,
        productive_actions_exposed=productive_actions_exposed(run),
        forbidden_action_labels=FORBIDDEN_PRODUCTIVE_ACTION_LABELS,
        honest_copy=honest,
        separation_notes=tuple(dict.fromkeys(separation)),
    )


__all__ = (
    "MSG_ERRORS_NOT_IN_REVIEW",
    "MSG_NO_FINAL_APPROVAL",
    "MSG_PLANNED_INSPECT_PREVIEW",
    "MSG_RECOGNIZED_NOT_IN_REVIEW",
    "MSG_REVIEW_FROM_DRY_RUN",
    "ReviewFlowErrorVM",
    "ReviewFlowPlannedVM",
    "ReviewFlowState",
    "build_review_flow_state",
)
