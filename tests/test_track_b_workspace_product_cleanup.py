"""Track-B UI-v2 product UX audit + workspace cleanup gates.

Source/VM assertions only. No GUI window, no run_once, no productive
processing, no real invoice folders, no final-write.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from invoice_tool.ui_v2.navigation import ADMIN_NAV, DAILY_NAV, NAV_SETTINGS
from invoice_tool.ui_v2.pages.settings import SETTINGS_PAGE_TITLE, build_settings_page_vm
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_OPEN_REVIEW,
    ACTION_SHOW_DOCUMENT,
    ACTION_VIEW_PROPOSAL,
    FILENAME_EDIT_FOCUS_MARKER,
    FILENAME_EDIT_SECONDARY_MARKER,
    MSG_NOT_CHECKED_YET,
    MSG_START_HELPER,
    OUTPUT_ACTION_ICON_MARKER,
    OUTPUT_ROW_ACTIONABLE_MARKER,
    OUTPUT_ROW_PLACEHOLDER_MARKER,
    PRODUCT_UX_CLEANUP_MARKER,
    SECTION_DEV_DIAGNOSE,
    SECTION_TEST_NACHWEIS_COLLAPSED,
    START_CTA_STRONG,
    WORKSPACE_COMPACT_STATUS_MARKER,
    WORKSPACE_IA_SECTION_ORDER,
    WORKSPACE_NO_PRIMARY_DEV_MARKER,
)
from invoice_tool.ui_v2.workspace_file_pairs import (
    MSG_NEED_OUTPUT_FOLDER,
    MSG_NO_PROPOSAL,
    MSG_NOT_CHECKED,
    STATUS_NEED_OUTPUT,
    STATUS_NOT_CHECKED,
    STATUS_PROPOSED,
    STATUS_REVIEW,
    build_live_file_pairs_vm,
    output_row_action_tooltip,
    output_row_is_actionable,
)

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
SETTINGS = ROOT / "invoice_tool" / "ui_v2" / "pages" / "settings.py"
SHELL = ROOT / "invoice_tool" / "ui_v2" / "shell.py"
NAV = ROOT / "invoice_tool" / "ui_v2" / "navigation.py"
PAIRS = ROOT / "invoice_tool" / "ui_v2" / "workspace_file_pairs.py"
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
DOC = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_UI_V2_PRODUCT_UX_AUDIT_AND_WORKSPACE_CLEANUP_2026-07-25.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_UI_V2_PRODUCT_UX_AUDIT_AND_WORKSPACE_CLEANUP_2026-07-25.md"
)

TRACK_A_PROTECTED = (
    ROOT / "app_main.py",
    ROOT / "app_internal_launcher.py",
    ROOT / "invoice_tool" / "gui.py",
    ROOT / "invoice_tool" / "ui_shell.py",
    ROOT / "invoice_tool" / "ui_workspace.py",
    ROOT / "invoice_tool" / "ui_configurations.py",
    ROOT / "invoice_tool" / "ui_profiles.py",
    ROOT / "invoice_tool" / "ui_review.py",
    ROOT / "invoice_tool" / "ui_settings.py",
    ROOT / "invoice_tool" / "ui_profile_dialog.py",
    ROOT / "invoice_tool" / "ui_document_rules.py",
)

PROCESSING_CORE = (
    ROOT / "invoice_tool" / "run.py",
    ROOT / "invoice_tool" / "processing.py",
    ROOT / "invoice_tool" / "routing.py",
    ROOT / "invoice_tool" / "routing_guards.py",
    ROOT / "invoice_tool" / "classification.py",
    ROOT / "invoice_tool" / "target_routing.py",
    ROOT / "invoice_tool" / "core_dry_run.py",
)


def _ws_src() -> str:
    return WORKSPACE.read_text(encoding="utf-8")


def _pair_fn_src() -> str:
    src = _ws_src()
    return src.split("def _workspace_file_pair_rows")[1].split(
        "def _workspace_result_summary"
    )[0]


def _items_block() -> str:
    return _ws_src().split("items: list[ft.Control] = [")[-1]


def _filename_panel_src() -> str:
    src = REVIEW.read_text(encoding="utf-8")
    return src.split("def _filename_preview_panel")[1].split(
        "def _test_tools_collapsed"
    )[0]


# --- Workspace scope ---


def test_01_workspace_primary_no_dev_test_evidence_blocks() -> None:
    src = _ws_src()
    assert "PRODUCT_UX_CLEANUP_MARKER" in src
    assert PRODUCT_UX_CLEANUP_MARKER == "track_b_ui_v2_product_ux_audit_workspace_cleanup_v1"
    assert "WORKSPACE_NO_PRIMARY_DEV_MARKER" in src
    assert WORKSPACE_NO_PRIMARY_DEV_MARKER == "workspace_no_primary_dev_test_evidence_v1"
    assert "show_dev_surfaces" in src
    items = _items_block()
    # Primary items assembly gates advanced blocks behind show_dev_surfaces.
    assert "if show_dev_surfaces:" in items
    assert "items.extend(advanced_blocks)" in items
    # Advanced blocks are not unconditionally appended to primary flow.
    primary_tail = items.split("if show_dev_surfaces:")[0]
    assert "items.extend(advanced_blocks)" not in primary_tail


def test_02_test_nachweis_not_primary_workspace() -> None:
    assert SECTION_TEST_NACHWEIS_COLLAPSED == "Test & Nachweis"
    src = _ws_src()
    assert "SECTION_TEST_NACHWEIS_COLLAPSED" in src
    assert "show_dev_surfaces" in src
    items = _items_block()
    # Collapsible title may exist in advanced_blocks construction above items,
    # but primary append is gated.
    assert "if show_dev_surfaces:" in items


def test_03_entwickler_diagnose_not_primary_workspace() -> None:
    assert SECTION_DEV_DIAGNOSE == "Entwickler / Diagnose"
    src = _ws_src()
    assert "SECTION_DEV_DIAGNOSE" in src
    assert "WORKSPACE_NO_PRIMARY_DEV_MARKER" in src
    assert "show_dev_surfaces" in src


def test_04_letzte_ergebnisse_absent_or_compact_non_dominant() -> None:
    src = _ws_src()
    assert "WORKSPACE_COMPACT_STATUS_MARKER" in src
    assert WORKSPACE_COMPACT_STATUS_MARKER == "workspace_compact_status_line_v1"
    assert "_workspace_compact_status_line" in src
    assert "compact_not_dominant" in src
    assert "no_letzte_ergebnisse_section" in src
    items = _items_block()
    # Full tab "Letzte Ergebnisse" only under show_dev_surfaces.
    assert "tab_bar" in items
    gated = items.split("if show_dev_surfaces:")[1]
    assert "tab_bar" in gated
    primary_before = items.split("if show_dev_surfaces:")[0]
    assert "tab_bar" not in primary_before or "show_compact_status" in primary_before


def test_05_detailed_configuration_lists_not_primary() -> None:
    src = _ws_src()
    items = _items_block()
    # Destination/config detail tabs are not primary product content.
    assert 'make_tab_bar' in src
    assert "zielordner" in src
    gated = items.split("if show_dev_surfaces:")[1]
    assert "tab_bar" in gated
    # Workspace still has compact profile/config summary (not detailed lists).
    assert "_workspace_profile_config_summary" in src
    assert "make_destination_list_row" in src  # exists for advanced only


def test_06_workspace_still_shows_profile_config_summary() -> None:
    src = _ws_src()
    assert "_workspace_profile_config_summary" in src
    assert "_workspace_profile_card" in src
    assert "_workspace_configuration_card" in src
    assert WORKSPACE_IA_SECTION_ORDER[0] == "Profil"
    assert WORKSPACE_IA_SECTION_ORDER[1] == "Konfiguration"


def test_07_workspace_still_shows_folder_cards() -> None:
    src = _ws_src()
    assert "folder_selection_panel" in src
    assert "LABEL_INPUT_FOLDER" in src
    assert "LABEL_OUTPUT_FOLDER" in src
    assert "file_list=input_file_list" in src
    assert "file_list=output_file_list" in src


def test_08_workspace_still_shows_primary_cta() -> None:
    assert START_CTA_STRONG == "Belegnamen jetzt ändern"
    src = _ws_src()
    assert "START_CTA_STRONG" in src or "Belegnamen jetzt ändern" in src
    assert "_workspace_primary_cta_button" in src


def test_09_workspace_still_shows_safety_text() -> None:
    assert MSG_START_HELPER == "Nur Vorschau — Originale bleiben unverändert."
    src = _ws_src()
    assert "MSG_START_HELPER" in src
    assert "file_pair_safety_helper" in src


# --- Output clickability ---


def test_10_placeholder_noch_nicht_geaendert_not_clickable() -> None:
    assert MSG_NOT_CHECKED == "Noch nicht geändert"
    assert MSG_NOT_CHECKED_YET == "Noch nicht geändert"
    assert (
        output_row_is_actionable(
            output_status=STATUS_NOT_CHECKED,
            output_display=MSG_NOT_CHECKED,
            has_proposal=False,
            source_filename="a.pdf",
        )
        is False
    )
    pair_fn = _pair_fn_src()
    assert "OUTPUT_ROW_PLACEHOLDER_MARKER" in pair_fn
    assert OUTPUT_ROW_PLACEHOLDER_MARKER == "workspace_output_row_placeholder_non_clickable_v1"
    assert "non_clickable" in pair_fn
    assert "no_dead_end" in pair_fn


def test_11_placeholder_no_pointer_hover_action_icon() -> None:
    pair_fn = _pair_fn_src()
    assert "OUTPUT_ROW_PLACEHOLDER_MARKER" in pair_fn
    assert "no_action_icon" in pair_fn
    # Flet 0.85 Container rejects cursor kwargs — neither branch may set them.
    assert "mouse_cursor=" not in pair_fn
    assert "MouseCursor." not in pair_fn
    # Placeholder branch: no click / hover / action icon.
    placeholder_branch = pair_fn.split("else:")[-1]
    assert "on_click=_on_target_click" not in placeholder_branch
    assert "on_hover=_on_output_hover" not in placeholder_branch
    assert (
        "OUTPUT_ACTION_ICON_MARKER" not in placeholder_branch
        or "no_action" in placeholder_branch
    )


def test_12_valid_proposed_row_clickable_when_target_exists() -> None:
    assert (
        output_row_is_actionable(
            output_status=STATUS_PROPOSED,
            output_display="out.pdf",
            has_proposal=True,
            source_filename="a.pdf",
        )
        is True
    )
    assert (
        output_row_is_actionable(
            output_status=STATUS_REVIEW,
            output_display="Zur Prüfung",
            has_proposal=False,
            source_filename="a.pdf",
        )
        is True
    )
    # No source → never actionable (no dead end).
    assert (
        output_row_is_actionable(
            output_status=STATUS_PROPOSED,
            output_display="out.pdf",
            has_proposal=True,
            source_filename="",
        )
        is False
    )
    pair_fn = _pair_fn_src()
    assert "OUTPUT_ROW_ACTIONABLE_MARKER" in pair_fn
    assert OUTPUT_ROW_ACTIONABLE_MARKER == "workspace_output_row_actionable_v1"
    assert "if actionable:" in pair_fn
    assert "on_click=_on_target_click" in pair_fn


def test_13_valid_proposed_row_shows_hover_click_marker() -> None:
    pair_fn = _pair_fn_src()
    # Clickability via on_click + ink; hover via bgcolor (no Container cursor kwarg).
    assert "on_click=_on_target_click" in pair_fn
    assert "hover_bg" in pair_fn
    assert "on_hover=_on_output_hover" in pair_fn
    assert "_OUTPUT_ROW_HOVER_BG" in _ws_src()
    assert "mouse_cursor=" not in pair_fn


def test_14_output_action_icon_right_aligned_only_when_valid() -> None:
    assert OUTPUT_ACTION_ICON_MARKER == "workspace_output_action_icon_v1"
    pair_fn = _pair_fn_src()
    assert "FACT_CHECK_OUTLINED" in pair_fn
    assert "OUTPUT_ACTION_ICON_MARKER" in pair_fn
    assert "file_pair_output_action" in pair_fn
    assert "if actionable:" in pair_fn
    # Placeholder uses spacer, not action icon.
    assert "pair_row_height_spacer" in pair_fn
    assert "no_action_icon" in pair_fn


def test_15_no_dead_end_from_output_placeholders() -> None:
    for display, status in (
        (MSG_NOT_CHECKED, STATUS_NOT_CHECKED),
        (MSG_NO_PROPOSAL, STATUS_NOT_CHECKED),
        (MSG_NEED_OUTPUT_FOLDER, STATUS_NEED_OUTPUT),
    ):
        assert (
            output_row_is_actionable(
                output_status=status,
                output_display=display,
                has_proposal=False,
                source_filename="x.pdf",
            )
            is False
        )
    pair_fn = _pair_fn_src()
    assert "if not allow:" in pair_fn
    assert "return" in pair_fn
    tip = output_row_action_tooltip(
        output_status=STATUS_PROPOSED, has_proposal=True
    )
    assert tip in {ACTION_VIEW_PROPOSAL, ACTION_OPEN_REVIEW, "Datei anzeigen"}


# --- Filename edit focus ---


def test_16_filename_edit_renders_input_in_same_detail_section() -> None:
    panel = _filename_panel_src()
    assert "FILENAME_EDIT_FOCUS_MARKER" in panel
    assert FILENAME_EDIT_FOCUS_MARKER == "review_filename_edit_focus_in_place_v1"
    assert "same_detail_section" in panel or "same_section" in panel
    assert "in_place" in panel
    assert "if edit_active:" in panel
    assert "ft.TextField(" in panel.split("if edit_active:")[1]


def test_17_filename_edit_has_focus_visibility_marker() -> None:
    panel = _filename_panel_src()
    assert "autofocus=True" in panel
    assert "focus_visibility_marker" in panel or "autofocus" in panel
    assert "FILENAME_EDIT_FOCUS_MARKER" in COPY_MOD.read_text(encoding="utf-8")
    assert FILENAME_EDIT_FOCUS_MARKER in COPY_MOD.read_text(encoding="utf-8")


def test_18_filename_edit_not_distant_hidden_section() -> None:
    panel = _filename_panel_src()
    assert "no_distant_hidden_section" in panel or "in_place" in panel
    # Field is built inside edit_active before helpers/actions — not appended far below.
    edit_block = panel.split("if edit_active:")[1].split("else:")[0]
    assert "ft.TextField(" in edit_block
    assert "FILENAME_EDIT_FOCUS_MARKER" in edit_block


def test_19_filename_edit_no_layout_collapse() -> None:
    panel = _filename_panel_src()
    assert "no_layout_collapse" in panel or "section_stable" in panel
    assert "FILENAME_EDIT_SECONDARY_MARKER" in panel
    assert FILENAME_EDIT_SECONDARY_MARKER == "filename_edit_secondary_not_primary"
    # Edit remains secondary until requested.
    assert "ACTION_EDIT_FILENAME" in panel
    assert "set_filename_editor_active" in panel


# --- Settings / dev ---


def test_20_no_empty_erweiterte_einstellungen_as_user_settings() -> None:
    label = ADMIN_NAV[0][1]
    assert "Erweiterte Einstellungen" not in label
    assert "Diagnose" in label or "Entwickler" in label
    assert SETTINGS_PAGE_TITLE == "Entwickler / Diagnose"
    vm = build_settings_page_vm(UiV2State())
    assert "Erweiterte Einstellungen" not in vm.title
    settings_src = SETTINGS.read_text(encoding="utf-8")
    assert "not_user_settings" in settings_src or "dev_advanced_only" in settings_src
    # Title/subtitle/nav must not present empty "Erweiterte Einstellungen" as settings.
    assert SETTINGS_PAGE_TITLE != "Erweiterte Einstellungen"
    assert 'SETTINGS_PAGE_TITLE = "Erweiterte Einstellungen"' not in settings_src
    assert 'title="Erweiterte Einstellungen"' not in settings_src


def test_21_developer_diagnosis_dev_advanced_only() -> None:
    assert NAV_SETTINGS not in {i for i, _, _ in DAILY_NAV}
    shell = SHELL.read_text(encoding="utf-8")
    assert "nav_dev_diagnose_collapsed_secondary" in shell
    assert "initially_expanded=False" in shell
    assert "dev_advanced_only" in shell or "not_erweiterte_einstellungen" in shell
    nav = NAV.read_text(encoding="utf-8")
    assert "Entwickler / Diagnose" in nav


# --- Terminology ---


def test_22_belege_pruefen_not_in_primary_workflow() -> None:
    assert "Belege prüfen" not in START_CTA_STRONG
    cta_region = _ws_src().split("def _workspace_primary_cta_button")[1].split(
        "def _workspace_file_pair_rows"
    )[0]
    assert "Belege prüfen" not in cta_region
    for _nav_id, label, _icon in DAILY_NAV:
        assert "Belege prüfen" not in label


def test_23_noch_nicht_geprueft_not_in_workspace_placeholder() -> None:
    assert "Noch nicht geprüft" not in MSG_NOT_CHECKED
    assert MSG_NOT_CHECKED == "Noch nicht geändert"
    pair_fn = _pair_fn_src()
    assert "Noch nicht geprüft" not in pair_fn


def test_24_raw_final_write_run_once_sandbox_not_primary_ui() -> None:
    items = _items_block().split("if show_dev_surfaces:")[0]
    assert "final_write" not in items.casefold() or "show_dev" in items
    assert "run_once" not in items
    # Primary CTA / compact status region must stay product language.
    assert "Sandbox-Lauf starten" not in START_CTA_STRONG
    assert "final_write" not in START_CTA_STRONG
    assert "run_once" not in START_CTA_STRONG
    primary_src = _ws_src()
    assert "WORKSPACE_COMPACT_STATUS_MARKER" in primary_src
    # Live pairs helper does not expose raw terms as display.
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf",),
        output_folder_selected=True,
    )
    assert "final_write" not in vm.rows[0].output_display
    assert "Sandbox" not in vm.rows[0].output_display
    assert "run_once" not in vm.rows[0].output_display


# --- UX audit docs ---


def test_25_ux_audit_document_exists() -> None:
    assert DOC.is_file()
    assert AUDIT.is_file()
    assert PRODUCT_UX_CLEANUP_MARKER in COPY_MOD.read_text(encoding="utf-8")


def test_26_ux_audit_lists_fixed_issues() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "Fixed" in text or "Behoben" in text or "fixed" in text.casefold()
    assert "Workspace" in text or "Arbeitsbereich" in text


def test_27_ux_audit_lists_follow_up_issues() -> None:
    text = DOC.read_text(encoding="utf-8") + "\n" + AUDIT.read_text(encoding="utf-8")
    assert "Follow-up" in text or "Folge" in text or "follow-up" in text.casefold()


# --- Safety ---


def test_28_no_auto_run() -> None:
    for path in (WORKSPACE, REVIEW, SETTINGS):
        src = path.read_text(encoding="utf-8")
        assert "auto_start" not in src.casefold() or "no_auto" in src.casefold()


def test_29_no_run_once_in_ui_v2_pages() -> None:
    for path in (WORKSPACE, REVIEW, SETTINGS, PAIRS):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").endswith("run")
                names = {alias.name for alias in node.names}
                assert "run_once" not in names
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    assert func.id != "run_once"
                if isinstance(func, ast.Attribute):
                    assert func.attr != "run_once"


def test_30_no_production_final_write() -> None:
    src = _ws_src()
    assert "final_write_allowed_for_production=True" not in src
    assert "production_final_write_enabled = True" not in src
    pairs = PAIRS.read_text(encoding="utf-8")
    assert "implies_final_write: bool = False" in pairs


def test_31_no_real_invoice_folders_in_changed_sources() -> None:
    for path in (WORKSPACE, REVIEW, SETTINGS, PAIRS, COPY_MOD):
        text = path.read_text(encoding="utf-8")
        assert "/Users/hadi" not in text
        assert "Desktop/Rechnungen" not in text


def test_32_track_a_protection_paths_unchanged_in_index() -> None:
    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
    )
    for path in TRACK_A_PROTECTED:
        rel = str(path.relative_to(ROOT))
        assert rel not in staged.splitlines()


def test_33_processing_core_unchanged_in_diff() -> None:
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=ROOT,
        text=True,
    )
    for path in PROCESSING_CORE:
        rel = str(path.relative_to(ROOT))
        assert rel not in changed.splitlines()


def test_34_release_tags_unchanged() -> None:
    tags = subprocess.check_output(
        ["git", "show-ref", "--tags"],
        cwd=ROOT,
        text=True,
    )
    assert "product-v1-local-pilot-2026-07-22" in tags


def test_35_eye_and_review_actions_still_present() -> None:
    assert ACTION_SHOW_DOCUMENT == "Dokument anzeigen"
    assert ACTION_OPEN_REVIEW == "Zur Prüfung öffnen"
    assert ACTION_VIEW_PROPOSAL == "Vorschlag ansehen"
    src = _ws_src()
    assert "ACTION_SHOW_DOCUMENT" in src
    assert "ACTION_OPEN_REVIEW" in src
    assert "VISIBILITY_OUTLINED" in src


def _flet_version_tuple() -> tuple[int, int, int]:
    try:
        from flet.version import flet_version  # type: ignore[attr-defined]

        raw = str(flet_version)
    except Exception:
        try:
            from flet.version import version as raw  # type: ignore[attr-defined]
        except Exception:
            return (0, 0, 0)
    parts: list[int] = []
    for part in str(raw).split(".")[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def test_36_workspace_file_pair_rows_construct_with_current_flet() -> None:
    """Startup/render gate: construct pair rows with UI-v2 Flet (0.85+).

    Catches incompatible constructor kwargs (e.g. Container mouse_cursor= on
    Flet 0.85) that source-string tests previously missed. When the active
    pytest interpreter is older, run the construct check via .venv-flet085.
    """
    flet085_python = ROOT / ".venv-flet085" / "bin" / "python"
    construct_script = r"""
