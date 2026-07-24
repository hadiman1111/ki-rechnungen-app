"""Track-B configuration rule draft editor / save flow (Prompt 26/34).

Opens drafts from Review guidance, validates, and saves only after explicit
user confirmation into UI-v2 profile/config state.

Never calls run_once. Never mutates input files. Never writes final PDFs.
Never maps PayPal/card to private business categories or AMEX without evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
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
from invoice_tool.ui_v2.components import form_field_group, secondary_button, section_block
from invoice_tool.ui_v2.configuration_duplicate_remediation import (
    ACTION_DEACTIVATE_EXACT_DUPLICATES,
    ACTION_SHOW_DUPLICATES,
    CONTROLLED_OUTPUT_ROOT,
    analyze_active_configuration_duplicates,
    controlled_target_missing_message,
    deactivate_exact_duplicate_configs,
    is_controlled_output_target,
)
from invoice_tool.ui_v2.configuration_matching import load_active_configuration_candidates
from invoice_tool.ui_v2.configuration_rule_apply_preview import (
    mark_rule_saved_for_preview_apply,
    rerun_preview_matching_after_rule_change,
)
from invoice_tool.ui_v2.configuration_rule_draft import (
    ACTION_CANCEL_DRAFT,
    ACTION_CREATE_FROM_GUIDANCE,
    ACTION_EDIT_EXISTING,
    ACTION_MANUAL_KEEP_UNCLEAR,
    ACTION_SAVE_DRAFT,
    DEFAULT_PATTERN,
    ConfigurationRuleDraft,
    coverage_gap_actions_available,
    draft_from_coverage_guidance,
    load_unmatched_filename_pattern,
    validate_configuration_rule_draft,
)
from invoice_tool.ui_v2.dev_defaults import (
    ACTION_CREATE_CONTROLLED_FOLDERS,
    MSG_PAYPAL_TARGET_MISSING,
    ensure_track_b_dev_folders_if_requested,
    is_track_b_dev_defaults_enabled,
    maybe_prefill_track_b_dev_paypal_target,
    paypal_target_status_message,
)
from invoice_tool.ui_v2.draft_models import ConfigurationDraftVM, MatchingRuleDraftVM
from invoice_tool.ui_v2.edit_components import full_width_field
from invoice_tool.ui_v2.theme import COLOR_TEXT_MUTED, COLOR_TEXT_SECONDARY
from invoice_tool.ui_v2.track_b_smoke_debug_copy import SMOKE_DEV_UI_LAYOUT_MARKER

ACTION_SAVE_AND_RERUN = "Speichern und Matching neu berechnen"
ACTION_PAYPAL_SMOKE_SAVE_AND_RERUN = (
    "PayPal-Regel speichern und Matching neu berechnen"
)
ACTION_FINALIZATION_DRY_RUN = "Finalisierungs-Trockenlauf erstellen"
ACTION_SANDBOX_FINAL_WRITE = "Sandbox-Finalschreiben testen"


@dataclass(frozen=True)
class ConfigurationRuleSaveResult:
    ok: bool
    message: str
    draft: ConfigurationRuleDraft | None = None
    configuration_id: str | None = None
    called_run_once: bool = False
    mutated_input: bool = False
    wrote_final_pdfs: bool = False
    preview_only_rerun: bool = False
    assigned_business_category: bool = False
    mapped_card_to_amex: bool = False
    updated_run_state: Any | None = None
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
    draft = draft_from_coverage_guidance(
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
    # Track-B UI-v2 smoke: prefill PayPal target only (never auto-save).
    prefill = maybe_prefill_track_b_dev_paypal_target(draft)
    return prefill.draft if prefill.draft is not None else draft


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
        preview_only_rerun=False,
        assigned_business_category=False,
        mapped_card_to_amex=False,
    )


def is_paypal_smoke_draft(draft: ConfigurationRuleDraft | None) -> bool:
    if draft is None:
        return False
    feature = str(draft.proposed_matching_feature_key or "").strip().casefold()
    values = {
        str(v).strip().casefold() for v in draft.proposed_matching_values if str(v).strip()
    }
    condition = str(draft.proposed_condition or "").strip().casefold()
    if condition.replace("_", " ") == "payment field ist paypal":
        return True
    if condition == "payment_field ist paypal":
        return True
    return feature in {"payment_field", "payment field"} and "paypal" in values


def save_paypal_rule_and_rerun_matching(
    *,
    profile_id: str,
    draft: ConfigurationRuleDraft,
    run_state: Any,
    explicit_user_confirmation: bool = False,
    require_controlled_target: bool = True,
) -> ConfigurationRuleSaveResult:
    """One-click PayPal smoke: save active PayPal rule + preview-only rematch."""

    if not explicit_user_confirmation:
        return ConfigurationRuleSaveResult(
            ok=False,
            message="PayPal-Smoke erfordert explizite Nutzerbestätigung.",
            draft=draft,
            errors=("requires_user_confirmation",),
        )
    if not is_paypal_smoke_draft(draft):
        return ConfigurationRuleSaveResult(
            ok=False,
            message=(
                "PayPal-Smoke nur bei proposed_condition "
                "„payment_field ist paypal“ verfügbar."
            ),
            draft=draft,
            errors=("not_paypal_draft",),
        )

    prepared = replace(
        draft,
        proposed_configuration_name=str(
            draft.proposed_configuration_name or "PayPal"
        ).strip()
        or "PayPal",
        proposed_matching_feature_key="payment_field",
        proposed_matching_operator="ist",
        proposed_matching_values=("paypal",),
        proposed_filename_pattern=str(
            draft.proposed_filename_pattern or DEFAULT_PATTERN
        ).strip()
        or DEFAULT_PATTERN,
        proposes_business_category=False,
    )
    if require_controlled_target and not is_controlled_output_target(
        prepared.proposed_destination_path
    ):
        return ConfigurationRuleSaveResult(
            ok=False,
            message=controlled_target_missing_message(
                prepared.proposed_destination_path
            ),
            draft=prepared,
            errors=("controlled_target_required",),
        )
    # Also require the folder to exist for smoke clarity.
    dest = Path(str(prepared.proposed_destination_path or "")).expanduser()
    if not dest.is_dir():
        return ConfigurationRuleSaveResult(
            ok=False,
            message=(
                f"Zielordner fehlt oder ist nicht erreichbar: {dest}. "
                f"Kontrollierter Smoke-Output: {CONTROLLED_OUTPUT_ROOT}"
            ),
            draft=prepared,
            errors=("target_folder_missing",),
        )

    saved = save_configuration_rule_draft(
        profile_id=profile_id,
        draft=prepared,
        explicit_user_confirmation=True,
    )
    if not saved.ok or saved.draft is None:
        return saved

    apply = rerun_preview_matching_after_rule_change(
        run_state=run_state,
        profile_id=profile_id,
        applied_configuration_name=saved.draft.proposed_configuration_name,
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    message = saved.message
    if apply.ok:
        message = (
            f"{saved.message} — Matching neu berechnet (Preview only). "
            f"{apply.message}"
        )
    else:
        message = (
            f"{saved.message} — Speichern ok, Matching-Rerun: {apply.message}"
        )
    return ConfigurationRuleSaveResult(
        ok=bool(saved.ok and apply.ok),
        message=message,
        draft=saved.draft,
        configuration_id=saved.configuration_id,
        called_run_once=False,
        mutated_input=False,
        wrote_final_pdfs=False,
        preview_only_rerun=True,
        assigned_business_category=False,
        mapped_card_to_amex=False,
        updated_run_state=apply.updated_run_state if apply.ok else None,
        errors=() if apply.ok else apply.errors,
    )


def build_configuration_rule_action_labels() -> tuple[str, ...]:
    return (
        ACTION_CREATE_FROM_GUIDANCE,
        ACTION_EDIT_EXISTING,
        ACTION_MANUAL_KEEP_UNCLEAR,
        ACTION_SAVE_DRAFT,
        ACTION_SAVE_AND_RERUN,
        ACTION_PAYPAL_SMOKE_SAVE_AND_RERUN,
        ACTION_SHOW_DUPLICATES,
        ACTION_DEACTIVATE_EXACT_DUPLICATES,
    )


def _content_padding(*, horizontal: int = 12, vertical: int = 10) -> Any:
    """Flet 0.85 uses Padding.symmetric; older builds expose padding.symmetric."""

    padding_cls = getattr(ft, "Padding", None)
    if padding_cls is not None and hasattr(padding_cls, "symmetric"):
        return padding_cls.symmetric(horizontal=horizontal, vertical=vertical)
    padding_mod = getattr(ft, "padding", None)
    if padding_mod is not None and hasattr(padding_mod, "symmetric"):
        return padding_mod.symmetric(horizontal=horizontal, vertical=vertical)
    return None


def _smoke_field(
    *,
    value: str,
    on_change: Any,
    disabled: bool = False,
    multiline: bool = False,
    hint: str | None = None,
) -> ft.TextField:
    kwargs: dict[str, Any] = {
        "dense": False,
        "text_size": 13,
        "border_radius": 8,
        "expand": True,
    }
    pad = _content_padding()
    if pad is not None:
        kwargs["content_padding"] = pad
    if multiline:
        kwargs["min_lines"] = 2
        kwargs["max_lines"] = 5
    else:
        kwargs["max_lines"] = 1
    return ft.TextField(
        value=value,
        on_change=on_change,
        disabled=disabled,
        hint_text=hint,
        **kwargs,
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

    name_field = _smoke_field(
        value=draft.proposed_configuration_name,
        on_change=lambda e: _update_draft_field(
            state, "proposed_configuration_name", e.control.value or ""
        ),
    )
    feature_field = _smoke_field(
        value=draft.proposed_matching_feature_key or "",
        on_change=lambda e: _update_draft_field(
            state, "proposed_matching_feature_key", e.control.value or ""
        ),
        disabled=draft.draft_type == "manual_review_only",
    )
    operator_field = _smoke_field(
        value=draft.proposed_matching_operator or "",
        on_change=lambda e: _update_draft_field(
            state, "proposed_matching_operator", e.control.value or ""
        ),
        disabled=draft.draft_type == "manual_review_only",
    )
    values_field = _smoke_field(
        value=", ".join(draft.proposed_matching_values),
        on_change=lambda e: _update_draft_values(state, e.control.value or ""),
        disabled=draft.draft_type == "manual_review_only",
    )
    pattern_field = _smoke_field(
        value=draft.proposed_filename_pattern,
        on_change=lambda e: _update_draft_field(
            state, "proposed_filename_pattern", e.control.value or ""
        ),
        multiline=True,
    )
    # Track-B UI-v2 smoke: keep PayPal destination prefilled when empty (no auto-save).
    if is_track_b_dev_defaults_enabled() and is_paypal_smoke_draft(draft):
        prefill = maybe_prefill_track_b_dev_paypal_target(draft)
        if prefill.applied and prefill.draft is not None:
            draft = prefill.draft
            state.configuration_rule_draft = draft

    destination_field = _smoke_field(
        value=draft.proposed_destination_path,
        on_change=lambda e: _update_draft_field(
            state, "proposed_destination_path", e.control.value or ""
        ),
        multiline=True,
        hint=f"Smoke-Ziel z. B. {CONTROLLED_OUTPUT_ROOT / 'geplant' / 'paypal'}",
    )

    evidence_text = "; ".join(draft.source_evidence) if draft.source_evidence else "—"
    warnings_text = "; ".join(draft.warnings) if draft.warnings else "—"
    future_text = (
        "; ".join(draft.future_match_preview) if draft.future_match_preview else "—"
    )
    errors_text = (
        "; ".join(draft.validation_errors) if draft.validation_errors else ""
    )

    can_save = draft.draft_type != "manual_review_only" and not draft.saved
    paypal_ready = is_paypal_smoke_draft(draft) and can_save
    paypal_missing_msg = (
        paypal_target_status_message()
        if is_track_b_dev_defaults_enabled() and is_paypal_smoke_draft(draft)
        else None
    )

    def _profile_id() -> str:
        from invoice_tool.app_paths import resolve_active_profile_id

        return str(
            getattr(state, "selected_profile_id", "") or ""
        ).strip() or resolve_active_profile_id()

    def _after_save(result: ConfigurationRuleSaveResult) -> None:
        state.configuration_rule_draft = result.draft
        state.configuration_rule_draft_feedback = result.message
        state.configuration_rule_draft_feedback_error = not result.ok
        if result.updated_run_state is not None:
            state.processing_run_state = result.updated_run_state
        if result.ok and result.draft is not None:
            mark_rule_saved_for_preview_apply(
                state,
                draft=result.draft,
                configuration_id=result.configuration_id,
            )
            state.configuration_rule_draft_feedback = (
                f"{result.message} — Preview only — keine finale Verarbeitung."
            )
        if state.refresh is not None:
            state.refresh()

    def _on_save(_e: ft.ControlEvent) -> None:
        current = getattr(state, "configuration_rule_draft", None)
        if current is None:
            return
        result = save_configuration_rule_draft(
            profile_id=_profile_id(),
            draft=current,
            explicit_user_confirmation=True,
        )
        _after_save(result)

    def _on_save_and_rerun(_e: ft.ControlEvent) -> None:
        current = getattr(state, "configuration_rule_draft", None)
        if current is None:
            return
        result = save_configuration_rule_draft(
            profile_id=_profile_id(),
            draft=current,
            explicit_user_confirmation=True,
        )
        if result.ok and result.draft is not None:
            mark_rule_saved_for_preview_apply(
                state,
                draft=result.draft,
                configuration_id=result.configuration_id,
            )
            apply = rerun_preview_matching_after_rule_change(
                run_state=getattr(state, "processing_run_state", None),
                profile_id=_profile_id(),
                applied_configuration_name=result.draft.proposed_configuration_name,
                applied_configuration_condition=str(
                    result.draft.proposed_condition or ""
                )
                or None,
                applied_configuration_id=result.configuration_id,
                explicit_user_action=True,
            )
            if apply.ok and apply.updated_run_state is not None:
                state.processing_run_state = apply.updated_run_state
            result = ConfigurationRuleSaveResult(
                ok=result.ok and apply.ok,
                message=(
                    f"{result.message} — {apply.message}"
                    if result.ok
                    else result.message
                ),
                draft=result.draft,
                configuration_id=result.configuration_id,
                called_run_once=False,
                mutated_input=False,
                wrote_final_pdfs=False,
                preview_only_rerun=True,
                assigned_business_category=False,
                mapped_card_to_amex=False,
                errors=apply.errors if result.ok and not apply.ok else result.errors,
            )
        _after_save(result)

    def _on_paypal_smoke(_e: ft.ControlEvent) -> None:
        current = getattr(state, "configuration_rule_draft", None)
        if current is None:
            return
        result = save_paypal_rule_and_rerun_matching(
            profile_id=_profile_id(),
            draft=current,
            run_state=getattr(state, "processing_run_state", None),
            explicit_user_confirmation=True,
            require_controlled_target=True,
        )
        _after_save(result)

    def _on_cancel(_e: ft.ControlEvent) -> None:
        state.configuration_rule_draft = None
        state.configuration_rule_draft_feedback = ""
        state.configuration_rule_draft_feedback_error = False
        state.configuration_rule_manual_keep_unclear = False
        if state.refresh is not None:
            state.refresh()

    def _on_create_controlled_folders(_e: ft.ControlEvent) -> None:
        result = ensure_track_b_dev_folders_if_requested(explicit_user_action=True)
        state.configuration_rule_draft_feedback = (
            result.message
            if result.ok
            else (result.message or MSG_PAYPAL_TARGET_MISSING)
        )
        state.configuration_rule_draft_feedback_error = not result.ok
        if state.refresh is not None:
            state.refresh()

    action_buttons: list[ft.Control] = [
        secondary_button(
            ACTION_SAVE_DRAFT,
            on_click=_on_save,
            disabled=not can_save,
        ),
        secondary_button(
            ACTION_SAVE_AND_RERUN,
            on_click=_on_save_and_rerun,
            disabled=not can_save,
        ),
        secondary_button(
            ACTION_PAYPAL_SMOKE_SAVE_AND_RERUN,
            on_click=_on_paypal_smoke,
            disabled=not paypal_ready,
        ),
        secondary_button(ACTION_CANCEL_DRAFT, on_click=_on_cancel),
    ]
    if is_track_b_dev_defaults_enabled() and paypal_missing_msg:
        action_buttons.append(
            secondary_button(
                ACTION_CREATE_CONTROLLED_FOLDERS,
                on_click=_on_create_controlled_folders,
            )
        )

    action_row = ft.Container(
        content=ft.Row(
            action_buttons,
            spacing=8,
            wrap=True,
        ),
        padding=_content_padding(horizontal=0, vertical=4),
    )

    meta_lines: list[ft.Control] = [
        ft.Text(SMOKE_DEV_UI_LAYOUT_MARKER, size=10, color=COLOR_TEXT_MUTED),
    ]
    if paypal_missing_msg:
        meta_lines.append(ft.Text(paypal_missing_msg, size=12, color="#B91C1C"))
    meta = ft.Column(
        [
            *meta_lines,
            ft.Text(
                f"Entwurfstyp: {draft.draft_type}",
                size=12,
                color=COLOR_TEXT_SECONDARY,
            ),
            ft.Text(f"Grund: {draft.reason}", size=12),
            ft.Text(f"Evidenz: {evidence_text}", size=11, color=COLOR_TEXT_MUTED),
            ft.Text(
                f"Warnungen: {warnings_text}",
                size=11,
                color=COLOR_TEXT_MUTED,
            ),
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
        ],
        spacing=4,
        tight=True,
    )

    form = ft.Column(
        [
            form_field_group("Konfigurationsname", full_width_field(name_field)),
            form_field_group("Matching-Merkmal", full_width_field(feature_field)),
            form_field_group("Operator", full_width_field(operator_field)),
            form_field_group(
                "Matching-Werte (kommagetrennt)", full_width_field(values_field)
            ),
            form_field_group("Dateinamensmuster", full_width_field(pattern_field)),
            form_field_group(
                "Zielordner (Pflicht zum Speichern)",
                full_width_field(destination_field),
                helper="Kein privater Default — kontrollierten Smoke-Output wählen",
            ),
        ],
        spacing=12,
        tight=True,
    )

    lines: list[ft.Control] = [action_row, meta, form]
    if errors_text:
        lines.append(ft.Text(f"Validierung: {errors_text}", size=12, color="#B45309"))
    if feedback:
        lines.append(
            ft.Text(
                feedback,
                size=12,
                color="#B45309" if feedback_error else COLOR_TEXT_SECONDARY,
            )
        )
    lines.append(action_row)

    return section_block(
        "Konfigurationsregel-Entwurf",
        ft.Column(lines, spacing=10, tight=True),
        subtitle="Dev-Smoke UI — Labels oberhalb, breite Felder, sticky Aktionen",
    )


def build_duplicate_config_remediation_panel(state: Any) -> ft.Control:
    """Dev-only remediation for exact duplicate active configs in UI-v2 state."""

    report = str(getattr(state, "track_b_duplicate_report_text", "") or "")
    feedback = str(getattr(state, "track_b_duplicate_remediation_feedback", "") or "")
    feedback_error = bool(
        getattr(state, "track_b_duplicate_remediation_feedback_error", False)
    )

    def _profile_id() -> str:
        from invoice_tool.app_paths import resolve_active_profile_id

        return str(
            getattr(state, "selected_profile_id", "") or ""
        ).strip() or resolve_active_profile_id()

    def _on_show(_e: ft.ControlEvent) -> None:
        try:
            from invoice_tool.profile_store import load_profile_bundle

            bundle = load_profile_bundle(_profile_id())
            analysis = analyze_active_configuration_duplicates(bundle.configurations)
            state.track_b_duplicate_report_text = analysis.report_text()
            state.track_b_duplicate_remediation_feedback = "Duplikat-Analyse aktualisiert."
            state.track_b_duplicate_remediation_feedback_error = False
        except Exception as exc:  # noqa: BLE001
            state.track_b_duplicate_remediation_feedback = str(exc)
            state.track_b_duplicate_remediation_feedback_error = True
        if state.refresh is not None:
            state.refresh()

    def _on_deactivate(_e: ft.ControlEvent) -> None:
        result = deactivate_exact_duplicate_configs(
            _profile_id(),
            explicit_user_confirmation=True,
        )
        state.track_b_duplicate_remediation_feedback = result.message
        state.track_b_duplicate_remediation_feedback_error = not result.ok
        if result.ok:
            _on_show(_e)
            return
        if state.refresh is not None:
            state.refresh()

    body: list[ft.Control] = [
        ft.Text(
            "Nur UI-v2 Profilzustand — keine PDFs, kein run_once, kein Track A.",
            size=11,
            color=COLOR_TEXT_MUTED,
        ),
        ft.Row(
            [
                secondary_button(ACTION_SHOW_DUPLICATES, on_click=_on_show),
                secondary_button(
                    ACTION_DEACTIVATE_EXACT_DUPLICATES,
                    on_click=_on_deactivate,
                ),
            ],
            spacing=8,
            wrap=True,
        ),
    ]
    if report:
        report_kwargs: dict[str, Any] = {
            "value": report,
            "read_only": True,
            "min_lines": 4,
            "max_lines": 10,
            "text_size": 11,
        }
        pad = _content_padding()
        if pad is not None:
            report_kwargs["content_padding"] = pad
        body.append(ft.TextField(**report_kwargs))
    if feedback:
        body.append(
            ft.Text(
                feedback,
                size=12,
                color="#B45309" if feedback_error else COLOR_TEXT_SECONDARY,
            )
        )
    return section_block(
        "Doppelte Konfigurationen (Dev-Repair)",
        ft.Column(body, spacing=8, tight=True),
        subtitle="Exakte Duplikate nur nach explizitem Klick deaktivieren",
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
    "ACTION_FINALIZATION_DRY_RUN",
    "ACTION_PAYPAL_SMOKE_SAVE_AND_RERUN",
    "ACTION_SANDBOX_FINAL_WRITE",
    "ACTION_SAVE_AND_RERUN",
    "ConfigurationRuleSaveResult",
    "build_configuration_coverage_action_row",
    "build_configuration_rule_action_labels",
    "build_configuration_rule_draft_panel",
    "build_duplicate_config_remediation_panel",
    "draft_to_configuration_draft_vm",
    "is_paypal_smoke_draft",
    "open_create_draft_from_review_detail",
    "open_edit_existing_draft_from_review_detail",
    "save_configuration_rule_draft",
    "save_paypal_rule_and_rerun_matching",
)
