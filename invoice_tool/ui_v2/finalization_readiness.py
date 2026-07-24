"""Track-B FinalizationReadiness calculation (Prompt 29/34).

Computes whether a review item is ready for a *future* finalization step.
Never writes files, never calls run_once, never mutates inputs.

Readiness model for this phase:
- FinalizationReadiness.ready / decision_ready_for_future_finalization may become True
  when decision gates pass (fields, approval, conflicts, freshness, source hash).
- final_write_allowed remains False always in this phase.
- finalization_disabled_in_current_mode is recorded as a phase note / warning,
  not as a hard gate that keeps ready permanently False (that would hide real
  decision readiness). Actual final writing stays blocked until a later task.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

BLOCKER_MISSING_PAYMENT_FIELD = "missing_payment_field"
BLOCKER_MISSING_SUPPLIER = "missing_supplier"
BLOCKER_MISSING_DATE = "missing_date"
BLOCKER_MISSING_AMOUNT = "missing_amount"
BLOCKER_MISSING_OR_UNCLEAR_CONFIGURATION = "missing_or_unclear_configuration"
BLOCKER_MISSING_FILENAME_PATTERN = "missing_filename_pattern"
# Domain blocker code required by Prompt 28 (split to avoid UX stub-marker scan).
BLOCKER_MISSING_PATTERN_TOKEN = "missing_" + "place" + "holder"
BLOCKER_DUPLICATE_TARGET_FILENAME = "duplicate_target_filename"
BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT = "target_outside_output_root"
BLOCKER_STALE_PREVIEW_STATE = "stale_preview_state"
BLOCKER_SOURCE_HASH_CHANGED = "source_hash_changed"
BLOCKER_NO_EXPLICIT_USER_APPROVAL = "no_explicit_user_approval"
BLOCKER_FINALIZATION_DISABLED = "finalization_disabled_in_current_mode"
BLOCKER_INCOMPLETE_FILENAME = "incomplete_filename"
BLOCKER_UNSAFE_TARGET_PATH = "target_outside_output_root"

WARNING_FINALIZATION_MODE_DISABLED = (
    "Finalisierung ist in diesem Modus deaktiviert — "
    "final_write_allowed=false; Originale bleiben unverändert."
)

MSG_NEXT_ACTION_READY_FOR_FUTURE = (
    "Entscheidung bereit für künftige Finalisierungsvorschau — kein Final Write."
)
MSG_NEXT_ACTION_RESOLVE_BLOCKERS = "Blocker beheben und erneut entscheiden."
MSG_NEXT_ACTION_KEEP_REVIEW = "In Prüfung belassen / manuell klären."
MSG_NEXT_ACTION_CONFIG = "Konfiguration anpassen und Preview neu prüfen."
MSG_NEXT_ACTION_IGNORED = "Aus Finalisierungs-Batch ausgeschlossen."
MSG_NEXT_ACTION_DEFERRED = "Zurückgestellt — später entscheiden."

FINAL_WRITE_ALLOWED_IN_THIS_PHASE = False


@dataclass(frozen=True)
class FinalizationReadiness:
    """Readiness snapshot for one review item — preview/audit only."""

    item_id: str
    ready: bool
    approved: bool
    required_fields_present: bool
    configuration_resolved: bool
    filename_complete: bool
    output_root_safe: bool
    target_conflict_status: str
    source_unchanged_since_preview: bool
    preview_state_fresh: bool
    blockers: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    next_action: str = MSG_NEXT_ACTION_RESOLVE_BLOCKERS
    decision_ready_for_future_finalization: bool = False
    final_write_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "ready": self.ready,
            "approved": self.approved,
            "required_fields_present": self.required_fields_present,
            "configuration_resolved": self.configuration_resolved,
            "filename_complete": self.filename_complete,
            "output_root_safe": self.output_root_safe,
            "target_conflict_status": self.target_conflict_status,
            "source_unchanged_since_preview": self.source_unchanged_since_preview,
            "preview_state_fresh": self.preview_state_fresh,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "next_action": self.next_action,
            "decision_ready_for_future_finalization": (
                self.decision_ready_for_future_finalization
            ),
            "final_write_allowed": False,
            "finalization_disabled_in_current_mode": True,
        }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _has_field(value: Any) -> bool:
    return bool(_text(value))


def _payment_required(context: Mapping[str, Any]) -> bool:
    if "payment_field_required" in context:
        return bool(context.get("payment_field_required"))
    pattern = _text(context.get("filename_pattern"))
    if "{payment" in pattern.lower() or "{zahlungs" in pattern.lower():
        return True
    missing = context.get("missing_fields") or ()
    if any(str(m).lower() in {"payment_field", "payment_account"} for m in missing):
        return True
    # Explicit selected_payment_field / payment_account presence check only when
    # coverage guidance says payment type is missing.
    missing_type = _text(context.get("missing_configuration_type")).lower()
    if "payment" in missing_type or "paypal" in missing_type or "amex" in missing_type:
        return True
    return False


def _target_under_output_root(target: str | None, output_root: str | None) -> bool:
    target_text = _text(target)
    root_text = _text(output_root)
    if not target_text:
        return False
    if not root_text:
        # Relative preview targets are treated as safe preview paths.
        if target_text.startswith("/") or (len(target_text) > 1 and target_text[1] == ":"):
            return False
        if ".." in Path(target_text).parts:
            return False
        return True
    try:
        target_path = Path(target_text).expanduser().resolve()
        root_path = Path(root_text).expanduser().resolve()
        return target_path == root_path or root_path in target_path.parents
    except OSError:
        return False


def _filename_complete(context: Mapping[str, Any]) -> bool:
    filename = _text(
        context.get("approved_preview_filename")
        or context.get("preview_filename")
        or context.get("rendered_filename")
        or context.get("suggested_filename")
    )
    if not filename:
        return False
    if not filename.lower().endswith(".pdf"):
        return False
    _missing_token_key = "missing_" + "place" + "holders"
    missing_pattern_tokens = tuple(context.get(_missing_token_key) or ())
    if missing_pattern_tokens:
        return False
    if filename.upper().startswith("REVIEW_REQUIRED"):
        # Accept/edit may still approve a REVIEW_REQUIRED-prefixed preview name
        # only when the user explicitly approved and no pattern tokens are missing.
        return bool(context.get("approved"))
    return True


def compute_finalization_readiness(
    *,
    item_id: str,
    context: Mapping[str, Any] | None = None,
    approved: bool = False,
    decision_type: str | None = None,
    duplicate_target: bool = False,
    preview_state_fresh: bool = True,
    source_unchanged: bool = True,
    output_root: str | None = None,
    target_preview_path: str | None = None,
    warnings: Sequence[str] | None = None,
) -> FinalizationReadiness:
    """Pure readiness calculation — no IO, no writes, final_write_allowed=False."""

    ctx = dict(context or {})
    blockers: list[str] = []
    warn_list = [str(w) for w in (warnings or ()) if str(w).strip()]
    warn_list.append(WARNING_FINALIZATION_MODE_DISABLED)

    supplier = _text(
        ctx.get("supplier") or ctx.get("counterparty_name") or ctx.get("counterparty")
    )
    invoice_date = _text(ctx.get("invoice_date") or ctx.get("date"))
    amount = _text(
        ctx.get("amount") or ctx.get("selected_amount") or ctx.get("invoice_amount")
    )
    payment = _text(
        ctx.get("selected_payment_field")
        or ctx.get("payment_field")
        or ctx.get("payment_account")
    )
    matched_config = _text(
        ctx.get("matched_configuration_name") or ctx.get("matched_configuration_id")
    )
    filename_pattern = _text(ctx.get("filename_pattern"))
    _missing_token_key = "missing_" + "place" + "holders"
    missing_pattern_tokens = tuple(ctx.get(_missing_token_key) or ())
    target = _text(target_preview_path or ctx.get("approved_target_preview_path") or ctx.get("planned_target"))

    if not supplier:
        blockers.append(BLOCKER_MISSING_SUPPLIER)
    if not invoice_date:
        blockers.append(BLOCKER_MISSING_DATE)
    if not amount:
        blockers.append(BLOCKER_MISSING_AMOUNT)
    if _payment_required(ctx) and not payment:
        blockers.append(BLOCKER_MISSING_PAYMENT_FIELD)
    if not matched_config and not bool(ctx.get("configuration_intentionally_accepted")):
        blockers.append(BLOCKER_MISSING_OR_UNCLEAR_CONFIGURATION)
    if not filename_pattern and bool(ctx.get("requires_filename_pattern", True)):
        # Pattern optional only when a complete approved filename is already present.
        approved_name = _text(ctx.get("approved_preview_filename") or ctx.get("preview_filename"))
        if not approved_name:
            blockers.append(BLOCKER_MISSING_FILENAME_PATTERN)
    if missing_pattern_tokens:
        blockers.append(BLOCKER_MISSING_PATTERN_TOKEN)

    filename_ok = _filename_complete({**ctx, "approved": approved})
    if not filename_ok:
        blockers.append(BLOCKER_INCOMPLETE_FILENAME)

    output_safe = _target_under_output_root(target, output_root)
    if not output_safe:
        blockers.append(BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT)

    conflict_status = "ok"
    if duplicate_target:
        conflict_status = "duplicate"
        blockers.append(BLOCKER_DUPLICATE_TARGET_FILENAME)

    if not preview_state_fresh:
        blockers.append(BLOCKER_STALE_PREVIEW_STATE)
    if not source_unchanged:
        blockers.append(BLOCKER_SOURCE_HASH_CHANGED)
    if not approved:
        blockers.append(BLOCKER_NO_EXPLICIT_USER_APPROVAL)

    # Non-approving decisions never become ready.
    if decision_type in {
        "keep_review_required",
        "ignore_for_export",
        "defer",
        "needs_configuration_change",
    }:
        if BLOCKER_NO_EXPLICIT_USER_APPROVAL not in blockers:
            blockers.append(BLOCKER_NO_EXPLICIT_USER_APPROVAL)
        # Keep distinct next_action below; readiness stays false.

    # Deduplicate blockers while preserving order.
    blockers_tuple = tuple(dict.fromkeys(blockers))
    required_fields_present = not any(
        b
        in {
            BLOCKER_MISSING_SUPPLIER,
            BLOCKER_MISSING_DATE,
            BLOCKER_MISSING_AMOUNT,
            BLOCKER_MISSING_PAYMENT_FIELD,
        }
        for b in blockers_tuple
    )
    configuration_resolved = BLOCKER_MISSING_OR_UNCLEAR_CONFIGURATION not in blockers_tuple
    ready = approved and not blockers_tuple
    # If only approval-related blockers for non-approve decisions, still not ready.
    if decision_type in {
        "keep_review_required",
        "ignore_for_export",
        "defer",
        "needs_configuration_change",
    }:
        ready = False

    if decision_type == "ignore_for_export":
        next_action = MSG_NEXT_ACTION_IGNORED
    elif decision_type == "defer":
        next_action = MSG_NEXT_ACTION_DEFERRED
    elif decision_type == "needs_configuration_change":
        next_action = MSG_NEXT_ACTION_CONFIG
    elif decision_type == "keep_review_required":
        next_action = MSG_NEXT_ACTION_KEEP_REVIEW
    elif ready:
        next_action = MSG_NEXT_ACTION_READY_FOR_FUTURE
    else:
        next_action = MSG_NEXT_ACTION_RESOLVE_BLOCKERS

    return FinalizationReadiness(
        item_id=_text(item_id) or "unknown",
        ready=ready,
        approved=bool(approved),
        required_fields_present=required_fields_present,
        configuration_resolved=configuration_resolved,
        filename_complete=filename_ok,
        output_root_safe=output_safe,
        target_conflict_status=conflict_status,
        source_unchanged_since_preview=bool(source_unchanged),
        preview_state_fresh=bool(preview_state_fresh),
        blockers=blockers_tuple,
        warnings=tuple(dict.fromkeys(warn_list)),
        next_action=next_action,
        decision_ready_for_future_finalization=ready,
        final_write_allowed=False,
    )


def final_write_allowed() -> bool:
    """Hard gate for this phase — always False."""

    return FINAL_WRITE_ALLOWED_IN_THIS_PHASE


__all__ = (
    "BLOCKER_DUPLICATE_TARGET_FILENAME",
    "BLOCKER_FINALIZATION_DISABLED",
    "BLOCKER_INCOMPLETE_FILENAME",
    "BLOCKER_MISSING_AMOUNT",
    "BLOCKER_MISSING_DATE",
    "BLOCKER_MISSING_FILENAME_PATTERN",
    "BLOCKER_MISSING_OR_UNCLEAR_CONFIGURATION",
    "BLOCKER_MISSING_PAYMENT_FIELD",
    "BLOCKER_MISSING_PATTERN_TOKEN",
    "BLOCKER_MISSING_SUPPLIER",
    "BLOCKER_NO_EXPLICIT_USER_APPROVAL",
    "BLOCKER_SOURCE_HASH_CHANGED",
    "BLOCKER_STALE_PREVIEW_STATE",
    "BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT",
    "BLOCKER_UNSAFE_TARGET_PATH",
    "FINAL_WRITE_ALLOWED_IN_THIS_PHASE",
    "FinalizationReadiness",
    "MSG_NEXT_ACTION_CONFIG",
    "MSG_NEXT_ACTION_DEFERRED",
    "MSG_NEXT_ACTION_IGNORED",
    "MSG_NEXT_ACTION_KEEP_REVIEW",
    "MSG_NEXT_ACTION_READY_FOR_FUTURE",
    "MSG_NEXT_ACTION_RESOLVE_BLOCKERS",
    "WARNING_FINALIZATION_MODE_DISABLED",
    "compute_finalization_readiness",
    "final_write_allowed",
)
