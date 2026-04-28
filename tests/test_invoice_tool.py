from __future__ import annotations

import json
from pathlib import Path

import fitz

from invoice_tool.classification import classify_document_type
from invoice_tool.config import load_app_config, load_office_rules
from invoice_tool.extraction import _enrich_from_raw_text, _extract_json_payload
from invoice_tool.filename_schema import build_filename
from invoice_tool.models import ExtractedData
from invoice_tool.normalization import (
    normalize_invoice_date,
    parse_invoice_date_from_text,
    parse_amount_from_text,
    parse_supplier_from_text,
    clean_supplier_text,
)
from invoice_tool.models import SupplierCleaningRules
from invoice_tool.processing import InvoiceProcessor, _extract_rule_name, _extract_signals
from invoice_tool.trace import DecisionTrace, TraceWriter, mask_sensitive
from invoice_tool.routing import (
    apply_final_assignment,
    determine_business_context,
    detect_payment_method,
    resolve_account,
)
from invoice_tool.state import DirectoryLock, load_processed_state, save_processed_state


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


def test_order_confirmation_with_billing_address_and_vat_is_document() -> None:
    """Eine Bestellbestätigung mit Rechnungsadresse, MwSt. und PayPal darf keine invoice sein.

    Das Dokument hat 'Rechnungsadresse' (kein eigenständiges 'Rechnung'),
    'Bestellte Artikel' als Abschnitt und kein Rechnungsdatum/Rechnungsnummer.
    Es soll als document klassifiziert werden, nicht als invoice/unklar.
    """
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="260318",
        supplier_raw="Detail Magazin",
        amount_raw="299,00",
        raw_text=(
            "Bestellung # 000040795 Vollständig Erstellt:\n"
            "Bestellte Artikel Produktname Artikelnummer Preis Menge Zwischensumme\n"
            "Testabo Einzelnutzer PREMIUM DEO-EP-DEO-EJP 299,00 €\n"
            "Zwischensumme 299,00 € MwSt. 19,56 €\n"
            "Rechnungsadresse Alexander Tandawardaja SOMAA. Bismarckstrasse 63\n"
            "Zahlungsart PayPal Express Checkout"
        ),
        payment_method_raw="paypal",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "document", (
        f"Bestellbestätigung muss document sein, war: {classification.dokumenttyp!r} "
        f"({classification.begruendung})"
    )


def test_invoice_with_rechnung_standalone_stays_invoice() -> None:
    """Eine echte Rechnung mit 'Rechnung' als eigenständigem Wort bleibt invoice.

    Regression: 'Rechnung' als Standalone-Wort muss weiterhin als invoice_keyword greifen,
    auch wenn das Dokument 'Rechnungsadresse' enthält.
    """
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="260401",
        supplier_raw="Test GmbH",
        amount_raw="100,00",
        raw_text=(
            "Rechnung Nr. 1234\n"
            "Rechnungsadresse SOMAA Bismarckstrasse 63 Stuttgart\n"
            "MwSt. 19% 15,97 € Gesamt: 100,00 €"
        ),
        payment_method_raw="transfer",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "invoice", (
        f"Echte Rechnung mit 'Rechnung' als eigenständigem Wort muss invoice bleiben, "
        f"war: {classification.dokumenttyp!r}"
    )


def test_bestellbestaetigung_keyword_triggers_document() -> None:
    """'Bestellbestätigung' als Dokument-Keyword führt direkt zu document-Klassifikation."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="260320",
        supplier_raw="Some Shop",
        amount_raw="50,00",
        raw_text="Bestellbestätigung Produkt A 50,00 € Rechnungsadresse SOMAA MwSt. 7%",
        payment_method_raw="paypal",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "document", (
        f"'Bestellbestätigung' muss als Dokument-Indikator greifen, "
        f"war: {classification.dokumenttyp!r}"
    )


def test_invoice_with_rechnungsadresse_only_but_invoice_number_is_invoice() -> None:
    """Dokument mit nur 'Rechnungsadresse' (kein standalone Rechnung) aber mit invoice_number_raw → invoice."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="260401",
        supplier_raw="Shop GmbH",
        amount_raw="39,99",
        invoice_number_raw="INV-2026-001",  # explizite Rechnungsnummer
        raw_text="Rechnungsadresse SOMAA Bismarckstrasse MwSt. 19% 39,99 €",
        payment_method_raw="transfer",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "invoice", (
        f"Dokument mit invoice_number_raw muss invoice bleiben, "
        f"war: {classification.dokumenttyp!r}"
    )


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


def test_iban_ending_in_fitz_supplement_resolves_account() -> None:
    """IBAN-Endung aus Fitz-Text (Seite 2) ermöglicht Konto-Zuordnung.

    Simuliert den Adobe-Fall: OpenAI's raw_text_excerpt enthält die IBAN nicht,
    aber nach Ergänzung des Fitz-Textes (der die SEPA-Mandatsseite mit
    DE***...***1004 enthält) findet resolve_account die Endung 1004 = vobaai.
    """
    rules = load_office_rules(Path("office_rules.json"))
    # Vor Fitz-Ergänzung: raw_text ohne IBAN → kein Account
    extracted_without_fitz = ExtractedData(
        invoice_date_raw="05.04.2026",
        supplier_raw="Adobe Systems Software Ireland Ltd",
        amount_raw="39.99",
        raw_text="Rechnungsanschrift Alexander Tandawardaja 70197 GERMANY",
        source_method="openai",
    )
    account_before = resolve_account(extracted_without_fitz, rules.preset)
    assert account_before.konto is None, "Ohne IBAN kein Account erwartet"

    # Nach Fitz-Ergänzung: raw_text enthält SEPA-Mandatsseite mit IBAN
    fitz_supplement = (
        "Name des Zahlungspflichtigen: Alexander Tandawardaja\n"
        "E-Mail-Adresse: office@somaa.de\n"
        "IBAN: DE****************1004\n"
    )
    extracted_with_fitz = ExtractedData(
        invoice_date_raw="05.04.2026",
        supplier_raw="Adobe Systems Software Ireland Ltd",
        amount_raw="39.99",
        raw_text="Rechnungsanschrift Alexander Tandawardaja 70197 GERMANY\n" + fitz_supplement,
        source_method="openai",
    )
    account_after = resolve_account(extracted_with_fitz, rules.preset)
    assert account_after.konto == "vobaai", (
        f"IBAN-Endung 1004 muss vobaai liefern, war: {account_after.konto!r}"
    )
    assert "1004" in account_after.begruendung, (
        f"Begründung muss IBAN-Endung enthalten: {account_after.begruendung}"
    )


def test_somaa_email_in_fitz_supplement_enables_business_context() -> None:
    """'office@somaa.de' im ergänzten Fitz-Text liefert SOMAA-Business-Kontext.

    Wenn OpenAI 'SOMAA' nicht in context_markers schreibt (wegen neuer Prompt-
    Beschränkung), aber die Fitz-Ergänzung die E-Mail office@somaa.de enthält,
    muss somaa-unspecified greifen und art=ai liefern.
    """
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="05.04.2026",
        supplier_raw="Adobe Systems Software Ireland Ltd",
        amount_raw="39.99",
        raw_text=(
            "Rechnungsanschrift Alexander Tandawardaja 70197 GERMANY\n"
            "E-Mail-Adresse: office@somaa.de\n"
            "IBAN: DE****************1004\n"
        ),
        context_markers=[],  # OpenAI hat kein SOMAA in context_markers gesetzt
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, reason = determine_business_context(extracted, account, rules.preset)
    assert art == "ai", (
        f"'somaa' aus office@somaa.de muss Business-Kontext ai liefern, war: {art!r} ({reason})"
    )


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


