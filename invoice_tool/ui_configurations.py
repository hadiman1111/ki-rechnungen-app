"""Konfigurationen page with list and right-side editor drawer."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import flet as ft

from invoice_tool import app_paths
from invoice_tool.configuration_model import (
    Configuration,
    FilenamePattern,
    MatchingRule,
    ProfileBundle,
    UnmatchedConfiguration,
    copy_filename_pattern,
    default_filename_pattern,
    destination_display,
    matching_summary,
    new_configuration_id,
    preview_filename,
    validate_profile_bundle,
)
from invoice_tool.profile_store import load_profile_bundle, save_profile_bundle
from invoice_tool.scan_models import matching_features
from invoice_tool.ui_components import (
    configuration_card,
    form_field,
    page_error_state,
    page_heading,
    popup_menu_item,
    primary_button,
    profile_selector,
    secondary_button,
    section_heading,
    status_badge,
    validation_message,
)
from invoice_tool.ui_filename_builder import build_filename_builder_dialog
from invoice_tool.ui_theme import (
    COLOR_BORDER,
    COLOR_SURFACE,
    COLOR_TEXT_MUTED,
    PANEL_PADDING,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
)

logger = logging.getLogger(__name__)


def build_configurations_view(
    *,
    page: ft.Page,
    profile_id: str,
    on_profile_changed: Callable[[str], None],
    initial_config_id: str | None = None,
) -> ft.Container:
    try:
        return _build_configurations_view(
            page=page,
            profile_id=profile_id,
            on_profile_changed=on_profile_changed,
            initial_config_id=initial_config_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Konfigurationen konnten nicht geladen werden (Profil=%s)", profile_id)
        return page_error_state(
            "Konfigurationen konnten nicht geladen werden",
            "Die Einstellungen für dieses Profil konnten nicht angezeigt werden. "
            "Bitte erneut versuchen oder ein anderes Profil wählen.",
            on_retry=lambda _e: on_profile_changed(profile_id),
        )


def _build_configurations_view(
    *,
    page: ft.Page,
    profile_id: str,
    on_profile_changed: Callable[[str], None],
    initial_config_id: str | None = None,
) -> ft.Container:
    bundle = load_profile_bundle(profile_id)
    draft_config: Configuration | None = None
    draft_unmatched: UnmatchedConfiguration | None = None
    draft_is_new = False
    editor_host = ft.Container(visible=False)
    validation_label = ft.Text("", size=12)
    list_column = ft.Column(spacing=SPACE_MD, scroll=ft.ScrollMode.AUTO, expand=True)

    def _reload_bundle() -> ProfileBundle:
        nonlocal bundle
        bundle = load_profile_bundle(profile_id)
        return bundle

    def _profile_options() -> list[tuple[str, str]]:
        return [(entry_id, label) for entry_id, _, label in app_paths.list_profile_entries()]

    def _configuration_card_for(config: Configuration) -> ft.Control:
        try:
            return configuration_card(
                name=config.name,
                active=config.active,
                matching_summary=matching_summary(config, bundle.scan_model),
                filename_example=preview_filename(config.filename_pattern, bundle.scan_model),
                destination=destination_display(config.destination.get("path", "")),
                on_edit=lambda _e, cfg_id=config.id: _open_editor(cfg_id),
                menu_items=[
                    popup_menu_item(
                        "Duplizieren",
                        on_click=lambda _e, cfg_id=config.id: _duplicate(cfg_id),
                    ),
                    popup_menu_item(
                        "Deaktivieren" if config.active else "Aktivieren",
                        on_click=lambda _e, cfg_id=config.id: _toggle_active(cfg_id),
                    ),
                    popup_menu_item(
                        "Löschen",
                        on_click=lambda _e, cfg_id=config.id: _delete(cfg_id),
                    ),
                ],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Konfiguration %s konnte nicht dargestellt werden: %s", config.id, exc)
            return ft.Container(
                bgcolor=COLOR_SURFACE,
                border=ft.Border.all(1, COLOR_BORDER),
                border_radius=10,
                padding=SPACE_MD,
                content=ft.Column(
                    [
                        ft.Text(config.name or "Konfiguration", weight=ft.FontWeight.W_700),
                        validation_message(
                            "Diese Konfiguration konnte nicht vollständig angezeigt werden. "
                            "Bitte bearbeiten oder erneut speichern.",
                            is_error=True,
                        ),
                        secondary_button("Bearbeiten", on_click=lambda _e, cfg_id=config.id: _open_editor(cfg_id)),
                    ],
                    spacing=SPACE_SM,
                ),
            )

    def _render_list(*, refresh_page: bool = False) -> None:
        _reload_bundle()
        cards: list[ft.Control] = []
        for config in bundle.configurations:
            cards.append(_configuration_card_for(config))

        cards.append(
            ft.Container(
                border=ft.Border(top=ft.BorderSide(1, COLOR_BORDER)),
                padding=ft.Padding.only(top=SPACE_MD),
                content=ft.Column(
                    [
                        ft.Text("Nicht zugeordnete Dokumente", weight=ft.FontWeight.W_700),
                        ft.Text(
                            "Dokumente ohne eindeutige Zuordnung werden hier zur späteren Prüfung gesammelt.",
                            color=COLOR_TEXT_MUTED,
                        ),
                        ft.Text("Dateiname:", size=11),
                        ft.Text(
                            preview_filename(bundle.unmatched.filename_pattern, bundle.scan_model),
                            selectable=True,
                        ),
                        ft.Text("Zielordner:", size=11),
                        ft.Text(destination_display(bundle.unmatched.destination.get("path", ""))),
                        secondary_button("Bearbeiten", on_click=lambda _e: _open_unmatched_editor()),
                    ],
                    spacing=SPACE_SM,
                ),
            )
        )
        list_column.controls = cards
        if refresh_page:
            page.update()

    def _save_bundle(*, close_editor: bool = True) -> bool:
        errors = validate_profile_bundle(bundle)
        if errors:
            validation_label.value = errors[0]
            validation_label.color = ft.Colors.RED
            validation_label.update()
            return False
        save_profile_bundle(bundle)
        validation_label.value = "Konfiguration gespeichert."
        validation_label.color = ft.Colors.GREEN
        validation_label.update()
        _render_list()
        if close_editor:
            editor_host.visible = False
            editor_host.content = None
        page.update()
        return True

    async def _pick_folder(on_selected: Callable[[str], None]) -> None:
        path = await ft.FilePicker().get_directory_path(dialog_title="Ordner auswählen")
        if path:
            on_selected(path)

    def _open_editor(config_id: str | None = None) -> None:
        nonlocal draft_config, draft_unmatched, draft_is_new
        draft_unmatched = None
        if config_id:
            source = next((item for item in bundle.configurations if item.id == config_id), None)
            if source is None:
                return
            draft_config = Configuration.from_dict(source.to_dict())
            draft_is_new = False
        else:
            draft_config = Configuration(
                id=new_configuration_id(),
                name="Neue Konfiguration",
                active=True,
                matching=MatchingRule(
                    feature_key=matching_features(bundle.scan_model)[0].key
                    if matching_features(bundle.scan_model)
                    else "payment_field",
                    values=[""],
                ),
                filename_pattern=default_filename_pattern(bundle.scan_model),
                destination={"type": "local_folder", "path": ""},
            )
            draft_is_new = True

        name_field = form_field(
            "Name",
            value=draft_config.name,
            on_change=lambda e: _set_name(e.control.value or ""),
        )
        active_switch = ft.Switch(label="Diese Konfiguration verwenden", value=draft_config.active)
        feature_dd = ft.Dropdown(
            label="Merkmal",
            value=draft_config.matching.feature_key if draft_config.matching else "",
            options=[
                ft.dropdown.Option(feature.key, feature.label) for feature in matching_features(bundle.scan_model)
            ],
        )
        operator_dd = ft.Dropdown(label="Bedingung", value="ist", options=[ft.dropdown.Option("ist", "ist")])
        value_field = form_field(
            "Wert",
            value=", ".join(draft_config.matching.values) if draft_config.matching else "",
        )
        filename_preview = ft.Text(preview_filename(draft_config.filename_pattern, bundle.scan_model), selectable=True)
        destination_text = ft.Text(destination_display(draft_config.destination.get("path", "")))

        def _set_name(value: str) -> None:
            if draft_config:
                draft_config.name = value

        def _open_pattern_builder(_event: ft.ControlEvent) -> None:
            if not draft_config:
                return

            def _apply(pattern: FilenamePattern) -> None:
                draft_config.filename_pattern = pattern
                filename_preview.value = preview_filename(pattern, bundle.scan_model)
                filename_preview.update()

            dialog = build_filename_builder_dialog(
                page=page,
                scan_model=bundle.scan_model,
                initial_pattern=draft_config.filename_pattern,
                on_done=_apply,
                on_cancel=lambda: None,
            )
            page.open(dialog)

        async def _choose_folder(_event: ft.ControlEvent) -> None:
            if not draft_config:
                return

            def _apply(path: str) -> None:
                draft_config.destination = {"type": "local_folder", "path": path}
                destination_text.value = destination_display(path)
                destination_text.update()

            await _pick_folder(_apply)

        def _cancel(_event: ft.ControlEvent) -> None:
            nonlocal draft_config, draft_unmatched, draft_is_new
            draft_config = None
            draft_unmatched = None
            draft_is_new = False
            _reload_bundle()
            editor_host.visible = False
            editor_host.content = None
            _render_list()
            page.update()

        def _save_draft(_event: ft.ControlEvent) -> None:
            nonlocal draft_config, draft_is_new
            if not draft_config:
                return
            draft_config.active = active_switch.value
            values = [part.strip() for part in (value_field.value or "").split(",") if part.strip()]
            draft_config.matching = MatchingRule(
                feature_key=feature_dd.value or draft_config.matching.feature_key,
                operator=operator_dd.value or "ist",
                values=values,
            )
            existing = {item.id: item for item in bundle.configurations}
            existing[draft_config.id] = draft_config
            bundle.configurations = list(existing.values())
            if _save_bundle():
                draft_config = None
                draft_is_new = False

        editor_host.content = ft.Container(
            width=420,
            bgcolor=COLOR_SURFACE,
            border=ft.Border(left=ft.BorderSide(1, COLOR_BORDER)),
            padding=PANEL_PADDING,
            content=ft.Column(
                [
                    ft.Text(
                        "Neue Konfiguration" if draft_is_new else "Konfiguration bearbeiten",
                        size=18,
                        weight=ft.FontWeight.W_700,
                    ),
                    name_field,
                    active_switch,
                    section_heading("Welche Dokumente gehören dazu?"),
                    ft.Row([feature_dd, operator_dd, value_field], spacing=SPACE_SM),
                    section_heading("Wie sollen die Dateien heißen?"),
                    filename_preview,
                    secondary_button("Dateinamensmuster bearbeiten", on_click=_open_pattern_builder),
                    section_heading("Wo sollen die Dateien gespeichert werden?"),
                    destination_text,
                    secondary_button("Ordner auswählen", on_click=lambda e: page.run_task(_choose_folder, e)),
                    ft.Row(
                        [
                            secondary_button("Abbrechen", on_click=_cancel),
                            primary_button("Konfiguration speichern", on_click=_save_draft),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=SPACE_MD,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )
        editor_host.visible = True
        page.update()

    def _open_unmatched_editor() -> None:
        nonlocal draft_config, draft_unmatched, draft_is_new
        draft_config = None
        draft_is_new = False
        draft_unmatched = UnmatchedConfiguration.from_dict(bundle.unmatched.to_dict())
        unmatched_preview = ft.Text(
            preview_filename(draft_unmatched.filename_pattern, bundle.scan_model),
            selectable=True,
        )
        destination_text = ft.Text(destination_display(draft_unmatched.destination.get("path", "")))

        def _open_pattern_builder(_event: ft.ControlEvent) -> None:
            if draft_unmatched is None:
                return

            def _apply(pattern: FilenamePattern) -> None:
                draft_unmatched.filename_pattern = pattern
                unmatched_preview.value = preview_filename(pattern, bundle.scan_model)
                unmatched_preview.update()

            dialog = build_filename_builder_dialog(
                page=page,
                scan_model=bundle.scan_model,
                initial_pattern=draft_unmatched.filename_pattern,
                on_done=_apply,
                on_cancel=lambda: None,
            )
            page.open(dialog)

        async def _choose_folder(_event: ft.ControlEvent) -> None:
            if draft_unmatched is None:
                return

            def _apply(path: str) -> None:
                draft_unmatched.destination = {"type": "local_folder", "path": path}
                destination_text.value = destination_display(path)
                destination_text.update()

            await _pick_folder(_apply)

        def _cancel(_event: ft.ControlEvent) -> None:
            nonlocal draft_unmatched
            draft_unmatched = None
            editor_host.visible = False
            editor_host.content = None
            _reload_bundle()
            _render_list()
            page.update()

        def _save_unmatched(_event: ft.ControlEvent) -> None:
            nonlocal draft_unmatched
            if draft_unmatched is None:
                return
            bundle.unmatched = UnmatchedConfiguration.from_dict(draft_unmatched.to_dict())
            if _save_bundle():
                draft_unmatched = None

        editor_host.content = ft.Container(
            width=420,
            bgcolor=COLOR_SURFACE,
            border=ft.Border(left=ft.BorderSide(1, COLOR_BORDER)),
            padding=PANEL_PADDING,
            content=ft.Column(
                [
                    ft.Text("Nicht zugeordnete Dokumente", size=18, weight=ft.FontWeight.W_700),
                    unmatched_preview,
                    secondary_button("Dateinamensmuster bearbeiten", on_click=_open_pattern_builder),
                    destination_text,
                    secondary_button("Ordner auswählen", on_click=lambda e: page.run_task(_choose_folder, e)),
                    ft.Row(
                        [
                            secondary_button("Abbrechen", on_click=_cancel),
                            primary_button("Konfiguration speichern", on_click=_save_unmatched),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=SPACE_MD,
            ),
        )
        editor_host.visible = True
        page.update()

    def _duplicate(config_id: str) -> None:
        source = next((item for item in bundle.configurations if item.id == config_id), None)
        if not source:
            return
        clone = Configuration.from_dict(source.to_dict())
        clone.id = new_configuration_id()
        clone.name = f"{source.name} (Kopie)"
        clone.filename_pattern = copy_filename_pattern(source.filename_pattern)
        bundle.configurations.append(clone)
        _save_bundle(close_editor=False)

    def _toggle_active(config_id: str) -> None:
        for config in bundle.configurations:
            if config.id == config_id:
                config.active = not config.active
        _save_bundle(close_editor=False)

    def _delete(config_id: str) -> None:
        bundle.configurations = [item for item in bundle.configurations if item.id != config_id]
        _save_bundle(close_editor=False)

    def _on_profile_select(event: ft.ControlEvent) -> None:
        selected = event.control.value
        if selected:
            on_profile_changed(str(selected))

    active_count = sum(1 for item in bundle.configurations if item.active)
    header = ft.Column(
        [
            page_heading(
                "Konfigurationen",
                subtitle="Lege fest, welche Dokumente zusammengehören, wie sie benannt "
                "und in welchen Ordner sie gespeichert werden.",
            ),
            profile_selector(_profile_options(), active_id=profile_id, on_change=_on_profile_select),
            ft.Row(
                [
                    status_badge(f"{active_count} aktiv", tone="success" if active_count else "muted"),
                    ft.Container(expand=True),
                    primary_button("Konfiguration hinzufügen", on_click=lambda _e: _open_editor(None)),
                ]
            ),
            validation_label,
        ],
        spacing=SPACE_MD,
    )

    _render_list()
    if initial_config_id:
        _open_editor(initial_config_id)

    body = ft.Row(
        [
            ft.Container(expand=True, content=list_column),
            editor_host,
        ],
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    return ft.Container(
        expand=True,
        padding=PANEL_PADDING,
        content=ft.Column([header, body], spacing=SPACE_LG, expand=True),
    )
