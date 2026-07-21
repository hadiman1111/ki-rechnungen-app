"""SOMAA bounded rule correction — filename token repair and routing tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invoice_tool.configuration_model import (
    SOMAA_CANONICAL_FILENAME_TEMPLATE,
    Configuration,
    FilenameComponent,
    FilenamePattern,
    MatchingRule,
    UnmatchedConfiguration,
    compile_profile_bundle_to_legacy,
    pattern_from_template,
    pattern_to_template,
    preview_filename,
    repair_filename_pattern,
    resolve_configuration_match,
    somaa_canonical_filename_pattern,
)
from invoice_tool.filename_schema import tokenize_filename_stem
from invoice_tool.profile_compiler import compile_profile_to_rules
from invoice_tool.profile_store import load_profile_bundle, save_profile_bundle
from invoice_tool.scan_models import get_scan_model
from invoice_tool.target_routing import render_routing_filename_template


def _fragmented_somaa_pattern() -> FilenamePattern:
    """Stored corruption: tokens split at underscores inside brace names."""
    return FilenamePattern(
        separator="_",
        components=[
            FilenameComponent(type="system", key="custom_text", custom_text="{invoice"),
            FilenameComponent(type="system", key="custom_text", custom_text="date}"),
            FilenameComponent(type="system", key="custom_text", custom_text="er"),
            FilenameComponent(type="feature", key="art", label="art"),
            FilenameComponent(type="feature", key="supplier", label="supplier"),
            FilenameComponent(type="feature", key="amount", label="amount"),
            FilenameComponent(type="system", key="custom_text", custom_text="{payment"),
            FilenameComponent(type="system", key="custom_text", custom_text="field}"),
            FilenameComponent(type="system", key="extension", label="Dateityp"),
        ],
    )


@pytest.fixture()
def scan_model():
    return get_scan_model("rechnungen")


def test_tokenize_preserves_invoice_date_and_payment_field() -> None:
    stem = "{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}"
    tokens = tokenize_filename_stem(stem)
    assert tokens == [
        "{invoice_date}",
        "er",
        "{art}",
        "{supplier}",
        "{amount}",
        "{payment_field}",
    ]


def test_repair_fragmented_pattern_round_trip(scan_model) -> None:
    repaired = repair_filename_pattern(_fragmented_somaa_pattern(), scan_model=scan_model)
    template = pattern_to_template(repaired)
    assert template == SOMAA_CANONICAL_FILENAME_TEMPLATE
    keys = [c.key for c in repaired.components if c.type == "feature"]
    assert keys == ["invoice_date", "art", "supplier", "amount", "payment_field"]


def test_pattern_from_dict_auto_repairs(tmp_path: Path, scan_model) -> None:
    raw = _fragmented_somaa_pattern().to_dict()
    loaded = FilenamePattern.from_dict(raw)
    assert pattern_to_template(loaded) == SOMAA_CANONICAL_FILENAME_TEMPLATE


def test_bare_token_names_repair_to_features(scan_model) -> None:
    corrupted = "invoice_date_er_{art}_{supplier}_{amount}_payment_field.pdf"
    pattern = pattern_from_template(corrupted, scan_model=scan_model)
    assert pattern_to_template(pattern) == SOMAA_CANONICAL_FILENAME_TEMPLATE


def test_ui_round_trip_never_splits_invoice_date(scan_model) -> None:
    canonical = somaa_canonical_filename_pattern(scan_model)
    draft = FilenamePattern.from_dict(canonical.to_dict())
    saved = FilenamePattern.from_dict(draft.to_dict())
    reloaded = FilenamePattern.from_dict(json.loads(json.dumps(saved.to_dict())))
    for pattern in (draft, saved, reloaded):
        template = pattern_to_template(pattern)
        assert "{invoice_date}" in template or "invoice_date" not in template.split("_")[0]
        assert "invoice" not in [
            c.custom_text
            for c in pattern.components
            if c.type == "system" and c.key == "custom_text"
        ]
        assert template == SOMAA_CANONICAL_FILENAME_TEMPLATE


def test_filename_render_historical_contract(scan_model) -> None:
    pattern = somaa_canonical_filename_pattern(scan_model)
    template = pattern_to_template(pattern)
    rendered = render_routing_filename_template(
        template,
        {
            "invoice_date": "260708",
            "art": "er",
            "supplier": "Musterfirma",
            "amount": "125,00",
            "payment_field": "amex",
        },
    )
    assert rendered == "260708_er_er_Musterfirma_125,00_amex.pdf"


def test_filename_missing_supplier(scan_model) -> None:
    template = SOMAA_CANONICAL_FILENAME_TEMPLATE
    rendered = render_routing_filename_template(
        template,
        {
            "invoice_date": "260708",
            "art": "er",
            "supplier": "",
            "amount": "125,00",
            "payment_field": "amex",
        },
    )
    assert "unbekannt" in rendered


def test_filename_umlaut_sanitization(scan_model) -> None:
    rendered = render_routing_filename_template(
        SOMAA_CANONICAL_FILENAME_TEMPLATE,
        {
            "invoice_date": "260708",
            "art": "er",
            "supplier": "Müller GmbH",
            "amount": "125,00",
            "payment_field": "amex",
        },
    )
    assert "/" not in rendered
    assert "müller" in rendered.lower() or "muller" in rendered.lower()


def test_somaa_matching_matrix() -> None:
    configs = [
        Configuration(
            id="amex",
            name="American Express",
            active=True,
            matching=MatchingRule(
                feature_key="payment_field",
                values=["amex", "American Express"],
            ),
            destination={"type": "legacy_relative", "path": "amex"},
        ),
        Configuration(
            id="ep",
            name="Event Production",
            active=True,
            matching=MatchingRule(
                feature_key="payment_field",
                values=["ep", "Event Production", "vobaep"],
            ),
            destination={"type": "legacy_relative", "path": "ep"},
        ),
        Configuration(
            id="ai",
            name="Architektur & Innenarchitektur",
            active=True,
            matching=MatchingRule(
                feature_key="payment_field",
                values=["ai", "Architektur & Innenarchitektur", "vobaai"],
            ),
            destination={"type": "legacy_relative", "path": "ai"},
        ),
        Configuration(
            id="private",
            name="Privat",
            active=True,
            matching=MatchingRule(
                feature_key="payment_field",
                values=["private", "privat", "Privat", "Private Rechnung"],
            ),
            destination={"type": "legacy_relative", "path": "private"},
        ),
    ]

    cases = [
        ("amex", "amex"),
        ("American Express", "amex"),
        ("ep", "ep"),
        ("Event Production", "ep"),
        ("vobaep", "ep"),
        ("ai", "ai"),
        ("Architektur & Innenarchitektur", "ai"),
        ("vobaai", "ai"),
        ("private", "private"),
        ("Privat", "private"),
        ("Private Rechnung", "private"),
        ("totally-unknown", None),
        ("", None),
    ]
    for value, expected_id in cases:
        matched, _reason = resolve_configuration_match(
            configs,
            feature_key="payment_field",
            value=value,
        )
        if expected_id is None:
            assert matched is None, value
        else:
            assert matched is not None, value
            assert matched.id == expected_id, value


def test_compile_profile_without_test_contract(tmp_path: Path) -> None:
    profile = json.loads(
        (Path(__file__).resolve().parents[1] / "profile_config.example.json").read_text(encoding="utf-8")
    )
    profile["document_profiles"] = [
        dp for dp in profile.get("document_profiles", []) if dp.get("id") != "test_contract"
    ]
    result = compile_profile_to_rules(profile)
    assert "document_profiles" in result


def test_compile_profile_test_contract_disabled(tmp_path: Path) -> None:
    profile = json.loads(
        (Path(__file__).resolve().parents[1] / "profile_config.example.json").read_text(encoding="utf-8")
    )
    for dp in profile.get("document_profiles", []):
        if dp.get("id") == "test_contract":
            dp["enabled"] = False
    result = compile_profile_to_rules(profile)
    compiled_ids = [item.get("id") for item in result.get("document_profiles", [])]
    assert "test_contract" not in compiled_ids


def test_preview_filename_neutral(scan_model) -> None:
    pattern = somaa_canonical_filename_pattern(scan_model)
    example = preview_filename(pattern, scan_model)
    assert example.endswith(".pdf")
    assert "invoice" not in example.split("_")[0]
