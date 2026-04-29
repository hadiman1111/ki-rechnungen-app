"""Tests for invoice_tool/profile_compiler.py – Profile Compiler MVP.

Covers: address_profiles → routing.strassen + routing.prioritaetsregeln.
All other profile sections are outside the MVP scope and are not tested here.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from invoice_tool.profile_compiler import compile_profile_to_rules


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile(**address_profiles_kwargs) -> dict:
    """Return a minimal profile dict containing a single address_profile."""
    return {
        "schema_version": "1.0",
        "profile_name": "Test",
        "categories": [],
        "folders": [],
        "account_card_profiles": [],
        "address_profiles": [address_profiles_kwargs],
        "naming_profile": {
            "separator": "_",
            "max_length": 50,
            "fields": [],
            "fallback_values": {},
        },
        "review_policy": {
            "unclear_folder": "unklar",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }


def _get_strassen(result: dict, preset: str = "office_default") -> list[dict]:
    return result["presets"][preset]["routing"]["strassen"]


def _get_prioritaetsregeln(result: dict, preset: str = "office_default") -> list[dict]:
    return result["presets"][preset]["routing"]["prioritaetsregeln"]


# ---------------------------------------------------------------------------
# A. Bismarckstraße → strassen entry with art=ai
# ---------------------------------------------------------------------------


def test_address_profile_bismarck_generates_street_rule() -> None:
    """Bismarckstraße with category=ai must produce a routing.strassen entry."""
    profile = _make_profile(
        id="bismarck-ai",
        label="Bismarckstraße",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        matching_mode="normal",
        enabled=True,
    )
    result = compile_profile_to_rules(profile)
    strassen = _get_strassen(result)

    assert len(strassen) == 1
    entry = strassen[0]
    assert entry["art"] == "ai"
    assert entry["key"] == "bismarck"  # normalized base from "Bismarckstraße"
    # Varianten must contain at least the most common form
    varianten_lower = [v.lower() for v in entry["varianten"]]
    assert any("bismarck" in v for v in varianten_lower), (
        f"Expected 'bismarck' in varianten, got: {entry['varianten']}"
    )
    assert any("strasse" in v or "straße" in v for v in varianten_lower), (
        "Expected a 'strasse' variant in output"
    )


# ---------------------------------------------------------------------------
# B. disabled profile is skipped
# ---------------------------------------------------------------------------


def test_address_profile_disabled_is_skipped() -> None:
    """An address_profile with enabled=False must not produce any output."""
    profile = _make_profile(
        id="bismarck-ai",
        label="Bismarckstraße",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=False,
    )
    result = compile_profile_to_rules(profile)
    assert _get_strassen(result) == []
    assert _get_prioritaetsregeln(result) == []


# ---------------------------------------------------------------------------
# C. Rötestraße with house_number
# ---------------------------------------------------------------------------


def test_address_profile_with_house_number() -> None:
    """House number must appear in at least one generated variant."""
    profile = _make_profile(
        id="roete-private",
        label="Rötestraße",
        category="private",
        canonical_address={"street": "Rötestraße", "house_number": "58"},
        matching_mode="normal",
        enabled=True,
    )
    result = compile_profile_to_rules(profile)
    strassen = _get_strassen(result)

    assert len(strassen) == 1
    varianten = strassen[0]["varianten"]
    assert any("58" in v for v in varianten), (
        f"Expected at least one variant containing '58', got: {varianten}"
    )


# ---------------------------------------------------------------------------
# D. matching_mode → fuzzy_threshold
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode,expected_threshold", [
    ("strict",   0.95),
    ("normal",   0.84),
    ("tolerant", 0.70),
])
def test_address_profile_matching_mode_maps_to_threshold(
    mode: str, expected_threshold: float
) -> None:
    profile = _make_profile(
        id="test-address",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        matching_mode=mode,
        enabled=True,
    )
    result = compile_profile_to_rules(profile)
    strassen = _get_strassen(result)

    assert len(strassen) == 1
    assert strassen[0]["fuzzy_threshold"] == expected_threshold, (
        f"Expected {expected_threshold} for mode={mode!r}, "
        f"got {strassen[0]['fuzzy_threshold']}"
    )


def test_address_profile_missing_matching_mode_defaults_to_normal() -> None:
    """Absent matching_mode must default to 0.84 (normal)."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    result = compile_profile_to_rules(profile)
    assert _get_strassen(result)[0]["fuzzy_threshold"] == 0.84


