"""Track-B duplicate active-configuration detection and safe remediation.

UI-v2 / profile-config state only. Never calls run_once, never mutates input
PDFs, never writes production finals, never touches Track-A runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from invoice_tool.configuration_model import (
    Configuration,
    pattern_to_template,
    validate_profile_bundle,
)
from invoice_tool.profile_store import load_profile_bundle, save_profile_bundle
from invoice_tool.target_routing import normalize_routing_value

ACTION_SHOW_DUPLICATES = "Doppelte Konfigurationen anzeigen"
ACTION_DEACTIVATE_EXACT_DUPLICATES = "Exakte Duplikate deaktivieren"

CODE_DUPLICATE_EXACT_ACTIVE_CONFIG = "duplicate_exact_active_config"
CODE_DUPLICATE_NAME_WARNING = "duplicate_name_warning"
CODE_CROSS_CONFIG_VALUE_CONFLICT = "cross_config_value_conflict"
CODE_INTRA_CONFIG_ALIAS_COLLISION = "intra_config_alias_collision"
CODE_PROFILE_UNSAFE_EXACT_DUPLICATES = "profile_unsafe_exact_duplicates"

MSG_PROFILE_ISSUE_PREFIX = (
    "Profilproblem (unabhängig vom aktuellen Entwurf): "
)
MSG_EXACT_DUPLICATE = "Exakte aktive Duplikate"
MSG_REMEDIATION_REQUIRED = (
    "Profil enthält exakte aktive Duplikate — bitte zuerst "
    f"„{ACTION_DEACTIVATE_EXACT_DUPLICATES}“ ausführen."
)
MSG_REMEDIATION_REQUIRES_CLICK = (
    "Exakte Duplikate deaktivieren erfordert einen expliziten Klick."
)
MSG_REMEDIATION_DONE = "Exakte Duplikate deaktiviert (nur UI-v2 Profilzustand)."
MSG_NO_EXACT_DUPLICATES = "Keine exakten aktiven Duplikate gefunden."
MSG_CALLED_RUN_ONCE = False

CONTROLLED_OUTPUT_ROOT = Path(
    "/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output"
).expanduser().resolve()


@dataclass(frozen=True)
class ActiveConfigSnapshot:
    configuration_id: str
    name: str
    active: bool
    feature_key: str
    operator: str
    values: tuple[str, ...]
    destination_path: str
    filename_pattern: str

    @property
    def condition_text(self) -> str:
        joined = ", ".join(self.values)
        return f"{self.feature_key} {self.operator} {joined}".strip()

    @property
    def stable_key(self) -> tuple[str, str, str, str]:
        """name + condition + target + filename_pattern (normalized)."""

        values_key = "|".join(
            sorted(
                normalize_routing_value(v, case_sensitive=False)
                for v in self.values
                if str(v or "").strip()
            )
        )
        condition = f"{self.feature_key}|{self.operator}|{values_key}"
        return (
            self.name.strip().casefold(),
            condition,
            self.destination_path.strip(),
            self.filename_pattern.strip(),
        )


@dataclass(frozen=True)
class DuplicateFinding:
    code: str
    message: str
    affected_names: tuple[str, ...] = ()
    affected_ids: tuple[str, ...] = ()
    blocking_for_unrelated_save: bool = False


@dataclass(frozen=True)
class DuplicateAnalysis:
    snapshots: tuple[ActiveConfigSnapshot, ...] = ()
    findings: tuple[DuplicateFinding, ...] = ()
    exact_duplicate_groups: tuple[tuple[ActiveConfigSnapshot, ...], ...] = ()
    profile_globally_unsafe: bool = False

    @property
    def has_exact_duplicates(self) -> bool:
        return bool(self.exact_duplicate_groups)

    def report_text(self) -> str:
        lines = ["# Doppelte / problematische aktive Konfigurationen", ""]
        if not self.findings:
            lines.append("Keine Duplikat-/Alias-Probleme erkannt.")
            return "\n".join(lines)
        for finding in self.findings:
            names = ", ".join(finding.affected_names) or "—"
            lines.append(f"- [{finding.code}] {finding.message}")
            lines.append(f"  betroffen: {names}")
        if self.profile_globally_unsafe:
            lines.append("")
            lines.append(MSG_REMEDIATION_REQUIRED)
        return "\n".join(lines)


@dataclass(frozen=True)
class RemediationResult:
    ok: bool
    message: str
    deactivated_ids: tuple[str, ...] = ()
    called_run_once: bool = False
    mutated_input: bool = False
    wrote_final_pdfs: bool = False
    affected_ui_v2_config_state_only: bool = True
    errors: tuple[str, ...] = ()


def _destination_path(config: Configuration | Mapping[str, Any]) -> str:
    if isinstance(config, Configuration):
        dest = config.destination or {}
        return str(dest.get("path") or "").strip()
    dest = config.get("destination") or {}
    if isinstance(dest, Mapping):
        return str(dest.get("path") or "").strip()
    return str(config.get("destination_path") or "").strip()


def _filename_pattern_text(config: Configuration | Mapping[str, Any]) -> str:
    if isinstance(config, Configuration):
        try:
            return pattern_to_template(config.filename_pattern)
        except Exception:  # noqa: BLE001
            return ""
    raw = config.get("filename_pattern") or config.get("proposed_filename_pattern") or ""
    if isinstance(raw, str):
        return raw.strip()
    return str(raw or "").strip()


def snapshot_configuration(config: Configuration | Mapping[str, Any] | Any) -> ActiveConfigSnapshot | None:
    if isinstance(config, Configuration):
        if config.matching is None:
            return None
        return ActiveConfigSnapshot(
            configuration_id=str(config.id or ""),
            name=str(config.name or ""),
            active=bool(config.active),
            feature_key=str(config.matching.feature_key or "").strip(),
            operator=str(config.matching.operator or "ist").strip() or "ist",
            values=tuple(str(v) for v in config.matching.values if str(v or "").strip()),
            destination_path=_destination_path(config),
            filename_pattern=_filename_pattern_text(config),
        )
    if isinstance(config, Mapping):
        matching = config.get("matching") or {}
        if not isinstance(matching, Mapping):
            matching = {}
        feature = str(
            matching.get("feature_key")
            or config.get("matching_feature_key")
            or config.get("feature_key")
            or ""
        ).strip()
        operator = str(
            matching.get("operator")
            or config.get("matching_operator")
            or config.get("operator")
            or "ist"
        ).strip() or "ist"
        raw_values = (
            matching.get("values")
            or config.get("matching_values")
            or config.get("values")
            or ()
        )
        values = tuple(str(v) for v in raw_values if str(v or "").strip())
        return ActiveConfigSnapshot(
            configuration_id=str(
                config.get("configuration_id") or config.get("id") or ""
            ),
            name=str(config.get("name") or config.get("configuration_name") or ""),
            active=bool(config.get("active", True)),
            feature_key=feature,
            operator=operator,
            values=values,
            destination_path=_destination_path(config),
            filename_pattern=_filename_pattern_text(config),
        )

    # ConfigurationCandidate / other attribute-bearing objects
    if bool(getattr(config, "is_unmatched", False)):
        return None
    feature = str(
        getattr(config, "matching_feature_key", None)
        or getattr(config, "feature_key", None)
        or ""
    ).strip()
    operator = str(
        getattr(config, "matching_operator", None)
        or getattr(config, "operator", None)
        or "ist"
    ).strip() or "ist"
    raw_values = getattr(config, "matching_values", None) or getattr(
        config, "values", None
    ) or ()
    values = tuple(str(v) for v in raw_values if str(v or "").strip())
    pattern = str(
        getattr(config, "filename_pattern", None)
        or getattr(config, "matched_configuration_pattern", None)
        or ""
    ).strip()
    return ActiveConfigSnapshot(
        configuration_id=str(
            getattr(config, "configuration_id", None)
            or getattr(config, "id", None)
            or ""
        ),
        name=str(
            getattr(config, "name", None)
            or getattr(config, "configuration_name", None)
            or ""
        ),
        active=bool(getattr(config, "active", True)),
        feature_key=feature,
        operator=operator,
        values=values,
        destination_path=str(
            getattr(config, "destination_path", None)
            or getattr(config, "planned_path", None)
            or ""
        ).strip(),
        filename_pattern=pattern,
    )


def analyze_active_configuration_duplicates(
    configurations: Sequence[Configuration | Mapping[str, Any]],
) -> DuplicateAnalysis:
    """Detect exact duplicates, name warnings, and cross-config value conflicts."""

    snapshots: list[ActiveConfigSnapshot] = []
    for item in configurations:
        snap = snapshot_configuration(item)
        if snap is None or not snap.active:
            continue
        if not snap.feature_key or not snap.values:
            continue
        snapshots.append(snap)

    findings: list[DuplicateFinding] = []
    exact_groups: list[tuple[ActiveConfigSnapshot, ...]] = []

    by_stable: dict[tuple[str, str, str, str], list[ActiveConfigSnapshot]] = {}
    for snap in snapshots:
        by_stable.setdefault(snap.stable_key, []).append(snap)
    for group in by_stable.values():
        if len(group) < 2:
            continue
        exact_groups.append(tuple(group))
        names = tuple(item.name for item in group)
        ids = tuple(item.configuration_id for item in group)
        findings.append(
            DuplicateFinding(
                code=CODE_DUPLICATE_EXACT_ACTIVE_CONFIG,
                message=(
                    f"{MSG_EXACT_DUPLICATE} für „{group[0].name}“ "
                    f"(Bedingung: {group[0].condition_text})."
                ),
                affected_names=names,
                affected_ids=ids,
                blocking_for_unrelated_save=True,
            )
        )

    by_name: dict[str, list[ActiveConfigSnapshot]] = {}
    for snap in snapshots:
        by_name.setdefault(snap.name.strip().casefold(), []).append(snap)
    for group in by_name.values():
        if len(group) < 2:
            continue
        # Skip if already reported as exact duplicates.
        stable_keys = {item.stable_key for item in group}
        if len(stable_keys) == 1:
            continue
        findings.append(
            DuplicateFinding(
                code=CODE_DUPLICATE_NAME_WARNING,
                message=(
                    f"Gleicher Konfigurationsname „{group[0].name}“, "
                    "aber unterschiedliche Bedingung/Ziel/Muster — Warnung, "
                    "nicht zwingend blockierend."
                ),
                affected_names=tuple(item.name for item in group),
                affected_ids=tuple(item.configuration_id for item in group),
                blocking_for_unrelated_save=False,
            )
        )

    # Cross-config normalized matching-value conflicts (real duplicates).
    value_owners: dict[tuple[str, str], list[ActiveConfigSnapshot]] = {}
    for snap in snapshots:
        seen_norm: set[str] = set()
        for raw in snap.values:
            norm = normalize_routing_value(raw, case_sensitive=False)
            if not norm or norm in seen_norm:
                # Intra-config alias collision (e.g. privat + Privat).
                if norm and norm in seen_norm:
                    findings.append(
                        DuplicateFinding(
                            code=CODE_INTRA_CONFIG_ALIAS_COLLISION,
                            message=(
                                f"Alias-Kollision in „{snap.name}“: "
                                f"mehrere Werte normalisieren auf „{norm}“ "
                                f"(Rohwert „{raw}“). Dies ist ein Profilhinweis "
                                "und blockiert keinen unrelated PayPal-Entwurf."
                            ),
                            affected_names=(snap.name,),
                            affected_ids=(snap.configuration_id,),
                            blocking_for_unrelated_save=False,
                        )
                    )
                continue
            seen_norm.add(norm)
            value_owners.setdefault((snap.feature_key, norm), []).append(snap)

    for (feature, norm), owners in value_owners.items():
        unique_ids = {item.configuration_id for item in owners}
        if len(unique_ids) < 2:
            continue
        names = tuple(dict.fromkeys(item.name for item in owners))
        findings.append(
            DuplicateFinding(
                code=CODE_CROSS_CONFIG_VALUE_CONFLICT,
                message=(
                    f"Doppelte aktive Regel für „{norm}“ "
                    f"(Merkmal {feature}) in: {', '.join(names)}."
                ),
                affected_names=names,
                affected_ids=tuple(unique_ids),
                blocking_for_unrelated_save=True,
            )
        )

    # Deduplicate findings by (code, message, names)
    deduped: list[DuplicateFinding] = []
    seen_keys: set[tuple[Any, ...]] = set()
    for finding in findings:
        key = (finding.code, finding.message, finding.affected_names)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(finding)

    globally_unsafe = any(
        f.code == CODE_DUPLICATE_EXACT_ACTIVE_CONFIG for f in deduped
    )
    if globally_unsafe:
        deduped.append(
            DuplicateFinding(
                code=CODE_PROFILE_UNSAFE_EXACT_DUPLICATES,
                message=MSG_REMEDIATION_REQUIRED,
                affected_names=tuple(
                    name
                    for group in exact_groups
                    for name in (item.name for item in group)
                ),
                blocking_for_unrelated_save=True,
            )
        )

    return DuplicateAnalysis(
        snapshots=tuple(snapshots),
        findings=tuple(deduped),
        exact_duplicate_groups=tuple(exact_groups),
        profile_globally_unsafe=globally_unsafe,
    )


def is_intra_config_or_alias_bundle_error(message: str) -> bool:
    """True for known false-positive / alias-only bundle validation noise."""

    text = str(message or "").strip()
    lower = text.casefold()
    if "doppelter routing-wert" in lower:
        return True
    if "doppelte aktive regel" not in lower:
        return False
    # Pattern: … in "Privat" und "Privat" (same display name twice)
    if " und " not in text:
        return False
    try:
        # Extract the two quoted config names at the end.
        parts = text.split(" in ", 1)
        if len(parts) != 2:
            return False
        rhs = parts[1]
        if " und " not in rhs:
            return False
        left, right = rhs.split(" und ", 1)
        left_name = left.strip().strip('"').strip("„”")
        right_name = right.strip().strip('"').strip("„”")
        return bool(left_name) and left_name.casefold() == right_name.casefold()
    except Exception:  # noqa: BLE001
        return False


def filter_bundle_errors_for_unrelated_rule_save(
    bundle_errors: Sequence[str],
    *,
    draft_name: str | None,
    draft_values: Sequence[str],
    analysis: DuplicateAnalysis | None = None,
) -> tuple[str, ...]:
    """Keep only errors that truly block saving an unrelated draft (e.g. PayPal)."""

    draft_norms = {
        normalize_routing_value(v, case_sensitive=False)
        for v in draft_values
        if str(v or "").strip()
    }
    draft_name_l = (draft_name or "").strip().casefold()
    blocking: list[str] = []

    if analysis is not None and analysis.profile_globally_unsafe:
        # Exact duplicate configs make profile state unsafe until remediated.
        blocking.append(MSG_REMEDIATION_REQUIRED)
        for finding in analysis.findings:
            if finding.code == CODE_DUPLICATE_EXACT_ACTIVE_CONFIG:
                blocking.append(finding.message)

    for err in bundle_errors:
        if is_intra_config_or_alias_bundle_error(err):
            continue
        lower = err.casefold()
        # Cross-config routing conflicts: block only if they involve the draft.
        if "mehreren aktiven zielordnern" in lower or "doppelte aktive regel" in lower:
            involves_draft = False
            if draft_name_l and draft_name_l in lower:
                involves_draft = True
            for norm in draft_norms:
                if norm and norm in lower:
                    involves_draft = True
                    break
            if involves_draft:
                blocking.append(err)
            # Unrelated cross-config conflicts are profile issues, not PayPal blockers,
            # unless exact duplicates made the profile globally unsafe (handled above).
            continue
        # Keep other structural bundle errors (missing destinations etc.).
        blocking.append(err)

    # Deduplicate while preserving order.
    return tuple(dict.fromkeys(blocking))


def profile_issue_warnings_for_unrelated_save(
    bundle_errors: Sequence[str],
    *,
    analysis: DuplicateAnalysis | None = None,
) -> tuple[str, ...]:
    """Non-blocking profile warnings to surface while allowing an unrelated save."""

    warnings: list[str] = []
    for err in bundle_errors:
        if is_intra_config_or_alias_bundle_error(err):
            warnings.append(MSG_PROFILE_ISSUE_PREFIX + err)
    if analysis is not None:
        for finding in analysis.findings:
            if finding.code in {
                CODE_INTRA_CONFIG_ALIAS_COLLISION,
                CODE_DUPLICATE_NAME_WARNING,
            }:
                warnings.append(MSG_PROFILE_ISSUE_PREFIX + finding.message)
            elif (
                finding.code == CODE_CROSS_CONFIG_VALUE_CONFLICT
                and not finding.blocking_for_unrelated_save
            ):
                warnings.append(MSG_PROFILE_ISSUE_PREFIX + finding.message)
    return tuple(dict.fromkeys(warnings))


def validate_bundle_for_track_b_rule_save(
    bundle: Any,
    *,
    draft_name: str | None,
    draft_values: Sequence[str],
    draft_configuration_id: str | None = None,
) -> tuple[str, ...]:
    """Bundle validation for Track-B rule saves — does not false-block PayPal."""

    del draft_configuration_id  # reserved for future exclude-self edits
    raw_errors = validate_profile_bundle(bundle)
    analysis = analyze_active_configuration_duplicates(bundle.configurations)
    return filter_bundle_errors_for_unrelated_rule_save(
        raw_errors,
        draft_name=draft_name,
        draft_values=draft_values,
        analysis=analysis,
    )


def deactivate_exact_duplicate_configs(
    profile_id: str,
    *,
    explicit_user_confirmation: bool = False,
) -> RemediationResult:
    """Deactivate extras in exact-duplicate groups (keep first active)."""

    if not explicit_user_confirmation:
        return RemediationResult(
            ok=False,
            message=MSG_REMEDIATION_REQUIRES_CLICK,
            errors=("requires_explicit_click",),
            called_run_once=False,
            mutated_input=False,
            wrote_final_pdfs=False,
            affected_ui_v2_config_state_only=True,
        )
    try:
        bundle = load_profile_bundle(profile_id)
    except Exception as exc:  # noqa: BLE001
        return RemediationResult(
            ok=False,
            message=f"Profil konnte nicht geladen werden: {exc}",
            errors=("profile_load_failed",),
        )

    analysis = analyze_active_configuration_duplicates(bundle.configurations)
    if not analysis.exact_duplicate_groups:
        return RemediationResult(
            ok=True,
            message=MSG_NO_EXACT_DUPLICATES,
            called_run_once=False,
            mutated_input=False,
            wrote_final_pdfs=False,
            affected_ui_v2_config_state_only=True,
        )

    deactivate_ids: set[str] = set()
    for group in analysis.exact_duplicate_groups:
        # Keep the first; deactivate the rest.
        for item in group[1:]:
            if item.configuration_id:
                deactivate_ids.add(item.configuration_id)

    if not deactivate_ids:
        return RemediationResult(
            ok=True,
            message=MSG_NO_EXACT_DUPLICATES,
            affected_ui_v2_config_state_only=True,
        )

    for config in bundle.configurations:
        if config.id in deactivate_ids:
            config.active = False

    try:
        save_profile_bundle(bundle)
    except Exception as exc:  # noqa: BLE001
        return RemediationResult(
            ok=False,
            message=f"Speichern fehlgeschlagen: {exc}",
            errors=("save_failed",),
        )

    return RemediationResult(
        ok=True,
        message=MSG_REMEDIATION_DONE
        + f" Deaktiviert: {', '.join(sorted(deactivate_ids))}.",
        deactivated_ids=tuple(sorted(deactivate_ids)),
        called_run_once=False,
        mutated_input=False,
        wrote_final_pdfs=False,
        affected_ui_v2_config_state_only=True,
    )


def is_controlled_output_target(path: str | Path | None) -> bool:
    """True when path is the controlled smoke output root or a child thereof."""

    raw = str(path or "").strip()
    if not raw:
        return False
    try:
        resolved = Path(raw).expanduser().resolve()
    except Exception:  # noqa: BLE001
        return False
    root = CONTROLLED_OUTPUT_ROOT
    if resolved == root:
        return True
    try:
        resolved.relative_to(root)
        return True
    except ValueError:
        return False


def controlled_target_missing_message(path: str | Path | None) -> str:
    raw = str(path or "").strip()
    if not raw:
        return (
            "Zielordner fehlt — für PayPal-Smoke bitte den kontrollierten "
            f"Output-Ordner setzen ({CONTROLLED_OUTPUT_ROOT})."
        )
    return (
        f"Zielordner „{raw}“ ist kein kontrollierter Smoke-Output "
        f"(erwartet unter {CONTROLLED_OUTPUT_ROOT})."
    )


__all__ = (
    "ACTION_DEACTIVATE_EXACT_DUPLICATES",
    "ACTION_SHOW_DUPLICATES",
    "ActiveConfigSnapshot",
    "CODE_CROSS_CONFIG_VALUE_CONFLICT",
    "CODE_DUPLICATE_EXACT_ACTIVE_CONFIG",
    "CODE_DUPLICATE_NAME_WARNING",
    "CODE_INTRA_CONFIG_ALIAS_COLLISION",
    "CODE_PROFILE_UNSAFE_EXACT_DUPLICATES",
    "CONTROLLED_OUTPUT_ROOT",
    "DuplicateAnalysis",
    "DuplicateFinding",
    "MSG_EXACT_DUPLICATE",
    "MSG_NO_EXACT_DUPLICATES",
    "MSG_PROFILE_ISSUE_PREFIX",
    "MSG_REMEDIATION_DONE",
    "MSG_REMEDIATION_REQUIRED",
    "MSG_REMEDIATION_REQUIRES_CLICK",
    "RemediationResult",
    "analyze_active_configuration_duplicates",
    "controlled_target_missing_message",
    "deactivate_exact_duplicate_configs",
    "filter_bundle_errors_for_unrelated_rule_save",
    "is_controlled_output_target",
    "is_intra_config_or_alias_bundle_error",
    "profile_issue_warnings_for_unrelated_save",
    "snapshot_configuration",
    "validate_bundle_for_track_b_rule_save",
)
