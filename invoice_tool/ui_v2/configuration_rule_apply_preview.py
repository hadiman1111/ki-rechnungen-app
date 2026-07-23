"""Track-B apply saved configuration rule + preview-only matching rerun (Prompt 27/34).

After an explicit configuration rule save, the user can re-evaluate current
review/planned preview items against the updated UI-v2 configuration state.

Preview-only — never calls run_once, never mutates inputs, never writes final
PDFs, never touches real invoice folders, never enables productive processing.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Mapping

import flet as ft

from invoice_tool.ui_v2.components import secondary_button, section_block
from invoice_tool.ui_v2.configuration_filename_renderer import (
    build_configuration_placeholder_values,
    render_configuration_filename_pattern,
)
from invoice_tool.ui_v2.configuration_matching import (
    load_active_configuration_candidates,
    match_active_configuration,
)
from invoice_tool.ui_v2.configuration_rule_draft import ConfigurationRuleDraft
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingRunState,
)
from invoice_tool.ui_v2.theme import COLOR_TEXT_MUTED, COLOR_TEXT_SECONDARY

ACTION_RERUN_PREVIEW_WITH_NEW_RULE = "Vorschau mit neuer Regel neu berechnen"
ACTION_RECHECK_MATCHING = "Matching erneut prüfen"
ACTION_APPLY_RULE_TO_REVIEW = "Regel auf Prüffälle anwenden"

MSG_RULE_SAVED = "Regel gespeichert"
MSG_PREVIEW_RECOMPUTED = "Vorschau neu berechnet"
MSG_NO_FINAL_PROCESSING = "keine finale Verarbeitung"
MSG_ORIGINALS_UNCHANGED = "Originale unverändert"
MSG_APPLY_PREVIEW_ONLY = (
    f"{MSG_RULE_SAVED} — {MSG_PREVIEW_RECOMPUTED} — "
    f"{MSG_NO_FINAL_PROCESSING} — {MSG_ORIGINALS_UNCHANGED}"
)
MSG_RERUN_READY_AFTER_SAVE = (
    "Regel gespeichert. Vorschau kann jetzt mit der neuen Regel neu berechnet werden "
    "(Preview only — keine finale Verarbeitung)."
)
MSG_NO_RUN_STATE = "Kein Preview-Lauf vorhanden — zuerst Sandbox-Lauf ausführen."
MSG_RERUN_REQUIRES_EXPLICIT = (
    "Preview-Rerun erfordert explizite Aktion nach dem Speichern."
)

PREVIEW_RERUN_ACTION_LABELS = (
    ACTION_RERUN_PREVIEW_WITH_NEW_RULE,
    ACTION_RECHECK_MATCHING,
    ACTION_APPLY_RULE_TO_REVIEW,
)


@dataclass(frozen=True)
class ConfigurationRuleApplyResult:
    """Result of applying a saved rule to in-memory preview state."""

    ok: bool
    message: str
    updated_run_state: ProcessingRunState | None = None
    items_reevaluated: int = 0
    items_matched_after_change: int = 0
    applied_configuration_name: str | None = None
    applied_configuration_condition: str | None = None
    called_run_once: bool = False
    mutated_input: bool = False
    wrote_final_pdfs: bool = False
    touched_real_invoice_folders: bool = False
    productive_processing: bool = False
    preview_only: bool = True
    errors: tuple[str, ...] = ()


def build_applied_condition(
    draft: ConfigurationRuleDraft | Mapping[str, Any] | None,
) -> str | None:
    """Serialize the saved rule condition for report/manifest fields."""

    if draft is None:
        return None
    if isinstance(draft, Mapping):
        feature = str(draft.get("proposed_matching_feature_key") or "").strip()
        operator = str(draft.get("proposed_matching_operator") or "ist").strip() or "ist"
        values = draft.get("proposed_matching_values") or ()
        name = str(draft.get("proposed_configuration_name") or "").strip() or None
        condition = str(draft.get("proposed_condition") or "").strip()
    else:
        feature = str(draft.proposed_matching_feature_key or "").strip()
        operator = str(draft.proposed_matching_operator or "ist").strip() or "ist"
        values = draft.proposed_matching_values or ()
        name = str(draft.proposed_configuration_name or "").strip() or None
        condition = str(draft.proposed_condition or "").strip()
    if condition:
        return condition
    value_text = ", ".join(str(v).strip() for v in values if str(v).strip())
    if feature and value_text:
        return f"{feature} {operator} {value_text}"
    if name:
        return name
    return None


def preview_rerun_action_labels() -> tuple[str, ...]:
    return PREVIEW_RERUN_ACTION_LABELS


def preview_rerun_available(state: Any) -> bool:
    """True when a rule was explicitly saved and a preview run exists."""

    if not bool(getattr(state, "configuration_rule_apply_available", False)):
        return False
    run = getattr(state, "processing_run_state", None)
    if run is None:
        return False
    if (getattr(run, "status", None) or "") != "completed":
        return False
    planned = getattr(run, "planned_destinations", ()) or ()
    return bool(planned)


def mark_rule_saved_for_preview_apply(
    state: Any,
    *,
    draft: ConfigurationRuleDraft | None,
    configuration_id: str | None = None,
) -> None:
    """After explicit save — expose preview-only rerun action (no auto rerun)."""

    state.configuration_rule_apply_available = True
    state.configuration_rule_last_saved_draft = draft
    state.configuration_rule_last_saved_configuration_id = configuration_id
    state.configuration_rule_apply_feedback = MSG_RERUN_READY_AFTER_SAVE
    state.configuration_rule_apply_feedback_error = False
    state.configuration_rule_apply_last_result = None


def _lookup_destination_path(
    *,
    profile_id: str | None,
    configuration_id: str | None,
    configuration_name: str | None,
    is_unmatched: bool,
) -> str | None:
    if not profile_id:
        return None
    try:
        from invoice_tool.profile_store import load_profile_bundle

        bundle = load_profile_bundle(profile_id)
    except Exception:  # noqa: BLE001 — preview update must fail closed
        return None
    if is_unmatched and bundle.unmatched is not None:
        dest = bundle.unmatched.destination
        if isinstance(dest, Mapping):
            path = str(dest.get("path") or "").strip()
            return path or None
        return str(getattr(dest, "path", "") or "").strip() or None
    target_id = (configuration_id or "").strip()
    target_name = (configuration_name or "").strip().lower()
    for cfg in bundle.configurations or []:
        cfg_id = str(getattr(cfg, "id", "") or "").strip()
        cfg_name = str(getattr(cfg, "name", "") or "").strip().lower()
        if (target_id and cfg_id == target_id) or (
            target_name and cfg_name == target_name
        ):
            dest = cfg.destination
            if isinstance(dest, Mapping):
                path = str(dest.get("path") or "").strip()
                return path or None
            return str(getattr(dest, "path", "") or "").strip() or None
    return None


def _placeholder_map(
    planned: ProcessingPlannedDestination,
) -> dict[str, str | None]:
    existing = {
        str(key): value for key, value in (planned.placeholder_values or ())
    }
    if existing:
        return existing
    payment = (
        (planned.selected_payment_field or planned.payment_account or "").strip()
        or None
    )
    return build_configuration_placeholder_values(
        pattern=planned.filename_pattern
        or planned.matched_configuration_pattern
        or "{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf",
        invoice_date=planned.invoice_date,
        art=planned.selected_art or planned.document_type,
        supplier=planned.supplier or planned.counterparty_name,
        amount=planned.selected_amount or planned.amount,
        payment_field=payment,
        document_direction=planned.document_direction,
        document_type=planned.document_type,
        counterparty_name=planned.counterparty_name,
        payment_account=planned.payment_account,
    )


def reevaluate_planned_destination(
    planned: ProcessingPlannedDestination,
    *,
    profile_id: str | None,
    applied_configuration_name: str | None,
    applied_configuration_condition: str | None,
    applied_configuration_id: str | None = None,
) -> ProcessingPlannedDestination:
    """Re-match one planned destination against current active configs."""

    previous = (planned.matched_configuration_name or "").strip() or None
    payment_field = (
        (planned.selected_payment_field or planned.payment_account or "").strip()
        or None
    )
    match = match_active_configuration(
        payment_field=payment_field,
        payment_account=planned.payment_account,
        supplier=planned.supplier,
        recipient=planned.counterparty_name,
        document_type=planned.document_type,
        profile_id=profile_id,
    )
    transparency = match.transparency_fields()
    new_name = (match.matched_configuration_name or "").strip() or None
    pattern = match.matched_configuration_pattern or planned.filename_pattern
    placeholders = _placeholder_map(planned)
    # Keep payment_field token aligned with selected signal for PayPal/card.
    if payment_field:
        placeholders["payment_field"] = payment_field
    rendered = None
    missing_placeholders = planned.missing_placeholders
    placeholder_values = planned.placeholder_values
    filename_source = planned.filename_source
    naming_confidence = planned.naming_confidence
    naming_reason = match.matched_configuration_reason or planned.naming_reason
    if pattern:
        render = render_configuration_filename_pattern(
            pattern,
            placeholder_values=placeholders,
        )
        rendered = render.rendered_filename
        missing_placeholders = render.missing_placeholders
        placeholder_values = render.placeholder_values
        filename_source = render.filename_source
        naming_confidence = render.naming_confidence
        if render.naming_reason:
            naming_reason = f"{match.matched_configuration_reason} {render.naming_reason}".strip()

    rule_applied = bool(
        applied_configuration_name
        and new_name
        and new_name == applied_configuration_name
        and not match.is_unmatched_fallback
    )
    # Also accept id match when names differ only by whitespace/case.
    if (
        not rule_applied
        and applied_configuration_id
        and match.matched_configuration_id
        and str(match.matched_configuration_id) == str(applied_configuration_id)
        and not match.is_unmatched_fallback
    ):
        rule_applied = True

    matched_after = previous != new_name
    planned_path = _lookup_destination_path(
        profile_id=profile_id,
        configuration_id=match.matched_configuration_id,
        configuration_name=new_name,
        is_unmatched=bool(match.is_unmatched_fallback),
    ) or planned.planned_path

    return replace(
        planned,
        planned_path=planned_path,
        destination_label=new_name or planned.destination_label,
        reason=match.matched_configuration_reason or planned.reason,
        preview_only=True,
        applied=False,
        matched_configuration_name=new_name,
        matched_configuration_id=match.matched_configuration_id,
        matched_configuration_pattern=pattern,
        matched_configuration_reason=match.matched_configuration_reason,
        matched_configuration_confidence=match.matched_configuration_confidence,
        filename_pattern=pattern,
        rendered_filename=rendered or planned.rendered_filename,
        suggested_filename=rendered or planned.suggested_filename,
        placeholder_values=placeholder_values,
        missing_placeholders=missing_placeholders,
        filename_source=filename_source,
        naming_confidence=naming_confidence,
        naming_reason=naming_reason,
        available_configurations=tuple(
            transparency.get("available_configurations") or ()
        ),
        evaluated_configuration_candidates=tuple(
            transparency.get("evaluated_configuration_candidates") or ()
        ),
        unmatched_reasons=tuple(transparency.get("unmatched_reasons") or ()),
        condition_results=tuple(transparency.get("condition_results") or ()),
        alternative_matches=tuple(transparency.get("alternative_matches") or ()),
        missing_configuration_rule=transparency.get("missing_configuration_rule"),
        configuration_coverage_status=transparency.get(
            "configuration_coverage_status"
        ),
        missing_configuration_type=transparency.get("missing_configuration_type"),
        user_guidance=transparency.get("user_guidance"),
        suggested_configuration_action=transparency.get(
            "suggested_configuration_action"
        ),
        guidance_severity=transparency.get("guidance_severity"),
        rule_applied=rule_applied,
        applied_configuration_name=applied_configuration_name if rule_applied else None,
        applied_configuration_condition=(
            applied_configuration_condition if rule_applied else None
        ),
        rerun_preview_after_rule_change=True,
        matched_after_rule_change=matched_after,
        previous_matched_configuration=previous,
        new_matched_configuration=new_name,
    )


def rerun_preview_matching_after_rule_change(
    *,
    run_state: ProcessingRunState,
    profile_id: str | None,
    applied_configuration_name: str | None,
    applied_configuration_condition: str | None = None,
    applied_configuration_id: str | None = None,
    explicit_user_action: bool = False,
) -> ConfigurationRuleApplyResult:
    """Re-evaluate planned destinations — preview only, explicit action required."""

    if not explicit_user_action:
        return ConfigurationRuleApplyResult(
            ok=False,
            message=MSG_RERUN_REQUIRES_EXPLICIT,
            errors=("requires_explicit_rerun_action",),
        )
    planned = tuple(run_state.planned_destinations or ())
    if not planned:
        return ConfigurationRuleApplyResult(
            ok=False,
            message=MSG_NO_RUN_STATE,
            errors=("no_planned_destinations",),
        )

    # Ensure active candidates can load (surface missing profile early).
    try:
        load_active_configuration_candidates(profile_id=profile_id)
    except Exception as exc:  # noqa: BLE001
        return ConfigurationRuleApplyResult(
            ok=False,
            message=f"Aktive Konfigurationen konnten nicht geladen werden: {exc}",
            errors=("configuration_load_failed",),
        )

    updated: list[ProcessingPlannedDestination] = []
    matched_after_count = 0
    for item in planned:
        refreshed = reevaluate_planned_destination(
            item,
            profile_id=profile_id,
            applied_configuration_name=applied_configuration_name,
            applied_configuration_condition=applied_configuration_condition,
            applied_configuration_id=applied_configuration_id,
        )
        if refreshed.matched_after_rule_change:
            matched_after_count += 1
        updated.append(refreshed)

    stamp = datetime.now(timezone.utc).isoformat()
    new_state = replace(
        run_state,
        planned_destinations=tuple(updated),
        planned_destination_count=len(updated),
        state_updated_at=stamp,
        message=(
            f"{run_state.message or ''} · {MSG_APPLY_PREVIEW_ONLY}".strip(" ·")
        ),
    )
    return ConfigurationRuleApplyResult(
        ok=True,
        message=MSG_APPLY_PREVIEW_ONLY,
        updated_run_state=new_state,
        items_reevaluated=len(updated),
        items_matched_after_change=matched_after_count,
        applied_configuration_name=applied_configuration_name,
        applied_configuration_condition=applied_configuration_condition,
        called_run_once=False,
        mutated_input=False,
        wrote_final_pdfs=False,
        touched_real_invoice_folders=False,
        productive_processing=False,
        preview_only=True,
    )


def apply_saved_rule_to_preview_state(
    state: Any,
    *,
    explicit_user_action: bool = False,
    profile_id: str | None = None,
) -> ConfigurationRuleApplyResult:
    """Apply last saved rule onto UiV2 processing_run_state (preview only)."""

    if not explicit_user_action:
        return ConfigurationRuleApplyResult(
            ok=False,
            message=MSG_RERUN_REQUIRES_EXPLICIT,
            errors=("requires_explicit_rerun_action",),
        )
    if not bool(getattr(state, "configuration_rule_apply_available", False)):
        return ConfigurationRuleApplyResult(
            ok=False,
            message="Keine gespeicherte Regel für Preview-Rerun verfügbar.",
            errors=("no_saved_rule_for_apply",),
        )

    run = getattr(state, "processing_run_state", None)
    if run is None or (getattr(run, "status", None) or "") != "completed":
        return ConfigurationRuleApplyResult(
            ok=False,
            message=MSG_NO_RUN_STATE,
            errors=("no_completed_preview_run",),
        )

    draft = getattr(state, "configuration_rule_last_saved_draft", None)
    applied_name = None
    applied_condition = None
    applied_id = getattr(state, "configuration_rule_last_saved_configuration_id", None)
    if isinstance(draft, ConfigurationRuleDraft):
        applied_name = str(draft.proposed_configuration_name or "").strip() or None
        applied_condition = build_applied_condition(draft)
        applied_id = applied_id or draft.proposed_configuration_id
    elif isinstance(draft, Mapping):
        applied_name = str(draft.get("proposed_configuration_name") or "").strip() or None
        applied_condition = build_applied_condition(draft)
        applied_id = applied_id or draft.get("proposed_configuration_id")

    resolved_profile = (
        (profile_id or "").strip()
        or str(getattr(state, "selected_profile_id", "") or "").strip()
        or None
    )
    if not resolved_profile:
        try:
            from invoice_tool.app_paths import resolve_active_profile_id

            resolved_profile = resolve_active_profile_id()
        except Exception:  # noqa: BLE001
            resolved_profile = None

    result = rerun_preview_matching_after_rule_change(
        run_state=run,
        profile_id=resolved_profile,
        applied_configuration_name=applied_name,
        applied_configuration_condition=applied_condition,
        applied_configuration_id=str(applied_id) if applied_id else None,
        explicit_user_action=True,
    )
    if result.ok and result.updated_run_state is not None:
        state.processing_run_state = result.updated_run_state
        state.configuration_rule_apply_feedback = result.message
        state.configuration_rule_apply_feedback_error = False
        state.configuration_rule_apply_last_result = result
        # Keep action available for repeat preview refreshes in the same session.
        state.configuration_rule_apply_available = True
    else:
        state.configuration_rule_apply_feedback = result.message
        state.configuration_rule_apply_feedback_error = True
        state.configuration_rule_apply_last_result = result
    return result


def attach_rule_apply_report_fields(
    payload: dict[str, Any],
    planned: ProcessingPlannedDestination | Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Attach apply/rerun transparency fields to export/review payloads."""

    out = dict(payload)
    if planned is None:
        out.setdefault("rule_applied", False)
        out.setdefault("applied_configuration_name", None)
        out.setdefault("applied_configuration_condition", None)
        out.setdefault("rerun_preview_after_rule_change", False)
        out.setdefault("matched_after_rule_change", False)
        out.setdefault("previous_matched_configuration", None)
        out.setdefault("new_matched_configuration", None)
        return out
    getter = planned.get if isinstance(planned, Mapping) else lambda k, d=None: getattr(
        planned, k, d
    )
    out["rule_applied"] = bool(getter("rule_applied", False))
    out["applied_configuration_name"] = getter("applied_configuration_name")
    out["applied_configuration_condition"] = getter(
        "applied_configuration_condition"
    )
    out["rerun_preview_after_rule_change"] = bool(
        getter("rerun_preview_after_rule_change", False)
    )
    out["matched_after_rule_change"] = bool(
        getter("matched_after_rule_change", False)
    )
    out["previous_matched_configuration"] = getter(
        "previous_matched_configuration"
    )
    out["new_matched_configuration"] = getter("new_matched_configuration")
    return out


