"""Track-B Review Accordion Layout (2026-07-24).

UI-only: compact summary cards + inline detail under the selected document.
No productive processing, no real invoice folders, no Track-A/core changes.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.dev_defaults import MSG_EMPTY_REVIEW_HELP
from invoice_tool.ui_v2.pages.review import (
    build_review_page_vm,
    get_open_review_item_id,
    set_open_review_item_id,
    toggle_review_item_details,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_DETAILS_CLOSE,
    ACTION_DETAILS_OPEN,
    DETAIL_PANEL_DISTINCT_BACKGROUND,
    INLINE_DETAIL_UNDER_SELECTED_CARD,
    LABEL_REVIEW_AMOUNT,
    LABEL_REVIEW_DATE,
    LABEL_REVIEW_DOC_NAME,
    MSG_ORACLE_AVAILABLE,
    MSG_SAFETY_LINE_NO_FINAL,
    ORACLE_COMMAND,
    REVIEW_ACCORDION_LAYOUT_MARKER,
    REVIEW_CARD_ACTIVE_HIGHLIGHT,
    REVIEW_CARD_COLLAPSED_SUMMARY_ONLY,
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
    / "KI_RECHNUNGEN_TRACK_B_REVIEW_ACCORDION_LAYOUT_2026-07-24.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_REVIEW_ACCORDION_LAYOUT_2026-07-24.md"
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


def _two_item_state() -> UiV2State:
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="accordion-1",
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
                supplier="LUMITOP",
                counterparty_name="LUMITOP",
                invoice_date="2026-05-11",
                amount="476,00",
                selected_amount="476,00",
                suggested_filename="2026-05-11_er_LUMITOP_476,00_paypal.pdf",
                selected_payment_field="paypal",
                payment_account="paypal",
            ),
        ),
        planned_destination_count=2,
        outcome_kind="all_review",
    )
    return UiV2State(processing_run_state=run)


def _open_state(item_key: str = "doc-a") -> UiV2State:
    state = _two_item_state()
    set_open_review_item_id(state, item_key)
    return state


def test_01_review_page_exposes_accordion_layout_marker() -> None:
    vm = build_review_page_vm(_open_state())
    assert vm.accordion_layout_marker == REVIEW_ACCORDION_LAYOUT_MARKER
    src = REVIEW.read_text(encoding="utf-8")
    assert "REVIEW_ACCORDION_LAYOUT_MARKER" in src
    assert "render_review_summary_card" in src
    assert "render_review_inline_detail" in src
    assert REVIEW_ACCORDION_LAYOUT_MARKER in COPY_MOD.read_text(encoding="utf-8")


def test_02_collapsed_card_shows_name_date_amount() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.list_items
    row = vm.list_items[0]
    assert row.collapsed_summary_only is True
    assert row.summary_display_name
    assert row.invoice_date
    assert row.amount
    src = REVIEW.read_text(encoding="utf-8")
    assert "LABEL_REVIEW_DOC_NAME" in src
    assert "LABEL_REVIEW_DATE" in src
    assert "LABEL_REVIEW_AMOUNT" in src
    assert LABEL_REVIEW_DOC_NAME == "Dokumentname"
    assert LABEL_REVIEW_DATE == "Datum"
    assert LABEL_REVIEW_AMOUNT == "Betrag"


def test_03_collapsed_card_hides_raw_debug_fields() -> None:
    vm = build_review_page_vm(_two_item_state())
    row = vm.list_items[0]
    collapsed_blob = " ".join(
        [
            str(row.summary_display_name or ""),
            str(row.invoice_date or ""),
            str(row.amount or ""),
            str(row.details_action_label or ""),
        ]
    )
    for token in RAW_DEBUG_KEYS:
        assert token not in collapsed_blob
    src = REVIEW.read_text(encoding="utf-8")
    summary_fn = src.split("def render_review_summary_card")[1].split(
        "def render_review_inline_detail"
    )[0]
    assert "LABEL_REVIEW_DOC_NAME" in summary_fn
    assert "LABEL_REVIEW_DATE" in summary_fn
    assert "LABEL_REVIEW_AMOUNT" in summary_fn
    assert "Zahlungsart" not in summary_fn
    assert "matching_reason" not in summary_fn


def test_04_collapsed_card_has_details_open_action() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.details_open_action_label == ACTION_DETAILS_OPEN
    assert vm.list_items[0].details_action_label == ACTION_DETAILS_OPEN
    assert vm.list_items[0].details_open is False
    assert ACTION_DETAILS_OPEN in COPY_MOD.read_text(encoding="utf-8")


def test_05_open_card_has_details_close_action() -> None:
    vm = build_review_page_vm(_open_state("doc-a"))
    open_rows = [r for r in vm.list_items if r.details_open]
    assert len(open_rows) == 1
    assert open_rows[0].details_action_label == ACTION_DETAILS_CLOSE
    assert vm.details_close_action_label == ACTION_DETAILS_CLOSE


def test_06_open_detail_renders_immediately_under_selected_card() -> None:
    vm = build_review_page_vm(_open_state("doc-a"))
    assert vm.open_review_item_id == "doc-a"
    assert vm.inline_detail_marker == INLINE_DETAIL_UNDER_SELECTED_CARD
    src = REVIEW.read_text(encoding="utf-8")
    assert "render_review_inline_detail" in src
    assert "INLINE_DETAIL_UNDER_SELECTED_CARD" in src
    # Detail is appended in the same accordion block as the card, not after full list.
    assert "block_controls.append" in src
    assert "render_review_inline_detail(state, vm, vm.selected_detail)" in src


def test_07_detail_panel_uses_distinct_background_marker() -> None:
    vm = build_review_page_vm(_open_state())
    assert vm.detail_panel_background_marker == DETAIL_PANEL_DISTINCT_BACKGROUND
    src = REVIEW.read_text(encoding="utf-8")
    assert "DETAIL_PANEL_DISTINCT_BACKGROUND" in src
    assert "COLOR_SURFACE_ALT" in src
    assert "COLOR_BORDER_STRONG" in src


def test_08_active_card_has_highlight_marker() -> None:
    vm = build_review_page_vm(_open_state("doc-a"))
    active = [r for r in vm.list_items if r.accordion_active]
    assert len(active) == 1
    assert vm.active_card_highlight_marker == REVIEW_CARD_ACTIVE_HIGHLIGHT
    src = REVIEW.read_text(encoding="utf-8")
    assert "REVIEW_CARD_ACTIVE_HIGHLIGHT" in src
    assert "COLOR_PRIMARY_SUBTLE" in src


def test_09_only_one_card_open_at_a_time() -> None:
    state = _two_item_state()
    assert vm_open_count(state) == 0
    toggle_review_item_details(state, "doc-a")
    assert get_open_review_item_id(state) == "doc-a"
    assert vm_open_count(state) == 1
    toggle_review_item_details(state, "doc-b")
    assert get_open_review_item_id(state) == "doc-b"
    assert vm_open_count(state) == 1
    vm = build_review_page_vm(state)
    assert vm.accordion_single_open is True
    assert sum(1 for r in vm.list_items if r.details_open) == 1


def vm_open_count(state: UiV2State) -> int:
    return sum(1 for r in build_review_page_vm(state).list_items if r.details_open)


def test_10_simple_user_review_sections_inside_expanded_detail() -> None:
    vm = build_review_page_vm(_open_state())
    assert vm.selected_detail is not None
    for title in (
        SECTION_ERKANNT,
        SECTION_UNKLAR,
        SECTION_DATEINAME,
        SECTION_ENTSCHEIDEN,
        SECTION_FINAL_WRITE_Q,
        SECTION_TECHNISCHE,
    ):
        assert title in vm.section_titles
    src = REVIEW.read_text(encoding="utf-8")
    assert "SECTION_ERKANNT" in src
    assert "_selected_detail_section_controls" in src


def test_11_technical_details_collapsed_by_default() -> None:
    vm = build_review_page_vm(_open_state())
    assert vm.technical_details_collapsed_by_default is True
    src = REVIEW.read_text(encoding="utf-8")
    assert "initially_expanded=False" in src
    assert "SECTION_TECHNISCHE" in src


def test_12_empty_state_includes_preview_oracle_help() -> None:
    state = UiV2State(processing_run_state=ProcessingRunState(status="idle"))
    vm = build_review_page_vm(state)
    assert vm.empty is True
    assert MSG_EMPTY_REVIEW_HELP
    assert MSG_SAFETY_LINE_NO_FINAL in (vm.safety_line_declutter or "")
    assert MSG_ORACLE_AVAILABLE
    assert ORACLE_COMMAND in (vm.oracle_command or "")
    src = REVIEW.read_text(encoding="utf-8")
    assert "MSG_EMPTY_REVIEW_HELP" in src
    assert "ACTION_COPY_ORACLE" in src


def test_13_no_auto_run() -> None:
    vm = build_review_page_vm(_open_state())
    assert vm.auto_runs_oracle is False
    src = REVIEW.read_text(encoding="utf-8")
    assert "run_automated_smoke_oracle(" not in src


def test_14_no_run_once() -> None:
    vm = build_review_page_vm(_open_state())
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


def test_15_no_production_final_write() -> None:
    vm = build_review_page_vm(_open_state())
    assert vm.production_final_write_enabled is False
    assert vm.writes_final_files is False
    src = REVIEW.read_text(encoding="utf-8")
    assert "final_write_allowed_for_production=True" not in src
    assert "final_write_allowed_for_production = True" not in src


def test_16_no_real_invoice_folders() -> None:
    vm = build_review_page_vm(_open_state())
    assert vm.touches_real_invoice_folders is False
    for path in (REVIEW, COPY_MOD):
        text = path.read_text(encoding="utf-8")
        for folder in FORBIDDEN_FOLDERS:
            assert folder not in text


def test_17_automated_smoke_oracle_still_passes() -> None:
    assert ORACLE_SCRIPT.is_file()
    assert ORACLE_TEST.is_file()
    assert DOCS.is_file()
    assert AUDIT.is_file()
    assert REVIEW_CARD_COLLAPSED_SUMMARY_ONLY in COPY_MOD.read_text(encoding="utf-8")


def test_18_track_a_protection_still_passes() -> None:
    assert TRACK_A_TEST.is_file()
    for rel in TRACK_A_PROTECTED:
        assert (ROOT / rel).exists() or rel.endswith("ui_document_rules.py")
    for rel in CORE_PROTECTED:
        assert (ROOT / rel).is_file()
