"""Track-B UI-v2 Second UX Cleanup (2026-07-24).

Menu compactness, workspace file pairs, profile/config simplification,
review document list — UI/UX only. No productive processing.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.navigation import (
    ADMIN_NAV,
    DAILY_NAV,
    NAV_SETTINGS,
)
from invoice_tool.ui_v2.pages.review import (
    build_review_page_vm,
    open_review_document_preview,
    review_summary_display_name,
    set_open_review_item_id,
)
from invoice_tool.ui_v2.pages.settings import build_settings_page_vm
from invoice_tool.ui_v2.pages.workspace import (
    START_CTA_LABEL,
    build_workspace_folder_selection_vm,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_CHANGE_PROFILE,
    ACTION_CREATE_CONFIGURATION,
    ACTION_CREATE_PROFILE,
    ACTION_EDIT_CONFIGURATIONS,
    ACTION_NEW_CONFIGURATION,
    ACTION_SHOW_DOCUMENT,
    ACTION_WORKSPACE_EDIT,
    LABEL_ACTIVE_EXPLAIN,
    LABEL_INPUT_FILES,
    LABEL_ORIGINAL_FILE,
    LABEL_PROPOSED_FILENAME,
    LABEL_PROPOSED_OUTPUT_FILES,
    MENU_COMPACT_ROW_MARKER,
    MSG_NO_RESULT_YET,
    MSG_REVIEW_SAFETY_ONCE,
    MSG_RUN_ACTIVITY,
    MSG_START_HELPER,
    MSG_WHY_MISSING_PAYMENT,
    MSG_WHY_NOT_AMEX,
    MSG_WHY_PAYPAL_DETECTED,
    MSG_WHY_STORNO,
    PICK_INPUT_FOLDER_CHANGE,
    PICK_INPUT_FOLDER_CHOOSE,
    PICK_OUTPUT_FOLDER_CHANGE,
    PICK_OUTPUT_FOLDER_CHOOSE,
    REVIEW_DOCUMENT_PREVIEW_MARKER,
    SECOND_UX_CLEANUP_MARKER,
    SECTION_DEV_DIAGNOSE,
    SECTION_TECHNISCHE,
    START_CTA_STRONG,
    WORKSPACE_CTA_PRIMARY_MARKER,
    WORKSPACE_FILE_PAIR_MARKER,
    WORKSPACE_SHARED_SUMMARY_MARKER,
    clean_user_facing_filename,
    truncate_filename_display,
)

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
PROFILES = ROOT / "invoice_tool" / "ui_v2" / "pages" / "profiles.py"
CONFIGS = ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py"
SETTINGS = ROOT / "invoice_tool" / "ui_v2" / "pages" / "settings.py"
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
NAV = ROOT / "invoice_tool" / "ui_v2" / "navigation.py"
SHELL = ROOT / "invoice_tool" / "ui_v2" / "shell.py"
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
ORACLE_SCRIPT = ROOT / "scripts" / "dev" / "track_b_automated_smoke_oracle.py"
TRACK_A_TEST = ROOT / "tests" / "test_track_a_internal_app_protection.py"

CORE_PROTECTED = (
    "invoice_tool/run.py",
    "invoice_tool/processing.py",
    "invoice_tool/routing.py",
    "invoice_tool/routing_guards.py",
    "invoice_tool/classification.py",
    "invoice_tool/target_routing.py",
    "invoice_tool/core_dry_run.py",
)
FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)


def _boettcher_state() -> UiV2State:
    planned = ProcessingPlannedDestination(
        document_name="FA011466.pdf",
        planned_path="preview/geplant/paypal/x.pdf",
        destination_label="PayPal",
        preview_only=True,
        applied=False,
        suggested_filename="REVIEW_REQUIRED__SUGGESTED__2026-05-11_er_LUMITOP_476,00_paypal.pdf",
        supplier="LUMITOP",
        counterparty_name="LUMITOP",
        invoice_date="2026-05-11",
        amount="476,00",
        selected_amount="476,00",
        selected_payment_field="paypal",
        payment_account="paypal",
        selected_art="er",
        matched_configuration_name="PayPal",
        configuration_coverage_status="matched",
        user_guidance="PayPal erkannt.",
    )
    planned2 = ProcessingPlannedDestination(
        document_name="Böttcher Rechnung.pdf",
        planned_path="preview/geplant/card/x.pdf",
        destination_label="Karte",
        preview_only=True,
        applied=False,
        suggested_filename="REVIEW_REQUIRED__SUGGESTED__2026-05-23_er_Böttcher_AG_84,39_card.pdf",
        supplier="Böttcher AG",
        counterparty_name="Böttcher AG",
        invoice_date="2026-05-23",
        amount="84,39",
        selected_amount="84,39",
        selected_payment_field="card",
        payment_account="card",
        selected_art="er",
        matched_configuration_name="Karte",
        configuration_coverage_status="matched",
        user_guidance="Kartenzahlung erkannt, aber AMEX ist nicht belegt.",
    )
    run = ProcessingRunState(
        status="completed",
        message="Vorschau-Prüfung abgeschlossen.",
        run_id="second-ux-1",
        review_items=(
            ProcessingReviewItem(
                document_name="Böttcher Rechnung.pdf",
                reason="Prüfung erforderlich",
                status_label="unklar",
                document_id="doc-boettcher",
            ),
        ),
        planned_destinations=(planned, planned2),
        planned_destination_count=2,
        outcome_kind="all_review",
    )
    state = UiV2State(processing_run_state=run)
    state.review_preview_ui.selected_item_key = "doc-boettcher"
    set_open_review_item_id(state, "doc-boettcher")
    return state


# --- Menu / Settings ---


def test_01_main_menu_row_spacing_compact() -> None:
    src = SHELL.read_text(encoding="utf-8")
    assert "MENU_COMPACT_ROW_MARKER" in src
    assert MENU_COMPACT_ROW_MARKER == "menu_compact_row_spacing_v2"
    assert "vertical=2" in src or "top=3" in src
    assert "VisualDensity.COMPACT" in src or "dense=True" in src


def test_02_advanced_settings_not_normal_user_page() -> None:
    assert NAV_SETTINGS not in {i for i, _, _ in DAILY_NAV}
    label = ADMIN_NAV[0][1]
    assert "Erweiterte Einstellungen" not in label
    assert "Diagnose" in label or "Entwickler" in label
    vm = build_settings_page_vm(UiV2State())
    assert "Erweiterte Einstellungen" not in vm.title
    assert "Diagnose" in vm.title or "Entwickler" in vm.title


def test_03_developer_diagnosis_not_primary_workflow() -> None:
    src = SHELL.read_text(encoding="utf-8")
    assert "is_track_b_dev_defaults_enabled" in src
    assert "nav_dev_diagnose_collapsed_secondary" in src or "initially_expanded=False" in src
    assert SECTION_DEV_DIAGNOSE == "Entwickler / Diagnose"


def test_04_developer_diagnosis_accessible_advanced_only() -> None:
    assert [item[0] for item in ADMIN_NAV] == [NAV_SETTINGS]
    src = SETTINGS.read_text(encoding="utf-8")
    assert "SECTION_DEV_DIAGNOSE" in src or "Entwickler" in src


# --- Workspace top summary ---


def test_05_profile_config_shared_summary_frame() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "WORKSPACE_SHARED_SUMMARY_MARKER" in src
    assert "_workspace_profile_config_summary" in src
    assert "SECOND_UX_CLEANUP_MARKER" in src
    assert WORKSPACE_SHARED_SUMMARY_MARKER.startswith("workspace_profile_config")


def test_06_profile_config_responsive_wrap_marker() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "wrap_responsive" in src
    assert "ResponsiveRow" in src
    assert 'col={"xs": 12, "md": 6}' in src


def test_07_both_columns_use_bearbeiten() -> None:
    assert ACTION_CHANGE_PROFILE == ACTION_WORKSPACE_EDIT == "Bearbeiten"
    assert ACTION_EDIT_CONFIGURATIONS == "Bearbeiten"


def test_08_buttons_navigate_different_targets() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "_navigate_to_profiles" in src
    assert "_navigate_to_configurations" in src
    assert src.index("_navigate_to_profiles") != src.index("_navigate_to_configurations")


def test_09_profile_config_equal_hierarchy() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "equal_hierarchy" in src
    assert "workspace_profile_name_equal_hierarchy" in src
    assert "workspace_config_name_equal_hierarchy" in src


# --- Folder cards ---


def test_10_input_button_waehlen_when_empty() -> None:
    state = UiV2State()
    state.workspace_input_folder_override = ""
    state.workspace_output_folder_override = ""
    vm = build_workspace_folder_selection_vm(state)
    assert vm.input_pick_label == PICK_INPUT_FOLDER_CHOOSE


def test_11_input_button_aendern_when_selected() -> None:
    state = UiV2State()
    state.workspace_input_folder_override = "/tmp/controlled-input"
    vm = build_workspace_folder_selection_vm(state)
    assert vm.input_pick_label == PICK_INPUT_FOLDER_CHANGE


def test_12_output_button_waehlen_when_empty() -> None:
    state = UiV2State()
    state.workspace_output_folder_override = ""
    vm = build_workspace_folder_selection_vm(state)
    assert vm.output_pick_label == PICK_OUTPUT_FOLDER_CHOOSE


def test_13_output_button_aendern_when_selected() -> None:
    state = UiV2State()
    state.workspace_output_folder_override = "/tmp/controlled-output"
    vm = build_workspace_folder_selection_vm(state)
    assert vm.output_pick_label == PICK_OUTPUT_FOLDER_CHANGE


def test_14_selected_folders_show_checkmark() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "folder_selected_checkmark" in src
    assert "CHECK_CIRCLE" in src


def test_15_input_output_visually_distinct() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "FOLDER_INPUT_BG" in src
    assert "FOLDER_OUTPUT_BG" in src


def test_16_full_path_accessible() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "tooltip=full" in src or "full_path" in src
    assert "folder_path_" in src


# --- Run CTA ---


def test_17_cta_strong_label() -> None:
    assert START_CTA_LABEL == START_CTA_STRONG == "Belege jetzt prüfen"


def test_18_safety_helper_nur_vorschau() -> None:
    assert MSG_START_HELPER == "Nur Vorschau — Originale bleiben unverändert."
    assert MSG_REVIEW_SAFETY_ONCE == MSG_START_HELPER


def test_19_cta_visually_primary() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "WORKSPACE_CTA_PRIMARY_MARKER" in src
    assert "primary_cta" in src
    assert "primary=True" in src
    assert WORKSPACE_CTA_PRIMARY_MARKER.startswith("workspace_run_cta")


def test_20_cta_directly_after_folder_cards() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert src.index("folder_selection_panel") < src.index("run_start_panel")
    assert src.index("run_start_panel") < src.index("file_pair_panel")


def test_21_running_state_activity() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert MSG_RUN_ACTIVITY in src or "MSG_RUN_ACTIVITY" in src
    assert "folder_run_activity_marker" in src or "ProgressRing" in src
    assert "Prüfung läuft" in MSG_RUN_ACTIVITY


# --- Workspace file pairs ---


def test_22_paired_list_headers() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "LABEL_INPUT_FILES" in src
    assert "LABEL_PROPOSED_OUTPUT_FILES" in src
    assert "WORKSPACE_FILE_PAIR_MARKER" in src
    assert LABEL_INPUT_FILES == "Eingangsdateien"
    assert LABEL_PROPOSED_OUTPUT_FILES == "Vorgeschlagene Ausgabedateien"
    assert WORKSPACE_FILE_PAIR_MARKER.startswith("workspace_input_output")


def test_23_original_and_output_same_row() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "same_row" in src
    assert "workspace_file_pair_row" in src


def test_24_no_numbering_jumps() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "stable_order" in src
    assert "_collect_workspace_file_pairs" in src


def test_25_placeholder_before_result() -> None:
    assert MSG_NO_RESULT_YET == "Noch kein Ergebnis vorhanden."
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "MSG_NO_RESULT_YET" in src


def test_26_green_completed_not_primary() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "secondary_not_primary" in src or "Laufzahlen (erweitert)" in src
    assert 'details_title="Details anzeigen"' not in src or "tone == \"completed\"" in src


def test_27_file_pair_row_navigates_review() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "nav_review" in src
    assert "_navigate_to_review" in src


def test_28_long_filenames_truncate_full_accessible() -> None:
    long_name = "a" * 60 + ".pdf"
    shown = truncate_filename_display(long_name, max_chars=40)
    assert shown.endswith("…")
    assert len(shown) <= 40
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "file_pair_source_full" in src
    assert "tooltip=" in src


# --- Profiles ---


def test_29_profile_slim_summary_band() -> None:
    src = PROFILES.read_text(encoding="utf-8")
    assert "profiles_active_summary" in src
    assert "slim_summary_band" in src


def test_30_profile_list_primary() -> None:
    src = PROFILES.read_text(encoding="utf-8")
    assert "compact_list_item" in src
    assert "ACTION_CREATE_PROFILE" in src


def test_31_new_profile_visible() -> None:
    src = PROFILES.read_text(encoding="utf-8")
    assert ACTION_CREATE_PROFILE == "Profil erstellen"
    assert "ACTION_CREATE_PROFILE" in src


def test_32_active_wording_clear() -> None:
    assert LABEL_ACTIVE_EXPLAIN == "aktiv = wird bei der Prüfung verwendet"
    src = PROFILES.read_text(encoding="utf-8")
    assert "LABEL_ACTIVE_EXPLAIN" in src


def test_33_drafts_import_export_not_primary() -> None:
    src = PROFILES.read_text(encoding="utf-8")
    assert "profiles_drafts_not_primary" in src or "not_primary" in src
    assert "initially_expanded=False" in src


# --- Configurations ---


def test_34_config_mirrors_profile_structure() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "mirrors_profile" in src
    assert "slim_summary_band" in src


def test_35_actual_used_configuration_not_draft_wording() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "In-Memory-Entwurf ohne private Vorbelegung" not in src
    assert "nicht die aktive Arbeitskonfiguration" in src.lower() or "SECTION_IMPORT_EXPORT" in src


def test_36_config_list_primary() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "compact_list_item" in src
    assert "ACTION_NEW_CONFIGURATION" in src or ACTION_NEW_CONFIGURATION in src


def test_37_neue_konfiguration_erstellen_clickable() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "on_click=lambda _e: _start_create()" in src
    assert ACTION_NEW_CONFIGURATION == "Neue Konfiguration erstellen"


def test_38_create_form_konfiguration_erstellen() -> None:
    assert ACTION_CREATE_CONFIGURATION == "Konfiguration erstellen"
    src = CONFIGS.read_text(encoding="utf-8")
    assert "ACTION_CREATE_CONFIGURATION" in src


def test_39_edit_form_no_side_scrollbar() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "config_edit_form_no_side_scroll" in src
    assert "scroll=None" in src


def test_40_edit_form_page_scroll_visible() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert 'make_section_label("Konfiguration bearbeiten")' in src or "Konfiguration bearbeiten" in src


def test_41_internal_hints_not_primary() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "config_drafts_not_primary" in src or "not_primary" in src


def test_42_target_path_full_accessible() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "smart_path_display" in src


# --- Review ---


def test_43_no_internal_sandbox_heading_primary() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "einfache Prüfung: erkennen" not in src.lower()
    assert "ohne Technikjargon" not in src
    assert "Sandbox Final Write Test" not in src.split("build_review_page")[-1][:800]


def test_44_faelle_not_primary_wording() -> None:
    from invoice_tool.ui_v2.track_b_smoke_debug_copy import SECTION_BEREIT, SECTION_PRUEFUNG

    assert "Fälle" not in SECTION_BEREIT
    assert "Fälle" not in SECTION_PRUEFUNG
    assert "Dokumente" in SECTION_PRUEFUNG


def test_45_duplicate_summary_list_removed() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "no_duplicate_summary_list" in src
    # Panels exist but are not called as primary list before accordion.
    assert "items.append(_ready_cases_panel" not in src
    assert "items.append(_review_cases_panel" not in src


def test_46_full_original_filename_shown() -> None:
    state = _boettcher_state()
    vm = build_review_page_vm(state)
    assert vm.list_items
    row = next(r for r in vm.list_items if "Böttcher" in (r.source_filename or ""))
    name = review_summary_display_name(row)
    assert name == "Böttcher Rechnung.pdf" or "Böttcher" in name
    assert name != "Böttcher AG" or row.source_filename


def test_47_supplier_date_amount_secondary() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "review_secondary_metadata_supplier_date_amount" in src


def test_48_side_by_side_original_proposed() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "review_filename_side_by_side" in src
    assert LABEL_ORIGINAL_FILE in src or "LABEL_ORIGINAL_FILE" in src
    assert LABEL_PROPOSED_FILENAME in src or "LABEL_PROPOSED_FILENAME" in src


def test_49_row_expands_detail_below() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "expand_detail_below" in src or "INLINE_DETAIL_UNDER_SELECTED_CARD" in src
    assert "render_review_inline_detail" in src


def test_50_original_filename_preview_marker() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "REVIEW_DOCUMENT_PREVIEW_MARKER" in src
    assert "ACTION_SHOW_DOCUMENT" in src
    assert REVIEW_DOCUMENT_PREVIEW_MARKER.startswith("review_document_preview")
    assert ACTION_SHOW_DOCUMENT == "Dokument anzeigen"


def test_51_preview_open_non_mutating() -> None:
    state = UiV2State()
    state.workspace_input_folder_override = "/tmp/does-not-exist-second-ux"
    msg = open_review_document_preview(state, "missing.pdf")
    assert "non_mutating" in msg or REVIEW_DOCUMENT_PREVIEW_MARKER in msg
    assert "Keine Änderung" in msg or "nicht gefunden" in msg
    src = REVIEW.read_text(encoding="utf-8")
    assert "non_mutating" in src
    # No mutation APIs in preview helper.
    preview_fn = REVIEW.read_text(encoding="utf-8")
    assert "shutil.move" not in preview_fn
    assert "os.rename" not in preview_fn.split("def open_review_document_preview")[1].split("def ")[0]


def test_52_user_filename_no_review_required() -> None:
    raw = "REVIEW_REQUIRED__SUGGESTED__2026-05-23_er_Böttcher_AG_84,39_card.pdf"
    clean = clean_user_facing_filename(raw)
    assert "REVIEW_REQUIRED" not in clean


def test_53_user_filename_no_suggested() -> None:
    raw = "SUGGESTED__2026-05-23_er_Böttcher_AG_84,39_card.pdf"
    clean = clean_user_facing_filename(raw)
    assert not clean.startswith("SUGGESTED")


def test_54_missing_payment_guidance() -> None:
    assert MSG_WHY_MISSING_PAYMENT == "Zahlungsart fehlt. Bitte Zahlungsart prüfen."


def test_55_card_guidance() -> None:
    assert MSG_WHY_NOT_AMEX == "Kartenzahlung erkannt, aber AMEX ist nicht belegt."


def test_56_paypal_guidance() -> None:
    assert MSG_WHY_PAYPAL_DETECTED == "PayPal erkannt."


def test_57_storno_guidance() -> None:
    assert MSG_WHY_STORNO == "Storno erkannt."


def test_58_technical_details_collapsed() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert SECTION_TECHNISCHE in src or "SECTION_TECHNISCHE" in src
    assert "initially_expanded=False" in src


# --- Safety ---


def test_59_no_auto_run() -> None:
    for path in (WORKSPACE, REVIEW):
        assert "auto_start_run(" not in path.read_text(encoding="utf-8")


def test_60_no_run_once() -> None:
    for path in (WORKSPACE, REVIEW, PROFILES, CONFIGS, SETTINGS):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                assert name != "run_once"


def test_61_no_production_final_write() -> None:
    from invoice_tool.ui_v2.finalization_readiness import FINAL_WRITE_ALLOWED_IN_THIS_PHASE

    assert FINAL_WRITE_ALLOWED_IN_THIS_PHASE is False
    blob = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (WORKSPACE, REVIEW, SETTINGS, COPY_MOD)
    )
    assert "final_write_allowed_for_production=True" not in blob
    assert "final_write_allowed_for_production = True" not in blob


def test_62_no_real_invoice_folders() -> None:
    blob = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (WORKSPACE, REVIEW, PROFILES, CONFIGS, SETTINGS, NAV, SHELL)
    )
    for folder in FORBIDDEN_FOLDERS:
        assert folder not in blob


def test_63_oracle_script_exists() -> None:
    assert ORACLE_SCRIPT.is_file()


def test_64_track_a_protection_test_exists() -> None:
    assert TRACK_A_TEST.is_file()


def test_65_processing_core_unchanged_paths_exist() -> None:
    for rel in CORE_PROTECTED:
        assert (ROOT / rel).is_file()


def test_66_second_ux_marker_present() -> None:
    assert SECOND_UX_CLEANUP_MARKER == "track_b_ui_v2_second_ux_cleanup_v1"
    assert "SECOND_UX_CLEANUP_MARKER" in WORKSPACE.read_text(encoding="utf-8")
    assert "SECOND_UX_CLEANUP_MARKER" in REVIEW.read_text(encoding="utf-8")
    assert SECOND_UX_CLEANUP_MARKER in COPY_MOD.read_text(encoding="utf-8")
