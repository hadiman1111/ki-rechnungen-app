"""Track-B local extraction → suggested-filename bridge (Prompt 18/34).

Read-only PDF text extraction for copied sandbox inputs only.
Uses local text layer (PyMuPDF) + normalization helpers + Track-B supplier
heuristics. Does **not** call OpenAI/OCR, does **not** call ``run_once``,
does **not** move/rename/archive/write originals or productive outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

from invoice_tool.normalization import (
    parse_amount_from_text,
    parse_invoice_date_from_text,
)
from invoice_tool.ui_v2.core_dry_run_contract import (
    is_explicit_copied_sandbox_test_path,
    path_has_forbidden_productive_marker,
)
from invoice_tool.ui_v2.processing_state import ProcessingPlannedDestination
from invoice_tool.ui_v2.suggested_filename_mapping import (
    SuggestedFilenameFields,
    map_suggested_filename,
)

MSG_EXTRACTION_LOCAL_TEXT = "local_pdf_text_layer"
MSG_EXTRACTION_SKIPPED_UNSAFE_PATH = "extraction_skipped_unsafe_path"
MSG_EXTRACTION_NO_TEXT = "extraction_no_readable_text"
MSG_AI_OCR_NOT_USED = "ai_ocr_not_used"

_LEGAL_FORM_RE = re.compile(
    r"\b(?:GmbH|AG|UG|KG|Ltd|Inc|SAS|SARL|S\.A\.|e\.K\.)\b",
    re.IGNORECASE,
)
_SHOP_DOMAIN_RE = re.compile(
    r"\b[A-Za-z0-9][A-Za-z0-9\-]*\.(?:de|com|fr|eu)\b",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(
    r"^(?:stornorechnung|rechnung|facture|invoice|credit\s*note)\b",
    re.IGNORECASE,
)
_SKIP_SUPPLIER_LINE_RE = re.compile(
    r"^(?:"
    r"seite|page|rechnung|stornorechnung|facture|invoice|adresse|"
    r"bill|bankverbindung|aus dem ausland|geschäftsführung|"
    r"registergericht|so erreichen sie uns|internet|e-?mail|"
    r"telefon|steuer-?nr|ustid|wee+e|powered by|adresse de|"
    r"numéro|date de|réf\.|produit|total|moyen de paiement|"
    r"transporteur|pack duo|détail"
    r")\b",
    re.IGNORECASE,
)
_DATE_ONLY_RE = re.compile(
    r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$|^\d{4}-\d{2}-\d{2}$"
)
_PAYMENT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bpaypal\b", re.I), "paypal"),
    (re.compile(r"\bkreditkarte|credit\s*card|carte\s*bancaire\b", re.I), "card"),
    (re.compile(r"\büberweisung|bank\s*transfer|virement\b", re.I), "transfer"),
    (re.compile(r"\bapple\s*pay\b", re.I), "apple_pay"),
)
_DOC_TYPE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bstornorechnung|credit\s*note|avoir\b", re.I), "storno"),
    (re.compile(r"\brechnung|invoice|facture\b", re.I), "rechnung"),
)


@dataclass(frozen=True)
class LocalExtractionResult:
    """Local naming-oriented extraction for one sandbox PDF."""

    source_filename: str
    source_path: str
    supplier: str | None = None
    invoice_date: str | None = None
    amount: str | None = None
    document_type: str | None = None
    payment_account: str | None = None
    text_chars: int = 0
    extraction_method: str = MSG_EXTRACTION_LOCAL_TEXT
    warnings: tuple[str, ...] = ()
    ok: bool = False
    # First text chunk only — for safe direction heuristics (no private hardcodes).
    raw_text_head: str | None = None


def _norm_path(path: Path | str | None) -> Path | None:
    raw = str(path or "").strip()
    if not raw:
        return None
    try:
        return Path(raw).expanduser().resolve()
    except OSError:
        return Path(raw).expanduser()


def assert_safe_sandbox_extraction_root(input_root: Path | str | None) -> str | None:
    """Return an error message when extraction root is not a copied sandbox path."""

    root = _norm_path(input_root)
    if root is None or not root.is_dir():
        return MSG_EXTRACTION_SKIPPED_UNSAFE_PATH
    text = str(root)
    if path_has_forbidden_productive_marker(text):
        return MSG_EXTRACTION_SKIPPED_UNSAFE_PATH
    if not is_explicit_copied_sandbox_test_path(text):
        return MSG_EXTRACTION_SKIPPED_UNSAFE_PATH
    return None


def read_pdf_text_layer(path: Path, *, max_pages: int = 2) -> str:
    """Read embedded PDF text only — no OCR, no network, no mutation."""

    import fitz  # lazy: keeps import light when unused

    chunks: list[str] = []
    with fitz.open(path) as document:
        limit = min(max_pages, len(document))
        for index in range(limit):
            chunks.append(document.load_page(index).get_text("text"))
    return "\n".join(chunks)


def _guess_document_type(text: str) -> str | None:
    for pattern, label in _DOC_TYPE_PATTERNS:
        if pattern.search(text):
            return label
    return None


def _guess_payment_account(text: str) -> str | None:
    for pattern, label in _PAYMENT_PATTERNS:
        if pattern.search(text):
            return label
    return None


def guess_supplier_from_local_text(text: str) -> str | None:
    """Track-B supplier heuristic for readable PDF text (no AI)."""

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None

    # Prefer issuer lines with legal form.
    for line in lines[:40]:
        if _SKIP_SUPPLIER_LINE_RE.search(line):
            continue
        if _DATE_ONLY_RE.match(line):
            continue
        if _LEGAL_FORM_RE.search(line):
            return line.split(" - ")[0].split(",")[0].strip()

    # Footer / imprint company lines (e.g. LUMITOP - address).
    for line in reversed(lines[-12:]):
        if " - " in line and not line.lower().startswith("powered"):
            left = line.split(" - ", 1)[0].strip()
            if left and not _SKIP_SUPPLIER_LINE_RE.search(left) and not _DATE_ONLY_RE.match(left):
                if len(left) >= 3 and not re.search(r"\d{5}", left):
                    return left

    # Shop domains near the top.
    for line in lines[:20]:
        match = _SHOP_DOMAIN_RE.search(line)
        if match:
            return match.group(0)

    # After an invoice heading, take the next non-skip company-ish line.
    for index, line in enumerate(lines[:20]):
        if not _HEADING_RE.search(line):
            continue
        for nxt in lines[index + 1 : index + 4]:
            if _SKIP_SUPPLIER_LINE_RE.search(nxt) or _DATE_ONLY_RE.match(nxt):
                continue
            if re.search(r"\d{5}", nxt):
                continue
            candidate = nxt.split(",")[0].strip()
            if len(candidate) >= 3:
                return candidate
    return None


def extract_local_fields_from_pdf(path: Path | str) -> LocalExtractionResult:
    """Extract naming fields from one PDF via local text layer only."""

    pdf_path = Path(path)
    warnings = [MSG_AI_OCR_NOT_USED]
    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        return LocalExtractionResult(
            source_filename=pdf_path.name,
            source_path=str(pdf_path),
            warnings=tuple(warnings + ["not_a_pdf"]),
            ok=False,
        )
    try:
        text = read_pdf_text_layer(pdf_path)
    except Exception as exc:  # noqa: BLE001 — bridge must fail closed
        return LocalExtractionResult(
            source_filename=pdf_path.name,
            source_path=str(pdf_path),
            warnings=tuple(warnings + [f"pdf_read_failed:{type(exc).__name__}"]),
            ok=False,
        )
    cleaned = text.strip()
    if not cleaned:
        return LocalExtractionResult(
            source_filename=pdf_path.name,
            source_path=str(pdf_path),
            text_chars=0,
            warnings=tuple(warnings + [MSG_EXTRACTION_NO_TEXT]),
            ok=False,
        )

    supplier = guess_supplier_from_local_text(cleaned)
    invoice_date = parse_invoice_date_from_text(cleaned)
    amount = parse_amount_from_text(cleaned)
    document_type = _guess_document_type(cleaned)
    payment_account = _guess_payment_account(cleaned)
    ok = bool(supplier or invoice_date or amount)
    return LocalExtractionResult(
        source_filename=pdf_path.name,
        source_path=str(pdf_path),
        supplier=supplier,
        invoice_date=invoice_date,
        amount=amount,
        document_type=document_type,
        payment_account=payment_account,
        text_chars=len(cleaned),
        extraction_method=MSG_EXTRACTION_LOCAL_TEXT,
        warnings=tuple(warnings),
        ok=ok,
        raw_text_head=cleaned[:1200],
    )


def _planned_with_suggestion(
    planned: ProcessingPlannedDestination,
    *,
    extraction: LocalExtractionResult,
) -> ProcessingPlannedDestination:
    mapping = map_suggested_filename(
        SuggestedFilenameFields(
            supplier=extraction.supplier,
            invoice_date=extraction.invoice_date,
            amount=extraction.amount,
            document_type=extraction.document_type,
            payment_account=extraction.payment_account,
            source_filename=planned.document_name or extraction.source_filename,
            planned_basename=Path(planned.planned_path).name if planned.planned_path else None,
            target_folder=str(Path(planned.planned_path).parent) if planned.planned_path else None,
            review_reason=planned.reason,
            # Prefer any already-resolved routing/profile category on the plan;
            # never invent Architektur when absent.
            business_category=planned.business_category,
            routing_category=planned.business_category,
            document_direction=planned.document_direction,
            raw_text_head=extraction.raw_text_head,
        ),
        review_required=True,
    )
    suggested = mapping.suggested_filename
    new_path = planned.planned_path
    if suggested and planned.planned_path:
        parent = Path(planned.planned_path).parent.as_posix()
        new_path = f"{parent}/{suggested}" if parent not in {"", "."} else suggested
    return replace(
        planned,
        planned_path=new_path,
        suggested_filename=suggested,
        filename_source=mapping.filename_source,
        naming_confidence=mapping.naming_confidence,
        naming_reason=mapping.naming_reason,
        supplier=mapping.supplier,
        invoice_date=mapping.invoice_date,
        amount=mapping.amount,
        document_type=mapping.document_type,
        payment_account=mapping.payment_account,
        suggested_filename_fields=mapping.suggested_filename_fields,
        extraction_method=extraction.extraction_method,
        reason=planned.reason or mapping.naming_reason,
        canonical_filename=mapping.canonical_filename,
        filename_template_version=mapping.filename_template_version,
        document_direction=mapping.document_direction,
        business_category=mapping.business_category,
        business_category_display=mapping.business_category_display,
        counterparty_name=mapping.counterparty_name,
        missing_fields=mapping.missing_fields,
        matched_configuration_name=mapping.matched_configuration_name,
        matched_configuration_id=mapping.matched_configuration_id,
        matched_configuration_pattern=mapping.matched_configuration_pattern,
        matched_configuration_reason=mapping.matched_configuration_reason,
        matched_configuration_confidence=mapping.matched_configuration_confidence,
        filename_pattern=mapping.filename_pattern,
        rendered_filename=mapping.rendered_filename,
        placeholder_values=mapping.placeholder_values,
        missing_placeholders=mapping.missing_placeholders,
        amount_format=mapping.amount_format,
    )


def enrich_planned_destinations_with_local_extraction(
    planned: Iterable[ProcessingPlannedDestination],
    *,
    input_folder: Path | str | None,
) -> tuple[ProcessingPlannedDestination, ...]:
    """Enrich planned destinations with local suggested filenames.

    Only runs against explicit copied sandbox input roots. Never mutates files.
    """

    planned_list = tuple(planned or ())
    unsafe = assert_safe_sandbox_extraction_root(input_folder)
    if unsafe is not None:
        return planned_list
    root = _norm_path(input_folder)
    if root is None:
        return planned_list

    enriched: list[ProcessingPlannedDestination] = []
    for item in planned_list:
        name = (item.document_name or "").strip()
        if not name.lower().endswith(".pdf"):
            enriched.append(item)
            continue
        pdf_path = root / name
        if not pdf_path.is_file():
            # Do not invent paths outside the sandbox root.
            enriched.append(item)
            continue
        try:
            if not pdf_path.resolve().is_relative_to(root):
                enriched.append(item)
                continue
        except (OSError, ValueError, AttributeError):
            # Python <3.9 compatibility / resolve edge cases — skip enrichment.
            enriched.append(item)
            continue
        extraction = extract_local_fields_from_pdf(pdf_path)
        if not extraction.ok:
            enriched.append(
                replace(
                    item,
                    naming_reason=MSG_EXTRACTION_NO_TEXT,
                    extraction_method=extraction.extraction_method,
                    naming_confidence="none",
                    filename_source="original_fallback",
                )
            )
            continue
        enriched.append(_planned_with_suggestion(item, extraction=extraction))
    return tuple(enriched)


__all__ = (
    "LocalExtractionResult",
    "MSG_AI_OCR_NOT_USED",
    "MSG_EXTRACTION_LOCAL_TEXT",
    "MSG_EXTRACTION_NO_TEXT",
    "MSG_EXTRACTION_SKIPPED_UNSAFE_PATH",
    "assert_safe_sandbox_extraction_root",
    "enrich_planned_destinations_with_local_extraction",
    "extract_local_fields_from_pdf",
    "guess_supplier_from_local_text",
    "read_pdf_text_layer",
)
