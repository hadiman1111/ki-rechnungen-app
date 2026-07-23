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
from invoice_tool.ui_v2.preview_export import resolve_preview_naming
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
    if detail.planned_destination:
        planned_for_naming = ProcessingPlannedDestination(
            document_name=detail.source_filename or detail.document_label,
            planned_path=detail.planned_destination,
            destination_label=detail.planned_action,
            preview_only=True,
            applied=False,
        )
    naming = resolve_preview_naming(
        source_filename=detail.source_filename or detail.document_label,
        review_required=True,
        planned=planned_for_naming,
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
        naming_reason=naming.naming_reason,
        naming_not_final=MSG_NAMING_NOT_FINAL,
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
        if detail.naming_reason:
            detail_fields.insert(
                insert_at, (MSG_FIELD_NAMING_REASON, detail.naming_reason)
            )
            insert_at += 1
        if detail.planned_target:
            detail_fields.insert(
                insert_at, (MSG_FIELD_PLANNED_TARGET, detail.planned_target)
            )
            insert_at += 1
        detail_fields.insert(insert_at, ("Benennung", detail.naming_not_final))
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
