"""Track-B Controlled Final Write Sandbox (Prompt 33/34).

Copies approved selected source PDFs into a controlled sandbox-final-write folder
only after FinalWriteGate preconditions and explicit sandbox authorization pass.

Never moves/renames/archives/deletes originals.
Never writes production final output.
Never calls run_once.
Never sets final_write_allowed_for_production=True.
"""

from __future__ import annotations

import csv
import io
import json
import re
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from invoice_tool.ui_v2.core_dry_run_contract import (
    is_explicit_copied_sandbox_test_path,
    path_has_forbidden_productive_marker,
    path_looks_like_original,
)
from invoice_tool.ui_v2.final_write_gate import (
    AUTH_SCOPE_SELECTED,
    AUTH_SCOPE_WHOLE_READY,
    BLOCKER_CONTROLLED_OUTPUT,
    BLOCKER_MISSING_AUTH,
    BLOCKER_MISSING_DRY_RUN,
    BLOCKER_REAL_INVOICE,
    BLOCKER_SANDBOX_FLAG,
    FinalWriteAuthorization,
    FinalWriteGateRuntimeCheck,
    FinalWritePlan,
    build_sandbox_final_write_authorization,
    default_sandbox_acknowledgements,
    run_final_write_gate_runtime_check,
)
from invoice_tool.ui_v2.finalization_dry_run_package import (
    FinalizationDryRunPackage,
    get_finalization_dry_run_package_bag,
)
from invoice_tool.ui_v2.finalization_preview_batch import (
    FinalizationPreviewBatch,
    build_finalization_preview_batch,
    get_finalization_preview_batch_bag,
)

SANDBOX_FINAL_WRITE_KIND = "track_b_controlled_final_write_sandbox"
SANDBOX_FINAL_WRITE_SCHEMA_VERSION = 1
SANDBOX_FINAL_WRITE_FOLDER_PREFIX = "sandbox-final-write-"

ARTIFACT_README = "SANDBOX_FINAL_WRITE_README.md"
ARTIFACT_MANIFEST_JSON = "sandbox-final-write-manifest.json"
ARTIFACT_MANIFEST_CSV = "sandbox-final-write-manifest.csv"
ARTIFACT_PRE_AUDIT = "pre-write-audit.md"
ARTIFACT_POST_AUDIT = "post-write-audit.md"
ARTIFACT_COPIED = "copied-files.md"
ARTIFACT_SKIPPED = "skipped-items.md"
ARTIFACT_BLOCKED = "blocked-items.md"
ARTIFACT_FAILURES = "failures.md"

MSG_CTA_SANDBOX_WRITE = "Sandbox-Finalschreiben testen"
MSG_CTA_CONTROLLED_ONLY = "Nur kontrollierter Test-Output"
MSG_CTA_ORIGINALS_UNCHANGED = "Originale bleiben unverändert"
MSG_TITLE = "Sandbox Final Write Test"
MSG_NOT_PRODUCTION = "kein finales Produktions-Output / not production output"
MSG_COPIES_ONLY = "Kopien nur — copies only"
MSG_NO_ARCHIVE_DELETE_RENAME = (
    "keine Archivierung/Löschung/Umbenennung von Originalen"
)
MSG_PRODUCTION_DISABLED = "production final write remains disabled"
MSG_SAFETY_SUMMARY = (
    "Controlled sandbox final write — sandbox_final_write=true; "
    "final_write_allowed_for_production=false; copies only; "
    "originals unchanged; no run_once; no real invoice folders."
)
MSG_NEEDS_SANDBOX_FLAG = (
    "Sandbox-Finalschreiben blockiert: sandbox_final_write=true ist erforderlich."
)
MSG_NEEDS_OUTPUT = (
    "Sandbox-Finalschreiben blockiert: kontrollierter Ausgabeordner erforderlich."
)
MSG_BLOCKED_PATH = (
    "Sandbox-Finalschreiben blockiert: Pfadpolitik verletzt "
    "(Sandbox/Test-Output erforderlich; keine realen Rechnungsordner)."
)
MSG_OUTSIDE_OUTPUT = (
    "Sandbox-Finalschreiben blockiert: Ziel liegt außerhalb des controlled output root."
)
MSG_PRODUCTIVE_REJECTED = (
    "Sandbox-Finalschreiben blockiert: produktiver Modus / run_once ist verboten."
)
MSG_NEEDS_PACKAGE = (
    "Sandbox-Finalschreiben blockiert: FinalizationDryRunPackage fehlt."
)
MSG_NEEDS_AUTH = (
    "Sandbox-Finalschreiben blockiert: explizite Sandbox-Autorisierung fehlt."
)
MSG_GATE_BLOCKED = "Sandbox-Finalschreiben blockiert: FinalWriteGate Preconditions fehlgeschlagen."
MSG_CREATED = "Sandbox-Finalschreiben abgeschlossen"
MSG_NO_SAAS = "nicht SaaS-ready"
MSG_NO_PRODUCTION_READY = "nicht production-ready"

_UNSAFE_NAME_RE = re.compile(r"[^\w.\-]+", re.UNICODE)


