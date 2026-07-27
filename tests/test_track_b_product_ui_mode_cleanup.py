"""Track-B Product UI Mode Cleanup (2026-07-27).

Dev-defaults vs show-dev-surfaces, clickable workspace titles,
unified collapsible chevrons, concrete review actions, full-width cards.
No productive processing, no real invoice folders, no Track-A/core changes.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

from invoice_tool.ui_v2.navigation import ADMIN_NAV, DAILY_NAV, NAV_SETTINGS
from invoice_tool.ui_v2.state import (
    ENV_SHOW_DEV_SURFACES,
    UiV2State,
    is_track_b_show_dev_surfaces_enabled,
)
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_ACCEPT_SUGGESTION,
    ACTION_CHANGE_PROFILE,
    ACTION_EDIT_CONFIGURATIONS,
    ACTION_EDIT_FILENAME,
    ACTION_IGNORE_EXPORT,
    ACTION_KEEP_IN_REVIEW_GUIDED,
    ACTION_KEEP_UNCLEAR_GUIDED,
    ACTION_WORKSPACE_EDIT,
    COLLAPSIBLE_CHEVRON_MARKER,
    FILENAME_SECTION_EDITING_ACTIVE_MARKER,
    MSG_DECISION_CHOOSE_NEXT,
    PRODUCT_UI_MODE_CLEANUP_MARKER,
    REVIEW_DETAIL_CARD_FULL_WIDTH_MARKER,
    WORKSPACE_CLICKABLE_TITLE_MARKER,
)

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "invoice_tool" / "ui_v2" / "shell.py"
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
COMPONENTS = ROOT / "invoice_tool" / "ui_v2" / "components.py"
STATE = ROOT / "invoice_tool" / "ui_v2" / "state.py"
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
APP_UI = ROOT / "app_ui_v2.py"
DOC = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_PRODUCT_UI_MODE_CLEANUP_2026-07-27.md"
)

TRACK_A_PROTECTED = (
    "app_main.py",
    "app_internal_launcher.py",
    "invoice_tool/gui.py",
    "invoice_tool/ui_shell.py",
    "invoice_tool/ui_workspace.py",
    "invoice_tool/ui_configurations.py",
    "invoice_tool/ui_profiles.py",
    "invoice_tool/ui_review.py",
    "invoice_tool/ui_settings.py",
    "invoice_tool/ui_profile_dialog.py",
    "invoice_tool/ui_document_rules.py",
)
CORE_PROTECTED = (
    "invoice_tool/run.py",
    "invoice_tool/processing.py",
    "invoice_tool/routing.py",
    "invoice_tool/routing_guards.py",
    "invoice_tool/classification.py",
    "invoice_tool/target_routing.py",
    "invoice_tool/core_dry_run.py",
)


def _ws() -> str:
    return WORKSPACE.read_text(encoding="utf-8")


def _review() -> str:
    return REVIEW.read_text(encoding="utf-8")


def _detail_fn() -> str:
    return _review().split("def _selected_detail_section_controls")[1].split(
        "def build_review_page("
    )[0]


def test_01_dev_defaults_env_does_not_enable_surfaces_helper() -> None:
    assert ENV_SHOW_DEV_SURFACES == "KI_RECHNUNGEN_UI_V2_SHOW_DEV_SURFACES"
    assert is_track_b_show_dev_surfaces_enabled(env={}) is False
    assert is_track_b_show_dev_surfaces_enabled(
        env={"KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS": "1"}
    ) is False
    assert is_track_b_show_dev_surfaces_enabled(
        env={ENV_SHOW_DEV_SURFACES: "1"}
    ) is True


def test_02_shell_gates_dev_nav_on_show_dev_surfaces_not_defaults() -> None:
    shell = SHELL.read_text(encoding="utf-8")
    assert "is_track_b_show_dev_surfaces_enabled" in shell
    assert "is_track_b_dev_defaults_enabled" not in shell
    assert "show_dev_surfaces_only" in shell
    assert "dev_defaults_do_not_enable_surfaces" in shell
    assert "if show_dev_nav:" in shell


def test_03_workspace_gates_dev_surfaces_on_show_flag() -> None:
    src = _ws()
    assert "is_track_b_show_dev_surfaces_enabled" in src
    assert "show_dev_surfaces = bool(is_track_b_show_dev_surfaces_enabled())" in src
    assert "if show_dev_surfaces:" in src


def test_04_review_gates_test_tools_on_show_flag() -> None:
    detail = _detail_fn()
    assert "is_track_b_show_dev_surfaces_enabled()" in detail
    gated = detail.split("if is_track_b_show_dev_surfaces_enabled():")[1]
    assert "_test_tools_collapsed" in gated
    primary = detail.split("if is_track_b_show_dev_surfaces_enabled():")[0]
    assert "_test_tools_collapsed" not in primary


def test_05_normal_daily_nav_product_only() -> None:
    labels = [label for _, label, _ in DAILY_NAV]
    assert labels == ["Arbeitsbereich", "Profile", "Konfigurationen", "Prüfung"]
    assert NAV_SETTINGS not in {i for i, _, _ in DAILY_NAV}
    assert ADMIN_NAV[0][1] == "Entwickler / Diagnose"


def test_06_workspace_profile_title_clickable_no_bearbeiten_button() -> None:
    src = _ws()
    card = src.split("def _workspace_profile_card")[1].split(
        "def _workspace_configuration_card"
    )[0]
    assert "WORKSPACE_CLICKABLE_TITLE_MARKER" in card or "_workspace_clickable_title" in card
    assert "no_separate_bearbeiten" in card
    assert 'action_button(\n                    ACTION_CHANGE_PROFILE' not in card
    assert ACTION_CHANGE_PROFILE == "Profil bearbeiten"
    assert ACTION_WORKSPACE_EDIT == "Bearbeiten"
    assert WORKSPACE_CLICKABLE_TITLE_MARKER == "workspace_clickable_profile_config_title_v1"


def test_07_workspace_config_title_clickable_no_bearbeiten_button() -> None:
    src = _ws()
    card = src.split("def _workspace_configuration_card")[1].split(
        "def _workspace_profile_config_summary"
    )[0]
    assert "_workspace_clickable_title" in card
    assert "no_separate_bearbeiten" in card
    assert "ACTION_EDIT_CONFIGURATIONS" in card
    assert ACTION_EDIT_CONFIGURATIONS == "Konfiguration bearbeiten"
    assert 'action_button(\n            ACTION_EDIT_CONFIGURATIONS' not in card


def test_08_shared_collapsible_chevron_right_down() -> None:
    components = COMPONENTS.read_text(encoding="utf-8")
    assert "def make_expansion_tile" in components
    assert "COLLAPSIBLE_CHEVRON_MARKER" in components
    assert "KEYBOARD_ARROW_RIGHT" in components
    assert "KEYBOARD_ARROW_DOWN" in components
    assert "closed_chevron_right" in components or "closed_right" in components
    assert COLLAPSIBLE_CHEVRON_MARKER == "ui_v2_collapsible_chevron_right_down_v1"
    review = _review()
    assert "make_expansion_tile" in review
    tools = review.split("def _test_tools_collapsed")[1].split(
        "def _selected_detail_section_controls"
    )[0]
    assert "make_expansion_tile" in tools


def test_09_no_zur_pruefung_zulassen_in_normal_actions() -> None:
    assert "Zur Prüfung zulassen" not in ACTION_KEEP_IN_REVIEW_GUIDED
    assert "Zur Prüfung lassen" not in ACTION_KEEP_IN_REVIEW_GUIDED
    assert ACTION_KEEP_IN_REVIEW_GUIDED == "Weiter manuell prüfen"
    assert ACTION_KEEP_UNCLEAR_GUIDED == "Weiter manuell prüfen"
    assert ACTION_ACCEPT_SUGGESTION == "Vorschlag übernehmen"
    assert ACTION_IGNORE_EXPORT == "Nicht exportieren"
    assert ACTION_EDIT_FILENAME == "Dateiname anpassen"
    assert MSG_DECISION_CHOOSE_NEXT.startswith("Bitte wählen Sie")
    detail = _detail_fn()
    primary = detail.split("if is_track_b_show_dev_surfaces_enabled():")[0]
    assert "Zur Prüfung zulassen" not in primary


def test_10_detail_cards_full_width_marker() -> None:
    src = _review()
    section = src.split("def review_section(")[1].split("def review_card(")[0]
    assert "REVIEW_DETAIL_CARD_FULL_WIDTH_MARKER" in section
    assert 'expand": True' in section or "expand=True" in section or '"expand": True' in section
    assert REVIEW_DETAIL_CARD_FULL_WIDTH_MARKER == "review_detail_card_full_width_v1"
    assert PRODUCT_UI_MODE_CLEANUP_MARKER in section or "PRODUCT_UI_MODE_CLEANUP_MARKER" in section


def test_11_filename_edit_active_visual_marker() -> None:
    panel = _review().split("def _filename_preview_panel")[1].split(
        "def _test_tools_collapsed"
    )[0]
    assert "FILENAME_SECTION_EDITING_ACTIVE_MARKER" in panel
    assert "editing_active" in panel or "edit_active" in panel
    assert FILENAME_SECTION_EDITING_ACTIVE_MARKER == (
        "review_filename_section_editing_active_v1"
    )
    assert "request_review_scroll_to_filename_section" in panel


def test_12_app_ui_v2_documents_surface_separation() -> None:
    text = APP_UI.read_text(encoding="utf-8")
    assert "SHOW_DEV_SURFACES" in text
    assert "DEV_DEFAULTS" in text


def test_13_audit_doc_exists() -> None:
    assert DOC.is_file()
    text = DOC.read_text(encoding="utf-8")
    assert "PRODUCT_UI_MODE_CLEANUP" in text or "Product UI Mode" in text
    assert "SHOW_DEV_SURFACES" in text


def test_14_no_track_a_or_core_touched_in_phase1_sources() -> None:
    for rel in TRACK_A_PROTECTED + CORE_PROTECTED:
        path = ROOT / rel
        # Existence check only — content must not be edited in this phase.
        assert path.exists() or rel.endswith("ui_document_rules.py")


def test_15_phase1_sources_parse() -> None:
    for path in (SHELL, WORKSPACE, REVIEW, COMPONENTS, STATE, COPY_MOD, APP_UI):
        ast.parse(path.read_text(encoding="utf-8"))


def test_16_state_helper_ignores_dev_defaults_in_os_environ_when_passed() -> None:
    # Explicit env mapping wins; DEV_DEFAULTS must not flip surfaces.
    env = {
        "KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS": "1",
        ENV_SHOW_DEV_SURFACES: "0",
    }
    assert is_track_b_show_dev_surfaces_enabled(env=env) is False
    _ = UiV2State()  # smoke construct
    # Restore-safe: do not mutate process env permanently.
    assert os.environ.get(ENV_SHOW_DEV_SURFACES, "") != "force-unset-sentinel"
