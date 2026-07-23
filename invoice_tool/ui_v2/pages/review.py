"""Zur Prüfung page — Track-B UI-v2 review workflow completion.

Honest empty state by default. Items appear only from ProcessingRunState
after a real run injects them. No fake documents, no PDF processing,
no folder scan, no file mutation, no processing-core imports.
Review actions stay disabled / readiness-only (no persistence).
"""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from invoice_tool.ui_v2.components import (
    collapsible_details,
    compact_entry_row,
    empty_state,
    page_header,
    page_scaffold,
    secondary_button,
    section_block,
    stacked_list,
)
from invoice_tool.ui_v2.processing_state import ProcessingReviewItem, ProcessingRunState
from invoice_tool.ui_v2.review_components import (
    review_error_section_lines,
    review_planned_preview_lines,
    review_safety_line,
)
from invoice_tool.ui_v2.review_state import (
    MSG_NO_FINAL_APPROVAL,
    ReviewFlowState,
    build_review_flow_state,
)
from invoice_tool.ui_v2.review_workflow import (
    DEFAULT_EVIDENCE_SUMMARY,
    DEFAULT_NEXT_ACTION_HINT,
    EMPTY_REVIEW_DETAIL,
    EMPTY_REVIEW_TITLE,
    MSG_BUCKETS_SEPARATED,
    MSG_REVIEW_FROM_REAL_RUN,
    MSG_REVIEW_NO_FILE_MUTATION,
    MSG_UNCLEAR_CASES_STAY_REVIEW,
    REVIEW_QUEUE_SUBTITLE,
    ReviewItemViewModel,
    ReviewQueueViewModel,
    build_review_item_view_model,
    build_review_queue_view_model,
)
from invoice_tool.ui_v2.state import UiV2State

# Re-exports used by existing tests / callers.
__all__ = (
    "DEFAULT_EVIDENCE_SUMMARY",
    "DEFAULT_NEXT_ACTION_HINT",
    "EMPTY_REVIEW_DETAIL",
    "EMPTY_REVIEW_TITLE",
    "MSG_REVIEW_FROM_REAL_RUN",
    "MSG_REVIEW_NO_FILE_MUTATION",
    "REVIEW_QUEUE_SUBTITLE",
    "ReviewDetailItemVM",
    "ReviewPageVM",
    "build_review_page",
    "build_review_page_vm",
    "review_detail_from_item",
)


@dataclass(frozen=True)
class ReviewDetailItemVM:
    """Compatibility detail VM — mirrors ReviewItemViewModel fields used by tests."""

    document_label: str
    document_id: str
    reason: str
    suggested_status: str
    evidence_summary: str
    next_action_hint: str
    source_run_id: str | None = None
    severity: str | None = None


@dataclass(frozen=True)
class ReviewPageVM:
    """View-model for the Track-B review page — testable without a GUI window."""

    title: str
    subtitle: str
    empty: bool
    empty_title: str | None
    empty_detail: str | None
    items: tuple[ProcessingReviewItem, ...]
    detail_items: tuple[ReviewDetailItemVM, ...]
    honest_copy: tuple[str, ...]
    mutates_files: bool
    # Errors/results stay on the workspace shell — never mixed into the review queue.
    error_count: int = 0
    result_count: int = 0
    review_count: int = 0
    separation_notes: tuple[str, ...] = ()
    actions_disabled: bool = True
    action_labels: tuple[str, ...] = ()
    source_run_id: str | None = None
    planned_preview_lines: tuple[str, ...] = ()
    error_section_lines: tuple[str, ...] = ()
    safety_line: str | None = None
    productive_actions_exposed: bool = False


def _detail_from_item_vm(item: ReviewItemViewModel) -> ReviewDetailItemVM:
    return ReviewDetailItemVM(
        document_label=item.document_label,
        document_id=item.document_id,
        reason=item.reason,
        suggested_status=item.suggested_status,
        evidence_summary=item.evidence_summary,
        next_action_hint=item.next_action_hint,
        source_run_id=item.source_run_id,
        severity=item.severity,
    )