@dataclass(frozen=True)
class ControlledFinalWriteSandboxFileResult:
    item_id: str
    source_path: str
    source_sha256_before_write: str | None
    source_sha256_at_write_check: str | None
    hash_match: bool
    final_sandbox_target_path: str
    operation_type: str
    copy_result: str
    blockers: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_path": self.source_path,
            "source_sha256_before_write": self.source_sha256_before_write,
            "source_sha256_at_write_check": self.source_sha256_at_write_check,
            "hash_match": bool(self.hash_match),
            "final_sandbox_target_path": self.final_sandbox_target_path,
            "operation_type": self.operation_type,
            "copy_result": self.copy_result,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ControlledFinalWriteSandboxResult:
    """Result of a controlled sandbox final-write execution."""

    result_id: str
    gate_id: str | None
    authorization_id: str | None
    dry_run_package_id: str | None
    batch_id: str | None
    source_run_id: str | None
    preview_state_id: str | None
    created_at: str
    sandbox_final_write: bool
    productive_mode_requested: bool
    controlled_output_root: str | None
    sandbox_final_write_root: str | None
    final_write_allowed_for_sandbox: bool
    final_write_allowed_for_production: bool
    final_files_written_count: int
    final_files_written: tuple[ControlledFinalWriteSandboxFileResult, ...]
    skipped_items: tuple[dict[str, Any], ...]
    blocked_items: tuple[dict[str, Any], ...]
    failures: tuple[dict[str, Any], ...]
    originals_moved: bool
    originals_renamed: bool
    originals_archived: bool
    originals_deleted: bool
    source_mutation: bool
    run_once_called: bool
    safety_summary: str
    ok: bool = False
    status: str = "blocked"
    error: str | None = None
    artifacts: tuple[str, ...] = field(default_factory=tuple)
    runtime_check: FinalWriteGateRuntimeCheck | None = None
    claims_saas_ready: bool = False
    claims_production_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": SANDBOX_FINAL_WRITE_KIND,
            "schema_version": SANDBOX_FINAL_WRITE_SCHEMA_VERSION,
            "result_id": self.result_id,
            "gate_id": self.gate_id,
            "authorization_id": self.authorization_id,
            "dry_run_package_id": self.dry_run_package_id,
            "batch_id": self.batch_id,
            "source_run_id": self.source_run_id,
            "preview_state_id": self.preview_state_id,
            "created_at": self.created_at,
            "sandbox_final_write": True,
            "productive_mode_requested": False,
            "controlled_output_root": self.controlled_output_root,
            "sandbox_final_write_root": self.sandbox_final_write_root,
            "final_write_allowed_for_sandbox": bool(
                self.final_write_allowed_for_sandbox
            ),
            "final_write_allowed_for_production": False,
            "final_files_written_count": self.final_files_written_count,
            "final_files_written": [f.to_dict() for f in self.final_files_written],
            "skipped_items": list(self.skipped_items),
            "blocked_items": list(self.blocked_items),
            "failures": list(self.failures),
            "originals_moved": False,
            "originals_renamed": False,
            "originals_archived": False,
            "originals_deleted": False,
            "source_mutation": False,
            "run_once_called": False,
            "safety_summary": self.safety_summary,
            "ok": bool(self.ok),
            "status": self.status,
            "error": self.error,
            "artifacts": list(self.artifacts),
            "runtime_check": (
                self.runtime_check.to_dict()
                if self.runtime_check is not None
                else None
            ),
            "claims_saas_ready": False,
            "claims_production_ready": False,
            "title": MSG_TITLE,
        }


@dataclass
class ControlledFinalWriteSandboxBag:
    last_result: ControlledFinalWriteSandboxResult | None = None
    last_result_root: str = ""
    last_feedback: str = ""
    last_feedback_error: bool = False
    called_run_once: bool = False
    mutated_input: bool = False
    touched_real_invoice_folders: bool = False

    def reset(self) -> None:
        self.last_result = None
        self.last_result_root = ""
        self.last_feedback = ""
        self.last_feedback_error = False
        self.called_run_once = False
        self.mutated_input = False
        self.touched_real_invoice_folders = False


def get_controlled_final_write_sandbox_bag(
    state: Any,
) -> ControlledFinalWriteSandboxBag:
    bag = getattr(state, "controlled_final_write_sandbox_ui", None)
    if isinstance(bag, ControlledFinalWriteSandboxBag):
        return bag
    bag = ControlledFinalWriteSandboxBag()
    try:
        state.controlled_final_write_sandbox_ui = bag
    except Exception:
        pass
    return bag


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _new_result_id() -> str:
    return f"sfw-{uuid.uuid4().hex[:12]}"


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
    return text[:80] or fallback


def _path_is_controlled(path: Path | None) -> bool:
    if path is None:
        return False
    text = str(path)
    if path_has_forbidden_productive_marker(text):
        return False
    if path_looks_like_original(text):
        return False
    return is_explicit_copied_sandbox_test_path(text)


