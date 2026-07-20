"""Cursor/Anysphere consistency: same use-case must not flip between ai and private."""
from __future__ import annotations

from pathlib import Path

from invoice_tool.config import load_app_config, load_office_rules
from invoice_tool.models import ExtractedData
from invoice_tool.processing import InvoiceProcessor
from invoice_tool.routing import determine_business_context, detect_payment_method, resolve_account
from invoice_tool.software_ai_tools import (
    evaluate_software_ai_tool_context,
    is_software_ai_coding_tool_invoice,
)
from invoice_tool.supplier_routing import resolve_supplier_profile_routing
from tests.test_invoice_tool import StubExtractor, create_pdf, make_test_setup


def _cursor_vendor_profile() -> dict:
    return {
        "recipient_policy": {
            "business_recipient_hints": [
                "somaa",
                "tandawardaja",
                "bismarckstrasse",
            ],
            "private_recipient_hints": ["roetestrasse"],
            "foreign_recipient_block_hints": [],
        },
        "vendor_profiles": [
            {
                "id": "cursor-anysphere",
                "label": "Cursor / Anysphere",
                "recognition_hints": [
                    "anysphere",
                    "cursor pro",
                    "cursor usage",
                    "hi@cursor.com",
                    "cursor.com",
                ],
                "payment_field": "amex",
                "enabled": True,
                "exclusive": True,
            }
        ],
    }


def _cursor_invoice_text(
    *,
    amount: str,
    invoice_number: str,
    refund: bool = False,
    mid_month_negative: bool = False,
    business_signals: bool = True,
) -> str:
    bill_to = (
        "Bill to A S TANDAWARDAJA Bismarckstraße 63 70197 Stuttgart "
        "haditan@somaa.de "
        if business_signals
        else "Bill to Private Person Some Street 1 "
    )
    text = (
        f"Invoice {invoice_number} Cursor Anysphere Inc "
        f"{bill_to}"
        f"hi@cursor.com cursor.com "
        f"Cursor Usage token-based usage GPT Claude Codex "
        f"Amount {amount} USD "
        "Payment history American Express - 1005 "
    )
    if refund:
        text += "Refund Credit adjustment -12.00 "
    if mid_month_negative:
        text += "Mid-month usage paid -40.00 "
    return text


def _extracted(
    *,
    amount: str,
    invoice_number: str,
    supplier_raw: str,
    refund: bool = False,
    mid_month_negative: bool = False,
    business_signals: bool = True,
) -> ExtractedData:
    return ExtractedData(
        invoice_date_raw="27.05.2026",
        supplier_raw=supplier_raw,
        amount_raw=amount,
        invoice_number_raw=invoice_number,
        raw_text=_cursor_invoice_text(
            amount=amount,
            invoice_number=invoice_number,
            refund=refund,
            mid_month_negative=mid_month_negative,
            business_signals=business_signals,
        ),
        address_fragments=(
            ["Bismarckstraße 63", "70197 Stuttgart", "A S TANDAWARDAJA"]
            if business_signals
            else ["Some Street 1"]
        ),
        provider_mentions=["cursor", "anysphere"],
        context_markers=["cursor usage", "token-based usage"],
        document_type_indicators=["invoice"],
        card_endings=["1005"],
        apple_pay_endings=[],
        payment_method_raw="American Express - 1005",
        source_method="openai",
    )


def _process(tmp_path: Path, extracted: ExtractedData, profile: dict | None = None):
    config_path, rules_path, input_dir, _output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / f"{extracted.invoice_number_raw or 'cursor'}.pdf"
    create_pdf(pdf)
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=profile if profile is not None else _cursor_vendor_profile(),
    )
    results = processor.process_all()
    assert len(results) == 1
    return results[0], rules


def test_cursor_be0kjys5_0016_amount_101_10_is_ai_amex(tmp_path: Path) -> None:
    extracted = _extracted(
        amount="101.10",
        invoice_number="BE0KJYS5-0016",
        supplier_raw="Cursor",
    )
    result, _rules = _process(tmp_path, extracted)
    assert result.art == "ai"
    assert result.payment_field == "amex"
    assert result.storage_file.parent.name == "amex"
    assert "private" not in result.storage_file.name


def test_cursor_be0kjys5_0010_amount_59_01_is_ai_amex(tmp_path: Path) -> None:
    extracted = _extracted(
        amount="59.01",
        invoice_number="BE0KJYS5-0010",
        supplier_raw="Cursor / Anysphere Inc\nhi@cursor.com",
        refund=True,
        mid_month_negative=True,
    )
    result, _rules = _process(tmp_path, extracted)
    assert result.art == "ai"
    assert result.payment_field == "amex"
    assert result.storage_file.parent.name == "amex"
    assert "private" not in result.storage_file.name


