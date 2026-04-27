"""
Validierungstests: office_rules.json gegen office_rules.schema.json.

Keine Fachlogik, keine Routingregeln – nur Schema-Konformität.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

try:
    import jsonschema
    from jsonschema import ValidationError, validate

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

RULES_PATH = Path("office_rules.json")
SCHEMA_PATH = Path("office_rules.schema.json")

skip_if_no_jsonschema = pytest.mark.skipif(
    not JSONSCHEMA_AVAILABLE,
    reason="jsonschema nicht installiert",
)


def _load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Basistests
# ---------------------------------------------------------------------------


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.exists(), "office_rules.schema.json muss vorhanden sein."


def test_schema_is_valid_json() -> None:
    schema = _load_schema()
    assert isinstance(schema, dict)
    assert "$schema" in schema


def test_rules_file_exists() -> None:
    assert RULES_PATH.exists(), "office_rules.json muss vorhanden sein."


# ---------------------------------------------------------------------------
# Hauptvalidierung
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_office_rules_valid_against_schema() -> None:
    """office_rules.json muss vollständig gegen das Schema valide sein."""
    rules = _load_rules()
    schema = _load_schema()
    validate(instance=rules, schema=schema)


# ---------------------------------------------------------------------------
# Pflichtbereiche
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_active_preset_present() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    del bad["active_preset"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_presets_required() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    del bad["presets"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_preset_routing_required() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    del bad["presets"][preset_key]["routing"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_preset_classification_required() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    del bad["presets"][preset_key]["classification"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_preset_dateiname_schema_required() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    del bad["presets"][preset_key]["dateiname_schema"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_preset_supplier_cleaning_required() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    del bad["presets"][preset_key]["supplier_cleaning"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


# ---------------------------------------------------------------------------
# Wertebereiche: Zielordner / Art
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_zielordner_value_private_is_valid() -> None:
    """'private' ist ein gültiger Zielordner-Wert in output_route_rules."""
    rules = _load_rules()
    schema = _load_schema()
    preset_key = list(rules["presets"].keys())[0]
    output_rules = rules["presets"][preset_key]["routing"]["output_route_rules"]
    zielordner_values = [r["zielordner"] for r in output_rules if "zielordner" in r]
    assert "private" in zielordner_values, "'private' muss als zielordner in output_route_rules vorkommen."
    validate(instance=rules, schema=schema)


@skip_if_no_jsonschema
def test_invalid_art_value_rejected() -> None:
    """Ein ungültiger art-Wert in business_context_rules muss das Schema verletzen."""
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    bcr = bad["presets"][preset_key]["routing"]["business_context_rules"]
    if bcr:
        bcr[0]["art"] = "privat"
        with pytest.raises(ValidationError):
            validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_privat_not_valid_as_zielordner() -> None:
    """'privat' (ohne e) ist kein gültiger zielordner-Wert in output_route_rules."""
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    output_rules = bad["presets"][preset_key]["routing"]["output_route_rules"]
    if output_rules:
        output_rules[0]["zielordner"] = "privat"
        with pytest.raises(ValidationError):
            validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_invalid_default_art_rejected() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    bad["presets"][preset_key]["routing"]["default_art"] = "unbekannt"
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_invalid_default_zielordner_rejected() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    bad["presets"][preset_key]["routing"]["default_zielordner"] = "kasse"
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


# ---------------------------------------------------------------------------
# Strukturtests
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_fuzzy_threshold_must_be_number() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    strassen = bad["presets"][preset_key]["routing"]["strassen"]
    if strassen:
        strassen[0]["fuzzy_threshold"] = "hoch"
        with pytest.raises(ValidationError):
            validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_fuzzy_threshold_above_one_rejected() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    strassen = bad["presets"][preset_key]["routing"]["strassen"]
    if strassen:
        strassen[0]["fuzzy_threshold"] = 1.5
        with pytest.raises(ValidationError):
            validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_unknown_top_level_field_rejected() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    bad["ungueltig_extra"] = True
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_konten_entry_name_required() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    konten = bad["presets"][preset_key]["routing"]["konten"]
    if konten:
        del konten[0]["name"]
        with pytest.raises(ValidationError):
            validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_erweiterung_must_start_with_dot() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    bad["presets"][preset_key]["dateiname_schema"]["erweiterung"] = "pdf"
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_report_extension_must_start_with_dot() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    bad["presets"][preset_key]["duplicate_handling"]["report_extension"] = "txt"
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_invoice_like_threshold_must_be_integer() -> None:
    rules = _load_rules()
    schema = _load_schema()
    bad = copy.deepcopy(rules)
    preset_key = list(bad["presets"].keys())[0]
    bad["presets"][preset_key]["classification"]["invoice_like_threshold"] = "drei"
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)
