"""
Diagnostic decision trace for each processed file.

Records every active rule decision so that routing/classification problems
can be distinguished from extraction/OCR problems and configuration gaps.

Behavior is strictly observational: this module never changes routing decisions.
Sensitive data (card numbers, full IBANs) is masked to last-4-digit endings only.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Masking helpers
# ---------------------------------------------------------------------------

_IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
_CARD_NUMBER_PATTERN = re.compile(r"\b\d{13,19}\b")


def _mask_iban(value: str) -> str:
    """Replace every full IBAN with its last-4-digit ending only."""
    def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
        iban = match.group(0)
        return f"IBAN-ending-{iban[-4:]}"
    return _IBAN_PATTERN.sub(_replace, value)


def _mask_card_number(value: str) -> str:
    """Replace bare 13–19 digit sequences with their last-4-digit ending."""
    def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
        digits = match.group(0)
        return f"card-ending-{digits[-4:]}"
    return _CARD_NUMBER_PATTERN.sub(_replace, value)


def mask_sensitive(value: str | None) -> str | None:
    if not value:
        return value
    value = _mask_iban(value)
    value = _mask_card_number(value)
    return value


# ---------------------------------------------------------------------------
# DecisionTrace dataclass
# ---------------------------------------------------------------------------

@dataclass
class DecisionTrace:
    """One trace entry per processed file, capturing every active rule decision."""

    # --- Identity ---
    run_id: str
    original_filename: str
    final_filename: str | None
    source_path: str | None
    target_path: str | None
    archive_path: str | None

    # --- Classification ---
    document_type: str          # "invoice" | "document" | "duplicate" | "failed"
    classification_reason: str | None

    # --- Extraction ---
    extracted_invoice_date: str | None
    extracted_supplier: str | None
    extracted_amount: str | None
    extraction_method: str | None    # "openai" | "tesseract"
    fallback_used: bool

    # --- Street/address ---
    detected_street_key: str | None

    # --- Business context (art/category) ---
    business_context_art: str | None
    business_context_reason: str | None

    # --- Account resolution ---
    account_konto: str | None
    account_payment_field: str | None
    account_match_source: str | None    # "card" | "apple" | "iban" | "provider"
    account_match_reason: str | None
    account_matched_rule: str | None

    # --- Payment method ---
    detected_payment_method: str | None
    payment_rule_name: str | None
    payment_explicit: bool | None
    payment_signals: str | None

    # --- Priority routing ---
    priority_rule_name: str | None  # non-None if a priority rule overrode standard routing

    # --- Final assignment ---
    final_assignment_rule_name: str | None
    final_art: str | None
    final_konto: str | None
    final_payment_field: str | None
    final_status: str | None

    # --- Output routing ---
    output_route_rule_name: str | None
    final_output_folder: str | None

    # --- Filename ---
    filename_fields_used: list[str] = field(default_factory=list)

    # --- Warnings ---
    normalization_warnings: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_csv_row(self) -> dict:
        """Flat CSV-friendly representation."""
        return {
            "run_id": self.run_id,
            "filename": self.original_filename,
            "art": self.final_art or "",
            "konto": self.final_konto or "",
            "payment_field": self.final_payment_field or "",
            "target_folder": self.final_output_folder or "",
            "document_type": self.document_type,
            "business_rule": self.business_context_reason or "",
            "payment_rule": self.payment_rule_name or "",
            "final_assignment_rule": self.final_assignment_rule_name or "",
            "output_route_rule": self.output_route_rule_name or "",
            "priority_rule": self.priority_rule_name or "",
            "street": self.detected_street_key or "",
            "account_matched_rule": self.account_matched_rule or "",
            "fallback_used": str(self.fallback_used).lower(),
            "warnings": "; ".join(self.normalization_warnings),
            "conflicts": "; ".join(self.conflicts),
            "final_filename": self.final_filename or "",
        }


CSV_FIELDNAMES = [
    "run_id",
    "filename",
    "art",
    "konto",
    "payment_field",
    "target_folder",
    "document_type",
    "business_rule",
    "payment_rule",
    "final_assignment_rule",
    "output_route_rule",
    "priority_rule",
    "street",
    "account_matched_rule",
    "fallback_used",
    "warnings",
    "conflicts",
    "final_filename",
]


# ---------------------------------------------------------------------------
# TraceWriter: accumulates traces per run, writes files at the end
# ---------------------------------------------------------------------------

class TraceWriter:
    """Accumulates decision traces for one run and writes them to disk."""

    def __init__(self) -> None:
        self._traces: list[DecisionTrace] = []

    def record(self, trace: DecisionTrace) -> None:
        self._traces.append(trace)

    def flush(self, report_dir: Path) -> tuple[Path, Path]:
        """Write decision_trace.jsonl and routing_summary.csv. Return their paths."""
        report_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = report_dir / "decision_trace.jsonl"
        csv_path = report_dir / "routing_summary.csv"

        with jsonl_path.open("w", encoding="utf-8") as handle:
            for trace in self._traces:
                handle.write(json.dumps(trace.to_dict(), ensure_ascii=False) + "\n")

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()
            for trace in self._traces:
                writer.writerow(trace.to_csv_row())

        return jsonl_path, csv_path
