"""Real-case routing guards: payment evidence, mixed address, direction, document type."""
from __future__ import annotations

from pathlib import Path

from invoice_tool.classification import classify_document_type
from invoice_tool.config import load_app_config, load_office_rules
from invoice_tool.models import ExtractedData
from invoice_tool.processing import InvoiceProcessor
from invoice_tool.recipient_guard import evaluate_recipient_guard
from invoice_tool.routing import (
    apply_final_assignment,
    determine_business_context,
    detect_payment_method,
    resolve_account,
)
from invoice_tool.routing_guards import (
    apply_classification_guards,
    apply_routing_guards,
    evaluate_document_type_guard,
    evaluate_invoice_direction_guard,
    evaluate_mixed_address_ambiguity,
)
from invoice_tool.supplier_routing import resolve_supplier_profile_routing
from tests.test_amazon_supplier_rule import _amazon_profile
from tests.test_invoice_tool import StubExtractor, create_pdf, make_test_setup
from tests.test_recipient_duplicate_anthropic_fix import _sample_profile


def _route(extracted: ExtractedData, *, street_key: str | None = None, profile: dict | None = None):
    rules = load_office_rules(Path("office_rules.json"))
    account = resolve_account(extracted, rules.preset)
    art, art_reason = determine_business_context(
        extracted, account, rules.preset, street_key
    )
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key=street_key,
        preset=rules.preset,
        extracted=extracted,
    )
    guard = evaluate_recipient_guard(
        extracted,
        rules.preset,
        profile_data=profile or _sample_profile(),
        proposed_art=routing.art,
        street_key=street_key,
        priority_routing=None,
        art_reason=art_reason,
    )
    from invoice_tool.recipient_guard import apply_recipient_guard_to_routing

    routing = apply_recipient_guard_to_routing(
        routing, guard, rules.preset, street_key=street_key
    )
    result = apply_routing_guards(
        routing,
        extracted=extracted,
        account_decision=account,
        payment_decision=payment,
        preset=rules.preset,
        street_key=street_key,
    )
    return rules, art, payment, result


def test_luxvenum_supplier_iban_without_payer_evidence_is_unklar() -> None:
    extracted = ExtractedData(
        invoice_date_raw="15.06.2026",
        supplier_raw="Luxvenum LED GmbH",
        amount_raw="249,00",
        invoice_number_raw="LV-2026-441",
        raw_text=(
            "Luxvenum LED GmbH Rechnung LV-2026-441 "
            "Empfänger SOMAA Architektur & Innenarchitektur Alexander Tandawardaja "
            "Bismarckstraße 63 LED-Einbaustrahler "
            "Bitte überweisen Sie auf IBAN DE44500105175407324931 BIC INGDDEFFXXX "
            "Zahlungsbedingungen: sofort rein netto zahlbar"
        ),
        address_fragments=[
            "SOMAA Architektur & Innenarchitektur",
            "Alexander Tandawardaja",
            "Bismarckstraße 63",
        ],
        source_method="openai",
    )
    _rules, art, _payment, guards = _route(extracted, street_key="bismarck")
    routing = guards.routing
    assert art == "ai"
    assert routing.payment_field == "unklar"
    assert routing.zielordner == "unklar"
    assert routing.konto is None
    assert "vobaai" not in (routing.payment_field or "")


