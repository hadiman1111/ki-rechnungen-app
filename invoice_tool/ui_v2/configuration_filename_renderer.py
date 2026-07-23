"""Track-B configuration filename pattern renderer (Prompt 20/34).

Renders the active/matched configuration's filename pattern using extracted
placeholder values. Amounts use app/config syntax: decimal comma + two decimals.

Preview-only — no run_once, no file mutation, no productive writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Mapping

from invoice_tool.ui_v2.canonical_filename_template import (
    DOCUMENT_DIRECTION_AUSGANG,
    DOCUMENT_DIRECTION_EINGANG,
    sanitize_filename_component,
)

AMOUNT_FORMAT_COMMA_2 = "decimal_comma_2"

FilenameSource = Literal[
    "configuration_pattern",
    "configuration_pattern_incomplete",
    "canonical_fallback_no_configuration_pattern",
    "original_fallback",
]

FILENAME_SOURCE_CONFIGURATION_PATTERN: FilenameSource = "configuration_pattern"
FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE: FilenameSource = (
    "configuration_pattern_incomplete"
)
FILENAME_SOURCE_CANONICAL_FALLBACK: FilenameSource = (
    "canonical_fallback_no_configuration_pattern"
)
FILENAME_SOURCE_ORIGINAL_FALLBACK: FilenameSource = "original_fallback"

MISSING_PLACEHOLDER_PREFIX = "FEHLT_"

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
# Allow decimal comma in amounts; block path/control characters only.
_UNSAFE_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTI_UNDERSCORE_RE = re.compile(r"_{2,}")
_AMOUNT_SAFE_RE = re.compile(r"[^0-9,.\-]+")

_ART_FROM_DIRECTION: dict[str, str] = {
    DOCUMENT_DIRECTION_EINGANG: "er",
    DOCUMENT_DIRECTION_AUSGANG: "ar",
    "eingangsrechnung": "er",
    "ausgangsrechnung": "ar",
    "er": "er",
    "ar": "ar",
}


@dataclass(frozen=True)
class ConfigurationFilenameRenderResult:
    """Rendered configuration filename + honest placeholder metadata."""

    rendered_filename: str | None
    filename_pattern: str | None
    placeholder_values: tuple[tuple[str, str | None], ...] = field(default_factory=tuple)
    missing_placeholders: tuple[str, ...] = field(default_factory=tuple)
    filename_source: FilenameSource = FILENAME_SOURCE_ORIGINAL_FALLBACK
    amount_format: str | None = None
    naming_reason: str = ""
    naming_confidence: Literal["none", "low", "medium", "high"] = "none"
    review_required: bool = True
    incomplete: bool = False


def format_amount_comma(value: str | None) -> str | None:
    """Format an amount with decimal comma and exactly two decimals."""

    raw = str(value or "").strip()
    if not raw:
        return None
    cleaned = raw.lower()
    for token in ("eur", "usd", "gbp", "chf", "€", "$", "£"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.replace(" ", "")
    if not cleaned:
        return None
    last_comma = cleaned.rfind(",")
    last_dot = cleaned.rfind(".")
    if last_comma > last_dot:
        normalized = cleaned.replace(".", "").replace(",", ".")
    else:
        normalized = cleaned.replace(",", "")
    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None
    quantized = amount.quantize(Decimal("0.01"))
    return f"{quantized:.2f}".replace(".", ",")


def format_invoice_date_iso(value: str | None) -> str | None:
    """Normalize common invoice-date tokens to YYYY-MM-DD for config previews."""

    raw = str(value or "").strip()
    if not raw:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    if re.fullmatch(r"\d{8}", raw):
        try:
            return datetime.strptime(raw, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return None
    if re.fullmatch(r"\d{6}", raw):
        try:
            return datetime.strptime(raw, "%y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return sanitize_filename_component(raw) or None


def map_art_placeholder(
    *,
    art: str | None = None,
    document_direction: str | None = None,
    document_type: str | None = None,
) -> str | None:
    """Map document direction / explicit art into the configured ``art`` token."""

    explicit = str(art or "").strip().lower()
    if explicit in _ART_FROM_DIRECTION:
        return _ART_FROM_DIRECTION[explicit]
    if explicit in {"er", "ar", "ep", "ai", "private", "d"}:
        return explicit
    direction = str(document_direction or "").strip()
    mapped = _ART_FROM_DIRECTION.get(direction) or _ART_FROM_DIRECTION.get(
        direction.lower()
    )
    if mapped:
        return mapped
    doc_type = str(document_type or "").strip().lower()
    if doc_type in {"rechnung", "invoice", "facture", "storno", "credit_note"}:
        return "er"
    return None


def extract_pattern_placeholders(pattern: str | None) -> tuple[str, ...]:
    text = str(pattern or "").strip()
    if not text:
        return ()
    return tuple(dict.fromkeys(_PLACEHOLDER_RE.findall(text)))


def build_configuration_placeholder_values(
    *,
    pattern: str | None,
    invoice_date: str | None = None,
    art: str | None = None,
    supplier: str | None = None,
    amount: str | None = None,
    payment_field: str | None = None,
    document_direction: str | None = None,
    document_type: str | None = None,
    counterparty_name: str | None = None,
    payment_account: str | None = None,
    extra_values: Mapping[str, Any] | None = None,
) -> dict[str, str | None]:
    """Build placeholder values for a configuration filename pattern."""

    placeholders = extract_pattern_placeholders(pattern)
    amount_fmt = format_amount_comma(amount)
    date_fmt = format_invoice_date_iso(invoice_date)
    supplier_token = sanitize_configuration_filename_component(
        supplier or counterparty_name
    ) or None
    art_token = map_art_placeholder(
        art=art,
        document_direction=document_direction,
        document_type=document_type,
    )
    payment_token = sanitize_configuration_filename_component(
        payment_field or payment_account
    ) or None

    values: dict[str, str | None] = {
        "invoice_date": date_fmt,
        "art": art_token,
        "supplier": supplier_token,
        "amount": sanitize_amount_filename_token(amount_fmt) or None,
        "payment_field": payment_token,
        "document_type": sanitize_configuration_filename_component(document_type)
        or None,
        "currency": None,
        "invoice_number": None,
        "project": None,
    }
    if extra_values:
        for key, raw in extra_values.items():
            key_text = str(key).strip()
            if not key_text:
                continue
            if key_text == "amount":
                values[key_text] = sanitize_amount_filename_token(
                    format_amount_comma(str(raw) if raw is not None else None)
                ) or None
            elif key_text == "invoice_date":
                values[key_text] = format_invoice_date_iso(
                    str(raw) if raw is not None else None
                )
            else:
                values[key_text] = (
                    sanitize_configuration_filename_component(
                        str(raw) if raw is not None else None
                    )
                    or None
                )
    # Keep only placeholders that appear in the pattern (+ core keys for reporting).
    report_keys = list(placeholders) or [
        "invoice_date",
        "art",
        "supplier",
        "amount",
        "payment_field",
    ]
    return {key: values.get(key) for key in report_keys}


def sanitize_configuration_filename_component(value: str | None) -> str:
    """Sanitize a non-amount configuration filename token."""

    return sanitize_filename_component(value)


def sanitize_amount_filename_token(value: str | None) -> str:
    """Keep decimal-comma amounts intact for configuration filenames."""

    raw = str(value or "").strip()
    if not raw:
        return ""
    cleaned = _AMOUNT_SAFE_RE.sub("", raw)
    return cleaned


def _sanitize_rendered_filename(name: str) -> str | None:
    base = str(name or "").strip()
    if not base:
        return None
    has_pdf = base.lower().endswith(".pdf")
    stem = base[:-4] if has_pdf else base
    # Preserve FEHLT_* / literals / decimal commas; strip only unsafe path chars.
    cleaned = _UNSAFE_RE.sub("_", stem)
    cleaned = cleaned.replace(" ", "_")
    cleaned = _MULTI_UNDERSCORE_RE.sub("_", cleaned).strip(" ._")
    if not cleaned or ".." in cleaned or "/" in cleaned or "\\" in cleaned:
        return None
    return f"{cleaned}.pdf"


def render_configuration_filename_pattern(
    pattern: str | None,
    *,
    placeholder_values: Mapping[str, str | None] | None = None,
    values: Mapping[str, Any] | None = None,
) -> ConfigurationFilenameRenderResult:
    """Render a configured filename pattern without inventing missing tokens.

    Missing placeholders become ``FEHLT_<key>`` and are listed in
    ``missing_placeholders``. Literal segments such as ``_er_`` are preserved.
    """

    pattern_text = str(pattern or "").strip() or None
    if not pattern_text:
        return ConfigurationFilenameRenderResult(
            rendered_filename=None,
            filename_pattern=None,
            filename_source=FILENAME_SOURCE_ORIGINAL_FALLBACK,
            naming_reason=(
                "Kein Konfigurations-Dateinamensmuster verfügbar — "
                "kein Pattern-Render möglich."
            ),
            naming_confidence="none",
            review_required=True,
            incomplete=True,
        )

    merged: dict[str, str | None] = {}
    if values:
        for key, raw in values.items():
            key_text = str(key).strip()
            if not key_text:
                continue
            if key_text == "amount":
                merged[key_text] = sanitize_amount_filename_token(
                    format_amount_comma(str(raw) if raw is not None else None)
                ) or None
            elif key_text == "invoice_date":
                merged[key_text] = format_invoice_date_iso(
                    str(raw) if raw is not None else None
                )
            else:
                merged[key_text] = (
                    sanitize_configuration_filename_component(
                        str(raw) if raw is not None else None
                    )
                    or None
                )
    if placeholder_values:
        for key, raw in placeholder_values.items():
            key_text = str(key)
            if key_text == "amount" and raw is not None:
                merged[key_text] = sanitize_amount_filename_token(str(raw)) or None
            else:
                merged[key_text] = raw if raw is None else str(raw)

    placeholders = extract_pattern_placeholders(pattern_text)
    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = merged.get(key)
        text = str(value or "").strip()
        if text:
            return text
        missing.append(key)
        return f"{MISSING_PLACEHOLDER_PREFIX}{key}"

    rendered_raw = _PLACEHOLDER_RE.sub(_replace, pattern_text)
    if not rendered_raw.lower().endswith(".pdf"):
        rendered_raw = f"{rendered_raw}.pdf"
    rendered = _sanitize_rendered_filename(rendered_raw)
    missing_unique = tuple(dict.fromkeys(missing))
    incomplete = bool(missing_unique) or rendered is None
    amount_present = bool(str(merged.get("amount") or "").strip())
    report_values = tuple((key, merged.get(key)) for key in placeholders)

    if rendered is None:
        return ConfigurationFilenameRenderResult(
            rendered_filename=None,
            filename_pattern=pattern_text,
            placeholder_values=report_values,
            missing_placeholders=missing_unique or placeholders,
            filename_source=FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE,
            amount_format=AMOUNT_FORMAT_COMMA_2 if amount_present else None,
            naming_reason=(
                "Konfigurationsmuster konnte nicht sicher gerendert werden; "
                "Review bleibt erforderlich."
            ),
            naming_confidence="low",
            review_required=True,
            incomplete=True,
        )

    if incomplete:
        return ConfigurationFilenameRenderResult(
            rendered_filename=rendered,
            filename_pattern=pattern_text,
            placeholder_values=report_values,
            missing_placeholders=missing_unique,
            filename_source=FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE,
            amount_format=AMOUNT_FORMAT_COMMA_2 if amount_present else None,
            naming_reason=(
                "Konfigurations-Dateinamensmuster teilweise gerendert; "
                f"fehlende Platzhalter: {', '.join(missing_unique)}. "
                "Review bleibt erforderlich — nicht final."
            ),
            naming_confidence="low",
            review_required=True,
            incomplete=True,
        )

    return ConfigurationFilenameRenderResult(
        rendered_filename=rendered,
        filename_pattern=pattern_text,
        placeholder_values=report_values,
        missing_placeholders=(),
        filename_source=FILENAME_SOURCE_CONFIGURATION_PATTERN,
        amount_format=AMOUNT_FORMAT_COMMA_2,
        naming_reason=(
            "Dateiname aus aktivem Konfigurationsmuster gerendert; "
            "Review bleibt erforderlich — nicht final."
        ),
        naming_confidence="medium",
        review_required=True,
        incomplete=False,
    )


__all__ = (
    "AMOUNT_FORMAT_COMMA_2",
    "ConfigurationFilenameRenderResult",
    "FILENAME_SOURCE_CANONICAL_FALLBACK",
    "FILENAME_SOURCE_CONFIGURATION_PATTERN",
    "FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE",
    "FILENAME_SOURCE_ORIGINAL_FALLBACK",
    "MISSING_PLACEHOLDER_PREFIX",
    "build_configuration_placeholder_values",
    "extract_pattern_placeholders",
    "format_amount_comma",
    "format_invoice_date_iso",
    "map_art_placeholder",
    "render_configuration_filename_pattern",
)
