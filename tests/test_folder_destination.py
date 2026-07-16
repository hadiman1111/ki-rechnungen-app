"""Tests for invoice_tool/folder_destination.py (CFG-001)."""
from __future__ import annotations

from pathlib import Path

import pytest

from invoice_tool.file_lifecycle import PathSafetyError
from invoice_tool.folder_destination import (
    MODE_ABSOLUTE,
    MODE_RELATIVE,
    build_folder_destinations,
    migrate_profile_destinations,
    normalize_folder_destination,
    resolve_configured_target_directory,
    resolve_routing_folder_key,
    validate_destination,
)
from invoice_tool.profile_compiler import compile_profile_to_rules


def test_normalize_legacy_folder_name() -> None:
    folder = {"id": "inbox", "label": "Posteingang", "folder_name": "inbox"}
    assert normalize_folder_destination(folder) == {
        "mode": MODE_RELATIVE,
        "path": "inbox",
    }


def test_normalize_explicit_destination() -> None:
    folder = {
        "id": "external",
        "label": "Extern",
        "destination": {"mode": MODE_ABSOLUTE, "path": "/tmp/external-inbox"},
    }
    assert normalize_folder_destination(folder)["mode"] == MODE_ABSOLUTE


def test_migrate_profile_adds_destination() -> None:
    profile = {
        "folders": [{"id": "a", "label": "A", "folder_name": "alpha"}],
    }
    migrated = migrate_profile_destinations(profile)
    assert migrated["folders"][0]["destination"] == {
        "mode": MODE_RELATIVE,
        "path": "alpha",
    }


def test_validate_rejects_traversal() -> None:
    errors = validate_destination(
        {"mode": MODE_RELATIVE, "path": "../escape"},
        prefix="destination",
    )
    assert any(".." in err for err in errors)


def test_resolve_relative_under_output_root(tmp_path: Path) -> None:
    output_root = tmp_path / "out"
    output_root.mkdir()
    dest = {"mode": MODE_RELATIVE, "path": "contracts"}
    resolved = resolve_configured_target_directory(output_root, dest)
    assert resolved == (output_root / "contracts").resolve()


def test_resolve_absolute_target(tmp_path: Path) -> None:
    absolute = tmp_path / "fixed-target"
    absolute.mkdir()
    dest = {"mode": MODE_ABSOLUTE, "path": str(absolute)}
    resolved = resolve_configured_target_directory(tmp_path / "out", dest)
    assert resolved == absolute.resolve()


def test_resolve_routing_prefers_folder_destinations(tmp_path: Path) -> None:
    absolute = tmp_path / "amex-external"
    absolute.mkdir()
    output_root = tmp_path / "out"
    output_root.mkdir()
    folder_destinations = {
        "amex": {"mode": MODE_ABSOLUTE, "path": str(absolute)},
    }
    resolved = resolve_routing_folder_key(
        "amex",
        output_root=output_root,
        folder_destinations=folder_destinations,
        zielordner_map={"amex": "amex"},
    )
    assert resolved == absolute.resolve()


def test_compiler_emits_folder_destinations() -> None:
    profile = {
        "schema_version": "1.0",
        "profile_name": "Test",
        "folders": [
            {
                "id": "contracts",
                "label": "Verträge",
                "destination": {"mode": MODE_RELATIVE, "path": "contracts"},
            },
            {
                "id": "external",
                "label": "Extern",
                "destination": {"mode": MODE_ABSOLUTE, "path": "/tmp/external"},
            },
        ],
        "address_profiles": [],
        "account_card_profiles": [],
        "naming_profile": {
            "separator": "_",
            "max_length": 50,
            "fields": [{"key": "invoice_date", "label": "Datum", "enabled": True}],
            "fallback_values": {},
        },
        "review_policy": {
            "unclear_folder_id": "contracts",
            "unclear_folder": "contracts",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
        "document_profiles": [
            {
                "id": "vertrag",
                "label": "Vertrag",
                "document_type": "contract",
                "target_folder_id": "contracts",
                "enabled": True,
            }
        ],
    }
    compiled = compile_profile_to_rules(profile)
    assert "folder_destinations" in compiled
    assert compiled["folder_destinations"]["external"]["mode"] == MODE_ABSOLUTE
    doc = compiled["document_profiles"][0]
    assert doc["target_destination"]["path"] == "contracts"


def test_absolute_path_rejected_when_not_fully_qualified() -> None:
    with pytest.raises(PathSafetyError):
        resolve_configured_target_directory(
            Path("/tmp/out"),
            {"mode": MODE_ABSOLUTE, "path": "relative-looking"},
        )


def test_validate_runtime_destinations_preflight_rejects_archive_target(tmp_path: Path) -> None:
    from invoice_tool.folder_destination import validate_runtime_destinations_preflight

    source = tmp_path / "input"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    archive = source / "archiv"
    archive.mkdir()
    profile = {
        "folders": [
            {
                "id": "bad",
                "label": "Bad",
                "destination": {"mode": MODE_ABSOLUTE, "path": str(archive)},
            }
        ]
    }
    errors = validate_runtime_destinations_preflight(
        profile,
        output_root=output,
        source_root=source,
        run_support_root=tmp_path / "support",
        project_root_path=tmp_path / "project",
    )
    assert errors
    assert any("verbotenen" in err for err in errors)
    folders = [
        {"id": "ok", "label": "OK", "folder_name": "ok"},
        {"id": "bad", "label": "Bad"},
    ]
    result = build_folder_destinations(folders)
    assert "ok" in result
    assert "bad" not in result
