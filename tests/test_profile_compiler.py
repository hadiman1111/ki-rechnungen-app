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


# ---------------------------------------------------------------------------
# vendor_profiles → routing.payment_detection_rules
# ---------------------------------------------------------------------------

def _get_pdr(result: dict, preset: str = "office_default") -> list[dict]:
    return result["presets"][preset]["routing"].get("payment_detection_rules", [])


def test_vendor_profile_generates_payment_detection_rule() -> None:
    """A vendor_profile with recognition_hints must produce one payment_detection_rule."""
    profile = _make_profile(
        id="test",
        label="Test",
        category="ai",
        canonical_address={"street": "Bismarckstraße"},
        enabled=True,
    )
    profile["vendor_profiles"] = [
        {
            "id": "my-vendor",
            "label": "My Vendor",
            "recognition_hints": ["myvendor", "vendor.com", "hi@vendor.com"],
            "payment_field": "amex",
            "enabled": True,
        }
    ]
    result = compile_profile_to_rules(profile)
    pdr = _get_pdr(result)

    assert len(pdr) == 1
    rule = pdr[0]
    assert rule["name"] == "my-vendor"
    assert rule["text_any"] == ["myvendor", "vendor.com", "hi@vendor.com"]
    assert rule["payment_method"] == "amex"
    assert rule["explicit"] is True
    assert rule["text_all"] == []


def test_vendor_profile_disabled_is_skipped() -> None:
    """enabled=False must skip the vendor."""
    profile = _make_profile(
        id="test", label="Test", category="ai",
        canonical_address={"street": "Bismarckstraße"}, enabled=True,
    )
    profile["vendor_profiles"] = [
        {"id": "disabled-vendor", "label": "Disabled",
         "recognition_hints": ["x"], "payment_field": "amex", "enabled": False}
    ]
    assert _get_pdr(compile_profile_to_rules(profile)) == []


def test_vendor_profile_without_recognition_hints_is_skipped() -> None:
    """A vendor without recognition_hints produces no rule (no match criteria)."""
    profile = _make_profile(
        id="test", label="Test", category="ai",
        canonical_address={"street": "Bismarckstraße"}, enabled=True,
    )
    profile["vendor_profiles"] = [
        {"id": "no-hints", "label": "No Hints",
         "recognition_hints": [], "payment_field": "amex", "enabled": True}
    ]
    assert _get_pdr(compile_profile_to_rules(profile)) == []


def test_vendor_profiles_absent_generates_no_pdr() -> None:
    """Without vendor_profiles, no payment_detection_rules key."""
    profile = _make_profile(
        id="test", label="Test", category="ai",
        canonical_address={"street": "Bismarckstraße"}, enabled=True,
    )
    profile.pop("vendor_profiles", None)
    result = compile_profile_to_rules(profile)
    assert "payment_detection_rules" not in result["presets"]["office_default"]["routing"]


def test_compile_profile_example_generates_payment_detection_rules() -> None:
    """profile_config.example.json vendor_profiles must produce payment_detection_rules."""
    example = json.loads(Path("profile_config.example.json").read_text(encoding="utf-8"))
    result = compile_profile_to_rules(example)
    pdr = _get_pdr(result)
    assert len(pdr) >= 1
    names = {r["name"] for r in pdr}
    assert "cursor-anysphere" in names


# ---------------------------------------------------------------------------
# Classification document_keywords – example profile completeness
# ---------------------------------------------------------------------------


def test_example_profile_document_keywords_includes_bestellung_keywords() -> None:
    """profile_config.example.json must include Bestellbestätigungs-Keywords."""
    example = json.loads(Path("profile_config.example.json").read_text(encoding="utf-8"))
    doc_kw = example.get("classification_profile", {}).get("document_keywords", [])
    assert "bestellte artikel" in doc_kw
    assert "bestellbestätigung" in doc_kw
    assert "order confirmation" in doc_kw


# ---------------------------------------------------------------------------
# validate_profile
# ---------------------------------------------------------------------------

from invoice_tool.profile_compiler import validate_profile


def test_validate_profile_clean_profile_returns_no_issues() -> None:
    """A valid profile must produce no issues."""
    example = json.loads(Path("profile_config.example.json").read_text(encoding="utf-8"))
    issues = validate_profile(example)
    assert issues == [], f"Unexpected issues: {issues}"


