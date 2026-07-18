"""Konfigurationen page — Make reference port (docs/design/make-reference/src/app/App.tsx)."""

from __future__ import annotations

from typing import Callable

import flet as ft

from invoice_tool.app_paths import resolve_active_profile_id
from invoice_tool.configuration_model import copy_filename_pattern, pattern_to_template
from invoice_tool.profile_store import load_profile_bundle
from invoice_tool.ui_v2.adapters.configuration_write_adapter import (
    delete_configuration,
    new_configuration_draft,
    reorder_configurations,
    set_configuration_active,
    update_configuration,
    update_unmatched_configuration,
)
from invoice_tool.ui_v2.adapters.folder_picker_adapter import choose_target_folder
from invoice_tool.ui_v2.components import (
    compact_list_item,
    display_path_value,
    divider,
    empty_state,
    form_field_group,
    inline_warning,
    kpi_strip,
    list_detail_split,
    list_panel,
    make_accent_cta_button,
    make_create_list_marker,
    make_form_status_toggle,
    make_matching_rule_display,
    make_metadata_block,
    make_metadata_row,
    make_panel_close_button,
    make_panel_footer_end,
    make_panel_footer_start,
    make_split_detail_panel,
    make_status_toggle_pill,
    page_header,
    page_scaffold,
    resolve_list_detail_height,
    secondary_button,
    status_badge,
)
from invoice_tool.ui_v2.config_edit_components import build_folder_picker_field, build_rule_builder_field
from invoice_tool.ui_v2.display_format import user_matching_summary_from_text
from invoice_tool.ui_v2.draft_models import ConfigurationDraftVM
from invoice_tool.ui_v2.edit_components import (
    action_button,
    confirmation_dialog,
    feedback_banner,
    form_field,
    full_width_field,
    helper_text,
    unsaved_changes_dialog,
)
from invoice_tool.ui_v2.filename_editor import build_filename_pattern_editor
from invoice_tool.ui_v2.saas_profile_surface import (
    GENERIC_CONFIG_NAME_HINT,
    SAAS_SURFACE_UI_LABELS,
    blank_configuration_create_defaults,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.validation import validate_configuration_draft, validate_unmatched_draft
from invoice_tool.ui_v2.view_models import ConfigurationSummaryVM, UiV2ReadOnlySnapshot


def _snapshot(state: UiV2State) -> UiV2ReadOnlySnapshot | None:
    snap = state.snapshot
    return snap if isinstance(snap, UiV2ReadOnlySnapshot) else None


def _default_selected_id(state: UiV2State, page_vm) -> str | None:
    if state.config_list_selected_id:
        return state.config_list_selected_id
    if page_vm.configurations:
        return page_vm.configurations[0].configuration_id
    if page_vm.unmatched is not None:
        return "unmatched"
    return None


def _find_config(page_vm, config_id: str | None) -> ConfigurationSummaryVM | None:
    if not config_id:
        return None
    if config_id == "unmatched":
        return page_vm.unmatched
    for config in page_vm.configurations:
        if config.configuration_id == config_id:
            return config
    return None


def _is_unmatched_config(config: ConfigurationSummaryVM) -> bool:
    return config.configuration_id == "unmatched"


def build_configurations_page(state: UiV2State) -> ft.Control:
    snapshot = _snapshot(state)
    if snapshot is None:
        return page_scaffold(
            page_header(
                "Konfigurationen",
                subtitle="Lege fest, welche Dokumente zusammengehören, wie sie benannt und in welchen Ordner sie gespeichert werden.",
            ),
            inline_warning("Konfigurationsdaten vorübergehend nicht verfügbar."),
        )

    page_vm = snapshot.configurations
    profile_id = resolve_active_profile_id()
    selected_id = _default_selected_id(state, page_vm)
    selected_config = _find_config(page_vm, selected_id)
    is_editing = state.config_edit_mode in ("create", "edit", "unmatched") and state.config_draft is not None
    is_creating = state.config_edit_mode == "create" and is_editing

    def _refresh() -> None:
        if state.refresh:
            state.refresh()

    def _set_feedback(message: str, *, is_error: bool = False) -> None:
        state.config_feedback = message
        state.config_feedback_error = is_error

    def _confirm_discard(on_discard: Callable[[], None]) -> None:
        def _discard() -> None:
            state.discard_config_edit()
            if state.close_dialog:
                state.close_dialog()
            on_discard()

        def _continue() -> None:
            if state.close_dialog:
                state.close_dialog()

        if state.open_dialog:
            state.open_dialog(unsaved_changes_dialog(on_discard=_discard, on_continue=_continue))

    def _select_config(config_id: str) -> None:
        if state.has_unsaved_config_changes():
            _confirm_discard(lambda: _apply_select(config_id))
            return
        _apply_select(config_id)

    def _apply_select(config_id: str) -> None:
        state.config_list_selected_id = config_id
        state.discard_config_edit()
        _set_feedback("")
        _refresh()

    def _start_create() -> None:
        if state.has_unsaved_config_changes():
            _confirm_discard(_apply_start_create)
            return
        _apply_start_create()

    def _apply_start_create() -> None:
        state.config_edit_mode = "create"
        draft = new_configuration_draft(profile_id)
        # Overlay generic SaaS create defaults (empty name/target; no private prefill).
        saas_defaults = blank_configuration_create_defaults()
        draft.name = saas_defaults.name
        draft.destination_path = saas_defaults.destination_folder
        state.config_draft = draft
        saas_draft = state.saas_draft_store.begin_blank_configuration(
            document_type=saas_defaults.document_type
        )
        saas_draft.filename_pattern = saas_defaults.filename_pattern
        state.config_list_selected_id = None
        state.config_field_errors = {}
        _set_feedback("")
        _refresh()

    def _start_edit(config_id: str, *, is_unmatched: bool = False) -> None:
        if state.has_unsaved_config_changes():
            _confirm_discard(lambda: _apply_start_edit(config_id, is_unmatched=is_unmatched))
            return
        _apply_start_edit(config_id, is_unmatched=is_unmatched)

    def _apply_start_edit(config_id: str, *, is_unmatched: bool = False) -> None:
        try:
            bundle = load_profile_bundle(profile_id)
        except Exception:
            _set_feedback("Profil konnte nicht geladen werden.", is_error=True)
            _refresh()
            return
        if is_unmatched:
            state.config_edit_mode = "unmatched"
            state.config_draft = ConfigurationDraftVM.from_unmatched(bundle.unmatched)
        else:
            source = next((item for item in bundle.configurations if item.id == config_id), None)
            if source is None:
                _set_feedback("Konfiguration nicht gefunden.", is_error=True)
                _refresh()
                return
            state.config_edit_mode = "edit"
            state.config_draft = ConfigurationDraftVM.from_configuration(
                source,
                sort_index=next(i for i, c in enumerate(bundle.configurations) if c.id == config_id),
            )
        state.config_list_selected_id = config_id
        state.config_field_errors = {}
        _set_feedback("")
        _refresh()

    def _cancel_edit(_event: ft.ControlEvent | None = None) -> None:
        state.discard_config_edit()
        state.config_field_errors = {}
        _set_feedback("Änderungen verworfen.")
        _refresh()

    def _validate_draft_fields(draft: ConfigurationDraftVM) -> dict[str, str]:
        try:
            bundle = load_profile_bundle(profile_id)
        except Exception:
            return {"_form": "Profil konnte nicht geladen werden."}
        if draft.is_unmatched or state.config_edit_mode == "unmatched":
            issues = validate_unmatched_draft(draft.to_unmatched(), bundle.scan_model)
        else:
            issues = validate_configuration_draft(draft.to_configuration(), bundle, is_unmatched=False)
        errors: dict[str, str] = {}
        for issue in issues:
            lowered = issue.lower()
            if "name" in lowered and "konfiguration" in lowered:
                errors.setdefault("name", issue)
            elif "zuordnung" in lowered or "wert" in lowered or "feld" in lowered:
                errors.setdefault("matching", issue)
            elif "dateiname" in lowered or "muster" in lowered:
                errors.setdefault("filename_pattern", issue)
            elif "zielordner" in lowered:
                errors.setdefault("destination_path", issue)
            elif "erkennungsmodell" in lowered:
                errors.setdefault("scan_model_id", issue)
            else:
                errors.setdefault("_form", issue)
        return errors

    def _save_config(_event: ft.ControlEvent) -> None:
        draft = state.config_draft
        if draft is None:
            return
        errors = _validate_draft_fields(draft)
        if errors:
            state.config_field_errors = errors
            _set_feedback("")
            _refresh()
            return
        state.config_field_errors = {}
        if draft.is_unmatched or state.config_edit_mode == "unmatched":
            result = update_unmatched_configuration(profile_id, draft)
        else:
            result = update_configuration(profile_id, draft)
        if not result.success:
            _set_feedback(result.message, is_error=True)
            _refresh()
            return
        state.discard_config_edit()
        if result.configuration_id:
            state.config_list_selected_id = result.configuration_id
        _set_feedback(result.message)
        _refresh()

    def _toggle_active(config_id: str, active: bool) -> None:
        result = set_configuration_active(profile_id, config_id, active=active)
        if not result.success:
            _set_feedback(result.message, is_error=True)
        else:
            _set_feedback("Konfiguration aktiviert." if active else "Konfiguration deaktiviert.")
        _refresh()

    def _reorder(config_id: str, *, direction: int) -> None:
        ordered_ids = [item.configuration_id for item in page_vm.configurations]
        try:
            index = ordered_ids.index(config_id)
        except ValueError:
            _set_feedback("Konfiguration nicht gefunden.", is_error=True)
            _refresh()
            return
        target = index + direction
        if target < 0 or target >= len(ordered_ids):
            return
        ordered_ids[index], ordered_ids[target] = ordered_ids[target], ordered_ids[index]
        result = reorder_configurations(profile_id, ordered_ids)
        if not result.success:
            _set_feedback(result.message, is_error=True)
        else:
            _set_feedback(result.message)
        _refresh()

    def _request_delete(config_id: str, name: str) -> None:
        if state.open_dialog:
            state.open_dialog(
                confirmation_dialog(
                    title="Konfiguration löschen?",
                    message=f'„{name}" wird dauerhaft gelöscht. Dieser Schritt kann nicht rückgängig gemacht werden.',
                    confirm_label="Endgültig löschen",
                    on_confirm=lambda: _confirm_delete(config_id),
                    on_cancel=lambda: state.close_dialog() if state.close_dialog else None,
                )
            )

    def _confirm_delete(config_id: str) -> None:
        if state.close_dialog:
            state.close_dialog()
        result = delete_configuration(profile_id, config_id)
        if not result.success:
            _set_feedback(result.message, is_error=True)
        else:
            if state.config_list_selected_id == config_id:
                state.config_list_selected_id = None
            state.discard_config_edit()
            _set_feedback(result.message)
        _refresh()

    items: list[ft.Control] = [
        page_header(
            "Konfigurationen",
            subtitle="Lege fest, welche Dokumente zusammengehören, wie sie benannt und in welchen Ordner sie gespeichert werden.",
            trailing=action_button("Neue Konfiguration", on_click=lambda _e: _start_create(), primary=True),
        ),
    ]

    if state.config_feedback:
        items.append(feedback_banner(state.config_feedback, is_error=state.config_feedback_error))

    items.append(
        helper_text(
            f"SaaS-Entwurf: {state.saas_disk_persistence_label} — nur lokale Disk-Persistenz, kein Cloud-/Mandantenbackend."
        )
    )

    items.append(
        kpi_strip(
            ("Profil", snapshot.profile.profile_name, False),
            ("Konfigurationen", str(page_vm.total_count), False),
            ("Aktiv", str(page_vm.active_count), False),
            ("Fehlende Ziele", str(page_vm.missing_destination_count), page_vm.missing_destination_count > 0),
        )
    )

    def _list_row(config: ConfigurationSummaryVM) -> ft.Control:
        config_id = config.configuration_id
        is_selected = selected_id == config_id and not is_editing
        tone = "active" if config.active else "inactive"
        status_label = "Aktiv" if config.active else "Inaktiv"
        return compact_list_item(
            config.name,
            trailing=status_badge(status_label, tone=tone),
            selected=is_selected,
            on_select=lambda _e, cid=config_id: _select_config(cid),
        )

    list_rows: list[ft.Control] = []
    for index, config in enumerate(page_vm.configurations):
        if index > 0:
            list_rows.append(divider())
        list_rows.append(_list_row(config))
    if page_vm.unmatched is not None:
        if list_rows:
            list_rows.append(divider())
        list_rows.append(_list_row(page_vm.unmatched))
    if is_creating:
        if list_rows:
            list_rows.append(divider())
        list_rows.append(make_create_list_marker("Neue Konfiguration"))

    if list_rows:
        list_body = ft.Column(list_rows, spacing=0, scroll=ft.ScrollMode.AUTO)
    else:
        list_body = ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=empty_state(
                "Keine Konfigurationen vorhanden",
                detail='Legen Sie mit „Neue Konfiguration“ eine erste Zuordnungsregel an.',
                icon=ft.Icons.TUNE,
            ),
        )

    field_errors = state.config_field_errors or {}
    detail_title = "Konfigurationen"
    header_trailing: ft.Control | None = None
    detail_body: ft.Control
    footer: ft.Control | None = None

    if is_editing and state.config_draft is not None:
        draft = state.config_draft
        try:
            bundle = load_profile_bundle(profile_id)
            scan_model = bundle.scan_model
        except Exception:
            items.append(inline_warning("Profil konnte nicht geladen werden."))
            return page_scaffold(*items)

        if state.config_edit_mode == "create":
            detail_title = "Neue Konfiguration"
        elif draft.is_unmatched:
            detail_title = "Nicht zugeordnete Dokumente bearbeiten"
        elif selected_config is not None:
            detail_title = f"Bearbeiten: {selected_config.name}"
        else:
            detail_title = "Konfiguration bearbeiten"

        header_trailing = make_panel_close_button(_cancel_edit)
        editor_fields: list[ft.Control] = []

        async def _pick_folder(_event: ft.ControlEvent) -> None:
            path = await choose_target_folder(dialog_title="Zielordner auswählen")
            if path:
                draft.destination_path = path
                state.saas_draft_store.update_configuration_field("destination_folder", path)
                _refresh()

        def _schedule_pick(_event: ft.ControlEvent) -> None:
            if state.page is not None and hasattr(state.page, "run_task"):
                state.page.run_task(_pick_folder, _event)

        def _on_pattern_change(pattern) -> None:
            draft.filename_pattern = copy_filename_pattern(pattern)
            try:
                summary = pattern_to_template(pattern).strip()
            except Exception:
                summary = ""
            if summary:
                state.saas_draft_store.update_configuration_field("filename_pattern", summary)

        def _set_active(val: bool) -> None:
            draft.active = val
            state.saas_draft_store.update_configuration_field("active", val)
            _refresh()

        saas_config = state.saas_draft_store.configuration_draft
        if saas_config is None and state.config_edit_mode == "create":
            saas_config = state.saas_draft_store.begin_blank_configuration()

        if not draft.is_unmatched:
            name_field = form_field(
                "Name",
                value=draft.name,
                hint=GENERIC_CONFIG_NAME_HINT,
            )
            document_type_field = form_field(
                SAAS_SURFACE_UI_LABELS["document_type"],
                value=(saas_config.document_type if saas_config else ""),
            )
            payment_field = form_field(
                SAAS_SURFACE_UI_LABELS["payment_hint"],
                value=(saas_config.payment_hint if saas_config else ""),
            )
            review_field = form_field(
                SAAS_SURFACE_UI_LABELS["review_rule"],
                value=(saas_config.review_rule_label() if saas_config else "Unklar bei Nicht-Treffer"),
            )

            def _update_name(_event: ft.ControlEvent | None = None) -> None:
                draft.name = (name_field.value or "").strip()
                state.saas_draft_store.update_configuration_field("name", draft.name)
                state.config_field_errors = {}

            def _update_saas_extras(_event: ft.ControlEvent | None = None) -> None:
                state.saas_draft_store.update_configuration_field(
                    "document_type", (document_type_field.value or "").strip()
                )
                state.saas_draft_store.update_configuration_field(
                    "payment_hint", (payment_field.value or "").strip()
                )
                state.config_field_errors = {}

            name_field.on_change = _update_name
            document_type_field.on_change = _update_saas_extras
            payment_field.on_change = _update_saas_extras

            def _update_field(feature_key: str) -> None:
                draft.matching.feature_key = feature_key
                draft.matching.operator = "ist"
                state.saas_draft_store.update_configuration_field(
                    "matching_conditions",
                    f"{feature_key} ist {', '.join(draft.matching.values)}".strip(),
                )
                state.config_field_errors = {}
                _refresh()

            def _update_values(values: list[str]) -> None:
                draft.matching.values = values
                draft.matching.operator = "ist"
                state.saas_draft_store.update_configuration_field(
                    "matching_conditions",
                    f"{draft.matching.feature_key} ist {', '.join(values)}".strip(),
                )
                state.config_field_errors = {}
                _refresh()

            editor_fields.append(form_field_group("Name", full_width_field(name_field), error=field_errors.get("name")))
            editor_fields.append(
                form_field_group(
                    SAAS_SURFACE_UI_LABELS["document_type"],
                    full_width_field(document_type_field),
                    error=field_errors.get("document_type"),
                )
            )
            editor_fields.append(
                build_rule_builder_field(
                    scan_model=scan_model,
                    feature_key=draft.matching.feature_key,
                    values=list(draft.matching.values),
                    on_field_change=_update_field,
                    on_values_change=_update_values,
                    error=field_errors.get("matching"),
                )
            )
            editor_fields.append(
                form_field_group(
                    SAAS_SURFACE_UI_LABELS["review_rule"],
                    full_width_field(review_field),
                )
            )
            editor_fields.append(
                form_field_group(
                    SAAS_SURFACE_UI_LABELS["payment_hint"],
                    full_width_field(payment_field),
                )
            )
        else:
            editor_fields.append(helper_text("Dokumente ohne eindeutige Zuordnung werden hier gesammelt."))

        if field_errors.get("_form"):
            editor_fields.append(inline_warning(field_errors["_form"]))

        def _on_destination_change(path: str) -> None:
            draft.destination_path = path
            state.saas_draft_store.update_configuration_field("destination_folder", path)

        editor_fields.append(
            build_filename_pattern_editor(
                scan_model=scan_model,
                pattern=draft.filename_pattern,
                on_change=_on_pattern_change,
                error=field_errors.get("filename_pattern"),
            )
        )
        editor_fields.append(
            build_folder_picker_field(
                value=draft.destination_path,
                on_change=_on_destination_change,
                on_pick=_schedule_pick,
                error=field_errors.get("destination_path"),
            )
        )

        if not draft.is_unmatched:
            editor_fields.append(make_form_status_toggle(active=draft.active, on_change=_set_active))

        if state.config_edit_mode == "create":
            generic_keys = ", ".join(
                item["label"] for item in state.saas_draft_store.generic_editor_fields()
            )
            editor_fields.append(
                helper_text(
                    f"Generischer Konfigurationseditor: {generic_keys}. "
                    "In-Memory-Entwurf ohne private Vorbelegung."
                )
            )

        footer = make_panel_footer_end(
            secondary_button("Abbrechen", on_click=_cancel_edit),
            make_accent_cta_button("Speichern", on_click=_save_config),
        )
        detail_body = ft.ListView(editor_fields, spacing=14, padding=0, auto_scroll=False, expand=True)

    elif selected_config is not None:
        config = selected_config
        is_unmatched = _is_unmatched_config(config)
        detail_title = "Nicht zugeordnete Dokumente" if is_unmatched else config.name

        if is_unmatched:
            erkannt_bei = make_metadata_row(
                "Erkannt bei",
                "Fallback — fängt alle nicht zugeordneten Dokumente auf",
                italic=True,
            )
        else:
            if config.matching_feature_label and config.matching_values:
                erkannt_value = make_matching_rule_display(config.matching_feature_label, config.matching_values)
            else:
                erkannt_value = user_matching_summary_from_text(config.matching_summary)
            erkannt_bei = make_metadata_row("Erkannt bei", erkannt_value)

        metadata_rows = [
            erkannt_bei,
            make_metadata_row("Dateinamenmuster", config.filename_pattern_summary, mono=True),
        ]
        if config.filename_example:
            metadata_rows.append(make_metadata_row("Beispiel", config.filename_example, mono=True))
        metadata_rows.append(
            make_metadata_row(
                "Zielordner",
                display_path_value(config.destination_summary),
                mono=True,
                warn="Ordner fehlt oder ist nicht erreichbar." if config.destination_missing else None,
            )
        )

        if not is_unmatched:
            header_trailing = make_status_toggle_pill(
                active=config.active,
                on_toggle=lambda _e, cid=config.configuration_id, active=config.active: _toggle_active(cid, not active),
            )

        view_actions: list[ft.Control] = [
            action_button(
                "Bearbeiten",
                on_click=lambda _e, cid=config.configuration_id, um=is_unmatched: _start_edit(cid, is_unmatched=um),
            ),
        ]
        if not is_unmatched:
            activate_label = "Deaktivieren" if config.active else "Aktivieren"
            view_actions.append(
                action_button(
                    activate_label,
                    on_click=lambda _e, cid=config.configuration_id, active=config.active: _toggle_active(
                        cid, not active
                    ),
                )
            )
            view_actions.append(
                action_button(
                    "Nach oben",
                    on_click=lambda _e, cid=config.configuration_id: _reorder(cid, direction=-1),
                )
            )
            view_actions.append(
                action_button(
                    "Nach unten",
                    on_click=lambda _e, cid=config.configuration_id: _reorder(cid, direction=1),
                )
            )

        footer = make_panel_footer_start(
            *view_actions,
            destructive=None
            if is_unmatched
            else action_button(
                "Löschen",
                on_click=lambda _e, cid=config.configuration_id, n=config.name: _request_delete(cid, n),
                destructive=True,
            ),
        )
        detail_body = make_metadata_block(*metadata_rows)

    else:
        detail_body = ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=empty_state(
                "Keine Konfigurationen vorhanden",
                detail='Legen Sie mit „Neue Konfiguration“ eine erste Zuordnungsregel an.',
                icon=ft.Icons.TUNE,
            ),
        )

    panel_height = resolve_list_detail_height(state.page, editing=is_editing)
    edit_body_padding = ft.Padding.only(left=18, right=18, top=16, bottom=12)
    view_body_padding = ft.Padding.only(left=18, right=18, top=2, bottom=0)

    detail_panel_ctrl = make_split_detail_panel(
        detail_title,
        detail_body,
        height=panel_height,
        header_trailing=header_trailing,
        footer=footer,
        scroll_body=is_editing,
        body_padding=edit_body_padding if is_editing else view_body_padding,
    )

    items.append(
        list_detail_split(
            list_panel("Konfigurationen", list_body, height=panel_height),
            detail_panel_ctrl,
        )
    )

    for warning in page_vm.warnings:
        items.append(inline_warning(warning))

    return page_scaffold(*items)
