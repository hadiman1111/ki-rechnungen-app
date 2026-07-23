"""Track-B active profile/configuration matching (Prompt 22/34).

Resolves the matched active configuration (or configured Unklar/fallback)
from configured matching conditions — no private/category hardcodes.

Preview-only — no productive processing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Sequence

from invoice_tool.configuration_model import Configuration, pattern_to_template
from invoice_tool.matching import normalize_for_matching
from invoice_tool.ui_v2.configuration_guidance import (
    derive_configuration_coverage_guidance,
)

logger = logging.getLogger(__name__)

MatchingConfidence = Literal["none", "low", "medium", "high"]

UNMATCHED_CONFIGURATION_ID = "unmatched"

_CONFIDENCE_RANK: dict[str, int] = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
}

_PAYMENT_FEATURE_KEYS = frozenset(
    {"payment_field", "payment_account", "konto", "zahlungsart"}
)
_GENERIC_CARD_VALUES = frozenset(
    {"card", "credit_card", "card_generic", "kreditkarte", "credit card"}
)
_PAYPAL_VALUES = frozenset({"paypal", "pay pal"})
_AMEX_VALUES = frozenset({"amex", "american express", "americanexpress"})


@dataclass(frozen=True)
class ConfigurationCandidate:
    """Lightweight configuration view for Track-B matching."""

    configuration_id: str
    name: str
    active: bool = True
    is_unmatched: bool = False
    matching_feature_key: str | None = None
    matching_operator: str = "ist"
    matching_values: tuple[str, ...] = field(default_factory=tuple)
    filename_pattern: str | None = None


@dataclass(frozen=True)
class ConditionResult:
    """One evaluated matching condition for a configuration candidate."""

    condition_type: str
    feature_key: str | None
    expected_value: str | None
    actual_value: str | None
    matched: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "condition_type": self.condition_type,
            "feature_key": self.feature_key,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "matched": self.matched,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EvaluatedConfigurationCandidate:
    """Full candidate evaluation for manifest / review transparency."""

    configuration_name: str
    configuration_id: str
    active: bool
    is_unmatched: bool = False
    conditions: tuple[dict[str, object], ...] = field(default_factory=tuple)
    condition_results: tuple[ConditionResult, ...] = field(default_factory=tuple)
    matched: bool = False
    reason: str = ""
    confidence: MatchingConfidence = "none"
    filename_pattern: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "configuration_name": self.configuration_name,
            "configuration_id": self.configuration_id,
            "active": self.active,
            "is_unmatched": self.is_unmatched,
            "conditions": list(self.conditions),
            "condition_results": [item.to_dict() for item in self.condition_results],
            "matched": self.matched,
            "reason": self.reason,
            "confidence": self.confidence,
            "filename_pattern": self.filename_pattern,
        }


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
    available_configurations: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    evaluated_configuration_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    unmatched_reasons: tuple[str, ...] = field(default_factory=tuple)
    condition_results: tuple[dict[str, object], ...] = field(default_factory=tuple)
    alternative_matches: tuple[dict[str, object], ...] = field(default_factory=tuple)
    missing_configuration_rule: str | None = None

    def transparency_fields(self) -> dict[str, Any]:
        """Fields to propagate into mapping / export / review."""

        guidance = derive_configuration_coverage_guidance(
            selected_payment_field=self.matched_payment_field,
            payment_account=self.matched_payment_field,
            matched_configuration_name=self.matched_configuration_name,
            evaluated_configuration_candidates=self.evaluated_configuration_candidates,
            unmatched_reasons=self.unmatched_reasons,
            is_unmatched_fallback=self.is_unmatched_fallback,
            matched_configuration_reason=self.matched_configuration_reason,
            missing_configuration_rule=self.missing_configuration_rule,
        )
        return {
            "matched_configuration_name": self.matched_configuration_name,
            "matched_configuration_id": self.matched_configuration_id,
            "matched_configuration_pattern": self.matched_configuration_pattern,
            "matched_configuration_reason": self.matched_configuration_reason,
            "matched_configuration_confidence": self.matched_configuration_confidence,
            "available_configurations": tuple(self.available_configurations),
            "evaluated_configuration_candidates": tuple(
                self.evaluated_configuration_candidates
            ),
            "unmatched_reasons": tuple(self.unmatched_reasons),
            "condition_results": tuple(self.condition_results),
            "alternative_matches": tuple(self.alternative_matches),
            "missing_configuration_rule": self.missing_configuration_rule,
            **guidance.to_export_fields(),
        }


def _candidate_from_configuration(config: Configuration) -> ConfigurationCandidate:
    pattern = None
    try:
        pattern = pattern_to_template(config.filename_pattern)
    except Exception:  # noqa: BLE001 — matching must fail closed to unmatched
        pattern = None
    matching = config.matching
    values: tuple[str, ...] = ()
    feature_key = None
    operator = "ist"
    if matching is not None:
        feature_key = str(matching.feature_key or "").strip() or None
        operator = str(matching.operator or "ist").strip() or "ist"
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
        matching_operator=operator,
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
            matching_operator="fallback",
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
    return (
        compact_left == compact_right
        or compact_left in compact_right
        or compact_right in compact_left
    )


def _text_contains_value(text: str, candidate_value: str) -> bool:
    hay = normalize_for_matching(text)
    needle = normalize_for_matching(candidate_value)
    if not hay or not needle:
        return False
    # Short codes like "ai"/"ep" are too ambiguous for free-text substring hits.
    compact_hay = hay.replace(" ", "")
    compact_needle = needle.replace(" ", "")
    if len(compact_needle) <= 3:
        tokens = set(hay.split())
        return needle in tokens or compact_needle in tokens
    return needle in hay or compact_needle in compact_hay


def _norm(value: str | None) -> str:
    return normalize_for_matching(str(value or "").strip())


def _is_amex_config(config: ConfigurationCandidate) -> bool:
    if _norm(config.configuration_id) in _AMEX_VALUES:
        return True
    if "american express" in _norm(config.name):
        return True
    return any(_norm(value) in _AMEX_VALUES for value in config.matching_values)


def _is_paypal_signal(payment_field: str | None, payment_account: str | None) -> bool:
    return any(_norm(value) in _PAYPAL_VALUES for value in (payment_field, payment_account))


def _is_generic_card_signal(
    payment_field: str | None, payment_account: str | None
) -> bool:
    return any(
        _norm(value) in _GENERIC_CARD_VALUES for value in (payment_field, payment_account)
    )


def _has_explicit_amex_evidence(
    *,
    payment_field: str | None,
    payment_account: str | None,
) -> bool:
    for probe in (payment_field, payment_account):
        normalized = _norm(probe)
        if not normalized:
            continue
        if normalized in _AMEX_VALUES:
            return True
        if "amex" in normalized.replace(" ", "") or "americanexpress" in normalized.replace(
            " ", ""
        ):
            return True
    return False


def _available_configuration_dicts(
    active: Sequence[ConfigurationCandidate],
    unmatched: ConfigurationCandidate | None,
) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for config in active:
        rows.append(
            {
                "configuration_name": config.name,
                "configuration_id": config.configuration_id,
                "active": config.active,
                "is_unmatched": False,
                "matching_feature_key": config.matching_feature_key,
                "matching_operator": config.matching_operator,
                "matching_values": list(config.matching_values),
                "filename_pattern": config.filename_pattern,
            }
        )
    if unmatched is not None:
        rows.append(
            {
                "configuration_name": unmatched.name,
                "configuration_id": unmatched.configuration_id,
                "active": unmatched.active,
                "is_unmatched": True,
                "matching_feature_key": unmatched.matching_feature_key,
                "matching_operator": "fallback",
                "matching_values": [],
                "filename_pattern": unmatched.filename_pattern,
            }
        )
    return tuple(rows)


def _condition_specs(config: ConfigurationCandidate) -> tuple[dict[str, object], ...]:
    feature = (config.matching_feature_key or "").strip() or None
    operator = (config.matching_operator or "ist").strip() or "ist"
    if not config.matching_values:
        return (
            {
                "condition_type": "fallback_unmatched"
                if config.is_unmatched
                else "no_conditions",
                "feature_key": feature,
                "operator": operator,
                "values": [],
            },
        )
    feature_l = (feature or "").lower()
    if feature_l in _PAYMENT_FEATURE_KEYS:
        condition_type = "payment_field_equals" if operator in {"ist", "equals", "="} else "payment_field_contains"
    elif feature_l in {"supplier", "lieferant", "vendor"}:
        condition_type = "supplier_contains"
    elif feature_l in {"recipient", "company", "empfaenger", "empfänger", "firma"}:
        condition_type = "recipient_contains"
    elif feature_l in {"document_type", "art", "dokumenttyp"}:
        condition_type = "document_type_equals"
    elif feature_l in {"text", "raw_text", "inhalt"}:
        condition_type = "text_contains"
    else:
        condition_type = "field_equals" if operator in {"ist", "equals", "="} else "field_contains"
    return (
        {
            "condition_type": condition_type,
            "feature_key": feature,
            "operator": operator,
            "values": list(config.matching_values),
        },
    )


def _field_probe_for_feature(
    feature_key: str | None,
    *,
    payment_field: str | None,
    payment_account: str | None,
    supplier: str | None,
    recipient: str | None,
    document_type: str | None,
    raw_text_head: str | None,
) -> tuple[str | None, str]:
    feature = (feature_key or "").strip().lower()
    if feature in _PAYMENT_FEATURE_KEYS:
        value = (payment_field or payment_account or "").strip() or None
        return value, "payment_field"
    if feature in {"supplier", "lieferant", "vendor"}:
        return (supplier or "").strip() or None, "supplier"
    if feature in {"recipient", "company", "empfaenger", "empfänger", "firma"}:
        return (recipient or "").strip() or None, "recipient"
    if feature in {"document_type", "art", "dokumenttyp"}:
        return (document_type or "").strip() or None, "document_type"
    if feature in {"text", "raw_text", "inhalt"}:
        return (raw_text_head or "").strip() or None, "text"
    # Unknown feature: prefer payment signals, then text.
    if payment_field or payment_account:
        return (payment_field or payment_account or "").strip() or None, "payment_field"
    return (raw_text_head or "").strip() or None, "text"


def _evaluate_active_candidate(
    config: ConfigurationCandidate,
    *,
    payment_field: str | None,
    payment_account: str | None,
    supplier: str | None,
    recipient: str | None,
    document_type: str | None,
    raw_text_head: str | None,
) -> EvaluatedConfigurationCandidate:
    conditions = _condition_specs(config)
    condition_results: list[ConditionResult] = []

    if not config.active:
        return EvaluatedConfigurationCandidate(
            configuration_name=config.name,
            configuration_id=config.configuration_id,
            active=False,
            conditions=conditions,
            condition_results=(
                ConditionResult(
                    condition_type="active",
                    feature_key=None,
                    expected_value="true",
                    actual_value="false",
                    matched=False,
                    reason="Konfiguration ist inaktiv und darf nicht matchen.",
                ),
            ),
            matched=False,
            reason="Inaktive Konfiguration — ausgeschlossen.",
            confidence="none",
            filename_pattern=config.filename_pattern,
        )

    # Hard guards: PayPal / generic card never match American Express.
    if _is_amex_config(config):
        if _is_paypal_signal(payment_field, payment_account):
            result = ConditionResult(
                condition_type="payment_field_equals",
                feature_key="payment_field",
                expected_value="amex",
                actual_value=payment_field or payment_account,
                matched=False,
                reason="PayPal matcht nicht American Express.",
            )
            return EvaluatedConfigurationCandidate(
                configuration_name=config.name,
                configuration_id=config.configuration_id,
                active=True,
                conditions=conditions,
                condition_results=(result,),
                matched=False,
                reason=result.reason,
                confidence="none",
                filename_pattern=config.filename_pattern,
            )
        if _is_generic_card_signal(payment_field, payment_account) and not _has_explicit_amex_evidence(
            payment_field=payment_field,
            payment_account=payment_account,
        ):
            result = ConditionResult(
                condition_type="payment_field_equals",
                feature_key="payment_field",
                expected_value="amex",
                actual_value=payment_field or payment_account,
                matched=False,
                reason="generic credit card detected, AMEX not proven",
            )
            return EvaluatedConfigurationCandidate(
                configuration_name=config.name,
                configuration_id=config.configuration_id,
                active=True,
                conditions=conditions,
                condition_results=(result,),
                matched=False,
                reason=result.reason,
                confidence="none",
                filename_pattern=config.filename_pattern,
            )
        if not _has_explicit_amex_evidence(
            payment_field=payment_field,
            payment_account=payment_account,
        ):
            # AMEX config requires explicit AMEX evidence on payment signals.
            result = ConditionResult(
                condition_type="payment_field_equals",
                feature_key="payment_field",
                expected_value="amex / American Express",
                actual_value=payment_field or payment_account,
                matched=False,
                reason="AMEX nur bei explizitem AMEX-/American-Express-Nachweis.",
            )
            return EvaluatedConfigurationCandidate(
                configuration_name=config.name,
                configuration_id=config.configuration_id,
                active=True,
                conditions=conditions,
                condition_results=(result,),
                matched=False,
                reason=result.reason,
                confidence="none",
                filename_pattern=config.filename_pattern,
            )

    if not config.matching_values:
        result = ConditionResult(
            condition_type="no_conditions",
            feature_key=config.matching_feature_key,
            expected_value=None,
            actual_value=None,
            matched=False,
            reason="Keine Matching-Werte konfiguriert.",
        )
        return EvaluatedConfigurationCandidate(
            configuration_name=config.name,
            configuration_id=config.configuration_id,
            active=True,
            conditions=conditions,
            condition_results=(result,),
            matched=False,
            reason=result.reason,
            confidence="none",
            filename_pattern=config.filename_pattern,
        )

    probe, probe_name = _field_probe_for_feature(
        config.matching_feature_key,
        payment_field=payment_field,
        payment_account=payment_account,
        supplier=supplier,
        recipient=recipient,
        document_type=document_type,
        raw_text_head=raw_text_head,
    )
    feature = (config.matching_feature_key or "").strip().lower()
    condition_type = str(conditions[0].get("condition_type") or "field_equals")

    direct_hit_value: str | None = None
    if probe:
        for configured_value in config.matching_values:
            if _value_matches(configured_value, probe):
                direct_hit_value = configured_value
                break

    if direct_hit_value is not None:
        result = ConditionResult(
            condition_type=condition_type,
            feature_key=config.matching_feature_key,
            expected_value=direct_hit_value,
            actual_value=probe,
            matched=True,
            reason=(
                f"{probe_name} „{probe}“ erfüllt Bedingung "
                f"{config.matching_feature_key or 'Merkmal'}={direct_hit_value}."
            ),
        )
        return EvaluatedConfigurationCandidate(
            configuration_name=config.name,
            configuration_id=config.configuration_id,
            active=True,
            conditions=conditions,
            condition_results=(result,),
            matched=True,
            reason=(
                f"Aktive Konfiguration „{config.name}“ über "
                f"{config.matching_feature_key or 'Merkmal'}="
                f"„{direct_hit_value}“ (Signal: {probe})."
            ),
            confidence="high",
            filename_pattern=config.filename_pattern,
        )

    # Free-text body matching is unsafe for payment_field rules.
    text_hit_value: str | None = None
    text = str(raw_text_head or "")
    if text and feature and feature not in _PAYMENT_FEATURE_KEYS:
        for configured_value in config.matching_values:
            if _text_contains_value(text, configured_value):
                text_hit_value = configured_value
                break

    if text_hit_value is not None:
        result = ConditionResult(
            condition_type="text_contains",
            feature_key=config.matching_feature_key,
            expected_value=text_hit_value,
            actual_value="raw_text_head",
            matched=True,
            reason=f"Text enthält Erkennungswert „{text_hit_value}“.",
        )
        return EvaluatedConfigurationCandidate(
            configuration_name=config.name,
            configuration_id=config.configuration_id,
            active=True,
            conditions=conditions,
            condition_results=(result,),
            matched=True,
            reason=(
                f"Aktive Konfiguration „{config.name}“ über Texttreffer "
                f"auf Erkennungswert „{text_hit_value}“."
            ),
            confidence="medium",
            filename_pattern=config.filename_pattern,
        )

    missing = probe is None
    result = ConditionResult(
        condition_type=condition_type,
        feature_key=config.matching_feature_key,
        expected_value=", ".join(config.matching_values),
        actual_value=probe,
        matched=False,
        reason=(
            f"Feld {probe_name} fehlt — Bedingung nicht auswertbar."
            if missing
            else (
                f"{probe_name} „{probe}“ erfüllt keine Werte "
                f"{list(config.matching_values)}."
            )
        ),
    )
    return EvaluatedConfigurationCandidate(
        configuration_name=config.name,
        configuration_id=config.configuration_id,
        active=True,
        conditions=conditions,
        condition_results=(result,),
        matched=False,
        reason=result.reason,
        confidence="none",
        filename_pattern=config.filename_pattern,
    )


def _precise_unmatched_reason(
    *,
    payment_field: str | None,
    payment_account: str | None,
    active: Sequence[ConfigurationCandidate],
) -> tuple[str, str | None]:
    """Return (reason, missing_configuration_rule)."""

    signal = str(payment_field or payment_account or "").strip()
    if not signal:
        return (
            "payment_field fehlt — keine Zahlungsart erkannt; "
            "konfiguriertes Unklar/Fallback verwendet.",
            "payment_field fehlt",
        )
    signal_l = signal.lower().replace(" ", "_")
    supports_paypal = any(
        any(_norm(value) in _PAYPAL_VALUES for value in config.matching_values)
        or "paypal" in _norm(config.name)
        for config in active
    )
    if signal_l in {"paypal"} or _norm(signal) in _PAYPAL_VALUES:
        if not supports_paypal:
            reason = (
                "payment_field paypal detected, but no active configuration supports PayPal"
            )
            return reason, "keine aktive PayPal-Konfiguration"
        return (
            "payment_field paypal erkannt, aber keine aktive PayPal-Konfiguration "
            "gematcht — Unklar/Fallback verwendet.",
            "PayPal-Bedingung nicht erfüllt",
        )
    if signal_l in _GENERIC_CARD_VALUES or _norm(signal) in _GENERIC_CARD_VALUES:
        return (
            "generic credit card detected, AMEX not proven",
            "kein AMEX-Nachweis / keine passende Nicht-AMEX-Karten-Konfiguration",
        )
    if _norm(signal) in _AMEX_VALUES:
        has_amex = any(_is_amex_config(config) for config in active)
        if not has_amex:
            return (
                "payment_field amex erkannt, aber keine aktive American-Express-"
                "Konfiguration verfügbar — Unklar/Fallback verwendet.",
                "keine aktive American-Express-Konfiguration",
            )
    return (
        f"payment_field „{signal}“ erkannt, aber keine aktive Konfiguration "
        "erfüllt die Bedingungen — Unklar/Fallback verwendet.",
        f"keine passende Regel für payment_field={signal}",
    )


def _unmatched_result(
    unmatched: ConfigurationCandidate | None,
    *,
    reason: str,
    confidence: MatchingConfidence,
    available: tuple[dict[str, object], ...],
    evaluated: tuple[dict[str, object], ...],
    unmatched_reasons: tuple[str, ...],
    missing_configuration_rule: str | None,
    detected_payment_field: str | None = None,
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
            matched_payment_field=detected_payment_field,
            available_configurations=available,
            evaluated_configuration_candidates=evaluated,
            unmatched_reasons=unmatched_reasons or (reason,),
            condition_results=(),
            missing_configuration_rule=missing_configuration_rule,
        )
    return ConfigurationMatchResult(
        matched_configuration_name=unmatched.name,
        matched_configuration_id=unmatched.configuration_id,
        matched_configuration_pattern=unmatched.filename_pattern,
        matched_configuration_reason=reason,
        matched_configuration_confidence=confidence,
        is_unmatched_fallback=True,
        unmatched_reason=reason,
        matched_payment_field=detected_payment_field,
        available_configurations=available,
        evaluated_configuration_candidates=evaluated
        + (
            {
                "configuration_name": unmatched.name,
                "configuration_id": unmatched.configuration_id,
                "active": True,
                "is_unmatched": True,
                "conditions": [{"condition_type": "fallback_unmatched"}],
                "condition_results": [
                    {
                        "condition_type": "fallback_unmatched",
                        "feature_key": None,
                        "expected_value": None,
                        "actual_value": None,
                        "matched": True,
                        "reason": "Kein Nicht-Fallback-Treffer — Unklar/Fallback gewählt.",
                    }
                ],
                "matched": True,
                "reason": reason,
                "confidence": confidence,
                "filename_pattern": unmatched.filename_pattern,
            },
        ),
        unmatched_reasons=unmatched_reasons or (reason,),
        condition_results=(
            {
                "condition_type": "fallback_unmatched",
                "feature_key": None,
                "expected_value": None,
                "actual_value": None,
                "matched": True,
                "reason": reason,
            },
        ),
        missing_configuration_rule=missing_configuration_rule,
    )


def match_active_configuration(
    *,
    payment_field: str | None = None,
    payment_account: str | None = None,
    supplier: str | None = None,
    recipient: str | None = None,
    document_type: str | None = None,
    raw_text_head: str | None = None,
    configurations: Sequence[ConfigurationCandidate] | None = None,
    unmatched: ConfigurationCandidate | None = None,
    profile_id: str | None = None,
) -> ConfigurationMatchResult:
    """Match extraction/result signals against active configuration rules.

    Only active configs may match. Unklar/fallback is used only when no
    non-fallback config matches. PayPal/generic card never map to AMEX without
    explicit AMEX evidence.
    """

    active: tuple[ConfigurationCandidate, ...]
    unmatched_candidate: ConfigurationCandidate | None
    if configurations is None:
        active, unmatched_candidate = load_active_configuration_candidates(
            profile_id=profile_id
        )
    else:
        # Include inactive in evaluation for transparency, but never match them.
        active = tuple(item for item in configurations if not item.is_unmatched)
        unmatched_candidate = unmatched

    available = _available_configuration_dicts(
        tuple(item for item in active if item.active),
        unmatched_candidate,
    )

    evaluated_models: list[EvaluatedConfigurationCandidate] = []
    for config in active:
        evaluated_models.append(
            _evaluate_active_candidate(
                config,
                payment_field=payment_field,
                payment_account=payment_account,
                supplier=supplier,
                recipient=recipient,
                document_type=document_type,
                raw_text_head=raw_text_head,
            )
        )

    evaluated = tuple(item.to_dict() for item in evaluated_models)
    unmatched_reasons = tuple(
        item.reason for item in evaluated_models if not item.matched and item.reason
    )

    matches = [item for item in evaluated_models if item.matched and item.active]
    if matches:
        matches_sorted = sorted(
            matches,
            key=lambda item: _CONFIDENCE_RANK.get(item.confidence, 0),
            reverse=True,
        )
        winner = matches_sorted[0]
        alternatives = tuple(item.to_dict() for item in matches_sorted[1:])
        winner_config = next(
            (cfg for cfg in active if cfg.configuration_id == winner.configuration_id),
            None,
        )
        matched_payment = None
        if winner_config and (winner_config.matching_feature_key or "").lower() in _PAYMENT_FEATURE_KEYS:
            for condition in winner.condition_results:
                if condition.matched and condition.expected_value:
                    matched_payment = condition.expected_value
                    break
        reason = winner.reason
        if alternatives:
            alt_names = ", ".join(
                str(item.get("configuration_name") or "?") for item in alternatives
            )
            reason = (
                f"{reason} Alternativen mit niedrigerer/gleicher Konfidenz: {alt_names}."
            )
        return ConfigurationMatchResult(
            matched_configuration_name=winner.configuration_name,
            matched_configuration_id=winner.configuration_id,
            matched_configuration_pattern=winner.filename_pattern,
            matched_configuration_reason=reason,
            matched_configuration_confidence=winner.confidence,
            is_unmatched_fallback=False,
            matched_payment_field=matched_payment or payment_field or payment_account,
            available_configurations=available,
            evaluated_configuration_candidates=evaluated,
            unmatched_reasons=unmatched_reasons,
            condition_results=tuple(
                item.to_dict() for item in winner.condition_results
            ),
            alternative_matches=alternatives,
            missing_configuration_rule=None,
        )

    detected_payment = (payment_field or payment_account or "").strip() or None

    if not any(item.active for item in active) and unmatched_candidate is None:
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
            matched_payment_field=detected_payment,
            available_configurations=available,
            evaluated_configuration_candidates=evaluated,
            unmatched_reasons=unmatched_reasons
            or ("Keine aktiven Konfigurationen und kein Unklar-Fallback verfügbar.",),
            missing_configuration_rule="keine aktiven Konfigurationen",
        )

    reason, missing_rule = _precise_unmatched_reason(
        payment_field=payment_field,
        payment_account=payment_account,
        active=tuple(item for item in active if item.active),
    )
    return _unmatched_result(
        unmatched_candidate,
        reason=reason,
        confidence="low"
        if unmatched_candidate and unmatched_candidate.filename_pattern
        else "none",
        available=available,
        evaluated=evaluated,
        unmatched_reasons=unmatched_reasons + (reason,),
        missing_configuration_rule=missing_rule,
        detected_payment_field=detected_payment,
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
                matching_operator=str(item.get("matching_operator") or item.get("operator") or "ist"),
                matching_values=tuple(str(v).strip() for v in values if str(v or "").strip()),
                filename_pattern=(
                    str(item.get("filename_pattern") or item.get("pattern") or "").strip()
                    or None
                ),
            )
        )
    return tuple(out)


__all__ = (
    "ConditionResult",
    "ConfigurationCandidate",
    "ConfigurationMatchResult",
    "EvaluatedConfigurationCandidate",
    "UNMATCHED_CONFIGURATION_ID",
    "configurations_from_raw",
    "load_active_configuration_candidates",
    "match_active_configuration",
)
