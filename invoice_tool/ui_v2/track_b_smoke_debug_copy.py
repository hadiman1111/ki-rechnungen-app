"""Track-B developer smoke copy/debug text helpers.

Builds plain-text diagnostics for manual smoke — no file mutation, no run_once.
"""

from __future__ import annotations

from typing import Any, Mapping

from invoice_tool.ui_v2.configuration_duplicate_remediation import (
    analyze_active_configuration_duplicates,
)

ACTION_COPY_CASE = "Prüffall als Text kopieren"
ACTION_COPY_DIAGNOSIS = "Diagnose kopieren"

# Layout marker for focused smoke UI tests / visual QA.
SMOKE_DEV_UI_LAYOUT_MARKER = "track_b_smoke_dev_ui_layout_v1_no_overlap"


def _g(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def build_prueffall_copy_text(
    detail: Any,
    *,
    draft: Any | None = None,
    profile_id: str | None = None,
) -> str:
    """Copy text for a single review case — includes PayPal guidance when present."""

    lines = [
        "# Prüffall (Track-B Smoke)",
        f"source_file: {_g(detail, 'source_filename') or '—'}",
        f"suggested_filename: {_g(detail, 'suggested_filename') or _g(detail, 'preview_filename') or '—'}",
        f"config/matching_status: {_g(detail, 'matched_configuration_name') or '—'}",
        f"matched_configuration_reason: {_g(detail, 'matched_configuration_reason') or '—'}",
        f"configuration_coverage_status: {_g(detail, 'configuration_coverage_status') or '—'}",
        f"user_guidance: {_g(detail, 'user_guidance') or '—'}",
        f"suggested_configuration_action: {_g(detail, 'suggested_configuration_action') or '—'}",
        f"missing_configuration_type: {_g(detail, 'missing_configuration_type') or '—'}",
        f"target_folder: {_g(detail, 'planned_target') or '—'}",
        f"review_decision: {_g(detail, 'review_decision_status') or _g(detail, 'category') or '—'}",
        f"finalization_state: {_g(detail, 'finalization_ready') or _g(detail, 'finalization_status') or '—'}",
        "safety_flags:",
        "  - preview_only",
        "  - no_final_write",
        "  - originals_unchanged",
        "  - final_write_allowed_for_production=false",
        "  - no productive processing",
    ]
    guidance = str(_g(detail, "user_guidance") or "")
    missing_type = str(_g(detail, "missing_configuration_type") or "").casefold()
    if "paypal" in guidance.casefold() or missing_type == "paypal":
        lines.append("paypal_guidance: present")
        lines.append(
            "  - PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden."
        )
    if draft is not None:
        lines.extend(
            [
                "proposed_config:",
                f"  - proposed_configuration_name: {_g(draft, 'proposed_configuration_name') or '—'}",
                f"  - proposed_condition: {_g(draft, 'proposed_condition') or '—'}",
                f"  - proposed_filename_pattern: {_g(draft, 'proposed_filename_pattern') or '—'}",
                f"  - proposed_destination_path: {_g(draft, 'proposed_destination_path') or '—'}",
            ]
        )
    if profile_id:
        lines.append(f"profile_id: {profile_id}")
    return "\n".join(lines)


def build_diagnosis_copy_text(
    detail: Any,
    *,
    draft: Any | None = None,
    profile_id: str | None = None,
    duplicate_report: str | None = None,
    run_state: Any | None = None,
) -> str:
    """Broader diagnosis blob including safety flags and duplicate report."""

    case = build_prueffall_copy_text(
        detail, draft=draft, profile_id=profile_id
    )
    lines = [
        "# Diagnose (Track-B Smoke)",
        case,
        "",
        "safety_flags_detail:",
        "  - final_write_allowed_for_production=false",
        "  - production_final_write_disabled",
        "  - no_run_once",
        "  - no_real_invoice_folders",
        "  - track_b_preview_only",
    ]
    if run_state is not None:
        lines.append(f"run_status: {_g(run_state, 'status') or '—'}")
        lines.append(f"run_id: {_g(run_state, 'run_id') or '—'}")
    if duplicate_report:
        lines.append("")
        lines.append(duplicate_report)
    elif profile_id:
        try:
            from invoice_tool.profile_store import load_profile_bundle

            bundle = load_profile_bundle(profile_id)
            report = analyze_active_configuration_duplicates(
                bundle.configurations
            ).report_text()
            lines.append("")
            lines.append(report)
        except Exception as exc:  # noqa: BLE001
            lines.append(f"duplicate_report_error: {exc}")
    return "\n".join(lines)


def copy_text_to_state_and_clipboard(
    state: Any,
    text: str,
    *,
    kind: str,
) -> str:
    """Store copy payload on state; push to page clipboard when available."""

    state.track_b_smoke_last_copy_text = text
    state.track_b_smoke_last_copy_kind = kind
    state.track_b_smoke_copy_feedback = f"{kind} in Zwischenablage / State kopiert."
    state.track_b_smoke_copy_feedback_error = False
    page = getattr(state, "page", None)
    if page is not None and hasattr(page, "set_clipboard"):
        try:
            page.set_clipboard(text)
        except Exception:  # noqa: BLE001
            state.track_b_smoke_copy_feedback = (
                f"{kind} im State gespeichert (Clipboard nicht verfügbar)."
            )
    return text


__all__ = (
    "ACTION_COPY_CASE",
    "ACTION_COPY_DIAGNOSIS",
    "SMOKE_DEV_UI_LAYOUT_MARKER",
    "build_diagnosis_copy_text",
    "build_prueffall_copy_text",
    "copy_text_to_state_and_clipboard",
)
