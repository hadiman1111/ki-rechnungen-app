"""Zur Prüfung page — Track-B UI-v2 review queue shell.

Honest empty state by default. Items appear only from ProcessingRunState
after a real run injects them. No fake documents, no PDF processing,
no folder scan, no processing-core imports.
"""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from invoice_tool.ui_v2.components import (
    compact_entry_row,
    empty_state,
    focus_panel,
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


@dataclass(frozen=True)
class ReviewPageVM:
    """View-model for the Track-B review page — testable without a GUI window."""

    title: str
    subtitle: str
    empty: bool
    empty_title: str | None
    empty_detail: str | None
    items: tuple[ProcessingReviewItem, ...]


def build_review_page_vm(state: UiV2State) -> ReviewPageVM:
    """Derive review queue from ProcessingRunState only — never invent items."""

    run_state: ProcessingRunState = state.processing_run_state or ProcessingRunState()
    items = tuple(run_state.review_items or ())
    if not items:
        return ReviewPageVM(
            title="Zur Prüfung",
            subtitle=REVIEW_QUEUE_SUBTITLE,
            empty=True,
            empty_title=EMPTY_REVIEW_TITLE,
            empty_detail=EMPTY_REVIEW_DETAIL,
            items=(),
        )
    return ReviewPageVM(
        title="Zur Prüfung",
        subtitle=REVIEW_QUEUE_SUBTITLE,
        empty=False,
        empty_title=None,
        empty_detail=None,
        items=items,
    )


def build_review_page(state: UiV2State) -> ft.Control:
    vm = build_review_page_vm(state)
    items: list[ft.Control] = [
        page_header(vm.title, subtitle=vm.subtitle),
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
            item.document_name,
            ("Grund", item.reason),
            ("Status", item.status_label),
        )
        for item in vm.items
    ]
    items.append(
        section_block(
            f"{len(vm.items)} Dokument(e) zur Prüfung",
            stacked_list(*review_rows),
            subtitle="Aus dem aktuellen Laufstatus",
        )
    )
    return page_scaffold(*items)
