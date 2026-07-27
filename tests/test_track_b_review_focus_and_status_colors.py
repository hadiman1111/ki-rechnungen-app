"""Track-B Review Focus & Status Colors (2026-07-27).

OK = green check (no checkbox), open = red/soft-red, success message,
decision-needed review list, top-focus selected file + detail.
No productive processing, no real invoice folders, no Track-A/core changes.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.components import document_status_marker
from invoice_tool.ui_v2.pages.review import (
    build_review_page_vm,
    request_review_scroll_to_item,
    set_filename_editor_active,
    set_open_review_item_id,
    toggle_review_item_details,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import (
    ENV_SHOW_DEV_SURFACES,
    UiV2State,
    is_track_b_show_dev_surfaces_enabled,
)
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_ACCEPT_SUGGESTION,
    ACTION_EDIT_FILENAME,
    ACTION_IGNORE_EXPORT,
    ACTION_KEEP_IN_REVIEW_GUIDED,
    DOCUMENT_STATUS_NEEDS_REVIEW_MARKER,
    DOCUMENT_STATUS_NON_INTERACTIVE_MARKER,
    DOCUMENT_STATUS_OK_MARKER,
    MSG_ALL_CHECKS_SUCCESSFUL,
    REVIEW_DECISION_LIST_FILTER_MARKER,
    REVIEW_FOCUS_AND_STATUS_COLORS_MARKER,
    REVIEW_TOP_FOCUS_MARKER,
    STATUS_UI_NEEDS_REVIEW,
    STATUS_UI_OK,
    map_output_status_to_ui_kind,
    review_item_needs_open_decision,
)
from invoice_tool.ui_v2.workspace_file_pairs import STATUS_PROPOSED, STATUS_REVIEW

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
COMPONENTS = ROOT / "invoice_tool" / "ui_v2" / "components.py"
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
TRACK_A_TEST = ROOT / "tests" / "test_track_a_internal_app_protection.py"
GUI_STARTUP_TEST = ROOT / "tests" / "test_gui_startup.py"

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


def _review_src() -> str:
    return REVIEW.read_text(encoding="utf-8")


def _page_fn_src() -> str:
    return _review_src().split("def build_review_page(")[1]


def _planned(**overrides: object) -> ProcessingPlannedDestination:
    base: dict[str, object] = dict(
        document_name="FA011466.pdf",
        planned_path="preview/geplant/paypal/x.pdf",
        destination_label="PayPal",
        preview_only=True,
        applied=False,
        suggested_filename="2026-05-11_er_LUMITOP_476,00_paypal.pdf",
        supplier="LUMITOP",
        counterparty_name="LUMITOP",
        invoice_date="2026-05-11",
        amount="476,00",
        selected_amount="476,00",
        selected_payment_field="paypal",
        payment_account="paypal",
        selected_art="er",
        matched_configuration_name="Unklar",
        missing_configuration_type="paypal",
        configuration_coverage_status="missing_config_for_detected_payment",
        user_guidance="PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden.",
    )
    base.update(overrides)
    return ProcessingPlannedDestination(**base)  # type: ignore[arg-type]


def _two_item_state(*, open_key: str | None = "doc-b") -> UiV2State:
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="focus-status-1",
        review_items=(
            ProcessingReviewItem(
                document_name="FA011466.pdf",
                reason="PayPal-Regel fehlt",
                status_label="unklar",
                document_id="doc-a",
            ),
            ProcessingReviewItem(
                document_name="Rechnung-2026156019-102201.pdf",
                reason="Zahlung unklar",
                status_label="unklar",
                document_id="doc-b",
            ),
        ),
        planned_destinations=(
            _planned(),
            _planned(
                document_name="Rechnung-2026156019-102201.pdf",
                supplier="Luxvenum LED GmbH",
                counterparty_name="Luxvenum LED GmbH",
                invoice_date="2026-05-11",
                amount="154,95",
                selected_amount="154,95",
                suggested_filename=(
                    "2026-05-11_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf"
                ),
                selected_payment_field=None,
                payment_account=None,
                missing_configuration_type="payment_field",
                configuration_coverage_status="missing_payment_field",
                user_guidance="Zahlungsart fehlt.",
            ),
        ),
        planned_destination_count=2,
        outcome_kind="all_review",
    )
    state = UiV2State(processing_run_state=run)
    if open_key:
        set_open_review_item_id(state, open_key)
        request_review_scroll_to_item(state, open_key)
    return state


def test_01_shared_status_mapping_ok_green_review_red() -> None:
    assert map_output_status_to_ui_kind(STATUS_PROPOSED) == STATUS_UI_OK
    assert map_output_status_to_ui_kind(STATUS_REVIEW) == STATUS_UI_NEEDS_REVIEW
    assert map_output_status_to_ui_kind("error") == STATUS_UI_NEEDS_REVIEW
    assert DOCUMENT_STATUS_OK_MARKER in COPY_MOD.read_text(encoding="utf-8")
    assert DOCUMENT_STATUS_NEEDS_REVIEW_MARKER in COPY_MOD.read_text(encoding="utf-8")
    assert "def document_status_marker" in COMPONENTS.read_text(encoding="utf-8")
    assert "def map_output_status_to_ui_kind" in COPY_MOD.read_text(encoding="utf-8")


def test_02_ok_marker_is_green_check_not_checkbox() -> None:
    components = COMPONENTS.read_text(encoding="utf-8")
    marker_fn = components.split("def document_status_marker")[1].split(
        "def make_ergebnis_row"
    )[0]
    assert "DOCUMENT_STATUS_OK_MARKER" in marker_fn
    assert "DOCUMENT_STATUS_NON_INTERACTIVE_MARKER" in marker_fn
    assert "no_checkbox" in marker_fn
    assert "ft.Checkbox" not in marker_fn
    assert "Icons.CHECK" in marker_fn
    assert "green_check" in marker_fn
    assert DOCUMENT_STATUS_OK_MARKER in COPY_MOD.read_text(encoding="utf-8")
    assert DOCUMENT_STATUS_NON_INTERACTIVE_MARKER in COPY_MOD.read_text(
        encoding="utf-8"
    )
    # Keep import reachable without constructing Flet controls in older venvs.
    assert callable(document_status_marker)


def test_03_workspace_uses_shared_status_markers() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "document_status_marker" in src
    assert "map_output_status_to_ui_kind" in src
    assert "REVIEW_FOCUS_AND_STATUS_COLORS_MARKER" in src
    assert "COLOR_ERROR_SOFT" in src
    assert "MSG_ALL_CHECKS_SUCCESSFUL" in src
    assert MSG_ALL_CHECKS_SUCCESSFUL == "Alle Prüfungen erfolgreich."


def test_04_success_message_constant() -> None:
    assert MSG_ALL_CHECKS_SUCCESSFUL == "Alle Prüfungen erfolgreich."
    vm = build_review_page_vm(
        UiV2State(
            processing_run_state=ProcessingRunState(
                status="completed",
                run_id="ok-run",
                review_items=(),
                results=(
                    ProcessingResultSummary(
                        document_name="ok.pdf",
                        document_type="er",
                        classification_status="ok",
                        status_label="ok",
                    ),
                ),
            )
        )
    )
    assert vm.all_checks_successful is True
    assert vm.all_checks_successful_message == MSG_ALL_CHECKS_SUCCESSFUL
    assert not vm.list_items
    page = _page_fn_src()
    assert "MSG_ALL_CHECKS_SUCCESSFUL" in page
    assert "positive_empty_state" in page
    assert "Oracle" not in page.split("if vm.all_checks_successful")[1].split(
        "if vm.empty:"
    )[0]


def test_05_review_list_filters_resolved_ok_items() -> None:
    assert review_item_needs_open_decision() is True
    assert review_item_needs_open_decision(checked_preview=True) is False
    assert review_item_needs_open_decision(
        decision_type="accept_suggestion"
    ) is False
    assert review_item_needs_open_decision(finalization_ready=True) is False
    assert review_item_needs_open_decision(
        decision_type="keep_review_required"
    ) is True
    assert "REVIEW_DECISION_LIST_FILTER_MARKER" in _review_src()
    assert "review_item_needs_open_decision" in _review_src()
    vm = build_review_page_vm(_two_item_state(open_key=None))
    assert vm.primary_decision_item_count == 2
    assert vm.decision_list_filter_marker == REVIEW_DECISION_LIST_FILTER_MARKER


def test_06_top_focus_on_selected_file() -> None:
    state = _two_item_state(open_key="doc-b")
    vm = build_review_page_vm(state)
    assert vm.open_review_item_id == "doc-b"
    assert vm.selected_detail is not None
    assert vm.top_focus_marker == REVIEW_TOP_FOCUS_MARKER
    page = _page_fn_src()
    assert "REVIEW_TOP_FOCUS_MARKER" in page
    assert "top_focus_not_list_position" in page
    assert page.index("REVIEW_TOP_FOCUS_MARKER") < page.index("accordion_blocks.append")
    assert "render_review_inline_detail" in page
    assert page.index("render_review_inline_detail") < page.index(
        "accordion_blocks.append"
    )
    # Selected file is omitted from the lower list to avoid duplication.
    assert "if is_open:" in page
    assert "continue" in page


def test_07_filename_edit_stays_in_top_focus() -> None:
    state = _two_item_state(open_key="doc-a")
    set_filename_editor_active(state, "doc-a", active=True)
    vm = build_review_page_vm(state)
    assert vm.open_review_item_id == "doc-a"
    assert vm.selected_detail is not None
    panel = _review_src().split("def _filename_preview_panel")[1].split(
        "def _test_tools_collapsed"
    )[0]
    assert "FILENAME_SECTION_EDITING_ACTIVE_MARKER" in panel
    assert "request_review_scroll_to_filename_section" in panel
    page = _page_fn_src()
    assert "REVIEW_TOP_FOCUS_MARKER" in page
    assert ACTION_EDIT_FILENAME == "Dateiname anpassen"


def test_08_no_zur_pruefung_zulassen_and_concrete_actions() -> None:
    assert "Zur Prüfung zulassen" not in ACTION_KEEP_IN_REVIEW_GUIDED
    assert ACTION_KEEP_IN_REVIEW_GUIDED == "Weiter manuell prüfen"
    assert ACTION_ACCEPT_SUGGESTION == "Vorschlag übernehmen"
    assert ACTION_IGNORE_EXPORT == "Nicht exportieren"
    assert ACTION_EDIT_FILENAME == "Dateiname anpassen"
    detail = _review_src().split("def _selected_detail_section_controls")[1].split(
        "def build_review_page("
    )[0]
    primary = detail.split("if is_track_b_show_dev_surfaces_enabled():")[0]
    assert "Zur Prüfung zulassen" not in primary


def test_09_dev_surfaces_gated() -> None:
    assert is_track_b_show_dev_surfaces_enabled(
        env={"KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS": "1"}
    ) is False
    assert is_track_b_show_dev_surfaces_enabled(
        env={ENV_SHOW_DEV_SURFACES: "1"}
    ) is True
    page = _page_fn_src()
    success_branch = page.split("if vm.all_checks_successful")[1].split("if vm.empty:")[0]
    assert "Oracle" not in success_branch
    assert "SECTION_DEV_DIAGNOSE" not in success_branch


def test_10_toggle_sets_selected_and_top_focus_markers() -> None:
    state = _two_item_state(open_key=None)
    toggle_review_item_details(state, "doc-a")
    vm = build_review_page_vm(state)
    assert vm.open_review_item_id == "doc-a"
    assert any(r.details_open for r in vm.list_items)
    assert vm.status_colors_marker == REVIEW_FOCUS_AND_STATUS_COLORS_MARKER


def test_11_no_productive_processing_or_run_once() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.production_final_write_enabled is False
    assert vm.writes_final_files is False
    assert vm.calls_run_once is False
    tree = ast.parse(_review_src())
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "run_once" not in call_names


def test_12_track_a_and_core_out_of_scope() -> None:
    assert TRACK_A_TEST.is_file()
    assert GUI_STARTUP_TEST.is_file()
    for rel in TRACK_A_PROTECTED:
        assert (ROOT / rel).exists() or rel.endswith("ui_document_rules.py")
    for rel in CORE_PROTECTED:
        assert (ROOT / rel).is_file()
    assert REVIEW_FOCUS_AND_STATUS_COLORS_MARKER == (
        "track_b_review_focus_and_status_colors_v1"
    )
    assert REVIEW_TOP_FOCUS_MARKER == "review_top_focus_selected_file_and_detail_v1"
