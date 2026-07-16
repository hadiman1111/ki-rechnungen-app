"""Focused tests for recipient guard, same-run duplicate archive, Anthropic supplier rule."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from invoice_tool.config import load_app_config, load_office_rules
from invoice_tool.file_lifecycle import archive_same_run_duplicate
from invoice_tool.models import ExtractedData
from invoice_tool.processing import InvoiceProcessor
from invoice_tool.recipient_guard import evaluate_recipient_guard
from invoice_tool.routing import apply_final_assignment, determine_business_context, detect_payment_method, resolve_account
from invoice_tool.state import fingerprint_file
from invoice_tool.supplier_routing import resolve_supplier_profile_routing
from tests.test_invoice_tool import StubExtractor, create_pdf, make_test_setup


def _sample_profile() -> dict:
    return {
        "recipient_policy": {
            "business_recipient_hints": [
                "somaa",
                "tandawardaja",
                "alexander tandawardaja",
                "bismarckstrasse",
            ],
            "private_recipient_hints": [
                "tandawardaja",
                "alexander tandawardaja",
                "roetestrasse",
            ],
            "foreign_recipient_block_hints": [],
        },
        "vendor_profiles": [
            {
                "id": "anthropic-ep-amex-1005",
                "label": "Anthropic PBC",
                "recognition_hints": ["anthropic", "anthropic pbc", "anthropic, pbc"],
                "payment_field": "amex-1005",
                "category": "ep",
                "target_folder": "amex",
                "payment_reference": "1005",
                "match_scope": "supplier",
                "exclusive": True,
                "enabled": True,
            }
        ],
    }


class SequenceExtractor:
    def __init__(self, items: list[ExtractedData]) -> None:
        self.items = list(items)
        self.index = 0

    def extract(self, pdf_path: Path, *, log):
        item = self.items[min(self.index, len(self.items) - 1)]
        self.index += 1
        return item


def test_martin_kohnle_foreign_recipient_routes_unklar_not_private(tmp_path: Path) -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="21.06.2026",
        supplier_raw="Martin Kohnle",
        amount_raw="3172,31",
        invoice_number_raw="39705-RE26084/1",
        raw_text=(
            "Rechnung 39705-RE26084/1 Martin Kohnle "
            "Projekt Airstream Ausbau 2 Marc Goldhammer "
            "Ernst-Kauffmann-Strasse 69 71640 Ludwigsburg "
            "Gesamtbetrag 3.172,31 EUR"
        ),
        address_fragments=[
            "Marc Goldhammer",
            "Ernst-Kauffmann-Straße 69",
            "71640 Ludwigsburg",
        ],
        source_method="openai",
    )
    account = resolve_account(extracted, rules.preset)
    art, art_reason = determine_business_context(extracted, account, rules.preset, None)
    payment = detect_payment_method(extracted, rules.preset)
    routing = apply_final_assignment(
        art=art,
        payment_decision=payment,
        account_decision=account,
        street_key=None,
        preset=rules.preset,
    )
    guard = evaluate_recipient_guard(
        extracted,
        rules.preset,
        profile_data=_sample_profile(),
        proposed_art=routing.art,
        street_key=None,
        priority_routing=None,
        art_reason=art_reason,
    )
    assert guard.outcome == "force_unklar"
    assert routing.art == "private"
    assert routing.payment_field == "unklar"

    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "RE26084_1.pdf"
    create_pdf(pdf)
    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.storage_file.parent.name == "unklar"
    assert result.art == "unklar"
    assert result.payment_field == "unklar"
    assert "private" not in result.storage_file.name
    assert "unklar" in result.storage_file.name


def test_legitimate_private_roete_still_private(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "private_roete.pdf"
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
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.storage_file.parent.name == "private"
    assert result.art == "private"


def test_same_run_duplicate_archived_under_duplikate(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf_a = input_dir / "Rechnung_RE0072.pdf"
    pdf_b = input_dir / "Rechnung_RE0072_29.06.2026.pdf"
    create_pdf(pdf_a)
    shutil.copyfile(pdf_a, pdf_b)
    assert fingerprint_file(pdf_a) == fingerprint_file(pdf_b)

    extracted = ExtractedData(
        invoice_date_raw="29.06.2026",
        supplier_raw="Superpunkt Kalashn",
        amount_raw="1997,71",
        raw_text="Rechnung SOMAA Bismarckstrasse 63 RE0072 1997,71 EUR",
        address_fragments=["SOMAA Architektur", "Bismarckstraße 63"],
        card_endings=["7166"],
        source_method="openai",
    )
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
    assert list(input_dir.glob("*.pdf")) == []
    run_id = processor.run_logger.run_id
    dup_dir = input_dir / "archiv" / run_id / "duplikate"
    assert dup_dir.is_dir()
    assert len(list(dup_dir.glob("*.pdf"))) == 1
    assert (input_dir / "archiv" / run_id / pdf_a.name).exists()
    report_dir = output_dir / "_duplicate_reports"
    reports = list(report_dir.glob("Rechnung_RE0072_29.06.2026.txt"))
    assert reports
    report_text = reports[0].read_text(encoding="utf-8")
    assert "source_lifecycle_status: archived_as_duplicate" in report_text
    assert "source_archive_path:" in report_text


def test_archive_same_run_duplicate_collision_suffix(tmp_path: Path) -> None:
    source_root = tmp_path / "input"
    source_root.mkdir()
    run_id = "20260714_test"
    dup_dir = source_root / "archiv" / run_id / "duplikate"
    dup_dir.mkdir(parents=True)
    first = source_root / "dup.pdf"
    create_pdf(first)
    shutil.copyfile(first, dup_dir / "dup.pdf")
    second = source_root / "dup.pdf"
    create_pdf(second)
    result = archive_same_run_duplicate(
        source_path=second,
        source_root=source_root,
        run_id=run_id,
    )
    assert result.success
    assert result.archive_path == dup_dir / "dup__duplikat_2.pdf"
    assert not second.exists()


def test_anthropic_supplier_rule_routes_ep_amex_single_output(tmp_path: Path) -> None:
    config_path, rules_path, input_dir, output_dir, _docs = make_test_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)
    pdf = input_dir / "anthropic.pdf"
    create_pdf(pdf)
    extracted = ExtractedData(
        invoice_date_raw="23.06.2026",
        supplier_raw="Anthropic PBC",
        amount_raw="90,00",
        raw_text="Invoice Anthropic PBC SOMAA Architektur amount 90.00 USD",
        address_fragments=["SOMAA Architektur & Innenarchitektur"],
        source_method="openai",
    )
    match = resolve_supplier_profile_routing(extracted, rules.preset, _sample_profile())
    assert match is not None
    assert match.routing.art == "ep"
    assert match.routing.payment_field == "amex-1005"
    assert match.routing.zielordner == "amex"

    processor = InvoiceProcessor(
        config,
        StubExtractor(extracted),
        office_rules=rules,
        profile_data=_sample_profile(),
        original_source_dir=input_dir,
    )
    results = processor.process_all()
    assert len(results) == 1
    result = results[0]
    assert result.storage_file.parent.name == "amex"
    assert result.art == "ep"
    assert result.payment_field == "amex-1005"
    assert "vobaep" not in result.storage_file.name
    assert len(list(output_dir.rglob("*anthropic*"))) == 1
    ep_matches = list((output_dir / "ep").glob("*anthropic*")) if (output_dir / "ep").exists() else []
    assert not ep_matches


def test_anthropic_text_mention_without_supplier_does_not_match() -> None:
    rules = load_office_rules(Path("office_rules.json"))
    extracted = ExtractedData(
        invoice_date_raw="23.06.2026",
        supplier_raw="Microsoft Ireland Operations Ltd",
        amount_raw="11,70",
        raw_text="Powered by Anthropic models in Azure",
        source_method="openai",
    )
    match = resolve_supplier_profile_routing(extracted, rules.preset, _sample_profile())
    assert match is None
