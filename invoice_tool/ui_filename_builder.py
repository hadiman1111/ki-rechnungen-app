"""Filename pattern builder dialog."""

from __future__ import annotations

from typing import Callable

import flet as ft

from invoice_tool.configuration_model import (
    DATE_FORMATS,
    FilenameComponent,
    FilenamePattern,
    SEPARATORS,
    available_filename_components,
    copy_filename_pattern,
    format_date_preview,
    preview_filename,
)
from invoice_tool.scan_models import ScanModel
from invoice_tool.ui_components import primary_button, secondary_button, section_heading, validation_message
from invoice_tool.ui_theme import (
    COLOR_BORDER,
    COLOR_SURFACE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    RADIUS_LG,
    SPACE_MD,
    SPACE_SM,
)


def build_filename_builder_dialog(
    *,
    page: ft.Page,
    scan_model: ScanModel,
    initial_pattern: FilenamePattern,
    on_done: Callable[[FilenamePattern], None],
    on_cancel: Callable[[], None],
) -> ft.AlertDialog:
    draft = copy_filename_pattern(initial_pattern)
    preview_text = ft.Text("", selectable=True)
    component_column = ft.Column(spacing=SPACE_SM, scroll=ft.ScrollMode.AUTO)

    def _refresh_preview() -> None:
        preview_text.value = preview_filename(draft, scan_model)
        preview_text.update()

    def _render_components() -> None:
        rows: list[ft.Control] = []
        for index, component in enumerate(draft.components):
            label = component.label or component.key
            if component.type == "feature" and component.key in DATE_FORMATS:
                label = f"{component.label} ({component.date_format})"
            rows.append(
                ft.Container(
                    border=ft.Border.all(1, COLOR_BORDER),
                    border_radius=RADIUS_LG,
                    padding=SPACE_SM,
                    content=ft.Row(
                        [
                            ft.Text(label, expand=True),
                            ft.IconButton(
                                icon=ft.Icons.ARROW_UPWARD,
                                tooltip="Nach oben",
                                on_click=lambda _e, idx=index: _move(idx, -1),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.ARROW_DOWNWARD,
                                tooltip="Nach unten",
                                on_click=lambda _e, idx=index: _move(idx, 1),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                tooltip="Entfernen",
                                on_click=lambda _e, idx=index: _remove(idx),
                            ),
                        ]
                    ),
                )
            )
        component_column.controls = rows
        component_column.update()
        _refresh_preview()

    def _move(index: int, delta: int) -> None:
        new_index = index + delta
        if 0 <= new_index < len(draft.components):
            draft.components[index], draft.components[new_index] = (
                draft.components[new_index],
                draft.components[index],
            )
            _render_components()

    def _remove(index: int) -> None:
        if 0 <= index < len(draft.components):
            draft.components.pop(index)
            _render_components()

    def _add_component(item: dict[str, str]) -> None:
        if item["key"] == "extension":
            if any(c.key == "extension" for c in draft.components):
                return
            draft.components.append(
                FilenameComponent(type="system", key="extension", label=item["label"])
            )
        elif item["key"] == "custom_text":
            draft.components.append(
                FilenameComponent(type="system", key="custom_text", label=item["label"], custom_text="text")
            )
        else:
            feature = scan_model.get_feature(item["key"])
            draft.components.append(
                FilenameComponent(
                    type="feature",
                    key=item["key"],
                    label=feature.label if feature else item["label"],
                )
            )
        _render_components()

    separator_dropdown = ft.Dropdown(
        label="Trennzeichen",
        value=_separator_key(draft.separator),
        options=[
            ft.dropdown.Option("underscore", "Unterstrich (_)"),
            ft.dropdown.Option("hyphen", "Bindestrich (-)"),
            ft.dropdown.Option("space", "Leerzeichen"),
            ft.dropdown.Option("dot", "Punkt (.)"),
        ],
        on_select=lambda e: _set_separator(str(e.control.value or "underscore")),
    )

    def _set_separator(key: str) -> None:
        draft.separator = SEPARATORS.get(key, "_")
        _refresh_preview()

    available = ft.Wrap(
        spacing=SPACE_SM,
        run_spacing=SPACE_SM,
        controls=[
            ft.OutlinedButton(
                item["label"],
                on_click=lambda _e, payload=item: _add_component(payload),
            )
            for item in available_filename_components(scan_model)
        ],
    )

    date_format_help = ft.Column(
        [
            ft.Text(f"{key} → {format_date_preview(key)}", size=11, color=COLOR_TEXT_MUTED)
            for key in DATE_FORMATS
        ],
        spacing=2,
    )

    _render_components()

    def _finish(_event: ft.ControlEvent) -> None:
        on_done(copy_filename_pattern(draft))
        page.close(dialog)

    def _cancel(_event: ft.ControlEvent) -> None:
        on_cancel()
        page.close(dialog)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Dateinamensmuster bearbeiten"),
        content=ft.Container(
            width=720,
            content=ft.Column(
                [
                    ft.Text(
                        "Wähle die gewünschten Bestandteile und bringe sie in die gewünschte Reihenfolge.",
                        color=COLOR_TEXT_MUTED,
                    ),
                    section_heading("Verfügbare Bausteine"),
                    available,
                    section_heading("Aktuelle Dateistruktur"),
                    component_column,
                    separator_dropdown,
                    section_heading("Datumsformat (Beispiele)"),
                    date_format_help,
                    section_heading("So sieht ein Dateiname mit Beispieldaten aus"),
                    preview_text,
                    validation_message("", is_error=False),
                ],
                spacing=SPACE_MD,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
        actions=[
            secondary_button("Abbrechen", on_click=_cancel),
            primary_button("Fertig", on_click=_finish),
        ],
    )
    _refresh_preview()
    return dialog


def _separator_key(value: str) -> str:
    for key, sep in SEPARATORS.items():
        if sep == value:
            return key
    return "underscore"
