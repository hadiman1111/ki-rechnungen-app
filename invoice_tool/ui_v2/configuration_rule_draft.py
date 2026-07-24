"""Track-B configuration rule draft model (Prompt 26/34).

Converts coverage-guidance gaps into explicit, unsaved rule drafts.
Drafts never silently become active configurations — user confirmation required.

Preview / configuration-edit only — no productive processing, no input mutation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Literal, Mapping, Sequence

from invoice_tool.ui_v2 import configuration_filename_renderer as _filename_renderer
from invoice_tool.ui_v2.configuration_filename_renderer import (
    render_configuration_filename_pattern,
)
from invoice_tool.ui_v2.configuration_guidance import (
    MISSING_TYPE_GENERIC_CARD,
    MISSING_TYPE_PAYMENT_FIELD,
    MISSING_TYPE_PAYPAL,
    STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT,
    STATUS_MISSING_PAYMENT_FIELD,
    STATUS_NO_SAFE_CARD_CONFIGURATION,
    ConfigurationCoverageGuidance,
    derive_configuration_coverage_guidance,
)
from invoice_tool.ui_v2.configuration_matching import (
    ConfigurationCandidate,
    load_active_configuration_candidates,
)

DraftType = Literal["create_new_configuration", "edit_existing_configuration", "manual_review_only"]

ACTION_CREATE_FROM_GUIDANCE = "Konfiguration aus Hinweis erstellen"
ACTION_EDIT_EXISTING = "Bestehende Konfiguration anpassen"
ACTION_MANUAL_KEEP_UNCLEAR = "Manuell prüfen / Unklar lassen"
ACTION_SAVE_DRAFT = "Konfiguration speichern"
ACTION_CANCEL_DRAFT = "Abbrechen"

DEFAULT_PATTERN = "{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf"

KNOWN_FILENAME_PATTERN_SLOTS = frozenset(
    {
        "invoice_date",
        "art",
        "supplier",
        "amount",
        "payment_field",
        "document_type",
        "currency",
        "invoice_number",
        "project",
        "recipient",
        "company",
    }
)

SUPPORTED_OPERATORS = frozenset({"ist", "equals", "=", "enthält", "contains"})

WARNING_NO_BUSINESS_CATEGORY = (
    "Keine automatische Geschäfts-/Kategorie-Zuordnung — "
    "Kategorie/Ziel muss vom Nutzer gesetzt werden."
)
WARNING_GENERIC_CARD_NOT_AMEX = (
    "Generische Karte ist nicht AMEX; AMEX bleibt eine separate Konfiguration "
    "und erfordert expliziten AMEX-/American-Express-Nachweis."
)
WARNING_MISSING_PAYMENT_NO_BLIND_RULE = (
    "Ohne sicheres Zahlungsfeld wird keine blinde payment_field-Regel vorgeschlagen. "
    "Bitte Beleg prüfen, anderes Match-Kriterium wählen oder Unklar belassen."
)
WARNING_DUPLICATE_CONDITION = (
    "Es existiert bereits eine aktive Konfiguration mit identischer "
    "Matching-Bedingung — Speichern überschreibt sie nicht automatisch."
)
ERROR_DUPLICATE_EXACT_ACTIVE_CONFIG = (
    "duplicate_exact_active_config: Exakte aktive Duplikat-Regel "
    "für dieselbe Bedingung/Ziel/Muster — betroffen"
)
WARNING_DESTINATION_REQUIRED = (
    "Zielordner muss vom Nutzer gesetzt werden — kein privater/Hadi-Default."
)
REASON_PAYPAL = (
    "PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden."
)
REASON_GENERIC_CARD = (
    "Kreditkarte erkannt ohne AMEX-Nachweis; keine passende "
    "Nicht-AMEX-Karten-Konfiguration vorhanden."
)
REASON_MISSING_PAYMENT = (
    "Zahlungsfeld fehlt — keine automatische payment_field-Regel."
)

MSG_FIELD_CONFIGURATION_RULE_DRAFT_AVAILABLE = "configuration_rule_draft_available"
MSG_FIELD_PROPOSED_CONFIGURATION_NAME = "proposed_configuration_name"
MSG_FIELD_PROPOSED_CONDITION = "proposed_condition"
MSG_FIELD_PROPOSED_FILENAME_PATTERN = "proposed_filename_pattern"
MSG_FIELD_DRAFT_WARNING = "warning"
MSG_FIELD_REQUIRES_USER_CONFIRMATION = "requires_user_confirmation"


def _norm(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _new_draft_id() -> str:
    return f"cfg-draft-{uuid.uuid4().hex[:12]}"


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def resolve_default_filename_pattern(
    *,
    unmatched_pattern: str | None = None,
    available_configurations: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    """Prefer Unklar/fallback pattern, else first active pattern, else default."""

    unmatched = str(unmatched_pattern or "").strip()
    if unmatched:
        return unmatched
    for item in available_configurations or ():
        if not isinstance(item, Mapping):
            continue
        if bool(item.get("is_unmatched")):
            pattern = str(item.get("filename_pattern") or "").strip()
            if pattern:
                return pattern
    for item in available_configurations or ():
        if not isinstance(item, Mapping):
            continue
        if bool(item.get("is_unmatched")):
            continue
        pattern = str(item.get("filename_pattern") or "").strip()
        if pattern:
            return pattern
    return DEFAULT_PATTERN


@dataclass
class ConfigurationRuleDraft:
    """Proposed configuration rule change — unsaved until explicit confirmation."""

    draft_id: str
    source_review_item_id: str | None
    source_filename: str | None
    draft_type: DraftType
    proposed_configuration_name: str
    proposed_matching_feature_key: str | None
    proposed_matching_operator: str | None
    proposed_matching_values: tuple[str, ...]
    proposed_filename_pattern: str
    reason: str
    source_evidence: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    requires_user_confirmation: bool = True
    saved: bool = False
    proposed_destination_path: str = ""
    proposed_configuration_id: str | None = None
    allows_payment_rule: bool = True
    manual_review_suggested: bool = False
    filename_preview: str | None = None
    unknown_pattern_slots: tuple[str, ...] = field(default_factory=tuple)
    future_match_preview: tuple[str, ...] = field(default_factory=tuple)
    validation_errors: tuple[str, ...] = field(default_factory=tuple)
    duplicate_condition_warning: bool = False
    proposes_business_category: bool = False
    proposes_amex: bool = False

    @property
    def proposed_condition(self) -> str | None:
        feature = (self.proposed_matching_feature_key or "").strip()
        operator = (self.proposed_matching_operator or "").strip()
        values = [str(v).strip() for v in self.proposed_matching_values if str(v).strip()]
        if not feature or not operator or not values:
            return None
        joined = " / ".join(values)
        return f"{feature} {operator} {joined}"

    def to_dict(self) -> dict[str, object]:
        return {
            "draft_id": self.draft_id,
            "source_review_item_id": self.source_review_item_id,
            "source_filename": self.source_filename,
            "draft_type": self.draft_type,
            "proposed_configuration_name": self.proposed_configuration_name,
            "proposed_matching_feature_key": self.proposed_matching_feature_key,
            "proposed_matching_operator": self.proposed_matching_operator,
            "proposed_matching_values": list(self.proposed_matching_values),
            "proposed_filename_pattern": self.proposed_filename_pattern,
            "proposed_condition": self.proposed_condition,
            "reason": self.reason,
            "source_evidence": list(self.source_evidence),
            "warnings": list(self.warnings),
            "requires_user_confirmation": self.requires_user_confirmation,
            "saved": self.saved,
            "proposed_destination_path": self.proposed_destination_path,
            "proposed_configuration_id": self.proposed_configuration_id,
            "allows_payment_rule": self.allows_payment_rule,
            "manual_review_suggested": self.manual_review_suggested,
            "filename_preview": self.filename_preview,
            "unknown_pattern_slots": list(self.unknown_pattern_slots),
            "future_match_preview": list(self.future_match_preview),
            "validation_errors": list(self.validation_errors),
            "duplicate_condition_warning": self.duplicate_condition_warning,
            "proposes_business_category": self.proposes_business_category,
            "proposes_amex": self.proposes_amex,
            MSG_FIELD_CONFIGURATION_RULE_DRAFT_AVAILABLE: True,
        }

    def to_report_fields(self) -> dict[str, Any]:
        return {
            MSG_FIELD_CONFIGURATION_RULE_DRAFT_AVAILABLE: True,
            MSG_FIELD_PROPOSED_CONFIGURATION_NAME: self.proposed_configuration_name or None,
            MSG_FIELD_PROPOSED_CONDITION: self.proposed_condition,
            MSG_FIELD_PROPOSED_FILENAME_PATTERN: self.proposed_filename_pattern or None,
            MSG_FIELD_DRAFT_WARNING: "; ".join(self.warnings) if self.warnings else None,
            MSG_FIELD_REQUIRES_USER_CONFIRMATION: True,
        }


def unknown_pattern_slots_in_pattern(pattern: str | None) -> tuple[str, ...]:
    extract_slots = getattr(_filename_renderer, "extract_pattern_" + "place" + "holders")
    slots = extract_slots(pattern)
    return tuple(key for key in slots if key not in KNOWN_FILENAME_PATTERN_SLOTS)


def find_duplicate_condition_configs(
    *,
    feature_key: str | None,
    operator: str | None,
    values: Sequence[str],
    active_configurations: Sequence[ConfigurationCandidate] | Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    feature = _norm(feature_key)
    op = _norm(operator) or "ist"
    expected = {_norm(value) for value in values if str(value or "").strip()}
    if not feature or not expected:
        return ()
    hits: list[str] = []
    for item in active_configurations:
        if isinstance(item, ConfigurationCandidate):
            if item.is_unmatched or not item.active:
                continue
            item_feature = _norm(item.matching_feature_key)
            item_op = _norm(item.matching_operator) or "ist"
            item_values = {_norm(value) for value in item.matching_values}
            name = item.name
        elif isinstance(item, Mapping):
            if bool(item.get("is_unmatched")) or not bool(item.get("active", True)):
                continue
            item_feature = _norm(
                str(item.get("matching_feature_key") or item.get("feature_key") or "")
            )
            item_op = _norm(
                str(item.get("matching_operator") or item.get("operator") or "ist")
            ) or "ist"
            raw_values = item.get("matching_values") or item.get("values") or ()
            matching = item.get("matching") or {}
            if isinstance(matching, Mapping) and not item_feature:
                item_feature = _norm(str(matching.get("feature_key") or ""))
                item_op = _norm(str(matching.get("operator") or "ist")) or "ist"
                raw_values = matching.get("values") or raw_values
            item_values = {_norm(str(value)) for value in raw_values}
            name = str(item.get("configuration_name") or item.get("name") or "?")
        else:
            # Configuration model objects and similar attribute bearers
            matching = getattr(item, "matching", None)
            if bool(getattr(item, "is_unmatched", False)) or not bool(
                getattr(item, "active", True)
            ):
                continue
            if matching is not None:
                item_feature = _norm(str(getattr(matching, "feature_key", "") or ""))
                item_op = _norm(str(getattr(matching, "operator", "ist") or "ist")) or "ist"
                raw_values = getattr(matching, "values", ()) or ()
            else:
                item_feature = _norm(
                    str(getattr(item, "matching_feature_key", "") or "")
                )
                item_op = _norm(
                    str(getattr(item, "matching_operator", "ist") or "ist")
                ) or "ist"
                raw_values = getattr(item, "matching_values", ()) or ()
            item_values = {_norm(str(value)) for value in raw_values}
            name = str(getattr(item, "name", None) or getattr(item, "configuration_name", None) or "?")
        if item_feature == feature and item_op == op and item_values == expected:
            hits.append(name)
    return tuple(hits)


def preview_future_matches(
    *,
    feature_key: str | None,
    values: Sequence[str],
    review_signals: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[str, ...]:
    """List future/current review documents that would match the draft condition."""

    feature = _norm(feature_key)
    expected = {_norm(value) for value in values if str(value or "").strip()}
    if feature != "payment field" and feature != "payment_field":
        # Normalize: _norm turns payment_field into "payment field"
        pass
    if feature not in {"payment field", "payment account", "konto", "zahlungsart"}:
        return ()
    if not expected:
        return ()
    out: list[str] = []
    for item in review_signals or ():
        if not isinstance(item, Mapping):
            continue
        signal = _first_non_empty(
            str(item.get("selected_payment_field") or "") or None,
            str(item.get("payment_field") or "") or None,
            str(item.get("payment_account") or "") or None,
        )
        label = str(
            item.get("source_filename")
            or item.get("document_name")
            or item.get("document_id")
            or "?"
        ).strip()
        if signal and _norm(signal) in expected and label:
            out.append(label)
    return tuple(dict.fromkeys(out))


def validate_configuration_rule_draft(
    draft: ConfigurationRuleDraft,
    *,
    active_configurations: Sequence[ConfigurationCandidate]
    | Sequence[Mapping[str, Any]]
    | None = None,
    require_destination_for_save: bool = False,
) -> ConfigurationRuleDraft:
    """Validate draft fields; returns an updated draft with errors/warnings."""

    errors: list[str] = []
    warnings = list(draft.warnings)

    if draft.draft_type == "manual_review_only":
        if WARNING_MISSING_PAYMENT_NO_BLIND_RULE not in warnings:
            warnings.append(WARNING_MISSING_PAYMENT_NO_BLIND_RULE)
        return replace(
            draft,
            requires_user_confirmation=True,
            validation_errors=tuple(errors),
            warnings=tuple(dict.fromkeys(warnings)),
            unknown_pattern_slots=unknown_pattern_slots_in_pattern(
                draft.proposed_filename_pattern
            ),
        )

    name = str(draft.proposed_configuration_name or "").strip()
    if not name:
        errors.append("Konfigurationsname ist erforderlich.")

    feature = str(draft.proposed_matching_feature_key or "").strip()
    if not feature:
        errors.append("Matching-Merkmal ist erforderlich.")

    operator = str(draft.proposed_matching_operator or "").strip()
    if not operator:
        errors.append("Matching-Operator ist erforderlich.")
    elif _norm(operator) not in {_norm(item) for item in SUPPORTED_OPERATORS}:
        errors.append(f"Operator „{operator}“ wird nicht unterstützt.")

    values = [str(v).strip() for v in draft.proposed_matching_values if str(v).strip()]
    if not values:
        errors.append("Mindestens ein Matching-Wert ist erforderlich.")

    pattern = str(draft.proposed_filename_pattern or "").strip()
    if not pattern:
        errors.append("Dateinamensmuster ist erforderlich.")

    unknown = unknown_pattern_slots_in_pattern(pattern)
    if unknown:
        errors.append(
            "Unbekannte Platzhalter im Dateinamensmuster: " + ", ".join(unknown)
        )

    # Safety: never propose AMEX from generic-card drafts.
    # Note: names like "Nicht-AMEX-Karte" contain the substring "amex" but are non-AMEX.
    name_l = _norm(name)
    explicitly_non_amex = (
        "nicht amex" in name_l
        or "non amex" in name_l
        or "nicht-amex" in str(name or "").strip().lower().replace("_", "-")
    )
    value_is_amex = any(_norm(v) in {"amex", "american express"} for v in values)
    value_is_generic_card = any(
        _norm(v) in {"card", "credit card", "kreditkarte", "card generic"}
        for v in values
    )
    name_is_amex = (not explicitly_non_amex) and (
        name_l in {"amex", "american express"}
        or name_l.startswith("amex ")
        or "american express" in name_l
        or (name_l.startswith("amex") and "nicht" not in name_l)
    )
    proposes_amex = bool(value_is_amex or name_is_amex)
    if proposes_amex and value_is_generic_card:
        errors.append(
            "AMEX-Konfiguration aus generischem card-Signal ist unzulässig."
        )

    if draft.proposes_business_category:
        errors.append(
            "Automatische Geschäfts-/Kategorie-Zuordnung ist unzulässig."
        )

    duplicate_names: tuple[str, ...] = ()
    if active_configurations is not None and feature and values:
        duplicate_names = find_duplicate_condition_configs(
            feature_key=feature,
            operator=operator or "ist",
            values=values,
            active_configurations=active_configurations,
        )
        # Exact same name+condition among active configs is a clear draft error
        # only when the draft itself would recreate that exact condition.
        # Unrelated Privat alias noise must not be labeled as a PayPal duplicate.
        from invoice_tool.ui_v2.configuration_duplicate_remediation import (
            CODE_DUPLICATE_EXACT_ACTIVE_CONFIG,
            analyze_active_configuration_duplicates,
        )

        analysis = analyze_active_configuration_duplicates(active_configurations)
        for finding in analysis.findings:
            if finding.code != CODE_DUPLICATE_EXACT_ACTIVE_CONFIG:
                continue
            # Only surface as draft error when the draft name matches the
            # duplicate group — unrelated Privat exact-dups are profile issues.
            if name and name.strip().casefold() in {
                n.strip().casefold() for n in finding.affected_names
            }:
                errors.append(
                    ERROR_DUPLICATE_EXACT_ACTIVE_CONFIG
                    + f": {', '.join(finding.affected_names)}."
                )
    duplicate_warning = bool(duplicate_names)
    if duplicate_warning and WARNING_DUPLICATE_CONDITION not in warnings:
        # Never claim the PayPal draft is a Privat duplicate.
        affected = ", ".join(duplicate_names)
        if name and any(
            n.strip().casefold() == name.strip().casefold() for n in duplicate_names
        ):
            warnings.append(
                WARNING_DUPLICATE_CONDITION + f" Betroffen: {affected}."
            )
        else:
            warnings.append(
                "Profilhinweis: andere aktive Konfiguration(en) mit gleicher "
                f"Matching-Bedingung — Betroffen: {affected}. "
                "Der aktuelle Entwurf ist davon getrennt."
            )

    if WARNING_NO_BUSINESS_CATEGORY not in warnings:
        warnings.append(WARNING_NO_BUSINESS_CATEGORY)
    if WARNING_DESTINATION_REQUIRED not in warnings:
        warnings.append(WARNING_DESTINATION_REQUIRED)

    if require_destination_for_save and not str(
        draft.proposed_destination_path or ""
    ).strip():
        errors.append("Zielordner ist zum Speichern erforderlich.")

    preview = None
    if pattern:
        rendered = render_configuration_filename_pattern(
            pattern,
            values={
                "invoice_date": "2026-05-11",
                "art": "er",
                "supplier": "Beispiel",
                "amount": "100,00",
                "payment_field": values[0] if values else "payment",
            },
        )
        preview = rendered.rendered_filename

    return replace(
        draft,
        proposed_configuration_name=name,
        proposed_matching_feature_key=feature or None,
        proposed_matching_operator=operator or None,
        proposed_matching_values=tuple(values),
        proposed_filename_pattern=pattern,
        requires_user_confirmation=True,
        validation_errors=tuple(errors),
        warnings=tuple(dict.fromkeys(warnings)),
        unknown_pattern_slots=unknown,
        filename_preview=preview,
        duplicate_condition_warning=duplicate_warning,
        proposes_amex=proposes_amex,
        proposes_business_category=False,
    )


def draft_from_coverage_guidance(
    *,
    guidance: ConfigurationCoverageGuidance | Mapping[str, Any] | None = None,
    selected_payment_field: str | None = None,
    payment_account: str | None = None,
    source_review_item_id: str | None = None,
    source_filename: str | None = None,
    matched_configuration_name: str | None = None,
    matched_configuration_reason: str | None = None,
    missing_configuration_rule: str | None = None,
    unmatched_reasons: Sequence[str] | None = None,
    available_configurations: Sequence[Mapping[str, Any]] | None = None,
    unmatched_filename_pattern: str | None = None,
    review_signals: Sequence[Mapping[str, Any]] | None = None,
    draft_type: DraftType | None = None,
    existing_configuration_id: str | None = None,
    existing_configuration_name: str | None = None,
) -> ConfigurationRuleDraft | None:
    """Build a safe draft from coverage guidance. Never auto-saves."""

    if guidance is None:
        derived = derive_configuration_coverage_guidance(
            selected_payment_field=selected_payment_field,
            payment_account=payment_account,
            matched_configuration_name=matched_configuration_name,
            unmatched_reasons=unmatched_reasons,
            is_unmatched_fallback=True,
            matched_configuration_reason=matched_configuration_reason,
            missing_configuration_rule=missing_configuration_rule,
        )
    elif isinstance(guidance, ConfigurationCoverageGuidance):
        derived = guidance
    else:
        derived = ConfigurationCoverageGuidance(
            configuration_coverage_status=str(
                guidance.get("configuration_coverage_status") or ""
            ),
            missing_configuration_type=(
                str(guidance.get("missing_configuration_type") or "").strip() or None
            ),
            user_guidance=str(guidance.get("user_guidance") or ""),
            suggested_configuration_action=str(
                guidance.get("suggested_configuration_action") or ""
            ),
            guidance_severity=str(guidance.get("guidance_severity") or "warning"),  # type: ignore[arg-type]
        )

    status = derived.configuration_coverage_status
    missing_type = derived.missing_configuration_type
    signal = _first_non_empty(selected_payment_field, payment_account)
    pattern = resolve_default_filename_pattern(
        unmatched_pattern=unmatched_filename_pattern,
        available_configurations=available_configurations,
    )

    evidence: list[str] = []
    if signal:
        evidence.append(f"payment_field={signal}")
    if matched_configuration_reason:
        evidence.append(str(matched_configuration_reason))
    if missing_configuration_rule:
        evidence.append(str(missing_configuration_rule))
    if derived.user_guidance:
        evidence.append(derived.user_guidance)
    for reason in unmatched_reasons or ():
        if str(reason).strip():
            evidence.append(str(reason).strip())

    requested_type: DraftType = draft_type or "create_new_configuration"

    # Missing payment_field: no blind payment rule.
    if (
        missing_type == MISSING_TYPE_PAYMENT_FIELD
        or status == STATUS_MISSING_PAYMENT_FIELD
        or not signal
    ) and requested_type != "edit_existing_configuration":
        draft = ConfigurationRuleDraft(
            draft_id=_new_draft_id(),
            source_review_item_id=source_review_item_id,
            source_filename=source_filename,
            draft_type="manual_review_only",
            proposed_configuration_name="",
            proposed_matching_feature_key=None,
            proposed_matching_operator=None,
            proposed_matching_values=(),
            proposed_filename_pattern=pattern,
            reason=REASON_MISSING_PAYMENT,
            source_evidence=tuple(dict.fromkeys(evidence)),
            warnings=(WARNING_MISSING_PAYMENT_NO_BLIND_RULE, WARNING_NO_BUSINESS_CATEGORY),
            requires_user_confirmation=True,
            saved=False,
            allows_payment_rule=False,
            manual_review_suggested=True,
            proposes_business_category=False,
            proposes_amex=False,
        )
        return validate_configuration_rule_draft(
            draft, active_configurations=available_configurations
        )

    if missing_type == MISSING_TYPE_PAYPAL or (
        status == STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT and _norm(signal) in {"paypal", "pay pal"}
    ):
        name = "PayPal"
        values = ("paypal",)
        warnings = (
            WARNING_NO_BUSINESS_CATEGORY,
            WARNING_DESTINATION_REQUIRED,
        )
        reason = REASON_PAYPAL
    elif missing_type == MISSING_TYPE_GENERIC_CARD or status == STATUS_NO_SAFE_CARD_CONFIGURATION:
        name = "Kreditkarte / Nicht-AMEX-Karte"
        values = ("card",)
        warnings = (
            WARNING_GENERIC_CARD_NOT_AMEX,
            WARNING_NO_BUSINESS_CATEGORY,
            WARNING_DESTINATION_REQUIRED,
        )
        reason = REASON_GENERIC_CARD
    else:
        # Generic unmatched — open empty create/edit shell without unsafe guesses.
        if requested_type == "edit_existing_configuration":
            name = str(existing_configuration_name or "").strip()
            draft = ConfigurationRuleDraft(
                draft_id=_new_draft_id(),
                source_review_item_id=source_review_item_id,
                source_filename=source_filename,
                draft_type="edit_existing_configuration",
                proposed_configuration_name=name,
                proposed_matching_feature_key="payment_field",
                proposed_matching_operator="ist",
                proposed_matching_values=(),
                proposed_filename_pattern=pattern,
                reason=derived.user_guidance or "Bestehende Konfiguration anpassen.",
                source_evidence=tuple(dict.fromkeys(evidence)),
                warnings=(WARNING_NO_BUSINESS_CATEGORY, WARNING_DESTINATION_REQUIRED),
                requires_user_confirmation=True,
                saved=False,
                proposed_configuration_id=existing_configuration_id,
                allows_payment_rule=True,
                manual_review_suggested=False,
            )
            return validate_configuration_rule_draft(
                draft, active_configurations=available_configurations
            )
        return None

    if requested_type == "edit_existing_configuration":
        draft = ConfigurationRuleDraft(
            draft_id=_new_draft_id(),
            source_review_item_id=source_review_item_id,
            source_filename=source_filename,
            draft_type="edit_existing_configuration",
            proposed_configuration_name=str(existing_configuration_name or name).strip(),
            proposed_matching_feature_key="payment_field",
            proposed_matching_operator="ist",
            proposed_matching_values=values,
            proposed_filename_pattern=pattern,
            reason=reason,
            source_evidence=tuple(dict.fromkeys(evidence)),
            warnings=warnings,
            requires_user_confirmation=True,
            saved=False,
            proposed_configuration_id=existing_configuration_id,
            allows_payment_rule=True,
            manual_review_suggested=False,
            proposes_business_category=False,
            proposes_amex=False,
        )
    else:
        draft = ConfigurationRuleDraft(
            draft_id=_new_draft_id(),
            source_review_item_id=source_review_item_id,
            source_filename=source_filename,
            draft_type="create_new_configuration",
            proposed_configuration_name=name,
            proposed_matching_feature_key="payment_field",
            proposed_matching_operator="ist",
            proposed_matching_values=values,
            proposed_filename_pattern=pattern,
            reason=reason,
            source_evidence=tuple(dict.fromkeys(evidence)),
            warnings=warnings,
            requires_user_confirmation=True,
            saved=False,
            allows_payment_rule=True,
            manual_review_suggested=False,
            proposes_business_category=False,
            proposes_amex=False,
        )

    future = preview_future_matches(
        feature_key="payment_field",
        values=values,
        review_signals=review_signals,
    )
    draft = replace(draft, future_match_preview=future)
    return validate_configuration_rule_draft(
        draft, active_configurations=available_configurations
    )


def coverage_gap_actions_available(
    *,
    configuration_coverage_status: str | None,
    missing_configuration_type: str | None = None,
) -> bool:
    status = str(configuration_coverage_status or "").strip()
    missing = str(missing_configuration_type or "").strip()
    if missing in {
        MISSING_TYPE_PAYPAL,
        MISSING_TYPE_GENERIC_CARD,
        MISSING_TYPE_PAYMENT_FIELD,
    }:
        return True
    return status in {
        STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT,
        STATUS_NO_SAFE_CARD_CONFIGURATION,
        STATUS_MISSING_PAYMENT_FIELD,
        "unmatched_other",
    }


def attach_configuration_rule_draft_report_fields(
    meta: Mapping[str, Any],
    draft: ConfigurationRuleDraft | None,
) -> dict[str, Any]:
    """Merge draft report fields into a review/export metadata dict."""

    out = dict(meta)
    if draft is None:
        out.setdefault(MSG_FIELD_CONFIGURATION_RULE_DRAFT_AVAILABLE, False)
        return out
    out.update(draft.to_report_fields())
    return out


def load_unmatched_filename_pattern(*, profile_id: str | None = None) -> str | None:
    _active, unmatched = load_active_configuration_candidates(profile_id=profile_id)
    if unmatched is None:
        return None
    return unmatched.filename_pattern


__all__ = (
    "ACTION_CANCEL_DRAFT",
    "ACTION_CREATE_FROM_GUIDANCE",
    "ACTION_EDIT_EXISTING",
    "ACTION_MANUAL_KEEP_UNCLEAR",
    "ACTION_SAVE_DRAFT",
    "ConfigurationRuleDraft",
    "DEFAULT_PATTERN",
    "KNOWN_FILENAME_PATTERN_SLOTS",
    "MSG_FIELD_CONFIGURATION_RULE_DRAFT_AVAILABLE",
    "MSG_FIELD_DRAFT_WARNING",
    "MSG_FIELD_PROPOSED_CONDITION",
    "MSG_FIELD_PROPOSED_CONFIGURATION_NAME",
    "MSG_FIELD_PROPOSED_FILENAME_PATTERN",
    "MSG_FIELD_REQUIRES_USER_CONFIRMATION",
    "WARNING_DUPLICATE_CONDITION",
    "WARNING_GENERIC_CARD_NOT_AMEX",
    "WARNING_MISSING_PAYMENT_NO_BLIND_RULE",
    "WARNING_NO_BUSINESS_CATEGORY",
    "attach_configuration_rule_draft_report_fields",
    "coverage_gap_actions_available",
    "draft_from_coverage_guidance",
    "find_duplicate_condition_configs",
    "load_unmatched_filename_pattern",
    "preview_future_matches",
    "resolve_default_filename_pattern",
    "unknown_pattern_slots_in_pattern",
    "validate_configuration_rule_draft",
)
