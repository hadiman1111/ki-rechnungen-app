"""Zur Prüfung page — Track-B UI-v2 review bucket usability (Prompt 15/34).

Honest empty state by default. Items appear only from ProcessingRunState
after a real run injects them. No fake documents, no PDF processing,
no folder scan, no file mutation, no processing-core imports.

Preview-only actions mutate in-memory UiV2 review state only — never
run_once, never final writes, never productive export.
"""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from invoice_tool.ui_v2.components import (
    collapsible_details,
    compact_entry_row,
    empty_state,
    page_header,
    page_scaffold,
    secondary_button,
    section_block,
    stacked_list,
    status_badge,
)
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
    build_configuration_coverage_action_row,
    build_configuration_rule_action_labels,
    build_configuration_rule_draft_panel,
)
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
    """Visible Review-bucket list row (Prompt 15/34)."""

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
    calls_run_once: bool = False
    writes_final_files: bool = False
    mutates_input: bool = False
    touches_real_invoice_folders: bool = False
    claims_saas_ready: bool = False
    claims_production_ready: bool = False


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


def _build_list_items(
    detail_items: tuple[ReviewDetailItemVM, ...],
    *,
    selected_key: str | None,
    checked_keys: set[str],
    excluded_keys: set[str],
) -> tuple[ReviewListItemVM, ...]:
    rows: list[ReviewListItemVM] = []
    for detail in detail_items:
        key = detail.item_key or detail.document_id or detail.document_label
        checked = key in checked_keys
        excluded = key in excluded_keys
        rows.append(
            ReviewListItemVM(
                item_key=key,
                source_filename=detail.source_filename or detail.document_label,
                category=detail.category or MSG_CATEGORY_REVIEW,
                reason=detail.reason,
                planned_action=detail.planned_action,
                planned_destination=detail.planned_destination,
                confidence_or_status=detail.suggested_status,
                preview_only_badge=detail.preview_only_badge,
                no_final_write_badge=detail.no_final_write_badge,
                productive_blocked_badge=detail.productive_blocked_badge,
                selected=bool(selected_key and key == selected_key),
                checked_preview=checked,
                excluded_from_export_preview=excluded,
                preview_status_label=_preview_status_label(
                    checked=checked, excluded=excluded
                ),
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

    list_items = _build_list_items(
        detail_items,
        selected_key=selected_key,
        checked_keys=bag.checked_preview_keys,
        excluded_keys=bag.excluded_from_export_preview_keys,
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
        calls_run_once=False,
        writes_final_files=False,
        mutates_input=False,
        touches_real_invoice_folders=False,
        claims_saas_ready=False,
        claims_production_ready=False,
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
        ft.Text("final_write_allowed: false", size=12),
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
        ft.Text("final_write_allowed: false", size=12),
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


def build_review_page(state: UiV2State) -> ft.Control:
    vm = build_review_page_vm(state)
    queue = build_review_queue_view_model(state.processing_run_state)
    items: list[ft.Control] = [
        page_header(vm.title, subtitle="Unklare Fälle aus dem Lauf prüfen."),
        ft.Text(vm.preview_only_banner, size=12),
        ft.Text(vm.empty_output_explanation, size=12),
    ]

    if vm.empty:
        items.append(
            empty_state(
                vm.empty_title or EMPTY_REVIEW_TITLE,
                detail=None,
                icon=ft.Icons.FACT_CHECK_OUTLINED,
                compact=True,
            )
        )
        items.append(
            collapsible_details(
                MSG_REVIEW_FROM_REAL_RUN,
                MSG_REVIEW_NO_FILE_MUTATION,
                MSG_UNCLEAR_CASES_STAY_REVIEW,
                MSG_BUCKETS_SEPARATED,
                *vm.separation_notes,
                title="Details anzeigen",
            )
        )
        items.append(
            section_block(
                "Preview-Aktionen",
                _preview_action_row(state, enabled=False),
                subtitle="Nur UI-Vorschau — keine finalen Dateien",
            )
        )
        items.append(
            section_block(
                "Prüfaktionen",
                _legacy_action_row(queue),
                subtitle="Noch nicht verbunden",
            )
        )
        return page_scaffold(*items)

    review_rows: list[ft.Control] = []
    for row in vm.list_items:
        fields: list[tuple[str, str]] = [
            ("Status", row.category),
            (MSG_FIELD_REVIEW_REASON, row.reason),
            ("Konfidenz/Status", row.confidence_or_status),
            ("Preview-Status", row.preview_status_label),
            ("Marker", f"{row.preview_only_badge} · {row.no_final_write_badge}"),
        ]
        if row.planned_destination or row.planned_action:
            planned = row.planned_destination or row.planned_action or ""
            if row.planned_action and row.planned_destination:
                planned = f"{row.planned_action}: {row.planned_destination}"
            fields.append((MSG_FIELD_PLANNED_TARGET, planned))
        key = row.item_key

        def _select(_e: ft.ControlEvent, item_key: str = key) -> None:
            select_review_item(state, item_key)
            if state.refresh is not None:
                state.refresh()

        trailing = status_badge(
            "Ausgewählt" if row.selected else "Öffnen",
            tone="active" if row.selected else "neutral",
        )
        entry = compact_entry_row(
            row.source_filename,
            *fields,
            trailing=trailing,
        )
        review_rows.append(
            ft.Container(
                content=entry,
                on_click=_select,
                ink=True,
                bgcolor=None,
            )
        )

    items.append(
        section_block(
            f"{vm.review_count} Dokument(e) zur Prüfung",
            stacked_list(*review_rows),
        )
    )

    if vm.selected_detail is not None:
        detail = vm.selected_detail
        detail_fields = [
            ("Quelldatei", detail.source_filename),
            (MSG_FIELD_REVIEW_REASON, detail.review_reason),
            ("Kategorie", detail.category),
            ("Status", detail.confidence_or_status),
            ("Sicherheitsstatus", detail.safety_status),
            ("Export-Vorschau", detail.export_preview_status),
            ("Produktiv", detail.no_productive_processing_status),
            ("Originale", detail.originals_unchanged),
            ("Hinweis", detail.preview_only_banner),
            ("Output", detail.empty_output_explanation),
        ]
        insert_at = 2
        if detail.preview_filename:
            detail_fields.insert(
                insert_at, (MSG_FIELD_PREVIEW_FILENAME, detail.preview_filename)
            )
            insert_at += 1
        if detail.suggested_filename:
            detail_fields.insert(
                insert_at, ("Vorgeschlagener Dateiname", detail.suggested_filename)
            )
            insert_at += 1
        if detail.matched_configuration_name:
            detail_fields.insert(
                insert_at,
                (MSG_FIELD_CONFIGURATION, detail.matched_configuration_name),
            )
            insert_at += 1
        if detail.matched_configuration_reason:
            detail_fields.insert(
                insert_at,
                (MSG_FIELD_MATCHING_REASON, detail.matched_configuration_reason),
            )
            insert_at += 1
        if detail.condition_results:
            cond_txt = "; ".join(
                str(c.get("reason") or c.get("condition_type") or c)
                for c in detail.condition_results
            )
            detail_fields.insert(
                insert_at, (MSG_FIELD_CONDITION_RESULTS, cond_txt)
            )
            insert_at += 1
        if detail.missing_configuration_rule:
            detail_fields.insert(
                insert_at,
                (
                    MSG_FIELD_MISSING_CONFIGURATION_RULE,
                    detail.missing_configuration_rule,
                ),
            )
            insert_at += 1
        if detail.available_configurations:
            names = ", ".join(
                str(c.get("configuration_name") or c.get("name") or "?")
                for c in detail.available_configurations
            )
            detail_fields.insert(
                insert_at, (MSG_FIELD_AVAILABLE_CONFIGURATIONS, names)
            )
            insert_at += 1
        if detail.evaluated_configuration_candidates:
            parts = []
            for candidate in detail.evaluated_configuration_candidates:
                status = "ja" if candidate.get("matched") else "nein"
                parts.append(
                    f"{candidate.get('configuration_name')}: {status}"
                    f" ({candidate.get('reason') or ''})"
                )
            detail_fields.insert(
                insert_at,
                (MSG_FIELD_EVALUATED_CANDIDATES, "; ".join(parts)),
            )
            insert_at += 1
        if detail.configuration_coverage_status or detail.user_guidance:
            coverage_txt = detail.configuration_coverage_status or "—"
            if detail.missing_configuration_type:
                coverage_txt = (
                    f"{coverage_txt} ({detail.missing_configuration_type})"
                )
            detail_fields.insert(
                insert_at,
                (MSG_FIELD_CONFIGURATION_COVERAGE, coverage_txt),
            )
            insert_at += 1
        if detail.user_guidance:
            detail_fields.insert(
                insert_at,
                (MSG_FIELD_USER_GUIDANCE, detail.user_guidance),
            )
            insert_at += 1
        if detail.suggested_configuration_action:
            detail_fields.insert(
                insert_at,
                (
                    MSG_FIELD_SUGGESTED_CONFIGURATION_ACTION,
                    detail.suggested_configuration_action,
                ),
            )
            insert_at += 1
        if detail.configuration_rule_draft_available:
            detail_fields.insert(
                insert_at,
                (
                    MSG_FIELD_CONFIGURATION_RULE_DRAFT_AVAILABLE,
                    "true",
                ),
            )
            insert_at += 1
        if detail.proposed_configuration_name:
            detail_fields.insert(
                insert_at,
                (
                    MSG_FIELD_PROPOSED_CONFIGURATION_NAME,
                    detail.proposed_configuration_name,
                ),
            )
            insert_at += 1
        if detail.proposed_condition:
            detail_fields.insert(
                insert_at,
                (MSG_FIELD_PROPOSED_CONDITION, detail.proposed_condition),
            )
            insert_at += 1
        if detail.proposed_filename_pattern:
            detail_fields.insert(
                insert_at,
                (
                    MSG_FIELD_PROPOSED_FILENAME_PATTERN,
                    detail.proposed_filename_pattern,
                ),
            )
            insert_at += 1
        if detail.configuration_rule_draft_warning:
            detail_fields.insert(
                insert_at,
                (MSG_FIELD_DRAFT_WARNING, detail.configuration_rule_draft_warning),
            )
            insert_at += 1
        if detail.configuration_coverage_action_labels:
            detail_fields.insert(
                insert_at,
                (
                    "Konfigurationsaktionen",
                    " · ".join(detail.configuration_coverage_action_labels),
                ),
            )
            insert_at += 1
        detail_fields.insert(
            insert_at,
            (
                MSG_FIELD_REQUIRES_USER_CONFIRMATION,
                "true" if detail.requires_user_confirmation else "false",
            ),
        )
        insert_at += 1
        pattern_label = (
            detail.matched_configuration_pattern or detail.filename_pattern
        )
        if pattern_label:
            detail_fields.insert(
                insert_at, (MSG_FIELD_FILENAME_PATTERN, pattern_label)
            )
            insert_at += 1
        if detail.rendered_filename:
            detail_fields.insert(
                insert_at, ("Gerenderter Dateiname", detail.rendered_filename)
            )
            insert_at += 1
        if detail.placeholder_values:
            placeholder_text = ", ".join(
                f"{key}={value if value is not None else '—'}"
                for key, value in detail.placeholder_values
            )
            detail_fields.insert(
                insert_at, (MSG_FIELD_PLACEHOLDER_VALUES, placeholder_text)
            )
            insert_at += 1
        if detail.missing_placeholders:
            detail_fields.insert(
                insert_at,
                (
                    MSG_FIELD_MISSING_PLACEHOLDERS,
                    ", ".join(detail.missing_placeholders),
                ),
            )
            insert_at += 1
        if detail.amount_format:
            detail_fields.insert(
                insert_at, (MSG_FIELD_AMOUNT_FORMAT, detail.amount_format)
            )
            insert_at += 1
        direction = detail.document_direction or "Unklare_Rechnungsart"
        detail_fields.insert(insert_at, (MSG_FIELD_DOCUMENT_DIRECTION, direction))
        insert_at += 1
        category_label = (
            detail.business_category_display
            or detail.business_category
            or "Unklare_Zuordnung"
        )
        detail_fields.insert(insert_at, (MSG_FIELD_BUSINESS_CATEGORY, category_label))
        insert_at += 1
        name_label = detail.counterparty_name or detail.supplier
        if name_label:
            detail_fields.insert(
                insert_at, (MSG_FIELD_COUNTERPARTY_NAME, name_label)
            )
            insert_at += 1
        amount_value = detail.selected_amount or detail.amount
        if amount_value:
            detail_fields.insert(insert_at, (MSG_FIELD_AMOUNT, amount_value))
            insert_at += 1
        if detail.selected_amount_reason:
            detail_fields.insert(
                insert_at, (MSG_FIELD_AMOUNT_REASON, detail.selected_amount_reason)
            )
            insert_at += 1
        payment_value = detail.selected_payment_field or detail.payment_account
        if payment_value:
            detail_fields.insert(
                insert_at, (MSG_FIELD_PAYMENT_FIELD, payment_value)
            )
            insert_at += 1
        elif detail.selected_payment_field_reason:
            detail_fields.insert(insert_at, (MSG_FIELD_PAYMENT_FIELD, "—"))
            insert_at += 1
        if detail.selected_payment_field_reason:
            detail_fields.insert(
                insert_at,
                (
                    MSG_FIELD_PAYMENT_FIELD_REASON,
                    detail.selected_payment_field_reason,
                ),
            )
            insert_at += 1
        art_value = detail.selected_art or detail.document_type
        if art_value:
            detail_fields.insert(insert_at, (MSG_FIELD_DOCUMENT_ART, art_value))
            insert_at += 1
        if detail.selected_art_reason:
            detail_fields.insert(
                insert_at, (MSG_FIELD_ART_REASON, detail.selected_art_reason)
            )
            insert_at += 1
        if detail.missing_fields:
            detail_fields.insert(
                insert_at,
                ("fehlende Felder", ", ".join(detail.missing_fields)),
            )
            insert_at += 1
        if detail.naming_reason:
            detail_fields.insert(
                insert_at, (MSG_FIELD_NAMING_REASON, detail.naming_reason)
            )
            insert_at += 1
        if detail.naming_confidence:
            detail_fields.insert(
                insert_at, ("naming_confidence", detail.naming_confidence)
            )
            insert_at += 1
        if detail.planned_target:
            detail_fields.insert(
                insert_at, (MSG_FIELD_PLANNED_TARGET, detail.planned_target)
            )
            insert_at += 1
        if detail.rerun_preview_after_rule_change:
            detail_fields.insert(
                insert_at,
                (MSG_PREVIEW_RECOMPUTED, "true"),
            )
            insert_at += 1
            detail_fields.insert(
                insert_at,
                (
                    "previous_matched_configuration",
                    detail.previous_matched_configuration or "—",
                ),
            )
            insert_at += 1
            detail_fields.insert(
                insert_at,
                (
                    "new_matched_configuration",
                    detail.new_matched_configuration or "—",
                ),
            )
            insert_at += 1
            detail_fields.insert(
                insert_at,
                ("rule_applied", "true" if detail.rule_applied else "false"),
            )
            insert_at += 1
            if detail.applied_configuration_name:
                detail_fields.insert(
                    insert_at,
                    (
                        "applied_configuration_name",
                        detail.applied_configuration_name,
                    ),
                )
                insert_at += 1
            if detail.applied_configuration_condition:
                detail_fields.insert(
                    insert_at,
                    (
                        "applied_configuration_condition",
                        detail.applied_configuration_condition,
                    ),
                )
                insert_at += 1
            detail_fields.insert(
                insert_at,
                (MSG_RULE_SAVED, MSG_APPLY_PREVIEW_ONLY),
            )
            insert_at += 1
            detail_fields.insert(
                insert_at,
                (MSG_NO_FINAL_PROCESSING, MSG_ORIGINALS_UNCHANGED),
            )
            insert_at += 1
        detail_fields.insert(
            insert_at, ("Benennung noch nicht final", detail.naming_not_final)
        )
        items.append(
            section_block(
                "Prüffall-Details",
                stacked_list(
                    compact_entry_row(detail.source_filename, *detail_fields)
                ),
                subtitle="Auswahl aus der Prüfliste",
            )
        )
        action_row = build_configuration_coverage_action_row(state, detail)
        if action_row is not None:
            items.append(action_row)
        if state.configuration_rule_draft is not None:
            items.append(
                build_configuration_rule_draft_panel(
                    state, state.configuration_rule_draft
                )
            )
        elif state.configuration_rule_manual_keep_unclear:
            items.append(
                section_block(
                    ACTION_MANUAL_KEEP_UNCLEAR,
                    ft.Text(
                        state.configuration_rule_draft_feedback
                        or "Keine Regel gespeichert — Unklar bleibt aktiv.",
                        size=12,
                    ),
                    subtitle="Manuelle Prüfung",
                )
            )
        apply_panel = build_configuration_rule_apply_panel(state)
        if apply_panel is not None:
            items.append(apply_panel)
        items.append(_decision_status_panel(detail))
        items.append(_finalization_preview_batch_panel(vm))
        items.append(_finalization_dry_run_panel(state, vm))
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

        items.append(
            section_block(
                "Vorschlag bearbeiten (Dateiname)",
                ft.TextField(
                    value=draft_value,
                    label="Vorschau-Dateiname (editierbar)",
                    on_change=_on_filename_change,
                    dense=True,
                ),
                subtitle="Nur State — keine Dateischreibung",
            )
        )
        items.append(
            section_block(
                "Review-Entscheidungen",
                _decision_action_row(state, enabled=True),
                subtitle=MSG_NOT_FINAL_YET,
            )
        )

    detail_bits = [
        MSG_REVIEW_NO_FILE_MUTATION,
        MSG_NO_FINAL_APPROVAL,
        MSG_TARGET_PATHS_VORSCHAU_ONLY,
        MSG_EMPTY_OUTPUT_EXPLAIN,
        *vm.separation_notes,
        *(vm.error_section_lines or ()),
        *(vm.planned_preview_lines or ()),
    ]
    if vm.export_preview_summary:
        detail_bits.append(vm.export_preview_summary)
    if vm.safety_line:
        detail_bits.append(vm.safety_line)
    items.append(
        collapsible_details(
            *detail_bits,
            title="Details anzeigen",
        )
    )
    items.append(
        section_block(
            "Preview-Aktionen",
            _preview_action_row(state, enabled=vm.preview_actions_enabled),
            subtitle="Nur UI-Vorschau — keine finalen Dateien",
        )
    )
    items.append(
        section_block(
            "Prüfaktionen",
            _legacy_action_row(queue),
            subtitle="Noch nicht verbunden",
        )
    )
    return page_scaffold(*items)
