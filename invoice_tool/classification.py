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

# Hard document keywords: never overridden by invoice indicators.
_HARD_DOCUMENT_KEYWORD_MARKERS: tuple[str, ...] = (
    "bestellbestätigung",
    "bestellbestaetigung",
    "order confirmation",
    "bestellte artikel",
    "spendenbescheinigung",
    "donation confirmation",
    "donation receipt",
    "contribution statement",
    "tax certificate",
    "transfer proof",
    "payment confirmation",
    "bescheid",
    "steuerbescheid",
    "jahreskonto",
    "kanzlei-rechnungswesen",
    "ungeklärte posten",
    "ungeklaerte posten",
    "auswertung entspricht dem derzeitigen stand der buchführung",
    "auswertung entspricht dem derzeitigen stand der buchfuehrung",
)

# Soft/format phrases that must not dominate clear invoices.
_WEAK_DOCUMENT_OVERRIDE_MARKERS: tuple[str, ...] = (
    "lieferschein",
    "delivery note",
    "packing slip",
    "packing list",
    "zugferd",
    "xrechnung",
    "x-rechnung",
)

_FORMAT_AVAILABILITY_NOISE_PATTERNS: tuple[str, ...] = (
    r"\bzugferd\b(?:\s+\w+){0,6}\b(?:available|verfuegbar|verfügbar|on\s+request|auf\s+anfrage)\b",
    r"\bx[\s-]?rechnung\b(?:\s+\w+){0,6}\b(?:available|verfuegbar|verfügbar|on\s+request|auf\s+anfrage)\b",
    r"\brechnungs\s*lieferscheindatum\b",
    r"\brechnungs\s*/\s*lieferscheindatum\b",
)

_STRONG_INVOICE_TITLE = re.compile(
    r"(?<![a-z0-9])(?:rechnung|invoice)(?![a-z0-9])",
)
_STRONG_INVOICE_NUMBER = re.compile(
    r"(?:rechnung(?:s)?\s*(?:nr|nummer)|invoice\s*(?:no|number|nr))"
    r"\s*[:.]?\s*[a-z0-9][\w./-]{2,}",
)


def _keyword_matches(keyword: str, text: str) -> bool:
    """Match a normalized keyword on token boundaries (not as substring of a longer token)."""

    normalized = normalize_for_matching(keyword)
    if not normalized or not text:
        return False
    tokens = normalized.split()
    if not tokens:
        return False
    pattern = r"(?<![a-z0-9])" + r"\s+".join(re.escape(token) for token in tokens) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _invoice_keyword_matches(keyword: str, text: str) -> bool:
    """Match invoice keywords including German compounds (rechnung → rechnungsadresse)."""

    if _keyword_matches(keyword, text):
        return True
    normalized = normalize_for_matching(keyword)
    if not normalized or not text:
        return False
    tokens = normalized.split()
    # Single-token stems may head longer compounds (Rechnung/Rechnungsadresse).
    if len(tokens) == 1 and len(tokens[0]) >= 4:
        pattern = r"(?<![a-z0-9])" + re.escape(tokens[0]) + r"[a-z0-9]+"
        return re.search(pattern, text) is not None
    return False


def _strip_format_availability_noise(text: str) -> str:
    cleaned = text
    for pattern in _FORMAT_AVAILABILITY_NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def _count_strong_invoice_indicators(
    extracted: ExtractedData,
    search_text: str,
) -> tuple[int, list[str]]:
    """Count clear invoice-identity signals that should beat weak document phrases."""

    matched: list[str] = []
    if extracted.invoice_number_raw and str(extracted.invoice_number_raw).strip():
        matched.append("invoice-number-field")
    if _STRONG_INVOICE_NUMBER.search(search_text):
        matched.append("invoice-number-phrase")
    if _STRONG_INVOICE_TITLE.search(search_text):
        matched.append("invoice-title")
    if extracted.invoice_date_raw and str(extracted.invoice_date_raw).strip():
        matched.append("invoice-date")
    if re.search(
        r"\b(?:rechnungsanschrift|rechnungsadresse|billing\s+address|invoice\s+address)\b",
        search_text,
    ):
        matched.append("billing-address")
    if re.search(r"\b(?:mwst|mehrwertsteuer|umsatzsteuer|ust\.?|vat)\b", search_text):
        matched.append("vat")
    if extracted.amount_raw and str(extracted.amount_raw).strip():
        matched.append("amount")
    if re.search(
        r"\b(?:gesamtwert|gesamtbetrag|endbetrag|bruttobetrag|total\s+amount)\b",
        search_text,
    ):
        matched.append("total-amount")
    if re.search(
        r"\b(?:positionen|line\s*items|artikelliste?|leistungsposition)\b",
        search_text,
    ):
        matched.append("line-items")
    if re.search(
        r"\b(?:zahlungsbedingungen|payment\s+terms|zahlbar|zahlung\s+per)\b",
        search_text,
    ):
        matched.append("payment-terms")
    return len(matched), matched


