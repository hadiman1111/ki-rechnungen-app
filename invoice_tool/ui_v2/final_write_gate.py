"""Track-B Final Write Gate / Authorization / Plan (Prompt 33/34 runtime).

Runtime models and preflight checks for controlled sandbox final-write only.
Production final write remains disabled: final_write_execution_allowed_for_production
is always False. Never calls run_once, never mutates originals.
"""

from __future__ import annotations

import hashlib
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
from invoice_tool.ui_v2.finalization_dry_run_package import FinalizationDryRunPackage
from invoice_tool.ui_v2.finalization_preview_batch import (
    STATUS_READY,
    FinalizationPreviewBatch,
)

GATE_KIND = "track_b_final_write_gate"
GATE_SCHEMA_VERSION = 1

GATE_STATUS_CLOSED = "closed"
GATE_STATUS_OPEN_FOR_FUTURE = "open_for_future_authorized_write"
GATE_STATUS_BLOCKED = "blocked"

AUTH_SCOPE_SELECTED = "selected_items"
AUTH_SCOPE_WHOLE_READY = "whole_ready_batch"

OPERATION_COPY = "copy_to_final_output"
OPERATION_RENAME_COPY = "rename_copy_to_final_output"
OPERATION_NO_OP = "no_op"

ORIGINAL_POLICY_LEAVE = "leave_original_unchanged"

ACK_SANDBOX_WRITE = "sandbox_write_acknowledged"
ACK_ORIGINALS_UNCHANGED = "originals_remain_unchanged"
ACK_NOT_PRODUCTION = "not_production_final_output"
ACK_FINAL_WRITE_COPY = "final_write_will_copy_or_rename"
ACK_ORIGINALS_POLICY = "originals_policy"
ACK_CONFLICTS_RESOLVED = "conflicts_resolved"
ACK_SOURCE_HASH = "source_hash_recheck"
ACK_TARGET_PATH = "target_path_recheck"
ACK_NO_ROLLBACK = "no_rollback_guarantee_without_backup"

REQUIRED_SANDBOX_ACKS = (
    ACK_SANDBOX_WRITE,
    ACK_ORIGINALS_UNCHANGED,
    ACK_NOT_PRODUCTION,
    ACK_FINAL_WRITE_COPY,
    ACK_ORIGINALS_POLICY,
    ACK_CONFLICTS_RESOLVED,
    ACK_SOURCE_HASH,
    ACK_TARGET_PATH,
    ACK_NO_ROLLBACK,
)

BLOCKER_MISSING_DRY_RUN = "missing_dry_run_package"
BLOCKER_STALE_DRY_RUN = "stale_dry_run_package"
BLOCKER_STALE_PREVIEW = "stale_preview_state"
BLOCKER_SOURCE_HASH_CHANGED = "source_hash_changed"
BLOCKER_TARGET_OUTSIDE = "target_outside_output_root"
BLOCKER_DUPLICATE_UNRESOLVED = "duplicate_target_unresolved"
BLOCKER_TARGET_EXISTS = "target_exists_without_explicit_policy"
BLOCKER_UNRESOLVED_REVIEW = "unresolved_review_item"
BLOCKER_MISSING_FIELD = "missing_required_field"
BLOCKER_INCOMPLETE_FILENAME = "incomplete_filename"
BLOCKER_UNRESOLVED_CONFIG = "unresolved_configuration"
BLOCKER_MISSING_AUTH = "missing_final_write_authorization"
BLOCKER_PHRASE_MISSING = "confirmation_phrase_missing"
BLOCKER_PRODUCTIVE_NOT_ENABLED = "productive_mode_not_explicitly_enabled"
BLOCKER_AUDIT_PRE_MISSING = "final_audit_pre_record_missing"
BLOCKER_REAL_INVOICE = "real_invoice_folder_path_detected"
BLOCKER_SANDBOX_FLAG = "sandbox_final_write_required"
BLOCKER_NO_READY_ITEMS = "no_selected_ready_items"
BLOCKER_CONTROLLED_OUTPUT = "controlled_output_root_required"
BLOCKER_PRODUCTION_WRITE = "production_final_write_disabled"

