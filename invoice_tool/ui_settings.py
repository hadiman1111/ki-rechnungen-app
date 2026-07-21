"""Minimal Einstellungen page."""

from __future__ import annotations

import flet as ft

from invoice_tool.ui_components import page_heading
from invoice_tool.ui_theme import PANEL_PADDING, SPACE_MD


def build_settings_view() -> ft.Container:
    return ft.Container(
        expand=True,
        padding=PANEL_PADDING,
        content=ft.Column(
            [
                page_heading(
                    "Einstellungen",
                    subtitle="Hier werden allgemeine Programmeinstellungen verwaltet.",
                ),
                ft.Text(
                    "Derzeit sind keine weiteren Einstellungen verfügbar.",
                    size=13,
                ),
            ],
            spacing=SPACE_MD,
        ),
    )
