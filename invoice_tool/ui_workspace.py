"""Arbeitsbereich page composition — presentation only, no runtime logic."""

from __future__ import annotations

from typing import Callable

import flet as ft

from invoice_tool.ui_theme import (
    COLOR_BORDER as LINE,
    COLOR_ERROR as ERR,
    COLOR_PRIMARY as ACCENT,
    COLOR_SUCCESS as OK,
    COLOR_SUCCESS_SOFT as OK_SOFT,
    COLOR_SURFACE as SURFACE,
    COLOR_SURFACE_ALT as SURFACE_2,
    COLOR_TEXT_MUTED as MUTED,
    COLOR_TEXT_MUTED_2 as MUTED_2,
    COLOR_TEXT_SECONDARY as INK_2,
    COLOR_WARNING as WARN,
    COLOR_WARNING_SOFT as WARN_SOFT,
    RADIUS_LG as RADIUS_CARD,
    RADIUS_PILL,
    RADIUS_WORKSPACE_CARD as FOLDER_CARD_RADIUS,
    SPACE_LG as SP_16,
    SPACE_MD as SP_12,
    SPACE_SM as SP_8,
    SPACE_XL as SP_24,
    SPACE_XXL as SP_32,
    SPACE_XXS as SP_4,
    WORKSPACE_CARD_HEIGHT as FOLDER_CARD_HEIGHT,
    WORKSPACE_CENTER_WIDTH as CENTER_COL_WIDTH,
)
from invoice_tool.ui_tokens import WARN_EDGE


def _kpi(label: str, value_ctrl: ft.Text, dot_color: str) -> ft.Container:
    return ft.Container(
        width=118,
        bgcolor=SURFACE_2,
        border=ft.Border.all(1, LINE),
        border_radius=RADIUS_CARD,
        padding=ft.Padding.symmetric(horizontal=SP_8, vertical=SP_8),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=6,
                            height=6,
                            border_radius=RADIUS_PILL,
                            bgcolor=dot_color,
                        ),
                        ft.Text(label, size=9, color=MUTED, weight=ft.FontWeight.W_600),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                value_ctrl,
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def build_folder_card(
    *,
    title: str,
    subtitle: str,
    accent: str,
    soft: str,
    path_field: ft.TextField,
    pick_label: str,
    on_pick,
    on_finder,
    extra_content: ft.Control | None = None,
) -> ft.Container:
    card_header_radius = ft.BorderRadius.only(
        top_left=FOLDER_CARD_RADIUS,
        top_right=FOLDER_CARD_RADIUS,
    )
    return ft.Container(
        expand=1,
        height=FOLDER_CARD_HEIGHT,
        bgcolor=SURFACE,
        border=ft.Border.all(1, LINE),
        border_radius=FOLDER_CARD_RADIUS,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            [
                ft.Container(
                    bgcolor=soft,
                    border_radius=card_header_radius,
                    padding=ft.Padding.symmetric(horizontal=SP_24, vertical=SP_16),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.FOLDER_OPEN, size=32, color=accent),
                            ft.Column(
                                [
                                    ft.Text(title, size=18, weight=ft.FontWeight.W_700, color=INK_2),
                                    ft.Text(subtitle, size=12, color=MUTED),
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=SP_24, vertical=SP_16),
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        pick_label,
                                        icon=ft.Icons.FOLDER_OPEN,
                                        on_click=on_pick,
                                        style=ft.ButtonStyle(
                                            bgcolor=accent,
                                            color=ft.Colors.WHITE,
                                            text_style=ft.TextStyle(
                                                size=13,
                                                weight=ft.FontWeight.W_600,
                                            ),
                                            padding=ft.Padding.symmetric(horizontal=18, vertical=12),
                                        ),
                                    ),
                                    ft.OutlinedButton(
                                        "Im Finder",
                                        icon=ft.Icons.OPEN_IN_NEW,
                                        on_click=on_finder,
                                        style=ft.ButtonStyle(
                                            color=MUTED,
                                            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                                        ),
                                    ),
                                ],
                                spacing=SP_8,
                            ),
                            ft.Divider(height=1, color=LINE),
                            ft.Text("Aktueller Pfad", size=10, color=MUTED_2, weight=ft.FontWeight.W_500),
                            path_field,
                            *([extra_content] if extra_content is not None else []),
                        ],
                        spacing=SP_8,
                    ),
                ),
            ],
            spacing=0,
        ),
    )


def build_destination_summary_panel(
    *,
    configuration_rows: list[ft.Control],
    on_open_configurations: Callable,
) -> ft.Container:
    """Shows which active configuration writes to which folder before processing."""
    if configuration_rows:
        body = ft.Column(configuration_rows, spacing=4)
    else:
        body = ft.Text(
            "Noch keine Konfigurationen – lege Zielordner in Konfigurationen fest.",
            size=12,
            color=MUTED,
        )
    return ft.Container(
        bgcolor=SURFACE_2,
        border=ft.Border.all(1, LINE),
        border_radius=RADIUS_CARD,
        padding=ft.Padding.symmetric(horizontal=SP_8, vertical=SP_8),
        content=ft.Column(
            [
                ft.Text("Zielordner je Konfiguration", size=11, weight=ft.FontWeight.W_600, color=MUTED_2),
                body,
                ft.TextButton(
                    "Konfigurationen bearbeiten",
                    icon=ft.Icons.TUNE,
                    on_click=lambda _e: on_open_configurations(),
                    style=ft.ButtonStyle(
                        color=ACCENT,
                        padding=ft.Padding.symmetric(horizontal=0, vertical=2),
                    ),
                ),
            ],
            spacing=SP_4,
        ),
    )


