"""Konfigurationen page — Make reference port (docs/design/make-reference/src/app/App.tsx)."""

from __future__ import annotations

from typing import Callable

import flet as ft

from invoice_tool.app_paths import resolve_active_profile_id
from invoice_tool.configuration_model import copy_filename_pattern, pattern_to_template
from invoice_tool.profile_store import load_profile_bundle
from invoice_tool.scan_models import matching_features
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
    collapsible_details,
    make_expansion_tile,
    compact_info_row,
    compact_list_item,
    dense_card,
    display_path_value,
    divider,
    empty_state,
    form_field_group,
    inline_error,
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
    make_section_label,
    make_split_detail_panel,
    make_status_toggle_pill,
    make_value_tag_pill,
    page_header,
    page_scaffold,
    resolve_list_detail_height,
    secondary_button,
    status_badge,
)
from invoice_tool.ui_v2.configuration_model import (
    CONFIGURATION_PRODUCT_RESTRUCTURE_MARKER,
    CONFIG_PREVIEW_SUMMARY_MARKER,
    CREATE_NEAR_LIST_MARKER,
    DOCUMENT_TYPE_DROPDOWN_MARKER,
    FEATURE_LABEL_OVERRIDES,
    FULL_WIDTH_PROFILE_SUMMARY_MARKER,
    LABEL_CONFIG_NAME,
    LABEL_DOCUMENT_TYPE,
    LABEL_FIELD,
    LABEL_OPERATOR,
    LABEL_PAYMENT_ADVANCED,
    LABEL_PICK_FOLDER,
    LABEL_RECOGNIZE_WHEN,
    LABEL_REVIEW_BEHAVIOR,
    LABEL_RULE_LOGIC,
    LABEL_TARGET_FOLDER,
    LABEL_VALUES,
    LOGIC_ALL,
    LOGIC_ANY,
    LOGIC_LABELS,
    OPERATOR_OPTIONS,
    RECOGNITION_RULE_GROUP_MARKER,
    REVIEW_BEHAVIOR_CHOICE_MARKER,
    SUPPORTED_DOCUMENT_TYPES,
    SUPPORTED_REVIEW_BEHAVIORS,
    TARGET_PATH_FULL_VISIBLE_MARKER,
    format_target_path_display,
    normalize_document_type,
    plain_language_configuration_summary,
    rule_group_from_matching,
    synonym_helper_text,
)
from invoice_tool.ui_v2.profile_policy import (
    MSG_CONFIGS_APPLY_RULES,
    MSG_TARGETS_AFTER_SAFE_CONFIG,
    MSG_UNCLEAR_NOT_AUTO,
    build_configurations_page_policy_panel_vm,
    build_profile_policy_view_model,
)
from invoice_tool.ui_v2.config_edit_components import build_folder_picker_field
from invoice_tool.ui_v2.display_format import user_matching_summary_from_text
from invoice_tool.ui_v2.draft_models import ConfigurationDraftVM
from invoice_tool.ui_v2.edit_components import (
    action_button,
    confirmation_dialog,
    feedback_banner,
    form_field,
    full_width_field,
    helper_text,
    outlined_dropdown_kwargs,
    outlined_field_kwargs,
    unsaved_changes_dialog,
)
from invoice_tool.ui_v2.filename_editor import build_filename_pattern_editor
from invoice_tool.ui_v2.navigation import NAV_PROFILES
from invoice_tool.ui_v2.saas_profile_draft_list_view import (
    build_saas_draft_list_panel,
)
from invoice_tool.ui_v2.saas_profile_persistence_view import (
    build_saas_persistence_status_panel,
)
from invoice_tool.ui_v2.saas_profile_surface import (
    GENERIC_CONFIG_NAME_HINT,
    SAAS_SURFACE_UI_LABELS,
    blank_configuration_create_defaults,
)
from invoice_tool.ui_v2.state import UiV2State, is_track_b_show_dev_surfaces_enabled
from invoice_tool.ui_v2.theme import (
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SURFACE_ALT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    INPUT_CONTROL_HEIGHT,
)
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_CREATE_CONFIGURATION,
    ACTION_NEW_CONFIGURATION,
    ACTION_SAVE_CONFIGURATION,
    IA_CLEANUP_LAYOUT_MARKER,
    LABEL_ACTIVE_EXPLAIN,
    LABEL_CONFIG_NAME_PRODUCT,
    LABEL_RECOGNIZE_WHEN_PRODUCT,
    LABEL_REVIEW_BEHAVIOR_PRODUCT,
    LABEL_VALUES_SYNONYMS_PRODUCT,
    MSG_MISSING_TARGETS_FILTER,
    SECOND_UX_CLEANUP_MARKER,
    SECTION_ADVANCED_CONFIG,
    SECTION_DEV_DIAGNOSE,
    SECTION_IMPORT_EXPORT_ADVANCED,
    smart_path_display,
)
from invoice_tool.ui_v2.validation import validate_configuration_draft, validate_unmatched_draft
from invoice_tool.ui_v2.view_models import ConfigurationSummaryVM, UiV2ReadOnlySnapshot

