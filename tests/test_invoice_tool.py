from __future__ import annotations

import json
from pathlib import Path

import fitz

from invoice_tool.classification import classify_document_type
from invoice_tool.config import load_app_config, load_office_rules
from invoice_tool.extraction import _enrich_from_raw_text, _extract_json_payload
from invoice_tool.filename_schema import build_filename
from invoice_tool.models import ExtractedData
from invoice_tool.normalization import normalize_invoice_date
from invoice_tool.processing import InvoiceProcessor
from invoice_tool.routing import (
    apply_final_assignment,
    determine_business_context,
    detect_payment_method,
    resolve_account,
)
from invoice_tool.state import DirectoryLock, load_processed_state


class StubExtractor:
    def __init__(self, extracted: ExtractedData) -> None:
        self.extracted = extracted

    def extract(self, pdf_path: Path, *, log):
        return self.extracted


class FailingExtractor:
    def extract(self, pdf_path: Path, *, log):
        raise RuntimeError("simulierter Extraktionsfehler")


def create_pdf(path: Path, pages: int = 3) -> bytes:
    document = fitz.open()
    for page_number in range(pages):
        page = document.new_page()
        page.insert_text((72, 72), f"Test PDF Seite {page_number + 1}")
    document.save(path)
    document.close()
    return path.read_bytes()


def make_test_setup(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    documents_dir = tmp_path / "documents"
    runtime_dir = tmp_path / "runtime"
    logs_dir = tmp_path / "logs"
    input_dir.mkdir()

    rules_data = json.loads(Path("office_rules.json").read_text(encoding="utf-8"))
    rules_data["presets"]["office_default"]["dokumente"]["basis_pfad"] = str(documents_dir)
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(rules_data), encoding="utf-8")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "eingangsordner": str(input_dir),
                "ausgangsordner": str(output_dir),
                "api_key_pfad": "$HOME/Library/Application Support/KI-Rechnungen-Umbenennen/.env",
                "archiv_aktiv": True,
                "regeln_datei": str(rules_path),
                "aktives_preset": "office_default",
                "runtime_ordner": str(runtime_dir),
                "log_ordner": str(logs_dir),
            }
        ),
        encoding="utf-8",
    )
    return config_path, rules_path, input_dir, output_dir, documents_dir


def test_config_loading_from_json() -> None:
    config = load_app_config(Path("invoice_config.json"))
    assert config.eingangsordner.name == "input"
    assert config.ausgangsordner.name == "output"
    assert config.archiv_aktiv is True
    assert config.aktives_preset == "office_default"


def test_filename_generation_uses_payment_field() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    filename = build_filename(
        rules.preset.filename_schema,
        {
            "invoice_date": "260320",
            "art": "ai",
            "supplier": "sehr-langer-rechnungsstellername-mit-zusatz",
            "amount": "1234.56",
            "payment_field": "vobaai",
        },
    )
    assert filename.endswith(".pdf")
    assert len(filename) <= 50
    assert filename.startswith("260320_er_ai_")
    assert "_1234.56_vobaai.pdf" in filename


def test_document_indicator_overrides_invoice_like_fields() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Hilfsverein e.V.",
        amount_raw="123,45",
        raw_text="Donation confirmation 2026",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "document"


def test_transfer_proof_is_document() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Sparkasse",
        amount_raw="123,45",
        raw_text="SEPA transfer proof",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "document"


def test_internal_form_is_invoice() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw=None,
        supplier_raw=None,
        amount_raw=None,
        raw_text="Eigenbeleg Taxi Fahrt",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "invoice"


def test_supplier_date_amount_alone_do_not_force_invoice() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="2026-03-20",
        supplier_raw="Some Supplier",
        amount_raw="44.00",
        raw_text="Statement 2026",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "document"


def test_english_invoice_classified_as_invoice() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="2026-03-20",
        supplier_raw="Acme Ltd",
        amount_raw="199.00",
        invoice_number_raw="INV-2026-77",
        raw_text="Invoice number INV-2026-77",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "invoice"


