from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation

from invoice_tool.models import (
    ExtractedData,
    InvoiceFallbacks,
    NormalizedInvoice,
    SupplierCleaningRules,
)


class NormalizationError(RuntimeError):
    pass


DATE_PATTERNS = (
    "%y%m%d",
    "%d.%m.%Y",
    "%d.%m.%y",
    "%d-%m-%Y",
    "%d-%m-%y",
    "%Y-%m-%d",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%d-%b-%y",
    "%d-%B-%y",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
)

GERMAN_MONTHS = {
    "januar": "january",
    "februar": "february",
    "maerz": "march",
    "märz": "march",
    "marz": "march",   # OCR umlaut-loss: Tesseract reads "März" as "Marz"
    "april": "april",
    "mai": "may",
    "juni": "june",
    "juli": "july",
    "august": "august",
    "september": "september",
    "oktober": "october",
    "november": "november",
    "dezember": "december",
}

DATE_LABEL_PATTERNS = (
    r"rechnungsdatum",
    r"invoice date",
    r"issue date",
    r"belegdatum",
    r"datum",
)

# Explicit invoice-date labels that beat all other candidates
_HIGH_PRIORITY_DATE_LABELS = (
    r"rechnungsdatum",
    r"invoice\s*date",
    r"receipt\s*date",
    r"issue\s*date",
    r"belegdatum",
)

# Generic date labels used only as fallback (lower priority than heading detection)
_FALLBACK_DATE_LABELS = (r"\bdatum\b",)

# Lines whose dates must be ignored (renewal/cancellation/copyright/email-timestamps)
_NEGATIVE_DATE_LINE_LABELS = (
    r"verlang(?:er|rt)\s*(?:sich\s*)?am",
    r"naechste\s*(?:zahlung|abbuchung|rechnung|faelligkeit)",
    r"verlaengert\s*sich",
    r"\brenewal\b",
    r"refund\s*period",
    r"cancellation\s*period",
    r"kuendigungsfrist",
    r"copyright\s*\d{4}",
    r"\(c\)\s*\d{4}",
    # Email send-timestamps carry a time component — not an invoice date.
    r"\bum\s+\d{1,2}:\d{2}\b",          # German: "6. März 2026 um 06:12"
    r"\bat\s+\d{1,2}:\d{2}\b",           # English: "March 6, 2026 at 06:12"
    r"\d{1,2}:\d{2}\s*(?:uhr|am|pm)\b",  # "12:00 Uhr", "12:00 am"
)

AMOUNT_LABEL_PATTERNS = (
    r"gesamt",
    r"gesamtbetrag",
    r"rechnungsbetrag",
    r"betrag",
    r"summe",
    r"\btotal\b",
)

# Ordered tiers for amount extraction: lower index = higher priority.
# Each entry: (compiled_pattern, tier).
_AMOUNT_LABEL_TIERS: tuple[tuple[re.Pattern[str], int], ...] = tuple(
    (re.compile(p, re.IGNORECASE), t)
    for p, t in (
        (r"\bamount\s+due\b", 0),
        (r"\bzu\s+zahlend\b", 0),
        (r"\btotal\s+incl", 1),
        (r"\bgesamtbetrag\b", 1),
        (r"\brechnungsbetrag\b", 1),
        # plain "Gesamtsumme" (without "Netto") → tier 1; "Gesamtsumme (Netto)" caught later
        (r"\bgesamtsumme\b(?!.*\bnetto\b)", 1),
        # plain "Total" (not "Total excl…" / "Total ohne…") → tier 1
        (r"\btotal\b(?!\s*excl|\s*excluding|\s*without|\s*zzgl|\s*ohne|\s*netto)", 1),
        (r"\bsubtotal\b", 2),
        (r"\bzwischensumme\b", 2),
        (r"\bgesamtsumme\b", 2),   # catch-all for "Gesamtsumme (Netto)"
        (r"\bgesamt\b", 3),
        (r"\bsumme\b", 3),
        (r"\bbetrag\b", 3),
        (r"\btotal\b", 4),         # catch-all for "Total excl. tax" etc.
    )
)


def normalize_supplier_name(value: str) -> str:
    lowered = value.strip().lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)
    lowered = unicodedata.normalize("NFKD", lowered)
    lowered = lowered.encode("ascii", "ignore").decode("ascii")
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered).strip("-")
    if not lowered:
        raise NormalizationError("Rechnungssteller konnte nicht in einen gueltigen Dateinamen umgewandelt werden.")
    return lowered