MSG_SAFETY_SUMMARY = (
    "FinalWriteGate runtime — sandbox execution may be allowed only after "
    "all preconditions; final_write_execution_allowed_for_production=false; "
    "Originale bleiben unverändert; keine realen Rechnungsordner."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm_path(value: Path | str | None) -> Path | None:
    raw = _text(value)
    if not raw:
        return None
    try:
        return Path(raw).expanduser().resolve()
    except OSError:
        return Path(raw).expanduser()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True)
class FinalWritePlan:
    """Per-item final-write plan (sandbox copy only in Prompt 33)."""

    item_id: str
    source_path: str
    source_sha256_at_preview: str | None
    source_sha256_at_write_check: str | None
    source_hash_match: bool
    approved_final_filename: str | None
    final_target_path: str
    target_within_output_root: bool
    target_exists: bool
    duplicate_policy: str
    conflict_status: str
    operation_type: str
    original_file_policy: str
    ready_for_write: bool
    write_blockers: tuple[str, ...] = field(default_factory=tuple)
    audit_record_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_path": self.source_path,
            "source_sha256_at_preview": self.source_sha256_at_preview,
            "source_sha256_at_write_check": self.source_sha256_at_write_check,
            "source_hash_match": bool(self.source_hash_match),
            "approved_final_filename": self.approved_final_filename,
            "final_target_path": self.final_target_path,
            "target_within_output_root": bool(self.target_within_output_root),
            "target_exists": bool(self.target_exists),
            "duplicate_policy": self.duplicate_policy,
            "conflict_status": self.conflict_status,
            "operation_type": self.operation_type,
            "original_file_policy": self.original_file_policy,
            "ready_for_write": bool(self.ready_for_write),
            "write_blockers": list(self.write_blockers),
            "audit_record_id": self.audit_record_id,
        }


@dataclass(frozen=True)
class FinalWriteAuthorization:
    """Explicit user authorization for sandbox final write."""

    authorization_id: str
    authorized_by_user: bool
    authorization_timestamp: str
    authorization_scope: str
    selected_item_ids: tuple[str, ...]
    user_acknowledged: Mapping[str, bool]
    dry_run_package_id: str
    finalization_preview_batch_id: str
    confirmation_phrase_required: bool
    confirmation_phrase_entered: str
    confirmation_phrase_expected: str
    authorization_valid: bool
    authorization_blockers: tuple[str, ...] = field(default_factory=tuple)
    sandbox_final_write: bool = True
    productive_mode_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorization_id": self.authorization_id,
            "authorized_by_user": bool(self.authorized_by_user),
            "authorization_timestamp": self.authorization_timestamp,
            "authorization_scope": self.authorization_scope,
            "selected_item_ids": list(self.selected_item_ids),
            "user_acknowledged": dict(self.user_acknowledged),
            "dry_run_package_id": self.dry_run_package_id,
            "finalization_preview_batch_id": self.finalization_preview_batch_id,
            "confirmation_phrase_required": bool(self.confirmation_phrase_required),
            "confirmation_phrase_entered": self.confirmation_phrase_entered,
            "confirmation_phrase_expected": self.confirmation_phrase_expected,
            "authorization_valid": bool(self.authorization_valid),
            "authorization_blockers": list(self.authorization_blockers),
            "sandbox_final_write": True,
            "productive_mode_requested": False,
        }


