"""Shared edit UI helpers for UI-v2 write controls."""

from __future__ import annotations

from typing import Callable

import flet as ft

from invoice_tool.ui_v2.components import (
    destructive_button,
    inline_error,
    primary_button,
    secondary_button,
)
from invoice_tool.ui_v2.theme import (
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_SURFACE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    INPUT_CONTROL_HEIGHT,
    RADIUS_INPUT,
    RADIUS_PANEL,
    SPACE_MD,
    SPACE_XL,
)


def _dialog_shell(*, title: str, body: ft.Control, actions: list[ft.Control]) -> ft.AlertDialog:
    return ft.AlertDialog(
        modal=True,
        bgcolor=COLOR_SURFACE,
        shape=ft.RoundedRectangleBorder(radius=RADIUS_PANEL),
        title=ft.Text(title, size=15, weight=ft.FontWeight.W_700, color=COLOR_TEXT_PRIMARY),
        content=body,
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )


def action_button(label: str, *, on_click: Callable[[ft.ControlEvent], None], primary: bool = False, destructive: bool = False) -> ft.Control:
    if destructive:
        return destructive_button(label, on_click=on_click)
    if primary:
        return primary_button(label, on_click=on_click)
    return secondary_button(label, on_click=on_click)


def feedback_banner(message: str, *, is_error: bool = False) -> ft.Container:
    if is_error:
        return inline_error(message)
    return ft.Container(
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=8,
        padding=SPACE_MD,
        content=ft.Text(message, color=COLOR_TEXT_PRIMARY, size=13),
    )


def confirmation_dialog(
    *,
    title: str,
    message: str,
    confirm_label: str = "Bestätigen",
    cancel_label: str = "Abbrechen",
    on_confirm: Callable[[], None],
    on_cancel: Callable[[], None] | None = None,
) -> ft.AlertDialog:
    def _close(_event: ft.ControlEvent | None = None) -> None:
        if on_cancel:
            on_cancel()

    return _dialog_shell(
        title=title,
        body=ft.Text(message, color=COLOR_TEXT_SECONDARY, size=13),
        actions=[
            secondary_button(cancel_label, on_click=_close),
            destructive_button(confirm_label, on_click=lambda _e: on_confirm()),
        ],
    )


def unsaved_changes_dialog(
    *,
    on_discard: Callable[[], None],
    on_continue: Callable[[], None],
) -> ft.AlertDialog:
    return _dialog_shell(
        title="Ungespeicherte Änderungen",
        body=ft.Text(
            "Es gibt ungespeicherte Änderungen. Möchten Sie fortfahren?",
            color=COLOR_TEXT_SECONDARY,
            size=13,
        ),
        actions=[
            secondary_button("Weiter bearbeiten", on_click=lambda _e: on_continue()),
            primary_button("Änderungen verwerfen", on_click=lambda _e: on_discard()),
        ],
    )


def _outlined_input_kwargs() -> dict:
    return {
        "dense": True,
        "text_size": 12,
        "max_lines": 1,
        "border_radius": RADIUS_INPUT,
        "border_color": COLOR_BORDER,
        "focused_border_color": COLOR_BORDER_STRONG,
        "bgcolor": COLOR_SURFACE,
        "content_padding": ft.Padding.symmetric(horizontal=10, vertical=6),
    }


def compact_input_shell(field: ft.Control) -> ft.Container:
    """Uniform 34px control height for single-line inputs."""
    return ft.Container(height=INPUT_CONTROL_HEIGHT, alignment=ft.Alignment.CENTER_LEFT, content=field)


def outlined_field_kwargs() -> dict:
    """Shared outline styling for TextField/Dropdown in edit forms."""
    return _outlined_input_kwargs()


def form_field(
    label: str,
    *,
    value: str = "",
    on_change: Callable[[ft.ControlEvent], None] | None = None,
    read_only: bool = False,
    placeholder: str | None = None,
) -> ft.TextField:
    """Single-line input — pair with form_field_group for Make-style label-above layout."""
    del label  # Label is rendered by form_field_group.
    return ft.TextField(
        value=value,
        read_only=read_only,
        on_change=on_change,
        hint_text=placeholder,
        **_outlined_input_kwargs(),
    )


def section_label(text: str) -> ft.Text:
    return ft.Text(
        text.upper(),
        size=10,
        weight=ft.FontWeight.W_700,
        color=COLOR_TEXT_MUTED,
    )


def helper_text(text: str) -> ft.Text:
    return ft.Text(text, size=11, color=COLOR_TEXT_MUTED)
