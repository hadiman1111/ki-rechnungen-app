from __future__ import annotations

import re

from invoice_tool.models import ClassificationDecision, ExtractedData, ProcessingPreset
from invoice_tool.matching import normalize_for_matching

# Positive accounting signals: (regex_pattern, label).
# Each matching pattern adds 1 to the invoice-likeness score.
_INVOICE_LIKE_POSITIVE_PATTERNS: list[tuple[str, str]] = [
    (r"\b(?:mwst|mehrwertsteuer|umsatzsteuer|ust\.?|vat)\b", "vat-signal"),
    (r"\b(?:nettobetrag|nettosumme|netto(?!\w)|net\s+amount|excl\.?\s*(?:tax|mwst))\b", "net-amount"),
    (r"\b(?:bruttobetrag|bruttosumme|brutto(?!\w)|gross\s+amount|incl\.?\s*(?:tax|mwst))\b", "gross-amount"),
    (r"\b(?:rechnungsanschrift|rechnungsadresse|billing\s+address|lieferanschrift|invoice\s+address)\b", "billing-address"),
    (r"\b(?:bestellnummer|auftragsnummer|belegn(?:ummer)?r?\.?|receipt\s*(?:number|nr)|order\s*(?:number|no)|transaktionsnr?)\b", "doc-number"),
    (r"\b(?:positionen|line\s*items|artikelliste?|leistungsposition)\b", "line-items"),
    (r"\b(?:zwischensumme|subtotal|teilbetrag)\b", "subtotal"),
    (r"\b(?:zahlungsart|zahlungsmethode|payment\s*(?:method|information)|zahlungsanweisung|bezahlmethode)\b", "payment-method-info"),
    (r"\b(?:sepa|lastschrift|direct\s*debit|bankeinzug|kontoverbindung)\b", "bank-signal"),
    (r"\b(?:kreditkarte|kartenzahlung|card\s*(?:ending|number)|endet\s*auf)\b", "card-signal"),
    (r"\b(?:abonnement|monatsrechnung|subscription|monthly\s*(?:invoice|bill))\b", "subscription-billing"),
    (r"\b(?:kontoauszug|kreditkartenabrechnung|card\s*statement|account\s*statement|monatsabrechnung)\b", "statement"),
]

# If any of these patterns match, the document is NOT invoice-like
_INVOICE_LIKE_NEGATIVE_PATTERNS: list[str] = [
    r"\b(?:lieferschein|packing\s*(?:slip|list))\b",
    r"\b(?:werbung|newsletter|katalog|prospekt|advertisement)\b",
]


def _score_invoice_likeness(
    extracted: ExtractedData,
    extra_indicators: tuple[str, ...],
) -> tuple[int, list[str]]:
    """Return (score, matched_signal_labels). Score counts distinct positive indicators."""
    text = normalize_for_matching(
        " ".join(
            part
            for part in [
                extracted.raw_text,
                extracted.payment_method_raw or "",
                " ".join(extracted.context_markers),
                " ".join(extracted.document_type_indicators),
            ]
            if part
        )
    )

    # Negative signals veto any positive scoring
    for pattern in _INVOICE_LIKE_NEGATIVE_PATTERNS:
        if re.search(pattern, text):
            return 0, []

    matched: list[str] = []
    for pattern, label in _INVOICE_LIKE_POSITIVE_PATTERNS:
        if re.search(pattern, text):
            matched.append(label)

    # Extra indicators from preset config
    for indicator in extra_indicators:
        normalized_indicator = normalize_for_matching(indicator)
        if normalized_indicator and normalized_indicator in text:
            matched.append(f"config:{indicator}")

    # Bonus: extracted card/apple-pay endings signal a payment document
    if extracted.card_endings:
        matched.append("card-endings-extracted")
    if extracted.apple_pay_endings:
        matched.append("apple-pay-extracted")

    # Guard: require at least one financial or document-identity signal
    financial_labels = {"vat-signal", "net-amount", "gross-amount", "bank-signal", "card-signal", "statement", "subscription-billing", "card-endings-extracted", "apple-pay-extracted"}
    doc_labels = {"doc-number", "billing-address", "payment-method-info"}
    if not any(lbl in financial_labels or lbl in doc_labels for lbl in matched):
        return 0, matched

    return len(matched), matched


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

    # Fallback: score accounting-indicator signals for documents without invoice keywords
    score, matched_signals = _score_invoice_likeness(
        extracted,
        preset.classification.invoice_like_indicators,
    )
    threshold = preset.classification.invoice_like_threshold
    if score >= threshold:
        signal_summary = ", ".join(matched_signals[:4])
        return ClassificationDecision(
            dokumenttyp="invoice",
            begruendung=f"Invoice-Likeness-Score {score}/{threshold} erkannt ({signal_summary}).",
        )

    return ClassificationDecision(
        dokumenttyp="document",
        begruendung="Kein belastbarer Invoice-Indikator gefunden.",
    )
