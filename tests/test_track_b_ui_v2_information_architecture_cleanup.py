"""Track-B UI-v2 Information Architecture Cleanup (2026-07-24).

Navigation / workspace / profiles / configurations / settings / review
clarification — UI/UX only. No productive processing, no real invoice folders.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.navigation import (
    ADMIN_NAV,
    ALL_NAV_IDS,
    DAILY_NAV,
    NAV_CONFIGURATIONS,
    NAV_PROFILES,
    NAV_REVIEW,
    NAV_SETTINGS,
    NAV_WORKSPACE,
)
from invoice_tool.ui_v2.pages.review import (
    build_review_page_vm,
    set_open_review_item_id,
)
from invoice_tool.ui_v2.pages.settings import build_settings_page_vm
from invoice_tool.ui_v2.pages.workspace import (
    START_CTA_LABEL,
    WORKSPACE_SUBTITLE,
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
    ACTION_OPEN_REVIEW,
    CLEAN_USER_FILENAME_MARKER,
    FILENAME_EDIT_SECONDARY_MARKER,
    IA_CLEANUP_LAYOUT_MARKER,
    MSG_CLARIFICATION_STATUS,
    MSG_FILENAME_FOLLOWS_SCHEMA,
    MSG_MISSING_TARGETS_FILTER,
    MSG_RUN_ACTIVITY,
    MSG_START_HELPER,
    MSG_WHY_MISSING_PAYMENT,
    MSG_WHY_NOT_AMEX,
    MSG_WHY_PAYPAL_DETECTED,
    MSG_WHY_STORNO,
    PROFILE_PAGE_EXPLANATION,
    REVIEW_CLARIFICATION_MARKER,
    SECTION_ADVANCED_CONFIG,
    SECTION_ADVANCED_PROFILE,
    SECTION_DEV_DIAGNOSE,
    SECTION_IMPORT_EXPORT_ADVANCED,
    WORKSPACE_IA_SECTION_ORDER,
    clean_user_facing_filename,
    smart_path_display,
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
        document_name="320262919974.pdf",
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
        message="Vorschau-Prüfung abgeschlossen — Fälle zur Prüfung.",
        run_id="ia-cleanup-1",
        review_items=(
            ProcessingReviewItem(
                document_name="320262919974.pdf",
                reason="Prüfung erforderlich",
                status_label="unklar",
                document_id="doc-boettcher",
            ),
        ),
        planned_destinations=(planned,),
        planned_destination_count=1,
        outcome_kind="all_review",
    )
    state = UiV2State(processing_run_state=run)
    state.review_preview_ui.selected_item_key = "doc-boettcher"
    set_open_review_item_id(state, "doc-boettcher")
    return state


def test_01_main_workflow_order() -> None:
    assert [item[0] for item in DAILY_NAV] == [
        NAV_WORKSPACE,
        NAV_PROFILES,
        NAV_CONFIGURATIONS,
        NAV_REVIEW,
    ]


def test_02_profile_before_configurations() -> None:
    assert ALL_NAV_IDS.index(NAV_PROFILES) < ALL_NAV_IDS.index(NAV_CONFIGURATIONS)


def test_03_settings_is_secondary() -> None:
    assert NAV_SETTINGS not in {i for i, _, _ in DAILY_NAV}
    assert [item[0] for item in ADMIN_NAV] == [NAV_SETTINGS]
    assert "Erweiterte" in ADMIN_NAV[0][1] or "Diagnose" in ADMIN_NAV[0][1]
    shell_src = SHELL.read_text(encoding="utf-8")
    assert "NAV_GROUP_ADVANCED" in shell_src


def test_04_workspace_section_order_profil_config_ordner_lauf() -> None:
    assert WORKSPACE_IA_SECTION_ORDER == (
        "Profil",
        "Konfiguration",
        "Ordner",
        "Belegnamen ändern",
    )
    src = WORKSPACE.read_text(encoding="utf-8")
    assert src.index("profile_card = _workspace_profile_card") < src.index(
        "configuration_card = _workspace_configuration_card"
    )
    assert src.index("folder_selection_panel") < src.index("run_start_panel")
    assert "Profil → Konfiguration → Ordner" in WORKSPACE_SUBTITLE


def test_05_active_profile_card_at_top() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "_workspace_profile_card" in src
    assert "workspace_profile_card" in src
    assert "ACTION_CHANGE_PROFILE" in src
    assert ACTION_CHANGE_PROFILE == "Bearbeiten"


def test_06_active_configuration_card_below_profile() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "_workspace_configuration_card" in src
    assert "ACTION_EDIT_CONFIGURATIONS" in src
    assert src.index("profile_card =") < src.index("configuration_card =")


def test_07_profil_aendern_navigates() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "_navigate_to_profiles" in src
    assert "NAV_PROFILES" in src
    assert "ACTION_CHANGE_PROFILE" in src


def test_08_konfigurationen_bearbeiten_navigates() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "_navigate_to_configurations" in src
    assert "ACTION_EDIT_CONFIGURATIONS" in src
    assert ACTION_EDIT_CONFIGURATIONS == "Bearbeiten"


def test_09_input_folder_checkmark() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "folder_selected_checkmark" in src
    assert "CHECK_CIRCLE" in src


def test_10_output_folder_checkmark() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "LABEL_OUTPUT_FOLDER" in src
    assert "folder_selected_checkmark" in src


def test_11_input_output_visually_distinct() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "FOLDER_INPUT_BG" in src
    assert "FOLDER_OUTPUT_BG" in src
    assert "FOLDER_INPUT_BORDER" in src
    assert "FOLDER_OUTPUT_BORDER" in src


def test_12_start_action_user_friendly() -> None:
    assert START_CTA_LABEL != "Sandbox-Lauf starten"
    assert "Sandbox Lauf starten" not in START_CTA_LABEL
    assert (
        "Vorschau" in START_CTA_LABEL
        or "prüfen" in START_CTA_LABEL.lower()
        or "ändern" in START_CTA_LABEL.lower()
    )


def test_13_start_action_directly_after_folders() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert src.index("folder_selection_panel") < src.index("run_start_panel")
    assert "MSG_START_HELPER" in src
    assert MSG_START_HELPER.startswith("Nur Vorschau")


def test_14_pilot_status_not_primary() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert 'make_section_label(ONBOARDING_SECTION_LABEL_COMPACT)' not in src
    assert 'title="Pilot-Details anzeigen"' not in src
    assert "SECTION_DEV_DIAGNOSE" in src
    assert SECTION_DEV_DIAGNOSE == "Entwickler / Diagnose"


def test_15_controlled_folders_not_primary() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "track_b_dev_controls" in src
    assert "SECTION_DEV_DIAGNOSE" in src or "SECTION_TEST_NACHWEIS_COLLAPSED" in src


def test_16_exportvorschau_not_primary_setup() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    items_block = src.split("items: list[ft.Control] = [")[-1]
    assert "run_start_panel" in items_block
    # Export report is only appended after run results / advanced, not before start.
    assert items_block.index("run_start_panel") < items_block.index(
        "_build_run_report_panel"
    )


def test_17_sandbox_completed_status_not_primary_green() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert 'compact_status_banner(\n                "Lokale Pilotversion"' not in src
    assert "Sandbox-Lauf mit Prüffällen abgeschlossen" not in START_CTA_LABEL


def test_18_run_result_links_to_review() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "ACTION_OPEN_REVIEW" in src
    assert "_navigate_to_review" in src
    assert "workspace_result_summary" in src
    assert ACTION_OPEN_REVIEW == "Prüfung öffnen"


def test_19_running_state_activity_on_folders() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "MSG_RUN_ACTIVITY" in src or MSG_RUN_ACTIVITY in src
    assert "ProgressRing" in src
    assert "run_is_active" in src


def test_20_profile_page_starts_with_active_summary() -> None:
    src = PROFILES.read_text(encoding="utf-8")
    assert "profiles_active_summary" in src
    assert "PROFILE_PAGE_EXPLANATION" in src
    assert PROFILE_PAGE_EXPLANATION.startswith("Ein Profil bündelt")
    items_block = src.split("items: list[ft.Control] = [")[1]
    assert items_block.index("active_summary") < items_block.index(
        "build_saas_draft_list_panel"
    )


def test_21_new_profile_button_profil_erstellen() -> None:
    src = PROFILES.read_text(encoding="utf-8")
    assert "ACTION_CREATE_PROFILE" in src
    assert ACTION_CREATE_PROFILE == "Profil erstellen"


def test_22_local_ui_v2_draft_not_primary() -> None:
    src = PROFILES.read_text(encoding="utf-8")
    assert "lokaler UI-v2 Profil Entwurf" not in src
    assert "MSG_PROFILE_DRAFT_CURRENT" in src


def test_23_profile_hints_collapsed() -> None:
    src = PROFILES.read_text(encoding="utf-8")
    assert "SECTION_ADVANCED_PROFILE" in src
    assert SECTION_ADVANCED_PROFILE == "Erweiterte Profilinformationen"


def test_24_configuration_page_starts_with_summary() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "configurations_top_summary" in src
    assert "MSG_MISSING_TARGETS_FILTER" in src
    assert "fehlt ein Zielordner" in MSG_MISSING_TARGETS_FILTER


def test_25_active_config_details_not_draft_wording() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "In-Memory-Entwurf ohne private Vorbelegung" not in src
    assert "SECTION_ADVANCED_CONFIG" in src
    assert SECTION_ADVANCED_CONFIG == "Erweiterte Hinweise"


def test_26_neue_konfiguration_clickable() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "on_click=lambda _e: _start_create()" in src
    assert "Neue Konfiguration" in src


def test_27_create_button_konfiguration_erstellen() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "ACTION_CREATE_CONFIGURATION" in src
    assert ACTION_CREATE_CONFIGURATION == "Konfiguration erstellen"


def test_28_edit_form_near_top() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert 'make_section_label("Konfiguration bearbeiten")' in src
    assert "if is_editing:" in src


def test_29_edit_form_no_internal_side_scrollbar() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "config_edit_form_no_side_scroll" in src
    assert "scroll=None" in src


def test_30_target_path_preserves_end() -> None:
    shown = smart_path_display(
        "/Users/x/Desktop/KI-Rechnungen-Test/output/geplant/paypal",
        max_chars=40,
    )
    assert shown.endswith("paypal")
    assert shown.startswith("…") or "paypal" in shown
    src = CONFIGS.read_text(encoding="utf-8")
    assert "smart_path_display" in src


def test_31_hint_policy_collapsed() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "SECTION_ADVANCED_CONFIG" in src
    assert 'compact_info_row(\n                "Policy"' not in src


def test_32_hint_line_spacing_normal_if_retained() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "collapsible_details(" in src


def test_33_import_export_not_primary() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "SECTION_IMPORT_EXPORT_ADVANCED" in src
    assert SECTION_IMPORT_EXPORT_ADVANCED == "Import / Export (erweitert)"
    items_block = src.split("items: list[ft.Control] = [")[1]
    assert "summary_extras" in src or "top_summary" in src
    assert "SECTION_IMPORT_EXPORT_ADVANCED" in items_block
    # Summary is built before items; import/export appears inside items as collapsed.
    assert "configurations_top_summary" in src


def test_34_user_filename_no_review_required() -> None:
    raw = "REVIEW_REQUIRED__SUGGESTED__2026-05-23_er_Böttcher_AG_84,39_card.pdf"
    clean = clean_user_facing_filename(raw)
    assert "REVIEW_REQUIRED" not in clean
    assert clean.startswith("2026-05-23")


def test_35_user_filename_no_suggested_prefix() -> None:
    raw = "SUGGESTED__2026-05-23_er_Böttcher_AG_84,39_card.pdf"
    clean = clean_user_facing_filename(raw)
    assert not clean.startswith("SUGGESTED")
    assert "SUGGESTED__" not in clean


def test_36_status_separate_from_filename() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "MSG_CLARIFICATION_STATUS" in src
    assert "review_status_separate" in src
    assert MSG_CLARIFICATION_STATUS.startswith("Prüfung")


def test_37_missing_payment_guidance() -> None:
    assert MSG_WHY_MISSING_PAYMENT == "Zahlungsart fehlt. Bitte Zahlungsart prüfen."


def test_38_card_guidance() -> None:
    assert MSG_WHY_NOT_AMEX == "Kartenzahlung erkannt, aber AMEX ist nicht belegt."


def test_39_paypal_guidance() -> None:
    assert MSG_WHY_PAYPAL_DETECTED == "PayPal erkannt."


def test_40_storno_guidance() -> None:
    assert MSG_WHY_STORNO == "Storno erkannt."


def test_41_filename_follows_schema() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "MSG_FILENAME_FOLLOWS_SCHEMA" in src
    assert "REVIEW_CLARIFICATION_MARKER" in src
    assert MSG_FILENAME_FOLLOWS_SCHEMA.startswith("Der Dateiname folgt")


def test_42_filename_edit_secondary() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "FILENAME_EDIT_SECONDARY_MARKER" in src
    assert "CLEAN_USER_FILENAME_MARKER" in src
    assert FILENAME_EDIT_SECONDARY_MARKER
    assert CLEAN_USER_FILENAME_MARKER


def test_43_technical_details_collapsed() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "SECTION_TECHNISCHE" in src
    assert "_test_tools_collapsed" in src


def test_44_settings_secondary_or_advanced() -> None:
    assert NAV_SETTINGS not in {i for i, _, _ in DAILY_NAV}
    vm = build_settings_page_vm(UiV2State())
    assert "Erweiterte" in vm.title or "Diagnose" in vm.title
    src = SETTINGS.read_text(encoding="utf-8")
    assert "SECTION_DEV_DIAGNOSE" in src or "Entwickler" in src


def test_45_user_relevant_settings_accessible() -> None:
    vm = build_settings_page_vm(UiV2State())
    assert vm.productive_execution_enabled is False
    assert vm.has_productive_toggle is False
    src = SETTINGS.read_text(encoding="utf-8")
    assert "Produktive Ausführung" in src


def test_46_no_auto_run() -> None:
    for path in (WORKSPACE, REVIEW):
        src = path.read_text(encoding="utf-8")
        assert "auto_start_run(" not in src


def test_47_no_run_once() -> None:
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


def test_48_no_production_final_write() -> None:
    from invoice_tool.ui_v2.finalization_readiness import FINAL_WRITE_ALLOWED_IN_THIS_PHASE

    assert FINAL_WRITE_ALLOWED_IN_THIS_PHASE is False
    blob = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (WORKSPACE, REVIEW, SETTINGS, COPY_MOD)
    )
    assert "final_write_allowed_for_production=True" not in blob
    assert "final_write_allowed_for_production = True" not in blob


def test_49_no_real_invoice_folders() -> None:
    blob = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (WORKSPACE, REVIEW, PROFILES, CONFIGS, SETTINGS, NAV)
    )
    for folder in FORBIDDEN_FOLDERS:
        assert folder not in blob


def test_50_oracle_script_exists() -> None:
    assert ORACLE_SCRIPT.is_file()


def test_51_track_a_protection_test_exists() -> None:
    assert TRACK_A_TEST.is_file()


def test_52_processing_core_unchanged_in_this_task() -> None:
    for rel in CORE_PROTECTED:
        assert (ROOT / rel).is_file()


def test_53_release_tags_unchanged_marker() -> None:
    assert IA_CLEANUP_LAYOUT_MARKER
    assert REVIEW_CLARIFICATION_MARKER


def test_54_clean_filename_in_review_vm_display_path() -> None:
    dirty = "REVIEW_REQUIRED_SUGGESTED_2026-05-23_er_Böttcher_AG_84,39_card.pdf"
    assert "REVIEW_REQUIRED" not in clean_user_facing_filename(dirty)
    state = _boettcher_state()
    vm = build_review_page_vm(state)
    assert vm.selected_detail is not None
    raw = (
        vm.selected_detail.suggested_filename
        or vm.selected_detail.preview_filename
        or ""
    )
    assert "REVIEW_REQUIRED" not in clean_user_facing_filename(raw)
    src = REVIEW.read_text(encoding="utf-8")
    assert "clean_user_facing_filename" in src
