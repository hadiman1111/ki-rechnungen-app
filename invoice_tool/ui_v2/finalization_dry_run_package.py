"""Track-B Finalization Dry-Run Package & Audit (Prompt 31/34).

Creates a non-productive, reviewable package from a FinalizationPreviewBatch.
Writes audit/plan/manifest artifacts only under a controlled sandbox output root.

Never writes final production PDFs, never mutates inputs, never calls run_once,
never sets final_write_allowed=True, never touches real invoice folders.
"""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from invoice_tool.ui_v2.core_dry_run_contract import (
    is_explicit_copied_sandbox_test_path,
    path_has_forbidden_productive_marker,
    path_looks_like_original,
)
from invoice_tool.ui_v2.finalization_preview_batch import (
    STATUS_BLOCKED,
    STATUS_DEFERRED,
    STATUS_IGNORED,
    STATUS_READY,
    STATUS_STILL_REVIEW,
    FinalizationPreviewBatch,
    FinalizationPreviewConflict,
    build_finalization_preview_batch,
    get_finalization_preview_batch_bag,
)

DRY_RUN_PACKAGE_KIND = "track_b_finalization_dry_run_package"
DRY_RUN_PACKAGE_SCHEMA_VERSION = 1
DRY_RUN_PACKAGE_FOLDER_PREFIX = "finalization-dry-run-"

ARTIFACT_README = "README_FINALIZATION_DRY_RUN.md"
ARTIFACT_MANIFEST_JSON = "finalization-dry-run-manifest.json"
ARTIFACT_MANIFEST_CSV = "finalization-dry-run-manifest.csv"
ARTIFACT_AUDIT = "finalization-audit.md"
ARTIFACT_PLAN = "finalization-plan.md"
ARTIFACT_CONFLICTS = "conflicts.md"
ARTIFACT_BLOCKED = "blocked-items.md"
ARTIFACT_READY = "ready-items.md"
ARTIFACT_IGNORED = "ignored-items.md"
ARTIFACT_DEFERRED = "deferred-items.md"
ARTIFACT_STILL_REVIEW = "still-review-required.md"

MSG_CTA_CREATE_DRY_RUN = "Finalisierungs-Trockenlauf erstellen"
MSG_CTA_CREATE_AUDIT = "Audit-Paket erzeugen"
MSG_CTA_CHECK_ONLY = "Nur prüfen — nichts final schreiben"
MSG_DRY_RUN_TITLE = "Finalisierungs-Trockenlauf / Dry Run"
MSG_NO_FINAL_PRODUCTION = "kein finales Produktions-Output / no final production output"
MSG_ORIGINALS_UNCHANGED = "Originale unverändert — nicht verschoben, umbenannt, archiviert oder gelöscht"
MSG_NO_FINAL_PDFS = "keine finalen PDFs geschrieben"
MSG_FINAL_WRITE_FALSE = "final_write_allowed=false"
MSG_LATER_AUTHORIZATION = (
    "Finale Finalisierung erfordert spätere explizite Autorisierung "
    "(Final-Write-Gating — out of scope hier)."
)
MSG_SAFETY_SUMMARY = (
    "Finalization dry-run package only — dry_run_package=true; "
    "final_write_allowed=false; keine produktive Verarbeitung; "
    "Originale bleiben unverändert; keine finalen PDFs."
)
MSG_NEEDS_BATCH = "Finalisierungs-Trockenlauf blockiert: FinalizationPreviewBatch fehlt."
MSG_NEEDS_OUTPUT = (
    "Finalisierungs-Trockenlauf blockiert: kontrollierter Ausgabeordner erforderlich."
)
MSG_BLOCKED_PATH = (
    "Finalisierungs-Trockenlauf blockiert: Pfadpolitik verletzt "
    "(Sandbox/Test-Output erforderlich; keine realen Rechnungsordner)."
)
MSG_PACKAGE_OUTSIDE_OUTPUT = (
    "Finalisierungs-Trockenlauf blockiert: package_root liegt außerhalb des output_root."
)
MSG_FINAL_WRITE_REJECTED = (
    "Finalisierungs-Trockenlauf blockiert: final_write_allowed=true ist verboten."
)
MSG_PRODUCTIVE_REJECTED = (
    "Finalisierungs-Trockenlauf blockiert: produktiver Modus / run_once ist verboten."
)
MSG_STALE_PREVIEW = (
    "Finalisierungs-Trockenlauf blockiert: Preview-State ist veraltet (stale)."
)
MSG_CREATED = "Finalisierungs-Trockenlauf-Paket erstellt"
MSG_NO_SAAS_READY = "nicht SaaS-ready"
MSG_NO_PRODUCTION_READY = "nicht production-ready"