def build_configuration_rule_apply_panel(state: Any) -> ft.Control | None:
    """UI panel: explicit preview-only rerun after rule save."""

    if not bool(getattr(state, "configuration_rule_apply_available", False)):
        return None

    feedback = str(getattr(state, "configuration_rule_apply_feedback", "") or "")
    feedback_error = bool(
        getattr(state, "configuration_rule_apply_feedback_error", False)
    )
    draft = getattr(state, "configuration_rule_last_saved_draft", None)
    rule_name = ""
    condition = ""
    if isinstance(draft, ConfigurationRuleDraft):
        rule_name = draft.proposed_configuration_name or ""
        condition = draft.proposed_condition or build_applied_condition(draft) or ""
    elif isinstance(draft, Mapping):
        rule_name = str(draft.get("proposed_configuration_name") or "")
        condition = str(
            draft.get("proposed_condition") or build_applied_condition(draft) or ""
        )

    lines: list[ft.Control] = [
        ft.Text(MSG_RULE_SAVED, size=12, color=COLOR_TEXT_SECONDARY),
        ft.Text(
            f"Gespeicherte Regel: {rule_name or '—'}"
            + (f" · {condition}" if condition else ""),
            size=11,
            color=COLOR_TEXT_MUTED,
        ),
        ft.Text(
            "Vorschau neu berechnen — keine finale Verarbeitung — Originale unverändert.",
            size=11,
            color=COLOR_TEXT_MUTED,
        ),
    ]
    if feedback:
        lines.append(
            ft.Text(
                feedback,
                size=12,
                color="#B45309" if feedback_error else COLOR_TEXT_SECONDARY,
            )
        )

    def _on_rerun(_e: ft.ControlEvent) -> None:
        result = apply_saved_rule_to_preview_state(
            state,
            explicit_user_action=True,
        )
        state.configuration_rule_apply_feedback = result.message
        state.configuration_rule_apply_feedback_error = not result.ok
        if state.refresh is not None:
            state.refresh()

    disabled = not preview_rerun_available(state)
    lines.append(
        ft.Row(
            [
                secondary_button(
                    ACTION_RERUN_PREVIEW_WITH_NEW_RULE,
                    on_click=_on_rerun,
                    disabled=disabled,
                ),
                secondary_button(
                    ACTION_RECHECK_MATCHING,
                    on_click=_on_rerun,
                    disabled=disabled,
                ),
                secondary_button(
                    ACTION_APPLY_RULE_TO_REVIEW,
                    on_click=_on_rerun,
                    disabled=disabled,
                ),
            ],
            spacing=8,
            wrap=True,
        )
    )
    return section_block(
        "Regel anwenden (Preview)",
        ft.Column(lines, spacing=8, tight=True),
        subtitle="Explizit · Preview only · kein run_once",
    )


