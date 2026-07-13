"""Safe configuration write operations for UI-v2."""

from __future__ import annotations

import logging

from invoice_tool.configuration_model import (
    Configuration,
    UnmatchedConfiguration,
    default_filename_pattern,
    new_configuration_id,
)
from invoice_tool.profile_store import load_profile_bundle, save_profile_bundle
from invoice_tool.scan_models import matching_features
from invoice_tool.ui_v2.adapters.write_result import WriteOperationResult
from invoice_tool.ui_v2.draft_models import ConfigurationDraftVM
from invoice_tool.ui_v2.validation import (
    validate_bundle_for_save,
    validate_configuration_draft,
    validate_unmatched_draft,
)

logger = logging.getLogger(__name__)


def _apply_draft_to_bundle(bundle, draft: ConfigurationDraftVM) -> None:
    if draft.is_unmatched:
        bundle.unmatched = draft.to_unmatched()
        return

    config = draft.to_configuration()
    if draft.is_new:
        if not config.id:
            config.id = new_configuration_id()
        bundle.configurations.append(config)
        return

    for index, existing in enumerate(bundle.configurations):
        if existing.id == config.id:
            bundle.configurations[index] = config
            return
    bundle.configurations.append(config)


def create_configuration(profile_id: str, draft: ConfigurationDraftVM) -> WriteOperationResult:
    draft.is_new = True
    if not draft.configuration_id:
        draft.configuration_id = new_configuration_id()
    return update_configuration(profile_id, draft)


def update_configuration(profile_id: str, draft: ConfigurationDraftVM) -> WriteOperationResult:
    try:
        bundle = load_profile_bundle(profile_id)
    except Exception:
        logger.exception("Profil laden fehlgeschlagen")
        return WriteOperationResult.fail("Profil konnte nicht geladen werden.")

    if draft.is_unmatched:
        errors = validate_unmatched_draft(draft.to_unmatched(), bundle.scan_model)
    else:
        errors = validate_configuration_draft(draft.to_configuration(), bundle, is_unmatched=False)

    if errors:
        return WriteOperationResult.fail(*errors)

    _apply_draft_to_bundle(bundle, draft)
    bundle_errors = validate_bundle_for_save(bundle)
    if bundle_errors:
        return WriteOperationResult.fail(*bundle_errors)

    try:
        save_profile_bundle(bundle)
        config_id = "unmatched" if draft.is_unmatched else draft.configuration_id
        return WriteOperationResult.ok(
            message="Konfiguration gespeichert.",
            profile_id=profile_id,
            configuration_id=config_id,
        )
    except Exception:
        logger.exception("Konfiguration speichern fehlgeschlagen")
        return WriteOperationResult.fail("Konfiguration konnte nicht gespeichert werden.")


def set_configuration_active(profile_id: str, configuration_id: str, *, active: bool) -> WriteOperationResult:
    try:
        bundle = load_profile_bundle(profile_id)
    except Exception:
        return WriteOperationResult.fail("Profil konnte nicht geladen werden.")
    for config in bundle.configurations:
        if config.id == configuration_id:
            config.active = active
            break
    else:
        return WriteOperationResult.fail("Konfiguration nicht gefunden.")
    bundle_errors = validate_bundle_for_save(bundle)
    if bundle_errors and active:
        return WriteOperationResult.fail(*bundle_errors)
    try:
        save_profile_bundle(bundle)
        return WriteOperationResult.ok(message="Konfiguration gespeichert.", configuration_id=configuration_id)
    except Exception:
        logger.exception("Aktivstatus speichern fehlgeschlagen")
        return WriteOperationResult.fail("Konfiguration konnte nicht gespeichert werden.")


def reorder_configurations(profile_id: str, ordered_ids: list[str]) -> WriteOperationResult:
    try:
        bundle = load_profile_bundle(profile_id)
    except Exception:
        return WriteOperationResult.fail("Profil konnte nicht geladen werden.")
    by_id = {config.id: config for config in bundle.configurations}
    if set(ordered_ids) != set(by_id):
        return WriteOperationResult.fail("Konfigurationsreihenfolge ist ungültig.")
    bundle.configurations = [by_id[config_id] for config_id in ordered_ids]
    try:
        save_profile_bundle(bundle)
        return WriteOperationResult.ok(message="Reihenfolge gespeichert.")
    except Exception:
        logger.exception("Reihenfolge speichern fehlgeschlagen")
        return WriteOperationResult.fail("Reihenfolge konnte nicht gespeichert werden.")


def delete_configuration(profile_id: str, configuration_id: str) -> WriteOperationResult:
    try:
        bundle = load_profile_bundle(profile_id)
    except Exception:
        return WriteOperationResult.fail("Profil konnte nicht geladen werden.")
    remaining = [config for config in bundle.configurations if config.id != configuration_id]
    if len(remaining) == len(bundle.configurations):
        return WriteOperationResult.fail("Konfiguration nicht gefunden.")
    bundle.configurations = remaining
    try:
        save_profile_bundle(bundle)
        return WriteOperationResult.ok(message="Konfiguration gelöscht.")
    except Exception:
        logger.exception("Konfiguration löschen fehlgeschlagen")
        return WriteOperationResult.fail("Konfiguration konnte nicht gelöscht werden.")


def update_unmatched_configuration(profile_id: str, draft: ConfigurationDraftVM) -> WriteOperationResult:
    draft.is_unmatched = True
    draft.configuration_id = "unmatched"
    return update_configuration(profile_id, draft)


def new_configuration_draft(profile_id: str) -> ConfigurationDraftVM:
    from invoice_tool.ui_v2.draft_models import MatchingRuleDraftVM

    bundle = load_profile_bundle(profile_id)
    scan_model = bundle.scan_model
    features = matching_features(scan_model)
    feature_key = features[0].key if features else "payment_field"
    return ConfigurationDraftVM(
        configuration_id=new_configuration_id(),
        name="",
        active=True,
        matching=MatchingRuleDraftVM(feature_key=feature_key, values=[""]),
        filename_pattern=default_filename_pattern(scan_model),
        destination_path="",
        sort_index=len(bundle.configurations),
        is_new=True,
        is_unmatched=False,
    )
