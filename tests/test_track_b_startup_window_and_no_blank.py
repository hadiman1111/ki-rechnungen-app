"""Track-B Startup Window & No-Blank Root (2026-07-27).

Sensible initial/min window size, loading surface instead of blank root.
No productive processing, no Track-A/core changes.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from invoice_tool.ui_v2.theme import (
    APP_MIN_HEIGHT,
    APP_MIN_WIDTH,
    APP_WINDOW_HEIGHT,
    APP_WINDOW_WIDTH,
)
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    MSG_STARTUP_LOADING,
    STARTUP_NO_BLANK_MARKER,
    STARTUP_WINDOW_SIZE_MARKER,
)

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "invoice_tool" / "ui_v2" / "app.py"
APP_UI_V2 = ROOT / "app_ui_v2.py"
TOKENS = ROOT / "invoice_tool" / "ui_v2" / "tokens.py"

try:
    import flet as ft

    _flet_ok = tuple(int(x) for x in str(getattr(ft, "version", "0.0.0")).split(".")[:3] if str(x).isdigit())
    if len(_flet_ok) < 3:
        from invoice_tool.ui_v2.startup_diagnostics import flet_meets_ui_v2_requirement

        requires_flet_085 = pytest.mark.skipif(
            not flet_meets_ui_v2_requirement(),
            reason="Flet >= 0.85 required",
        )
    else:
        from invoice_tool.ui_v2.startup_diagnostics import flet_meets_ui_v2_requirement

        requires_flet_085 = pytest.mark.skipif(
            not flet_meets_ui_v2_requirement(),
            reason="Flet >= 0.85 required",
        )
except Exception:  # noqa: BLE001
    requires_flet_085 = pytest.mark.skip(reason="Flet not available")


def test_01_window_dimensions_sensible() -> None:
    assert 1280 <= APP_WINDOW_WIDTH <= 1400
    assert 850 <= APP_WINDOW_HEIGHT <= 950
    assert 1180 <= APP_MIN_WIDTH <= 1200
    assert 760 <= APP_MIN_HEIGHT <= 820
    src = APP.read_text(encoding="utf-8")
    assert "APP_WINDOW_WIDTH" in src
    assert "APP_MIN_HEIGHT" in src
    assert "STARTUP_WINDOW_SIZE_MARKER" in src
    assert STARTUP_WINDOW_SIZE_MARKER == "track_b_startup_sensible_window_size_v1"
    geom = src.split("def _apply_startup_window_geometry")[1].split("def build_ui_v2")[0]
    assert "APP_WINDOW_HEIGHT" in geom
    assert "page.window.height = 800" not in src


def test_02_startup_loading_surface_in_source() -> None:
    src = APP.read_text(encoding="utf-8")
    assert "_mount_startup_loading_surface" in src
    assert MSG_STARTUP_LOADING == "Belegerfassung wird geladen …"
    assert "STARTUP_NO_BLANK_MARKER" in src
    assert STARTUP_NO_BLANK_MARKER == "track_b_startup_no_blank_loading_surface_v1"
    assert "no_blank_root" in src
    assert "page.bgcolor" in src or "COLOR_PAGE_BG" in src


def test_03_tokens_define_window_constants() -> None:
    text = TOKENS.read_text(encoding="utf-8")
    assert "APP_WINDOW_WIDTH" in text
    assert "APP_WINDOW_HEIGHT" in text
    assert "APP_MIN_HEIGHT" in text


@requires_flet_085
def test_04_build_sets_window_and_non_empty_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KI_RECHNUNGEN_UI_V2_SHOW_DEV_SURFACES", raising=False)
    monkeypatch.setenv("KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS", "1")
    page = MagicMock()
    page.controls = []
    page.overlay = []
    page.window = MagicMock()
    page.services = SimpleNamespace(register_service=lambda _service: None)

    def _add(*controls: object) -> None:
        page.controls.extend(controls)

    page.add.side_effect = _add
    page.update = MagicMock()

    from invoice_tool.ui_v2.app import build_ui_v2

    build_ui_v2(page)
    assert page.window.width == APP_WINDOW_WIDTH
    assert page.window.height == APP_WINDOW_HEIGHT
    assert page.window.min_width == APP_MIN_WIDTH
    assert page.window.min_height == APP_MIN_HEIGHT
    assert page.controls, "page.controls must not be empty after mount"
    assert page.update.call_count >= 1
    assert STARTUP_WINDOW_SIZE_MARKER in str(getattr(page, "data", "") or "")


def test_05_app_ui_v2_entry_guards_blank() -> None:
    src = APP_UI_V2.read_text(encoding="utf-8")
    assert "start_ui_v2" in src
    assert "_refuse_wrong_flet_before_window" in src