_UNSAFE_NAME_RE = re.compile(r"[^\w.\-]+", re.UNICODE)


@dataclass(frozen=True)
class FinalizationDryRunItemRecord:
    """One item row inside the dry-run package (text/audit only)."""

    item_id: str
    source_filename: str
    source_sha256: str | None
    preview_sha256: str | None
    approved_preview_filename: str | None
    target_preview_path: str | None
    review_decision: str | None
    finalization_status: str
    finalization_blockers: tuple[str, ...] = field(default_factory=tuple)
    finalization_warnings: tuple[str, ...] = field(default_factory=tuple)
    conflicts: tuple[str, ...] = field(default_factory=tuple)
    ready_for_future_finalization: bool = False
    final_write_allowed: bool = False
    would_copy_or_rename_source_to_target: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_filename": self.source_filename,
            "source_sha256": self.source_sha256,
            "preview_sha256": self.preview_sha256,
            "approved_preview_filename": self.approved_preview_filename,
            "target_preview_path": self.target_preview_path,
            "review_decision": self.review_decision,
            "finalization_status": self.finalization_status,
            "finalization_blockers": list(self.finalization_blockers),
            "finalization_warnings": list(self.finalization_warnings),
            "conflicts": list(self.conflicts),
            "ready_for_future_finalization": bool(self.ready_for_future_finalization),
            "final_write_allowed": False,
            "would_copy_or_rename_source_to_target": bool(
                self.would_copy_or_rename_source_to_target
            ),
        }


@dataclass(frozen=True)
class FinalizationDryRunPackage:
    """Non-productive finalization dry-run / audit package model."""

    package_id: str
    batch_id: str
    preview_state_id: str
    source_run_id: str | None
    created_at: str
    input_root: str | None
    output_root: str | None
    package_root: str | None
    dry_run_package: bool = True
    final_write_allowed: bool = False
    productive_mode_requested: bool = False
    source_mutation: bool = False
    final_files_written: bool = False
    originals_moved: bool = False
    originals_renamed: bool = False
    originals_archived: bool = False
    originals_deleted: bool = False
    total_items: int = 0
    ready_count: int = 0
    blocked_count: int = 0
    ignored_count: int = 0
    deferred_count: int = 0
    still_review_required_count: int = 0
    artifacts: tuple[str, ...] = field(default_factory=tuple)
    safety_summary: str = MSG_SAFETY_SUMMARY
    items: tuple[FinalizationDryRunItemRecord, ...] = field(default_factory=tuple)
    conflicts: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": DRY_RUN_PACKAGE_KIND,
            "schema_version": DRY_RUN_PACKAGE_SCHEMA_VERSION,
            "package_id": self.package_id,
            "batch_id": self.batch_id,
            "preview_state_id": self.preview_state_id,
            "source_run_id": self.source_run_id,
            "created_at": self.created_at,
            "input_root": self.input_root,
            "output_root": self.output_root,
            "package_root": self.package_root,
            "dry_run_package": True,
            "final_write_allowed": False,
            "productive_mode_requested": False,
            "source_mutation": False,
            "final_files_written": False,
            "originals_moved": False,
            "originals_renamed": False,
            "originals_archived": False,
            "originals_deleted": False,
            "total_items": self.total_items,
            "ready_count": self.ready_count,
            "blocked_count": self.blocked_count,
            "ignored_count": self.ignored_count,
            "deferred_count": self.deferred_count,
            "still_review_required_count": self.still_review_required_count,
            "artifacts": list(self.artifacts),
            "safety_summary": self.safety_summary,
            "items": [item.to_dict() for item in self.items],
            "conflicts": list(self.conflicts),
            "claims_saas_ready": False,
            "claims_production_ready": False,
            "title": MSG_DRY_RUN_TITLE,
        }


@dataclass(frozen=True)
class FinalizationDryRunPackageResult:
    ok: bool
    status: str
    package: FinalizationDryRunPackage | None = None
    package_root: Path | None = None
    error: str | None = None
    dry_run_package: bool = True
    final_write_allowed: bool = False
    productive_mode_requested: bool = False
    source_mutation: bool = False
    final_files_written: bool = False
    called_run_once: bool = False
    mutated_input: bool = False
    wrote_final_pdfs: bool = False
    touched_real_invoice_folders: bool = False


@dataclass
class FinalizationDryRunPackageBag:
    """In-memory bag for the last dry-run package creation."""

    last_package: FinalizationDryRunPackage | None = None
    last_package_root: str = ""
    last_feedback: str = ""
    last_feedback_error: bool = False
    called_run_once: bool = False
    mutated_input: bool = False
    wrote_final_pdfs: bool = False
    touched_real_invoice_folders: bool = False

    def reset(self) -> None:
        self.last_package = None
        self.last_package_root = ""
        self.last_feedback = ""
        self.last_feedback_error = False
        self.called_run_once = False
        self.mutated_input = False
        self.wrote_final_pdfs = False
        self.touched_real_invoice_folders = False


