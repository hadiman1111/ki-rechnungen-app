"""Smoke-/Strukturtests für das lokale macOS-Dock-App-Packaging."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCK_BUILD = ROOT / "scripts" / "build_macos_dock_app.sh"
ROOT_BUILD = ROOT / "build_macos_app.sh"
LAUNCHER = ROOT / "scripts" / "run_internal_launcher_flet085.sh"
LAUNCHER_C = ROOT / "scripts" / "macos_dock_launcher.c"
ENTRY = ROOT / "app_internal_launcher.py"


def test_dock_build_script_exists_and_targets_internal_launcher() -> None:
    assert DOCK_BUILD.is_file()
    content = DOCK_BUILD.read_text(encoding="utf-8")
    assert "run_internal_launcher_flet085.sh" in content
    assert 'APP_NAME="KI-Rechnungen"' in content
    assert 'APP_PATH="${DIST_DIR}/${APP_NAME}.app"' in content
    assert "Library/Logs/KI-Rechnungen" in content
    assert "CFBundleDisplayName" in content
    assert "app_icon.icns" in content
    assert "app_icon.png" in content
    assert "macos_dock_launcher.c" in content
    assert "app_internal_launcher.py" in content
    assert ".venv-flet085/bin/python" in content
    assert "NSDesktopFolderUsageDescription" in content
    assert "FletView" in content
    assert "LSUIElement" in content
    assert "de.kirechnungen.view" in content
    assert "files.user-selected.read-write" in content
    # View must not be hidden via LSUIElement (previous broken approach)
    assert "FletView darf kein LSUIElement" in content
    # Dock icon comes from CFBundleIconName → Assets.car, not only AppIcon.icns
    assert "brand_fletview_assets_car" in content
    assert "Assets.car" in content
    assert "actool" in content
    assert "AppIcon.appiconset" in content
    assert "CFBundleIconName" in content


def test_native_stub_source_has_no_auto_processing() -> None:
    assert LAUNCHER_C.is_file()
    content = LAUNCHER_C.read_text(encoding="utf-8")
    assert "app_internal_launcher" in content
    assert "No automatic invoice processing" in content
    assert "execl" in content
    assert "FLET_VIEW_PATH" in content
    assert "FletView" in content
    assert "fork" not in content  # keep simple execl path that restored launch


def test_root_build_delegates_to_dock_wrapper() -> None:
    assert ROOT_BUILD.is_file()
    content = ROOT_BUILD.read_text(encoding="utf-8")
    assert "build_macos_dock_app.sh" in content


def test_launcher_script_points_to_app_internal_launcher() -> None:
    assert LAUNCHER.is_file()
    content = LAUNCHER.read_text(encoding="utf-8")
    assert "app_internal_launcher.py" in content
    assert ".venv-flet085" in content


def test_app_internal_launcher_entry_has_no_auto_run() -> None:
    source = ENTRY.read_text(encoding="utf-8")
    ast.parse(source)  # Syntax gültig
    assert "build_internal_launcher" in source
    assert "invoice_tool.processing" not in source
    assert "RunController" not in source
    assert "_prefer_env_flet_view_path" in source
    assert "FLET_VIEW_PATH" in source


def test_dock_build_script_bash_syntax() -> None:
    subprocess.run(["bash", "-n", str(DOCK_BUILD)], check=True)
    subprocess.run(["bash", "-n", str(ROOT_BUILD)], check=True)
    subprocess.run(["bash", "-n", str(LAUNCHER)], check=True)
