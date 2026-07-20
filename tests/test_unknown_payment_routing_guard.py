"""Focused payment-evidence guard: no supplier IBAN / bare SOMAA → vobaai."""
from __future__ import annotations

from pathlib import Path

from invoice_tool.config import load_office_rules
from invoice_tool.models import ExtractedData
from invoice_tool.routing import (
    apply_final_assignment,
    determine_business_context,
    detect_payment_method,
    resolve_account,
)
from invoice_tool.routing_guards import (
    apple_pay_without_known_card_reference,
    has_secure_payer_payment_evidence,
)


def test_supplier_iban_bic_is_not_secure_payment_evidence() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.01.2026",
        supplier_raw="Lieferant GmbH",
        amount_raw="10,00",
        raw_text="Rechnung SOMAA IBAN DE44500105175407324931 BIC INGDDEFFXXX",
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    evidence = has_secure_payer_payment_evidence(extracted, account, payment)
    assert evidence.has_secure_evidence is False
    art, _ = determine_business_context(extracted, account, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key="bismarck",
        preset=rules.preset,
        extracted=extracted,
    )
    assert routing.payment_field == "unklar"
    assert routing.zielordner == "unklar"


def test_apple_pay_without_ending_is_not_secure() -> None:
    extracted = ExtractedData(
        invoice_date_raw="01.01.2026",
        supplier_raw="EasyPark",
        amount_raw="2,00",
        raw_text="Total payment via Apple Pay",
        apple_pay_endings=[],
        source_method="openai",
    )
    assert apple_pay_without_known_card_reference(extracted) is True


def test_known_apple_pay_ending_is_secure() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.01.2026",
        supplier_raw="Shop",
        amount_raw="2,00",
        raw_text="Apple Pay SOMAA Bismarckstrasse",
        apple_pay_endings=["6281"],
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    evidence = has_secure_payer_payment_evidence(extracted, account, payment)
    assert evidence.has_secure_evidence is True
    art, _ = determine_business_context(extracted, account, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key="bismarck",
        preset=rules.preset,
        extracted=extracted,
    )
    assert routing.payment_field == "vobaai"
