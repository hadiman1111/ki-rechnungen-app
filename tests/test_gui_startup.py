from __future__ import annotations

import ast
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.gui_workspace_helpers import (
    assert_document_rules_layout,
    assert_layout_regressions_fixed,
    assert_navigation_shell,
    assert_no_raw_hex_in_ui_modules,
    assert_workspace_present,
    iter_controls,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_MAIN_PATH = PROJECT_ROOT / "app_main.py"
GUI_PATH = PROJECT_ROOT / "invoice_tool" / "gui.py"
UI_STARTUP_FILES = [
    GUI_PATH,
    PROJECT_ROOT / "invoice_tool" / "ui_document_rules.py",
    PROJECT_ROOT / "invoice_tool" / "ui_profile_dialog.py",
]
LEGACY_FLET_HELPERS = (
    "ft.padding.",
    "ft.margin.",
    "ft.border.",
    "ft.border_radius.",
)


def _flet_version_tuple() -> tuple[int, int, int]:
    try:
        from flet.version import flet_version
    except Exception:
        return (0, 0, 0)
    parts = [int(part) for part in str(flet_version).split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


requires_flet_085 = pytest.mark.skipif(
    _flet_version_tuple() < (0, 85, 0),
    reason="Erfordert Flet >= 0.85 für Padding/Border-Klassen-API",
)


def _install_gui_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    import types

    config_mod = types.ModuleType("invoice_tool.config")

    class ConfigError(Exception):
        pass

    config_mod.ConfigError = ConfigError
    config_mod.load_app_config = lambda _config_path=None: SimpleNamespace(
        source_dir=Path("/tmp/in"),
        output_dir=Path("/tmp/out"),
        preset_name="test",
        regeln_datei=Path("/tmp/office_rules.json"),
        aktives_preset="test",
        eingangsordner=Path("/tmp/in"),
        ausgangsordner=Path("/tmp/out"),
    )
    config_mod.load_office_rules = lambda _rules_path, active_preset_override=None: SimpleNamespace(
        active_preset=active_preset_override or "test"
    )
    monkeypatch.setitem(sys.modules, "invoice_tool.config", config_mod)

    run_mod = types.ModuleType("invoice_tool.run")

    class RunError(Exception):
        pass

    run_mod.RunError = RunError
    run_mod.run_once = lambda *_args, **_kwargs: Path("/tmp/run")
    monkeypatch.setitem(sys.modules, "invoice_tool.run", run_mod)


def _build_test_page(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, list[object]]:
    _install_gui_stubs(monkeypatch)
    monkeypatch.delenv("FLET_PLATFORM", raising=False)

    added: list[object] = []
    page = MagicMock()
    page.controls = []
    page.services = SimpleNamespace(register_service=lambda _service: None)

    def _add(*controls: object) -> None:
        added.extend(controls)
        page.controls.extend(controls)

    def _run_task(handler: object, *args: object, **kwargs: object) -> None:
        if not callable(handler):
            raise TypeError("handler must be a coroutine function")
        asyncio.run(handler(*args, **kwargs))  # type: ignore[misc,operator]

    page.add.side_effect = _add
    page.update = MagicMock()
    page.run_task = _run_task
    page.run_thread = MagicMock()

    return page, added


def test_app_main_does_not_import_gui_at_module_level() -> None:
    tree = ast.parse(APP_MAIN_PATH.read_text(encoding="utf-8"))
    imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("invoice_tool.gui")
    ]
    assert imports == []


def test_app_main_defines_page_handler_and_ft_run_entrypoint() -> None:
    source = APP_MAIN_PATH.read_text(encoding="utf-8")
    assert "def main(page" in source
    assert "run(main)" in source


def test_startup_ui_files_do_not_use_legacy_flet_module_helpers() -> None:
    offenders: list[str] = []
    for path in UI_STARTUP_FILES:
        source = path.read_text(encoding="utf-8")
        for helper in LEGACY_FLET_HELPERS:
            if helper in source:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}: {helper}")
    assert offenders == []


@requires_flet_085
def test_build_ui_adds_expected_controls(monkeypatch: pytest.MonkeyPatch) -> None:
    page, added = _build_test_page(monkeypatch)

    from invoice_tool.gui import build_ui

    build_ui(page)

    assert len(page.controls) >= 1
    assert page.update.call_count >= 1
    assert_workspace_present(page.controls)


@requires_flet_085
def test_build_ui_workspace_contains_processing_area(monkeypatch: pytest.MonkeyPatch) -> None:
    page, _added = _build_test_page(monkeypatch)

    from invoice_tool.gui import build_ui

    build_ui(page)

    workspace_info = assert_workspace_present(page.controls)
    assert "Verarbeitung starten" in workspace_info["labels"]
    assert workspace_info["root"].__class__.__name__ == "Container"


