"""Track-B configuration coverage guidance (Prompt 23/34).

Derives user-facing guidance when matching falls back to Unklar because no
active configuration covers the detected payment/account/category.

Guidance only — never creates or edits user configurations.
Preview/sandbox only — no productive processing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

GuidanceSeverity = Literal["info", "warning", "error"]

STATUS_COVERED = "covered"
STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT = "missing_config_for_detected_payment"
STATUS_NO_SAFE_CARD_CONFIGURATION = "no_safe_card_configuration"
STATUS_MISSING_PAYMENT_FIELD = "missing_payment_field"
STATUS_UNMATCHED_OTHER = "unmatched_other"

MISSING_TYPE_PAYPAL = "paypal"
MISSING_TYPE_GENERIC_CARD = "generic_card"
MISSING_TYPE_PAYMENT_FIELD = "payment_field"

MSG_GUIDANCE_PAYPAL = (
    "PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden."
)
MSG_ACTION_PAYPAL = (
    "PayPal-Konfiguration ergänzen oder manuell prüfen."
)
MSG_GUIDANCE_GENERIC_CARD = (
    "Kreditkarte erkannt, aber AMEX nicht belegt; keine passende "
    "Nicht-AMEX-Karten-Konfiguration vorhanden."
)
MSG_ACTION_GENERIC_CARD = (
    "Karten-Konfiguration ergänzen oder Beleg manuell prüfen."
)
MSG_GUIDANCE_MISSING_PAYMENT = (
    "Zahlungsfeld nicht sicher erkannt; Konfiguration konnte deshalb nicht "
    "eindeutig gewählt werden."
)
MSG_ACTION_MISSING_PAYMENT = (
    "Zahlungsfeld prüfen oder Konfiguration mit anderem Match-Kriterium ergänzen."
)
MSG_GUIDANCE_COVERED = (
    "Aktive Konfiguration hat die erkannten Bedingungen erfüllt."
)
MSG_ACTION_COVERED = "Keine Abdeckungsaktion erforderlich — Review bleibt Preview-only."
MSG_GUIDANCE_UNMATCHED_OTHER = (
    "Keine aktive Konfiguration erfüllt die erkannten Bedingungen; "
    "Unklar/Fallback bleibt aktiv."
)
MSG_ACTION_UNMATCHED_OTHER = (
    "Konfiguration ergänzen, bestehende anpassen, manuell prüfen oder als Unklar belassen."
)

SAFE_NEXT_ACTIONS: tuple[str, ...] = (
    "Konfiguration ergänzen",
    "bestehende Konfiguration anpassen",
    "manuell prüfen",
    "als Unklar belassen",
)

MSG_FIELD_CONFIGURATION_COVERAGE = "Konfigurationsabdeckung"
MSG_FIELD_USER_GUIDANCE = "Nutzerhinweis"
MSG_FIELD_SUGGESTED_ACTION = "vorgeschlagene Aktion"
MSG_FIELD_MISSING_CONFIGURATION_TYPE = "fehlender Konfigurationstyp"
MSG_FIELD_GUIDANCE_SEVERITY = "Hinweis-Schwere"

_GENERIC_CARD_VALUES = frozenset(
    {"card", "credit_card", "card_generic", "kreditkarte", "credit card"}
)
_PAYPAL_VALUES = frozenset({"paypal", "pay pal"})
_AMEX_VALUES = frozenset({"amex", "american express", "americanexpress"})


def _norm(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _is_paypal(signal: str | None) -> bool:
    return _norm(signal) in _PAYPAL_VALUES or "paypal" in _norm(signal)


def _is_generic_card(signal: str | None) -> bool:
    return _norm(signal) in _GENERIC_CARD_VALUES


def _is_amex(signal: str | None) -> bool:
    return _norm(signal) in _AMEX_VALUES


def _reason_blob(
    *,
    matched_configuration_reason: str | None,
    unmatched_reasons: Sequence[str],
    missing_configuration_rule: str | None,
) -> str:
    parts = [
        str(matched_configuration_reason or ""),
        str(missing_configuration_rule or ""),
        " ".join(str(item) for item in unmatched_reasons or ()),
    ]
    return " ".join(parts).lower()


@dataclass(frozen=True)
class ConfigurationCoverageGuidance:
    """User-facing coverage guidance for Unklar / missing-config cases."""

    configuration_coverage_status: str
    missing_configuration_type: str | None
    user_guidance: str
    suggested_configuration_action: str
    guidance_severity: GuidanceSeverity = "warning"
    safe_next_actions: tuple[str, ...] = field(default_factory=lambda: SAFE_NEXT_ACTIONS)
    evaluated_configuration_summary: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "configuration_coverage_status": self.configuration_coverage_status,
            "missing_configuration_type": self.missing_configuration_type,
            "user_guidance": self.user_guidance,
            "suggested_configuration_action": self.suggested_configuration_action,
            "guidance_severity": self.guidance_severity,
            "safe_next_actions": list(self.safe_next_actions),
            "evaluated_configuration_summary": list(
                self.evaluated_configuration_summary
            ),
        }

    def to_export_fields(self) -> dict[str, Any]:
        return {
            "configuration_coverage_status": self.configuration_coverage_status,
            "missing_configuration_type": self.missing_configuration_type,
            "user_guidance": self.user_guidance,
            "suggested_configuration_action": self.suggested_configuration_action,
            "guidance_severity": self.guidance_severity,
        }


def _summarize_evaluated(
    evaluated: Sequence[Mapping[str, Any]] | None,
) -> tuple[str, ...]:
    out: list[str] = []
    for item in evaluated or ():
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("configuration_name") or item.get("name") or "?").strip()
        matched = bool(item.get("matched"))
        reason = str(item.get("reason") or "").strip()
        status = "Treffer" if matched else "kein Treffer"
        if reason:
            out.append(f"{name}: {status} — {reason}")
        else:
            out.append(f"{name}: {status}")
    return tuple(out)


def derive_configuration_coverage_guidance(
    *,
    selected_payment_field: str | None = None,
    payment_field_candidates: Sequence[Mapping[str, Any]] | None = None,
    matched_configuration_name: str | None = None,
    evaluated_configuration_candidates: Sequence[Mapping[str, Any]] | None = None,
    unmatched_reasons: Sequence[str] | None = None,
    absent_pattern_slots: Sequence[str] | None = None,
    document_type: str | None = None,
    supplier: str | None = None,
    source_filename: str | None = None,
    is_unmatched_fallback: bool | None = None,
    matched_configuration_reason: str | None = None,
    missing_configuration_rule: str | None = None,
    payment_account: str | None = None,
) -> ConfigurationCoverageGuidance:
    """Derive SaaS-safe coverage guidance from matching / extraction signals.

    Does not create or edit configurations. Does not map PayPal/card to private
    categories. Does not assert product maturity claims.
    """

    _ = (document_type, supplier, source_filename, payment_field_candidates)
    signal = _first_non_empty(selected_payment_field, payment_account)
    absent_slots = {
        str(item).strip().lower() for item in (absent_pattern_slots or ())
    }
    reasons = tuple(str(item) for item in (unmatched_reasons or ()) if str(item).strip())
    blob = _reason_blob(
        matched_configuration_reason=matched_configuration_reason,
        unmatched_reasons=reasons,
        missing_configuration_rule=missing_configuration_rule,
    )
    summary = _summarize_evaluated(evaluated_configuration_candidates)

    covered = (
        is_unmatched_fallback is False
        and bool(str(matched_configuration_name or "").strip())
        and str(matched_configuration_name or "").strip().lower() != "unklar"
    )
    if covered:
        return ConfigurationCoverageGuidance(
            configuration_coverage_status=STATUS_COVERED,
            missing_configuration_type=None,
            user_guidance=MSG_GUIDANCE_COVERED,
            suggested_configuration_action=MSG_ACTION_COVERED,
            guidance_severity="info",
            safe_next_actions=SAFE_NEXT_ACTIONS,
            evaluated_configuration_summary=summary,
        )

    payment_missing = (
        not signal
        or "payment_field" in absent_slots
        or "payment_field fehlt" in blob
        or "zahlungsfeld nicht" in blob
    )
    paypal_gap = (
        _is_paypal(signal)
        or "paypal" in blob
        or "no active configuration supports paypal" in blob
    )
    generic_card_gap = (
        (_is_generic_card(signal) and not _is_amex(signal))
        or "amex not proven" in blob
        or "generic credit card" in blob
        or "nicht-amex" in blob
    )

    if paypal_gap and not payment_missing:
        return ConfigurationCoverageGuidance(
            configuration_coverage_status=STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT,
            missing_configuration_type=MISSING_TYPE_PAYPAL,
            user_guidance=MSG_GUIDANCE_PAYPAL,
            suggested_configuration_action=MSG_ACTION_PAYPAL,
            guidance_severity="warning",
            safe_next_actions=SAFE_NEXT_ACTIONS,
            evaluated_configuration_summary=summary,
        )

    if generic_card_gap and not payment_missing:
        return ConfigurationCoverageGuidance(
            configuration_coverage_status=STATUS_NO_SAFE_CARD_CONFIGURATION,
            missing_configuration_type=MISSING_TYPE_GENERIC_CARD,
            user_guidance=MSG_GUIDANCE_GENERIC_CARD,
            suggested_configuration_action=MSG_ACTION_GENERIC_CARD,
            guidance_severity="warning",
            safe_next_actions=SAFE_NEXT_ACTIONS,
            evaluated_configuration_summary=summary,
        )

    if payment_missing:
        return ConfigurationCoverageGuidance(
            configuration_coverage_status=STATUS_MISSING_PAYMENT_FIELD,
            missing_configuration_type=MISSING_TYPE_PAYMENT_FIELD,
            user_guidance=MSG_GUIDANCE_MISSING_PAYMENT,
            suggested_configuration_action=MSG_ACTION_MISSING_PAYMENT,
            guidance_severity="warning",
            safe_next_actions=SAFE_NEXT_ACTIONS,
            evaluated_configuration_summary=summary,
        )

    return ConfigurationCoverageGuidance(
        configuration_coverage_status=STATUS_UNMATCHED_OTHER,
        missing_configuration_type=None,
        user_guidance=MSG_GUIDANCE_UNMATCHED_OTHER,
        suggested_configuration_action=MSG_ACTION_UNMATCHED_OTHER,
        guidance_severity="warning",
        safe_next_actions=SAFE_NEXT_ACTIONS,
        evaluated_configuration_summary=summary,
    )


def ensure_guidance_fields(meta: Mapping[str, Any]) -> dict[str, Any]:
    """Return guidance export fields, deriving them when absent."""

    status = str(meta.get("configuration_coverage_status") or "").strip()
    if status:
        return {
            "configuration_coverage_status": status,
            "missing_configuration_type": meta.get("missing_configuration_type"),
            "user_guidance": meta.get("user_guidance"),
            "suggested_configuration_action": meta.get(
                "suggested_configuration_action"
            ),
            "guidance_severity": meta.get("guidance_severity") or "warning",
        }
    guidance = derive_configuration_coverage_guidance(
        selected_payment_field=_first_non_empty(
            str(meta.get("selected_payment_field") or "") or None,
            str(meta.get("payment_account") or "") or None,
        ),
        payment_account=str(meta.get("payment_account") or "") or None,
        matched_configuration_name=str(meta.get("matched_configuration_name") or "")
        or None,
        evaluated_configuration_candidates=meta.get(
            "evaluated_configuration_candidates"
        )
        or (),
        unmatched_reasons=meta.get("unmatched_reasons") or (),
        document_type=str(meta.get("document_type") or "") or None,
        supplier=str(meta.get("supplier") or "") or None,
        source_filename=str(meta.get("source_filename") or "") or None,
        is_unmatched_fallback=(
            True
            if str(meta.get("matched_configuration_name") or "").strip().lower()
            in {"", "unklar"}
            else False
        ),
        matched_configuration_reason=str(meta.get("matched_configuration_reason") or "")
        or None,
        missing_configuration_rule=str(meta.get("missing_configuration_rule") or "")
        or None,
    )
    return guidance.to_export_fields()


__all__ = (
    "ConfigurationCoverageGuidance",
    "MISSING_TYPE_GENERIC_CARD",
    "MISSING_TYPE_PAYMENT_FIELD",
    "MISSING_TYPE_PAYPAL",
    "MSG_ACTION_GENERIC_CARD",
    "MSG_ACTION_MISSING_PAYMENT",
    "MSG_ACTION_PAYPAL",
    "MSG_FIELD_CONFIGURATION_COVERAGE",
    "MSG_FIELD_GUIDANCE_SEVERITY",
    "MSG_FIELD_MISSING_CONFIGURATION_TYPE",
    "MSG_FIELD_SUGGESTED_ACTION",
    "MSG_FIELD_USER_GUIDANCE",
    "MSG_GUIDANCE_GENERIC_CARD",
    "MSG_GUIDANCE_MISSING_PAYMENT",
    "MSG_GUIDANCE_PAYPAL",
    "SAFE_NEXT_ACTIONS",
    "STATUS_COVERED",
    "STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT",
    "STATUS_MISSING_PAYMENT_FIELD",
    "STATUS_NO_SAFE_CARD_CONFIGURATION",
    "STATUS_UNMATCHED_OTHER",
    "derive_configuration_coverage_guidance",
    "ensure_guidance_fields",
)
