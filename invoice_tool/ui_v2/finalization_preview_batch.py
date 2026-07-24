"""Track-B Finalization Preview Batch & Conflicts (Prompt 30/34).

Groups review decisions into a non-productive finalization preview batch.
Never writes final PDFs, never mutates inputs, never calls run_once,
never sets final_write_allowed=True, never touches real invoice folders.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from invoice_tool.ui_v2.finalization_readiness import (
    BLOCKER_DUPLICATE_TARGET_FILENAME,
    BLOCKER_INCOMPLETE_FILENAME,
    BLOCKER_MISSING_AMOUNT,
    BLOCKER_MISSING_DATE,
    BLOCKER_MISSING_FILENAME_PATTERN,
    BLOCKER_MISSING_OR_UNCLEAR_CONFIGURATION,
    BLOCKER_MISSING_PAYMENT_FIELD,
    BLOCKER_MISSING_PATTERN_TOKEN,
    BLOCKER_MISSING_SUPPLIER,
    BLOCKER_NO_EXPLICIT_USER_APPROVAL,
    BLOCKER_SOURCE_HASH_CHANGED,
    BLOCKER_STALE_PREVIEW_STATE,
    BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT,
    FINAL_WRITE_ALLOWED_IN_THIS_PHASE,
    FinalizationReadiness,
    final_write_allowed,
)
from invoice_tool.ui_v2.review_decision import (
    DECISION_ACCEPT,
    DECISION_DEFER,
    DECISION_EDIT,
    DECISION_IGNORE,
    DECISION_KEEP_REVIEW,
    DECISION_NEEDS_CONFIG,
    ReviewDecision,
    ensure_preview_state_id,
    get_review_decision_bag,
)
from invoice_tool.ui_v2.review_preview_state import review_item_key

FinalizationStatus = Literal[
    "ready_for_future_finalization",
    "blocked",
    "ignored",
    "deferred",
    "still_review_required",
]

ConflictType = Literal[
    "duplicate_target_filename",
    "duplicate_target_path",
    "unsafe_target_path",
    "stale_preview_state",
    "changed_source_hash",
    "missing_approval",
    "missing_required_field",
    "unresolved_configuration",
    "incomplete_filename",
    "ignored_item",
    "deferred_item",
]

STATUS_READY = "ready_for_future_finalization"
STATUS_BLOCKED = "blocked"
STATUS_IGNORED = "ignored"
STATUS_DEFERRED = "deferred"
STATUS_STILL_REVIEW = "still_review_required"

CONFLICT_DUPLICATE_TARGET_FILENAME = "duplicate_target_filename"
CONFLICT_DUPLICATE_TARGET_PATH = "duplicate_target_path"
CONFLICT_UNSAFE_TARGET_PATH = "unsafe_target_path"
CONFLICT_STALE_PREVIEW_STATE = "stale_preview_state"
CONFLICT_CHANGED_SOURCE_HASH = "changed_source_hash"
CONFLICT_MISSING_APPROVAL = "missing_approval"
CONFLICT_MISSING_REQUIRED_FIELD = "missing_required_field"
CONFLICT_UNRESOLVED_CONFIGURATION = "unresolved_configuration"
CONFLICT_INCOMPLETE_FILENAME = "incomplete_filename"
CONFLICT_IGNORED_ITEM = "ignored_item"
CONFLICT_DEFERRED_ITEM = "deferred_item"

MSG_BATCH_TITLE = "Finalisierungs-Vorschau"
MSG_BATCH_READY = "Bereit für spätere Finalisierung"
MSG_BATCH_BLOCKED = "Blockiert"
MSG_BATCH_IGNORED = "Ignoriert"
MSG_BATCH_DEFERRED = "Zurückgestellt"
MSG_BATCH_STILL_REVIEW = "Weiterhin zur Prüfung"
MSG_BATCH_NO_FINAL_WRITE = (
    "Noch kein finales Schreiben — Originale bleiben unverändert."
)
MSG_SAFETY_SUMMARY = (
    "Finalisierungs-Vorschau only — final_write_allowed=false; "
    "keine produktive Verarbeitung; Originale bleiben unverändert."
)

_SUGGESTED_RESOLUTION: dict[str, str] = {
    CONFLICT_DUPLICATE_TARGET_FILENAME: (
        "Einen der freigegebenen Dateinamen ändern, damit Ziele eindeutig sind."
    ),
    CONFLICT_DUPLICATE_TARGET_PATH: (
        "Zielpfade entkoppeln — doppelte Preview-Ziele auflösen."
    ),
    CONFLICT_UNSAFE_TARGET_PATH: (
        "Zielpfad auf einen Pfad unter dem erlaubten Output-Root korrigieren."
    ),
    CONFLICT_STALE_PREVIEW_STATE: (
        "Preview/Sandbox neu ausführen und Entscheidung erneut treffen."
    ),
    CONFLICT_CHANGED_SOURCE_HASH: (
        "Quelldatei unverändert halten oder Preview nach Änderung neu prüfen."
    ),
    CONFLICT_MISSING_APPROVAL: (
        "Vorschlag explizit akzeptieren oder bearbeitet freigeben."
    ),
    CONFLICT_MISSING_REQUIRED_FIELD: (
        "Fehlende Pflichtfelder ergänzen und erneut entscheiden."
    ),
    CONFLICT_UNRESOLVED_CONFIGURATION: (
        "Konfiguration anpassen und Preview neu prüfen."
    ),
    CONFLICT_INCOMPLETE_FILENAME: (
        "Vorschau-Dateiname vervollständigen (.pdf, ohne Mustertoken)."
    ),
    CONFLICT_IGNORED_ITEM: (
        "Ignorierte Items bleiben außerhalb der künftigen Finalisierung."
    ),
    CONFLICT_DEFERRED_ITEM: (
        "Zurückgestellte Items später erneut entscheiden."
    ),
}

_MISSING_FIELD_BLOCKERS = frozenset(
    {
        BLOCKER_MISSING_SUPPLIER,
        BLOCKER_MISSING_DATE,
        BLOCKER_MISSING_AMOUNT,
        BLOCKER_MISSING_PAYMENT_FIELD,
    }
)
_INCOMPLETE_FILENAME_BLOCKERS = frozenset(
    {
        BLOCKER_INCOMPLETE_FILENAME,
        BLOCKER_MISSING_FILENAME_PATTERN,
        BLOCKER_MISSING_PATTERN_TOKEN,
    }
)


@dataclass(frozen=True)
class FinalizationPreviewConflict:
    conflict_id: str
    conflict_type: ConflictType
    affected_item_ids: tuple[str, ...]
    severity: str
    message: str
    blocking: bool
    suggested_resolution: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type,
            "affected_item_ids": list(self.affected_item_ids),
            "severity": self.severity,
            "message": self.message,
            "blocking": bool(self.blocking),
            "suggested_resolution": self.suggested_resolution,
        }


@dataclass(frozen=True)
class FinalizationPreviewBatchItem:
    item_id: str
    source_filename: str
    review_decision_type: str | None
    approved_by_user: bool
    approved_preview_filename: str | None
    target_preview_path: str | None
    finalization_status: FinalizationStatus
    finalization_readiness: FinalizationReadiness | None
    blockers: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    source_hash_at_decision: str | None = None
    preview_state_id: str | None = None
    final_write_allowed: bool = False
    target_conflict_status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        readiness = (
            self.finalization_readiness.to_dict()
            if self.finalization_readiness is not None
            else None
        )
        return {
            "item_id": self.item_id,
            "source_filename": self.source_filename,
            "review_decision_type": self.review_decision_type,
            "review_decision": self.review_decision_type,
            "approved_by_user": bool(self.approved_by_user),
            "approved_preview_filename": self.approved_preview_filename,
            "target_preview_path": self.target_preview_path,
            "finalization_status": self.finalization_status,
            "finalization_readiness": readiness,
            "blockers": list(self.blockers),
            "finalization_blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "finalization_warnings": list(self.warnings),
            "source_hash_at_decision": self.source_hash_at_decision,
            "preview_state_id": self.preview_state_id,
            "final_write_allowed": False,
            "target_conflict_status": self.target_conflict_status,
        }


@dataclass(frozen=True)
class FinalizationPreviewBatch:
    batch_id: str
    preview_state_id: str
    created_at: str
    source_run_id: str | None
    input_root: str | None
    output_root: str | None
    final_write_allowed: bool = False
    productive_mode_requested: bool = False
    source_mutation: bool = False
    total_items: int = 0
    ready_count: int = 0
    blocked_count: int = 0
    ignored_count: int = 0
    deferred_count: int = 0
    still_review_required_count: int = 0
    items: tuple[FinalizationPreviewBatchItem, ...] = field(default_factory=tuple)
    conflicts: tuple[FinalizationPreviewConflict, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    safety_summary: str = MSG_SAFETY_SUMMARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "preview_state_id": self.preview_state_id,
            "created_at": self.created_at,
            "source_run_id": self.source_run_id,
            "input_root": self.input_root,
            "output_root": self.output_root,
            "final_write_allowed": False,
            "productive_mode_requested": False,
            "source_mutation": False,
            "total_items": self.total_items,
            "ready_count": self.ready_count,
            "blocked_count": self.blocked_count,
            "ignored_count": self.ignored_count,
            "deferred_count": self.deferred_count,
            "still_review_required_count": self.still_review_required_count,
            "items": [item.to_dict() for item in self.items],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
            "warnings": list(self.warnings),
            "safety_summary": self.safety_summary,
            "title": MSG_BATCH_TITLE,
            "claims_saas_ready": False,
            "claims_production_ready": False,
        }


@dataclass
class FinalizationPreviewBatchBag:
    """In-memory bag for the last built finalization preview batch."""

    last_batch: FinalizationPreviewBatch | None = None
    called_run_once: bool = False
    mutated_input: bool = False
    wrote_final_pdfs: bool = False
    touched_real_invoice_folders: bool = False
    last_feedback: str = ""

    def reset(self) -> None:
        self.last_batch = None
        self.called_run_once = False
        self.mutated_input = False
        self.wrote_final_pdfs = False
        self.touched_real_invoice_folders = False
        self.last_feedback = ""


def get_finalization_preview_batch_bag(state: Any) -> FinalizationPreviewBatchBag:
    bag = getattr(state, "finalization_preview_batch_ui", None)
    if isinstance(bag, FinalizationPreviewBatchBag):
        return bag
    bag = FinalizationPreviewBatchBag()
    try:
        state.finalization_preview_batch_ui = bag
    except Exception:
        pass
    return bag


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _new_batch_id() -> str:
    return f"fpb-{uuid.uuid4().hex[:12]}"


def _new_conflict_id(conflict_type: str) -> str:
    return f"fpc-{conflict_type}-{uuid.uuid4().hex[:8]}"


def _basename(path_or_name: str | None) -> str:
    text = _text(path_or_name)
    if not text:
        return ""
    return Path(text).name.lower()


def _norm_path_key(path_or_name: str | None) -> str:
    text = _text(path_or_name)
    if not text:
        return ""
    return text.replace("\\", "/").lower()


def _blocker_to_conflict_type(blocker: str) -> ConflictType | None:
    if blocker == BLOCKER_DUPLICATE_TARGET_FILENAME:
        return CONFLICT_DUPLICATE_TARGET_FILENAME
    if blocker == BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT:
        return CONFLICT_UNSAFE_TARGET_PATH
    if blocker == BLOCKER_STALE_PREVIEW_STATE:
        return CONFLICT_STALE_PREVIEW_STATE
    if blocker == BLOCKER_SOURCE_HASH_CHANGED:
        return CONFLICT_CHANGED_SOURCE_HASH
    if blocker == BLOCKER_NO_EXPLICIT_USER_APPROVAL:
        return CONFLICT_MISSING_APPROVAL
    if blocker in _MISSING_FIELD_BLOCKERS:
        return CONFLICT_MISSING_REQUIRED_FIELD
    if blocker == BLOCKER_MISSING_OR_UNCLEAR_CONFIGURATION:
        return CONFLICT_UNRESOLVED_CONFIGURATION
    if blocker in _INCOMPLETE_FILENAME_BLOCKERS:
        return CONFLICT_INCOMPLETE_FILENAME
    return None


def _make_conflict(
    *,
    conflict_type: ConflictType,
    affected_item_ids: Sequence[str],
    message: str,
    blocking: bool,
    severity: str | None = None,
) -> FinalizationPreviewConflict:
    return FinalizationPreviewConflict(
        conflict_id=_new_conflict_id(conflict_type),
        conflict_type=conflict_type,
        affected_item_ids=tuple(dict.fromkeys(str(i) for i in affected_item_ids if i)),
        severity=severity or ("error" if blocking else "info"),
        message=message,
        blocking=bool(blocking),
        suggested_resolution=_SUGGESTED_RESOLUTION.get(
            conflict_type, "Konflikt prüfen und Entscheidung erneut treffen."
        ),
    )


def _collect_review_item_keys(state: Any) -> list[str]:
    run = getattr(state, "processing_run_state", None)
    keys: list[str] = []
    known_source_names: set[str] = set()
    if run is not None:
        for item in getattr(run, "review_items", ()) or ():
            key = review_item_key(item)
            if key:
                keys.append(key)
            name = _text(getattr(item, "document_name", None))
            if name:
                known_source_names.add(name)
        for planned in getattr(run, "planned_destinations", ()) or ():
            name = _text(getattr(planned, "document_name", None))
            if not name or name in known_source_names or name in keys:
                continue
            # Fallback only when no review-item key already covers this source.
            keys.append(name)
            known_source_names.add(name)
    bag = get_review_decision_bag(state)
    for key in bag.decisions_by_item_key:
        if key not in keys:
            keys.append(key)
    # Deduplicate while preserving order.
    return list(dict.fromkeys(keys))


def _source_filename_for(state: Any, item_id: str) -> str:
    run = getattr(state, "processing_run_state", None)
    if run is not None:
        for item in getattr(run, "review_items", ()) or ():
            if review_item_key(item) == item_id:
                return _text(getattr(item, "document_name", None)) or item_id
        for planned in getattr(run, "planned_destinations", ()) or ():
            name = _text(getattr(planned, "document_name", None))
            if name == item_id:
                return name
    decision = get_review_decision_bag(state).decisions_by_item_key.get(item_id)
    if decision is not None:
        return decision.source_filename or item_id
    return item_id


def _detect_duplicate_maps(
    candidates: Sequence[tuple[str, str | None, str | None]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Return filename→item_ids and path→item_ids for duplicates among accept/edit."""

    by_filename: dict[str, list[str]] = {}
    by_path: dict[str, list[str]] = {}
    for item_id, filename, target in candidates:
        name_key = _basename(filename) or _basename(target)
        path_key = _norm_path_key(target)
        if name_key:
            by_filename.setdefault(name_key, []).append(item_id)
        if path_key:
            by_path.setdefault(path_key, []).append(item_id)
    return by_filename, by_path


