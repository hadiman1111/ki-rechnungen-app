"""Tests for Runtime Rules: merge_rules_dicts, load_office_rules_from_dict,
and run_once integration.

All tests use tmp_path and synthetic data.
No real invoice PDFs, no OpenAI calls, no network access.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest

from invoice_tool.config import (
    ConfigError,
    load_office_rules_from_dict,
    merge_rules_dicts,
)


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

def _minimal_rules_dict(active_preset: str = "office_default") -> dict:
    """Return the smallest valid rules dict loadable by load_office_rules_from_dict."""
    from invoice_tool.config import load_office_rules
    # Use actual office_rules.json as the base – it is always valid.
    actual_path = Path("office_rules.json").resolve()
    raw = json.loads(actual_path.read_text(encoding="utf-8"))
    return raw


def _strassen_a() -> list[dict]:
    return [{"key": "alpha", "art": "ai", "varianten": ["alphastrasse"], "fuzzy_threshold": 0.84}]


def _strassen_b() -> list[dict]:
    return [{"key": "beta", "art": "private", "varianten": ["betaweg"], "fuzzy_threshold": 0.84}]


def _prioritaetsregeln_a() -> list[dict]:
    return [{"name": "rule-a", "street_any": ["alpha"], "text_none_any": ["x"],
             "text_all": [], "text_any": [], "provider_any": [],
             "require_no_clear_payment": False, "zielordner": "private",
             "art": "private", "status": "processed"}]


def _prioritaetsregeln_b() -> list[dict]:
    return [{"name": "rule-b", "street_any": ["beta"], "text_none_any": [],
             "text_all": [], "text_any": [], "provider_any": [],
             "require_no_clear_payment": False, "zielordner": "ai",
             "art": "ai", "status": "processed"}]


def _make_patch(strassen=None, prioritaetsregeln=None, preset="office_default") -> dict:
    routing: dict = {}
    if strassen is not None:
        routing["strassen"] = strassen
    if prioritaetsregeln is not None:
        routing["prioritaetsregeln"] = prioritaetsregeln
    return {"active_preset": preset, "presets": {preset: {"routing": routing}}}


def _make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Test")
    doc.save(str(path))
    doc.close()


def _make_run_config_path(tmp_path: Path) -> Path:
    """Minimal invoice_config.json pointing at actual office_rules.json."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    rules_path = Path("office_rules.json").resolve()
    config = {
        "eingangsordner": str(input_dir),
        "ausgangsordner": str(tmp_path / "output"),
        "api_key_pfad": "$HOME/Library/Application Support/KI-Rechnungen-Umbenennen/.env",
        "archiv_aktiv": True,
        "regeln_datei": str(rules_path),
        "aktives_preset": "office_default",
        "runtime_ordner": str(tmp_path / "runtime"),
        "log_ordner": str(tmp_path / "logs"),
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def _make_minimal_profile(tmp_path: Path) -> Path:
    """Profile with one address profile → generates strassen + prioritaetsregeln."""
    profile = {
        "schema_version": "1.0",
        "profile_name": "Test",
        "categories": [{"id": "ai", "label": "AI"}],
        "folders": [{"id": "ai", "label": "AI", "folder_name": "ai"}],
        "account_card_profiles": [],
        "address_profiles": [
            {
                "id": "test-bismarck",
                "label": "Test Street",
                "category": "ai",
                "canonical_address": {"street": "Bismarckstraße"},
                "matching_mode": "normal",
                "advanced_variants": [],
                "enabled": True,
            }
        ],
        "naming_profile": {
            "separator": "_", "max_length": 50, "fields": [], "fallback_values": {}
        },
        "review_policy": {
            "unclear_folder": "unklar",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# A. merge_rules_dicts: replaces strassen
# ---------------------------------------------------------------------------


def test_merge_rules_dicts_replaces_strassen() -> None:
    base = _minimal_rules_dict()
    base["presets"]["office_default"]["routing"]["strassen"] = _strassen_a()

    patch = _make_patch(strassen=_strassen_b())
    merged = merge_rules_dicts(base, patch)

    result_strassen = merged["presets"]["office_default"]["routing"]["strassen"]
    assert result_strassen == _strassen_b()
    assert result_strassen != _strassen_a()


def test_merge_rules_dicts_without_strassen_keeps_base() -> None:
    base = _minimal_rules_dict()
    base["presets"]["office_default"]["routing"]["strassen"] = _strassen_a()

    patch = _make_patch()  # no strassen key
    merged = merge_rules_dicts(base, patch)

    assert merged["presets"]["office_default"]["routing"]["strassen"] == _strassen_a()


# ---------------------------------------------------------------------------
# B. merge_rules_dicts: replaces prioritaetsregeln
# ---------------------------------------------------------------------------


def test_merge_rules_dicts_replaces_prioritaetsregeln() -> None:
    base = _minimal_rules_dict()
    base["presets"]["office_default"]["routing"]["prioritaetsregeln"] = _prioritaetsregeln_a()

    patch = _make_patch(prioritaetsregeln=_prioritaetsregeln_b())
    merged = merge_rules_dicts(base, patch)

    result = merged["presets"]["office_default"]["routing"]["prioritaetsregeln"]
    assert result == _prioritaetsregeln_b()


# ---------------------------------------------------------------------------
# C. merge_rules_dicts: protected sections stay unchanged
# ---------------------------------------------------------------------------


def test_merge_rules_dicts_preserves_konten() -> None:
    base = _minimal_rules_dict()
    original_konten = copy.deepcopy(base["presets"]["office_default"]["routing"]["konten"])
    patch = _make_patch(strassen=_strassen_b(), prioritaetsregeln=_prioritaetsregeln_b())

    merged = merge_rules_dicts(base, patch)

    assert merged["presets"]["office_default"]["routing"]["konten"] == original_konten


def test_merge_rules_dicts_preserves_business_context_rules() -> None:
    base = _minimal_rules_dict()
    orig = copy.deepcopy(base["presets"]["office_default"]["routing"]["business_context_rules"])
    patch = _make_patch(strassen=_strassen_b())
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["routing"]["business_context_rules"] == orig


def test_merge_rules_dicts_preserves_payment_detection_rules() -> None:
    base = _minimal_rules_dict()
    orig = copy.deepcopy(base["presets"]["office_default"]["routing"]["payment_detection_rules"])
    patch = _make_patch(strassen=_strassen_b())
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["routing"]["payment_detection_rules"] == orig


def test_merge_rules_dicts_preserves_final_assignment_rules() -> None:
    base = _minimal_rules_dict()
    orig = copy.deepcopy(base["presets"]["office_default"]["routing"]["final_assignment_rules"])
    patch = _make_patch(strassen=_strassen_b())
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["routing"]["final_assignment_rules"] == orig


def test_merge_rules_dicts_preserves_output_route_rules() -> None:
    base = _minimal_rules_dict()
    orig = copy.deepcopy(base["presets"]["office_default"]["routing"]["output_route_rules"])
    patch = _make_patch(strassen=_strassen_b())
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["routing"]["output_route_rules"] == orig


def test_merge_rules_dicts_preserves_classification() -> None:
    base = _minimal_rules_dict()
    orig = copy.deepcopy(base["presets"]["office_default"]["classification"])
    patch = _make_patch(strassen=_strassen_b())
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["classification"] == orig


def test_merge_rules_dicts_preserves_supplier_cleaning() -> None:
    base = _minimal_rules_dict()
    orig = copy.deepcopy(base["presets"]["office_default"]["supplier_cleaning"])
    patch = _make_patch(strassen=_strassen_b())
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["supplier_cleaning"] == orig


# ---------------------------------------------------------------------------
# D. merge_rules_dicts: does not mutate base
# ---------------------------------------------------------------------------


def test_merge_rules_dicts_does_not_mutate_base() -> None:
    base = _minimal_rules_dict()
    base["presets"]["office_default"]["routing"]["strassen"] = _strassen_a()
    original_base = copy.deepcopy(base)

    patch = _make_patch(strassen=_strassen_b())
    _ = merge_rules_dicts(base, patch)

    assert base == original_base


def test_merge_rules_dicts_patch_not_mutated() -> None:
    base = _minimal_rules_dict()
    patch = _make_patch(strassen=_strassen_b())
    original_patch = copy.deepcopy(patch)

    _ = merge_rules_dicts(base, patch)

    assert patch == original_patch


# ---------------------------------------------------------------------------
# E. load_office_rules_from_dict: produces valid OfficeRules
# ---------------------------------------------------------------------------


def test_load_office_rules_from_dict_produces_valid_office_rules() -> None:
    from invoice_tool.models import OfficeRules

    rules_dict = _minimal_rules_dict()
    base_dir = Path("office_rules.json").resolve().parent
    result = load_office_rules_from_dict(rules_dict, base_dir)

    assert isinstance(result, OfficeRules)
    assert result.active_preset == "office_default"
    assert "office_default" in result.presets


def test_load_office_rules_from_dict_active_preset_override() -> None:
    rules_dict = _minimal_rules_dict()
    base_dir = Path("office_rules.json").resolve().parent
    result = load_office_rules_from_dict(rules_dict, base_dir, active_preset_override="office_default")
    assert result.active_preset == "office_default"


def test_load_office_rules_from_dict_ignores_meta_key() -> None:
    """_meta in the top-level dict must not cause a parse error."""
    from invoice_tool.models import OfficeRules

    rules_dict = _minimal_rules_dict()
    rules_dict["_meta"] = {"profile_applied": True, "generated_sections": ["routing.strassen"]}
    base_dir = Path("office_rules.json").resolve().parent
    result = load_office_rules_from_dict(rules_dict, base_dir)
    assert isinstance(result, OfficeRules)


def test_load_office_rules_from_dict_invalid_raises() -> None:
    base_dir = Path("office_rules.json").resolve().parent
    with pytest.raises(ConfigError):
        load_office_rules_from_dict({}, base_dir)


def test_load_office_rules_from_dict_merged_strassen_is_used() -> None:
    """After replacing strassen via merge, load_office_rules_from_dict must
    produce OfficeRules with the new street key."""
    rules_dict = _minimal_rules_dict()
    # Replace strassen with a single known key
    rules_dict["presets"]["office_default"]["routing"]["strassen"] = [
        {"key": "teststreet", "art": "ai", "varianten": ["teststreet"], "fuzzy_threshold": 0.84}
    ]
    base_dir = Path("office_rules.json").resolve().parent
    result = load_office_rules_from_dict(rules_dict, base_dir)

    street_keys = [s.key for s in result.preset.routing.strassen]
    assert "teststreet" in street_keys


# ---------------------------------------------------------------------------
# F. run_once with profile: writes profile_snapshot and runtime_rules
# ---------------------------------------------------------------------------


def test_run_once_with_profile_writes_profile_snapshot_and_runtime_rules(tmp_path: Path) -> None:
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)
    profile_path = _make_minimal_profile(tmp_path)

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "test.pdf")

    with patch("invoice_tool.run.InvoiceProcessor") as mock_cls:
        mock_cls.return_value.process_all.return_value = []
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_dir = run_once(
                        source=source,
                        output=tmp_path / "runs",
                        config_path=config_path,
                        profile_path=profile_path,
                    )

    assert (run_dir / "profile_snapshot.json").exists(), "profile_snapshot.json must exist"
    assert (run_dir / "runtime_rules.json").exists(), "runtime_rules.json must exist"

    runtime = json.loads((run_dir / "runtime_rules.json").read_text())
    assert "_meta" in runtime
    assert runtime["_meta"]["profile_applied"] is True
    assert "routing.strassen" in runtime["_meta"]["generated_sections"]


# ---------------------------------------------------------------------------
# G. run_once with profile: generated strassen applied to InvoiceProcessor
# ---------------------------------------------------------------------------


def test_run_once_with_profile_applies_generated_strassen(tmp_path: Path) -> None:
    """The InvoiceProcessor must receive OfficeRules containing strassen
    derived from the profile, not the base rules."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)
    profile_path = _make_minimal_profile(tmp_path)

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "test.pdf")

    received_rules = {}

    def capture_processor(config, extractor, *, office_rules):
        received_rules["rules"] = office_rules
        mock = type("M", (), {"process_all": lambda self: []})()
        return mock

    with patch("invoice_tool.run.InvoiceProcessor", side_effect=capture_processor):
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_once(
                        source=source,
                        output=tmp_path / "runs",
                        config_path=config_path,
                        profile_path=profile_path,
                    )

    office_rules = received_rules.get("rules")
    assert office_rules is not None
    street_keys = [s.key for s in office_rules.preset.routing.strassen]
    # Profile defines "Bismarckstraße" → key "bismarck"
    assert "bismarck" in street_keys, (
        f"Expected 'bismarck' in strassen from profile, got: {street_keys}"
    )


# ---------------------------------------------------------------------------
# H. run_once without profile: base behavior unchanged
# ---------------------------------------------------------------------------


def test_run_once_without_profile_preserves_existing_behavior(tmp_path: Path) -> None:
    """Without profile_path, run_once must use base rules and NOT write
    runtime_rules.json."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "test.pdf")

    with patch("invoice_tool.run.InvoiceProcessor") as mock_cls:
        mock_cls.return_value.process_all.return_value = []
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_dir = run_once(
                        source=source,
                        output=tmp_path / "runs",
                        config_path=config_path,
                    )

    assert not (run_dir / "runtime_rules.json").exists(), (
        "runtime_rules.json must NOT be written when no profile is provided"
    )
    assert not (run_dir / "profile_snapshot.json").exists()


# ---------------------------------------------------------------------------
# E. merge_rules_dicts: replaces konten
# ---------------------------------------------------------------------------


def _konten_a() -> list[dict]:
    return [{"name": "bank-a", "konto": "banka", "payment_field": "banka",
             "art_override": "ai", "karten_endungen": ["1111"],
             "apple_pay_endungen": [], "iban_endungen": ["1234"],
             "anbieter_hinweise": ["bank a"], "zuweisungs_hinweise": []}]


def _konten_b() -> list[dict]:
    return [{"name": "bank-b", "konto": "bankb", "payment_field": "bankb",
             "art_override": "ep", "karten_endungen": ["2222"],
             "apple_pay_endungen": [], "iban_endungen": [],
             "anbieter_hinweise": [], "zuweisungs_hinweise": []}]


def test_merge_rules_dicts_replaces_konten() -> None:
    base = _minimal_rules_dict()
    base["presets"]["office_default"]["routing"]["konten"] = _konten_a()

    patch = {"active_preset": "office_default", "presets": {
        "office_default": {"routing": {"konten": _konten_b()}}
    }}
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["routing"]["konten"] == _konten_b()


def test_merge_rules_dicts_without_konten_keeps_base() -> None:
    base = _minimal_rules_dict()
    base["presets"]["office_default"]["routing"]["konten"] = _konten_a()

    patch = {"active_preset": "office_default", "presets": {
        "office_default": {"routing": {}}  # no konten key
    }}
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["routing"]["konten"] == _konten_a()


# ---------------------------------------------------------------------------
# F. Protected sections remain unchanged when konten is replaced
# ---------------------------------------------------------------------------


def test_merge_rules_dicts_preserves_other_sections_when_konten_replaced() -> None:
    base = _minimal_rules_dict()
    orig_bc = copy.deepcopy(base["presets"]["office_default"]["routing"]["business_context_rules"])
    orig_fa = copy.deepcopy(base["presets"]["office_default"]["routing"]["final_assignment_rules"])
    orig_or = copy.deepcopy(base["presets"]["office_default"]["routing"]["output_route_rules"])

    patch = {"active_preset": "office_default", "presets": {
        "office_default": {"routing": {"konten": _konten_b()}}
    }}
    merged = merge_rules_dicts(base, patch)

    assert merged["presets"]["office_default"]["routing"]["business_context_rules"] == orig_bc
    assert merged["presets"]["office_default"]["routing"]["final_assignment_rules"] == orig_fa
    assert merged["presets"]["office_default"]["routing"]["output_route_rules"] == orig_or


# ---------------------------------------------------------------------------
# G. run_once with profile applies generated konten
# ---------------------------------------------------------------------------


def test_run_once_with_profile_applies_generated_konten(tmp_path: Path) -> None:
    """InvoiceProcessor must receive OfficeRules with konten derived from profile."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)

    # Build a profile with one distinct account_card_profile
    profile_data = {
        "schema_version": "1.0",
        "profile_name": "Test Konten",
        "categories": [{"id": "ai", "label": "AI"}],
        "folders": [{"id": "ai", "label": "AI", "folder_name": "ai"}],
        "account_card_profiles": [
            {
                "id": "unique-test-konto",
                "label": "Unique Test",
                "category": "ai",
                "payment_field": "unique-test",
                "card_endings": ["9876"],
                "apple_pay_endings": [],
                "iban_endings": [],
                "provider_hints": [],
                "assignment_hints": [],
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
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile_data), encoding="utf-8")

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "test.pdf")

    received = {}

    def capture(config, extractor, *, office_rules):
        received["rules"] = office_rules
        return type("M", (), {"process_all": lambda self: []})()

    with patch("invoice_tool.run.InvoiceProcessor", side_effect=capture):
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_once(
                        source=source,
                        output=tmp_path / "runs",
                        config_path=config_path,
                        profile_path=profile_path,
                    )

    office_rules = received.get("rules")
    assert office_rules is not None
    konto_names = [k.name for k in office_rules.preset.routing.konten]
    assert "unique-test-konto" in konto_names, (
        f"Expected 'unique-test-konto' in konten, got: {konto_names}"
    )


# ---------------------------------------------------------------------------
# H. runtime_rules _meta reflects routing.konten as generated section
# ---------------------------------------------------------------------------


def test_runtime_rules_meta_includes_konten_generated_section(tmp_path: Path) -> None:
    """When profile has account_card_profiles, runtime_rules._meta.generated_sections
    must include 'routing.konten' and protected_sections must NOT include it."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)
    profile_path = _make_minimal_profile(tmp_path)

    # Ensure profile has account_card_profiles (it's in the example profile)
    import json
    profile_data = json.loads(profile_path.read_text())
    profile_data["account_card_profiles"] = [
        {
            "id": "test-konto",
            "label": "Test",
            "category": "ai",
            "payment_field": "testkonto",
            "card_endings": [],
            "apple_pay_endings": [],
            "iban_endings": [],
            "provider_hints": [],
            "assignment_hints": [],
            "enabled": True,
        }
    ]
    profile_path.write_text(json.dumps(profile_data), encoding="utf-8")

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "test.pdf")

    with patch("invoice_tool.run.InvoiceProcessor") as mock_cls:
        mock_cls.return_value.process_all.return_value = []
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_dir = run_once(
                        source=source,
                        output=tmp_path / "runs",
                        config_path=config_path,
                        profile_path=profile_path,
                    )

    runtime = json.loads((run_dir / "runtime_rules.json").read_text())
    meta = runtime.get("_meta", {})
    generated = meta.get("generated_sections", [])
    protected = meta.get("protected_sections", [])

    assert "routing.konten" in generated, (
        f"routing.konten must be in generated_sections when profile has konten. Got: {generated}"
    )
    assert "routing.konten" not in protected, (
        f"routing.konten must NOT be in protected_sections when generated. Got: {protected}"
    )


