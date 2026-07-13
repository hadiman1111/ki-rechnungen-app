"""Read-only configuration data for UI-v2."""

from __future__ import annotations

import logging

from invoice_tool.app_paths import resolve_active_profile_id
from invoice_tool.configuration_model import (
    Configuration,
    matching_summary,
    pattern_to_template,
    preview_filename,
)
from invoice_tool.profile_store import load_profile_bundle
from invoice_tool.ui_v2.adapters.path_display import (
    destination_is_missing,
    destination_summary_for_display,
)
from invoice_tool.ui_v2.view_models import ConfigurationSummaryVM, ConfigurationsPageVM, DestinationSummaryVM

logger = logging.getLogger(__name__)


def _configuration_vm(config: Configuration, *, index: int, scan_model) -> ConfigurationSummaryVM:
    warnings: list[str] = []
    dest_display = destination_summary_for_display(config.destination)
    dest_missing = destination_is_missing(config.destination)

    feature_label: str | None = None
    rule_values: tuple[str, ...] = ()
    if config.matching is not None:
        feature = scan_model.get_feature(config.matching.feature_key)
        feature_label = feature.label if feature else config.matching.feature_key
        rule_values = tuple(value.strip() for value in config.matching.values if str(value or "").strip())

    try:
        matching = matching_summary(config, scan_model)
    except Exception as exc:
        logger.warning("Matching-Zusammenfassung für %s fehlgeschlagen: %s", config.id, exc)
        matching = "Zuordnung nicht verfügbar"
        warnings.append("Zuordnungsregel konnte nicht gelesen werden.")

    try:
        pattern = pattern_to_template(config.filename_pattern)
    except Exception:
        pattern = "—"
        warnings.append("Dateinamenmuster nicht verfügbar.")

    example: str | None = None
    try:
        example = preview_filename(config.filename_pattern, scan_model)
    except Exception:
        example = None

    return ConfigurationSummaryVM(
        configuration_id=config.id,
        name=config.name,
        active=config.active,
        matching_summary=matching,
        matching_feature_label=feature_label,
        matching_values=rule_values,
        filename_pattern_summary=pattern,
        filename_example=example,
        destination_summary=dest_display,
        destination_missing=dest_missing,
        sort_index=index,
        warnings=tuple(warnings),
    )


def list_configuration_summaries() -> tuple[ConfigurationSummaryVM, ...]:
    page = get_configurations_page_vm()
    items = list(page.configurations)
    if page.unmatched is not None:
        items.append(page.unmatched)
    return tuple(items)


def get_unmatched_configuration_summary() -> ConfigurationSummaryVM | None:
    return get_configurations_page_vm().unmatched


def get_destination_summaries() -> tuple[DestinationSummaryVM, ...]:
    page = get_configurations_page_vm()
    destinations: list[DestinationSummaryVM] = []
    for config in page.configurations:
        destinations.append(
            DestinationSummaryVM(
                configuration_name=config.name,
                destination_summary=config.destination_summary,
                destination_missing=config.destination_missing,
            )
        )
    if page.unmatched is not None:
        destinations.append(
            DestinationSummaryVM(
                configuration_name=page.unmatched.name,
                destination_summary=page.unmatched.destination_summary,
                destination_missing=page.unmatched.destination_missing,
                is_unmatched=True,
            )
        )
    return tuple(destinations)


def get_configurations_page_vm() -> ConfigurationsPageVM:
    profile_id = resolve_active_profile_id()
    warnings: list[str] = []
    try:
        bundle = load_profile_bundle(profile_id)
        scan_model = bundle.scan_model
        configs = [
            _configuration_vm(config, index=index, scan_model=scan_model)
            for index, config in enumerate(bundle.configurations)
        ]
        unmatched_vm: ConfigurationSummaryVM | None = None
        unmatched_path = str((bundle.unmatched.destination or {}).get("path") or "")
        unmatched_setup = bool((bundle.unmatched.name or "").strip()) or bool(bundle.unmatched.filename_pattern.components)
        unmatched_present = unmatched_setup or bool(unmatched_path.strip())
        if unmatched_present:
            unmatched_vm = ConfigurationSummaryVM(
                configuration_id="unmatched",
                name=bundle.unmatched.name or "Nicht zugeordnete Dokumente",
                active=True,
                matching_summary="Dokumente ohne eindeutige Zuordnung",
                filename_pattern_summary=pattern_to_template(bundle.unmatched.filename_pattern),
                filename_example=preview_filename(bundle.unmatched.filename_pattern, scan_model),
                destination_summary=destination_summary_for_display(bundle.unmatched.destination),
                destination_missing=destination_is_missing(bundle.unmatched.destination),
                sort_index=len(configs),
            )

        missing_count = sum(1 for item in configs if item.destination_missing)
        if unmatched_vm and unmatched_vm.destination_missing:
            missing_count += 1

        return ConfigurationsPageVM(
            profile_name=bundle.name,
            configurations=tuple(configs),
            unmatched=unmatched_vm,
            total_count=len(configs),
            active_count=sum(1 for item in configs if item.active),
            missing_destination_count=missing_count,
            unmatched_present=unmatched_present,
            warnings=tuple(warnings),
        )
    except Exception as exc:
        logger.warning("Konfigurationsliste nicht lesbar: %s", exc)
        warnings.append("Konfigurationen konnten nicht vollständig geladen werden.")
        return ConfigurationsPageVM(
            profile_name="Profil",
            configurations=tuple(),
            unmatched=None,
            total_count=0,
            active_count=0,
            missing_destination_count=0,
            unmatched_present=False,
            warnings=tuple(warnings),
        )