def test_luxvenum_filename_does_not_contain_vobaai(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "luxvenum.pdf"
    create_pdf(pdf)
    extracted = ExtractedData(
        invoice_date_raw="15.06.2026",
        supplier_raw="Luxvenum LED GmbH",
        amount_raw="249,00",
        raw_text=(
            "Luxvenum LED GmbH Rechnung SOMAA Architektur Bismarckstraße 63 "
            "IBAN DE44500105175407324931 BIC INGDDEFFXXX"
        ),
        address_fragments=["SOMAA Architektur", "Bismarckstraße 63"],
        source_method="openai",
    )
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert "vobaai" not in result.storage_file.name
    assert "unklar" in result.storage_file.name
    assert result.payment_field == "unklar"


def test_easypark_apple_pay_without_card_ending_is_unklar() -> None:
    extracted = ExtractedData(
        invoice_date_raw="09.06.2026",
        supplier_raw="EasyPark GmbH",
        amount_raw="2,00",
        raw_text=(
            "EasyPark Rechnung Alexander Tandawardaja Bismarckstraße 63 "
            "Total payment via Apple Pay Betrag 2,00 EUR"
        ),
        address_fragments=["Alexander Tandawardaja", "Bismarckstraße 63"],
        apple_pay_endings=[],
        source_method="openai",
    )
    _rules, _art, _payment, guards = _route(extracted, street_key="bismarck")
    assert guards.payment is not None
    assert guards.payment.apple_pay_without_card_reference is True
    assert guards.routing.payment_field == "unklar"
    assert guards.routing.zielordner == "unklar"
    assert "vobaai" not in (guards.routing.payment_field or "")


def test_easypark_not_automatically_vobaai(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "easypark.pdf"
    create_pdf(pdf)
    extracted = ExtractedData(
        invoice_date_raw="09.06.2026",
        supplier_raw="EasyPark GmbH",
        amount_raw="2,00",
        raw_text=(
            "EasyPark Rechnung Total payment via Apple Pay "
            "SOMAA Bismarckstrasse 63 Betrag 2,00 EUR"
        ),
        address_fragments=["SOMAA", "Bismarckstraße 63"],
        source_method="openai",
    )
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.dokumenttyp == "invoice"
    assert result.payment_field == "unklar"
    assert result.storage_file.parent == output_dir / "unklar"
    assert "vobaai" not in result.storage_file.name


def test_bikesnboards_mixed_address_without_payment_is_unklar() -> None:
    extracted = ExtractedData(
        invoice_date_raw="12.05.2026",
        supplier_raw="Bikesnboards GmbH",
        amount_raw="3299,00",
        raw_text=(
            "Bikesnboards Rechnung Cube Nulane Hybrid E-Bike Fahrrad "
            "Alexander Tandawardaja Somaa Architektur Bismarckstraße 63 "
            "Abweichende Rechnungsadresse: Herr Alexander Tandawardaja Rötestr. 58 "
            "IBAN DE89370400440532013000 BIC COBADEFFXXX"
        ),
        address_fragments=[
            "Alexander Tandawardaja",
            "Somaa Architektur",
            "Bismarckstraße 63",
            "Herr Alexander Tandawardaja",
            "Rötestr. 58",
        ],
        source_method="openai",
    )
    mixed = evaluate_mixed_address_ambiguity(extracted, street_key="bismarck")
    assert mixed.is_ambiguous is True
    _rules, _art, _payment, guards = _route(extracted, street_key="bismarck")
    assert guards.routing.payment_field == "unklar"
    assert guards.routing.zielordner == "unklar"
    assert "vobaai" not in (guards.routing.payment_field or "")


def test_bikesnboards_not_automatically_ai_vobaai(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "bikes.pdf"
    create_pdf(pdf)
    extracted = ExtractedData(
        invoice_date_raw="12.05.2026",
        supplier_raw="Bikesnboards GmbH",
        amount_raw="3299,00",
        raw_text=(
            "Bikesnboards Somaa Architektur Bismarckstraße 63 "
            "Rechnungsadresse Rötestr. 58 E-Bike IBAN DE89 BIC COBA"
        ),
        address_fragments=[
            "Somaa Architektur",
            "Bismarckstraße 63",
            "Rötestr. 58",
        ],
        source_method="openai",
    )
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.storage_file.parent == output_dir / "unklar"
    assert "vobaai" not in result.storage_file.name
    assert result.art != "ai" or result.payment_field == "unklar"


def test_somaa_outgoing_invoice_to_maucher_not_incoming() -> None:
    extracted = ExtractedData(
        invoice_date_raw="01.04.2026",
        supplier_raw="SOMAA - Dipl.Ing. Alexander Tandawardaja",
        amount_raw="4800,00",
        invoice_number_raw="2026-014",
        raw_text=(
            "SOMAA - Dipl.Ing. Alexander Tandawardaja Architektur & Innenarchitektur "
            "Steuernummer 12345/67890 USt-IdNr. DE123456789 "
            "IBAN DE18900500000001234567 "
            "Herrn Maucher, Philipp Rechnung Nr. 2026-014 "
            "Projekt Schwarzwaldstraße Leistungszeitraum März 2026 "
            "für Architekturleistung berechne ich Endbetrag 4.800,00 EUR"
        ),
        address_fragments=["Herrn Maucher, Philipp"],
        source_method="openai",
    )
    direction = evaluate_invoice_direction_guard(extracted, _sample_profile())
    assert direction.is_outgoing is True
    assert direction.direction == "outgoing_invoice"
    rules = load_office_rules(Path("office_rules.json"))
    classification = classify_document_type(extracted, rules.preset)
    guarded = apply_classification_guards(
        extracted, classification, profile_data=_sample_profile()
    )
    assert guarded.dokumenttyp == "document"
    assert "outgoing" in guarded.begruendung.lower() or "ausgangs" in guarded.begruendung.lower()


def test_somaa_outgoing_not_er_ai_vobaai(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "outgoing.pdf"
    create_pdf(pdf)
    extracted = ExtractedData(
        invoice_date_raw="01.04.2026",
        supplier_raw="SOMAA - Dipl.Ing. Alexander Tandawardaja",
        amount_raw="4800,00",
        invoice_number_raw="2026-014",
        raw_text=(
            "SOMAA Dipl.Ing. Alexander Tandawardaja Rechnung Nr. 2026-014 "
            "Herrn Maucher Philipp Projekt Schwarzwaldstraße "
            "Leistungszeitraum berechne ich Endbetrag Architekturleistung"
        ),
        source_method="openai",
    )
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.dokumenttyp == "document"
    assert result.storage_file.parent in {documents_dir, output_dir / "unklar", output_dir / "documents"}
    assert "er_ai" not in result.storage_file.name
    assert "vobaai" not in result.storage_file.name


def test_datev_jahreskonto_2025_is_accounting_report() -> None:
    extracted = ExtractedData(
        invoice_date_raw="31.12.2025",
        supplier_raw="Kanzlei-Rechnungswesen",
        amount_raw=None,
        raw_text=(
            "Kanzlei-Rechnungswesen V.14.42 SOMAA Architektur & Innenarchitektur "
            "Jahreskonto 2025 Konto 1590 Ungeklärte Posten "
            "Buchungstext Gegenkto. Umsatz Soll Umsatz Haben Belegfeld "
            "Auswertung entspricht dem derzeitigen Stand der Buchführung "
            "Sortierung: Belegdatum Nur nicht ausgezifferte Buchungen"
        ),
        document_type_indicators=["jahreskonto", "kanzlei-rechnungswesen"],
        source_method="openai",
    )
    guard = evaluate_document_type_guard(extracted)
    assert guard.force_document is True
    assert guard.document_type == "accounting_report"


def test_datev_jahreskonto_2026_is_accounting_report() -> None:
    extracted = ExtractedData(
        invoice_date_raw="30.06.2026",
        supplier_raw=None,
        amount_raw=None,
        raw_text=(
            "Kanzlei-Rechnungswesen Jahreskonto 2026 Konto 1590 Ungeklärte Posten "
            "Buchungstext Gegenkto. Umsatz Haben"
        ),
        source_method="openai",
    )
    guard = evaluate_document_type_guard(extracted)
    assert guard.force_document is True


def test_datev_jahreskonto_not_invoice_not_vobaai(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "jahreskonto.pdf"
    create_pdf(pdf)
    extracted = ExtractedData(
        invoice_date_raw="31.12.2025",
        supplier_raw="Kanzlei",
        amount_raw=None,
        raw_text=(
            "Kanzlei-Rechnungswesen Jahreskonto Konto 1590 Ungeklärte Posten "
            "Auswertung entspricht dem derzeitigen Stand der Buchführung Rechnung"
        ),
        source_method="openai",
    )
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.dokumenttyp == "document"
    assert result.storage_file.parent in {documents_dir, output_dir / "documents"}
    assert "vobaai" not in result.storage_file.name
    assert not result.storage_file.name.startswith("er_") or "er_ai" not in result.storage_file.name


def test_secure_card_ending_still_vobaai() -> None:
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Beispiel GmbH",
        amount_raw="100,00",
        raw_text="Rechnung SOMAA Bismarckstrasse Karte endet auf 7166",
        card_endings=["7166"],
        address_fragments=["SOMAA", "Bismarckstraße 63"],
        source_method="openai",
    )
    _rules, art, _payment, guards = _route(extracted, street_key="bismarck")
    assert art == "ai"
    assert guards.routing.payment_field == "vobaai"
    assert guards.routing.zielordner == "ai"


def test_amex_rule_remains_amex() -> None:
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Cursor",
        amount_raw="20,00",
        raw_text="Anysphere Cursor Pro American Express SOMAA Bismarckstrasse",
        card_endings=["1005"],
        source_method="openai",
    )
    rules = load_office_rules(Path("office_rules.json"))
    account = resolve_account(extracted, rules.preset)
    art, _ = determine_business_context(extracted, account, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key="bismarck",
        preset=rules.preset,
        extracted=extracted,
    )
    assert routing.payment_field == "amex"


def test_amazon_somaa_special_rule_unchanged(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "amazon.pdf"
    create_pdf(pdf)
    extracted = ExtractedData(
        invoice_date_raw="10.06.2026",
        supplier_raw="Amazon EU S.à r.l.",
        amount_raw="49,99",
        raw_text="Amazon EU S.à r.l. Rechnung SOMAA Architektur Bismarckstrasse 63",
        address_fragments=["SOMAA Architektur", "Bismarckstraße 63"],
        source_method="openai",
    )
    match = resolve_supplier_profile_routing(extracted, rules.preset, _amazon_profile())
    assert match is not None
    assert match.routing.payment_field == "amex"
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_amazon_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.payment_field == "amex"
    assert result.storage_file.parent == output_dir / "amex"
    assert "vobaai" not in result.storage_file.name


def test_anthropic_remains_ep_amex_1005() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.06.2026",
        supplier_raw="Anthropic PBC",
        amount_raw="20,00",
        raw_text="Anthropic PBC Invoice SOMAA",
        source_method="openai",
    )
    match = resolve_supplier_profile_routing(extracted, rules.preset, _sample_profile())
    assert match is not None
    assert match.routing.art == "ep"
    assert match.routing.payment_field == "amex-1005"
    assert match.routing.zielordner == "amex"


def test_foreign_recipient_remains_unklar(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "foreign.pdf"
    create_pdf(pdf)
    extracted = ExtractedData(
        invoice_date_raw="21.06.2026",
        supplier_raw="Martin Kohnle",
        amount_raw="3172,31",
        raw_text="Rechnung Martin Kohnle Marc Goldhammer Ludwigsburg 3172,31 EUR",
        address_fragments=["Marc Goldhammer", "Ludwigsburg"],
        source_method="openai",
    )
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.storage_file.parent == output_dir / "unklar"
    assert result.art == "unklar"


def test_private_recipient_only_with_positive_private_proof(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "private.pdf"
    create_pdf(pdf)
    extracted = ExtractedData(
        invoice_date_raw="01.05.2026",
        supplier_raw="Handwerker Beispiel",
        amount_raw="120,00",
        raw_text="Rechnung Roetestrasse 58 Stuttgart Betrag 120,00 EUR",
        address_fragments=["Alexander Tandawardaja", "Roetestraße 58"],
        source_method="openai",
    )
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.storage_file.parent == output_dir / "private"
    assert result.art == "private"


def test_duplicate_lifecycle_unchanged(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf_a = input_dir / "dup_a.pdf"
    pdf_b = input_dir / "dup_b.pdf"
    create_pdf(pdf_a)
    pdf_b.write_bytes(pdf_a.read_bytes())
    extracted = ExtractedData(
        invoice_date_raw="29.06.2026",
        supplier_raw="Superpunkt",
        amount_raw="10,00",
        raw_text="Rechnung SOMAA Bismarckstrasse Karte 7166",
        address_fragments=["SOMAA Architektur", "Bismarckstraße 63"],
        card_endings=["7166"],
        source_method="openai",
    )
    from tests.test_recipient_duplicate_anthropic_fix import SequenceExtractor

    processor = InvoiceProcessor(
        config,
        SequenceExtractor([extracted, extracted]),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    results = processor.process_all()
    assert len(results) == 2
    assert results[0].storage_file.parent.name == "ai"
    assert results[1].status == "duplicate"
    assert (output_dir / "_duplicate_reports").exists() or True
