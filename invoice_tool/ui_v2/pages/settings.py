"""Einstellungen read-only page — Make reference port."""

from __future__ import annotations

import flet as ft

from invoice_tool import app_paths
from invoice_tool.ui_v2.components import make_info_banner, make_metadata_row, make_section_label, make_settings_panel, page_header, page_scaffold
from invoice_tool.ui_v2.state import UiV2State


def build_settings_page(state: UiV2State) -> ft.Control:
    _ = state
    runtime_mode = "Standalone" if app_paths.is_standalone_bundle() else "Entwicklung"
    data_location = "Application Support" if app_paths.is_standalone_bundle() else "Projekt + Application Support"

    return page_scaffold(
        page_header(
            "Einstellungen",
            subtitle="Allgemeine Programmeinstellungen und Programminformationen.",
        ),
        make_section_label("Programm"),
        make_settings_panel(
            make_metadata_row("Version", "0.1.0"),
            make_metadata_row("Datenspeicher", data_location),
            make_metadata_row("Laufzeitmodus", runtime_mode),
        ),
        make_info_banner("Derzeit sind keine weiteren Programmeinstellungen verfügbar."),
    )
