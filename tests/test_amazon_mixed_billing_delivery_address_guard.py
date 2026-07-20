"""Amazon mixed billing/delivery address → unklar; clear business billing stays ai/amex."""
from __future__ import annotations

from pathlib import Path

from invoice_tool.config import load_app_config, load_office_rules
from invoice_tool.models import ExtractedData
from invoice_tool.processing import InvoiceProcessor
from invoice_tool.routing_guards import evaluate_mixed_address_ambiguity
from invoice_tool.saas_product_model import (
    classification_policy_ui_texts,
    default_classification_policy,
)
from invoice_tool.supplier_routing import resolve_supplier_profile_routing
from invoice_tool.ui_v2.saas_profile_surface import (
    build_saas_profile_surface_vm,
    surface_payload_as_dict,
)
from tests.test_amazon_supplier_rule import _amazon_profile
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
    "97368",
    "DE189",
)


def _mixed_amazon_extracted() -> ExtractedData:
    return ExtractedData(
        invoice_date_raw="26.05.2026",
        supplier_raw="Amazon EU S.à r.l., Niederlassung Deutschland",
        amount_raw="36,99",
        raw_text=(
            "Amazon EU S.à r.l., Niederlassung Deutschland "
            "Rechnungsadresse Alexander Tandawardaja Rötestrasse 58 "
            "Stuttgart, 70197 DE "
            "Lieferadresse Alexander Tandawardaja Somaa, Bismarckstrasse 63 "
            "Stuttgart, 70197 DE "
            "TRAX Pro Abschleppsystem Fahrrad/Fahrrad/E-Bike 36,99 EUR "
            "Zahlungsreferenznummer 123456789"
        ),
        address_fragments=[
            "Alexander Tandawardaja",
            "Rötestrasse 58",
            "Somaa, Bismarckstrasse 63",
            "Stuttgart, 70197",
        ],
        source_method="openai",
    )


def _business_billing_amazon_extracted() -> ExtractedData:
    return ExtractedData(
        invoice_date_raw="27.05.2026",
        supplier_raw="Amazon EU S.à r.l., Niederlassung Deutschland",
        amount_raw="40,55",
        raw_text=(
            "Rechnung Amazon EU S.à r.l. Rechnungsadresse "
            "Alexander Tandawardaja Somaa, Bismarckstrasse 63 Stuttgart"
        ),
        address_fragments=[
            "Alexander Tandawardaja",
            "Somaa, Bismarckstrasse 63",
            "Stuttgart",
        ],
        source_method="openai",
    )


def test_amazon_private_billing_business_delivery_is_ambiguous() -> None:
    mixed = evaluate_mixed_address_ambiguity(_mixed_amazon_extracted(), street_key="roete")
    assert mixed.is_ambiguous is True
    assert mixed.private_billing_business_delivery is True
    assert mixed.business_signal_only_in_delivery is True


def test_amazon_supplier_rule_does_not_match_delivery_only_business() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    match = resolve_supplier_profile_routing(
        _mixed_amazon_extracted(), rules.preset, _amazon_profile()
    )
    assert match is None


def test_amazon_mixed_billing_delivery_routes_unklar_not_ai_amex(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "amazon_mixed.pdf"
    create_pdf(pdf)
    processor = InvoiceProcessor(
        config,
        StubExtractor(_mixed_amazon_extracted()),
        office_rules=rules,
        profile_data=_amazon_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.payment_field == "unklar"
    assert result.storage_file.parent == output_dir / "unklar"
    assert result.art != "ai" or result.payment_field == "unklar"
    name = result.storage_file.name.lower()
    assert "_ai_" not in name
    assert "amex" not in name
    assert "unklar" in name or result.storage_file.parent.name == "unklar"
    assert "vobaai" not in name
    assert "vobaep" not in name


def test_somaa_only_in_delivery_not_enough_for_ai() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    match = resolve_supplier_profile_routing(
        _mixed_amazon_extracted(), rules.preset, _amazon_profile()
    )
    assert match is None
    mixed = evaluate_mixed_address_ambiguity(_mixed_amazon_extracted())
    assert mixed.business_signal_only_in_delivery is True


def test_private_roetestr_billing_plus_somaa_delivery_not_ai_amex(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "amazon_roete.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_mixed_amazon_extracted()),
        office_rules=rules,
        profile_data=_amazon_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert (result.art, result.payment_field) != ("ai", "amex")
    assert result.storage_file.parent == output_dir / "unklar"


def test_no_secure_payment_keeps_payment_field_unklar(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "amazon_pay.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_mixed_amazon_extracted()),
        office_rules=rules,
        profile_data=_amazon_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.payment_field == "unklar"


def test_amazon_clear_business_billing_still_ai_amex(tmp_path: Path) -> None:
    rules = load_office_rules(Path("office_rules.json"))
    match = resolve_supplier_profile_routing(
        _business_billing_amazon_extracted(), rules.preset, _amazon_profile()
    )
    assert match is not None
    assert match.rule_id == "amazon-ai-amex"
    assert match.routing.art == "ai"
    assert match.routing.payment_field == "amex"

    config_path, rules_path, input_dir, output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "amazon_biz.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_business_billing_amazon_extracted()),
        office_rules=rules,
        profile_data=_amazon_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    assert result.art == "ai"
    assert result.payment_field == "amex"
    assert result.storage_file.parent == output_dir / "amex"


def test_existing_amazon_somaa_billing_no_regression(tmp_path: Path) -> None:
    # Same fixture shape as test_amazon_somaa_recipient_routes_ai_amex_not_vobaai
    test_amazon_clear_business_billing_still_ai_amex(tmp_path)


def test_ui_v2_address_policy_is_generic() -> None:
    policy = default_classification_policy()
    assert policy.address_policy.billing_address_takes_precedence is True
    assert policy.address_policy.delivery_address_only_is_not_business_evidence is True
    assert policy.address_policy.mixed_billing_delivery_address_target == "unklar"
    assert policy.address_policy.private_billing_business_delivery_target == "unklar"
    texts = " ".join(classification_policy_ui_texts())
    assert "Rechnungsadresse vor Lieferadresse priorisieren" in texts
    assert "Geschäftliche Lieferadresse allein reicht nicht" in texts
    assert "Gemischte Rechnungs-/Lieferadresssignale zur Prüfung" in texts
    vm = build_saas_profile_surface_vm()
    assert "address_policy" in vm.ui_labels
    payload = surface_payload_as_dict(vm)
    assert payload["classification_policy"]["address_policy"][
        "billing_address_takes_precedence"
    ] is True
    blob = str(payload) + texts
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker


def test_filename_does_not_encode_safe_ai_amex_for_mixed(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, _output_dir, _ = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    create_pdf(input_dir / "amazon_name.pdf")
    processor = InvoiceProcessor(
        config,
        StubExtractor(_mixed_amazon_extracted()),
        office_rules=rules,
        profile_data=_amazon_profile(),
        original_source_dir=input_dir,
    )
    result = processor.process_all()[0]
    lowered = result.storage_file.name.lower()
    assert "er_ai_" not in lowered
    assert "_amex" not in lowered