def test_openai_payload_address_fragments_captures_recipient_company_name() -> None:
    """address_fragments muss den vollständigen Empfänger-Firmennamen enthalten.

    Simuliert eine OpenAI-Antwort, in der 'address_fragments' den Empfänger
    'SOMAA Event & Produktion' enthält (wie bei Haaga-Steuerberater-Rechnungen).
    Stellt sicher, dass der Firmenname verlustfrei in ExtractedData landet
    und für das Routing per document_text verfügbar ist.
    """
    payload = _extract_json_payload(
        """
        {
          "invoice_date": "01.04.2026",
          "supplier": "HAAGA & PARTNER mbB",
          "amount": "1.068,38",
          "invoice_number": "260084",
          "document_name": null,
          "payment_method": "transfer",
          "context_markers": [],
          "document_type_indicators": [],
          "card_endings": [],
          "apple_pay_endings": [],
          "provider_mentions": ["haaga", "somaa"],
          "address_fragments": [
            "SOMAA Event & Produktion",
            "Bismarckstr. 63",
            "70197 Stuttgart",
            "HAAGA & PARTNER mbB",
            "Eduard-Steinle-Str. 46",
            "70619 Stuttgart"
          ],
          "raw_text_excerpt": "Rechnungsbetrag 1.068,38 EUR Rechnungsnummer 260084"
        }
        """
    )
    assert "SOMAA Event & Produktion" in payload["address_fragments"], (
        "Empfänger-Firmenname muss in address_fragments erhalten bleiben"
    )
    # Prüfe dass die address_fragments in ExtractedData korrekt landen
    extracted = ExtractedData(
        invoice_date_raw=payload.get("invoice_date"),
        supplier_raw=payload.get("supplier"),
        amount_raw=payload.get("amount"),
        raw_text=payload.get("raw_text_excerpt") or "",
        address_fragments=[s.strip().lower() for s in payload.get("address_fragments", []) if s.strip()],
        source_method="openai",
    )
    assert any("event" in f for f in extracted.address_fragments), (
        "'event' muss in address_fragments.lower() vorhanden sein für EP-Routing"
    )
    assert any("produktion" in f for f in extracted.address_fragments), (
        "'produktion' muss in address_fragments vorhanden sein für EP-Routing"
    )


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
    # art=private + payment_field=unklar → private-keep-folder-despite-unclear-attributes
    # → folder=private, status=processed (not unklar), payment_field stays unklar
    assert routing.status == "processed"
    assert routing.zielordner == "private"


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
    # art=private + payment_field=unklar → private-keep-folder → private, status=processed
    assert reprocessed_results[0].status == "processed"
    assert reprocessed_results[0].dokumenttyp == "invoice"
    assert reprocessed_results[0].storage_file.parent == output_dir / "private"
    historical_reports = sorted((output_dir / "_duplicate_reports").glob("*historical_reprocess*.txt"))
    assert historical_reports
    report_text = historical_reports[-1].read_text(encoding="utf-8")
    assert "historical_match_detected: true" in report_text
    assert "action: current top-level input file was intentionally processed again" in report_text
    assert "previous_storage_path:" in report_text


def test_reprocessing_same_result_keeps_single_active_file(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "same.pdf"
    pdf_bytes = create_pdf(original_pdf, pages=1)
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Acme Ltd",
        amount_raw="10,00",
        invoice_number_raw="INV-1",
        raw_text="Invoice",
        source_method="openai",
    )
    first_processor = InvoiceProcessor(config, StubExtractor(extracted), office_rules=rules)
    first_results = first_processor.process_all()
    assert len(first_results) == 1
    first_active = first_results[0].storage_file
    assert first_active.exists()

    rerun_pdf = input_dir / "same.pdf"
    rerun_pdf.write_bytes(pdf_bytes)
    second_processor = InvoiceProcessor(config, StubExtractor(extracted), office_rules=rules)
    second_results = second_processor.process_all()
    assert len(second_results) == 1
    assert second_results[0].storage_file == first_active
    assert first_active.exists()
    assert len(list(first_active.parent.glob(f"{first_active.stem}*.pdf"))) == 1
    assert not list((output_dir / "_history").rglob(first_active.name))

    report_path = output_dir / "_runs" / second_processor.run_logger.run_id / "report.txt"
    report_text = report_path.read_text(encoding="utf-8")
    assert "Datei unverändert übernommen" in report_text


def test_updated_active_file_is_moved_to_history(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "same.pdf"
    pdf_bytes = create_pdf(original_pdf, pages=1)
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Acme Ltd",
        amount_raw="10,00",
        invoice_number_raw="INV-1",
        raw_text="Invoice",
        source_method="openai",
    )
    first_processor = InvoiceProcessor(config, StubExtractor(extracted), office_rules=rules)
    first_results = first_processor.process_all()
    first_active = first_results[0].storage_file
    legacy_active = first_active.with_name(f"{first_active.stem}_7{first_active.suffix}")
    first_active.rename(legacy_active)

    state_file = config.runtime_ordner / "state" / "processed_state.json"
    state = load_processed_state(state_file)
    fingerprint = first_results[0].fingerprint
    state[fingerprint]["storage_file"] = str(legacy_active)
    save_processed_state(state_file, state)

    rerun_pdf = input_dir / "same.pdf"
    rerun_pdf.write_bytes(pdf_bytes)
    second_processor = InvoiceProcessor(config, StubExtractor(extracted), office_rules=rules)
    second_results = second_processor.process_all()
    assert len(second_results) == 1
    updated_active = second_results[0].storage_file
    assert updated_active == first_active
    assert updated_active.exists()
    assert not legacy_active.exists()

    history_files = list((output_dir / "_history").rglob(legacy_active.name))
    assert history_files

    report_path = output_dir / "_runs" / second_processor.run_logger.run_id / "report.txt"
    report_text = report_path.read_text(encoding="utf-8")
    assert "Bestehende Datei aktualisiert" in report_text


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
    # art=private + payment_field=unklar → private-keep-folder → processed, not unklar
    assert [result.status for result in results].count("processed") == 1
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


def test_run_report_contains_summary_and_fallback_count(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _documents_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "report.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="SOMAA Architektur",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Invoice SOMAA Architektur lastschrift",
                source_method="tesseract",
                fallback_used=True,
            )
        ),
        office_rules=rules,
    )
    processor.process_all()
    report_path = output_dir / "_runs" / processor.run_logger.run_id / "report.txt"
    report_text = report_path.read_text(encoding="utf-8")
    assert f"Run ID: {processor.run_logger.run_id}" in report_text
    assert "Processed: 1" in report_text
    assert "System Fallbacks: 1" in report_text
    assert "Rechnung korrekt verarbeitet" in report_text
    assert "System-Fallback verwendet" in report_text


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
    rules_data["presets"]["alt"]["routing"]["zielordner"]["private"] = "private-alt"
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(rules_data), encoding="utf-8")
    loaded = load_office_rules(rules_path, active_preset_override="alt")
    assert loaded.active_preset == "alt"
    assert loaded.preset.routing.zielordner["private"] == "private-alt"


def test_directory_lock_removes_stale_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "sample.lock"
    lock_path.mkdir()
    (lock_path / "lock.json").write_text('{"created_at": 1, "pid": 1}', encoding="utf-8")
    with DirectoryLock(lock_path, stale_after_seconds=1):
        assert lock_path.exists()
    assert not lock_path.exists()


# ---------------------------------------------------------------------------
# Stage-1 regression tests
# ---------------------------------------------------------------------------

from invoice_tool.classification import _score_invoice_likeness
from invoice_tool.normalization import parse_invoice_date_from_text
from invoice_tool.routing import resolve_priority_routing, detect_street


def test_bestellung_with_accounting_indicators_classified_as_invoice() -> None:
    """A document titled 'Bestellung' with VAT, billing address, line items etc. must be invoice."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Some Shop GmbH",
        amount_raw="119,00",
        raw_text=(
            "Bestellung Rechnungsanschrift: Musterstr. 1, 70197 Stuttgart "
            "Bestellnummer: ORD-2026-42 MwSt. 19% 19,00 EUR Nettobetrag 100,00 EUR "
            "Bruttobetrag 119,00 EUR Zahlungsart: Kreditkarte"
        ),
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "invoice", classification.begruendung


def test_marketing_page_with_price_is_not_invoice() -> None:
    """A marketing page with a single price mention must stay as generic document."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw=None,
        supplier_raw=None,
        amount_raw="9,99",
        raw_text="Unser neues Produkt ab nur 9,99 EUR kaufen Sie jetzt!",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "document"


