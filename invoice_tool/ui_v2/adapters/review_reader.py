"""Read-only review data for UI-v2."""

from __future__ import annotations

import logging

from invoice_tool.ui_v2.adapters.run_reader import _REVIEW_STATUSES, _load_report_data
from invoice_tool.ui_v2.view_models import ReviewItemVM, ReviewSummaryVM

logger = logging.getLogger(__name__)


def get_review_summary() -> ReviewSummaryVM:
    data, run = _load_report_data()

    if run.availability == "no_run":
        return ReviewSummaryVM(
            availability="no_run",
            review_count=None,
            run_timestamp=None,
        )

    if run.availability == "malformed" or not isinstance(data, dict):
        return ReviewSummaryVM(
            availability="malformed",
            review_count=None,
            run_timestamp=run.run_timestamp,
            warnings=run.warnings,
        )

    files = data.get("files")
    if not isinstance(files, list):
        return ReviewSummaryVM(
            availability="unknown",
            review_count=None,
            run_timestamp=run.run_timestamp,
            warnings=("Prüfdaten im letzten Laufbericht sind unvollständig.",),
        )

    items: list[ReviewItemVM] = []
    for entry in files:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "").lower()
        if status not in _REVIEW_STATUSES:
            continue
        notes = str(entry.get("notes") or "").strip()
        reason = notes or status
        items.append(
            ReviewItemVM(
                filename=str(entry.get("filename") or "—"),
                reason=reason,
                run_timestamp=run.run_timestamp,
                status_label=status,
                configuration_label=str(entry.get("type") or None) or None,
            )
        )

    if not items:
        return ReviewSummaryVM(
            availability="zero",
            review_count=0,
            items=tuple(),
            run_timestamp=run.run_timestamp,
        )

    return ReviewSummaryVM(
        availability="items",
        review_count=len(items),
        items=tuple(items),
        run_timestamp=run.run_timestamp,
    )
