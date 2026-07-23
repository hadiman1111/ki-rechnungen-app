"""Track-B configuration rule draft editor / save flow (Prompt 26/34).

Opens drafts from Review guidance, validates, and saves only after explicit
user confirmation into UI-v2 profile/config state.

Never calls run_once. Never mutates input files. Never writes final PDFs.
Never maps PayPal/card to private business categories or AMEX without evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

import flet as ft

from invoice_tool.configuration_model import (
    FilenamePattern,
    pattern_from_template,
)
from invoice_tool.ui_v2.adapters.configuration_write_adapter import (
    create_configuration,
    update_configuration,
)
from invoice_tool.ui_v2.adapters.write_result import WriteOperationResult
from invoice_tool.ui_v2.components import secondary_button, section_block
from invoice_tool.ui_v2.configuration_matching import load_active_configuration_candidates
from invoice_tool.ui_v2.configuration_rule_draft import (
    ACTION_CANCEL_DRAFT,
    ACTION_CREATE_FROM_GUIDANCE,
    ACTION_EDIT_EXISTING,
    ACTION_MANUAL_KEEP_UNCLEAR,
    ACTION_SAVE_DRAFT,
    ConfigurationRuleDraft,
    coverage_gap_actions_available,
    draft_from_coverage_guidance,
    load_unmatched_filename_pattern,
    validate_configuration_rule_draft,
)
from invoice_tool.ui_v2.draft_models import ConfigurationDraftVM, MatchingRuleDraftVM
from invoice_tool.ui_v2.edit_components import outlined_field_kwargs
from invoice_tool.ui_v2.theme import COLOR_TEXT_MUTED, COLOR_TEXT_SECONDARY


@dataclass(frozen=True)
class ConfigurationRuleSaveResult:
    ok: bool
    message: str
    draft: ConfigurationRuleDraft | None = None
    configuration_id: str | None = None
    called_run_once: bool = False
    mutated_input: bool = False
    wrote_final_pdfs: bool = False
    errors: tuple[str, ...] = ()


def open_create_draft_from_review_detail(
    detail: Mapping[str, Any] | Any,
    *,
    review_signals: Sequence[Mapping[str, Any]] | None = None,
    profile_id: str | None = None,
) -> ConfigurationRuleDraft | None:
    """Create a draft from a review detail / guidance payload."""

    getter = detail.get if isinstance(detail, Mapping) else lambda key, default=None: getattr(
        detail, key, default
    )
    status = getter("configuration_coverage_status")
    missing = getter("missing_configuration_type")
    if not coverage_gap_actions_available(
        configuration_coverage_status=str(status or "") or None,
        missing_configuration_type=str(missing or "") or None,
    ):
        return None

    available = getter("available_configurations") or ()
    unmatched_pattern = load_unmatched_filename_pattern(profile_id=profile_id)
    return draft_from_coverage_guidance(
        selected_payment_field=str(getter("selected_payment_field") or "") or None,
        payment_account=str(getter("payment_account") or "") or None,
        source_review_item_id=str(
            getter("item_key") or getter("document_id") or ""
        )
        or None,
        source_filename=str(
            getter("source_filename") or getter("document_label") or ""
        )
        or None,
        matched_configuration_name=str(getter("matched_configuration_name") or "")
        or None,
        matched_configuration_reason=str(getter("matched_configuration_reason") or "")
        or None,
        missing_configuration_rule=str(getter("missing_configuration_rule") or "")
        or None,
        unmatched_reasons=tuple(getter("unmatched_reasons") or ()),
        available_configurations=tuple(available),
        unmatched_filename_pattern=unmatched_pattern,
        review_signals=review_signals,
        guidance={
            "configuration_coverage_status": status,
            "missing_configuration_type": missing,
            "user_guidance": getter("user_guidance"),
            "suggested_configuration_action": getter(
                "suggested_configuration_action"
            ),
            "guidance_severity": getter("guidance_severity") or "warning",
        },
        draft_type="create_new_configuration",
    )


def open_edit_existing_draft_from_review_detail(
    detail: Mapping[str, Any] | Any,
    *,
    existing_configuration_id: str | None = None,
    existing_configuration_name: str | None = None,
    profile_id: str | None = None,
) -> ConfigurationRuleDraft | None:
    """Open an edit draft shell from review context (no silent overwrite)."""

    getter = detail.get if isinstance(detail, Mapping) else lambda key, default=None: getattr(
        detail, key, default
    )
    available = getter("available_configurations") or ()
    unmatched_pattern = load_unmatched_filename_pattern(profile_id=profile_id)
    name = existing_configuration_name
    config_id = existing_configuration_id
    if not name and available:
        for item in available:
            if not isinstance(item, Mapping):
                continue
            if bool(item.get("is_unmatched")):
                continue
            name = str(item.get("configuration_name") or item.get("name") or "")
            config_id = str(item.get("configuration_id") or item.get("id") or "") or None
            break
    return draft_from_coverage_guidance(
        selected_payment_field=str(getter("selected_payment_field") or "") or None,
        payment_account=str(getter("payment_account") or "") or None,
        source_review_item_id=str(getter("item_key") or getter("document_id") or "")
        or None,
        source_filename=str(
            getter("source_filename") or getter("document_label") or ""
        )
        or None,
        matched_configuration_reason=str(getter("matched_configuration_reason") or "")
        or None,
        missing_configuration_rule=str(getter("missing_configuration_rule") or "")
        or None,
        unmatched_reasons=tuple(getter("unmatched_reasons") or ()),
        available_configurations=tuple(available),
        unmatched_filename_pattern=unmatched_pattern,
        guidance={
            "configuration_coverage_status": getter("configuration_coverage_status"),
            "missing_configuration_type": getter("missing_configuration_type"),
            "user_guidance": getter("user_guidance"),
            "suggested_configuration_action": getter(
                "suggested_configuration_action"
            ),
            "guidance_severity": getter("guidance_severity") or "warning",
        },
        draft_type="edit_existing_configuration",
        existing_configuration_id=config_id,
        existing_configuration_name=name,
    )


def draft_to_configuration_draft_vm(draft: ConfigurationRuleDraft) -> ConfigurationDraftVM:
    """Map Track-B rule draft into the UI-v2 configuration write VM."""

    pattern_text = str(draft.proposed_filename_pattern or "").strip()
    try:
        filename_pattern = pattern_from_template(pattern_text) if pattern_text else FilenamePattern()
    except Exception:  # noqa: BLE001 — keep draft editable; validation catches later
        filename_pattern = FilenamePattern()

    return ConfigurationDraftVM(
        configuration_id=draft.proposed_configuration_id,
        name=str(draft.proposed_configuration_name or "").strip(),
        active=True,
        matching=MatchingRuleDraftVM(
            feature_key=str(draft.proposed_matching_feature_key or "").strip(),
            operator=str(draft.proposed_matching_operator or "ist").strip() or "ist",
            values=[str(v).strip() for v in draft.proposed_matching_values if str(v).strip()],
        ),
        filename_pattern=filename_pattern,
        destination_path=str(draft.proposed_destination_path or "").strip(),
        is_new=draft.draft_type == "create_new_configuration",
        is_unmatched=False,
    )


def save_configuration_rule_draft(
    *,
    profile_id: str,
    draft: ConfigurationRuleDraft,
    explicit_user_confirmation: bool = False,
    active_configurations: Sequence[Any] | None = None,
) -> ConfigurationRuleSaveResult:
    """Persist a draft into UI-v2 profile/config state only after explicit confirm."""

    if not explicit_user_confirmation:
        return ConfigurationRuleSaveResult(
            ok=False,
            message="Speichern erfordert explizite Nutzerbestätigung.",
            draft=draft,
            errors=("requires_user_confirmation",),
        )
    if draft.saved:
        return ConfigurationRuleSaveResult(
            ok=False,
            message="Entwurf wurde bereits gespeichert.",
            draft=draft,
            errors=("already_saved",),
        )
    if draft.draft_type == "manual_review_only":
        return ConfigurationRuleSaveResult(
            ok=False,
            message=(
                "Ohne sicheres Zahlungsfeld wird keine payment_field-Regel gespeichert. "
                "Bitte manuell prüfen oder anderes Match-Kriterium wählen."
            ),
            draft=draft,
            errors=("manual_review_only",),
        )

    configs = active_configurations
    if configs is None:
        active, _unmatched = load_active_configuration_candidates(profile_id=profile_id)
        configs = active

    validated = validate_configuration_rule_draft(
        draft,
        active_configurations=configs,
        require_destination_for_save=True,
    )
    if validated.validation_errors:
        return ConfigurationRuleSaveResult(
            ok=False,
            message=validated.validation_errors[0],
            draft=validated,
            errors=validated.validation_errors,
        )
    if not validated.requires_user_confirmation:
        return ConfigurationRuleSaveResult(
            ok=False,
            message="Entwurf ohne Bestätigungspflicht ist unzulässig.",
            draft=validated,
            errors=("confirmation_flag_missing",),
        )
    if validated.proposes_business_category:
        return ConfigurationRuleSaveResult(
            ok=False,
            message="Automatische Kategorie-Zuordnung ist unzulässig.",
            draft=validated,
            errors=("business_category_forbidden",),
        )

    vm = draft_to_configuration_draft_vm(validated)
    if validated.draft_type == "create_new_configuration":
        result: WriteOperationResult = create_configuration(profile_id, vm)
    else:
        result = update_configuration(profile_id, vm)

    if not result.success:
        return ConfigurationRuleSaveResult(
            ok=False,
            message=result.message or "Speichern fehlgeschlagen.",
            draft=validated,
            errors=result.errors or (result.message,),
        )

    saved_draft = replace(
        validated,
        saved=True,
        proposed_configuration_id=result.configuration_id
        or validated.proposed_configuration_id,
    )
    return ConfigurationRuleSaveResult(
        ok=True,
        message=result.message or "Konfiguration gespeichert.",
        draft=saved_draft,
        configuration_id=result.configuration_id,
        called_run_once=False,
        mutated_input=False,
        wrote_final_pdfs=False,
    )


def build_configuration_rule_action_labels() -> tuple[str, ...]:
    return (
        ACTION_CREATE_FROM_GUIDANCE,
        ACTION_EDIT_EXISTING,
        ACTION_MANUAL_KEEP_UNCLEAR,
    )


def build_configuration_rule_draft_panel(
    state: Any,
    draft: ConfigurationRuleDraft,
) -> ft.Control:
    """Render the draft editing panel (save/cancel require explicit clicks)."""

    feedback = str(getattr(state, "configuration_rule_draft_feedback", "") or "")
    feedback_error = bool(
        getattr(state, "configuration_rule_draft_feedback_error", False)
    )

    name_field = ft.TextField(
        label="Konfigurationsname",
        value=draft.proposed_configuration_name,
        on_change=lambda e: _update_draft_field(
            state, "proposed_configuration_name", e.control.value or ""
        ),
        **outlined_field_kwargs(),
    )
    feature_field = ft.TextField(
        label="Matching-Merkmal",
        value=draft.proposed_matching_feature_key or "",
        on_change=lambda e: _update_draft_field(
            state, "proposed_matching_feature_key", e.control.value or ""
        ),
        disabled=draft.draft_type == "manual_review_only",
        **outlined_field_kwargs(),
    )
    operator_field = ft.TextField(
        label="Operator",
        value=draft.proposed_matching_operator or "",
        on_change=lambda e: _update_draft_field(
            state, "proposed_matching_operator", e.control.value or ""
        ),
        disabled=draft.draft_type == "manual_review_only",
        **outlined_field_kwargs(),
    )
    values_field = ft.TextField(
        label="Matching-Werte (kommagetrennt)",
        value=", ".join(draft.proposed_matching_values),
        on_change=lambda e: _update_draft_values(state, e.control.value or ""),
        disabled=draft.draft_type == "manual_review_only",
        **outlined_field_kwargs(),
    )
    pattern_field = ft.TextField(
        label="Dateinamensmuster",
        value=draft.proposed_filename_pattern,
        on_change=lambda e: _update_draft_field(
            state, "proposed_filename_pattern", e.control.value or ""
        ),
        **outlined_field_kwargs(),
    )
    destination_field = ft.TextField(
        label="Zielordner (Pflicht zum Speichern)",
        value=draft.proposed_destination_path,
        on_change=lambda e: _update_draft_field(
            state, "proposed_destination_path", e.control.value or ""
        ),
        hint_text="Kein privater Default — explizit setzen",
        **outlined_field_kwargs(),
    )

    evidence_text = "; ".join(draft.source_evidence) if draft.source_evidence else "—"
    warnings_text = "; ".join(draft.warnings) if draft.warnings else "—"
    future_text = (
        "; ".join(draft.future_match_preview) if draft.future_match_preview else "—"
    )
    errors_text = (
        "; ".join(draft.validation_errors) if draft.validation_errors else ""
    )

    lines: list[ft.Control] = [
        ft.Text(f"Entwurfstyp: {draft.draft_type}", size=12, color=COLOR_TEXT_SECONDARY),
        ft.Text(f"Grund: {draft.reason}", size=12),
        ft.Text(f"Evidenz: {evidence_text}", size=11, color=COLOR_TEXT_MUTED),
        ft.Text(f"Warnungen: {warnings_text}", size=11, color=COLOR_TEXT_MUTED),
        ft.Text(
            f"Würde künftig matchen: {future_text}",
            size=11,
            color=COLOR_TEXT_MUTED,
        ),
        ft.Text(
            f"Dateiname-Vorschau: {draft.filename_preview or '—'}",
            size=11,
            color=COLOR_TEXT_MUTED,
        ),
        ft.Text(
            "Speichern nur nach explizitem Klick — keine produktive Verarbeitung.",
            size=11,
            color=COLOR_TEXT_MUTED,
        ),
        name_field,
        feature_field,
        operator_field,
        values_field,
        pattern_field,
        destination_field,
    ]
    if errors_text:
        lines.append(ft.Text(f"Validierung: {errors_text}", size=11, color="#B45309"))
    if feedback:
        lines.append(
            ft.Text(
                feedback,
                size=12,
                color="#B45309" if feedback_error else COLOR_TEXT_SECONDARY,
            )
        )

    can_save = draft.draft_type != "manual_review_only" and not draft.saved

    def _on_save(_e: ft.ControlEvent) -> None:
        from invoice_tool.app_paths import resolve_active_profile_id

        profile_id = str(
            getattr(state, "selected_profile_id", "") or ""
        ).strip() or resolve_active_profile_id()
        current = getattr(state, "configuration_rule_draft", None)
        if current is None:
            return
        result = save_configuration_rule_draft(
            profile_id=profile_id,
            draft=current,
            explicit_user_confirmation=True,
        )
        state.configuration_rule_draft = result.draft
        state.configuration_rule_draft_feedback = result.message
        state.configuration_rule_draft_feedback_error = not result.ok
        if state.refresh is not None:
            state.refresh()

    def _on_cancel(_e: ft.ControlEvent) -> None:
        state.configuration_rule_draft = None
        state.configuration_rule_draft_feedback = ""
        state.configuration_rule_draft_feedback_error = False
        state.configuration_rule_manual_keep_unclear = False
        if state.refresh is not None:
            state.refresh()

    lines.append(
        ft.Row(
            [
                secondary_button(
                    ACTION_SAVE_DRAFT,
                    on_click=_on_save,
                    disabled=not can_save,
                ),
                secondary_button(ACTION_CANCEL_DRAFT, on_click=_on_cancel),
            ],
            spacing=8,
            wrap=True,
        )
    )
    return section_block(
        "Konfigurationsregel-Entwurf",
        ft.Column(lines, spacing=8, tight=True),
        subtitle="Nur nach Bestätigung speichern — Preview/UI-v2",
    )


def build_configuration_coverage_action_row(
    state: Any,
    detail: Any,
) -> ft.Control | None:
    """Action buttons for coverage gaps in the Review detail panel."""

    status = getattr(detail, "configuration_coverage_status", None)
    missing = getattr(detail, "missing_configuration_type", None)
    if not coverage_gap_actions_available(
        configuration_coverage_status=status,
        missing_configuration_type=missing,
    ):
        return None

    def _refresh() -> None:
        if state.refresh is not None:
            state.refresh()

    def _signals() -> list[dict[str, object]]:
        run = getattr(state, "processing_run_state", None)
        items = getattr(run, "review_items", ()) or ()
        out: list[dict[str, object]] = []
        for item in items:
            out.append(
                {
                    "source_filename": getattr(item, "document_name", None),
                    "document_id": getattr(item, "document_id", None),
                    "selected_payment_field": None,
                    "payment_account": None,
                }
            )
        # Prefer rich signals from planned destinations when present.
        planned = getattr(run, "planned_destinations", ()) or ()
        enriched: list[dict[str, object]] = []
        for dest in planned:
            meta = getattr(dest, "metadata", None) or {}
            if not isinstance(meta, Mapping):
                meta = {}
            enriched.append(
                {
                    "source_filename": getattr(dest, "document_name", None),
                    "document_id": getattr(dest, "document_name", None),
                    "selected_payment_field": meta.get("selected_payment_field"),
                    "payment_account": meta.get("payment_account"),
                    "payment_field": meta.get("payment_field"),
                }
            )
        return enriched or out

    def _on_create(_e: ft.ControlEvent) -> None:
        draft = open_create_draft_from_review_detail(
            detail,
            review_signals=_signals(),
            profile_id=getattr(state, "selected_profile_id", None),
        )
        state.configuration_rule_draft = draft
        state.configuration_rule_manual_keep_unclear = False
        state.configuration_rule_draft_feedback = (
            "Entwurf geöffnet — noch nicht gespeichert."
            if draft is not None
            else "Kein sicherer Entwurf für diesen Hinweis."
        )
        state.configuration_rule_draft_feedback_error = draft is None
        _refresh()

    def _on_edit(_e: ft.ControlEvent) -> None:
        draft = open_edit_existing_draft_from_review_detail(
            detail,
            profile_id=getattr(state, "selected_profile_id", None),
        )
        state.configuration_rule_draft = draft
        state.configuration_rule_manual_keep_unclear = False
        state.configuration_rule_draft_feedback = (
            "Bearbeitungsentwurf geöffnet — Speichern erfordert Bestätigung."
            if draft is not None
            else "Kein Bearbeitungsentwurf verfügbar."
        )
        state.configuration_rule_draft_feedback_error = draft is None
        if state.navigate is not None and draft is not None:
            # Optional: stay on review with draft panel; also allow configs page.
            pass
        _refresh()

    def _on_manual(_e: ft.ControlEvent) -> None:
        state.configuration_rule_draft = None
        state.configuration_rule_manual_keep_unclear = True
        state.configuration_rule_draft_feedback = (
            "Manuell prüfen / Unklar belassen — keine Regel gespeichert."
        )
        state.configuration_rule_draft_feedback_error = False
        _refresh()

    return section_block(
        "Konfigurationsabdeckung — Aktionen",
        ft.Row(
            [
                secondary_button(
                    ACTION_CREATE_FROM_GUIDANCE,
                    on_click=_on_create,
                ),
                secondary_button(
                    ACTION_EDIT_EXISTING,
                    on_click=_on_edit,
                ),
                secondary_button(
                    ACTION_MANUAL_KEEP_UNCLEAR,
                    on_click=_on_manual,
                ),
            ],
            spacing=8,
            wrap=True,
        ),
        subtitle="Entwurf öffnen — kein stilles Speichern",
    )


def _update_draft_field(state: Any, field_name: str, value: str) -> None:
    draft = getattr(state, "configuration_rule_draft", None)
    if draft is None:
        return
    updated = replace(draft, **{field_name: value})
    active, _ = load_active_configuration_candidates(
        profile_id=getattr(state, "selected_profile_id", None)
    )
    state.configuration_rule_draft = validate_configuration_rule_draft(
        updated, active_configurations=active
    )


def _update_draft_values(state: Any, raw: str) -> None:
    values = tuple(
        part.strip() for part in str(raw or "").split(",") if part.strip()
    )
    draft = getattr(state, "configuration_rule_draft", None)
    if draft is None:
        return
    updated = replace(draft, proposed_matching_values=values)
    active, _ = load_active_configuration_candidates(
        profile_id=getattr(state, "selected_profile_id", None)
    )
    state.configuration_rule_draft = validate_configuration_rule_draft(
        updated, active_configurations=active
    )


__all__ = (
    "ConfigurationRuleSaveResult",
    "build_configuration_coverage_action_row",
    "build_configuration_rule_action_labels",
    "build_configuration_rule_draft_panel",
    "draft_to_configuration_draft_vm",
    "open_create_draft_from_review_detail",
    "open_edit_existing_draft_from_review_detail",
    "save_configuration_rule_draft",
)