def get_finalization_dry_run_package_bag(state: Any) -> FinalizationDryRunPackageBag:
    bag = getattr(state, "finalization_dry_run_package_ui", None)
    if isinstance(bag, FinalizationDryRunPackageBag):
        return bag
    bag = FinalizationDryRunPackageBag()
    try:
        state.finalization_dry_run_package_ui = bag
    except Exception:
        pass
    return bag


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _new_package_id() -> str:
    return f"fdr-{uuid.uuid4().hex[:12]}"


def _norm_path(value: Path | str | None) -> Path | None:
    raw = _text(value)
    if not raw:
        return None
    try:
        return Path(raw).expanduser().resolve()
    except OSError:
        return Path(raw).expanduser()


def _safe_token(value: str | None, *, fallback: str) -> str:
    text = _UNSAFE_NAME_RE.sub("_", _text(value) or fallback).strip("._")
    return (text[:80] or fallback)


def _conflicts_for_item(
    item_id: str, conflicts: Sequence[FinalizationPreviewConflict]
) -> tuple[str, ...]:
    labels: list[str] = []
    for conflict in conflicts:
        if item_id in conflict.affected_item_ids:
            labels.append(conflict.conflict_type)
    return tuple(dict.fromkeys(labels))


def _item_records(
    batch: FinalizationPreviewBatch,
) -> tuple[FinalizationDryRunItemRecord, ...]:
    records: list[FinalizationDryRunItemRecord] = []
    for item in batch.items:
        ready = item.finalization_status == STATUS_READY
        records.append(
            FinalizationDryRunItemRecord(
                item_id=item.item_id,
                source_filename=item.source_filename,
                source_sha256=item.source_hash_at_decision,
                preview_sha256=None,
                approved_preview_filename=item.approved_preview_filename,
                target_preview_path=item.target_preview_path,
                review_decision=item.review_decision_type,
                finalization_status=item.finalization_status,
                finalization_blockers=item.blockers,
                finalization_warnings=item.warnings,
                conflicts=_conflicts_for_item(item.item_id, batch.conflicts),
                ready_for_future_finalization=ready,
                final_write_allowed=False,
                # Plan text only — never executed.
                would_copy_or_rename_source_to_target=ready,
            )
        )
    return tuple(records)


def validate_finalization_dry_run_paths(
    output_root: Path | str | None,
    *,
    package_root: Path | str | None = None,
    input_root: Path | str | None = None,
    final_write_allowed: bool = False,
    productive_mode_requested: bool = False,
    call_run_once: bool = False,
) -> str | None:
    """Return an error message when dry-run package paths/flags are unsafe."""

    if final_write_allowed:
        return MSG_FINAL_WRITE_REJECTED
    if productive_mode_requested or call_run_once:
        return MSG_PRODUCTIVE_REJECTED
    output_path = _norm_path(output_root)
    if output_path is None:
        return MSG_NEEDS_OUTPUT
    if path_has_forbidden_productive_marker(str(output_path)):
        return MSG_BLOCKED_PATH
    if path_looks_like_original(str(output_path)):
        return MSG_BLOCKED_PATH
    if not is_explicit_copied_sandbox_test_path(str(output_path)):
        return MSG_BLOCKED_PATH
    if input_root is not None:
        input_path = _norm_path(input_root)
        if input_path is not None:
            if path_has_forbidden_productive_marker(str(input_path)):
                return MSG_BLOCKED_PATH
            if path_looks_like_original(str(input_path)):
                return MSG_BLOCKED_PATH
    if package_root is not None:
        package_path = _norm_path(package_root)
        if package_path is None:
            return MSG_PACKAGE_OUTSIDE_OUTPUT
        try:
            if not package_path.is_relative_to(output_path):
                return MSG_PACKAGE_OUTSIDE_OUTPUT
        except (OSError, ValueError):
            return MSG_PACKAGE_OUTSIDE_OUTPUT
        if path_has_forbidden_productive_marker(str(package_path)):
            return MSG_BLOCKED_PATH
    return None


