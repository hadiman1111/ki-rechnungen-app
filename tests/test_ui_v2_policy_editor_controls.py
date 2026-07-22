"""Track-B UI-v2 Policy Editor Controls readiness — non-GUI."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.pages.settings import build_settings_page_vm
from invoice_tool.ui_v2.policy_editor_controls import (
    MSG_FILENAME_NOT_TRUTH,
    MSG_PRODUCTIVE_NOT_RELEASED,
    MSG_RULES_PROFILE_CONFIGURABLE,
    MSG_UNCLEAR_STAYS_REVIEW,
    build_policy_editor_controls_vm,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
POLICY_MODULE = ROOT / "invoice_tool" / "ui_v2" / "policy_editor_controls.py"
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
)


def test_policy_editor_controls_exist() -> None:
    vm = build_policy_editor_controls_vm()
    assert vm.section_title
    assert len(vm.controls) >= 5
    ids = {item.control_id for item in vm.controls}
    assert "filename_not_source_of_truth" in ids
    assert "unknown_evidence_to_review" in ids
    assert "supplier_iban_not_payer" in ids
    assert "generic_card_without_account_ref" in ids
    assert "profile_configurable_rules" in ids


def test_policy_editor_says_filenames_are_not_source_of_truth() -> None:
    vm = build_policy_editor_controls_vm()
    assert vm.filename_is_source_of_truth is False
    assert MSG_FILENAME_NOT_TRUTH in vm.honest_copy
    blob = " ".join(vm.honest_copy + tuple(c.detail for c in vm.controls))
    assert "Dateinamen sind keine Belegwahrheit" in blob


def test_policy_editor_says_unclear_evidence_goes_to_review() -> None:
    vm = build_policy_editor_controls_vm()
    assert vm.unclear_evidence_goes_to_review is True
    assert MSG_UNCLEAR_STAYS_REVIEW in vm.honest_copy


def test_policy_editor_says_rules_are_profile_configurable() -> None:
    vm = build_policy_editor_controls_vm()
    assert vm.rules_profile_configurable is True
    assert MSG_RULES_PROFILE_CONFIGURABLE in vm.honest_copy


def test_policy_editor_no_private_defaults() -> None:
    vm = build_policy_editor_controls_vm()
    assert vm.has_private_defaults is False
    blob = " ".join(
        [
            vm.section_title,
            vm.subtitle,
            vm.banner,
            *vm.honest_copy,
            *(c.label for c in vm.controls),
            *(c.detail for c in vm.controls),
            *(c.value_label for c in vm.controls),
        ]
    )
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    src = POLICY_MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in src, marker


def test_policy_editor_no_productive_execution_toggle() -> None:
    vm = build_policy_editor_controls_vm()
    assert vm.has_productive_execution_toggle is False
    assert vm.productive_execution_enabled is False
    assert MSG_PRODUCTIVE_NOT_RELEASED in vm.honest_copy
    src = POLICY_MODULE.read_text(encoding="utf-8")
    for token in ("ft.Switch", "ft.Checkbox", "enable_productive", "productive_toggle"):
        assert token not in src, token


def test_settings_embeds_policy_editor_controls() -> None:
    settings = build_settings_page_vm(UiV2State())
    assert settings.policy_editor.rules_profile_configurable is True
    assert settings.policy_editor.filename_is_source_of_truth is False


def test_policy_editor_has_no_processing_core_import() -> None:
    for path in (POLICY_MODULE, SETTINGS_PAGE):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        for forbidden in PROCESSING_CORE:
            assert forbidden not in imported_modules
            assert forbidden not in src
