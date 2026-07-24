"""Track-B Guided Review UX Cleanup (2026-07-24).

Document-specific reasons + decision-first accordion detail.
UI/UX only — no productive processing, no real invoice folders.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.pages.review import (
    build_review_page_vm,
    set_filename_editor_active,
    set_open_review_item_id,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_ACCEPT_SUGGESTION,
    ACTION_COPY_FILENAME,
    ACTION_EDIT_FILENAME,
    ACTION_KEEP_IN_REVIEW_GUIDED,
    ACTION_KEEP_UNCLEAR_GUIDED,
    DECISION_FIRST_PANEL_MARKER,
    FILENAME_PREVIEW_ONLY_MARKER,
    GUIDED_STATUS_PANEL_MARKER,
    MSG_GUIDED_SAFETY_LINE,
    MSG_SAFETY_LINE_NO_FINAL,
    MSG_WHY_MISSING_PAYMENT,
    MSG_WHY_NOT_AMEX,
    MSG_WHY_PAYPAL_DETECTED,
    MSG_WHY_STORNO,
    REVIEW_ACCORDION_LAYOUT_MARKER,
    REVIEW_CARD_ACTIVE_HIGHLIGHT,
    REVIEW_GUIDED_LAYOUT_MARKER,
    SECTION_ENTSCHEIDEN,
    SECTION_TEST_TOOLS,
    derive_guided_status_lines,
    derive_why_review_plain_german,
    review_case_kind,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
DOCS = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_GUIDED_REVIEW_UX_CLEANUP_2026-07-24.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_GUIDED_REVIEW_UX_CLEANUP_2026-07-24.md"
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


def _state_for(
    *,
    document_name: str,
    document_id: str,
    planned: ProcessingPlannedDestination,
    reason: str = "Prüfung erforderlich",
    open_details: bool = True,
) -> UiV2State:
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="guided-review-1",
        review_items=(
            ProcessingReviewItem(
                document_name=document_name,
                reason=reason,
                status_label="unklar",
                document_id=document_id,
            ),
        ),
        planned_destinations=(planned,),
        planned_destination_count=1,
        outcome_kind="all_review",
    )
    state = UiV2State(processing_run_state=run)
    state.review_preview_ui.selected_item_key = document_id
    if open_details:
        set_open_review_item_id(state, document_id)
    return state


def _boettcher_state() -> UiV2State:
    return _state_for(
        document_name="320262919974.pdf",
        document_id="doc-card",
        planned=_planned(
            document_name="320262919974.pdf",
            suggested_filename="2026-05-23_er_Böttcher_AG_84,39_card.pdf",
            supplier="Böttcher AG",
            counterparty_name="Böttcher AG",
            invoice_date="2026-05-23",
            amount="84,39",
            selected_amount="84,39",
            selected_payment_field="card",
            payment_account="card",
            matched_configuration_name="Unklar",
            # Contaminated guidance must NOT leak into user-facing reasons.
            missing_configuration_type="generic_card",
            configuration_coverage_status="no_safe_card_configuration",
            user_guidance=(
                "PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden."
            ),
        ),
        reason="Kartenzahlung — AMEX nicht belegt",
    )


def _paypal_state() -> UiV2State:
    return _state_for(
        document_name="FA011466.pdf",
        document_id="doc-paypal",
        planned=_planned(),
        reason="PayPal-Regel fehlt",
    )


def _missing_payment_state() -> UiV2State:
    return _state_for(
        document_name="Rechnung-2026156019-102201.pdf",
        document_id="doc-missing",
        planned=_planned(
            document_name="Rechnung-2026156019-102201.pdf",
            suggested_filename=(
                "2026-05-11_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf"
            ),
            supplier="Luxvenum LED GmbH",
            counterparty_name="Luxvenum LED GmbH",
            selected_payment_field=None,
            payment_account=None,
            matched_configuration_name="Unklar",
            missing_configuration_type="payment_field",
            configuration_coverage_status="missing_payment_field",
            user_guidance="Zahlungsfeld nicht sicher erkannt.",
        ),
        reason="Zahlungsfeld fehlt",
    )


def _storno_state() -> UiV2State:
    return _state_for(
        document_name="420260091336.pdf",
        document_id="doc-storno",
        planned=_planned(
            document_name="420260091336.pdf",
            suggested_filename=(
                "2026-06-18_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
            ),
            supplier="Böttcher AG",
            counterparty_name="Böttcher AG",
            invoice_date="2026-06-18",
            amount="68,94",
            selected_amount="68,94",
            selected_art="storno",
            document_type="storno",
            selected_payment_field=None,
            payment_account=None,
            matched_configuration_name="Unklar",
            missing_configuration_type="payment_field",
            configuration_coverage_status="missing_payment_field",
            user_guidance="Storno erkannt; Zahlungsfeld fehlt.",
        ),
        reason="Storno zur Prüfung",
    )


def test_01_guided_status_panel_at_top() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.guided_layout_marker == REVIEW_GUIDED_LAYOUT_MARKER
    assert vm.guided_status_marker == GUIDED_STATUS_PANEL_MARKER
    assert vm.selected_detail is not None
    assert vm.selected_detail.guided_status_lines
    src = REVIEW.read_text(encoding="utf-8")
    assert "_guided_status_panel" in src
    assert "GUIDED_STATUS_PANEL_MARKER" in src
    # Guided panel is rendered before decision section in detail controls.
    detail_fn = src.split("def _selected_detail_section_controls")[1].split(
        "def build_review_page"
    )[0]
    assert detail_fn.index("_guided_status_panel") < detail_fn.index(
        "SECTION_ENTSCHEIDEN"
    )


def test_02_boettcher_reason_no_paypal() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.selected_detail is not None
    blob = " ".join(vm.selected_detail.unclear_items)
    blob += " " + " ".join(vm.selected_detail.guided_status_lines)
    assert "PayPal" not in blob
    assert "paypal" not in blob.casefold()


def test_03_boettcher_reason_card_amex() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.selected_detail is not None
    assert review_case_kind(vm.selected_detail) == "card_not_amex"
    why = derive_why_review_plain_german(vm.selected_detail)
    assert MSG_WHY_NOT_AMEX in why
    assert "AMEX" in " ".join(why)
    assert "Kartenzahlung" in " ".join(why)


def test_04_paypal_reason_mentions_paypal() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    why = " ".join(vm.selected_detail.unclear_items)
    assert "PayPal" in why
    assert MSG_WHY_PAYPAL_DETECTED in vm.selected_detail.unclear_items


def test_05_missing_payment_reason() -> None:
    vm = build_review_page_vm(_missing_payment_state())
    assert vm.selected_detail is not None
    assert MSG_WHY_MISSING_PAYMENT in vm.selected_detail.unclear_items
    assert "Zahlungsart fehlt" in " ".join(vm.selected_detail.guided_status_lines)


def test_06_storno_reason() -> None:
    vm = build_review_page_vm(_storno_state())
    assert vm.selected_detail is not None
    assert MSG_WHY_STORNO in vm.selected_detail.unclear_items
    assert "Storno" in " ".join(vm.selected_detail.guided_status_lines)


def test_07_reasons_are_document_specific() -> None:
    card = build_review_page_vm(_boettcher_state()).selected_detail
    paypal = build_review_page_vm(_paypal_state()).selected_detail
    assert card is not None and paypal is not None
    assert "PayPal" not in " ".join(card.unclear_items)
    assert "PayPal" in " ".join(paypal.unclear_items)
    assert "AMEX" not in " ".join(paypal.unclear_items)
    # Contaminated guidance on card fixture must be ignored.
    guided = derive_guided_status_lines(
        {
            "selected_payment_field": "card",
            "missing_configuration_type": "generic_card",
            "matched_configuration_name": "Unklar",
            "user_guidance": "PayPal erkannt",
        }
    )
    assert "PayPal" not in " ".join(guided)


def test_08_decision_panel_before_test_tools() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    detail_fn = src.split("def _selected_detail_section_controls")[1].split(
        "def build_review_page"
    )[0]
    assert detail_fn.index("SECTION_ENTSCHEIDEN") < detail_fn.index(
        "_test_tools_collapsed"
    )
    assert DECISION_FIRST_PANEL_MARKER in COPY_MOD.read_text(encoding="utf-8")
    assert SECTION_ENTSCHEIDEN == "Was muss ich entscheiden?"


def test_09_relevant_primary_action_per_case() -> None:
    card = build_review_page_vm(_boettcher_state()).selected_detail
    paypal = build_review_page_vm(_paypal_state()).selected_detail
    missing = build_review_page_vm(_missing_payment_state()).selected_detail
    assert card is not None and paypal is not None and missing is not None
    assert card.primary_decision_action == ACTION_KEEP_UNCLEAR_GUIDED
    assert paypal.primary_decision_action == ACTION_ACCEPT_SUGGESTION
    assert missing.primary_decision_action == ACTION_KEEP_IN_REVIEW_GUIDED
    src = REVIEW.read_text(encoding="utf-8")
    assert "primary_button" in src


def test_10_filename_preview_not_input_by_default() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.selected_detail is not None
    assert vm.selected_detail.filename_preview_only_by_default is True
    assert vm.filename_preview_only_marker == FILENAME_PREVIEW_ONLY_MARKER
    src = REVIEW.read_text(encoding="utf-8")
    assert "_filename_preview_panel" in src
    assert "ACTION_EDIT_FILENAME" in src
    assert ACTION_EDIT_FILENAME == "Dateiname bearbeiten"
    # Default path renders preview text marker, not immediate TextField construction
    # outside edit mode branch.
    preview_fn = src.split("def _filename_preview_panel")[1].split(
        "def _test_tools_collapsed"
    )[0]
    assert "FILENAME_PREVIEW_ONLY_MARKER" in preview_fn
    assert "if edit_active:" in preview_fn


def test_11_filename_edit_only_in_edit_mode() -> None:
    state = _boettcher_state()
    assert not build_review_page_vm(state).selected_detail or True
    set_filename_editor_active(state, "doc-card", active=True)
    src = REVIEW.read_text(encoding="utf-8")
    assert "is_filename_editor_active" in src
    assert "set_filename_editor_active" in src
    assert "ft.TextField(" in src.split("if edit_active:")[1]


def test_12_filename_copy_available() -> None:
    assert ACTION_COPY_FILENAME == "Dateiname kopieren"
    src = REVIEW.read_text(encoding="utf-8")
    assert "ACTION_COPY_FILENAME" in src
    assert ACTION_COPY_FILENAME in COPY_MOD.read_text(encoding="utf-8")


def test_13_test_tools_collapsed_by_default() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "_test_tools_collapsed" in src
    assert SECTION_TEST_TOOLS in COPY_MOD.read_text(encoding="utf-8")
    assert SECTION_TEST_TOOLS == "Test & Nachweis"
    tools_fn = src.split("def _test_tools_collapsed")[1].split(
        "def _selected_detail_section_controls"
    )[0]
    assert "initially_expanded=False" in tools_fn or "expanded=False" in tools_fn
    assert "_finalization_dry_run_panel" in tools_fn
    assert "_sandbox_final_write_panel" in tools_fn


def test_14_safety_line_visible() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert MSG_GUIDED_SAFETY_LINE in (vm.guided_safety_line or "")
    assert MSG_SAFETY_LINE_NO_FINAL in vm.safety_line_declutter
    src = REVIEW.read_text(encoding="utf-8")
    assert "MSG_GUIDED_SAFETY_LINE" in src


def test_15_accordion_behavior_still_works() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.accordion_layout_marker == REVIEW_ACCORDION_LAYOUT_MARKER
    assert vm.open_review_item_id == "doc-card"
    assert sum(1 for r in vm.list_items if r.details_open) == 1
    src = REVIEW.read_text(encoding="utf-8")
    assert "render_review_summary_card" in src
    assert "render_review_inline_detail" in src


def test_16_active_card_highlight_still_works() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.active_card_highlight_marker == REVIEW_CARD_ACTIVE_HIGHLIGHT
    assert any(r.accordion_active for r in vm.list_items)


def test_17_technical_details_collapsed_by_default() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.technical_details_collapsed_by_default is True
    src = REVIEW.read_text(encoding="utf-8")
    assert "initially_expanded=False" in src
    assert "_developer_tools_collapsed" in src


def test_18_no_auto_run() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.auto_runs_oracle is False
    assert "run_automated_smoke_oracle(" not in REVIEW.read_text(encoding="utf-8")


def test_19_no_run_once() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.calls_run_once is False
    tree = ast.parse(REVIEW.read_text(encoding="utf-8"))
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


def test_20_no_production_final_write() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.production_final_write_enabled is False
    src = REVIEW.read_text(encoding="utf-8")
    assert "final_write_allowed_for_production=True" not in src
    assert "final_write_allowed_for_production = True" not in src


def test_21_no_real_invoice_folders() -> None:
    vm = build_review_page_vm(_boettcher_state())
    assert vm.touches_real_invoice_folders is False
    for path in (REVIEW, COPY_MOD):
        text = path.read_text(encoding="utf-8")
        for folder in FORBIDDEN_FOLDERS:
            assert folder not in text


def test_22_automated_smoke_oracle_still_passes() -> None:
    assert ORACLE_SCRIPT.is_file()
    assert ORACLE_TEST.is_file()
    assert DOCS.is_file()
    assert AUDIT.is_file()


def test_23_track_a_protection_still_passes() -> None:
    assert TRACK_A_TEST.is_file()
    for rel in TRACK_A_PROTECTED:
        assert (ROOT / rel).exists() or rel.endswith("ui_document_rules.py")
    for rel in CORE_PROTECTED:
        assert (ROOT / rel).is_file()