def test_address_only_document_is_not_invoice() -> None:
    """Billing address alone (without 'rechnung' substring) must not become an invoice."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw=None,
        supplier_raw="Somebody",
        amount_raw=None,
        # Use English "Billing Address" to avoid the German 'rechnung' keyword substring
        raw_text="Billing Address: Main Street 1, 70197 Stuttgart",
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    # score=1 (billing-address) < threshold 3 → document
    assert classification.dokumenttyp == "document"


def test_card_statement_with_account_holder_is_invoice_like() -> None:
    """A card statement with account holder, statement date, and transaction list is invoice-like."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.03.2026",
        supplier_raw="SOMAA Architektur",
        amount_raw="2450,00",
        raw_text=(
            "Kreditkartenabrechnung Karteninhaber: Max Muster "
            "Abrechnungszeitraum 01.02.2026-28.02.2026 "
            "SOMAA Architektur Bismarckstrasse 63 Stuttgart "
            "MwSt. 0,00 Gesamtbetrag 2450,00 EUR IBAN DE90600901000252831004"
        ),
        source_method="openai",
    )
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "invoice", classification.begruendung


def test_roete_private_address_routes_to_private_not_unklar(tmp_path: Path) -> None:
    """Tax-advisor invoice sent to Rötestraße (private address) must route to private, not unklar."""
    config_path, rules_path, input_dir, output_dir, _docs_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "steuerberater.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="Steuerberater GmbH",
                amount_raw="350,00",
                invoice_number_raw="INV-2026-10",
                raw_text=(
                    "Rechnung Steuerberater GmbH "
                    "Rechnungsempfaenger: Kunde Roetestrasse 12 70197 Stuttgart "
                    "MwSt. 19% Gesamtbetrag 350,00 EUR"
                ),
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.status == "processed", f"Expected processed, got {result.status}"
    assert result.storage_file.parent.name == "private", f"Expected private folder, got {result.storage_file}"


def test_somaa_with_roete_address_stays_ai_not_private(tmp_path: Path) -> None:
    """A SOMAA document that also mentions Rötestraße must stay AI (text_none_any guard)."""
    config_path, rules_path, input_dir, _output_dir, _docs_dir = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "somaa_roete.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="SOMAA Architektur",
                amount_raw="1200,00",
                invoice_number_raw="INV-2026-99",
                raw_text=(
                    "Rechnung SOMAA Architektur Roetestrasse 12 70197 Stuttgart "
                    "MwSt. 19% card payment Gesamtbetrag 1200,00 EUR"
                ),
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    # SOMAA text_none_any guard prevents roete-private from firing → business context wins
    # Check the parent folder name rather than full path (which starts with /private/ on macOS)
    assert result.storage_file.parent.name != "private", (
        f"SOMAA document wrongly routed to private folder: {result.storage_file}"
    )


def test_ep_produktion_alias_classified_as_ep() -> None:
    """SOMAA Event Produktion (German spelling) must classify as ep, not ai."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Eventservice GmbH",
        amount_raw="500,00",
        raw_text="Rechnung SOMAA Event Produktion Veranstaltung 2026",
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, _ = determine_business_context(extracted, account, rules.preset)
    assert art == "ep"


def test_ai_business_category_preserved_when_paid_via_non_amex_private_card() -> None:
    """AI business document paid with a non-Amex private card: art stays ai, payment → unklar."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Somaa Architektur GmbH",
        amount_raw="800,00",
        raw_text="SOMAA Architektur karte",
        card_endings=["3375"],  # Barclays Visa private card ending
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
    # Business category must stay ai; private card → payment unklar (not private)
    assert routing.art == "ai", f"Expected ai, got {routing.art}"
    assert routing.payment_field == "unklar", f"Expected unklar, got {routing.payment_field}"


def test_ep_business_category_preserved_when_paid_via_private_card() -> None:
    """EP business document paid with a configured private card must stay in ep."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Somaa Event Production",
        amount_raw="600,00",
        raw_text="SOMAA Event Production karte",
        card_endings=["3375"],  # barclays visa private card ending
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
    assert routing.art == "ep", f"Expected ep, got {routing.art}"
    assert routing.payment_field == "private"


def test_explicit_rechnungsdatum_has_priority_over_datum_fallback() -> None:
    """Explicit RECHNUNGSDATUM field must beat generic Datum: line."""
    text = (
        "Datum: 24. März 2026 um 16:17\n"
        "Rechnungsdatum 27.03.2026\n"
        "Verlängert sich am 24. April 2026"
    )
    result = parse_invoice_date_from_text(text)
    assert result == "260327", f"Expected 260327, got {result}"


def test_rechnung_heading_date_beats_datum_fallback() -> None:
    """A date directly after 'Rechnung' heading must beat generic Datum: line."""
    text = (
        "Datum: 24. März 2026 um 16:17\n"
        "Rechnung\n"
        "5. April 2026\n"
        "Verlängert sich am 24. April 2026"
    )
    result = parse_invoice_date_from_text(text)
    assert result == "260405", f"Expected 260405, got {result}"


def test_renewal_date_not_used_as_invoice_date() -> None:
    """'Verlängert sich am' date must be ignored; earlier Datum used only as fallback."""
    text = (
        "Datum: 5. April 2026\n"
        "Verlängert sich am 24. April 2026"
    )
    result = parse_invoice_date_from_text(text)
    # renewal date suppressed; fallback Datum date must be used
    assert result == "260405", f"Expected 260405, got {result}"
    assert result != "260424", "Renewal date must not be used as invoice date"


def test_german_ordinal_date_format_extracted_and_normalized() -> None:
    """'24. März 2026' (ordinal dot + space) must be extracted and normalized correctly."""
    text = "Rechnungsdatum 24. März 2026"
    result = parse_invoice_date_from_text(text)
    assert result == "260324", f"Expected 260324, got {result}"


def test_normalize_invoice_date_ordinal_dot() -> None:
    """normalize_invoice_date must handle '24. März 2026' with ordinal dot."""
    assert normalize_invoice_date("24. März 2026") == "260324"
    assert normalize_invoice_date("5. April 2026") == "260405"


def test_iban_ending_in_text_can_resolve_account() -> None:
    """A document containing a configured IBAN (vobaai) must resolve to vobaai account."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="Telekom Deutschland GmbH",
        amount_raw="49,99",
        invoice_number_raw="INV-99",
        raw_text=(
            "SOMAA Architektur Bismarckstrasse 63 "
            "IBAN DE90600901000252831004 BIC SSKMDEMMXXX"
        ),
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    # IBAN ending 1004 is configured for vobaai
    assert account.konto == "vobaai", f"Expected vobaai, got {account.konto}"


# ---------------------------------------------------------------------------
# Stage-1b regression tests – Amex routing and business-category consistency
# ---------------------------------------------------------------------------


def test_amex_monthly_statement_routes_to_amex_folder_not_private(tmp_path: Path) -> None:
    """Test A: Amex monthly statement with SOMAA+Bismarck context → amex folder, ai category."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "amex_statement.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="01.03.2026",
                supplier_raw="American Express",
                amount_raw="2450,00",
                raw_text=(
                    "American Express Business Platinum Card Monatsabrechnung "
                    "SOMAA ARCH & INNENAR BISMARCKSTRASSE 63 Stuttgart "
                    "Karten-Nr. xxxx-xxxxxx-01005 "
                    "Gesamtbetrag 2450,00 EUR"
                ),
                card_endings=["1005"],
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.storage_file.parent.name == "amex", (
        f"Expected amex folder, got {result.storage_file.parent.name}"
    )
    assert result.payment_field == "amex", f"Expected amex payment, got {result.payment_field}"
    assert result.art == "ai", f"Expected ai category, got {result.art}"
    assert result.status == "processed"
    # Filename must not say "private"
    assert "private" not in result.storage_file.name, (
        f"Filename must not contain 'private': {result.storage_file.name}"
    )


def test_apple_receipt_american_express_routes_to_amex(tmp_path: Path) -> None:
    """Test B: Apple receipt with 'American Express •••• 1005' + Bismarck → amex folder."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "apple_amex.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="05.04.2026",
                supplier_raw="Apple",
                amount_raw="0,99",
                raw_text=(
                    "Rechnung Bismarckstrasse 63 Stuttgart "
                    "American Express •••• 1005 "
                    "Betrag 0,99 EUR"
                ),
                card_endings=["1005"],
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.storage_file.parent.name == "amex", (
        f"Expected amex folder, got {result.storage_file.parent.name}"
    )
    assert result.payment_field == "amex"
    assert "private" not in result.storage_file.name


