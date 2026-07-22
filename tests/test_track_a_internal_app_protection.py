"""Track A internal-app regression / protection gate after Track-B UI-v2 work.

Static + git-index checks only. No GUI window, no PDF processing, no OCR/AI,
no real invoice folders, no processing-core imports as a runtime side effect.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import app_main
import app_ui_v2

ROOT = Path(__file__).resolve().parents[1]

APP_MAIN = ROOT / "app_main.py"
APP_UI_V2 = ROOT / "app_ui_v2.py"
APP_INTERNAL_LAUNCHER = ROOT / "app_internal_launcher.py"

TRACK_A_PROTECTED = (
    APP_MAIN,
    APP_INTERNAL_LAUNCHER,
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
    ROOT / "invoice_tool" / "processing.py",
    ROOT / "invoice_tool" / "routing.py",
    ROOT / "invoice_tool" / "routing_guards.py",
    ROOT / "invoice_tool" / "classification.py",
    ROOT / "invoice_tool" / "target_routing.py",
    ROOT / "invoice_tool" / "run.py",
)

TRACK_A_IMPORT_ROOTS = (
    ROOT / "invoice_tool" / "gui.py",
    ROOT / "invoice_tool" / "ui_shell.py",
    ROOT / "invoice_tool" / "ui_workspace.py",
    ROOT / "invoice_tool" / "ui_configurations.py",
    ROOT / "invoice_tool" / "ui_profiles.py",
    ROOT / "invoice_tool" / "ui_review.py",
    ROOT / "invoice_tool" / "ui_settings.py",
)

TRACK_B_ENTRY_MODULES = (
    APP_UI_V2,
    ROOT / "invoice_tool" / "ui_v2" / "app.py",
    ROOT / "invoice_tool" / "ui_v2" / "export_reporting.py",
    ROOT / "invoice_tool" / "ui_v2" / "sandbox_execution_boundary.py",
    ROOT / "invoice_tool" / "ui_v2" / "local_processing_adapter.py",
)

PRIVATE_DEFAULT_MARKERS = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX",
    "voba",
    "/Users/",
    "Desktop/",
)

# Recent Track-B UI-v2 completion commits (Prompt 1–5 lineage on main).
TRACK_B_COMMIT_SUBJECT_MARKERS = (
    "UI-v2",
    "ui-v2",
    "Sandbox",
    "Pruefworkflow",
    "Profil-Policy",
)


def _module_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


def _git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _staged_names() -> list[str]:
    out = _git_output("diff", "--cached", "--name-only")
    return [line.strip() for line in out.splitlines() if line.strip()]


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def test_entry_files_exist_and_are_distinct() -> None:
    assert APP_MAIN.is_file()
    assert APP_UI_V2.is_file()
    assert APP_INTERNAL_LAUNCHER.is_file()
    assert APP_MAIN.resolve() != APP_UI_V2.resolve()
    assert APP_MAIN.read_text(encoding="utf-8") != APP_UI_V2.read_text(encoding="utf-8")


def test_app_main_points_to_track_a_gui_not_ui_v2() -> None:
    src = APP_MAIN.read_text(encoding="utf-8")
    imports = _module_imports(APP_MAIN)
    assert "invoice_tool.gui" in imports
    assert "build_ui" in src
    assert not any(
        name == "invoice_tool.ui_v2" or name.startswith("invoice_tool.ui_v2.")
        for name in imports
    )
    assert "build_ui_v2" not in src
    assert "invoice_tool.ui_v2" not in src


def test_app_ui_v2_points_to_track_b_ui_v2() -> None:
    src = APP_UI_V2.read_text(encoding="utf-8")
    imports = _module_imports(APP_UI_V2)
    assert "invoice_tool.ui_v2.app" in imports
    assert "build_ui_v2" in src
    assert "invoice_tool.gui" not in imports
    assert "build_ui(" not in src.replace("build_ui_v2", "")


def test_app_internal_launcher_stays_on_internal_path() -> None:
    src = APP_INTERNAL_LAUNCHER.read_text(encoding="utf-8")
    imports = _module_imports(APP_INTERNAL_LAUNCHER)
    assert "invoice_tool.internal_launcher.app" in imports
    assert "build_internal_launcher" in src
    assert not any(
        name == "invoice_tool.ui_v2" or name.startswith("invoice_tool.ui_v2.")
        for name in imports
    )


def test_entry_modules_import_without_launching_gui() -> None:
    """Entry modules expose main() and do not auto-run ft.run on import."""
    assert callable(app_main.main)
    assert callable(app_ui_v2.main)
    app_main_src = APP_MAIN.read_text(encoding="utf-8")
    app_ui_src = APP_UI_V2.read_text(encoding="utf-8")
    assert 'if __name__ == "__main__"' in app_main_src
    assert 'if __name__ == "__main__"' in app_ui_src
    # Module-level body must not call run/app outside the __main__ guard.
    for path in (APP_MAIN, APP_UI_V2):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                raise AssertionError(f"{path.name} has top-level call on import")


def test_track_a_modules_do_not_import_ui_v2() -> None:
    for path in TRACK_A_IMPORT_ROOTS:
        assert path.is_file(), path
        imports = _module_imports(path)
        for name in imports:
            assert name != "invoice_tool.ui_v2"
            assert not name.startswith("invoice_tool.ui_v2.")


def test_track_b_entry_modules_do_not_import_track_a_runtime() -> None:
    forbidden_prefixes = (
        "invoice_tool.gui",
        "invoice_tool.ui_shell",
        "invoice_tool.ui_workspace",
        "invoice_tool.ui_configurations",
        "invoice_tool.ui_profiles",
        "invoice_tool.ui_review",
        "invoice_tool.ui_settings",
        "invoice_tool.ui_profile_dialog",
        "invoice_tool.ui_document_rules",
        "app_main",
        "app_internal_launcher",
    )
    for path in TRACK_B_ENTRY_MODULES:
        assert path.is_file(), path
        imports = _module_imports(path)
        for name in imports:
            assert not any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in forbidden_prefixes
            ), f"{path.name} imports {name}"


def test_track_a_protected_files_unchanged_vs_head() -> None:
    """Working-tree Track A entry/shell modules must match HEAD (except known legacy dirty)."""
    known_legacy_dirty = {
        "invoice_tool/ui_profile_dialog.py",
        "invoice_tool/ui_document_rules.py",
    }
    for path in TRACK_A_PROTECTED:
        rel = _relative(path)
        if rel in known_legacy_dirty:
            continue
        if not path.exists():
            # ui_document_rules may be untracked locally; covered separately.
            continue
        diff = _git_output("diff", "--", rel)
        assert diff == "", f"unexpected Track A dirty file: {rel}"


def test_processing_core_unchanged_vs_head() -> None:
    for path in PROCESSING_CORE:
        assert path.is_file(), path
        diff = _git_output("diff", "--", _relative(path))
        assert diff == "", f"processing-core dirty: {_relative(path)}"


def test_protected_track_a_and_core_not_staged() -> None:
    staged = set(_staged_names())
    forbidden = {_relative(p) for p in TRACK_A_PROTECTED + PROCESSING_CORE}
    forbidden.add("profile_config.local.json")
    hits = sorted(staged & forbidden)
    assert hits == [], f"forbidden staged files: {hits}"


def test_profile_config_local_not_staged() -> None:
    staged = _staged_names()
    assert "profile_config.local.json" not in staged


def test_no_real_invoice_folders_staged() -> None:
    staged = _staged_names()
    banned_substrings = (
        "TEST Rechnungen",
        "Desktop/Programm Belegerfassung/Rechnungen",
        "RECHNUNGEN/",
        ".pdf",
    )
    for name in staged:
        lowered = name.lower()
        assert not name.endswith(".pdf"), name
        for marker in banned_substrings:
            assert marker.lower() not in lowered, name


def test_recent_track_b_commits_exclude_track_a_protected_files() -> None:
    log = _git_output("log", "--oneline", "-30", "--", "invoice_tool/ui_v2")
    commit_ids = [line.split()[0] for line in log.splitlines() if line.strip()]
    assert commit_ids, "expected recent ui_v2 commits"
    protected_rels = {
        _relative(p)
        for p in TRACK_A_PROTECTED + PROCESSING_CORE
        if p.exists() or _relative(p) == "invoice_tool/ui_document_rules.py"
    }
    # Only inspect commits that are clearly Track-B UI-v2 work.
    checked = 0
    for commit in commit_ids[:15]:
        subject = _git_output("log", "-1", "--pretty=%s", commit).strip()
        if not any(marker in subject for marker in TRACK_B_COMMIT_SUBJECT_MARKERS):
            continue
        files = [
            line.strip()
            for line in _git_output("show", "--name-only", "--pretty=format:", commit).splitlines()
            if line.strip()
        ]
        overlap = sorted(set(files) & protected_rels)
        assert overlap == [], f"{commit} ({subject}) touched protected files: {overlap}"
        checked += 1
    assert checked >= 3, "expected several Track-B UI-v2 commits to inspect"


def test_track_b_state_defaults_have_no_private_folder_paths() -> None:
    from invoice_tool.ui_v2.state import UiV2State

    state = UiV2State()
    default_paths = (
        state.workspace_input_folder_override,
        state.workspace_output_folder_override,
        state.workspace_sandbox_root,
        state.workspace_original_source_folder,
        state.workspace_export_path_draft,
    )
    for value in default_paths:
        if value is None:
            continue
        text = str(value)
        for marker in PRIVATE_DEFAULT_MARKERS:
            assert marker not in text, marker
    assert state.workspace_input_folder_override is None
    assert state.workspace_output_folder_override is None
    assert state.workspace_sandbox_root is None
    assert state.workspace_export_path_draft == ""
    assert state.workspace_sandbox_mode is False
    assert state.workspace_copied_data_confirmed is False


def test_track_b_app_source_has_no_private_path_literals_as_defaults() -> None:
    """Entry/bootstrap modules must not hardcode private invoice folder defaults."""
    for path in (APP_UI_V2, ROOT / "invoice_tool" / "ui_v2" / "app.py"):
        src = path.read_text(encoding="utf-8")
        for marker in ("/Users/", "Desktop/Programm Belegerfassung", "TEST Rechnungen"):
            assert marker not in src, f"{path.name}: {marker}"


def test_ui_v2_export_reporting_import_safe() -> None:
    import invoice_tool.ui_v2.app as ui_v2_app
    import invoice_tool.ui_v2.export_reporting as export_reporting

    assert callable(ui_v2_app.build_ui_v2)
    assert hasattr(export_reporting, "build_run_report_view_model") or hasattr(
        export_reporting, "EXPORT_KIND"
    )