def clean_supplier_text(value: str, rules: SupplierCleaningRules | None = None) -> str:
    cleaned = value.strip()
    if rules:
        for pattern in rules.remove_suffix_patterns:
            updated = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip(" ,;-")
            if updated and updated != cleaned:
                cleaned = updated
                break
        if rules.supplier_aliases:
            try:
                slug = normalize_supplier_name(cleaned)
            except NormalizationError:
                slug = ""
            if slug in rules.supplier_aliases:
                return rules.supplier_aliases[slug]
    return cleaned


def normalize_amount(value: str) -> str:
    cleaned = value.strip().lower()
    for token in ("eur", "usd", "gbp", "chf", "€", "$", "£"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.replace(" ", "")
    if not cleaned:
        raise NormalizationError("Betrag fehlt.")

    last_comma = cleaned.rfind(",")
    last_dot = cleaned.rfind(".")
    decimal_separator = "," if last_comma > last_dot else "."

    if decimal_separator == ",":
        normalized = cleaned.replace(".", "").replace(",", ".")
    else:
        normalized = cleaned.replace(",", "")

    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise NormalizationError(f"Betrag ist ungueltig: {value}") from exc
    if amount <= 0:
        raise NormalizationError(f"Betrag ist nicht positiv: {value}")

    return f"{amount:.2f}"


def normalize_invoice_date(value: str) -> str:
    candidate = value.strip()
    lowered = candidate.lower()
    for german, english in GERMAN_MONTHS.items():
        lowered = re.sub(rf"\b{re.escape(german)}\b", english, lowered)
    # Normalize ordinal dot in German dates: "24. March 2026" → "24 March 2026"
    lowered = re.sub(r"\b(\d{1,2})\.\s+([a-z])", r"\1 \2", lowered)
    candidate = re.sub(r"\s{2,}", " ", lowered).strip()
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(candidate, pattern).strftime("%y%m%d")
        except ValueError:
            continue
    raise NormalizationError(f"Rechnungsdatum ist ungueltig oder nicht nutzbar: {value}")


def normalize_required_fields(extracted: ExtractedData) -> NormalizedInvoice:
    if not extracted.invoice_date_raw:
        raise NormalizationError("Rechnungsdatum fehlt.")
    if not extracted.supplier_raw:
        raise NormalizationError("Rechnungssteller fehlt.")
    if not extracted.amount_raw:
        raise NormalizationError("Betrag fehlt.")
    return NormalizedInvoice(
        invoice_date=normalize_invoice_date(extracted.invoice_date_raw),
        supplier=normalize_supplier_name(extracted.supplier_raw),
        amount=normalize_amount(extracted.amount_raw),
    )


def normalize_invoice_with_fallbacks(
    extracted: ExtractedData,
    fallbacks: InvoiceFallbacks,
    supplier_cleaning_rules: SupplierCleaningRules | None = None,
) -> tuple[NormalizedInvoice, list[str]]:
    warnings: list[str] = []

    if extracted.invoice_date_raw:
        try:
            invoice_date = normalize_invoice_date(extracted.invoice_date_raw)
        except NormalizationError:
            invoice_date = fallbacks.invoice_date or "unknown-date"
            warnings.append("Rechnungsdatum unbrauchbar, Ersatzwert gesetzt.")
    else:
        invoice_date = fallbacks.invoice_date or "unknown-date"
        warnings.append("Rechnungsdatum fehlt, Ersatzwert gesetzt.")

    if extracted.supplier_raw:
        try:
            supplier = normalize_supplier_name(
                clean_supplier_text(extracted.supplier_raw, supplier_cleaning_rules)
            )
        except NormalizationError:
            supplier = fallbacks.supplier or "unknown-supplier"
            warnings.append("Rechnungssteller unbrauchbar, Ersatzwert gesetzt.")
    else:
        supplier = fallbacks.supplier or "unknown-supplier"
        warnings.append("Rechnungssteller fehlt, Ersatzwert gesetzt.")

    if extracted.amount_raw:
        try:
            amount = normalize_amount(extracted.amount_raw)
        except NormalizationError:
            amount = fallbacks.amount or "unknown-amount"
            warnings.append("Betrag unbrauchbar, Ersatzwert gesetzt.")
    else:
        amount = fallbacks.amount or "unknown-amount"
        warnings.append("Betrag fehlt, Ersatzwert gesetzt.")

    return NormalizedInvoice(invoice_date=invoice_date, supplier=supplier, amount=amount), warnings


def _normalize_line_for_label(line: str) -> str:
    """Lowercase + German-umlaut replacement for label pattern matching."""
    lowered = line.lower()
    for src, tgt in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        lowered = lowered.replace(src, tgt)
    return lowered


def _has_negative_date_label(normalized_line: str) -> bool:
    return any(re.search(p, normalized_line) for p in _NEGATIVE_DATE_LINE_LABELS)


def _is_invoice_heading_line(normalized_line: str) -> bool:
    """True for standalone invoice/receipt headings like 'Rechnung' (not Rechnungsnummer etc.)."""
    stripped = normalized_line.strip()
    if not re.search(r"\brechnung\b", stripped):
        return False
    # Exclude lines that are labels or compound terms
    if re.search(r"\b(?:nummer|nr\.?|datum|adresse|empfaenger|anschrift|betrag|steller)\b", stripped):
        return False
    return True


def _find_dates_in_line(line: str) -> list[str]:
    month_name_pattern = (
        r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
        r"nov(?:ember)?|dec(?:ember)?)\s+\d{1,2},\s+\d{4}\b"
    )
    day_month_name_pattern = (
        r"\b\d{1,2}[ -](?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|"
        r"januar|februar|maerz|märz|marz|april|mai|juni|juli|august|september|oktober|november|dezember)"
        r"[ -]\d{2,4}\b"
    )
    # Additional pattern for German ordinal style: "24. März 2026" (dot + space separator).
    # Includes "marz" for Tesseract OCR umlaut-loss ("März" → "Marz").
    german_ordinal_pattern = (
        r"\b\d{1,2}\.\s+(?:januar|februar|maerz|märz|marz|april|mai|juni|juli|august|"
        r"september|oktober|november|dezember|"
        r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+\d{4}\b"
    )
    return re.findall(
        rf"\b\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b"
        rf"|{month_name_pattern}|{day_month_name_pattern}|{german_ordinal_pattern}",
        line,
        flags=re.IGNORECASE,
    )


def parse_invoice_date_from_text(text: str) -> str | None:
    # Priority 1: explicit invoice-date labels (Rechnungsdatum, Invoice Date, …)
    explicit_matches: list[str] = []
    # Priority 2: date on or within _HEADING_PROXIMITY lines after an invoice heading
    heading_matches: list[str] = []
    # Priority 3: generic date label ("Datum:") — fallback only
    labeled_matches: list[str] = []
    # Priority 4: any other date in the document
    unlabeled_matches: list[str] = []

    # How many lines after a heading line still count as "heading context".
    # A value of 3 bridges a blank separator line that Tesseract often inserts
    # between "Rechnung" and the date on printed-email PDFs.
    _HEADING_PROXIMITY = 3

    lines = text.splitlines()
    heading_proximity_remaining = 0

    for line in lines:
        normalized = _normalize_line_for_label(line)

        # Skip lines with renewal / cancellation / copyright / timestamp labels
        if _has_negative_date_label(normalized):
            heading_proximity_remaining = 0
            continue

        dates = _find_dates_in_line(line)

        is_heading = _is_invoice_heading_line(normalized)

        if not dates:
            if is_heading:
                heading_proximity_remaining = _HEADING_PROXIMITY
            elif heading_proximity_remaining > 0:
                heading_proximity_remaining -= 1
            else:
                heading_proximity_remaining = 0
            continue

        if any(re.search(p, normalized) for p in _HIGH_PRIORITY_DATE_LABELS):
            explicit_matches.extend(dates)
        elif is_heading or heading_proximity_remaining > 0:
            heading_matches.extend(dates)
        elif any(re.search(p, normalized) for p in _FALLBACK_DATE_LABELS):
            labeled_matches.extend(dates)
        else:
            unlabeled_matches.extend(dates)

        if is_heading:
            heading_proximity_remaining = _HEADING_PROXIMITY
        elif heading_proximity_remaining > 0:
            heading_proximity_remaining -= 1
        else:
            heading_proximity_remaining = 0

    candidates = (
        list(dict.fromkeys(explicit_matches))
        or list(dict.fromkeys(heading_matches))
        or list(dict.fromkeys(labeled_matches))
        or list(dict.fromkeys(unlabeled_matches))
    )

    if not candidates:
        return None

    for candidate in candidates:
        try:
            return normalize_invoice_date(candidate)
        except NormalizationError:
            continue
    return None


def _get_amount_tier(line_lower: str) -> int | None:
    """Return the priority tier of a line's amount label (0 = highest), or None."""
    for pattern, tier in _AMOUNT_LABEL_TIERS:
        if pattern.search(line_lower):
            return tier
    return None


def parse_amount_from_text(text: str) -> str | None:
    """Extract the most relevant invoice amount using priority tiers.

    Labels and their values are often on separate lines in Tesseract output
    (table columns split across lines). A look-ahead / sequential-pairing
    strategy is used: pending label tiers are consumed in order as orphan
    amount lines are encountered below them.
    """
    _AMOUNT_RE = re.compile(r"\b\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})\b|\b\d+(?:\.\d{2})\b")

    lines = text.splitlines()
    tiered_candidates: list[tuple[int, str]] = []
    generic_candidates: list[str] = []
    pending_tiers: list[int] = []

    for line in lines:
        line_lower = line.lower()
        amounts = _AMOUNT_RE.findall(line)
        tier = _get_amount_tier(line_lower)

        if tier is not None:
            if amounts:
                # Label and amount on the same line — clear any stale pending state.
                pending_tiers.clear()
                for a in amounts:
                    tiered_candidates.append((tier, a))
            else:
                # Label without amount: queue for sequential pairing with
                # the next orphan amount line(s).
                pending_tiers.append(tier)
        elif amounts:
            if pending_tiers:
                # Consume the oldest pending label for the first amount found.
                consumed_tier = pending_tiers.pop(0)
                for a in amounts:
                    tiered_candidates.append((consumed_tier, a))
            else:
                generic_candidates.extend(amounts)
        # Empty lines do not reset pending_tiers — label blocks can span blank lines.

    if tiered_candidates:
        tiered_candidates.sort(key=lambda x: x[0])
        best_tier = tiered_candidates[0][0]
        for t, raw in tiered_candidates:
            if t != best_tier:
                break
            try:
                return normalize_amount(raw)
            except (NormalizationError, InvalidOperation):
                continue

    normalized: list[tuple[Decimal, str]] = []
    for candidate in generic_candidates:
        try:
            value = normalize_amount(candidate)
            normalized.append((Decimal(value), value))
        except (NormalizationError, InvalidOperation):
            continue

    if not normalized:
        return None

    normalized.sort(key=lambda item: item[0], reverse=True)
    return normalized[0][1]


# Single-word email header labels (matched after stripping all non-alpha characters).
_EMAIL_HEADER_BARE_WORDS = frozenset({
    "von", "an", "betreff", "from", "to", "subject", "date", "cc", "bcc",
})

# Patterns that disqualify a line as a supplier name (word-boundary checks).
_INVALID_SUPPLIER_PATTERNS = (
    r"\brechnung\b",
    r"\binvoice\b",
    r"\breceipt\b",
    r"\bdocument\b",
    r"\bpage\b",
    r"\bseite\b",
    r"\btax\b",
    r"\bnotice\b",
    r"\brechnungsadresse\b",
    r"\bbilling\s+address\b",
    r"\brechnungsanschrift\b",
)


def parse_supplier_from_text(text: str) -> str | None:
    # Legacy exact-match set kept for backward compatibility.
    _exact_skip = {"invoice", "rechnung", "receipt", "bill", "document", "page", "seite", "tax", "notice"}

    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if len(stripped) < 3:
            continue
        if re.search(r"\d", stripped):
            continue
        if any(label in lowered for label in DATE_LABEL_PATTERNS):
            continue
        if any(re.search(p, lowered) for p in AMOUNT_LABEL_PATTERNS):
            continue
        if lowered in _exact_skip:
            continue
        # Skip email header labels: "Von:", "An:", "Betreff:", "From:", "To:", …
        bare = re.sub(r"[^a-z]", "", lowered)
        if bare in _EMAIL_HEADER_BARE_WORDS:
            continue
        # Skip lines containing email addresses or web URLs.
        if "@" in stripped or re.search(r"\bwww\.", lowered):
            continue
        # Skip billing-address labels and other non-supplier line patterns.
        if any(re.search(p, lowered) for p in _INVALID_SUPPLIER_PATTERNS):
            continue
        try:
            return normalize_supplier_name(stripped)
        except NormalizationError:
            continue
    return None


def parse_card_endings_from_text(text: str) -> tuple[list[str], list[str]]:
    physical: set[str] = set()
    apple: set[str] = set()

    for match in re.finditer(r"(?:\*{2,}|x{2,}|ending|endet auf|last four|letzte(?:n)? vier)?[^0-9]{0,8}(\d{4})", text.lower()):
        digits = match.group(1)
        context = text[max(0, match.start() - 20) : match.end() + 20].lower()
        if "apple" in context or "pay" in context:
            apple.add(digits)
        else:
            physical.add(digits)

    return sorted(physical), sorted(apple)


def parse_invoice_number_from_text(text: str) -> str | None:
    patterns = (
        r"(?:rechnungsnummer|rechnungsnr|invoice number|invoice no|invoice #|bill number)[^a-z0-9]{0,10}([a-z0-9\-\/]+)",
        r"\b(?:inv|rn)[-_ ]?\d{3,}\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1) if match.lastindex else match.group(0)
            stripped = value.strip().strip(":").strip()
            if stripped:
                return stripped
    return None


def sanitize_document_name(value: str, *, max_words: int = 5) -> str:
    normalized = normalize_supplier_name(value)
    words = [word for word in normalized.split("-") if word]
    if not words:
        raise NormalizationError("Dokumentname konnte nicht bereinigt werden.")
    return "-".join(words[:max_words])
