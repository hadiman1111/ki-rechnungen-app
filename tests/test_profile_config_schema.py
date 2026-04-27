"""
Validierungstests: profile_config.schema.json und profile_config.example.json.

Keine Fachlogik, keine Routingregeln – nur Schema-Konformität der Profilschicht.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

try:
    import jsonschema
    from jsonschema import Draft7Validator, ValidationError, validate

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

SCHEMA_PATH = Path("profile_config.schema.json")
EXAMPLE_PATH = Path("profile_config.example.json")

skip_if_no_jsonschema = pytest.mark.skipif(
    not JSONSCHEMA_AVAILABLE,
    reason="jsonschema nicht installiert",
)


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def _minimal_valid() -> dict:
    """Kleinstes valides Profil-Dokument für Negativtests."""
    return {
        "schema_version": "1.0",
        "profile_name": "Testprofil",
        "categories": [{"id": "private", "label": "Privat"}],
        "folders": [{"id": "private", "label": "Privat", "folder_name": "private"}],
        "account_card_profiles": [],
        "address_profiles": [],
        "naming_profile": {
            "separator": "_",
            "max_length": 50,
            "fields": [{"key": "invoice_date", "label": "Datum", "enabled": True}],
            "fallback_values": {"invoice_date": "unknown-date"},
        },
        "review_policy": {
            "unclear_folder": "unklar",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }


# ---------------------------------------------------------------------------
# Basistests: Dateien vorhanden und gültiges JSON
# ---------------------------------------------------------------------------


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.exists(), "profile_config.schema.json muss vorhanden sein."


def test_schema_is_valid_json() -> None:
    schema = _load_schema()
    assert isinstance(schema, dict)
    assert "$schema" in schema
    assert schema.get("title") == "ProfileConfig"


@skip_if_no_jsonschema
def test_schema_is_valid_json_schema() -> None:
    """Das Schema selbst muss ein valides JSON Schema Draft-07 sein."""
    schema = _load_schema()
    Draft7Validator.check_schema(schema)


def test_example_file_exists() -> None:
    assert EXAMPLE_PATH.exists(), "profile_config.example.json muss vorhanden sein."


def test_example_is_valid_json() -> None:
    example = _load_example()
    assert isinstance(example, dict)


# ---------------------------------------------------------------------------
# Hauptvalidierung: Beispiel gegen Schema
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_example_valid_against_schema() -> None:
    """profile_config.example.json muss vollständig gegen das Schema valide sein."""
    schema = _load_schema()
    example = _load_example()
    validate(instance=example, schema=schema)


# ---------------------------------------------------------------------------
# Pflichtfelder
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_schema_version_required() -> None:
    schema = _load_schema()
    bad = _minimal_valid()
    del bad["schema_version"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_profile_name_required() -> None:
    schema = _load_schema()
    bad = _minimal_valid()
    del bad["profile_name"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_categories_required() -> None:
    schema = _load_schema()
    bad = _minimal_valid()
    del bad["categories"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_folders_required() -> None:
    schema = _load_schema()
    bad = _minimal_valid()
    del bad["folders"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_naming_profile_required() -> None:
    schema = _load_schema()
    bad = _minimal_valid()
    del bad["naming_profile"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_review_policy_required() -> None:
    schema = _load_schema()
    bad = _minimal_valid()
    del bad["review_policy"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


# ---------------------------------------------------------------------------
# Kategorien und Ordner
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_private_is_valid_category() -> None:
    """'private' muss als gültige Kategorie-ID akzeptiert werden."""
    schema = _load_schema()
    doc = _minimal_valid()
    doc["categories"] = [{"id": "private", "label": "Privat"}]
    validate(instance=doc, schema=schema)


@skip_if_no_jsonschema
def test_invalid_category_id_rejected() -> None:
    """'privat' (ohne e) ist keine gültige Kategorie-ID."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["categories"] = [{"id": "privat", "label": "Privat"}]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_private_is_valid_folder_name() -> None:
    """'private' ist ein gültiger folder_name."""
    schema = _load_schema()
    doc = _minimal_valid()
    doc["folders"] = [{"id": "private", "label": "Privat", "folder_name": "private"}]
    validate(instance=doc, schema=schema)


@skip_if_no_jsonschema
def test_privat_folder_name_rejected() -> None:
    """'privat' (ohne e) als folder_name ist ungültig."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["folders"] = [{"id": "private", "label": "Privat", "folder_name": "privat"}]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_unknown_folder_id_rejected() -> None:
    """Ein unbekannter folder id-Wert muss abgelehnt werden."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["folders"] = [{"id": "kasse", "label": "Kasse", "folder_name": "kasse"}]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


# ---------------------------------------------------------------------------
# Account/Card Profile
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_account_profile_without_id_rejected() -> None:
    """account_card_profile ohne 'id' muss abgelehnt werden."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["account_card_profiles"] = [
        {"label": "Kein ID", "category": "private", "enabled": True}
    ]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_account_profile_without_label_rejected() -> None:
    """account_card_profile ohne 'label' muss abgelehnt werden."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["account_card_profiles"] = [{"id": "test", "category": "private"}]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_account_profile_invalid_category_rejected() -> None:
    """account_card_profile mit ungültiger Kategorie muss abgelehnt werden."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["account_card_profiles"] = [
        {"id": "test", "label": "Test", "category": "unknown"}
    ]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_account_profile_invalid_card_ending_rejected() -> None:
    """Kartenendung mit weniger oder mehr als 4 Ziffern muss abgelehnt werden."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["account_card_profiles"] = [
        {"id": "test", "label": "Test", "card_endings": ["12"]}
    ]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_account_profile_no_technical_flags() -> None:
    """account_card_profiles kennt keine technischen Flags wie use_account_art."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["account_card_profiles"] = [
        {
            "id": "test",
            "label": "Test",
            "use_account_art": True,
            "use_account_konto": True,
        }
    ]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


# ---------------------------------------------------------------------------
# Address Profile
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_address_profile_without_canonical_address_rejected() -> None:
    """address_profile ohne canonical_address muss abgelehnt werden."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["address_profiles"] = [
        {"id": "test", "label": "Test", "category": "private"}
    ]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_address_profile_valid_without_advanced_variants() -> None:
    """address_profile ohne advanced_variants ist gültig."""
    schema = _load_schema()
    doc = _minimal_valid()
    doc["address_profiles"] = [
        {
            "id": "test-addr",
            "label": "Teststraße",
            "category": "private",
            "canonical_address": {"street": "Teststraße"},
        }
    ]
    validate(instance=doc, schema=schema)


