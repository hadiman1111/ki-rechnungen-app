"""Reusable Flet UI components backed by the central theme."""

from __future__ import annotations

from typing import Callable

import flet as ft

from invoice_tool.ui_theme import (
    BORDER_WIDTH,
    COLOR_BORDER,
    COLOR_DISABLED,
    COLOR_ERROR,
    COLOR_ERROR_SOFT,
    COLOR_FOCUS,
    COLOR_NAV_ACTIVE_BG,
    COLOR_PAGE_BG,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_SUCCESS_SOFT,
    COLOR_SURFACE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
    COLOR_WARNING_SOFT,
    CONTROL_HEIGHT,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_CARD_TITLE,
    FONT_SIZE_PAGE_TITLE,
    FONT_SIZE_SECTION_TITLE,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_PILL,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
)


def primary_button(
    label: str,
    *,
    icon: str | None = None,
    on_click: Callable | None = None,
    disabled: bool = False,
    expand: bool | int = False,
) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        label,
        icon=icon,
        on_click=on_click,
        disabled=disabled,
        expand=expand,
        height=CONTROL_HEIGHT,
        style=ft.ButtonStyle(
            bgcolor=COLOR_PRIMARY,
            color=ft.Colors.WHITE,
            text_style=ft.TextStyle(size=FONT_SIZE_BODY, weight=ft.FontWeight.W_600),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
        ),
    )


def secondary_button(
    label: str,
    *,
    icon: str | None = None,
    on_click: Callable | None = None,
    disabled: bool = False,
) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        label,
        icon=icon,
        on_click=on_click,
        disabled=disabled,
        height=CONTROL_HEIGHT,
        style=ft.ButtonStyle(
            color=COLOR_TEXT_SECONDARY,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
            side=ft.BorderSide(BORDER_WIDTH, COLOR_BORDER),
        ),
    )


def destructive_button(
    label: str,
    *,
    on_click: Callable | None = None,
) -> ft.TextButton:
    return ft.TextButton(
        label,
        on_click=on_click,
        style=ft.ButtonStyle(color=COLOR_ERROR),
    )