def apply_preview_asserts_no_maturity_claim() -> bool:
    """Honesty helper — always False (no positive maturity claim)."""

    return False


def apply_preview_calls_run_once() -> bool:
    return False


def apply_preview_mutates_input() -> bool:
    return False


def apply_preview_writes_final_pdfs() -> bool:
    return False


def apply_preview_touches_real_invoice_folders() -> bool:
    return False


__all__ = (
    "ACTION_APPLY_RULE_TO_REVIEW",
    "ACTION_RECHECK_MATCHING",
    "ACTION_RERUN_PREVIEW_WITH_NEW_RULE",
    "ConfigurationRuleApplyResult",
    "MSG_APPLY_PREVIEW_ONLY",
    "MSG_NO_FINAL_PROCESSING",
    "MSG_ORIGINALS_UNCHANGED",
    "MSG_PREVIEW_RECOMPUTED",
    "MSG_RULE_SAVED",
    "PREVIEW_RERUN_ACTION_LABELS",
    "apply_preview_asserts_no_maturity_claim",
    "apply_preview_calls_run_once",
    "apply_preview_mutates_input",
    "apply_preview_touches_real_invoice_folders",
    "apply_preview_writes_final_pdfs",
    "apply_saved_rule_to_preview_state",
    "attach_rule_apply_report_fields",
    "build_applied_condition",
    "build_configuration_rule_apply_panel",
    "mark_rule_saved_for_preview_apply",
    "preview_rerun_action_labels",
    "preview_rerun_available",
    "reevaluate_planned_destination",
    "rerun_preview_matching_after_rule_change",
)
