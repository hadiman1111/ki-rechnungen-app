"""Product filename pattern builder — Bausteine, Eigener Text, Validierung.

Preview-only UI. Replaces unrestricted free-text pattern authoring.
"""

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
from invoice_tool.ui_v2.edit_components import (
    helper_text,
    outlined_dropdown_kwargs,
    outlined_field_kwargs,
    section_label,
)
from invoice_tool.ui_v2.filename_pattern import (
    FILENAME_PATTERN_SAFE_EDIT_MARKER,
    MSG_ER_ER_DUPLICATION,
    add_custom_text_component,
    sanitize_custom_text,
    strip_er_custom_when_art_present,
    supported_block_catalog,
    validate_pattern_product_rules,
)
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    FILENAME_BLOCK_REORDER_MARKER,
    TOOLTIP_FILENAME_BLOCK_EARLIER,
    TOOLTIP_FILENAME_BLOCK_LATER,
)
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
    INPUT_CONTROL_HEIGHT,
    SPACE_SM,
)
from invoice_tool.ui_v2.validation import validate_filename_pattern

PREVIEW_LABEL = "So sieht der Dateiname mit Beispieldaten aus"
SECTION_FILENAME = "Dateiname"
SECTION_FILENAME_PATTERN = "Dateinamenmuster"


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


def _has_feature(pattern: FilenamePattern, key: str) -> bool:
    if key == "custom_text":
        return False  # multiple custom texts allowed
    return any(component.key == key for component in _feature_components(pattern))


def _remove_component_simple(pattern: FilenamePattern, index: int) -> FilenamePattern:
    updated = copy_filename_pattern(pattern)
    features = _feature_components(updated)
    if not (0 <= index < len(features)):
        return pattern
    features.pop(index)
    features.append(FilenameComponent(type="system", key="extension", label="Dateityp"))
    updated.components = features
    return updated


def _move_component(pattern: FilenamePattern, index: int, *, delta: int) -> FilenamePattern:
    """Reorder a filename block earlier (−1) or later (+1) in the filename."""

    updated = copy_filename_pattern(pattern)
    features = _feature_components(updated)
    target = index + delta
    if not (0 <= index < len(features) and 0 <= target < len(features)):
        return pattern
    features[index], features[target] = features[target], features[index]
    features.append(FilenameComponent(type="system", key="extension", label="Dateityp"))
    updated.components = features
    return updated


def _add_feature(pattern: FilenamePattern, item: dict[str, str]) -> FilenamePattern:
    key = item.get("key") or ""
    if not key or key == "separator":
        return pattern
    if key == "custom_text":
        return add_custom_text_component(pattern, "text")
    if _has_feature(pattern, key):
        return pattern
    updated = copy_filename_pattern(pattern)
    without_ext = [
        c for c in updated.components if not (c.type == "system" and c.key == "extension")
    ]
    without_ext.append(
        FilenameComponent(
            type=str(item.get("type") or "feature"),
            key=key,
            label=str(item.get("label") or key),
        )
    )
    without_ext.append(
        FilenameComponent(type="system", key="extension", label="Dateityp")
    )
    updated.components = without_ext
    return updated