def test_validate_profile_detects_duplicate_card_endings() -> None:
    """Duplicate card_endings across two account_card_profiles must be reported."""
    profile = {
        "account_card_profiles": [
            {"id": "a", "label": "A", "card_endings": ["1234"], "enabled": True},
            {"id": "b", "label": "B", "card_endings": ["1234", "5678"], "enabled": True},
        ]
    }
    issues = validate_profile(profile)
    assert any("1234" in i for i in issues), f"Expected duplicate 1234 issue, got: {issues}"


def test_validate_profile_detects_vendor_without_recognition_hints() -> None:
    """A vendor_profile with empty recognition_hints must be flagged."""
    profile = {
        "account_card_profiles": [],
        "vendor_profiles": [
            {"id": "no-hints-vendor", "label": "X",
             "recognition_hints": [], "enabled": True}
        ]
    }
    issues = validate_profile(profile)
    assert any("no-hints-vendor" in i for i in issues), f"Expected issue for empty hints, got: {issues}"


def test_validate_profile_disabled_entries_not_flagged() -> None:
    """Disabled entries with issues must not be reported."""
    profile = {
        "account_card_profiles": [
            {"id": "a", "label": "A", "card_endings": ["1234"], "enabled": True},
            {"id": "dup", "label": "Dup", "card_endings": ["1234"], "enabled": False},
        ],
        "vendor_profiles": [
            {"id": "no-hints", "label": "X", "recognition_hints": [], "enabled": False}
        ]
    }
    issues = validate_profile(profile)
    assert issues == [], f"Disabled entries must not cause issues: {issues}"


# ---------------------------------------------------------------------------
# _compile_naming_profile
# ---------------------------------------------------------------------------

from invoice_tool.profile_compiler import _compile_naming_profile  # noqa: E402


class TestCompileNamingProfile:
    def _standard_profile(self) -> dict:
        return {
            "separator": "_",
            "max_length": 50,
            "fields": [
                {"key": "invoice_date", "label": "Datum", "enabled": True},
                {"key": "literal_er", "label": "er", "enabled": True},
                {"key": "art", "label": "Kategorie", "enabled": True},
                {"key": "supplier", "label": "Lieferant", "enabled": True},
                {"key": "amount", "label": "Betrag", "enabled": True},
                {"key": "payment_field", "label": "Zahlung", "enabled": True},
            ],
        }

    def test_separator_and_max_laenge(self):
        result = _compile_naming_profile({"separator": "-", "max_length": 80, "fields": []})
        assert result["separator"] == "-"
        assert result["max_laenge"] == 80

    def test_erweiterung_always_pdf(self):
        result = _compile_naming_profile({})
        assert result["erweiterung"] == ".pdf"

    def test_invoice_date_field(self):
        result = _compile_naming_profile({"fields": [{"key": "invoice_date", "enabled": True}]})
        f = result["felder"][0]
        assert f["typ"] == "datum"
        assert f["quelle"] == "invoice_date"
        assert f["format"] == "jjmmtt"
        assert f["aktiv"] is True

    def test_literal_field(self):
        result = _compile_naming_profile({"fields": [{"key": "literal_er", "enabled": True}]})
        f = result["felder"][0]
        assert f["typ"] == "literal"
        assert f["wert"] == "er"
        assert f["aktiv"] is True

    def test_literal_field_disabled(self):
        result = _compile_naming_profile({"fields": [{"key": "literal_er", "enabled": False}]})
        assert result["felder"][0]["aktiv"] is False

    def test_wert_field(self):
        result = _compile_naming_profile({"fields": [{"key": "supplier", "enabled": True}]})
        f = result["felder"][0]
        assert f["typ"] == "wert"
        assert f["quelle"] == "supplier"

    def test_full_standard_profile_produces_six_fields(self):
        result = _compile_naming_profile(self._standard_profile())
        assert len(result["felder"]) == 6

    def test_empty_fields_list(self):
        result = _compile_naming_profile({"fields": []})
        assert result["felder"] == []

    def test_empty_profile_uses_defaults(self):
        result = _compile_naming_profile({})
        assert result["separator"] == "_"
        assert result["max_laenge"] == 50

    def test_field_with_empty_key_is_skipped(self):
        result = _compile_naming_profile({"fields": [{"key": "", "enabled": True}, {"key": "art", "enabled": True}]})
        assert len(result["felder"]) == 1
        assert result["felder"][0]["quelle"] == "art"


