"""UI-v2 validation helpers for profile and configuration drafts."""

from __future__ import annotations

import re
from pathlib import Path

from invoice_tool.configuration_model import (
    Configuration,
    FilenamePattern,
    ProfileBundle,
    UnmatchedConfiguration,
    pattern_to_template,
    preview_filename,
    validate_profile_bundle,
)
from invoice_tool.profile_store import list_canonical_profile_ids, load_profile_bundle
from invoice_tool.scan_models import ScanModel, get_scan_model, matching_features
from invoice_tool.ui_v2.adapters.path_display import resolve_destination_path
from invoice_tool.file_lifecycle import PathSafetyError, resolve_safe_target_directory

_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f{}]')


def validate_profile_name(name: str, *, exclude_profile_id: str | None = None) -> list[str]:
    cleaned = (name or "").strip()
    if not cleaned:
        return ["Profilname ist erforderlich."]
    for profile_id in list_canonical_profile_ids():
        if exclude_profile_id and profile_id == exclude_profile_id:
            continue
        try:
            existing = load_profile_bundle(profile_id)
        except Exception:
            continue
        if existing.name.strip().casefold() == cleaned.casefold():
            return [f'Profilname „{cleaned}" ist bereits vergeben.']
    return []


def validate_scan_model_id(scan_model_id: str) -> list[str]:
    resolved = (scan_model_id or "").strip()
    if not resolved:
        return ["Erkennungsmodell ist erforderlich."]
    model = get_scan_model(resolved)
    if model.id != resolved:
        return [f"Unbekanntes Erkennungsmodell: {resolved}"]
    return []


def validate_matching_rule(config: Configuration, scan_model: ScanModel) -> list[str]:
    errors: list[str] = []
    if config.matching is None:
        return ["Mindestens eine Zuordnungsregel ist erforderlich."]
    feature_key = (config.matching.feature_key or "").strip()
    if not feature_key:
        errors.append("Zuordnungsfeld fehlt.")
    elif feature_key not in scan_model.feature_keys():
        errors.append(f"Unbekanntes Zuordnungsfeld: {feature_key}")
    elif not any(feature.key == feature_key for feature in matching_features(scan_model)):
        errors.append(f'Feld „{feature_key}" unterstützt keine Zuordnung.')
    values = [value.strip() for value in config.matching.values if str(value or "").strip()]
    if not values:
        errors.append("Mindestens ein Zuordnungswert ist erforderlich.")
    return errors


def validate_filename_pattern(pattern: FilenamePattern, scan_model: ScanModel) -> list[str]:
    errors: list[str] = []
    if not pattern.components:
        return ["Dateinamenmuster darf nicht leer sein."]
    feature_keys = set(scan_model.feature_keys())
    has_content = False
    for component in pattern.components:
        if component.type == "system" and component.key == "extension":
            continue
        if component.type == "feature":
            if component.key not in feature_keys:
                errors.append(f"Unbekanntes Merkmal im Dateinamen: {component.key}")
            has_content = True
        elif component.type == "system" and component.key == "custom_text":
            text = (component.custom_text or "").strip()
            if text:
                has_content = True
                if _UNSAFE_FILENAME_CHARS.search(text):
                    errors.append("Dateiname enthält ungültige Zeichen.")
    if not has_content:
        errors.append("Dateinamenmuster enthält keine gültigen Bestandteile.")
    try:
        template = pattern_to_template(pattern)
        if "/" in template or "\\" in template:
            errors.append("Dateiname darf keine Pfadtrenner enthalten.")
        if template.count(".pdf") > 1:
            errors.append("Dateiname enthält mehrere Dateiendungen.")
        preview_filename(pattern, scan_model)
    except Exception as exc:
        errors.append(f"Dateinamenmuster ungültig: {exc}")
    return errors


def validate_target_folder(path: str, *, require_exists: bool = True) -> list[str]:
    cleaned = (path or "").strip()
    if not cleaned:
        return ["Zielordner ist erforderlich."]

    expanded = Path(cleaned).expanduser()
    if not expanded.is_absolute():
        from invoice_tool.ui_v2.adapters.path_display import resolve_output_root

        output_root = resolve_output_root()
        if output_root is not None:
            try:
                resolve_safe_target_directory(output_root.resolve(), cleaned)
                if require_exists:
                    resolved = resolve_safe_target_directory(output_root.resolve(), cleaned)
                    if resolved.is_dir():
                        return []
                    # Relative Zielordner unter dem Ausgangsordner werden bei Verarbeitung angelegt.
                    return []
                return []
            except PathSafetyError:
                return ["Zielordner fehlt oder ist nicht erreichbar."]

    resolved = resolve_destination_path(raw_path=cleaned)
    if require_exists and (resolved is None or not resolved.is_dir()):
        return ["Zielordner fehlt oder ist nicht erreichbar."]
    return []


def validate_configuration_name(
    name: str,
    configurations: list[Configuration],
    *,
    exclude_id: str | None = None,
) -> list[str]:
    cleaned = (name or "").strip()
    if not cleaned:
        return ["Konfigurationsname ist erforderlich."]
    for config in configurations:
        if exclude_id and config.id == exclude_id:
            continue
        if config.name.strip().casefold() == cleaned.casefold():
            return [f'Konfigurationsname „{cleaned}" ist bereits vergeben.']
    return []


def validate_configuration_draft(
    config: Configuration,
    bundle: ProfileBundle,
    *,
    is_unmatched: bool = False,
) -> list[str]:
    scan_model = bundle.scan_model
    errors: list[str] = []
    if is_unmatched:
        errors.extend(validate_filename_pattern(config.filename_pattern, scan_model))
        if config.active:
            errors.extend(validate_target_folder(str(config.destination.get("path") or "")))
        return errors

    errors.extend(validate_configuration_name(config.name, bundle.configurations, exclude_id=config.id))
    if config.active:
        errors.extend(validate_matching_rule(config, scan_model))
        errors.extend(validate_filename_pattern(config.filename_pattern, scan_model))
        errors.extend(validate_target_folder(str(config.destination.get("path") or "")))
    return errors


def validate_unmatched_draft(unmatched: UnmatchedConfiguration, scan_model: ScanModel) -> list[str]:
    errors: list[str] = []
    errors.extend(validate_filename_pattern(unmatched.filename_pattern, scan_model))
    errors.extend(validate_target_folder(str(unmatched.destination.get("path") or "")))
    return errors


def validate_bundle_for_save(bundle: ProfileBundle) -> list[str]:
    return validate_profile_bundle(bundle)