def review_detail_from_item(item: ProcessingReviewItem) -> ReviewDetailItemVM:
    """Map a provided review item into the detail shell — never invent private rows."""

    return _detail_from_item_vm(build_review_item_view_model(item))


def build_review_page_vm(state: UiV2State) -> ReviewPageVM:
    """Derive review queue from ProcessingRunState only — never invent items."""

    run_state: ProcessingRunState = state.processing_run_state or ProcessingRunState()
    flow: ReviewFlowState = build_review_flow_state(run_state)
    queue: ReviewQueueViewModel = flow.queue
    raw_items = tuple(flow.review_items)
    detail_items = tuple(_detail_from_item_vm(item) for item in flow.review_view_items)
    action_labels = tuple(action.label for action in flow.actions)
    return ReviewPageVM(
        title=queue.title,
        subtitle=queue.subtitle,
        empty=flow.empty,
        empty_title=queue.empty_title,
        empty_detail=queue.empty_detail,
        items=raw_items,
        detail_items=detail_items,
        honest_copy=flow.honest_copy,
        mutates_files=False,
        error_count=flow.error_count,
        result_count=flow.recognized_count,
        review_count=flow.review_count,
        separation_notes=flow.separation_notes,
        actions_disabled=True,
        action_labels=action_labels,
        source_run_id=flow.source_run_id,
        planned_preview_lines=review_planned_preview_lines(flow),
        error_section_lines=review_error_section_lines(flow),
        safety_line=review_safety_line(flow),
        productive_actions_exposed=False,
    )


def _action_row(queue: ReviewQueueViewModel) -> ft.Control:
    """Render disabled readiness-only review actions — no handlers that persist."""

    buttons = [
        secondary_button(
            f"{action.label} ({action.readiness_label})",
            on_click=lambda _e: None,
            disabled=True,
        )
        for action in queue.actions
    ]
    return ft.Row(buttons, spacing=8, wrap=True)


def build_review_page(state: UiV2State) -> ft.Control:
    vm = build_review_page_vm(state)
    queue = build_review_queue_view_model(state.processing_run_state)
    items: list[ft.Control] = [
        page_header(vm.title, subtitle="Unklare Fälle aus dem Lauf prüfen."),
    ]

    if vm.empty:
        items.append(
            empty_state(
                vm.empty_title or EMPTY_REVIEW_TITLE,
                detail=None,
                icon=ft.Icons.FACT_CHECK_OUTLINED,
                compact=True,
            )
        )
        items.append(
            collapsible_details(
                MSG_REVIEW_FROM_REAL_RUN,
                MSG_REVIEW_NO_FILE_MUTATION,
                MSG_UNCLEAR_CASES_STAY_REVIEW,
                MSG_BUCKETS_SEPARATED,
                *vm.separation_notes,
                title="Details anzeigen",
            )
        )
        items.append(
            section_block(
                "Prüfaktionen",
                _action_row(queue),
                subtitle="Noch nicht verbunden",
            )
        )
        return page_scaffold(*items)

    review_rows: list[ft.Control] = []
    for detail in vm.detail_items:
        fields: list[tuple[str, str]] = [
            ("Dokument-ID", detail.document_id),
            ("Grund", detail.reason),
            ("Status", detail.suggested_status),
            ("Nächster Schritt", detail.next_action_hint),
        ]
        if detail.source_run_id:
            fields.append(("Lauf-ID", detail.source_run_id))
        review_rows.append(compact_entry_row(detail.document_label, *fields))

    items.append(
        section_block(
            f"{vm.review_count} Dokument(e) zur Prüfung",
            stacked_list(*review_rows),
        )
    )
    detail_bits = [
        MSG_REVIEW_NO_FILE_MUTATION,
        MSG_NO_FINAL_APPROVAL,
        *vm.separation_notes,
        *(vm.error_section_lines or ()),
        *(vm.planned_preview_lines or ()),
    ]
    if vm.safety_line:
        detail_bits.append(vm.safety_line)
    items.append(
        collapsible_details(
            *detail_bits,
            title="Details anzeigen",
        )
    )
    items.append(
        section_block(
            "Prüfaktionen",
            _action_row(queue),
            subtitle="Noch nicht verbunden",
        )
    )
    return page_scaffold(*items)
