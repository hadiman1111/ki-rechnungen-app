"""Track-B UI-v2 settings navigation and generic detail shell — non-GUI."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.navigation import ALL_NAV_ITEMS, NAV_SETTINGS
from invoice_tool.ui_v2.pages.settings import (
    DRY_RUN_UNAVAILABLE_NOTICE,
    PRODUCT_NEUTRAL_NOTICE,
    PRODUCTIVE_EXECUTION_NOTICE,
    SETTINGS_SECTIONS,
    build_settings_page_vm,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "settings.py"
PROCESSING_CORE = (
    "invoice_tool.processing",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
    "invoice_tool.run",
)
PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX",
    "voba",
    "/Users/",
    "Desktop/",
    "Privat",
    "Volksbank",
    "Application Support",
)


def test_settings_navigation_item_exists() -> None:
    labels = {label for _, label, _ in ALL_NAV_ITEMS}
    ids = {nav_id for nav_id, _, _ in ALL_NAV_ITEMS}
    assert "Einstellungen" in labels
    assert NAV_SETTINGS in ids
    assert NAV_SETTINGS == "einstellungen"


def test_settings_page_generic_sections() -> None:
    vm = build_settings_page_vm(UiV2State())
    assert vm.title == "Einstellungen"
    section_titles = {section.title for section in vm.sections}
    assert section_titles == {
        "Allgemein",
        "Verarbeitung",
        "Sicherheit",
        "Export",
        "Produktstatus",
    }
    assert len(SETTINGS_SECTIONS) == 5


def test_settings_page_shows_dry_run_unavailable() -> None:
    vm = build_settings_page_vm(UiV2State())
    assert vm.dry_run_available is False
    assert vm.safety.dry_run_available is False
    assert DRY_RUN_UNAVAILABLE_NOTICE in vm.dry_run_notice
    assert "Dry-Run ohne Dateiveränderung ist im lokalen Core noch nicht verfügbar." in (
        vm.dry_run_notice
    )


def test_settings_page_shows_productive_execution_not_enabled() -> None:
    vm = build_settings_page_vm(UiV2State())
    assert vm.productive_execution_enabled is False
    assert vm.has_productive_toggle is False
    assert PRODUCTIVE_EXECUTION_NOTICE in vm.productive_execution_notice
    assert "noch nicht freigegeben" in vm.productive_execution_notice
    assert vm.saas_ready is False
    assert vm.datev_productive_export_ready is False
    assert any(item.key == "productive_processing" for item in vm.capability_matrix)
    assert any(
        item.key == "saas_login_tenant_billing" and item.status == "not_included"
        for item in vm.capability_matrix
    )


def test_settings_page_no_private_defaults() -> None:
    vm = build_settings_page_vm(UiV2State())
    assert vm.safety.has_private_defaults is False
    assert PRODUCT_NEUTRAL_NOTICE in vm.product_neutral_notice
    blob = " ".join(
        [
            vm.title,
            vm.subtitle,
            vm.banner,
            vm.productive_execution_notice,
            vm.dry_run_notice,
            vm.product_neutral_notice,
            *(section.title for section in vm.sections),
            *(section.detail for section in vm.sections),
            *(section.status for section in vm.sections),
        ]
    )
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    src = SETTINGS_PAGE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in src, marker


def test_settings_page_no_productive_execution_toggle() -> None:
    vm = build_settings_page_vm()
    assert vm.has_productive_toggle is False
    assert vm.productive_execution_enabled is False
    src = SETTINGS_PAGE.read_text(encoding="utf-8")
    for token in (
        "Switch",
        "Toggle",
        "productive_execution_toggle",
        "enable_productive",
        "ft.Switch",
        "ft.Checkbox",
    ):
        assert token not in src, token


def test_settings_page_has_no_processing_core_import() -> None:
    src = SETTINGS_PAGE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    for forbidden in PROCESSING_CORE:
        assert forbidden not in imported_modules
        assert forbidden not in src
    assert "invoice_tool.app_paths" not in imported_modules
