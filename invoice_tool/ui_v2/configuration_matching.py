"""Track-B active profile/configuration matching bridge (Prompt 20/34).

Resolves the matched active configuration (or configured Unklar/fallback)
and exposes its filename pattern for Track-B preview naming.

Uses existing profile/configuration data — no private hardcodes.
Preview-only — no productive processing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Sequence

from invoice_tool.configuration_model import Configuration, pattern_to_template
from invoice_tool.matching import normalize_for_matching

logger = logging.getLogger(__name__)

MatchingConfidence = Literal["none", "low", "medium", "high"]

UNMATCHED_CONFIGURATION_ID = "unmatched"


@dataclass(frozen=True)
class ConfigurationCandidate:
    """Lightweight configuration view for Track-B matching."""

    configuration_id: str
    name: str
    active: bool = True
    is_unmatched: bool = False
    matching_feature_key: str | None = None
    matching_values: tuple[str, ...] = field(default_factory=tuple)
    filename_pattern: str | None = None


@dataclass(frozen=True)
class ConfigurationMatchResult:
    """Honest configuration match for Track-B filename rendering."""

    matched_configuration_name: str | None
    matched_configuration_id: str | None
    matched_configuration_pattern: str | None
    matched_configuration_reason: str
    matched_configuration_confidence: MatchingConfidence
    is_unmatched_fallback: bool = False
    unmatched_reason: str | None = None
    matched_payment_field: str | None = None


def _candidate_from_configuration(config: Configuration) -> ConfigurationCandidate:
    pattern = None
    try:
        pattern = pattern_to_template(config.filename_pattern)
    except Exception:  # noqa: BLE001 — matching must fail closed to unmatched
        pattern = None
    matching = config.matching
    values: tuple[str, ...] = ()
    feature_key = None
    if matching is not None:
        feature_key = str(matching.feature_key or "").strip() or None
        values = tuple(
            str(value).strip()
            for value in (matching.values or [])
            if str(value or "").strip()
        )
    return ConfigurationCandidate(
        configuration_id=str(config.id or "").strip(),
        name=str(config.name or "").strip() or str(config.id or "configuration"),
        active=bool(config.active),
        is_unmatched=False,
        matching_feature_key=feature_key,
        matching_values=values,
        filename_pattern=pattern,
    )


def load_active_configuration_candidates(
    *,
    profile_id: str | None = None,
) -> tuple[tuple[ConfigurationCandidate, ...], ConfigurationCandidate | None]:
    """Load active configurations + unmatched fallback from the profile store."""

    try:
        from invoice_tool.app_paths import resolve_active_profile_id
        from invoice_tool.profile_store import load_profile_bundle
    except Exception as exc:  # noqa: BLE001
        logger.warning("Profil-Module nicht ladbar für Matching: %s", exc)
        return (), None

    resolved = (profile_id or "").strip() or resolve_active_profile_id()
    try:
        bundle = load_profile_bundle(resolved)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Profilbundle nicht ladbar für Matching: %s", exc)
        return (), None

    active = tuple(
        _candidate_from_configuration(config)
        for config in (bundle.configurations or [])
        if bool(getattr(config, "active", False))
    )
    unmatched: ConfigurationCandidate | None = None
    try:
        unmatched_cfg = bundle.unmatched
        unmatched_pattern = None
        try:
            unmatched_pattern = pattern_to_template(unmatched_cfg.filename_pattern)
        except Exception:  # noqa: BLE001
            unmatched_pattern = None
        unmatched = ConfigurationCandidate(
            configuration_id=UNMATCHED_CONFIGURATION_ID,
            name=str(unmatched_cfg.name or "Unklar").strip() or "Unklar",
            active=True,
            is_unmatched=True,
            matching_feature_key=None,
            matching_values=(),
            filename_pattern=unmatched_pattern,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unklar-Konfiguration nicht ladbar: %s", exc)
        unmatched = None
    return active, unmatched


def _value_matches(candidate_value: str, probe: str) -> bool:
    left = normalize_for_matching(candidate_value)
    right = normalize_for_matching(probe)
    if not left or not right:
        return False
    if left == right:
        return True
    compact_left = left.replace(" ", "")
    compact_right = right.replace(" ", "")
    return compact_left == compact_right or compact_left in compact_right or compact_right in compact_left


def _text_contains_value(text: str, candidate_value: str) -> bool:
    hay = normalize_for_matching(text)
    needle = normalize_for_matching(candidate_value)
    if not hay or not needle:
        return False
    # Short codes like "ai"/"ep" are too ambiguous for free-text substring hits.
    # Require equality-style token presence (word boundary) for short needles.
    compact_hay = hay.replace(" ", "")
    compact_needle = needle.replace(" ", "")
    if len(compact_needle) <= 3:
        tokens = set(hay.split())
        return needle in tokens or compact_needle in tokens
    return needle in hay or compact_needle in compact_hay


def match_active_configuration(
    *,
    payment_field: str | None = None,
    payment_account: str | None = None,
    raw_text_head: str | None = None,
    configurations: Sequence[ConfigurationCandidate] | None = None,
    unmatched: ConfigurationCandidate | None = None,
    profile_id: str | None = None,
) -> ConfigurationMatchResult:
    """Match extraction/result signals against active configuration rules.

    Prefer explicit payment_field / payment_account equality against configured
    matching values. Optionally use raw text hits against those same values.
    If uncertain, use the configured Unklar/unmatched configuration (not a
    hardcoded business category).
    """

    active: tuple[ConfigurationCandidate, ...]
    unmatched_candidate: ConfigurationCandidate | None
    if configurations is None:
        active, unmatched_candidate = load_active_configuration_candidates(
            profile_id=profile_id
        )
    else:
        active = tuple(
            item for item in configurations if item.active and not item.is_unmatched
        )
        unmatched_candidate = unmatched

    probes = [
        str(value).strip()
        for value in (payment_field, payment_account)
        if str(value or "").strip()
    ]
    text = str(raw_text_head or "")

    direct_hits: list[tuple[ConfigurationCandidate, str, str]] = []
    text_hits: list[tuple[ConfigurationCandidate, str]] = []
    for config in active:
        if not config.matching_values:
            continue
        for configured_value in config.matching_values:
            for probe in probes:
                if _value_matches(configured_value, probe):
                    direct_hits.append((config, configured_value, probe))
                    break
            else:
                continue
            break
        if any(hit[0].configuration_id == config.configuration_id for hit in direct_hits):
            continue
        # Free-text body matching is unsafe for payment_field rules: recipient /
        # letterhead names (e.g. "Architektur & Innenarchitektur") collide with
        # payment routing values. Only non-payment features may use text hits.
        feature = (config.matching_feature_key or "").strip().lower()
        if text and feature and feature not in {"payment_field", "payment_account", "konto"}:
            for configured_value in config.matching_values:
                if _text_contains_value(text, configured_value):
                    text_hits.append((config, configured_value))
                    break

    if len(direct_hits) == 1:
        config, matched_value, probe = direct_hits[0]
        return ConfigurationMatchResult(
            matched_configuration_name=config.name,
            matched_configuration_id=config.configuration_id,
            matched_configuration_pattern=config.filename_pattern,
            matched_configuration_reason=(
                f"Aktive Konfiguration „{config.name}“ über "
                f"{config.matching_feature_key or 'Merkmal'}="
                f"„{matched_value}“ (Signal: {probe})."
            ),
            matched_configuration_confidence="high",
            is_unmatched_fallback=False,
            matched_payment_field=matched_value,
        )

    if len(direct_hits) > 1:
        names = ", ".join(sorted({hit[0].name for hit in direct_hits}))
        return _unmatched_result(
            unmatched_candidate,
            reason=(
                f"Mehrdeutige Konfigurations-Treffer ({names}) — "
                "Unklar/Fallback-Konfiguration verwendet."
            ),
            confidence="low",
        )

    if len(text_hits) == 1:
        config, matched_value = text_hits[0]
        return ConfigurationMatchResult(
            matched_configuration_name=config.name,
            matched_configuration_id=config.configuration_id,
            matched_configuration_pattern=config.filename_pattern,
            matched_configuration_reason=(
                f"Aktive Konfiguration „{config.name}“ über Texttreffer "
                f"auf Erkennungswert „{matched_value}“."
            ),
            matched_configuration_confidence="medium",
            is_unmatched_fallback=False,
            matched_payment_field=matched_value,
        )

    if len(text_hits) > 1:
        names = ", ".join(sorted({hit[0].name for hit in text_hits}))
        return _unmatched_result(
            unmatched_candidate,
            reason=(
                f"Mehrdeutige Text-Treffer ({names}) — "
                "Unklar/Fallback-Konfiguration verwendet."
            ),
            confidence="low",
        )

    if not active and unmatched_candidate is None:
        return ConfigurationMatchResult(
            matched_configuration_name=None,
            matched_configuration_id=None,
            matched_configuration_pattern=None,
            matched_configuration_reason=(
                "Keine aktiven Konfigurationen und kein Unklar-Fallback verfügbar."
            ),
            matched_configuration_confidence="none",
            is_unmatched_fallback=True,
            unmatched_reason="no_active_configuration_or_unmatched",
        )

    return _unmatched_result(
        unmatched_candidate,
        reason=_precise_unmatched_reason(
            payment_field=payment_field,
            payment_account=payment_account,
            active=active,
        ),
        confidence="low" if unmatched_candidate and unmatched_candidate.filename_pattern else "none",
    )


def _precise_unmatched_reason(
    *,
    payment_field: str | None,
    payment_account: str | None,
    active: Sequence[ConfigurationCandidate],
) -> str:
    """Explain Unklar fallback precisely for review/manifest."""

    signal = str(payment_field or payment_account or "").strip()
    if not signal:
        return (
            "payment_field fehlt — keine Zahlungsart erkannt; "
            "konfiguriertes Unklar/Fallback verwendet."
        )
    signal_l = signal.lower()
    active_values = {
        normalize_for_matching(value)
        for config in active
        for value in config.matching_values
    }
    if signal_l in {"paypal"}:
        return (
            "payment_field paypal erkannt, keine aktive PayPal-Konfiguration "
            "gematcht — Unklar/Fallback verwendet."
        )
    if signal_l in {"card", "credit_card", "card_generic"}:
        return (
            "payment_field card (Kreditkarte generisch) erkannt; kein AMEX-Nachweis "
            "und keine passende aktive Konfiguration — Unklar/Fallback "
            "(nicht American Express)."
        )
    if signal_l in {"amex", "american express"} and "amex" not in active_values:
        return (
            "payment_field amex erkannt, aber keine aktive American-Express-"
            "Konfiguration verfügbar — Unklar/Fallback verwendet."
        )
    return (
        f"payment_field „{signal}“ erkannt, aber keine aktive Konfiguration "
        "erfüllt die Bedingungen — Unklar/Fallback verwendet."
    )


def _unmatched_result(
    unmatched: ConfigurationCandidate | None,
    *,
    reason: str,
    confidence: MatchingConfidence,
) -> ConfigurationMatchResult:
    if unmatched is None:
        return ConfigurationMatchResult(
            matched_configuration_name=None,
            matched_configuration_id=None,
            matched_configuration_pattern=None,
            matched_configuration_reason=reason,
            matched_configuration_confidence="none",
            is_unmatched_fallback=True,
            unmatched_reason=reason,
        )
    return ConfigurationMatchResult(
        matched_configuration_name=unmatched.name,
        matched_configuration_id=unmatched.configuration_id,
        matched_configuration_pattern=unmatched.filename_pattern,
        matched_configuration_reason=reason,
        matched_configuration_confidence=confidence,
        is_unmatched_fallback=True,
        unmatched_reason=reason,
        matched_payment_field=None,
    )


def configurations_from_raw(
    items: Iterable[Mapping[str, Any] | ConfigurationCandidate],
) -> tuple[ConfigurationCandidate, ...]:
    """Test helper: build candidates from dict-like payloads."""

    out: list[ConfigurationCandidate] = []
    for item in items:
        if isinstance(item, ConfigurationCandidate):
            out.append(item)
            continue
        values = item.get("matching_values") or item.get("values") or ()
        out.append(
            ConfigurationCandidate(
                configuration_id=str(item.get("configuration_id") or item.get("id") or ""),
                name=str(item.get("name") or ""),
                active=bool(item.get("active", True)),
                is_unmatched=bool(item.get("is_unmatched", False)),
                matching_feature_key=(
                    str(item.get("matching_feature_key") or item.get("feature_key") or "").strip()
                    or None
                ),
                matching_values=tuple(str(v).strip() for v in values if str(v or "").strip()),
                filename_pattern=(
                    str(item.get("filename_pattern") or item.get("pattern") or "").strip()
                    or None
                ),
            )
        )
    return tuple(out)


__all__ = (
    "ConfigurationCandidate",
    "ConfigurationMatchResult",
    "UNMATCHED_CONFIGURATION_ID",
    "configurations_from_raw",
    "load_active_configuration_candidates",
    "match_active_configuration",
)