def build_filename_pattern_editor(
    *,
    scan_model: ScanModel,
    pattern: FilenamePattern,
    on_change: Callable[[FilenamePattern], None],
    error: str | None = None,
) -> ft.Column:
    """Dateinamenmuster with plus/dropdown, Eigener Text, live preview, validation."""

    current = strip_er_custom_when_art_present(copy_filename_pattern(pattern))
    preview_text = ft.Text(
        "", size=11, font_family="Menlo", color=COLOR_TEXT_SECONDARY, max_lines=2
    )
    issues_host = ft.Column(spacing=SPACE_SM)
    composition_host = ft.Row(spacing=2, wrap=True, run_spacing=4)
    custom_input = ft.TextField(
        hint_text="Eigener Text…",
        dense=True,
        **outlined_field_kwargs(),
    )
    add_dd = ft.Dropdown(
        hint_text="Baustein hinzufügen",
        options=[],
        dense=True,
        width=220,
        **outlined_dropdown_kwargs(),
    )

    catalog = [
        item
        for item in supported_block_catalog(scan_model)
        if item.get("key") != "separator"
    ]

    def _emit(updated: FilenamePattern) -> None:
        nonlocal current
        cleaned = strip_er_custom_when_art_present(copy_filename_pattern(updated))
        current = cleaned
        on_change(current)
        _render()

    def _render() -> None:
        components = _feature_components(current)
        composition_host.controls = []
        if not components:
            composition_host.controls.append(
                ft.Text(
                    "Bausteine hinzufügen",
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
                if component.key == "custom_text":
                    label = f"„{component.custom_text or '…'}“"
                else:
                    label = component.label or component.key
                composition_host.controls.append(
                    ft.Container(
                        bgcolor=COLOR_PRIMARY_SUBTLE,
                        border=ft.Border.all(1, COLOR_PRIMARY_SUBTLE),
                        border_radius=4,
                        padding=ft.Padding.only(left=9, right=4, top=3, bottom=3),
                        content=ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK,
                                    icon_size=12,
                                    icon_color=COLOR_PRIMARY,
                                    tooltip=TOOLTIP_FILENAME_BLOCK_EARLIER,
                                    style=ft.ButtonStyle(padding=0),
                                    disabled=index == 0,
                                    on_click=lambda _e, idx=index: _emit(
                                        _move_component(current, idx, delta=-1)
                                    ),
                                    data=(
                                        f"{FILENAME_BLOCK_REORDER_MARKER}|"
                                        f"earlier|{TOOLTIP_FILENAME_BLOCK_EARLIER}"
                                    ),
                                ),
                                ft.Text(
                                    label,
                                    size=11,
                                    color=COLOR_PRIMARY,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_FORWARD,
                                    icon_size=12,
                                    icon_color=COLOR_PRIMARY,
                                    tooltip=TOOLTIP_FILENAME_BLOCK_LATER,
                                    style=ft.ButtonStyle(padding=0),
                                    disabled=index >= len(components) - 1,
                                    on_click=lambda _e, idx=index: _emit(
                                        _move_component(current, idx, delta=1)
                                    ),
                                    data=(
                                        f"{FILENAME_BLOCK_REORDER_MARKER}|"
                                        f"later|{TOOLTIP_FILENAME_BLOCK_LATER}"
                                    ),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_size=10,
                                    icon_color=COLOR_PRIMARY,
                                    style=ft.ButtonStyle(padding=0),
                                    on_click=lambda _e, idx=index: _emit(
                                        _remove_component_simple(current, idx)
                                    ),
                                ),
                            ],
                            spacing=2,
                            tight=True,
                        ),
                        data=(
                            f"{FILENAME_PATTERN_SAFE_EDIT_MARKER}|segment|{component.key}|"
                            f"{FILENAME_BLOCK_REORDER_MARKER}|no_nach_oben_unten"
                        ),
                    )
                )
            composition_host.controls.append(
                ft.Text(".pdf", size=12, color=COLOR_TEXT_MUTED, font_family="Menlo")
            )

        # Plus-adjacent dropdown options: unused features + Eigener Text.
        options: list[ft.dropdown.Option] = []
        for item in catalog:
            key = item.get("key") or ""
            label = item.get("label") or key
            if key == "custom_text":
                options.append(ft.dropdown.Option("custom_text", "Eigener Text"))
                continue
            if not _has_feature(current, key):
                options.append(ft.dropdown.Option(key, label))
        add_dd.options = options

        base_issues = validate_filename_pattern(current, scan_model)
        try:
            preview = preview_filename(current, scan_model)
        except Exception:
            preview = "—"
        product_issues = validate_pattern_product_rules(
            current, scan_model, preview=preview
        )
        # Prefer cleaned preview without _er_er_ when auto-stripped.
        if MSG_ER_ER_DUPLICATION in product_issues:
            cleaned = strip_er_custom_when_art_present(current)
            if cleaned is not current and cleaned.components != current.components:
                current.components = cleaned.components
                try:
                    preview = preview_filename(current, scan_model)
                except Exception:
                    pass
                product_issues = validate_pattern_product_rules(
                    current, scan_model, preview=preview
                )
        preview_text.value = preview
        all_issues = list(dict.fromkeys([*base_issues, *product_issues]))
        issues_host.controls = [inline_warning(item) for item in all_issues]
        _safe_update(composition_host)
        _safe_update(preview_text)
        _safe_update(issues_host)
        _safe_update(add_dd)

    def _on_add_selected(_e: ft.ControlEvent) -> None:
        key = str(add_dd.value or "")
        if not key:
            return
        if key == "custom_text":
            text = sanitize_custom_text(custom_input.value) or "text"
            _emit(add_custom_text_component(current, text))
            custom_input.value = ""
        else:
            payload = next((i for i in catalog if i.get("key") == key), None)
            if payload:
                _emit(_add_feature(current, payload))
        add_dd.value = None
        _safe_update(add_dd)
        _safe_update(custom_input)

    def _on_add_custom(_e: ft.ControlEvent) -> None:
        text = sanitize_custom_text(custom_input.value)
        if not text:
            issues_host.controls = [
                inline_warning("Bitte eigenen Text eingeben, dann hinzufügen.")
            ]
            _safe_update(issues_host)
            return
        _emit(add_custom_text_component(current, text))
        custom_input.value = ""
        _safe_update(custom_input)

    add_dd.on_select = _on_add_selected

    # Legacy palette chips for quick add (supported blocks only).
    palette_controls: list[ft.Control] = []
    for item in available_filename_components(scan_model):
        key = item.get("key") or ""
        if key in {"extension"}:
            continue
        label = "Eigener Text" if key == "custom_text" else (item.get("label") or key)
        used = _has_feature(current, key) if key != "custom_text" else False

        def _add(_e: ft.ControlEvent, payload: dict[str, str] = item) -> None:
            if (payload.get("key") or "") == "custom_text":
                text = sanitize_custom_text(custom_input.value) or "text"
                _emit(add_custom_text_component(current, text))
            else:
                _emit(_add_feature(current, payload))

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
                data=f"{FILENAME_PATTERN_SAFE_EDIT_MARKER}|palette|{key}",
            )
        )

    _render()

    return ft.Column(
        [
            section_label(SECTION_FILENAME_PATTERN),
            helper_text(
                "Bausteine wählen oder über Plus/Dropdown hinzufügen. "
                "Eigener Text ist ein sicherer Abschnitt — kein freier Muster-Freitext."
            ),
            ft.Row(palette_controls, spacing=5, wrap=True),
            ft.Row(
                [
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=18, color=COLOR_PRIMARY),
                    add_dd,
                    custom_input,
                    ft.OutlinedButton(
                        "Eigener Text übernehmen",
                        on_click=_on_add_custom,
                        height=INPUT_CONTROL_HEIGHT,
                    ),
                ],
                spacing=8,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                data=f"{FILENAME_PATTERN_SAFE_EDIT_MARKER}|plus_dropdown_add",
            ),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                bgcolor=COLOR_SURFACE_ALT,
                border=ft.Border.all(1, COLOR_BORDER),
                border_radius=6,
                alignment=ft.Alignment.TOP_LEFT,
                content=composition_host,
                data=f"{FILENAME_PATTERN_SAFE_EDIT_MARKER}|composition_locked_structure",
            ),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                bgcolor=COLOR_SURFACE_ALT,
                border=ft.Border.all(1, COLOR_BORDER),
                border_radius=6,
                content=ft.Column(
                    [
                        ft.Text(
                            PREVIEW_LABEL,
                            size=10,
                            weight=ft.FontWeight.W_700,
                            color=COLOR_TEXT_MUTED,
                        ),
                        preview_text,
                    ],
                    spacing=4,
                    tight=True,
                ),
                data=f"{FILENAME_PATTERN_SAFE_EDIT_MARKER}|live_preview",
            ),
            issues_host,
            inline_error(error) if error else ft.Container(height=0),
        ],
        spacing=8,
        tight=True,
        data=f"{FILENAME_PATTERN_SAFE_EDIT_MARKER}|builder_root|{SECTION_FILENAME}",
    )