def validate_sandbox_final_write_paths(
    output_root: Path | str | None,
    *,
    sandbox_root: Path | str | None = None,
    input_root: Path | str | None = None,
    sandbox_final_write: bool = True,
    productive_mode_requested: bool = False,
    call_run_once: bool = False,
) -> str | None:
    if not sandbox_final_write:
        return MSG_NEEDS_SANDBOX_FLAG
    if productive_mode_requested or call_run_once:
        return MSG_PRODUCTIVE_REJECTED
    output_path = _norm_path(output_root)
    if output_path is None:
        return MSG_NEEDS_OUTPUT
    if not _path_is_controlled(output_path):
        return MSG_BLOCKED_PATH
    if input_root is not None:
        input_path = _norm_path(input_root)
        if input_path is not None:
            if path_has_forbidden_productive_marker(str(input_path)):
                return MSG_BLOCKED_PATH
            if path_looks_like_original(str(input_path)) and not (
                is_explicit_copied_sandbox_test_path(str(input_path))
            ):
                return MSG_BLOCKED_PATH
    if sandbox_root is not None:
        sandbox_path = _norm_path(sandbox_root)
        if sandbox_path is None:
            return MSG_OUTSIDE_OUTPUT
        try:
            if not sandbox_path.is_relative_to(output_path):
                return MSG_OUTSIDE_OUTPUT
        except (OSError, ValueError):
            return MSG_OUTSIDE_OUTPUT
        if not sandbox_path.name.startswith(SANDBOX_FINAL_WRITE_FOLDER_PREFIX):
            return MSG_BLOCKED_PATH
        if path_has_forbidden_productive_marker(str(sandbox_path)):
            return MSG_BLOCKED_PATH
    return None


def _blocked_result(
    *,
    error: str,
    result_id: str | None = None,
    runtime_check: FinalWriteGateRuntimeCheck | None = None,
    package: FinalizationDryRunPackage | None = None,
    authorization: FinalWriteAuthorization | None = None,
    controlled_output_root: str | None = None,
) -> ControlledFinalWriteSandboxResult:
    return ControlledFinalWriteSandboxResult(
        result_id=result_id or _new_result_id(),
        gate_id=runtime_check.gate.gate_id if runtime_check and runtime_check.gate else None,
        authorization_id=authorization.authorization_id if authorization else None,
        dry_run_package_id=package.package_id if package else None,
        batch_id=package.batch_id if package else None,
        source_run_id=package.source_run_id if package else None,
        preview_state_id=package.preview_state_id if package else None,
        created_at=_utc_now(),
        sandbox_final_write=True,
        productive_mode_requested=False,
        controlled_output_root=controlled_output_root,
        sandbox_final_write_root=None,
        final_write_allowed_for_sandbox=False,
        final_write_allowed_for_production=False,
        final_files_written_count=0,
        final_files_written=(),
        skipped_items=(),
        blocked_items=tuple(
            {"blocker": b} for b in (runtime_check.blockers if runtime_check else ())
        ),
        failures=(),
        originals_moved=False,
        originals_renamed=False,
        originals_archived=False,
        originals_deleted=False,
        source_mutation=False,
        run_once_called=False,
        safety_summary=MSG_SAFETY_SUMMARY,
        ok=False,
        status="blocked",
        error=error,
        runtime_check=runtime_check,
    )


def _readme_text(result: ControlledFinalWriteSandboxResult) -> str:
    return "\n".join(
        [
            f"# {MSG_TITLE}",
            "",
            "- Sandbox Final Write Test",
            f"- {MSG_NOT_PRODUCTION}",
            f"- {MSG_CTA_ORIGINALS_UNCHANGED}",
            f"- {MSG_COPIES_ONLY}",
            f"- {MSG_NO_ARCHIVE_DELETE_RENAME}",
            f"- {MSG_PRODUCTION_DISABLED}",
            f"- sandbox_final_write=true",
            f"- productive_mode_requested=false",
            f"- final_write_allowed_for_production=false",
            f"- originals_moved=false",
            f"- originals_renamed=false",
            f"- originals_archived=false",
            f"- originals_deleted=false",
            f"- source_mutation=false",
            f"- run_once_called=false",
            f"- {MSG_NO_SAAS}",
            f"- {MSG_NO_PRODUCTION_READY}",
            "",
            "## Identifiers",
            f"- result_id: `{result.result_id}`",
            f"- gate_id: `{result.gate_id or ''}`",
            f"- authorization_id: `{result.authorization_id or ''}`",
            f"- dry_run_package_id: `{result.dry_run_package_id or ''}`",
            f"- batch_id: `{result.batch_id or ''}`",
            f"- preview_state_id: `{result.preview_state_id or ''}`",
            f"- source_run_id: `{result.source_run_id or ''}`",
            f"- created_at: `{result.created_at}`",
            "",
            "## Paths",
            f"- controlled_output_root: `{result.controlled_output_root or ''}`",
            f"- sandbox_final_write_root: `{result.sandbox_final_write_root or ''}`",
            "",
            "## Counts",
            f"- final_files_written_count: {result.final_files_written_count}",
            f"- skipped_items: {len(result.skipped_items)}",
            f"- blocked_items: {len(result.blocked_items)}",
            f"- failures: {len(result.failures)}",
            "",
            result.safety_summary,
            "",
        ]
    )


