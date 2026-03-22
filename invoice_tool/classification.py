from __future__ import annotations

from invoice_tool.models import ClassificationDecision, ExtractedData, ProcessingPreset
from invoice_tool.matching import normalize_for_matching


def classify_document_type(extracted: ExtractedData, preset: ProcessingPreset) -> ClassificationDecision:
    search_text = normalize_for_matching(
        " ".join(
            part
            for part in [
                extracted.raw_text,
                extracted.invoice_number_raw or "",
                extracted.supplier_raw or "",
                extracted.document_name_raw or "",
                extracted.payment_method_raw or "",
                " ".join(extracted.context_markers),
                " ".join(extracted.document_type_indicators),
            ]
            if part
        )
    )

    if any(
        normalize_for_matching(keyword) in search_text
        for keyword in preset.classification.document_keywords
    ):
        return ClassificationDecision(
            dokumenttyp="document",
            begruendung="Dokument-Indikator aus Preset-Regeln erkannt.",
        )

    if any(
        normalize_for_matching(keyword) in search_text
        for keyword in preset.classification.internal_invoice_keywords
    ):
        return ClassificationDecision(
            dokumenttyp="invoice",
            begruendung="Interner Beleg/Invoice-Sonderfall aus Preset-Regeln erkannt.",
        )

    if any(
        normalize_for_matching(keyword) in search_text
        for keyword in preset.classification.invoice_keywords
    ):
        return ClassificationDecision(
            dokumenttyp="invoice",
            begruendung="Invoice-Indikator aus Preset-Regeln erkannt.",
        )

    if extracted.invoice_number_raw:
        return ClassificationDecision(
            dokumenttyp="invoice",
            begruendung="Rechnungsnummer erkannt.",
        )

    return ClassificationDecision(
        dokumenttyp="document",
        begruendung="Kein belastbarer Invoice-Indikator gefunden.",
    )