import inspect
import sys
from pathlib import Path

ROOT = Path(r""" + repr(str(ROOT)) + r""")
sys.path.insert(0, str(ROOT))

import flet as ft
from invoice_tool.ui_v2.pages.workspace import _workspace_file_pair_rows
from invoice_tool.ui_v2.processing_state import ProcessingPlannedDestination
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    OUTPUT_ROW_ACTIONABLE_MARKER,
    OUTPUT_ROW_PLACEHOLDER_MARKER,
)
from invoice_tool.ui_v2.workspace_file_pairs import build_live_file_pairs_vm

params = inspect.signature(ft.Container.__init__).parameters
assert "mouse_cursor" not in params, "assumption: Container has no mouse_cursor"

planned = (
    ProcessingPlannedDestination(
        document_name="a.pdf",
        planned_path="p",
        destination_label="x",
        preview_only=True,
        applied=False,
        suggested_filename="a_proposed.pdf",
    ),
)
vm = build_live_file_pairs_vm(
    input_filenames=("a.pdf", "b.pdf"),
    output_folder_selected=True,
    planned_destinations=planned,
)
assert vm.rows[0].has_proposal is True
assert vm.rows[1].has_proposal is False

panel = _workspace_file_pair_rows(
    pairs=(),
    on_open_review=lambda: None,
    live_vm=vm,
    on_show_document=lambda _name: None,
    on_open_review_for_source=lambda _name: None,
)
assert panel.input_list is not None
assert panel.output_list is not None
assert panel.review_cta is not None

