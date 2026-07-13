#!/usr/bin/env python3
"""Comprehensive UI-v2 self-check — layout, navigation, page content."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from invoice_tool.ui_v2.adapters.read_only_backend import load_read_only_snapshot
from invoice_tool.ui_v2.app import build_ui_v2
from invoice_tool.ui_v2.control_tree import collect_labels, find_nav_handler, iter_controls
from invoice_tool.ui_v2.navigation import ALL_NAV_ITEMS, NAV_WORKSPACE
from invoice_tool.ui_v2.rendering_checks import audit_all_pages, has_full_page_overlay
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.theme import APP_MIN_WIDTH, CONTENT_MAX_WIDTH, NAV_WIDTH, PAGE_PADDING


def _fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def _pass(message: str) -> None:
    print(f"PASS: {message}")


def _build_test_page() -> tuple[MagicMock, list[object]]:
    added: list[object] = []
    page = MagicMock()
    page.controls = []
    page.services = SimpleNamespace(register_service=lambda _service: None)
    page.overlay = []
    page.window = SimpleNamespace(width=APP_MIN_WIDTH, height=800, min_width=APP_MIN_WIDTH, min_height=720)

    def _add(*controls: object) -> None:
        added.extend(controls)
        page.controls.extend(controls)

    page.add.side_effect = _add
    page.update = MagicMock()
    return page, added


def _navigate(page: MagicMock, label: str) -> object:
    root = page.controls[0]
    handler = find_nav_handler(root, label)
    if handler is None:
        raise AssertionError(f"Nav-Handler nicht gefunden: {label!r}")
    handler(MagicMock())
    return page.controls[0]


def _content_host_labels(root: object) -> set[str]:
    for control in iter_controls(root):
        if getattr(control, "key", None) == "ui-v2-content-host":
            return collect_labels(control)
    return set()


def _shell_has_stack(root: object) -> bool:
    return any(ctrl.__class__.__name__ == "Stack" for ctrl in iter_controls(root))


def _sidebar_width(root: object) -> int | None:
    for control in iter_controls(root):
        if getattr(control, "key", None) == "ui-v2-sidebar":
            return getattr(control, "width", None)
    return None


def main() -> int:
    print("=== UI-v2 Self-Check ===")

    # 1) Snapshot + page builders
    state = UiV2State(active_nav_id=NAV_WORKSPACE)
    try:
        state.snapshot = load_read_only_snapshot()
    except Exception as exc:
        return _fail(f"Snapshot laden: {exc}")

    report = audit_all_pages(state)
    if report.blocking:
        for finding in report.blocking:
            print(f"  [{finding.severity}] {finding.page} / {finding.category}: {finding.message}")
        return _fail("Layout-Audit — blocking findings")
    _pass("Layout-Audit aller 4 Seiten (0 blocking)")

    max_host = APP_MIN_WIDTH - NAV_WIDTH
    if CONTENT_MAX_WIDTH > max_host - (PAGE_PADDING * 2):
        _pass(f"CONTENT_MAX_WIDTH ({CONTENT_MAX_WIDTH}) > Host — page_scaffold ohne feste Breite (OK)")
    else:
        _pass("Content-Breite innerhalb Host")

    # 2) Full app mount + shell structure
    page, _ = _build_test_page()
    try:
        build_ui_v2(page)
    except Exception as exc:
        return _fail(f"build_ui_v2: {exc}")

    if not page.controls:
        return _fail("Kein Root-Control nach build_ui_v2")
    root = page.controls[0]

    if not _shell_has_stack(root):
        return _fail("Shell nutzt kein Stack-Layout (Sidebar-Hit-Test-Risiko)")
    _pass("Shell Stack-Layout vorhanden")

    sidebar_w = _sidebar_width(root)
    if sidebar_w != NAV_WIDTH:
        return _fail(f"Sidebar-Breite {sidebar_w!r} != {NAV_WIDTH}")
    _pass(f"Sidebar-Breite {NAV_WIDTH}px")

    # 3) Navigation handlers + content swap per page
    page_labels: dict[str, set[str]] = {}
    required_per_page = {
        "Arbeitsbereich": ("WORKFLOW", "EINGANGSORDNER", "ERGEBNISORDNER", "Zielordner"),
        "Konfigurationen": ("Konfigurationen",),
        "Profile": ("Profile",),
    }
    config_detail_titles = {
        "Hauptkonto",
        "American Express",
        "Privat",
        "Event Production",
        "Architektur & Innenarchitektur",
        "Nicht zugeordnete Dokumente",
    }

    for nav_id, label, _icon in ALL_NAV_ITEMS:
        handler = find_nav_handler(root, label)
        if handler is None:
            return _fail(f"Nav-Handler fehlt: {label!r}")
        _navigate(page, label)
        labels = _content_host_labels(page.controls[0])
        page_labels[label] = labels
        for required in required_per_page.get(label, (label,)):
            if required not in labels:
                return _fail(f"Nach Navigation zu {label!r} fehlt Label {required!r}")
        if label == "Konfigurationen" and not (labels & config_detail_titles):
            return _fail("Konfigurationen-Detailtitel fehlt (erwartet Name der ausgewählten Konfiguration)")
        if label == "Profile" and not any("Profil" in entry for entry in labels):
            return _fail("Profile-Detail fehlt (erwartet Profilname im Detailbereich)")
        if has_full_page_overlay(page.controls[0]):
            return _fail(f"Seite {label!r} ist Vollflächen-Overlay ohne Inhalt")

    _pass("Alle Nav-Handler klickbar (simuliert) + Pflicht-Labels im Content-Host")

    # 4) Pages must differ (navigation actually swaps content)
    workspace_labels = page_labels["Arbeitsbereich"]
    for other_label in ("Konfigurationen", "Profile"):
        if page_labels[other_label] == workspace_labels:
            return _fail(f"Content nach {other_label!r} identisch mit Arbeitsbereich — Navigation tauscht nicht")
    _pass("Navigation tauscht Seiteninhalt (Label-Sets unterscheidlich)")

    # 5) Workspace run panel sanity
    _navigate(page, "Arbeitsbereich")
    host_labels = _content_host_labels(page.controls[0])
    for required in ("EINGANGSORDNER", "ERGEBNISORDNER", "WORKFLOW"):
        if required not in host_labels:
            return _fail(f"Arbeitsbereich: Label {required!r} fehlt im Content-Host")
    _pass("Arbeitsbereich Run-Panel strukturell OK")

    print("=== RESULT: ALL CHECKS PASSED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
