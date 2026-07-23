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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

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
    review_item_key,
)

PREVIEW_EXPORT_KIND = "track_b_preview_export_package"
PREVIEW_EXPORT_SCHEMA_VERSION = 1
PREVIEW_EXPORT_FOLDER_PREFIX = "preview-export-"
REVIEW_REQUIRED_PREFIX = "REVIEW_REQUIRED__"
REVIEW_REQUIRED_SUGGESTED_PREFIX = "REVIEW_REQUIRED__SUGGESTED__"
FILES_SUBDIR = "files"

FilenameSource = Literal[
    "planned_result",
    "suggested_mapping",
    "original_fallback",
]

FILENAME_SOURCE_PLANNED_RESULT: FilenameSource = "planned_result"
FILENAME_SOURCE_SUGGESTED_MAPPING: FilenameSource = "suggested_mapping"
FILENAME_SOURCE_ORIGINAL_FALLBACK: FilenameSource = "original_fallback"

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
MSG_NO_SAAS_READY = "nicht SaaS-ready"
MSG_NO_PRODUCTION_READY = "nicht production-ready"
MSG_FIELD_PREVIEW_FILENAME = "Vorschau-Dateiname"
MSG_FIELD_NAMING_REASON = "Grund für REVIEW_REQUIRED"
MSG_FIELD_PLANNED_TARGET = "Geplantes Ziel"
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

_UNSAFE_FILENAME_RE = re.compile(r"[^\w.\- ()\[\]]+", re.UNICODE)
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


@dataclass(frozen=True)
class PreviewNamingDecision:
    """Honest preview naming decision — never invents invoice metadata."""

    preview_filename: str
    suggested_filename: str | None
    planned_target: str | None
    filename_source: FilenameSource
    naming_reason: str
    review_required: bool


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


def review_required_suggested_preview_filename(suggested_filename: str) -> str:
    """Mark a safe suggested name as review-required preview (not final)."""

    safe = sanitize_preview_filename(suggested_filename)
    # Strip existing review prefixes so we never double-wrap.
    while safe.startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX):
        safe = safe[len(REVIEW_REQUIRED_SUGGESTED_PREFIX) :]
    while safe.startswith(REVIEW_REQUIRED_PREFIX):
        safe = safe[len(REVIEW_REQUIRED_PREFIX) :]
    safe = sanitize_preview_filename(safe)
    return f"{REVIEW_REQUIRED_SUGGESTED_PREFIX}{safe}"


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

    planned_name = _planned_basename(planned)
    explicit_suggested = (suggested_filename or "").strip() or None
    if explicit_suggested:
        explicit_suggested = Path(explicit_suggested).name
        if not explicit_suggested.lower().endswith(".pdf") or ".." in explicit_suggested:
            explicit_suggested = None

    # Prefer an explicit suggested mapping name when it safely differs.
    candidate: str | None = None
    source_kind: FilenameSource = FILENAME_SOURCE_ORIGINAL_FALLBACK
    if explicit_suggested and _basename_differs_from_source(
        explicit_suggested, source_filename
    ):
        candidate = explicit_suggested
        source_kind = FILENAME_SOURCE_SUGGESTED_MAPPING
    elif planned_name and _basename_differs_from_source(planned_name, source_filename):
        candidate = planned_name
        source_kind = FILENAME_SOURCE_PLANNED_RESULT

    if review_required:
        if candidate is not None:
            safe_suggested = sanitize_preview_filename(candidate)
            return PreviewNamingDecision(
                preview_filename=review_required_suggested_preview_filename(safe_suggested),
                suggested_filename=safe_suggested,
                planned_target=planned_target,
                filename_source=source_kind,
                naming_reason=MSG_NAMING_REASON_SUGGESTED,
                review_required=True,
            )
        reason = (
            MSG_NAMING_REASON_PLANNED_SAME_AS_SOURCE
            if planned_target
            else MSG_NAMING_REASON_NO_SUGGESTED
        )
        return PreviewNamingDecision(
            preview_filename=review_required_preview_filename(source_filename),
            suggested_filename=None,
            planned_target=planned_target,
            filename_source=FILENAME_SOURCE_ORIGINAL_FALLBACK,
            naming_reason=reason,
            review_required=True,
        )

    if candidate is not None:
        return PreviewNamingDecision(
            preview_filename=sanitize_preview_filename(candidate),
            suggested_filename=sanitize_preview_filename(candidate),
            planned_target=planned_target,
            filename_source=source_kind,
            naming_reason=MSG_NAMING_REASON_RECOGNIZED_PLANNED,
            review_required=False,
        )
    return PreviewNamingDecision(
        preview_filename=sanitize_preview_filename(source_filename),
        suggested_filename=None,
        planned_target=planned_target,
        filename_source=FILENAME_SOURCE_ORIGINAL_FALLBACK,
        naming_reason=MSG_NAMING_REASON_RECOGNIZED_SOURCE,
        review_required=False,
    )


