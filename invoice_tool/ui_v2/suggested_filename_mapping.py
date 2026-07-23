"""Track-B suggested filename mapping (Prompt 18/34).

Builds safe, non-final suggested PDF filenames from structured extraction /
planning fields. Never calls run_once, never writes/moves/archives files,
never invents supplier/date/amount tokens when fields are absent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

NamingConfidence = Literal["none", "low", "medium", "high"]
FilenameSource = Literal[
    "suggested_mapping",
    "planned_result",
    "original_fallback",
]

DEFAULT_FILENAME_PATTERN = "{invoice_date}_{supplier}_{amount}.pdf"

FILENAME_SOURCE_SUGGESTED_MAPPING: FilenameSource = "suggested_mapping"
FILENAME_SOURCE_PLANNED_RESULT: FilenameSource = "planned_result"
FILENAME_SOURCE_ORIGINAL_FALLBACK: FilenameSource = "original_fallback"

MSG_NAMING_REASON_STRUCTURED = (
    "Vorschlagsname aus lokalen Extraktionsfeldern (Lieferant/Datum/Betrag); "
    "Review bleibt erforderlich — nicht final."
)
MSG_NAMING_REASON_PARTIAL = (
    "Teilfelder für Vorschlagsname vorhanden; Review bleibt erforderlich."
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

_UNSAFE_COMPONENT_RE = re.compile(r"[^\w.\- ()\[\]]+", re.UNICODE)
_MULTI_UNDERSCORE_RE = re.compile(r"_+")
_TEMPLATE_TOKEN_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")


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


def sanitize_filename_component(value: str | None) -> str:
    """Sanitize one filename token — no path separators / unsafe chars."""

    raw = str(value or "").strip()
    if not raw:
        return ""
    # Collapse whitespace to underscore before stripping other junk.
    cleaned = re.sub(r"\s+", "_", raw)
    cleaned = _UNSAFE_COMPONENT_RE.sub("_", cleaned)
    cleaned = _MULTI_UNDERSCORE_RE.sub("_", cleaned).strip(" ._")
    return cleaned


def sanitize_suggested_filename(name: str | None) -> str | None:
    """Return a safe PDF basename or None."""

    if name is None:
        return None
    base = Path(str(name).strip()).name
    if not base or ".." in base or "/" in base or "\\" in base:
        return None
    stem = base[:-4] if base.lower().endswith(".pdf") else base
    safe_stem = sanitize_filename_component(stem)
    if not safe_stem:
        return None
    return f"{safe_stem}.pdf"


def _clean_optional(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _supplier_token(fields: SuggestedFilenameFields) -> str | None:
    return _clean_optional(fields.supplier) or _clean_optional(fields.vendor)


def _present_field_keys(fields: SuggestedFilenameFields) -> tuple[str, ...]:
    present: list[str] = []
    if _supplier_token(fields):
        present.append("supplier")
    if _clean_optional(fields.invoice_date):
        present.append("invoice_date")
    if _clean_optional(fields.amount):
        present.append("amount")
    if _clean_optional(fields.document_type):
        present.append("document_type")
    if _clean_optional(fields.payment_account):
        present.append("payment_account")
    return tuple(present)


def _confidence_from_fields(present: tuple[str, ...]) -> NamingConfidence:
    keys = set(present)
    if {"supplier", "invoice_date", "amount"} <= keys:
        return "high"
    if len(keys & {"supplier", "invoice_date", "amount"}) >= 2:
        return "medium"
    if keys & {"supplier", "invoice_date", "amount"}:
        return "low"
    return "none"


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
    """Render a suggested basename from structured fields only.

    Missing tokens are omitted (no synthetic fallback labels such as
    ``unbekannt``), so incomplete extractions still produce compact names
    when at least one useful field exists.
    """

    _assert_no_forbidden_keys(extra_values)
    values: dict[str, str] = {}
    supplier = _supplier_token(fields)
    if supplier:
        values["supplier"] = sanitize_filename_component(supplier)
        values["vendor"] = values["supplier"]
    if fields.invoice_date:
        values["invoice_date"] = sanitize_filename_component(fields.invoice_date)
    if fields.amount:
        values["amount"] = sanitize_filename_component(fields.amount)
    if fields.document_type:
        values["document_type"] = sanitize_filename_component(fields.document_type)
    if fields.payment_account:
        # Only short category tokens (paypal/card/transfer) — never IBAN/PAN.
        values["payment_account"] = sanitize_filename_component(fields.payment_account)
        values["payment_field"] = values["payment_account"]
    if extra_values:
        for key, raw in extra_values.items():
            lowered = str(key).strip().lower()
            if lowered in FORBIDDEN_SENSITIVE_FIELD_KEYS:
                continue
            token = sanitize_filename_component(str(raw) if raw is not None else "")
            if token:
                values[str(key)] = token

    if not any(values.get(k) for k in ("supplier", "invoice_date", "amount")):
        return None

    stem_template = pattern[:-4] if pattern.lower().endswith(".pdf") else pattern
    parts: list[str] = []
    last_end = 0
    for match in _TEMPLATE_TOKEN_RE.finditer(stem_template):
        literal = stem_template[last_end : match.start()]
        if literal and parts:
            # Keep separators only between present tokens.
            pass
        key = match.group(1)
        token = values.get(key) or ""
        if token:
            if parts and literal:
                # Use a single underscore between filled tokens.
                if not parts[-1].endswith("_") and not token.startswith("_"):
                    parts.append("_")
            elif parts and not literal:
                if not parts[-1].endswith("_") and not token.startswith("_"):
                    parts.append("_")
            parts.append(token)
        last_end = match.end()
    # If the template had no tokens matched into parts, fall back to ordered fields.
    if not parts:
        ordered = [
            values.get("invoice_date") or "",
            values.get("supplier") or "",
            values.get("amount") or "",
        ]
        parts = [p for p in ordered if p]
        rendered = "_".join(parts)
    else:
        rendered = "".join(parts)
    rendered = _MULTI_UNDERSCORE_RE.sub("_", rendered).strip(" ._")
    if not rendered:
        return None
    return sanitize_suggested_filename(f"{rendered}.pdf")


def map_suggested_filename(
    fields: SuggestedFilenameFields,
    *,
    pattern: str = DEFAULT_FILENAME_PATTERN,
    review_required: bool = True,
    extra_values: Mapping[str, Any] | None = None,
) -> SuggestedFilenameMappingResult:
    """Map structured fields to a Track-B suggested filename decision."""

    present = _present_field_keys(fields)
    confidence = fields.confidence or _confidence_from_fields(present)
    source_name = _clean_optional(fields.source_filename)
    supplier = _supplier_token(fields)
    invoice_date = _clean_optional(fields.invoice_date)
    amount = _clean_optional(fields.amount)
    document_type = _clean_optional(fields.document_type)
    payment_account = _clean_optional(fields.payment_account)

    suggested = render_suggested_filename(
        fields, pattern=pattern, extra_values=extra_values
    )
    if suggested and source_name:
        if suggested.lower() == sanitize_suggested_filename(source_name):
            suggested = None

    # Planned basename may already differ from the source (bridge / planner).
    if suggested is None:
        planned = sanitize_suggested_filename(fields.planned_basename)
        if planned and source_name:
            if planned.lower() != (sanitize_suggested_filename(source_name) or "").lower():
                suggested = planned
                return SuggestedFilenameMappingResult(
                    suggested_filename=suggested,
                    filename_source=FILENAME_SOURCE_PLANNED_RESULT,
                    naming_confidence=confidence if confidence != "none" else "low",
                    naming_reason=MSG_NAMING_REASON_PLANNED_BASENAME,
                    suggested_filename_fields=present,
                    supplier=supplier,
                    invoice_date=invoice_date,
                    amount=amount,
                    document_type=document_type,
                    payment_account=payment_account,
                    source_filename=source_name,
                    review_required=review_required,
                )

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
            review_required=review_required,
        )

    reason = (
        MSG_NAMING_REASON_STRUCTURED
        if confidence in {"medium", "high"}
        else MSG_NAMING_REASON_PARTIAL
    )
    return SuggestedFilenameMappingResult(
        suggested_filename=suggested,
        filename_source=FILENAME_SOURCE_SUGGESTED_MAPPING,
        naming_confidence=confidence if confidence != "none" else "low",
        naming_reason=reason,
        suggested_filename_fields=present,
        supplier=supplier,
        invoice_date=invoice_date,
        amount=amount,
        document_type=document_type,
        payment_account=payment_account,
        source_filename=source_name,
        review_required=review_required,
    )


__all__ = (
    "DEFAULT_FILENAME_PATTERN",
    "FORBIDDEN_SENSITIVE_FIELD_KEYS",
    "FILENAME_SOURCE_ORIGINAL_FALLBACK",
    "FILENAME_SOURCE_PLANNED_RESULT",
    "FILENAME_SOURCE_SUGGESTED_MAPPING",
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
