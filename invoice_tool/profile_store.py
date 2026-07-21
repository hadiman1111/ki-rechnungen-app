"""Canonical profile storage, migration, and persistence under Application Support."""

from __future__ import annotations

import copy
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from invoice_tool import app_paths
from invoice_tool.configuration_model import (
    Configuration,
    ProfileBundle,
    UnmatchedConfiguration,
    compile_profile_bundle_to_legacy,
    default_filename_pattern,
    load_bundle_from_legacy_profile,
    new_configuration_id,
    new_profile_id,
)
from invoice_tool.profile_editor import load_profile_for_edit, save_profile_atomic
from invoice_tool.scan_models import DEFAULT_SCAN_MODEL_ID, get_scan_model

logger = logging.getLogger(__name__)

CANONICAL_PROFILES_DIR = "profiles_v2"
PROFILE_JSON = "profile.json"
CONFIGURATIONS_DIR = "configurations"
UNMATCHED_JSON = "unmatched.json"
MIGRATION_MARKER = ".migrated_v2"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def canonical_profiles_root() -> Path:
    root = app_paths.profile_storage_dir() / CANONICAL_PROFILES_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def _profile_dir(profile_id: str) -> Path:
    return canonical_profiles_root() / profile_id


def _backup_path(original: Path) -> Path:
    return original.with_name(f"{original.name}.bak_{_timestamp()}")


