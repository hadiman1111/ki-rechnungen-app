"""Track-B controlled Preview Export package writer (Prompt 16–17/34).

Writes a clearly marked preview-export package under a controlled sandbox/test
output folder. Copies input PDFs as byte-identical preview artifacts and emits
manifest/README reports with honest filename-source / naming-reason metadata.

Never mutates input/source files, never calls run_once, never performs final
productive processing, never writes outside the validated sandbox output root.
Never invents supplier/date/amount invoice names when extraction data is absent.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping

from invoice_tool.ui_v2.configuration_guidance import (
    MSG_FIELD_CONFIGURATION_COVERAGE,
    MSG_FIELD_GUIDANCE_SEVERITY,
    MSG_FIELD_MISSING_CONFIGURATION_TYPE,
    MSG_FIELD_SUGGESTED_ACTION,
    MSG_FIELD_USER_GUIDANCE,
    SAFE_NEXT_ACTIONS,
    ensure_guidance_fields,
)
from invoice_tool.ui_v2.core_dry_run_contract import (
    is_explicit_copied_sandbox_test_path,
    path_has_forbidden_productive_marker,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingErrorItem,
    ProcessingPlannedDestination,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_preview_state import (
    get_review_preview_ui,
    planned_for_document,
    review_item_key,
)

# Stable aliases for review UI / tests (Prompt 23/34).
MSG_FIELD_SUGGESTED_CONFIGURATION_ACTION = MSG_FIELD_SUGGESTED_ACTION

PREVIEW_EXPORT_KIND = "track_b_preview_export_package"
PREVIEW_EXPORT_SCHEMA_VERSION = 1
PREVIEW_EXPORT_FOLDER_PREFIX = "preview-export-"
REVIEW_REQUIRED_PREFIX = "REVIEW_REQUIRED__"
REVIEW_REQUIRED_SUGGESTED_PREFIX = "REVIEW_REQUIRED__SUGGESTED__"
REVIEW_REQUIRED_SUGGESTED_INCOMPLETE_PREFIX = "REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__"
SUGGESTED_PREFIX = "SUGGESTED__"
FILES_SUBDIR = "files"

FilenameSource = Literal[
    "planned_result",
    "suggested_mapping",
    "original_fallback",
    "configuration_pattern",
    "configuration_pattern_incomplete",
    "canonical_fallback_no_configuration_pattern",
]

FILENAME_SOURCE_PLANNED_RESULT: FilenameSource = "planned_result"
FILENAME_SOURCE_SUGGESTED_MAPPING: FilenameSource = "suggested_mapping"
FILENAME_SOURCE_ORIGINAL_FALLBACK: FilenameSource = "original_fallback"
FILENAME_SOURCE_CONFIGURATION_PATTERN: FilenameSource = "configuration_pattern"
FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE: FilenameSource = (
    "configuration_pattern_incomplete"
)
FILENAME_SOURCE_CANONICAL_FALLBACK: FilenameSource = (
    "canonical_fallback_no_configuration_pattern"
)

MSG_FIELD_CONFIGURATION = "Konfiguration"
MSG_FIELD_MATCHING_REASON = "Matching-Grund"
MSG_FIELD_CONDITION_RESULTS = "geprüfte Bedingungen"
MSG_FIELD_MISSING_CONFIGURATION_RULE = "fehlende Konfigurationsregel"
MSG_FIELD_AVAILABLE_CONFIGURATIONS = "verfügbare Konfigurationen"
MSG_FIELD_EVALUATED_CANDIDATES = "geprüfte Konfigurationen"
MSG_FIELD_FILENAME_PATTERN = "Dateinamensmuster"
MSG_FIELD_PLACEHOLDER_VALUES = "Platzhalterwerte"
MSG_FIELD_MISSING_PLACEHOLDERS = "fehlende Platzhalter"
MSG_FIELD_AMOUNT_FORMAT = "Betrag format"
MSG_FIELD_RENDERED_FILENAME = "Vorschau-Dateiname"

MSG_PREVIEW_EXPORT_TITLE = "Preview Export"
MSG_PREVIEW_EXPORT_CTA = "Preview-Export in Output-Ordner schreiben"
MSG_PREVIEW_EXPORT_WRITES_PACKAGE_ONLY = "schreibt nur ein Preview-Paket"
MSG_PREVIEW_EXPORT_ORIGINALS_UNCHANGED = "Originale bleiben unverändert"
MSG_PREVIEW_EXPORT_NO_FINAL = "keine finale Verarbeitung"
MSG_PREVIEW_EXPORT_PRODUCTIVE_LOCKED = "Produktiv gesperrt"
MSG_PREVIEW_EXPORT_CREATED = "Preview-Export erstellt"
MSG_PREVIEW_EXPORT_NO_FINAL_FILES = "Keine finalen Dateien geschrieben"
MSG_PREVIEW_EXPORT_NOT_PRODUCTION = "kein finales Produktions-Output"
MSG_PREVIEW_EXPORT_SANDBOX_ONLY = "Preview/Sandbox-Export — kein Produktivexport"
MSG_PREVIEW_EXPORT_NEEDS_COMPLETED_RUN = (
    "Preview-Export erst nach erfolgreichem Sandbox-Ergebnis verfügbar."
)
MSG_PREVIEW_EXPORT_NEEDS_FOLDERS = (
    "Preview-Export benötigt kontrollierten Eingangs- und Ausgabeordner."
)
MSG_PREVIEW_EXPORT_BLOCKED_PATH = (
    "Preview-Export blockiert: Pfadpolitik verletzt (Sandbox/Test erforderlich)."
)
MSG_PREVIEW_EXPORT_SAME_PATH = (
    "Preview-Export blockiert: Eingang und Ausgabe müssen getrennt sein."
)
MSG_PREVIEW_EXPORT_NO_SOURCE = (
    "Preview-Export blockiert: Quell-PDF nicht im kontrollierten Eingang gefunden."
)
MSG_PREVIEW_EXPORT_PARTIAL_BLOCKED = (
    "Preview-Export blockiert: unsicherer Teillauf — nichts wurde als fertig markiert."
)
MSG_PREVIEW_EXPORT_STALE_STATE_BLOCKED = (
    "PREVIEW_EXPORT_STALE_STATE_BLOCKED: Preview-Export blockiert — "
    "Export-State weicht vom aktuellen Review-UI-/Run-State ab oder ist intern veraltet."
)
MSG_PREVIEW_EXPORT_STALE_SOURCE_BLOCKED = (
    "PREVIEW_EXPORT_STALE_STATE_BLOCKED: Preview-Export blockiert — "
    "alter Preview-Export-Ordner darf nicht als Datenquelle dienen."
)
MSG_NO_SAAS_READY = "nicht SaaS-ready"
MSG_NO_PRODUCTION_READY = "nicht production-ready"
STATE_SOURCE_CURRENT_PROCESSING_RUN = "processing_run_state.current"
STATE_SOURCE_REVIEW_UI = "review_ui_current_state"
MSG_FIELD_PREVIEW_FILENAME = "Vorschau-Dateiname"
MSG_FIELD_NAMING_REASON = "Grund für REVIEW_REQUIRED"
MSG_FIELD_PLANNED_TARGET = "Geplantes Ziel"
MSG_FIELD_DOCUMENT_DIRECTION = "Rechnungsart"
MSG_FIELD_BUSINESS_CATEGORY = "Zuordnung"
MSG_FIELD_COUNTERPARTY_NAME = "Name"
MSG_FIELD_AMOUNT = "Betrag"
MSG_FIELD_AMOUNT_REASON = "Betrag Quelle/Grund"
MSG_FIELD_PAYMENT_FIELD = "Zahlungsfeld"
MSG_FIELD_PAYMENT_FIELD_REASON = "Zahlungsfeld Quelle/Grund"
MSG_FIELD_DOCUMENT_ART = "Art/Dokumenttyp"
MSG_FIELD_ART_REASON = "Art Quelle/Grund"
MSG_NAMING_NOT_FINAL = "Benennung noch nicht final"
MSG_SUGGESTED_PREVIEW_ONLY = (
    "Vorschlagsname nur als Preview — finale Freigabe erforderlich; "
    "Originale unverändert; kein Produktivexport."
)
MSG_NAMING_REASON_SUGGESTED = (
    "Prüffall — sicherer Vorschlagsname aus geplantem Ziel verwendet; "
    "finale Freigabe erforderlich."
)
MSG_NAMING_REASON_PLANNED_SAME_AS_SOURCE = (
    "Prüffall — geplantes Ziel vorhanden, aber Dateiname entspricht dem Original; "
    "kein abweichender Vorschlagsname (fehlende Extraktion/Mapping)."
)
MSG_NAMING_REASON_NO_SUGGESTED = (
    "Prüffall — kein sicherer geplanter/vorgeschlagener Dateiname verfügbar; "
    "Originalname als Fallback."
)
MSG_NAMING_REASON_RECOGNIZED_PLANNED = (
    "Erkannt/geplant — Preview-Dateiname aus geplantem Ziel (nicht final)."
)
MSG_NAMING_REASON_RECOGNIZED_SOURCE = (
    "Erkannt — Preview-Dateiname aus Original (kein abweichendes geplantes Ziel)."
)

# Positive maturity / write claims only — negated disclaimers are allowed.
FORBIDDEN_POSITIVE_CLAIM_MARKERS = (
    "saas ready",
    "saas_ready",
    "production ready",
    "production_ready",
    "produktiv verarbeitet",
    "final geschrieben",
    "final verarbeitet",
)
# Back-compat alias used by tests / callers.
FORBIDDEN_CLAIM_MARKERS = FORBIDDEN_POSITIVE_CLAIM_MARKERS

# Allow decimal comma in configuration-pattern amounts (e.g. 84,39).
_UNSAFE_FILENAME_RE = re.compile(r"[^\w.\-, ()\[\]]+", re.UNICODE)
_MULTI_UNDERSCORE_RE = re.compile(r"_{2,}")


@dataclass(frozen=True)
class PreviewNamingDecision:
    """Honest preview naming decision — never invents invoice metadata."""

    preview_filename: str
    suggested_filename: str | None
    planned_target: str | None
    filename_source: FilenameSource
    naming_reason: str
    review_required: bool
    naming_confidence: str | None = None
    supplier: str | None = None
    invoice_date: str | None = None
    amount: str | None = None
    document_type: str | None = None
    payment_account: str | None = None
    suggested_filename_fields: tuple[str, ...] = field(default_factory=tuple)
    canonical_filename: str | None = None
    filename_template_version: str | None = None
    document_direction: str | None = None
    business_category: str | None = None
    business_category_display: str | None = None
    counterparty_name: str | None = None
    missing_fields: tuple[str, ...] = field(default_factory=tuple)
    matched_configuration_name: str | None = None
    matched_configuration_id: str | None = None
    matched_configuration_pattern: str | None = None
    matched_configuration_reason: str | None = None
    matched_configuration_confidence: str | None = None
    filename_pattern: str | None = None
    rendered_filename: str | None = None
    placeholder_values: tuple[tuple[str, str | None], ...] = field(default_factory=tuple)
    missing_placeholders: tuple[str, ...] = field(default_factory=tuple)
    amount_format: str | None = None
    amount_candidates: tuple[dict[str, object], ...] = field(default_factory=tuple)
    selected_amount: str | None = None
    selected_amount_reason: str | None = None
    rejected_amount_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    payment_field_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    selected_payment_field: str | None = None
    selected_payment_field_reason: str | None = None
    document_art_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    selected_art: str | None = None
    selected_art_reason: str | None = None
    art_ambiguity: bool = False
    available_configurations: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    evaluated_configuration_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    unmatched_reasons: tuple[str, ...] = field(default_factory=tuple)
    condition_results: tuple[dict[str, object], ...] = field(default_factory=tuple)
    alternative_matches: tuple[dict[str, object], ...] = field(default_factory=tuple)
    missing_configuration_rule: str | None = None
    configuration_coverage_status: str | None = None
    missing_configuration_type: str | None = None
    user_guidance: str | None = None
    suggested_configuration_action: str | None = None
    guidance_severity: str | None = None
    # Prompt 27/34 — apply saved rule + preview rerun transparency.
    rule_applied: bool = False
    applied_configuration_name: str | None = None
    applied_configuration_condition: str | None = None
    rerun_preview_after_rule_change: bool = False
    matched_after_rule_change: bool = False
    previous_matched_configuration: str | None = None
    new_matched_configuration: str | None = None


@dataclass(frozen=True)
class PreviewExportItem:
    source_filename: str
    preview_filename: str
    status: str
    category: str
    planned_target: str | None
    review_required: bool
    source_sha256: str
    preview_sha256: str
    source_path: str
    preview_path: str
    excluded: bool = False
    suggested_filename: str | None = None
    filename_source: FilenameSource = FILENAME_SOURCE_ORIGINAL_FALLBACK
    naming_reason: str = MSG_NAMING_REASON_NO_SUGGESTED
    review_reason: str | None = None
    naming_confidence: str | None = None
    supplier: str | None = None
    invoice_date: str | None = None
    amount: str | None = None
    document_type: str | None = None
    payment_account: str | None = None
    suggested_filename_fields: tuple[str, ...] = field(default_factory=tuple)
    canonical_filename: str | None = None
    filename_template_version: str | None = None
    document_direction: str | None = None
    business_category: str | None = None
    business_category_display: str | None = None
    counterparty_name: str | None = None
    missing_fields: tuple[str, ...] = field(default_factory=tuple)
    matched_configuration_name: str | None = None
    matched_configuration_id: str | None = None
    matched_configuration_pattern: str | None = None
    matched_configuration_reason: str | None = None
    matched_configuration_confidence: str | None = None
    filename_pattern: str | None = None
    rendered_filename: str | None = None
    placeholder_values: tuple[tuple[str, str | None], ...] = field(default_factory=tuple)
    missing_placeholders: tuple[str, ...] = field(default_factory=tuple)
    amount_format: str | None = None
    amount_candidates: tuple[dict[str, object], ...] = field(default_factory=tuple)
    selected_amount: str | None = None
    selected_amount_reason: str | None = None
    rejected_amount_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    payment_field_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    selected_payment_field: str | None = None
    selected_payment_field_reason: str | None = None
    document_art_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    selected_art: str | None = None
    selected_art_reason: str | None = None
    art_ambiguity: bool = False
    available_configurations: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    evaluated_configuration_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    unmatched_reasons: tuple[str, ...] = field(default_factory=tuple)
    condition_results: tuple[dict[str, object], ...] = field(default_factory=tuple)
    alternative_matches: tuple[dict[str, object], ...] = field(default_factory=tuple)
    missing_configuration_rule: str | None = None
    configuration_coverage_status: str | None = None
    missing_configuration_type: str | None = None
    user_guidance: str | None = None
    suggested_configuration_action: str | None = None
    guidance_severity: str | None = None
    # Prompt 27/34 — apply saved rule + preview rerun transparency.
    rule_applied: bool = False
    applied_configuration_name: str | None = None
    applied_configuration_condition: str | None = None
    rerun_preview_after_rule_change: bool = False
    matched_after_rule_change: bool = False
    previous_matched_configuration: str | None = None
    new_matched_configuration: str | None = None
    # Prompt 29/34 — review decision / finalization readiness (no final write).
    review_decision: str | None = None
    decision_timestamp: str | None = None
    approved_by_user: bool = False
    finalization_ready: bool = False
    decision_ready_for_future_finalization: bool = False
    finalization_blockers: tuple[str, ...] = field(default_factory=tuple)
    approved_preview_filename: str | None = None
    target_preview_path: str | None = None
    user_edited_fields: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    warnings_acknowledged: tuple[str, ...] = field(default_factory=tuple)
    source_hash_at_decision: str | None = None
    preview_state_id: str | None = None
    final_write_allowed: bool = False
    # Prompt 30/34 — finalization preview batch item fields (no final write).
    finalization_status: str | None = None
    finalization_warnings: tuple[str, ...] = field(default_factory=tuple)
    target_conflict_status: str | None = None


@dataclass(frozen=True)
class PreviewExportResult:
    ok: bool
    status: str
    export_folder: Path | None = None
    copied_file_count: int = 0
    item_count: int = 0
    recognized_count: int = 0
    review_count: int = 0
    error_count: int = 0
    planned_count: int = 0
    written_files: tuple[str, ...] = ()
    items: tuple[PreviewExportItem, ...] = ()
    error: str | None = None
    productive_mode_requested: bool = False
    dry_run: bool = True
    preview_export: bool = True
    final_write: bool = False
    source_mutation: bool = False
    claims_saas_ready: bool = False
    claims_production_ready: bool = False


@dataclass(frozen=True)
class PreviewExportRequest:
    run_state: ProcessingRunState
    input_root: Path | str
    output_root: Path | str
    excluded_keys: frozenset[str] = field(default_factory=frozenset)
    productive_mode_requested: bool = False
    dry_run: bool = True
    preview_export: bool = True
    final_write: bool = False


@dataclass(frozen=True)
class ReviewExportExpectation:
    """Values the Review UI would show for one document — export must match."""

    source_filename: str
    preview_filename: str
    rendered_filename: str | None = None
    selected_amount: str | None = None
    selected_payment_field: str | None = None
    selected_art: str | None = None
    suggested_filename: str | None = None


def sanitize_preview_filename(name: str) -> str:
    """Sanitize a basename for preview package use — no path traversal."""

    base = Path(str(name or "").strip() or "document.pdf").name
    cleaned = base.replace(" ", "_")
    cleaned = _UNSAFE_FILENAME_RE.sub("_", cleaned).strip(" ._")
    cleaned = _MULTI_UNDERSCORE_RE.sub("_", cleaned)
    if not cleaned:
        cleaned = "document.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned


def review_required_preview_filename(source_filename: str) -> str:
    safe = sanitize_preview_filename(source_filename)
    if safe.startswith(REVIEW_REQUIRED_PREFIX):
        return safe
    return f"{REVIEW_REQUIRED_PREFIX}{safe}"


def _strip_preview_name_prefixes(name: str) -> str:
    safe = sanitize_preview_filename(name)
    changed = True
    while changed:
        changed = False
        for prefix in (
            REVIEW_REQUIRED_SUGGESTED_INCOMPLETE_PREFIX,
            REVIEW_REQUIRED_SUGGESTED_PREFIX,
            REVIEW_REQUIRED_PREFIX,
            SUGGESTED_PREFIX,
            "INCOMPLETE__",
        ):
            if safe.startswith(prefix):
                safe = safe[len(prefix) :]
                changed = True
    return sanitize_preview_filename(safe)


def review_required_suggested_preview_filename(
    suggested_filename: str,
    *,
    incomplete: bool = False,
) -> str:
    """Mark a safe suggested name as review-required preview (not final)."""

    safe = _strip_preview_name_prefixes(suggested_filename)
    if incomplete:
        return f"{REVIEW_REQUIRED_SUGGESTED_INCOMPLETE_PREFIX}{safe}"
    return f"{REVIEW_REQUIRED_SUGGESTED_PREFIX}{safe}"


def suggested_preview_filename(suggested_filename: str) -> str:
    """Mark a safe suggested name for recognized (non-review) preview cases."""

    safe = _strip_preview_name_prefixes(suggested_filename)
    return f"{SUGGESTED_PREFIX}{safe}"


def _planned_basename(planned: ProcessingPlannedDestination | None) -> str | None:
    if planned is None:
        return None
    name = Path(str(planned.planned_path or "").strip()).name
    if not name or not name.lower().endswith(".pdf"):
        return None
    if ".." in name or "/" in name or "\\" in name:
        return None
    return name


def _basename_differs_from_source(planned_name: str, source_filename: str) -> bool:
    return sanitize_preview_filename(planned_name).lower() != sanitize_preview_filename(
        source_filename
    ).lower()


def _meta_from_planned(
    planned: ProcessingPlannedDestination | None,
) -> dict[str, Any]:
    if planned is None:
        return {
            "naming_confidence": None,
            "supplier": None,
            "invoice_date": None,
            "amount": None,
            "document_type": None,
            "payment_account": None,
            "suggested_filename_fields": (),
            "planned_naming_reason": None,
            "planned_filename_source": None,
            "canonical_filename": None,
            "filename_template_version": None,
            "document_direction": None,
            "business_category": None,
            "business_category_display": None,
            "counterparty_name": None,
            "missing_fields": (),
            "matched_configuration_name": None,
            "matched_configuration_id": None,
            "matched_configuration_pattern": None,
            "matched_configuration_reason": None,
            "matched_configuration_confidence": None,
            "filename_pattern": None,
            "rendered_filename": None,
            "placeholder_values": (),
            "missing_placeholders": (),
            "amount_format": None,
            "amount_candidates": (),
            "selected_amount": None,
            "selected_amount_reason": None,
            "rejected_amount_candidates": (),
            "payment_field_candidates": (),
            "selected_payment_field": None,
            "selected_payment_field_reason": None,
            "document_art_candidates": (),
            "selected_art": None,
            "selected_art_reason": None,
            "art_ambiguity": False,
            "available_configurations": (),
            "evaluated_configuration_candidates": (),
            "unmatched_reasons": (),
            "condition_results": (),
            "alternative_matches": (),
            "missing_configuration_rule": None,
            "configuration_coverage_status": None,
            "missing_configuration_type": None,
            "user_guidance": None,
            "suggested_configuration_action": None,
            "guidance_severity": None,
            "rule_applied": False,
            "applied_configuration_name": None,
            "applied_configuration_condition": None,
            "rerun_preview_after_rule_change": False,
            "matched_after_rule_change": False,
            "previous_matched_configuration": None,
            "new_matched_configuration": None,
            "source_filename": None,
        }
    fields = tuple(planned.suggested_filename_fields or ())
    base = {
        "naming_confidence": planned.naming_confidence,
        "supplier": planned.supplier,
        "invoice_date": planned.invoice_date,
        "amount": planned.amount,
        "document_type": planned.document_type,
        "payment_account": planned.payment_account,
        "suggested_filename_fields": fields,
        "planned_naming_reason": planned.naming_reason,
        "planned_filename_source": planned.filename_source,
        "canonical_filename": planned.canonical_filename or planned.suggested_filename,
        "filename_template_version": planned.filename_template_version,
        "document_direction": planned.document_direction,
        "business_category": planned.business_category,
        "business_category_display": planned.business_category_display,
        "counterparty_name": planned.counterparty_name or planned.supplier,
        "missing_fields": tuple(planned.missing_fields or ()),
        "matched_configuration_name": planned.matched_configuration_name,
        "matched_configuration_id": planned.matched_configuration_id,
        "matched_configuration_pattern": planned.matched_configuration_pattern,
        "matched_configuration_reason": planned.matched_configuration_reason,
        "matched_configuration_confidence": planned.matched_configuration_confidence,
        "filename_pattern": planned.filename_pattern,
        "rendered_filename": planned.rendered_filename or planned.suggested_filename,
        "placeholder_values": tuple(planned.placeholder_values or ()),
        "missing_placeholders": tuple(planned.missing_placeholders or ()),
        "amount_format": planned.amount_format,
        "amount_candidates": tuple(planned.amount_candidates or ()),
        "selected_amount": planned.selected_amount or planned.amount,
        "selected_amount_reason": planned.selected_amount_reason,
        "rejected_amount_candidates": tuple(planned.rejected_amount_candidates or ()),
        "payment_field_candidates": tuple(planned.payment_field_candidates or ()),
        "selected_payment_field": planned.selected_payment_field
        or planned.payment_account,
        "selected_payment_field_reason": planned.selected_payment_field_reason,
        "document_art_candidates": tuple(planned.document_art_candidates or ()),
        "selected_art": planned.selected_art,
        "selected_art_reason": planned.selected_art_reason,
        "art_ambiguity": bool(planned.art_ambiguity),
        "available_configurations": tuple(planned.available_configurations or ()),
        "evaluated_configuration_candidates": tuple(
            planned.evaluated_configuration_candidates or ()
        ),
        "unmatched_reasons": tuple(planned.unmatched_reasons or ()),
        "condition_results": tuple(planned.condition_results or ()),
        "alternative_matches": tuple(planned.alternative_matches or ()),
        "missing_configuration_rule": planned.missing_configuration_rule,
        "configuration_coverage_status": planned.configuration_coverage_status,
        "missing_configuration_type": planned.missing_configuration_type,
        "user_guidance": planned.user_guidance,
        "suggested_configuration_action": planned.suggested_configuration_action,
        "guidance_severity": planned.guidance_severity,
        "rule_applied": bool(planned.rule_applied),
        "applied_configuration_name": planned.applied_configuration_name,
        "applied_configuration_condition": planned.applied_configuration_condition,
        "rerun_preview_after_rule_change": bool(
            planned.rerun_preview_after_rule_change
        ),
        "matched_after_rule_change": bool(planned.matched_after_rule_change),
        "previous_matched_configuration": planned.previous_matched_configuration,
        "new_matched_configuration": planned.new_matched_configuration,
        "source_filename": planned.document_name,
    }
    return {**base, **ensure_guidance_fields(base)}


def _naming_decision_fields(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "naming_confidence": meta["naming_confidence"],
        "supplier": meta["supplier"],
        "invoice_date": meta["invoice_date"],
        "amount": meta["amount"],
        "document_type": meta["document_type"],
        "payment_account": meta["payment_account"],
        "suggested_filename_fields": meta["suggested_filename_fields"],
        "canonical_filename": meta.get("canonical_filename"),
        "filename_template_version": meta.get("filename_template_version"),
        "document_direction": meta.get("document_direction"),
        "business_category": meta.get("business_category"),
        "business_category_display": meta.get("business_category_display"),
        "counterparty_name": meta.get("counterparty_name"),
        "missing_fields": tuple(meta.get("missing_fields") or ()),
        "matched_configuration_name": meta.get("matched_configuration_name"),
        "matched_configuration_id": meta.get("matched_configuration_id"),
        "matched_configuration_pattern": meta.get("matched_configuration_pattern"),
        "matched_configuration_reason": meta.get("matched_configuration_reason"),
        "matched_configuration_confidence": meta.get(
            "matched_configuration_confidence"
        ),
        "filename_pattern": meta.get("filename_pattern"),
        "rendered_filename": meta.get("rendered_filename"),
        "placeholder_values": tuple(meta.get("placeholder_values") or ()),
        "missing_placeholders": tuple(meta.get("missing_placeholders") or ()),
        "amount_format": meta.get("amount_format"),
        "amount_candidates": tuple(meta.get("amount_candidates") or ()),
        "selected_amount": meta.get("selected_amount"),
        "selected_amount_reason": meta.get("selected_amount_reason"),
        "rejected_amount_candidates": tuple(
            meta.get("rejected_amount_candidates") or ()
        ),
        "payment_field_candidates": tuple(meta.get("payment_field_candidates") or ()),
        "selected_payment_field": meta.get("selected_payment_field"),
        "selected_payment_field_reason": meta.get("selected_payment_field_reason"),
        "document_art_candidates": tuple(meta.get("document_art_candidates") or ()),
        "selected_art": meta.get("selected_art"),
        "selected_art_reason": meta.get("selected_art_reason"),
        "art_ambiguity": bool(meta.get("art_ambiguity") or False),
        "available_configurations": tuple(meta.get("available_configurations") or ()),
        "evaluated_configuration_candidates": tuple(
            meta.get("evaluated_configuration_candidates") or ()
        ),
        "unmatched_reasons": tuple(meta.get("unmatched_reasons") or ()),
        "condition_results": tuple(meta.get("condition_results") or ()),
        "alternative_matches": tuple(meta.get("alternative_matches") or ()),
        "missing_configuration_rule": meta.get("missing_configuration_rule"),
        "rule_applied": bool(meta.get("rule_applied") or False),
        "applied_configuration_name": meta.get("applied_configuration_name"),
        "applied_configuration_condition": meta.get(
            "applied_configuration_condition"
        ),
        "rerun_preview_after_rule_change": bool(
            meta.get("rerun_preview_after_rule_change") or False
        ),
        "matched_after_rule_change": bool(
            meta.get("matched_after_rule_change") or False
        ),
        "previous_matched_configuration": meta.get(
            "previous_matched_configuration"
        ),
        "new_matched_configuration": meta.get("new_matched_configuration"),
        **ensure_guidance_fields(meta),
    }


def _coerce_filename_source(raw: str | None, default: FilenameSource) -> FilenameSource:
    text = str(raw or "").strip()
    allowed: set[str] = {
        FILENAME_SOURCE_PLANNED_RESULT,
        FILENAME_SOURCE_SUGGESTED_MAPPING,
        FILENAME_SOURCE_ORIGINAL_FALLBACK,
        FILENAME_SOURCE_CONFIGURATION_PATTERN,
        FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE,
        FILENAME_SOURCE_CANONICAL_FALLBACK,
    }
    if text in allowed:
        return text  # type: ignore[return-value]
    return default


def resolve_preview_naming(
    *,
    source_filename: str,
    review_required: bool,
    planned: ProcessingPlannedDestination | None = None,
    suggested_filename: str | None = None,
) -> PreviewNamingDecision:
    """Resolve preview filename + honest naming metadata.

    Uses planned/suggested basenames only when they differ safely from the
    source name. Never invents supplier/date/amount tokens.
    """

    planned_target = (planned.planned_path if planned is not None else None) or None
    if planned_target is not None:
        planned_target = str(planned_target).strip() or None

    meta = _meta_from_planned(planned)
    planned_name = _planned_basename(planned)
    planned_suggested = None
    if planned is not None and (planned.suggested_filename or "").strip():
        planned_suggested = Path(str(planned.suggested_filename).strip()).name
        if not planned_suggested.lower().endswith(".pdf") or ".." in planned_suggested:
            planned_suggested = None

    explicit_suggested = (suggested_filename or "").strip() or None
    if explicit_suggested:
        explicit_suggested = Path(explicit_suggested).name
        if not explicit_suggested.lower().endswith(".pdf") or ".." in explicit_suggested:
            explicit_suggested = None
    if explicit_suggested is None:
        explicit_suggested = planned_suggested

    # Prefer an explicit suggested mapping name when it safely differs.
    candidate: str | None = None
    source_kind: FilenameSource = FILENAME_SOURCE_ORIGINAL_FALLBACK
    if explicit_suggested and _basename_differs_from_source(
        explicit_suggested, source_filename
    ):
        candidate = explicit_suggested
        planned_source = str(meta.get("planned_filename_source") or "").strip()
        source_kind = _coerce_filename_source(
            planned_source, FILENAME_SOURCE_SUGGESTED_MAPPING
        )
        if planned_source == FILENAME_SOURCE_PLANNED_RESULT:
            source_kind = FILENAME_SOURCE_PLANNED_RESULT
    elif planned_name and _basename_differs_from_source(planned_name, source_filename):
        candidate = planned_name
        source_kind = FILENAME_SOURCE_PLANNED_RESULT

    naming_reason_override = meta.get("planned_naming_reason")
    extra = _naming_decision_fields(meta)
    # Prefer rendered configuration / canonical basename when available and safe.
    rendered = (meta.get("rendered_filename") or "").strip() or None
    if rendered:
        rendered = Path(rendered).name
        if not rendered.lower().endswith(".pdf") or ".." in rendered:
            rendered = None
    canonical = (meta.get("canonical_filename") or "").strip() or None
    if canonical:
        canonical = Path(canonical).name
        if not canonical.lower().endswith(".pdf") or ".." in canonical:
            canonical = None
    if candidate is None and rendered and _basename_differs_from_source(
        rendered, source_filename
    ):
        candidate = rendered
        source_kind = _coerce_filename_source(
            str(meta.get("planned_filename_source") or ""),
            FILENAME_SOURCE_CONFIGURATION_PATTERN,
        )
    if candidate is None and canonical and _basename_differs_from_source(
        canonical, source_filename
    ):
        candidate = canonical
        source_kind = FILENAME_SOURCE_CANONICAL_FALLBACK
    if candidate is not None and canonical is None:
        extra = {**extra, "canonical_filename": sanitize_preview_filename(candidate)}

    incomplete = (
        source_kind == FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE
        or bool(meta.get("missing_placeholders"))
    )

    if review_required:
        if candidate is not None:
            safe_suggested = sanitize_preview_filename(candidate)
            return PreviewNamingDecision(
                preview_filename=review_required_suggested_preview_filename(
                    safe_suggested, incomplete=incomplete
                ),
                suggested_filename=safe_suggested,
                planned_target=planned_target,
                filename_source=source_kind,
                naming_reason=naming_reason_override or MSG_NAMING_REASON_SUGGESTED,
                review_required=True,
                **extra,
            )
        reason = (
            naming_reason_override
            or (
                MSG_NAMING_REASON_PLANNED_SAME_AS_SOURCE
                if planned_target
                else MSG_NAMING_REASON_NO_SUGGESTED
            )
        )
        return PreviewNamingDecision(
            preview_filename=review_required_preview_filename(source_filename),
            suggested_filename=None,
            planned_target=planned_target,
            filename_source=FILENAME_SOURCE_ORIGINAL_FALLBACK,
            naming_reason=reason,
            review_required=True,
            **extra,
        )

    if candidate is not None:
        safe_suggested = sanitize_preview_filename(candidate)
        return PreviewNamingDecision(
            preview_filename=suggested_preview_filename(safe_suggested),
            suggested_filename=safe_suggested,
            planned_target=planned_target,
            filename_source=source_kind,
            naming_reason=naming_reason_override or MSG_NAMING_REASON_RECOGNIZED_PLANNED,
            review_required=False,
            **extra,
        )
    return PreviewNamingDecision(
        preview_filename=sanitize_preview_filename(source_filename),
        suggested_filename=None,
        planned_target=planned_target,
        filename_source=FILENAME_SOURCE_ORIGINAL_FALLBACK,
        naming_reason=naming_reason_override or MSG_NAMING_REASON_RECOGNIZED_SOURCE,
        review_required=False,
        **extra,
    )


def preview_export_available(run_state: ProcessingRunState | None) -> bool:
    """True only after a successful sandbox result state exists."""

    if run_state is None:
        return False
    return (run_state.status or "") == "completed"


def _norm_text(value: str | None) -> str:
    return (value or "").strip()


def _path_is_previous_preview_export(path: Path | None) -> bool:
    """True when a path is/inside a previous preview-export-* package."""

    if path is None:
        return False
    try:
        parts = path.resolve().parts
    except OSError:
        parts = path.parts
    for part in parts:
        if str(part).startswith(PREVIEW_EXPORT_FOLDER_PREFIX):
            return True
    return False


def build_review_ui_export_expectations(
    run_state: ProcessingRunState,
) -> tuple[ReviewExportExpectation, ...]:
    """Serialize the same preview naming the Review UI uses for this run state."""

    planned_rows = tuple(run_state.planned_destinations or ())
    expectations: list[ReviewExportExpectation] = []
    seen: set[str] = set()

    def _add(source_filename: str, *, review_required: bool) -> None:
        key = _norm_text(source_filename)
        if not key or key in seen:
            return
        seen.add(key)
        planned = planned_for_document(planned_rows, key)
        naming = resolve_preview_naming(
            source_filename=key,
            review_required=review_required,
            planned=planned,
            suggested_filename=(
                planned.suggested_filename
                if planned is not None
                else None
            )
            or (planned.rendered_filename if planned is not None else None)
            or (planned.canonical_filename if planned is not None else None),
        )
        expectations.append(
            ReviewExportExpectation(
                source_filename=key,
                preview_filename=naming.preview_filename,
                rendered_filename=naming.rendered_filename,
                selected_amount=naming.selected_amount or naming.amount,
                selected_payment_field=naming.selected_payment_field
                or naming.payment_account,
                selected_art=naming.selected_art,
                suggested_filename=naming.suggested_filename,
            )
        )

    for item in run_state.review_items or ():
        _add(item.document_name, review_required=True)
    for item in run_state.results or ():
        _add(item.document_name, review_required=False)
    for item in run_state.error_items or ():
        _add(item.document_name, review_required=True)
    for planned in planned_rows:
        _add(planned.document_name, review_required=True)
    return tuple(expectations)


def _internal_state_stale_reason(
    *,
    preview_filename: str,
    selected_amount: str | None,
    selected_art: str | None,
    suggested_filename: str | None = None,
) -> str | None:
    """Detect internal contradictions that prove stale/pre-repair export state."""

    preview = _norm_text(preview_filename)
    suggested = _norm_text(suggested_filename)
    haystack = f"{preview} {suggested}".lower()
    amount = _norm_text(selected_amount)
    art = _norm_text(selected_art).lower()
    if art == "storno" and "storno" not in haystack and "er_er" in haystack:
        return (
            f"selected_art=storno but preview/suggested filename still uses er_er "
            f"({preview_filename})"
        )
    if amount and amount not in preview and amount not in suggested:
        # Only flag when a suggested invoice-like name exists but omits the amount.
        if suggested and any(ch.isdigit() for ch in suggested):
            return (
                f"selected_amount={amount} missing from preview/suggested filename "
                f"({preview_filename})"
            )
    return None


def validate_export_state_freshness(
    *,
    export_rows: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    expectations: tuple[ReviewExportExpectation, ...] | list[ReviewExportExpectation],
) -> str | None:
    """Return blocker text when export rows disagree with Review UI expectations."""

    expected_by_name = {
        _norm_text(item.source_filename): item for item in expectations
    }
    for row in export_rows:
        source = _norm_text(str(row.get("source_filename") or ""))
        if not source:
            continue
        preview = _norm_text(str(row.get("preview_filename") or ""))
        amount = _norm_text(
            str(row.get("selected_amount") or row.get("amount") or "")
        ) or None
        payment = _norm_text(str(row.get("selected_payment_field") or "")) or None
        art = _norm_text(str(row.get("selected_art") or "")) or None
        suggested = _norm_text(str(row.get("suggested_filename") or "")) or None
        rendered = _norm_text(str(row.get("rendered_filename") or "")) or None

        internal = _internal_state_stale_reason(
            preview_filename=preview,
            selected_amount=amount,
            selected_art=art,
            suggested_filename=suggested,
        )
        if internal:
            return f"{MSG_PREVIEW_EXPORT_STALE_STATE_BLOCKED} ({source}: {internal})"

        expected = expected_by_name.get(source)
        if expected is None:
            continue
        if preview != _norm_text(expected.preview_filename):
            return (
                f"{MSG_PREVIEW_EXPORT_STALE_STATE_BLOCKED} ({source}: "
                f"preview_filename export={preview!r} ui={expected.preview_filename!r})"
            )
        exp_amount = _norm_text(expected.selected_amount) or None
        if exp_amount and amount and amount != exp_amount:
            return (
                f"{MSG_PREVIEW_EXPORT_STALE_STATE_BLOCKED} ({source}: "
                f"amount export={amount!r} ui={exp_amount!r})"
            )
        exp_payment = _norm_text(expected.selected_payment_field) or None
        if exp_payment and payment and payment != exp_payment:
            return (
                f"{MSG_PREVIEW_EXPORT_STALE_STATE_BLOCKED} ({source}: "
                f"payment_field export={payment!r} ui={exp_payment!r})"
            )
        exp_art = _norm_text(expected.selected_art) or None
        if exp_art and art and art != exp_art:
            return (
                f"{MSG_PREVIEW_EXPORT_STALE_STATE_BLOCKED} ({source}: "
                f"art export={art!r} ui={exp_art!r})"
            )
        exp_rendered = _norm_text(expected.rendered_filename) or None
        if exp_rendered and rendered and rendered != exp_rendered:
            return (
                f"{MSG_PREVIEW_EXPORT_STALE_STATE_BLOCKED} ({source}: "
                f"rendered_filename export={rendered!r} ui={exp_rendered!r})"
            )
    return None


def refresh_run_state_from_current_sandbox_input(
    run_state: ProcessingRunState,
    *,
    input_root: Path | str | None,
) -> ProcessingRunState:
    """Re-apply current local enrichment onto planned destinations (sandbox only).

    Ensures Preview Export cannot keep pre-repair amounts/art from an older
    in-memory mapping when the controlled input PDFs are still available.
    Never mutates input files.
    """

    if run_state is None:
        return run_state
    if _path_is_previous_preview_export(_norm_path(input_root)):
        return run_state
    planned = tuple(run_state.planned_destinations or ())
    if not planned:
        return run_state
    from invoice_tool.ui_v2.extraction_mapping import (  # noqa: PLC0415
        enrich_planned_destinations_with_local_extraction,
    )

    refreshed = enrich_planned_destinations_with_local_extraction(
        planned,
        input_folder=input_root,
    )
    stamp = datetime.now(timezone.utc).isoformat()
    return replace(
        run_state,
        planned_destinations=refreshed,
        planned_destination_count=len(refreshed),
        state_updated_at=stamp,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _norm_path(path: Path | str | None) -> Path | None:
    raw = str(path or "").strip()
    if not raw:
        return None
    try:
        return Path(raw).expanduser().resolve()
    except OSError:
        return Path(raw).expanduser()


def validate_preview_export_paths(
    input_root: Path | str | None,
    output_root: Path | str | None,
    *,
    productive_mode_requested: bool = False,
    final_write: bool = False,
) -> str | None:
    """Return an error message when preview export paths are unsafe."""

    if productive_mode_requested or final_write:
        return MSG_PREVIEW_EXPORT_BLOCKED_PATH
    input_path = _norm_path(input_root)
    output_path = _norm_path(output_root)
    if input_path is None or output_path is None:
        return MSG_PREVIEW_EXPORT_NEEDS_FOLDERS
    if input_path == output_path:
        return MSG_PREVIEW_EXPORT_SAME_PATH
    # Never use a previous preview-export package as input/source data.
    if _path_is_previous_preview_export(input_path):
        return MSG_PREVIEW_EXPORT_STALE_SOURCE_BLOCKED
    if path_has_forbidden_productive_marker(str(input_path)) or path_has_forbidden_productive_marker(
        str(output_path)
    ):
        return MSG_PREVIEW_EXPORT_BLOCKED_PATH
    if not is_explicit_copied_sandbox_test_path(str(input_path)):
        return MSG_PREVIEW_EXPORT_BLOCKED_PATH
    if not is_explicit_copied_sandbox_test_path(str(output_path)):
        return MSG_PREVIEW_EXPORT_BLOCKED_PATH
    # Output must not be inside input (would look like source mutation / pollution).
    try:
        if output_path == input_path or output_path.is_relative_to(input_path):
            return MSG_PREVIEW_EXPORT_SAME_PATH
    except (OSError, ValueError):
        pass
    return None


def _resolve_source_pdf(input_root: Path, filename: str) -> Path | None:
    safe_name = Path(filename).name
    if not safe_name:
        return None
    direct = input_root / safe_name
    if direct.is_file():
        return direct
    # Case-insensitive fallback within the controlled input root only.
    lowered = safe_name.lower()
    try:
        for candidate in input_root.iterdir():
            if candidate.is_file() and candidate.name.lower() == lowered:
                return candidate
    except OSError:
        return None
    return None


def _planned_for(
    planned: tuple[ProcessingPlannedDestination, ...],
    document_name: str,
) -> ProcessingPlannedDestination | None:
    name = (document_name or "").strip()
    for entry in planned or ():
        if (entry.document_name or "").strip() == name:
            return entry
    return None


def _collect_export_candidates(
    run_state: ProcessingRunState,
    *,
    excluded_keys: frozenset[str],
) -> list[dict[str, Any]]:
    """Collect unique document rows from the real run state only."""

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(
        *,
        source_filename: str,
        category: str,
        status: str,
        review_required: bool,
        document_id: str | None = None,
        excluded: bool = False,
        review_reason: str | None = None,
    ) -> None:
        key = (source_filename or "").strip()
        if not key or key in seen:
            return
        seen.add(key)
        rows.append(
            {
                "source_filename": key,
                "category": category,
                "status": status,
                "review_required": review_required,
                "document_id": document_id,
                "excluded": excluded,
                "review_reason": (review_reason or "").strip() or None,
            }
        )

    for item in run_state.review_items or ():
        assert isinstance(item, ProcessingReviewItem)
        key = review_item_key(item)
        _add(
            source_filename=item.document_name,
            category="review",
            status=item.status_label or "unklar",
            review_required=True,
            document_id=item.document_id,
            excluded=key in excluded_keys,
            review_reason=item.reason,
        )
    for item in run_state.results or ():
        assert isinstance(item, ProcessingResultSummary)
        _add(
            source_filename=item.document_name,
            category="recognized",
            status=item.status_label or item.classification_status or "erkannt",
            review_required=False,
        )
    for item in run_state.error_items or ():
        assert isinstance(item, ProcessingErrorItem)
        _add(
            source_filename=item.document_name,
            category="error",
            status=item.status_label or "fehler",
            review_required=True,
            review_reason=item.message,
        )
    # Planned-only rows that were not already listed.
    for planned in run_state.planned_destinations or ():
        _add(
            source_filename=planned.document_name,
            category="planned",
            status="geplant",
            review_required=True,
            review_reason=planned.reason,
        )
    return rows


def _unique_preview_name(desired: str, used: set[str]) -> str:
    if desired not in used:
        used.add(desired)
        return desired
    stem = Path(desired).stem
    suffix = Path(desired).suffix or ".pdf"
    index = 2
    while True:
        candidate = f"{stem}__{index}{suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def _readme_text(
    *,
    run_id: str,
    export_folder: Path,
    input_root: Path,
    output_root: Path,
    copied_file_count: int,
    review_count: int,
) -> str:
    return "\n".join(
        [
            "# README — Preview Export",
            "",
            "This is a preview/sandbox export.",
            "It is not a final production output.",
            "Original files were not moved/renamed/deleted.",
            "Files in `files/` are preview copies.",
            "Review-required files must be checked manually.",
            "Suggested preview filenames are not final approvals.",
            "Export was generated from controlled test input.",
            "",
            f"- Kind: {PREVIEW_EXPORT_KIND}",
            f"- Run-ID: `{run_id}`",
            f"- Export folder: `{export_folder}`",
            f"- Input root: `{input_root}`",
            f"- Output root: `{output_root}`",
            f"- Copied preview PDFs: {copied_file_count}",
            f"- Review items: {review_count}",
            "",
            "## Naming",
            "",
            f"- `{REVIEW_REQUIRED_PREFIX}<original>` = Prüffall ohne abweichenden Vorschlagsnamen",
            f"- `{REVIEW_REQUIRED_SUGGESTED_PREFIX}<name>` = Prüffall mit sicherem Vorschlagsnamen",
            f"- {MSG_SUGGESTED_PREVIEW_ONLY}",
            f"- {MSG_NAMING_NOT_FINAL}",
            "- Manifest fields: `matched_configuration_name`, "
            "`matched_configuration_pattern`, `filename_pattern`, "
            "`rendered_filename`, `placeholder_values`, `missing_placeholders`, "
            "`amount_format`, `amount_candidates`, `selected_amount`, "
            "`selected_amount_reason`, `payment_field_candidates`, "
            "`selected_payment_field`, `selected_payment_field_reason`, "
            "`document_art_candidates`, `selected_art`, `selected_art_reason`, "
            "`filename_source`, `canonical_filename` (fallback), "
            "`naming_reason`, `naming_confidence`, `suggested_filename`, "
            "`configuration_coverage_status`, `missing_configuration_type`, "
            "`user_guidance`, `suggested_configuration_action`, `guidance_severity`",
            "",
            "## Configuration coverage guidance",
            "",
            "- PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden.",
            "- Kreditkarte erkannt, aber AMEX nicht belegt; keine passende "
            "Nicht-AMEX-Karten-Konfiguration vorhanden.",
            "- Zahlungsfeld nicht sicher erkannt; Konfiguration konnte deshalb "
            "nicht eindeutig gewählt werden.",
            "- Sichere nächste Schritte: "
            + "; ".join(SAFE_NEXT_ACTIONS)
            + ".",
            "- Keine automatische Erstellung/Änderung von Nutzerkonfigurationen.",
            "",
            "## Safety",
            "",
            f"- {MSG_PREVIEW_EXPORT_TITLE}",
            f"- {MSG_PREVIEW_EXPORT_NO_FINAL_FILES}",
            f"- {MSG_PREVIEW_EXPORT_ORIGINALS_UNCHANGED}",
            f"- {MSG_PREVIEW_EXPORT_PRODUCTIVE_LOCKED}",
            f"- {MSG_PREVIEW_EXPORT_NOT_PRODUCTION}",
            f"- {MSG_NO_SAAS_READY}",
            f"- {MSG_NO_PRODUCTION_READY}",
            "",
        ]
    )


def _review_items_md(items: tuple[PreviewExportItem, ...]) -> str:
    lines = [
        "# Review items (Preview Export)",
        "",
        "Diese Dateien sind zur manuellen Prüfung markiert.",
        f"{MSG_NAMING_NOT_FINAL}. {MSG_SUGGESTED_PREVIEW_ONLY}",
        "",
    ]
    review_rows = [item for item in items if item.review_required and not item.excluded]
    if not review_rows:
        lines.append("Keine Review-Items in diesem Preview-Export.")
        lines.append("")
        return "\n".join(lines)
    for item in review_rows:
        lines.append(f"- `{item.source_filename}` → `{item.preview_filename}`")
        lines.append(f"  - {MSG_FIELD_PREVIEW_FILENAME}: `{item.preview_filename}`")
        lines.append(f"  - Warum REVIEW_REQUIRED: {item.naming_reason}")
        if item.review_reason:
            lines.append(f"  - Prüffgrund (Dry-Run): {item.review_reason}")
        if item.suggested_filename:
            lines.append(f"  - Vorgeschlagener Dateiname: `{item.suggested_filename}`")
        else:
            lines.append("  - Vorgeschlagener Dateiname: nicht verfügbar")
        if item.matched_configuration_name:
            lines.append(
                f"  - {MSG_FIELD_CONFIGURATION}: `{item.matched_configuration_name}`"
            )
        if item.matched_configuration_reason:
            lines.append(
                f"  - {MSG_FIELD_MATCHING_REASON}: {item.matched_configuration_reason}"
            )
        if item.condition_results:
            cond_txt = "; ".join(
                str(c.get("reason") or c.get("condition_type") or c)
                for c in item.condition_results
            )
            lines.append(f"  - {MSG_FIELD_CONDITION_RESULTS}: {cond_txt}")
        if item.missing_configuration_rule:
            lines.append(
                f"  - {MSG_FIELD_MISSING_CONFIGURATION_RULE}: "
                f"{item.missing_configuration_rule}"
            )
        if item.available_configurations:
            names = ", ".join(
                str(c.get("configuration_name") or c.get("name") or "?")
                for c in item.available_configurations
            )
            lines.append(f"  - {MSG_FIELD_AVAILABLE_CONFIGURATIONS}: {names}")
        if item.evaluated_configuration_candidates:
            parts = []
            for c in item.evaluated_configuration_candidates:
                status = "matched" if c.get("matched") else "no"
                parts.append(
                    f"{c.get('configuration_name')}: {status} ({c.get('reason') or ''})"
                )
            lines.append(
                f"  - {MSG_FIELD_EVALUATED_CANDIDATES}: " + "; ".join(parts)
            )
        if item.unmatched_reasons:
            lines.append(
                "  - unmatched_reasons: " + " | ".join(item.unmatched_reasons)
            )
        if item.configuration_coverage_status:
            coverage = item.configuration_coverage_status
            if item.missing_configuration_type:
                coverage = f"{coverage} ({item.missing_configuration_type})"
            lines.append(f"  - {MSG_FIELD_CONFIGURATION_COVERAGE}: {coverage}")
        if item.user_guidance:
            lines.append(f"  - {MSG_FIELD_USER_GUIDANCE}: {item.user_guidance}")
        if item.suggested_configuration_action:
            lines.append(
                f"  - {MSG_FIELD_SUGGESTED_CONFIGURATION_ACTION}: "
                f"{item.suggested_configuration_action}"
            )
        if item.user_guidance or item.suggested_configuration_action:
            lines.append(
                "  - Sichere nächste Schritte: " + "; ".join(SAFE_NEXT_ACTIONS)
            )
        if item.rerun_preview_after_rule_change:
            lines.append("  - rerun_preview_after_rule_change: true")
            lines.append(
                "  - previous_matched_configuration: "
                f"`{item.previous_matched_configuration or '—'}`"
            )
            lines.append(
                "  - new_matched_configuration: "
                f"`{item.new_matched_configuration or '—'}`"
            )
            lines.append(
                f"  - rule_applied: {'true' if item.rule_applied else 'false'}"
            )
            if item.applied_configuration_name:
                lines.append(
                    "  - applied_configuration_name: "
                    f"`{item.applied_configuration_name}`"
                )
            if item.applied_configuration_condition:
                lines.append(
                    "  - applied_configuration_condition: "
                    f"`{item.applied_configuration_condition}`"
                )
            lines.append(
                "  - matched_after_rule_change: "
                f"{'true' if item.matched_after_rule_change else 'false'}"
            )
        if item.review_decision:
            lines.append(f"  - review_decision: `{item.review_decision}`")
            lines.append(
                f"  - decision_timestamp: `{item.decision_timestamp or '—'}`"
            )
            lines.append(
                "  - approved_by_user: "
                f"{'true' if item.approved_by_user else 'false'}"
            )
            lines.append(
                "  - finalization_ready: "
                f"{'true' if item.finalization_ready else 'false'}"
            )
            lines.append(
                "  - decision_ready_for_future_finalization: "
                f"{'true' if item.decision_ready_for_future_finalization else 'false'}"
            )
            if item.finalization_blockers:
                lines.append(
                    "  - finalization_blockers: "
                    + ", ".join(item.finalization_blockers)
                )
            if item.approved_preview_filename:
                lines.append(
                    "  - approved_preview_filename: "
                    f"`{item.approved_preview_filename}`"
                )
            if item.target_preview_path:
                lines.append(
                    f"  - target_preview_path: `{item.target_preview_path}`"
                )
            if item.user_edited_fields:
                edited = ", ".join(
                    f"{key}={value}" for key, value in item.user_edited_fields
                )
                lines.append(f"  - user_edited_fields: {edited}")
            lines.append("  - final_write_allowed: false")
        if item.matched_configuration_pattern or item.filename_pattern:
            lines.append(
                f"  - {MSG_FIELD_FILENAME_PATTERN}: `"
                f"{item.matched_configuration_pattern or item.filename_pattern}`"
            )
        if item.rendered_filename:
            lines.append(
                f"  - rendered_filename: `{item.rendered_filename}`"
            )
        if item.placeholder_values:
            rendered_vals = ", ".join(
                f"{key}={value if value is not None else '—'}"
                for key, value in item.placeholder_values
            )
            lines.append(f"  - {MSG_FIELD_PLACEHOLDER_VALUES}: `{rendered_vals}`")
        if item.missing_placeholders:
            lines.append(
                f"  - {MSG_FIELD_MISSING_PLACEHOLDERS}: `"
                + ", ".join(item.missing_placeholders)
                + "`"
            )
            lines.append(
                "  - Hinweis: Fehlende Platzhalter wurden nicht stillschweigend entfernt."
            )
        if item.amount_format:
            lines.append(f"  - {MSG_FIELD_AMOUNT_FORMAT}: `{item.amount_format}`")
        if item.selected_amount or item.amount:
            lines.append(
                f"  - {MSG_FIELD_AMOUNT}: `{item.selected_amount or item.amount}`"
            )
        if item.selected_amount_reason:
            lines.append(
                f"  - {MSG_FIELD_AMOUNT_REASON}: {item.selected_amount_reason}"
            )
        if item.selected_payment_field is not None or item.payment_account:
            lines.append(
                f"  - {MSG_FIELD_PAYMENT_FIELD}: `"
                f"{item.selected_payment_field or item.payment_account or '—'}`"
            )
        elif item.selected_payment_field_reason:
            lines.append(f"  - {MSG_FIELD_PAYMENT_FIELD}: `—`")
        if item.selected_payment_field_reason:
            lines.append(
                f"  - {MSG_FIELD_PAYMENT_FIELD_REASON}: "
                f"{item.selected_payment_field_reason}"
            )
        if item.selected_art or item.document_type:
            lines.append(
                f"  - {MSG_FIELD_DOCUMENT_ART}: `"
                f"{item.selected_art or item.document_type}`"
            )
        if item.selected_art_reason:
            lines.append(f"  - {MSG_FIELD_ART_REASON}: {item.selected_art_reason}")
        if item.canonical_filename:
            lines.append(f"  - canonical_filename (Fallback): `{item.canonical_filename}`")
        if item.filename_template_version:
            lines.append(
                f"  - filename_template_version: `{item.filename_template_version}`"
            )
        direction = item.document_direction or "Unklare_Rechnungsart"
        lines.append(f"  - {MSG_FIELD_DOCUMENT_DIRECTION}: `{direction}`")
        if direction == "Unklare_Rechnungsart":
            lines.append("  - Hinweis: Rechnungsart unklar — nicht stillschweigend weggelassen.")
        category_display = (
            item.business_category_display
            or item.business_category
            or "Unklare_Zuordnung"
        )
        lines.append(f"  - {MSG_FIELD_BUSINESS_CATEGORY}: `{category_display}`")
        if (item.business_category or "Unklare_Zuordnung") == "Unklare_Zuordnung":
            lines.append(
                "  - Hinweis: Zuordnung unklar — kein Blind-Default auf Architektur."
            )
        name = item.counterparty_name or item.supplier
        if name:
            lines.append(f"  - {MSG_FIELD_COUNTERPARTY_NAME}: `{name}`")
        if item.invoice_date:
            lines.append(f"  - invoice_date: `{item.invoice_date}`")
        if item.missing_fields:
            lines.append(
                "  - fehlende Felder: `"
                + ", ".join(item.missing_fields)
                + "`"
            )
        if item.naming_confidence:
            lines.append(f"  - naming_confidence: `{item.naming_confidence}`")
        if item.supplier:
            lines.append(f"  - supplier: `{item.supplier}`")
        if item.document_type:
            lines.append(f"  - document_type: `{item.document_type}`")
        if item.payment_account:
            lines.append(f"  - payment_account: `{item.payment_account}`")
        if item.planned_target:
            lines.append(f"  - {MSG_FIELD_PLANNED_TARGET} (Vorschau): `{item.planned_target}`")
        else:
            lines.append(f"  - {MSG_FIELD_PLANNED_TARGET}: nicht verfügbar")
        lines.append(f"  - Namensquelle (`filename_source`): `{item.filename_source}`")
        lines.append(f"  - Status: {item.status}")
        lines.append(f"  - {MSG_NAMING_NOT_FINAL}")
    lines.append("")
    return "\n".join(lines)


def _manifest_csv(items: tuple[PreviewExportItem, ...]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "source_filename",
            "preview_filename",
            "status",
            "category",
            "planned_target",
            "suggested_filename",
            "rendered_filename",
            "matched_configuration_name",
            "matched_configuration_id",
            "matched_configuration_pattern",
            "matched_configuration_reason",
            "available_configurations",
            "missing_configuration_rule",
            "configuration_coverage_status",
            "missing_configuration_type",
            "user_guidance",
            "suggested_configuration_action",
            "guidance_severity",
            "rule_applied",
            "applied_configuration_name",
            "applied_configuration_condition",
            "rerun_preview_after_rule_change",
            "matched_after_rule_change",
            "previous_matched_configuration",
            "new_matched_configuration",
            "filename_pattern",
            "placeholder_values",
            "missing_placeholders",
            "amount_format",
            "canonical_filename",
            "filename_template_version",
            "document_direction",
            "business_category",
            "counterparty_name",
            "filename_source",
            "naming_reason",
            "naming_confidence",
            "supplier",
            "invoice_date",
            "amount",
            "selected_amount",
            "selected_amount_reason",
            "selected_payment_field",
            "selected_payment_field_reason",
            "selected_art",
            "selected_art_reason",
            "missing_fields",
            "document_type",
            "payment_account",
            "review_required",
            "source_sha256",
            "preview_sha256",
            "excluded",
            "review_decision",
            "decision_timestamp",
            "approved_by_user",
            "finalization_ready",
            "decision_ready_for_future_finalization",
            "finalization_blockers",
            "approved_preview_filename",
            "target_preview_path",
            "user_edited_fields",
            "warnings_acknowledged",
            "source_hash_at_decision",
            "preview_state_id",
            "final_write_allowed",
            "finalization_status",
            "finalization_warnings",
            "target_conflict_status",
        ]
    )
    for item in items:
        placeholder_text = "|".join(
            f"{key}={value if value is not None else ''}"
            for key, value in (item.placeholder_values or ())
        )
        edited_text = "|".join(
            f"{key}={value}" for key, value in (item.user_edited_fields or ())
        )
        writer.writerow(
            [
                item.source_filename,
                item.preview_filename,
                item.status,
                item.category,
                item.planned_target or "",
                item.suggested_filename or "",
                item.rendered_filename or "",
                item.matched_configuration_name or "",
                item.matched_configuration_id or "",
                item.matched_configuration_pattern or "",
                item.matched_configuration_reason or "",
                "|".join(
                    str(c.get("configuration_name") or "")
                    for c in (item.available_configurations or ())
                ),
                item.missing_configuration_rule or "",
                item.configuration_coverage_status or "",
                item.missing_configuration_type or "",
                item.user_guidance or "",
                item.suggested_configuration_action or "",
                item.guidance_severity or "",
                "true" if item.rule_applied else "false",
                item.applied_configuration_name or "",
                item.applied_configuration_condition or "",
                "true" if item.rerun_preview_after_rule_change else "false",
                "true" if item.matched_after_rule_change else "false",
                item.previous_matched_configuration or "",
                item.new_matched_configuration or "",
                item.filename_pattern or "",
                placeholder_text,
                "|".join(item.missing_placeholders or ()),
                item.amount_format or "",
                item.canonical_filename or "",
                item.filename_template_version or "",
                item.document_direction or "",
                item.business_category or "",
                item.counterparty_name or "",
                item.filename_source,
                item.naming_reason,
                item.naming_confidence or "",
                item.supplier or "",
                item.invoice_date or "",
                item.amount or "",
                item.selected_amount or item.amount or "",
                item.selected_amount_reason or "",
                item.selected_payment_field or "",
                item.selected_payment_field_reason or "",
                item.selected_art or "",
                item.selected_art_reason or "",
                "|".join(item.missing_fields or ()),
                item.document_type or "",
                item.payment_account or "",
                "yes" if item.review_required else "no",
                item.source_sha256,
                item.preview_sha256,
                "yes" if item.excluded else "no",
                item.review_decision or "",
                item.decision_timestamp or "",
                "true" if item.approved_by_user else "false",
                "true" if item.finalization_ready else "false",
                "true" if item.decision_ready_for_future_finalization else "false",
                "|".join(item.finalization_blockers or ()),
                item.approved_preview_filename or "",
                item.target_preview_path or "",
                edited_text,
                "|".join(item.warnings_acknowledged or ()),
                item.source_hash_at_decision or "",
                item.preview_state_id or "",
                "false",
                item.finalization_status or "",
                "|".join(item.finalization_warnings or ()),
                item.target_conflict_status or "",
            ]
        )
    return buffer.getvalue()


def _manifest_payload(
    *,
    run_id: str,
    generated_at: str,
    input_root: Path,
    output_root: Path,
    export_folder: Path,
    items: tuple[PreviewExportItem, ...],
    recognized_count: int,
    review_count: int,
    error_count: int,
    planned_count: int,
    state_source: str = STATE_SOURCE_CURRENT_PROCESSING_RUN,
    source_state_updated_at: str | None = None,
    state_freshness_checked: bool = True,
    state_freshness_result: str = "pass",
    finalization_preview_batch: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    copied = [item for item in items if not item.excluded]
    batch_payload = dict(finalization_preview_batch or {})
    return {
        "kind": PREVIEW_EXPORT_KIND,
        "schema_version": PREVIEW_EXPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "source_run_id": run_id,
        "generated_at": generated_at,
        "export_created_at": generated_at,
        "state_source": state_source,
        "exported_from_current_state": True,
        "previous_export_reused": False,
        "source_state_updated_at": source_state_updated_at,
        "state_freshness_checked": bool(state_freshness_checked),
        "state_freshness_result": state_freshness_result,
        "input_root": str(input_root),
        "output_root": str(output_root),
        "export_folder": str(export_folder),
        "item_count": len(items),
        "copied_file_count": len(copied),
        "recognized_count": recognized_count,
        "review_count": review_count,
        "error_count": error_count,
        "planned_count": planned_count,
        "preview_export": True,
        "dry_run": True,
        "final_write": False,
        "productive_mode_requested": False,
        "source_mutation": False,
        "claims_saas_ready": False,
        "claims_production_ready": False,
        "disclaimer": MSG_PREVIEW_EXPORT_SANDBOX_ONLY,
        "naming_disclaimer": MSG_SUGGESTED_PREVIEW_ONLY,
        "final_write_allowed": False,
        "finalization_preview_batch": batch_payload.get("finalization_preview_batch")
        if "finalization_preview_batch" in batch_payload
        else batch_payload or None,
        "ready_count": int(batch_payload.get("ready_count") or 0),
        "blocked_count": int(batch_payload.get("blocked_count") or 0),
        "ignored_count": int(batch_payload.get("ignored_count") or 0),
        "deferred_count": int(batch_payload.get("deferred_count") or 0),
        "still_review_required_count": int(
            batch_payload.get("still_review_required_count") or 0
        ),
        "conflicts": list(batch_payload.get("conflicts") or []),
        "safety_summary": batch_payload.get("safety_summary")
        or "Finalisierungs-Vorschau only — final_write_allowed=false",
        "items": [
            {
                "source_filename": item.source_filename,
                "preview_filename": item.preview_filename,
                "status": item.status,
                "category": item.category,
                "planned_target": item.planned_target,
                "suggested_filename": item.suggested_filename,
                "rendered_filename": item.rendered_filename,
                "matched_configuration_name": item.matched_configuration_name,
                "matched_configuration_id": item.matched_configuration_id,
                "matched_configuration_pattern": item.matched_configuration_pattern,
                "matched_configuration_reason": item.matched_configuration_reason,
                "matched_configuration_confidence": (
                    item.matched_configuration_confidence
                ),
                "available_configurations": list(item.available_configurations or ()),
                "evaluated_configuration_candidates": list(
                    item.evaluated_configuration_candidates or ()
                ),
                "unmatched_reasons": list(item.unmatched_reasons or ()),
                "condition_results": list(item.condition_results or ()),
                "alternative_matches": list(item.alternative_matches or ()),
                "missing_configuration_rule": item.missing_configuration_rule,
                "configuration_coverage_status": item.configuration_coverage_status,
                "missing_configuration_type": item.missing_configuration_type,
                "user_guidance": item.user_guidance,
                "suggested_configuration_action": item.suggested_configuration_action,
                "guidance_severity": item.guidance_severity,
                "rule_applied": bool(item.rule_applied),
                "applied_configuration_name": item.applied_configuration_name,
                "applied_configuration_condition": item.applied_configuration_condition,
                "rerun_preview_after_rule_change": bool(
                    item.rerun_preview_after_rule_change
                ),
                "matched_after_rule_change": bool(item.matched_after_rule_change),
                "previous_matched_configuration": item.previous_matched_configuration,
                "new_matched_configuration": item.new_matched_configuration,
                "filename_pattern": item.filename_pattern,
                "placeholder_values": {
                    key: value for key, value in (item.placeholder_values or ())
                },
                "missing_placeholders": list(item.missing_placeholders or ()),
                "amount_format": item.amount_format,
                "amount_candidates": list(item.amount_candidates or ()),
                "selected_amount": item.selected_amount or item.amount,
                "selected_amount_reason": item.selected_amount_reason,
                "rejected_amount_candidates": list(
                    item.rejected_amount_candidates or ()
                ),
                "payment_field_candidates": list(item.payment_field_candidates or ()),
                "selected_payment_field": item.selected_payment_field,
                "selected_payment_field_reason": item.selected_payment_field_reason,
                "document_art_candidates": list(item.document_art_candidates or ()),
                "selected_art": item.selected_art,
                "selected_art_reason": item.selected_art_reason,
                "art_ambiguity": bool(item.art_ambiguity),
                "canonical_filename": item.canonical_filename,
                "filename_template_version": item.filename_template_version,
                "document_direction": item.document_direction,
                "business_category": item.business_category,
                "business_category_display": item.business_category_display,
                "counterparty_name": item.counterparty_name,
                "missing_fields": list(item.missing_fields or ()),
                "filename_source": item.filename_source,
                "naming_reason": item.naming_reason,
                "naming_confidence": item.naming_confidence,
                "supplier": item.supplier,
                "invoice_date": item.invoice_date,
                "amount": item.amount,
                "document_type": item.document_type,
                "payment_account": item.payment_account,
                "suggested_filename_fields": list(item.suggested_filename_fields or ()),
                "review_reason": item.review_reason,
                "review_required": item.review_required,
                "source_sha256": item.source_sha256,
                "preview_sha256": item.preview_sha256,
                "excluded": item.excluded,
                "review_decision": item.review_decision,
                "decision_timestamp": item.decision_timestamp,
                "approved_by_user": bool(item.approved_by_user),
                "finalization_ready": bool(item.finalization_ready),
                "decision_ready_for_future_finalization": bool(
                    item.decision_ready_for_future_finalization
                ),
                "finalization_blockers": list(item.finalization_blockers or ()),
                "approved_preview_filename": item.approved_preview_filename,
                "target_preview_path": item.target_preview_path,
                "user_edited_fields": {
                    key: value for key, value in (item.user_edited_fields or ())
                },
                "warnings_acknowledged": list(item.warnings_acknowledged or ()),
                "source_hash_at_decision": item.source_hash_at_decision,
                "preview_state_id": item.preview_state_id,
                "final_write_allowed": False,
                "finalization_status": item.finalization_status,
                "finalization_warnings": list(item.finalization_warnings or ()),
                "target_conflict_status": item.target_conflict_status,
            }
            for item in items
        ],
    }


def _cleanup_export_folder(export_folder: Path | None) -> None:
    if export_folder is None:
        return
    try:
        if export_folder.is_dir() and export_folder.name.startswith(PREVIEW_EXPORT_FOLDER_PREFIX):
            shutil.rmtree(export_folder)
    except OSError:
        pass


def _decision_fields_for_source(
    decision_fields_by_key: Mapping[str, Mapping[str, Any]] | None,
    *,
    source_filename: str,
    item_key: str | None = None,
) -> dict[str, Any]:
    """Lookup Prompt-29 decision/readiness fields for a source row."""

    mapping = decision_fields_by_key or {}
    payload: Mapping[str, Any] | None = None
    if item_key and item_key in mapping:
        payload = mapping[item_key]
    elif source_filename in mapping:
        payload = mapping[source_filename]
    else:
        for key, value in mapping.items():
            if str(value.get("source_filename") or "") == source_filename:
                payload = value
                break
    if not payload:
        return {
            "review_decision": None,
            "decision_timestamp": None,
            "approved_by_user": False,
            "finalization_ready": False,
            "decision_ready_for_future_finalization": False,
            "finalization_blockers": (),
            "approved_preview_filename": None,
            "target_preview_path": None,
            "user_edited_fields": (),
            "warnings_acknowledged": (),
            "source_hash_at_decision": None,
            "preview_state_id": None,
            "final_write_allowed": False,
            "finalization_status": None,
            "finalization_warnings": (),
            "target_conflict_status": None,
        }
    edited = payload.get("user_edited_fields") or payload.get("edited_fields") or {}
    if isinstance(edited, Mapping):
        edited_fields = tuple((str(k), str(v)) for k, v in edited.items())
    else:
        edited_fields = tuple((str(k), str(v)) for k, v in (edited or ()))
    blockers = payload.get("finalization_blockers") or ()
    warnings = payload.get("warnings_acknowledged") or ()
    fin_warnings = payload.get("finalization_warnings") or ()
    return {
        "review_decision": payload.get("review_decision")
        or payload.get("decision_type"),
        "decision_timestamp": payload.get("decision_timestamp"),
        "approved_by_user": bool(payload.get("approved_by_user")),
        "finalization_ready": bool(payload.get("finalization_ready")),
        "decision_ready_for_future_finalization": bool(
            payload.get("decision_ready_for_future_finalization")
            or payload.get("finalization_ready")
        ),
        "finalization_blockers": tuple(str(b) for b in blockers),
        "approved_preview_filename": payload.get("approved_preview_filename"),
        "target_preview_path": payload.get("target_preview_path")
        or payload.get("approved_target_preview_path"),
        "user_edited_fields": edited_fields,
        "warnings_acknowledged": tuple(str(w) for w in warnings),
        "source_hash_at_decision": payload.get("source_hash_at_decision"),
        "preview_state_id": payload.get("preview_state_id"),
        "final_write_allowed": False,
        "finalization_status": payload.get("finalization_status"),
        "finalization_warnings": tuple(str(w) for w in fin_warnings),
        "target_conflict_status": payload.get("target_conflict_status"),
    }


def _with_decision_fields(
    item: PreviewExportItem,
    decision_fields_by_key: Mapping[str, Mapping[str, Any]] | None,
    *,
    item_key: str | None = None,
) -> PreviewExportItem:
    fields = _decision_fields_for_source(
        decision_fields_by_key,
        source_filename=item.source_filename,
        item_key=item_key,
    )
    return replace(item, **fields)


def write_preview_export_package(
    run_state: ProcessingRunState | None,
    *,
    input_root: Path | str,
    output_root: Path | str,
    excluded_keys: frozenset[str] | set[str] | None = None,
    productive_mode_requested: bool = False,
    dry_run: bool = True,
    preview_export: bool = True,
    final_write: bool = False,
    review_expectations: tuple[ReviewExportExpectation, ...]
    | list[ReviewExportExpectation]
    | None = None,
    refresh_from_input: bool = False,
    decision_fields_by_key: Mapping[str, Mapping[str, Any]] | None = None,
    finalization_preview_batch: Mapping[str, Any] | None = None,
) -> PreviewExportResult:
    """Create a dedicated preview-export-* package under controlled output."""

    if not preview_export or not dry_run or final_write or productive_mode_requested:
        return PreviewExportResult(
            ok=False,
            status="blocked",
            error=MSG_PREVIEW_EXPORT_BLOCKED_PATH,
            productive_mode_requested=productive_mode_requested,
            dry_run=dry_run,
            preview_export=preview_export,
            final_write=final_write,
        )
    if not preview_export_available(run_state):
        return PreviewExportResult(
            ok=False,
            status="no_run",
            error=MSG_PREVIEW_EXPORT_NEEDS_COMPLETED_RUN,
        )

    assert run_state is not None
    path_error = validate_preview_export_paths(
        input_root,
        output_root,
        productive_mode_requested=productive_mode_requested,
        final_write=final_write,
    )
    if path_error:
        return PreviewExportResult(ok=False, status="blocked", error=path_error)

    input_path = _norm_path(input_root)
    output_path = _norm_path(output_root)
    assert input_path is not None and output_path is not None
    if not input_path.is_dir():
        return PreviewExportResult(
            ok=False,
            status="blocked",
            error=MSG_PREVIEW_EXPORT_NEEDS_FOLDERS,
        )
    if refresh_from_input:
        run_state = refresh_run_state_from_current_sandbox_input(
            run_state,
            input_root=input_path,
        )
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return PreviewExportResult(
            ok=False,
            status="failed",
            error=f"Ausgabeordner nicht nutzbar: {exc}",
        )

    excluded = frozenset(excluded_keys or ())
    candidates = _collect_export_candidates(run_state, excluded_keys=excluded)
    if not candidates:
        return PreviewExportResult(
            ok=False,
            status="empty",
            error=MSG_PREVIEW_EXPORT_NO_SOURCE,
            recognized_count=run_state.recognized_count,
            review_count=run_state.review_count,
            error_count=run_state.error_count,
            planned_count=run_state.planned_destination_count,
        )

    # Resolve sources before creating the package folder (no partial package).
    resolved: list[tuple[dict[str, Any], Path | None, ProcessingPlannedDestination | None]] = []
    for row in candidates:
        if row["excluded"]:
            resolved.append((row, None, _planned_for(run_state.planned_destinations, row["source_filename"])))
            continue
        source = _resolve_source_pdf(input_path, row["source_filename"])
        if source is None:
            return PreviewExportResult(
                ok=False,
                status="blocked",
                error=f"{MSG_PREVIEW_EXPORT_NO_SOURCE} ({row['source_filename']})",
            )
        # Source must remain under controlled input root.
        try:
            if not source.resolve().is_relative_to(input_path):
                return PreviewExportResult(
                    ok=False,
                    status="blocked",
                    error=MSG_PREVIEW_EXPORT_BLOCKED_PATH,
                )
        except (OSError, ValueError):
            return PreviewExportResult(
                ok=False,
                status="blocked",
                error=MSG_PREVIEW_EXPORT_BLOCKED_PATH,
            )
        resolved.append(
            (
                row,
                source,
                _planned_for(run_state.planned_destinations, row["source_filename"]),
            )
        )

    # Pre-resolve naming + freshness guard before any package write.
    used_names: set[str] = set()
    naming_resolved: list[
        tuple[dict[str, Any], Path | None, ProcessingPlannedDestination | None, PreviewNamingDecision, str]
    ] = []
    freshness_rows: list[dict[str, Any]] = []
    for row, source, planned in resolved:
        naming = resolve_preview_naming(
            source_filename=row["source_filename"],
            review_required=bool(row["review_required"]),
            planned=planned,
            suggested_filename=(
                planned.suggested_filename
                if planned is not None
                else None
            )
            or (planned.rendered_filename if planned is not None else None)
            or (planned.canonical_filename if planned is not None else None),
        )
        preview_name = _unique_preview_name(naming.preview_filename, used_names)
        naming_resolved.append((row, source, planned, naming, preview_name))
        freshness_rows.append(
            {
                "source_filename": row["source_filename"],
                "preview_filename": preview_name,
                "rendered_filename": naming.rendered_filename,
                "selected_amount": naming.selected_amount or naming.amount,
                "selected_payment_field": naming.selected_payment_field
                or naming.payment_account,
                "selected_art": naming.selected_art,
                "suggested_filename": naming.suggested_filename,
            }
        )
    expectations = (
        tuple(review_expectations)
        if review_expectations is not None
        else build_review_ui_export_expectations(run_state)
    )
    freshness_error = validate_export_state_freshness(
        export_rows=freshness_rows,
        expectations=expectations,
    )
    if freshness_error:
        return PreviewExportResult(
            ok=False,
            status="blocked",
            error=freshness_error,
            recognized_count=run_state.recognized_count,
            review_count=run_state.review_count,
            error_count=run_state.error_count,
            planned_count=run_state.planned_destination_count,
        )

    run_id = (run_state.run_id or "sandbox-run").strip() or "sandbox-run"
    safe_run_id = re.sub(r"[^\w.\-]+", "_", run_id)[:80] or "sandbox-run"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    export_folder = output_path / f"{PREVIEW_EXPORT_FOLDER_PREFIX}{safe_run_id}-{stamp}"
    files_dir = export_folder / FILES_SUBDIR

    # Ensure new folder stays under controlled output.
    try:
        if not export_folder.resolve().is_relative_to(output_path):
            return PreviewExportResult(
                ok=False,
                status="blocked",
                error=MSG_PREVIEW_EXPORT_BLOCKED_PATH,
            )
    except (OSError, ValueError):
        return PreviewExportResult(
            ok=False,
            status="blocked",
            error=MSG_PREVIEW_EXPORT_BLOCKED_PATH,
        )

    written: list[str] = []
    items: list[PreviewExportItem] = []
    generated_at = datetime.now(timezone.utc).isoformat()
    source_state_updated_at = _norm_text(run_state.state_updated_at) or generated_at

    try:
        export_folder.mkdir(parents=False, exist_ok=False)
        files_dir.mkdir(parents=False, exist_ok=False)

        for row, source, planned, naming, preview_name in naming_resolved:
            review_reason = row.get("review_reason")

            if row["excluded"] or source is None:
                items.append(
                    PreviewExportItem(
                        source_filename=row["source_filename"],
                        preview_filename=preview_name,
                        status=row["status"],
                        category=row["category"],
                        planned_target=naming.planned_target,
                        review_required=bool(row["review_required"]),
                        source_sha256="",
                        preview_sha256="",
                        source_path="",
                        preview_path="",
                        excluded=True,
                        suggested_filename=naming.suggested_filename,
                        filename_source=naming.filename_source,
                        naming_reason=naming.naming_reason,
                        review_reason=review_reason,
                        naming_confidence=naming.naming_confidence,
                        supplier=naming.supplier,
                        invoice_date=naming.invoice_date,
                        amount=naming.amount,
                        document_type=naming.document_type,
                        payment_account=naming.payment_account,
                        suggested_filename_fields=naming.suggested_filename_fields,
                        canonical_filename=naming.canonical_filename,
                        filename_template_version=naming.filename_template_version,
                        document_direction=naming.document_direction,
                        business_category=naming.business_category,
                        business_category_display=naming.business_category_display,
                        counterparty_name=naming.counterparty_name,
                        missing_fields=naming.missing_fields,
                        matched_configuration_name=naming.matched_configuration_name,
                        matched_configuration_id=naming.matched_configuration_id,
                        matched_configuration_pattern=naming.matched_configuration_pattern,
                        matched_configuration_reason=naming.matched_configuration_reason,
                        matched_configuration_confidence=(
                            naming.matched_configuration_confidence
                        ),
                        filename_pattern=naming.filename_pattern,
                        rendered_filename=naming.rendered_filename,
                        placeholder_values=naming.placeholder_values,
                        missing_placeholders=naming.missing_placeholders,
                        amount_format=naming.amount_format,
                        amount_candidates=naming.amount_candidates,
                        selected_amount=naming.selected_amount,
                        selected_amount_reason=naming.selected_amount_reason,
                        rejected_amount_candidates=naming.rejected_amount_candidates,
                        payment_field_candidates=naming.payment_field_candidates,
                        selected_payment_field=naming.selected_payment_field,
                        selected_payment_field_reason=(
                            naming.selected_payment_field_reason
                        ),
                        document_art_candidates=naming.document_art_candidates,
                        selected_art=naming.selected_art,
                        selected_art_reason=naming.selected_art_reason,
                        art_ambiguity=naming.art_ambiguity,
                        available_configurations=naming.available_configurations,
                        evaluated_configuration_candidates=(
                            naming.evaluated_configuration_candidates
                        ),
                        unmatched_reasons=naming.unmatched_reasons,
                        condition_results=naming.condition_results,
                        alternative_matches=naming.alternative_matches,
                        missing_configuration_rule=naming.missing_configuration_rule,
                        configuration_coverage_status=(
                            naming.configuration_coverage_status
                        ),
                        missing_configuration_type=naming.missing_configuration_type,
                        user_guidance=naming.user_guidance,
                        suggested_configuration_action=(
                            naming.suggested_configuration_action
                        ),
                        guidance_severity=naming.guidance_severity,
                        rule_applied=bool(naming.rule_applied),
                        applied_configuration_name=naming.applied_configuration_name,
                        applied_configuration_condition=(
                            naming.applied_configuration_condition
                        ),
                        rerun_preview_after_rule_change=bool(
                            naming.rerun_preview_after_rule_change
                        ),
                        matched_after_rule_change=bool(
                            naming.matched_after_rule_change
                        ),
                        previous_matched_configuration=(
                            naming.previous_matched_configuration
                        ),
                        new_matched_configuration=naming.new_matched_configuration,
                    )
                )
                continue

            source_sha = sha256_file(source)
            target = files_dir / preview_name
            # Final containment check before copy.
            if not target.resolve().is_relative_to(files_dir.resolve()):
                raise RuntimeError(MSG_PREVIEW_EXPORT_BLOCKED_PATH)
            shutil.copy2(source, target)
            preview_sha = sha256_file(target)
            if preview_sha != source_sha:
                raise RuntimeError("Preview-Kopie ist nicht byte-identisch zur Quelle.")
            written.append(str(target))
            items.append(
                PreviewExportItem(
                    source_filename=row["source_filename"],
                    preview_filename=preview_name,
                    status=row["status"],
                    category=row["category"],
                    planned_target=naming.planned_target,
                    review_required=bool(row["review_required"]),
                    source_sha256=source_sha,
                    preview_sha256=preview_sha,
                    source_path=str(source),
                    preview_path=str(target),
                    excluded=False,
                    suggested_filename=naming.suggested_filename,
                    filename_source=naming.filename_source,
                    naming_reason=naming.naming_reason,
                    review_reason=review_reason,
                    naming_confidence=naming.naming_confidence,
                    supplier=naming.supplier,
                    invoice_date=naming.invoice_date,
                    amount=naming.amount,
                    document_type=naming.document_type,
                    payment_account=naming.payment_account,
                    suggested_filename_fields=naming.suggested_filename_fields,
                    canonical_filename=naming.canonical_filename,
                    filename_template_version=naming.filename_template_version,
                    document_direction=naming.document_direction,
                    business_category=naming.business_category,
                    business_category_display=naming.business_category_display,
                    counterparty_name=naming.counterparty_name,
                    missing_fields=naming.missing_fields,
                    matched_configuration_name=naming.matched_configuration_name,
                    matched_configuration_id=naming.matched_configuration_id,
                    matched_configuration_pattern=naming.matched_configuration_pattern,
                    matched_configuration_reason=naming.matched_configuration_reason,
                    matched_configuration_confidence=(
                        naming.matched_configuration_confidence
                    ),
                    filename_pattern=naming.filename_pattern,
                    rendered_filename=naming.rendered_filename,
                    placeholder_values=naming.placeholder_values,
                    missing_placeholders=naming.missing_placeholders,
                    amount_format=naming.amount_format,
                    amount_candidates=naming.amount_candidates,
                    selected_amount=naming.selected_amount,
                    selected_amount_reason=naming.selected_amount_reason,
                    rejected_amount_candidates=naming.rejected_amount_candidates,
                    payment_field_candidates=naming.payment_field_candidates,
                    selected_payment_field=naming.selected_payment_field,
                    selected_payment_field_reason=(
                        naming.selected_payment_field_reason
                    ),
                    document_art_candidates=naming.document_art_candidates,
                    selected_art=naming.selected_art,
                    selected_art_reason=naming.selected_art_reason,
                    art_ambiguity=naming.art_ambiguity,
                    available_configurations=naming.available_configurations,
                    evaluated_configuration_candidates=(
                        naming.evaluated_configuration_candidates
                    ),
                    unmatched_reasons=naming.unmatched_reasons,
                    condition_results=naming.condition_results,
                    alternative_matches=naming.alternative_matches,
                    missing_configuration_rule=naming.missing_configuration_rule,
                    configuration_coverage_status=naming.configuration_coverage_status,
                    missing_configuration_type=naming.missing_configuration_type,
                    user_guidance=naming.user_guidance,
                    suggested_configuration_action=(
                        naming.suggested_configuration_action
                    ),
                    guidance_severity=naming.guidance_severity,
                    rule_applied=bool(naming.rule_applied),
                    applied_configuration_name=naming.applied_configuration_name,
                    applied_configuration_condition=(
                        naming.applied_configuration_condition
                    ),
                    rerun_preview_after_rule_change=bool(
                        naming.rerun_preview_after_rule_change
                    ),
                    matched_after_rule_change=bool(
                        naming.matched_after_rule_change
                    ),
                    previous_matched_configuration=(
                        naming.previous_matched_configuration
                    ),
                    new_matched_configuration=naming.new_matched_configuration,
                )
            )

        enriched_items: list[PreviewExportItem] = []
        key_by_source = {
            (item.document_name or "").strip(): review_item_key(item)
            for item in (run_state.review_items or ())
        }
        for item in items:
            enriched_items.append(
                _with_decision_fields(
                    item,
                    decision_fields_by_key,
                    item_key=key_by_source.get(item.source_filename),
                )
            )
        items = enriched_items

        item_tuple = tuple(items)
        copied_count = sum(1 for item in item_tuple if not item.excluded)
        payload = _manifest_payload(
            run_id=run_id,
            generated_at=generated_at,
            input_root=input_path,
            output_root=output_path,
            export_folder=export_folder,
            items=item_tuple,
            recognized_count=run_state.recognized_count,
            review_count=run_state.review_count,
            error_count=run_state.error_count,
            planned_count=run_state.planned_destination_count,
            state_source=STATE_SOURCE_CURRENT_PROCESSING_RUN,
            source_state_updated_at=source_state_updated_at,
            state_freshness_checked=True,
            state_freshness_result="pass",
            finalization_preview_batch=finalization_preview_batch,
        )
        readme_path = export_folder / "README_PREVIEW_EXPORT.md"
        manifest_json = export_folder / "manifest.json"
        manifest_csv = export_folder / "manifest.csv"
        review_md = export_folder / "review-items.md"

        readme_path.write_text(
            _readme_text(
                run_id=run_id,
                export_folder=export_folder,
                input_root=input_path,
                output_root=output_path,
                copied_file_count=copied_count,
                review_count=run_state.review_count,
            ),
            encoding="utf-8",
        )
        written.append(str(readme_path))
        manifest_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(str(manifest_json))
        manifest_csv.write_text(_manifest_csv(item_tuple), encoding="utf-8")
        written.append(str(manifest_csv))
        if run_state.review_count > 0:
            review_md.write_text(_review_items_md(item_tuple), encoding="utf-8")
            written.append(str(review_md))

        # Absolute containment: every written file under output_root.
        for path_str in written:
            written_path = Path(path_str).resolve()
            if not written_path.is_relative_to(output_path):
                raise RuntimeError(MSG_PREVIEW_EXPORT_BLOCKED_PATH)

        return PreviewExportResult(
            ok=True,
            status="exported",
            export_folder=export_folder,
            copied_file_count=copied_count,
            item_count=len(item_tuple),
            recognized_count=run_state.recognized_count,
            review_count=run_state.review_count,
            error_count=run_state.error_count,
            planned_count=run_state.planned_destination_count,
            written_files=tuple(written),
            items=item_tuple,
            productive_mode_requested=False,
            dry_run=True,
            preview_export=True,
            final_write=False,
            source_mutation=False,
            claims_saas_ready=False,
            claims_production_ready=False,
        )
    except Exception as exc:  # noqa: BLE001 — convert to blocker, cleanup package
        _cleanup_export_folder(export_folder if export_folder.exists() else None)
        return PreviewExportResult(
            ok=False,
            status="blocked",
            error=f"{MSG_PREVIEW_EXPORT_PARTIAL_BLOCKED} ({exc})",
        )


def apply_workspace_preview_export(state: Any) -> PreviewExportResult:
    """UI-v2 helper: write preview-export package from workspace folder overrides.

    Refreshes planned destinations from the current sandbox input with the same
    enrichment path that feeds the Review UI, then exports that current state.
    Never reads previous preview-export folders as a data source.
    """

    run_state = getattr(state, "processing_run_state", None)
    input_root = (getattr(state, "workspace_input_folder_override", None) or "").strip()
    output_root = (getattr(state, "workspace_output_folder_override", None) or "").strip()
    bag = get_review_preview_ui(state)
    from invoice_tool.ui_v2.finalization_preview_batch import (
        batch_report_fields,
        build_finalization_preview_batch,
        item_batch_export_fields,
    )
    from invoice_tool.ui_v2.review_decision import (
        decision_report_fields_for_item,
        get_review_decision_bag,
        items_excluded_from_finalization_batch,
    )

    excluded = frozenset(bag.excluded_from_export_preview_keys) | set(
        items_excluded_from_finalization_batch(state)
    )
    decision_bag = get_review_decision_bag(state)
    finalization_batch = build_finalization_preview_batch(state)
    batch_manifest_fields = batch_report_fields(finalization_batch)
    decision_fields_by_key = {
        key: {
            **decision_report_fields_for_item(state, key),
            **item_batch_export_fields(finalization_batch, key),
        }
        for key in decision_bag.decisions_by_item_key
    }
    # Also attach batch fields for review items without a stored decision.
    for batch_item in finalization_batch.items:
        if batch_item.item_id not in decision_fields_by_key:
            decision_fields_by_key[batch_item.item_id] = {
                **decision_report_fields_for_item(state, batch_item.item_id),
                **item_batch_export_fields(finalization_batch, batch_item.item_id),
            }

    # Reject stale previous export folders as input before any write.
    if _path_is_previous_preview_export(_norm_path(input_root)):
        err = MSG_PREVIEW_EXPORT_STALE_SOURCE_BLOCKED
        state.workspace_preview_export_feedback = err
        state.workspace_preview_export_feedback_error = True
        state.workspace_export_feedback = err
        state.workspace_export_feedback_error = True
        return PreviewExportResult(ok=False, status="blocked", error=err)

    if isinstance(run_state, ProcessingRunState) and input_root:
        refreshed = refresh_run_state_from_current_sandbox_input(
            run_state,
            input_root=input_root,
        )
        state.processing_run_state = refreshed
        run_state = refreshed

    # Expectations from the same current state the Review UI will show after refresh.
    expectations = (
        build_review_ui_export_expectations(run_state)
        if isinstance(run_state, ProcessingRunState)
        else ()
    )

    result = write_preview_export_package(
        run_state,
        input_root=input_root,
        output_root=output_root,
        excluded_keys=excluded,
        productive_mode_requested=False,
        dry_run=True,
        preview_export=True,
        final_write=False,
        review_expectations=expectations,
        refresh_from_input=False,
        decision_fields_by_key=decision_fields_by_key,
        finalization_preview_batch=batch_manifest_fields,
    )

    if result.ok:
        folder = str(result.export_folder) if result.export_folder else ""
        feedback = (
            f"{MSG_PREVIEW_EXPORT_CREATED}: {folder} · "
            f"{result.copied_file_count} Preview-PDFs · "
            f"Manifest/Report geschrieben · "
            f"{MSG_PREVIEW_EXPORT_NO_FINAL_FILES} · "
            f"{MSG_PREVIEW_EXPORT_ORIGINALS_UNCHANGED} · "
            f"{MSG_PREVIEW_EXPORT_PRODUCTIVE_LOCKED}"
        )
        state.workspace_preview_export_feedback = feedback
        state.workspace_preview_export_feedback_error = False
        state.workspace_last_preview_export_folder = folder
        # Also surface in the general export feedback slot for existing panels.
        state.workspace_export_feedback = feedback
        state.workspace_export_feedback_error = False
    else:
        err = result.error or "Preview-Export fehlgeschlagen."
        state.workspace_preview_export_feedback = err
        state.workspace_preview_export_feedback_error = True
        state.workspace_export_feedback = err
        state.workspace_export_feedback_error = True
    return result


def preview_export_ui_copy() -> tuple[str, ...]:
    return (
        MSG_PREVIEW_EXPORT_TITLE,
        MSG_PREVIEW_EXPORT_CTA,
        MSG_PREVIEW_EXPORT_WRITES_PACKAGE_ONLY,
        MSG_PREVIEW_EXPORT_ORIGINALS_UNCHANGED,
        MSG_PREVIEW_EXPORT_NO_FINAL,
        MSG_PREVIEW_EXPORT_PRODUCTIVE_LOCKED,
        MSG_PREVIEW_EXPORT_NO_FINAL_FILES,
        MSG_FIELD_PREVIEW_FILENAME,
        MSG_FIELD_CONFIGURATION,
        MSG_FIELD_FILENAME_PATTERN,
        MSG_FIELD_PLACEHOLDER_VALUES,
        MSG_FIELD_MISSING_PLACEHOLDERS,
        MSG_FIELD_AMOUNT_FORMAT,
        MSG_FIELD_DOCUMENT_DIRECTION,
        MSG_FIELD_BUSINESS_CATEGORY,
        MSG_FIELD_COUNTERPARTY_NAME,
        MSG_FIELD_AMOUNT,
        MSG_FIELD_AMOUNT_REASON,
        MSG_FIELD_PAYMENT_FIELD,
        MSG_FIELD_PAYMENT_FIELD_REASON,
        MSG_FIELD_DOCUMENT_ART,
        MSG_FIELD_ART_REASON,
        MSG_FIELD_NAMING_REASON,
        MSG_FIELD_PLANNED_TARGET,
        MSG_NAMING_NOT_FINAL,
        MSG_SUGGESTED_PREVIEW_ONLY,
        MSG_NO_SAAS_READY,
        MSG_NO_PRODUCTION_READY,
    )


def text_claims_forbidden_maturity(text: str) -> bool:
    """True only for positive maturity claims — negated disclaimers are honest."""

    lowered = (text or "").lower()
    # Strip honest negative forms before scanning.
    cleaned = (
        lowered.replace("nicht saas-ready", " ")
        .replace("nicht production-ready", " ")
        .replace("not saas-ready", " ")
        .replace("not production-ready", " ")
        .replace("kein finales produktions-output", " ")
        .replace("not a final production output", " ")
        # Path/test-name false positives (e.g. …/no_saas_ready_… in export folder).
        .replace("no_saas_ready", " ")
        .replace("no_production_ready", " ")
        .replace("not_saas_ready", " ")
        .replace("not_production_ready", " ")
    )
    # Bare "saas-ready" / "production-ready" after stripping negations is a claim.
    if "saas-ready" in cleaned or "production-ready" in cleaned:
        return True
    return any(marker in cleaned for marker in FORBIDDEN_POSITIVE_CLAIM_MARKERS)


__all__ = (
    "FILES_SUBDIR",
    "FILENAME_SOURCE_CANONICAL_FALLBACK",
    "FILENAME_SOURCE_CONFIGURATION_PATTERN",
    "FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE",
    "FILENAME_SOURCE_ORIGINAL_FALLBACK",
    "FILENAME_SOURCE_PLANNED_RESULT",
    "FILENAME_SOURCE_SUGGESTED_MAPPING",
    "FORBIDDEN_CLAIM_MARKERS",
    "FORBIDDEN_POSITIVE_CLAIM_MARKERS",
    "MSG_FIELD_AMOUNT",
    "MSG_FIELD_AMOUNT_FORMAT",
    "MSG_FIELD_AMOUNT_REASON",
    "MSG_FIELD_PAYMENT_FIELD",
    "MSG_FIELD_PAYMENT_FIELD_REASON",
    "MSG_FIELD_DOCUMENT_ART",
    "MSG_FIELD_ART_REASON",
    "MSG_FIELD_BUSINESS_CATEGORY",
    "MSG_FIELD_CONFIGURATION",
    "MSG_FIELD_COUNTERPARTY_NAME",
    "MSG_FIELD_DOCUMENT_DIRECTION",
    "MSG_FIELD_FILENAME_PATTERN",
    "MSG_FIELD_MISSING_PLACEHOLDERS",
    "MSG_FIELD_NAMING_REASON",
    "MSG_FIELD_PLACEHOLDER_VALUES",
    "MSG_FIELD_PLANNED_TARGET",
    "MSG_FIELD_PREVIEW_FILENAME",
    "MSG_FIELD_RENDERED_FILENAME",
    "MSG_NAMING_NOT_FINAL",
    "MSG_PREVIEW_EXPORT_STALE_SOURCE_BLOCKED",
    "MSG_PREVIEW_EXPORT_STALE_STATE_BLOCKED",
    "REVIEW_REQUIRED_SUGGESTED_INCOMPLETE_PREFIX",
    "MSG_NAMING_REASON_NO_SUGGESTED",
    "MSG_NAMING_REASON_PLANNED_SAME_AS_SOURCE",
    "MSG_NAMING_REASON_SUGGESTED",
    "MSG_NO_PRODUCTION_READY",
    "MSG_NO_SAAS_READY",
    "MSG_PREVIEW_EXPORT_BLOCKED_PATH",
    "MSG_PREVIEW_EXPORT_CREATED",
    "MSG_PREVIEW_EXPORT_CTA",
    "MSG_PREVIEW_EXPORT_NEEDS_COMPLETED_RUN",
    "MSG_PREVIEW_EXPORT_NEEDS_FOLDERS",
    "MSG_PREVIEW_EXPORT_NO_FINAL",
    "MSG_PREVIEW_EXPORT_NO_FINAL_FILES",
    "MSG_PREVIEW_EXPORT_NOT_PRODUCTION",
    "MSG_PREVIEW_EXPORT_ORIGINALS_UNCHANGED",
    "MSG_PREVIEW_EXPORT_PRODUCTIVE_LOCKED",
    "MSG_PREVIEW_EXPORT_SAME_PATH",
    "MSG_PREVIEW_EXPORT_SANDBOX_ONLY",
    "MSG_PREVIEW_EXPORT_TITLE",
    "MSG_PREVIEW_EXPORT_WRITES_PACKAGE_ONLY",
    "MSG_SUGGESTED_PREVIEW_ONLY",
    "PREVIEW_EXPORT_FOLDER_PREFIX",
    "PREVIEW_EXPORT_KIND",
    "PREVIEW_EXPORT_SCHEMA_VERSION",
    "STATE_SOURCE_CURRENT_PROCESSING_RUN",
    "STATE_SOURCE_REVIEW_UI",
    "PreviewExportItem",
    "PreviewExportRequest",
    "PreviewExportResult",
    "PreviewNamingDecision",
    "ReviewExportExpectation",
    "REVIEW_REQUIRED_PREFIX",
    "REVIEW_REQUIRED_SUGGESTED_PREFIX",
    "SUGGESTED_PREFIX",
    "apply_workspace_preview_export",
    "build_review_ui_export_expectations",
    "preview_export_available",
    "preview_export_ui_copy",
    "refresh_run_state_from_current_sandbox_input",
    "resolve_preview_naming",
    "review_required_preview_filename",
    "review_required_suggested_preview_filename",
    "sanitize_preview_filename",
    "sha256_file",
    "suggested_preview_filename",
    "text_claims_forbidden_maturity",
    "validate_export_state_freshness",
    "validate_preview_export_paths",
    "write_preview_export_package",
)
