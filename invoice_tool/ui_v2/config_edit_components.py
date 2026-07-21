"""Figma-aligned configuration edit form blocks (Make RuleBuilder, FilenameBuilder, FolderPicker)."""

from __future__ import annotations

from typing import Callable

import flet as ft

from invoice_tool.scan_models import ScanModel, matching_features
from invoice_tool.ui_v2.components import inline_error, make_value_tag_pill, secondary_button
from invoice_tool.ui_v2.edit_components import full_width_field, helper_text, outlined_dropdown_kwargs, outlined_field_kwargs, section_label
from invoice_tool.ui_v2.theme import (
    COLOR_BORDER,
    COLOR_MUTED_LIGHT,
    COLOR_SURFACE,
    COLOR_SURFACE_ALT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    INPUT_CONTROL_HEIGHT,
    RADIUS_INPUT,
)


def _field_caption(text: str, *, hint: str | None = None) -> ft.Column:
    items: list[ft.Control] = [
        ft.Text(
            text.upper(),
            size=10,
            weight=ft.FontWeight.W_700,
            color=COLOR_TEXT_MUTED,
        ),
    ]
    if hint:
        items.append(ft.Text(hint, size=10, color=COLOR_MUTED_LIGHT))
    return ft.Column(items, spacing=4, tight=True)


def build_rule_builder_field(
    *,
    scan_model: ScanModel,
    feature_key: str,
    values: list[str],
    on_field_change: Callable[[str], None],
    on_values_change: Callable[[list[str]], None],
    error: str | None = None,
) -> ft.Column:
    """Erkennungsregel — Feld-Dropdown + ODER-verknüpfte Werte-Tags."""
    value_input = ft.TextField(
        hint_text="Wert eingeben, z.B. amex",
        expand=True,
        **outlined_field_kwargs(),
    )

    def _add_value(_event: ft.ControlEvent | None = None) -> None:
        raw = (value_input.value or "").strip()
        if not raw:
            return
        cleaned = [part.strip() for part in raw.split(",") if part.strip()]
        merged = list(values)
        for item in cleaned:
            if item not in merged:
                merged.append(item)
        value_input.value = ""
        on_values_change(merged)

    value_input.on_submit = _add_value

    tag_row: list[ft.Control] = []
    for index, value in enumerate(values):
        tag_row.append(
            make_value_tag_pill(
                value,
                on_remove=lambda _e, idx=index: on_values_change([v for i, v in enumerate(values) if i != idx]),
            )
        )

    feature_dd = ft.Dropdown(
        value=feature_key or None,
        options=[ft.dropdown.Option(f.key, f.label) for f in matching_features(scan_model)],
        hint_text="— Feld wählen —",
        on_select=lambda e: on_field_change(str(e.control.value or "")),
        expand=True,
        **outlined_dropdown_kwargs(),
    )

    body = ft.Column(
        [
            section_label("Erkennungsregel"),
            ft.Container(
                border=ft.Border.all(1, COLOR_BORDER),
                border_radius=8,
                content=ft.Column(
                    [
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                            bgcolor=COLOR_SURFACE_ALT,
                            border=ft.Border(bottom=ft.BorderSide(1, COLOR_BORDER)),
                            content=ft.Column(
                                [
                                    _field_caption("Feld"),
                                    full_width_field(feature_dd),
                                ],
                                spacing=6,
                                tight=True,
                            ),
                        ),
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                            content=ft.Column(
                                [
                                    _field_caption("Werte", hint="(ODER-verknüpft)"),
                                    ft.Row(tag_row, spacing=5, wrap=True) if tag_row else ft.Container(),
                                    ft.Row(
                                        [
                                            full_width_field(value_input),
                                            secondary_button(
                                                "+ Hinzufügen",
                                                on_click=_add_value,
                                                height=INPUT_CONTROL_HEIGHT,
                                            ),
                                        ],
                                        spacing=5,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                        ),
                    ],
                    spacing=0,
                    tight=True,
                ),
            ),
            helper_text("Mehrere Werte werden per ODER verknüpft."),
            inline_error(error) if error else ft.Container(height=0),
        ],
        spacing=8,
        tight=True,
    )
    return body


def build_folder_picker_field(
    *,
    value: str,
    on_change: Callable[[str], None],
    on_pick: Callable[[ft.ControlEvent], None],
    error: str | None = None,
) -> ft.Column:
    """Zielordner — Pfad-Eingabe mit „Pfad eingeben“-Button."""
    path_field = ft.TextField(
        value=value,
        text_style=ft.TextStyle(font_family="Menlo"),
        hint_text="Ordner über den Button auswählen…",
        expand=True,
        on_change=lambda e: on_change((e.control.value or "").strip()),
        **outlined_field_kwargs(),
    )
    pick_btn = ft.OutlinedButton(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER_OPEN_OUTLINED, size=13, color=COLOR_TEXT_SECONDARY),
                ft.Text("Pfad eingeben", size=12, color=COLOR_TEXT_SECONDARY),
            ],
            spacing=6,
            tight=True,
        ),
        on_click=on_pick,
        height=INPUT_CONTROL_HEIGHT,
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, COLOR_BORDER),
            shape=ft.RoundedRectangleBorder(radius=6),
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        ),
    )
    return ft.Column(
        [
            section_label("Zielordner"),
            ft.Row(
                [full_width_field(path_field), pick_btn],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            helper_text("Öffnet den nativen Systemdialog zur Ordnerauswahl."),
            inline_error(error) if error else ft.Container(height=0),
        ],
        spacing=5,
        tight=True,
    )