def preview_export_available(run_state: ProcessingRunState | None) -> bool:
    """True only after a successful sandbox result state exists."""

    if run_state is None:
        return False
    return (run_state.status or "") == "completed"


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
            "- Manifest fields: `filename_source`, `naming_reason`, `suggested_filename`, `planned_target`",
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
            "filename_source",
            "naming_reason",
            "review_required",
            "source_sha256",
            "preview_sha256",
            "excluded",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.source_filename,
                item.preview_filename,
                item.status,
                item.category,
                item.planned_target or "",
                item.suggested_filename or "",
                item.filename_source,
                item.naming_reason,
                "yes" if item.review_required else "no",
                item.source_sha256,
                item.preview_sha256,
                "yes" if item.excluded else "no",
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
) -> dict[str, Any]:
    copied = [item for item in items if not item.excluded]
    return {
        "kind": PREVIEW_EXPORT_KIND,
        "schema_version": PREVIEW_EXPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at": generated_at,
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
        "items": [
            {
                "source_filename": item.source_filename,
                "preview_filename": item.preview_filename,
                "status": item.status,
                "category": item.category,
                "planned_target": item.planned_target,
                "suggested_filename": item.suggested_filename,
                "filename_source": item.filename_source,
                "naming_reason": item.naming_reason,
                "review_reason": item.review_reason,
                "review_required": item.review_required,
                "source_sha256": item.source_sha256,
                "preview_sha256": item.preview_sha256,
                "excluded": item.excluded,
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
    used_names: set[str] = set()
    generated_at = datetime.now(timezone.utc).isoformat()

    try:
        export_folder.mkdir(parents=False, exist_ok=False)
        files_dir.mkdir(parents=False, exist_ok=False)

        for row, source, planned in resolved:
            naming = resolve_preview_naming(
                source_filename=row["source_filename"],
                review_required=bool(row["review_required"]),
                planned=planned,
            )
            preview_name = _unique_preview_name(naming.preview_filename, used_names)
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
                )
            )

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
    """UI-v2 helper: write preview-export package from workspace folder overrides."""

    run_state = getattr(state, "processing_run_state", None)
    input_root = (getattr(state, "workspace_input_folder_override", None) or "").strip()
    output_root = (getattr(state, "workspace_output_folder_override", None) or "").strip()
    bag = get_review_preview_ui(state)
    excluded = frozenset(bag.excluded_from_export_preview_keys)

    result = write_preview_export_package(
        run_state,
        input_root=input_root,
        output_root=output_root,
        excluded_keys=excluded,
        productive_mode_requested=False,
        dry_run=True,
        preview_export=True,
        final_write=False,
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
    "FILENAME_SOURCE_ORIGINAL_FALLBACK",
    "FILENAME_SOURCE_PLANNED_RESULT",
    "FILENAME_SOURCE_SUGGESTED_MAPPING",
    "FORBIDDEN_CLAIM_MARKERS",
    "FORBIDDEN_POSITIVE_CLAIM_MARKERS",
    "MSG_FIELD_NAMING_REASON",
    "MSG_FIELD_PLANNED_TARGET",
    "MSG_FIELD_PREVIEW_FILENAME",
    "MSG_NAMING_NOT_FINAL",
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
    "PreviewExportItem",
    "PreviewExportRequest",
    "PreviewExportResult",
    "PreviewNamingDecision",
    "REVIEW_REQUIRED_PREFIX",
    "REVIEW_REQUIRED_SUGGESTED_PREFIX",
    "apply_workspace_preview_export",
    "preview_export_available",
    "preview_export_ui_copy",
    "resolve_preview_naming",
    "review_required_preview_filename",
    "review_required_suggested_preview_filename",
    "sanitize_preview_filename",
    "sha256_file",
    "text_claims_forbidden_maturity",
    "validate_preview_export_paths",
    "write_preview_export_package",
)