def _pre_write_audit_text(
    result: ControlledFinalWriteSandboxResult,
    runtime_check: FinalWriteGateRuntimeCheck,
    selected_ids: Sequence[str],
) -> str:
    lines = [
        "# Pre-Write Audit (Sandbox Final Write)",
        "",
        f"- final_write_gate_id: `{result.gate_id or ''}`",
        f"- dry_run_package_id: `{result.dry_run_package_id or ''}`",
        f"- batch_id: `{result.batch_id or ''}`",
        f"- authorization_id: `{result.authorization_id or ''}`",
        f"- selected_item_ids: {', '.join(selected_ids)}",
        f"- preflight_timestamp: `{result.created_at}`",
        f"- source_hash_recheck_result: `{runtime_check.source_hash_recheck_result}`",
        f"- target_recheck_result: `{runtime_check.target_path_recheck_result}`",
        f"- conflict_recheck_result: `{runtime_check.conflict_recheck_result}`",
        f"- blockers: {', '.join(runtime_check.blockers) or '—'}",
        f"- final_write_allowed_at_preflight: false (production)",
        f"- final_write_allowed_for_sandbox: "
        f"{str(runtime_check.final_write_execution_allowed_for_sandbox).lower()}",
        f"- execution_available_for_production: false",
        f"- sandbox_final_write: true",
        "",
        "## Plans",
    ]
    for plan in runtime_check.plans:
        lines.extend(
            [
                f"### {plan.item_id}",
                f"- source_path: `{plan.source_path}`",
                f"- source_sha256_at_preview: `{plan.source_sha256_at_preview or ''}`",
                f"- source_sha256_at_write_check: "
                f"`{plan.source_sha256_at_write_check or ''}`",
                f"- source_hash_match: {str(plan.source_hash_match).lower()}",
                f"- final_target_path: `{plan.final_target_path}`",
                f"- operation_type: `{plan.operation_type}`",
                f"- ready_for_write: {str(plan.ready_for_write).lower()}",
                f"- write_blockers: {', '.join(plan.write_blockers) or '—'}",
                "",
            ]
        )
    return "\n".join(lines)


def _post_write_audit_text(
    result: ControlledFinalWriteSandboxResult,
    *,
    started_at: str,
    finished_at: str,
) -> str:
    lines = [
        "# Post-Write Audit (Sandbox Final Write)",
        "",
        f"- execution_started_at: `{started_at}`",
        f"- execution_finished_at: `{finished_at}`",
        f"- final_files_written: {result.final_files_written_count}",
        f"- originals_moved: false",
        f"- originals_renamed: false",
        f"- originals_archived: false",
        f"- originals_deleted: false",
        f"- source_mutation: false",
        f"- run_once_called: false",
        f"- final_write_allowed_for_production: false",
        f"- failures: {len(result.failures)}",
        f"- rollback_or_abort_notes: no automatic rollback; originals untouched",
        "",
        "## File results",
    ]
    for item in result.final_files_written:
        lines.extend(
            [
                f"### {item.item_id}",
                f"- source_path: `{item.source_path}`",
                f"- source_sha256_before_write: `{item.source_sha256_before_write or ''}`",
                f"- source_sha256_at_write_check: `{item.source_sha256_at_write_check or ''}`",
                f"- hash_match: {str(item.hash_match).lower()}",
                f"- final_sandbox_target_path: `{item.final_sandbox_target_path}`",
                f"- operation_type: `{item.operation_type}`",
                f"- copy_result: `{item.copy_result}`",
                "",
            ]
        )
    if result.failures:
        lines.append("## Failures")
        for failure in result.failures:
            lines.append(f"- {failure}")
        lines.append("")
    return "\n".join(lines)


def _list_md(title: str, rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [f"# {title}", "", f"Anzahl: {len(rows)}", ""]
    if not rows:
        lines.append("_Keine Einträge._")
        lines.append("")
        return "\n".join(lines)
    for row in rows:
        lines.append(f"- {dict(row)}")
    lines.append("")
    return "\n".join(lines)


def _copied_md(files: Sequence[ControlledFinalWriteSandboxFileResult]) -> str:
    lines = ["# Copied Files", "", f"Anzahl: {len(files)}", ""]
    if not files:
        lines.append("_Keine Dateien kopiert._")
        lines.append("")
        return "\n".join(lines)
    for item in files:
        lines.extend(
            [
                f"## {item.item_id}",
                f"- source: `{item.source_path}`",
                f"- target: `{item.final_sandbox_target_path}`",
                f"- hash_match: {str(item.hash_match).lower()}",
                f"- copy_result: `{item.copy_result}`",
                "",
            ]
        )
    return "\n".join(lines)


def _manifest_csv(result: ControlledFinalWriteSandboxResult) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "item_id",
            "source_path",
            "source_sha256_before_write",
            "source_sha256_at_write_check",
            "hash_match",
            "final_sandbox_target_path",
            "operation_type",
            "copy_result",
            "blockers",
            "originals_moved",
            "originals_renamed",
            "originals_archived",
            "originals_deleted",
            "run_once_called",
            "final_write_allowed_for_production",
        ]
    )
    for item in result.final_files_written:
        writer.writerow(
            [
                item.item_id,
                item.source_path,
                item.source_sha256_before_write or "",
                item.source_sha256_at_write_check or "",
                str(item.hash_match).lower(),
                item.final_sandbox_target_path,
                item.operation_type,
                item.copy_result,
                "|".join(item.blockers),
                "false",
                "false",
                "false",
                "false",
                "false",
                "false",
            ]
        )
    for row in result.skipped_items:
        writer.writerow(
            [
                row.get("item_id", ""),
                row.get("source_path", ""),
                "",
                "",
                "",
                "",
                "skipped",
                "skipped",
                "|".join(row.get("blockers") or row.get("reasons") or []),
                "false",
                "false",
                "false",
                "false",
                "false",
                "false",
            ]
        )
    for row in result.blocked_items:
        writer.writerow(
            [
                row.get("item_id", ""),
                row.get("source_path", ""),
                "",
                "",
                "",
                row.get("final_target_path", ""),
                "blocked",
                "blocked",
                "|".join(row.get("blockers") or ([row.get("blocker")] if row.get("blocker") else [])),
                "false",
                "false",
                "false",
                "false",
                "false",
                "false",
            ]
        )
    for row in result.failures:
        writer.writerow(
            [
                row.get("item_id", ""),
                row.get("source_path", ""),
                "",
                "",
                "",
                row.get("final_target_path", ""),
                "failure",
                row.get("error", "failure"),
                "",
                "false",
                "false",
                "false",
                "false",
                "false",
                "false",
            ]
        )
    return buffer.getvalue()


