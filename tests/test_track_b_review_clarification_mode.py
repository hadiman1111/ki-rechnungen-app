"""Track-B Review Clarification Mode (2026-07-24).

Clean user-facing filenames, status vs filename separation,
plain missing-field guidance. UI/UX only.
"""

from __future__ import annotations

from pathlib import Path

from invoice_tool.ui_v2.pages.review import (
    build_review_page_vm,
    set_open_review_item_id,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    CLEAN_USER_FILENAME_MARKER,
    FILENAME_EDIT_SECONDARY_MARKER,
    MSG_CLARIFICATION_STATUS,
    MSG_FILENAME_FOLLOWS_SCHEMA,
    MSG_WHY_MISSING_PAYMENT,
    MSG_WHY_NOT_AMEX,
    MSG_WHY_PAYPAL_DETECTED,
    MSG_WHY_STORNO,
    REVIEW_CLARIFICATION_MARKER,
    clean_user_facing_filename,
    derive_why_review_plain_german,
    review_case_kind,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"


def _planned(**overrides: object) -> ProcessingPlannedDestination:
    base: dict[str, object] = dict(
        document_name="doc.pdf",
        planned_path="preview/x.pdf",
        destination_label="Unklar",
        preview_only=True,
        applied=False,
        suggested_filename="2026-05-23_er_Beispiel_10,00_card.pdf",
        supplier="Beispiel",
        counterparty_name="Beispiel",
        invoice_date="2026-05-23",
        amount="10,00",
        selected_amount="10,00",
        selected_payment_field="",
        payment_account="",
        selected_art="er",
        matched_configuration_name="Unklar",
        configuration_coverage_status="missing_payment",
        user_guidance="Zahlungsart fehlt.",
    )
    base.update(overrides)
    return ProcessingPlannedDestination(**base)  # type: ignore[arg-type]


def _state(planned: ProcessingPlannedDestination, document_id: str = "d1") -> UiV2State:
    run = ProcessingRunState(
        status="completed",
        message="Vorschau",
        run_id="clarification-1",
        review_items=(
            ProcessingReviewItem(
                document_name=planned.document_name,
                reason="Prüfung erforderlich",
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
    set_open_review_item_id(state, document_id)
    return state


def test_clean_filename_strips_review_required_suggested() -> None:
    dirty = "REVIEW_REQUIRED__SUGGESTED__2026-05-23_er_Böttcher_AG_84,39_card.pdf"
    assert clean_user_facing_filename(dirty) == "2026-05-23_er_Böttcher_AG_84,39_card.pdf"


def test_clean_filename_strips_suggested_only() -> None:
    dirty = "SUGGESTED__2026-05-11_er_LUMITOP_476,00_paypal.pdf"
    assert "SUGGESTED" not in clean_user_facing_filename(dirty)


def test_status_and_schema_copy_in_review_source() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "MSG_CLARIFICATION_STATUS" in src
    assert "MSG_FILENAME_FOLLOWS_SCHEMA" in src
    assert "REVIEW_CLARIFICATION_MARKER" in src
    assert "CLEAN_USER_FILENAME_MARKER" in src
    assert "FILENAME_EDIT_SECONDARY_MARKER" in src
    assert MSG_CLARIFICATION_STATUS.startswith("Zur Prüfung")
    assert MSG_FILENAME_FOLLOWS_SCHEMA.startswith("Der Dateiname folgt")
    assert REVIEW_CLARIFICATION_MARKER
    assert CLEAN_USER_FILENAME_MARKER
    assert FILENAME_EDIT_SECONDARY_MARKER


def test_missing_payment_guidance_plain_german() -> None:
    assert MSG_WHY_MISSING_PAYMENT == "Zahlungsart fehlt. Bitte Zahlungsart prüfen."
    planned = _planned(selected_payment_field="", payment_account="")
    why = derive_why_review_plain_german(planned)
    assert any("Zahlungsart fehlt" in line for line in why)


def test_card_amex_guidance() -> None:
    assert MSG_WHY_NOT_AMEX == "Kartenzahlung erkannt, aber AMEX ist nicht belegt."


def test_paypal_and_storno_guidance() -> None:
    assert MSG_WHY_PAYPAL_DETECTED == "PayPal erkannt."
    assert MSG_WHY_STORNO == "Storno erkannt."


def test_review_vm_builds_with_prefixed_suggested_name() -> None:
    planned = _planned(
        suggested_filename="REVIEW_REQUIRED__SUGGESTED__2026-05-23_er_Böttcher_AG_84,39_card.pdf",
        selected_payment_field="card",
        payment_account="card",
        user_guidance=MSG_WHY_NOT_AMEX,
    )
    vm = build_review_page_vm(_state(planned, "boettcher"))
    assert vm.selected_detail is not None
    dirty = (
        vm.selected_detail.preview_filename
        or vm.selected_detail.suggested_filename
        or ""
    )
    assert "REVIEW_REQUIRED" not in clean_user_facing_filename(dirty)


def test_case_kind_helpers_still_work() -> None:
    planned = _planned(selected_payment_field="paypal", payment_account="paypal")
    kind = review_case_kind(planned)
    assert kind in {"paypal", "generic", "missing_payment", "card_not_amex", "storno"}
