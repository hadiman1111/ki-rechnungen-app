"""Track-B GUI visual smoke — blank-window evidence intake and startup triage.

No GUI window launch for humans, no PDF processing, no productive runs,
no real invoice folders.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_UI_V2 = ROOT / "app_ui_v2.py"
STARTUP_DIAG = ROOT / "invoice_tool" / "ui_v2" / "startup_diagnostics.py"
GUIDE = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_GUI_VISUAL_SMOKE_EVIDENCE_INTAKE_AND_BLANK_WINDOW_TRIAGE_2026-07-22.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_GUI_VISUAL_SMOKE_EVIDENCE_INTAKE_AND_BLANK_WINDOW_TRIAGE_2026-07-22.md"
)

FORBIDDEN_REAL_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)


def _flet_version_tuple() -> tuple[int, int, int]:
    from invoice_tool.ui_v2.startup_diagnostics import get_flet_version_tuple

    return get_flet_version_tuple()


def _iter_controls(root: object):
    if root is None:
        return
    yield root
    content = getattr(root, "content", None)
    if content is not None:
        if isinstance(content, list):
            for item in content:
                yield from _iter_controls(item)
        else:
            yield from _iter_controls(content)
    controls = getattr(root, "controls", None)
    if controls:
        for item in controls:
            yield from _iter_controls(item)


def _collect_text(root: object) -> set[str]:
    labels: set[str] = set()
    for control in _iter_controls(root):
        value = getattr(control, "value", None)
        if isinstance(value, str) and value.strip():
            labels.add(value)
        key = getattr(control, "key", None)
        if isinstance(key, str) and key.strip():
            labels.add(key)
    return labels


def _make_page() -> MagicMock:
    page = MagicMock()
    page.controls = []
    page.overlay = []
    page.window = MagicMock()
    page.services = SimpleNamespace(register_service=lambda _service: None)

    def _add(*controls: object) -> None:
        page.controls.extend(controls)

    def _clean() -> None:
        page.controls.clear()

    page.add.side_effect = _add
    page.clean.side_effect = _clean
    page.update = MagicMock()
    return page


def test_app_ui_v2_entrypoint_exists() -> None:
    assert APP_UI_V2.is_file()
    assert STARTUP_DIAG.is_file()


def test_startup_target_importable_without_productive_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    run_once_calls: list[object] = []

    def _blocked_run_once(*_a: object, **_k: object) -> None:
        run_once_calls.append((_a, _k))
        raise AssertionError("run_once must not run during startup import")

    monkeypatch.setitem(sys.modules, "invoice_tool.run", SimpleNamespace(run_once=_blocked_run_once))
    mod = importlib.import_module("app_ui_v2")
    importlib.reload(mod)
    assert callable(mod.main)
    from invoice_tool.ui_v2.startup_diagnostics import start_ui_v2

    assert callable(start_ui_v2)
    assert run_once_calls == []


def test_default_root_render_produces_visible_control_or_diagnostic() -> None:
    from invoice_tool.ui_v2.startup_diagnostics import (
        DIAGNOSTIC_KEY,
        start_ui_v2,
    )

    page = _make_page()
    mode = start_ui_v2(page)
    assert mode in {"workspace", "diagnostic"}
    assert page.controls, "blank render is not allowed"
    texts = set()
    for root in page.controls:
        texts |= _collect_text(root)
    assert texts, "at least one visible label/key required"
    if mode == "diagnostic":
        assert DIAGNOSTIC_KEY in texts or any("Flet" in t or "Start" in t for t in texts)
    else:
        assert any(
            key in texts for key in ("ui-v2-shell", "ui-v2-sidebar", "Arbeitsbereich", "NAME.IT PRO")
        ) or any("Arbeitsbereich" in t or "Sandbox" in t or "ui-v2" in t for t in texts)


def test_workspace_route_or_diagnostic_is_reachable() -> None:
    from invoice_tool.ui_v2.navigation import NAV_WORKSPACE
    from invoice_tool.ui_v2.startup_diagnostics import flet_meets_ui_v2_requirement, start_ui_v2

    page = _make_page()
    mode = start_ui_v2(page)
    assert page.controls
    if flet_meets_ui_v2_requirement():
        assert mode == "workspace"
        assert NAV_WORKSPACE == "arbeitsbereich"
        texts = set()
        for root in page.controls:
            texts |= _collect_text(root)
        assert "ui-v2-shell" in texts or "Arbeitsbereich" in texts
    else:
        assert mode == "diagnostic"


def test_blank_render_not_allowed_even_on_startup_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2 import startup_diagnostics as sd

    monkeypatch.setattr(sd, "flet_meets_ui_v2_requirement", lambda: True)

    def _boom(_page: object) -> None:
        raise RuntimeError("synthetic startup failure")

    monkeypatch.setattr(
        "invoice_tool.ui_v2.app.build_ui_v2",
        _boom,
        raising=False,
    )
    # Ensure import path used inside start_ui_v2 is patched.
    import invoice_tool.ui_v2.app as app_mod

    monkeypatch.setattr(app_mod, "build_ui_v2", _boom)

    page = _make_page()
    mode = sd.start_ui_v2(page)
    assert mode == "diagnostic"
    assert page.controls
    texts = set()
    for root in page.controls:
        texts |= _collect_text(root)
    assert sd.DIAGNOSTIC_KEY in texts or any("Startfehler" in t for t in texts)
    assert any("synthetic startup failure" in t for t in texts)


def test_no_run_once_during_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _run_once(*_a: object, **_k: object) -> None:
        calls.append("run_once")

    fake_run = SimpleNamespace(run_once=_run_once)
    monkeypatch.setitem(sys.modules, "invoice_tool.run", fake_run)
    monkeypatch.setattr(
        "invoice_tool.ui_v2.startup_diagnostics.flet_meets_ui_v2_requirement",
        lambda: False,
    )
    from invoice_tool.ui_v2.startup_diagnostics import start_ui_v2

    start_ui_v2(_make_page())
    assert calls == []


def test_no_pdf_or_productive_processing_during_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    forbidden_hits: list[str] = []

    class _Guard:
        def __getattr__(self, name: str):  # noqa: ANN001
            forbidden_hits.append(name)

            def _blocked(*_a: object, **_k: object) -> None:
                raise AssertionError(f"forbidden processing call: {name}")

            return _blocked

    monkeypatch.setitem(sys.modules, "invoice_tool.processing", _Guard())
    monkeypatch.setitem(sys.modules, "invoice_tool.run", _Guard())
    monkeypatch.setattr(
        "invoice_tool.ui_v2.startup_diagnostics.flet_meets_ui_v2_requirement",
        lambda: False,
    )
    from invoice_tool.ui_v2.startup_diagnostics import start_ui_v2

    start_ui_v2(_make_page())
    assert forbidden_hits == []


def test_no_real_invoice_folders_touched_in_startup_sources() -> None:
    for path in (APP_UI_V2, STARTUP_DIAG):
        text = path.read_text(encoding="utf-8")
        for folder in FORBIDDEN_REAL_FOLDERS:
            assert folder not in text


def test_app_ui_v2_main_uses_safe_start_and_keeps_build_ui_v2_contract() -> None:
    src = APP_UI_V2.read_text(encoding="utf-8")
    assert "start_ui_v2" in src
    assert "build_ui_v2" in src
    assert "invoice_tool.ui_v2.app" in src
    tree = ast.parse(src)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert "invoice_tool.ui_v2.app" in imported
    assert "invoice_tool.ui_v2.startup_diagnostics" in imported


def test_startup_exception_is_logged(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2 import startup_diagnostics as sd
    import invoice_tool.ui_v2.app as app_mod

    monkeypatch.setattr(sd, "flet_meets_ui_v2_requirement", lambda: True)

    def _boom(_page: object) -> None:
        raise ValueError("logged-startup-error")

    monkeypatch.setattr(app_mod, "build_ui_v2", _boom)
    page = _make_page()
    sd.start_ui_v2(page)
    err = capsys.readouterr().err
    assert "logged-startup-error" in err or "UI-v2 startup" in err


def test_triage_docs_exist() -> None:
    assert GUIDE.is_file()
    assert AUDIT.is_file()
    guide = GUIDE.read_text(encoding="utf-8")
    assert "GUI_VISUAL_SMOKE_BLOCKED" in guide
    assert ".venv-flet085/bin/python app_ui_v2.py" in guide
    assert "Padding.symmetric" in guide or "Flet" in guide