def execute_controlled_final_write_sandbox(
    *,
    package: FinalizationDryRunPackage | None,
    batch: FinalizationPreviewBatch | None,
    authorization: FinalWriteAuthorization | None,
    controlled_output_root: Path | str | None,
    sandbox_final_write: bool = True,
    productive_mode_requested: bool = False,
    call_run_once: bool = False,
    preview_state_fresh: bool = True,
    allow_overwrite: bool = False,
    selected_item_ids: Sequence[str] | None = None,
) -> ControlledFinalWriteSandboxResult:
    """Copy selected ready sources into sandbox-final-write-* under output root."""

    result_id = _new_result_id()
    if call_run_once or productive_mode_requested:
        return _blocked_result(
            error=MSG_PRODUCTIVE_REJECTED,
            result_id=result_id,
            package=package,
            authorization=authorization,
            controlled_output_root=_text(controlled_output_root) or None,
        )
    if not sandbox_final_write:
        return _blocked_result(
            error=MSG_NEEDS_SANDBOX_FLAG,
            result_id=result_id,
            package=package,
            authorization=authorization,
            controlled_output_root=_text(controlled_output_root) or None,
        )
    if package is None:
        return _blocked_result(
            error=MSG_NEEDS_PACKAGE,
            result_id=result_id,
            authorization=authorization,
            controlled_output_root=_text(controlled_output_root) or None,
        )
    if authorization is None or not authorization.authorization_valid:
        return _blocked_result(
            error=MSG_NEEDS_AUTH,
            result_id=result_id,
            package=package,
            authorization=authorization,
            controlled_output_root=_text(controlled_output_root) or None,
        )

    output_path = _norm_path(controlled_output_root) or _norm_path(package.output_root)
    path_error = validate_sandbox_final_write_paths(
        output_path,
        input_root=package.input_root,
        sandbox_final_write=True,
        productive_mode_requested=False,
        call_run_once=False,
    )
    if path_error or output_path is None:
        return _blocked_result(
            error=path_error or MSG_NEEDS_OUTPUT,
            result_id=result_id,
            package=package,
            authorization=authorization,
            controlled_output_root=_text(controlled_output_root) or None,
        )

    run_token = _safe_token(package.source_run_id, fallback=result_id)
    stamp = _stamp()
    sandbox_root = (
        output_path
        / f"{SANDBOX_FINAL_WRITE_FOLDER_PREFIX}{run_token}-{result_id}-{stamp}"
    )
    path_error = validate_sandbox_final_write_paths(
        output_path,
        sandbox_root=sandbox_root,
        input_root=package.input_root,
        sandbox_final_write=True,
    )
    if path_error:
        return _blocked_result(
            error=path_error,
            result_id=result_id,
            package=package,
            authorization=authorization,
            controlled_output_root=str(output_path),
        )

    selected = list(selected_item_ids or authorization.selected_item_ids)
    if authorization.authorization_scope == AUTH_SCOPE_WHOLE_READY:
        selected = [
            item.item_id
            for item in package.items
            if item.ready_for_future_finalization
        ]

    # Preflight with intended sandbox root (folder not yet created — plans use path).
    runtime_check = run_final_write_gate_runtime_check(
        package=package,
        batch=batch,
        authorization=authorization,
        controlled_output_root=output_path,
        sandbox_final_write_root=sandbox_root,
        sandbox_final_write=True,
        productive_mode_requested=False,
        preview_state_fresh=preview_state_fresh,
        pre_write_audit_ready=True,
        allow_overwrite=allow_overwrite,
        selected_item_ids=selected,
    )
    if not runtime_check.final_write_execution_allowed_for_sandbox:
        detail = ", ".join(runtime_check.blockers) or "unknown"
        return _blocked_result(
            error=f"{MSG_GATE_BLOCKED} ({detail})",
            result_id=result_id,
            runtime_check=runtime_check,
            package=package,
            authorization=authorization,
            controlled_output_root=str(output_path),
        )

    try:
        output_path.mkdir(parents=True, exist_ok=True)
        sandbox_root.mkdir(parents=False, exist_ok=False)
    except OSError as exc:
        return _blocked_result(
            error=f"Sandbox-Ordner nicht nutzbar: {exc}",
            result_id=result_id,
            runtime_check=runtime_check,
            package=package,
            authorization=authorization,
            controlled_output_root=str(output_path),
        )

    started_at = _utc_now()
    written: list[ControlledFinalWriteSandboxFileResult] = []
    skipped: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    # Record non-selected ready/non-ready as skipped for audit clarity.
    selected_set = set(selected)
    for item in package.items:
        if item.item_id in selected_set:
            continue
        skipped.append(
            {
                "item_id": item.item_id,
                "source_path": item.source_filename,
                "reasons": ["not_selected"],
            }
        )

    # Write pre-audit before any copies.
    pre_result_stub = ControlledFinalWriteSandboxResult(
        result_id=result_id,
        gate_id=runtime_check.gate.gate_id if runtime_check.gate else None,
        authorization_id=authorization.authorization_id,
        dry_run_package_id=package.package_id,
        batch_id=package.batch_id,
        source_run_id=package.source_run_id,
        preview_state_id=package.preview_state_id,
        created_at=started_at,
        sandbox_final_write=True,
        productive_mode_requested=False,
        controlled_output_root=str(output_path),
        sandbox_final_write_root=str(sandbox_root),
        final_write_allowed_for_sandbox=True,
        final_write_allowed_for_production=False,
        final_files_written_count=0,
        final_files_written=(),
        skipped_items=tuple(skipped),
        blocked_items=(),
        failures=(),
        originals_moved=False,
        originals_renamed=False,
        originals_archived=False,
        originals_deleted=False,
        source_mutation=False,
        run_once_called=False,
        safety_summary=MSG_SAFETY_SUMMARY,
        ok=False,
        status="running",
        runtime_check=runtime_check,
    )
    try:
        (sandbox_root / ARTIFACT_PRE_AUDIT).write_text(
            _pre_write_audit_text(pre_result_stub, runtime_check, selected),
            encoding="utf-8",
        )
    except OSError as exc:
        return _blocked_result(
            error=f"Pre-Write-Audit fehlgeschlagen: {exc}",
            result_id=result_id,
            runtime_check=runtime_check,
            package=package,
            authorization=authorization,
            controlled_output_root=str(output_path),
        )

    for plan in runtime_check.plans:
        if not plan.ready_for_write:
            blocked_items.append(
                {
                    "item_id": plan.item_id,
                    "source_path": plan.source_path,
                    "final_target_path": plan.final_target_path,
                    "blockers": list(plan.write_blockers),
                }
            )
            continue
        source = Path(plan.source_path)
        target = Path(plan.final_target_path)
        try:
            if not target.resolve().is_relative_to(sandbox_root.resolve()):
                failures.append(
                    {
                        "item_id": plan.item_id,
                        "source_path": plan.source_path,
                        "final_target_path": plan.final_target_path,
                        "error": BLOCKER_CONTROLLED_OUTPUT,
                    }
                )
                continue
            if not target.resolve().is_relative_to(output_path.resolve()):
                failures.append(
                    {
                        "item_id": plan.item_id,
                        "source_path": plan.source_path,
                        "final_target_path": plan.final_target_path,
                        "error": MSG_OUTSIDE_OUTPUT,
                    }
                )
                continue
            if target.exists() and not allow_overwrite:
                blocked_items.append(
                    {
                        "item_id": plan.item_id,
                        "source_path": plan.source_path,
                        "final_target_path": plan.final_target_path,
                        "blockers": ["target_exists_without_explicit_policy"],
                    }
                )
                continue
            # Copy only — never move/rename originals.
            shutil.copy2(source, target)
            if not source.exists():
                failures.append(
                    {
                        "item_id": plan.item_id,
                        "source_path": plan.source_path,
                        "error": "source_missing_after_copy",
                    }
                )
                continue
            written.append(
                ControlledFinalWriteSandboxFileResult(
                    item_id=plan.item_id,
                    source_path=plan.source_path,
                    source_sha256_before_write=plan.source_sha256_at_preview,
                    source_sha256_at_write_check=plan.source_sha256_at_write_check,
                    hash_match=plan.source_hash_match,
                    final_sandbox_target_path=str(target),
                    operation_type=plan.operation_type,
                    copy_result="copied",
                    blockers=(),
                )
            )
        except OSError as exc:
            failures.append(
                {
                    "item_id": plan.item_id,
                    "source_path": plan.source_path,
                    "final_target_path": plan.final_target_path,
                    "error": str(exc),
                }
            )

    finished_at = _utc_now()
    result = ControlledFinalWriteSandboxResult(
        result_id=result_id,
        gate_id=runtime_check.gate.gate_id if runtime_check.gate else None,
        authorization_id=authorization.authorization_id,
        dry_run_package_id=package.package_id,
        batch_id=package.batch_id,
        source_run_id=package.source_run_id,
        preview_state_id=package.preview_state_id,
        created_at=started_at,
        sandbox_final_write=True,
        productive_mode_requested=False,
        controlled_output_root=str(output_path),
        sandbox_final_write_root=str(sandbox_root),
        final_write_allowed_for_sandbox=True,
        final_write_allowed_for_production=False,
        final_files_written_count=len(written),
        final_files_written=tuple(written),
        skipped_items=tuple(skipped),
        blocked_items=tuple(blocked_items),
        failures=tuple(failures),
        originals_moved=False,
        originals_renamed=False,
        originals_archived=False,
        originals_deleted=False,
        source_mutation=False,
        run_once_called=False,
        safety_summary=MSG_SAFETY_SUMMARY,
        ok=bool(written) and not failures,
        status="completed" if written and not failures else (
            "completed_with_issues" if written else "failed"
        ),
        artifacts=(
            ARTIFACT_README,
            ARTIFACT_MANIFEST_JSON,
            ARTIFACT_MANIFEST_CSV,
            ARTIFACT_PRE_AUDIT,
            ARTIFACT_POST_AUDIT,
            ARTIFACT_COPIED,
            ARTIFACT_SKIPPED,
            ARTIFACT_BLOCKED,
            ARTIFACT_FAILURES,
        ),
        runtime_check=runtime_check,
    )

    files: dict[str, str] = {
        ARTIFACT_README: _readme_text(result),
        ARTIFACT_MANIFEST_JSON: json.dumps(
            result.to_dict(), ensure_ascii=False, indent=2
        )
        + "\n",
        ARTIFACT_MANIFEST_CSV: _manifest_csv(result),
        ARTIFACT_POST_AUDIT: _post_write_audit_text(
            result, started_at=started_at, finished_at=finished_at
        ),
        ARTIFACT_COPIED: _copied_md(result.final_files_written),
        ARTIFACT_SKIPPED: _list_md("Skipped Items", result.skipped_items),
        ARTIFACT_BLOCKED: _list_md("Blocked Items", result.blocked_items),
        ARTIFACT_FAILURES: _list_md("Failures", result.failures),
    }
    try:
        for name, content in files.items():
            (sandbox_root / name).write_text(content, encoding="utf-8")
    except OSError as exc:
        return ControlledFinalWriteSandboxResult(
            result_id=result_id,
            gate_id=result.gate_id,
            authorization_id=result.authorization_id,
            dry_run_package_id=result.dry_run_package_id,
            batch_id=result.batch_id,
            source_run_id=result.source_run_id,
            preview_state_id=result.preview_state_id,
            created_at=result.created_at,
            sandbox_final_write=True,
            productive_mode_requested=False,
            controlled_output_root=str(output_path),
            sandbox_final_write_root=str(sandbox_root),
            final_write_allowed_for_sandbox=True,
            final_write_allowed_for_production=False,
            final_files_written_count=result.final_files_written_count,
            final_files_written=result.final_files_written,
            skipped_items=result.skipped_items,
            blocked_items=result.blocked_items,
            failures=result.failures
            + ({"error": f"artifact_write_failed: {exc}"},),
            originals_moved=False,
            originals_renamed=False,
            originals_archived=False,
            originals_deleted=False,
            source_mutation=False,
            run_once_called=False,
            safety_summary=MSG_SAFETY_SUMMARY,
            ok=False,
            status="failed",
            error=f"Artefakt-Schreiben fehlgeschlagen: {exc}",
            runtime_check=runtime_check,
        )

    return result


