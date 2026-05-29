from __future__ import annotations

import re
from dataclasses import dataclass, field

from invoice_tool.models import FilenameSchema


class FilenameSchemaError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Document profile filename renderer
# ---------------------------------------------------------------------------

_PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Standard placeholder keys supplied by the runtime caller.
_ALLOWED_PLACEHOLDER_SOURCES: frozenset[str] = frozenset(
    {"date", "supplier", "amount", "type_literal"}
)


@dataclass
class DocumentFilenameResult:
    """Result of render_document_filename().

    Callers must inspect the metadata fields to decide whether to use
    the target_folder or fall back to the fallback_folder.
    """

    filename: str
    """Rendered filename stem (no .pdf extension). Never empty."""

    missing_placeholders: list[str] = field(default_factory=list)
    """Known placeholder keys that had no value and no fallback entry."""

    fallback_placeholder_used: list[str] = field(default_factory=list)
    """Placeholder keys resolved via fallback_values instead of primary values."""

    unknown_placeholders: list[str] = field(default_factory=list)
    """Placeholder keys not in the allowed sources and not in fallback_values."""


def render_document_filename(
    template: str,
    values: dict[str, str],
    *,
    fallback_values: dict[str, str] | None = None,
) -> DocumentFilenameResult:
    """Render a document filename stem from a {placeholder} template.

    Allowed placeholder sources in *values*: date, supplier, amount, type_literal.
    Additional fallback entries may be supplied via *fallback_values*.

    Resolution order for each {key}:
    1. values[key] is non-empty  → use it; nothing to report.
    2. fallback_values[key] is non-empty → use it; append key to
       fallback_placeholder_used.
    3. key is in _ALLOWED_PLACEHOLDER_SOURCES but no value/fallback →
       substitute "unbekannt"; append key to missing_placeholders.
    4. key is not in allowed sources and not in fallback_values →
       substitute "unbekannt"; append key to unknown_placeholders.

    NOTE: The .pdf extension is NOT added here.  The caller
    (_process_document_with_profile) appends it before writing the file.

    Sanitization applied to the rendered string:
    - Unsafe filesystem characters replaced with "_".
    - Repeated underscores collapsed to one.
    - Leading/trailing underscores stripped.
    - Empty result → safe fallback "dokument-unbekannt".
    """
    _fb = fallback_values or {}

    missing_placeholders: list[str] = []
    fallback_placeholder_used: list[str] = []
    unknown_placeholders: list[str] = []

    def _resolve(match: re.Match) -> str:  # type: ignore[type-arg]
        key = match.group(1)
        val = values.get(key, "")
        if val:
            return val
        fb_val = _fb.get(key, "")
        if fb_val:
            fallback_placeholder_used.append(key)
            return fb_val
        if key in _ALLOWED_PLACEHOLDER_SOURCES:
            missing_placeholders.append(key)
        else:
            unknown_placeholders.append(key)
        return "unbekannt"

    rendered = _PLACEHOLDER_PATTERN.sub(_resolve, template)

    rendered = _UNSAFE_CHARS.sub("_", rendered)
    rendered = re.sub(r"_+", "_", rendered)
    rendered = rendered.strip("_")

    if not rendered:
        rendered = "dokument-unbekannt"

    return DocumentFilenameResult(
        filename=rendered,
        missing_placeholders=missing_placeholders,
        fallback_placeholder_used=fallback_placeholder_used,
        unknown_placeholders=unknown_placeholders,
    )


def build_filename(schema: FilenameSchema, values: dict[str, str]) -> str:
    parts: list[str] = []
    supplier_index: int | None = None

    for field in schema.felder:
        if not field.aktiv:
            continue
        if field.typ == "literal":
            if not field.wert:
                raise FilenameSchemaError("Literal-Feld im Dateinamenschema hat keinen Wert.")
            parts.append(field.wert.lower())
        elif field.typ in {"wert", "datum"}:
            if not field.quelle:
                raise FilenameSchemaError("Schemafeld ohne Quelle gefunden.")
            value = values.get(field.quelle, "")
            if not value:
                raise FilenameSchemaError(f"Schemaquelle '{field.quelle}' konnte nicht aufgebaut werden.")
            parts.append(value.lower())
            if field.quelle == "supplier":
                supplier_index = len(parts) - 1
        else:
            raise FilenameSchemaError(f"Nicht unterstuetzter Feldtyp im Schema: {field.typ}")

    extension = schema.erweiterung.lower()
    filename = schema.separator.join(parts) + extension
    if len(filename) <= schema.max_laenge:
        return filename

    if supplier_index is None:
        raise FilenameSchemaError("Dateiname ueberschreitet die Maximalgrenze und enthaelt kein kuerzbares supplier-Feld.")

    overflow = len(filename) - schema.max_laenge
    truncated_supplier = parts[supplier_index]
    if len(truncated_supplier) <= overflow:
        raise FilenameSchemaError(
            "Dateiname kann nicht auf die konfigurierte Maximalgrenze gekuerzt werden, ohne Pflichtfelder zu verletzen."
        )

    parts[supplier_index] = truncated_supplier[: len(truncated_supplier) - overflow]
    parts[supplier_index] = parts[supplier_index].rstrip("-_")
    if not parts[supplier_index]:
        raise FilenameSchemaError("Supplier-Feld waere nach Kuerzung leer.")

    final_name = schema.separator.join(parts) + extension
    if len(final_name) > schema.max_laenge:
        raise FilenameSchemaError("Dateiname bleibt trotz Supplier-Kuerzung zu lang.")
    return final_name