def _readme_text(package: FinalizationDryRunPackage) -> str:
    return "\n".join(
        [
            f"# {MSG_DRY_RUN_TITLE}",
            "",
            "Dieses Paket ist ein **Trockenlauf / Dry Run**.",
            f"- {MSG_NO_FINAL_PRODUCTION}",
            f"- {MSG_ORIGINALS_UNCHANGED}",
            f"- {MSG_NO_FINAL_PDFS}",
            f"- {MSG_FINAL_WRITE_FALSE}",
            f"- dry_run_package=true",
            f"- productive_mode_requested=false",
            f"- source_mutation=false",
            f"- {MSG_LATER_AUTHORIZATION}",
            f"- {MSG_NO_SAAS_READY}",
            f"- {MSG_NO_PRODUCTION_READY}",
            "",
            "## Identifiers",
            f"- package_id: `{package.package_id}`",
            f"- batch_id: `{package.batch_id}`",
            f"- preview_state_id: `{package.preview_state_id}`",
            f"- source_run_id: `{package.source_run_id or ''}`",
            f"- created_at: `{package.created_at}`",
            "",
            "## Paths",
            f"- input_root: `{package.input_root or ''}`",
            f"- output_root: `{package.output_root or ''}`",
            f"- package_root: `{package.package_root or ''}`",
            "",
            "## Counts",
            f"- total_items: {package.total_items}",
            f"- ready_count: {package.ready_count}",
            f"- blocked_count: {package.blocked_count}",
            f"- ignored_count: {package.ignored_count}",
            f"- deferred_count: {package.deferred_count}",
            f"- still_review_required_count: {package.still_review_required_count}",
            "",
            "## Safety proof",
            f"- final_files_written: {str(package.final_files_written).lower()}",
            f"- originals_moved: {str(package.originals_moved).lower()}",
            f"- originals_renamed: {str(package.originals_renamed).lower()}",
            f"- originals_archived: {str(package.originals_archived).lower()}",
            f"- originals_deleted: {str(package.originals_deleted).lower()}",
            "",
            package.safety_summary,
            "",
        ]
    )


def _audit_text(package: FinalizationDryRunPackage) -> str:
    lines = [
        "# Finalization Audit",
        "",
        "## Safety flags",
        f"- dry_run_package: true",
        f"- final_write_allowed: false",
        f"- productive_mode_requested: false",
        f"- source_mutation: false",
        f"- final_files_written: false",
        f"- originals_moved: false",
        f"- originals_renamed: false",
        f"- originals_archived: false",
        f"- originals_deleted: false",
        f"- no final files written",
        f"- no originals moved",
        f"- no originals renamed",
        f"- no originals archived",
        f"- no originals deleted",
        f"- no run_once productive path",
        f"- no real invoice folders",
        "",
        "## Roots",
        f"- output_root: `{package.output_root or ''}`",
        f"- package_root: `{package.package_root or ''}`",
        f"- input_root: `{package.input_root or ''}`",
        "",
        "## No final write proof",
        "- Package contains markdown/json/csv audit artifacts only.",
        "- No final renamed production PDFs were written.",
        "- Planned operations in finalization-plan.md were not executed.",
        "",
        "## Items",
    ]
    for item in package.items:
        lines.extend(
            [
                f"### {item.source_filename or item.item_id}",
                f"- source_sha256: `{item.source_sha256 or ''}`",
                f"- preview_sha256: `{item.preview_sha256 or ''}`",
                f"- review_decision: `{item.review_decision or ''}`",
                f"- finalization_status: `{item.finalization_status}`",
                f"- ready_for_future_finalization: "
                f"{'yes' if item.ready_for_future_finalization else 'no'}",
                f"- blockers: {', '.join(item.finalization_blockers) or '—'}",
                f"- warnings: {', '.join(item.finalization_warnings) or '—'}",
                f"- conflicts: {', '.join(item.conflicts) or '—'}",
                f"- final_write_allowed: false",
                "",
            ]
        )
    return "\n".join(lines)


def _plan_text(package: FinalizationDryRunPackage) -> str:
    lines = [
        "# Finalization Plan (text only — not executed)",
        "",
        "Diese Datei beschreibt geplante spätere Operationen als Text.",
        "Es wurden **keine** Copy/Rename/Move/Archive/Delete-Operationen ausgeführt.",
        f"{MSG_FINAL_WRITE_FALSE}",
        "",
    ]
    for item in package.items:
        lines.extend(
            [
                f"## {item.source_filename or item.item_id}",
                f"- would_copy_or_rename_source_to_target: "
                f"{str(item.would_copy_or_rename_source_to_target).lower()}",
                f"- source: `{item.source_filename}`",
                f"- target_preview_path: `{item.target_preview_path or ''}`",
                f"- approved_preview_filename: `{item.approved_preview_filename or ''}`",
                f"- status: `{item.finalization_status}`",
                f"- blockers: {', '.join(item.finalization_blockers) or '—'}",
                f"- executed: false",
                "",
            ]
        )
    if not package.items:
        lines.append("_Keine Items im Batch._")
        lines.append("")
    return "\n".join(lines)