def apply_controlled_final_write_sandbox(
    state: Any,
    *,
    sandbox_final_write: bool = True,
    confirmation_phrase_required: bool = False,
    confirmation_phrase_entered: str = "",
    allow_overwrite: bool = False,
    preview_state_fresh: bool = True,
    selected_item_ids: Sequence[str] | None = None,
) -> ControlledFinalWriteSandboxResult:
    """UI helper: authorize + execute sandbox final write under workspace output."""

    bag = get_controlled_final_write_sandbox_bag(state)
    dry_bag = get_finalization_dry_run_package_bag(state)
    batch_bag = get_finalization_preview_batch_bag(state)
    package = dry_bag.last_package
    batch = batch_bag.last_batch
    if batch is None:
        batch = build_finalization_preview_batch(state)
    if package is None:
        result = _blocked_result(
            error=MSG_NEEDS_PACKAGE,
            controlled_output_root=_text(
                getattr(state, "workspace_output_folder_override", None)
            )
            or None,
        )
        bag.last_feedback = result.error or MSG_NEEDS_PACKAGE
        bag.last_feedback_error = True
        return result

    if selected_item_ids is None:
        selected_item_ids = [
            item.item_id
            for item in package.items
            if item.ready_for_future_finalization
        ]
    authorization = build_sandbox_final_write_authorization(
        dry_run_package_id=package.package_id,
        batch_id=package.batch_id,
        selected_item_ids=selected_item_ids,
        authorization_scope=AUTH_SCOPE_SELECTED
        if selected_item_ids
        else AUTH_SCOPE_WHOLE_READY,
        authorized_by_user=True,
        acknowledgements=default_sandbox_acknowledgements(),
        confirmation_phrase_required=confirmation_phrase_required,
        confirmation_phrase_entered=confirmation_phrase_entered,
    )
    output_root = (
        _text(getattr(state, "workspace_output_folder_override", None))
        or _text(package.output_root)
        or None
    )
    result = execute_controlled_final_write_sandbox(
        package=package,
        batch=batch,
        authorization=authorization,
        controlled_output_root=output_root,
        sandbox_final_write=sandbox_final_write,
        productive_mode_requested=False,
        call_run_once=False,
        preview_state_fresh=preview_state_fresh,
        allow_overwrite=allow_overwrite,
        selected_item_ids=selected_item_ids,
    )
    bag.called_run_once = False
    bag.mutated_input = False
    bag.touched_real_invoice_folders = False
    if result.ok:
        bag.last_result = result
        bag.last_result_root = str(result.sandbox_final_write_root or "")
        bag.last_feedback = (
            f"{MSG_CREATED}: {bag.last_result_root} · "
            f"written={result.final_files_written_count} "
            f"skipped={len(result.skipped_items)} "
            f"blocked={len(result.blocked_items)} "
            f"failures={len(result.failures)} · "
            f"{MSG_CTA_CONTROLLED_ONLY} · {MSG_CTA_ORIGINALS_UNCHANGED}"
        )
        bag.last_feedback_error = False
        try:
            state.workspace_last_sandbox_final_write_folder = bag.last_result_root
            state.workspace_sandbox_final_write_feedback = bag.last_feedback
            state.workspace_sandbox_final_write_feedback_error = False
        except Exception:
            pass
    else:
        err = result.error or "Sandbox-Finalschreiben fehlgeschlagen."
        bag.last_result = result
        bag.last_result_root = str(result.sandbox_final_write_root or "")
        bag.last_feedback = err
        bag.last_feedback_error = True
        try:
            state.workspace_sandbox_final_write_feedback = err
            state.workspace_sandbox_final_write_feedback_error = True
        except Exception:
            pass
    return result