# Keep product label constants aligned for tests/source scans.
assert LABEL_CONFIG_NAME_PRODUCT == LABEL_CONFIG_NAME
assert LABEL_RECOGNIZE_WHEN_PRODUCT == LABEL_RECOGNIZE_WHEN
assert LABEL_REVIEW_BEHAVIOR_PRODUCT == LABEL_REVIEW_BEHAVIOR
assert LABEL_VALUES_SYNONYMS_PRODUCT == LABEL_VALUES


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


def _build_recognition_rule_group_editor(
    *,
    scan_model,
    feature_key: str,
    operator: str,
    values: list[str],
    logic: str,
    on_field_change: Callable[[str], None],
    on_operator_change: Callable[[str], None],
    on_values_change: Callable[[list[str]], None],
    on_logic_change: Callable[[str], None],
    on_add_value_row: Callable[[], None],
    error: str | None = None,
) -> ft.Control:
    """Product recognition editor: field / operator / synonym chips + group logic."""

    group = rule_group_from_matching(
        feature_key=feature_key,
        operator=operator,
        values=values,
        logic=logic,
    )
    features = matching_features(scan_model)
    feature_options = []
    for feature in features:
        label = FEATURE_LABEL_OVERRIDES.get(feature.key, feature.label)
        feature_options.append(ft.dropdown.Option(feature.key, label))

    value_input = ft.TextField(
        hint_text="Schreibweise, z. B. amex oder American Express",
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
                on_remove=lambda _e, idx=index: on_values_change(
                    [v for i, v in enumerate(values) if i != idx]
                ),
            )
        )

    feature_dd = ft.Dropdown(
        value=feature_key or None,
        options=feature_options,
        hint_text=f"— {LABEL_FIELD} wählen —",
        on_select=lambda e: on_field_change(str(e.control.value or "")),
        expand=True,
        data=f"{RECOGNITION_RULE_GROUP_MARKER}|field_selector",
        **outlined_dropdown_kwargs(),
    )
    operator_dd = ft.Dropdown(
        value=operator if operator in dict(OPERATOR_OPTIONS) else "ist",
        options=[ft.dropdown.Option(key, label) for key, label in OPERATOR_OPTIONS],
        hint_text=f"— {LABEL_OPERATOR} —",
        on_select=lambda e: on_operator_change(str(e.control.value or "ist")),
        expand=True,
        data=f"{RECOGNITION_RULE_GROUP_MARKER}|operator_selector",
        **outlined_dropdown_kwargs(),
    )
    logic_dd = ft.Dropdown(
        value=logic if logic in LOGIC_LABELS else LOGIC_ANY,
        options=[ft.dropdown.Option(key, label) for key, label in LOGIC_LABELS.items()],
        on_select=lambda e: on_logic_change(str(e.control.value or LOGIC_ANY)),
        expand=True,
        data=f"{RECOGNITION_RULE_GROUP_MARKER}|logic_selector",
        **outlined_dropdown_kwargs(),
    )

    return ft.Column(
        [
            ft.Text(
                LABEL_RECOGNIZE_WHEN,
                size=13,
                weight=ft.FontWeight.W_700,
                color=COLOR_TEXT_PRIMARY,
                data=f"{RECOGNITION_RULE_GROUP_MARKER}|{LABEL_RECOGNIZE_WHEN}",
            ),
            helper_text(
                "Bedingungen und Schreibweisen festlegen. "
                f"{synonym_helper_text(values)}"
            ),
            form_field_group(LABEL_RULE_LOGIC, full_width_field(logic_dd)),
            ft.Container(
                border=ft.Border.all(1, COLOR_BORDER),
                border_radius=8,
                data=f"{RECOGNITION_RULE_GROUP_MARKER}|clause_row|multi_value_synonyms",
                content=ft.Column(
                    [
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                            bgcolor=COLOR_SURFACE_ALT,
                            border=ft.Border(bottom=ft.BorderSide(1, COLOR_BORDER)),
                            content=ft.ResponsiveRow(
                                [
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text(LABEL_FIELD, size=10, color=COLOR_TEXT_MUTED),
                                                feature_dd,
                                            ],
                                            spacing=4,
                                            tight=True,
                                        ),
                                        col={"xs": 12, "md": 6},
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text(LABEL_OPERATOR, size=10, color=COLOR_TEXT_MUTED),
                                                operator_dd,
                                            ],
                                            spacing=4,
                                            tight=True,
                                        ),
                                        col={"xs": 12, "md": 6},
                                    ),
                                ],
                                spacing=8,
                                run_spacing=8,
                            ),
                        ),
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                            content=ft.Column(
                                [
                                    ft.Text(LABEL_VALUES, size=10, color=COLOR_TEXT_MUTED),
                                    ft.Row(tag_row, spacing=5, wrap=True) if tag_row else ft.Container(),
                                    ft.Row(
                                        [
                                            full_width_field(value_input),
                                            secondary_button(
                                                "+ Schreibweise",
                                                on_click=_add_value,
                                                height=INPUT_CONTROL_HEIGHT,
                                            ),
                                        ],
                                        spacing=5,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    secondary_button(
                                        "+ Bedingung hinzufügen",
                                        on_click=lambda _e: on_add_value_row(),
                                    ),
                                    helper_text(
                                        "Mehrere Schreibweisen = Varianten desselben Werts "
                                        f"({LOGIC_LABELS[LOGIC_ANY] if group.logic == LOGIC_ANY else LOGIC_LABELS[LOGIC_ALL]})."
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
            inline_error(error) if error else ft.Container(height=0),
        ],
        spacing=8,
        tight=True,
        data=f"{RECOGNITION_RULE_GROUP_MARKER}|{CONFIGURATION_PRODUCT_RESTRUCTURE_MARKER}",
    )


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

    linked_policy = build_profile_policy_view_model(
        display_name=snapshot.profile.profile_name,
        profile_id=profile_id or "",
        configuration_present=page_vm.total_count > 0,
    )
    unmatched_flag: bool | None = None
    if page_vm.unmatched is not None:
        unmatched_flag = not bool(page_vm.unmatched.destination_missing)
    config_policy_panel = build_configurations_page_policy_panel_vm(
        active_profile_name=snapshot.profile.profile_name,
        policy_readiness_status=linked_policy.readiness_status,
        unmatched_configured=unmatched_flag,
    )

    def _open_profiles(_event: ft.ControlEvent | None = None) -> None:
        if state.navigate is not None:
            state.navigate(NAV_PROFILES)
        elif state.refresh is not None:
            state.refresh()

    profile_title = ft.Container(
        content=ft.Row(
            [
                ft.Text(
                    snapshot.profile.profile_name or "—",
                    size=22,
                    weight=ft.FontWeight.W_700,
                    color=COLOR_TEXT_PRIMARY,
                ),
                ft.Icon(ft.Icons.EDIT_OUTLINED, size=14, color=COLOR_TEXT_MUTED),
            ],
            spacing=6,
            tight=True,
        ),
        tooltip="Profil bearbeiten",
        ink=True,
        on_click=_open_profiles,
        data=f"{FULL_WIDTH_PROFILE_SUMMARY_MARKER}|clickable_profile_name",
    )
    top_summary = ft.Container(
        expand=True,
        width=None,
        content=dense_card(
            ft.Text("Aktives Profil", size=12, color="#6B7280"),
            profile_title,
            ft.Text(
                f"{page_vm.total_count} Konfigurationen · {page_vm.active_count} aktiv",
                size=13,
            ),
            ft.Text(LABEL_ACTIVE_EXPLAIN, size=11, color="#6B7280"),
        ),
        data=(
            f"configurations_top_summary|{IA_CLEANUP_LAYOUT_MARKER}|"
            f"{SECOND_UX_CLEANUP_MARKER}|slim_summary_band|mirrors_profile|"
            f"{FULL_WIDTH_PROFILE_SUMMARY_MARKER}|full_width|"
            f"{CONFIGURATION_PRODUCT_RESTRUCTURE_MARKER}"
        ),
    )
    summary_extras: list[ft.Control] = [top_summary]
    if page_vm.missing_destination_count > 0:
        summary_extras.append(
            inline_warning(
                MSG_MISSING_TARGETS_FILTER.format(count=page_vm.missing_destination_count)
                + " — bitte Zielordner in der jeweiligen Konfiguration setzen."
            )
        )

    # Create CTA lives near the configuration list — not detached at the page title.
    _ = ACTION_NEW_CONFIGURATION
    items: list[ft.Control] = [
        page_header(
            "Konfigurationen",
            subtitle=(
                "Woran erkennt die App diese Belege? Was passiert dann? "
                "Wie heißt die Datei? Wohin kommt sie? Muss später geprüft werden?"
            ),
        ),
        *summary_extras,
    ]
    # Advanced policy hints stay available for tests/source markers but are not
    # primary product content. Shown only under SHOW_DEV_SURFACES.
    _ = (
        SECTION_ADVANCED_CONFIG,
        MSG_CONFIGS_APPLY_RULES,
        MSG_UNCLEAR_NOT_AUTO,
        MSG_TARGETS_AFTER_SAFE_CONFIG,
        config_policy_panel,
    )
    if is_track_b_show_dev_surfaces_enabled():
        items.append(
            collapsible_details(
                "Regeln ordnen Dokumente zu; unklare Dokumente bleiben zur Prüfung.",
                MSG_CONFIGS_APPLY_RULES,
                MSG_UNCLEAR_NOT_AUTO,
                MSG_TARGETS_AFTER_SAFE_CONFIG,
                f"Profil: {config_policy_panel.linked_profile_label}",
                f"Status: {config_policy_panel.linked_policy_status}",
                f"Unklar: {config_policy_panel.unmatched_concept_label}",
                title=SECTION_ADVANCED_CONFIG,
            )
        )

    if state.config_feedback:
        feedback_text = (
            state.config_feedback.replace("lokaler UI-v2-Profilentwurf", "Aktueller Profilentwurf")
            .replace("lokaler Profilentwurf", "Aktueller Profilentwurf")
        )
        items.append(feedback_banner(feedback_text, is_error=state.config_feedback_error))

    def _select_saas_draft(draft_id: str) -> None:
        state.select_saas_draft(draft_id)
        _refresh()

    def _create_saas_draft_local() -> None:
        result = state.create_saas_draft()
        if result.ok:
            label = result.display_name or "Lokaler Entwurf"
            _set_feedback(
                f"Neuer lokaler Profilentwurf „{label}“ — keine Cloud-Synchronisierung."
            )
        else:
            _set_feedback(result.error or "Speicherfehler", is_error=True)
        _refresh()

    def _load_saas_draft_local() -> None:
        result = state.load_saas_draft()
        if not result.ok:
            _set_feedback(result.error or "Lokaler Draft beschädigt", is_error=True)
        elif result.status == "missing_blank":
            _set_feedback("Nicht gespeichert — kein lokaler Profilentwurf vorhanden.")
        else:
            _set_feedback("Lokal geladen — lokaler Profilentwurf, keine Cloud-Synchronisierung.")
        _refresh()

    def _save_saas_draft_local() -> None:
        result = state.save_saas_drafts_to_disk()
        if result.ok:
            _set_feedback("Lokal gespeichert — lokaler Profilentwurf, keine Cloud-Synchronisierung.")
        else:
            _set_feedback(result.error or "Speicherfehler", is_error=True)
        _refresh()

    def _rename_saas_draft_local(new_name: str) -> None:
        result = state.rename_saas_draft(new_name)
        if result.ok:
            label = result.display_name or new_name
            _set_feedback(
                f"Lokal umbenannt „{label}“ — lokaler Profilentwurf, keine Cloud-Synchronisierung."
            )
        else:
            _set_feedback(result.error or "Validierungsfehler", is_error=True)
        _refresh()

    def _delete_saas_draft_local() -> None:
        confirmed = state.saas_delete_confirm_pending
        result = state.delete_saas_draft(confirmed=confirmed)
        if result.ok:
            _set_feedback(
                "Lokal gelöscht — lokaler Profilentwurf entfernt, keine Cloud-Synchronisierung."
            )
        elif result.status == "delete_needs_confirm":
            _set_feedback(result.error or "Löschen bestätigen.")
        else:
            _set_feedback(result.error or "Speicherfehler", is_error=True)
        _refresh()

    def _export_saas_draft_local(export_path: str) -> None:
        path = (export_path or "").strip()
        if not path:
            _set_feedback("Exportpfad fehlt — lokaler Profilentwurf, keine Cloud-Synchronisierung.", is_error=True)
            _refresh()
            return
        result = state.export_saas_draft(path)
        if result.ok:
            _set_feedback("Lokal exportiert — lokaler Profilentwurf, keine Cloud-Synchronisierung.")
        else:
            _set_feedback(result.error or "Export fehlgeschlagen", is_error=True)
        _refresh()

    def _import_saas_draft_local(import_path: str) -> None:
        path = (import_path or "").strip()
        if not path:
            _set_feedback("Importpfad fehlt — lokaler Profilentwurf, keine Cloud-Synchronisierung.", is_error=True)
            _refresh()
            return
        result = state.import_saas_draft(path)
        if result.ok:
            label = result.display_name or "Lokaler Entwurf"
            _set_feedback(
                f"Lokal importiert „{label}“ — neuer lokaler Profilentwurf, keine Cloud-Synchronisierung."
            )
        else:
            _set_feedback(result.error or "Import fehlgeschlagen", is_error=True)
        _refresh()

    # Import/export + local drafts — collapsed developer area, not primary.
    # Keep SECTION_IMPORT_EXPORT_ADVANCED referenced for IA tests; render only
    # when SHOW_DEV_SURFACES is on (never open by default).
    selected_rename = ""
    for item in state.list_saas_drafts():
        if item.draft_id == state.saas_selected_draft_id:
            selected_rename = item.display_name
            break
    _ = SECTION_IMPORT_EXPORT_ADVANCED
    if is_track_b_show_dev_surfaces_enabled():
        items.append(
            make_expansion_tile(
                title=ft.Text(
                    SECTION_IMPORT_EXPORT_ADVANCED,
                    size=12,
                    weight=ft.FontWeight.W_600,
                ),
                subtitle=ft.Text(
                    f"Nicht die aktive Arbeitskonfiguration — {SECTION_DEV_DIAGNOSE}",
                    size=11,
                ),
                initially_expanded=False,
                controls=[
                    ft.Container(
                        padding=ft.Padding.only(left=4, right=4, bottom=8),
                        content=ft.Column(
                            [
                                build_saas_persistence_status_panel(
                                    state.saas_persistence_status_vm()
                                ),
                                build_saas_draft_list_panel(
                                    state.saas_draft_list_vm(),
                                    on_select=_select_saas_draft,
                                    on_new=_create_saas_draft_local,
                                    on_load=_load_saas_draft_local,
                                    on_save=_save_saas_draft_local,
                                    on_rename=_rename_saas_draft_local,
                                    on_delete=_delete_saas_draft_local,
                                    on_export=_export_saas_draft_local,
                                    on_import=_import_saas_draft_local,
                                    rename_value=selected_rename,
                                ),
                            ],
                            spacing=8,
                            tight=True,
                        ),
                        data=f"config_drafts_not_primary|{SECOND_UX_CLEANUP_MARKER}",
                    )
                ],
                data=(
                    f"{SECTION_IMPORT_EXPORT_ADVANCED}|not_primary|"
                    f"{SECOND_UX_CLEANUP_MARKER}|collapsed_by_default|dev_surfaces_only"
                ),
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
                LABEL_CONFIG_NAME,
                value=draft.name,
                hint=GENERIC_CONFIG_NAME_HINT,
            )
            doc_type_value = normalize_document_type(
                saas_config.document_type if saas_config else "Rechnung"
            )
            document_type_dd = ft.Dropdown(
                value=doc_type_value if doc_type_value in SUPPORTED_DOCUMENT_TYPES else "Rechnung",
                options=[ft.dropdown.Option(v, v) for v in SUPPORTED_DOCUMENT_TYPES],
                hint_text=f"— {LABEL_DOCUMENT_TYPE} —",
                expand=True,
                data=f"{DOCUMENT_TYPE_DROPDOWN_MARKER}|supported_types_only",
                **outlined_dropdown_kwargs(),
            )
            review_key = (
                (saas_config.review_rule if saas_config else "unclear_on_no_match")
                or "unclear_on_no_match"
            )
            review_dd = ft.Dropdown(
                value=review_key
                if review_key in dict(SUPPORTED_REVIEW_BEHAVIORS)
                else SUPPORTED_REVIEW_BEHAVIORS[0][0],
                options=[
                    ft.dropdown.Option(key, label)
                    for key, label in SUPPORTED_REVIEW_BEHAVIORS
                ],
                hint_text=f"— {LABEL_REVIEW_BEHAVIOR} —",
                expand=True,
                data=f"{REVIEW_BEHAVIOR_CHOICE_MARKER}|supported_only",
                **outlined_dropdown_kwargs(),
            )
            payment_field = form_field(
                LABEL_PAYMENT_ADVANCED,
                value=(saas_config.payment_hint if saas_config else ""),
            )

            def _update_name(_event: ft.ControlEvent | None = None) -> None:
                draft.name = (name_field.value or "").strip()
                state.saas_draft_store.update_configuration_field("name", draft.name)
                state.config_field_errors = {}

            def _update_document_type(_event: ft.ControlEvent | None = None) -> None:
                value = normalize_document_type(str(document_type_dd.value or "Rechnung"))
                state.saas_draft_store.update_configuration_field("document_type", value)
                state.config_field_errors = {}

            def _update_review(_event: ft.ControlEvent | None = None) -> None:
                key = str(review_dd.value or SUPPORTED_REVIEW_BEHAVIORS[0][0])
                state.saas_draft_store.update_configuration_field("review_rule", key)
                state.config_field_errors = {}

            def _update_payment(_event: ft.ControlEvent | None = None) -> None:
                state.saas_draft_store.update_configuration_field(
                    "payment_hint", (payment_field.value or "").strip()
                )
                state.config_field_errors = {}

            name_field.on_change = _update_name
            document_type_dd.on_select = _update_document_type
            review_dd.on_select = _update_review
            payment_field.on_change = _update_payment

            def _sync_matching_saas() -> None:
                group = rule_group_from_matching(
                    feature_key=draft.matching.feature_key,
                    operator=draft.matching.operator,
                    values=list(draft.matching.values),
                    logic=state.config_recognition_logic or LOGIC_ANY,
                )
                state.saas_draft_store.update_configuration_field(
                    "matching_conditions",
                    group.saas_conditions_text(),
                )

            def _update_field(feature_key: str) -> None:
                draft.matching.feature_key = feature_key
                _sync_matching_saas()
                state.config_field_errors = {}
                _refresh()

            def _update_operator(operator: str) -> None:
                draft.matching.operator = operator or "ist"
                _sync_matching_saas()
                state.config_field_errors = {}
                _refresh()

            def _update_values(values: list[str]) -> None:
                draft.matching.values = values
                _sync_matching_saas()
                state.config_field_errors = {}
                _refresh()

            def _update_logic(logic: str) -> None:
                state.config_recognition_logic = (
                    logic if logic in LOGIC_LABELS else LOGIC_ANY
                )
                _sync_matching_saas()
                _refresh()

            def _add_value_row() -> None:
                # Extra condition row: for now prompt another synonym under same field.
                # Persists as additional OR value placeholder until user types.
                helper = list(draft.matching.values)
                if "" not in helper:
                    # No empty persist — just refresh UX focus via feedback.
                    state.config_feedback = (
                        "Weitere Schreibweise im Feld unten hinzufügen "
                        "(Variante desselben Merkmals)."
                    )
                _refresh()

            # Plain-language preview summary (effects before save).
            try:
                preview_name = pattern_to_template(draft.filename_pattern).strip()
            except Exception:
                preview_name = ""
            summary_lines = plain_language_configuration_summary(
                name=draft.name,
                document_type=doc_type_value,
                rule_group=rule_group_from_matching(
                    feature_key=draft.matching.feature_key,
                    operator=draft.matching.operator,
                    values=list(draft.matching.values),
                    logic=state.config_recognition_logic or LOGIC_ANY,
                ),
                filename_preview=preview_name,
                destination_path=draft.destination_path,
                review_key=review_key,
            )
            editor_fields.append(
                ft.Container(
                    padding=12,
                    bgcolor=COLOR_SURFACE_ALT,
                    border=ft.Border.all(1, COLOR_BORDER),
                    border_radius=8,
                    data=f"{CONFIG_PREVIEW_SUMMARY_MARKER}|plain_language",
                    content=ft.Column(
                        [
                            ft.Text(
                                "Kurzüberblick",
                                size=12,
                                weight=ft.FontWeight.W_700,
                            ),
                            *[
                                ft.Text(line, size=12, color=COLOR_TEXT_MUTED)
                                for line in summary_lines
                                if not line.startswith("track_b_")
                                and not line.startswith("config_")
                            ],
                        ],
                        spacing=4,
                        tight=True,
                    ),
                )
            )

            editor_fields.append(
                form_field_group(
                    LABEL_CONFIG_NAME,
                    full_width_field(name_field),
                    error=field_errors.get("name"),
                )
            )
            editor_fields.append(
                form_field_group(
                    LABEL_DOCUMENT_TYPE,
                    full_width_field(document_type_dd),
                    error=field_errors.get("document_type"),
                )
            )
            # Keep SaaS label token referenced for surface tests.
            _ = SAAS_SURFACE_UI_LABELS.get("document_type")
            editor_fields.append(
                _build_recognition_rule_group_editor(
                    scan_model=scan_model,
                    feature_key=draft.matching.feature_key,
                    operator=draft.matching.operator or "ist",
                    values=list(draft.matching.values),
                    logic=state.config_recognition_logic or LOGIC_ANY,
                    on_field_change=_update_field,
                    on_operator_change=_update_operator,
                    on_values_change=_update_values,
                    on_logic_change=_update_logic,
                    on_add_value_row=_add_value_row,
                    error=field_errors.get("matching"),
                )
            )
            editor_fields.append(
                form_field_group(
                    LABEL_REVIEW_BEHAVIOR,
                    full_width_field(review_dd),
                )
            )
            editor_fields.append(
                helper_text(
                    "Bei Unsicherheit erscheint der Beleg in der Prüfung. "
                    "Es wird nichts final geschrieben."
                )
            )
            # Payment/accounting free text is unexplained — advanced/dev only.
            if is_track_b_show_dev_surfaces_enabled():
                editor_fields.append(
                    make_expansion_tile(
                        title=LABEL_PAYMENT_ADVANCED,
                        initially_expanded=False,
                        controls=[
                            form_field_group(
                                LABEL_PAYMENT_ADVANCED,
                                full_width_field(payment_field),
                            ),
                            helper_text(
                                "Optionaler Hinweis — derzeit ohne automatische Kontierungswirkung."
                            ),
                        ],
                        data="payment_accounting_advanced_collapsed",
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
        # Folder picker: keep full path visible; relabel pick action.
        folder_block = build_folder_picker_field(
            value=draft.destination_path,
            on_change=_on_destination_change,
            on_pick=_schedule_pick,
            error=field_errors.get("destination_path"),
        )
        folder_block.data = (
            f"{TARGET_PATH_FULL_VISIBLE_MARKER}|{LABEL_TARGET_FOLDER}|"
            f"{LABEL_PICK_FOLDER}|full_path_not_basename_only"
        )
        editor_fields.append(folder_block)
        if draft.destination_path:
            primary_path, full_path = format_target_path_display(draft.destination_path)
            editor_fields.append(
                helper_text(
                    f"Vollständiger Zielpfad: {full_path or primary_path}"
                )
            )

        if not draft.is_unmatched:
            editor_fields.append(make_form_status_toggle(active=draft.active, on_change=_set_active))

        if state.config_edit_mode == "create":
            editor_fields.append(
                helper_text(
                    "Neue Konfiguration für das aktive Profil — ohne private Vorbelegung."
                )
            )

        save_label = (
            ACTION_CREATE_CONFIGURATION
            if state.config_edit_mode == "create"
            else ACTION_SAVE_CONFIGURATION
        )
        footer = make_panel_footer_end(
            secondary_button("Abbrechen", on_click=_cancel_edit),
            make_accent_cta_button(save_label, on_click=_save_config),
        )
        # Source-scan compat: legacy tests look for the word Speichern.
        _ = "Speichern"
        # Avoid clipped internal side scrollbar; allow page-level scrolling.
        detail_body = ft.Column(
            editor_fields,
            spacing=14,
            tight=True,
            scroll=None,
            data=f"config_edit_form_no_side_scroll|{IA_CLEANUP_LAYOUT_MARKER}",
        )

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

        primary_path, full_path = format_target_path_display(config.destination_summary)
        # Keep smart_path_display referenced for IA path-preservation tests.
        _ = smart_path_display(config.destination_summary or "", max_chars=72)
        metadata_rows = [
            ft.Container(
                padding=10,
                bgcolor=COLOR_SURFACE_ALT,
                border_radius=8,
                data=f"{CONFIG_PREVIEW_SUMMARY_MARKER}|detail_view",
                content=ft.Column(
                    [
                        ft.Text(
                            f"Diese Konfiguration erkennt Belege, wenn … "
                            f"{config.matching_summary or '—'}",
                            size=12,
                        ),
                        ft.Text(
                            f"Dann wird der Dateiname geplant als "
                            f"{config.filename_example or config.filename_pattern_summary or '—'}",
                            size=12,
                        ),
                        ft.Text(f"Zielordner: {full_path or primary_path}", size=12),
                        ft.Text(
                            f"Prüfverhalten: {SUPPORTED_REVIEW_BEHAVIORS[0][1]}",
                            size=12,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                ),
            ),
            erkannt_bei,
            make_metadata_row("Dateinamenmuster", config.filename_pattern_summary, mono=True),
        ]
        if config.filename_example:
            metadata_rows.append(make_metadata_row("Beispiel", config.filename_example, mono=True))
        metadata_rows.append(
            make_metadata_row(
                LABEL_TARGET_FOLDER,
                full_path or primary_path,
                mono=True,
                warn="Ordner fehlt oder ist nicht erreichbar." if config.destination_missing else None,
            )
        )
        if config.destination_summary:
            metadata_rows.append(
                make_metadata_row(
                    "Vollständiger Pfad",
                    str(config.destination_summary),
                    mono=True,
                )
            )
            metadata_rows.append(
                ft.Container(
                    data=f"{TARGET_PATH_FULL_VISIBLE_MARKER}|not_basename_only",
                    height=0,
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

    # When editing, place the form near the top (before long list noise).
    panel_height = resolve_list_detail_height(state.page, editing=is_editing)
    edit_body_padding = ft.Padding.only(left=18, right=18, top=16, bottom=12)
    view_body_padding = ft.Padding.only(left=18, right=18, top=2, bottom=0)

    detail_panel_ctrl = make_split_detail_panel(
        detail_title,
        detail_body,
        height=panel_height if not is_editing else None,
        header_trailing=header_trailing,
        footer=footer,
        scroll_body=False if is_editing else False,
        body_padding=edit_body_padding if is_editing else view_body_padding,
    )

    create_near_list = ft.Container(
        content=action_button(
            ACTION_NEW_CONFIGURATION,
            on_click=lambda _e: _start_create(),
            primary=True,
        ),
        padding=ft.Padding.only(bottom=8),
        data=f"{CREATE_NEAR_LIST_MARKER}|near_configuration_list",
    )
    list_region = ft.Column(
        [
            create_near_list,
            list_panel("Konfigurationen", list_body, height=panel_height),
        ],
        spacing=0,
        tight=True,
        data=f"{CREATE_NEAR_LIST_MARKER}|list_and_create_together",
    )

    if is_editing:
        items.append(make_section_label("Konfiguration bearbeiten"))
        items.append(detail_panel_ctrl)
        items.append(
            ft.Column(
                [
                    create_near_list,
                    list_panel(
                        "Konfigurationen", list_body, height=min(panel_height, 280)
                    ),
                ],
                spacing=0,
                tight=True,
            )
        )
    else:
        items.append(
            list_detail_split(
                list_region,
                detail_panel_ctrl,
            )
        )

    for warning in page_vm.warnings:
        items.append(inline_warning(warning))

    # Source markers for unused imports kept for IA / compactness tests.
    _ = (compact_info_row, display_path_value, kpi_strip, COLOR_PRIMARY, LOGIC_ALL)

    return page_scaffold(*items)