@requires_flet_085
def test_filepicker_handlers_update_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    import flet as ft

    page, _added = _build_test_page(monkeypatch)

    class _StubFilePicker:
        def __init__(self, picked_path: str) -> None:
            self._picked_path = picked_path

        async def get_directory_path(self, **_kwargs: object) -> str:
            return self._picked_path

    monkeypatch.setattr(
        ft,
        "FilePicker",
        lambda: _StubFilePicker("/tmp/picked-source"),
    )

    from invoice_tool.gui import build_ui

    build_ui(page)
    workspace_info = assert_workspace_present(page.controls)

    source_before = workspace_info["read_only_path_fields"][0].value
    pick_buttons = workspace_info["pick_buttons"]
    pick_buttons[0].on_click(MagicMock())

    source_after = workspace_info["read_only_path_fields"][0].value
    assert source_after == "/tmp/picked-source"
    assert source_after != source_before or source_before in (None, "", "/tmp/in")


@requires_flet_085
def test_filepicker_cancel_preserves_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import flet as ft

    page, _added = _build_test_page(monkeypatch)

    class _CancelFilePicker:
        async def get_directory_path(self, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr(ft, "FilePicker", _CancelFilePicker)

    from invoice_tool.gui import build_ui

    build_ui(page)
    workspace_info = assert_workspace_present(page.controls)

    path_field = workspace_info["read_only_path_fields"][0]
    path_field.value = "/tmp/unchanged"
    before = path_field.value
    workspace_info["pick_buttons"][0].on_click(MagicMock())
    assert path_field.value == before


@requires_flet_085
def test_ordner_waehlen_invokes_run_task_with_coroutine_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import inspect

    import flet as ft

    page, _added = _build_test_page(monkeypatch)
    run_task_calls: list[tuple[object, tuple[object, ...]]] = []

    class _StubFilePicker:
        async def get_directory_path(self, **_kwargs: object) -> str:
            return "/tmp/picked-source"

    # Flet 0.85 requires FilePicker on the page; stub avoids real dialog / page binding.
    monkeypatch.setattr(ft, "FilePicker", lambda: _StubFilePicker())

    def _run_task(handler: object, *args: object, **kwargs: object) -> None:
        run_task_calls.append((handler, args))
        asyncio.run(handler(*args, **kwargs))  # type: ignore[misc,operator]

    page.run_task = _run_task

    from invoice_tool.gui import build_ui

    build_ui(page)
    workspace_info = assert_workspace_present(page.controls)

    for pick_button in workspace_info["pick_buttons"]:
        pick_button.on_click(MagicMock())
        handler, _args = run_task_calls[-1]
        assert inspect.iscoroutinefunction(handler), (
            "page.run_task muss die Coroutine-Funktion erhalten, nicht das Coroutine-Objekt"
        )


@requires_flet_085
def test_no_filepicker_in_visible_control_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    page, added = _build_test_page(monkeypatch)

    from invoice_tool.gui import build_ui

    build_ui(page)

    visible_types = {
        type(control).__name__
        for control in iter_controls(added[0])
    }
    assert "FilePicker" not in visible_types


def test_app_main_has_no_diagnostic_startup_text() -> None:
    source = APP_MAIN_PATH.read_text(encoding="utf-8")
    assert "KI-Rechnungen UI gestartet" not in source


@requires_flet_085
def test_build_ui_layout_regressions_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    page, _added = _build_test_page(monkeypatch)

    from invoice_tool.gui import build_ui

    build_ui(page)
    assert_workspace_present(page.controls)
    assert_layout_regressions_fixed(page.controls)


@requires_flet_085
def test_build_ui_navigation_shell_present(monkeypatch: pytest.MonkeyPatch) -> None:
    page, _added = _build_test_page(monkeypatch)

    from invoice_tool.gui import build_ui

    build_ui(page)
    assert_navigation_shell(page.controls[-1])


def test_ui_modules_avoid_raw_hex_colors() -> None:
    assert_no_raw_hex_in_ui_modules()


@requires_flet_085
def test_document_rules_view_layout_regressions_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    page, _added = _build_test_page(monkeypatch)

    from invoice_tool.ui_document_rules import build_document_rules_view

    rules_view = build_document_rules_view(
        page=page,
        profile_path=None,
        on_back=lambda: None,
    )
    assert_document_rules_layout(rules_view)


def test_gui_main_delegates_to_flet_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def _fake_run(target: object, **_kwargs: object) -> None:
        calls.append(target)

    import invoice_tool.gui as gui_module

    run_attr = getattr(gui_module.ft, "run", None) or getattr(gui_module.ft, "app")
    monkeypatch.setattr(gui_module.ft, run_attr.__name__, _fake_run)

    from invoice_tool.gui import build_ui, main

    main()

    assert calls == [build_ui]


# ---------------------------------------------------------------------------
# UI-v2 startup / render gate — catches blank blue window regressions
# ---------------------------------------------------------------------------

APP_UI_V2_PATH = PROJECT_ROOT / "app_ui_v2.py"
REQUIRED_UI_V2_NAV = ("Arbeitsbereich", "Profile", "Konfigurationen", "Prüfung")
FORBIDDEN_UI_V2_NORMAL_NAV = (
    "Entwickler / Diagnose",
    "Oracle",
    "Test & Nachweis",
    "Dry Run",
    "Sandbox",
)


def _collect_ui_v2_labels(root: object) -> set[str]:
    from invoice_tool.ui_v2.control_tree import collect_labels, iter_controls

    labels = set(collect_labels(root))
    for control in iter_controls(root):
        key = getattr(control, "key", None)
        if isinstance(key, str) and key.strip():
            labels.add(key)
    return labels


def _find_ui_v2_key(root: object, key: str) -> object | None:
    from invoice_tool.ui_v2.control_tree import iter_controls

    for control in iter_controls(root):
        if getattr(control, "key", None) == key:
            return control
    return None


def _build_ui_v2_test_page(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    monkeypatch.delenv("FLET_PLATFORM", raising=False)
    monkeypatch.delenv("KI_RECHNUNGEN_UI_V2_SHOW_DEV_SURFACES", raising=False)
    page = MagicMock()
    page.controls = []
    page.overlay = []
    page.window = MagicMock()
    page.services = SimpleNamespace(register_service=lambda _service: None)

    def _add(*controls: object) -> None:
        page.controls.extend(controls)

    page.add.side_effect = _add
    page.update = MagicMock()
    page.clean = MagicMock()
    return page


def test_app_ui_v2_refuses_wrong_flet_before_window() -> None:
    source = APP_UI_V2_PATH.read_text(encoding="utf-8")
    assert "_refuse_wrong_flet_before_window" in source
    assert "flet_meets_ui_v2_requirement" in source
    assert "SystemExit" in source
    assert "start_ui_v2" in source
    assert "build_ui_v2" in source


@requires_flet_085
def test_ui_v2_startup_mounts_non_empty_shell_with_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank blue window regression: page.controls, nav, and Arbeitsbereich must render."""
    page = _build_ui_v2_test_page(monkeypatch)
    monkeypatch.setenv("KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS", "1")

    from invoice_tool.ui_v2.startup_diagnostics import start_ui_v2

    mode = start_ui_v2(page)
    assert mode == "workspace"
    assert page.controls, "page.controls must not be empty after UI-v2 init"
    assert len(page.controls) >= 1
    assert page.update.call_count >= 1

    root = page.controls[0]
    labels = _collect_ui_v2_labels(root)
    assert _find_ui_v2_key(root, "ui-v2-shell") is not None
    assert _find_ui_v2_key(root, "ui-v2-sidebar") is not None
    assert _find_ui_v2_key(root, "ui-v2-content-host") is not None

    for label in REQUIRED_UI_V2_NAV:
        assert label in labels, f"navigation missing: {label}"
    assert "NAME.IT PRO" in labels

    for label in FORBIDDEN_UI_V2_NORMAL_NAV:
        assert label not in labels, f"developer surface leaked into normal UI: {label}"

    content_host = _find_ui_v2_key(root, "ui-v2-content-host")
    assert content_host is not None
    assert getattr(content_host, "content", None) is not None
    content_labels = _collect_ui_v2_labels(content_host)
    assert content_labels, "Arbeitsbereich must render visible content, not only background"
    assert "Arbeitsbereich" in content_labels

    # Shell must use Row layout (Stack+absolute collapsed to a blank blue client).
    shell = _find_ui_v2_key(root, "ui-v2-shell")
    assert shell is not None
    assert getattr(shell, "content", None).__class__.__name__ == "Row"
    assert "shell_row_layout" in str(getattr(shell, "data", "") or "")


@requires_flet_085
def test_ui_v2_dev_defaults_do_not_empty_product_ui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _build_ui_v2_test_page(monkeypatch)
    monkeypatch.setenv("KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS", "1")
    monkeypatch.delenv("KI_RECHNUNGEN_UI_V2_SHOW_DEV_SURFACES", raising=False)

    from invoice_tool.ui_v2.app import build_ui_v2

    build_ui_v2(page)
    assert page.controls
    labels = _collect_ui_v2_labels(page.controls[0])
    for label in REQUIRED_UI_V2_NAV:
        assert label in labels
    assert "Entwickler / Diagnose" not in labels
    assert "Test & Nachweis" not in labels
    assert "Oracle" not in labels


@requires_flet_085
def test_ui_v2_empty_mount_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2 import app as app_mod

    page = _build_ui_v2_test_page(monkeypatch)

    def _empty_add(*_controls: object) -> None:
        # Simulate a failed mount that never attaches the shell.
        return

    page.add.side_effect = _empty_add
    with pytest.raises(RuntimeError, match="page.controls is empty"):
        app_mod.build_ui_v2(page)