# ---------------------------------------------------------------------------
# E. exclude_if_text_contains → prioritaetsregeln
# ---------------------------------------------------------------------------


def test_address_profile_exclude_if_text_generates_priority_rule() -> None:
    """exclude_if_text_contains must produce a prioritaetsregeln entry."""
    profile = _make_profile(
        id="roete-private",
        label="Rötestraße",
        category="private",
        canonical_address={"street": "Rötestraße", "house_number": "58"},
        exclude_if_text_contains=["somaa"],
        matching_mode="normal",
        enabled=True,
    )
    result = compile_profile_to_rules(profile)
    rules = _get_prioritaetsregeln(result)

    assert len(rules) == 1
    rule = rules[0]
    assert "somaa" in rule["text_none_any"]
    assert "roete" in rule["street_any"]
    assert rule["art"] == "private"
    assert rule["zielordner"] == "private"


def test_no_exclude_produces_no_priority_rule() -> None:
    """When exclude_if_text_contains is empty, no priority rule must be generated."""
    profile = _make_profile(
        id="bismarck-ai",
        label="Bismarckstraße",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        exclude_if_text_contains=[],
        enabled=True,
    )
    result = compile_profile_to_rules(profile)
    assert _get_prioritaetsregeln(result) == []


# ---------------------------------------------------------------------------
# F. advanced_variants are included in varianten
# ---------------------------------------------------------------------------


def test_address_profile_advanced_variants_included() -> None:
    """advanced_variants must appear in the generated varianten list."""
    profile = _make_profile(
        id="roete-private",
        label="Rötestraße",
        category="private",
        canonical_address={"street": "Rötestraße"},
        advanced_variants=["rotestrasse"],
        matching_mode="normal",
        enabled=True,
    )
    result = compile_profile_to_rules(profile)
    strassen = _get_strassen(result)

    assert len(strassen) == 1
    assert "rotestrasse" in strassen[0]["varianten"], (
        f"'rotestrasse' must be in varianten, got: {strassen[0]['varianten']}"
    )


# ---------------------------------------------------------------------------
# G. Output has valid office_rules structure
# ---------------------------------------------------------------------------


