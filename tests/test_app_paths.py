from __future__ import annotations

import json
from pathlib import Path

import pytest

from invoice_tool import app_paths


def test_project_root_points_to_repository_root() -> None:
    root = app_paths.project_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "invoice_tool").is_dir()


def test_resolve_invoice_config_path_uses_project_root_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLET_PLATFORM", raising=False)
    config_path = app_paths.resolve_invoice_config_path()
    assert config_path.name == "invoice_config.json"
    assert config_path.parent == app_paths.project_root()


def test_user_support_dir_is_under_library_application_support() -> None:
    support = app_paths.user_support_dir()
    assert support.name == app_paths.APP_SUPPORT_DIR_NAME
    assert support.parent.name == "Application Support"


def test_create_run_support_dir_is_unique(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    support = tmp_path / "Application Support" / "KI-Rechnungen"
    monkeypatch.setattr(app_paths, "user_support_dir", lambda: support)

    first, first_id = app_paths.create_run_support_dir(run_id="20260708_120000")
    second, second_id = app_paths.create_run_support_dir(run_id="20260708_120000")

    assert first.exists()
    assert second.exists()
    assert first != second
    assert second_id == "20260708_120000_2"


def test_resolve_profile_path_prefers_active_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLET_PLATFORM", raising=False)
    support = tmp_path / "Application Support" / "KI-Rechnungen"
    support.mkdir(parents=True)
    monkeypatch.setattr(app_paths, "user_support_dir", lambda: support)
    monkeypatch.setattr(app_paths, "project_root", lambda: tmp_path / "project")

    default = support / "profile_config.local.json"
    default.write_text('{"profile_name": "Default"}', encoding="utf-8")

    profiles_dir = support / "profiles"
    profiles_dir.mkdir()
    alt = profiles_dir / "alt.json"
    alt.write_text('{"profile_name": "Alternativ"}', encoding="utf-8")

    entries = app_paths.list_profile_entries()
    assert len(entries) == 2
    assert app_paths.resolve_profile_path() == default

    app_paths.set_active_profile_id("alt")
    assert app_paths.resolve_profile_path() == alt


def test_migrate_legacy_project_profile_to_application_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    support = tmp_path / "Application Support" / "KI-Rechnungen"
    monkeypatch.setattr(app_paths, "project_root", lambda: project)
    monkeypatch.setattr(app_paths, "user_support_dir", lambda: support)

    legacy = project / "profile_config.local.json"
    legacy.write_text('{"profile_name": "Legacy"}', encoding="utf-8")

    result = app_paths.ensure_profile_storage_layout()
    migrated = result / "profile_config.local.json"
    assert migrated.is_file()
    assert '"Legacy"' in migrated.read_text(encoding="utf-8")
    assert legacy.is_file()


def test_migration_does_not_overwrite_existing_application_support_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    support = tmp_path / "Application Support" / "KI-Rechnungen"
    support.mkdir(parents=True)
    monkeypatch.setattr(app_paths, "project_root", lambda: project)
    monkeypatch.setattr(app_paths, "user_support_dir", lambda: support)

    (project / "profile_config.local.json").write_text('{"profile_name": "Legacy"}', encoding="utf-8")
    existing = support / "profile_config.local.json"
    existing.write_text('{"profile_name": "Canonical"}', encoding="utf-8")

    app_paths.ensure_profile_storage_layout()
    assert '"Canonical"' in existing.read_text(encoding="utf-8")


def test_seed_user_config_from_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    defaults = tmp_path / "defaults"
    defaults.mkdir()
    (defaults / "invoice_config.json").write_text(
        json.dumps({"eingangsordner": str(tmp_path / "in"), "regeln_datei": "office_rules.json"}),
        encoding="utf-8",
    )
    (defaults / "office_rules.json").write_text("{}", encoding="utf-8")

    support = tmp_path / "support"
    monkeypatch.setattr(app_paths, "is_standalone_bundle", lambda: True)
    monkeypatch.setattr(app_paths, "user_support_dir", lambda: support)
    monkeypatch.setattr(app_paths, "bundled_defaults_dir", lambda: defaults)

    result = app_paths.ensure_user_config_layout()

    assert result == support
    assert (support / "invoice_config.json").is_file()
    assert (support / "office_rules.json").is_file()


def test_save_user_json_creates_backup(tmp_path: Path) -> None:
    target = tmp_path / "invoice_config.json"
    target.write_text('{"old": true}\n', encoding="utf-8")

    app_paths.save_user_json(target, {"new": True})

    backups = list(tmp_path.glob("invoice_config.json.backup-*"))
    assert len(backups) == 1
    assert '"new": true' in target.read_text(encoding="utf-8")