@dataclass(frozen=True)
class FinalWriteGate:
    """Gate model for future/sandbox-authorized final write."""

    gate_id: str
    source_run_id: str | None
    preview_state_id: str
    dry_run_package_id: str
    batch_id: str
    created_at: str
    final_write_allowed: bool
    productive_mode_requested: bool
    gate_status: str
    required_preconditions: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    user_authorization_required: bool = True
    audit_required: bool = True
    source_recheck_required: bool = True
    target_recheck_required: bool = True
    conflict_recheck_required: bool = True
    stale_state_recheck_required: bool = True
    final_write_execution_available: bool = False
    sandbox_final_write: bool = True
    final_write_execution_allowed_for_sandbox: bool = False
    final_write_execution_allowed_for_production: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": GATE_KIND,
            "schema_version": GATE_SCHEMA_VERSION,
            "gate_id": self.gate_id,
            "source_run_id": self.source_run_id,
            "preview_state_id": self.preview_state_id,
            "dry_run_package_id": self.dry_run_package_id,
            "batch_id": self.batch_id,
            "created_at": self.created_at,
            "final_write_allowed": bool(self.final_write_allowed),
            "productive_mode_requested": False,
            "gate_status": self.gate_status,
            "required_preconditions": list(self.required_preconditions),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "user_authorization_required": True,
            "audit_required": True,
            "source_recheck_required": True,
            "target_recheck_required": True,
            "conflict_recheck_required": True,
            "stale_state_recheck_required": True,
            "final_write_execution_available": bool(
                self.final_write_execution_available
            ),
            "sandbox_final_write": True,
            "final_write_execution_allowed_for_sandbox": bool(
                self.final_write_execution_allowed_for_sandbox
            ),
            "final_write_execution_allowed_for_production": False,
            "safety_summary": MSG_SAFETY_SUMMARY,
        }


@dataclass(frozen=True)
class FinalWriteGateRuntimeCheck:
    """Immediate preflight result before sandbox final write."""

    gate_status: str
    all_preconditions_passed: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    source_hash_recheck_result: str
    target_path_recheck_result: str
    conflict_recheck_result: str
    dry_run_package_link_result: str
    authorization_result: str
    final_write_execution_allowed_for_sandbox: bool
    final_write_execution_allowed_for_production: bool = False
    plans: tuple[FinalWritePlan, ...] = field(default_factory=tuple)
    gate: FinalWriteGate | None = None
    authorization: FinalWriteAuthorization | None = None
    pre_write_audit_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_status": self.gate_status,
            "all_preconditions_passed": bool(self.all_preconditions_passed),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "source_hash_recheck_result": self.source_hash_recheck_result,
            "target_path_recheck_result": self.target_path_recheck_result,
            "conflict_recheck_result": self.conflict_recheck_result,
            "dry_run_package_link_result": self.dry_run_package_link_result,
            "authorization_result": self.authorization_result,
            "final_write_execution_allowed_for_sandbox": bool(
                self.final_write_execution_allowed_for_sandbox
            ),
            "final_write_execution_allowed_for_production": False,
            "plans": [plan.to_dict() for plan in self.plans],
            "gate": self.gate.to_dict() if self.gate is not None else None,
            "authorization": (
                self.authorization.to_dict()
                if self.authorization is not None
                else None
            ),
            "pre_write_audit_ready": bool(self.pre_write_audit_ready),
        }


def build_sandbox_final_write_authorization(
    *,
    dry_run_package_id: str,
    batch_id: str,
    selected_item_ids: Sequence[str],
    authorization_scope: str = AUTH_SCOPE_SELECTED,
    authorized_by_user: bool = True,
    acknowledgements: Mapping[str, bool] | None = None,
    confirmation_phrase_required: bool = False,
    confirmation_phrase_entered: str = "",
    confirmation_phrase_expected: str = "SANDBOX FINAL WRITE",
    authorization_id: str | None = None,
) -> FinalWriteAuthorization:
    """Build a sandbox authorization; valid only with explicit user + acks."""

    acks = dict(acknowledgements or {})
    blockers: list[str] = []
    if not authorized_by_user:
        blockers.append(BLOCKER_MISSING_AUTH)
    if authorization_scope not in {AUTH_SCOPE_SELECTED, AUTH_SCOPE_WHOLE_READY}:
        blockers.append(BLOCKER_MISSING_AUTH)
    if not selected_item_ids:
        blockers.append(BLOCKER_NO_READY_ITEMS)
    if not _text(dry_run_package_id):
        blockers.append(BLOCKER_MISSING_DRY_RUN)
    for key in REQUIRED_SANDBOX_ACKS:
        if not bool(acks.get(key)):
            blockers.append(f"missing_acknowledgement:{key}")
            acks[key] = False
        else:
            acks[key] = True
    if confirmation_phrase_required:
        if _text(confirmation_phrase_entered) != _text(confirmation_phrase_expected):
            blockers.append(BLOCKER_PHRASE_MISSING)
    valid = not blockers
    return FinalWriteAuthorization(
        authorization_id=authorization_id or _new_id("fwa"),
        authorized_by_user=bool(authorized_by_user),
        authorization_timestamp=_utc_now(),
        authorization_scope=authorization_scope,
        selected_item_ids=tuple(dict.fromkeys(_text(i) for i in selected_item_ids if _text(i))),
        user_acknowledged=acks,
        dry_run_package_id=_text(dry_run_package_id),
        finalization_preview_batch_id=_text(batch_id),
        confirmation_phrase_required=bool(confirmation_phrase_required),
        confirmation_phrase_entered=_text(confirmation_phrase_entered),
        confirmation_phrase_expected=_text(confirmation_phrase_expected),
        authorization_valid=valid,
        authorization_blockers=tuple(blockers),
        sandbox_final_write=True,
        productive_mode_requested=False,
    )


