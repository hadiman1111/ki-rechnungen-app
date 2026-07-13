"""Safe profile write operations for UI-v2."""

from __future__ import annotations

import logging

from invoice_tool.app_paths import resolve_active_profile_id, set_active_profile_id
from invoice_tool.profile_store import (
    create_profile_bundle,
    delete_profile_bundle,
    duplicate_profile_bundle,
    list_canonical_profile_ids,
    load_profile_bundle,
    save_profile_bundle,
)
from invoice_tool.ui_v2.adapters.write_result import WriteOperationResult
from invoice_tool.ui_v2.validation import validate_profile_name, validate_scan_model_id

logger = logging.getLogger(__name__)


def create_profile(*, name: str, scan_model_id: str) -> WriteOperationResult:
    errors = validate_profile_name(name)
    errors.extend(validate_scan_model_id(scan_model_id))
    if errors:
        return WriteOperationResult.fail(*errors)
    try:
        bundle = create_profile_bundle(name=name.strip(), scan_model_id=scan_model_id.strip())
        return WriteOperationResult.ok(message="Profil gespeichert.", profile_id=bundle.id)
    except Exception as exc:
        logger.exception("Profil erstellen fehlgeschlagen")
        return WriteOperationResult.fail("Profil konnte nicht gespeichert werden.")


def rename_profile(profile_id: str, *, name: str) -> WriteOperationResult:
    errors = validate_profile_name(name, exclude_profile_id=profile_id)
    if errors:
        return WriteOperationResult.fail(*errors)
    try:
        bundle = load_profile_bundle(profile_id)
        bundle.name = name.strip()
        save_profile_bundle(bundle)
        return WriteOperationResult.ok(message="Profil gespeichert.", profile_id=profile_id)
    except Exception as exc:
        logger.exception("Profil umbenennen fehlgeschlagen")
        return WriteOperationResult.fail("Profil konnte nicht gespeichert werden.")


def set_profile_scan_model(profile_id: str, *, scan_model_id: str) -> WriteOperationResult:
    errors = validate_scan_model_id(scan_model_id)
    if errors:
        return WriteOperationResult.fail(*errors)
    try:
        bundle = load_profile_bundle(profile_id)
        bundle.scan_model_id = scan_model_id.strip()
        save_profile_bundle(bundle)
        return WriteOperationResult.ok(message="Profil gespeichert.", profile_id=profile_id)
    except Exception as exc:
        logger.exception("Erkennungsmodell setzen fehlgeschlagen")
        return WriteOperationResult.fail("Profil konnte nicht gespeichert werden.")


def save_profile_changes(profile_id: str, *, name: str, scan_model_id: str) -> WriteOperationResult:
    errors = validate_profile_name(name, exclude_profile_id=profile_id)
    errors.extend(validate_scan_model_id(scan_model_id))
    if errors:
        return WriteOperationResult.fail(*errors)
    try:
        bundle = load_profile_bundle(profile_id)
        bundle.name = name.strip()
        bundle.scan_model_id = scan_model_id.strip()
        save_profile_bundle(bundle)
        return WriteOperationResult.ok(message="Profil gespeichert.", profile_id=profile_id)
    except Exception as exc:
        logger.exception("Profil speichern fehlgeschlagen")
        return WriteOperationResult.fail("Profil konnte nicht gespeichert werden.")


def activate_profile(profile_id: str) -> WriteOperationResult:
    if profile_id not in list_canonical_profile_ids():
        return WriteOperationResult.fail(f"Unbekanntes Profil: {profile_id}")
    try:
        set_active_profile_id(profile_id)
        return WriteOperationResult.ok(message="Profil aktiviert.", profile_id=profile_id)
    except Exception as exc:
        logger.exception("Profil aktivieren fehlgeschlagen")
        return WriteOperationResult.fail("Profil konnte nicht aktiviert werden.")


def duplicate_profile(source_id: str, *, name_suffix: str = " (Kopie)") -> WriteOperationResult:
    try:
        bundle = duplicate_profile_bundle(source_id, name_suffix=name_suffix)
        return WriteOperationResult.ok(message="Profil dupliziert.", profile_id=bundle.id)
    except Exception as exc:
        logger.exception("Profil duplizieren fehlgeschlagen")
        return WriteOperationResult.fail("Profil konnte nicht dupliziert werden.")


def delete_profile(profile_id: str) -> WriteOperationResult:
    active_id = resolve_active_profile_id()
    profile_ids = list_canonical_profile_ids()
    if len(profile_ids) <= 1:
        return WriteOperationResult.fail("Das letzte Profil kann nicht gelöscht werden.")
    if profile_id not in profile_ids:
        return WriteOperationResult.fail(f"Unbekanntes Profil: {profile_id}")
    try:
        delete_profile_bundle(profile_id)
        message = "Profil gelöscht."
        if active_id == profile_id:
            message = "Profil gelöscht und anderes Profil aktiviert."
        return WriteOperationResult.ok(message=message)
    except ValueError as exc:
        return WriteOperationResult.fail(str(exc))
    except Exception:
        logger.exception("Profil löschen fehlgeschlagen")
        return WriteOperationResult.fail("Profil konnte nicht gelöscht werden.")


def can_delete_profile(profile_id: str) -> tuple[bool, str]:
    if len(list_canonical_profile_ids()) <= 1:
        return False, "Das letzte Profil kann nicht gelöscht werden."
    if profile_id not in list_canonical_profile_ids():
        return False, "Profil nicht gefunden."
    return True, ""
