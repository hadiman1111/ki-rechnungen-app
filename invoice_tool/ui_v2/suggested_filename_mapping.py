"""Track-B suggested filename mapping (Prompt 18–20/34).

Primary source of truth: matched active configuration filename pattern.

Fallback only when no configuration pattern is available:
canonical Track-B template (Prompt 19 demoted).

Never calls run_once, never writes/moves/archives files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from invoice_tool.ui_v2.canonical_filename_template import (
    BUSINESS_CATEGORY_UNCLEAR,
    DOCUMENT_DIRECTION_UNCLEAR,
    FILENAME_TEMPLATE_VERSION,
    CanonicalFilenameFields,
    build_canonical_filename,
    sanitize_canonical_filename,
    sanitize_filename_component,
)
from invoice_tool.ui_v2.configuration_filename_renderer import (
    AMOUNT_FORMAT_COMMA_2,
    FILENAME_SOURCE_CANONICAL_FALLBACK,
    FILENAME_SOURCE_CONFIGURATION_PATTERN,
    FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE,
    FILENAME_SOURCE_ORIGINAL_FALLBACK,
    build_configuration_placeholder_values,
    format_amount_comma,
    render_configuration_filename_pattern,
)
from invoice_tool.ui_v2.configuration_guidance import (
    derive_configuration_coverage_guidance,
)
from invoice_tool.ui_v2.configuration_matching import (
    ConfigurationCandidate,
    ConfigurationMatchResult,
    match_active_configuration,
)

NamingConfidence = Literal["none", "low", "medium", "high"]
FilenameSource = Literal[
    "configuration_pattern",
    "configuration_pattern_incomplete",
    "canonical_fallback_no_configuration_pattern",
    "suggested_mapping",
    "planned_result",
    "original_fallback",
]

# Compatibility alias — canonical template is fallback-only now.
DEFAULT_FILENAME_PATTERN = (
    "{invoice_date}_{document_direction}_{business_category}"
    "_{supplier}_{amount}.pdf"
)

FILENAME_SOURCE_SUGGESTED_MAPPING: FilenameSource = "suggested_mapping"
FILENAME_SOURCE_PLANNED_RESULT: FilenameSource = "planned_result"

MSG_NAMING_REASON_STRUCTURED = (
    "Vorschlagsname aus Konfigurations-Dateinamensmuster; "
    "Review bleibt erforderlich — nicht final."
)
MSG_NAMING_REASON_PARTIAL = (
    "Konfigurationsmuster teilweise gerendert; fehlende Platzhalter explizit; "
    "Review bleibt erforderlich."
)
MSG_NAMING_REASON_CANONICAL_FALLBACK = (
    "Kein Konfigurations-Dateinamensmuster verfügbar — "
    "kanonischer Track-B-Fallback; Review bleibt erforderlich."
)
MSG_NAMING_REASON_MISSING = (
    "Keine ausreichenden strukturierten Felder für einen abweichenden "
    "Vorschlagsnamen — Originalname als Fallback."
)
MSG_NAMING_REASON_PLANNED_BASENAME = (
    "Vorschlagsname aus geplantem Basename (abweichend vom Original); "
    "Review bleibt erforderlich — nicht final."
)

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
    payment_field: str | None = None
    art: str | None = None
    filename_pattern: str | None = None
    matched_configuration_name: str | None = None
    matched_configuration_id: str | None = None
    selected_amount: str | None = None
    selected_amount_reason: str | None = None
    amount_candidates: tuple[dict[str, object], ...] = field(default_factory=tuple)
    rejected_amount_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    selected_payment_field: str | None = None
    selected_payment_field_reason: str | None = None
    payment_field_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    selected_art: str | None = None
    selected_art_reason: str | None = None
    document_art_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    art_ambiguity: bool = False


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
    matched_configuration_name: str | None = None
    matched_configuration_id: str | None = None
    matched_configuration_pattern: str | None = None
    matched_configuration_reason: str | None = None
    matched_configuration_confidence: str | None = None
    filename_pattern: str | None = None
    rendered_filename: str | None = None
    placeholder_values: tuple[tuple[str, str | None], ...] = field(default_factory=tuple)
    missing_placeholders: tuple[str, ...] = field(default_factory=tuple)
    amount_format: str | None = None
    amount_candidates: tuple[dict[str, object], ...] = field(default_factory=tuple)
    selected_amount: str | None = None
    selected_amount_reason: str | None = None
    rejected_amount_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    payment_field_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    selected_payment_field: str | None = None
    selected_payment_field_reason: str | None = None
    document_art_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    selected_art: str | None = None
    selected_art_reason: str | None = None
    art_ambiguity: bool = False
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
    configuration_coverage_status: str | None = None
    missing_configuration_type: str | None = None
    user_guidance: str | None = None
    suggested_configuration_action: str | None = None
    guidance_severity: str | None = None


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
    if _clean_optional(fields.payment_account) or _clean_optional(fields.payment_field):
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


def _candidate_meta(fields: SuggestedFilenameFields) -> dict[str, Any]:
    return {
        "amount_candidates": tuple(fields.amount_candidates or ()),
        "selected_amount": fields.selected_amount or format_amount_comma(fields.amount),
        "selected_amount_reason": fields.selected_amount_reason,
        "rejected_amount_candidates": tuple(fields.rejected_amount_candidates or ()),
        "payment_field_candidates": tuple(fields.payment_field_candidates or ()),
        "selected_payment_field": fields.selected_payment_field
        or fields.payment_field
        or fields.payment_account,
        "selected_payment_field_reason": fields.selected_payment_field_reason,
        "document_art_candidates": tuple(fields.document_art_candidates or ()),
        "selected_art": fields.selected_art or fields.art,
        "selected_art_reason": fields.selected_art_reason,
        "art_ambiguity": bool(fields.art_ambiguity),
    }


def _empty_match_transparency() -> dict[str, Any]:
    return {
        "matched_configuration_name": None,
        "matched_configuration_id": None,
        "matched_configuration_pattern": None,
        "matched_configuration_reason": None,
        "matched_configuration_confidence": None,
        "available_configurations": (),
        "evaluated_configuration_candidates": (),
        "unmatched_reasons": (),
        "condition_results": (),
        "alternative_matches": (),
        "missing_configuration_rule": None,
        "configuration_coverage_status": None,
        "missing_configuration_type": None,
        "user_guidance": None,
        "suggested_configuration_action": None,
        "guidance_severity": None,
    }


def _match_transparency(
    match: ConfigurationMatchResult | None,
    *,
    selected_payment_field: str | None = None,
    payment_account: str | None = None,
    absent_pattern_slots: Sequence[str] | None = None,
    document_type: str | None = None,
    supplier: str | None = None,
    source_filename: str | None = None,
    payment_field_candidates: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if match is None:
        base = _empty_match_transparency()
    else:
        base = match.transparency_fields()
    guidance = derive_configuration_coverage_guidance(
        selected_payment_field=selected_payment_field
        or (match.matched_payment_field if match else None),
        payment_account=payment_account,
        payment_field_candidates=payment_field_candidates,
        matched_configuration_name=base.get("matched_configuration_name"),
        evaluated_configuration_candidates=base.get(
            "evaluated_configuration_candidates"
        )
        or (),
        unmatched_reasons=base.get("unmatched_reasons") or (),
        absent_pattern_slots=absent_pattern_slots,
        document_type=document_type,
        supplier=supplier,
        source_filename=source_filename,
        is_unmatched_fallback=(
            match.is_unmatched_fallback if match is not None else True
        ),
        matched_configuration_reason=base.get("matched_configuration_reason"),
        missing_configuration_rule=base.get("missing_configuration_rule"),
    )
    return {**base, **guidance.to_export_fields()}


def _canonical_fallback(
    fields: SuggestedFilenameFields,
    *,
    review_required: bool,
    extra_values: Mapping[str, Any] | None,
    match: ConfigurationMatchResult | None,
) -> SuggestedFilenameMappingResult:
    present = _present_field_keys(fields)
    source_name = _clean_optional(fields.source_filename)
    supplier = _supplier_token(fields)
    invoice_date = _clean_optional(fields.invoice_date)
    amount = _clean_optional(fields.amount)
    document_type = _clean_optional(fields.document_type)
    payment_account = _clean_optional(fields.payment_account)

    has_core = bool(supplier or fields.counterparty_name or invoice_date or amount)
    payment_signal = (
        _clean_optional(fields.selected_payment_field)
        or _clean_optional(fields.payment_field)
        or payment_account
    )
    match_meta = {
        **_match_transparency(
            match,
            selected_payment_field=payment_signal,
            payment_account=payment_account,
            document_type=document_type,
            supplier=supplier,
            source_filename=source_name,
            payment_field_candidates=fields.payment_field_candidates,
        ),
        **_candidate_meta(fields),
    }
    if not has_core:
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
                    **match_meta,
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
            **match_meta,
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
            **match_meta,
        )
    return SuggestedFilenameMappingResult(
        suggested_filename=suggested,
        filename_source=FILENAME_SOURCE_CANONICAL_FALLBACK,
        naming_confidence=canonical.naming_confidence,
        naming_reason=(
            f"{MSG_NAMING_REASON_CANONICAL_FALLBACK} {canonical.naming_reason}"
        ).strip(),
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
        rendered_filename=suggested,
        **match_meta,
    )


def render_suggested_filename(
    fields: SuggestedFilenameFields,
    *,
    pattern: str = DEFAULT_FILENAME_PATTERN,
    extra_values: Mapping[str, Any] | None = None,
    configurations: Sequence[ConfigurationCandidate] | None = None,
    unmatched: ConfigurationCandidate | None = None,
    use_configuration_bridge: bool = True,
) -> str | None:
    """Render a suggested basename — configuration pattern preferred."""

    mapped = map_suggested_filename(
        fields,
        pattern=pattern,
        extra_values=extra_values,
        configurations=configurations,
        unmatched=unmatched,
        use_configuration_bridge=use_configuration_bridge,
    )
    return mapped.suggested_filename


def map_suggested_filename(
    fields: SuggestedFilenameFields,
    *,
    pattern: str = DEFAULT_FILENAME_PATTERN,
    review_required: bool = True,
    extra_values: Mapping[str, Any] | None = None,
    configurations: Sequence[ConfigurationCandidate] | None = None,
    unmatched: ConfigurationCandidate | None = None,
    use_configuration_bridge: bool = True,
) -> SuggestedFilenameMappingResult:
    """Map structured fields to a Track-B suggested filename decision."""

    _ = pattern  # legacy API; configuration pattern / canonical fallback are authoritative
    _assert_no_forbidden_keys(extra_values)
    present = _present_field_keys(fields)
    source_name = _clean_optional(fields.source_filename)
    supplier = _supplier_token(fields)
    invoice_date = _clean_optional(fields.invoice_date)
    amount = _clean_optional(fields.selected_amount) or _clean_optional(fields.amount)
    amount_comma = format_amount_comma(amount)
    document_type = _clean_optional(fields.document_type)
    payment_account = (
        _clean_optional(fields.selected_payment_field)
        or _clean_optional(fields.payment_account)
        or _clean_optional(fields.payment_field)
    )
    payment_field = (
        _clean_optional(fields.selected_payment_field)
        or _clean_optional(fields.payment_field)
        or payment_account
    )
    art_token = _clean_optional(fields.selected_art) or _clean_optional(fields.art)
    candidate_meta = _candidate_meta(fields)

    has_core = bool(supplier or fields.counterparty_name or invoice_date or amount)
    match: ConfigurationMatchResult | None = None
    config_pattern = _clean_optional(fields.filename_pattern)
    if use_configuration_bridge and has_core:
        match = match_active_configuration(
            payment_field=payment_field,
            payment_account=payment_account,
            supplier=supplier,
            recipient=_clean_optional(fields.counterparty_name),
            document_type=document_type,
            raw_text_head=fields.raw_text_head,
            configurations=configurations,
            unmatched=unmatched,
        )
        if not config_pattern:
            config_pattern = match.matched_configuration_pattern
        elif fields.matched_configuration_name or fields.matched_configuration_id:
            # Explicit pattern/name from caller wins for rendering; keep evaluator
            # transparency for review/manifest.
            from dataclasses import replace as _dc_replace

            match = _dc_replace(
                match,
                matched_configuration_name=(
                    fields.matched_configuration_name
                    or match.matched_configuration_name
                ),
                matched_configuration_id=(
                    fields.matched_configuration_id or match.matched_configuration_id
                ),
                matched_configuration_pattern=config_pattern,
                matched_configuration_reason=(
                    match.matched_configuration_reason
                    or "Explizites Dateinamensmuster am Mapping-Input."
                ),
                matched_payment_field=payment_field or match.matched_payment_field,
            )
        else:
            from dataclasses import replace as _dc_replace

            match = _dc_replace(
                match,
                matched_configuration_pattern=config_pattern,
            )

    if use_configuration_bridge and has_core and config_pattern:
        placeholders = build_configuration_placeholder_values(
            pattern=config_pattern,
            invoice_date=invoice_date,
            art=art_token,
            supplier=supplier,
            amount=amount,
            payment_field=payment_field
            or (match.matched_payment_field if match else None),
            document_direction=fields.document_direction,
            document_type=document_type,
            counterparty_name=fields.counterparty_name,
            payment_account=payment_account,
            extra_values=extra_values,
        )
        rendered = render_configuration_filename_pattern(
            config_pattern,
            placeholder_values=placeholders,
        )
        # Still compute canonical metadata for reports / demoted fallback visibility.
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
            review_required=True,
            extra_values=extra_values,
        )
        suggested = rendered.rendered_filename
        if suggested and source_name:
            if suggested.lower() == sanitize_suggested_filename(source_name):
                suggested = None
        missing_fields = tuple(
            dict.fromkeys(
                list(canonical.missing_fields)
                + list(rendered.missing_placeholders)
            )
        )
        source: FilenameSource = (
            FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE
            if rendered.incomplete
            else FILENAME_SOURCE_CONFIGURATION_PATTERN
        )
        if suggested is None:
            return SuggestedFilenameMappingResult(
                suggested_filename=None,
                filename_source=FILENAME_SOURCE_ORIGINAL_FALLBACK,
                naming_confidence="none",
                naming_reason=MSG_NAMING_REASON_MISSING,
                suggested_filename_fields=present,
                supplier=supplier,
                invoice_date=invoice_date or canonical.invoice_date,
                amount=amount_comma or amount or canonical.amount,
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
                missing_fields=missing_fields,
                filename_pattern=config_pattern,
                rendered_filename=None,
                placeholder_values=rendered.placeholder_values,
                missing_placeholders=rendered.missing_placeholders,
                amount_format=rendered.amount_format or AMOUNT_FORMAT_COMMA_2,
                **{
                    **_match_transparency(
                        match,
                        selected_payment_field=payment_field,
                        payment_account=payment_account,
                        absent_pattern_slots=rendered.missing_placeholders,
                        document_type=document_type,
                        supplier=supplier,
                        source_filename=source_name,
                        payment_field_candidates=fields.payment_field_candidates,
                    ),
                    "matched_configuration_pattern": config_pattern,
                },
                **candidate_meta,
            )
        reason = rendered.naming_reason
        if match and match.matched_configuration_reason:
            reason = f"{match.matched_configuration_reason} {reason}".strip()
        if fields.selected_art_reason and fields.art_ambiguity:
            reason = f"{reason} {fields.selected_art_reason}".strip()
        return SuggestedFilenameMappingResult(
            suggested_filename=suggested,
            filename_source=source,
            naming_confidence=rendered.naming_confidence,
            naming_reason=reason or MSG_NAMING_REASON_STRUCTURED,
            suggested_filename_fields=present
            + tuple(
                key
                for key in (
                    "filename_pattern",
                    "rendered_filename",
                    "matched_configuration_name",
                )
                if key not in present
            ),
            supplier=supplier,
            invoice_date=placeholders.get("invoice_date") or invoice_date,
            amount=amount_comma or amount,
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
            missing_fields=missing_fields,
            filename_pattern=config_pattern,
            rendered_filename=suggested,
            placeholder_values=rendered.placeholder_values,
            missing_placeholders=rendered.missing_placeholders,
            amount_format=rendered.amount_format or AMOUNT_FORMAT_COMMA_2,
            **{
                **_match_transparency(
                    match,
                    selected_payment_field=payment_field,
                    payment_account=payment_account,
                    absent_pattern_slots=rendered.missing_placeholders,
                    document_type=document_type,
                    supplier=supplier,
                    source_filename=source_name,
                    payment_field_candidates=fields.payment_field_candidates,
                ),
                "matched_configuration_pattern": config_pattern,
            },
            **candidate_meta,
        )

    # No configuration pattern → demoted canonical fallback.
    return _canonical_fallback(
        fields,
        review_required=review_required,
        extra_values=extra_values,
        match=match,
    )


__all__ = (
    "DEFAULT_FILENAME_PATTERN",
    "FORBIDDEN_SENSITIVE_FIELD_KEYS",
    "FILENAME_SOURCE_CANONICAL_FALLBACK",
    "FILENAME_SOURCE_CONFIGURATION_PATTERN",
    "FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE",
    "FILENAME_SOURCE_ORIGINAL_FALLBACK",
    "FILENAME_SOURCE_PLANNED_RESULT",
    "FILENAME_SOURCE_SUGGESTED_MAPPING",
    "FILENAME_TEMPLATE_VERSION",
    "MSG_NAMING_REASON_CANONICAL_FALLBACK",
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
