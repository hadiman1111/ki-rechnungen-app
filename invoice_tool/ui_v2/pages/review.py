"""Zur Prüfung page — Track-B UI-v2 simple user review mode.

Honest empty state by default. Items appear only from ProcessingRunState
after a real run injects them. No fake documents, no PDF processing,
no folder scan, no file mutation, no processing-core imports.

Primary surface answers plain-German user questions only. Technical
flags stay collapsed. Preview-only actions mutate in-memory UiV2 review
state only — never run_once, never final writes, never productive export.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import flet as ft

from invoice_tool.ui_v2.components import (
    collapsible_details,
    compact_entry_row,
    empty_state,
    form_field_group,
    page_header,
    page_scaffold,
    secondary_button,
    section_block,
    stacked_list,
    status_badge,
)
from invoice_tool.ui_v2.theme import (
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_PRIMARY,
    COLOR_PRIMARY_SUBTLE,
    COLOR_SURFACE,
    COLOR_SURFACE_ALT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    FONT_SIZE_HELPER,
    FONT_SIZE_MONO,
    FONT_SIZE_SECTION_TITLE,
    RADIUS_CARD,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
)
from invoice_tool.ui_v2.dev_defaults import (
    ACTION_CREATE_CONTROLLED_FOLDERS,
    MSG_EMPTY_REVIEW_HELP,
    apply_track_b_dev_folder_defaults_to_state,
    ensure_track_b_dev_folders_if_requested,
    is_track_b_dev_defaults_enabled,
)
from invoice_tool.ui_v2.navigation import NAV_WORKSPACE
from invoice_tool.ui_v2.export_reporting import (
    MSG_EXPORT_PREVIEW_TITLE,
    MSG_NO_FINAL_FILES_WRITTEN,
    MSG_NO_SANDBOX_RUN,
    MSG_ORIGINALS_UNCHANGED,
    MSG_PRODUCTIVE_PROCESSING_BLOCKED,
    MSG_TARGET_PATHS_VORSCHAU_ONLY,
    build_export_preview_report,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_components import (
    review_error_section_lines,
    review_planned_preview_lines,
    review_safety_line,
)
from invoice_tool.ui_v2.preview_export import (
    MSG_FIELD_AMOUNT,
    MSG_FIELD_AMOUNT_FORMAT,
    MSG_FIELD_AMOUNT_REASON,
    MSG_FIELD_ART_REASON,
    MSG_FIELD_BUSINESS_CATEGORY,
    MSG_FIELD_AVAILABLE_CONFIGURATIONS,
    MSG_FIELD_CONDITION_RESULTS,
    MSG_FIELD_CONFIGURATION,
    MSG_FIELD_COUNTERPARTY_NAME,
    MSG_FIELD_EVALUATED_CANDIDATES,
    MSG_FIELD_MATCHING_REASON,
    MSG_FIELD_MISSING_CONFIGURATION_RULE,
    MSG_FIELD_CONFIGURATION_COVERAGE,
    MSG_FIELD_USER_GUIDANCE,
    MSG_FIELD_SUGGESTED_CONFIGURATION_ACTION,
    MSG_FIELD_DOCUMENT_ART,
    MSG_FIELD_DOCUMENT_DIRECTION,
    MSG_FIELD_FILENAME_PATTERN,
    MSG_FIELD_MISSING_PLACEHOLDERS,
    MSG_FIELD_PAYMENT_FIELD,
    MSG_FIELD_PAYMENT_FIELD_REASON,
    MSG_FIELD_PLACEHOLDER_VALUES,
    resolve_preview_naming,
)
from invoice_tool.ui_v2.review_preview_state import (
    ACTION_EXCLUDE_EXPORT_PREVIEW,
    ACTION_KEEP_IN_REVIEW,
    ACTION_MARK_CHECKED_PREVIEW,
    ACTION_RESET_SELECTION,
    MSG_BADGE_NO_FINAL_WRITE,
    MSG_BADGE_ORIGINALS_UNCHANGED,
    MSG_BADGE_PREVIEW,
    MSG_BADGE_PRODUCTIVE_BLOCKED,
    MSG_CATEGORY_REVIEW,
    MSG_EMPTY_OUTPUT_EXPLAIN,
    MSG_FIELD_NAMING_REASON,
    MSG_FIELD_PLANNED_TARGET,
    MSG_FIELD_PREVIEW_FILENAME,
    MSG_FIELD_REVIEW_REASON,
    MSG_NAMING_NOT_FINAL,
    MSG_PREVIEW_ONLY_BANNER,
    PREVIEW_ACTION_LABELS,
    STATUS_CHECKED_PREVIEW,
    STATUS_EXCLUDED_EXPORT,
    STATUS_IN_REVIEW,
    exclude_from_export_preview,
    get_review_preview_ui,
    keep_in_review,
    mark_checked_preview,
    reset_preview_selection,
    select_review_item,
)
from invoice_tool.ui_v2.review_state import (
    MSG_NO_FINAL_APPROVAL,
    ReviewFlowState,
    build_review_flow_state,
)
from invoice_tool.ui_v2.review_workflow import (
    DEFAULT_EVIDENCE_SUMMARY,
    DEFAULT_NEXT_ACTION_HINT,
    EMPTY_REVIEW_DETAIL,
    EMPTY_REVIEW_TITLE,
    MSG_BUCKETS_SEPARATED,
    MSG_REVIEW_FROM_REAL_RUN,
    MSG_REVIEW_NO_FILE_MUTATION,
    MSG_UNCLEAR_CASES_STAY_REVIEW,
    REVIEW_QUEUE_SUBTITLE,
    ReviewItemViewModel,
    ReviewQueueViewModel,
    build_review_item_view_model,
    build_review_queue_view_model,
)
from invoice_tool.ui_v2.configuration_rule_draft import (
    ACTION_CREATE_FROM_GUIDANCE,
    ACTION_EDIT_EXISTING,
    ACTION_MANUAL_KEEP_UNCLEAR,
    MSG_FIELD_CONFIGURATION_RULE_DRAFT_AVAILABLE,
    MSG_FIELD_DRAFT_WARNING,
    MSG_FIELD_PROPOSED_CONDITION,
    MSG_FIELD_PROPOSED_CONFIGURATION_NAME,
    MSG_FIELD_PROPOSED_FILENAME_PATTERN,
    MSG_FIELD_REQUIRES_USER_CONFIRMATION,
    attach_configuration_rule_draft_report_fields,
    coverage_gap_actions_available,
    draft_from_coverage_guidance,
)
from invoice_tool.ui_v2.configuration_rule_apply_preview import (
    MSG_APPLY_PREVIEW_ONLY,
    MSG_NO_FINAL_PROCESSING,
    MSG_ORIGINALS_UNCHANGED,
    MSG_PREVIEW_RECOMPUTED,
    MSG_RULE_SAVED,
    PREVIEW_RERUN_ACTION_LABELS,
    build_configuration_rule_apply_panel,
    preview_rerun_action_labels,
)
from invoice_tool.ui_v2.configuration_rule_editor import (
    ACTION_FINALIZATION_DRY_RUN,
    ACTION_PAYPAL_SMOKE_SAVE_AND_RERUN,
    ACTION_SANDBOX_FINAL_WRITE,
    ACTION_SAVE_AND_RERUN,
    ACTION_SAVE_DRAFT,
    build_configuration_coverage_action_row,
    build_configuration_rule_action_labels,
    build_configuration_rule_draft_panel,
    build_duplicate_config_remediation_panel,
)
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_COPY_CASE,
    ACTION_COPY_DIAGNOSIS,
    ACTION_COPY_FILENAME,
    ACTION_COPY_ORACLE,
    ACTION_DETAILS_CLOSE,
    ACTION_DETAILS_OPEN,
    ACTION_OPEN_WORKSPACE,
    DETAIL_PANEL_DISTINCT_BACKGROUND,
    FILENAME_FIELD_POLISH_MARKER,
    INLINE_DETAIL_UNDER_SELECTED_CARD,
    LABEL_DATEINAME_BEARBEITEN,
    LABEL_REVIEW_AMOUNT,
    LABEL_REVIEW_DATE,
    LABEL_REVIEW_DOC_NAME,
    LABEL_VORSCHAU_DATEINAME,
    MSG_FILENAME_PREVIEW_HELPER,
    MSG_FILENAME_PREVIEW_ONLY,
    MSG_FINAL_WRITE_USER_ANSWER,
    MSG_NO_READY_CASES,
    MSG_NO_REVIEW_CASES,
    MSG_ORACLE_AVAILABLE,
    MSG_ORACLE_NO_AUTO_RUN,
    MSG_SAFETY_LINE_NO_FINAL,
    MSG_USER_REVIEW_SUBTITLE,
    ORACLE_COMMAND,
    PRIMARY_PRUEFEN,
    REVIEW_ACCORDION_LAYOUT_MARKER,
    REVIEW_CARD_ACTIVE_HIGHLIGHT,
    REVIEW_CARD_COLLAPSED_SUMMARY_ONLY,
    REVIEW_DECLUTTER_LAYOUT_MARKER,
    REVIEW_SECTION_TITLES,
    REVIEW_UI_POLISH_LAYOUT_MARKER,
    REVIEW_USER_MODE_LAYOUT_MARKER,
    SECTION_BEREIT,
    SECTION_DATEINAME,
    SECTION_ENTSCHEIDEN,
    SECTION_ERKANNT,
    SECTION_FINALISIERUNG,
    SECTION_FINAL_WRITE_Q,
    SECTION_KURZPRUEFUNG,
    SECTION_NAECHSTE,
    SECTION_PRUEFUNG,
    SECTION_TECHNISCHE,
    SECTION_UNKLAR,
    SECTION_VORSCHLAG,
    SECTION_WARUM,
    SMOKE_DEV_UI_LAYOUT_MARKER,
    USER_REVIEW_SECTION_TITLES,
    build_diagnosis_copy_text,
    build_oracle_command_copy_text,
    build_prueffall_copy_text,
    copy_text_to_state_and_clipboard,
    derive_decision_prompt,
    derive_primary_list_action,
    derive_recognized_fields,
    derive_status_badges,
    derive_why_review_plain_german,
    filename_has_er_er,
    next_action_labels_for_detail,
    payment_display_label,
    paypal_action_relevant,
    split_ready_and_review_cases,
)

# Accordion open-state lives on the in-memory review_preview_ui bag (UI-only).
_OPEN_REVIEW_ITEM_ATTR = "open_review_item_id"

# Legacy preview artifacts only — not the current Track-B filename pattern.
MSG_LEGACY_ER_ER_NOTE = "Altes technisches Muster aus früherem Preview-Export."
# Compatibility alias for declutter tests / imports that still look for MSG_ER_ER_NOTE.
MSG_ER_ER_NOTE = MSG_LEGACY_ER_ER_NOTE


def get_open_review_item_id(state: UiV2State) -> str | None:
    """Return the currently expanded accordion item key (UI-only)."""

    bag = get_review_preview_ui(state)
    raw = getattr(bag, _OPEN_REVIEW_ITEM_ATTR, None)
    if raw is None:
        return None
    cleaned = str(raw).strip()
    return cleaned or None


def set_open_review_item_id(state: UiV2State, item_key: str | None) -> None:
    """Open one review item (single-open accordion) or close all when None."""

    bag = get_review_preview_ui(state)
    cleaned = (item_key or "").strip() or None
    setattr(bag, _OPEN_REVIEW_ITEM_ATTR, cleaned)
    if cleaned:
        select_review_item(state, cleaned)


def toggle_review_item_details(state: UiV2State, item_key: str) -> None:
    """Toggle details for one card; opening another closes the previous."""

    key = (item_key or "").strip()
    if not key:
        return
    current = get_open_review_item_id(state)
    if current == key:
        set_open_review_item_id(state, None)
    else:
        set_open_review_item_id(state, key)


def review_summary_display_name(row: ReviewListItemVM | Any) -> str:
    """Prefer Lieferant/Name, else original filename."""

    supplier = str(getattr(row, "supplier", None) or "").strip()
    if supplier and supplier != "—":
        return supplier
    source = str(getattr(row, "source_filename", None) or "").strip()
    return source or "Dokument"


def review_section(
    title: str,
    content: ft.Control,
    *,
    subtitle: str | None = None,
) -> ft.Container:
    """Visually separated review detail section (card + spacing)."""

    header: list[ft.Control] = [
        ft.Text(
            title,
            size=FONT_SIZE_SECTION_TITLE,
            weight=ft.FontWeight.W_700,
            color=COLOR_TEXT_PRIMARY,
        )
    ]
    if subtitle:
        header.append(
            ft.Text(subtitle, size=FONT_SIZE_HELPER, color=COLOR_TEXT_MUTED)
        )
    return ft.Container(
        margin=ft.Margin.only(top=SPACE_MD, bottom=SPACE_SM),
        padding=SPACE_LG,
        bgcolor=COLOR_SURFACE_ALT,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        content=ft.Column(
            [*header, content],
            spacing=SPACE_SM,
            tight=True,
        ),
        data=REVIEW_UI_POLISH_LAYOUT_MARKER,
    )


def review_card(title: str, content: ft.Control, *, subtitle: str | None = None) -> ft.Control:
    """Alias for :func:`review_section` — clearer product-preview cards."""

    return review_section(title, content, subtitle=subtitle)


def section_divider() -> ft.Control:
    """Subtle horizontal separator between review sections."""

    return ft.Container(
        height=1,
        bgcolor=COLOR_BORDER,
        margin=ft.Margin.symmetric(vertical=SPACE_XS),
    )


def er_er_note_for_filename(name: str | None) -> str | None:
    """Return a legacy-artifact note when ``_er_er_`` appears; else None."""

    if filename_has_er_er(name):
        return MSG_LEGACY_ER_ER_NOTE
    return None
from invoice_tool.ui_v2.review_decision import (
    ACTION_ACCEPT_SUGGESTION,
    ACTION_DEFER,
    ACTION_EDIT_SUGGESTION,
    ACTION_IGNORE_EXPORT,
    ACTION_KEEP_UNCLEAR,
    ACTION_NEEDS_CONFIGURATION,
    DECISION_ACTION_LABELS,
    MSG_FINALIZATION_READY_NO,
    MSG_FINALIZATION_READY_YES,
    MSG_NOT_FINAL_YET,
    arm_accept_confirmation,
    create_accept_suggestion_decision,
    create_defer_decision,
    create_edit_suggestion_decision,
    create_ignore_for_export_decision,
    create_keep_review_required_decision,
    create_needs_configuration_change_decision,
    get_review_decision_bag,
    set_edit_filename_draft,
)
from invoice_tool.ui_v2.controlled_final_write_sandbox import (
    MSG_CTA_CONTROLLED_ONLY,
    MSG_CTA_ORIGINALS_UNCHANGED,
    MSG_CTA_SANDBOX_WRITE,
    MSG_TITLE as MSG_SANDBOX_FINAL_WRITE_TITLE,
    apply_controlled_final_write_sandbox,
    get_controlled_final_write_sandbox_bag,
    sandbox_final_write_summary_lines,
)
from invoice_tool.ui_v2.finalization_dry_run_package import (
    MSG_CTA_CHECK_ONLY,
    MSG_CTA_CREATE_AUDIT,
    MSG_CTA_CREATE_DRY_RUN,
    MSG_DRY_RUN_TITLE,
    MSG_FINAL_WRITE_FALSE,
    apply_finalization_dry_run_package,
    dry_run_package_summary_lines,
    get_finalization_dry_run_package_bag,
)
from invoice_tool.ui_v2.finalization_preview_batch import (
    MSG_BATCH_BLOCKED,
    MSG_BATCH_DEFERRED,
    MSG_BATCH_IGNORED,
    MSG_BATCH_NO_FINAL_WRITE,
    MSG_BATCH_READY,
    MSG_BATCH_STILL_REVIEW,
    MSG_BATCH_TITLE,
    batch_summary_lines,
    build_finalization_preview_batch,
)
from invoice_tool.ui_v2.state import UiV2State

# Re-exports used by existing tests / callers.
__all__ = (
    "DEFAULT_EVIDENCE_SUMMARY",
    "DEFAULT_NEXT_ACTION_HINT",
    "EMPTY_REVIEW_DETAIL",
    "EMPTY_REVIEW_TITLE",
    "MSG_REVIEW_FROM_REAL_RUN",
    "MSG_REVIEW_NO_FILE_MUTATION",
    "REVIEW_QUEUE_SUBTITLE",
    "ReviewDetailItemVM",
    "ReviewListItemVM",
    "ReviewPageVM",
    "ReviewSelectedDetailVM",
    "build_review_page",
    "build_review_page_vm",
    "review_detail_from_item",
)


@dataclass(frozen=True)
class ReviewDetailItemVM:
    """Compatibility detail VM — mirrors ReviewItemViewModel fields used by tests."""

    document_label: str
    document_id: str
    reason: str
    suggested_status: str
    evidence_summary: str
    next_action_hint: str
    source_run_id: str | None = None
    severity: str | None = None
    item_key: str = ""
    source_filename: str = ""
    category: str = MSG_CATEGORY_REVIEW
    planned_action: str | None = None
    planned_destination: str | None = None
    preview_only_badge: str = MSG_BADGE_PREVIEW
    no_final_write_badge: str = MSG_BADGE_NO_FINAL_WRITE
    productive_blocked_badge: str = MSG_BADGE_PRODUCTIVE_BLOCKED
    suggested_filename: str | None = None
    naming_confidence: str | None = None
    naming_reason: str | None = None
    filename_source: str | None = None
    supplier: str | None = None
    invoice_date: str | None = None
    amount: str | None = None
    document_type: str | None = None
    payment_account: str | None = None
    canonical_filename: str | None = None
    filename_template_version: str | None = None
    document_direction: str | None = None
    business_category: str | None = None
    business_category_display: str | None = None
    counterparty_name: str | None = None
    missing_fields: tuple[str, ...] = ()
    matched_configuration_name: str | None = None
    matched_configuration_id: str | None = None
    matched_configuration_pattern: str | None = None
    matched_configuration_reason: str | None = None
    matched_configuration_confidence: str | None = None
    filename_pattern: str | None = None
    rendered_filename: str | None = None
    placeholder_values: tuple[tuple[str, str | None], ...] = ()
    missing_placeholders: tuple[str, ...] = ()
    amount_format: str | None = None
    amount_candidates: tuple[dict[str, object], ...] = ()
    selected_amount: str | None = None
    selected_amount_reason: str | None = None
    rejected_amount_candidates: tuple[dict[str, object], ...] = ()
    payment_field_candidates: tuple[dict[str, object], ...] = ()
    selected_payment_field: str | None = None
    selected_payment_field_reason: str | None = None
    document_art_candidates: tuple[dict[str, object], ...] = ()
    selected_art: str | None = None
    selected_art_reason: str | None = None
    art_ambiguity: bool = False
    available_configurations: tuple[dict[str, object], ...] = ()
    evaluated_configuration_candidates: tuple[dict[str, object], ...] = ()
    unmatched_reasons: tuple[str, ...] = ()
    condition_results: tuple[dict[str, object], ...] = ()
    alternative_matches: tuple[dict[str, object], ...] = ()
    missing_configuration_rule: str | None = None
    configuration_coverage_status: str | None = None
    missing_configuration_type: str | None = None
    user_guidance: str | None = None
    suggested_configuration_action: str | None = None
    guidance_severity: str | None = None
    configuration_rule_draft_available: bool = False
    proposed_configuration_name: str | None = None
    proposed_condition: str | None = None
    proposed_filename_pattern: str | None = None
    configuration_rule_draft_warning: str | None = None
    requires_user_confirmation: bool = True
    configuration_coverage_action_labels: tuple[str, ...] = ()
    rule_applied: bool = False
    applied_configuration_name: str | None = None
    applied_configuration_condition: str | None = None
    rerun_preview_after_rule_change: bool = False
    matched_after_rule_change: bool = False
    previous_matched_configuration: str | None = None
    new_matched_configuration: str | None = None


@dataclass(frozen=True)
class ReviewListItemVM:
    """Visible Review-bucket list row (Prompt 15/34 + declutter cards)."""

    item_key: str
    source_filename: str
    category: str
    reason: str
    planned_action: str | None
    planned_destination: str | None
    confidence_or_status: str
    preview_only_badge: str
    no_final_write_badge: str
    productive_blocked_badge: str
    selected: bool = False
    checked_preview: bool = False
    excluded_from_export_preview: bool = False
    preview_status_label: str = STATUS_IN_REVIEW
    # Declutter compact card fields
    supplier: str | None = None
    invoice_date: str | None = None
    amount: str | None = None
    payment_field: str | None = None
    document_art: str | None = None
    configuration: str | None = None
    status_badges: tuple[str, ...] = ()
    suggested_filename: str | None = None
    primary_action: str = PRIMARY_PRUEFEN
    safety_line: str = MSG_SAFETY_LINE_NO_FINAL
    compact_card: bool = True
    # Accordion summary card (collapsed overview)
    summary_display_name: str | None = None
    details_open: bool = False
    collapsed_summary_only: bool = True
    details_action_label: str = ACTION_DETAILS_OPEN
    accordion_active: bool = False


@dataclass(frozen=True)
class ReviewSelectedDetailVM:
    """Detail panel for a selected Review item — preview-only."""

    item_key: str
    source_filename: str
    review_reason: str
    planned_target: str | None
    planned_action: str | None
    safety_status: str
    export_preview_status: str
    no_productive_processing_status: str
    preview_only_banner: str
    empty_output_explanation: str
    category: str = MSG_CATEGORY_REVIEW
    confidence_or_status: str = STATUS_IN_REVIEW
    originals_unchanged: str = MSG_BADGE_ORIGINALS_UNCHANGED
    preview_filename: str | None = None
    naming_reason: str | None = None
    naming_not_final: str = MSG_NAMING_NOT_FINAL
    suggested_filename: str | None = None
    naming_confidence: str | None = None
    filename_source: str | None = None
    supplier: str | None = None
    invoice_date: str | None = None
    amount: str | None = None
    document_type: str | None = None
    payment_account: str | None = None
    canonical_filename: str | None = None
    filename_template_version: str | None = None
    document_direction: str | None = None
    business_category: str | None = None
    business_category_display: str | None = None
    counterparty_name: str | None = None
    missing_fields: tuple[str, ...] = ()
    matched_configuration_name: str | None = None
    matched_configuration_id: str | None = None
    matched_configuration_pattern: str | None = None
    matched_configuration_reason: str | None = None
    matched_configuration_confidence: str | None = None
    filename_pattern: str | None = None
    rendered_filename: str | None = None
    placeholder_values: tuple[tuple[str, str | None], ...] = ()
    missing_placeholders: tuple[str, ...] = ()
    amount_format: str | None = None
    amount_candidates: tuple[dict[str, object], ...] = ()
    selected_amount: str | None = None
    selected_amount_reason: str | None = None
    rejected_amount_candidates: tuple[dict[str, object], ...] = ()
    payment_field_candidates: tuple[dict[str, object], ...] = ()
    selected_payment_field: str | None = None
    selected_payment_field_reason: str | None = None
    document_art_candidates: tuple[dict[str, object], ...] = ()
    selected_art: str | None = None
    selected_art_reason: str | None = None
    art_ambiguity: bool = False
    available_configurations: tuple[dict[str, object], ...] = ()
    evaluated_configuration_candidates: tuple[dict[str, object], ...] = ()
    unmatched_reasons: tuple[str, ...] = ()
    condition_results: tuple[dict[str, object], ...] = ()
    alternative_matches: tuple[dict[str, object], ...] = ()
    missing_configuration_rule: str | None = None
    configuration_coverage_status: str | None = None
    missing_configuration_type: str | None = None
    user_guidance: str | None = None
    suggested_configuration_action: str | None = None
    guidance_severity: str | None = None
    configuration_rule_draft_available: bool = False
    proposed_configuration_name: str | None = None
    proposed_condition: str | None = None
    proposed_filename_pattern: str | None = None
    configuration_rule_draft_warning: str | None = None
    requires_user_confirmation: bool = True
    configuration_coverage_action_labels: tuple[str, ...] = ()
    rule_applied: bool = False
    applied_configuration_name: str | None = None
    applied_configuration_condition: str | None = None
    rerun_preview_after_rule_change: bool = False
    matched_after_rule_change: bool = False
    previous_matched_configuration: str | None = None
    new_matched_configuration: str | None = None
    # Prompt 29/34 — review decision / readiness display.
    review_decision: str | None = None
    decision_timestamp: str | None = None
    approved_preview_filename: str | None = None
    finalization_ready: bool = False
    finalization_blockers: tuple[str, ...] = ()
    readiness_warnings: tuple[str, ...] = ()
    final_write_allowed: bool = False
    not_final_yet_text: str = MSG_NOT_FINAL_YET
    decision_feedback: str | None = None
    # Declutter / simple user-review detail sections
    status_badges: tuple[str, ...] = ()
    why_review_plain: tuple[str, ...] = ()
    next_action_labels_relevant: tuple[str, ...] = ()
    paypal_action_visible: bool = False
    er_er_note: str | None = None
    safety_line_declutter: str = MSG_SAFETY_LINE_NO_FINAL
    section_titles: tuple[str, ...] = USER_REVIEW_SECTION_TITLES
    technical_details_collapsed_by_default: bool = True
    kurzpruefung_fields: tuple[tuple[str, str], ...] = ()
    vorschlag_fields: tuple[tuple[str, str], ...] = ()
    finalization_summary_lines: tuple[str, ...] = ()
    # Simple user review mode (primary surface)
    recognized_fields: tuple[tuple[str, str], ...] = ()
    unclear_items: tuple[str, ...] = ()
    decision_prompt: str = ""
    final_write_user_answer: str = MSG_FINAL_WRITE_USER_ANSWER
    user_mode_enabled: bool = True


@dataclass(frozen=True)
class ReviewPageVM:
    """View-model for the Track-B review page — testable without a GUI window."""

    title: str
    subtitle: str
    empty: bool
    empty_title: str | None
    empty_detail: str | None
    items: tuple[ProcessingReviewItem, ...]
    detail_items: tuple[ReviewDetailItemVM, ...]
    honest_copy: tuple[str, ...]
    mutates_files: bool
    # Errors/results stay on the workspace shell — never mixed into the review queue.
    error_count: int = 0
    result_count: int = 0
    review_count: int = 0
    separation_notes: tuple[str, ...] = ()
    actions_disabled: bool = True
    action_labels: tuple[str, ...] = ()
    source_run_id: str | None = None
    planned_preview_lines: tuple[str, ...] = ()
    error_section_lines: tuple[str, ...] = ()
    safety_line: str | None = None
    productive_actions_exposed: bool = False
    # Prompt 5/34 — light Export-Vorschau summary (no final action).
    export_preview_title: str = MSG_EXPORT_PREVIEW_TITLE
    export_preview_summary: str | None = None
    export_preview_only: bool = True
    final_actions_blocked: bool = True
    # Prompt 15/34 — list / selection / preview actions.
    list_items: tuple[ReviewListItemVM, ...] = ()
    selected_item_key: str | None = None
    selected_detail: ReviewSelectedDetailVM | None = None
    preview_action_labels: tuple[str, ...] = PREVIEW_ACTION_LABELS
    preview_actions_enabled: bool = True
    preview_only_banner: str = MSG_PREVIEW_ONLY_BANNER
    empty_output_explanation: str = MSG_EMPTY_OUTPUT_EXPLAIN
    configuration_coverage_action_labels: tuple[str, ...] = ()
    configuration_rule_draft_available: bool = False
    preview_rerun_action_labels: tuple[str, ...] = PREVIEW_RERUN_ACTION_LABELS
    configuration_rule_apply_available: bool = False
    decision_action_labels: tuple[str, ...] = DECISION_ACTION_LABELS
    not_final_yet_text: str = MSG_NOT_FINAL_YET
    decision_feedback: str = ""
    decision_feedback_error: bool = False
    # Prompt 30/34 — Finalization preview batch summary (no final write).
    finalization_preview_batch_title: str = MSG_BATCH_TITLE
    finalization_preview_batch_ready_count: int = 0
    finalization_preview_batch_blocked_count: int = 0
    finalization_preview_batch_ignored_count: int = 0
    finalization_preview_batch_deferred_count: int = 0
    finalization_preview_batch_still_review_required_count: int = 0
    finalization_preview_batch_summary_lines: tuple[str, ...] = ()
    finalization_preview_batch_no_final_write_text: str = MSG_BATCH_NO_FINAL_WRITE
    # Prompt 31/34 — Finalization dry-run package / audit (no final write).
    finalization_dry_run_title: str = MSG_DRY_RUN_TITLE
    finalization_dry_run_cta_create: str = MSG_CTA_CREATE_DRY_RUN
    finalization_dry_run_cta_audit: str = MSG_CTA_CREATE_AUDIT
    finalization_dry_run_check_only: str = MSG_CTA_CHECK_ONLY
    finalization_dry_run_package_path: str = ""
    finalization_dry_run_feedback: str = ""
    finalization_dry_run_feedback_error: bool = False
    finalization_dry_run_summary_lines: tuple[str, ...] = ()
    # Prompt 33/34 — Controlled sandbox final write (not production).
    sandbox_final_write_title: str = MSG_SANDBOX_FINAL_WRITE_TITLE
    sandbox_final_write_cta: str = MSG_CTA_SANDBOX_WRITE
    sandbox_final_write_controlled_only: str = MSG_CTA_CONTROLLED_ONLY
    sandbox_final_write_originals_unchanged: str = MSG_CTA_ORIGINALS_UNCHANGED
    sandbox_final_write_result_path: str = ""
    sandbox_final_write_feedback: str = ""
    sandbox_final_write_feedback_error: bool = False
    sandbox_final_write_summary_lines: tuple[str, ...] = ()
    sandbox_final_write_written_count: int = 0
    sandbox_final_write_skipped_count: int = 0
    sandbox_final_write_blocked_count: int = 0
    sandbox_final_write_failure_count: int = 0
    calls_run_once: bool = False
    writes_final_files: bool = False
    mutates_input: bool = False
    touches_real_invoice_folders: bool = False
    claims_saas_ready: bool = False
    claims_production_ready: bool = False
    # Declutter / oracle / simple user-review surface
    declutter_layout_marker: str = REVIEW_DECLUTTER_LAYOUT_MARKER
    user_mode_layout_marker: str = REVIEW_USER_MODE_LAYOUT_MARKER
    ui_polish_layout_marker: str = REVIEW_UI_POLISH_LAYOUT_MARKER
    filename_field_polish_marker: str = FILENAME_FIELD_POLISH_MARKER
    accordion_layout_marker: str = REVIEW_ACCORDION_LAYOUT_MARKER
    collapsed_summary_marker: str = REVIEW_CARD_COLLAPSED_SUMMARY_ONLY
    active_card_highlight_marker: str = REVIEW_CARD_ACTIVE_HIGHLIGHT
    inline_detail_marker: str = INLINE_DETAIL_UNDER_SELECTED_CARD
    detail_panel_background_marker: str = DETAIL_PANEL_DISTINCT_BACKGROUND
    safety_line_declutter: str = MSG_SAFETY_LINE_NO_FINAL
    final_write_user_answer: str = MSG_FINAL_WRITE_USER_ANSWER
    oracle_available_title: str = MSG_ORACLE_AVAILABLE
    oracle_command: str = ORACLE_COMMAND
    oracle_no_auto_run: str = MSG_ORACLE_NO_AUTO_RUN
    technical_details_collapsed_by_default: bool = True
    section_titles: tuple[str, ...] = USER_REVIEW_SECTION_TITLES
    copy_action_labels: tuple[str, ...] = (
        ACTION_COPY_CASE,
        ACTION_COPY_DIAGNOSIS,
        ACTION_COPY_ORACLE,
        ACTION_COPY_FILENAME,
    )
    empty_state_workspace_action: str = ACTION_OPEN_WORKSPACE
    empty_state_oracle_action: str = ACTION_COPY_ORACLE
    auto_runs_oracle: bool = False
    production_final_write_enabled: bool = False
    user_mode_enabled: bool = True
    ready_case_summaries: tuple[str, ...] = ()
    review_case_summaries: tuple[str, ...] = ()
    cases_ready_count: int = 0
    cases_review_count: int = 0
    # Accordion: at most one open detail under its card
    open_review_item_id: str | None = None
    accordion_single_open: bool = True
    details_open_action_label: str = ACTION_DETAILS_OPEN
    details_close_action_label: str = ACTION_DETAILS_CLOSE


def _suggested_rule_draft_fields(
    *,
    configuration_coverage_status: str | None,
    missing_configuration_type: str | None,
    user_guidance: str | None,
    suggested_configuration_action: str | None,
    guidance_severity: str | None,
    selected_payment_field: str | None,
    payment_account: str | None,
    source_filename: str | None,
    source_review_item_id: str | None,
    matched_configuration_reason: str | None,
    missing_configuration_rule: str | None,
    unmatched_reasons: tuple[str, ...],
    available_configurations: tuple[dict[str, object], ...],
) -> dict[str, object]:
    """Attach suggested draft report fields for coverage gaps (unsaved)."""

    labels = build_configuration_rule_action_labels()
    if not coverage_gap_actions_available(
        configuration_coverage_status=configuration_coverage_status,
        missing_configuration_type=missing_configuration_type,
    ):
        return {
            "configuration_rule_draft_available": False,
            "proposed_configuration_name": None,
            "proposed_condition": None,
            "proposed_filename_pattern": None,
            "configuration_rule_draft_warning": None,
            "requires_user_confirmation": True,
            "configuration_coverage_action_labels": (),
        }
    draft = draft_from_coverage_guidance(
        selected_payment_field=selected_payment_field,
        payment_account=payment_account,
        source_review_item_id=source_review_item_id,
        source_filename=source_filename,
        matched_configuration_reason=matched_configuration_reason,
        missing_configuration_rule=missing_configuration_rule,
        unmatched_reasons=unmatched_reasons,
        available_configurations=available_configurations,
        guidance={
            "configuration_coverage_status": configuration_coverage_status,
            "missing_configuration_type": missing_configuration_type,
            "user_guidance": user_guidance,
            "suggested_configuration_action": suggested_configuration_action,
            "guidance_severity": guidance_severity or "warning",
        },
    )
    if draft is None:
        return {
            "configuration_rule_draft_available": False,
            "proposed_configuration_name": None,
            "proposed_condition": None,
            "proposed_filename_pattern": None,
            "configuration_rule_draft_warning": None,
            "requires_user_confirmation": True,
            "configuration_coverage_action_labels": labels,
        }
    report = attach_configuration_rule_draft_report_fields({}, draft)
    return {
        "configuration_rule_draft_available": bool(
            report.get(MSG_FIELD_CONFIGURATION_RULE_DRAFT_AVAILABLE)
        ),
        "proposed_configuration_name": report.get(
            MSG_FIELD_PROPOSED_CONFIGURATION_NAME
        ),
        "proposed_condition": report.get(MSG_FIELD_PROPOSED_CONDITION),
        "proposed_filename_pattern": report.get(MSG_FIELD_PROPOSED_FILENAME_PATTERN),
        "configuration_rule_draft_warning": report.get(MSG_FIELD_DRAFT_WARNING),
        "requires_user_confirmation": bool(
            report.get(MSG_FIELD_REQUIRES_USER_CONFIRMATION, True)
        ),
        "configuration_coverage_action_labels": labels,
    }


def _detail_from_item_vm(item: ReviewItemViewModel) -> ReviewDetailItemVM:
    draft_fields = _suggested_rule_draft_fields(
        configuration_coverage_status=item.configuration_coverage_status,
        missing_configuration_type=item.missing_configuration_type,
        user_guidance=item.user_guidance,
        suggested_configuration_action=item.suggested_configuration_action,
        guidance_severity=item.guidance_severity,
        selected_payment_field=item.selected_payment_field,
        payment_account=item.payment_account,
        source_filename=item.source_filename or item.document_label,
        source_review_item_id=item.item_key or item.document_id,
        matched_configuration_reason=item.matched_configuration_reason,
        missing_configuration_rule=item.missing_configuration_rule,
        unmatched_reasons=tuple(item.unmatched_reasons or ()),
        available_configurations=tuple(item.available_configurations or ()),
    )
    return ReviewDetailItemVM(
        document_label=item.document_label,
        document_id=item.document_id,
        reason=item.reason,
        suggested_status=item.suggested_status,
        evidence_summary=item.evidence_summary,
        next_action_hint=item.next_action_hint,
        source_run_id=item.source_run_id,
        severity=item.severity,
        item_key=item.item_key,
        source_filename=item.source_filename or item.document_label,
        category=item.category,
        planned_action=item.planned_action,
        planned_destination=item.planned_destination,
        preview_only_badge=item.preview_only_badge,
        no_final_write_badge=item.no_final_write_badge,
        productive_blocked_badge=item.productive_blocked_badge,
        suggested_filename=item.suggested_filename,
        naming_confidence=item.naming_confidence,
        naming_reason=item.naming_reason,
        filename_source=item.filename_source,
        supplier=item.supplier,
        invoice_date=item.invoice_date,
        amount=item.amount,
        document_type=item.document_type,
        payment_account=item.payment_account,
        canonical_filename=item.canonical_filename,
        filename_template_version=item.filename_template_version,
        document_direction=item.document_direction,
        business_category=item.business_category,
        business_category_display=item.business_category_display,
        counterparty_name=item.counterparty_name,
        missing_fields=tuple(item.missing_fields or ()),
        matched_configuration_name=item.matched_configuration_name,
        matched_configuration_id=item.matched_configuration_id,
        matched_configuration_pattern=item.matched_configuration_pattern,
        matched_configuration_reason=item.matched_configuration_reason,
        matched_configuration_confidence=item.matched_configuration_confidence,
        filename_pattern=item.filename_pattern,
        rendered_filename=item.rendered_filename,
        placeholder_values=tuple(item.placeholder_values or ()),
        missing_placeholders=tuple(item.missing_placeholders or ()),
        amount_format=item.amount_format,
        amount_candidates=tuple(item.amount_candidates or ()),
        selected_amount=item.selected_amount,
        selected_amount_reason=item.selected_amount_reason,
        rejected_amount_candidates=tuple(item.rejected_amount_candidates or ()),
        payment_field_candidates=tuple(item.payment_field_candidates or ()),
        selected_payment_field=item.selected_payment_field,
        selected_payment_field_reason=item.selected_payment_field_reason,
        document_art_candidates=tuple(item.document_art_candidates or ()),
        selected_art=item.selected_art,
        selected_art_reason=item.selected_art_reason,
        art_ambiguity=bool(item.art_ambiguity),
        available_configurations=tuple(item.available_configurations or ()),
        evaluated_configuration_candidates=tuple(
            item.evaluated_configuration_candidates or ()
        ),
        unmatched_reasons=tuple(item.unmatched_reasons or ()),
        condition_results=tuple(item.condition_results or ()),
        alternative_matches=tuple(item.alternative_matches or ()),
        missing_configuration_rule=item.missing_configuration_rule,
        configuration_coverage_status=item.configuration_coverage_status,
        missing_configuration_type=item.missing_configuration_type,
        user_guidance=item.user_guidance,
        suggested_configuration_action=item.suggested_configuration_action,
        guidance_severity=item.guidance_severity,
        configuration_rule_draft_available=bool(
            draft_fields["configuration_rule_draft_available"]
        ),
        proposed_configuration_name=(
            str(draft_fields["proposed_configuration_name"])
            if draft_fields["proposed_configuration_name"]
            else None
        ),
        proposed_condition=(
            str(draft_fields["proposed_condition"])
            if draft_fields["proposed_condition"]
            else None
        ),
        proposed_filename_pattern=(
            str(draft_fields["proposed_filename_pattern"])
            if draft_fields["proposed_filename_pattern"]
            else None
        ),
        configuration_rule_draft_warning=(
            str(draft_fields["configuration_rule_draft_warning"])
            if draft_fields["configuration_rule_draft_warning"]
            else None
        ),
        requires_user_confirmation=bool(
            draft_fields["requires_user_confirmation"]
        ),
        configuration_coverage_action_labels=tuple(
            draft_fields["configuration_coverage_action_labels"] or ()
        ),
        rule_applied=bool(item.rule_applied),
        applied_configuration_name=item.applied_configuration_name,
        applied_configuration_condition=item.applied_configuration_condition,
        rerun_preview_after_rule_change=bool(
            item.rerun_preview_after_rule_change
        ),
        matched_after_rule_change=bool(item.matched_after_rule_change),
        previous_matched_configuration=item.previous_matched_configuration,
        new_matched_configuration=item.new_matched_configuration,
    )


def review_detail_from_item(item: ProcessingReviewItem) -> ReviewDetailItemVM:
    """Map a provided review item into the detail shell — never invent private rows."""

    return _detail_from_item_vm(build_review_item_view_model(item))


def _preview_status_label(
    *,
    checked: bool,
    excluded: bool,
) -> str:
    if excluded:
        return STATUS_EXCLUDED_EXPORT
    if checked:
        return STATUS_CHECKED_PREVIEW
    return STATUS_IN_REVIEW


def _document_art_label(detail: ReviewDetailItemVM | ReviewSelectedDetailVM) -> str:
    art = str(
        getattr(detail, "selected_art", None)
        or getattr(detail, "document_type", None)
        or ""
    ).strip()
    if art.casefold() == "storno":
        return "Storno"
    if art:
        return "Rechnung" if art.casefold() in {"er", "rechnung", "invoice"} else art
    return "Rechnung"


def _build_list_items(
    detail_items: tuple[ReviewDetailItemVM, ...],
    *,
    selected_key: str | None,
    checked_keys: set[str],
    excluded_keys: set[str],
    readiness_by_key: dict[str, Any] | None = None,
    open_key: str | None = None,
) -> tuple[ReviewListItemVM, ...]:
    rows: list[ReviewListItemVM] = []
    readiness_by_key = readiness_by_key or {}
    for detail in detail_items:
        key = detail.item_key or detail.document_id or detail.document_label
        checked = key in checked_keys
        excluded = key in excluded_keys
        readiness = readiness_by_key.get(key)
        finalization_ready = bool(getattr(readiness, "ready", False))
        blockers = tuple(getattr(readiness, "blockers", ()) or ())
        badges = derive_status_badges(
            detail,
            finalization_ready=finalization_ready,
            finalization_blockers=blockers,
        )
        suggested = (
            detail.suggested_filename
            or detail.rendered_filename
            or detail.canonical_filename
        )
        supplier = detail.counterparty_name or detail.supplier
        source_filename = detail.source_filename or detail.document_label
        summary_name = str(supplier or source_filename or "Dokument").strip()
        is_open = bool(open_key and key == open_key)
        rows.append(
            ReviewListItemVM(
                item_key=key,
                source_filename=source_filename,
                category=detail.category or MSG_CATEGORY_REVIEW,
                reason=detail.reason,
                planned_action=detail.planned_action,
                planned_destination=detail.planned_destination,
                confidence_or_status=detail.suggested_status,
                preview_only_badge=detail.preview_only_badge,
                no_final_write_badge=detail.no_final_write_badge,
                productive_blocked_badge=detail.productive_blocked_badge,
                selected=bool(selected_key and key == selected_key) or is_open,
                checked_preview=checked,
                excluded_from_export_preview=excluded,
                preview_status_label=_preview_status_label(
                    checked=checked, excluded=excluded
                ),
                supplier=supplier,
                invoice_date=detail.invoice_date,
                amount=detail.selected_amount or detail.amount,
                payment_field=payment_display_label(detail),
                document_art=_document_art_label(detail),
                configuration=detail.matched_configuration_name or "Unklar",
                status_badges=badges,
                suggested_filename=suggested,
                primary_action=derive_primary_list_action(
                    detail, finalization_ready=finalization_ready
                ),
                safety_line=MSG_SAFETY_LINE_NO_FINAL,
                compact_card=True,
                summary_display_name=summary_name,
                details_open=is_open,
                collapsed_summary_only=not is_open,
                details_action_label=(
                    ACTION_DETAILS_CLOSE if is_open else ACTION_DETAILS_OPEN
                ),
                accordion_active=is_open,
            )
        )
    return tuple(rows)


def _build_selected_detail(
    detail: ReviewDetailItemVM,
    *,
    safety_line: str | None,
    export_preview_summary: str | None,
    excluded: bool,
    checked: bool,
    review_decision: str | None = None,
    decision_timestamp: str | None = None,
    approved_preview_filename: str | None = None,
    finalization_ready: bool = False,
    finalization_blockers: tuple[str, ...] = (),
    readiness_warnings: tuple[str, ...] = (),
    decision_feedback: str | None = None,
) -> ReviewSelectedDetailVM:
    export_status = MSG_EXPORT_PREVIEW_TITLE
    if excluded:
        export_status = f"{MSG_EXPORT_PREVIEW_TITLE}: {STATUS_EXCLUDED_EXPORT}"
    elif checked:
        export_status = f"{MSG_EXPORT_PREVIEW_TITLE}: {STATUS_CHECKED_PREVIEW}"
    elif export_preview_summary:
        export_status = export_preview_summary
    safety = safety_line or (
        f"{MSG_BADGE_ORIGINALS_UNCHANGED} · {MSG_BADGE_PRODUCTIVE_BLOCKED} · "
        f"{MSG_BADGE_PREVIEW}"
    )
    planned_target = detail.planned_destination
    if detail.planned_action and planned_target:
        planned_target = f"{detail.planned_action}: {planned_target}"
    elif detail.planned_action and not planned_target:
        planned_target = detail.planned_action
    planned_for_naming = None
    if detail.planned_destination or detail.suggested_filename:
        planned_for_naming = ProcessingPlannedDestination(
            document_name=detail.source_filename or detail.document_label,
            planned_path=detail.planned_destination
            or detail.suggested_filename
            or detail.source_filename
            or detail.document_label,
            destination_label=detail.planned_action,
            preview_only=True,
            applied=False,
            suggested_filename=detail.suggested_filename,
            filename_source=detail.filename_source,
            naming_confidence=detail.naming_confidence,
            naming_reason=detail.naming_reason,
            supplier=detail.supplier,
            invoice_date=detail.invoice_date,
            amount=detail.amount,
            document_type=detail.document_type,
            payment_account=detail.payment_account,
            canonical_filename=detail.canonical_filename,
            filename_template_version=detail.filename_template_version,
            document_direction=detail.document_direction,
            business_category=detail.business_category,
            business_category_display=detail.business_category_display,
            counterparty_name=detail.counterparty_name,
            missing_fields=tuple(detail.missing_fields or ()),
            matched_configuration_name=detail.matched_configuration_name,
            matched_configuration_id=detail.matched_configuration_id,
            matched_configuration_pattern=detail.matched_configuration_pattern,
            matched_configuration_reason=detail.matched_configuration_reason,
            matched_configuration_confidence=detail.matched_configuration_confidence,
            filename_pattern=detail.filename_pattern,
            rendered_filename=detail.rendered_filename,
            placeholder_values=tuple(detail.placeholder_values or ()),
            missing_placeholders=tuple(detail.missing_placeholders or ()),
            amount_format=detail.amount_format,
            amount_candidates=tuple(detail.amount_candidates or ()),
            selected_amount=detail.selected_amount,
            selected_amount_reason=detail.selected_amount_reason,
            rejected_amount_candidates=tuple(detail.rejected_amount_candidates or ()),
            payment_field_candidates=tuple(detail.payment_field_candidates or ()),
            selected_payment_field=detail.selected_payment_field,
            selected_payment_field_reason=detail.selected_payment_field_reason,
            document_art_candidates=tuple(detail.document_art_candidates or ()),
            selected_art=detail.selected_art,
            selected_art_reason=detail.selected_art_reason,
            art_ambiguity=bool(detail.art_ambiguity),
            available_configurations=tuple(detail.available_configurations or ()),
            evaluated_configuration_candidates=tuple(
                detail.evaluated_configuration_candidates or ()
            ),
            unmatched_reasons=tuple(detail.unmatched_reasons or ()),
            condition_results=tuple(detail.condition_results or ()),
            alternative_matches=tuple(detail.alternative_matches or ()),
            missing_configuration_rule=detail.missing_configuration_rule,
            configuration_coverage_status=detail.configuration_coverage_status,
            missing_configuration_type=detail.missing_configuration_type,
            user_guidance=detail.user_guidance,
            suggested_configuration_action=detail.suggested_configuration_action,
            guidance_severity=detail.guidance_severity,
        )
    naming = resolve_preview_naming(
        source_filename=detail.source_filename or detail.document_label,
        review_required=True,
        planned=planned_for_naming,
        suggested_filename=detail.suggested_filename
        or detail.rendered_filename
        or detail.canonical_filename,
    )
    return ReviewSelectedDetailVM(
        item_key=detail.item_key or detail.document_id,
        source_filename=detail.source_filename or detail.document_label,
        review_reason=detail.reason,
        planned_target=planned_target,
        planned_action=detail.planned_action,
        safety_status=safety,
        export_preview_status=export_status,
        no_productive_processing_status=MSG_BADGE_PRODUCTIVE_BLOCKED,
        preview_only_banner=MSG_PREVIEW_ONLY_BANNER,
        empty_output_explanation=MSG_EMPTY_OUTPUT_EXPLAIN,
        category=detail.category or MSG_CATEGORY_REVIEW,
        confidence_or_status=_preview_status_label(checked=checked, excluded=excluded),
        originals_unchanged=MSG_BADGE_ORIGINALS_UNCHANGED,
        preview_filename=naming.preview_filename,
        naming_reason=naming.naming_reason or detail.naming_reason,
        naming_not_final=MSG_NAMING_NOT_FINAL,
        suggested_filename=naming.suggested_filename or detail.suggested_filename,
        naming_confidence=naming.naming_confidence or detail.naming_confidence,
        filename_source=naming.filename_source or detail.filename_source,
        supplier=naming.supplier or detail.supplier,
        invoice_date=naming.invoice_date or detail.invoice_date,
        amount=naming.amount or detail.amount,
        document_type=naming.document_type or detail.document_type,
        payment_account=naming.payment_account or detail.payment_account,
        canonical_filename=naming.canonical_filename or detail.canonical_filename,
        filename_template_version=(
            naming.filename_template_version or detail.filename_template_version
        ),
        document_direction=naming.document_direction or detail.document_direction,
        business_category=naming.business_category or detail.business_category,
        business_category_display=(
            naming.business_category_display or detail.business_category_display
        ),
        counterparty_name=naming.counterparty_name or detail.counterparty_name,
        missing_fields=tuple(naming.missing_fields or detail.missing_fields or ()),
        matched_configuration_name=(
            naming.matched_configuration_name or detail.matched_configuration_name
        ),
        matched_configuration_id=(
            naming.matched_configuration_id or detail.matched_configuration_id
        ),
        matched_configuration_pattern=(
            naming.matched_configuration_pattern
            or detail.matched_configuration_pattern
        ),
        matched_configuration_reason=(
            naming.matched_configuration_reason
            or detail.matched_configuration_reason
        ),
        matched_configuration_confidence=(
            naming.matched_configuration_confidence
            or detail.matched_configuration_confidence
        ),
        filename_pattern=naming.filename_pattern or detail.filename_pattern,
        rendered_filename=naming.rendered_filename or detail.rendered_filename,
        placeholder_values=tuple(
            naming.placeholder_values or detail.placeholder_values or ()
        ),
        missing_placeholders=tuple(
            naming.missing_placeholders or detail.missing_placeholders or ()
        ),
        amount_format=naming.amount_format or detail.amount_format,
        amount_candidates=tuple(
            naming.amount_candidates or detail.amount_candidates or ()
        ),
        selected_amount=naming.selected_amount or detail.selected_amount or detail.amount,
        selected_amount_reason=(
            naming.selected_amount_reason or detail.selected_amount_reason
        ),
        rejected_amount_candidates=tuple(
            naming.rejected_amount_candidates
            or detail.rejected_amount_candidates
            or ()
        ),
        payment_field_candidates=tuple(
            naming.payment_field_candidates or detail.payment_field_candidates or ()
        ),
        selected_payment_field=(
            naming.selected_payment_field
            or detail.selected_payment_field
            or detail.payment_account
        ),
        selected_payment_field_reason=(
            naming.selected_payment_field_reason
            or detail.selected_payment_field_reason
        ),
        document_art_candidates=tuple(
            naming.document_art_candidates or detail.document_art_candidates or ()
        ),
        selected_art=naming.selected_art or detail.selected_art,
        selected_art_reason=naming.selected_art_reason or detail.selected_art_reason,
        art_ambiguity=bool(naming.art_ambiguity or detail.art_ambiguity),
        available_configurations=tuple(
            naming.available_configurations or detail.available_configurations or ()
        ),
        evaluated_configuration_candidates=tuple(
            naming.evaluated_configuration_candidates
            or detail.evaluated_configuration_candidates
            or ()
        ),
        unmatched_reasons=tuple(
            naming.unmatched_reasons or detail.unmatched_reasons or ()
        ),
        condition_results=tuple(
            naming.condition_results or detail.condition_results or ()
        ),
        alternative_matches=tuple(
            naming.alternative_matches or detail.alternative_matches or ()
        ),
        missing_configuration_rule=(
            naming.missing_configuration_rule or detail.missing_configuration_rule
        ),
        configuration_coverage_status=(
            naming.configuration_coverage_status
            or detail.configuration_coverage_status
        ),
        missing_configuration_type=(
            naming.missing_configuration_type or detail.missing_configuration_type
        ),
        user_guidance=naming.user_guidance or detail.user_guidance,
        suggested_configuration_action=(
            naming.suggested_configuration_action
            or detail.suggested_configuration_action
        ),
        guidance_severity=naming.guidance_severity or detail.guidance_severity,
        configuration_rule_draft_available=detail.configuration_rule_draft_available,
        proposed_configuration_name=detail.proposed_configuration_name,
        proposed_condition=detail.proposed_condition,
        proposed_filename_pattern=detail.proposed_filename_pattern,
        configuration_rule_draft_warning=detail.configuration_rule_draft_warning,
        requires_user_confirmation=detail.requires_user_confirmation,
        configuration_coverage_action_labels=detail.configuration_coverage_action_labels,
        rule_applied=bool(detail.rule_applied),
        applied_configuration_name=detail.applied_configuration_name,
        applied_configuration_condition=detail.applied_configuration_condition,
        rerun_preview_after_rule_change=bool(
            detail.rerun_preview_after_rule_change
        ),
        matched_after_rule_change=bool(detail.matched_after_rule_change),
        previous_matched_configuration=detail.previous_matched_configuration,
        new_matched_configuration=detail.new_matched_configuration,
        review_decision=review_decision,
        decision_timestamp=decision_timestamp,
        approved_preview_filename=approved_preview_filename,
        finalization_ready=bool(finalization_ready),
        finalization_blockers=tuple(finalization_blockers or ()),
        readiness_warnings=tuple(readiness_warnings or ()),
        final_write_allowed=False,
        not_final_yet_text=MSG_NOT_FINAL_YET,
        decision_feedback=decision_feedback,
        status_badges=derive_status_badges(
            detail,
            finalization_ready=bool(finalization_ready),
            finalization_blockers=tuple(finalization_blockers or ()),
        ),
        why_review_plain=derive_why_review_plain_german(
            {
                "source_filename": detail.source_filename or detail.document_label,
                "selected_payment_field": detail.selected_payment_field
                or detail.payment_account,
                "payment_account": detail.payment_account,
                "selected_art": detail.selected_art or detail.document_type,
                "document_type": detail.document_type,
                "missing_configuration_type": detail.missing_configuration_type,
                "configuration_coverage_status": detail.configuration_coverage_status,
                "user_guidance": detail.user_guidance,
                "business_category": detail.business_category,
                "business_category_display": detail.business_category_display,
                "matched_configuration_name": detail.matched_configuration_name,
                "review_reason": detail.reason,
                "suggested_filename": detail.suggested_filename
                or detail.rendered_filename,
            }
        ),
        next_action_labels_relevant=next_action_labels_for_detail(detail),
        paypal_action_visible=paypal_action_relevant(detail),
        er_er_note=er_er_note_for_filename(
            naming.suggested_filename
            or naming.preview_filename
            or detail.suggested_filename
            or detail.rendered_filename
        ),
        safety_line_declutter=MSG_SAFETY_LINE_NO_FINAL,
        section_titles=USER_REVIEW_SECTION_TITLES,
        technical_details_collapsed_by_default=True,
        kurzpruefung_fields=derive_recognized_fields(
            {
                "source_filename": detail.source_filename or detail.document_label,
                "document_label": detail.document_label,
                "counterparty_name": detail.counterparty_name,
                "supplier": detail.supplier,
                "invoice_date": detail.invoice_date,
                "selected_amount": detail.selected_amount,
                "amount": detail.amount,
                "selected_payment_field": detail.selected_payment_field,
                "payment_account": detail.payment_account,
                "selected_art": detail.selected_art,
                "document_type": detail.document_type,
            }
        ),
        vorschlag_fields=(
            (
                "vorgeschlagener Dateiname",
                naming.suggested_filename
                or naming.preview_filename
                or detail.suggested_filename
                or "—",
            ),
            ("Hinweis", MSG_FILENAME_PREVIEW_ONLY),
        ),
        finalization_summary_lines=(
            MSG_FINAL_WRITE_USER_ANSWER,
            MSG_SAFETY_LINE_NO_FINAL,
            MSG_NOT_FINAL_YET,
        ),
        recognized_fields=derive_recognized_fields(
            {
                "source_filename": detail.source_filename or detail.document_label,
                "document_label": detail.document_label,
                "counterparty_name": detail.counterparty_name,
                "supplier": detail.supplier,
                "invoice_date": detail.invoice_date,
                "selected_amount": detail.selected_amount,
                "amount": detail.amount,
                "selected_payment_field": detail.selected_payment_field,
                "payment_account": detail.payment_account,
                "selected_art": detail.selected_art,
                "document_type": detail.document_type,
            }
        ),
        unclear_items=derive_why_review_plain_german(
            {
                "source_filename": detail.source_filename or detail.document_label,
                "selected_payment_field": detail.selected_payment_field
                or detail.payment_account,
                "payment_account": detail.payment_account,
                "selected_art": detail.selected_art or detail.document_type,
                "document_type": detail.document_type,
                "missing_configuration_type": detail.missing_configuration_type,
                "configuration_coverage_status": detail.configuration_coverage_status,
                "user_guidance": detail.user_guidance,
                "business_category": detail.business_category,
                "business_category_display": detail.business_category_display,
                "matched_configuration_name": detail.matched_configuration_name,
                "review_reason": detail.reason,
                "suggested_filename": detail.suggested_filename
                or detail.rendered_filename,
            }
        ),
        decision_prompt=derive_decision_prompt(detail),
        final_write_user_answer=MSG_FINAL_WRITE_USER_ANSWER,
        user_mode_enabled=True,
    )


def build_review_page_vm(state: UiV2State) -> ReviewPageVM:
    """Derive review queue from ProcessingRunState only — never invent items."""

    run_state: ProcessingRunState = state.processing_run_state or ProcessingRunState()
    flow: ReviewFlowState = build_review_flow_state(run_state)
    queue: ReviewQueueViewModel = flow.queue
    raw_items = tuple(flow.review_items)
    detail_items = tuple(_detail_from_item_vm(item) for item in flow.review_view_items)
    action_labels = tuple(action.label for action in flow.actions)
    preview = build_export_preview_report(run_state)
    if preview.no_run:
        export_summary = MSG_NO_SANDBOX_RUN
    else:
        export_summary = (
            f"{MSG_EXPORT_PREVIEW_TITLE}: "
            f"{preview.recognized_count} erkannt · "
            f"{preview.review_count} Prüfung · "
            f"{preview.error_count} Fehler · "
            f"{preview.planned_destination_count} Ziele (Vorschau). "
            f"{MSG_NO_FINAL_FILES_WRITTEN} {MSG_ORIGINALS_UNCHANGED} "
            f"{MSG_PRODUCTIVE_PROCESSING_BLOCKED}"
        )

    bag = get_review_preview_ui(state)
    decision_bag = get_review_decision_bag(state)
    selected_key = bag.selected_item_key
    # Auto-select first item when items exist and nothing selected yet.
    if detail_items and not selected_key:
        selected_key = detail_items[0].item_key or detail_items[0].document_id
        bag.selected_item_key = selected_key
    # Drop stale selection if item no longer in queue.
    keys = {d.item_key or d.document_id for d in detail_items}
    if selected_key and selected_key not in keys:
        selected_key = (
            (detail_items[0].item_key or detail_items[0].document_id)
            if detail_items
            else None
        )
        bag.selected_item_key = selected_key

    open_key = get_open_review_item_id(state)
    if open_key and open_key not in keys:
        set_open_review_item_id(state, None)
        open_key = None
    # Single-open accordion: at most one expanded detail card.
    if open_key:
        selected_key = open_key
        bag.selected_item_key = open_key

    list_items = _build_list_items(
        detail_items,
        selected_key=selected_key,
        checked_keys=bag.checked_preview_keys,
        excluded_keys=bag.excluded_from_export_preview_keys,
        readiness_by_key=dict(decision_bag.readiness_by_item_key),
        open_key=open_key,
    )
    selected_detail = None
    coverage_action_labels: tuple[str, ...] = ()
    draft_available = False
    if selected_key:
        for detail in detail_items:
            key = detail.item_key or detail.document_id
            if key == selected_key:
                decision = decision_bag.decisions_by_item_key.get(key)
                readiness = decision_bag.readiness_by_item_key.get(key)
                selected_detail = _build_selected_detail(
                    detail,
                    safety_line=review_safety_line(flow),
                    export_preview_summary=export_summary,
                    excluded=key in bag.excluded_from_export_preview_keys,
                    checked=key in bag.checked_preview_keys,
                    review_decision=(
                        decision.decision_type if decision is not None else None
                    ),
                    decision_timestamp=(
                        decision.decision_timestamp if decision is not None else None
                    ),
                    approved_preview_filename=(
                        decision.approved_preview_filename
                        if decision is not None
                        else None
                    ),
                    finalization_ready=bool(
                        readiness.ready if readiness is not None else False
                    ),
                    finalization_blockers=tuple(
                        readiness.blockers
                        if readiness is not None
                        else (decision.finalization_blockers if decision else ())
                    ),
                    readiness_warnings=tuple(
                        readiness.warnings if readiness is not None else ()
                    ),
                    decision_feedback=decision_bag.last_feedback or None,
                )
                coverage_action_labels = detail.configuration_coverage_action_labels
                draft_available = bool(detail.configuration_rule_draft_available)
                break
    if state.configuration_rule_draft is not None:
        draft_available = True

    finalization_batch = build_finalization_preview_batch(state)
    batch_lines = batch_summary_lines(finalization_batch)
    dry_run_bag = get_finalization_dry_run_package_bag(state)
    dry_run_lines = dry_run_package_summary_lines(dry_run_bag.last_package)
    sandbox_bag = get_controlled_final_write_sandbox_bag(state)
    sandbox_lines = sandbox_final_write_summary_lines(sandbox_bag.last_result)
    sandbox_result = sandbox_bag.last_result
    ready_summaries, review_summaries = split_ready_and_review_cases(
        detail_items,
        readiness_by_key=dict(decision_bag.readiness_by_item_key),
    )

    return ReviewPageVM(
        title=queue.title,
        subtitle=queue.subtitle,
        empty=flow.empty,
        empty_title=queue.empty_title,
        empty_detail=queue.empty_detail,
        items=raw_items,
        detail_items=detail_items,
        honest_copy=flow.honest_copy,
        mutates_files=False,
        error_count=flow.error_count,
        result_count=flow.recognized_count,
        review_count=flow.review_count,
        separation_notes=flow.separation_notes,
        actions_disabled=True,
        action_labels=action_labels,
        source_run_id=flow.source_run_id,
        planned_preview_lines=review_planned_preview_lines(flow),
        error_section_lines=review_error_section_lines(flow),
        safety_line=review_safety_line(flow),
        productive_actions_exposed=False,
        export_preview_title=MSG_EXPORT_PREVIEW_TITLE,
        export_preview_summary=export_summary,
        export_preview_only=True,
        final_actions_blocked=True,
        list_items=list_items,
        selected_item_key=selected_key,
        selected_detail=selected_detail,
        preview_action_labels=PREVIEW_ACTION_LABELS,
        preview_actions_enabled=bool(detail_items),
        preview_only_banner=MSG_PREVIEW_ONLY_BANNER,
        empty_output_explanation=MSG_EMPTY_OUTPUT_EXPLAIN,
        configuration_coverage_action_labels=coverage_action_labels,
        configuration_rule_draft_available=draft_available,
        preview_rerun_action_labels=preview_rerun_action_labels(),
        configuration_rule_apply_available=bool(
            getattr(state, "configuration_rule_apply_available", False)
        ),
        decision_action_labels=DECISION_ACTION_LABELS,
        not_final_yet_text=MSG_NOT_FINAL_YET,
        decision_feedback=decision_bag.last_feedback,
        decision_feedback_error=bool(decision_bag.last_feedback_error),
        finalization_preview_batch_title=MSG_BATCH_TITLE,
        finalization_preview_batch_ready_count=finalization_batch.ready_count,
        finalization_preview_batch_blocked_count=finalization_batch.blocked_count,
        finalization_preview_batch_ignored_count=finalization_batch.ignored_count,
        finalization_preview_batch_deferred_count=finalization_batch.deferred_count,
        finalization_preview_batch_still_review_required_count=(
            finalization_batch.still_review_required_count
        ),
        finalization_preview_batch_summary_lines=batch_lines,
        finalization_preview_batch_no_final_write_text=MSG_BATCH_NO_FINAL_WRITE,
        finalization_dry_run_title=MSG_DRY_RUN_TITLE,
        finalization_dry_run_cta_create=MSG_CTA_CREATE_DRY_RUN,
        finalization_dry_run_cta_audit=MSG_CTA_CREATE_AUDIT,
        finalization_dry_run_check_only=MSG_CTA_CHECK_ONLY,
        finalization_dry_run_package_path=dry_run_bag.last_package_root
        or getattr(state, "workspace_last_finalization_dry_run_folder", "")
        or "",
        finalization_dry_run_feedback=dry_run_bag.last_feedback
        or getattr(state, "workspace_finalization_dry_run_feedback", "")
        or "",
        finalization_dry_run_feedback_error=bool(
            dry_run_bag.last_feedback_error
            or getattr(state, "workspace_finalization_dry_run_feedback_error", False)
        ),
        finalization_dry_run_summary_lines=dry_run_lines,
        sandbox_final_write_title=MSG_SANDBOX_FINAL_WRITE_TITLE,
        sandbox_final_write_cta=MSG_CTA_SANDBOX_WRITE,
        sandbox_final_write_controlled_only=MSG_CTA_CONTROLLED_ONLY,
        sandbox_final_write_originals_unchanged=MSG_CTA_ORIGINALS_UNCHANGED,
        sandbox_final_write_result_path=sandbox_bag.last_result_root
        or getattr(state, "workspace_last_sandbox_final_write_folder", "")
        or "",
        sandbox_final_write_feedback=sandbox_bag.last_feedback
        or getattr(state, "workspace_sandbox_final_write_feedback", "")
        or "",
        sandbox_final_write_feedback_error=bool(
            sandbox_bag.last_feedback_error
            or getattr(state, "workspace_sandbox_final_write_feedback_error", False)
        ),
        sandbox_final_write_summary_lines=sandbox_lines,
        sandbox_final_write_written_count=(
            sandbox_result.final_files_written_count if sandbox_result else 0
        ),
        sandbox_final_write_skipped_count=(
            len(sandbox_result.skipped_items) if sandbox_result else 0
        ),
        sandbox_final_write_blocked_count=(
            len(sandbox_result.blocked_items) if sandbox_result else 0
        ),
        sandbox_final_write_failure_count=(
            len(sandbox_result.failures) if sandbox_result else 0
        ),
        calls_run_once=False,
        writes_final_files=False,
        mutates_input=False,
        touches_real_invoice_folders=False,
        claims_saas_ready=False,
        claims_production_ready=False,
        declutter_layout_marker=REVIEW_DECLUTTER_LAYOUT_MARKER,
        user_mode_layout_marker=REVIEW_USER_MODE_LAYOUT_MARKER,
        ui_polish_layout_marker=REVIEW_UI_POLISH_LAYOUT_MARKER,
        filename_field_polish_marker=FILENAME_FIELD_POLISH_MARKER,
        accordion_layout_marker=REVIEW_ACCORDION_LAYOUT_MARKER,
        collapsed_summary_marker=REVIEW_CARD_COLLAPSED_SUMMARY_ONLY,
        active_card_highlight_marker=REVIEW_CARD_ACTIVE_HIGHLIGHT,
        inline_detail_marker=INLINE_DETAIL_UNDER_SELECTED_CARD,
        detail_panel_background_marker=DETAIL_PANEL_DISTINCT_BACKGROUND,
        safety_line_declutter=MSG_SAFETY_LINE_NO_FINAL,
        final_write_user_answer=MSG_FINAL_WRITE_USER_ANSWER,
        oracle_available_title=MSG_ORACLE_AVAILABLE,
        oracle_command=ORACLE_COMMAND,
        oracle_no_auto_run=MSG_ORACLE_NO_AUTO_RUN,
        technical_details_collapsed_by_default=True,
        section_titles=USER_REVIEW_SECTION_TITLES,
        copy_action_labels=(
            ACTION_COPY_CASE,
            ACTION_COPY_DIAGNOSIS,
            ACTION_COPY_ORACLE,
            ACTION_COPY_FILENAME,
        ),
        empty_state_workspace_action=ACTION_OPEN_WORKSPACE,
        empty_state_oracle_action=ACTION_COPY_ORACLE,
        auto_runs_oracle=False,
        production_final_write_enabled=False,
        user_mode_enabled=True,
        ready_case_summaries=ready_summaries,
        review_case_summaries=review_summaries,
        cases_ready_count=len(ready_summaries),
        cases_review_count=len(review_summaries),
        open_review_item_id=open_key,
        accordion_single_open=True,
        details_open_action_label=ACTION_DETAILS_OPEN,
        details_close_action_label=ACTION_DETAILS_CLOSE,
    )


def _legacy_action_row(queue: ReviewQueueViewModel) -> ft.Control:
    """Render disabled readiness-only review actions — no handlers that persist."""

    buttons = [
        secondary_button(
            f"{action.label} ({action.readiness_label})",
            on_click=lambda _e: None,
            disabled=True,
        )
        for action in queue.actions
    ]
    return ft.Row(buttons, spacing=8, wrap=True)


def _preview_action_row(state: UiV2State, *, enabled: bool) -> ft.Control:
    """Enabled preview-only actions — mutate UiV2 local state only."""

    def _refresh() -> None:
        if state.refresh is not None:
            state.refresh()

    def _on_mark(_e: ft.ControlEvent) -> None:
        mark_checked_preview(state)
        _refresh()

    def _on_keep(_e: ft.ControlEvent) -> None:
        keep_in_review(state)
        _refresh()

    def _on_exclude(_e: ft.ControlEvent) -> None:
        exclude_from_export_preview(state)
        _refresh()

    def _on_reset(_e: ft.ControlEvent) -> None:
        reset_preview_selection(state)
        _refresh()

    buttons = [
        secondary_button(
            ACTION_MARK_CHECKED_PREVIEW,
            on_click=_on_mark,
            disabled=not enabled,
        ),
        secondary_button(
            ACTION_KEEP_IN_REVIEW,
            on_click=_on_keep,
            disabled=not enabled,
        ),
        secondary_button(
            ACTION_EXCLUDE_EXPORT_PREVIEW,
            on_click=_on_exclude,
            disabled=not enabled,
        ),
        secondary_button(
            ACTION_RESET_SELECTION,
            on_click=_on_reset,
            disabled=not enabled,
        ),
    ]
    return ft.Row(buttons, spacing=8, wrap=True)


def _decision_action_row(state: UiV2State, *, enabled: bool) -> ft.Control:
    """Prompt-29 decision actions — state only, never final write."""

    decision_bag = get_review_decision_bag(state)
    selected = get_review_preview_ui(state).selected_item_key

    def _refresh() -> None:
        if state.refresh is not None:
            state.refresh()

    def _on_accept(_e: ft.ControlEvent) -> None:
        key = get_review_preview_ui(state).selected_item_key
        if decision_bag.pending_accept_confirm_key != key:
            arm_accept_confirmation(state, key)
            _refresh()
            return
        create_accept_suggestion_decision(
            state,
            item_key=key,
            decided_by_user=True,
            explicit_confirmation=True,
        )
        _refresh()

    def _on_edit(_e: ft.ControlEvent) -> None:
        key = get_review_preview_ui(state).selected_item_key
        draft = decision_bag.edit_filename_draft_by_key.get(key or "", "")
        if not draft and selected:
            # Seed draft from current preview filename when empty.
            vm = build_review_page_vm(state)
            if vm.selected_detail and vm.selected_detail.preview_filename:
                draft = vm.selected_detail.preview_filename
                set_edit_filename_draft(state, selected, draft)
        create_edit_suggestion_decision(
            state,
            item_key=key,
            decided_by_user=True,
            edited_filename=draft or None,
        )
        _refresh()

    def _on_config(_e: ft.ControlEvent) -> None:
        create_needs_configuration_change_decision(state, decided_by_user=True)
        _refresh()

    def _on_keep_unclear(_e: ft.ControlEvent) -> None:
        create_keep_review_required_decision(state, decided_by_user=True)
        _refresh()

    def _on_ignore(_e: ft.ControlEvent) -> None:
        create_ignore_for_export_decision(state, decided_by_user=True)
        _refresh()

    def _on_defer(_e: ft.ControlEvent) -> None:
        create_defer_decision(state, decided_by_user=True)
        _refresh()

    accept_label = ACTION_ACCEPT_SUGGESTION
    if (
        selected
        and decision_bag.pending_accept_confirm_key == selected
    ):
        accept_label = f"{ACTION_ACCEPT_SUGGESTION} (bestätigen)"

    buttons = [
        secondary_button(accept_label, on_click=_on_accept, disabled=not enabled),
        secondary_button(
            ACTION_EDIT_SUGGESTION, on_click=_on_edit, disabled=not enabled
        ),
        secondary_button(
            ACTION_NEEDS_CONFIGURATION, on_click=_on_config, disabled=not enabled
        ),
        secondary_button(
            ACTION_KEEP_UNCLEAR, on_click=_on_keep_unclear, disabled=not enabled
        ),
        secondary_button(
            ACTION_IGNORE_EXPORT, on_click=_on_ignore, disabled=not enabled
        ),
        secondary_button(ACTION_DEFER, on_click=_on_defer, disabled=not enabled),
    ]
    return ft.Column(
        [
            ft.Text(MSG_NOT_FINAL_YET, size=12),
            ft.Row(buttons, spacing=8, wrap=True),
        ],
        spacing=8,
        tight=True,
    )


def _decision_status_panel(detail: ReviewSelectedDetailVM) -> ft.Control:
    ready_label = (
        MSG_FINALIZATION_READY_YES
        if detail.finalization_ready
        else MSG_FINALIZATION_READY_NO
    )
    lines = [
        ft.Text(detail.not_final_yet_text, size=12),
        ft.Text(ready_label, size=12),
        ft.Text(MSG_FINAL_WRITE_USER_ANSWER, size=12),
    ]
    if detail.review_decision:
        lines.append(ft.Text(f"Entscheidung: {detail.review_decision}", size=12))
    if detail.decision_timestamp:
        lines.append(ft.Text(f"Zeitpunkt: {detail.decision_timestamp}", size=12))
    if detail.approved_preview_filename:
        lines.append(
            ft.Text(
                f"Freigegebener Dateiname: {detail.approved_preview_filename}",
                size=12,
            )
        )
    if detail.finalization_blockers:
        lines.append(
            ft.Text(
                "Blocker: " + ", ".join(detail.finalization_blockers),
                size=12,
            )
        )
    if detail.readiness_warnings:
        lines.append(
            ft.Text(
                "Warnungen: " + ", ".join(detail.readiness_warnings),
                size=12,
            )
        )
    if detail.decision_feedback:
        lines.append(ft.Text(detail.decision_feedback, size=12))
    return section_block(
        "Review-Entscheidung / Finalisierungsbereitschaft",
        ft.Column(lines, spacing=4, tight=True),
        subtitle="Preview only — keine finale Verarbeitung",
    )


def _finalization_preview_batch_panel(vm: ReviewPageVM) -> ft.Control:
    """Prompt-30 batch summary — counts/conflicts only, never final write."""

    lines = [
        ft.Text(f"{MSG_BATCH_READY}: {vm.finalization_preview_batch_ready_count}", size=12),
        ft.Text(
            f"{MSG_BATCH_BLOCKED}: {vm.finalization_preview_batch_blocked_count}",
            size=12,
        ),
        ft.Text(
            f"{MSG_BATCH_IGNORED}: {vm.finalization_preview_batch_ignored_count}",
            size=12,
        ),
        ft.Text(
            f"{MSG_BATCH_DEFERRED}: {vm.finalization_preview_batch_deferred_count}",
            size=12,
        ),
        ft.Text(
            f"{MSG_BATCH_STILL_REVIEW}: "
            f"{vm.finalization_preview_batch_still_review_required_count}",
            size=12,
        ),
        ft.Text(MSG_BATCH_NO_FINAL_WRITE, size=12),
        ft.Text(MSG_FINAL_WRITE_USER_ANSWER, size=12),
    ]
    for line in vm.finalization_preview_batch_summary_lines:
        if line in {
            MSG_BATCH_TITLE,
            MSG_BATCH_NO_FINAL_WRITE,
            f"{MSG_BATCH_READY}: {vm.finalization_preview_batch_ready_count}",
            f"{MSG_BATCH_BLOCKED}: {vm.finalization_preview_batch_blocked_count}",
            f"{MSG_BATCH_IGNORED}: {vm.finalization_preview_batch_ignored_count}",
            f"{MSG_BATCH_DEFERRED}: {vm.finalization_preview_batch_deferred_count}",
            (
                f"{MSG_BATCH_STILL_REVIEW}: "
                f"{vm.finalization_preview_batch_still_review_required_count}"
            ),
        }:
            continue
        lines.append(ft.Text(line, size=12))
    return section_block(
        MSG_BATCH_TITLE,
        ft.Column(lines, spacing=4, tight=True),
        subtitle="Nicht-produktiv — kein finales Schreiben",
    )


def _finalization_dry_run_panel(state: UiV2State, vm: ReviewPageVM) -> ft.Control:
    """Prompt-31 dry-run package CTA — audit artifacts only, never final write."""

    def _refresh() -> None:
        if state.refresh is not None:
            state.refresh()

    def _on_create(_e: ft.ControlEvent) -> None:
        apply_finalization_dry_run_package(state)
        _refresh()

    lines: list[ft.Control] = [
        ft.Text(MSG_CTA_CREATE_DRY_RUN, size=12),
        ft.Text(MSG_CTA_CREATE_AUDIT, size=12),
        ft.Text(MSG_CTA_CHECK_ONLY, size=12),
        ft.Text(MSG_FINAL_WRITE_FALSE, size=12),
        ft.Text(
            f"{MSG_BATCH_READY}: {vm.finalization_preview_batch_ready_count} · "
            f"{MSG_BATCH_BLOCKED}: {vm.finalization_preview_batch_blocked_count}",
            size=12,
        ),
        secondary_button(
            MSG_CTA_CREATE_DRY_RUN,
            on_click=_on_create,
            disabled=False,
        ),
    ]
    if vm.finalization_dry_run_package_path:
        lines.append(
            ft.Text(f"Paket: {vm.finalization_dry_run_package_path}", size=12)
        )
    if vm.finalization_dry_run_feedback:
        lines.append(ft.Text(vm.finalization_dry_run_feedback, size=12))
    for line in vm.finalization_dry_run_summary_lines:
        if line in {
            MSG_DRY_RUN_TITLE,
            MSG_CTA_CREATE_DRY_RUN,
            MSG_CTA_CREATE_AUDIT,
            MSG_CTA_CHECK_ONLY,
            MSG_FINAL_WRITE_FALSE,
        }:
            continue
        lines.append(ft.Text(line, size=12))
    return section_block(
        MSG_DRY_RUN_TITLE,
        ft.Column(lines, spacing=6, tight=True),
        subtitle=MSG_CTA_CHECK_ONLY,
    )


def _sandbox_final_write_panel(state: UiV2State, vm: ReviewPageVM) -> ft.Control:
    """Prompt-33 sandbox final-write CTA — controlled copies only, not production."""

    def _refresh() -> None:
        if state.refresh is not None:
            state.refresh()

    def _on_sandbox_write(_e: ft.ControlEvent) -> None:
        apply_controlled_final_write_sandbox(state, sandbox_final_write=True)
        _refresh()

    lines: list[ft.Control] = [
        ft.Text(MSG_CTA_SANDBOX_WRITE, size=12),
        ft.Text(MSG_CTA_CONTROLLED_ONLY, size=12),
        ft.Text(MSG_CTA_ORIGINALS_UNCHANGED, size=12),
        ft.Text(
            "Sandbox-Test — kein Produktions-Final-Write. "
            + MSG_FINAL_WRITE_USER_ANSWER,
            size=12,
        ),
        ft.Text(
            f"geschrieben: {vm.sandbox_final_write_written_count} · "
            f"übersprungen: {vm.sandbox_final_write_skipped_count} · "
            f"blockiert: {vm.sandbox_final_write_blocked_count} · "
            f"Fehler: {vm.sandbox_final_write_failure_count}",
            size=12,
        ),
        secondary_button(
            MSG_CTA_SANDBOX_WRITE,
            on_click=_on_sandbox_write,
            disabled=False,
        ),
    ]
    if vm.sandbox_final_write_result_path:
        lines.append(
            ft.Text(f"Sandbox-Pfad: {vm.sandbox_final_write_result_path}", size=12)
        )
    if vm.sandbox_final_write_feedback:
        lines.append(ft.Text(vm.sandbox_final_write_feedback, size=12))
    for line in vm.sandbox_final_write_summary_lines:
        if line in {
            MSG_SANDBOX_FINAL_WRITE_TITLE,
            MSG_CTA_SANDBOX_WRITE,
            MSG_CTA_CONTROLLED_ONLY,
            MSG_CTA_ORIGINALS_UNCHANGED,
        }:
            continue
        lines.append(ft.Text(line, size=12))
    return section_block(
        MSG_SANDBOX_FINAL_WRITE_TITLE,
        ft.Column(lines, spacing=6, tight=True),
        subtitle=MSG_CTA_CONTROLLED_ONLY,
    )



def _kv_lines(fields: tuple[tuple[str, str], ...] | list[tuple[str, str]]) -> ft.Control:
    rows = [
        ft.Text(f"{label}: {value or '—'}", size=12) for label, value in fields
    ]
    return ft.Column(rows, spacing=4, tight=True)


def _oracle_dev_box(state: UiV2State, vm: ReviewPageVM) -> ft.Control:
    def _copy_oracle(_e: ft.ControlEvent) -> None:
        copy_text_to_state_and_clipboard(
            state,
            build_oracle_command_copy_text(),
            kind=ACTION_COPY_ORACLE,
        )
        if state.refresh is not None:
            state.refresh()

    body = ft.Column(
        [
            ft.Text(vm.oracle_available_title, size=13, weight=ft.FontWeight.W_600),
            ft.Text(vm.oracle_command, size=11, selectable=True),
            ft.Text(vm.oracle_no_auto_run, size=11),
            secondary_button(ACTION_COPY_ORACLE, on_click=_copy_oracle),
        ],
        spacing=6,
        tight=True,
    )
    return section_block(
        "Dev: Automatischer Smoke-Test",
        body,
        subtitle="Kein Auto-Run — nur Kopieren",
    )


def _next_action_row(state: UiV2State, detail: ReviewSelectedDetailVM) -> ft.Control:
    """Show only relevant next actions — never final write / never run_once."""

    decision_bag = get_review_decision_bag(state)

    def _refresh() -> None:
        if state.refresh is not None:
            state.refresh()

    def _profile_id() -> str:
        from invoice_tool.app_paths import resolve_active_profile_id

        return (
            str(state.selected_profile_id or "").strip()
            or resolve_active_profile_id()
        )

    def _on_paypal(_e: ft.ControlEvent) -> None:
        from invoice_tool.ui_v2.configuration_rule_editor import (
            save_paypal_rule_and_rerun_matching,
        )

        current = state.configuration_rule_draft
        if current is None:
            state.configuration_rule_draft_feedback = (
                "Kein PayPal-Entwurf geöffnet — zuerst aus dem Hinweis erstellen."
            )
            state.configuration_rule_draft_feedback_error = True
            _refresh()
            return
        result = save_paypal_rule_and_rerun_matching(
            profile_id=_profile_id(),
            draft=current,
            run_state=state.processing_run_state,
            explicit_user_confirmation=True,
            require_controlled_target=True,
        )
        state.configuration_rule_draft = result.draft
        state.configuration_rule_draft_feedback = result.message
        state.configuration_rule_draft_feedback_error = not result.ok
        if result.updated_run_state is not None:
            state.processing_run_state = result.updated_run_state
        _refresh()

    def _on_accept(_e: ft.ControlEvent) -> None:
        key = get_review_preview_ui(state).selected_item_key
        if decision_bag.pending_accept_confirm_key != key:
            arm_accept_confirmation(state, key)
            _refresh()
            return
        create_accept_suggestion_decision(
            state,
            item_key=key,
            decided_by_user=True,
            explicit_confirmation=True,
        )
        _refresh()

    def _on_keep_unclear(_e: ft.ControlEvent) -> None:
        create_keep_review_required_decision(state, decided_by_user=True)
        _refresh()

    def _on_ignore(_e: ft.ControlEvent) -> None:
        create_ignore_for_export_decision(state, decided_by_user=True)
        _refresh()

    def _on_defer(_e: ft.ControlEvent) -> None:
        create_defer_decision(state, decided_by_user=True)
        _refresh()

    accept_label = ACTION_ACCEPT_SUGGESTION
    selected = get_review_preview_ui(state).selected_item_key
    if selected and decision_bag.pending_accept_confirm_key == selected:
        accept_label = f"{ACTION_ACCEPT_SUGGESTION} (bestätigen)"

    buttons: list[ft.Control] = []
    if detail.paypal_action_visible:
        buttons.append(
            secondary_button(
                ACTION_PAYPAL_SMOKE_SAVE_AND_RERUN,
                on_click=_on_paypal,
            )
        )
    buttons.extend(
        [
            secondary_button(accept_label, on_click=_on_accept),
            secondary_button(ACTION_KEEP_UNCLEAR, on_click=_on_keep_unclear),
            secondary_button(ACTION_DEFER, on_click=_on_defer),
            secondary_button(ACTION_IGNORE_EXPORT, on_click=_on_ignore),
        ]
    )
    return ft.Column(
        [
            ft.Text(
                "Deine Entscheidung gilt nur für diese Vorschau. "
                "Originale bleiben unverändert — es wird nichts final geschrieben.",
                size=11,
            ),
            ft.Text(MSG_NOT_FINAL_YET, size=12),
            ft.Row(buttons, spacing=8, wrap=True),
        ],
        spacing=8,
        tight=True,
    )


def _copy_actions_row(
    state: UiV2State,
    detail: ReviewSelectedDetailVM,
) -> ft.Control:
    def _refresh() -> None:
        if state.refresh is not None:
            state.refresh()

    def _copy_case(_e: ft.ControlEvent) -> None:
        text = build_prueffall_copy_text(
            detail,
            draft=state.configuration_rule_draft,
            profile_id=state.selected_profile_id,
        )
        copy_text_to_state_and_clipboard(state, text, kind=ACTION_COPY_CASE)
        _refresh()

    def _copy_diagnosis(_e: ft.ControlEvent) -> None:
        text = build_diagnosis_copy_text(
            detail,
            draft=state.configuration_rule_draft,
            profile_id=state.selected_profile_id,
            duplicate_report=state.track_b_duplicate_report_text or None,
            run_state=state.processing_run_state,
        )
        copy_text_to_state_and_clipboard(state, text, kind=ACTION_COPY_DIAGNOSIS)
        _refresh()

    def _copy_oracle(_e: ft.ControlEvent) -> None:
        copy_text_to_state_and_clipboard(
            state,
            build_oracle_command_copy_text(),
            kind=ACTION_COPY_ORACLE,
        )
        _refresh()

    controls: list[ft.Control] = [
        ft.Row(
            [
                secondary_button(ACTION_COPY_CASE, on_click=_copy_case),
                secondary_button(ACTION_COPY_DIAGNOSIS, on_click=_copy_diagnosis),
                secondary_button(ACTION_COPY_ORACLE, on_click=_copy_oracle),
            ],
            spacing=8,
            wrap=True,
        ),
    ]
    if state.track_b_smoke_copy_feedback:
        controls.append(ft.Text(state.track_b_smoke_copy_feedback, size=12))
    return ft.Column(controls, spacing=6, tight=True)


def _technical_detail_lines(detail: ReviewSelectedDetailVM) -> tuple[str, ...]:
    """Collapsed developer dump — not shown on the primary user surface."""

    lines = [
        f"matching_reason: {detail.matched_configuration_reason or '—'}",
        f"configuration_coverage_status: {detail.configuration_coverage_status or '—'}",
        f"missing_configuration_type: {detail.missing_configuration_type or '—'}",
        f"matched_configuration_id: {detail.matched_configuration_id or '—'}",
        f"proposed_configuration: {detail.proposed_configuration_name or '—'}",
        f"proposed_condition: {detail.proposed_condition or '—'}",
        f"proposed_filename_pattern: {detail.proposed_filename_pattern or '—'}",
        f"finalization_ready: {detail.finalization_ready}",
        f"finalization_blockers: {', '.join(detail.finalization_blockers) or '—'}",
        "final_write_allowed: false",
        "production_final_write: disabled",
        f"naming_confidence: {detail.naming_confidence or '—'}",
        f"filename_source: {detail.filename_source or '—'}",
        f"selected_payment_field_reason: {detail.selected_payment_field_reason or '—'}",
        f"selected_art_reason: {detail.selected_art_reason or '—'}",
        f"selected_amount_reason: {detail.selected_amount_reason or '—'}",
        f"review_decision: {detail.review_decision or '—'}",
        f"safety: {detail.safety_status}",
        SMOKE_DEV_UI_LAYOUT_MARKER,
        REVIEW_USER_MODE_LAYOUT_MARKER,
    ]
    if detail.condition_results:
        cond = "; ".join(
            str(c.get("reason") or c.get("condition_type") or c)
            for c in detail.condition_results
        )
        lines.append(f"checked_conditions: {cond}")
    if detail.evaluated_configuration_candidates:
        parts = []
        for candidate in detail.evaluated_configuration_candidates:
            status = "ja" if candidate.get("matched") else "nein"
            parts.append(
                f"{candidate.get('configuration_name')}: {status}"
                f" ({candidate.get('reason') or ''})"
            )
        lines.append(f"evaluated_candidates: {'; '.join(parts)}")
    if detail.missing_fields:
        lines.append(f"missing_fields: {', '.join(detail.missing_fields)}")
    if detail.placeholder_values:
        lines.append(
            "placeholder_values: "
            + ", ".join(
                f"{key}={value if value is not None else '—'}"
                for key, value in detail.placeholder_values
            )
        )
    return tuple(lines)


def _finalization_declutter_panel(
    state: UiV2State,
    vm: ReviewPageVM,
    detail: ReviewSelectedDetailVM,
) -> ft.Control:
    """User-facing final-write answer — technical flags stay collapsed."""

    _ = state  # panel is display-only in user mode
    body = ft.Column(
        [
            ft.Text(detail.final_write_user_answer or vm.final_write_user_answer, size=13),
            ft.Text(MSG_SAFETY_LINE_NO_FINAL, size=12),
            ft.Text(MSG_NOT_FINAL_YET, size=12),
            ft.Text(
                "Bereit für spätere Vorschau-Finalisierung"
                if detail.finalization_ready
                else (
                    "Blockiert"
                    if detail.finalization_blockers
                    else "Weiter zur Prüfung"
                ),
                size=12,
            ),
        ],
        spacing=6,
        tight=True,
    )
    return review_section(
        SECTION_FINAL_WRITE_Q,
        body,
        subtitle=MSG_NOT_FINAL_YET,
    )


def _ready_cases_panel(vm: ReviewPageVM) -> ft.Control:
    if vm.ready_case_summaries:
        lines = [ft.Text(f"· {line}", size=12) for line in vm.ready_case_summaries]
    else:
        lines = [ft.Text(f"· {MSG_NO_READY_CASES}", size=12)]
    lines.insert(
        0,
        ft.Text(f"Anzahl: {vm.cases_ready_count}", size=12, weight=ft.FontWeight.W_600),
    )
    return section_block(SECTION_BEREIT, ft.Column(lines, spacing=4, tight=True))


def _review_cases_panel(vm: ReviewPageVM) -> ft.Control:
    if vm.review_case_summaries:
        lines = [ft.Text(f"· {line}", size=12) for line in vm.review_case_summaries]
    else:
        lines = [ft.Text(f"· {MSG_NO_REVIEW_CASES}", size=12)]
    lines.insert(
        0,
        ft.Text(
            f"Anzahl: {vm.cases_review_count}",
            size=12,
            weight=ft.FontWeight.W_600,
        ),
    )
    return section_block(SECTION_PRUEFUNG, ft.Column(lines, spacing=4, tight=True))


def _developer_tools_collapsed(
    state: UiV2State,
    vm: ReviewPageVM,
    detail: ReviewSelectedDetailVM | None,
) -> ft.Control:
    """Oracle / dry-run / sandbox / diagnosis — never primary user surface."""

    tech_lines: list[str] = [
        vm.user_mode_layout_marker,
        vm.declutter_layout_marker,
        vm.ui_polish_layout_marker,
        vm.filename_field_polish_marker,
        vm.accordion_layout_marker,
        MSG_ORACLE_AVAILABLE,
        vm.oracle_command,
        MSG_ORACLE_NO_AUTO_RUN,
        "Kein Auto-Run — Terminal-Oracle bleibt fachliches Regressionsgate.",
    ]
    if detail is not None:
        tech_lines.extend(_technical_detail_lines(detail))
        tech_lines.extend(detail.finalization_summary_lines or ())
        if vm.finalization_dry_run_package_path:
            tech_lines.append(f"Dry-run: {vm.finalization_dry_run_package_path}")
        if vm.sandbox_final_write_result_path:
            tech_lines.append(
                f"Sandbox-final-write: {vm.sandbox_final_write_result_path}"
            )
    return collapsible_details(
        *tech_lines,
        title=SECTION_TECHNISCHE,
        initially_expanded=False,
    )


def render_review_summary_card(
    row: ReviewListItemVM,
    *,
    is_open: bool,
    on_toggle,
) -> ft.Control:
    """Collapsed overview: name, date, amount + Details öffnen/schließen."""

    display_name = row.summary_display_name or review_summary_display_name(row)
    fields: list[tuple[str, str]] = [
        (LABEL_REVIEW_DOC_NAME, display_name),
        (LABEL_REVIEW_DATE, row.invoice_date or "—"),
        (LABEL_REVIEW_AMOUNT, row.amount or "—"),
    ]
    action_label = ACTION_DETAILS_CLOSE if is_open else ACTION_DETAILS_OPEN
    trailing = status_badge(
        action_label,
        tone="active" if is_open else "neutral",
    )
    entry = compact_entry_row(
        display_name,
        *fields,
        trailing=trailing,
    )
    border = ft.Border.all(
        2 if is_open else 1,
        COLOR_PRIMARY if is_open else COLOR_BORDER,
    )
    accent = ft.Container(
        width=4,
        bgcolor=COLOR_PRIMARY if is_open else COLOR_BORDER,
        border_radius=RADIUS_CARD,
    )
    return ft.Container(
        content=ft.Row(
            [accent, ft.Container(content=entry, expand=True)],
            spacing=SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        on_click=on_toggle,
        ink=True,
        padding=SPACE_MD,
        bgcolor=COLOR_PRIMARY_SUBTLE if is_open else COLOR_SURFACE,
        border=border,
        border_radius=RADIUS_CARD,
        data=(
            REVIEW_CARD_ACTIVE_HIGHLIGHT
            if is_open
            else REVIEW_CARD_COLLAPSED_SUMMARY_ONLY
        ),
    )


def render_review_inline_detail(
    state: UiV2State,
    vm: ReviewPageVM,
    detail: ReviewSelectedDetailVM,
) -> ft.Control:
    """Detail panel rendered directly under the open accordion card."""

    sections = _selected_detail_section_controls(state, vm, detail)
    return ft.Container(
        content=ft.Column(sections, spacing=SPACE_SM, tight=True),
        margin=ft.Margin.only(top=SPACE_XS, bottom=SPACE_MD, left=SPACE_SM),
        padding=SPACE_LG,
        bgcolor=COLOR_SURFACE_ALT,
        border=ft.Border.all(1, COLOR_BORDER_STRONG),
        border_radius=RADIUS_CARD,
        data=f"{INLINE_DETAIL_UNDER_SELECTED_CARD}|{DETAIL_PANEL_DISTINCT_BACKGROUND}",
    )


def _selected_detail_section_controls(
    state: UiV2State,
    vm: ReviewPageVM,
    detail: ReviewSelectedDetailVM,
) -> list[ft.Control]:
    """Reuse Simple User Review sections inside the inline accordion detail."""

    out: list[ft.Control] = [
        review_section(
            SECTION_ERKANNT,
            _kv_lines(detail.recognized_fields or detail.kurzpruefung_fields),
        )
    ]
    unclear_lines = [
        ft.Text(f"· {line}", size=12)
        for line in (detail.unclear_items or detail.why_review_plain)
    ]
    out.append(
        review_section(
            SECTION_UNKLAR,
            ft.Column(
                unclear_lines or [ft.Text("· Prüfung erforderlich", size=12)],
                spacing=4,
                tight=True,
            ),
        )
    )
    vorschlag_body: list[ft.Control] = [
        ft.Text(
            detail.suggested_filename or detail.preview_filename or "—",
            size=13,
            weight=ft.FontWeight.W_600,
            selectable=True,
        ),
        _kv_lines(detail.vorschlag_fields),
    ]
    if detail.er_er_note:
        vorschlag_body.append(ft.Text(detail.er_er_note, size=11))
    elif detail.suggested_filename and "_er_er_" in detail.suggested_filename:
        vorschlag_body.append(ft.Text(MSG_LEGACY_ER_ER_NOTE, size=11))
    decision_bag = get_review_decision_bag(state)
    draft_value = decision_bag.edit_filename_draft_by_key.get(
        detail.item_key,
        detail.approved_preview_filename
        or detail.preview_filename
        or detail.suggested_filename
        or "",
    )

    def _on_filename_change(e: ft.ControlEvent) -> None:
        set_edit_filename_draft(
            state, detail.item_key, str(getattr(e.control, "value", "") or "")
        )

    def _copy_filename(_e: ft.ControlEvent, value: str = draft_value) -> None:
        current = decision_bag.edit_filename_draft_by_key.get(detail.item_key, value)
        copy_text_to_state_and_clipboard(
            state,
            str(current or value or ""),
            kind=ACTION_COPY_FILENAME,
        )
        if state.refresh is not None:
            state.refresh()

    filename_field = ft.TextField(
        value=draft_value,
        on_change=_on_filename_change,
        multiline=True,
        min_lines=2,
        max_lines=4,
        expand=True,
        text_size=FONT_SIZE_MONO,
        border_color=COLOR_BORDER,
        dense=False,
        data=FILENAME_FIELD_POLISH_MARKER,
    )
    filename_editor = form_field_group(
        LABEL_VORSCHAU_DATEINAME,
        ft.Column(
            [
                ft.Text(
                    LABEL_DATEINAME_BEARBEITEN,
                    size=FONT_SIZE_HELPER,
                    color=COLOR_TEXT_MUTED,
                ),
                ft.Container(
                    content=filename_field,
                    expand=True,
                    width=None,
                    data=FILENAME_FIELD_POLISH_MARKER,
                ),
                ft.Row(
                    [secondary_button(ACTION_COPY_FILENAME, on_click=_copy_filename)],
                    spacing=SPACE_SM,
                ),
            ],
            spacing=SPACE_XS,
            tight=True,
            expand=True,
        ),
        helper=MSG_FILENAME_PREVIEW_HELPER,
    )
    vorschlag_body.append(filename_editor)
    out.append(
        review_section(
            SECTION_DATEINAME,
            ft.Column(vorschlag_body, spacing=SPACE_SM, tight=True),
        )
    )
    out.append(
        review_section(
            SECTION_ENTSCHEIDEN,
            ft.Column(
                [
                    ft.Text(detail.decision_prompt, size=13),
                    _next_action_row(state, detail),
                ],
                spacing=SPACE_SM,
                tight=True,
            ),
        )
    )
    out.append(_finalization_declutter_panel(state, vm, detail))
    out.append(
        review_section(
            "Kopieren",
            _copy_actions_row(state, detail),
            subtitle=MSG_SAFETY_LINE_NO_FINAL,
        )
    )
    advanced: list[ft.Control] = []
    action_row = build_configuration_coverage_action_row(state, detail)
    if action_row is not None:
        advanced.append(action_row)
    advanced.append(build_duplicate_config_remediation_panel(state))
    if state.configuration_rule_draft is not None:
        advanced.append(
            build_configuration_rule_draft_panel(
                state, state.configuration_rule_draft
            )
        )
    apply_panel = build_configuration_rule_apply_panel(state)
    if apply_panel is not None:
        advanced.append(apply_panel)
    advanced.append(_oracle_dev_box(state, vm))
    advanced.append(_finalization_dry_run_panel(state, vm))
    advanced.append(_sandbox_final_write_panel(state, vm))
    if advanced:
        out.append(
            section_block(
                "Erweiterte Werkzeuge (optional)",
                ft.Column(advanced, spacing=10, tight=True),
                subtitle="Nicht nötig für die normale Prüfung",
            )
        )
    out.append(_developer_tools_collapsed(state, vm, detail))
    return out


def build_review_page(state: UiV2State) -> ft.Control:
    vm = build_review_page_vm(state)
    items: list[ft.Control] = [
        page_header(
            vm.title,
            subtitle=MSG_USER_REVIEW_SUBTITLE,
        ),
        ft.Text(vm.final_write_user_answer, size=12),
        ft.Text(vm.safety_line_declutter, size=12),
    ]

    if vm.empty:
        items.append(
            empty_state(
                vm.empty_title or EMPTY_REVIEW_TITLE,
                detail=MSG_EMPTY_REVIEW_HELP,
                icon=ft.Icons.FACT_CHECK_OUTLINED,
                compact=True,
            )
        )

        def _on_go_workspace(_e: ft.ControlEvent) -> None:
            if state.navigate is not None:
                state.navigate(NAV_WORKSPACE)
            elif state.refresh is not None:
                state.refresh()

        def _copy_oracle(_e: ft.ControlEvent) -> None:
            copy_text_to_state_and_clipboard(
                state,
                build_oracle_command_copy_text(),
                kind=ACTION_COPY_ORACLE,
            )
            if state.refresh is not None:
                state.refresh()

        def _on_create_folders(_e: ft.ControlEvent) -> None:
            result = ensure_track_b_dev_folders_if_requested(
                explicit_user_action=True
            )
            state.track_b_dev_defaults_folder_feedback = result.message
            state.track_b_dev_defaults_folder_feedback_error = not result.ok
            if state.refresh is not None:
                state.refresh()

        if is_track_b_dev_defaults_enabled():
            apply_track_b_dev_folder_defaults_to_state(state)

        items.append(ft.Text(MSG_EMPTY_REVIEW_HELP, size=12))
        items.append(
            ft.Row(
                [
                    secondary_button(
                        ACTION_OPEN_WORKSPACE,
                        on_click=_on_go_workspace,
                    ),
                    secondary_button(
                        ACTION_CREATE_CONTROLLED_FOLDERS,
                        on_click=_on_create_folders,
                    ),
                ],
                spacing=8,
                wrap=True,
            )
        )
        if state.track_b_dev_defaults_folder_feedback:
            items.append(
                ft.Text(state.track_b_dev_defaults_folder_feedback, size=11)
            )
        # Oracle copy stays available, but only under technical details.
        items.append(
            collapsible_details(
                MSG_REVIEW_FROM_REAL_RUN,
                MSG_REVIEW_NO_FILE_MUTATION,
                MSG_UNCLEAR_CASES_STAY_REVIEW,
                MSG_BUCKETS_SEPARATED,
                MSG_ORACLE_AVAILABLE,
                vm.oracle_command,
                MSG_ORACLE_NO_AUTO_RUN,
                ACTION_COPY_ORACLE,
                *vm.separation_notes,
                title=SECTION_TECHNISCHE,
                initially_expanded=False,
            )
        )
        items.append(
            ft.Row(
                [
                    secondary_button(
                        ACTION_COPY_ORACLE,
                        on_click=_copy_oracle,
                    ),
                ],
                spacing=8,
                wrap=True,
            )
        )
        return page_scaffold(*items)

    items.append(_ready_cases_panel(vm))
    items.append(_review_cases_panel(vm))
    items.append(
        ft.Text(
            REVIEW_ACCORDION_LAYOUT_MARKER,
            size=1,
            color=COLOR_SURFACE,
            selectable=False,
        )
    )

    accordion_blocks: list[ft.Control] = []
    open_key = vm.open_review_item_id
    for row in vm.list_items:
        key = row.item_key
        is_open = bool(open_key and key == open_key)

        def _toggle(_e: ft.ControlEvent, item_key: str = key) -> None:
            toggle_review_item_details(state, item_key)
            if state.refresh is not None:
                state.refresh()

        card = render_review_summary_card(row, is_open=is_open, on_toggle=_toggle)
        block_controls: list[ft.Control] = [card]
        if is_open and vm.selected_detail is not None:
            if vm.selected_detail.item_key == key:
                block_controls.append(
                    render_review_inline_detail(state, vm, vm.selected_detail)
                )
        accordion_blocks.append(
            ft.Column(block_controls, spacing=SPACE_XS, tight=True)
        )

    items.append(
        section_block(
            f"{vm.review_count} Dokument(e) zur Prüfung",
            stacked_list(*accordion_blocks),
            subtitle="Zur Prüfung — kompakte Übersicht, Details unter dem Dokument",
        )
    )

    items.append(
        collapsible_details(
            MSG_REVIEW_NO_FILE_MUTATION,
            MSG_NO_FINAL_APPROVAL,
            MSG_TARGET_PATHS_VORSCHAU_ONLY,
            MSG_EMPTY_OUTPUT_EXPLAIN,
            MSG_SAFETY_LINE_NO_FINAL,
            MSG_FINAL_WRITE_USER_ANSWER,
            *vm.separation_notes,
            title="Weitere Hinweise",
            initially_expanded=False,
        )
    )
    return page_scaffold(*items)
