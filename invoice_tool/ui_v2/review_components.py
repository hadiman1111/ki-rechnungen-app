"""Track-B review display helpers — pure text/view helpers, no mutation."""

from __future__ import annotations

from invoice_tool.ui_v2.review_state import ReviewFlowState

MSG_ERROR_SECTION = "Fehler (getrennt von Prüffällen)"
MSG_PLANNED_SECTION = "Geplante Ziele (Vorschau)"
MSG_SAFETY_SECTION = "Sicherheitsnachweis"


def review_error_section_lines(flow: ReviewFlowState) -> tuple[str, ...]:
    if not flow.error_items:
        return ()
    lines = [MSG_ERROR_SECTION]
    for item in flow.error_items[:32]:
        name = (item.document_name or "").strip() or "(ohne Name)"
        code = (item.error_code or "").strip()
        prefix = f"{name}: " if name else ""
        detail = f"{code}: {item.message}" if code else item.message
        lines.append(f"{prefix}{detail}")
    return tuple(lines)


def review_planned_preview_lines(flow: ReviewFlowState) -> tuple[str, ...]:
    if not flow.planned_destinations:
        return (MSG_PLANNED_SECTION, "Keine geplanten Ziele in diesem Lauf.")
    lines = [MSG_PLANNED_SECTION, "Vorschau only — keine Datei geschrieben."]
    for item in flow.planned_destinations[:32]:
        label = item.destination_label or "geplant"
        lines.append(f"{item.document_name} → {item.planned_path} ({label})")
    return tuple(lines)


def review_safety_line(flow: ReviewFlowState) -> str:
    return f"{MSG_SAFETY_SECTION}: {flow.safety_proof_line}"


__all__ = (
    "MSG_ERROR_SECTION",
    "MSG_PLANNED_SECTION",
    "MSG_SAFETY_SECTION",
    "review_error_section_lines",
    "review_planned_preview_lines",
    "review_safety_line",
)
