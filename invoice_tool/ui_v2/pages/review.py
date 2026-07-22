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
    compact_entry_row,
    empty_state,
    focus_panel,
    make_info_banner,
    page_header,
    page_scaffold,
    secondary_button,
    section_block,
    stacked_list,
    summary_alert,
)
from invoice_tool.ui_v2.processing_state import ProcessingReviewItem, ProcessingRunState
from invoice_tool.ui_v2.review_workflow import (
    DEFAULT_EVIDENCE_SUMMARY,
    DEFAULT_NEXT_ACTION_HINT,
    EMPTY_REVIEW_DETAIL,
    EMPTY_REVIEW_TITLE,
    MSG_REVIEW_FROM_REAL_RUN,
    MSG_REVIEW_NO_FILE_MUTATION,
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
    queue: ReviewQueueViewModel = build_review_queue_view_model(run_state)
    raw_items = tuple(run_state.review_items or ())
    detail_items = tuple(_detail_from_item_vm(item) for item in queue.items)
    action_labels = tuple(action.label for action in queue.actions)
    return ReviewPageVM(
        title=queue.title,
        subtitle=queue.subtitle,
        empty=queue.empty,
        empty_title=queue.empty_title,
        empty_detail=queue.empty_detail,
        items=raw_items,
        detail_items=detail_items,
        honest_copy=queue.honest_copy,
        mutates_files=False,
        error_count=queue.error_count,
        result_count=queue.result_count,
        review_count=queue.review_count,
        separation_notes=queue.separation_notes,
        actions_disabled=all(not action.enabled for action in queue.actions),
        action_labels=action_labels,
        source_run_id=queue.source_run_id,
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
        page_header(vm.title, subtitle=vm.subtitle),
        make_info_banner(f"{MSG_REVIEW_FROM_REAL_RUN} {MSG_REVIEW_NO_FILE_MUTATION}"),
    ]

    if vm.empty:
        empty_detail = (
            f"{vm.empty_detail or EMPTY_REVIEW_DETAIL} {MSG_REVIEW_NO_FILE_MUTATION}"
        )
        items.append(
            section_block(
                "Prüfwarteschlange",
                focus_panel(
                    empty_state(
                        vm.empty_title or EMPTY_REVIEW_TITLE,
                        detail=empty_detail,
                        icon=ft.Icons.FACT_CHECK_OUTLINED,
                    ),
                ),
            )
        )
        for note in vm.separation_notes:
            items.append(summary_alert(note))
        items.append(
            section_block(
                "Prüfaktionen (noch nicht verbunden)",
                _action_row(queue),
                subtitle="Keine Speicherung, keine Dateiänderung, keine PDF-Verarbeitung",
            )
        )
        return page_scaffold(*items)

    review_rows: list[ft.Control] = []
    for detail in vm.detail_items:
        fields: list[tuple[str, str]] = [
            ("Dokument-ID", detail.document_id),
            ("Grund", detail.reason),
            ("Vorgeschlagener Status", detail.suggested_status),
            ("Nachweis", detail.evidence_summary),
            ("Nächster Schritt", detail.next_action_hint),
        ]
        if detail.source_run_id:
            fields.append(("Lauf-ID", detail.source_run_id))
        if detail.severity and detail.severity != detail.suggested_status:
            fields.append(("Schwere", detail.severity))
        review_rows.append(compact_entry_row(detail.document_label, *fields))

    items.append(
        section_block(
            f"{vm.review_count} Dokument(e) zur Prüfung",
            stacked_list(*review_rows),
            subtitle="Aus dem aktuellen Laufstatus — ohne Dateiänderung",
        )
    )
    for note in vm.separation_notes:
        items.append(summary_alert(note))
    items.append(make_info_banner(MSG_REVIEW_NO_FILE_MUTATION))
    items.append(
        section_block(
            "Prüfaktionen (noch nicht verbunden)",
            _action_row(queue),
            subtitle="Keine Speicherung, keine Dateiänderung, keine PDF-Verarbeitung",
        )
    )
    return page_scaffold(*items)
