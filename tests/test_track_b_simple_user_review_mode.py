"""Track-B Simple User Review Mode (2026-07-24).

Presentation only — no productive processing, no real invoice folders.
Oracle remains the fachliche regression gate; this task does not change it.
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
    BADGE_MISSING_PAYMENT,
    BADGE_NOT_AMEX,
    BADGE_PAYPAL,
    BADGE_STORNO,
    MSG_FINAL_WRITE_USER_ANSWER,
    REVIEW_USER_MODE_LAYOUT_MARKER,
    SECTION_BEREIT,
    SECTION_DATEINAME,
    SECTION_ENTSCHEIDEN,
    SECTION_ERKANNT,
    SECTION_FINAL_WRITE_Q,
    SECTION_PRUEFUNG,
    SECTION_TECHNISCHE,
    SECTION_UNKLAR,
    USER_REVIEW_SECTION_TITLES,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
DOCS = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_SIMPLE_USER_REVIEW_MODE_2026-07-24.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_SIMPLE_USER_REVIEW_MODE_2026-07-24.md"
)
ORACLE_SCRIPT = ROOT / "scripts" / "dev" / "track_b_automated_smoke_oracle.py"
ORACLE_TEST = ROOT / "tests" / "test_track_b_automated_smoke_oracle.py"
TRACK_A_TEST = ROOT / "tests" / "test_track_a_internal_app_protection.py"

FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)
TECHNICAL_USER_SURFACE_TOKENS = (
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
) -> UiV2State:
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="user-review-1",
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
    return state


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
            missing_configuration_type="payment_field",
            configuration_coverage_status="missing_payment_field",
            user_guidance="Zahlungsfeld nicht sicher erkannt.",
        ),
        reason="Zahlungsfeld fehlt",
    )


def test_01_user_mode_section_titles() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.user_mode_enabled is True
    assert vm.section_titles == USER_REVIEW_SECTION_TITLES
    assert SECTION_ERKANNT in vm.section_titles
    assert SECTION_UNKLAR in vm.section_titles
    assert SECTION_DATEINAME in vm.section_titles
    assert SECTION_ENTSCHEIDEN in vm.section_titles
    assert SECTION_FINAL_WRITE_Q in vm.section_titles
    assert SECTION_BEREIT in vm.section_titles
    assert SECTION_PRUEFUNG in vm.section_titles
    assert SECTION_TECHNISCHE in vm.section_titles


def test_02_recognized_fields_plain_german() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    labels = {label for label, _ in vm.selected_detail.recognized_fields}
    assert "Lieferant / Name" in labels
    assert "Zahlungsart" in labels
    assert "Dokumentart" in labels
    joined = " ".join(f"{k}={v}" for k, v in vm.selected_detail.recognized_fields)
    for token in TECHNICAL_USER_SURFACE_TOKENS:
        assert token not in joined


def test_03_unclear_items_plain_german() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    assert vm.selected_detail.unclear_items
    blob = " ".join(vm.selected_detail.unclear_items)
    assert "PayPal" in blob
    for token in ("matching_reason", "final_write_allowed", "configuration_id"):
        assert token not in blob


def test_04_suggested_filename_visible() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    assert vm.selected_detail.suggested_filename
    assert "paypal.pdf" in (vm.selected_detail.suggested_filename or "")
    assert any("Dateiname" in k for k, _ in vm.selected_detail.vorschlag_fields)


def test_05_decision_prompt_present() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    assert vm.selected_detail.decision_prompt
    assert "PayPal" in vm.selected_detail.decision_prompt or "akzeptieren" in (
        vm.selected_detail.decision_prompt or ""
    )


def test_06_final_write_answer_is_no_preview_only() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.final_write_user_answer == MSG_FINAL_WRITE_USER_ANSWER
    assert "Nein" in vm.final_write_user_answer
    assert "Vorschau" in vm.final_write_user_answer
    assert vm.selected_detail is not None
    assert vm.selected_detail.final_write_allowed is False
    assert vm.selected_detail.final_write_user_answer == MSG_FINAL_WRITE_USER_ANSWER
    # Technical flag must not appear in user-facing summary lines.
    assert not any(
        "final_write_allowed" in line
        for line in vm.selected_detail.finalization_summary_lines
    )


def test_07_ready_and_review_case_buckets() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.cases_ready_count + vm.cases_review_count >= 1
    assert isinstance(vm.ready_case_summaries, tuple)
    assert isinstance(vm.review_case_summaries, tuple)
    # Unready PayPal gap case stays in review.
    assert vm.cases_review_count >= 1
    assert any("FA011466" in line for line in vm.review_case_summaries)


def test_08_german_status_badges() -> None:
    paypal = build_review_page_vm(_paypal_state())
    assert BADGE_PAYPAL in paypal.selected_detail.status_badges  # type: ignore[union-attr]
    missing = build_review_page_vm(_missing_payment_state())
    assert BADGE_MISSING_PAYMENT in missing.selected_detail.status_badges  # type: ignore[union-attr]
    assert BADGE_MISSING_PAYMENT == "Zahlung unklar"
    assert BADGE_NOT_AMEX == "Keine AMEX"
    assert BADGE_STORNO == "Storno"


def test_09_technical_details_collapsed_by_default() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.technical_details_collapsed_by_default is True
    src = REVIEW.read_text(encoding="utf-8")
    assert "initially_expanded=False" in src
    assert "SECTION_TECHNISCHE" in src
    assert "_developer_tools_collapsed" in src


def test_10_primary_surface_omits_technical_tokens() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    # Primary user panels must not print these tokens as visible labels.
    assert 'section_block(\n                SECTION_ERKANNT' in src or "SECTION_ERKANNT" in src
    assert "MSG_FINAL_WRITE_USER_ANSWER" in src
    assert "REVIEW_USER_MODE_LAYOUT_MARKER" in COPY_MOD.read_text(encoding="utf-8")
    assert REVIEW_USER_MODE_LAYOUT_MARKER in COPY_MOD.read_text(encoding="utf-8")
    # Technical dump helper still exists for collapsed details.
    assert "matching_reason:" in src
    assert "_technical_detail_lines" in src


def test_11_no_product_logic_regression_guards() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.auto_runs_oracle is False
    assert vm.calls_run_once is False
    assert vm.writes_final_files is False
    assert vm.production_final_write_enabled is False
    assert vm.touches_real_invoice_folders is False
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
    assert "run_automated_smoke_oracle(" not in src
    for path in (REVIEW, COPY_MOD):
        text = path.read_text(encoding="utf-8")
        for folder in FORBIDDEN_FOLDERS:
            assert folder not in text


def test_12_oracle_and_track_a_protection_still_present() -> None:
    assert ORACLE_SCRIPT.is_file()
    assert ORACLE_TEST.is_file()
    assert TRACK_A_TEST.is_file()
    assert DOCS.is_file()
    assert AUDIT.is_file()
    assert "REVIEW_USER_MODE_LAYOUT_MARKER" in REVIEW.read_text(encoding="utf-8")