def _bc_rule_a() -> list[dict]:
    return [{"name": "ctx-a", "text_all": ["x"], "text_any": ["y"], "art": "ai", "match_source": "enriched_text"}]


def _bc_rule_b() -> list[dict]:
    return [{"name": "ctx-b", "text_all": [], "text_any": ["z"], "art": "ep", "match_source": "raw_text"}]


# ---------------------------------------------------------------------------
# F. merge_rules_dicts: replaces business_context_rules
# ---------------------------------------------------------------------------


def test_merge_rules_dicts_replaces_business_context_rules() -> None:
    base = _minimal_rules_dict()
    base["presets"]["office_default"]["routing"]["business_context_rules"] = _bc_rule_a()
    patch = {"active_preset": "office_default", "presets": {
        "office_default": {"routing": {"business_context_rules": _bc_rule_b()}}
    }}
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["routing"]["business_context_rules"] == _bc_rule_b()


def test_merge_rules_dicts_without_bc_rules_keeps_base() -> None:
    base = _minimal_rules_dict()
    base["presets"]["office_default"]["routing"]["business_context_rules"] = _bc_rule_a()
    patch = {"active_preset": "office_default", "presets": {
        "office_default": {"routing": {}}
    }}
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["routing"]["business_context_rules"] == _bc_rule_a()


