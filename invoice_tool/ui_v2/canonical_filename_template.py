"""Track-B canonical filename template (Prompt 19/34).

Builds non-final suggested PDF basenames in fixed component order:

    <YYMMDD>_<DOCUMENT_DIRECTION>_<BUSINESS_CATEGORY>_<COUNTERPARTY_NAME>_<AMOUNT>.pdf

Never invents private tenant defaults. Uncertain direction/category become
explicit markers (Unklare_Rechnungsart / Unklare_Zuordnung). Preview-only —
no run_once, no file mutation, no productive writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

NamingConfidence = Literal["none", "low", "medium", "high"]

FILENAME_TEMPLATE_VERSION = "track_b_canonical_v1"

DOCUMENT_DIRECTION_EINGANG = "Eingangsrechnung"
DOCUMENT_DIRECTION_AUSGANG = "Ausgangsrechnung"
DOCUMENT_DIRECTION_UNCLEAR = "Unklare_Rechnungsart"

BUSINESS_CATEGORY_ARCHITEKTUR = "Architektur"
BUSINESS_CATEGORY_INNENARCHITEKTUR = "Innenarchitektur"
BUSINESS_CATEGORY_EVENT = "Event_and_Production"
BUSINESS_CATEGORY_PRIVAT = "Privat"
BUSINESS_CATEGORY_UNCLEAR = "Unklare_Zuordnung"

AMOUNT_UNCLEAR = "Unklar"
DATE_UNCLEAR = "Unklar"
NAME_UNCLEAR = "Unklar"

CANONICAL_DOCUMENT_DIRECTIONS = frozenset(
    {
        DOCUMENT_DIRECTION_EINGANG,
        DOCUMENT_DIRECTION_AUSGANG,
        DOCUMENT_DIRECTION_UNCLEAR,
    }
)

CANONICAL_BUSINESS_CATEGORIES = frozenset(
    {
        BUSINESS_CATEGORY_ARCHITEKTUR,
        BUSINESS_CATEGORY_INNENARCHITEKTUR,
        BUSINESS_CATEGORY_EVENT,
        BUSINESS_CATEGORY_PRIVAT,
        BUSINESS_CATEGORY_UNCLEAR,
    }
)

# UI display labels (filename tokens stay underscore-safe).
BUSINESS_CATEGORY_DISPLAY = {
    BUSINESS_CATEGORY_ARCHITEKTUR: "Architektur",
    BUSINESS_CATEGORY_INNENARCHITEKTUR: "Innenarchitektur",
    BUSINESS_CATEGORY_EVENT: "Event and Production",
    BUSINESS_CATEGORY_PRIVAT: "Privat",
    BUSINESS_CATEGORY_UNCLEAR: "Unklare_Zuordnung",
}

_UNSAFE_COMPONENT_RE = re.compile(r"[^\w.\- ()\[\]]+", re.UNICODE)
_MULTI_UNDERSCORE_RE = re.compile(r"_+")

_CATEGORY_ALIASES: dict[str, str] = {
    "architektur": BUSINESS_CATEGORY_ARCHITEKTUR,
    "architecture": BUSINESS_CATEGORY_ARCHITEKTUR,
    "innenarchitektur": BUSINESS_CATEGORY_INNENARCHITEKTUR,
    "interior": BUSINESS_CATEGORY_INNENARCHITEKTUR,
    "interior_architecture": BUSINESS_CATEGORY_INNENARCHITEKTUR,
    "event_and_production": BUSINESS_CATEGORY_EVENT,
    "event and production": BUSINESS_CATEGORY_EVENT,
    "event production": BUSINESS_CATEGORY_EVENT,
    "event_production": BUSINESS_CATEGORY_EVENT,
    "event": BUSINESS_CATEGORY_EVENT,
    "production": BUSINESS_CATEGORY_EVENT,
    "ep": BUSINESS_CATEGORY_EVENT,
    "privat": BUSINESS_CATEGORY_PRIVAT,
    "private": BUSINESS_CATEGORY_PRIVAT,
    "unklare_zuordnung": BUSINESS_CATEGORY_UNCLEAR,
    "unclear": BUSINESS_CATEGORY_UNCLEAR,
    "unknown": BUSINESS_CATEGORY_UNCLEAR,
}

_DIRECTION_ALIASES: dict[str, str] = {
    "eingangsrechnung": DOCUMENT_DIRECTION_EINGANG,
    "eingang": DOCUMENT_DIRECTION_EINGANG,
    "incoming": DOCUMENT_DIRECTION_EINGANG,
    "incoming_invoice": DOCUMENT_DIRECTION_EINGANG,
    "in": DOCUMENT_DIRECTION_EINGANG,
    "ausgangsrechnung": DOCUMENT_DIRECTION_AUSGANG,
    "ausgang": DOCUMENT_DIRECTION_AUSGANG,
    "outgoing": DOCUMENT_DIRECTION_AUSGANG,
    "outgoing_invoice": DOCUMENT_DIRECTION_AUSGANG,
    "out": DOCUMENT_DIRECTION_AUSGANG,
    "unklare_rechnungsart": DOCUMENT_DIRECTION_UNCLEAR,
    "unclear": DOCUMENT_DIRECTION_UNCLEAR,
    "unknown": DOCUMENT_DIRECTION_UNCLEAR,
}

_INVOICE_LIKE_DOC_TYPES = frozenset(
    {
        "rechnung",
        "invoice",
        "facture",
        "storno",
        "credit_note",
        "creditnote",
        "eingangsrechnung",
        "ausgangsrechnung",
    }
)


@dataclass(frozen=True)
class CanonicalFilenameFields:
    """Structured inputs for the Track-B canonical filename template."""

    invoice_date: str | None = None
    document_direction: str | None = None
    business_category: str | None = None
    counterparty_name: str | None = None
    amount: str | None = None
    document_type: str | None = None
    confidence: NamingConfidence | None = None
    source_filename: str | None = None
    review_reason: str | None = None
    # Optional safe derivation hints — never private hardcodes inside this module.
    supplier: str | None = None
    vendor: str | None = None
    routing_category: str | None = None
    profile_category: str | None = None
    target_folder: str | None = None
    direction_hint: str | None = None
    own_issuer_hints: tuple[str, ...] = field(default_factory=tuple)
    recipient_hints: tuple[str, ...] = field(default_factory=tuple)
    raw_text_head: str | None = None


@dataclass(frozen=True)
class CanonicalFilenameResult:
    """Canonical naming decision for Track-B preview / review / manifest."""

    canonical_filename: str
    filename_template_version: str
    document_direction: str
    business_category: str
    counterparty_name: str
    invoice_date: str
    amount: str
    naming_confidence: NamingConfidence
    naming_reason: str
    missing_fields: tuple[str, ...] = field(default_factory=tuple)
    review_required: bool = True
    business_category_display: str = BUSINESS_CATEGORY_UNCLEAR


def sanitize_filename_component(value: str | None) -> str:
    """Sanitize one filename token — no path separators / unsafe chars."""

    raw = str(value or "").strip()
    if not raw:
        return ""
    cleaned = re.sub(r"\s+", "_", raw)
    cleaned = _UNSAFE_COMPONENT_RE.sub("_", cleaned)
    cleaned = _MULTI_UNDERSCORE_RE.sub("_", cleaned).strip(" ._")
    return cleaned


def sanitize_canonical_filename(name: str | None) -> str | None:
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


def _normalize_key(value: str | None) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("-", "_").replace("/", "_")
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_match(value: str | None) -> str:
    text = _normalize_key(value)
    return re.sub(r"[^a-z0-9]+", "", text)


def map_document_direction(
    *,
    document_direction: str | None = None,
    direction_hint: str | None = None,
    document_type: str | None = None,
    supplier: str | None = None,
    own_issuer_hints: tuple[str, ...] | list[str] | None = None,
    recipient_hints: tuple[str, ...] | list[str] | None = None,
    raw_text_head: str | None = None,
) -> tuple[str, str | None]:
    """Map to a canonical document direction.

    Returns ``(direction, missing_marker_or_None)``.
    Does **not** hardcode private org names — own/recipient hints must be passed in.
    """

    for candidate in (document_direction, direction_hint, document_type):
        key = _normalize_key(candidate)
        if key in _DIRECTION_ALIASES:
            mapped = _DIRECTION_ALIASES[key]
            if mapped == DOCUMENT_DIRECTION_UNCLEAR:
                return DOCUMENT_DIRECTION_UNCLEAR, "document_direction"
            return mapped, None

    supplier_norm = _normalize_match(supplier)
    own_hints = tuple(
        h for h in (own_issuer_hints or ()) if str(h or "").strip()
    )
    recipient = tuple(h for h in (recipient_hints or ()) if str(h or "").strip())
    head = _normalize_match(raw_text_head)

    issuer_is_own = False
    for hint in own_hints:
        hint_norm = _normalize_match(hint)
        if not hint_norm:
            continue
        if supplier_norm and (
            hint_norm in supplier_norm or supplier_norm in hint_norm
        ):
            issuer_is_own = True
            break
        if head and hint_norm in head[:800]:
            issuer_is_own = True
            break

    if issuer_is_own:
        return DOCUMENT_DIRECTION_AUSGANG, None

    doc_type = _normalize_key(document_type)
    invoice_like = doc_type in _INVOICE_LIKE_DOC_TYPES or doc_type.startswith(
        "rechnung"
    )
    recipient_matched = False
    if recipient and head:
        for hint in recipient:
            hint_norm = _normalize_match(hint)
            if hint_norm and hint_norm in head:
                recipient_matched = True
                break

    # External supplier + (recipient proof or invoice-like doc without own issuer).
    if supplier_norm and not issuer_is_own:
        if recipient_matched or invoice_like:
            return DOCUMENT_DIRECTION_EINGANG, None

    return DOCUMENT_DIRECTION_UNCLEAR, "document_direction"


def map_business_category(
    *,
    business_category: str | None = None,
    routing_category: str | None = None,
    profile_category: str | None = None,
    target_folder: str | None = None,
) -> tuple[str, str | None]:
    """Map to a canonical business category.

    Never defaults to Architektur when uncertain — uses Unklare_Zuordnung.
    """

    candidates = (
        business_category,
        routing_category,
        profile_category,
        Path(str(target_folder or "")).name if target_folder else None,
        target_folder,
    )
    for candidate in candidates:
        raw = _clean_optional(candidate)
        if not raw:
            continue
        key = _normalize_key(raw)
        if key in _CATEGORY_ALIASES:
            mapped = _CATEGORY_ALIASES[key]
            if mapped == BUSINESS_CATEGORY_UNCLEAR:
                return BUSINESS_CATEGORY_UNCLEAR, "business_category"
            return mapped, None
        # Folder path segments, e.g. .../Architektur/2026
        for part in re.split(r"[\\/_\s]+", raw):
            part_key = _normalize_key(part)
            if part_key in _CATEGORY_ALIASES:
                mapped = _CATEGORY_ALIASES[part_key]
                if mapped != BUSINESS_CATEGORY_UNCLEAR:
                    return mapped, None
    return BUSINESS_CATEGORY_UNCLEAR, "business_category"


def _counterparty_token(fields: CanonicalFilenameFields) -> tuple[str, bool]:
    """Return (token, was_fallback)."""

    for candidate in (
        fields.counterparty_name,
        fields.supplier,
        fields.vendor,
    ):
        cleaned = sanitize_filename_component(candidate)
        if cleaned:
            return cleaned, False
    source = _clean_optional(fields.source_filename)
    if source:
        stem = Path(source).stem
        cleaned = sanitize_filename_component(stem)
        if cleaned:
            return cleaned, True
    return NAME_UNCLEAR, True


def _date_token(value: str | None) -> tuple[str, bool]:
    cleaned = sanitize_filename_component(value)
    if cleaned:
        return cleaned, False
    return DATE_UNCLEAR, True


def _amount_token(value: str | None) -> tuple[str, bool]:
    cleaned = sanitize_filename_component(value)
    if cleaned:
        return cleaned, False
    return AMOUNT_UNCLEAR, True


def _confidence(
    *,
    missing: tuple[str, ...],
    present_core: int,
) -> NamingConfidence:
    if present_core >= 3 and not missing:
        return "high"
    if present_core >= 2 and len(missing) <= 1:
        return "medium"
    if present_core >= 1:
        return "low"
    return "none"


def _naming_reason(
    *,
    direction: str,
    category: str,
    missing: tuple[str, ...],
    review_reason: str | None,
) -> str:
    bits = [
        "Kanonisches Track-B-Dateinamensmuster "
        f"(v{FILENAME_TEMPLATE_VERSION}): "
        "Datum, Rechnungsart, Zuordnung, Name, Betrag."
    ]
    if direction == DOCUMENT_DIRECTION_UNCLEAR:
        bits.append("Rechnungsart unklar → Unklare_Rechnungsart.")
    if category == BUSINESS_CATEGORY_UNCLEAR:
        bits.append(
            "Zuordnung unklar → Unklare_Zuordnung "
            "(kein Blind-Default auf Architektur)."
        )
    if "invoice_date" in missing:
        bits.append("Datum unklar.")
    if "counterparty_name" in missing:
        bits.append("Name/Gegenpartei unklar oder Quellname-Fallback.")
    if "amount" in missing:
        bits.append("Betrag unklar.")
    bits.append("Benennung noch nicht final — Review bleibt erforderlich.")
    if review_reason:
        bits.append(f"Prüfgrund: {review_reason.strip()}")
    return " ".join(bits)


def build_canonical_filename(
    fields: CanonicalFilenameFields,
    *,
    review_required: bool = True,
    extra_values: Mapping[str, Any] | None = None,
) -> CanonicalFilenameResult:
    """Build a canonical suggested basename from structured fields."""

    _ = extra_values  # reserved; sensitive extras must not enter the template
    direction, direction_missing = map_document_direction(
        document_direction=fields.document_direction,
        direction_hint=fields.direction_hint,
        document_type=fields.document_type,
        supplier=fields.supplier or fields.counterparty_name or fields.vendor,
        own_issuer_hints=fields.own_issuer_hints,
        recipient_hints=fields.recipient_hints,
        raw_text_head=fields.raw_text_head,
    )
    category, category_missing = map_business_category(
        business_category=fields.business_category,
        routing_category=fields.routing_category,
        profile_category=fields.profile_category,
        target_folder=fields.target_folder,
    )
    date_token, date_missing = _date_token(fields.invoice_date)
    name_token, name_fallback = _counterparty_token(fields)
    amount_token, amount_missing = _amount_token(fields.amount)

    missing: list[str] = []
    if date_missing:
        missing.append("invoice_date")
    if direction_missing:
        missing.append("document_direction")
    if category_missing:
        missing.append("business_category")
    if name_fallback:
        missing.append("counterparty_name")
    if amount_missing:
        missing.append("amount")

    present_core = sum(
        1
        for flag in (not date_missing, not name_fallback, not amount_missing)
        if flag
    )
    confidence = fields.confidence or _confidence(
        missing=tuple(missing), present_core=present_core
    )

    stem = "_".join(
        [
            date_token,
            sanitize_filename_component(direction) or DOCUMENT_DIRECTION_UNCLEAR,
            sanitize_filename_component(category) or BUSINESS_CATEGORY_UNCLEAR,
            name_token,
            amount_token,
        ]
    )
    stem = _MULTI_UNDERSCORE_RE.sub("_", stem).strip(" ._")
    canonical = sanitize_canonical_filename(f"{stem}.pdf") or (
        f"{DATE_UNCLEAR}_{DOCUMENT_DIRECTION_UNCLEAR}_"
        f"{BUSINESS_CATEGORY_UNCLEAR}_{NAME_UNCLEAR}_{AMOUNT_UNCLEAR}.pdf"
    )

    # Force review when direction/category unclear or core fields missing.
    needs_review = bool(
        review_required
        or direction == DOCUMENT_DIRECTION_UNCLEAR
        or category == BUSINESS_CATEGORY_UNCLEAR
        or missing
    )

    return CanonicalFilenameResult(
        canonical_filename=canonical,
        filename_template_version=FILENAME_TEMPLATE_VERSION,
        document_direction=direction,
        business_category=category,
        counterparty_name=(
            _clean_optional(fields.counterparty_name)
            or _clean_optional(fields.supplier)
            or _clean_optional(fields.vendor)
            or (Path(fields.source_filename).stem if fields.source_filename else None)
            or NAME_UNCLEAR
        ),
        invoice_date=_clean_optional(fields.invoice_date) or DATE_UNCLEAR,
        amount=_clean_optional(fields.amount) or AMOUNT_UNCLEAR,
        naming_confidence=confidence if confidence != "none" else "low",
        naming_reason=_naming_reason(
            direction=direction,
            category=category,
            missing=tuple(missing),
            review_reason=fields.review_reason,
        ),
        missing_fields=tuple(missing),
        review_required=needs_review,
        business_category_display=BUSINESS_CATEGORY_DISPLAY.get(
            category, category
        ),
    )


__all__ = (
    "AMOUNT_UNCLEAR",
    "BUSINESS_CATEGORY_ARCHITEKTUR",
    "BUSINESS_CATEGORY_DISPLAY",
    "BUSINESS_CATEGORY_EVENT",
    "BUSINESS_CATEGORY_INNENARCHITEKTUR",
    "BUSINESS_CATEGORY_PRIVAT",
    "BUSINESS_CATEGORY_UNCLEAR",
    "CANONICAL_BUSINESS_CATEGORIES",
    "CANONICAL_DOCUMENT_DIRECTIONS",
    "CanonicalFilenameFields",
    "CanonicalFilenameResult",
    "DATE_UNCLEAR",
    "DOCUMENT_DIRECTION_AUSGANG",
    "DOCUMENT_DIRECTION_EINGANG",
    "DOCUMENT_DIRECTION_UNCLEAR",
    "FILENAME_TEMPLATE_VERSION",
    "NAME_UNCLEAR",
    "build_canonical_filename",
    "map_business_category",
    "map_document_direction",
    "sanitize_canonical_filename",
    "sanitize_filename_component",
)