def test_abbuchung_von_amex_routes_to_amex(tmp_path: Path) -> None:
    """Test C: 'ABBUCHUNG VON Amex .... 1005' with Bismarck context → amex folder."""
    config_path, rules_path, input_dir, _output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "abbuchung_amex.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="10.04.2026",
                supplier_raw="Metzgerei Beispiel",
                amount_raw="45,80",
                raw_text=(
                    "Rechnung Bismarckstrasse 63 Stuttgart "
                    "ABBUCHUNG VON Amex .... 1005 "
                    "Betrag 45,80 EUR"
                ),
                card_endings=["1005"],
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.storage_file.parent.name == "amex"
    assert result.payment_field == "amex"
    assert "private" not in result.storage_file.name


def test_amex_card_ending_gives_amex_payment_field() -> None:
    """Test A/B (unit): Amex card ending 1005 resolves to amex payment_field, not private."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.03.2026",
        supplier_raw="American Express",
        amount_raw="2450,00",
        raw_text="American Express Business Platinum Card SOMAA Architektur Bismarckstrasse 63",
        card_endings=["1005"],
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
    assert routing.payment_field == "amex", f"Expected amex, got {routing.payment_field}"
    assert routing.art == "ai", f"Expected ai, got {routing.art}"
    assert routing.status == "processed"


def test_bismarck_without_somaa_gives_ai_category() -> None:
    """Test D/F (unit): Bismarck address alone (no SOMAA) → business category ai via street art."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="dm Drogerie",
        amount_raw="25,40",
        raw_text="Gutschrift Bismarckstrasse 63 Stuttgart Betrag 25,40 EUR",
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    street_key = detect_street(extracted, rules.preset)
    art, reason = determine_business_context(extracted, account, rules.preset, street_key)
    assert art == "ai", f"Expected ai from bismarck street, got {art}: {reason}"


def test_bismarck_without_somaa_filename_uses_ai_category(tmp_path: Path) -> None:
    """Test F: dm credit/Gutschrift with Bismarck, no payment → unklar folder but er_ai in filename."""
    config_path, rules_path, input_dir, _output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "dm_gutschrift.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="15.03.2026",
                supplier_raw="dm Drogerie",
                amount_raw="25,40",
                invoice_number_raw="GS-2026-42",
                raw_text=(
                    "Gutschrift Bismarckstrasse 63 Stuttgart "
                    "Gesamtbetrag 25,40 EUR"
                ),
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    # Filename category segment must be ai, not private
    assert "_er_ai_" in result.storage_file.name, (
        f"Filename must contain '_er_ai_', got: {result.storage_file.name}"
    )
    assert "_er_private_" not in result.storage_file.name


# ---------------------------------------------------------------------------
# Config-correction tests – verifying corrected card/Apple-Pay ending mappings
# ---------------------------------------------------------------------------


def _resolve(raw_text: str = "", card_endings: list | None = None, apple_pay_endings: list | None = None):
    """Helper: resolve account from ExtractedData using the real office_rules.json."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw=None,
        supplier_raw=None,
        amount_raw=None,
        raw_text=raw_text,
        card_endings=card_endings or [],
        apple_pay_endings=apple_pay_endings or [],
        source_method="openai",
    )
    return resolve_account(extracted, rules.preset)


def test_c24_physical_card_ending_8692_routes_private() -> None:
    acct = _resolve(card_endings=["8692"])
    assert acct.payment_field == "private"
    assert acct.art_override == "private"
    assert acct.matched_rule == "c24-private"


def test_c24_girocard_ending_0495_routes_private() -> None:
    acct = _resolve(card_endings=["0495"])
    assert acct.payment_field == "private"
    assert acct.matched_rule == "c24-private"


def test_c24_apple_pay_4924_routes_private() -> None:
    acct = _resolve(apple_pay_endings=["4924"])
    assert acct.payment_field == "private"
    assert acct.matched_rule == "c24-private"


def test_visa_physical_card_ending_3375_routes_private() -> None:
    acct = _resolve(card_endings=["3375"])
    assert acct.payment_field == "private"
    assert acct.matched_rule == "visa-private"


def test_visa_apple_pay_1081_routes_private() -> None:
    acct = _resolve(apple_pay_endings=["1081"])
    assert acct.payment_field == "private"
    assert acct.matched_rule == "visa-private"


def test_amex_physical_1005_routes_amex() -> None:
    acct = _resolve(card_endings=["1005"])
    assert acct.payment_field == "amex"
    assert acct.matched_rule == "amex"


def test_amex_physical_1013_routes_amex() -> None:
    acct = _resolve(card_endings=["1013"])
    assert acct.payment_field == "amex"
    assert acct.matched_rule == "amex"


def test_amex_physical_1000_routes_amex() -> None:
    """Amex ht private card ending 1000 must route to amex payment, not private."""
    acct = _resolve(card_endings=["1000"])
    assert acct.payment_field == "amex"
    assert acct.matched_rule == "amex"


def test_amex_apple_pay_4141_routes_amex() -> None:
    acct = _resolve(apple_pay_endings=["4141"])
    assert acct.payment_field == "amex"
    assert acct.matched_rule == "amex"


def test_amex_apple_pay_6276_routes_amex() -> None:
    acct = _resolve(apple_pay_endings=["6276"])
    assert acct.payment_field == "amex"
    assert acct.matched_rule == "amex"


def test_amex_apple_pay_4385_routes_amex() -> None:
    """Amex ht private Apple Pay ending 4385 must route to amex."""
    acct = _resolve(apple_pay_endings=["4385"])
    assert acct.payment_field == "amex"
    assert acct.matched_rule == "amex"


def test_vobaep_physical_4879_routes_vobaep() -> None:
    acct = _resolve(card_endings=["4879"])
    assert acct.payment_field == "vobaep"
    assert acct.art_override == "ep"
    assert acct.matched_rule == "vobaep"


def test_vobaep_apple_pay_4561_routes_vobaep() -> None:
    acct = _resolve(apple_pay_endings=["4561"])
    assert acct.payment_field == "vobaep"
    assert acct.art_override == "ep"
    assert acct.matched_rule == "vobaep"


def test_vobaai_physical_7166_routes_vobaai() -> None:
    """VobaAI Visa physical card ending 7166 must route to vobaai/ai."""
    acct = _resolve(card_endings=["7166"])
    assert acct.payment_field == "vobaai", f"Expected vobaai, got {acct.payment_field}"
    assert acct.art_override == "ai"
    assert acct.matched_rule == "vobaai"


def test_vobaai_apple_pay_6281_routes_vobaai() -> None:
    """VobaAI virtual debit Apple Pay ending 6281 must route to vobaai/ai."""
    acct = _resolve(apple_pay_endings=["6281"])
    assert acct.payment_field == "vobaai", f"Expected vobaai, got {acct.payment_field}"
    assert acct.art_override == "ai"
    assert acct.matched_rule == "vobaai"


def test_old_vobaai_ending_4861_no_longer_matches() -> None:
    """Obsolete vobaAI card ending 4861 must not match any configured account."""
    acct = _resolve(card_endings=["4861"])
    assert acct.payment_field is None, "4861 must not resolve to any configured account"


def test_volksbank_remseck_provider_hint_matches_vobaai() -> None:
    """Provider hint 'Volksbank Remseck' must resolve to vobaai (with ai zuweisungs-hinweis)."""
    acct = _resolve(raw_text="Volksbank Remseck eG artificial intelligence SOMAA Architektur")
    assert acct.payment_field == "vobaai"
    assert acct.matched_rule == "vobaai"


def test_vobaai_payment_field_explicit_rule_routes_to_ai_folder() -> None:
    """vobaai payment_field must always resolve to 'ai' folder via explicit output_route_rule."""
    rules = load_office_rules(Path("office_rules.json"))
    from invoice_tool.routing import resolve_output_route
    folder, status = resolve_output_route(art="ai", payment_field="vobaai", preset=rules.preset)
    assert folder == "ai", f"vobaai must route to 'ai' folder, got '{folder}'"
    assert status == "processed"


def test_vobaep_payment_field_explicit_rule_routes_to_ep_folder() -> None:
    """vobaep payment_field must always resolve to 'ep' folder via explicit output_route_rule."""
    rules = load_office_rules(Path("office_rules.json"))
    from invoice_tool.routing import resolve_output_route
    folder, status = resolve_output_route(art="ep", payment_field="vobaep", preset=rules.preset)
    assert folder == "ep", f"vobaep must route to 'ep' folder, got '{folder}'"
    assert status == "processed"


def test_vobaai_folder_name_never_empty() -> None:
    """resolve_output_route must never return an empty folder name for vobaai."""
    rules = load_office_rules(Path("office_rules.json"))
    from invoice_tool.routing import resolve_output_route
    folder, _ = resolve_output_route(art="ai", payment_field="vobaai", preset=rules.preset)
    assert folder, "Folder name must not be empty for vobaai"
    assert folder == "ai"


def test_vobaai_integration_folder_is_ai_not_empty(tmp_path: Path) -> None:
    """Integration: a transfer-ai document with vobaai payment must be stored in output/ai/."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "vodafone.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="05.03.2026",
                supplier_raw="Vodafone GmbH",
                amount_raw="55,61",
                invoice_number_raw="INV-2026-VF",
                raw_text="Rechnung SOMAA Architektur IBAN DE90600901000252831004 BIC lastschrift",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.payment_field == "vobaai", f"Expected vobaai payment, got {result.payment_field}"
    assert result.storage_file.parent.name == "ai", (
        f"Expected 'ai' folder, got '{result.storage_file.parent.name}'"
    )
    assert result.storage_file.parent.name != "", "Output folder name must not be empty"
    assert "_er_ai_" in result.storage_file.name, (
        f"Filename must contain '_er_ai_': {result.storage_file.name}"
    )
    assert result.storage_file.name.endswith("_vobaai.pdf"), (
        f"Filename must end with vobaai: {result.storage_file.name}"
    )


