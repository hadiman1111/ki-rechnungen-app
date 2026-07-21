"""Böttcher business invoice + generic credit card → invoice/ai/unklar (generalized)."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from invoice_tool.classification import classify_document_type
from invoice_tool.config import load_app_config, load_office_rules
from invoice_tool.models import ExtractedData
from invoice_tool.processing import InvoiceProcessor
from invoice_tool.saas_product_model import (
    classification_policy_ui_texts,
    default_classification_policy,
)
from invoice_tool.ui_v2.saas_profile_surface import (
    build_saas_profile_surface_vm,
    surface_payload_as_dict,
)
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


def _boettcher_observed_invoice() -> ExtractedData:
    return ExtractedData(
        invoice_date_raw="23.05.2026",
        supplier_raw="Böttcher AG",
        amount_raw="84,39",
        invoice_number_raw="320262919974",
        raw_text=(
            "RECHNUNG Böttcher AG "
            "Rechnung Nr.: 320262919974 "
            "Datum: 23.05.2026 "
            "Rechnungs-/Lieferscheindatum: 23.05.2026 "
            "Empfänger/Rechnungsanschrift: "
            "SOMAA EG Eckbüro Bismarckstr. 63 70176 Stuttgart DEUTSCHLAND "
            "Positionen: Prospekthüllen Leitz Fahrradschloss Abus Bordo "
            "Gesamtwert: 84,39 EUR MwSt 19% "
            "Zahlung per Kreditkarte "
            "ZUGFeRD available on request "
            "XRechnung available on request"
        ),
        address_fragments=[
            "SOMAA",
            "EG Eckbüro",
            "Bismarckstr. 63",
            "70176 Stuttgart",
        ],
        payment_method_raw="Zahlung per Kreditkarte",
        document_name_raw="Rechnung",
        source_method="openai",
    )


def _neutral_business_invoice() -> ExtractedData:
    """Generalized fixture: neutral company/address/payment — no private tenant names."""

    return ExtractedData(
        invoice_date_raw="11.04.2026",
        supplier_raw="Nordwerk Supplies AG",
        amount_raw="112,50",
        invoice_number_raw="NW-2026-8891",
        raw_text=(
            "RECHNUNG Nordwerk Supplies AG "
            "Rechnung Nr.: NW-2026-8891 "
            "Datum: 11.04.2026 "
            "Rechnungs-/Lieferscheindatum: 11.04.2026 "
            "Empfänger/Rechnungsanschrift: "
            "ACME GmbH Büro Mitte Hauptstrasse 12 10115 Berlin "
            "Positionen: Ordner A4 Fahrradschloss Modell X "
            "Gesamtwert: 112,50 EUR MwSt 19% "
            "Zahlung per Kreditkarte "
            "ZUGFeRD available on request"
        ),
        address_fragments=[
            "ACME GmbH",
            "Hauptstrasse 12",
            "10115 Berlin",
        ],
        payment_method_raw="Zahlung per Kreditkarte",
        document_name_raw="Rechnung",
        source_method="openai",
    )


def _neutral_profile() -> dict:
    return {
        "recipient_policy": {
            "business_recipient_hints": ["acme gmbh", "hauptstrasse"],
            "private_recipient_hints": [],
            "foreign_recipient_block_hints": [],
        },
        "vendor_profiles": [],
    }


def _preset_with_lieferschein_document_keyword(preset):
    return replace(
        preset,
        classification=replace(
            preset.classification,
            document_keywords=tuple(
                list(preset.classification.document_keywords)
                + ["lieferschein", "delivery note"]
            ),
        ),
    )


def test_boettcher_rechnung_title_is_not_document() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = _boettcher_observed_invoice()
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "invoice"


def test_boettcher_invoice_number_date_items_vat_make_invoice() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = _boettcher_observed_invoice()
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "invoice"
    assert extracted.invoice_number_raw == "320262919974"
    assert "mwst" in extracted.raw_text.lower() or "MwSt" in extracted.raw_text
    assert "84,39" in (extracted.amount_raw or "")


def test_zugferd_xrechnung_note_does_not_make_document() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = _boettcher_observed_invoice()
    classification = classify_document_type(extracted, rules.preset)
    assert classification.dokumenttyp == "invoice"
    assert "zugferd" in extracted.raw_text.lower()
    assert "xrechnung" in extracted.raw_text.lower()


def test_rechnungs_lieferscheindatum_does_not_make_document() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    preset = _preset_with_lieferschein_document_keyword(rules.preset)
    extracted = _boettcher_observed_invoice()
    classification = classify_document_type(extracted, preset)
    assert classification.dokumenttyp == "invoice"
    assert "lieferscheindatum" in extracted.raw_text.lower()


def test_boettcher_somaa_billing_gives_art_ai(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "260523_d_boettcher_amex.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_boettcher_observed_invoice()),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.dokumenttyp == "invoice"
    assert result.art == "ai"
    assert result.payment_field == "unklar"
    assert result.storage_file.parent == output_dir / "unklar"


def test_fahrradschloss_item_does_not_override_business_billing(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "boettcher_items.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_boettcher_observed_invoice()),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert "fahrradschloss" in (_boettcher_observed_invoice().raw_text or "").lower()
    assert result.art == "ai"
    assert result.art != "private"


def test_generic_kreditkarte_payment_field_unklar(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "boettcher_card.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_boettcher_observed_invoice()),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.payment_field == "unklar"
    assert "amex" not in (result.payment_field or "").lower()


def test_generic_kreditkarte_target_folder_unklar(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "boettcher_target.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_boettcher_observed_invoice()),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.storage_file.parent == output_dir / "unklar"


def test_input_filename_amex_does_not_set_amex(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "260523_d_boettcher_amex.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_boettcher_observed_invoice()),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    lowered = result.storage_file.name.lower()
    assert "amex" not in lowered
    assert result.payment_field == "unklar"
    assert "_er_" in lowered
    assert "_d_" not in lowered or "_er_" in lowered


def test_expected_filename_approximately_er_ai_boettcher_unklar(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "260523_d_boettcher_amex.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_boettcher_observed_invoice()),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    name = result.storage_file.name.lower()
    assert name.startswith("260523_er_ai_")
    assert "boettcher" in name
    assert "84.39" in name or "84,39" in name
    assert name.endswith("_unklar.pdf")


def test_neutral_generalized_business_invoice_unknown_card(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    # Local street rule uses configured org hints from profile + business context.
    # Extend office rules business context via profile recipient + raw ACME markers
    # by injecting a temporary business-context-compatible text marker used in tests:
    # determine_business_context relies on preset rules; for neutral fixture we map
    # ACME via a synthetic business_context rule only inside this test preset.
    from invoice_tool.models import BusinessContextRule, OfficeRules

    preset = replace(
        rules.preset,
        routing=replace(
            rules.preset.routing,
            business_context_rules=tuple(rules.preset.routing.business_context_rules)
            + (
                BusinessContextRule(
                    name="neutral-acme-business",
                    text_any=("acme gmbh",),
                    text_all=(),
                    art="ai",
                    match_source="raw_text",
                ),
            ),
        ),
    )
    office_rules = OfficeRules(
        active_preset=rules.active_preset,
        presets={**rules.presets, rules.active_preset: preset},
    )
    create_pdf(input_dir / "neutral_card_invoice.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_neutral_business_invoice()),
        office_rules=office_rules,
        profile_data=_neutral_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.dokumenttyp == "invoice"
    assert result.art == "ai"
    assert result.payment_field == "unklar"
    assert result.storage_file.parent == output_dir / "unklar"
    name = result.storage_file.name.lower()
    assert "_er_" in name
    assert "amex" not in name
    for marker in ("somaa", "hadi", "bismarck", "amex-1005"):
        assert marker not in name


def test_generalized_behavior_needs_no_private_saas_defaults() -> None:
    policy = default_classification_policy()
    idp = policy.invoice_detection_policy
    pep = policy.payment_evidence_policy
    bap = policy.business_assignment_policy
    assert idp.invoice_indicators_override_format_notes is True
    assert idp.format_availability_notes_are_not_document_type is True
    assert idp.filename_is_not_source_of_truth is True
    assert pep.generic_credit_card_without_identifier_target == "unklar"
    assert pep.card_payment_requires_known_reference is True
    assert pep.supplier_bank_details_are_not_payer_evidence is True
    assert bap.business_billing_address_assigns_business_context is True
    assert bap.ambiguous_items_do_not_override_business_billing_address is True
    assert bap.organization_identifiers_are_profile_configured is True
    blob = str(policy.to_dict()) + " ".join(classification_policy_ui_texts())
    vm = build_saas_profile_surface_vm()
    payload = surface_payload_as_dict(vm)
    blob += str(payload)
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
