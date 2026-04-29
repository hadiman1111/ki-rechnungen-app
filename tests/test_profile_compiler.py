"""Tests for invoice_tool/profile_compiler.py – Profile Compiler MVP.

Covers: address_profiles → routing.strassen + routing.prioritaetsregeln.
All other profile sections are outside the MVP scope and are not tested here.
"""
from __future__ import annotations

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