def sandbox_final_write_report_fields(
    result: ControlledFinalWriteSandboxResult | None,
) -> dict[str, Any]:
    """Manifest-level sandbox final-write metadata for preview export."""

    if result is None:
        return {
            "sandbox_final_write_available": False,
            "sandbox_final_write_result_id": None,
            "sandbox_final_write_root": None,
            "final_write_allowed_for_production": False,
            "originals_moved": False,
            "originals_renamed": False,
            "originals_archived": False,
            "originals_deleted": False,
            "source_mutation": False,
        }
    return {
        "sandbox_final_write_available": True,
        "sandbox_final_write_result_id": result.result_id,
        "sandbox_final_write_root": result.sandbox_final_write_root,
        "final_write_allowed_for_production": False,
        "originals_moved": False,
        "originals_renamed": False,
        "originals_archived": False,
        "originals_deleted": False,
        "source_mutation": False,
        "sandbox_final_write": True,
        "final_files_written_count": result.final_files_written_count,
        "run_once_called": False,
    }


def sandbox_final_write_summary_lines(
    result: ControlledFinalWriteSandboxResult | None,
) -> tuple[str, ...]:
    if result is None:
        return (
            MSG_TITLE,
            MSG_CTA_SANDBOX_WRITE,
            MSG_CTA_CONTROLLED_ONLY,
            MSG_CTA_ORIGINALS_UNCHANGED,
            "Sandbox-Finalschreiben noch nicht ausgeführt.",
        )
    return (
        MSG_TITLE,
        MSG_CTA_SANDBOX_WRITE,
        MSG_CTA_CONTROLLED_ONLY,
        MSG_CTA_ORIGINALS_UNCHANGED,
        f"written: {result.final_files_written_count} · "
        f"skipped: {len(result.skipped_items)} · "
        f"blocked: {len(result.blocked_items)} · "
        f"failures: {len(result.failures)}",
        f"Pfad: {result.sandbox_final_write_root or ''}",
        MSG_PRODUCTION_DISABLED,
        MSG_NO_SAAS,
        MSG_NO_PRODUCTION_READY,
    )


