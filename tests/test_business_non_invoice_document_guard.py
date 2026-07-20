"""Business non-invoice documents keep art/payment without becoming invoices."""
from __future__ import annotations

from pathlib import Path

from invoice_tool.classification import classify_document_type
from invoice_tool.config import load_app_config, load_office_rules
from invoice_tool.models import ExtractedData
from invoice_tool.processing import InvoiceProcessor
from invoice_tool.routing_guards import (
    evaluate_business_non_invoice_document,
    evaluate_document_type_guard,
    evaluate_invoice_direction_guard,
)
from invoice_tool.saas_product_model import (
    classification_policy_ui_texts,
    default_classification_policy,
)
from invoice_tool.supplier_routing import resolve_supplier_profile_routing
from invoice_tool.ui_v2.saas_profile_surface import (
    build_saas_profile_surface_vm,
    surface_payload_as_dict,
)
from tests.test_amazon_mixed_billing_delivery_address_guard import (
    _business_billing_amazon_extracted,
    _mixed_amazon_extracted,
)
from tests.test_amazon_supplier_rule import _amazon_profile
from tests.test_cursor_anysphere_consistency import _cursor_vendor_profile, _extracted
from tests.test_invoice_tool import StubExtractor, create_pdf, make_test_setup
from tests.test_recipient_duplicate_anthropic_fix import _sample_profile


PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "AMEX-1005",
    "vobaai",
    "vobaep",
    "Bismarck",
    "Rötestr",
)


def _led_centrum_order_confirmation() -> ExtractedData:
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
            "6er Pack Osram GU5.3 MR16 LED Strahler Summe: 29,01 EUR"
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


def _boettcher_invoice() -> ExtractedData:
    return ExtractedData(
        invoice_date_raw="18.06.2026",
        supplier_raw="Boettcher AG Stadtroda",
        amount_raw="68,94",
        invoice_number_raw="RE-2026-4411",
        raw_text=(
            "Rechnung RE-2026-4411 Boettcher AG Stadtroda "
            "Rechnungsadresse SOMAA Architektur Bismarckstrasse 63 Stuttgart "
            "MwSt. 19% Nettobetrag 57,93 EUR Bruttobetrag 68,94 EUR "
            "Zahlungsbedingungen: 14 Tage netto"
        ),
        address_fragments=[
            "SOMAA Architektur",
            "Bismarckstrasse 63",
            "Stuttgart",
        ],
        source_method="openai",
    )


def test_led_centrum_is_order_confirmation_not_invoice() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = _led_centrum_order_confirmation()
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "document"
    decision = evaluate_business_non_invoice_document(extracted, classification)
    assert decision.is_business_non_invoice is True
    assert decision.subtype == "order_confirmation"
    assert decision.has_business_billing_signal is True


def test_led_centrum_keeps_ai_and_paypal_not_neutral_document(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "led.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_led_centrum_order_confirmation()),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.dokumenttyp in {"order_confirmation", "business_purchase_document"}
    assert result.dokumenttyp != "invoice"
    assert result.art == "ai"
    assert result.payment_field == "paypal"
    assert result.storage_file.parent == output_dir / "unklar"
    name = result.storage_file.name.lower()
    assert "_ai_" in name
    assert "paypal" in name
    assert "_er_" not in name
    assert name.startswith("260519_d_") or "_d_ai_" in name


def test_filename_has_ai_paypal_not_er(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "led2.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_led_centrum_order_confirmation()),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    lowered = result.storage_file.name.lower()
    assert "ai" in lowered
    assert "paypal" in lowered
    assert not lowered.startswith("260519_er_")
    assert "_er_" not in lowered


def test_boettcher_real_invoice_stays_er_ai_unklar(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "boettcher.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_boettcher_invoice()),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.dokumenttyp == "invoice"
    assert result.art == "ai"
    assert result.payment_field == "unklar"
    assert result.storage_file.parent == output_dir / "unklar"
    assert "_er_" in result.storage_file.name.lower()
    assert "vobaai" not in result.storage_file.name.lower()


def test_amazon_mixed_billing_guard_still_unklar() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    match = resolve_supplier_profile_routing(
        _mixed_amazon_extracted(), rules.preset, _amazon_profile()
    )
    assert match is None


def test_amazon_clear_business_billing_still_matches() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    match = resolve_supplier_profile_routing(
        _business_billing_amazon_extracted(), rules.preset, _amazon_profile()
    )
    assert match is not None
    assert match.routing.art == "ai"
    assert match.routing.payment_field == "amex"


def test_cursor_anysphere_still_ai_amex(tmp_path: Path) -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = _extracted(
        amount="20.00",
        invoice_number="INV-CUR-1",
        supplier_raw="Anysphere Inc",
    )
    match = resolve_supplier_profile_routing(
        extracted, rules.preset, _cursor_vendor_profile()
    )
    assert match is not None
    assert match.rule_id == "cursor-anysphere"
    assert match.routing.payment_field == "amex"

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


def test_datev_jahreskonto_remains_document_accounting_report() -> None:
    extracted = ExtractedData(
        invoice_date_raw="01.01.2026",
        supplier_raw="DATEV",
        amount_raw="0,00",
        raw_text=(
            "DATEV Jahreskonto Kanzlei-Rechnungswesen "
            "Ungeklärte Posten Konto 1590 Auswertung entspricht dem derzeitigen "
            "Stand der Buchführung"
        ),
        source_method="openai",
    )
    decision = evaluate_document_type_guard(extracted)
    assert decision.force_document is True
    assert decision.document_type == "accounting_report"


def test_outgoing_invoice_not_incoming() -> None:
    extracted = ExtractedData(
        invoice_date_raw="01.04.2026",
        supplier_raw="SOMAA - Dipl.Ing. Alexander Tandawardaja",
        amount_raw="4800,00",
        invoice_number_raw="2026-014",
        raw_text=(
            "SOMAA - Dipl.Ing. Alexander Tandawardaja Rechnung "
            "Rechnungs-Nr 2026-014 Berechne ich für Architekturleistung "
            "Herrn Maucher Projekt Umbau Endbetrag 4800,00 EUR Honorar"
        ),
        source_method="openai",
    )
    direction = evaluate_invoice_direction_guard(extracted, _sample_profile())
    assert direction.is_outgoing is True


def test_ui_v2_business_document_policy_generic() -> None:
    policy = default_classification_policy()
    bdp = policy.business_document_policy
    assert bdp.classify_order_confirmations is True
    assert bdp.order_confirmation_is_not_invoice is True
    assert bdp.preserve_business_assignment_for_non_invoice_documents is True
    assert bdp.preserve_payment_method_for_non_invoice_documents is True
    assert bdp.non_invoice_business_document_target == "unklar"
    texts = " ".join(classification_policy_ui_texts())
    assert "Bestellbestätigungen von Rechnungen unterscheiden" in texts
    assert "Zahlungsmethode auch bei Nicht-Rechnungen erkennen" in texts
    vm = build_saas_profile_surface_vm()
    assert "business_document_policy" in vm.ui_labels
    payload = surface_payload_as_dict(vm)
    assert payload["classification_policy"]["business_document_policy"][
        "order_confirmation_is_not_invoice"
    ] is True
    blob = str(payload) + texts
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
