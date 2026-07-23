"""Track-B suggested filename mapping (Prompt 18–19/34).

Builds safe, non-final suggested PDF filenames via the canonical Track-B
template:

    <YYMMDD>_<DOCUMENT_DIRECTION>_<BUSINESS_CATEGORY>_<COUNTERPARTY_NAME>_<AMOUNT>.pdf

Never calls run_once, never writes/moves/archives files, never invents
supplier/date/amount tokens when fields are absent (uses explicit Unklar
markers inside the canonical template instead).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

from invoice_tool.ui_v2.canonical_filename_template import (
    BUSINESS_CATEGORY_UNCLEAR,
    DOCUMENT_DIRECTION_UNCLEAR,
    FILENAME_TEMPLATE_VERSION,
    CanonicalFilenameFields,
    build_canonical_filename,
    sanitize_canonical_filename,
    sanitize_filename_component,
)

NamingConfidence = Literal["none", "low", "medium", "high"]
FilenameSource = Literal[
    "suggested_mapping",
    "planned_result",
    "original_fallback",
]

# Kept for Prompt-18 compatibility; canonical template is authoritative.
DEFAULT_FILENAME_PATTERN = (
    "{invoice_date}_{document_direction}_{business_category}"
    "_{supplier}_{amount}.pdf"
)

FILENAME_SOURCE_SUGGESTED_MAPPING: FilenameSource = "suggested_mapping"
FILENAME_SOURCE_PLANNED_RESULT: FilenameSource = "planned_result"
FILENAME_SOURCE_ORIGINAL_FALLBACK: FilenameSource = "original_fallback"

MSG_NAMING_REASON_STRUCTURED = (
    "Vorschlagsname aus kanonischem Track-B-Muster "
    "(Datum/Rechnungsart/Zuordnung/Name/Betrag); "
    "Review bleibt erforderlich — nicht final."
)
MSG_NAMING_REASON_PARTIAL = (
    "Teilfelder für kanonischen Vorschlagsnamen vorhanden; "
    "unklare Felder explizit markiert; Review bleibt erforderlich."
)
MSG_NAMING_REASON_MISSING = (
    "Keine ausreichenden strukturierten Felder für einen abweichenden "
    "Vorschlagsnamen — Originalname als Fallback."
)
MSG_NAMING_REASON_PLANNED_BASENAME = (
    "Vorschlagsname aus geplantem Basename (abweichend vom Original); "
    "Review bleibt erforderlich — nicht final."
)

# Never embed these in suggested filenames unless explicitly allow-listed.
FORBIDDEN_SENSITIVE_FIELD_KEYS = frozenset(
    {
        "iban",
        "bic",
        "account_number",
        "konto",
        "card_number",
        "credit_card",
        "pan",
        "cvv",
        "ssn",
        "tax_id",
        "ust_id",
        "vat_id",
        "street",
        "address",
        "phone",
        "email",
        "personal_name",
    }
)


@dataclass(frozen=True)
class SuggestedFilenameFields:
    """Structured naming inputs — absent fields stay None (never invented)."""

    supplier: str | None = None
    vendor: str | None = None
    invoice_date: str | None = None
    amount: str | None = None
    document_type: str | None = None
    payment_account: str | None = None
    source_filename: str | None = None
    target_folder: str | None = None
    planned_basename: str | None = None
    confidence: NamingConfidence | None = None
    review_reason: str | None = None
    document_direction: str | None = None
    business_category: str | None = None
    counterparty_name: str | None = None
    routing_category: str | None = None
    profile_category: str | None = None
    direction_hint: str | None = None
    own_issuer_hints: tuple[str, ...] = field(default_factory=tuple)
    recipient_hints: tuple[str, ...] = field(default_factory=tuple)
    raw_text_head: str | None = None


@dataclass(frozen=True)
class SuggestedFilenameMappingResult:
    """Safe mapping output for Track-B preview / review / manifest."""

    suggested_filename: str | None
    filename_source: FilenameSource
    naming_confidence: NamingConfidence
    naming_reason: str
    suggested_filename_fields: tuple[str, ...] = field(default_factory=tuple)
    supplier: str | None = None
    invoice_date: str | None = None
    amount: str | None = None
    document_type: str | None = None
    payment_account: str | None = None
    source_filename: str | None = None
    review_required: bool = True
    canonical_filename: str | None = None
    filename_template_version: str | None = None
    document_direction: str | None = None
    business_category: str | None = None
    business_category_display: str | None = None
    counterparty_name: str | None = None
    missing_fields: tuple[str, ...] = field(default_factory=tuple)


def sanitize_suggested_filename(name: str | None) -> str | None:
    """Return a safe PDF basename or None."""

    return sanitize_canonical_filename(name)


def _clean_optional(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _supplier_token(fields: SuggestedFilenameFields) -> str | None:
    return _clean_optional(fields.supplier) or _clean_optional(fields.vendor)


def _present_field_keys(fields: SuggestedFilenameFields) -> tuple[str, ...]:
    present: list[str] = []
    if _supplier_token(fields) or _clean_optional(fields.counterparty_name):
        present.append("supplier")
    if _clean_optional(fields.invoice_date):
        present.append("invoice_date")
    if _clean_optional(fields.amount):
        present.append("amount")
    if _clean_optional(fields.document_type):
        present.append("document_type")
    if _clean_optional(fields.payment_account):
        present.append("payment_account")
    if _clean_optional(fields.document_direction) or _clean_optional(
        fields.direction_hint
    ):
        present.append("document_direction")
    if (
        _clean_optional(fields.business_category)
        or _clean_optional(fields.routing_category)
        or _clean_optional(fields.profile_category)
    ):
        present.append("business_category")
    return tuple(present)


def _assert_no_forbidden_keys(extra: Mapping[str, Any] | None) -> None:
    if not extra:
        return
    for key in extra:
        lowered = str(key).strip().lower()
        if lowered in FORBIDDEN_SENSITIVE_FIELD_KEYS:
            raise ValueError(
                f"Forbidden sensitive field not allowed in suggested filename: {key}"
            )


def render_suggested_filename(
    fields: SuggestedFilenameFields,
    *,
    pattern: str = DEFAULT_FILENAME_PATTERN,
    extra_values: Mapping[str, Any] | None = None,
) -> str | None:
    """Render a suggested basename via the canonical Track-B template.

    ``pattern`` is accepted for API compatibility but ignored — the canonical
    component order is fixed. Missing tokens become explicit Unklar markers.
    """

    _ = pattern
    _assert_no_forbidden_keys(extra_values)
    supplier = _supplier_token(fields)
    if not any(
        (
            supplier,
            _clean_optional(fields.counterparty_name),
            _clean_optional(fields.invoice_date),
            _clean_optional(fields.amount),
            _clean_optional(fields.document_direction),
            _clean_optional(fields.business_category),
        )
    ):
        return None
    result = build_canonical_filename(
        CanonicalFilenameFields(
            invoice_date=fields.invoice_date,
            document_direction=fields.document_direction,
            business_category=fields.business_category,
            counterparty_name=fields.counterparty_name or supplier,
            amount=fields.amount,
            document_type=fields.document_type,
            confidence=fields.confidence,
            source_filename=fields.source_filename,
            review_reason=fields.review_reason,
            supplier=fields.supplier,
            vendor=fields.vendor,
            routing_category=fields.routing_category,
            profile_category=fields.profile_category,
            target_folder=fields.target_folder,
            direction_hint=fields.direction_hint,
            own_issuer_hints=fields.own_issuer_hints,
            recipient_hints=fields.recipient_hints,
            raw_text_head=fields.raw_text_head,
        ),
        review_required=True,
        extra_values=extra_values,
    )
    return result.canonical_filename


def map_suggested_filename(
    fields: SuggestedFilenameFields,
    *,
    pattern: str = DEFAULT_FILENAME_PATTERN,
    review_required: bool = True,
    extra_values: Mapping[str, Any] | None = None,
) -> SuggestedFilenameMappingResult:
    """Map structured fields to a Track-B suggested filename decision."""

    _ = pattern
    present = _present_field_keys(fields)
    source_name = _clean_optional(fields.source_filename)
    supplier = _supplier_token(fields)
    invoice_date = _clean_optional(fields.invoice_date)
    amount = _clean_optional(fields.amount)
    document_type = _clean_optional(fields.document_type)
    payment_account = _clean_optional(fields.payment_account)

    has_core = bool(supplier or fields.counterparty_name or invoice_date or amount)
    if not has_core:
        # Planned basename may already differ from the source (bridge / planner).
        planned = sanitize_suggested_filename(fields.planned_basename)
        if planned and source_name:
            if planned.lower() != (sanitize_suggested_filename(source_name) or "").lower():
                return SuggestedFilenameMappingResult(
                    suggested_filename=planned,
                    filename_source=FILENAME_SOURCE_PLANNED_RESULT,
                    naming_confidence="low",
                    naming_reason=MSG_NAMING_REASON_PLANNED_BASENAME,
                    suggested_filename_fields=present,
                    supplier=supplier,
                    invoice_date=invoice_date,
                    amount=amount,
                    document_type=document_type,
                    payment_account=payment_account,
                    source_filename=source_name,
                    review_required=review_required,
                    canonical_filename=planned,
                    filename_template_version=None,
                    document_direction=DOCUMENT_DIRECTION_UNCLEAR,
                    business_category=BUSINESS_CATEGORY_UNCLEAR,
                    business_category_display="Unklare_Zuordnung",
                    counterparty_name=supplier,
                    missing_fields=("document_direction", "business_category"),
                )
        return SuggestedFilenameMappingResult(
            suggested_filename=None,
            filename_source=FILENAME_SOURCE_ORIGINAL_FALLBACK,
            naming_confidence="none",
            naming_reason=MSG_NAMING_REASON_MISSING,
            suggested_filename_fields=present,
            supplier=supplier,
            invoice_date=invoice_date,
            amount=amount,
            document_type=document_type,
            payment_account=payment_account,
            source_filename=source_name,
            review_required=review_required,
            canonical_filename=None,
            filename_template_version=FILENAME_TEMPLATE_VERSION,
            document_direction=DOCUMENT_DIRECTION_UNCLEAR,
            business_category=BUSINESS_CATEGORY_UNCLEAR,
            business_category_display="Unklare_Zuordnung",
            counterparty_name=supplier,
            missing_fields=(
                "invoice_date",
                "document_direction",
                "business_category",
                "counterparty_name",
                "amount",
            ),
        )

    canonical = build_canonical_filename(
        CanonicalFilenameFields(
            invoice_date=fields.invoice_date,
            document_direction=fields.document_direction,
            business_category=fields.business_category,
            counterparty_name=fields.counterparty_name or supplier,
            amount=fields.amount,
            document_type=fields.document_type,
            confidence=fields.confidence,
            source_filename=fields.source_filename,
            review_reason=fields.review_reason,
            supplier=fields.supplier,
            vendor=fields.vendor,
            routing_category=fields.routing_category,
            profile_category=fields.profile_category,
            target_folder=fields.target_folder,
            direction_hint=fields.direction_hint,
            own_issuer_hints=fields.own_issuer_hints,
            recipient_hints=fields.recipient_hints,
            raw_text_head=fields.raw_text_head,
        ),
        review_required=review_required,
        extra_values=extra_values,
    )
    suggested = canonical.canonical_filename
    if suggested and source_name:
        if suggested.lower() == sanitize_suggested_filename(source_name):
            suggested = None

    if suggested is None:
        return SuggestedFilenameMappingResult(
            suggested_filename=None,
            filename_source=FILENAME_SOURCE_ORIGINAL_FALLBACK,
            naming_confidence="none",
            naming_reason=MSG_NAMING_REASON_MISSING,
            suggested_filename_fields=present,
            supplier=supplier,
            invoice_date=invoice_date,
            amount=amount,
            document_type=document_type,
            payment_account=payment_account,
            source_filename=source_name,
            review_required=True,
            canonical_filename=canonical.canonical_filename,
            filename_template_version=canonical.filename_template_version,
            document_direction=canonical.document_direction,
            business_category=canonical.business_category,
            business_category_display=canonical.business_category_display,
            counterparty_name=canonical.counterparty_name,
            missing_fields=canonical.missing_fields,
        )

    reason = canonical.naming_reason or (
        MSG_NAMING_REASON_STRUCTURED
        if canonical.naming_confidence in {"medium", "high"}
        else MSG_NAMING_REASON_PARTIAL
    )
    return SuggestedFilenameMappingResult(
        suggested_filename=suggested,
        filename_source=FILENAME_SOURCE_SUGGESTED_MAPPING,
        naming_confidence=canonical.naming_confidence,
        naming_reason=reason,
        suggested_filename_fields=present
        + tuple(
            key
            for key in (
                "document_direction",
                "business_category",
                "canonical_filename",
            )
            if key not in present
        ),
        supplier=supplier,
        invoice_date=invoice_date or canonical.invoice_date,
        amount=amount or canonical.amount,
        document_type=document_type,
        payment_account=payment_account,
        source_filename=source_name,
        review_required=True,
        canonical_filename=canonical.canonical_filename,
        filename_template_version=canonical.filename_template_version,
        document_direction=canonical.document_direction,
        business_category=canonical.business_category,
        business_category_display=canonical.business_category_display,
        counterparty_name=canonical.counterparty_name,
        missing_fields=canonical.missing_fields,
    )


__all__ = (
    "DEFAULT_FILENAME_PATTERN",
    "FORBIDDEN_SENSITIVE_FIELD_KEYS",
    "FILENAME_SOURCE_ORIGINAL_FALLBACK",
    "FILENAME_SOURCE_PLANNED_RESULT",
    "FILENAME_SOURCE_SUGGESTED_MAPPING",
    "FILENAME_TEMPLATE_VERSION",
    "MSG_NAMING_REASON_MISSING",
    "MSG_NAMING_REASON_PARTIAL",
    "MSG_NAMING_REASON_PLANNED_BASENAME",
    "MSG_NAMING_REASON_STRUCTURED",
    "SuggestedFilenameFields",
    "SuggestedFilenameMappingResult",
    "map_suggested_filename",
    "render_suggested_filename",
    "sanitize_filename_component",
    "sanitize_suggested_filename",
)
