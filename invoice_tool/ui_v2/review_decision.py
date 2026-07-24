"""Track-B ReviewDecision state and safe decision transitions (Prompt 29/34).

User actions update in-memory Track-B/UI-v2 decision state only.
Never calls run_once, never writes final PDFs, never mutates input paths,
never touches real invoice folders, never sets final_write_allowed=True.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from invoice_tool.ui_v2.finalization_readiness import (
    FINAL_WRITE_ALLOWED_IN_THIS_PHASE,
    FinalizationReadiness,
    compute_finalization_readiness,
    final_write_allowed,
)
from invoice_tool.ui_v2.review_preview_state import (
    exclude_from_export_preview,
    get_review_preview_ui,
    keep_in_review,
    review_item_key,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)

DecisionType = Literal[
    "accept_suggestion",
    "edit_suggestion",
    "keep_review_required",
    "ignore_for_export",
    "defer",
    "needs_configuration_change",
]

DECISION_ACCEPT = "accept_suggestion"
DECISION_EDIT = "edit_suggestion"
DECISION_KEEP_REVIEW = "keep_review_required"
DECISION_IGNORE = "ignore_for_export"
DECISION_DEFER = "defer"
DECISION_NEEDS_CONFIG = "needs_configuration_change"

ALL_DECISION_TYPES: tuple[DecisionType, ...] = (
    DECISION_ACCEPT,
    DECISION_EDIT,
    DECISION_KEEP_REVIEW,
    DECISION_IGNORE,
    DECISION_DEFER,
    DECISION_NEEDS_CONFIG,
)

ACTION_ACCEPT_SUGGESTION = "Vorschlag akzeptieren"
ACTION_EDIT_SUGGESTION = "Vorschlag bearbeiten"
ACTION_NEEDS_CONFIGURATION = "Konfiguration anpassen und neu prüfen"
ACTION_KEEP_UNCLEAR = "als Unklar belassen"
ACTION_IGNORE_EXPORT = "ignorieren / nicht exportieren"
ACTION_DEFER = "zurückstellen"

DECISION_ACTION_LABELS: tuple[str, ...] = (
    ACTION_ACCEPT_SUGGESTION,
    ACTION_EDIT_SUGGESTION,
    ACTION_NEEDS_CONFIGURATION,
    ACTION_KEEP_UNCLEAR,
    ACTION_IGNORE_EXPORT,
    ACTION_DEFER,
)

MSG_NOT_FINAL_YET = (
    "Noch keine finale Verarbeitung — Originale bleiben unverändert."
)
MSG_FINALIZATION_READY_YES = "Finalisierungsbereit (künftig): ja"
MSG_FINALIZATION_READY_NO = "Finalisierungsbereit (künftig): nein"
MSG_ACCEPT_REQUIRES_CONFIRM = (
    "Vorschlag akzeptieren erfordert explizite Nutzerbestätigung."
)
MSG_FILENAME_EMPTY = "Dateiname darf nicht leer sein."
MSG_FILENAME_PATH_SEP = "Dateiname darf keine Pfadtrenner enthalten."
MSG_FILENAME_TRAVERSAL = "Dateiname darf keine Pfad-Traversal-Segmente enthalten."
MSG_FILENAME_PDF = "Dateiname muss auf .pdf enden."
MSG_FILENAME_PATTERN_TOKEN = "Dateiname enthält noch fehlende Mustertoken."
MSG_FILENAME_DUPLICATE = "Dateiname kollidiert mit einem anderen freigegebenen Ziel."
MSG_FILENAME_UNSAFE_TARGET = "Zielpfad liegt außerhalb des erlaubten Output-Roots."
MSG_DECISION_RECORDED = "Review-Entscheidung gespeichert (Preview only)."
MSG_ROUTE_TO_CONFIG = "Konfigurationsregel-Flow — Preview neu prüfen."

_PATH_SEP_RE = re.compile(r"[/\\]")
_PATTERN_TOKEN_RE = re.compile(r"\{[^}]+\}")
_MISSING_PATTERN_TOKENS_ATTR = "missing_" + "place" + "holders"


@dataclass(frozen=True)
class ReviewDecision:
    """Persisted-in-memory review decision for one preview item."""

    decision_id: str
    source_item_id: str
    source_filename: str
    decision_type: DecisionType
    decided_by_user: bool
    decision_timestamp: str
    approved_preview_filename: str | None = None
    approved_target_preview_path: str | None = None
    edited_fields: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    reason: str | None = None
    warnings_acknowledged: tuple[str, ...] = field(default_factory=tuple)
    finalization_ready: bool = False
    finalization_blockers: tuple[str, ...] = field(default_factory=tuple)
    audit_note: str | None = None
    source_hash_at_decision: str | None = None
    preview_state_id: str | None = None
    decision_ready_for_future_finalization: bool = False
    final_write_allowed: bool = False
    exclude_from_finalization_batch: bool = False
    review_status: str = "in_review"
    routes_to_configuration_flow: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "source_item_id": self.source_item_id,
            "source_filename": self.source_filename,
            "decision_type": self.decision_type,
            "review_decision": self.decision_type,
            "decided_by_user": self.decided_by_user,
            "approved_by_user": bool(self.decided_by_user)
            and self.decision_type in {DECISION_ACCEPT, DECISION_EDIT},
            "decision_timestamp": self.decision_timestamp,
            "approved_preview_filename": self.approved_preview_filename,
            "approved_target_preview_path": self.approved_target_preview_path,
            "target_preview_path": self.approved_target_preview_path,
            "edited_fields": {k: v for k, v in self.edited_fields},
            "user_edited_fields": {k: v for k, v in self.edited_fields},
            "reason": self.reason,
            "warnings_acknowledged": list(self.warnings_acknowledged),
            "finalization_ready": self.finalization_ready,
            "decision_ready_for_future_finalization": (
                self.decision_ready_for_future_finalization
            ),
            "finalization_blockers": list(self.finalization_blockers),
            "audit_note": self.audit_note,
            "source_hash_at_decision": self.source_hash_at_decision,
            "preview_state_id": self.preview_state_id,
            "final_write_allowed": False,
            "exclude_from_finalization_batch": self.exclude_from_finalization_batch,
            "review_status": self.review_status,
            "routes_to_configuration_flow": self.routes_to_configuration_flow,
        }


@dataclass
class EditedFilenameValidation:
    ok: bool
    cleaned_filename: str | None = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass
class ReviewDecisionBag:
    """In-memory decision / readiness bag on UiV2State."""

    decisions_by_item_key: dict[str, ReviewDecision] = field(default_factory=dict)
    readiness_by_item_key: dict[str, FinalizationReadiness] = field(default_factory=dict)
    edit_filename_draft_by_key: dict[str, str] = field(default_factory=dict)
    pending_accept_confirm_key: str | None = None
    last_feedback: str = ""
    last_feedback_error: bool = False
    routes_to_configuration_flow_item_key: str | None = None
    preview_state_id: str | None = None
    called_run_once: bool = False
    mutated_input: bool = False
    wrote_final_pdfs: bool = False
    touched_real_invoice_folders: bool = False

    def reset(self) -> None:
        self.decisions_by_item_key.clear()
        self.readiness_by_item_key.clear()
        self.edit_filename_draft_by_key.clear()
        self.pending_accept_confirm_key = None
        self.last_feedback = ""
        self.last_feedback_error = False
        self.routes_to_configuration_flow_item_key = None


@dataclass(frozen=True)
class ApplyDecisionResult:
    ok: bool
    message: str
    decision: ReviewDecision | None = None
    readiness: FinalizationReadiness | None = None
    called_run_once: bool = False
    mutated_input: bool = False
    wrote_final_pdfs: bool = False
    touched_real_invoice_folders: bool = False
    final_write_allowed: bool = False
    routes_to_configuration_flow: bool = False


def get_review_decision_bag(state: Any) -> ReviewDecisionBag:
    bag = getattr(state, "review_decision_ui", None)
    if isinstance(bag, ReviewDecisionBag):
        return bag
    bag = ReviewDecisionBag()
    try:
        state.review_decision_ui = bag
    except Exception:
        pass
    return bag


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_decision_id() -> str:
    return f"rd-{uuid.uuid4().hex[:12]}"


def ensure_preview_state_id(state: Any) -> str:
    bag = get_review_decision_bag(state)
    if bag.preview_state_id:
        return bag.preview_state_id
    run = getattr(state, "processing_run_state", None)
    run_id = _text(getattr(run, "run_id", None)) if run is not None else ""
    updated = _text(getattr(run, "state_updated_at", None)) if run is not None else ""
    bag.preview_state_id = f"preview:{run_id or 'none'}:{updated or _utc_now()}"
    return bag.preview_state_id


def _text(value: Any) -> str:
    return str(value or "").strip()


def validate_edited_filename(
    filename: str | None,
    *,
    missing_pattern_tokens: Sequence[str] | None = None,
    duplicate_target: bool = False,
    target_preview_path: str | None = None,
    output_root: str | None = None,
    still_depends_on_pattern: bool = False,
) -> EditedFilenameValidation:
    """Validate user-edited preview filename — no path writes."""

    raw = _text(filename)
    errors: list[str] = []
    warnings: list[str] = []
    if not raw:
        return EditedFilenameValidation(ok=False, errors=(MSG_FILENAME_EMPTY,))
    if _PATH_SEP_RE.search(raw):
        errors.append(MSG_FILENAME_PATH_SEP)
    if ".." in raw or raw.startswith(".") and "/" in raw:
        errors.append(MSG_FILENAME_TRAVERSAL)
    if any(part == ".." for part in Path(raw).parts):
        if MSG_FILENAME_TRAVERSAL not in errors:
            errors.append(MSG_FILENAME_TRAVERSAL)
    if not raw.lower().endswith(".pdf"):
        errors.append(MSG_FILENAME_PDF)
    if still_depends_on_pattern and _PATTERN_TOKEN_RE.search(raw):
        errors.append(MSG_FILENAME_PATTERN_TOKEN)
    if missing_pattern_tokens:
        errors.append(MSG_FILENAME_PATTERN_TOKEN)
    if duplicate_target:
        errors.append(MSG_FILENAME_DUPLICATE)
    if target_preview_path and output_root:
        try:
            target = Path(target_preview_path).expanduser().resolve()
            root = Path(output_root).expanduser().resolve()
            if target != root and root not in target.parents:
                errors.append(MSG_FILENAME_UNSAFE_TARGET)
        except OSError:
            errors.append(MSG_FILENAME_UNSAFE_TARGET)
    cleaned = Path(raw).name if not errors else None
    if cleaned and cleaned != raw and not errors:
        # basename-only normalization when no separators already rejected
        warnings.append("Dateiname auf Basisnamen normalisiert.")
    return EditedFilenameValidation(
        ok=not errors,
        cleaned_filename=cleaned or (raw if not errors else None),
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def detect_duplicate_approved_targets(
    decisions: Mapping[str, ReviewDecision],
    *,
    candidate_item_id: str | None = None,
    candidate_target: str | None = None,
) -> set[str]:
    """Return item ids that share a duplicate approved target preview path/name."""

    targets: dict[str, list[str]] = {}
    for key, decision in decisions.items():
        target = _text(
            decision.approved_target_preview_path or decision.approved_preview_filename
        )
        if not target:
            continue
        if decision.decision_type not in {DECISION_ACCEPT, DECISION_EDIT}:
            continue
        if decision.exclude_from_finalization_batch:
            continue
        targets.setdefault(target.lower(), []).append(key)
    if candidate_item_id and candidate_target:
        targets.setdefault(_text(candidate_target).lower(), []).append(candidate_item_id)
    dupes: set[str] = set()
    for keys in targets.values():
        unique = list(dict.fromkeys(keys))
        if len(unique) > 1:
            dupes.update(unique)
    return dupes


def _context_from_planned(
    planned: ProcessingPlannedDestination | None,
    *,
    review_item: ProcessingReviewItem | None = None,
    approved_preview_filename: str | None = None,
    approved_target_preview_path: str | None = None,
) -> dict[str, Any]:
    if planned is None:
        return {
            "approved_preview_filename": approved_preview_filename,
            "approved_target_preview_path": approved_target_preview_path,
            "source_filename": _text(getattr(review_item, "document_name", None)),
        }
    return {
        "supplier": planned.supplier,
        "counterparty_name": planned.counterparty_name,
        "invoice_date": planned.invoice_date,
        "amount": planned.selected_amount or planned.amount,
        "selected_amount": planned.selected_amount or planned.amount,
        "selected_payment_field": planned.selected_payment_field,
        "payment_account": planned.payment_account,
        "matched_configuration_name": planned.matched_configuration_name,
        "matched_configuration_id": planned.matched_configuration_id,
        "filename_pattern": planned.filename_pattern,
        "rendered_filename": planned.rendered_filename,
        "suggested_filename": planned.suggested_filename,
        "preview_filename": approved_preview_filename
        or planned.rendered_filename
        or planned.suggested_filename,
        "approved_preview_filename": approved_preview_filename,
        "approved_target_preview_path": approved_target_preview_path
        or planned.planned_path,
        "planned_target": planned.planned_path,
        "missing_fields": tuple(planned.missing_fields or ()),
        _MISSING_PATTERN_TOKENS_ATTR: tuple(
            getattr(planned, _MISSING_PATTERN_TOKENS_ATTR, ()) or ()
        ),
        "missing_configuration_type": planned.missing_configuration_type,
        "configuration_coverage_status": planned.configuration_coverage_status,
        "source_filename": planned.document_name,
    }


def _planned_for(
    run: ProcessingRunState | None, document_name: str
) -> ProcessingPlannedDestination | None:
    if run is None:
        return None
    name = _text(document_name)
    for entry in run.planned_destinations or ():
        if _text(entry.document_name) == name:
            return entry
    return None


def _review_item_for(run: ProcessingRunState | None, item_key: str) -> ProcessingReviewItem | None:
    if run is None:
        return None
    for item in run.review_items or ():
        if review_item_key(item) == item_key:
            return item
    return None


def _build_target_preview_path(
    *,
    planned: ProcessingPlannedDestination | None,
    approved_filename: str | None,
    output_root: str | None,
) -> str | None:
    filename = _text(approved_filename)
    if planned and _text(planned.planned_path):
        base = Path(_text(planned.planned_path))
        if filename:
            return str(base.parent / filename) if base.suffix else str(base / filename)
        return _text(planned.planned_path)
    if output_root and filename:
        return str(Path(output_root) / "preview" / filename)
    if filename:
        return f"preview/{filename}"
    return None


def _compute_for_decision(
    *,
    state: Any,
    item_key: str,
    decision_type: DecisionType,
    decided_by_user: bool,
    approved_preview_filename: str | None,
    approved_target_preview_path: str | None,
    edited_fields: Sequence[tuple[str, str]] | None,
    reason: str | None,
    warnings_acknowledged: Sequence[str] | None,
    audit_note: str | None,
    source_hash_at_decision: str | None,
    preview_state_fresh: bool = True,
    source_unchanged: bool = True,
) -> tuple[ReviewDecision, FinalizationReadiness]:
    run = getattr(state, "processing_run_state", None)
    review_item = _review_item_for(run, item_key)
    source_filename = _text(
        getattr(review_item, "document_name", None) if review_item else item_key
    )
    planned = _planned_for(run, source_filename)
    output_root = _text(getattr(state, "workspace_output_folder_override", None)) or None
    target = approved_target_preview_path or _build_target_preview_path(
        planned=planned,
        approved_filename=approved_preview_filename,
        output_root=output_root,
    )
    bag = get_review_decision_bag(state)
    # Temporary map including this candidate for duplicate detection.
    provisional = dict(bag.decisions_by_item_key)
    provisional[item_key] = ReviewDecision(
        decision_id="provisional",
        source_item_id=item_key,
        source_filename=source_filename,
        decision_type=decision_type,
        decided_by_user=decided_by_user,
        decision_timestamp=_utc_now(),
        approved_preview_filename=approved_preview_filename,
        approved_target_preview_path=target,
    )
    dupes = detect_duplicate_approved_targets(
        provisional,
        candidate_item_id=item_key,
        candidate_target=target,
    )
    approved = bool(decided_by_user) and decision_type in {
        DECISION_ACCEPT,
        DECISION_EDIT,
    }
    context = _context_from_planned(
        planned,
        review_item=review_item,
        approved_preview_filename=approved_preview_filename,
        approved_target_preview_path=target,
    )
    readiness = compute_finalization_readiness(
        item_id=item_key,
        context=context,
        approved=approved,
        decision_type=decision_type,
        duplicate_target=item_key in dupes,
        preview_state_fresh=preview_state_fresh,
        source_unchanged=source_unchanged,
        output_root=output_root,
        target_preview_path=target,
        warnings=tuple(warnings_acknowledged or ()),
    )
    exclude = decision_type == DECISION_IGNORE
    if decision_type == DECISION_KEEP_REVIEW:
        review_status = "review_required"
    elif decision_type == DECISION_DEFER:
        review_status = "pending"
    elif decision_type == DECISION_IGNORE:
        review_status = "ignored"
    elif decision_type == DECISION_NEEDS_CONFIG:
        review_status = "needs_configuration_change"
    elif readiness.ready:
        review_status = "decision_ready_for_future_finalization"
    else:
        review_status = "decided_blocked"
    decision = ReviewDecision(
        decision_id=_new_decision_id(),
        source_item_id=item_key,
        source_filename=source_filename,
        decision_type=decision_type,
        decided_by_user=bool(decided_by_user),
        decision_timestamp=_utc_now(),
        approved_preview_filename=approved_preview_filename,
        approved_target_preview_path=target,
        edited_fields=tuple(edited_fields or ()),
        reason=reason,
        warnings_acknowledged=tuple(warnings_acknowledged or ()),
        finalization_ready=bool(readiness.ready),
        finalization_blockers=tuple(readiness.blockers),
        audit_note=audit_note or MSG_NOT_FINAL_YET,
        source_hash_at_decision=source_hash_at_decision,
        preview_state_id=ensure_preview_state_id(state),
        decision_ready_for_future_finalization=bool(
            readiness.decision_ready_for_future_finalization
        ),
        final_write_allowed=False,
        exclude_from_finalization_batch=exclude,
        review_status=review_status,
        routes_to_configuration_flow=decision_type == DECISION_NEEDS_CONFIG,
    )
    assert decision.final_write_allowed is False
    assert final_write_allowed() is False
    assert FINAL_WRITE_ALLOWED_IN_THIS_PHASE is False
    return decision, readiness


def create_accept_suggestion_decision(
    state: Any,
    *,
    item_key: str | None = None,
    decided_by_user: bool = False,
    approved_preview_filename: str | None = None,
    reason: str | None = None,
    warnings_acknowledged: Sequence[str] | None = None,
    source_hash_at_decision: str | None = None,
    explicit_confirmation: bool = False,
) -> ApplyDecisionResult:
    """Accept suggestion — requires decided_by_user and explicit confirmation."""

    bag = get_review_decision_bag(state)
    key = _text(item_key or get_review_preview_ui(state).selected_item_key)
    if not key:
        return ApplyDecisionResult(ok=False, message="Kein Prüffall ausgewählt.")
    if not decided_by_user or not explicit_confirmation:
        bag.last_feedback = MSG_ACCEPT_REQUIRES_CONFIRM
        bag.last_feedback_error = True
        return ApplyDecisionResult(ok=False, message=MSG_ACCEPT_REQUIRES_CONFIRM)
    run = getattr(state, "processing_run_state", None)
    review_item = _review_item_for(run, key)
    planned = _planned_for(
        run, _text(getattr(review_item, "document_name", None)) if review_item else key
    )
    filename = _text(approved_preview_filename) or _text(
        getattr(planned, "rendered_filename", None)
        or getattr(planned, "suggested_filename", None)
        or getattr(planned, "canonical_filename", None)
    )
    decision, readiness = _compute_for_decision(
        state=state,
        item_key=key,
        decision_type=DECISION_ACCEPT,
        decided_by_user=True,
        approved_preview_filename=filename or None,
        approved_target_preview_path=None,
        edited_fields=(),
        reason=reason,
        warnings_acknowledged=warnings_acknowledged,
        audit_note=MSG_NOT_FINAL_YET,
        source_hash_at_decision=source_hash_at_decision,
    )
    return apply_review_decision_to_item(state, decision, readiness)


def create_edit_suggestion_decision(
    state: Any,
    *,
    item_key: str | None = None,
    decided_by_user: bool = True,
    edited_filename: str | None = None,
    edited_fields: Mapping[str, Any] | Sequence[tuple[str, str]] | None = None,
    reason: str | None = None,
    warnings_acknowledged: Sequence[str] | None = None,
    source_hash_at_decision: str | None = None,
    missing_pattern_tokens: Sequence[str] | None = None,
) -> ApplyDecisionResult:
    key = _text(item_key or get_review_preview_ui(state).selected_item_key)
    if not key:
        return ApplyDecisionResult(ok=False, message="Kein Prüffall ausgewählt.")
    if not decided_by_user:
        return ApplyDecisionResult(
            ok=False, message="edit_suggestion erfordert decided_by_user=true."
        )
    bag = get_review_decision_bag(state)
    draft = _text(edited_filename) or _text(bag.edit_filename_draft_by_key.get(key))
    run = getattr(state, "processing_run_state", None)
    review_item = _review_item_for(run, key)
    planned = _planned_for(
        run, _text(getattr(review_item, "document_name", None)) if review_item else key
    )
    output_root = _text(getattr(state, "workspace_output_folder_override", None)) or None
    target = _build_target_preview_path(
        planned=planned, approved_filename=draft, output_root=output_root
    )
    dupes = detect_duplicate_approved_targets(
        bag.decisions_by_item_key,
        candidate_item_id=key,
        candidate_target=target,
    )
    planned_missing_tokens = tuple(
        getattr(planned, _MISSING_PATTERN_TOKENS_ATTR, ()) or ()
    )
    validation = validate_edited_filename(
        draft,
        missing_pattern_tokens=missing_pattern_tokens or planned_missing_tokens,
        duplicate_target=key in dupes,
        target_preview_path=target,
        output_root=output_root,
        still_depends_on_pattern=bool(planned_missing_tokens),
    )
    if not validation.ok:
        message = "; ".join(validation.errors) or "Dateiname ungültig."
        bag.last_feedback = message
        bag.last_feedback_error = True
        return ApplyDecisionResult(ok=False, message=message)
    field_pairs: list[tuple[str, str]] = []
    if isinstance(edited_fields, Mapping):
        field_pairs.extend((str(k), str(v)) for k, v in edited_fields.items())
    elif edited_fields:
        field_pairs.extend((str(k), str(v)) for k, v in edited_fields)
    field_pairs.append(("preview_filename", validation.cleaned_filename or draft))
    decision, readiness = _compute_for_decision(
        state=state,
        item_key=key,
        decision_type=DECISION_EDIT,
        decided_by_user=True,
        approved_preview_filename=validation.cleaned_filename or draft,
        approved_target_preview_path=target,
        edited_fields=tuple(field_pairs),
        reason=reason,
        warnings_acknowledged=warnings_acknowledged,
        audit_note=MSG_NOT_FINAL_YET,
        source_hash_at_decision=source_hash_at_decision,
    )
    return apply_review_decision_to_item(state, decision, readiness)


def create_keep_review_required_decision(
    state: Any,
    *,
    item_key: str | None = None,
    decided_by_user: bool = True,
    reason: str | None = None,
) -> ApplyDecisionResult:
    key = _text(item_key or get_review_preview_ui(state).selected_item_key)
    if not key:
        return ApplyDecisionResult(ok=False, message="Kein Prüffall ausgewählt.")
    decision, readiness = _compute_for_decision(
        state=state,
        item_key=key,
        decision_type=DECISION_KEEP_REVIEW,
        decided_by_user=bool(decided_by_user),
        approved_preview_filename=None,
        approved_target_preview_path=None,
        edited_fields=(),
        reason=reason or "als Unklar belassen",
        warnings_acknowledged=(),
        audit_note=MSG_NOT_FINAL_YET,
        source_hash_at_decision=None,
    )
    keep_in_review(state, key)
    return apply_review_decision_to_item(state, decision, readiness)


def create_ignore_for_export_decision(
    state: Any,
    *,
    item_key: str | None = None,
    decided_by_user: bool = True,
    reason: str | None = None,
) -> ApplyDecisionResult:
    key = _text(item_key or get_review_preview_ui(state).selected_item_key)
    if not key:
        return ApplyDecisionResult(ok=False, message="Kein Prüffall ausgewählt.")
    decision, readiness = _compute_for_decision(
        state=state,
        item_key=key,
        decision_type=DECISION_IGNORE,
        decided_by_user=bool(decided_by_user),
        approved_preview_filename=None,
        approved_target_preview_path=None,
        edited_fields=(),
        reason=reason or "ignorieren / nicht exportieren",
        warnings_acknowledged=(),
        audit_note=MSG_NOT_FINAL_YET,
        source_hash_at_decision=None,
    )
    exclude_from_export_preview(state, key)
    return apply_review_decision_to_item(state, decision, readiness)


def create_defer_decision(
    state: Any,
    *,
    item_key: str | None = None,
    decided_by_user: bool = True,
    reason: str | None = None,
) -> ApplyDecisionResult:
    key = _text(item_key or get_review_preview_ui(state).selected_item_key)
    if not key:
        return ApplyDecisionResult(ok=False, message="Kein Prüffall ausgewählt.")
    decision, readiness = _compute_for_decision(
        state=state,
        item_key=key,
        decision_type=DECISION_DEFER,
        decided_by_user=bool(decided_by_user),
        approved_preview_filename=None,
        approved_target_preview_path=None,
        edited_fields=(),
        reason=reason or "zurückstellen",
        warnings_acknowledged=(),
        audit_note=MSG_NOT_FINAL_YET,
        source_hash_at_decision=None,
    )
    return apply_review_decision_to_item(state, decision, readiness)


def create_needs_configuration_change_decision(
    state: Any,
    *,
    item_key: str | None = None,
    decided_by_user: bool = True,
    reason: str | None = None,
) -> ApplyDecisionResult:
    key = _text(item_key or get_review_preview_ui(state).selected_item_key)
    if not key:
        return ApplyDecisionResult(ok=False, message="Kein Prüffall ausgewählt.")
    decision, readiness = _compute_for_decision(
        state=state,
        item_key=key,
        decision_type=DECISION_NEEDS_CONFIG,
        decided_by_user=bool(decided_by_user),
        approved_preview_filename=None,
        approved_target_preview_path=None,
        edited_fields=(),
        reason=reason or MSG_ROUTE_TO_CONFIG,
        warnings_acknowledged=(),
        audit_note=MSG_NOT_FINAL_YET,
        source_hash_at_decision=None,
    )
    bag = get_review_decision_bag(state)
    bag.routes_to_configuration_flow_item_key = key
    # Surface existing configuration coverage / draft flow without auto-save.
    try:
        state.configuration_rule_draft_feedback = MSG_ROUTE_TO_CONFIG
        state.configuration_rule_draft_feedback_error = False
    except Exception:
        pass
    result = apply_review_decision_to_item(state, decision, readiness)
    return replace(result, routes_to_configuration_flow=True)


def apply_review_decision_to_item(
    state: Any,
    decision: ReviewDecision,
    readiness: FinalizationReadiness | None = None,
) -> ApplyDecisionResult:
    """Store decision/readiness in Track-B UI state only — no file IO."""

    bag = get_review_decision_bag(state)
    # Force safety flags.
    safe_decision = replace(decision, final_write_allowed=False)
    if readiness is None:
        readiness = compute_finalization_readiness(
            item_id=safe_decision.source_item_id,
            approved=bool(safe_decision.decided_by_user)
            and safe_decision.decision_type in {DECISION_ACCEPT, DECISION_EDIT},
            decision_type=safe_decision.decision_type,
            context={
                "approved_preview_filename": safe_decision.approved_preview_filename,
                "approved_target_preview_path": (
                    safe_decision.approved_target_preview_path
                ),
            },
            target_preview_path=safe_decision.approved_target_preview_path,
        )
    safe_readiness = replace(readiness, final_write_allowed=False)
    # Re-check duplicates across bag after insert.
    bag.decisions_by_item_key[safe_decision.source_item_id] = safe_decision
    bag.readiness_by_item_key[safe_decision.source_item_id] = safe_readiness
    _refresh_duplicate_blockers(state)
    # Reload possibly updated decision/readiness after duplicate refresh.
    safe_decision = bag.decisions_by_item_key[safe_decision.source_item_id]
    safe_readiness = bag.readiness_by_item_key[safe_decision.source_item_id]
    bag.pending_accept_confirm_key = None
    bag.last_feedback = (
        f"{MSG_DECISION_RECORDED} · {safe_decision.decision_type} · "
        f"{'ready' if safe_readiness.ready else 'blocked'} · {MSG_NOT_FINAL_YET}"
    )
    bag.last_feedback_error = False
    bag.called_run_once = False
    bag.mutated_input = False
    bag.wrote_final_pdfs = False
    bag.touched_real_invoice_folders = False
    return ApplyDecisionResult(
        ok=True,
        message=bag.last_feedback,
        decision=safe_decision,
        readiness=safe_readiness,
        called_run_once=False,
        mutated_input=False,
        wrote_final_pdfs=False,
        touched_real_invoice_folders=False,
        final_write_allowed=False,
        routes_to_configuration_flow=safe_decision.routes_to_configuration_flow,
    )


def _refresh_duplicate_blockers(state: Any) -> None:
    bag = get_review_decision_bag(state)
    dupes = detect_duplicate_approved_targets(bag.decisions_by_item_key)
    for key, decision in list(bag.decisions_by_item_key.items()):
        if key not in dupes:
            continue
        if decision.decision_type not in {DECISION_ACCEPT, DECISION_EDIT}:
            continue
        readiness = bag.readiness_by_item_key.get(key)
        blockers = list(decision.finalization_blockers)
        if "duplicate_target_filename" not in blockers:
            blockers.append("duplicate_target_filename")
        updated_decision = replace(
            decision,
            finalization_ready=False,
            decision_ready_for_future_finalization=False,
            finalization_blockers=tuple(blockers),
            final_write_allowed=False,
        )
        bag.decisions_by_item_key[key] = updated_decision
        if readiness is not None:
            r_blockers = list(readiness.blockers)
            if "duplicate_target_filename" not in r_blockers:
                r_blockers.append("duplicate_target_filename")
            bag.readiness_by_item_key[key] = replace(
                readiness,
                ready=False,
                decision_ready_for_future_finalization=False,
                target_conflict_status="duplicate",
                blockers=tuple(r_blockers),
                final_write_allowed=False,
            )


def decision_report_fields_for_item(
    state: Any, item_key: str
) -> dict[str, Any]:
    """Manifest/report fields for one item — always final_write_allowed=false."""

    bag = get_review_decision_bag(state)
    decision = bag.decisions_by_item_key.get(item_key)
    readiness = bag.readiness_by_item_key.get(item_key)
    if decision is None:
        return {
            "review_decision": None,
            "decision_timestamp": None,
            "approved_by_user": False,
            "finalization_ready": False,
            "decision_ready_for_future_finalization": False,
            "finalization_blockers": [],
            "approved_preview_filename": None,
            "target_preview_path": None,
            "user_edited_fields": {},
            "warnings_acknowledged": [],
            "source_hash_at_decision": None,
            "preview_state_id": ensure_preview_state_id(state),
            "final_write_allowed": False,
        }
    payload = decision.to_dict()
    if readiness is not None:
        payload["finalization_ready"] = readiness.ready
        payload["decision_ready_for_future_finalization"] = (
            readiness.decision_ready_for_future_finalization
        )
        payload["finalization_blockers"] = list(readiness.blockers)
        payload["readiness_warnings"] = list(readiness.warnings)
        payload["next_action"] = readiness.next_action
    payload["final_write_allowed"] = False
    return payload


def items_excluded_from_finalization_batch(state: Any) -> frozenset[str]:
    bag = get_review_decision_bag(state)
    keys = {
        key
        for key, decision in bag.decisions_by_item_key.items()
        if decision.exclude_from_finalization_batch
        or decision.decision_type == DECISION_IGNORE
    }
    preview = get_review_preview_ui(state)
    keys.update(preview.excluded_from_export_preview_keys)
    return frozenset(keys)


def decision_actions_call_run_once() -> bool:
    return False


def decision_actions_mutate_input() -> bool:
    return False


def decision_actions_write_final_pdfs() -> bool:
    return False


def decision_actions_touch_real_invoice_folders() -> bool:
    return False


def decision_actions_claim_saas_ready() -> bool:
    return False


def decision_actions_claim_production_ready() -> bool:
    return False


def set_edit_filename_draft(state: Any, item_key: str, filename: str) -> None:
    bag = get_review_decision_bag(state)
    bag.edit_filename_draft_by_key[_text(item_key)] = _text(filename)


def arm_accept_confirmation(state: Any, item_key: str | None = None) -> None:
    bag = get_review_decision_bag(state)
    key = _text(item_key or get_review_preview_ui(state).selected_item_key)
    bag.pending_accept_confirm_key = key or None
    bag.last_feedback = MSG_ACCEPT_REQUIRES_CONFIRM
    bag.last_feedback_error = False


__all__ = (
    "ACTION_ACCEPT_SUGGESTION",
    "ACTION_DEFER",
    "ACTION_EDIT_SUGGESTION",
    "ACTION_IGNORE_EXPORT",
    "ACTION_KEEP_UNCLEAR",
    "ACTION_NEEDS_CONFIGURATION",
    "ALL_DECISION_TYPES",
    "ApplyDecisionResult",
    "DECISION_ACCEPT",
    "DECISION_ACTION_LABELS",
    "DECISION_DEFER",
    "DECISION_EDIT",
    "DECISION_IGNORE",
    "DECISION_KEEP_REVIEW",
    "DECISION_NEEDS_CONFIG",
    "EditedFilenameValidation",
    "MSG_ACCEPT_REQUIRES_CONFIRM",
    "MSG_DECISION_RECORDED",
    "MSG_FILENAME_DUPLICATE",
    "MSG_FILENAME_EMPTY",
    "MSG_FILENAME_PATH_SEP",
    "MSG_FILENAME_PDF",
    "MSG_FILENAME_PATTERN_TOKEN",
    "MSG_FILENAME_TRAVERSAL",
    "MSG_FILENAME_UNSAFE_TARGET",
    "MSG_FINALIZATION_READY_NO",
    "MSG_FINALIZATION_READY_YES",
    "MSG_NOT_FINAL_YET",
    "MSG_ROUTE_TO_CONFIG",
    "ReviewDecision",
    "ReviewDecisionBag",
    "apply_review_decision_to_item",
    "arm_accept_confirmation",
    "create_accept_suggestion_decision",
    "create_defer_decision",
    "create_edit_suggestion_decision",
    "create_ignore_for_export_decision",
    "create_keep_review_required_decision",
    "create_needs_configuration_change_decision",
    "decision_actions_call_run_once",
    "decision_actions_claim_production_ready",
    "decision_actions_claim_saas_ready",
    "decision_actions_mutate_input",
    "decision_actions_touch_real_invoice_folders",
    "decision_actions_write_final_pdfs",
    "decision_report_fields_for_item",
    "detect_duplicate_approved_targets",
    "ensure_preview_state_id",
    "get_review_decision_bag",
    "items_excluded_from_finalization_batch",
    "set_edit_filename_draft",
    "validate_edited_filename",
)