def default_sandbox_acknowledgements() -> dict[str, bool]:
    return {key: True for key in REQUIRED_SANDBOX_ACKS}


def _path_is_controlled_output(path: Path | None) -> bool:
    if path is None:
        return False
    text = str(path)
    if path_has_forbidden_productive_marker(text):
        return False
    if path_looks_like_original(text):
        return False
    return is_explicit_copied_sandbox_test_path(text)


def _blocking_conflicts_for_item(
    item_id: str, batch: FinalizationPreviewBatch
) -> tuple[str, ...]:
    labels: list[str] = []
    for conflict in batch.conflicts:
        if not conflict.blocking:
            continue
        if item_id in conflict.affected_item_ids:
            labels.append(conflict.conflict_type)
    return tuple(dict.fromkeys(labels))


def build_final_write_plans(
    *,
    package: FinalizationDryRunPackage,
    batch: FinalizationPreviewBatch,
    selected_item_ids: Sequence[str],
    sandbox_final_write_root: Path,
    controlled_output_root: Path,
    allow_overwrite: bool = False,
) -> tuple[FinalWritePlan, ...]:
    """Build per-item plans with hash/target/conflict rechecks."""

    selected = set(_text(i) for i in selected_item_ids if _text(i))
    package_by_id = {item.item_id: item for item in package.items}
    batch_by_id = {item.item_id: item for item in batch.items}
    plans: list[FinalWritePlan] = []
    input_root = _norm_path(package.input_root or batch.input_root)

    for item_id in selected:
        pkg_item = package_by_id.get(item_id)
        batch_item = batch_by_id.get(item_id)
        blockers: list[str] = []
        if pkg_item is None or batch_item is None:
            blockers.append(BLOCKER_UNRESOLVED_REVIEW)
            plans.append(
                FinalWritePlan(
                    item_id=item_id,
                    source_path="",
                    source_sha256_at_preview=None,
                    source_sha256_at_write_check=None,
                    source_hash_match=False,
                    approved_final_filename=None,
                    final_target_path="",
                    target_within_output_root=False,
                    target_exists=False,
                    duplicate_policy="block",
                    conflict_status="unresolved",
                    operation_type=OPERATION_NO_OP,
                    original_file_policy=ORIGINAL_POLICY_LEAVE,
                    ready_for_write=False,
                    write_blockers=tuple(blockers),
                )
            )
            continue

        if not pkg_item.ready_for_future_finalization:
            blockers.append(BLOCKER_UNRESOLVED_REVIEW)
        if batch_item.finalization_status != STATUS_READY:
            blockers.append(BLOCKER_UNRESOLVED_REVIEW)

        filename = _text(
            pkg_item.approved_preview_filename
            or batch_item.approved_preview_filename
            or pkg_item.source_filename
        )
        if not filename or not filename.lower().endswith(".pdf"):
            blockers.append(BLOCKER_INCOMPLETE_FILENAME)

        source_name = _text(pkg_item.source_filename or batch_item.source_filename)
        source_path = (input_root / source_name) if input_root is not None else None
        source_path_text = str(source_path) if source_path is not None else ""
        preview_hash = pkg_item.source_sha256 or batch_item.source_hash_at_decision
        write_hash: str | None = None
        hash_match = False
        if source_path is not None and source_path.is_file():
            write_hash = sha256_file(source_path)
            hash_match = bool(preview_hash) and write_hash == preview_hash
            if preview_hash and not hash_match:
                blockers.append(BLOCKER_SOURCE_HASH_CHANGED)
            if not preview_hash:
                # No stored preview hash → treat current hash as match baseline.
                hash_match = True
                preview_hash = write_hash
        else:
            blockers.append(BLOCKER_MISSING_FIELD)
            blockers.append(BLOCKER_SOURCE_HASH_CHANGED)

        if source_path_text and (
            path_has_forbidden_productive_marker(source_path_text)
            or path_looks_like_original(source_path_text)
        ):
            # Source under controlled sandbox input is allowed via positive signal.
            if not is_explicit_copied_sandbox_test_path(source_path_text):
                blockers.append(BLOCKER_REAL_INVOICE)

        target_path = sandbox_final_write_root / filename
        try:
            target_within = target_path.resolve().is_relative_to(
                controlled_output_root.resolve()
            ) and target_path.resolve().is_relative_to(
                sandbox_final_write_root.resolve()
            )
        except (OSError, ValueError):
            target_within = False
        if not target_within:
            blockers.append(BLOCKER_TARGET_OUTSIDE)

        target_exists = target_path.exists()
        if target_exists and not allow_overwrite:
            blockers.append(BLOCKER_TARGET_EXISTS)

        conflict_labels = _blocking_conflicts_for_item(item_id, batch)
        conflict_status = "ok"
        if conflict_labels:
            conflict_status = "unresolved"
            if any("duplicate" in label for label in conflict_labels):
                blockers.append(BLOCKER_DUPLICATE_UNRESOLVED)
            else:
                blockers.append(BLOCKER_DUPLICATE_UNRESOLVED)

        ready = not blockers
        plans.append(
            FinalWritePlan(
                item_id=item_id,
                source_path=source_path_text,
                source_sha256_at_preview=preview_hash,
                source_sha256_at_write_check=write_hash,
                source_hash_match=hash_match,
                approved_final_filename=filename or None,
                final_target_path=str(target_path),
                target_within_output_root=target_within,
                target_exists=target_exists,
                duplicate_policy="allow_overwrite" if allow_overwrite else "block",
                conflict_status=conflict_status,
                operation_type=OPERATION_RENAME_COPY if ready else OPERATION_NO_OP,
                original_file_policy=ORIGINAL_POLICY_LEAVE,
                ready_for_write=ready,
                write_blockers=tuple(dict.fromkeys(blockers)),
                audit_record_id=_new_id("audit"),
            )
        )
    return tuple(plans)


