"""Read-only profile data for UI-v2."""

from __future__ import annotations

import logging

from invoice_tool.app_paths import resolve_active_profile_id, sanitize_profile_display_name
from invoice_tool.profile_store import list_canonical_profile_ids, load_profile_bundle
from invoice_tool.scan_models import get_scan_model
from invoice_tool.ui_v2.adapters.path_display import destination_is_missing
from invoice_tool.ui_v2.view_models import ProfileDetailVM, ProfileSummaryVM

logger = logging.getLogger(__name__)


def _feature_summary(scan_model_id: str) -> str:
    model = get_scan_model(scan_model_id)
    labels = [feature.label for feature in model.features[:5]]
    if len(model.features) > 5:
        labels.append("…")
    return ", ".join(labels) if labels else "Keine Merkmale definiert"


def list_profiles_summary() -> tuple[ProfileSummaryVM, ...]:
    active_id = resolve_active_profile_id()
    summaries: list[ProfileSummaryVM] = []
    warnings: list[str] = []

    for profile_id in list_canonical_profile_ids():
        try:
            bundle = load_profile_bundle(profile_id)
            model = get_scan_model(bundle.scan_model_id)
            summaries.append(
                ProfileSummaryVM(
                    profile_id=profile_id,
                    profile_name=sanitize_profile_display_name(bundle.name),
                    scan_model_id=bundle.scan_model_id,
                    scan_model_name=model.label,
                    is_active=profile_id == active_id,
                )
            )
        except Exception as exc:
            logger.warning("Profil %s nicht lesbar: %s", profile_id, exc)
            summaries.append(
                ProfileSummaryVM(
                    profile_id=profile_id,
                    profile_name=profile_id,
                    scan_model_id="rechnungen",
                    scan_model_name="Rechnungsdaten",
                    is_active=profile_id == active_id,
                    warnings=("Profilinformationen unvollständig.",),
                )
            )
            warnings.append(f"Profil {profile_id} unvollständig.")

    if not summaries:
        try:
            active = get_active_profile_detail()
            summaries.append(
                ProfileSummaryVM(
                    profile_id=active.profile_id,
                    profile_name=active.profile_name,
                    scan_model_id=active.scan_model_id,
                    scan_model_name=active.scan_model_name,
                    is_active=True,
                    warnings=active.warnings,
                )
            )
        except Exception:
            pass

    return tuple(summaries)


def get_active_profile_detail() -> ProfileDetailVM:
    profile_id = resolve_active_profile_id()
    warnings: list[str] = []
    try:
        bundle = load_profile_bundle(profile_id)
        model = get_scan_model(bundle.scan_model_id)
        configs = bundle.configurations
        active_count = sum(1 for item in configs if item.active)
        unmatched_path = str((bundle.unmatched.destination or {}).get("path") or "")
        unmatched_configured = bool(bundle.unmatched.name.strip()) or bool(bundle.unmatched.filename_pattern.components) or bool(unmatched_path.strip())
        unmatched_missing = unmatched_configured and destination_is_missing(bundle.unmatched.destination)
        profiles = list_profiles_summary()
        return ProfileDetailVM(
            profile_id=profile_id,
            profile_name=sanitize_profile_display_name(bundle.name),
            scan_model_id=bundle.scan_model_id,
            scan_model_name=model.label,
            feature_summary=_feature_summary(bundle.scan_model_id),
            configuration_count=len(configs),
            active_configuration_count=active_count,
            unmatched_configured=unmatched_configured,
            unmatched_destination_missing=unmatched_missing,
            profiles=profiles,
            warnings=tuple(warnings),
        )
    except Exception as exc:
        logger.warning("Profildetails nicht vollständig lesbar: %s", exc)
        warnings.append("Profilinformationen konnten nicht vollständig geladen werden.")
        return ProfileDetailVM(
            profile_id=profile_id,
            profile_name="Profil",
            scan_model_id="rechnungen",
            scan_model_name="Rechnungsdaten",
            feature_summary="—",
            configuration_count=0,
            active_configuration_count=0,
            unmatched_configured=False,
            unmatched_destination_missing=False,
            profiles=tuple(),
            warnings=tuple(warnings),
        )
