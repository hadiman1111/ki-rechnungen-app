"""Zur Prüfung page — Track-B UI-v2 review detail shell.

Honest empty state by default. Items appear only from ProcessingRunState
after a real run injects them. No fake documents, no PDF processing,
no folder scan, no file mutation, no processing-core imports.
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
    section_block,
    stacked_list,
)
from invoice_tool.ui_v2.processing_state import ProcessingReviewItem, ProcessingRunState
from invoice_tool.ui_v2.state import UiV2State

EMPTY_REVIEW_TITLE = "Noch keine Prüffälle vorhanden."
EMPTY_REVIEW_DETAIL = (
    "Unklare Dokumente erscheinen hier erst nach einem echten Verarbeitungslauf."
)
REVIEW_QUEUE_SUBTITLE = "Dokumente ohne eindeutige Zuordnung oder mit Konflikten."
MSG_REVIEW_FROM_REAL_RUN = "Prüffälle entstehen erst aus einem echten Verarbeitungslauf."
MSG_REVIEW_NO_FILE_MUTATION = "Diese Ansicht verändert keine Dateien."
DEFAULT_NEXT_ACTION_HINT = "Manuell prüfen und Zuordnung im Profil nachziehen."
DEFAULT_EVIDENCE_SUMMARY = "Kein Nachweiszusammenfassung bereitgestellt."


@dataclass(frozen=True)
class ReviewDetailItemVM:
    """Generic review detail fields — only from provided ProcessingReviewItem."""

    document_label: str
    document_id: str
    reason: str
    suggested_status: str
    evidence_summary: str
    next_action_hint: str


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
    # Errors stay on the workspace shell — never mixed into the review queue.
    error_count: int = 0
    result_count: int = 0


def review_detail_from_item(item: ProcessingReviewItem) -> ReviewDetailItemVM:
    """Map a provided review item into the detail shell — never invent private rows."""

    document_label = (item.document_name or "").strip() or "Dokument"
    document_id = (item.document_id or "").strip() or document_label
    evidence = (item.evidence_summary or "").strip() or DEFAULT_EVIDENCE_SUMMARY
    next_action = (item.next_action_hint or "").strip() or DEFAULT_NEXT_ACTION_HINT
    return ReviewDetailItemVM(
        document_label=document_label,
        document_id=document_id,
        reason=(item.reason or "").strip() or "Grund nicht angegeben",
        suggested_status=(item.status_label or "").strip() or "unklar",
        evidence_summary=evidence,
        next_action_hint=next_action,
    )


def build_review_page_vm(state: UiV2State) -> ReviewPageVM:
    """Derive review queue from ProcessingRunState only — never invent items."""

    run_state: ProcessingRunState = state.processing_run_state or ProcessingRunState()
    items = tuple(run_state.review_items or ())
    detail_items = tuple(review_detail_from_item(item) for item in items)
    error_count = len(tuple(run_state.errors or ()))
    result_count = len(tuple(run_state.results or ()))
    honest_copy = (MSG_REVIEW_FROM_REAL_RUN, MSG_REVIEW_NO_FILE_MUTATION)
    if not items:
        return ReviewPageVM(
            title="Zur Prüfung",
            subtitle=REVIEW_QUEUE_SUBTITLE,
            empty=True,
            empty_title=EMPTY_REVIEW_TITLE,
            empty_detail=EMPTY_REVIEW_DETAIL,
            items=(),
            detail_items=(),
            honest_copy=honest_copy,
            mutates_files=False,
            error_count=error_count,
            result_count=result_count,
        )
    return ReviewPageVM(
        title="Zur Prüfung",
        subtitle=REVIEW_QUEUE_SUBTITLE,
        empty=False,
        empty_title=None,
        empty_detail=None,
        items=items,
        detail_items=detail_items,
        honest_copy=honest_copy,
        mutates_files=False,
        error_count=error_count,
        result_count=result_count,
    )


def build_review_page(state: UiV2State) -> ft.Control:
    vm = build_review_page_vm(state)
    items: list[ft.Control] = [
        page_header(vm.title, subtitle=vm.subtitle),
        make_info_banner(f"{MSG_REVIEW_FROM_REAL_RUN} {MSG_REVIEW_NO_FILE_MUTATION}"),
    ]

    if vm.empty:
        items.append(
            section_block(
                "Prüfwarteschlange",
                focus_panel(
                    empty_state(
                        vm.empty_title or EMPTY_REVIEW_TITLE,
                        detail=vm.empty_detail or EMPTY_REVIEW_DETAIL,
                        icon=ft.Icons.FACT_CHECK_OUTLINED,
                    ),
                ),
            )
        )
        return page_scaffold(*items)

    review_rows = [
        compact_entry_row(
            detail.document_label,
            ("Dokument-ID", detail.document_id),
            ("Grund", detail.reason),
            ("Vorgeschlagener Status", detail.suggested_status),
            ("Nachweis", detail.evidence_summary),
            ("Nächster Schritt", detail.next_action_hint),
        )
        for detail in vm.detail_items
    ]
    items.append(
        section_block(
            f"{len(vm.detail_items)} Dokument(e) zur Prüfung",
            stacked_list(*review_rows),
            subtitle="Aus dem aktuellen Laufstatus — ohne Dateiänderung",
        )
    )
    return page_scaffold(*items)