def _conflicts_text(package: FinalizationDryRunPackage) -> str:
    lines = [
        "# Conflicts",
        "",
        f"Anzahl Konflikte: {len(package.conflicts)}",
        "",
    ]
    if not package.conflicts:
        lines.append("_Keine Konflikte gemeldet._")
        lines.append("")
        return "\n".join(lines)
    for conflict in package.conflicts:
        lines.extend(
            [
                f"## {conflict.get('conflict_type', 'conflict')}",
                f"- conflict_id: `{conflict.get('conflict_id', '')}`",
                f"- severity: `{conflict.get('severity', '')}`",
                f"- blocking: `{conflict.get('blocking', False)}`",
                f"- message: {conflict.get('message', '')}",
                f"- affected_item_ids: "
                f"{', '.join(conflict.get('affected_item_ids') or [])}",
                f"- suggested_resolution: {conflict.get('suggested_resolution', '')}",
                "",
            ]
        )
    return "\n".join(lines)


def _status_items_text(
    title: str,
    package: FinalizationDryRunPackage,
    status: str,
) -> str:
    rows = [item for item in package.items if item.finalization_status == status]
    lines = [f"# {title}", "", f"Anzahl: {len(rows)}", ""]
    if not rows:
        lines.append("_Keine Einträge._")
        lines.append("")
        return "\n".join(lines)
    for item in rows:
        lines.extend(
            [
                f"## {item.source_filename or item.item_id}",
                f"- review_decision: `{item.review_decision or ''}`",
                f"- approved_preview_filename: `{item.approved_preview_filename or ''}`",
                f"- target_preview_path: `{item.target_preview_path or ''}`",
                f"- blockers: {', '.join(item.finalization_blockers) or '—'}",
                f"- warnings: {', '.join(item.finalization_warnings) or '—'}",
                f"- ready_for_future_finalization: "
                f"{'yes' if item.ready_for_future_finalization else 'no'}",
                f"- final_write_allowed: false",
                "",
            ]
        )
    return "\n".join(lines)


def _manifest_csv(package: FinalizationDryRunPackage) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "item_id",
            "source_filename",
            "source_sha256",
            "preview_sha256",
            "approved_preview_filename",
            "target_preview_path",
            "review_decision",
            "finalization_status",
            "finalization_blockers",
            "finalization_warnings",
            "conflicts",
            "ready_for_future_finalization",
            "final_write_allowed",
            "would_copy_or_rename_source_to_target",
        ]
    )
    for item in package.items:
        writer.writerow(
            [
                item.item_id,
                item.source_filename,
                item.source_sha256 or "",
                item.preview_sha256 or "",
                item.approved_preview_filename or "",
                item.target_preview_path or "",
                item.review_decision or "",
                item.finalization_status,
                "|".join(item.finalization_blockers),
                "|".join(item.finalization_warnings),
                "|".join(item.conflicts),
                "yes" if item.ready_for_future_finalization else "no",
                "false",
                "true" if item.would_copy_or_rename_source_to_target else "false",
            ]
        )
    return buffer.getvalue()


def build_finalization_dry_run_package_model(
    batch: FinalizationPreviewBatch,
    *,
    package_id: str | None = None,
    package_root: str | None = None,
    created_at: str | None = None,
) -> FinalizationDryRunPackage:
    """Build the in-memory dry-run package model from a preview batch."""

    items = _item_records(batch)
    artifacts = (
        ARTIFACT_README,
        ARTIFACT_MANIFEST_JSON,
        ARTIFACT_MANIFEST_CSV,
        ARTIFACT_AUDIT,
        ARTIFACT_PLAN,
        ARTIFACT_CONFLICTS,
        ARTIFACT_BLOCKED,
        ARTIFACT_READY,
        ARTIFACT_IGNORED,
        ARTIFACT_DEFERRED,
        ARTIFACT_STILL_REVIEW,
    )
    package = FinalizationDryRunPackage(
        package_id=package_id or _new_package_id(),
        batch_id=batch.batch_id,
        preview_state_id=batch.preview_state_id,
        source_run_id=batch.source_run_id,
        created_at=created_at or _utc_now(),
        input_root=batch.input_root,
        output_root=batch.output_root,
        package_root=package_root,
        dry_run_package=True,
        final_write_allowed=False,
        productive_mode_requested=False,
        source_mutation=False,
        final_files_written=False,
        originals_moved=False,
        originals_renamed=False,
        originals_archived=False,
        originals_deleted=False,
        total_items=batch.total_items,
        ready_count=batch.ready_count,
        blocked_count=batch.blocked_count,
        ignored_count=batch.ignored_count,
        deferred_count=batch.deferred_count,
        still_review_required_count=batch.still_review_required_count,
        artifacts=artifacts,
        safety_summary=MSG_SAFETY_SUMMARY,
        items=items,
        conflicts=tuple(c.to_dict() for c in batch.conflicts),
    )
    assert package.dry_run_package is True
    assert package.final_write_allowed is False
    assert package.source_mutation is False
    assert package.final_files_written is False
    return package