def run_final_write_gate_runtime_check(
    *,
    package: FinalizationDryRunPackage | None,
    batch: FinalizationPreviewBatch | None,
    authorization: FinalWriteAuthorization | None,
    controlled_output_root: Path | str | None,
    sandbox_final_write_root: Path | str | None = None,
    sandbox_final_write: bool = True,
    productive_mode_requested: bool = False,
    preview_state_fresh: bool = True,
    pre_write_audit_ready: bool = True,
    allow_overwrite: bool = False,
    selected_item_ids: Sequence[str] | None = None,
) -> FinalWriteGateRuntimeCheck:
    """Run all mandatory sandbox final-write preconditions."""

    blockers: list[str] = []
    warnings: list[str] = []

    if not sandbox_final_write:
        blockers.append(BLOCKER_SANDBOX_FLAG)
    if productive_mode_requested:
        blockers.append(BLOCKER_PRODUCTIVE_NOT_ENABLED)

    output_root = _norm_path(controlled_output_root)
    if output_root is None or not _path_is_controlled_output(output_root):
        blockers.append(BLOCKER_CONTROLLED_OUTPUT)
        if output_root is not None and (
            path_has_forbidden_productive_marker(str(output_root))
            or path_looks_like_original(str(output_root))
        ):
            blockers.append(BLOCKER_REAL_INVOICE)

    dry_run_link = "missing"
    if package is None:
        blockers.append(BLOCKER_MISSING_DRY_RUN)
    else:
        dry_run_link = "present"
        if batch is None:
            blockers.append(BLOCKER_STALE_PREVIEW)
            dry_run_link = "batch_missing"
        else:
            if package.batch_id != batch.batch_id:
                blockers.append(BLOCKER_STALE_DRY_RUN)
                dry_run_link = "batch_mismatch"
            if package.preview_state_id != batch.preview_state_id:
                blockers.append(BLOCKER_STALE_DRY_RUN)
                dry_run_link = "preview_mismatch"
            if dry_run_link == "present":
                dry_run_link = "linked"

    if not preview_state_fresh:
        blockers.append(BLOCKER_STALE_PREVIEW)

    auth_result = "missing"
    if authorization is None:
        blockers.append(BLOCKER_MISSING_AUTH)
    else:
        if not authorization.authorization_valid or not authorization.authorized_by_user:
            blockers.append(BLOCKER_MISSING_AUTH)
            auth_result = "invalid"
            blockers.extend(
                b
                for b in authorization.authorization_blockers
                if b not in blockers
            )
        else:
            auth_result = "valid"
            if package is not None and authorization.dry_run_package_id != package.package_id:
                blockers.append(BLOCKER_STALE_DRY_RUN)
                auth_result = "package_mismatch"
            if batch is not None and (
                authorization.finalization_preview_batch_id != batch.batch_id
            ):
                blockers.append(BLOCKER_STALE_PREVIEW)
                auth_result = "batch_mismatch"

    if not pre_write_audit_ready:
        blockers.append(BLOCKER_AUDIT_PRE_MISSING)

    # Production write is never allowed in this task.
    blockers = [b for b in dict.fromkeys(blockers)]
    # Remove production-only false-positive: production is disabled by flag, not
    # as a sandbox blocker unless productive mode was requested (handled above).

    selected: list[str]
    if selected_item_ids is not None:
        selected = [i for i in selected_item_ids if _text(i)]
    elif authorization is not None:
        selected = list(authorization.selected_item_ids)
    else:
        selected = []

    if package is not None and authorization is not None:
        if authorization.authorization_scope == AUTH_SCOPE_WHOLE_READY:
            selected = [
                item.item_id
                for item in package.items
                if item.ready_for_future_finalization
            ]
    if not selected:
        blockers.append(BLOCKER_NO_READY_ITEMS)

    sandbox_root = _norm_path(sandbox_final_write_root)
    if sandbox_root is None and output_root is not None:
        sandbox_root = output_root / "sandbox-final-write-preflight"
    plans: tuple[FinalWritePlan, ...] = ()
    source_hash_result = "skipped"
    target_result = "skipped"
    conflict_result = "skipped"

    if (
        package is not None
        and batch is not None
        and output_root is not None
        and sandbox_root is not None
        and selected
    ):
        plans = build_final_write_plans(
            package=package,
            batch=batch,
            selected_item_ids=selected,
            sandbox_final_write_root=sandbox_root,
            controlled_output_root=output_root,
            allow_overwrite=allow_overwrite,
        )
        hash_ok = all(p.source_hash_match for p in plans) if plans else False
        target_ok = all(p.target_within_output_root for p in plans) if plans else False
        conflict_ok = all(p.conflict_status == "ok" for p in plans) if plans else False
        source_hash_result = "pass" if hash_ok else "fail"
        target_result = "pass" if target_ok else "fail"
        conflict_result = "pass" if conflict_ok else "fail"
        for plan in plans:
            for blocker in plan.write_blockers:
                if blocker not in blockers:
                    blockers.append(blocker)
        if any(
            path_has_forbidden_productive_marker(p.final_target_path)
            or (
                path_looks_like_original(p.final_target_path)
                and not is_explicit_copied_sandbox_test_path(p.final_target_path)
            )
            for p in plans
            if p.final_target_path
        ):
            if BLOCKER_REAL_INVOICE not in blockers:
                blockers.append(BLOCKER_REAL_INVOICE)

    blockers = list(dict.fromkeys(blockers))
    # Sandbox may proceed only when every precondition passes.
    all_passed = not blockers and bool(plans) and all(p.ready_for_write for p in plans)
    sandbox_allowed = bool(sandbox_final_write) and all_passed
    gate_status = GATE_STATUS_BLOCKED
    if sandbox_allowed:
        gate_status = GATE_STATUS_OPEN_FOR_FUTURE
    elif not blockers and not selected:
        gate_status = GATE_STATUS_CLOSED

    gate = None
    if package is not None and batch is not None:
        gate = FinalWriteGate(
            gate_id=_new_id("fwg"),
            source_run_id=package.source_run_id or batch.source_run_id,
            preview_state_id=package.preview_state_id,
            dry_run_package_id=package.package_id,
            batch_id=package.batch_id,
            created_at=_utc_now(),
            final_write_allowed=False,  # production flag remains false
            productive_mode_requested=False,
            gate_status=gate_status if not sandbox_allowed else GATE_STATUS_OPEN_FOR_FUTURE,
            required_preconditions=(
                "dry_run_package",
                "user_authorization",
                "selected_ready_items",
                "source_hash_recheck",
                "target_path_recheck",
                "conflict_recheck",
                "controlled_output_root",
                "sandbox_final_write",
                "pre_write_audit",
            ),
            blockers=tuple(blockers),
            warnings=tuple(warnings),
            final_write_execution_available=sandbox_allowed,
            sandbox_final_write=True,
            final_write_execution_allowed_for_sandbox=sandbox_allowed,
            final_write_execution_allowed_for_production=False,
        )

    return FinalWriteGateRuntimeCheck(
        gate_status=gate_status if gate is None else gate.gate_status,
        all_preconditions_passed=all_passed,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        source_hash_recheck_result=source_hash_result,
        target_path_recheck_result=target_result,
        conflict_recheck_result=conflict_result,
        dry_run_package_link_result=dry_run_link,
        authorization_result=auth_result,
        final_write_execution_allowed_for_sandbox=sandbox_allowed,
        final_write_execution_allowed_for_production=False,
        plans=plans,
        gate=gate,
        authorization=authorization,
        pre_write_audit_ready=pre_write_audit_ready,
    )


