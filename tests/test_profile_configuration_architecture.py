"""Focused tests for profile/configuration architecture and design system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invoice_tool.configuration_model import (
    Configuration,
    DATE_FORMATS,
    FilenameComponent,
    FilenamePattern,
    MatchingRule,
    SEPARATORS,
    copy_filename_pattern,
    default_filename_pattern,
    format_date_preview,
    normalize_filename_part,
    preview_filename,
    resolve_configuration_match,
    validate_duplicate_active_rules,
    validate_profile_bundle,
    ProfileBundle,
    UnmatchedConfiguration,
)
from invoice_tool.profile_store import (
    CANONICAL_PROFILES_DIR,
    load_profile_bundle,
    migrate_all_profiles,
    save_profile_bundle,
)
from invoice_tool.scan_models import DEFAULT_SCAN_MODEL_ID, NEUTRAL_PREVIEW_VALUES, get_scan_model, list_scan_models
from invoice_tool.ui_shell import ADMIN_NAV, DAILY_NAV, NAV_CONFIGURATIONS, NAV_WORKSPACE
from invoice_tool.ui_theme import COLOR_PRIMARY, RAW_TOKENS_MODULE


@pytest.fixture()
def isolated_support(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    support = tmp_path / "Application Support" / "KI-Rechnungen"
    support.mkdir(parents=True)
    profiles = support / "profiles"
    profiles.mkdir()
    (support / "profile_state.json").write_text(
        json.dumps({"active_profile_id": "local"}), encoding="utf-8"
    )
    legacy = {
        "profile_name": "American Express Test",
        "scan_model_id": "rechnungen",
        "target_routing": {
            "schema_version": "1.0",
            "global_document_rules": {
                "filename_template": "{invoice_date}_{payment_field}.pdf",
                "routing_field": "payment_field",
                "case_sensitive": False,
            },
            "targets": [
                {
                    "id": "cfg-amex",
                    "display_name": "American Express",
                    "active": True,
                    "routing_values": ["amex", "American Express"],
                    "destination": {"type": "local_folder", "path": str(tmp_path / "amex")},
                    "overrides_enabled": False,
                    "overrides": {},
                }
            ],
            "fallback": {
                "display_name": "Nicht zugeordnete Dokumente",
                "destination": {"type": "local_folder", "path": str(tmp_path / "review")},
            },
        },
    }
    (support / "profile_config.local.json").write_text(json.dumps(legacy, indent=2), encoding="utf-8")
    monkeypatch.setattr("invoice_tool.app_paths.profile_storage_dir", lambda: support)
    monkeypatch.setattr("invoice_tool.profile_store.app_paths.profile_storage_dir", lambda: support)
    return support


def test_navigation_order_and_grouping() -> None:
    assert [item[0] for item in DAILY_NAV] == ["arbeitsbereich", "konfigurationen", "zur_pruefung"]
    assert [item[0] for item in ADMIN_NAV] == ["profile", "einstellungen"]
    assert NAV_WORKSPACE != NAV_CONFIGURATIONS


def test_shared_theme_module_exists() -> None:
    assert RAW_TOKENS_MODULE == "invoice_tool.ui_theme"
    assert COLOR_PRIMARY.startswith("#")


def test_one_scan_model_assigned_per_profile(isolated_support: Path) -> None:
    migrate_all_profiles(force=True)
    bundle = load_profile_bundle("local")
    assert bundle.scan_model_id == DEFAULT_SCAN_MODEL_ID
    assert bundle.scan_model.id == "rechnungen"


def test_feature_list_changes_by_scan_model() -> None:
    invoice = get_scan_model("rechnungen")
    poetry = get_scan_model("freitext-dokumente")
    assert "payment_field" in invoice.feature_keys()
    assert "payment_field" not in poetry.feature_keys()
    assert "author" in poetry.feature_keys()


def test_no_global_fixed_payment_field_requirement() -> None:
    neutral = default_filename_pattern(get_scan_model("freitext-dokumente"))
    keys = [component.key for component in neutral.components if component.type == "feature"]
    assert "payment_field" not in keys


def test_neutral_defaults_contain_no_personal_data() -> None:
    forbidden = {"amex", "American Express", "Architektur & Innenarchitektur", "Event Production", "Privat", "ai", "ep", "private"}
    for value in NEUTRAL_PREVIEW_VALUES.values():
        assert value not in forbidden
    for model in list_scan_models():
        assert "American Express" not in model.label


def test_migration_preserves_personal_configuration_names(isolated_support: Path) -> None:
    migrate_all_profiles(force=True)
    bundle = load_profile_bundle("local")
    names = {config.name for config in bundle.configurations}
    assert "American Express" in names


def test_configuration_contains_matching_filename_and_destination(isolated_support: Path) -> None:
    migrate_all_profiles(force=True)
    config = load_profile_bundle("local").configurations[0]
    assert config.matching is not None
    assert config.filename_pattern.components
    assert config.destination.get("path")


def test_filename_components_add_remove_reorder() -> None:
    pattern = FilenamePattern(
        separator="_",
        components=[
            FilenameComponent(type="feature", key="invoice_date", label="Datum"),
            FilenameComponent(type="feature", key="supplier", label="Lieferant"),
        ],
    )
    pattern.components.append(FilenameComponent(type="system", key="extension", label="Dateityp"))
    assert len(pattern.components) == 3
    pattern.components.pop(1)
    assert pattern.components[0].key == "invoice_date"
    pattern.components[0], pattern.components[1] = pattern.components[1], pattern.components[0]
    assert pattern.components[0].key == "extension"


def test_lowercase_filename_normalization() -> None:
    assert normalize_filename_part("  AMEX Value  ") == "amex value"
    assert normalize_filename_part("Bad/Name").startswith("bad")


def test_unsafe_filename_character_handling() -> None:
    assert "/" not in normalize_filename_part("a/b")
    assert "?" not in normalize_filename_part("a?b")


def test_pattern_copy_is_independent() -> None:
    source = default_filename_pattern(get_scan_model("rechnungen"))
    clone = copy_filename_pattern(source)
    clone.components[0].custom_text = "changed"
    assert source.components[0].custom_text != "changed"


def test_matching_is_case_insensitive() -> None:
    configs = [
        Configuration(
            id="1",
            name="Amex",
            active=True,
            matching=MatchingRule(feature_key="payment_field", values=["amex"]),
            destination={"type": "local_folder", "path": "/tmp/a"},
        )
    ]
    matched, reason = resolve_configuration_match(configs, feature_key="payment_field", value="AMEX")
    assert matched is not None
    assert reason is None


def test_duplicate_active_rules_blocked() -> None:
    configs = [
        Configuration(
            id="1",
            name="A",
            active=True,
            matching=MatchingRule(feature_key="payment_field", values=["amex"]),
            destination={"type": "local_folder", "path": "/tmp/a"},
        ),
        Configuration(
            id="2",
            name="B",
            active=True,
            matching=MatchingRule(feature_key="payment_field", values=["AMEX"]),
            destination={"type": "local_folder", "path": "/tmp/b"},
        ),
    ]
    assert validate_duplicate_active_rules(configs)


def test_zero_and_multiple_matches_use_unmatched() -> None:
    configs = [
        Configuration(
            id="1",
            name="A",
            active=True,
            matching=MatchingRule(feature_key="payment_field", values=["alpha"]),
            destination={"type": "local_folder", "path": "/tmp/a"},
        ),
        Configuration(
            id="2",
            name="B",
            active=True,
            matching=MatchingRule(feature_key="payment_field", values=["beta"]),
            destination={"type": "local_folder", "path": "/tmp/b"},
        ),
    ]
    none_match, none_reason = resolve_configuration_match(configs, feature_key="payment_field", value="gamma")
    assert none_match is None
    assert none_reason is not None

    configs[0].matching.values = ["shared"]
    configs[1].matching.values = ["shared"]
    multi_match, multi_reason = resolve_configuration_match(configs, feature_key="payment_field", value="shared")
    assert multi_match is None
    assert "Mehrere" in (multi_reason or "")


def test_atomic_save_writes_canonical_layout(isolated_support: Path, tmp_path: Path) -> None:
    migrate_all_profiles(force=True)
    bundle = load_profile_bundle("local")
    bundle.configurations[0].name = "Updated Name"
    save_profile_bundle(bundle)
    profile_dir = isolated_support / CANONICAL_PROFILES_DIR / "local"
    assert (profile_dir / "profile.json").exists()
    assert list((profile_dir / "configurations").glob("*.json"))
    reloaded = load_profile_bundle("local")
    assert reloaded.configurations[0].name == "Updated Name"


def test_preview_filename_uses_neutral_values() -> None:
    pattern = default_filename_pattern(get_scan_model("rechnungen"))
    example = preview_filename(pattern, get_scan_model("rechnungen"))
    assert "amex" not in example.lower()
    assert example.endswith(".pdf")


def test_date_format_selection_examples() -> None:
    assert format_date_preview("YYYYMMDD") == "20260708"
    assert format_date_preview("DD.MM.YYYY") == "08.07.2026"
    assert "YYYY-MM-DD" in DATE_FORMATS


def test_separator_selection() -> None:
    pattern = FilenamePattern(separator=SEPARATORS["hyphen"], components=[])
    assert pattern.separator == "-"


def test_cancel_preserves_persisted_configuration(isolated_support: Path) -> None:
    migrate_all_profiles(force=True)
    bundle = load_profile_bundle("local")
    original_name = bundle.configurations[0].name
    bundle.configurations[0].name = "Temporary Draft Name"
    assert bundle.configurations[0].name != original_name
    reloaded = load_profile_bundle("local")
    assert reloaded.configurations[0].name == original_name


def test_arbitrary_profile_types_supported(isolated_support: Path) -> None:
    migrate_all_profiles(force=True)
    bundle = load_profile_bundle("local")
    bundle.scan_model_id = "freitext-dokumente"
    bundle.configurations = []
    save_profile_bundle(bundle)
    reloaded = load_profile_bundle("local")
    assert reloaded.scan_model_id == "freitext-dokumente"
    assert "author" in reloaded.scan_model.feature_keys()


def test_validate_profile_bundle_blocks_duplicates(isolated_support: Path) -> None:
    migrate_all_profiles(force=True)
    bundle = load_profile_bundle("local")
    duplicate = Configuration.from_dict(bundle.configurations[0].to_dict())
    duplicate.id = "dup-id"
    bundle.configurations.append(duplicate)
    assert validate_profile_bundle(bundle)


def test_ui_configurations_uses_shared_components() -> None:
    source = Path(__file__).resolve().parents[1] / "invoice_tool" / "ui_configurations.py"
    text = source.read_text(encoding="utf-8")
    assert "ui_components" in text
    assert "page_heading" in text
    assert "configuration_card" in text
    assert "ui_theme" in text or "COLOR_" in text