def _is_hard_document_keyword(keyword: str) -> bool:
    normalized = normalize_for_matching(keyword)
    return any(
        normalize_for_matching(marker) == normalized
        or normalize_for_matching(marker) in normalized
        for marker in _HARD_DOCUMENT_KEYWORD_MARKERS
    )


def _is_weak_document_keyword(keyword: str) -> bool:
    normalized = normalize_for_matching(keyword)
    return any(
        normalize_for_matching(marker) == normalized
        or normalized == normalize_for_matching(marker)
        for marker in _WEAK_DOCUMENT_OVERRIDE_MARKERS
    )


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

    # Negative signals veto any positive scoring — but only as whole tokens.
    # "Prospekthüllen" must not veto; standalone "Lieferschein" may.
    for pattern in _INVOICE_LIKE_NEGATIVE_PATTERNS:
        if re.search(pattern, text):
            # Do not veto when strong invoice identity is already present.
            strong_count, _ = _count_strong_invoice_indicators(extracted, text)
            if strong_count >= 3:
                break
            return 0, []

    matched: list[str] = []
    for pattern, label in _INVOICE_LIKE_POSITIVE_PATTERNS:
        if re.search(pattern, text):
            matched.append(label)

    # Extra indicators from preset config
    for indicator in extra_indicators:
        if _keyword_matches(indicator, text):
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
    # Format-availability / compound date labels are not document-type evidence.
    document_search_text = _strip_format_availability_noise(search_text)

    strong_count, strong_labels = _count_strong_invoice_indicators(extracted, search_text)
    document_hits = [
        keyword
        for keyword in preset.classification.document_keywords
        if _keyword_matches(keyword, document_search_text)
    ]

    if document_hits:
        hard_hits = [kw for kw in document_hits if _is_hard_document_keyword(kw)]
        weak_only = bool(document_hits) and not hard_hits and all(
            _is_weak_document_keyword(kw) for kw in document_hits
        )
        # Strong invoice identity beats weak document/format/delivery-note phrases.
        if strong_count >= 3 and (weak_only or (not hard_hits and strong_count >= 4)):
            return ClassificationDecision(
                dokumenttyp="invoice",
                begruendung=(
                    "Starke Rechnungsindikatoren überschreiben schwache "
                    f"Dokument-/Formatphrasen ({', '.join(strong_labels[:4])})."
                ),
            )
        if hard_hits or not (strong_count >= 3 and weak_only):
            # Keep intentional non-invoice documents (order confirmation, DATEV, …).
            if hard_hits or strong_count < 3:
                return ClassificationDecision(
                    dokumenttyp="document",
                    begruendung="Dokument-Indikator aus Preset-Regeln erkannt.",
                )
            # Soft document keyword + enough invoice identity → invoice.
            return ClassificationDecision(
                dokumenttyp="invoice",
                begruendung=(
                    "Starke Rechnungsindikatoren überschreiben Dokument-Keyword "
                    f"({', '.join(strong_labels[:4])})."
                ),
            )

    if any(
        _invoice_keyword_matches(keyword, search_text)
        for keyword in preset.classification.internal_invoice_keywords
    ):
        return ClassificationDecision(
            dokumenttyp="invoice",
            begruendung="Interner Beleg/Invoice-Sonderfall aus Preset-Regeln erkannt.",
        )

    if any(
        _invoice_keyword_matches(keyword, search_text)
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