# ---------------------------------------------------------------------------
# G. Protected sections unchanged when bc_rules replaced
# ---------------------------------------------------------------------------


def test_merge_rules_dicts_preserves_other_sections_when_bc_rules_replaced() -> None:
    base = _minimal_rules_dict()
    orig_fa = copy.deepcopy(base["presets"]["office_default"]["routing"]["final_assignment_rules"])
    orig_or = copy.deepcopy(base["presets"]["office_default"]["routing"]["output_route_rules"])
    orig_pd = copy.deepcopy(base["presets"]["office_default"]["routing"]["payment_detection_rules"])
    orig_cl = copy.deepcopy(base["presets"]["office_default"]["classification"])
    orig_sc = copy.deepcopy(base["presets"]["office_default"]["supplier_cleaning"])

    patch = {"active_preset": "office_default", "presets": {
        "office_default": {"routing": {"business_context_rules": _bc_rule_b()}}
    }}
    merged = merge_rules_dicts(base, patch)

    assert merged["presets"]["office_default"]["routing"]["final_assignment_rules"] == orig_fa
    assert merged["presets"]["office_default"]["routing"]["output_route_rules"] == orig_or
    assert merged["presets"]["office_default"]["routing"]["payment_detection_rules"] == orig_pd
    assert merged["presets"]["office_default"]["classification"] == orig_cl
    assert merged["presets"]["office_default"]["supplier_cleaning"] == orig_sc