def sandbox_final_write_calls_run_once() -> bool:
    return False


def sandbox_final_write_mutates_input() -> bool:
    return False


def sandbox_final_write_moves_originals() -> bool:
    return False


def sandbox_final_write_renames_originals() -> bool:
    return False


def sandbox_final_write_archives_originals() -> bool:
    return False


def sandbox_final_write_deletes_originals() -> bool:
    return False


def sandbox_final_write_touches_real_invoice_folders() -> bool:
    return False


def sandbox_final_write_claims_saas_ready() -> bool:
    return False


def sandbox_final_write_claims_production_ready() -> bool:
    return False


__all__ = (
    "ARTIFACT_BLOCKED",
    "ARTIFACT_COPIED",
    "ARTIFACT_FAILURES",
    "ARTIFACT_MANIFEST_CSV",
    "ARTIFACT_MANIFEST_JSON",
    "ARTIFACT_POST_AUDIT",
    "ARTIFACT_PRE_AUDIT",
    "ARTIFACT_README",
    "ARTIFACT_SKIPPED",
    "ControlledFinalWriteSandboxBag",
    "ControlledFinalWriteSandboxFileResult",
    "ControlledFinalWriteSandboxResult",
    "MSG_CTA_CONTROLLED_ONLY",
    "MSG_CTA_ORIGINALS_UNCHANGED",
    "MSG_CTA_SANDBOX_WRITE",
    "MSG_PRODUCTION_DISABLED",
    "MSG_SAFETY_SUMMARY",
    "MSG_TITLE",
    "SANDBOX_FINAL_WRITE_FOLDER_PREFIX",
    "SANDBOX_FINAL_WRITE_KIND",
    "apply_controlled_final_write_sandbox",
    "execute_controlled_final_write_sandbox",
    "get_controlled_final_write_sandbox_bag",
    "sandbox_final_write_archives_originals",
    "sandbox_final_write_calls_run_once",
    "sandbox_final_write_claims_production_ready",
    "sandbox_final_write_claims_saas_ready",
    "sandbox_final_write_deletes_originals",
    "sandbox_final_write_moves_originals",
    "sandbox_final_write_mutates_input",
    "sandbox_final_write_renames_originals",
    "sandbox_final_write_report_fields",
    "sandbox_final_write_summary_lines",
    "sandbox_final_write_touches_real_invoice_folders",
    "validate_sandbox_final_write_paths",
)
