"""Core Dry-Run / No-Mutation sandbox processing API (Prompt 2/34).

Additive entry point for Track B. Does **not** call ``invoice_tool.run.run_once``,
does not archive/move/rename/delete source files, does not write outside the
explicit sandbox ``output_dir``, and does not run DATEV/cloud export.

Contract types live in ``invoice_tool.ui_v2.core_dry_run_contract``. This module
loads that contract file without executing ``ui_v2.__init__`` (which pulls Flet),
so processing-core stays free of UI runtime side effects.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Contract import (bypass ui_v2 package __init__ / Flet)
# ---------------------------------------------------------------------------

_CONTRACT_MODULE_NAME = "invoice_tool.ui_v2.core_dry_run_contract"


def _load_core_dry_run_contract() -> types.ModuleType:
    """Load contract types with stable module identity, without Flet bootstrap."""

    existing = sys.modules.get(_CONTRACT_MODULE_NAME)
    if existing is not None:
        return existing

    ui_v2_name = "invoice_tool.ui_v2"
    ui_v2_pkg = sys.modules.get(ui_v2_name)
    if ui_v2_pkg is None:
        stub = types.ModuleType(ui_v2_name)
        stub.__path__ = [str(Path(__file__).resolve().parent / "ui_v2")]  # type: ignore[attr-defined]
        stub.__package__ = ui_v2_name
        sys.modules[ui_v2_name] = stub
    elif not hasattr(ui_v2_pkg, "__path__"):
        ui_v2_pkg.__path__ = [str(Path(__file__).resolve().parent / "ui_v2")]  # type: ignore[attr-defined]

    contract_path = Path(__file__).resolve().parent / "ui_v2" / "core_dry_run_contract.py"
    spec = importlib.util.spec_from_file_location(_CONTRACT_MODULE_NAME, contract_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load core dry-run contract from {contract_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_CONTRACT_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


_contract = _load_core_dry_run_contract()

CoreDryRunContractViolation = _contract.CoreDryRunContractViolation
CoreDryRunDocumentResult = _contract.CoreDryRunDocumentResult
CoreDryRunErrorItem = _contract.CoreDryRunErrorItem
CoreDryRunMode = _contract.CoreDryRunMode
CoreDryRunPlannedDestination = _contract.CoreDryRunPlannedDestination
CoreDryRunRequest = _contract.CoreDryRunRequest
CoreDryRunResult = _contract.CoreDryRunResult
CoreDryRunReviewItem = _contract.CoreDryRunReviewItem
CoreDryRunSafetyProof = _contract.CoreDryRunSafetyProof
CoreDryRunStatus = _contract.CoreDryRunStatus
CoreDryRunSummary = _contract.CoreDryRunSummary
build_blocked_core_dry_run_result = _contract.build_blocked_core_dry_run_result
empty_safety_proof = _contract.empty_safety_proof
summarize_core_dry_run_buckets = _contract.summarize_core_dry_run_buckets
validate_core_dry_run_request = _contract.validate_core_dry_run_request

# ---------------------------------------------------------------------------
# Constants / safe local heuristics (no private path defaults)
# ---------------------------------------------------------------------------

_ARCHIVE_DIRNAME = "archiv"
_SUPPORTED_TEXT_SUFFIXES = {".txt", ".text", ".md"}
_SUPPORTED_PDF_SUFFIXES = {".pdf"}
_SKIP_NAMES = {".ds_store", "thumbs.db"}

# Strong invoice identity markers for *readable text only* — not filename-as-truth.
_INVOICE_TEXT_MARKERS = (
    "rechnung",
    "rechnungsnummer",
    "invoice number",
    "invoice no",
    "rechnungsnr",
    "ust-id",
    "ust id",
    "mwst",
    "mehrwertsteuer",
    "gesamtbetrag",
    "brutto",
    "nettobetrag",
)

# Hooks tests may monkeypatch to prove productive paths stay cold.
_PRODUCTIVE_RUN_ONCE: Callable[..., Any] | None = None
_DATEV_CLOUD_EXPORT_HOOK: Callable[..., Any] | None = None


class CoreDryRunError(RuntimeError):
    """Unexpected dry-run failure after contract validation."""


# ---------------------------------------------------------------------------
# FS helpers (read-only on source; no writes by default)
# ---------------------------------------------------------------------------


def _resolve_dir(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _source_snapshot(input_dir: Path) -> tuple[str, ...]:
    """Stable listing of source entries (name|type|size|mtime_ns|sha256 for files)."""

    if not input_dir.is_dir():
        return ()
    rows: list[str] = []
    for path in sorted(input_dir.iterdir(), key=lambda p: p.name.lower()):
        if path.name.lower() in _SKIP_NAMES:
            continue
        if path.is_dir():
            rows.append(f"dir|{path.name}|")
            continue
        if not path.is_file():
            rows.append(f"other|{path.name}|")
            continue
        try:
            stat = path.stat()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append(
                f"file|{path.name}|{stat.st_size}|{stat.st_mtime_ns}|{digest}"
            )
        except OSError as exc:
            rows.append(f"unreadable|{path.name}|{exc}")
    return tuple(rows)


def _discover_candidates(input_dir: Path) -> list[Path]:
    """Top-level candidate files; never enters archive subtree."""

    if not input_dir.is_dir():
        return []
    found: list[Path] = []
    for path in sorted(input_dir.iterdir(), key=lambda p: p.name.lower()):
        if path.name == _ARCHIVE_DIRNAME and path.is_dir():
            continue
        if path.name.lower() in _SKIP_NAMES:
            continue
        if path.is_file():
            found.append(path)
    return found


def _read_text_safely(path: Path) -> tuple[str | None, str | None]:
    """Return (text, error_code). Never mutates the file."""

    try:
        data = path.read_bytes()
    except OSError:
        return None, "unreadable"
    if b"\x00" in data[:4096]:
        return None, "binary_unsupported"
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding), None
        except UnicodeDecodeError:
            continue
    return None, "decode_failed"


def _count_invoice_markers(text: str) -> tuple[int, tuple[str, ...]]:
    lowered = text.lower()
    hits = [marker for marker in _INVOICE_TEXT_MARKERS if marker in lowered]
    return len(hits), tuple(hits[:6])


def _planned_path(output_dir: Path, bucket: str, document_name: str) -> str:
    # Data-only plan under explicit sandbox output — never applied / never written.
    return str((output_dir / "geplant" / bucket / document_name).as_posix())


def _forbid_productive_side_effects() -> None:
    """Fail closed if a test/wiring accidentally injects productive hooks."""

    if _PRODUCTIVE_RUN_ONCE is not None:
        raise CoreDryRunError("productive run_once hook must not be set in dry-run")
    if _DATEV_CLOUD_EXPORT_HOOK is not None:
        raise CoreDryRunError("DATEV/cloud export hook must not be set in dry-run")


# ---------------------------------------------------------------------------
# Per-document evaluation (no OCR/AI, no mutation)
# ---------------------------------------------------------------------------


def _evaluate_document(
    path: Path,
    *,
    output_dir: Path,
) -> tuple[
    CoreDryRunDocumentResult | None,
    CoreDryRunReviewItem | None,
    CoreDryRunErrorItem | None,
    CoreDryRunPlannedDestination | None,
    tuple[str, ...],
]:
    warnings: list[str] = []
    name = path.name
    suffix = path.suffix.lower()

    if suffix in _SUPPORTED_PDF_SUFFIXES:
        warnings.append("ocr_not_run")
        warnings.append("ai_not_run")
        review = CoreDryRunReviewItem(
            document_name=name,
            reason=(
                "PDF erkannt, aber OCR/AI im Core-Dry-Run absichtlich nicht ausgeführt; "
                "unzureichende Evidenz für sichere Erkennung."
            ),
            status_label="unklar",
            evidence_summary="pdf_present_without_extraction",
            next_action_hint="Nach Prompt-3-Bridge optional sichere Extraktion konfigurieren.",
        )
        planned = CoreDryRunPlannedDestination(
            document_name=name,
            planned_path=_planned_path(output_dir, "unklar", name),
            destination_label="unklar",
            reason="planned_only_insufficient_pdf_evidence",
            applied=False,
        )
        return None, review, None, planned, tuple(warnings)

    if suffix in _SUPPORTED_TEXT_SUFFIXES:
        text, err = _read_text_safely(path)
        if err is not None or text is None:
            error = CoreDryRunErrorItem(
                document_name=name,
                error_code=err or "unreadable",
                message="Textdatei konnte nicht sicher gelesen werden.",
            )
            return None, None, error, None, tuple(warnings)

        marker_count, markers = _count_invoice_markers(text)
        # Filename is never used as truth — only readable text body.
        if marker_count >= 2 and len(text.strip()) >= 20:
            recognized = CoreDryRunDocumentResult(
                document_name=name,
                document_type="invoice",
                classification_status="recognized",
                status_label="erkannt",
                confidence_label="limited_text_evidence",
                target_hint="geplant/erkannt",
                evidence_summary="text_markers:" + ",".join(markers),
            )
            planned = CoreDryRunPlannedDestination(
                document_name=name,
                planned_path=_planned_path(output_dir, "erkannt", name),
                destination_label="erkannt",
                reason="planned_only_text_invoice_markers",
                applied=False,
            )
            warnings.append("extraction_limited_text_only")
            warnings.append("no_write_performed")
            return recognized, None, None, planned, tuple(warnings)

        review = CoreDryRunReviewItem(
            document_name=name,
            reason="Unzureichende Text-Evidenz für sichere Rechnungserkennung.",
            status_label="unklar",
            evidence_summary=(
                f"text_markers={marker_count};filename_not_used_as_truth"
            ),
            next_action_hint="Manuelle Prüfung erforderlich.",
        )
        planned = CoreDryRunPlannedDestination(
            document_name=name,
            planned_path=_planned_path(output_dir, "unklar", name),
            destination_label="unklar",
            reason="planned_only_insufficient_text_evidence",
            applied=False,
        )
        warnings.append("extraction_limited_text_only")
        return None, review, None, planned, tuple(warnings)

    error = CoreDryRunErrorItem(
        document_name=name,
        error_code="unsupported_file_type",
        message=f"Nicht unterstützter Dateityp für Dry-Run: {suffix or '(ohne Endung)'}",
    )
    return None, None, error, None, tuple(warnings)


def _decide_status(
    *,
    recognized: tuple[Any, ...],
    review: tuple[Any, ...],
    errors: tuple[Any, ...],
    fatal: bool,
) -> Any:
    if fatal:
        return CoreDryRunStatus.FAILED
    if review and not recognized and not errors:
        return CoreDryRunStatus.COMPLETED_WITH_REVIEW
    if review:
        return CoreDryRunStatus.COMPLETED_WITH_REVIEW
    if errors and not recognized and not review:
        return CoreDryRunStatus.FAILED
    if errors:
        return CoreDryRunStatus.COMPLETED_WITH_REVIEW
    return CoreDryRunStatus.COMPLETED


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_core_dry_run_sandbox(request: CoreDryRunRequest) -> CoreDryRunResult:
    """Execute a no-mutation core dry-run against copied sandbox input.

    Signature (stable for Track-B Prompt 3/34):

        run_core_dry_run_sandbox(request: CoreDryRunRequest) -> CoreDryRunResult

    Raises:
        CoreDryRunContractViolation: when the request violates the sandbox contract.
    """

    validated = validate_core_dry_run_request(request)
    _forbid_productive_side_effects()

    input_dir = _resolve_dir(validated.input_dir or "")
    output_dir = _resolve_dir(validated.output_dir or "")

    if not input_dir.is_dir():
        return CoreDryRunResult(
            status=CoreDryRunStatus.FAILED,
            run_id=validated.run_id,
            errors=(
                CoreDryRunErrorItem(
                    document_name="",
                    error_code="input_dir_missing",
                    message=f"Sandbox-Eingang existiert nicht oder ist kein Ordner: {input_dir}",
                ),
            ),
            summary=CoreDryRunSummary(total_documents=0, error_count=1),
            warnings=("input_dir_missing", "no_write_performed"),
            safety_proof=empty_safety_proof(
                evidence_notes=(
                    "failed_before_document_scan",
                    "no_source_mutation",
                    "no_productive_mode",
                )
            ),
            message="Sandbox-Eingang fehlt.",
        )

    # output_dir need not exist: planned destinations are data-only strings.
    before = _source_snapshot(input_dir)
    recognized_list: list[Any] = []
    review_list: list[Any] = []
    error_list: list[Any] = []
    planned_list: list[Any] = []
    warning_set: list[str] = [
        "ocr_not_run_by_default",
        "ai_not_run_by_default",
        "no_write_performed",
        "no_source_archive",
        "planned_destinations_data_only",
        "filename_as_truth_disabled",
    ]

    for path in _discover_candidates(input_dir):
        try:
            recognized, review, error, planned, doc_warnings = _evaluate_document(
                path, output_dir=output_dir
            )
        except Exception as exc:  # noqa: BLE001 — never crash the dry-run API
            error_list.append(
                CoreDryRunErrorItem(
                    document_name=path.name,
                    error_code="evaluation_exception",
                    message=f"Unerwarteter Auswertungsfehler: {exc}",
                )
            )
            continue
        for w in doc_warnings:
            if w not in warning_set:
                warning_set.append(w)
        if recognized is not None:
            recognized_list.append(recognized)
        if review is not None:
            review_list.append(review)
        if error is not None:
            error_list.append(error)
        if planned is not None:
            assert planned.applied is False
            planned_list.append(planned)

    after = _source_snapshot(input_dir)
    source_unchanged = before == after
    archive_present_after = (input_dir / _ARCHIVE_DIRNAME).exists()
    # If archive existed before, keep it; we must not *create* one.
    archive_created = (not any(r.startswith(f"dir|{_ARCHIVE_DIRNAME}|") for r in before)) and (
        archive_present_after
    )

    evidence = [
        f"source_snapshot_before_count={len(before)}",
        f"source_snapshot_after_count={len(after)}",
        f"source_snapshot_identical={source_unchanged}",
        f"archive_created={archive_created}",
        "no_run_once_called",
        "no_datev_cloud_export",
        "writes_confined_to_sandbox_output=true",
        "no_file_writes_performed=true",
    ]
    if not source_unchanged or archive_created:
        mutation_errors = tuple(error_list) + (
            CoreDryRunErrorItem(
                document_name="",
                error_code="source_mutation_detected",
                message="Source-Ordner hat sich während des Dry-Runs verändert.",
            ),
        )
        return CoreDryRunResult(
            status=CoreDryRunStatus.FAILED,
            run_id=validated.run_id,
            recognized=tuple(recognized_list),
            review=tuple(review_list),
            errors=mutation_errors,
            planned_destinations=tuple(planned_list),
            summary=summarize_core_dry_run_buckets(
                recognized=tuple(recognized_list),
                review=tuple(review_list),
                errors=mutation_errors,
                planned_destinations=tuple(planned_list),
            ),
            warnings=tuple(warning_set),
            safety_proof=CoreDryRunSafetyProof(
                no_original_mutation=False,
                no_source_archive=not archive_created,
                no_source_rename=source_unchanged,
                no_source_delete=source_unchanged,
                no_source_move=source_unchanged,
                writes_confined_to_sandbox_output=True,
                productive_mode_disabled=True,
                real_datev_cloud_export_disabled=True,
                filename_as_truth_disabled=True,
                private_defaults_disabled=True,
                planned_destinations_not_applied=True,
                evidence_notes=tuple(evidence),
            ),
            message="Dry-Run abgebrochen: Source-Mutation erkannt.",
        )

    recognized_t = tuple(recognized_list)
    review_t = tuple(review_list)
    errors_t = tuple(error_list)
    planned_t = tuple(planned_list)
    summary = summarize_core_dry_run_buckets(
        recognized=recognized_t,
        review=review_t,
        errors=errors_t,
        planned_destinations=planned_t,
    )
    status = _decide_status(
        recognized=recognized_t,
        review=review_t,
        errors=errors_t,
        fatal=False,
    )
    if summary.total_documents == 0:
        warning_set.append("empty_input_no_candidates")
        status = CoreDryRunStatus.COMPLETED

    proof = empty_safety_proof(evidence_notes=tuple(evidence))
    return CoreDryRunResult(
        status=status,
        run_id=validated.run_id,
        recognized=recognized_t,
        review=review_t,
        errors=errors_t,
        planned_destinations=planned_t,
        summary=summary,
        warnings=tuple(warning_set),
        safety_proof=proof,
        message="Core-Dry-Run abgeschlossen ohne Source-Mutation.",
    )


__all__ = (
    "CoreDryRunError",
    "run_core_dry_run_sandbox",
)