# ---------------------------------------------------------------------------
# H. run_once with profile applies generated business_context_rules
# ---------------------------------------------------------------------------


def test_run_once_with_profile_applies_generated_business_context_rules(tmp_path: Path) -> None:
    """InvoiceProcessor must receive OfficeRules with business_context_rules from profile."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)

    profile_data = {
        "schema_version": "1.0",
        "profile_name": "Test BC",
        "categories": [{"id": "ai", "label": "AI"}],
        "folders": [{"id": "ai", "label": "AI", "folder_name": "ai"}],
        "account_card_profiles": [],
        "address_profiles": [],
        "business_context_profiles": [
            {
                "id": "unique-test-ctx",
                "label": "Unique Test Context",
                "required_keywords": ["unique-firm"],
                "optional_keywords": ["unique-keyword"],
                "category": "ai",
                "match_source": "raw_text",
                "enabled": True,
            }
        ],
        "naming_profile": {"separator": "_", "max_length": 50, "fields": [], "fallback_values": {}},
        "review_policy": {
            "unclear_folder": "unklar",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile_data), encoding="utf-8")

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "test.pdf")

    received = {}

    def capture(config, extractor, *, office_rules):
        received["rules"] = office_rules
        return type("M", (), {"process_all": lambda self: []})()

    with patch("invoice_tool.run.InvoiceProcessor", side_effect=capture):
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_once(
                        source=source,
                        output=tmp_path / "runs",
                        config_path=config_path,
                        profile_path=profile_path,
                    )

    office_rules = received.get("rules")
    assert office_rules is not None
    bc_names = [bc.name for bc in office_rules.preset.routing.business_context_rules]
    assert "unique-test-ctx" in bc_names, (
        f"Expected 'unique-test-ctx' in business_context_rules, got: {bc_names}"
    )


# ---------------------------------------------------------------------------
# I. runtime_rules _meta includes business_context_rules as generated section
# ---------------------------------------------------------------------------


def test_runtime_rules_meta_includes_business_context_generated_section(tmp_path: Path) -> None:
    """When profile has business_context_profiles, runtime_rules._meta.generated_sections
    must include 'routing.business_context_rules' and protected_sections must NOT."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)

    profile_data = {
        "schema_version": "1.0",
        "profile_name": "Test BC Meta",
        "categories": [],
        "folders": [],
        "account_card_profiles": [],
        "address_profiles": [],
        "business_context_profiles": [
            {
                "id": "meta-test-ctx",
                "label": "Meta Test",
                "required_keywords": [],
                "optional_keywords": ["meta-keyword"],
                "category": "ai",
                "enabled": True,
            }
        ],
        "naming_profile": {"separator": "_", "max_length": 50, "fields": [], "fallback_values": {}},
        "review_policy": {
            "unclear_folder": "unklar",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile_data), encoding="utf-8")

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "test.pdf")

    with patch("invoice_tool.run.InvoiceProcessor") as mock_cls:
        mock_cls.return_value.process_all.return_value = []
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_dir = run_once(
                        source=source,
                        output=tmp_path / "runs",
                        config_path=config_path,
                        profile_path=profile_path,
                    )

    runtime = json.loads((run_dir / "runtime_rules.json").read_text())
    meta = runtime.get("_meta", {})
    generated = meta.get("generated_sections", [])
    protected = meta.get("protected_sections", [])

    assert "routing.business_context_rules" in generated, (
        f"routing.business_context_rules must be in generated_sections. Got: {generated}"
    )
    assert "routing.business_context_rules" not in protected, (
        f"routing.business_context_rules must NOT be in protected_sections. Got: {protected}"
    )