# ---------------------------------------------------------------------------
# Stage-1c: Cursor / Anysphere → amex payment route
# ---------------------------------------------------------------------------


def test_cursor_pro_invoice_routes_to_amex_not_vobaai(tmp_path: Path) -> None:
    """Cursor Pro invoice: art=ai (Bismarck), payment_field=amex, folder=amex, not vobaai."""
    config_path, rules_path, input_dir, _output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "cursor_pro.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="06.04.2026",
                supplier_raw="Cursor / Anysphere Inc",
                amount_raw="23.80",
                invoice_number_raw="INV-BE0KJYS5-0009",
                raw_text=(
                    "Cursor Pro Invoice "
                    "Anysphere Inc 2261 Market Street San Francisco CA "
                    "Bill to SOMAA Architektur Bismarckstraße 63 70197 Stuttgart "
                    "haditan@somaa.de hi@cursor.com "
                    "Cursor Pro subscription 23.80 USD"
                ),
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.payment_field == "amex", f"Expected amex, got {result.payment_field}"
    assert result.art == "ai", f"Expected ai category, got {result.art}"
    assert result.storage_file.parent.name == "amex", (
        f"Expected amex folder, got '{result.storage_file.parent.name}'"
    )
    assert result.storage_file.name.endswith("_amex.pdf"), (
        f"Filename must end with amex: {result.storage_file.name}"
    )
    assert "vobaai" not in result.storage_file.name, (
        f"vobaai must not appear in filename: {result.storage_file.name}"
    )


def test_cursor_usage_invoice_routes_to_amex_not_vobaai(tmp_path: Path) -> None:
    """Cursor Usage invoice: art=ai (Bismarck), payment_field=amex, folder=amex, not vobaai."""
    config_path, rules_path, input_dir, _output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "cursor_usage.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="07.04.2026",
                supplier_raw="Cursor / Anysphere Inc",
                amount_raw="70.22",
                invoice_number_raw="INV-BE0KJYS5-0010",
                raw_text=(
                    "Cursor Usage Invoice "
                    "Anysphere Inc 2261 Market Street San Francisco "
                    "Bill to SOMAA Architektur & Innenarchitektur Bismarckstraße 63 70197 Stuttgart "
                    "haditan@somaa.de hi@cursor.com "
                    "Cursor Usage 70.22 USD"
                ),
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.payment_field == "amex", f"Expected amex, got {result.payment_field}"
    assert result.art == "ai", f"Expected ai category, got {result.art}"
    assert result.storage_file.parent.name == "amex", (
        f"Expected amex folder, got '{result.storage_file.parent.name}'"
    )
    assert "vobaai" not in result.storage_file.name


def test_generic_ai_invoice_without_cursor_stays_vobaai(tmp_path: Path) -> None:
    """Negative guard: plain AI invoice with Bismarck but no Cursor/Anysphere must NOT become amex."""
    config_path, rules_path, input_dir, _output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "strato.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="01.03.2026",
                supplier_raw="Strato GmbH",
                amount_raw="36.00",
                invoice_number_raw="INV-2026-STRATO",
                raw_text=(
                    "Rechnung Strato AG "
                    "SOMAA Architektur Bismarckstraße 63 Stuttgart "
                    "Lastschrift IBAN DE90600901000252831004"
                ),
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    # Generic transfer AI invoice: must route to ai folder with vobaai, not amex
    assert result.payment_field == "vobaai", f"Expected vobaai for generic AI invoice, got {result.payment_field}"
    assert result.storage_file.parent.name == "ai", (
        f"Expected ai folder for generic invoice, got '{result.storage_file.parent.name}'"
    )
    assert "amex" not in result.storage_file.name


def test_vodafone_vobaai_iban_routes_to_ai_not_private(tmp_path: Path) -> None:
    """Test E: Vodafone+SOMAA+Bismarck with masked vobaAI IBAN ending → ai/vobaai route."""
    config_path, rules_path, input_dir, _output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    original_pdf = input_dir / "vodafone_voba.pdf"
    create_pdf(original_pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="01.03.2026",
                supplier_raw="Vodafone GmbH",
                amount_raw="49,99",
                invoice_number_raw="VOD-2026-1",
                raw_text=(
                    "Rechnung SOMAA Architektur Bismarckstrasse 63 Stuttgart "
                    "Lastschrift von IBAN DE90600901000252831004"
                ),
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    # Bismarck + SOMAA + vobaai IBAN → ai folder with vobaai payment
    assert result.storage_file.parent.name == "ai", (
        f"Expected ai folder, got {result.storage_file.parent.name}"
    )
    assert result.payment_field == "vobaai", f"Expected vobaai, got {result.payment_field}"
    assert "_er_private_" not in result.storage_file.name


# ---------------------------------------------------------------------------
# Decision-Trace tests
# ---------------------------------------------------------------------------


def test_decision_trace_created_for_processed_invoice(tmp_path: Path) -> None:
    """A decision_trace.jsonl is created in the _runs/<run_id>/ folder after a run."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "trace_invoice.pdf", pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="Acme Ltd",
                amount_raw="19,99",
                invoice_number_raw="INV-99",
                raw_text="Invoice SOMAA Architektur lastschrift IBAN DE90600901000252831004",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    processor.process_all()
    run_id = processor.run_logger.run_id
    trace_path = output_dir / "_runs" / run_id / "decision_trace.jsonl"
    assert trace_path.exists(), f"Expected decision_trace.jsonl at {trace_path}"
    lines = [l for l in trace_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1


def test_decision_trace_contains_required_fields(tmp_path: Path) -> None:
    """The decision trace must contain all required routing/classification fields."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "fields.pdf", pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="SOMAA Architektur",
                amount_raw="50,00",
                invoice_number_raw="INV-1",
                raw_text="Rechnung SOMAA Architektur lastschrift IBAN DE90600901000252831004",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    processor.process_all()
    run_id = processor.run_logger.run_id
    trace_path = output_dir / "_runs" / run_id / "decision_trace.jsonl"
    entry = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[0])
    for key in [
        "final_art",
        "final_payment_field",
        "final_output_folder",
        "document_type",
        "business_context_reason",
        "final_filename",
        "original_filename",
    ]:
        assert key in entry, f"Missing required trace field: {key}"


