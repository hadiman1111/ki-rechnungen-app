"""Track-B UI-v2 configurations page — policy relationship copy (non-GUI)."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.profile_policy import (
    MSG_CONFIGS_APPLY_RULES,
    MSG_TARGETS_AFTER_SAFE_CONFIG,
    MSG_UNCLEAR_NOT_AUTO,
    build_configurations_page_policy_panel_vm,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIGS_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py"
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
)


def test_configurations_page_policy_panel_copy() -> None:
    panel = build_configurations_page_policy_panel_vm(
        active_profile_name="Mandant Demo",
        policy_readiness_status="review",
        unmatched_configured=None,
    )
    assert MSG_CONFIGS_APPLY_RULES in panel.banner
    assert MSG_UNCLEAR_NOT_AUTO in panel.honest_copy
    assert MSG_TARGETS_AFTER_SAFE_CONFIG in panel.honest_copy
    assert panel.has_private_destination_defaults is False
    assert panel.scans_folders is False
    assert panel.processes_pdfs is False
    assert panel.has_productive_execution_toggle is False


def test_configurations_page_source_contains_generic_policy_relationship() -> None:
    src = CONFIGS_PAGE.read_text(encoding="utf-8")
    assert "MSG_CONFIGS_APPLY_RULES" in src
    assert "MSG_UNCLEAR_NOT_AUTO" in src
    assert "MSG_TARGETS_AFTER_SAFE_CONFIG" in src
    assert "build_configurations_page_policy_panel_vm" in src
    assert "Konfiguration ↔ Profil-Policy" in src


def test_configurations_page_no_processing_core_import() -> None:
    src = CONFIGS_PAGE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    for forbidden in PROCESSING_CORE:
        assert forbidden not in imported


def test_configurations_page_source_has_no_private_hardcoded_defaults() -> None:
    src = CONFIGS_PAGE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert f'"{marker}"' not in src
        assert f"'{marker}'" not in src


def test_configurations_page_no_productive_execution_toggle_in_source() -> None:
    src = CONFIGS_PAGE.read_text(encoding="utf-8")
    for token in ("ft.Switch", "enable_productive", "productive_toggle"):
        assert token not in src