def _cls_a() -> dict:
    return {"invoice_keywords": ["rechnung"], "document_keywords": ["quittung"],
            "internal_invoice_keywords": [], "invoice_like_indicators": [], "invoice_like_threshold": 3}


def _cls_b() -> dict:
    return {"invoice_keywords": ["faktura", "invoice"], "document_keywords": ["bescheid"],
            "internal_invoice_keywords": ["eigenbeleg"], "invoice_like_indicators": [], "invoice_like_threshold": 5}


# ---------------------------------------------------------------------------
# E. merge_rules_dicts: replaces classification
# ---------------------------------------------------------------------------


def test_merge_rules_dicts_replaces_classification() -> None:
    base = _minimal_rules_dict()
    base["presets"]["office_default"]["classification"] = _cls_a()
    patch = {"active_preset": "office_default", "presets": {
        "office_default": {"classification": _cls_b()}
    }}
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["classification"] == _cls_b()


def test_merge_rules_dicts_without_classification_keeps_base() -> None:
    base = _minimal_rules_dict()
    base["presets"]["office_default"]["classification"] = _cls_a()
    patch = {"active_preset": "office_default", "presets": {
        "office_default": {}  # no classification key
    }}
    merged = merge_rules_dicts(base, patch)
    assert merged["presets"]["office_default"]["classification"] == _cls_a()


