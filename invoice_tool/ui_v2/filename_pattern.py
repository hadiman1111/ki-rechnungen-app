"""UI-v2 filename pattern validation helpers (preview-only).

No productive writes, no run_once, no Track-A mutation.
"""

from __future__ import annotations

import re
from typing import Sequence

from invoice_tool.configuration_model import (
    FilenameComponent,
    FilenamePattern,
    normalize_filename_part,
    preview_filename,
)
from invoice_tool.scan_models import ScanModel

FILENAME_PATTERN_SAFE_EDIT_MARKER = "track_b_filename_pattern_builder_safe_editing_v1"
MSG_ER_ER_DUPLICATION = (
    "Dokumentart ergibt bereits ‚er‘. Der zusätzliche Text ‚er‘ würde den Dateinamen doppeln."
)
MSG_EMPTY_CUSTOM = "Eigener Text darf nicht leer sein."
MSG_UNSAFE_CUSTOM = "Eigener Text enthält ungültige Zeichen."
MSG_PDF_REQUIRED = "Die Dateiendung .pdf muss erhalten bleiben."
MSG_DUPLICATE_SEPARATOR = "Doppelte Trennzeichen vermeiden."
MSG_UNSUPPORTED_BLOCK = "Dieser Baustein ist für das aktuelle Erkennungsmodell nicht verfügbar."

_UNSAFE_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_ER_ER_RE = re.compile(r"(^|_)er_er(_|$)")

DOCUMENT_ART_KEYS = frozenset(
    {"document_type", "document_direction", "art", "belegart"}
)


def sanitize_custom_text(raw: str | None) -> str:
    text = str(raw or "").strip()
    text = _UNSAFE_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def custom_text_is_empty(raw: str | None) -> bool:
    return not sanitize_custom_text(raw)


def custom_text_has_unsafe_chars(raw: str | None) -> bool:
    text = str(raw or "")
    return bool(_UNSAFE_RE.search(text))


def filename_has_er_er_duplication(name: str | None) -> bool:
    return bool(_ER_ER_RE.search(str(name or "").casefold()))


def pattern_has_er_custom_with_document_art(pattern: FilenamePattern) -> bool:
    has_art = any(
        c.type == "feature" and c.key in DOCUMENT_ART_KEYS for c in pattern.components
    )
    has_er_custom = any(
        c.type == "system"
        and c.key == "custom_text"
        and normalize_filename_part(c.custom_text or "") == "er"
        for c in pattern.components
    )
    return has_art and has_er_custom


def validate_pattern_product_rules(
    pattern: FilenamePattern,
    scan_model: ScanModel,
    *,
    preview: str | None = None,
) -> list[str]:
    """Product validation warnings/errors for the filename builder."""

    issues: list[str] = []
    feature_keys = set(scan_model.feature_keys())
    for component in pattern.components:
        if component.type == "feature" and component.key not in feature_keys:
            issues.append(MSG_UNSUPPORTED_BLOCK + f" ({component.key})")
        if component.type == "system" and component.key == "custom_text":
            raw = component.custom_text or ""
            if custom_text_is_empty(raw):
                issues.append(MSG_EMPTY_CUSTOM)
            elif custom_text_has_unsafe_chars(raw):
                issues.append(MSG_UNSAFE_CUSTOM)
    try:
        rendered = preview if preview is not None else preview_filename(pattern, scan_model)
    except Exception:
        rendered = ""
    if rendered and not str(rendered).lower().endswith(".pdf"):
        issues.append(MSG_PDF_REQUIRED)
    if filename_has_er_er_duplication(rendered) or pattern_has_er_custom_with_document_art(
        pattern
    ):
        issues.append(MSG_ER_ER_DUPLICATION)
    sep = pattern.separator or "_"
    if sep and sep * 2 in (rendered or ""):
        issues.append(MSG_DUPLICATE_SEPARATOR)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for item in issues:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def ensure_pdf_extension(name: str | None) -> str:
    text = str(name or "").strip()
    if not text:
        return "dokument.pdf"
    if text.lower().endswith(".pdf"):
        return text
    return f"{text}.pdf"