def test_decision_trace_contains_final_art(tmp_path: Path) -> None:
    """Trace must record final art/category."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "art.pdf", pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="SOMAA GmbH",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Rechnung SOMAA Architektur IBAN DE90600901000252831004",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    run_id = processor.run_logger.run_id
    trace_path = output_dir / "_runs" / run_id / "decision_trace.jsonl"
    entry = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["final_art"] == results[0].art


def test_decision_trace_contains_final_payment_field(tmp_path: Path) -> None:
    """Trace must record final payment_field, matching the processed result."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "pf.pdf", pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="SOMAA GmbH",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Rechnung SOMAA Architektur IBAN DE90600901000252831004",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    run_id = processor.run_logger.run_id
    trace_path = output_dir / "_runs" / run_id / "decision_trace.jsonl"
    entry = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["final_payment_field"] == results[0].payment_field


def test_decision_trace_contains_output_folder(tmp_path: Path) -> None:
    """Trace must record the final output folder name."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "folder.pdf", pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="SOMAA GmbH",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Rechnung SOMAA Architektur IBAN DE90600901000252831004",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    run_id = processor.run_logger.run_id
    trace_path = output_dir / "_runs" / run_id / "decision_trace.jsonl"
    entry = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["final_output_folder"] == results[0].storage_file.parent.name


def test_decision_trace_contains_rule_names(tmp_path: Path) -> None:
    """Trace must contain non-null payment_rule_name for deterministic payment detection."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "rules.pdf", pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="American Express",
                amount_raw="2450,00",
                invoice_number_raw="AMEX-2026-01",  # force invoice classification
                raw_text="Rechnung American Express SOMAA Architektur Bismarckstrasse 63",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    processor.process_all()
    run_id = processor.run_logger.run_id
    trace_path = output_dir / "_runs" / run_id / "decision_trace.jsonl"
    lines = [l for l in trace_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    invoice_entries = [json.loads(l) for l in lines if json.loads(l).get("document_type") == "invoice"]
    assert invoice_entries, "Expected at least one invoice trace entry"
    entry = invoice_entries[0]
    assert entry.get("payment_rule_name"), "payment_rule_name must be present for explicit amex detection"


def test_decision_trace_does_not_expose_full_iban(tmp_path: Path) -> None:
    """Full IBANs must not appear verbatim in the trace; only masked endings allowed."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "iban.pdf", pages=1)
    full_iban = "DE90600901000252831004"
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="Volksbank Remseck eG",
                amount_raw="49,99",
                invoice_number_raw="INV-1",
                raw_text=f"Rechnung SOMAA Architektur IBAN {full_iban} Lastschrift",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    processor.process_all()
    run_id = processor.run_logger.run_id
    trace_path = output_dir / "_runs" / run_id / "decision_trace.jsonl"
    raw = trace_path.read_text(encoding="utf-8")
    assert full_iban not in raw, f"Full IBAN {full_iban} must not appear in trace"


def test_decision_trace_does_not_expose_full_card_number(tmp_path: Path) -> None:
    """Full card numbers (16 digits) must not appear verbatim in the trace."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "card.pdf", pages=1)
    full_card = "4111222233331005"
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="American Express",
                amount_raw="120,00",
                raw_text=f"American Express Karte {full_card} SOMAA Architektur",
                card_endings=["1005"],
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    processor.process_all()
    run_id = processor.run_logger.run_id
    trace_path = output_dir / "_runs" / run_id / "decision_trace.jsonl"
    raw = trace_path.read_text(encoding="utf-8")
    assert full_card not in raw, f"Full card number {full_card} must not appear in trace"


def test_routing_summary_csv_created(tmp_path: Path) -> None:
    """routing_summary.csv must be created alongside the JSONL trace."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "csv.pdf", pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="20.03.2026",
                supplier_raw="Acme",
                amount_raw="10,00",
                invoice_number_raw="INV-1",
                raw_text="Invoice SOMAA",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    processor.process_all()
    run_id = processor.run_logger.run_id
    csv_path = output_dir / "_runs" / run_id / "routing_summary.csv"
    assert csv_path.exists(), "routing_summary.csv must be created"
    content = csv_path.read_text(encoding="utf-8")
    assert "payment_field" in content
    assert "art" in content


def test_mask_sensitive_replaces_iban() -> None:
    assert "DE90600901000252831004" not in (mask_sensitive("IBAN DE90600901000252831004") or "")
    assert "1004" in (mask_sensitive("IBAN DE90600901000252831004") or "")


def test_mask_sensitive_replaces_card_number() -> None:
    masked = mask_sensitive("Karte 4111222233331005 bezahlt")
    assert "4111222233331005" not in (masked or "")
    assert "1005" in (masked or "")


def test_mask_sensitive_leaves_short_numbers_intact() -> None:
    assert mask_sensitive("Betrag 199,00 EUR") == "Betrag 199,00 EUR"


def test_extract_rule_name_parses_begruendung() -> None:
    assert _extract_rule_name("Payment-Regel 'explicit-amex' getroffen.") == "explicit-amex"
    assert _extract_rule_name("Keine Regel getroffen.") is None


def test_extract_signals_parses_begruendung() -> None:
    assert _extract_signals("Payment-Regel 'x' getroffen. Signale: iban, bic.") == "iban, bic"
    assert _extract_signals("Signale: keine.") == "keine"


# ---------------------------------------------------------------------------
# Policy: private-keep-folder-despite-unclear-attributes
# ---------------------------------------------------------------------------


def test_private_with_unklar_payment_routes_to_private_folder(tmp_path: Path) -> None:
    """Core policy: art=private + payment_field=unklar → folder private, not unklar.

    This covers the Haaga-Mandant-19112 real-world case: no SOMAA, no Bismarck,
    transfer payment detected but no configured account → ultimate-fallback would
    previously send to unklar despite art=private.
    """
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "private_unklar.pdf"
    create_pdf(pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="01.04.2026",
                supplier_raw="Steuerberater GmbH",
                amount_raw="595,30",
                invoice_number_raw="INV-PRIVATE-1",
                raw_text="Rechnung Steuerberater GmbH Überweisung bitte",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.art == "private", f"Expected art=private, got {result.art}"
    assert result.storage_file.parent.name == "private", (
        f"Expected folder 'private', got '{result.storage_file.parent.name}'"
    )


def test_private_with_unklar_payment_field_stays_unklar(tmp_path: Path) -> None:
    """payment_field must remain unklar even though the folder becomes private."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "private_pf.pdf"
    create_pdf(pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="01.04.2026",
                supplier_raw="Steuerberater GmbH",
                amount_raw="595,30",
                invoice_number_raw="INV-PRIVATE-2",
                raw_text="Rechnung Steuerberater GmbH Überweisung bitte",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    # payment_field stays unklar — only the folder is corrected to private
    assert result.payment_field == "unklar", (
        f"payment_field must remain unklar, got {result.payment_field}"
    )
    assert result.storage_file.parent.name == "private", (
        f"Despite unklar payment, folder must be private for private art, got {result.storage_file.parent.name}"
    )


def test_private_with_transfer_payment_routes_to_private(tmp_path: Path) -> None:
    """art=private + transfer payment (no account match) → folder private."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "private_transfer.pdf"
    create_pdf(pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="15.03.2026",
                supplier_raw="Freelancer XY",
                amount_raw="200,00",
                invoice_number_raw="INV-PRIV-3",
                raw_text="Rechnung Überweisung",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.storage_file.parent.name == "private"


def test_private_keep_folder_rule_name_visible_in_trace(tmp_path: Path) -> None:
    """The output_route_rule must reference the policy name for UI traceability."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "private_trace.pdf"
    create_pdf(pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="01.04.2026",
                supplier_raw="Anwalt GmbH",
                amount_raw="300,00",
                invoice_number_raw="INV-PRIV-TRACE",
                raw_text="Rechnung Anwalt GmbH Überweisung",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    processor.process_all()
    run_id = processor.run_logger.run_id
    trace_path = output_dir / "_runs" / run_id / "decision_trace.jsonl"
    lines = [l for l in trace_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    invoice_entries = [json.loads(l) for l in lines if json.loads(l).get("document_type") == "invoice"]
    assert invoice_entries
    entry = invoice_entries[0]
    assert entry.get("output_route_rule_name") == "private-keep-folder-despite-unclear-attributes", (
        f"Expected policy rule name in trace, got: {entry.get('output_route_rule_name')}"
    )


def test_control_ai_with_unklar_payment_stays_unklar_folder(tmp_path: Path) -> None:
    """Control test: art=ai + payment_field=unklar must still go to unklar folder (dm case)."""
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "ai_unklar.pdf"
    create_pdf(pdf, pages=1)
    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="09.02.2026",
                supplier_raw="dm Drogerie",
                amount_raw="24,75",
                invoice_number_raw="GS-3456908",
                raw_text="Gutschrift Bismarckstrasse 63 Stuttgart",
                source_method="openai",
            )
        ),
        office_rules=rules,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.art == "ai", f"Expected art=ai, got {result.art}"
    assert result.storage_file.parent.name == "unklar", (
        f"ai+unklar must remain in unklar folder, got '{result.storage_file.parent.name}'"
    )


def test_control_ep_with_unklar_payment_stays_unklar_folder() -> None:
    """Control test: art=ep + payment_method=unknown → somaa-unclear-payment → folder unklar.

    Verifies that the private-keep-folder exception does NOT apply to ep:
    ep + unklar payment → unklar folder, not ep folder.
    Uses neutral text (no SOMAA, no payment keywords) so account and payment
    detection return empty results; art=ep is passed explicitly to apply_final_assignment.
    """
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="10.04.2026",
        supplier_raw="Event GmbH",
        amount_raw="500,00",
        raw_text="Event GmbH Rechnung",
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art="ep",
        payment_decision=payment,
        account_decision=account,
        street_key=None,
        preset=rules.preset,
    )
    assert payment.payment_method == "unknown", (
        f"Expected no payment detected, got {payment.payment_method}"
    )
    assert routing.art == "ep", f"Expected art=ep, got {routing.art}"
    assert routing.payment_field == "unklar", (
        f"Expected payment_field=unklar, got {routing.payment_field}"
    )
    assert routing.zielordner == "unklar", (
        f"ep+unklar must go to unklar folder, got {routing.zielordner!r}"
    )


# ---------------------------------------------------------------------------
# Street detection: Rötestr. abbreviation matching
# ---------------------------------------------------------------------------


def test_roetest_abbreviation_detected_as_roete_street() -> None:
    """'Rötestr.' (abbreviated, with dot) must be detected as street key 'roete'."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.04.2026",
        supplier_raw="Steuerberater GmbH",
        amount_raw="595,30",
        invoice_number_raw="INV-260085",
        raw_text=(
            "Herrn\n"
            "Alexander Tandawardaja\n"
            "Rötestr. 58\n"
            "70197 Stuttgart"
        ),
        source_method="openai",
    )
    street = detect_street(extracted, rules.preset)
    assert street == "roete", f"Expected street=roete for 'Rötestr. 58', got: {street!r}"


def test_roetest_abbreviation_gives_private_art() -> None:
    """Rötestr. abbreviation → art=private via street art mapping."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.04.2026",
        supplier_raw="Steuerberater GmbH",
        amount_raw="595,30",
        invoice_number_raw="INV-260085",
        raw_text=(
            "Herrn\n"
            "Alexander Tandawardaja\n"
            "Rötestr. 58\n"
            "70197 Stuttgart"
        ),
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    street = detect_street(extracted, rules.preset)
    art, reason = determine_business_context(extracted, account, rules.preset, street)
    assert art == "private", f"Expected art=private from Rötestr. street, got {art}: {reason}"


def test_roetest_with_sender_address_still_detects_recipient_roete() -> None:
    """Recipient Rötestr. 58 wins even when sender address Eduard-Steinle-Str. also present."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.04.2026",
        supplier_raw="Haaga & Partner mbB Steuerberatungsgesellschaft",
        amount_raw="595,30",
        invoice_number_raw="INV-260085",
        raw_text=(
            "HAAGA & PARTNER mbB, Eduard-Steinle-Str. 46, 70619 Stuttgart\n"
            "Herrn\n"
            "Alexander Tandawardaja\n"
            "Rötestr. 58\n"
            "70197 Stuttgart\n"
            "Rechnung über 595,30 EUR"
        ),
        source_method="openai",
    )
    street = detect_street(extracted, rules.preset)
    assert street == "roete", (
        f"Recipient Rötestr. must be detected despite sender address Eduard-Steinle-Str., got: {street!r}"
    )


def test_roetestr_dot_variant_does_not_match_bismarck() -> None:
    """Rötestr. abbreviation variants must NOT match Bismarckstraße text."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="20.03.2026",
        supplier_raw="SOMAA Architektur",
        amount_raw="100,00",
        invoice_number_raw="INV-1",
        raw_text="SOMAA Architektur Bismarckstrasse 63 70197 Stuttgart Rechnung",
        source_method="openai",
    )
    street = detect_street(extracted, rules.preset)
    assert street == "bismarck", f"Bismarck text must give bismarck, got: {street!r}"