# ---------------------------------------------------------------------------
# F. Protected sections unchanged when classification replaced
# ---------------------------------------------------------------------------


def test_merge_rules_dicts_preserves_routing_when_classification_replaced() -> None:
    base = _minimal_rules_dict()
    orig_fa = copy.deepcopy(base["presets"]["office_default"]["routing"]["final_assignment_rules"])
    orig_or = copy.deepcopy(base["presets"]["office_default"]["routing"]["output_route_rules"])
    orig_pd = copy.deepcopy(base["presets"]["office_default"]["routing"]["payment_detection_rules"])

    patch = {"active_preset": "office_default", "presets": {
        "office_default": {"classification": _cls_b()}
    }}
    merged = merge_rules_dicts(base, patch)

    assert merged["presets"]["office_default"]["routing"]["final_assignment_rules"] == orig_fa
    assert merged["presets"]["office_default"]["routing"]["output_route_rules"] == orig_or
    assert merged["presets"]["office_default"]["routing"]["payment_detection_rules"] == orig_pd


# ---------------------------------------------------------------------------
# G. run_once with profile applies generated classification
# ---------------------------------------------------------------------------


def test_run_once_with_profile_applies_generated_classification(tmp_path: Path) -> None:
    """InvoiceProcessor must receive OfficeRules with classification from profile."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)

    profile_data = {
        "schema_version": "1.0",
        "profile_name": "Test Classification",
        "categories": [],
        "folders": [],
        "account_card_profiles": [],
        "address_profiles": [],
        "classification_profile": {
            "invoice_keywords": ["unique-invoice-keyword"],
            "document_keywords": ["unique-doc-keyword"],
            "internal_invoice_keywords": [],
        },
        "naming_profile": {"separator": "_", "max_length": 50, "fields": [], "fallback_values": {}},
        "review_policy": {
            "unclear_folder": "unklar",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile_data), encoding="utf-8")

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "test.pdf")

    received = {}

    def capture(config, extractor, *, office_rules):
        received["rules"] = office_rules
        return type("M", (), {"process_all": lambda self: []})()

    with patch("invoice_tool.run.InvoiceProcessor", side_effect=capture):
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_once(
                        source=source,
                        output=tmp_path / "runs",
                        config_path=config_path,
                        profile_path=profile_path,
                    )

    office_rules = received.get("rules")
    assert office_rules is not None
    inv_kw = list(office_rules.preset.classification.invoice_keywords)
    assert "unique-invoice-keyword" in inv_kw, (
        f"Expected 'unique-invoice-keyword' in invoice_keywords, got: {inv_kw}"
    )
    doc_kw = list(office_rules.preset.classification.document_keywords)
    assert "unique-doc-keyword" in doc_kw


# ---------------------------------------------------------------------------
# H. runtime_rules _meta includes classification as generated section
# ---------------------------------------------------------------------------


def test_runtime_rules_meta_includes_classification_generated_section(tmp_path: Path) -> None:
    """When profile has classification_profile, runtime_rules._meta.generated_sections
    must include 'classification' and protected_sections must NOT."""
    from invoice_tool.run import run_once

    config_path = _make_run_config_path(tmp_path)

    profile_data = {
        "schema_version": "1.0",
        "profile_name": "Test Classification Meta",
        "categories": [],
        "folders": [],
        "account_card_profiles": [],
        "address_profiles": [],
        "classification_profile": {
            "invoice_keywords": ["rechnung"],
            "document_keywords": [],
            "internal_invoice_keywords": [],
        },
        "naming_profile": {"separator": "_", "max_length": 50, "fields": [], "fallback_values": {}},
        "review_policy": {
            "unclear_folder": "unklar",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile_data), encoding="utf-8")

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "test.pdf")

    with patch("invoice_tool.run.InvoiceProcessor") as mock_cls:
        mock_cls.return_value.process_all.return_value = []
        with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
            with patch("invoice_tool.run.OpenAIVisionExtractor"):
                with patch("invoice_tool.run.ExtractionCoordinator"):
                    run_dir = run_once(
                        source=source,
                        output=tmp_path / "runs",
                        config_path=config_path,
                        profile_path=profile_path,
                    )

    runtime = json.loads((run_dir / "runtime_rules.json").read_text())
    meta = runtime.get("_meta", {})
    generated = meta.get("generated_sections", [])
    protected = meta.get("protected_sections", [])

    assert "classification" in generated, (
        f"classification must be in generated_sections. Got: {generated}"
    )
    assert "classification" not in protected, (
        f"classification must NOT be in protected_sections. Got: {protected}"
    )
