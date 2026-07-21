"""Zur Prüfung page — shows review queue from the latest run when available."""

from __future__ import annotations

import json
from pathlib import Path

import flet as ft

from invoice_tool.ui_components import empty_state, page_heading, path_display, secondary_button
from invoice_tool.ui_theme import PANEL_PADDING, SPACE_MD


def build_review_view(*, last_report_json: Path | None) -> ft.Container:
    items: list[ft.Control] = []
    if last_report_json and last_report_json.exists():
        try:
            data = json.loads(last_report_json.read_text(encoding="utf-8"))
            review_files = [
                item
                for item in data.get("files", [])
                if isinstance(item, dict) and item.get("status") in {"unklar", "error", "failed"}
            ]
            for item in review_files:
                items.append(
                    ft.Container(
                        padding=SPACE_MD,
                        border=ft.Border.all(1, ft.Colors.OUTLINE),
                        border_radius=10,
                        content=ft.Column(
                            [
                                ft.Text(str(item.get("filename") or "Dokument"), weight=ft.FontWeight.W_600),
                                ft.Text(f"Grund: {item.get('notes') or item.get('status') or 'Prüfung nötig'}"),
                                path_display(str(item.get("output") or "")),
                            ],
                            spacing=4,
                        ),
                    )
                )
        except (OSError, json.JSONDecodeError):
            items = []

    if not items:
        items = [
            empty_state(
                "Keine Dokumente zur Prüfung",
                message="Nach einem Lauf erscheinen hier Dokumente ohne eindeutige Zuordnung.",
            )
        ]

    return ft.Container(
        expand=True,
        padding=PANEL_PADDING,
        content=ft.Column(
            [
                page_heading(
                    "Zur Prüfung",
                    subtitle="Dokumente ohne eindeutige Zuordnung oder mit Konflikten.",
                ),
                *items,
            ],
            spacing=SPACE_MD,
            scroll=ft.ScrollMode.AUTO,
        ),
    )