def test_openai_raw_text_enrichment_fills_missing_amount_and_date() -> None:
    extracted = ExtractedData(
        invoice_date_raw=None,
        supplier_raw="Adobe Systems Software Ireland Ltd",
        amount_raw=None,
        invoice_number_raw=None,
        raw_text=(
            "Rechnung Positionen Laufzeit: 05-FEB-2026 bis 04-MAR-2026 "
            "Rechnungsinformationen IEE2026002338961 Rechnungsnummer 05-FEB-2026 Rechnungsdatum "
            "Gesamtbetrag (EUR) 39.99"
        ),
        source_method="openai",
    )
    enriched = _enrich_from_raw_text(extracted)
    assert enriched.invoice_date_raw == "260205"
    assert enriched.amount_raw == "39.99"


def test_extract_json_payload_recovers_expected_object_from_multi_object_response() -> None:
    payload = _extract_json_payload(
        """
        {
          "betrag": "168997,12 €"
        },
        {
          "invoice_date": "03.09.1977",
          "supplier": "VVaD",
          "amount": "168997,12 €",
          "invoice_number": "INV-250307",
          "document_name": null,
          "payment_method": "transfer",
          "context_markers": [],
          "document_type_indicators": [],
          "card_endings": [],
          "apple_pay_endings": [],
          "provider_mentions": [],
          "address_fragments": [],
          "raw_text_excerpt": "..."
        }
        """
    )
    assert payload["invoice_date"] == "03.09.1977"
    assert payload["amount"] == "168997,12 €"
    assert "betrag" not in payload


def test_abbrev_month_date_normalizes_to_yymmdd() -> None:
    assert normalize_invoice_date("05-FEB-2026") == "260205"


def test_german_month_name_date_normalizes_to_yymmdd() -> None:
    assert normalize_invoice_date("17 Dezember 2022") == "221217"


def test_short_numeric_date_normalizes_to_yymmdd() -> None:
    assert normalize_invoice_date("17.12.22") == "221217"


def test_openai_raw_text_excerpt_date_is_used_when_primary_date_missing() -> None:
    extracted = ExtractedData(
        invoice_date_raw=None,
        supplier_raw="Acme Ltd",
        amount_raw="19,99",
        invoice_number_raw="INV-100",
        raw_text="Invoice number INV-100 invoice date 2026-02-05",
        source_method="openai",
    )
    enriched = _enrich_from_raw_text(extracted)
    assert enriched.invoice_date_raw == "260205"


def test_openai_raw_text_excerpt_date_replaces_invalid_primary_date() -> None:
    extracted = ExtractedData(
        invoice_date_raw="not-a-date",
        supplier_raw="Acme Ltd",
        amount_raw="19,99",
        invoice_number_raw="INV-101",
        raw_text="Invoice number INV-101 Rechnungsdatum 05-FEB-2026",
        source_method="openai",
    )
    enriched = _enrich_from_raw_text(extracted)
    assert enriched.invoice_date_raw == "260205"


def test_ocr_text_date_is_used_when_only_ocr_text_contains_date() -> None:
    extracted = ExtractedData(
        invoice_date_raw=None,
        supplier_raw="Acme Ltd",
        amount_raw="19,99",
        invoice_number_raw="INV-102",
        raw_text="OCR TEXT Rechnungsdatum 17 Dezember 2022",
        source_method="tesseract",
    )
    enriched = _enrich_from_raw_text(extracted)
    assert enriched.invoice_date_raw == "221217"


def test_business_context_ep_overrides_ai() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Somaa Event & Production",
        amount_raw="100,00",
        raw_text="SOMAA Event Production invoice",
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, _reason = determine_business_context(extracted, account, rules.preset)
    assert art == "ep"


def test_payment_detection_paypal_results_in_paypal_unklar() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Some Service",
        amount_raw="9,99",
        raw_text="Invoice paid with PayPal",
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, _ = determine_business_context(extracted, account, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key=None,
        preset=rules.preset,
    )
    assert routing.payment_field == "paypal-unklar"
    assert routing.status == "unklar"


