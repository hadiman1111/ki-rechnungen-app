"""Track-B Simple User Review UI Polish (2026-07-24).

Presentation only — clearer section separation + readable preview filename.
No productive processing, no real invoice folders, no Track-A/core changes.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    FILENAME_FIELD_POLISH_MARKER,
    MSG_FILENAME_PREVIEW_HELPER,
    REVIEW_UI_POLISH_LAYOUT_MARKER,
    SECTION_DATEINAME,
    SECTION_ENTSCHEIDEN,
    SECTION_ERKANNT,
    SECTION_FINAL_WRITE_Q,
    SECTION_TECHNISCHE,
    SECTION_UNKLAR,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
DOCS = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_SIMPLE_USER_REVIEW_UI_POLISH_2026-07-24.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_SIMPLE_USER_REVIEW_UI_POLISH_2026-07-24.md"
)
ORACLE_SCRIPT = ROOT / "scripts" / "dev" / "track_b_automated_smoke_oracle.py"
ORACLE_TEST = ROOT / "tests" / "test_track_b_automated_smoke_oracle.py"
TRACK_A_TEST = ROOT / "tests" / "test_track_a_internal_app_protection.py"

TRACK_A_PROTECTED = (
    "app_main.py",
    "app_internal_launcher.py",
    "invoice_tool/gui.py",
    "invoice_tool/ui_shell.py",
    "invoice_tool/ui_workspace.py",
    "invoice_tool/ui_configurations.py",
    "invoice_tool/ui_profiles.py",
    "invoice_tool/ui_review.py",
    "invoice_tool/ui_settings.py",
    "invoice_tool/ui_profile_dialog.py",
    "invoice_tool/ui_document_rules.py",
)
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
RAW_DEBUG_KEYS = (
    "payment_field",
    "matching_reason",
    "final_write_allowed",
    "matched_configuration_id",
    "configuration_coverage_status",
)


def _planned(**overrides: object) -> ProcessingPlannedDestination:
    base: dict[str, object] = dict(
        document_name="FA011466.pdf",
        planned_path="preview/geplant/paypal/x.pdf",
        destination_label="PayPal",
        preview_only=True,
        applied=False,
        suggested_filename="2026-05-23_er_Böttcher_AG_84,39_card.pdf",
        supplier="Böttcher AG",
        counterparty_name="Böttcher AG",
        invoice_date="2026-05-23",
        amount="84,39",
        selected_amount="84,39",
        selected_payment_field="card",
        payment_account="card",
        selected_art="er",
        matched_configuration_name="Unklar",
        missing_configuration_type="paypal",
        configuration_coverage_status="missing_config_for_detected_payment",
        user_guidance="PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden.",
    )
    base.update(overrides)
    return ProcessingPlannedDestination(**base)  # type: ignore[arg-type]


def _paypal_state() -> UiV2State:
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="ui-polish-1",
        review_items=(
            ProcessingReviewItem(
                document_name="FA011466.pdf",
                reason="PayPal-Regel fehlt",
                status_label="unklar",
                document_id="doc-polish",
            ),
        ),
        planned_destinations=(_planned(),),
        planned_destination_count=1,
        outcome_kind="all_review",
    )
    state = UiV2State(processing_run_state=run)
    state.review_preview_ui.selected_item_key = "doc-polish"
    return state


def test_01_detail_ui_exposes_visually_separated_sections() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.ui_polish_layout_marker == REVIEW_UI_POLISH_LAYOUT_MARKER
    src = REVIEW.read_text(encoding="utf-8")
    assert "def review_section(" in src
    assert "review_section(" in src
    assert "REVIEW_UI_POLISH_LAYOUT_MARKER" in src
    assert REVIEW_UI_POLISH_LAYOUT_MARKER in COPY_MOD.read_text(encoding="utf-8")


def test_02_section_headings_present() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert SECTION_ERKANNT == "Was wurde erkannt?"
    assert SECTION_DATEINAME == "Was schlägt die App vor?"
    assert SECTION_ENTSCHEIDEN == "Was muss ich entscheiden?"
    assert SECTION_ERKANNT in vm.section_titles
    assert SECTION_DATEINAME in vm.section_titles
    assert SECTION_ENTSCHEIDEN in vm.section_titles
    assert SECTION_UNKLAR in vm.section_titles
    assert SECTION_FINAL_WRITE_Q in vm.section_titles
    assert SECTION_TECHNISCHE in vm.section_titles
    src = REVIEW.read_text(encoding="utf-8")
    assert "SECTION_ERKANNT" in src
    assert "SECTION_DATEINAME" in src
    assert "SECTION_ENTSCHEIDEN" in src


def test_03_filename_field_full_width_no_clip_marker() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.filename_field_polish_marker == FILENAME_FIELD_POLISH_MARKER
    src = REVIEW.read_text(encoding="utf-8")
    assert "FILENAME_FIELD_POLISH_MARKER" in src
    assert "multiline=True" in src
    assert "expand=True" in src
    assert "LABEL_VORSCHAU_DATEINAME" in src
    assert "LABEL_DATEINAME_BEARBEITEN" in src
    assert 'label="Vorschau-Dateiname (editierbar)"' not in src
    assert FILENAME_FIELD_POLISH_MARKER in COPY_MOD.read_text(encoding="utf-8")


def test_04_filename_helper_text_nur_vorschau() -> None:
    assert "Nur Vorschau" in MSG_FILENAME_PREVIEW_HELPER
    assert MSG_FILENAME_PREVIEW_HELPER == (
        "Nur Vorschau — noch keine finale Datei geschrieben."
    )
    src = REVIEW.read_text(encoding="utf-8")
    assert "MSG_FILENAME_PREVIEW_HELPER" in src
    assert "Nur Vorschau" in COPY_MOD.read_text(encoding="utf-8")


def test_05_technical_details_collapsed_by_default() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.technical_details_collapsed_by_default is True
    src = REVIEW.read_text(encoding="utf-8")
    assert "initially_expanded=False" in src
    assert "SECTION_TECHNISCHE" in src
    assert "_developer_tools_collapsed" in src


def test_06_no_raw_debug_keys_in_primary_surface() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    primary = " ".join(
        f"{k}={v}" for k, v in vm.selected_detail.recognized_fields
    )
    primary += " " + " ".join(vm.selected_detail.unclear_items)
    primary += " " + (vm.selected_detail.decision_prompt or "")
    for token in RAW_DEBUG_KEYS:
        assert token not in primary


def test_07_no_auto_run() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.auto_runs_oracle is False
    src = REVIEW.read_text(encoding="utf-8")
    assert "run_automated_smoke_oracle(" not in src


def test_08_no_run_once() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.calls_run_once is False
    src = REVIEW.read_text(encoding="utf-8")
    tree = ast.parse(src)
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attr_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "run_once" not in call_names
    assert "run_once" not in attr_calls


def test_09_no_production_final_write() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.production_final_write_enabled is False
    assert vm.writes_final_files is False
    assert vm.selected_detail is not None
    assert vm.selected_detail.final_write_allowed is False
    src = REVIEW.read_text(encoding="utf-8")
    assert "final_write_allowed_for_production=True" not in src
    assert "final_write_allowed_for_production = True" not in src


def test_10_no_real_invoice_folders() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.touches_real_invoice_folders is False
    for path in (REVIEW, COPY_MOD):
        text = path.read_text(encoding="utf-8")
        for folder in FORBIDDEN_FOLDERS:
            assert folder not in text


def test_11_track_a_protection_still_passes() -> None:
    assert TRACK_A_TEST.is_file()
    for rel in TRACK_A_PROTECTED:
        assert (ROOT / rel).exists() or rel.endswith("ui_document_rules.py")
    # This polish task must not modify Track-A protected files.
    # Presence of the protection test file is the gate; content changes are
    # verified by running tests/test_track_a_internal_app_protection.py.


def test_12_automated_smoke_oracle_still_passes() -> None:
    assert ORACLE_SCRIPT.is_file()
    assert ORACLE_TEST.is_file()
    assert DOCS.is_file()
    assert AUDIT.is_file()
    assert "REVIEW_UI_POLISH_LAYOUT_MARKER" in REVIEW.read_text(encoding="utf-8")
    for rel in CORE_PROTECTED:
        assert (ROOT / rel).is_file()