def write_finalization_dry_run_package(
    batch: FinalizationPreviewBatch | None,
    *,
    output_root: Path | str | None,
    input_root: Path | str | None = None,
    package_root: Path | str | None = None,
    final_write_allowed: bool = False,
    productive_mode_requested: bool = False,
    call_run_once: bool = False,
    preview_state_fresh: bool = True,
) -> FinalizationDryRunPackageResult:
    """Write audit/plan artifacts only under controlled sandbox output."""

    if final_write_allowed:
        return FinalizationDryRunPackageResult(
            ok=False,
            status="blocked",
            error=MSG_FINAL_WRITE_REJECTED,
            final_write_allowed=False,
            productive_mode_requested=bool(productive_mode_requested),
        )
    if productive_mode_requested or call_run_once:
        return FinalizationDryRunPackageResult(
            ok=False,
            status="blocked",
            error=MSG_PRODUCTIVE_REJECTED,
            productive_mode_requested=bool(productive_mode_requested),
        )
    if batch is None:
        return FinalizationDryRunPackageResult(
            ok=False,
            status="blocked",
            error=MSG_NEEDS_BATCH,
        )
    if not preview_state_fresh:
        return FinalizationDryRunPackageResult(
            ok=False,
            status="blocked",
            error=MSG_STALE_PREVIEW,
        )

    output_path = _norm_path(output_root) or _norm_path(batch.output_root)
    input_path = _norm_path(input_root) or _norm_path(batch.input_root)
    path_error = validate_finalization_dry_run_paths(
        output_path,
        package_root=package_root,
        input_root=input_path,
        final_write_allowed=False,
        productive_mode_requested=False,
        call_run_once=False,
    )
    if path_error:
        return FinalizationDryRunPackageResult(
            ok=False,
            status="blocked",
            error=path_error,
        )
    assert output_path is not None

    package_id = _new_package_id()
    run_token = _safe_token(batch.source_run_id, fallback=package_id)
    stamp = _stamp()
    if package_root is not None:
        target_root = _norm_path(package_root)
        assert target_root is not None
        # Re-validate containment after resolve.
        try:
            if not target_root.is_relative_to(output_path):
                return FinalizationDryRunPackageResult(
                    ok=False,
                    status="blocked",
                    error=MSG_PACKAGE_OUTSIDE_OUTPUT,
                )
        except (OSError, ValueError):
            return FinalizationDryRunPackageResult(
                ok=False,
                status="blocked",
                error=MSG_PACKAGE_OUTSIDE_OUTPUT,
            )
        # Folder name must still use the dry-run prefix when we create it.
        if not target_root.name.startswith(DRY_RUN_PACKAGE_FOLDER_PREFIX):
            target_root = (
                output_path
                / f"{DRY_RUN_PACKAGE_FOLDER_PREFIX}{run_token}-{package_id}-{stamp}"
            )
    else:
        target_root = (
            output_path
            / f"{DRY_RUN_PACKAGE_FOLDER_PREFIX}{run_token}-{package_id}-{stamp}"
        )

    try:
        if not target_root.resolve().is_relative_to(output_path):
            return FinalizationDryRunPackageResult(
                ok=False,
                status="blocked",
                error=MSG_PACKAGE_OUTSIDE_OUTPUT,
            )
    except (OSError, ValueError):
        return FinalizationDryRunPackageResult(
            ok=False,
            status="blocked",
            error=MSG_PACKAGE_OUTSIDE_OUTPUT,
        )
    if not target_root.name.startswith(DRY_RUN_PACKAGE_FOLDER_PREFIX):
        return FinalizationDryRunPackageResult(
            ok=False,
            status="blocked",
            error=MSG_BLOCKED_PATH,
        )

    try:
        output_path.mkdir(parents=True, exist_ok=True)
        target_root.mkdir(parents=False, exist_ok=False)
    except OSError as exc:
        return FinalizationDryRunPackageResult(
            ok=False,
            status="failed",
            error=f"Paketordner nicht nutzbar: {exc}",
        )

    batch_for_model = replace(
        batch,
        input_root=str(input_path) if input_path else batch.input_root,
        output_root=str(output_path),
        final_write_allowed=False,
        productive_mode_requested=False,
        source_mutation=False,
    )
    package = build_finalization_dry_run_package_model(
        batch_for_model,
        package_id=package_id,
        package_root=str(target_root),
    )

    files: dict[str, str] = {
        ARTIFACT_README: _readme_text(package),
        ARTIFACT_MANIFEST_JSON: json.dumps(
            package.to_dict(), ensure_ascii=False, indent=2
        )
        + "\n",
        ARTIFACT_MANIFEST_CSV: _manifest_csv(package),
        ARTIFACT_AUDIT: _audit_text(package),
        ARTIFACT_PLAN: _plan_text(package),
        ARTIFACT_CONFLICTS: _conflicts_text(package),
        ARTIFACT_BLOCKED: _status_items_text(
            "Blocked Items", package, STATUS_BLOCKED
        ),
        ARTIFACT_READY: _status_items_text("Ready Items", package, STATUS_READY),
        ARTIFACT_IGNORED: _status_items_text(
            "Ignored Items", package, STATUS_IGNORED
        ),
        ARTIFACT_DEFERRED: _status_items_text(
            "Deferred Items", package, STATUS_DEFERRED
        ),
        ARTIFACT_STILL_REVIEW: _status_items_text(
            "Still Review Required", package, STATUS_STILL_REVIEW
        ),
    }

    try:
        for name, content in files.items():
            (target_root / name).write_text(content, encoding="utf-8")
    except OSError as exc:
        return FinalizationDryRunPackageResult(
            ok=False,
            status="failed",
            error=f"Artefakt-Schreiben fehlgeschlagen: {exc}",
            package_root=target_root,
        )

    # Safety: never write PDF binaries into the dry-run package.
    pdf_written = any(path.suffix.lower() == ".pdf" for path in target_root.iterdir())
    if pdf_written:
        return FinalizationDryRunPackageResult(
            ok=False,
            status="failed",
            error="Unerwartete PDF-Datei im Dry-Run-Paket — Abbruch.",
            package_root=target_root,
        )

    return FinalizationDryRunPackageResult(
        ok=True,
        status="created",
        package=package,
        package_root=target_root,
        dry_run_package=True,
        final_write_allowed=False,
        productive_mode_requested=False,
        source_mutation=False,
        final_files_written=False,
        called_run_once=False,
        mutated_input=False,
        wrote_final_pdfs=False,
        touched_real_invoice_folders=False,
    )


