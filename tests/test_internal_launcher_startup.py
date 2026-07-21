from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ENTRY = PROJECT_ROOT / "app_internal_launcher.py"
LAUNCHER_APP = PROJECT_ROOT / "invoice_tool" / "internal_launcher" / "app.py"


def test_entry_imports() -> None:
    import app_internal_launcher  # noqa: F401

    assert hasattr(app_internal_launcher, "main")


def test_page_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    import flet as ft

    from invoice_tool.internal_launcher.app import build_internal_launcher
    from invoice_tool.internal_launcher.profile_display import ProfileDisplayInfo

    page = MagicMock()
    page.window = SimpleNamespace(
        width=720,
        height=620,
        min_width=640,
        min_height=560,
        prevent_close=False,
        on_event=None,
    )
    added: list[object] = []

    def _add(*controls: object) -> None:
        added.extend(controls)

    page.add = _add
    page.update = MagicMock()

    def _run_task(handler: object, *_args: object, **_kwargs: object) -> None:
        if callable(handler):
            handler()

    page.run_task = _run_task

    profile = ProfileDisplayInfo(
        ok=True,
        profile_name="SOMAA Profil – Lokale Arbeitskopie",
        scan_model_id="rechnungen",
        scan_model_label="Rechnungsdaten",
        profile_path=Path("/tmp/profile.json"),
    )
    monkeypatch.setattr(
        "invoice_tool.internal_launcher.app.load_active_profile_display",
        lambda: profile,
    )
    monkeypatch.setattr(
        "invoice_tool.internal_launcher.app.RunController",
        lambda **_kwargs: MagicMock(is_running=lambda: False),
    )

    build_internal_launcher(page)
    assert added
    assert page.title == "KI-Rechnungen — Interner Verarbeitungsstart"


def test_start_disabled_without_valid_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.internal_launcher.app import build_internal_launcher
    from invoice_tool.internal_launcher.profile_display import ProfileDisplayInfo

    page = MagicMock()
    page.window = SimpleNamespace(
        width=720,
        height=620,
        min_width=640,
        min_height=560,
        prevent_close=False,
        on_event=None,
    )
    controls: list[object] = []

    def _collect(*items: object) -> None:
        for control in items:
            controls.append(control)
            if hasattr(control, "controls"):
                for child in control.controls:
                    _collect(child)
            content = getattr(control, "content", None)
            if content is not None and content is not control:
                _collect(content)

    page.add = _collect
    page.update = MagicMock()
    page.run_task = lambda handler, *_a, **_k: handler() if callable(handler) else None

    monkeypatch.setattr(
        "invoice_tool.internal_launcher.app.load_active_profile_display",
        lambda: ProfileDisplayInfo(
            ok=True,
            profile_name="Test",
            scan_model_id="rechnungen",
            scan_model_label="Rechnungsdaten",
            profile_path=Path("/tmp/profile.json"),
        ),
    )
    monkeypatch.setattr(
        "invoice_tool.internal_launcher.app.RunController",
        lambda **_kwargs: MagicMock(is_running=lambda: False),
    )

    build_internal_launcher(page)
    start_buttons = [
        control
        for control in controls
        if getattr(control, "__class__", None).__name__ == "FilledButton"
        and getattr(control, "text", "") == "Verarbeitung starten"
    ]
    assert start_buttons
    assert start_buttons[0].disabled is True


def test_no_processing_on_startup() -> None:
    source = LAUNCHER_APP.read_text(encoding="utf-8")
    assert "execute(" not in source
    assert "start_async(" in source


def test_protected_ui_v2_not_imported() -> None:
    tree = ast.parse(APP_ENTRY.read_text(encoding="utf-8"))
    imports = {
        node.names[0].name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("invoice_tool.ui_v2")
    }
    assert not imports

    launcher_tree = ast.parse(LAUNCHER_APP.read_text(encoding="utf-8"))
    ui_v2_imports = [
        node
        for node in ast.walk(launcher_tree)
        if isinstance(node, ast.ImportFrom) and node.module and "ui_v2" in node.module
    ]
    assert not ui_v2_imports