def test_compile_returns_valid_office_rules_structure() -> None:
    """Output must have the top-level shape of office_rules.json."""
    profile = _make_profile(
        id="bismarck-ai",
        label="Bismarckstraße",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    result = compile_profile_to_rules(profile)

    assert "active_preset" in result
    assert "presets" in result
    preset_name = result["active_preset"]
    assert preset_name in result["presets"]
    routing = result["presets"][preset_name]["routing"]
    assert "strassen" in routing
    assert "prioritaetsregeln" in routing
    assert isinstance(routing["strassen"], list)
    assert isinstance(routing["prioritaetsregeln"], list)


def test_compile_custom_preset_name() -> None:
    """Custom preset_name must be used as the key in the output."""
    profile = _make_profile(
        id="bismarck-ai",
        label="Bismarckstraße",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    result = compile_profile_to_rules(profile, preset_name="my_custom_preset")
    assert result["active_preset"] == "my_custom_preset"
    assert "my_custom_preset" in result["presets"]


def test_empty_address_profiles_produces_empty_lists() -> None:
    """Profile with empty address_profiles must return empty strassen and prioritaetsregeln."""
    profile: dict = {
        "schema_version": "1.0",
        "profile_name": "Empty",
        "categories": [],
        "folders": [],
        "account_card_profiles": [],
        "address_profiles": [],
        "naming_profile": {"separator": "_", "max_length": 50, "fields": [], "fallback_values": {}},
        "review_policy": {
            "unclear_folder": "unklar",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }
    result = compile_profile_to_rules(profile)
    assert _get_strassen(result) == []
    assert _get_prioritaetsregeln(result) == []


def test_multiple_address_profiles_produce_multiple_entries() -> None:
    """Two enabled profiles must each produce one strassen entry."""
    profile: dict = {
        "schema_version": "1.0",
        "profile_name": "Multi",
        "categories": [],
        "folders": [],
        "account_card_profiles": [],
        "address_profiles": [
            {
                "id": "bismarck-ai",
                "label": "Bismarck",
                "category": "ai",
                "canonical_address": {"street": "Bismarckstraße"},
                "enabled": True,
            },
            {
                "id": "roete-private",
                "label": "Röte",
                "category": "private",
                "canonical_address": {"street": "Rötestraße", "house_number": "58"},
                "exclude_if_text_contains": ["somaa"],
                "advanced_variants": ["rotestrasse"],
                "enabled": True,
            },
        ],
        "naming_profile": {"separator": "_", "max_length": 50, "fields": [], "fallback_values": {}},
        "review_policy": {
            "unclear_folder": "unklar",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }
    result = compile_profile_to_rules(profile)
    strassen = _get_strassen(result)
    prioritaetsregeln = _get_prioritaetsregeln(result)

    assert len(strassen) == 2
    # Only roete has exclude → 1 priority rule
    assert len(prioritaetsregeln) == 1
    keys = {s["key"] for s in strassen}
    assert "bismarck" in keys
    assert "roete" in keys


def test_profile_example_json_produces_two_address_entries() -> None:
    """The shipping profile_config.example.json must compile to exactly 2 strassen entries."""
    import json
    from pathlib import Path

    path = Path("profile_config.example.json")
    with path.open(encoding="utf-8") as fh:
        profile = json.load(fh)

    result = compile_profile_to_rules(profile)
    strassen = _get_strassen(result)
    prioritaetsregeln = _get_prioritaetsregeln(result)

    assert len(strassen) == 2, f"Expected 2 strassen, got {len(strassen)}"
    # roete-private has exclude_if_text_contains → 1 priority rule
    assert len(prioritaetsregeln) == 1
    # rotestrasse must be in roete varianten (advanced_variants)
    roete_entries = [s for s in strassen if s["key"] == "roete"]
    assert roete_entries, "Expected a 'roete' entry"
    assert "rotestrasse" in roete_entries[0]["varianten"], (
        "advanced_variants='rotestrasse' must appear in varianten"
    )


# ---------------------------------------------------------------------------
# account_card_profiles → routing.konten
# ---------------------------------------------------------------------------

def _get_konten(result: dict, preset: str = "office_default") -> list[dict]:
    return result["presets"][preset]["routing"].get("konten", [])


def test_account_card_profile_generates_konten_entry() -> None:
    """A single enabled account_card_profile must produce one konten dict."""
    profile = {
        "schema_version": "1.0",
        "profile_name": "Test",
        "categories": [],
        "folders": [],
        "account_card_profiles": [
            {
                "id": "my-bank",
                "label": "My Bank",
                "category": "ai",
                "payment_field": "mybank",
                "card_endings": ["1234", "5678"],
                "apple_pay_endings": ["9999"],
                "iban_endings": ["0001"],
                "provider_hints": ["my bank", "mybank gmbh"],
                "assignment_hints": ["ai"],
                "enabled": True,
            }
        ],
        "address_profiles": [],
        "naming_profile": {"separator": "_", "max_length": 50, "fields": [], "fallback_values": {}},
        "review_policy": {
            "unclear_folder": "unklar",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }
    result = compile_profile_to_rules(profile)
    konten = _get_konten(result)

    assert len(konten) == 1
    k = konten[0]
    assert k["name"] == "my-bank"
    assert k["payment_field"] == "mybank"
    assert k["konto"] == "mybank"
    assert k["art_override"] == "ai"
    assert k["karten_endungen"] == ["1234", "5678"]
    assert k["apple_pay_endungen"] == ["9999"]
    assert k["iban_endungen"] == ["0001"]
    assert k["anbieter_hinweise"] == ["my bank", "mybank gmbh"]
    assert k["zuweisungs_hinweise"] == ["ai"]


def test_account_card_profile_unklar_category_gives_no_art_override() -> None:
    """category='unklar' must produce art_override=None (no forced category)."""
    profile = _make_profile(
        id="amex-profile",
        label="Amex",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    # Override to test account_card_profiles specifically
    profile["account_card_profiles"] = [
        {
            "id": "amex",
            "label": "American Express",
            "category": "unklar",
            "payment_field": "amex",
            "card_endings": ["1005"],
            "apple_pay_endings": [],
            "iban_endings": [],
            "provider_hints": ["american express"],
            "assignment_hints": [],
            "enabled": True,
        }
    ]
    result = compile_profile_to_rules(profile)
    konten = _get_konten(result)
    assert len(konten) == 1
    assert konten[0]["art_override"] is None, (
        "category='unklar' must yield art_override=None"
    )


def test_account_card_profile_disabled_is_skipped() -> None:
    """enabled=False must result in no konten entry."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    profile["account_card_profiles"] = [
        {
            "id": "disabled-bank",
            "label": "Disabled",
            "category": "ai",
            "payment_field": "disabledbank",
            "card_endings": ["0000"],
            "apple_pay_endings": [],
            "iban_endings": [],
            "provider_hints": [],
            "assignment_hints": [],
            "enabled": False,
        }
    ]
    result = compile_profile_to_rules(profile)
    assert _get_konten(result) == []


def test_account_card_profile_missing_lists_default_to_empty() -> None:
    """Optional list fields absent from the profile must default to empty lists."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    profile["account_card_profiles"] = [
        {
            "id": "minimal",
            "label": "Minimal",
            "category": "private",
            "payment_field": "minimal",
            "enabled": True,
            # All list fields absent
        }
    ]
    result = compile_profile_to_rules(profile)
    konten = _get_konten(result)

    assert len(konten) == 1
    k = konten[0]
    assert k["karten_endungen"] == []
    assert k["apple_pay_endungen"] == []
    assert k["iban_endungen"] == []
    assert k["anbieter_hinweise"] == []
    assert k["zuweisungs_hinweise"] == []

    # Must be parseable by load_office_rules_from_dict
    from pathlib import Path
    from invoice_tool.config import load_office_rules_from_dict, merge_rules_dicts
    rules_dict = json.loads(Path("office_rules.json").read_text(encoding="utf-8"))
    merged = merge_rules_dicts(rules_dict, result)
    base_dir = Path("office_rules.json").resolve().parent
    office_rules = load_office_rules_from_dict(merged, base_dir)
    assert office_rules is not None


def test_compile_profile_example_generates_konten_entries() -> None:
    """profile_config.example.json must produce konten from account_card_profiles."""
    example_profile = json.loads(Path("profile_config.example.json").read_text(encoding="utf-8"))
    result = compile_profile_to_rules(example_profile)
    konten = _get_konten(result)

    # profile_config.example.json has 5 account_card_profiles, all enabled
    assert len(konten) == 5, f"Expected 5 konten, got {len(konten)}: {[k['name'] for k in konten]}"
    names = {k["name"] for k in konten}
    assert "amex" in names
    assert "vobaai" in names
    assert "vobaep" in names


# ---------------------------------------------------------------------------
# business_context_profiles → routing.business_context_rules
# ---------------------------------------------------------------------------

def _get_bc_rules(result: dict, preset: str = "office_default") -> list[dict]:
    return result["presets"][preset]["routing"].get("business_context_rules", [])


def test_business_context_profile_generates_rule() -> None:
    """A single enabled business_context_profile must produce one business_context_rules entry."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    profile["business_context_profiles"] = [
        {
            "id": "my-firm",
            "label": "My Firm",
            "required_keywords": ["myfirm", "client"],
            "optional_keywords": ["architektur", "design"],
            "category": "ai",
            "match_source": "raw_text",
            "enabled": True,
        }
    ]
    result = compile_profile_to_rules(profile)
    bc_rules = _get_bc_rules(result)

    assert len(bc_rules) == 1
    rule = bc_rules[0]
    assert rule["name"] == "my-firm"
    assert rule["art"] == "ai"
    assert rule["text_all"] == ["myfirm", "client"]
    assert rule["text_any"] == ["architektur", "design"]
    assert rule["match_source"] == "raw_text"


def test_business_context_profile_disabled_is_skipped() -> None:
    """enabled=False must result in no business_context_rules entry."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    profile["business_context_profiles"] = [
        {
            "id": "disabled-ctx",
            "label": "Disabled",
            "required_keywords": ["x"],
            "optional_keywords": [],
            "category": "ai",
            "enabled": False,
        }
    ]
    result = compile_profile_to_rules(profile)
    assert _get_bc_rules(result) == []


def test_business_context_profile_match_source_defaults_to_enriched_text() -> None:
    """Absent match_source must default to 'enriched_text'."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    profile["business_context_profiles"] = [
        {
            "id": "ctx-no-source",
            "label": "No Source",
            "required_keywords": [],
            "optional_keywords": ["keyword"],
            "category": "ai",
            "enabled": True,
            # match_source absent
        }
    ]
    result = compile_profile_to_rules(profile)
    bc_rules = _get_bc_rules(result)
    assert len(bc_rules) == 1
    assert bc_rules[0]["match_source"] == "enriched_text"


def test_business_context_profile_raw_text_is_preserved() -> None:
    """match_source='raw_text' must appear in the output."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    profile["business_context_profiles"] = [
        {
            "id": "ctx-raw",
            "label": "Raw",
            "required_keywords": ["firm", "keyword"],
            "optional_keywords": ["extra"],
            "category": "ep",
            "match_source": "raw_text",
            "enabled": True,
        }
    ]
    result = compile_profile_to_rules(profile)
    bc_rules = _get_bc_rules(result)
    assert len(bc_rules) == 1
    assert bc_rules[0]["match_source"] == "raw_text"


def test_compile_profile_example_generates_business_context_rules() -> None:
    """profile_config.example.json must produce business_context_rules."""
    example_profile = json.loads(Path("profile_config.example.json").read_text(encoding="utf-8"))
    result = compile_profile_to_rules(example_profile)
    bc_rules = _get_bc_rules(result)

    # profile_config.example.json has 3 enabled business_context_profiles
    assert len(bc_rules) == 3
    names = {r["name"] for r in bc_rules}
    assert "somaa-event-production" in names
    assert "somaa-architektur-innenarchitektur" in names
    assert "somaa-unspecified" in names


# ---------------------------------------------------------------------------
# classification_profile → classification section
# ---------------------------------------------------------------------------

def _get_classification(result: dict, preset: str = "office_default") -> dict | None:
    return result["presets"][preset].get("classification")


def test_classification_profile_generates_classification_section() -> None:
    """A classification_profile must produce a classification section."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    profile["classification_profile"] = {
        "invoice_keywords": ["rechnung", "faktura"],
        "document_keywords": ["quittung", "bescheid"],
        "internal_invoice_keywords": ["eigenbeleg"],
        "invoice_like_indicators": [],
        "invoice_like_threshold": 5,
    }
    result = compile_profile_to_rules(profile)
    cls = _get_classification(result)

    assert cls is not None, "classification section must be generated"
    assert cls["invoice_keywords"] == ["rechnung", "faktura"]
    assert cls["document_keywords"] == ["quittung", "bescheid"]
    assert cls["internal_invoice_keywords"] == ["eigenbeleg"]
    assert cls["invoice_like_indicators"] == []
    assert cls["invoice_like_threshold"] == 5


def test_classification_profile_missing_lists_default_to_empty() -> None:
    """Absent optional list fields must default to empty lists."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    profile["classification_profile"] = {}  # all fields absent
    result = compile_profile_to_rules(profile)
    cls = _get_classification(result)

    assert cls is not None
    assert cls["invoice_keywords"] == []
    assert cls["document_keywords"] == []
    assert cls["internal_invoice_keywords"] == []
    assert cls["invoice_like_indicators"] == []
    assert cls["invoice_like_threshold"] == 3  # default

    # Must be parseable by load_office_rules_from_dict
    from invoice_tool.config import load_office_rules_from_dict, merge_rules_dicts
    rules_dict = json.loads(Path("office_rules.json").read_text(encoding="utf-8"))
    merged = merge_rules_dicts(rules_dict, result)
    base_dir = Path("office_rules.json").resolve().parent
    office_rules = load_office_rules_from_dict(merged, base_dir)
    assert office_rules is not None


def test_classification_profile_absent_does_not_generate_classification() -> None:
    """Without classification_profile, no classification must appear in output."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    # No classification_profile key
    profile.pop("classification_profile", None)
    result = compile_profile_to_rules(profile)
    cls = _get_classification(result)
    assert cls is None, "classification must NOT be generated when classification_profile is absent"


def test_compile_profile_example_generates_classification() -> None:
    """profile_config.example.json must produce classification from classification_profile."""
    example_profile = json.loads(Path("profile_config.example.json").read_text(encoding="utf-8"))
    result = compile_profile_to_rules(example_profile)
    cls = _get_classification(result)

    assert cls is not None
    assert "rechnung" in cls["invoice_keywords"]
    assert "invoice" in cls["invoice_keywords"]
    # profile has 3 document_keywords
    assert len(cls["document_keywords"]) >= 1
    assert "eigenbeleg" in cls["internal_invoice_keywords"]