def test_both_cursor_cases_use_equivalent_rule_chain(tmp_path: Path) -> None:
    profile = _cursor_vendor_profile()
    a = _extracted(
        amount="101.10",
        invoice_number="BE0KJYS5-0016",
        supplier_raw="Cursor",
    )
    b = _extracted(
        amount="59.01",
        invoice_number="BE0KJYS5-0010",
        supplier_raw="Cursor / Anysphere Inc\nhi@cursor.com",
        refund=True,
        mid_month_negative=True,
    )
    path_a = tmp_path / "case_a"
    path_b = tmp_path / "case_b"
    path_a.mkdir()
    path_b.mkdir()
    result_a, rules = _process(path_a, a, profile)
    result_b, _ = _process(path_b, b, profile)

    assert (result_a.art, result_a.payment_field) == (result_b.art, result_b.payment_field) == (
        "ai",
        "amex",
    )
    assert result_a.storage_file.parent.name == result_b.storage_file.parent.name == "amex"

    # B hits payment-only supplier profile (art deferred); A may not — both refine to ai/amex.
    match_b = resolve_supplier_profile_routing(b, rules.preset, profile)
    assert match_b is not None
    assert match_b.rule_id == "cursor-anysphere"
    assert match_b.art_deferred is True
    assert match_b.economic_assignment is None

    decision_a = evaluate_software_ai_tool_context(
        a,
        art="ai",
        art_reason="Business-Context-Regel",
        street_key="bismarck",
        preset=rules.preset,
    )
    decision_b = evaluate_software_ai_tool_context(
        b,
        art="ai",
        art_reason="Business-Context-Regel",
        street_key="bismarck",
        preset=rules.preset,
    )
    assert decision_a.art == decision_b.art == "ai"
    assert decision_a.has_business_signal and decision_b.has_business_signal


def test_refund_credit_does_not_flip_art_to_private(tmp_path: Path) -> None:
    extracted = _extracted(
        amount="59.01",
        invoice_number="BE0KJYS5-0010",
        supplier_raw="Anysphere Inc hi@cursor.com",
        refund=True,
        mid_month_negative=False,
    )
    result, _ = _process(tmp_path, extracted)
    assert result.art == "ai"
    assert result.payment_field == "amex"
    assert result.art != "private"


def test_mid_month_usage_paid_negative_line_does_not_flip_to_private(tmp_path: Path) -> None:
    extracted = _extracted(
        amount="59.01",
        invoice_number="BE0KJYS5-0010",
        supplier_raw="Cursor / Anysphere",
        refund=False,
        mid_month_negative=True,
    )
    result, _ = _process(tmp_path, extracted)
    assert result.art == "ai"
    assert result.payment_field == "amex"


def test_amex_1005_stays_payment_field_amex(tmp_path: Path) -> None:
    extracted = _extracted(
        amount="101.10",
        invoice_number="BE0KJYS5-0016",
        supplier_raw="Cursor / Anysphere Inc",
    )
    result, rules = _process(tmp_path, extracted)
    payment = detect_payment_method(extracted, rules.preset)
    account = resolve_account(extracted, rules.preset)
    assert "1005" in extracted.card_endings
    assert account.payment_field == "amex"
    assert payment.payment_method == "amex"
    assert result.payment_field == "amex"


def test_cursor_usage_gpt_claude_codex_recognized_as_ai_with_business_signals() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = _extracted(
        amount="101.10",
        invoice_number="BE0KJYS5-0016",
        supplier_raw="Cursor",
        business_signals=True,
    )
    assert is_software_ai_coding_tool_invoice(extracted)
    account = resolve_account(extracted, rules.preset)
    art, art_reason = determine_business_context(
        extracted, account, rules.preset, "bismarck"
    )
    decision = evaluate_software_ai_tool_context(
        extracted,
        art=art,
        art_reason=art_reason,
        street_key="bismarck",
        preset=rules.preset,
    )
    assert decision.is_ai_coding_tool
    assert decision.has_business_signal
    assert decision.art == "ai"


def test_cursor_without_business_signals_goes_to_review_not_blind_ai_or_private(
    tmp_path: Path,
) -> None:
    extracted = _extracted(
        amount="40.00",
        invoice_number="BE0KJYS5-0099",
        supplier_raw="Cursor / Anysphere Inc\nhi@cursor.com",
        business_signals=False,
    )
    result, _ = _process(tmp_path, extracted)
    assert result.art == "unklar"
    assert result.art != "private"
    assert result.art != "ai"
    assert result.storage_file.parent.name == "unklar"


def test_payment_only_supplier_profile_does_not_apply_default_art_private() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    profile = _cursor_vendor_profile()
    extracted = _extracted(
        amount="59.01",
        invoice_number="BE0KJYS5-0010",
        supplier_raw="Anysphere Inc hi@cursor.com",
    )
    match = resolve_supplier_profile_routing(extracted, rules.preset, profile)
    assert match is not None
    assert match.rule_id == "cursor-anysphere"
    assert match.art_deferred is True
    assert match.economic_assignment is None
    assert match.routing.art != "private"
    assert match.routing.payment_field == "amex"