@skip_if_no_jsonschema
def test_address_profile_with_advanced_variants_valid() -> None:
    """address_profile mit advanced_variants ist ebenfalls gültig."""
    schema = _load_schema()
    doc = _minimal_valid()
    doc["address_profiles"] = [
        {
            "id": "test-addr",
            "label": "Teststraße",
            "category": "private",
            "canonical_address": {"street": "Teststraße"},
            "advanced_variants": ["teststr.", "teststrasse"],
        }
    ]
    validate(instance=doc, schema=schema)


@skip_if_no_jsonschema
def test_matching_mode_strict_valid() -> None:
    schema = _load_schema()
    doc = _minimal_valid()
    doc["address_profiles"] = [
        {
            "id": "t",
            "label": "T",
            "category": "private",
            "canonical_address": {"street": "T"},
            "matching_mode": "strict",
        }
    ]
    validate(instance=doc, schema=schema)


@skip_if_no_jsonschema
def test_matching_mode_normal_valid() -> None:
    schema = _load_schema()
    doc = _minimal_valid()
    doc["address_profiles"] = [
        {
            "id": "t",
            "label": "T",
            "category": "private",
            "canonical_address": {"street": "T"},
            "matching_mode": "normal",
        }
    ]
    validate(instance=doc, schema=schema)


@skip_if_no_jsonschema
def test_matching_mode_tolerant_valid() -> None:
    schema = _load_schema()
    doc = _minimal_valid()
    doc["address_profiles"] = [
        {
            "id": "t",
            "label": "T",
            "category": "private",
            "canonical_address": {"street": "T"},
            "matching_mode": "tolerant",
        }
    ]
    validate(instance=doc, schema=schema)


@skip_if_no_jsonschema
def test_matching_mode_invalid_value_rejected() -> None:
    """Ein ungültiger matching_mode muss abgelehnt werden."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["address_profiles"] = [
        {
            "id": "t",
            "label": "T",
            "category": "private",
            "canonical_address": {"street": "T"},
            "matching_mode": "fuzzy",
        }
    ]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_address_profile_canonical_address_requires_street() -> None:
    """canonical_address ohne street muss abgelehnt werden."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["address_profiles"] = [
        {
            "id": "t",
            "label": "T",
            "category": "private",
            "canonical_address": {"house_number": "5"},
        }
    ]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


# ---------------------------------------------------------------------------
# Review Policy
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_review_policy_private_exception_present() -> None:
    """review_policy muss private_unclear_attributes_stay_private als boolean enthalten."""
    schema = _load_schema()
    doc = _minimal_valid()
    assert isinstance(doc["review_policy"]["private_unclear_attributes_stay_private"], bool)
    validate(instance=doc, schema=schema)


@skip_if_no_jsonschema
def test_review_policy_missing_private_flag_rejected() -> None:
    """review_policy ohne private_unclear_attributes_stay_private muss abgelehnt werden."""
    schema = _load_schema()
    bad = _minimal_valid()
    del bad["review_policy"]["private_unclear_attributes_stay_private"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_review_policy_unclear_folder_required() -> None:
    schema = _load_schema()
    bad = _minimal_valid()
    del bad["review_policy"]["unclear_folder"]
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


# ---------------------------------------------------------------------------
# Sonstiges
# ---------------------------------------------------------------------------


@skip_if_no_jsonschema
def test_unknown_top_level_field_rejected() -> None:
    """Unbekannte Root-Felder müssen abgelehnt werden."""
    schema = _load_schema()
    bad = _minimal_valid()
    bad["ungueltig_extra"] = True
    with pytest.raises(ValidationError):
        validate(instance=bad, schema=schema)


@skip_if_no_jsonschema
def test_example_contains_private_folder() -> None:
    """Beispielprofil muss einen folder mit id 'private' enthalten."""
    example = _load_example()
    folder_ids = [f["id"] for f in example["folders"]]
    assert "private" in folder_ids


@skip_if_no_jsonschema
def test_example_contains_no_privat_folder_name() -> None:
    """Beispielprofil darf keinen folder_name 'privat' (ohne e) enthalten."""
    example = _load_example()
    for folder in example["folders"]:
        assert folder["folder_name"] != "privat", (
            f"Folder '{folder['id']}' hat ungültigen folder_name 'privat'."
        )


@skip_if_no_jsonschema
def test_example_account_profiles_have_ids() -> None:
    """Alle account_card_profiles im Beispiel müssen eine id haben."""
    example = _load_example()
    for profile in example["account_card_profiles"]:
        assert "id" in profile and profile["id"]


@skip_if_no_jsonschema
def test_example_address_profiles_have_canonical_address() -> None:
    """Alle address_profiles im Beispiel müssen canonical_address haben."""
    example = _load_example()
    for profile in example["address_profiles"]:
        assert "canonical_address" in profile
        assert "street" in profile["canonical_address"]
