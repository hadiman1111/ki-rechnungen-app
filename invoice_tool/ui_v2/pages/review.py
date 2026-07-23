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
    calls_run_once: bool = False
    writes_final_files: bool = False
    mutates_input: bool = False
    touches_real_invoice_folders: bool = False
    claims_saas_ready: bool = False
    claims_production_ready: bool = False


def _detail_from_item_vm(item: ReviewItemViewModel) -> ReviewDetailItemVM:
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
    if selected_key:
        for detail in detail_items:
            key = detail.item_key or detail.document_id
            if key == selected_key:
                selected_detail = _build_selected_detail(
                    detail,
                    safety_line=review_safety_line(flow),
                    export_preview_summary=export_summary,
                    excluded=key in bag.excluded_from_export_preview_keys,
                    checked=key in bag.checked_preview_keys,
                )
                break

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