def rebuild_planned_filename_from_fields(
    *,
    invoice_date: str,
    document_art: str,
    supplier: str,
    amount: str,
    payment: str,
    custom_text: str = "",
    separator: str = "_",
) -> str:
    """Rebuild a planned filename from structured field corrections."""

    parts: list[str] = []
    for raw in (
        invoice_date,
        document_art,
        supplier,
        amount,
        payment,
        sanitize_custom_text(custom_text),
    ):
        part = normalize_filename_part(raw) if raw else ""
        # Keep amount comma; normalize_filename_part lowercases which is OK for preview.
        if raw and "amount" not in parts:
            # Prefer display amount with comma when provided as amount-like.
            pass
        if part:
            parts.append(part)
    # Prefer original amount formatting (decimal comma) over normalized wipe.
    rebuilt: list[str] = []
    mapping = [
        invoice_date,
        document_art,
        supplier,
        amount,
        payment,
        sanitize_custom_text(custom_text),
    ]
    for value in mapping:
        text = str(value or "").strip()
        if not text:
            continue
        safe = _UNSAFE_RE.sub("", text).strip().replace(" ", "_")
        if safe:
            rebuilt.append(safe)
    stem = separator.join(rebuilt) if rebuilt else "dokument"
    stem = re.sub(rf"{re.escape(separator)}+", separator, stem).strip(separator)
    return ensure_pdf_extension(stem)


def validate_planned_filename_candidate(
    name: str | None,
    *,
    document_art: str | None = None,
    custom_text: str | None = None,
) -> list[str]:
    issues: list[str] = []
    text = str(name or "").strip()
    if not text:
        issues.append("Geplanter Dateiname fehlt.")
        return issues
    if not text.lower().endswith(".pdf"):
        issues.append(MSG_PDF_REQUIRED)
    if _UNSAFE_RE.search(text):
        issues.append(MSG_UNSAFE_CUSTOM)
    if filename_has_er_er_duplication(text):
        issues.append(MSG_ER_ER_DUPLICATION)
    art = normalize_filename_part(document_art or "")
    custom = normalize_filename_part(sanitize_custom_text(custom_text))
    if art == "er" and custom == "er":
        issues.append(MSG_ER_ER_DUPLICATION)
    if "/" in text or "\\" in text:
        issues.append("Dateiname darf keine Pfadtrenner enthalten.")
    # Deduplicate
    return list(dict.fromkeys(issues))


def add_custom_text_component(
    pattern: FilenamePattern,
    text: str,
) -> FilenamePattern:
    from invoice_tool.configuration_model import copy_filename_pattern

    cleaned = sanitize_custom_text(text)
    updated = copy_filename_pattern(pattern)
    without_ext = [
        c
        for c in updated.components
        if not (c.type == "system" and c.key == "extension")
    ]
    if cleaned:
        without_ext.append(
            FilenameComponent(
                type="system",
                key="custom_text",
                label="Eigener Text",
                custom_text=cleaned,
            )
        )
    without_ext.append(
        FilenameComponent(type="system", key="extension", label="Dateityp")
    )
    updated.components = without_ext
    return updated


def supported_block_catalog(scan_model: ScanModel) -> list[dict[str, str]]:
    """Blocks the runtime can populate or safely treat as empty."""

    from invoice_tool.configuration_model import available_filename_components

    items: list[dict[str, str]] = []
    for item in available_filename_components(scan_model):
        key = item.get("key") or ""
        if key == "extension":
            continue
        items.append(dict(item))
    # Ensure product labels for system blocks.
    for item in items:
        if item.get("key") == "custom_text":
            item["label"] = "Eigener Text"
    # Explicit separator option (UI-only add → uses pattern.separator).
    items.append({"type": "system", "key": "separator", "label": "Trennzeichen"})
    return items


def strip_er_custom_when_art_present(pattern: FilenamePattern) -> FilenamePattern:
    """Remove custom_text 'er' when document art block already implies er."""

    from invoice_tool.configuration_model import copy_filename_pattern

    if not pattern_has_er_custom_with_document_art(pattern):
        return pattern
    updated = copy_filename_pattern(pattern)
    updated.components = [
        c
        for c in updated.components
        if not (
            c.type == "system"
            and c.key == "custom_text"
            and normalize_filename_part(c.custom_text or "") == "er"
        )
    ]
    return updated