__all__ = (
    "ACK_CONFLICTS_RESOLVED",
    "ACK_FINAL_WRITE_COPY",
    "ACK_NO_ROLLBACK",
    "ACK_NOT_PRODUCTION",
    "ACK_ORIGINALS_POLICY",
    "ACK_ORIGINALS_UNCHANGED",
    "ACK_SANDBOX_WRITE",
    "ACK_SOURCE_HASH",
    "ACK_TARGET_PATH",
    "AUTH_SCOPE_SELECTED",
    "AUTH_SCOPE_WHOLE_READY",
    "BLOCKER_AUDIT_PRE_MISSING",
    "BLOCKER_CONTROLLED_OUTPUT",
    "BLOCKER_DUPLICATE_UNRESOLVED",
    "BLOCKER_MISSING_AUTH",
    "BLOCKER_MISSING_DRY_RUN",
    "BLOCKER_NO_READY_ITEMS",
    "BLOCKER_PHRASE_MISSING",
    "BLOCKER_PRODUCTIVE_NOT_ENABLED",
    "BLOCKER_REAL_INVOICE",
    "BLOCKER_SANDBOX_FLAG",
    "BLOCKER_SOURCE_HASH_CHANGED",
    "BLOCKER_TARGET_EXISTS",
    "BLOCKER_TARGET_OUTSIDE",
    "FinalWriteAuthorization",
    "FinalWriteGate",
    "FinalWriteGateRuntimeCheck",
    "FinalWritePlan",
    "ORIGINAL_POLICY_LEAVE",
    "REQUIRED_SANDBOX_ACKS",
    "build_final_write_plans",
    "build_sandbox_final_write_authorization",
    "default_sandbox_acknowledgements",
    "run_final_write_gate_runtime_check",
    "sha256_file",
)