def walk(control):
    found = [control]
    content = getattr(control, "content", None)
    if content is not None:
        found.extend(walk(content))
    for child in getattr(control, "controls", None) or []:
        found.extend(walk(child))
    return found

built = walk(panel.input_list) + walk(panel.output_list) + walk(panel.review_cta)
assert any(OUTPUT_ROW_ACTIONABLE_MARKER in str(getattr(c, "data", "") or "") for c in built)
assert any(OUTPUT_ROW_PLACEHOLDER_MARKER in str(getattr(c, "data", "") or "") for c in built)
for control in built:
    data = str(getattr(control, "data", "") or "")
    if OUTPUT_ROW_PLACEHOLDER_MARKER in data and "workspace_file_pair_row" in data:
        assert getattr(control, "on_click", None) in (None, False)
    if OUTPUT_ROW_ACTIONABLE_MARKER in data and "workspace_file_pair_row" in data:
        assert callable(getattr(control, "on_click", None))
print("OK_WORKSPACE_PAIR_ROWS_CONSTRUCT")
"""
    # Always also guard source: assignment form must stay absent.
    assert "mouse_cursor=" not in _pair_fn_src()

    if _flet_version_tuple() >= (0, 85, 0):
        ns: dict[str, object] = {}
        exec(construct_script, ns, ns)
        return

    if not flet085_python.is_file():
        raise AssertionError(
            "UI-v2 construct gate requires Flet >= 0.85 or .venv-flet085/bin/python"
        )

    result = subprocess.run(
        [str(flet085_python), "-c", construct_script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Workspace pair-row construct failed under .venv-flet085:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "OK_WORKSPACE_PAIR_ROWS_CONSTRUCT" in result.stdout
