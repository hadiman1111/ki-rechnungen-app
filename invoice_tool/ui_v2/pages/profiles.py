"""Profile management page — Make reference port."""

from __future__ import annotations

from typing import Callable

import flet as ft

from invoice_tool.app_paths import resolve_active_profile_id
from invoice_tool.profile_store import load_profile_bundle
from invoice_tool.scan_models import list_scan_models
from invoice_tool.ui_v2.adapters.profile_write_adapter import (
    activate_profile,
    can_delete_profile,
    create_profile,
    delete_profile,
    duplicate_profile,
    save_profile_changes,
)
from invoice_tool.ui_v2.components import (
    compact_list_item,
    divider,
    empty_state,
    form_field_group,
    inline_warning,
    kpi_strip,
    list_detail_split,
    list_panel,
    make_create_list_marker,
    make_metadata_block,
    make_metadata_row,
    make_panel_close_button,
    make_panel_footer_end,
    make_panel_footer_profile,
    make_split_detail_panel,
    page_header,
    page_scaffold,
    status_badge,
)
from invoice_tool.ui_v2.draft_models import ProfileDraftVM
from invoice_tool.ui_v2.edit_components import (
    action_button,
    compact_input_shell,
    confirmation_dialog,
    feedback_banner,
    form_field,
    helper_text,
    outlined_field_kwargs,
    unsaved_changes_dialog,
)
from invoice_tool.ui_v2.saas_profile_surface import (
    SAAS_SURFACE_UI_LABELS,
    blank_profile_draft,
    build_saas_profile_surface_vm,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.theme import SPACE_SM
from invoice_tool.ui_v2.validation import validate_profile_name, validate_scan_model_id
from invoice_tool.ui_v2.view_models import ProfileDetailVM, ProfileSummaryVM, UiV2ReadOnlySnapshot


def _snapshot(state: UiV2State) -> UiV2ReadOnlySnapshot | None:
    snap = state.snapshot
    return snap if isinstance(snap, UiV2ReadOnlySnapshot) else None


def _selected_profile_id(state: UiV2State, profile: ProfileDetailVM) -> str | None:
    if state.profile_list_selected_id:
        return state.profile_list_selected_id
    if profile.profiles:
        return profile.profiles[0].profile_id
    return None


def _profile_detail_for(state: UiV2State, profile: ProfileDetailVM, profile_id: str) -> ProfileSummaryVM | None:
    for entry in profile.profiles:
        if entry.profile_id == profile_id:
            return entry
    return None


def build_profiles_page(state: UiV2State) -> ft.Control:
    snapshot = _snapshot(state)
    if snapshot is None:
        return page_scaffold(
            page_header(
                "Profile",
                subtitle="Erkennungsprofile und ihre Konfigurationen verwalten.",
            ),
            inline_warning("Profilinformationen vorübergehend nicht verfügbar."),
        )

    profile = snapshot.profile
    active_id = resolve_active_profile_id()
    selected_id = _selected_profile_id(state, profile)
    is_editing = state.profile_edit_mode in ("create", "edit") and state.profile_draft is not None
    is_creating = state.profile_edit_mode == "create" and is_editing

    def _refresh() -> None:
        if state.refresh:
            state.refresh()

    def _set_feedback(message: str, *, is_error: bool = False) -> None:
        state.profile_feedback = message
        state.profile_feedback_error = is_error

    def _confirm_discard(on_discard: Callable[[], None]) -> None:
        def _discard() -> None:
            state.discard_profile_edit()
            if state.close_dialog:
                state.close_dialog()
            on_discard()

        def _continue() -> None:
            if state.close_dialog:
                state.close_dialog()

        if state.open_dialog:
            state.open_dialog(unsaved_changes_dialog(on_discard=_discard, on_continue=_continue))

    def _select_profile(profile_id: str) -> None:
        if state.has_unsaved_profile_changes():
            _confirm_discard(lambda: _apply_select(profile_id))
            return
        _apply_select(profile_id)

    def _apply_select(profile_id: str) -> None:
        state.profile_list_selected_id = profile_id
        state.discard_profile_edit()
        _set_feedback("")
        _refresh()

    def _start_create() -> None:
        if state.has_unsaved_profile_changes():
            _confirm_discard(_apply_start_create)
            return
        _apply_start_create()

    def _apply_start_create() -> None:
        state.profile_edit_mode = "create"
        # Create defaults from generic SaaS model (no private tenant prefill).
        state.profile_draft = blank_profile_draft()
        state.profile_list_selected_id = None
        state.profile_field_errors = {}
        _set_feedback("")
        _refresh()

    def _start_edit(profile_id: str) -> None:
        if state.has_unsaved_profile_changes():
            _confirm_discard(lambda: _apply_start_edit(profile_id))
            return
        _apply_start_edit(profile_id)

    def _apply_start_edit(profile_id: str) -> None:
        try:
            bundle = load_profile_bundle(profile_id)
        except Exception:
            _set_feedback("Profil konnte nicht geladen werden.", is_error=True)
            _refresh()
            return
        state.profile_edit_mode = "edit"
        state.profile_draft = ProfileDraftVM(
            profile_id=profile_id,
            name=bundle.name,
            scan_model_id=bundle.scan_model_id,
            is_new=False,
        )
        state.profile_list_selected_id = profile_id
        state.profile_field_errors = {}
        _set_feedback("")
        _refresh()

    def _cancel_edit(_event: ft.ControlEvent | None = None) -> None:
        state.discard_profile_edit()
        state.profile_field_errors = {}
        _set_feedback("Änderungen verworfen.")
        _refresh()

    def _save_profile(_event: ft.ControlEvent) -> None:
        draft = state.profile_draft
        if draft is None:
            return
        errors: dict[str, str] = {}
        name_issues = validate_profile_name(
            draft.name,
            exclude_profile_id=None if draft.is_new else draft.profile_id,
        )
        model_issues = validate_scan_model_id(draft.scan_model_id)
        if name_issues:
            errors["name"] = name_issues[0]
        if model_issues:
            errors["scan_model_id"] = model_issues[0]
        if errors:
            state.profile_field_errors = errors
            _set_feedback("")
            _refresh()
            return
        state.profile_field_errors = {}
        if state.profile_edit_mode == "create":
            result = create_profile(name=draft.name, scan_model_id=draft.scan_model_id)
        elif draft.profile_id:
            result = save_profile_changes(draft.profile_id, name=draft.name, scan_model_id=draft.scan_model_id)
        else:
            _set_feedback("Speichern nicht möglich.", is_error=True)
            _refresh()
            return
        if not result.success:
            _set_feedback(result.message, is_error=True)
            _refresh()
            return
        state.discard_profile_edit()
        if result.profile_id:
            state.profile_list_selected_id = result.profile_id
        _set_feedback(result.message)
        _refresh()

    def _activate(profile_id: str) -> None:
        if profile_id == active_id:
            return
        result = activate_profile(profile_id)
        if not result.success:
            _set_feedback(result.message, is_error=True)
        else:
            state.profile_list_selected_id = profile_id
            _set_feedback(result.message)
        _refresh()

    def _duplicate(profile_id: str) -> None:
        result = duplicate_profile(profile_id)
        if not result.success:
            _set_feedback(result.message, is_error=True)
        else:
            if result.profile_id:
                state.profile_list_selected_id = result.profile_id
            _set_feedback(result.message)
        _refresh()

    def _request_delete(profile_id: str) -> None:
        allowed, reason = can_delete_profile(profile_id)
        if not allowed:
            _set_feedback(reason, is_error=True)
            _refresh()
            return
        entry = _profile_detail_for(state, profile, profile_id)
        name = entry.profile_name if entry else profile_id
        if state.open_dialog:
            state.open_dialog(
                confirmation_dialog(
                    title="Profil löschen?",
                    message=(
                        f'„{name}" wird dauerhaft gelöscht. Alle zugehörigen Konfigurationen bleiben erhalten, '
                        "sind aber keinem Profil mehr zugeordnet."
                    ),
                    confirm_label="Profil löschen",
                    on_confirm=lambda: _confirm_delete(profile_id),
                    on_cancel=lambda: state.close_dialog() if state.close_dialog else None,
                )
            )

    def _confirm_delete(profile_id: str) -> None:
        if state.close_dialog:
            state.close_dialog()
        result = delete_profile(profile_id)
        if not result.success:
            _set_feedback(result.message, is_error=True)
        else:
            state.profile_list_selected_id = resolve_active_profile_id()
            state.discard_profile_edit()
            _set_feedback(result.message)
        _refresh()

    items: list[ft.Control] = [
        page_header(
            "Profile",
            subtitle="Erkennungsprofile und ihre Konfigurationen verwalten.",
            trailing=action_button(
                SAAS_SURFACE_UI_LABELS["new_profile"],
                on_click=lambda _e: _start_create(),
                primary=True,
            ),
        ),
    ]

    if state.profile_feedback:
        items.append(feedback_banner(state.profile_feedback, is_error=state.profile_feedback_error))

    items.append(
        kpi_strip(
            ("Profile", str(len(profile.profiles)), False),
            ("Aktives Profil", snapshot.profile.profile_name, False),
            ("Konfigurationen", str(profile.configuration_count), False),
            ("Aktive Regeln", str(profile.active_configuration_count), False),
        )
    )

    profile_rows: list[ft.Control] = []
    for index, entry in enumerate(profile.profiles):
        if index > 0:
            profile_rows.append(divider())
        is_selected = entry.profile_id == selected_id and not is_editing
        tone = "active" if entry.is_active else "inactive"
        status_label = "Aktiv" if entry.is_active else "Inaktiv"
        profile_rows.append(
            compact_list_item(
                entry.profile_name,
                trailing=status_badge(status_label, tone=tone),
                selected=is_selected,
                on_select=lambda _e, pid=entry.profile_id: _select_profile(pid),
            )
        )
    if is_creating:
        if profile_rows:
            profile_rows.append(divider())
        profile_rows.append(make_create_list_marker(SAAS_SURFACE_UI_LABELS["new_profile"]))

    if profile_rows:
        list_body = ft.Column(profile_rows, spacing=0, scroll=ft.ScrollMode.AUTO)
    else:
        list_body = ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=empty_state(
                "Keine Profile vorhanden",
                detail=f'Legen Sie mit „{SAAS_SURFACE_UI_LABELS["new_profile"]}“ ein erstes Profil an.',
            ),
        )

    field_errors = state.profile_field_errors or {}
    detail_title = "Profildetails"
    header_trailing: ft.Control | None = None
    detail_body: ft.Control
    footer: ft.Control | None = None
    saas_surface = build_saas_profile_surface_vm()

    if is_editing and state.profile_draft is not None:
        draft = state.profile_draft
        detail_title = (
            SAAS_SURFACE_UI_LABELS["new_profile"]
            if state.profile_edit_mode == "create"
            else f"Bearbeiten: {draft.name or 'Profil'}"
        )
        header_trailing = make_panel_close_button(_cancel_edit)

        name_field = form_field("Profilname", value=draft.name)
        model_dd = ft.Dropdown(
            value=draft.scan_model_id or None,
            options=[ft.dropdown.Option(model.id, model.label) for model in list_scan_models()],
            hint_text=f"— {SAAS_SURFACE_UI_LABELS['scan_model']} —",
            **outlined_field_kwargs(),
        )

        def _update_draft(_event: ft.ControlEvent | None = None) -> None:
            draft.name = (name_field.value or "").strip()
            draft.scan_model_id = (model_dd.value or "").strip()
            state.profile_field_errors = {}

        name_field.on_change = _update_draft
        model_dd.on_change = _update_draft

        editor_fields: list[ft.Control] = [
            form_field_group("Profilname", compact_input_shell(name_field), error=field_errors.get("name")),
            form_field_group(
                SAAS_SURFACE_UI_LABELS["scan_model"],
                compact_input_shell(model_dd),
                error=field_errors.get("scan_model_id"),
            ),
            helper_text("Bestimmt, welche KI-Modellkonfiguration zur Dokumenterkennung verwendet wird."),
            make_metadata_block(
                make_metadata_row(SAAS_SURFACE_UI_LABELS["document_type"], saas_surface.document_type),
                make_metadata_row(
                    SAAS_SURFACE_UI_LABELS["matching_conditions"],
                    saas_surface.matching_conditions_summary,
                ),
                make_metadata_row(
                    SAAS_SURFACE_UI_LABELS["destination"],
                    (
                        " / ".join(
                            part
                            for part in (
                                saas_surface.destination_category,
                                saas_surface.destination_folder,
                            )
                            if part
                        )
                        or "—"
                    ),
                ),
                make_metadata_row(
                    SAAS_SURFACE_UI_LABELS["filename_pattern"],
                    saas_surface.filename_pattern,
                ),
                make_metadata_row(SAAS_SURFACE_UI_LABELS["review_rule"], saas_surface.review_rule),
                make_metadata_row(
                    SAAS_SURFACE_UI_LABELS["payment_hint"],
                    saas_surface.payment_hint or "—",
                ),
            ),
            helper_text(
                "Weitere Felder folgen dem generischen SaaS-Profilmodell; "
                "keine privaten Vorbelegungen. Verarbeitung wird hier nicht gestartet."
            ),
        ]
        save_label = "Erstellen" if state.profile_edit_mode == "create" else "Speichern"
        footer = make_panel_footer_end(
            action_button("Abbrechen", on_click=_cancel_edit),
            action_button(save_label, on_click=_save_profile, primary=True),
        )
        detail_body = ft.Column(editor_fields, spacing=SPACE_SM, tight=True)

    elif selected_id and (selected_entry := _profile_detail_for(state, profile, selected_id)) is not None:
        try:
            bundle = load_profile_bundle(selected_id)
            config_count = len(bundle.configurations)
            active_count = sum(1 for item in bundle.configurations if item.active)
            unmatched_path = str((bundle.unmatched.destination or {}).get("path") or "").strip()
            unmatched_label = "eingerichtet" if unmatched_path else "nicht eingerichtet"
        except Exception:
            config_count = profile.configuration_count
            active_count = profile.active_configuration_count
            unmatched_label = "—"

        detail_title = selected_entry.profile_name
        header_trailing = status_badge("Aktiv" if selected_entry.is_active else "Inaktiv", tone="active" if selected_entry.is_active else "inactive")

        detail_body = make_metadata_block(
            make_metadata_row("Profil", selected_entry.profile_name),
            make_metadata_row("Erkennungsmodell", selected_entry.scan_model_name),
            make_metadata_row("Konfigurationen gesamt", str(config_count)),
            make_metadata_row("Aktive Konfigurationen", str(active_count)),
            make_metadata_row("Nicht zugeordnete Dokumente", unmatched_label),
        )

        primary_action = None
        if selected_id != active_id:
            primary_action = action_button(
                "Als aktives Profil setzen",
                on_click=lambda _e, pid=selected_id: _activate(pid),
                primary=True,
            )

        footer = make_panel_footer_profile(
            action_button("Bearbeiten", on_click=lambda _e, pid=selected_id: _start_edit(pid)),
            action_button("Duplizieren", on_click=lambda _e, pid=selected_id: _duplicate(pid)),
            primary=primary_action,
            destructive=action_button(
                "Profil löschen",
                on_click=lambda _e, pid=selected_id: _request_delete(pid),
                destructive=True,
            ),
        )
    else:
        detail_body = ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=empty_state("Profil auswählen", detail="Wählen Sie links ein Profil, um Details anzuzeigen."),
        )

    edit_body_padding = ft.Padding.only(left=18, right=18, top=16, bottom=12)
    view_body_padding = ft.Padding.only(left=18, right=18, top=2, bottom=0)

    detail_panel_ctrl = make_split_detail_panel(
        detail_title,
        detail_body,
        header_trailing=header_trailing,
        footer=footer,
        scroll_body=False,
        body_padding=edit_body_padding if is_editing else view_body_padding,
    )

    items.append(list_detail_split(list_panel("Profile", list_body, expand=True), detail_panel_ctrl, expand=True))

    for warning in profile.warnings:
        items.append(inline_warning(warning))

    return page_scaffold(*items, expand_last=True)