def test_card_payment_maps_to_vobaai_for_ai_case() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Somaa Architektur",
        amount_raw="120,00",
        raw_text="SOMAA Architektur card payment",
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, _ = determine_business_context(extracted, account, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key=None,
        preset=rules.preset,
    )
    assert routing.payment_field == "vobaai"
    assert routing.konto == "vobaai"
    assert routing.status == "processed"


def test_transfer_maps_to_ep_account() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Somaa Event Production",
        amount_raw="120,00",
        raw_text="SOMAA event production bank transfer",
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, _ = determine_business_context(extracted, account, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key=None,
        preset=rules.preset,
    )
    assert routing.payment_field == "vobaep"
    assert routing.konto == "vobaep"


def test_direct_debit_prenotification_maps_to_vobaai_for_somaa_ai() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Telekom Deutschland GmbH",
        amount_raw="49,99",
        invoice_number_raw="INV-2026-88",
        raw_text=(
            "Rechnung SOMAA Architektur Bismarckstrasse 63 "
            "Der Rechnungsbetrag wird entsprechend der Prenotification von Ihrem Konto abgebucht. "
            "SEPA Lastschrift IBAN DE02120300000000202051 BIC BYLADEM1001"
        ),
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, _ = determine_business_context(extracted, account, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key="bismarck",
        preset=rules.preset,
    )
    assert payment.payment_method == "transfer"
    assert routing.art == "ai"
    assert routing.konto == "vobaai"
    assert routing.payment_field == "vobaai"


def test_somaa_iban_bic_without_other_payment_text_maps_to_vobaai() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Telekom Deutschland GmbH",
        amount_raw="49,99",
        invoice_number_raw="INV-2026-89",
        raw_text=(
            "Rechnung SOMAA Architektur Bismarckstrasse 63 "
            "IBAN DE02120300000000202051 BIC BYLADEM1001"
        ),
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, _ = determine_business_context(extracted, account, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key="bismarck",
        preset=rules.preset,
    )
    assert payment.payment_method == "transfer"
    assert routing.art == "ai"
    assert routing.konto == "vobaai"
    assert routing.payment_field == "vobaai"


def test_payment_detection_avoids_short_substring_false_positives() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="05-FEB-2026",
        supplier_raw="Adobe Systems Software Ireland Ltd",
        amount_raw="39.99",
        invoice_number_raw="IEE2026002338961",
        raw_text=(
            "Rechnung Positionen Laufzeit: 05-FEB-2026 bis 04-MAR-2026 "
            "Rechnungsinformationen IEE2026002338961 Rechnungsnummer 05-FEB-2026 Rechnungsdatum "
            "SEPA-Lastschrift Zahlungsfrist 7237508818 Bestellnummer 163856312 "
            "Adobe Systems Software Ireland Ltd Gesamtbetrag (EUR) 39.99"
        ),
        source_method="openai",
    )
    payment = detect_payment_method(extracted, rules.preset)
    assert payment.payment_method == "transfer"


def test_somaa_invoice_without_payment_info_defaults_to_vobaai() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="17/03/2026",
        supplier_raw="Microsoft Ireland Operations Ltd",
        amount_raw="11,70",
        invoice_number_raw="E0700Z9AOV",
        raw_text=(
            "Rechnung Maerz 2026 Rechnungsdatum: 17/03/2026 Rechnungsnummer: E0700Z9AOV "
            "11,70 EUR Auftraggeber Rechnungsempfaenger Dienstnutzungsadresse SOMAA Bismarckstrasse 63 "
            "Summe: 11,70 Zahlungsanweisungen: BITTE NICHT BEZAHLEN. "
            "Der faellige Betrag wird ueber die ausgewaehlte Zahlungsmethode abgerechnet."
        ),
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, _ = determine_business_context(extracted, account, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key="bismarck",
        preset=rules.preset,
    )
    assert payment.payment_method == "transfer"
    assert routing.konto == "vobaai"
    assert routing.payment_field == "vobaai"
    assert routing.status == "processed"