class TestNamingProfileMerge:
    """Test that naming_profile flows through compile_profile_to_rules and merge_rules_dicts."""

    def _base_rules(self, preset: str = "office_default") -> dict:
        return {
            "active_preset": preset,
            "presets": {
                preset: {
                    "dateiname_schema": {
                        "separator": "_", "max_laenge": 50, "erweiterung": ".pdf", "felder": []
                    },
                    "routing": {},
                    "classification": {},
                }
            },
        }

    def test_naming_profile_appears_in_generated_preset(self):
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {
            "naming_profile": {
                "separator": "-",
                "max_length": 40,
                "fields": [{"key": "art", "enabled": True}],
            }
        }
        generated = compile_profile_to_rules(profile, preset_name="office_default")
        preset = generated["presets"]["office_default"]
        assert "dateiname_schema" in preset
        assert preset["dateiname_schema"]["separator"] == "-"
        assert preset["dateiname_schema"]["max_laenge"] == 40

    def test_merge_replaces_dateiname_schema(self):
        from invoice_tool.config import merge_rules_dicts
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {
            "naming_profile": {
                "separator": "-",
                "max_length": 40,
                "fields": [{"key": "art", "enabled": True}],
            }
        }
        base = self._base_rules()
        patch = compile_profile_to_rules(profile, preset_name="office_default")
        merged = merge_rules_dicts(base, patch)
        schema = merged["presets"]["office_default"]["dateiname_schema"]
        assert schema["separator"] == "-"
        assert schema["max_laenge"] == 40

    def test_no_naming_profile_leaves_schema_unchanged(self):
        from invoice_tool.config import merge_rules_dicts
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {}  # no naming_profile
        base = self._base_rules()
        original_schema = base["presets"]["office_default"]["dateiname_schema"].copy()
        patch = compile_profile_to_rules(profile, preset_name="office_default")
        merged = merge_rules_dicts(base, patch)
        assert merged["presets"]["office_default"]["dateiname_schema"] == original_schema


# ---------------------------------------------------------------------------
# review_policy compiler tests
# ---------------------------------------------------------------------------

class TestCompileReviewPolicy:
    """Unit tests for _compile_review_policy."""

    def test_unclear_folder_maps_to_routing_overrides(self):
        from invoice_tool.profile_compiler import _compile_review_policy
        result = _compile_review_policy({"unclear_folder": "unklar"})
        assert result["unklar_konto"] == "unklar"
        assert result["default_zielordner"] == "unklar"

    def test_custom_unclear_folder(self):
        from invoice_tool.profile_compiler import _compile_review_policy
        result = _compile_review_policy({"unclear_folder": "zu_pruefen"})
        assert result["unklar_konto"] == "zu_pruefen"
        assert result["default_zielordner"] == "zu_pruefen"

    def test_missing_unclear_folder_defaults_to_unklar(self):
        from invoice_tool.profile_compiler import _compile_review_policy
        result = _compile_review_policy({})
        assert result["unklar_konto"] == "unklar"
        assert result["default_zielordner"] == "unklar"

    def test_empty_string_unclear_folder_defaults_to_unklar(self):
        from invoice_tool.profile_compiler import _compile_review_policy
        result = _compile_review_policy({"unclear_folder": ""})
        assert result["unklar_konto"] == "unklar"
        assert result["default_zielordner"] == "unklar"

    def test_whitespace_only_defaults_to_unklar(self):
        from invoice_tool.profile_compiler import _compile_review_policy
        result = _compile_review_policy({"unclear_folder": "   "})
        assert result["unklar_konto"] == "unklar"
        assert result["default_zielordner"] == "unklar"

    def test_only_two_keys_in_result(self):
        from invoice_tool.profile_compiler import _compile_review_policy
        result = _compile_review_policy({"unclear_folder": "unklar", "review_flags_enabled": True})
        assert set(result.keys()) == {"unklar_konto", "default_zielordner"}