def nav_item(
    label: str,
    *,
    icon: str,
    active: bool = False,
    badge: str | None = None,
    on_click: Callable | None = None,
) -> ft.Container:
    trailing: list[ft.Control] = []
    if badge:
        trailing.append(
            ft.Container(
                content=ft.Text(badge, size=10, color=COLOR_WARNING, weight=ft.FontWeight.W_700),
                bgcolor=COLOR_WARNING_SOFT,
                border_radius=RADIUS_PILL,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            )
        )
    return ft.Container(
        on_click=on_click,
        bgcolor=COLOR_NAV_ACTIVE_BG if active else None,
        border=ft.Border(
            left=ft.BorderSide(3, COLOR_PRIMARY if active else ft.Colors.TRANSPARENT),
        ),
        border_radius=ft.BorderRadius.only(top_right=RADIUS_MD, bottom_right=RADIUS_MD),
        padding=ft.Padding.only(left=10, right=SPACE_MD, top=SPACE_SM, bottom=SPACE_SM),
        content=ft.Row(
            [
                ft.Icon(icon, size=18, color=COLOR_PRIMARY if active else COLOR_TEXT_MUTED),
                ft.Text(
                    label,
                    size=FONT_SIZE_BODY,
                    weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_500,
                    color=COLOR_PRIMARY if active else COLOR_TEXT_SECONDARY,
                    expand=True,
                ),
                *trailing,
            ],
            spacing=SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        ink=True,
    )


def page_heading(title: str, *, subtitle: str | None = None) -> ft.Column:
    controls: list[ft.Control] = [
        ft.Text(title, size=FONT_SIZE_PAGE_TITLE, weight=ft.FontWeight.W_700, color=COLOR_TEXT_PRIMARY),
    ]
    if subtitle:
        controls.append(ft.Text(subtitle, size=FONT_SIZE_BODY, color=COLOR_TEXT_MUTED))
    return ft.Column(controls, spacing=SPACE_XS)


def section_heading(title: str, *, subtitle: str | None = None) -> ft.Column:
    controls: list[ft.Control] = [
        ft.Text(title, size=FONT_SIZE_SECTION_TITLE, weight=ft.FontWeight.W_700, color=COLOR_TEXT_PRIMARY),
    ]
    if subtitle:
        controls.append(ft.Text(subtitle, size=FONT_SIZE_CAPTION, color=COLOR_TEXT_MUTED))
    return ft.Column(controls, spacing=2)


def configuration_card(
    *,
    name: str,
    active: bool,
    matching_summary: str,
    filename_example: str,
    destination: str,
    on_edit: Callable | None = None,
    menu_items: list[ft.PopupMenuItem] | None = None,
) -> ft.Container:
    status = status_badge("Aktiv" if active else "Inaktiv", tone="success" if active else "muted")
    actions: list[ft.Control] = [secondary_button("Bearbeiten", on_click=on_edit)]
    if menu_items:
        actions.append(
            ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                items=menu_items,
            )
        )
    return ft.Container(
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(BORDER_WIDTH, COLOR_BORDER),
        border_radius=RADIUS_LG,
        padding=SPACE_MD,
        content=ft.Column(
            [
                ft.Row(
                    [ft.Text(name, size=FONT_SIZE_CARD_TITLE, weight=ft.FontWeight.W_700, expand=True), status],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text("Wenn:", size=FONT_SIZE_CAPTION, color=COLOR_TEXT_MUTED),
                ft.Text(matching_summary, size=FONT_SIZE_BODY, color=COLOR_TEXT_SECONDARY),
                ft.Text("Dateiname:", size=FONT_SIZE_CAPTION, color=COLOR_TEXT_MUTED),
                ft.Text(filename_example, size=FONT_SIZE_BODY, color=COLOR_TEXT_SECONDARY, selectable=True),
                ft.Text("Zielordner:", size=FONT_SIZE_CAPTION, color=COLOR_TEXT_MUTED),
                path_display(destination),
                ft.Row(actions, spacing=SPACE_SM),
            ],
            spacing=SPACE_XS,
        ),
    )


def form_field(
    label: str,
    *,
    value: str = "",
    hint: str | None = None,
    read_only: bool = False,
    on_change: Callable | None = None,
    expand: bool | int = False,
) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value,
        hint_text=hint,
        read_only=read_only,
        on_change=on_change,
        expand=expand,
        height=CONTROL_HEIGHT,
        text_size=FONT_SIZE_BODY,
        border_color=COLOR_BORDER,
        focused_border_color=COLOR_FOCUS,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
    )


def status_badge(label: str, *, tone: str = "muted") -> ft.Container:
    palette = {
        "success": (COLOR_SUCCESS_SOFT, COLOR_SUCCESS, COLOR_SUCCESS),
        "warning": (COLOR_WARNING_SOFT, COLOR_WARNING, COLOR_WARNING),
        "error": (COLOR_ERROR_SOFT, COLOR_ERROR, COLOR_ERROR),
        "muted": (COLOR_PAGE_BG, COLOR_BORDER, COLOR_TEXT_MUTED),
    }
    bg, border, text = palette.get(tone, palette["muted"])
    return ft.Container(
        content=ft.Text(label, size=FONT_SIZE_CAPTION, color=text, weight=ft.FontWeight.W_600),
        bgcolor=bg,
        border=ft.Border.all(BORDER_WIDTH, border),
        border_radius=RADIUS_MD,
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
    )