def build_workspace_view(
    *,
    profile_strip: ft.Control,
    eingang_card: ft.Control,
    center_col: ft.Control,
    ergebnisse_card: ft.Control,
    ergebnis_panel: ft.Control,
    manual_review_panel: ft.Control,
) -> ft.Container:
    workspace = ft.Row(
        [eingang_card, center_col, ergebnisse_card],
        spacing=SP_16,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    return ft.Container(
        expand=True,
        padding=ft.Padding.symmetric(horizontal=SP_32, vertical=SP_24),
        content=ft.Column(
            [
                ft.Text("Arbeitsbereich", size=28, weight=ft.FontWeight.W_700),
                profile_strip,
                workspace,
                ergebnis_panel,
                manual_review_panel,
            ],
            spacing=SP_12,
            scroll=ft.ScrollMode.AUTO,
        ),
    )


def build_processing_column(
    *,
    start_button: ft.Control,
    status_badge: ft.Control,
    on_open_configurations: Callable,
    on_open_latest_report: Callable,
) -> ft.Container:
    return ft.Container(
        width=CENTER_COL_WIDTH,
        padding=ft.Padding.symmetric(horizontal=4, vertical=SP_16),
        content=ft.Column(
            [
                ft.Text("Verarbeitung", size=14, weight=ft.FontWeight.W_700, color=INK_2),
                start_button,
                status_badge,
                ft.Divider(height=1, color=LINE),
                ft.TextButton(
                    "Konfigurationen",
                    icon=ft.Icons.TUNE,
                    on_click=lambda _e: on_open_configurations(),
                    style=ft.ButtonStyle(
                        color=MUTED,
                        padding=ft.Padding.symmetric(horizontal=0, vertical=4),
                    ),
                ),
                ft.TextButton(
                    "Letzten Bericht öffnen",
                    icon=ft.Icons.DESCRIPTION,
                    on_click=on_open_latest_report,
                    style=ft.ButtonStyle(
                        color=MUTED_2,
                        padding=ft.Padding.symmetric(horizontal=0, vertical=2),
                    ),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=SP_12,
        ),
    )


def build_ergebnisse_card(
    *,
    run_dir_row: ft.Control,
    unmatched_summary: ft.Control,
    destination_summary: ft.Control,
    on_open_configurations: Callable,
) -> ft.Container:
    return ft.Container(
        expand=1,
        height=FOLDER_CARD_HEIGHT,
        bgcolor=SURFACE,
        border=ft.Border.all(1, LINE),
        border_radius=FOLDER_CARD_RADIUS,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            [
                ft.Container(
                    bgcolor=OK_SOFT,
                    border_radius=ft.BorderRadius.only(
                        top_left=FOLDER_CARD_RADIUS,
                        top_right=FOLDER_CARD_RADIUS,
                    ),
                    padding=ft.Padding.symmetric(horizontal=SP_24, vertical=SP_16),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.OUTPUT, size=32, color=OK),
                            ft.Column(
                                [
                                    ft.Text("Ergebnisse", size=18, weight=ft.FontWeight.W_700, color=INK_2),
                                    ft.Text(
                                        "Zielordner werden über Konfigurationen gesteuert",
                                        size=12,
                                        color=MUTED,
                                    ),
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=SP_24, vertical=SP_16),
                    content=ft.Column(
                        [
                            destination_summary,
                            run_dir_row,
                            unmatched_summary,
                            ft.OutlinedButton(
                                "Konfigurationen",
                                icon=ft.Icons.TUNE,
                                on_click=lambda _e: on_open_configurations(),
                            ),
                        ],
                        spacing=SP_8,
                    ),
                ),
            ],
            spacing=0,
        ),
    )


def build_ergebnis_panel(
    *,
    run_dir_row: ft.Control,
    pruefbedarf_box: ft.Control,
    summary_processed: ft.Text,
    summary_documents: ft.Text,
    summary_duplicates: ft.Text,
    summary_unklar: ft.Text,
    summary_errors: ft.Text,
    summary_unmatched: ft.Text,
) -> ft.Container:
    return ft.Container(
        bgcolor=SURFACE_2,
        border=ft.Border.all(1, LINE),
        border_radius=RADIUS_CARD,
        padding=ft.Padding.symmetric(horizontal=SP_12, vertical=SP_8),
        content=ft.Column(
            [
                ft.Text("Ergebnis", size=11, weight=ft.FontWeight.W_600, color=MUTED),
                run_dir_row,
                pruefbedarf_box,
                ft.Row(
                    [
                        _kpi("Verarbeitet", summary_processed, MUTED),
                        _kpi("Belege", summary_documents, OK),
                        _kpi("Duplikate", summary_duplicates, ACCENT),
                        _kpi("Unklar", summary_unklar, WARN),
                        _kpi("Fehler", summary_errors, ERR),
                        _kpi("Nicht zugeordnet", summary_unmatched, MUTED),
                    ],
                    wrap=True,
                    spacing=SP_8,
                ),
            ],
            spacing=SP_8,
        ),
    )


def build_manual_review_panel(
    *,
    pruefbedarf_box: ft.Control,
    on_open_review: Callable,
) -> ft.Container:
    return ft.Container(
        bgcolor=WARN_SOFT,
        border=ft.Border.all(1, WARN_EDGE),
        border_radius=RADIUS_CARD,
        padding=SP_12,
        content=ft.Column(
            [
                ft.Text("Zur manuellen Prüfung", size=14, weight=ft.FontWeight.W_700, color=WARN),
                pruefbedarf_box,
                ft.OutlinedButton(
                    "Dokumente prüfen",
                    icon=ft.Icons.FACT_CHECK_OUTLINED,
                    on_click=lambda _e: on_open_review(),
                ),
            ],
            spacing=SP_8,
        ),
    )