def _status_for_decision(
    decision: ReviewDecision | None,
    *,
    blockers: Sequence[str],
    ready: bool,
) -> FinalizationStatus:
    if decision is None:
        return STATUS_STILL_REVIEW
    if decision.decision_type == DECISION_IGNORE:
        return STATUS_IGNORED
    if decision.decision_type == DECISION_DEFER:
        return STATUS_DEFERRED
    if decision.decision_type == DECISION_KEEP_REVIEW:
        return STATUS_STILL_REVIEW
    if decision.decision_type == DECISION_NEEDS_CONFIG:
        return STATUS_BLOCKED
    if decision.decision_type in {DECISION_ACCEPT, DECISION_EDIT}:
        if ready and not blockers:
            return STATUS_READY
        return STATUS_BLOCKED
    return STATUS_STILL_REVIEW


def build_finalization_preview_batch(
    state: Any,
    *,
    preview_state_fresh: bool = True,
    expected_preview_state_id: str | None = None,
    current_source_hashes: Mapping[str, str] | None = None,
    store_on_state: bool = True,
) -> FinalizationPreviewBatch:
    """Pure batch builder from current review decisions — preview/audit only."""

    decision_bag = get_review_decision_bag(state)
    preview_state_id = ensure_preview_state_id(state)
    run = getattr(state, "processing_run_state", None)
    source_run_id = _text(getattr(run, "run_id", None)) or None
    input_root = _text(getattr(state, "workspace_input_folder_override", None)) or None
    output_root = _text(getattr(state, "workspace_output_folder_override", None)) or None

    item_ids = _collect_review_item_keys(state)
    accept_candidates: list[tuple[str, str | None, str | None]] = []
    for item_id in item_ids:
        decision = decision_bag.decisions_by_item_key.get(item_id)
        if decision is None:
            continue
        if decision.decision_type not in {DECISION_ACCEPT, DECISION_EDIT}:
            continue
        if decision.exclude_from_finalization_batch:
            continue
        accept_candidates.append(
            (
                item_id,
                decision.approved_preview_filename,
                decision.approved_target_preview_path,
            )
        )
    by_filename, by_path = _detect_duplicate_maps(accept_candidates)
    duplicate_filename_ids = {
        item_id
        for ids in by_filename.values()
        if len(set(ids)) > 1
        for item_id in ids
    }
    duplicate_path_ids = {
        item_id
        for ids in by_path.values()
        if len(set(ids)) > 1
        for item_id in ids
    }

    conflicts: list[FinalizationPreviewConflict] = []
    for name_key, ids in by_filename.items():
        unique = list(dict.fromkeys(ids))
        if len(unique) > 1:
            conflicts.append(
                _make_conflict(
                    conflict_type=CONFLICT_DUPLICATE_TARGET_FILENAME,
                    affected_item_ids=unique,
                    message=(
                        f"Doppelter freigegebener Zieldateiname: {name_key}"
                    ),
                    blocking=True,
                )
            )
    for path_key, ids in by_path.items():
        unique = list(dict.fromkeys(ids))
        if len(unique) > 1:
            conflicts.append(
                _make_conflict(
                    conflict_type=CONFLICT_DUPLICATE_TARGET_PATH,
                    affected_item_ids=unique,
                    message=f"Doppelter freigegebener Zielpfad: {path_key}",
                    blocking=True,
                )
            )

    batch_items: list[FinalizationPreviewBatchItem] = []
    batch_warnings: list[str] = [MSG_BATCH_NO_FINAL_WRITE, MSG_SAFETY_SUMMARY]
    hash_map = dict(current_source_hashes or {})

    for item_id in item_ids:
        decision = decision_bag.decisions_by_item_key.get(item_id)
        readiness = decision_bag.readiness_by_item_key.get(item_id)
        source_filename = _source_filename_for(state, item_id)
        blockers: list[str] = []
        warnings: list[str] = []
        if readiness is not None:
            blockers.extend(readiness.blockers)
            warnings.extend(readiness.warnings)
        elif decision is not None:
            blockers.extend(decision.finalization_blockers)

        if item_id in duplicate_filename_ids:
            if BLOCKER_DUPLICATE_TARGET_FILENAME not in blockers:
                blockers.append(BLOCKER_DUPLICATE_TARGET_FILENAME)
        if item_id in duplicate_path_ids:
            # Path duplicate is reported as conflict; also block readiness.
            if BLOCKER_DUPLICATE_TARGET_FILENAME not in blockers:
                blockers.append(BLOCKER_DUPLICATE_TARGET_FILENAME)

        # Stale preview state checks.
        if not preview_state_fresh:
            if BLOCKER_STALE_PREVIEW_STATE not in blockers:
                blockers.append(BLOCKER_STALE_PREVIEW_STATE)
        if expected_preview_state_id and decision is not None:
            if _text(decision.preview_state_id) and _text(
                decision.preview_state_id
            ) != _text(expected_preview_state_id):
                if BLOCKER_STALE_PREVIEW_STATE not in blockers:
                    blockers.append(BLOCKER_STALE_PREVIEW_STATE)
        if expected_preview_state_id and _text(expected_preview_state_id) != _text(
            preview_state_id
        ):
            if BLOCKER_STALE_PREVIEW_STATE not in blockers:
                blockers.append(BLOCKER_STALE_PREVIEW_STATE)

        # Source hash change checks.
        if decision is not None and decision.source_hash_at_decision:
            current_hash = (
                hash_map.get(item_id)
                or hash_map.get(source_filename)
                or hash_map.get(decision.source_filename)
            )
            if current_hash and _text(current_hash) != _text(
                decision.source_hash_at_decision
            ):
                if BLOCKER_SOURCE_HASH_CHANGED not in blockers:
                    blockers.append(BLOCKER_SOURCE_HASH_CHANGED)

        blockers_tuple = tuple(dict.fromkeys(blockers))
        warnings_tuple = tuple(dict.fromkeys(warnings))

        approved = bool(
            decision is not None
            and decision.decided_by_user
            and decision.decision_type in {DECISION_ACCEPT, DECISION_EDIT}
        )
        ready_flag = bool(
            readiness.ready if readiness is not None else False
        ) and not blockers_tuple
        if decision is not None and decision.decision_type in {
            DECISION_ACCEPT,
            DECISION_EDIT,
        }:
            # Accept/edit ready only when gates pass (except final_write_allowed).
            ready_flag = approved and not blockers_tuple
        else:
            ready_flag = False

        status = _status_for_decision(
            decision, blockers=blockers_tuple, ready=ready_flag
        )
        # Non-accept statuses must not appear as ready even if blockers empty.
        if status != STATUS_READY:
            ready_flag = False

        target_conflict = "ok"
        if item_id in duplicate_filename_ids or item_id in duplicate_path_ids:
            target_conflict = "duplicate"
        elif BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT in blockers_tuple:
            target_conflict = "conflict"
        elif readiness is not None and readiness.target_conflict_status != "ok":
            target_conflict = readiness.target_conflict_status

        if readiness is not None and blockers_tuple != readiness.blockers:
            readiness = replace(
                readiness,
                ready=ready_flag and status == STATUS_READY,
                decision_ready_for_future_finalization=(
                    ready_flag and status == STATUS_READY
                ),
                blockers=blockers_tuple,
                target_conflict_status=target_conflict,
                final_write_allowed=False,
            )

        batch_items.append(
            FinalizationPreviewBatchItem(
                item_id=item_id,
                source_filename=source_filename,
                review_decision_type=(
                    decision.decision_type if decision is not None else None
                ),
                approved_by_user=approved,
                approved_preview_filename=(
                    decision.approved_preview_filename if decision else None
                ),
                target_preview_path=(
                    decision.approved_target_preview_path if decision else None
                ),
                finalization_status=status,
                finalization_readiness=readiness,
                blockers=blockers_tuple,
                warnings=warnings_tuple,
                source_hash_at_decision=(
                    decision.source_hash_at_decision if decision else None
                ),
                preview_state_id=(
                    decision.preview_state_id if decision else preview_state_id
                ),
                final_write_allowed=False,
                target_conflict_status=target_conflict,
            )
        )

        # Item-level conflicts from blockers (deduped later by type+items).
        for blocker in blockers_tuple:
            conflict_type = _blocker_to_conflict_type(blocker)
            if conflict_type is None:
                continue
            # Duplicate filename/path already emitted from maps.
            if conflict_type in {
                CONFLICT_DUPLICATE_TARGET_FILENAME,
                CONFLICT_DUPLICATE_TARGET_PATH,
            }:
                continue
            conflicts.append(
                _make_conflict(
                    conflict_type=conflict_type,
                    affected_item_ids=(item_id,),
                    message=f"{conflict_type}: {source_filename or item_id}",
                    blocking=True,
                )
            )

        if status == STATUS_IGNORED:
            conflicts.append(
                _make_conflict(
                    conflict_type=CONFLICT_IGNORED_ITEM,
                    affected_item_ids=(item_id,),
                    message=f"Ignoriert / nicht exportieren: {source_filename}",
                    blocking=False,
                    severity="info",
                )
            )
        elif status == STATUS_DEFERRED:
            conflicts.append(
                _make_conflict(
                    conflict_type=CONFLICT_DEFERRED_ITEM,
                    affected_item_ids=(item_id,),
                    message=f"Zurückgestellt: {source_filename}",
                    blocking=False,
                    severity="info",
                )
            )

    # Merge identical conflict types for same item sets where helpful —
    # keep all conflicts but collapse exact duplicates.
    deduped: list[FinalizationPreviewConflict] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    for conflict in conflicts:
        key = (
            conflict.conflict_type,
            tuple(conflict.affected_item_ids),
            conflict.message,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(conflict)

    ready_count = sum(
        1 for item in batch_items if item.finalization_status == STATUS_READY
    )
    blocked_count = sum(
        1 for item in batch_items if item.finalization_status == STATUS_BLOCKED
    )
    ignored_count = sum(
        1 for item in batch_items if item.finalization_status == STATUS_IGNORED
    )
    deferred_count = sum(
        1 for item in batch_items if item.finalization_status == STATUS_DEFERRED
    )
    still_review_count = sum(
        1 for item in batch_items if item.finalization_status == STATUS_STILL_REVIEW
    )

    batch = FinalizationPreviewBatch(
        batch_id=_new_batch_id(),
        preview_state_id=preview_state_id,
        created_at=_utc_now(),
        source_run_id=source_run_id,
        input_root=input_root,
        output_root=output_root,
        final_write_allowed=False,
        productive_mode_requested=False,
        source_mutation=False,
        total_items=len(batch_items),
        ready_count=ready_count,
        blocked_count=blocked_count,
        ignored_count=ignored_count,
        deferred_count=deferred_count,
        still_review_required_count=still_review_count,
        items=tuple(batch_items),
        conflicts=tuple(deduped),
        warnings=tuple(dict.fromkeys(batch_warnings)),
        safety_summary=MSG_SAFETY_SUMMARY,
    )
    assert batch.final_write_allowed is False
    assert FINAL_WRITE_ALLOWED_IN_THIS_PHASE is False
    assert final_write_allowed() is False
    for item in batch.items:
        assert item.final_write_allowed is False

    if store_on_state:
        bag = get_finalization_preview_batch_bag(state)
        bag.last_batch = batch
        bag.called_run_once = False
        bag.mutated_input = False
        bag.wrote_final_pdfs = False
        bag.touched_real_invoice_folders = False
        bag.last_feedback = (
            f"{MSG_BATCH_TITLE}: {MSG_BATCH_READY} {ready_count} · "
            f"{MSG_BATCH_BLOCKED} {blocked_count} · {MSG_BATCH_NO_FINAL_WRITE}"
        )

    return batch


def batch_summary_lines(batch: FinalizationPreviewBatch | None) -> tuple[str, ...]:
    if batch is None:
        return (
            MSG_BATCH_TITLE,
            f"{MSG_BATCH_READY}: 0",
            f"{MSG_BATCH_BLOCKED}: 0",
            f"{MSG_BATCH_IGNORED}: 0",
            f"{MSG_BATCH_DEFERRED}: 0",
            f"{MSG_BATCH_STILL_REVIEW}: 0",
            MSG_BATCH_NO_FINAL_WRITE,
        )
    lines = [
        MSG_BATCH_TITLE,
        f"{MSG_BATCH_READY}: {batch.ready_count}",
        f"{MSG_BATCH_BLOCKED}: {batch.blocked_count}",
        f"{MSG_BATCH_IGNORED}: {batch.ignored_count}",
        f"{MSG_BATCH_DEFERRED}: {batch.deferred_count}",
        f"{MSG_BATCH_STILL_REVIEW}: {batch.still_review_required_count}",
        MSG_BATCH_NO_FINAL_WRITE,
    ]
    blocking = [c for c in batch.conflicts if c.blocking]
    if blocking:
        lines.append(f"Konflikte (blockierend): {len(blocking)}")
        for conflict in blocking[:8]:
            lines.append(
                f"- {conflict.conflict_type} "
                f"({len(conflict.affected_item_ids)}): {conflict.message}"
            )
            lines.append(f"  → {conflict.suggested_resolution}")
    return tuple(lines)


def batch_report_fields(batch: FinalizationPreviewBatch | None) -> dict[str, Any]:
    """Manifest-level finalization_preview_batch payload."""

    if batch is None:
        return {
            "finalization_preview_batch": None,
            "final_write_allowed": False,
            "ready_count": 0,
            "blocked_count": 0,
            "ignored_count": 0,
            "deferred_count": 0,
            "still_review_required_count": 0,
            "conflicts": [],
            "safety_summary": MSG_SAFETY_SUMMARY,
        }
    payload = batch.to_dict()
    return {
        "finalization_preview_batch": payload,
        "final_write_allowed": False,
        "ready_count": batch.ready_count,
        "blocked_count": batch.blocked_count,
        "ignored_count": batch.ignored_count,
        "deferred_count": batch.deferred_count,
        "still_review_required_count": batch.still_review_required_count,
        "conflicts": [c.to_dict() for c in batch.conflicts],
        "safety_summary": batch.safety_summary,
    }


def item_batch_export_fields(
    batch: FinalizationPreviewBatch | None, item_key: str
) -> dict[str, Any]:
    if batch is None:
        return {
            "finalization_status": None,
            "finalization_blockers": [],
            "finalization_warnings": [],
            "target_conflict_status": "ok",
            "final_write_allowed": False,
        }
    for item in batch.items:
        if item.item_id == item_key or item.source_filename == item_key:
            return {
                "finalization_status": item.finalization_status,
                "finalization_blockers": list(item.blockers),
                "finalization_warnings": list(item.warnings),
                "target_conflict_status": item.target_conflict_status,
                "final_write_allowed": False,
            }
    return {
        "finalization_status": None,
        "finalization_blockers": [],
        "finalization_warnings": [],
        "target_conflict_status": "ok",
        "final_write_allowed": False,
    }


def batch_builder_calls_run_once() -> bool:
    return False


def batch_builder_mutates_input() -> bool:
    return False


def batch_builder_writes_final_pdfs() -> bool:
    return False


def batch_builder_touches_real_invoice_folders() -> bool:
    return False


def batch_builder_claims_saas_ready() -> bool:
    return False


def batch_builder_claims_production_ready() -> bool:
    return False


__all__ = (
    "CONFLICT_CHANGED_SOURCE_HASH",
    "CONFLICT_DEFERRED_ITEM",
    "CONFLICT_DUPLICATE_TARGET_FILENAME",
    "CONFLICT_DUPLICATE_TARGET_PATH",
    "CONFLICT_IGNORED_ITEM",
    "CONFLICT_INCOMPLETE_FILENAME",
    "CONFLICT_MISSING_APPROVAL",
    "CONFLICT_MISSING_REQUIRED_FIELD",
    "CONFLICT_STALE_PREVIEW_STATE",
    "CONFLICT_UNRESOLVED_CONFIGURATION",
    "CONFLICT_UNSAFE_TARGET_PATH",
    "FinalizationPreviewBatch",
    "FinalizationPreviewBatchBag",
    "FinalizationPreviewBatchItem",
    "FinalizationPreviewConflict",
    "MSG_BATCH_BLOCKED",
    "MSG_BATCH_DEFERRED",
    "MSG_BATCH_IGNORED",
    "MSG_BATCH_NO_FINAL_WRITE",
    "MSG_BATCH_READY",
    "MSG_BATCH_STILL_REVIEW",
    "MSG_BATCH_TITLE",
    "MSG_SAFETY_SUMMARY",
    "STATUS_BLOCKED",
    "STATUS_DEFERRED",
    "STATUS_IGNORED",
    "STATUS_READY",
    "STATUS_STILL_REVIEW",
    "batch_builder_calls_run_once",
    "batch_builder_claims_production_ready",
    "batch_builder_claims_saas_ready",
    "batch_builder_mutates_input",
    "batch_builder_touches_real_invoice_folders",
    "batch_builder_writes_final_pdfs",
    "batch_report_fields",
    "batch_summary_lines",
    "build_finalization_preview_batch",
    "get_finalization_preview_batch_bag",
    "item_batch_export_fields",
)