def list_canonical_profile_ids() -> list[str]:
    root = canonical_profiles_root()
    ids = []
    for path in sorted(root.iterdir()):
        if path.is_dir() and (path / PROFILE_JSON).is_file():
            ids.append(path.name)
    return ids


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if path.exists():
        shutil.copy2(path, _backup_path(path))
    temp.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def save_profile_bundle(bundle: ProfileBundle) -> Path:
    """Persist bundle atomically in canonical layout and sync legacy runtime profile."""
    profile_dir = _profile_dir(bundle.id)
    profile_dir.mkdir(parents=True, exist_ok=True)
    config_dir = profile_dir / CONFIGURATIONS_DIR
    config_dir.mkdir(parents=True, exist_ok=True)

    profile_meta = {
        "id": bundle.id,
        "name": bundle.name,
        "active": bundle.active,
        "scan_model_id": bundle.scan_model_id,
        "schema_version": "2.0",
        "configuration_order": [config.id for config in bundle.configurations],
    }
    _write_json_atomic(profile_dir / PROFILE_JSON, profile_meta)
    _write_json_atomic(profile_dir / UNMATCHED_JSON, bundle.unmatched.to_dict())

    existing_ids = {path.stem for path in config_dir.glob("*.json")}
    keep_ids = {config.id for config in bundle.configurations}
    for stale in existing_ids - keep_ids:
        stale_path = config_dir / f"{stale}.json"
        if stale_path.exists():
            shutil.copy2(stale_path, _backup_path(stale_path))
            stale_path.unlink()

    for config in bundle.configurations:
        _write_json_atomic(config_dir / f"{config.id}.json", config.to_dict())

    legacy = compile_profile_bundle_to_legacy(bundle)
    legacy_path = _resolve_legacy_profile_path(bundle.id)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    if legacy_path.is_file():
        save_profile_atomic(legacy_path, legacy)
    else:
        legacy_path.write_text(json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    bundle.legacy_profile = legacy
    return profile_dir


def _resolve_legacy_profile_path(profile_id: str) -> Path:
    if profile_id == "local":
        return app_paths.profile_storage_dir() / app_paths.PROFILE_LOCAL_FILENAME
    return app_paths.profile_storage_dir() / app_paths.PROFILES_SUBDIR / f"{profile_id}.json"


def load_profile_bundle(profile_id: str) -> ProfileBundle:
    profile_dir = _profile_dir(profile_id)
    if (profile_dir / PROFILE_JSON).is_file():
        meta = _read_json(profile_dir / PROFILE_JSON)
        configurations: list[Configuration] = []
        config_dir = profile_dir / CONFIGURATIONS_DIR
        loaded_by_id: dict[str, Configuration] = {}
        if config_dir.is_dir():
            for path in sorted(config_dir.glob("*.json")):
                try:
                    loaded_by_id[path.stem] = Configuration.from_dict(_read_json(path))
                except (ValueError, json.JSONDecodeError, OSError, TypeError) as exc:
                    loaded_by_id[path.stem] = Configuration(
                        id=path.stem,
                        name=f"Konfiguration {path.stem[:8]}",
                        active=False,
                        matching=None,
                        destination={"type": "local_folder", "path": ""},
                    )
                    logger.warning("Konfiguration %s übersprungen: %s", path.name, exc)
        order = meta.get("configuration_order")
        if isinstance(order, list):
            for config_id in order:
                if isinstance(config_id, str) and config_id in loaded_by_id:
                    configurations.append(loaded_by_id.pop(config_id))
        configurations.extend(loaded_by_id[config_id] for config_id in sorted(loaded_by_id))
        unmatched = UnmatchedConfiguration.from_dict(
            _read_json(profile_dir / UNMATCHED_JSON) if (profile_dir / UNMATCHED_JSON).is_file() else None
        )
        legacy_path = _resolve_legacy_profile_path(profile_id)
        legacy_profile = load_profile_for_edit(legacy_path) if legacy_path.is_file() else {}
        return ProfileBundle(
            id=str(meta.get("id") or profile_id),
            name=str(meta.get("name") or profile_id),
            active=meta.get("active", True) is not False,
            scan_model_id=str(meta.get("scan_model_id") or DEFAULT_SCAN_MODEL_ID),
            configurations=configurations,
            unmatched=unmatched,
            legacy_profile=legacy_profile,
        )

    legacy_path = _resolve_legacy_profile_path(profile_id)
    if not legacy_path.is_file():
        return _create_neutral_profile_bundle(profile_id)
    legacy = load_profile_for_edit(legacy_path)
    return load_bundle_from_legacy_profile(profile_id, legacy)


def _create_neutral_profile_bundle(profile_id: str) -> ProfileBundle:
    scan_model = get_scan_model(DEFAULT_SCAN_MODEL_ID)
    return ProfileBundle(
        id=profile_id,
        name="Rechnungen" if profile_id == "local" else profile_id,
        active=True,
        scan_model_id=DEFAULT_SCAN_MODEL_ID,
        configurations=[],
        unmatched=UnmatchedConfiguration(
            filename_pattern=default_filename_pattern(scan_model),
            destination={"type": "local_folder", "path": ""},
        ),
        legacy_profile={},
    )


def migrate_all_profiles(*, force: bool = False) -> list[str]:
    """Migrate legacy profiles to canonical storage with timestamped backups."""
    migrated: list[str] = []
    support = app_paths.profile_storage_dir()
    marker = support / MIGRATION_MARKER
    if marker.exists() and not force:
        return migrated

    backup_root = support / f"migration_backup_{_timestamp()}"
    backup_root.mkdir(parents=True, exist_ok=True)

    entries = app_paths.list_profile_entries()
    for profile_id, legacy_path, display_name in entries:
        if not legacy_path.is_file():
            continue
        backup_copy = backup_root / f"{profile_id}.json"
        shutil.copy2(legacy_path, backup_copy)

        legacy = load_profile_for_edit(legacy_path)
        bundle = load_bundle_from_legacy_profile(profile_id, legacy)
        if not bundle.configurations and profile_id == "local":
            bundle.name = display_name or bundle.name
        if not bundle.scan_model_id:
            bundle.scan_model_id = DEFAULT_SCAN_MODEL_ID
        if not bundle.unmatched.filename_pattern.components:
            bundle.unmatched.filename_pattern = default_filename_pattern(bundle.scan_model)
        save_profile_bundle(bundle)
        migrated.append(profile_id)

    marker.write_text(json.dumps({"migrated_at": _timestamp(), "profiles": migrated}, indent=2), encoding="utf-8")
    return migrated


def inventory_personal_settings(profile_id: str) -> dict[str, Any]:
    bundle = load_profile_bundle(profile_id)
    return {
        "profile_id": profile_id,
        "profile_name": bundle.name,
        "scan_model_id": bundle.scan_model_id,
        "configuration_names": [config.name for config in bundle.configurations],
        "active_configurations": [config.name for config in bundle.configurations if config.active],
        "unmatched_destination": bundle.unmatched.destination.get("path"),
    }


def compare_migrated_values(profile_id: str, backup_path: Path) -> dict[str, Any]:
    before = load_profile_for_edit(backup_path)
    after_bundle = load_profile_bundle(profile_id)
    after = compile_profile_bundle_to_legacy(after_bundle)
    return {
        "profile_name_before": before.get("profile_name"),
        "profile_name_after": after.get("profile_name"),
        "target_count_before": len((before.get("target_routing") or {}).get("targets") or []),
        "target_count_after": len((after.get("target_routing") or {}).get("targets") or []),
    }


def create_profile_bundle(*, name: str, scan_model_id: str | None = None) -> ProfileBundle:
    """Create and persist a new empty profile bundle."""
    profile_id = new_profile_id()
    resolved_model_id = scan_model_id or DEFAULT_SCAN_MODEL_ID
    scan_model = get_scan_model(resolved_model_id)
    bundle = ProfileBundle(
        id=profile_id,
        name=name.strip() or "Neues Profil",
        active=True,
        scan_model_id=resolved_model_id,
        configurations=[],
        unmatched=UnmatchedConfiguration(
            filename_pattern=default_filename_pattern(scan_model),
            destination={"type": "local_folder", "path": ""},
        ),
    )
    save_profile_bundle(bundle)
    return bundle


def duplicate_profile_bundle(source_id: str, *, name_suffix: str = " (Kopie)") -> ProfileBundle:
    """Duplicate profile metadata; destination folders are never copied or deleted."""
    source = load_profile_bundle(source_id)
    new_id = new_profile_id()
    cloned_configs: list[Configuration] = []
    for config in source.configurations:
        clone = Configuration.from_dict(config.to_dict())
        clone.id = new_configuration_id()
        cloned_configs.append(clone)
    unmatched = UnmatchedConfiguration.from_dict(source.unmatched.to_dict())
    bundle = ProfileBundle(
        id=new_id,
        name=f"{source.name}{name_suffix}",
        active=True,
        scan_model_id=source.scan_model_id,
        configurations=cloned_configs,
        unmatched=unmatched,
    )
    save_profile_bundle(bundle)
    return bundle


def delete_profile_bundle(profile_id: str) -> None:
    """Remove profile metadata only; never delete configured destination folders."""
    entries = app_paths.list_profile_entries()
    if len(entries) <= 1:
        raise ValueError("Das letzte Profil kann nicht gelöscht werden.")
    if profile_id not in {entry_id for entry_id, _, _ in entries}:
        raise ValueError(f"Unbekanntes Profil: {profile_id}")

    profile_dir = _profile_dir(profile_id)
    if profile_dir.is_dir():
        shutil.rmtree(profile_dir)

    legacy_path = _resolve_legacy_profile_path(profile_id)
    if legacy_path.is_file():
        shutil.copy2(legacy_path, _backup_path(legacy_path))
        legacy_path.unlink()

    if app_paths.resolve_active_profile_id() == profile_id:
        remaining = [entry_id for entry_id, _, _ in entries if entry_id != profile_id]
        if remaining:
            app_paths.set_active_profile_id(remaining[0])
