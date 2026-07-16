"""Amazon SOMAA/Architektur → ai + amex + target amex; false positives stay out."""
from __future__ import annotations

from pathlib import Path

from invoice_tool.config import load_app_config, load_office_rules
from invoice_tool.models import ExtractedData
from invoice_tool.processing import InvoiceProcessor
from invoice_tool.supplier_routing import resolve_supplier_profile_routing
from tests.test_invoice_tool import StubExtractor, create_pdf, make_test_setup
from tests.test_recipient_duplicate_anthropic_fix import _sample_profile


def _amazon_profile() -> dict:
    profile = _sample_profile()
    profile["vendor_profiles"] = list(profile.get("vendor_profiles") or []) + [
        {
            "id": "amazon-ai-amex",
            "label": "Amazon SOMAA Architektur AMEX",
            "recognition_hints": [
                "amazon eu s.à r.l",
                "amazon eu s.a.r.l",
                "amazon eu",
                "amazon marketplace",
                "amazon services",
            ],
            "issuer_hints": [
                "amazon eu s.à r.l",
                "amazon eu s.a.r.l",
                "amazon eu s a r l",
                "www.amazon.de/contact-us",
                "amazon.de/contact-us",
                "www.amazon.de",
            ],
            "required_recipient_hints": [
                "somaa",
                "bismarckstrasse",
                "bismarckstraße",
            ],
            "payment_field": "amex",
            "category": "ai",
            "target_folder": "amex",
            "match_scope": "supplier",
            "exclusive": True,
            "enabled": True,
        }
    ]
    return profile


def test_amazon_somaa_recipient_routes_ai_amex_not_vobaai(tmp_path: Path) -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="27.05.2026",
        supplier_raw="Amazon EU S.à r.l., Niederlassung Deutschland",
        amount_raw="40,55",
        raw_text=(
            "Rechnung Amazon EU S.à r.l. Rechnungsadresse "
            "Alexander Tandawardaja Somaa, Bismarckstrasse 63 Stuttgart"
        ),
        address_fragments=["Alexander Tandawardaja", "Somaa, Bismarckstrasse 63", "Stuttgart"],
        source_method="openai",
    )
    match = resolve_supplier_profile_routing(extracted, rules.preset, _amazon_profile())
    assert match is not None
    assert match.rule_id == "amazon-ai-amex"
    assert match.routing.art == "ai"
    assert match.routing.payment_field == "amex"
    assert match.routing.zielordner == "amex"
    assert "1005" not in (match.payment_reference or "")
    assert match.routing.payment_field != "vobaai"

    config_path, rules_path, input_dir, output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "amazon1.pdf"
    create_pdf(pdf)
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_amazon_profile(),
        original_source_dir=input_dir,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.storage_file.parent.name == "amex"
    assert result.art == "ai"
    assert result.payment_field == "amex"
    assert "vobaai" not in result.storage_file.name
    assert len(list(output_dir.rglob("*.pdf"))) == 1


def test_amazon_missing_recipient_does_not_match_amex_rule() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="27.05.2026",
        supplier_raw="Amazon EU S.à r.l.",
        amount_raw="12,00",
        raw_text="Rechnung Amazon EU S.à r.l. ohne Empfaengerblock",
        address_fragments=[],
        source_method="openai",
    )
    assert resolve_supplier_profile_routing(extracted, rules.preset, _amazon_profile()) is None


def test_amazon_foreign_recipient_does_not_match_amex_rule() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="27.05.2026",
        supplier_raw="Amazon EU S.à r.l.",
        amount_raw="12,00",
        raw_text="Rechnung Amazon EU Rechnungsadresse Marc Goldhammer Ludwigsburg",
        address_fragments=["Marc Goldhammer", "Ernst-Kauffmann-Strasse 69", "Ludwigsburg"],
        source_method="openai",
    )
    assert resolve_supplier_profile_routing(extracted, rules.preset, _amazon_profile()) is None


def test_amazon_private_recipient_without_somaa_does_not_match_amex_rule() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="27.05.2026",
        supplier_raw="Amazon EU S.à r.l.",
        amount_raw="12,00",
        raw_text="Rechnung Amazon EU Rechnungsadresse Alexander Tandawardaja Roetestrasse 58",
        address_fragments=["Alexander Tandawardaja", "Roetestrasse 58"],
        source_method="openai",
    )
    assert resolve_supplier_profile_routing(extracted, rules.preset, _amazon_profile()) is None


def test_amazon_text_mention_without_amazon_supplier_or_issuer_does_not_match() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="01.06.2026",
        supplier_raw="MediaMarkt Saturn",
        amount_raw="99,00",
        raw_text="MediaMarkt Rechnung SOMAA Bismarckstrasse kompatibel mit Amazon Basics Adapter",
        address_fragments=["SOMAA", "Bismarckstrasse 63"],
        source_method="openai",
    )
    assert resolve_supplier_profile_routing(extracted, rules.preset, _amazon_profile()) is None


def test_amazon_marketplace_issuer_with_seller_supplier_matches() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="26.05.2026",
        supplier_raw="SP United Vertriebs GmbH",
        amount_raw="25,48",
        raw_text=(
            "Rechnung Amazon EU S.à r.l. Verkauft von SP United Vertriebs GmbH "
            "Rechnungsadresse Alexander Tandawardaja Somaa, Bismarckstrasse 63"
        ),
        address_fragments=["Alexander Tandawardaja", "Somaa, Bismarckstrasse 63"],
        source_method="openai",
    )
    match = resolve_supplier_profile_routing(extracted, rules.preset, _amazon_profile())
    assert match is not None
    assert match.rule_id == "amazon-ai-amex"
    assert match.routing.payment_field == "amex"
    assert match.routing.zielordner == "amex"


def test_amazon_marketplace_contact_us_issuer_without_eu_header_matches() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="26.05.2026",
        supplier_raw="SP United Vertriebs GmbH",
        amount_raw="25,48",
        raw_text=(
            "Verkauft von SP United Vertriebs GmbH "
            "Rechnungsadresse Alexander Tandawardaja Somaa, Bismarckstrasse 63 "
            "www.amazon.de/contact-us"
        ),
        address_fragments=["Alexander Tandawardaja", "Somaa, Bismarckstrasse 63"],
        source_method="openai",
    )
    match = resolve_supplier_profile_routing(extracted, rules.preset, _amazon_profile())
    assert match is not None
    assert match.rule_id == "amazon-ai-amex"
    assert match.routing.zielordner == "amex"


def test_anthropic_rule_unchanged_with_amazon_profile_present() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="23.06.2026",
        supplier_raw="Anthropic PBC",
        amount_raw="90,00",
        raw_text="Invoice Anthropic PBC",
        address_fragments=["SOMAA"],
        source_method="openai",
    )
    match = resolve_supplier_profile_routing(extracted, rules.preset, _amazon_profile())
    assert match is not None
    assert match.rule_id == "anthropic-ep-amex-1005"
    assert match.routing.art == "ep"
    assert match.routing.payment_field == "amex-1005"
    assert match.routing.zielordner == "amex"


def test_existing_amex_vendor_cursor_not_broken_by_amazon_helpers() -> None:
    """Bare product mention of Amazon must not trigger the Amazon issuer rule."""
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="10.06.2026",
        supplier_raw="MediaMarkt Saturn",
        amount_raw="10,00",
        raw_text="Random invoice mentioning amazon basics as product SOMAA Bismarckstrasse",
        address_fragments=["SOMAA Bismarckstrasse"],
        source_method="openai",
    )
    assert resolve_supplier_profile_routing(extracted, rules.preset, _amazon_profile()) is None
