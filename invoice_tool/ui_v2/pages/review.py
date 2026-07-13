"""Zur Prüfung read-only page."""

from __future__ import annotations

import flet as ft

from invoice_tool.ui_v2.components import (
    compact_entry_row,
    empty_state,
    focus_panel,
    inline_warning,
    metadata_row,
    page_header,
    page_scaffold,
    section_block,
    stacked_list,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.theme import SPACE_SM
from invoice_tool.ui_v2.view_models import UiV2ReadOnlySnapshot


def _snapshot(state: UiV2State) -> UiV2ReadOnlySnapshot | None:
    snap = state.snapshot
    return snap if isinstance(snap, UiV2ReadOnlySnapshot) else None


def build_review_page(state: UiV2State) -> ft.Control:
    items: list[ft.Control] = [
        page_header(
            "Zur Prüfung",
            subtitle="Dokumente ohne eindeutige Zuordnung oder mit Konflikten.",
        ),
    ]
    snapshot = _snapshot(state)
    if snapshot is None:
        items.append(inline_warning("Prüfstatus vorübergehend nicht verfügbar."))
        return page_scaffold(*items)

    review = snapshot.review
    if review.availability == "no_run":
        items.append(
            section_block(
                "Prüfstatus",
                focus_panel(
                    empty_state(
                        "Noch kein Prüfstatus verfügbar",
                        detail="Sobald ein Verarbeitungslauf vorliegt, erscheinen hier Dokumente zur manuellen Prüfung.",
                        icon=ft.Icons.FACT_CHECK_OUTLINED,
                    ),
                ),
            )
        )
    elif review.availability in {"unknown", "malformed"}:
        items.append(inline_warning("Prüfstatus vorübergehend nicht verfügbar."))
        for warning in review.warnings:
            items.append(inline_warning(warning))
    elif review.availability == "zero":
        items.append(
            section_block(
                "Prüfstatus",
                focus_panel(
                    ft.Column(
                        [
                            empty_state(
                                "Keine Dokumente zur Prüfung",
                                detail="Im letzten bekannten Lauf wurden keine Dokumente mit unklarer Zuordnung oder Konflikten gefunden.",
                                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                            ),
                            metadata_row("Letzter Lauf", review.run_timestamp or "—"),
                        ],
                        spacing=SPACE_SM,
                    ),
                ),
            )
        )
    else:
        review_rows = []
        for item in review.items:
            fields: list[tuple[str, str]] = [
                ("Grund", item.reason),
                ("Status", item.status_label),
                ("Letzter Lauf", item.run_timestamp or "—"),
            ]
            if item.configuration_label:
                fields.append(("Konfiguration", item.configuration_label))
            review_rows.append(compact_entry_row(item.filename, *fields))
        items.append(
            section_block(
                f"{review.review_count} Dokument(e) zur Prüfung",
                stacked_list(*review_rows),
                subtitle="Aus dem letzten bekannten Lauf",
            )
        )

    for warning in review.warnings:
        if review.availability not in {"unknown", "malformed"}:
            items.append(inline_warning(warning))

    return page_scaffold(*items)
