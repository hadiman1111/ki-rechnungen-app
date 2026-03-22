from __future__ import annotations

from invoice_tool.models import FilenameSchema


class FilenameSchemaError(RuntimeError):
    pass


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