def test_no_somaa_and_no_payment_signals_stays_unklar() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Generic Supplier GmbH",
        amount_raw="19,99",
        invoice_number_raw="INV-2026-90",
        raw_text="Invoice INV-2026-90 amount due 19,99 EUR",
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, _ = determine_business_context(extracted, account, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key=None,
        preset=rules.preset,
    )
    assert payment.payment_method == "unknown"
    assert routing.payment_field == "unklar"
    assert routing.status == "unklar"


def test_ec_card_signal_maps_to_vobaep_for_ep_case() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Somaa Event Production",
        amount_raw="120,00",
        raw_text="SOMAA Event Production bezahlt per EC-Karte",
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, _ = determine_business_context(extracted, account, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key=None,
        preset=rules.preset,
    )
    assert payment.payment_method == "card"
    assert routing.konto == "vobaep"
    assert routing.payment_field == "vobaep"


def test_supplier_cleaning_removes_clear_address_suffix(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "supplier.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="17 Dezember 2022",
                supplier_raw="METZGEREI Elisabethenstr. 30",
                amount_raw="19,28 €",
                invoice_number_raw="INV-1",
                raw_text="Invoice",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    assert "metzgerei" in results[0].storage_file.name
    assert "elisabethenstr" not in results[0].storage_file.name
    assert results[0].date == "221217"
    assert results[0].amount == "19.28"


def test_short_numeric_date_normalizes_to_20yy(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "short-date.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="17.12.22",
                supplier_raw="Acme Ltd",
                amount_raw="19,28 €",
                invoice_number_raw="INV-1",
                raw_text="Invoice",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    assert results[0].date == "221217"


def test_abbrev_month_date_normalizes(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "month-date.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="31-JAN-2023",
                supplier_raw="Adobe Ireland",
                amount_raw="39.99",
                invoice_number_raw="INV-2",
                raw_text="Invoice",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    assert results[0].date == "230131"


def test_document_is_stored_separately_with_vn_suffix(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "letter.pdf"
    create_pdf(original_pdf, pages=2)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw=None,
                supplier_raw=None,
                amount_raw=None,
                document_name_raw="Insurance Letter",
                raw_text="Insurance letter regarding policy update",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.dokumenttyp == "document"
    assert result.storage_file.parent == documents_dir
    assert result.storage_file.name.endswith("_d_insurance-letter_vn.pdf")
    assert not list(output_dir.glob("*.pdf"))


def test_invoice_without_clean_payment_defaults_somaa_invoice_to_vobaai(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "borderline.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw=None,
                supplier_raw=None,
                amount_raw=None,
                invoice_number_raw="INV-LOOKALIKE",
                raw_text="Invoice reference INV-LOOKALIKE SOMAA",
                source_method="tesseract",
                fallback_used=True,
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.dokumenttyp == "invoice"
    assert result.storage_file.parent == output_dir / "ai"
    assert result.konto == "vobaai"
    assert result.payment_field == "vobaai"
    assert result.status == "processed"
    assert "unknown-date" in result.storage_file.name
    assert not list(documents_dir.glob("*.pdf"))


def test_reprocessing_same_filename_with_new_content_is_processed(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    first_pdf = input_dir / "same.pdf"
    create_pdf(first_pdf, pages=1)
    processor_one = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="Acme Ltd",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Invoice",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    assert len(processor_one.process_all()) == 1

    second_pdf = input_dir / "same.pdf"
    create_pdf(second_pdf, pages=2)
    processor_two = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="21.03.2026",
                supplier_raw="Acme Ltd",
                amount_raw="11,00",
                invoice_number_raw="INV-2",
                raw_text="Invoice",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor_two.process_all()
    assert len(results) == 1
    assert results[0].dokumenttyp == "invoice"


def test_same_content_different_filename_is_reprocessed_with_historical_report(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "first.pdf"
    pdf_bytes = create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="Acme Ltd",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Invoice",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    assert len(processor.process_all()) == 1

    duplicate_pdf = input_dir / "second.pdf"
    duplicate_pdf.write_bytes(pdf_bytes)
    second_processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="21.03.2026",
                supplier_raw="Acme Ltd",
                amount_raw="11,00",
                invoice_number_raw="INV-2",
                raw_text="Invoice",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    reprocessed_results = second_processor.process_all()
    assert len(reprocessed_results) == 1
    assert reprocessed_results[0].status == "unklar"
    assert reprocessed_results[0].dokumenttyp == "invoice"
    assert reprocessed_results[0].storage_file.parent == output_dir / "unklar"
    historical_reports = sorted((output_dir / "_duplicate_reports").glob("*historical_reprocess*.txt"))
    assert historical_reports
    report_text = historical_reports[-1].read_text(encoding="utf-8")
    assert "historical_match_detected: true" in report_text
    assert "action: current top-level input file was intentionally processed again" in report_text
    assert "previous_storage_path:" in report_text


def test_same_run_duplicate_still_creates_duplicate_report(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    first_pdf = input_dir / "first.pdf"
    pdf_bytes = create_pdf(first_pdf, pages=1)
    second_pdf = input_dir / "second.pdf"
    second_pdf.write_bytes(pdf_bytes)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="Acme Ltd",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Invoice",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 2
    assert [result.status for result in results].count("unklar") == 1
    assert [result.status for result in results].count("duplicate") == 1
    duplicate_result = [result for result in results if result.status == "duplicate"][0]
    report_text = duplicate_result.storage_file.read_text(encoding="utf-8")
    assert "duplicate_reference_type: same-run" in report_text


def test_failed_file_remains_in_input_and_is_not_archived(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "broken.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(config, FailingExtractor(), office_rules=rules)
    results = processor.process_all()
    assert results == []
    assert original_pdf.exists()
    archive_root = input_dir / "archiv"
    assert not archive_root.exists() or not list(archive_root.rglob("broken.pdf"))


def test_logs_contain_decision_focused_fields(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "log.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="Acme Ltd",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Invoice paid with paypal",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    processor.process_all()
    log_files = sorted(config.log_ordner.glob("run_*.log"))
    assert log_files
    log_text = log_files[-1].read_text(encoding="utf-8")
    assert '"preset_used": "office_default"' in log_text
    assert '"payment_field": "paypal-unklar"' in log_text
    assert "Payment-Regel 'explicit-paypal' getroffen. Signale: paypal." in log_text
    assert '"archive_path":' in log_text


def test_top_level_only_input_scan_ignores_archive_contents(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _documents_dir = make_test_setup(tmp_path)
    archive_file = input_dir / "archiv" / "old.pdf"
    archive_file.parent.mkdir(parents=True)
    create_pdf(archive_file, pages=1)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="Acme Ltd",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Invoice",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    assert processor.process_all() == []


def test_state_records_processed_content_by_fingerprint(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "scan.pdf"
    create_pdf(original_pdf, pages=2)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="Acme Ltd",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Invoice",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    assert len(processor.process_all()) == 1
    state = load_processed_state(config.runtime_ordner / "state" / "processed_state.json")
    assert len(state) == 1


def test_office_rules_support_active_preset_override(tmp_path: Path) -> None:
    rules_data = json.loads(Path("office_rules.json").read_text(encoding="utf-8"))
    rules_data["presets"]["alt"] = json.loads(json.dumps(rules_data["presets"]["office_default"]))
    rules_data["presets"]["alt"]["routing"]["zielordner"]["privat"] = "private-alt"
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(rules_data), encoding="utf-8")
    loaded = load_office_rules(rules_path, active_preset_override="alt")
    assert loaded.active_preset == "alt"
    assert loaded.preset.routing.zielordner["privat"] == "private-alt"


def test_directory_lock_removes_stale_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "sample.lock"
    lock_path.mkdir()
    (lock_path / "lock.json").write_text('{"created_at": 1, "pid": 1}', encoding="utf-8")
    with DirectoryLock(lock_path, stale_after_seconds=1):
        assert lock_path.exists()
    assert not lock_path.exists()
