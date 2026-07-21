"""Runtime structural rendering checks for UI-v2 page trees."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import flet as ft

from invoice_tool.ui_v2.control_tree import collect_labels, control_label, iter_controls
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.theme import COLOR_CANVAS, COLOR_SURFACE, COLOR_SURFACE_ALT

OPAQUE_SURFACE_COLORS = {
    COLOR_CANVAS,
    COLOR_SURFACE,
    COLOR_SURFACE_ALT,
    "#f3f2ef",
    "#f8f7f4",
    "#f6f5f2",
    "#ffffff",
    "#faf9f6",
}


@dataclass
class RenderingFinding:
    page: str
    severity: str
    category: str
    message: str


@dataclass
class RenderingReport:
    findings: list[RenderingFinding] = field(default_factory=list)

    def add(self, page: str, severity: str, category: str, message: str) -> None:
        self.findings.append(RenderingFinding(page, severity, category, message))

    @property
    def blocking(self) -> list[RenderingFinding]:
        return [f for f in self.findings if f.severity in {"R0", "R1"}]


def _semantic_text_count(control: Any) -> int:
    count = 0
    if control.__class__.__name__ == "Text":
        value = getattr(control, "value", None)
        if isinstance(value, str) and value.strip():
            count += 1
    if control.__class__.__name__ in {"FilledButton", "OutlinedButton", "TextButton", "Dropdown", "Switch"}:
        count += 1
    content = getattr(control, "content", None)
    if content is not None:
        count += _semantic_text_count(content)
    for child in getattr(control, "controls", None) or []:
        count += _semantic_text_count(child)
    return count


def _is_opaque_surface(control: Any) -> bool:
    if control.__class__.__name__ != "Container":
        return False
    bgcolor = getattr(control, "bgcolor", None)
    return bgcolor in OPAQUE_SURFACE_COLORS


def _find_workflow_grid_layout_risk(root: Any, *, page: str, report: RenderingReport) -> None:
    """Legacy 3-phase workflow check — skip if new run panel is present."""
    labels = collect_labels(root)
    if "EINGANGSORDNER" in labels and "ERGEBNISORDNER" in labels:
        return
    phase_titles = {"Eingang", "Verarbeitung", "Ergebnisse"}
    for control in iter_controls(root):
        if control.__class__.__name__ != "Row":
            continue
        labels = collect_labels(control)
        if not (labels & phase_titles):
            continue
        child_count = len(getattr(control, "controls", None) or [])
        if child_count < 3:
            continue
        if getattr(control, "wrap", False):
            report.add(
                page,
                "R0",
                "workflow_grid_wrap",
                "Workflow Row uses wrap=True — collapses phase cards in Flet 0.85 scroll pages",
            )
        for child in getattr(control, "controls", None) or []:
            if child.__class__.__name__ != "Container":
                continue
            if getattr(child, "width", None) and getattr(child, "expand", False):
                report.add(
                    page,
                    "R0",
                    "workflow_grid_expand_width",
                    "Workflow column wrapper combines width + expand — known Flet 0.85 collapse pattern",
                )


def _find_page_scaffold_width_overflow(root: Any, *, page: str, report: RenderingReport) -> None:
    from invoice_tool.ui_v2.theme import APP_MIN_WIDTH, CONTENT_MAX_WIDTH, NAV_WIDTH, PAGE_PADDING

    max_host_width = APP_MIN_WIDTH - NAV_WIDTH
    max_safe_inner = max_host_width - (PAGE_PADDING * 2)
    if CONTENT_MAX_WIDTH > max_safe_inner:
        for control in iter_controls(root):
            if control.__class__.__name__ != "Container":
                continue
            if getattr(control, "width", None) == CONTENT_MAX_WIDTH:
                report.add(
                    page,
                    "R0",
                    "page_width_overflow",
                    (
                        f"Fixed width={CONTENT_MAX_WIDTH}px inside content host "
                        f"(~{max_host_width}px) blocks sidebar navigation clicks"
                    ),
                )
                return


def _find_workflow_card_fixed_height_risk(root: Any, *, page: str, report: RenderingReport) -> None:
    """Legacy 3-phase workflow cards — skip if new run panel is present."""
    labels = collect_labels(root)
    if "EINGANGSORDNER" in labels and "ERGEBNISORDNER" in labels:
        return
    phase_titles = {"Eingang", "Verarbeitung", "Ergebnisse"}
    from invoice_tool.ui_v2.theme import WORKFLOW_CARD_HEIGHT

    for control in iter_controls(root):
        if control.__class__.__name__ != "Container":
            continue
        height = getattr(control, "height", None)
        if not height or height < WORKFLOW_CARD_HEIGHT - 20:
            continue
        labels = collect_labels(control)
        if labels & phase_titles:
            report.add(
                page,
                "R1",
                "workflow_card_fixed_height",
                f"Workflow card {next(iter(labels & phase_titles))!r} uses fixed height={height}",
            )


_FILL_LAYOUT_KEYS = frozenset(
    {"ui-v2-page-fill", "ui-v2-list-detail-row", "ui-v2-list-panel", "ui-v2-detail-panel"}
)


def _find_oversized_empty_surfaces(root: Any, *, page: str, report: RenderingReport) -> None:
    for control in iter_controls(root):
        if control.__class__.__name__ != "Container":
            continue
        if getattr(control, "key", None) in _FILL_LAYOUT_KEYS:
            continue
        if not getattr(control, "expand", False):
            continue
        if not _is_opaque_surface(control):
            continue
        content = getattr(control, "content", None)
        if isinstance(content, ft.Column) and getattr(content, "expand", False):
            semantic = _semantic_text_count(control)
            if semantic < 5:
                report.add(
                    page,
                    "R0",
                    "opaque_surface",
                    (
                        f"Panel-style Container with expand=True and Column(expand=True) "
                        f"has only {semantic} semantic child control(s)"
                    ),
                )
        if isinstance(content, ft.Row) and getattr(content, "expand", False):
            if getattr(content, "key", None) not in _FILL_LAYOUT_KEYS and getattr(control, "key", None) not in _FILL_LAYOUT_KEYS:
                report.add(
                    page,
                    "R0",
                    "expand_row",
                    "Page content Row uses expand=True and can create full-height opaque surfaces",
                )
        if getattr(control, "key", None) == "ui-v2-content-host" and getattr(control, "bgcolor", None):
            report.add(page, "R0", "double_canvas", "content_host must not set bgcolor; shell root owns canvas")


def _assert_labels(page: str, root: Any, required: Iterable[str], report: RenderingReport) -> None:
    labels = collect_labels(root)
    for label in required:
        if label not in labels:
            report.add(page, "R0", "missing_content", f"Expected label not in control tree: {label!r}")


def _page_builders() -> dict[str, Callable[[UiV2State], ft.Control]]:
    from invoice_tool.ui_v2.pages.configurations import build_configurations_page
    from invoice_tool.ui_v2.pages.profiles import build_profiles_page
    from invoice_tool.ui_v2.pages.workspace import build_workspace_page

    return {
        "Arbeitsbereich": build_workspace_page,
        "Konfigurationen": build_configurations_page,
        "Profile": build_profiles_page,
    }


def audit_page_tree(page_name: str, root: Any, report: RenderingReport) -> None:
    _find_oversized_empty_surfaces(root, page=page_name, report=report)
    _find_page_scaffold_width_overflow(root, page=page_name, report=report)
    if page_name == "Arbeitsbereich":
        _find_workflow_grid_layout_risk(root, page=page_name, report=report)
        _find_workflow_card_fixed_height_risk(root, page=page_name, report=report)

    if page_name == "Arbeitsbereich":
        # Honest workspace: require workflow chrome; mapping headers only when real run data exists.
        _assert_labels(page_name, root, ("WORKFLOW", "Zielordner"), report)
        labels = collect_labels(root)
        has_mapping_headers = "EINGANGSORDNER" in labels and "ERGEBNISORDNER" in labels
        has_honest_empty = any(
            marker in labels
            for marker in (
                "Noch kein Verarbeitungslauf in dieser Oberfläche.",
                "Kein Lauf gestartet",
                "Keine Ergebnisse vorhanden",
                "Kein Ordner ausgewählt",
                "Noch keine Zuordnungen",
            )
        )
        if not has_mapping_headers and not has_honest_empty:
            report.add(
                page_name,
                "R0",
                "missing_content",
                "Workspace exposes neither real run mappings nor an honest empty state",
            )
    elif page_name == "Konfigurationen":
        _assert_labels(page_name, root, ("Bearbeiten", "Konfigurationen"), report)
        labels = collect_labels(root)
        if not any(label in labels for label in ("Hauptkonto", "American Express", "Privat", "Event Production")):
            report.add(page_name, "R0", "missing_content", "No configuration list entries found in control tree")
        if not any(label in labels for label in ("Hauptkonto", "American Express", "Privat", "Event Production", "Details")):
            report.add(page_name, "R0", "missing_content", "No configuration detail title found in control tree")
    elif page_name == "Profile":
        _assert_labels(page_name, root, ("SOMAA Profil", "Profile", "Erkennungsmodell", "Bearbeiten", "Duplizieren"), report)

    page_labels = [label for label in collect_labels(root) if label]
    if len(page_labels) < 3:
        report.add(page_name, "R0", "sparse_page", f"Page exposes only {len(page_labels)} text labels")


def audit_all_pages(state: UiV2State) -> RenderingReport:
    report = RenderingReport()
    for page_name, builder in _page_builders().items():
        audit_page_tree(page_name, builder(state), report)
    return report


def has_full_page_overlay(root: Any) -> bool:
    """True when page root is essentially one opaque expand container."""
    if root.__class__.__name__ != "Container":
        return False
    if not getattr(root, "expand", False):
        return False
    semantic = _semantic_text_count(root)
    return semantic < 5