def apply_finalization_dry_run_package(
    state: Any,
    *,
    preview_state_fresh: bool = True,
) -> FinalizationDryRunPackageResult:
    """UI helper: build batch (if needed) and write dry-run package under output."""

    bag = get_finalization_dry_run_package_bag(state)
    batch_bag = get_finalization_preview_batch_bag(state)
    batch = batch_bag.last_batch
    if batch is None:
        batch = build_finalization_preview_batch(state)
    output_root = (
        _text(getattr(state, "workspace_output_folder_override", None))
        or _text(getattr(batch, "output_root", None))
        or None
    )
    input_root = (
        _text(getattr(state, "workspace_input_folder_override", None))
        or _text(getattr(batch, "input_root", None))
        or None
    )
    result = write_finalization_dry_run_package(
        batch,
        output_root=output_root,
        input_root=input_root,
        final_write_allowed=False,
        productive_mode_requested=False,
        call_run_once=False,
        preview_state_fresh=preview_state_fresh,
    )
    bag.called_run_once = False
    bag.mutated_input = False
    bag.wrote_final_pdfs = False
    bag.touched_real_invoice_folders = False
    if result.ok and result.package is not None:
        bag.last_package = result.package
        bag.last_package_root = str(result.package_root or "")
        bag.last_feedback = (
            f"{MSG_CREATED}: {bag.last_package_root} · "
            f"ready={result.package.ready_count} blocked={result.package.blocked_count} · "
            f"{MSG_CTA_CHECK_ONLY} · {MSG_FINAL_WRITE_FALSE}"
        )
        bag.last_feedback_error = False
        try:
            state.workspace_last_finalization_dry_run_folder = bag.last_package_root
            state.workspace_finalization_dry_run_feedback = bag.last_feedback
            state.workspace_finalization_dry_run_feedback_error = False
        except Exception:
            pass
    else:
        err = result.error or "Finalisierungs-Trockenlauf fehlgeschlagen."
        bag.last_feedback = err
        bag.last_feedback_error = True
        try:
            state.workspace_finalization_dry_run_feedback = err
            state.workspace_finalization_dry_run_feedback_error = True
        except Exception:
            pass
    return result


