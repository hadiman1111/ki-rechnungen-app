"""UI-v2 policy → runtime-intent bridge (Track B).

Translates classification/profile policy into a structured runtime request shape
without executing the processing core, reading folders, or processing PDFs.

Does not import invoice_tool.processing / invoice_tool.run / routing / classification.
A future LocalProcessingAdapter may consume RuntimePolicyIntent under a separate PO gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from invoice_tool.saas_product_model import (
    ClassificationPolicy,
    classification_policy_from_dict,
    default_classification_policy,
)

BridgeStatus = Literal["ready", "incomplete", "blocked"]

MSG_POLICY_INCOMPLETE = "Verarbeitungsregeln sind noch nicht vollständig konfiguriert."
MSG_UNKNOWN_EVIDENCE_REVIEW = "Unklare Nachweise werden später zur Prüfung gestellt."
MSG_POLICY_BLOCKED_UNSAFE = (
    "Verarbeitungsregeln sind unsicher oder widersprüchlich und blockieren den Lauf-Intent."
)
MSG_FILENAME_NOT_SOURCE_OF_TRUTH = (
    "Dateiname ist keine Beweisquelle; Quelle der Wahrheit ist Beleginhalt "
    "plus konfigurierte Profilnachweise."
)
MSG_SUPPLIER_IBAN_NOT_PAYER = (
    "Lieferanten-IBAN allein ist kein Zahlernachweis."
)
MSG_GENERIC_CARD_UNCLEAR = (
    "Unspezifische Kartentexte ohne konfigurierte Kontoreferenz bleiben unklar/zur Prüfung."
)

# Safe runtime targets — never invent private payer/business defaults.
TARGET_UNKLAR = "unklar"
SOURCE_OF_TRUTH_DOCUMENT_AND_PROFILE = "document_content_and_configured_profile_evidence"
SOURCE_OF_TRUTH_FILENAME = "filename"  # never allowed as active SOT


@dataclass(frozen=True)
class RuntimePolicyIntent:
    """Structured policy intent for a future bounded processing adapter."""

    invoice_detection_policy: dict[str, Any] = field(default_factory=dict)
    payment_evidence_policy: dict[str, Any] = field(default_factory=dict)
    business_assignment_policy: dict[str, Any] = field(default_factory=dict)
    review_policy: dict[str, Any] = field(default_factory=dict)
    filename_policy: dict[str, Any] = field(default_factory=dict)
    unknown_evidence_policy: dict[str, Any] = field(default_factory=dict)
    source_of_truth_policy: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "invoice_detection_policy": dict(self.invoice_detection_policy),
            "payment_evidence_policy": dict(self.payment_evidence_policy),
            "business_assignment_policy": dict(self.business_assignment_policy),
            "review_policy": dict(self.review_policy),
            "filename_policy": dict(self.filename_policy),
            "unknown_evidence_policy": dict(self.unknown_evidence_policy),
            "source_of_truth_policy": dict(self.source_of_truth_policy),
        }


@dataclass(frozen=True)
class RuntimePolicyBridgeResult:
    """Outcome of translating UI-v2 policy into runtime intent (no processing)."""

    status: BridgeStatus
    intent: RuntimePolicyIntent | None = None
    warnings: tuple[str, ...] = ()
    review_required_reason: str | None = None
    missing_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "intent": self.intent.to_dict() if self.intent is not None else None,
            "warnings": list(self.warnings),
            "review_required_reason": self.review_required_reason,
            "missing_fields": list(self.missing_fields),
        }


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        raw = to_dict()
        if isinstance(raw, Mapping):
            return raw
    return None


def _extract_policy_payload(source: Any) -> ClassificationPolicy | None:
    """Resolve a ClassificationPolicy from UI-v2 policy/profile/config shapes."""

    if source is None:
        return None
    if isinstance(source, ClassificationPolicy):
        return source

    mapping = _as_mapping(source)
    if mapping is not None:
        if "classification_policy" in mapping:
            nested = mapping.get("classification_policy")
            if nested is None:
                return None
            if isinstance(nested, ClassificationPolicy):
                return nested
            if isinstance(nested, Mapping):
                return classification_policy_from_dict(nested)
            nested_map = _as_mapping(nested)
            if nested_map is not None:
                return classification_policy_from_dict(nested_map)
            return None
        # Treat bare policy dicts as classification policy payloads.
        policy_keys = {
            "invoice_detection_policy",
            "payment_evidence_policy",
            "business_assignment_policy",
            "require_explicit_payer_payment_evidence",
            "unknown_payment_target",
        }
        if policy_keys.intersection(mapping.keys()):
            return classification_policy_from_dict(mapping)
        return None

    nested = getattr(source, "classification_policy", None)
    if isinstance(nested, ClassificationPolicy):
        return nested
    nested_map = _as_mapping(nested)
    if nested_map is not None:
        return classification_policy_from_dict(nested_map)
    return None


def _normalize_target(value: Any, *, fallback: str = TARGET_UNKLAR) -> str:
    text = str(value or "").strip().lower()
    if text in {"unklar", "zur_pruefung", "zur-prüfung", "review"}:
        return TARGET_UNKLAR
    if text in {"documents", "document"}:
        return "documents"
    return fallback


def _build_intent_from_policy(policy: ClassificationPolicy) -> RuntimePolicyIntent:
    idp = policy.invoice_detection_policy
    pep = policy.payment_evidence_policy
    bap = policy.business_assignment_policy
    unknown_payment = _normalize_target(policy.unknown_payment_target)
    unknown_card = _normalize_target(pep.generic_credit_card_without_identifier_target)
    unknown_mixed = _normalize_target(policy.mixed_business_private_address_target)

    # Hard safety overlays — never allow filename-as-truth or private payer shortcuts.
    filename_is_not_sot = True
    supplier_iban_not_payer = True
    card_requires_reference = True
    org_ids_profile_configured = True

    invoice_detection = {
        "invoice_indicators_override_format_notes": bool(
            idp.invoice_indicators_override_format_notes
        ),
        "format_availability_notes_are_not_document_type": bool(
            idp.format_availability_notes_are_not_document_type
        ),
        "filename_is_not_source_of_truth": filename_is_not_sot,
    }
    payment_evidence = {
        "require_explicit_payer_payment_evidence": bool(
            policy.require_explicit_payer_payment_evidence
        ),
        "supplier_bank_details_are_payment_evidence": False,
        "supplier_bank_details_are_not_payer_evidence": supplier_iban_not_payer,
        "card_payment_requires_known_reference": card_requires_reference,
        "apple_pay_requires_known_card_reference": bool(
            policy.apple_pay_requires_known_card_reference
        ),
        "generic_credit_card_without_identifier_target": unknown_card or TARGET_UNKLAR,
        "explicit_document_payment_method_takes_precedence": bool(
            pep.explicit_document_payment_method_takes_precedence
        ),
        "unknown_payment_target": unknown_payment or TARGET_UNKLAR,
    }
    business_assignment = {
        "business_billing_address_assigns_business_context": bool(
            bap.business_billing_address_assigns_business_context
        ),
        "ambiguous_items_do_not_override_business_billing_address": bool(
            bap.ambiguous_items_do_not_override_business_billing_address
        ),
        "organization_identifiers_are_profile_configured": org_ids_profile_configured,
        "business_payment_account_rules_are_profile_configured": True,
    }
    review_policy = {
        "unknown_payment_target": unknown_payment or TARGET_UNKLAR,
        "unknown_business_target": unknown_mixed or TARGET_UNKLAR,
        "unknown_evidence_goes_to_review": True,
        "review_message": MSG_UNKNOWN_EVIDENCE_REVIEW,
    }
    filename_policy = {
        "filename_is_source_of_truth": False,
        "filename_is_not_source_of_truth": True,
        "filename_may_hint_only": True,
    }
    unknown_evidence_policy = {
        "unknown_payment_evidence_target": TARGET_UNKLAR,
        "unknown_business_evidence_target": TARGET_UNKLAR,
        "generic_card_text_without_configured_account_reference_target": TARGET_UNKLAR,
        "supplier_iban_alone_is_not_payer_evidence": True,
        "review_required_message": MSG_UNKNOWN_EVIDENCE_REVIEW,
    }
    source_of_truth_policy = {
        "primary_source": SOURCE_OF_TRUTH_DOCUMENT_AND_PROFILE,
        "filename_is_source_of_truth": False,
        "private_defaults_allowed": False,
        "profile_configured_evidence_required": True,
    }

    return RuntimePolicyIntent(
        invoice_detection_policy=invoice_detection,
        payment_evidence_policy=payment_evidence,
        business_assignment_policy=business_assignment,
        review_policy=review_policy,
        filename_policy=filename_policy,
        unknown_evidence_policy=unknown_evidence_policy,
        source_of_truth_policy=source_of_truth_policy,
    )


def _collect_unsafe_reasons(policy: ClassificationPolicy) -> list[str]:
    reasons: list[str] = []
    if not policy.invoice_detection_policy.filename_is_not_source_of_truth:
        reasons.append(MSG_FILENAME_NOT_SOURCE_OF_TRUTH)
    if policy.supplier_bank_details_are_payment_evidence:
        reasons.append(MSG_SUPPLIER_IBAN_NOT_PAYER)
    if not policy.payment_evidence_policy.supplier_bank_details_are_not_payer_evidence:
        reasons.append(MSG_SUPPLIER_IBAN_NOT_PAYER)
    if not policy.payment_evidence_policy.card_payment_requires_known_reference:
        reasons.append(MSG_GENERIC_CARD_UNCLEAR)
    if (
        _normalize_target(policy.payment_evidence_policy.generic_credit_card_without_identifier_target)
        != TARGET_UNKLAR
        and not policy.payment_evidence_policy.card_payment_requires_known_reference
    ):
        reasons.append(MSG_GENERIC_CARD_UNCLEAR)
    if not policy.business_assignment_policy.organization_identifiers_are_profile_configured:
        reasons.append(
            "Organisationskennungen und Kontonachweise müssen profilkonfiguriert bleiben."
        )
    return reasons


def build_runtime_policy_intent(source: Any = None) -> RuntimePolicyBridgeResult:
    """Translate UI-v2 policy/profile/config into RuntimePolicyIntent.

    Never calls processing-core, never reads files, never processes PDFs.
    """

    if source is None:
        return RuntimePolicyBridgeResult(
            status="incomplete",
            intent=None,
            warnings=(MSG_POLICY_INCOMPLETE, MSG_UNKNOWN_EVIDENCE_REVIEW),
            review_required_reason=MSG_UNKNOWN_EVIDENCE_REVIEW,
            missing_fields=("classification_policy",),
        )

    policy = _extract_policy_payload(source)
    if policy is None:
        return RuntimePolicyBridgeResult(
            status="incomplete",
            intent=None,
            warnings=(MSG_POLICY_INCOMPLETE, MSG_UNKNOWN_EVIDENCE_REVIEW),
            review_required_reason=MSG_UNKNOWN_EVIDENCE_REVIEW,
            missing_fields=("classification_policy",),
        )

    intent = _build_intent_from_policy(policy)
    unsafe = _collect_unsafe_reasons(policy)
    if unsafe:
        # Intent still carries safe overlays for inspection, but status is blocked.
        deduped = tuple(dict.fromkeys(unsafe))
        return RuntimePolicyBridgeResult(
            status="blocked",
            intent=intent,
            warnings=deduped + (MSG_POLICY_BLOCKED_UNSAFE,),
            review_required_reason=MSG_UNKNOWN_EVIDENCE_REVIEW,
            missing_fields=(),
        )

    warnings = (
        MSG_FILENAME_NOT_SOURCE_OF_TRUTH,
        MSG_SUPPLIER_IBAN_NOT_PAYER,
        MSG_GENERIC_CARD_UNCLEAR,
        MSG_UNKNOWN_EVIDENCE_REVIEW,
    )
    return RuntimePolicyBridgeResult(
        status="ready",
        intent=intent,
        warnings=warnings,
        review_required_reason=MSG_UNKNOWN_EVIDENCE_REVIEW,
        missing_fields=(),
    )


def build_default_safe_runtime_policy_intent() -> RuntimePolicyBridgeResult:
    """Bridge from generic blank ClassificationPolicy defaults (no private tenant data)."""

    return build_runtime_policy_intent(default_classification_policy())


def describe_future_local_processing_adapter_consumption() -> str:
    """Describe how a later bounded LocalProcessingAdapter may use this intent.

    A future adapter may read RuntimePolicyIntent from ProcessingRunRequest and map
    safe flags into core options — without treating filenames as truth and without
    private hardcoded payer/business defaults. Wiring that adapter is PO-gated and
    must not happen in this module (no import of processing.py / run.py).
    """

    return (
        "Future LocalProcessingAdapter may consume RuntimePolicyIntent from "
        "ProcessingRunRequest.policy_intent / policy_bridge_result.intent. "
        "It must keep filename_is_not_source_of_truth, map unknown evidence to "
        "review/unklar, require profile-configured business/payment/account evidence, "
        "and must not import or call processing until a separate PO-gated task."
    )
