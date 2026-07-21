"""LED-Centrum order confirmation: explicit PayPal beats weak vendor AMEX noise."""
from __future__ import annotations

import json
from pathlib import Path

from invoice_tool.classification import classify_document_type
from invoice_tool.config import (
    load_app_config,
    load_office_rules,
    load_office_rules_from_dict,
    merge_rules_dicts,
)
from invoice_tool.models import ExtractedData
from invoice_tool.processing import InvoiceProcessor
from invoice_tool.profile_compiler import compile_profile_to_rules
from invoice_tool.routing import detect_payment_method, labeled_document_payment_methods
from invoice_tool.routing_guards import (
    evaluate_business_non_invoice_document,
    evaluate_payment_evidence_precedence,
)
from invoice_tool.supplier_routing import resolve_supplier_profile_routing
from tests.test_cursor_anysphere_consistency import _cursor_vendor_profile, _extracted
from tests.test_invoice_tool import StubExtractor, create_pdf, make_test_setup
from tests.test_recipient_duplicate_anthropic_fix import _sample_profile


def _adobe_vendor_profile() -> dict:
    profile = _sample_profile()
    vendors = list(profile.get("vendor_profiles") or [])
    vendors.append(
        {
            "id": "adobe-creative",
            "label": "Adobe Creative Cloud",
            "recognition_hints": [
                "adobe",
                "adobe inc",
                "adobe systems",
                "adobe.com",
                "creativecloud",
            ],
            "payment_field": "amex",
            "enabled": True,
        }
    )
    profile["vendor_profiles"] = vendors
    return profile


def _rules_with_adobe_vendor(tmp_path: Path, documents_dir: Path):
    base = json.loads(Path("office_rules.json").read_text(encoding="utf-8"))
    base["presets"]["office_default"]["dokumente"]["basis_pfad"] = str(documents_dir)
    merged = merge_rules_dicts(base, compile_profile_to_rules(_adobe_vendor_profile()))
    rules_path = tmp_path / "rules_adobe.json"
    rules_path.write_text(json.dumps(merged), encoding="utf-8")
    return load_office_rules(rules_path), rules_path


def _led_centrum_order_confirmation(*, adobe_noise: bool = True) -> ExtractedData:
    adobe_footer = (
        "Um die zum Download angebotenen PDF-Dateien zu öffnen, benötigen Sie ein "
        "Zusatzprogramm, wie zum Beispiel den Adobe Reader, welchen Sie im Internet "
        "kostenfrei herunterladen können. "
        if adobe_noise
        else ""
    )
    return ExtractedData(
        invoice_date_raw="19.05.2026",
        supplier_raw="LED Centrum",
        amount_raw="29,01",
        raw_text=(
            "Von: info@led-centrum.de Betreff: Ihre Bestellung 635413 "
            "hiermit bestätigen wir den Eingang Ihrer Bestellung "
            "Rechnungsadresse SOMAA Architektur & Innenarchitektur "
            "Alexander Tandawardaja Bismarckstrasse 63 70197 Stuttgart Germany "
            "Lieferadresse MK-WoMo-Service Martin Kohnle Burgstraße 52 "
            "73642 Welzheim Germany "
            "Zahlungsmethode: PayPal Bestellnummer: 635413 "
            "USt-IdNr.: DE189417758 "
            "6er Pack Osram GU5.3 MR16 LED Strahler Summe: 29,01 EUR "
            f"{adobe_footer}"
        ),
        address_fragments=[
            "SOMAA Architektur & Innenarchitektur",
            "Alexander Tandawardaja",
            "Bismarckstrasse 63",
            "MK-WoMo-Service",
            "Burgstraße 52",
        ],
        payment_method_raw="paypal",
        document_name_raw="Bestellbestaetigung LED Leuchtmittel",
        source_method="openai",
    )


def _acme_order_confirmation_with_noise() -> ExtractedData:
    return ExtractedData(
        invoice_date_raw="10.06.2026",
        supplier_raw="ACME GmbH",
        amount_raw="42,00",
        raw_text=(
            "ACME GmbH Order Confirmation "
            "hiermit bestätigen wir den Eingang Ihrer Bestellung "
            "Rechnungsadresse ACME Billing GmbH Musterstrasse 1 10115 Berlin "
            "Lieferadresse ACME Warehouse Lagerweg 2 10115 Berlin "
            "Zahlungsmethode: PayPal Bestellnummer: ACME-9001 Summe: 42,00 EUR "
            "Zum Öffnen der AGB benötigen Sie den Adobe Reader. "
        ),
        address_fragments=["ACME Billing GmbH", "Musterstrasse 1", "10115 Berlin"],
        payment_method_raw="paypal",
        provider_mentions=["American Express", "AMEX"],
        context_markers=["legacy_output_amex.pdf"],
        document_name_raw="Order Confirmation ACME",
        source_method="openai",
    )


def test_led_centrum_is_not_invoice_and_is_order_confirmation() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = _led_centrum_order_confirmation()
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "document"
    decision = evaluate_business_non_invoice_document(extracted, classification)
    assert decision.is_business_non_invoice is True
    assert decision.subtype == "order_confirmation"
    assert decision.has_business_billing_signal is True


