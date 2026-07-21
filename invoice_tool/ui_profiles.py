"""Profile management page."""

from __future__ import annotations

import logging
from typing import Callable

import flet as ft

from invoice_tool import app_paths
from invoice_tool.app_paths import sanitize_profile_display_name
from invoice_tool.profile_store import (
    create_profile_bundle,
    delete_profile_bundle,
    duplicate_profile_bundle,
    load_profile_bundle,
    save_profile_bundle,
)
from invoice_tool.scan_models import list_scan_models
from invoice_tool.ui_components import (
    confirmation_dialog,
    destructive_button,
    form_field,
    page_heading,
    primary_button,
    secondary_button,
    status_badge,
)
from invoice_tool.ui_theme import COLOR_BORDER, COLOR_SURFACE, PANEL_PADDING, SPACE_MD, SPACE_SM

logger = logging.getLogger(__name__)


def build_profiles_view(
    *,
    page: ft.Page,
    profile_id: str,
    on_open_configurations: Callable[[], None],
    on_profiles_changed: Callable[[], None] | None = None,
) -> ft.Container:
    selected_id: list[str] = [profile_id]
    profile_list = ft.Column(spacing=SPACE_MD, expand=True)
    editor_host = ft.Container(visible=False, expand=True)

    def _notify_changed() -> None:
        if on_profiles_changed is not None:
            on_profiles_changed()

    def _render_list() -> None:
        entries = app_paths.list_profile_entries()
        cards: list[ft.Control] = []
        for entry_id, _path, label in entries:
            item = load_profile_bundle(entry_id)
            is_selected = entry_id == selected_id[0]
            cards.append(
                ft.Container(
                    padding=SPACE_MD,
                    bgcolor=COLOR_SURFACE if is_selected else None,
                    border=ft.Border.all(2 if is_selected else 1, COLOR_BORDER),
                    border_radius=10,
                    on_click=lambda _e, pid=entry_id: _select_profile(pid),
                    ink=True,
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(sanitize_profile_display_name(label), size=16, weight=ft.FontWeight.W_700, expand=True),
                                    status_badge(
                                        "Ausgewählt" if is_selected else "Profil",
                                        tone="success" if is_selected else "muted",
                                    ),
                                ]
                            ),
                            ft.Text(f"Erkennungsmodell: {item.scan_model.label}", size=12),
                            ft.Text(f"{len(item.configurations)} Konfigurationen", size=12),
                        ],
                        spacing=SPACE_SM,
                    ),
                )
            )
        profile_list.controls = cards

    def _select_profile(entry_id: str) -> None:
        selected_id[0] = entry_id
        _render_list()
        _open_editor(entry_id)
        page.update()

    def _close_editor() -> None:
        editor_host.visible = False
        editor_host.content = None

    def _open_editor(entry_id: str) -> None:
        selected_id[0] = entry_id
        item = load_profile_bundle(entry_id)
        name_field = form_field("Name", value=sanitize_profile_display_name(item.name))
        model_dd = ft.Dropdown(
            label="Erkennungsmodell",
            value=item.scan_model_id,
            options=[ft.dropdown.Option(model.id, model.label) for model in list_scan_models()],
        )
        features = ft.Text(
            "Dieses Modell erkennt: "
            + ", ".join(feature.label for feature in item.scan_model.features),
            size=12,
        )

        def _save(_event: ft.ControlEvent) -> None:
            item.name = name_field.value or item.name
            item.scan_model_id = model_dd.value or item.scan_model_id
            save_profile_bundle(item)
            _render_list()
            _notify_changed()
            page.update()

        def _confirm_delete(_event: ft.ControlEvent) -> None:
            def _do_delete(_confirm_event: ft.ControlEvent) -> None:
                page.close(dialog)
                try:
                    delete_profile_bundle(entry_id)
                except ValueError as exc:
                    page.open(ft.SnackBar(ft.Text(str(exc))))
                    page.update()
                    return
                _close_editor()
                remaining = app_paths.list_profile_entries()
                if remaining:
                    selected_id[0] = remaining[0][0]
                _render_list()
                _notify_changed()
                page.update()

            def _cancel_delete(_cancel_event: ft.ControlEvent) -> None:
                page.close(dialog)

            dialog = confirmation_dialog(
                "Profil löschen",
                f"Möchtest du das Profil „{item.name}“ wirklich löschen? "
                "Konfigurierte Zielordner bleiben unverändert.",
                on_confirm=_do_delete,
                on_cancel=_cancel_delete,
            )
            page.open(dialog)

        editor_host.content = ft.Container(
            width=480,
            bgcolor=COLOR_SURFACE,
            border=ft.Border(left=ft.BorderSide(1, COLOR_BORDER)),
            padding=PANEL_PADDING,
            content=ft.Column(
                [
                    ft.Text("Profil bearbeiten", size=18, weight=ft.FontWeight.W_700),
                    name_field,
                    model_dd,
                    features,
                    ft.Row(
                        [
                            primary_button("Speichern", on_click=_save),
                            destructive_button("Profil löschen", on_click=_confirm_delete),
                        ],
                        spacing=SPACE_SM,
                    ),
                ],
                spacing=SPACE_MD,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )
        editor_host.visible = True

    def _create_profile(_event: ft.ControlEvent) -> None:
        try:
            created = create_profile_bundle(name="Neues Profil")
        except Exception:  # noqa: BLE001
            logger.exception("Profil konnte nicht erstellt werden")
            page.open(ft.SnackBar(ft.Text("Profil konnte nicht erstellt werden.")))
            page.update()
            return
        selected_id[0] = created.id
        _render_list()
        _open_editor(created.id)
        _notify_changed()
        page.update()

    def _duplicate_selected(_event: ft.ControlEvent) -> None:
        try:
            created = duplicate_profile_bundle(selected_id[0])
        except Exception:  # noqa: BLE001
            logger.exception("Profil konnte nicht dupliziert werden")
            page.open(ft.SnackBar(ft.Text("Profil konnte nicht dupliziert werden.")))
            page.update()
            return
        selected_id[0] = created.id
        _render_list()
        _open_editor(created.id)
        _notify_changed()
        page.update()

    _render_list()
    if selected_id[0]:
        _open_editor(selected_id[0])

    return ft.Container(
        expand=True,
        padding=PANEL_PADDING,
        content=ft.Column(
            [
                page_heading(
                    "Profile",
                    subtitle="Profile bündeln zusammengehörige Dokumentarten und ihre Konfigurationen.",
                ),
                ft.Row(
                    [
                        primary_button("Neues Profil", on_click=_create_profile),
                        secondary_button("Profil duplizieren", on_click=_duplicate_selected),
                        secondary_button("Konfigurationen öffnen", on_click=lambda _e: on_open_configurations()),
                    ],
                    spacing=SPACE_SM,
                    wrap=True,
                ),
                ft.Row(
                    [
                        ft.Container(expand=2, content=profile_list),
                        editor_host,
                    ],
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            ],
            spacing=SPACE_MD,
            expand=True,
        ),
    )