def empty_state(title: str, *, message: str, action: ft.Control | None = None) -> ft.Container:
    controls: list[ft.Control] = [
        ft.Text(title, size=FONT_SIZE_SECTION_TITLE, weight=ft.FontWeight.W_700),
        ft.Text(message, size=FONT_SIZE_BODY, color=COLOR_TEXT_MUTED),
    ]
    if action is not None:
        controls.append(action)
    return ft.Container(
        padding=SPACE_MD,
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(BORDER_WIDTH, COLOR_BORDER),
        border_radius=RADIUS_LG,
        content=ft.Column(controls, spacing=SPACE_SM),
    )


def editor_panel(title: str, content: ft.Control, *, actions: list[ft.Control] | None = None) -> ft.Container:
    footer: list[ft.Control] = []
    if actions:
        footer = [ft.Row(actions, alignment=ft.MainAxisAlignment.END, spacing=SPACE_SM)]
    return ft.Container(
        width=420,
        bgcolor=COLOR_SURFACE,
        border=ft.Border(left=ft.BorderSide(BORDER_WIDTH, COLOR_BORDER)),
        padding=SPACE_MD,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(title, size=FONT_SIZE_SECTION_TITLE, weight=ft.FontWeight.W_700, expand=True),
                    ]
                ),
                content,
                *footer,
            ],
            spacing=SPACE_MD,
            expand=True,
        ),
    )


def confirmation_dialog(title: str, message: str, *, on_confirm: Callable, on_cancel: Callable) -> ft.AlertDialog:
    return ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(message),
        actions=[
            secondary_button("Abbrechen", on_click=on_cancel),
            primary_button("Bestätigen", on_click=on_confirm),
        ],
    )


def profile_selector(
    profiles: list[tuple[str, str]],
    *,
    active_id: str,
    on_change: Callable | None = None,
) -> ft.Row:
    options = [ft.dropdown.Option(key=profile_id, text=label) for profile_id, label in profiles]
    dropdown = ft.Dropdown(
        label="Profil",
        value=active_id,
        options=options,
        expand=True,
        text_size=FONT_SIZE_BODY,
        border_color=COLOR_BORDER,
        focused_border_color=COLOR_FOCUS,
    )
    if on_change is not None:
        if hasattr(dropdown, "on_select"):
            dropdown.on_select = on_change
        else:
            dropdown.on_change = on_change
    return ft.Row([dropdown], vertical_alignment=ft.CrossAxisAlignment.CENTER)


def path_display(path: str, *, tooltip: str | None = None) -> ft.Text:
    return ft.Text(
        path or "Ordner noch auswählen",
        size=FONT_SIZE_BODY,
        color=COLOR_TEXT_SECONDARY if path else COLOR_DISABLED,
        tooltip=tooltip or path,
        selectable=True,
    )


def validation_message(message: str, *, is_error: bool = True) -> ft.Text:
    return ft.Text(
        message,
        size=FONT_SIZE_CAPTION,
        color=COLOR_ERROR if is_error else COLOR_TEXT_MUTED,
    )


def popup_menu_item(
    label: str,
    *,
    on_click: Callable | None = None,
    icon: str | None = None,
) -> ft.PopupMenuItem:
    """Flet 0.85+ PopupMenuItem (uses ``content``, not legacy ``text``)."""
    return ft.PopupMenuItem(content=label, icon=icon, on_click=on_click)


def page_error_state(
    title: str,
    message: str,
    *,
    on_retry: Callable | None = None,
) -> ft.Container:
    controls: list[ft.Control] = [
        ft.Text(title, size=FONT_SIZE_SECTION_TITLE, weight=ft.FontWeight.W_700, color=COLOR_TEXT_PRIMARY),
        ft.Text(message, size=FONT_SIZE_BODY, color=COLOR_TEXT_MUTED),
    ]
    if on_retry is not None:
        controls.append(secondary_button("Erneut versuchen", on_click=on_retry))
    return ft.Container(
        expand=True,
        padding=SPACE_MD,
        content=ft.Column(controls, spacing=SPACE_SM),
    )