# ---------------------------------------------------------------------------
# Bug-fix tests: Tesseract-Extraktion (6 Bugs)
# ---------------------------------------------------------------------------


# Bug 1 + 2: Betragsextraktion -----------------------------------------------

def test_amount_totalling_not_confused_with_total() -> None:
    """'totalling:' in a line-item description must not match as a Total label."""
    text = (
        "64 token-based usage calls to gpt-5.4-medium, totalling: $236.41. Input 1  $236.41  19%  $236.41\n"
        "Subtotal\n"
        "Total excluding tax\n"
        "Total\n"
        "Amount due\n"
        "$100.68\n"
        "$100.68\n"
        "$119.81\n"
        "$119.81 USD\n"
    )
    assert parse_amount_from_text(text) == "119.81"


def test_amount_label_and_value_on_separate_lines() -> None:
    """When Total / Amount due appear on their own lines, the value on the next
    line must be paired via look-ahead."""
    text = (
        "Subtotal\n"
        "Total\n"
        "Amount due\n"
        "$50.00\n"
        "$59.50\n"
        "$59.50 USD\n"
    )
    assert parse_amount_from_text(text) == "59.50"


def test_amount_priority_amount_due_beats_subtotal() -> None:
    """'Amount due' (tier 0) must win over 'Subtotal' (tier 2) on same line."""
    text = (
        "Subtotal $40.86\n"
        "Total excluding tax $40.86\n"
        "Total $48.62\n"
        "Amount due $48.62 USD\n"
    )
    assert parse_amount_from_text(text) == "48.62"


def test_amount_gesamtsumme_brutto_beats_netto() -> None:
    """Plain 'Gesamtsumme' (tier 1) must beat 'Gesamtsumme (Netto)' (tier 2)."""
    text = (
        "Gesamtsumme (Netto): 199,15 €\n"
        "Gesamtsumme: 213,10 €\n"
    )
    assert parse_amount_from_text(text) == "213.10"