class TestReviewPolicyMerge:
    """Test that review_policy flows through compile_profile_to_rules and merge_rules_dicts."""

    def _base_rules(self, preset: str = "office_default") -> dict:
        return {
            "active_preset": preset,
            "presets": {
                preset: {
                    "dateiname_schema": {
                        "separator": "_", "max_laenge": 50, "erweiterung": ".pdf", "felder": []
                    },
                    "routing": {
                        "unklar_konto": "unklar",
                        "default_zielordner": "unklar",
                        "default_art": "private",
                    },
                    "classification": {},
                }
            },
        }

    def test_review_policy_appears_in_generated_preset(self):
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {"review_policy": {"unclear_folder": "unklar"}}
        generated = compile_profile_to_rules(profile, preset_name="office_default")
        preset = generated["presets"]["office_default"]
        assert "routing_overrides" in preset
        assert preset["routing_overrides"]["unklar_konto"] == "unklar"

    def test_merge_applies_routing_overrides_to_routing(self):
        from invoice_tool.config import merge_rules_dicts
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {"review_policy": {"unclear_folder": "zu_pruefen"}}
        base = self._base_rules()
        patch = compile_profile_to_rules(profile, preset_name="office_default")
        merged = merge_rules_dicts(base, patch)
        routing = merged["presets"]["office_default"]["routing"]
        assert routing["unklar_konto"] == "zu_pruefen"
        assert routing["default_zielordner"] == "zu_pruefen"

    def test_merge_keeps_routing_overrides_for_traceability(self):
        from invoice_tool.config import merge_rules_dicts
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {"review_policy": {"unclear_folder": "zu_pruefen"}}
        base = self._base_rules()
        patch = compile_profile_to_rules(profile, preset_name="office_default")
        merged = merge_rules_dicts(base, patch)
        preset = merged["presets"]["office_default"]
        assert "routing_overrides" in preset
        assert preset["routing_overrides"]["unklar_konto"] == "zu_pruefen"

    def test_merge_does_not_override_nonexistent_routing_keys(self):
        from invoice_tool.config import merge_rules_dicts
        from invoice_tool.profile_compiler import compile_profile_to_rules
        # default_art is in base routing; a hypothetical unknown key should NOT be injected
        profile = {"review_policy": {"unclear_folder": "unklar"}}
        base = self._base_rules()
        patch = compile_profile_to_rules(profile, preset_name="office_default")
        # Manually add a nonexistent key to routing_overrides to test the guard
        patch["presets"]["office_default"]["routing_overrides"]["nonexistent_key"] = "x"
        merged = merge_rules_dicts(base, patch)
        routing = merged["presets"]["office_default"]["routing"]
        assert "nonexistent_key" not in routing

    def test_no_review_policy_leaves_routing_keys_unchanged(self):
        from invoice_tool.config import merge_rules_dicts
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {}
        base = self._base_rules()
        patch = compile_profile_to_rules(profile, preset_name="office_default")
        merged = merge_rules_dicts(base, patch)
        routing = merged["presets"]["office_default"]["routing"]
        # The review_policy-controlled keys must remain at their base values
        assert routing["unklar_konto"] == "unklar"
        assert routing["default_zielordner"] == "unklar"
        assert "routing_overrides" not in merged["presets"]["office_default"]


# ---------------------------------------------------------------------------
# payment_profiles compiler tests
# ---------------------------------------------------------------------------

