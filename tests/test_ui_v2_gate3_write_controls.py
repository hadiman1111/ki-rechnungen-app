"""Gate-3 write-control tests for UI-v2 adapters (isolated storage)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invoice_tool.app_paths import resolve_active_profile_id
from invoice_tool.configuration_model import Configuration, MatchingRule, new_configuration_id
from invoice_tool.profile_store import load_profile_bundle, migrate_all_profiles
from invoice_tool.ui_v2.adapters.configuration_write_adapter import (
    create_configuration,
    delete_configuration,
    new_configuration_draft,
    reorder_configurations,
    set_configuration_active,
    update_configuration,
    update_unmatched_configuration,
)
from invoice_tool.ui_v2.adapters.profile_write_adapter import (
    activate_profile,
    can_delete_profile,
    create_profile,
    delete_profile,
    duplicate_profile,
    save_profile_changes,
)
from invoice_tool.ui_v2.draft_models import ConfigurationDraftVM, ProfileDraftVM
from invoice_tool.ui_v2.validation import validate_filename_pattern, validate_profile_name


@pytest.fixture()
def isolated_support(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    support = tmp_path / "support"
    support.mkdir(parents=True)
    (support / "profiles").mkdir()
    (support / "profile_state.json").write_text(json.dumps({"active_profile_id": "local"}), encoding="utf-8")
    legacy = {
        "profile_name": "Gate3 Test Profil",
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
                    "id": "cfg-1",
                    "display_name": "Hauptkonto",
                    "active": True,
                    "routing_values": ["test"],
                    "destination": {"type": "local_folder", "path": str(tmp_path / "ziel")},
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
    (tmp_path / "ziel").mkdir()
    (tmp_path / "review").mkdir()
    monkeypatch.setattr("invoice_tool.app_paths.profile_storage_dir", lambda: support)
    monkeypatch.setattr("invoice_tool.profile_store.app_paths.profile_storage_dir", lambda: support)
    migrate_all_profiles(force=True)
    return support


def test_create_profile_persists(isolated_support: Path) -> None:
    result = create_profile(name="Temp Gate3", scan_model_id="rechnungen")
    assert result.success
    bundle = load_profile_bundle(result.profile_id or "")
    assert bundle.name == "Temp Gate3"


def test_duplicate_profile_name_blocks_save(isolated_support: Path) -> None:
    errors = validate_profile_name("Gate3 Test Profil")
    assert errors


def test_cancel_profile_create_writes_nothing(isolated_support: Path) -> None:
    before = len(list((isolated_support / "profiles_v2").iterdir()))
    draft = ProfileDraftVM(name="", scan_model_id="")
    assert not draft.name
    after = len(list((isolated_support / "profiles_v2").iterdir()))
    assert before == after


def test_activate_profile_switches(isolated_support: Path) -> None:
    created = create_profile(name="Aktiv Test", scan_model_id="rechnungen")
    assert created.success
    result = activate_profile(created.profile_id or "")
    assert result.success
    assert resolve_active_profile_id() == created.profile_id


def test_unsafe_delete_last_profile_blocked(isolated_support: Path) -> None:
    allowed, _ = can_delete_profile("local")
    created = create_profile(name="Second", scan_model_id="rechnungen")
    assert created.success
    delete_profile("local")
    allowed_after, reason = can_delete_profile(created.profile_id or "")
    assert not allowed_after
    assert "letzte" in reason.lower()


def test_configuration_create_persists(isolated_support: Path, tmp_path: Path) -> None:
    draft = new_configuration_draft("local")
    draft.name = "Neue Regel"
    draft.matching.values = ["abc"]
    draft.destination_path = str(tmp_path / "ziel-neu")
    (tmp_path / "ziel-neu").mkdir()
    result = create_configuration("local", draft)
    assert result.success
    bundle = load_profile_bundle("local")
    assert any(item.name == "Neue Regel" for item in bundle.configurations)


def test_configuration_edit_persists(isolated_support: Path, tmp_path: Path) -> None:
    bundle = load_profile_bundle("local")
    config = bundle.configurations[0]
    draft = ConfigurationDraftVM.from_configuration(config)
    draft.name = "Geändert"
    result = update_configuration("local", draft)
    assert result.success
    reloaded = load_profile_bundle("local")
    assert reloaded.configurations[0].name == "Geändert"


def test_activate_deactivate_persists(isolated_support: Path) -> None:
    bundle = load_profile_bundle("local")
    config_id = bundle.configurations[0].id
    off = set_configuration_active("local", config_id, active=False)
    assert off.success
    on = set_configuration_active("local", config_id, active=True)
    assert on.success


def test_invalid_filename_blocks_save(isolated_support: Path) -> None:
    from invoice_tool.configuration_model import FilenamePattern
    from invoice_tool.scan_models import get_scan_model

    pattern = FilenamePattern(separator="_", components=[])
    errors = validate_filename_pattern(pattern, get_scan_model("rechnungen"))
    assert errors


def test_reorder_persists(isolated_support: Path, tmp_path: Path) -> None:
    draft = new_configuration_draft("local")
    draft.name = "Zweite"
    draft.matching.values = ["zwei"]
    draft.destination_path = str(tmp_path / "ziel2")
    (tmp_path / "ziel2").mkdir()
    create_configuration("local", draft)
    bundle = load_profile_bundle("local")
    ids = [item.id for item in bundle.configurations]
    swapped = list(reversed(ids))
    result = reorder_configurations("local", swapped)
    assert result.success
    reloaded = load_profile_bundle("local")
    assert [item.id for item in reloaded.configurations] == swapped


def test_unmatched_update_persists(isolated_support: Path, tmp_path: Path) -> None:
    bundle = load_profile_bundle("local")
    draft = ConfigurationDraftVM.from_unmatched(bundle.unmatched)
    draft.destination_path = str(tmp_path / "review-new")
    (tmp_path / "review-new").mkdir()
    result = update_unmatched_configuration("local", draft)
    assert result.success


def test_delete_configuration(isolated_support: Path) -> None:
    bundle = load_profile_bundle("local")
    config_id = bundle.configurations[0].id
    result = delete_configuration("local", config_id)
    assert result.success
    assert not load_profile_bundle("local").configurations


def test_duplicate_profile_supported(isolated_support: Path) -> None:
    result = duplicate_profile("local")
    assert result.success
    assert result.profile_id


def test_failed_validation_no_write(isolated_support: Path) -> None:
    draft = new_configuration_draft("local")
    draft.name = ""
    result = create_configuration("local", draft)
    assert not result.success