def dry_run_package_report_fields(
    package: FinalizationDryRunPackage | None,
) -> dict[str, Any]:
    """Manifest-level dry-run package metadata for preview export."""

    if package is None:
        return {
            "finalization_dry_run_package_available": False,
            "finalization_dry_run_package_path": None,
            "finalization_dry_run_package_id": None,
            "final_write_allowed": False,
            "dry_run_package": True,
        }
    return {
        "finalization_dry_run_package_available": True,
        "finalization_dry_run_package_path": package.package_root,
        "finalization_dry_run_package_id": package.package_id,
        "final_write_allowed": False,
        "dry_run_package": True,
        "finalization_dry_run_package": {
            "package_id": package.package_id,
            "batch_id": package.batch_id,
            "preview_state_id": package.preview_state_id,
            "source_run_id": package.source_run_id,
            "package_root": package.package_root,
            "ready_count": package.ready_count,
            "blocked_count": package.blocked_count,
            "ignored_count": package.ignored_count,
            "deferred_count": package.deferred_count,
            "still_review_required_count": package.still_review_required_count,
            "final_write_allowed": False,
            "dry_run_package": True,
            "source_mutation": False,
            "final_files_written": False,
        },
    }


def dry_run_package_summary_lines(
    package: FinalizationDryRunPackage | None,
) -> tuple[str, ...]:
    if package is None:
        return (
            MSG_DRY_RUN_TITLE,
            MSG_CTA_CHECK_ONLY,
            MSG_FINAL_WRITE_FALSE,
            "Paket noch nicht erzeugt.",
        )
    return (
        MSG_DRY_RUN_TITLE,
        MSG_CTA_CREATE_DRY_RUN,
        MSG_CTA_CREATE_AUDIT,
        MSG_CTA_CHECK_ONLY,
        f"ready: {package.ready_count} · blocked: {package.blocked_count}",
        f"Paket: {package.package_root or ''}",
        MSG_FINAL_WRITE_FALSE,
        MSG_NO_FINAL_PDFS,
        MSG_ORIGINALS_UNCHANGED,
    )


def dry_run_package_calls_run_once() -> bool:
    return False


def dry_run_package_mutates_input() -> bool:
    return False


def dry_run_package_writes_final_pdfs() -> bool:
    return False


def dry_run_package_moves_originals() -> bool:
    return False


def dry_run_package_renames_originals() -> bool:
    return False


def dry_run_package_archives_originals() -> bool:
    return False


def dry_run_package_deletes_originals() -> bool:
    return False


def dry_run_package_touches_real_invoice_folders() -> bool:
    return False


def dry_run_package_claims_saas_ready() -> bool:
    return False


def dry_run_package_claims_production_ready() -> bool:
    return False


__all__ = (
    "ARTIFACT_AUDIT",
    "ARTIFACT_BLOCKED",
    "ARTIFACT_CONFLICTS",
    "ARTIFACT_DEFERRED",
    "ARTIFACT_IGNORED",
    "ARTIFACT_MANIFEST_CSV",
    "ARTIFACT_MANIFEST_JSON",
    "ARTIFACT_PLAN",
    "ARTIFACT_READY",
    "ARTIFACT_README",
    "ARTIFACT_STILL_REVIEW",
    "DRY_RUN_PACKAGE_FOLDER_PREFIX",
    "DRY_RUN_PACKAGE_KIND",
    "FinalizationDryRunItemRecord",
    "FinalizationDryRunPackage",
    "FinalizationDryRunPackageBag",
    "FinalizationDryRunPackageResult",
    "MSG_CTA_CHECK_ONLY",
    "MSG_CTA_CREATE_AUDIT",
    "MSG_CTA_CREATE_DRY_RUN",
    "MSG_DRY_RUN_TITLE",
    "MSG_FINAL_WRITE_FALSE",
    "MSG_NO_FINAL_PDFS",
    "MSG_NO_FINAL_PRODUCTION",
    "MSG_ORIGINALS_UNCHANGED",
    "MSG_SAFETY_SUMMARY",
    "apply_finalization_dry_run_package",
    "build_finalization_dry_run_package_model",
    "dry_run_package_archives_originals",
    "dry_run_package_calls_run_once",
    "dry_run_package_claims_production_ready",
    "dry_run_package_claims_saas_ready",
    "dry_run_package_deletes_originals",
    "dry_run_package_moves_originals",
    "dry_run_package_mutates_input",
    "dry_run_package_renames_originals",
    "dry_run_package_report_fields",
    "dry_run_package_summary_lines",
    "dry_run_package_touches_real_invoice_folders",
    "dry_run_package_writes_final_pdfs",
    "get_finalization_dry_run_package_bag",
    "validate_finalization_dry_run_paths",
    "write_finalization_dry_run_package",
)
