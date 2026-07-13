"""Inline filename pattern builder — Figma tag composition (Make FilenameBuilder port)."""

from __future__ import annotations

from typing import Callable

import flet as ft

from invoice_tool.configuration_model import (
    FilenameComponent,
    FilenamePattern,
    available_filename_components,
    copy_filename_pattern,
    preview_filename,
)
from invoice_tool.scan_models import ScanModel
from invoice_tool.ui_v2.components import inline_error, inline_warning
from invoice_tool.ui_v2.edit_components import helper_text, section_label
from invoice_tool.ui_v2.theme import (
    COLOR_ACCENT_FAINT,
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_MUTED_LIGHT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_SUBTLE,
    COLOR_SURFACE_ALT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    SPACE_SM,
)
from invoice_tool.ui_v2.validation import validate_filename_pattern


def _safe_update(control: ft.Control) -> None:
    try:
        control.update()
    except (AssertionError, RuntimeError, AttributeError):
        pass


def _feature_components(pattern: FilenamePattern) -> list[FilenameComponent]:
    return [
        component
        for component in pattern.components
        if not (component.type == "system" and component.key == "extension")
    ]


def _has_component(pattern: FilenamePattern, key: str) -> bool:
    return any(component.key == key for component in _feature_components(pattern))


def _remove_component(pattern: FilenamePattern, key: str) -> FilenamePattern:
    updated = copy_filename_pattern(pattern)
    updated.components = [
        component
        for component in updated.components
        if not (component.key == key and not (component.type == "system" and component.key == "extension"))
    ]
    if not any(c.type == "system" and c.key == "extension" for c in updated.components):
        updated.components.append(FilenameComponent(type="system", key="extension", label="Dateityp"))
    return updated


def _add_component(pattern: FilenamePattern, item: dict[str, str]) -> FilenamePattern:
    key = item.get("key") or ""
    if not key or _has_component(pattern, key):
        return pattern
    updated = copy_filename_pattern(pattern)
    without_ext = [c for c in updated.components if not (c.type == "system" and c.key == "extension")]
    without_ext.append(
        FilenameComponent(
            type=str(item.get("type") or "feature"),
            key=key,
            label=str(item.get("label") or key),
        )
    )
    without_ext.append(FilenameComponent(type="system", key="extension", label="Dateityp"))
    updated.components = without_ext
    return updated


def build_filename_pattern_editor(
    *,
    scan_model: ScanModel,
    pattern: FilenamePattern,
    on_change: Callable[[FilenamePattern], None],
    error: str | None = None,
) -> ft.Column:
    """Figma Dateinamenmuster — Baustein-Pills, Tag-Zusammensetzung, Beispiel."""
    current = copy_filename_pattern(pattern)
    preview_text = ft.Text("", size=11, font_family="Menlo", color=COLOR_TEXT_SECONDARY, max_lines=2)
    issues_host = ft.Column(spacing=SPACE_SM)
    composition_host = ft.Row(spacing=2, wrap=True, run_spacing=4)

    palette_items = [
        item
        for item in available_filename_components(scan_model)
        if item.get("key") not in {"extension", "custom_text"}
    ]

    def _emit(updated: FilenamePattern) -> None:
        nonlocal current
        current = copy_filename_pattern(updated)
        on_change(current)
        _render()

    def _render() -> None:
        components = _feature_components(current)
        composition_host.controls = []
        if not components:
            composition_host.controls.append(
                ft.Text(
                    "Bausteine oben auswählen",
                    size=12,
                    color=COLOR_MUTED_LIGHT,
                    italic=True,
                )
            )
        else:
            for index, component in enumerate(components):
                if index > 0:
                    composition_host.controls.append(
                        ft.Text(
                            current.separator,
                            size=12,
                            color=COLOR_BORDER_STRONG,
                            font_family="Menlo",
                        )
                    )
                label = component.label or component.key
                composition_host.controls.append(
                    ft.Container(
                        bgcolor=COLOR_PRIMARY_SUBTLE,
                        border=ft.Border.all(1, COLOR_PRIMARY_SUBTLE),
                        border_radius=4,
                        padding=ft.Padding.only(left=9, right=4, top=3, bottom=3),
                        content=ft.Row(
                            [
                                ft.Text(label, size=11, color=COLOR_PRIMARY, weight=ft.FontWeight.W_600),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_size=10,
                                    icon_color=COLOR_PRIMARY,
                                    style=ft.ButtonStyle(padding=0),
                                    on_click=lambda _e, key=component.key: _emit(_remove_component(current, key)),
                                ),
                            ],
                            spacing=2,
                            tight=True,
                        ),
                    )
                )
            composition_host.controls.append(
                ft.Text(".pdf", size=12, color=COLOR_TEXT_MUTED, font_family="Menlo")
            )

        issues = validate_filename_pattern(current, scan_model)
        try:
            preview = preview_filename(current, scan_model)
        except Exception:
            preview = "—"
        preview_text.value = preview
        issues_host.controls = [inline_warning(item) for item in issues]
        _safe_update(composition_host)
        _safe_update(preview_text)
        _safe_update(issues_host)

    palette_controls: list[ft.Control] = []
    for item in palette_items:
        key = item.get("key") or ""
        label = item.get("label") or key
        used = _has_component(current, key)

        def _add(_e: ft.ControlEvent, payload: dict[str, str] = item) -> None:
            _emit(_add_component(current, payload))

        palette_controls.append(
            ft.Container(
                on_click=None if used else _add,
                ink=not used,
                border=ft.Border.all(1, COLOR_BORDER if used else COLOR_PRIMARY_SUBTLE),
                border_radius=4,
                bgcolor="#f0f0f2" if used else COLOR_ACCENT_FAINT,
                opacity=0.55 if used else 1.0,
                padding=ft.Padding.symmetric(horizontal=10, vertical=3),
                content=ft.Text(
                    label,
                    size=11,
                    weight=ft.FontWeight.W_600,
                    color=COLOR_BORDER_STRONG if used else COLOR_PRIMARY,
                ),
            )
        )

    _render()

    return ft.Column(
        [
            section_label("Dateinamenmuster"),
            helper_text("Verfügbare Bausteine — klicken zum Hinzufügen:"),
            ft.Row(palette_controls, spacing=5, wrap=True),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                bgcolor=COLOR_SURFACE_ALT,
                border=ft.Border.all(1, COLOR_BORDER),
                border_radius=6,
                alignment=ft.Alignment.TOP_LEFT,
                content=composition_host,
            ),
            ft.Container(
                visible=True,
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                bgcolor=COLOR_SURFACE_ALT,
                border=ft.Border.all(1, COLOR_BORDER),
                border_radius=6,
                content=ft.Row(
                    [
                        ft.Text(
                            "BEISPIEL",
                            size=10,
                            weight=ft.FontWeight.W_700,
                            color=COLOR_TEXT_MUTED,
                        ),
                        preview_text,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
            issues_host,
            inline_error(error) if error else ft.Container(height=0),
        ],
        spacing=8,
        tight=True,
    )
