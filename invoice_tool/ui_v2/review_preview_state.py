"""Track-B Review-bucket preview-only local UI state (Prompt 15/34).

Mutates in-memory UiV2 review preview fields only.
Never calls run_once, never processes PDFs, never writes/moves/archives files,
never touches real invoice folders, never enables productive export.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)

MSG_CATEGORY_REVIEW = "Zur Prüfung"
MSG_BADGE_PREVIEW = "Vorschau"
MSG_BADGE_NO_FINAL_WRITE = "Keine finalen Dateien geschrieben"
MSG_BADGE_PRODUCTIVE_BLOCKED = "Produktiv gesperrt"
MSG_BADGE_ORIGINALS_UNCHANGED = "Originale unverändert"
MSG_FIELD_PLANNED_TARGET = "Geplantes Ziel"
MSG_FIELD_REVIEW_REASON = "Grund der Prüfung"
MSG_EMPTY_OUTPUT_EXPLAIN = (
    "Output bleibt in Vorschau/Dry-Run leer, bis ein späterer explizit "
    "freigegebener Export-/Finalisierungsschritt folgt. "
    "Keine finalen Dateien geschrieben."
)
MSG_PREVIEW_ONLY_BANNER = (
    "Preview only — Keine finalen Dateien geschrieben — Produktiv gesperrt"
)
MSG_NO_SAAS_READY = "nicht SaaS-ready"
MSG_NO_PRODUCTION_READY = "nicht production-ready"

ACTION_MARK_CHECKED_PREVIEW = "Als geprüft markieren (Preview)"
ACTION_KEEP_IN_REVIEW = "In Prüfung belassen"
ACTION_EXCLUDE_EXPORT_PREVIEW = "Aus Export-Vorschau ausschließen"
ACTION_RESET_SELECTION = "Auswahl zurücksetzen"

PREVIEW_ACTION_LABELS = (
    ACTION_MARK_CHECKED_PREVIEW,
    ACTION_KEEP_IN_REVIEW,
    ACTION_EXCLUDE_EXPORT_PREVIEW,
    ACTION_RESET_SELECTION,
)

STATUS_CHECKED_PREVIEW = "als geprüft (Preview)"
STATUS_IN_REVIEW = "Zur Prüfung"
STATUS_EXCLUDED_EXPORT = "aus Export-Vorschau ausgeschlossen"


def review_item_key(item: ProcessingReviewItem) -> str:
    """Stable in-memory key for selection / preview actions."""

    doc_id = (item.document_id or "").strip()
    if doc_id:
        return doc_id
    return (item.document_name or "").strip() or "dokument"


def planned_for_document(
    planned: tuple[ProcessingPlannedDestination, ...] | list[ProcessingPlannedDestination],
    document_name: str,
) -> ProcessingPlannedDestination | None:
    name = (document_name or "").strip()
    if not name:
        return None
    for entry in planned or ():
        if (entry.document_name or "").strip() == name:
            return entry
    return None


@dataclass
class ReviewPreviewUiState:
    """In-memory preview selection state — never persisted, never writes files."""

    selected_item_key: str | None = None
    checked_preview_keys: set[str] = field(default_factory=set)
    excluded_from_export_preview_keys: set[str] = field(default_factory=set)

    def reset(self) -> None:
        self.selected_item_key = None
        self.checked_preview_keys.clear()
        self.excluded_from_export_preview_keys.clear()


def get_review_preview_ui(state: Any) -> ReviewPreviewUiState:
    """Ensure UiV2State carries a ReviewPreviewUiState bag."""

    bag = getattr(state, "review_preview_ui", None)
    if isinstance(bag, ReviewPreviewUiState):
        return bag
    bag = ReviewPreviewUiState()
    try:
        state.review_preview_ui = bag
    except Exception:
        pass
    return bag


def select_review_item(state: Any, item_key: str | None) -> None:
    bag = get_review_preview_ui(state)
    cleaned = (item_key or "").strip() or None
    bag.selected_item_key = cleaned


def mark_checked_preview(state: Any, item_key: str | None = None) -> None:
    """Mark selected (or given) item as checked in preview — local state only."""

    bag = get_review_preview_ui(state)
    key = (item_key or bag.selected_item_key or "").strip()
    if not key:
        return
    bag.checked_preview_keys.add(key)
    bag.excluded_from_export_preview_keys.discard(key)
    bag.selected_item_key = key


def keep_in_review(state: Any, item_key: str | None = None) -> None:
    """Keep item in the Review bucket preview state (undo checked/excluded)."""

    bag = get_review_preview_ui(state)
    key = (item_key or bag.selected_item_key or "").strip()
    if not key:
        return
    bag.checked_preview_keys.discard(key)
    bag.excluded_from_export_preview_keys.discard(key)
    bag.selected_item_key = key


def exclude_from_export_preview(state: Any, item_key: str | None = None) -> None:
    """Exclude item from export-preview inclusion — local state only."""

    bag = get_review_preview_ui(state)
    key = (item_key or bag.selected_item_key or "").strip()
    if not key:
        return
    bag.excluded_from_export_preview_keys.add(key)
    bag.selected_item_key = key


def reset_preview_selection(state: Any) -> None:
    """Return to initial preview selection state (local only)."""

    get_review_preview_ui(state).reset()


def preview_action_mutates_files() -> bool:
    return False


def preview_actions_call_run_once() -> bool:
    return False


def preview_actions_process_pdfs() -> bool:
    return False


def preview_actions_touch_real_invoice_folders() -> bool:
    return False


def preview_actions_claim_saas_ready() -> bool:
    return False


def preview_actions_claim_production_ready() -> bool:
    return False


def review_keys_from_run(run: ProcessingRunState | None) -> tuple[str, ...]:
    run_state = run or ProcessingRunState()
    return tuple(review_item_key(item) for item in (run_state.review_items or ()))


__all__ = (
    "ACTION_EXCLUDE_EXPORT_PREVIEW",
    "ACTION_KEEP_IN_REVIEW",
    "ACTION_MARK_CHECKED_PREVIEW",
    "ACTION_RESET_SELECTION",
    "MSG_BADGE_NO_FINAL_WRITE",
    "MSG_BADGE_ORIGINALS_UNCHANGED",
    "MSG_BADGE_PREVIEW",
    "MSG_BADGE_PRODUCTIVE_BLOCKED",
    "MSG_CATEGORY_REVIEW",
    "MSG_EMPTY_OUTPUT_EXPLAIN",
    "MSG_FIELD_PLANNED_TARGET",
    "MSG_FIELD_REVIEW_REASON",
    "MSG_NO_PRODUCTION_READY",
    "MSG_NO_SAAS_READY",
    "MSG_PREVIEW_ONLY_BANNER",
    "PREVIEW_ACTION_LABELS",
    "STATUS_CHECKED_PREVIEW",
    "STATUS_EXCLUDED_EXPORT",
    "STATUS_IN_REVIEW",
    "ReviewPreviewUiState",
    "exclude_from_export_preview",
    "get_review_preview_ui",
    "keep_in_review",
    "mark_checked_preview",
    "planned_for_document",
    "preview_action_mutates_files",
    "preview_actions_call_run_once",
    "preview_actions_claim_production_ready",
    "preview_actions_claim_saas_ready",
    "preview_actions_process_pdfs",
    "preview_actions_touch_real_invoice_folders",
    "reset_preview_selection",
    "review_item_key",
    "review_keys_from_run",
    "select_review_item",
)