# Bug 3: "Marz" (OCR Umlaut-Verlust) ----------------------------------------

def test_date_marz_ocr_umlaut_loss_recognized() -> None:
    """Tesseract drops the umlaut: 'Marz' must still be recognised as März."""
    assert normalize_invoice_date("5. Marz 2026") == "260305"
    assert normalize_invoice_date("23. Marz 2026") == "260323"


def test_date_parse_marz_from_tesseract_text() -> None:
    """parse_invoice_date_from_text must find '5. Marz 2026' after 'Rechnung' heading."""
    text = (
        "Von:\n"
        "Rechnung\n"
        "\n"
        "5. Marz 2026\n"
    )
    assert parse_invoice_date_from_text(text) == "260305"


# Bug 4: Datum in ausgedruckten E-Mails --------------------------------------

def test_date_email_timestamp_with_uhrzeit_ignored() -> None:
    """A line containing 'um HH:MM' is a send-timestamp and must be skipped."""
    text = (
        "Datum:\n"
        "6. Marz 2026 um 06:12\n"
        "Rechnung\n"
        "\n"
        "5. Marz 2026\n"
    )
    result = parse_invoice_date_from_text(text)
    assert result == "260305", f"Should pick invoice date 260305, not email timestamp, got {result!r}"


def test_date_heading_proximity_bridges_blank_line() -> None:
    """A blank line between 'Rechnung' and the date must not break heading-match."""
    text = (
        "Rechnung\n"
        "\n"
        "23. Marz 2026\n"
    )
    assert parse_invoice_date_from_text(text) == "260323"


def test_date_email_at_timestamp_ignored() -> None:
    """English 'at HH:MM' timestamp must also be suppressed."""
    text = (
        "Invoice\n"
        "\n"
        "March 6, 2026 at 06:12\n"
        "Invoice\n"
        "\n"
        "March 5, 2026\n"
    )
    result = parse_invoice_date_from_text(text)
    assert result == "260305", f"Expected 260305, got {result!r}"


# Bug 5: Lieferant – E-Mail-Header-Labels ------------------------------------

def test_supplier_von_colon_is_skipped() -> None:
    """'Von:' (email header label) must not be returned as supplier."""
    text = (
        "Von:\n"
        "Betreff:\n"
        "Datum:\n"
        "\n"
        "An:\n"
        "\n"
        "iCloud\n"
    )
    result = parse_supplier_from_text(text)
    assert result == "icloud", f"Expected 'icloud', got {result!r}"


def test_supplier_email_address_line_is_skipped() -> None:
    """A line containing '@' (email address) must be skipped."""
    text = (
        "Von:\n"
        "apple@email.apple.com\n"
        "Figma Inc\n"
    )
    result = parse_supplier_from_text(text)
    assert result == "figma-inc", f"Expected 'figma-inc', got {result!r}"


def test_supplier_rechnungsadresse_label_is_skipped() -> None:
    """'Deine Rechnungsadresse' must not be returned as supplier name."""
    text = (
        "Deine Rechnungsadresse\n"
        "dm-drogerie-markt GmbH\n"
    )
    result = parse_supplier_from_text(text)
    assert result is not None and "rechnungsadresse" not in result


# Bug 6: Supplier-Alias-Map --------------------------------------------------

def test_supplier_alias_ecasypark_corrected() -> None:
    """OCR reads 'ECasyPark' → slug 'ecasypark' → alias map returns 'easypark'."""
    rules = SupplierCleaningRules(
        remove_suffix_patterns=(),
        supplier_aliases={"ecasypark": "easypark"},
    )
    assert clean_supplier_text("ECasyPark", rules) == "easypark"


def test_supplier_alias_dm_corrected() -> None:
    """'deine-rechnungsadresse' slug → alias map returns 'dm-drogerie-markt'."""
    rules = SupplierCleaningRules(
        remove_suffix_patterns=(),
        supplier_aliases={"deine-rechnungsadresse": "dm-drogerie-markt"},
    )
    assert clean_supplier_text("Deine Rechnungsadresse", rules) == "dm-drogerie-markt"


def test_supplier_alias_no_match_unchanged() -> None:
    """A supplier not in the alias map passes through unchanged."""
    rules = SupplierCleaningRules(
        remove_suffix_patterns=(),
        supplier_aliases={"ecasypark": "easypark"},
    )
    assert clean_supplier_text("Figma Inc", rules) == "Figma Inc"


def test_supplier_aliases_loaded_from_office_rules() -> None:
    """office_rules.json must contain at least the two known aliases."""
    rules = load_office_rules(Path("office_rules.json"))
    aliases = rules.preset.supplier_cleaning.supplier_aliases
    assert aliases.get("ecasypark") == "easypark"
    assert aliases.get("deine-rechnungsadresse") == "dm-drogerie-markt"


# ---------------------------------------------------------------------------
# BusinessContextRule.match_source – Quellen-gesteuertes Matching
# ---------------------------------------------------------------------------


def test_business_context_rule_raw_text_source_ignores_ai_context_markers() -> None:
    """KI-Zusatzfelder dürfen EP nicht allein auslösen.

    Die somaa-event-production-Regel nutzt match_source=raw_text. Wenn 'event'
    und 'production' nur in context_markers (OpenAI-Halluzination) stehen, aber
    nicht im tatsächlichen PDF-Rohtext, darf die EP-Regel nicht greifen.

    Entspricht dem Vodafone-260205-Fall: SOMAA + Bismarck-Adresse im Rohtext,
    aber kein 'event'/'produktion' im PDF selbst.
    """
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="05.02.2026",
        supplier_raw="Vodafone West GmbH",
        amount_raw="53,43",
        raw_text="SOMAA Alexander Tandawardaja Bismarckstrasse 63 70197 Stuttgart",
        context_markers=["event", "production"],  # simulierte KI-Halluzination
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, reason = determine_business_context(
        extracted, account, rules.preset, street_key="bismarck"
    )
    assert art == "ai", (
        f"Halluzinierter EP-Kontext in context_markers darf nicht EP auslösen, "
        f"war: {art!r} ({reason})"
    )


def test_business_context_rule_raw_text_source_matches_real_event_produktion_text() -> None:
    """Echter EP-Kontext in Dokumentfeldern wird korrekt als EP klassifiziert.

    Entspricht dem Haaga-260084-Fall: 'SOMAA Event & Produktion' steht in den
    address_fragments (OpenAI extrahiert Empfängeradresse dahin). raw_text-Modus
    schließt address_fragments ein, aber nicht context_markers/provider_mentions.
    """
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.04.2026",
        supplier_raw="HAAGA & PARTNER mbB",
        amount_raw="1068,38",
        raw_text="Rechnungsbetrag 1.068,38 EUR Rechnungsnummer 260084",  # nur Excerpt
        address_fragments=["SOMAA Event & Produktion", "Bismarckstr. 63", "70197 Stuttgart"],
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, reason = determine_business_context(extracted, account, rules.preset)
    assert art == "ep", (
        f"'SOMAA Event & Produktion' in address_fragments muss EP bleiben, war: {art!r} ({reason})"
    )


def test_business_context_rule_default_match_source_uses_enriched_text() -> None:
    """Regeln ohne match_source (Default enriched_text) matchen weiter wie bisher.

    Die somaa-architektur-innenarchitektur-Regel hat match_source=enriched_text.
    Sie soll auch dann greifen, wenn 'architektur' nur in context_markers steht.
    """
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.02.2026",
        supplier_raw="Test GmbH",
        amount_raw="100,00",
        raw_text="SOMAA Bismarckstrasse 63 Stuttgart",  # kein 'architektur' im Rohtext
        context_markers=["architektur", "innenarchitektur"],  # nur in KI-Feldern
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, reason = determine_business_context(extracted, account, rules.preset)
    assert art == "ai", (
        f"Default enriched_text muss context_markers einbeziehen → ai erwartet, "
        f"war: {art!r} ({reason})"
    )