def test_led_centrum_keeps_ai_and_explicit_paypal(tmp_path: Path) -> None:
    config_path, _rules_path, input_dir, output_dir, documents_dir = make_test_setup(
        tmp_path
    )
    rules, rules_path = _rules_with_adobe_vendor(tmp_path, documents_dir)
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    config_data["regeln_datei"] = str(rules_path)
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    config = load_app_config(config_path)

    create_pdf(input_dir / "260519_er_ai_haus-und-licht_394-2_amex.pdf")
    extracted = _led_centrum_order_confirmation(adobe_noise=True)
    # Filename/provider noise must not become payment truth.
    extracted = ExtractedData(
        invoice_date_raw=extracted.invoice_date_raw,
        supplier_raw=extracted.supplier_raw,
        amount_raw=extracted.amount_raw,
        raw_text=extracted.raw_text,
        address_fragments=list(extracted.address_fragments),
        payment_method_raw="amex",
        provider_mentions=["American Express"],
        context_markers=["260519_er_ai_haus-und-licht_394-2_amex.pdf"],
        document_name_raw=extracted.document_name_raw,
        source_method="openai",
    )

    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_adobe_vendor_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.dokumenttyp in {"order_confirmation", "business_purchase_document"}
    assert result.dokumenttyp != "invoice"
    assert result.art == "ai"
    assert result.payment_field in {"paypal", "paypal-unklar"}
    assert "amex" not in (result.payment_field or "").lower()
    assert result.storage_file.parent == output_dir / "unklar"
    name = result.storage_file.name.lower()
    assert "paypal" in name
    assert "amex" not in name
    assert "_er_" not in name
    assert "_d_" in name or name.startswith("260519_d_")


def test_input_filename_amex_does_not_force_amex(tmp_path: Path) -> None:
    config_path, _rules_path, input_dir, _output_dir, documents_dir = make_test_setup(
        tmp_path
    )
    rules, rules_path = _rules_with_adobe_vendor(tmp_path, documents_dir)
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    config_data["regeln_datei"] = str(rules_path)
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    config = load_app_config(config_path)

    create_pdf(input_dir / "led_amex.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_led_centrum_order_confirmation()),
        office_rules=rules,
        profile_data=_adobe_vendor_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    lowered = result.storage_file.name.lower()
    assert "paypal" in lowered
    assert "amex" not in lowered


def test_adobe_reader_noise_does_not_override_labeled_paypal() -> None:
    base = json.loads(Path("office_rules.json").read_text(encoding="utf-8"))
    merged = merge_rules_dicts(base, compile_profile_to_rules(_adobe_vendor_profile()))
    rules = load_office_rules_from_dict(merged, base_dir=Path("."))
    extracted = _led_centrum_order_confirmation(adobe_noise=True)
    assert "paypal" in labeled_document_payment_methods(extracted)
    precedence = evaluate_payment_evidence_precedence(extracted, rules.preset)
    assert precedence.payment_decision.payment_method == "paypal"
    assert precedence.strong_amex_body_evidence is False
    decision = detect_payment_method(extracted, rules.preset)
    assert decision.payment_method == "paypal"
    assert "adobe" not in decision.begruendung.lower() or "vorrang" in decision.begruendung.lower()


def test_neutral_acme_order_confirmation_paypal_not_amex(tmp_path: Path) -> None:
    config_path, _rules_path, input_dir, output_dir, documents_dir = make_test_setup(
        tmp_path
    )
    rules, rules_path = _rules_with_adobe_vendor(tmp_path, documents_dir)
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    config_data["regeln_datei"] = str(rules_path)
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    config = load_app_config(config_path)

    create_pdf(input_dir / "acme_order.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_acme_order_confirmation_with_noise()),
        office_rules=rules,
        profile_data=_adobe_vendor_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.dokumenttyp in {"order_confirmation", "business_purchase_document"}
    assert result.dokumenttyp != "invoice"
    assert result.payment_field in {"paypal", "paypal-unklar"}
    assert "amex" not in (result.payment_field or "").lower()
    name = result.storage_file.name.lower()
    assert "paypal" in name
    assert "amex" not in name
    assert result.storage_file.parent == output_dir / "unklar"


def test_cursor_anysphere_still_ai_amex_with_real_amex_evidence(tmp_path: Path) -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = _extracted(
        amount="20.00",
        invoice_number="INV-CUR-PAY",
        supplier_raw="Anysphere Inc",
    )
    match = resolve_supplier_profile_routing(
        extracted, rules.preset, _cursor_vendor_profile()
    )
    assert match is not None
    assert match.routing.payment_field == "amex"

    payment = detect_payment_method(extracted, rules.preset)
    assert payment.payment_method == "amex"

    config_path, rules_path, input_dir, output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "cursor.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_cursor_vendor_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.art == "ai"
    assert result.payment_field == "amex"
    assert result.storage_file.parent == output_dir / "amex"
    assert "amex" in result.storage_file.name.lower()
