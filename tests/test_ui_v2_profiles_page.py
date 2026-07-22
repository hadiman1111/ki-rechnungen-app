"""Track-B UI-v2 profiles page — profile/policy readiness copy (non-GUI)."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.profile_policy import (
    MSG_PAYMENT_BUSINESS_PER_PROFILE,
    MSG_PROFILES_CONTAIN_RULES,
    MSG_WITHOUT_EVIDENCE_REVIEW,
    build_profiles_page_policy_panel_vm,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILES_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "profiles.py"
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


def test_profiles_page_policy_panel_copy() -> None:
    panel = build_profiles_page_policy_panel_vm(profile_count=0)
    assert MSG_PROFILES_CONTAIN_RULES in panel.banner
    assert MSG_PAYMENT_BUSINESS_PER_PROFILE in panel.honest_copy
    assert MSG_WITHOUT_EVIDENCE_REVIEW in panel.honest_copy
    assert panel.empty is True
    assert panel.has_private_defaults is False
    assert panel.has_productive_execution_toggle is False


def test_profiles_page_source_contains_generic_policy_copy() -> None:
    src = PROFILES_PAGE.read_text(encoding="utf-8")
    assert "MSG_PROFILES_CONTAIN_RULES" in src
    assert "MSG_PAYMENT_BUSINESS_PER_PROFILE" in src
    assert "MSG_WITHOUT_EVIDENCE_REVIEW" in src
    assert "build_profiles_page_policy_panel_vm" in src
    assert "Regeln ordnen Dokumente zu" in src


def test_profiles_page_shows_empty_state_honestly() -> None:
    panel = build_profiles_page_policy_panel_vm(profile_count=0)
    assert panel.empty_title
    assert "Profil" in panel.empty_title
    assert "privaten Standardwerte" in panel.empty_detail.lower() or "kein" in panel.empty_detail.lower()


def test_profiles_page_selected_readiness_when_profiles_exist() -> None:
    panel = build_profiles_page_policy_panel_vm(
        profile_count=1,
        selected_display_name="Mandant Demo",
        selected_profile_id="p-demo",
        configuration_present=False,
    )
    assert panel.empty is False
    assert panel.selected_readiness_status == "review"
    assert "profilspezifisch" in panel.rules_profile_specific_label.lower()


def test_profiles_page_no_processing_core_import() -> None:
    src = PROFILES_PAGE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    for forbidden in PROCESSING_CORE:
        assert forbidden not in imported


def test_profiles_page_source_has_no_private_hardcoded_defaults() -> None:
    src = PROFILES_PAGE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert f'"{marker}"' not in src
        assert f"'{marker}'" not in src
