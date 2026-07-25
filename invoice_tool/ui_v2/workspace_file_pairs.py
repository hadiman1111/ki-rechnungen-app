"""Aligned workspace live file-pair rows (original ↔ proposed output).

UI/state mapping only. Does not process invoices, write files, or call run_once.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    LABEL_NO_PROPOSAL_YET,
    clean_user_facing_filename,
)
from invoice_tool.ui_v2.workspace_input_listing import MSG_FILES_FOUND, MSG_NO_FILES_IN_INPUT

LIVE_FILE_PAIRS_MARKER = "workspace_live_file_pairs_v1"
LIVE_FILE_PAIR_ROW_MARKER = "workspace_live_file_pair_row_v1"
LIVE_PROPOSAL_UPDATE_MARKER = "workspace_live_proposal_update_v1"
JUST_IN_TIME_STATUS = "PARTIAL"  # synchronous adapter: post-result / post-batch only

MSG_NOT_CHECKED = "Noch nicht geprüft"
MSG_NO_PROPOSAL = LABEL_NO_PROPOSAL_YET  # "Noch kein Vorschlag"
MSG_NEED_OUTPUT_FOLDER = "Bitte Ausgangsordner wählen."
MSG_ROW_CHECKING = "Wird geprüft …"
MSG_PROPOSAL_CREATED = "Vorschlag erstellt"
MSG_ROW_REVIEW = "Zur Prüfung"
MSG_ROW_ERROR = "Fehler / nicht lesbar"
MSG_PAIR_STATUS_INTEGRATED = "file_pair_integrated_status_v1"

STATUS_NEED_OUTPUT = "need_output_folder"
STATUS_NOT_CHECKED = "not_checked"
STATUS_CHECKING = "checking"
STATUS_PROPOSED = "proposed"
STATUS_REVIEW = "review"
STATUS_ERROR = "error"


@dataclass(frozen=True)
class WorkspaceFilePairRow:
    """One stable input ↔ output proposal row."""

    index: int
    source_filename: str
    proposed_filename: str
    output_status: str
    output_display: str
    status_label: str
    has_proposal: bool
    marker: str = LIVE_FILE_PAIR_ROW_MARKER


@dataclass(frozen=True)
class WorkspaceLiveFilePairsVM:
    """Live file-pair panel view model for the Arbeitsbereich."""

    rows: tuple[WorkspaceFilePairRow, ...]
    input_count: int
    checked_count: int
    review_count: int
    files_found_label: str
    empty_message: str | None
    output_folder_selected: bool
    run_active: bool
    has_proposals: bool
    marker: str = LIVE_FILE_PAIRS_MARKER
    proposal_update_marker: str = LIVE_PROPOSAL_UPDATE_MARKER
    just_in_time_status: str = JUST_IN_TIME_STATUS
    integrated_status_marker: str = MSG_PAIR_STATUS_INTEGRATED
    implies_final_write: bool = False


def _proposal_map_from_planned(
    planned: Sequence[object],
) -> dict[str, tuple[str, str]]:
    """Map document_name → (suggested_filename, status_hint)."""

    out: dict[str, tuple[str, str]] = {}
    for item in planned:
        source = str(getattr(item, "document_name", "") or "").strip()
        if not source:
            continue
        suggested = clean_user_facing_filename(
            getattr(item, "suggested_filename", None)
            or getattr(item, "approved_preview_filename", None)
            or ""
        )
        coverage = str(getattr(item, "configuration_coverage_status", "") or "").casefold()
        guidance = str(getattr(item, "user_guidance", "") or "").casefold()
        status_hint = STATUS_PROPOSED
        if "fehl" in coverage or "error" in coverage or "nicht lesbar" in guidance:
            status_hint = STATUS_ERROR
        elif "review" in coverage or "unklar" in coverage or "prüfung" in guidance:
            status_hint = STATUS_REVIEW
        out[source] = (suggested, status_hint)
    return out


def _proposal_map_from_results(
    results: Sequence[object],
) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for item in results:
        source = str(
            getattr(item, "source_filename", None)
            or getattr(item, "document_name", None)
            or getattr(item, "filename", None)
            or ""
        ).strip()
        if not source:
            continue
        raw_target = (
            getattr(item, "target_filename", None)
            or getattr(item, "target_hint", None)
            or getattr(item, "destination_summary", None)
            or ""
        )
        target = clean_user_facing_filename(str(raw_target or "").rsplit("/", 1)[-1])
        if target == source:
            target = ""
        failed = bool(getattr(item, "failed", False))
        status_label = str(getattr(item, "status_label", "") or "").casefold()
        if failed or "fehl" in status_label or "error" in status_label:
            out[source] = (target, STATUS_ERROR)
        else:
            out[source] = (target, STATUS_PROPOSED if target else STATUS_REVIEW)
    return out


def build_live_file_pairs_vm(
    *,
    input_filenames: Sequence[str],
    output_folder_selected: bool,
    run_active: bool = False,
    planned_destinations: Sequence[object] = (),
    display_results: Sequence[object] = (),
    review_count: int = 0,
    empty_input_message: str | None = None,
) -> WorkspaceLiveFilePairsVM:
    """Build aligned live pairs from input listing + optional proposals.

    Before a check: status text only (no fake output filenames).
    During check: row status „Wird geprüft …“.
    After check: proposed filenames on the same row as the original.
    """

    names = tuple(str(n).strip() for n in input_filenames if str(n).strip())
    proposals: dict[str, tuple[str, str]] = {}
    if planned_destinations:
        proposals.update(_proposal_map_from_planned(planned_destinations))
    if display_results and not proposals:
        proposals.update(_proposal_map_from_results(display_results))

    rows: list[WorkspaceFilePairRow] = []
    checked = 0
    for index, source in enumerate(names):
        proposed, hint = proposals.get(source, ("", STATUS_NOT_CHECKED))
        has_proposal = bool(proposed)
        if not output_folder_selected:
            status = STATUS_NEED_OUTPUT
            display = MSG_NEED_OUTPUT_FOLDER
            label = MSG_NEED_OUTPUT_FOLDER
        elif run_active and not has_proposal:
            status = STATUS_CHECKING
            display = MSG_ROW_CHECKING
            label = MSG_ROW_CHECKING
        elif has_proposal:
            status = hint if hint in {STATUS_ERROR, STATUS_REVIEW, STATUS_PROPOSED} else STATUS_PROPOSED
            display = proposed
            if status == STATUS_ERROR:
                label = MSG_ROW_ERROR
            elif status == STATUS_REVIEW:
                label = MSG_ROW_REVIEW
            else:
                label = MSG_PROPOSAL_CREATED
            checked += 1
        else:
            status = STATUS_NOT_CHECKED
            display = MSG_NOT_CHECKED
            label = MSG_NOT_CHECKED
            # Alternate wording still accepted in UI tests.
            if not display:
                display = MSG_NO_PROPOSAL
        rows.append(
            WorkspaceFilePairRow(
                index=index,
                source_filename=source,
                proposed_filename=proposed,
                output_status=status,
                output_display=display,
                status_label=label,
                has_proposal=has_proposal,
            )
        )

    if names:
        files_label = MSG_FILES_FOUND.format(count=len(names))
        empty_msg = None
    else:
        files_label = MSG_FILES_FOUND.format(count=0)
        empty_msg = empty_input_message or MSG_NO_FILES_IN_INPUT

    return WorkspaceLiveFilePairsVM(
        rows=tuple(rows),
        input_count=len(names),
        checked_count=checked,
        review_count=int(review_count or 0),
        files_found_label=files_label,
        empty_message=empty_msg if not names else None,
        output_folder_selected=bool(output_folder_selected),
        run_active=bool(run_active),
        has_proposals=any(r.has_proposal for r in rows),
    )


def merge_input_names_with_proposal_sources(
    listed: Sequence[str],
    proposal_sources: Mapping[str, object] | Sequence[str],
) -> tuple[str, ...]:
    """Keep listing order stable; append unknown proposal sources at the end."""

    ordered: list[str] = []
    seen: set[str] = set()
    for name in listed:
        cleaned = str(name or "").strip()
        if cleaned and cleaned not in seen:
            ordered.append(cleaned)
            seen.add(cleaned)
    extras = (
        proposal_sources.keys()
        if isinstance(proposal_sources, Mapping)
        else proposal_sources
    )
    for name in extras:
        cleaned = str(name or "").strip()
        if cleaned and cleaned not in seen:
            ordered.append(cleaned)
            seen.add(cleaned)
    return tuple(ordered)


__all__ = (
    "JUST_IN_TIME_STATUS",
    "LIVE_FILE_PAIRS_MARKER",
    "LIVE_FILE_PAIR_ROW_MARKER",
    "LIVE_PROPOSAL_UPDATE_MARKER",
    "MSG_NEED_OUTPUT_FOLDER",
    "MSG_NO_PROPOSAL",
    "MSG_NOT_CHECKED",
    "MSG_PAIR_STATUS_INTEGRATED",
    "MSG_PROPOSAL_CREATED",
    "MSG_ROW_CHECKING",
    "MSG_ROW_ERROR",
    "MSG_ROW_REVIEW",
    "STATUS_CHECKING",
    "STATUS_ERROR",
    "STATUS_NEED_OUTPUT",
    "STATUS_NOT_CHECKED",
    "STATUS_PROPOSED",
    "STATUS_REVIEW",
    "WorkspaceFilePairRow",
    "WorkspaceLiveFilePairsVM",
    "build_live_file_pairs_vm",
    "merge_input_names_with_proposal_sources",
)