class TestCompilePaymentProfiles:
    """Unit tests for _compile_payment_profiles."""

    def test_single_profile_maps_to_rule(self):
        from invoice_tool.profile_compiler import _compile_payment_profiles
        result = _compile_payment_profiles([{
            "id": "twint",
            "label": "Twint",
            "keywords": ["twint"],
            "payment_method": "card",
            "is_explicit": True,
            "enabled": True,
        }])
        assert len(result) == 1
        r = result[0]
        assert r["name"] == "twint"
        assert r["text_any"] == ["twint"]
        assert r["payment_method"] == "card"
        assert r["explicit"] is True
        assert r["text_all"] == []

    def test_is_explicit_false(self):
        from invoice_tool.profile_compiler import _compile_payment_profiles
        result = _compile_payment_profiles([{
            "id": "hint-only",
            "label": "Hinweis",
            "keywords": ["rechnungszahlung"],
            "payment_method": "transfer",
            "is_explicit": False,
        }])
        assert result[0]["explicit"] is False

    def test_is_explicit_defaults_to_true(self):
        from invoice_tool.profile_compiler import _compile_payment_profiles
        result = _compile_payment_profiles([{"id": "x", "label": "X", "keywords": ["foo"], "payment_method": "bar"}])
        assert result[0]["explicit"] is True

    def test_disabled_profile_skipped(self):
        from invoice_tool.profile_compiler import _compile_payment_profiles
        result = _compile_payment_profiles([{
            "id": "off", "label": "Off", "keywords": ["foo"], "payment_method": "bar", "enabled": False,
        }])
        assert result == []

    def test_no_keywords_skipped(self):
        from invoice_tool.profile_compiler import _compile_payment_profiles
        result = _compile_payment_profiles([{"id": "empty", "label": "Empty", "keywords": [], "payment_method": "bar"}])
        assert result == []

    def test_missing_keywords_skipped(self):
        from invoice_tool.profile_compiler import _compile_payment_profiles
        result = _compile_payment_profiles([{"id": "nok", "label": "NoK", "payment_method": "bar"}])
        assert result == []

    def test_empty_id_skipped(self):
        from invoice_tool.profile_compiler import _compile_payment_profiles
        result = _compile_payment_profiles([{"id": "", "label": "X", "keywords": ["foo"], "payment_method": "bar"}])
        assert result == []

    def test_multiple_keywords(self):
        from invoice_tool.profile_compiler import _compile_payment_profiles
        result = _compile_payment_profiles([{
            "id": "multi", "label": "M", "keywords": ["word1", "word2", "word3"], "payment_method": "card",
        }])
        assert result[0]["text_any"] == ["word1", "word2", "word3"]

    def test_empty_list_returns_empty(self):
        from invoice_tool.profile_compiler import _compile_payment_profiles
        assert _compile_payment_profiles([]) == []


class TestPaymentProfilesMerge:
    """Test that payment_profiles combines with vendor_profiles and merges via PREPEND."""

    def _base_rules(self, preset: str = "office_default") -> dict:
        return {
            "active_preset": preset,
            "presets": {
                preset: {
                    "dateiname_schema": {
                        "separator": "_", "max_laenge": 50, "erweiterung": ".pdf", "felder": []
                    },
                    "routing": {
                        "payment_detection_rules": [{"name": "base-rule", "text_any": ["base"], "payment_method": "transfer", "explicit": True}],
                    },
                    "classification": {},
                }
            },
        }

    def test_payment_profiles_appears_in_generated_routing(self):
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {"payment_profiles": [
            {"id": "my-method", "label": "My", "keywords": ["mypay"], "payment_method": "card"},
        ]}
        generated = compile_profile_to_rules(profile, preset_name="office_default")
        routing = generated["presets"]["office_default"]["routing"]
        assert "payment_detection_rules" in routing
        assert routing["payment_detection_rules"][0]["name"] == "my-method"

    def test_payment_profiles_prepended_before_base_rules(self):
        from invoice_tool.config import merge_rules_dicts
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {"payment_profiles": [
            {"id": "my-method", "label": "My", "keywords": ["mypay"], "payment_method": "card"},
        ]}
        base = self._base_rules()
        patch = compile_profile_to_rules(profile, preset_name="office_default")
        merged = merge_rules_dicts(base, patch)
        rules = merged["presets"]["office_default"]["routing"]["payment_detection_rules"]
        names = [r["name"] for r in rules]
        assert names[0] == "my-method"
        assert "base-rule" in names

    def test_vendor_profiles_before_payment_profiles(self):
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {
            "vendor_profiles": [
                {"id": "vendor-rule", "recognition_hints": ["vendortext"], "payment_field": "amex"},
            ],
            "payment_profiles": [
                {"id": "generic-rule", "label": "G", "keywords": ["generictext"], "payment_method": "card"},
            ],
        }
        generated = compile_profile_to_rules(profile, preset_name="office_default")
        rules = generated["presets"]["office_default"]["routing"]["payment_detection_rules"]
        names = [r["name"] for r in rules]
        assert names.index("vendor-rule") < names.index("generic-rule")

    def test_null_payment_profiles_produces_no_rules(self):
        from invoice_tool.profile_compiler import compile_profile_to_rules
        profile = {"payment_profiles": None}
        generated = compile_profile_to_rules(profile, preset_name="office_default")
        routing = generated["presets"]["office_default"]["routing"]
        assert "payment_detection_rules" not in routing
