"""Tests for CFG-001 canonical target routing model."""
from __future__ import annotations

import pytest

from invoice_tool.folder_destination import MODE_RELATIVE
from invoice_tool.profile_editor import (
    add_target_folder,
    delete_target_folder,
    prepare_profile_for_edit,
    update_global_document_rules,
)
from invoice_tool.target_routing import (
    DEST_TYPE_LEGACY_RELATIVE,
    DEST_TYPE_LOCAL,
    build_runtime_filename,
    create_subdirectory,
    load_target_routing_config,
    normalize_routing_value,
    profile_uses_cfg001_runtime_routing,
    resolve_target_assignment,
    sync_target_routing_to_profile,
    validate_target_routing_config,
)


def _legacy_profile() -> dict:
    return {
        "schema_version": "1.0",
        "profile_name": "Legacy",
        "folders": [
            {"id": "amex", "label": "American Express", "folder_name": "amex"},
            {"id": "fallback", "label": "Manuelle Prüfung", "folder_name": "manual", "role": "unclear"},
        ],
        "review_policy": {
            "unclear_folder_id": "fallback",
            "unclear_folder": "manual",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
        "naming_profile": {
            "separator": "_",
            "max_length": 80,
            "fields": [
                {"key": "invoice_date", "label": "Datum", "enabled": True},
                {"key": "payment_field", "label": "Konto", "enabled": True},
            ],
            "fallback_values": {},
        },
    }


def test_load_target_routing_migrates_legacy_folders() -> None:
    config = load_target_routing_config(_legacy_profile())
    assert config["global_document_rules"]["routing_field"] == "payment_field"
    targets = config["targets"]
    assert len(targets) == 1
    assert targets[0]["display_name"] == "American Express"
    assert targets[0]["destination"]["type"] == DEST_TYPE_LEGACY_RELATIVE
    assert "amex" in targets[0]["routing_values"]
    assert config["fallback"]["display_name"] == "Manuelle Prüfung"


def test_sync_target_routing_rebuilds_legacy_folders() -> None:
    profile = _legacy_profile()
    config = load_target_routing_config(profile)
    config["targets"][0]["destination"] = {
        "type": DEST_TYPE_LOCAL,
        "path": "/tmp/amex-local",
    }
    synced = sync_target_routing_to_profile(profile, config)
    assert synced["target_routing"]["targets"][0]["destination"]["path"] == "/tmp/amex-local"
    assert any(
        f.get("destination", {}).get("mode") == "absolute"
        for f in synced["folders"]
        if f.get("id") == "amex"
    )


def test_resolve_target_assignment_matches_case_insensitive() -> None:
    config = {
        "global_document_rules": {
            "filename_template": "{invoice_date}_{payment_field}.pdf",
            "routing_field": "payment_field",
            "case_sensitive": False,
        },
        "targets": [
            {
                "id": "t1",
                "display_name": "AMEX",
                "active": True,
                "destination": {"type": DEST_TYPE_LOCAL, "path": "/tmp/amex"},
                "routing_values": ["AMEX", "American Express"],
            }
        ],
        "fallback": {
            "display_name": "Fallback",
            "destination": {"type": DEST_TYPE_LOCAL, "path": "/tmp/fallback"},
        },
    }
    result = resolve_target_assignment(config, "american express")
    assert result.matched_display_name == "AMEX"
    assert result.destination_path == "/tmp/amex"
    assert result.is_fallback is False


def test_resolve_target_assignment_uses_fallback_when_no_match() -> None:
    config = load_target_routing_config(_legacy_profile())
    result = resolve_target_assignment(config, "unknown-account")
    assert result.is_fallback is True
    assert result.matched_display_name == "Manuelle Prüfung"


def test_validate_target_routing_detects_duplicate_values() -> None:
    config = {
        "global_document_rules": {
            "filename_template": "{payment_field}.pdf",
            "routing_field": "payment_field",
            "case_sensitive": False,
        },
        "targets": [
            {
                "id": "a",
                "display_name": "A",
                "active": True,
                "destination": {"type": DEST_TYPE_LOCAL, "path": "/tmp/a"},
                "routing_values": ["AMEX"],
            },
            {
                "id": "b",
                "display_name": "B",
                "active": True,
                "destination": {"type": DEST_TYPE_LOCAL, "path": "/tmp/b"},
                "routing_values": ["amex"],
            },
        ],
        "fallback": {
            "display_name": "FB",
            "destination": {"type": DEST_TYPE_LOCAL, "path": "/tmp/fb"},
        },
    }
    errors = validate_target_routing_config(config)
    assert any("mehreren aktiven Zielordnern" in err for err in errors)


def test_add_and_delete_target_folder_roundtrip() -> None:
    profile = prepare_profile_for_edit(_legacy_profile())
    updated = add_target_folder(
        profile,
        display_name="Neuer Ordner",
        destination_path="/tmp/neu",
        routing_values=["NEU"],
    )
    config = load_target_routing_config(updated)
    new_target = next(t for t in config["targets"] if t["display_name"] == "Neuer Ordner")
    target_id = new_target["id"]
    deleted = delete_target_folder(updated, target_id)
    config_after = load_target_routing_config(deleted)
    assert all(t["id"] != target_id for t in config_after["targets"])


def test_update_global_document_rules_persists_template() -> None:
    profile = prepare_profile_for_edit(_legacy_profile())
    updated = update_global_document_rules(
        profile,
        {
            "filename_template": "{invoice_date}_{supplier}.pdf",
            "routing_field": "supplier",
            "case_sensitive": True,
        },
    )
    config = load_target_routing_config(updated)
    assert config["global_document_rules"]["filename_template"] == "{invoice_date}_{supplier}.pdf"
    assert config["global_document_rules"]["routing_field"] == "supplier"
    assert normalize_routing_value("AbC", case_sensitive=True) == "AbC"


def test_resolve_target_assignment_records_matched_routing_value() -> None:
    config = {
        "global_document_rules": {
            "filename_template": "{payment_field}.pdf",
            "routing_field": "payment_field",
            "case_sensitive": False,
        },
        "targets": [
            {
                "id": "t1",
                "display_name": "AMEX",
                "active": True,
                "destination": {"type": DEST_TYPE_LOCAL, "path": "/tmp/amex"},
                "routing_values": ["AMEX", "American Express"],
            }
        ],
        "fallback": {
            "display_name": "Fallback",
            "destination": {"type": DEST_TYPE_LOCAL, "path": "/tmp/fallback"},
        },
    }
    result = resolve_target_assignment(config, "american express")
    assert result.matched_routing_value == "American Express"


def test_build_runtime_filename_uses_override_template() -> None:
    config = {
        "global_document_rules": {
            "filename_template": "{invoice_date}_{payment_field}.pdf",
            "routing_field": "payment_field",
        },
        "targets": [
            {
                "id": "t1",
                "display_name": "T",
                "active": True,
                "destination": {"type": DEST_TYPE_LOCAL, "path": "/tmp/t"},
                "routing_values": ["alpha"],
                "overrides_enabled": True,
                "overrides": {"filename_template": "{invoice_date}_OVERRIDE.pdf"},
            }
        ],
        "fallback": {"display_name": "FB", "destination": {"type": DEST_TYPE_LOCAL, "path": "/tmp/fb"}},
    }
    assignment = resolve_target_assignment(config, "alpha")
    filename = build_runtime_filename(
        config,
        assignment,
        field_values={"invoice_date": "260708", "payment_field": "alpha"},
    )
    assert filename == "260708_OVERRIDE.pdf"


def test_profile_uses_cfg001_runtime_routing_requires_local_targets() -> None:
    profile = _legacy_profile()
    assert profile_uses_cfg001_runtime_routing(profile) is False
    synced = sync_target_routing_to_profile(
        profile,
        load_target_routing_config(profile),
    )
    synced["target_routing"]["targets"][0]["destination"] = {
        "type": DEST_TYPE_LOCAL,
        "path": "/tmp/local",
    }
    assert profile_uses_cfg001_runtime_routing(synced) is True


def test_create_subdirectory_rejects_invalid_names(tmp_path) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    created = create_subdirectory(parent, "child")
    assert created.is_dir()
    with pytest.raises(ValueError):
        create_subdirectory(parent, "../escape")
