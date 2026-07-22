"""Track-B UI-v2 navigation structure — non-GUI readiness checks."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.navigation import (
    ADMIN_NAV,
    ALL_NAV_IDS,
    ALL_NAV_ITEMS,
    DAILY_NAV,
    NAV_CONFIGURATIONS,
    NAV_PROFILES,
    NAV_REVIEW,
    NAV_SETTINGS,
    NAV_WORKSPACE,
)

ROOT = Path(__file__).resolve().parents[1]
NAV_MODULE = ROOT / "invoice_tool" / "ui_v2" / "navigation.py"
APP_MODULE = ROOT / "invoice_tool" / "ui_v2" / "app.py"
PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX",
    "voba",
    "/Users/",
    "Desktop/",
)


def test_navigation_contains_required_labels() -> None:
    labels = [label for _, label, _ in ALL_NAV_ITEMS]
    assert labels == [
        "Arbeitsbereich",
        "Konfigurationen",
        "Zur Prüfung",
        "Profile",
        "Einstellungen",
    ]
    assert "Arbeitsbereich" in labels
    assert "Konfigurationen" in labels
    assert "Profile" in labels
    assert "Zur Prüfung" in labels
    assert "Einstellungen" in labels


def test_navigation_order_matches_track_b_shell() -> None:
    assert [item[0] for item in DAILY_NAV] == [
        NAV_WORKSPACE,
        NAV_CONFIGURATIONS,
        NAV_REVIEW,
    ]
    assert [item[0] for item in ADMIN_NAV] == [NAV_PROFILES, NAV_SETTINGS]
    assert ALL_NAV_IDS == (
        NAV_WORKSPACE,
        NAV_CONFIGURATIONS,
        NAV_REVIEW,
        NAV_PROFILES,
        NAV_SETTINGS,
    )


def test_no_top_level_scanprofile() -> None:
    labels = [label for _, label, _ in ALL_NAV_ITEMS]
    assert "Scanprofile" not in labels
    src = NAV_MODULE.read_text(encoding="utf-8")
    assert "Scanprofile" not in src


def test_app_wires_review_and_settings_pages() -> None:
    src = APP_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imports = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "build_review_page" in imports
    assert "build_settings_page" in imports
    assert "NAV_REVIEW" in src
    assert "NAV_SETTINGS" in src
    assert "build_review_page" in src
    assert "build_settings_page" in src


def test_navigation_source_has_no_private_tokens() -> None:
    src = NAV_MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in src, marker
