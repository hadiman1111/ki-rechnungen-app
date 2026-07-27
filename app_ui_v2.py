"""Separate development entry point for UI-v2 — does not replace app_main.py."""

from __future__ import annotations

import sys


def _refuse_wrong_flet_before_window() -> None:
    """Exit before ft.run when Flet < 0.85 — avoids the empty light-blue client window.

    Opening a Flet 0.85 desktop client against a Flet 0.28 Python process leaves a
    blank blue window; the in-page diagnostic never becomes visible. Fail fast.
    """

    from invoice_tool.ui_v2.startup_diagnostics import (
        flet_meets_ui_v2_requirement,
        format_flet_version,
        wrong_flet_version_message,
    )

    if flet_meets_ui_v2_requirement():
        return
    title, detail, hint = wrong_flet_version_message()
    print(f"[UI-v2 startup] {title}", file=sys.stderr)
    print(detail, file=sys.stderr)
    print(hint, file=sys.stderr)
    print(
        f"Abbruch vor Fensterstart (gefunden: Flet {format_flet_version()}). "
        "Kein leeres blaues Fenster.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def main(page) -> None:  # type: ignore[no-untyped-def]
    """Mount UI-v2 workspace or a visible startup diagnostic (never blank)."""
    from invoice_tool.ui_v2.app import build_ui_v2  # noqa: F401 — Track-B entry contract
    from invoice_tool.ui_v2.dev_defaults import enable_track_b_dev_defaults_for_local_entry
    from invoice_tool.ui_v2.startup_diagnostics import start_ui_v2

    # Track-B manual-smoke convenience only (local UI-v2 entry). Not product defaults.
    # DEV_DEFAULTS=1 → controlled test folders/profile smoke data only.
    # SHOW_DEV_SURFACES=1 → Entwickler Diagnose / Test & Nachweis / Oracle UI.
    # Opt out: KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=0
    # Opt in:  KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv-flet085/bin/python app_ui_v2.py
    enable_track_b_dev_defaults_for_local_entry(app_path=__file__)

    # build_ui_v2 remains the root builder; start_ui_v2 guards blank windows
    # (wrong Flet / swallowed startup exceptions) and calls build_ui_v2 when safe.
    start_ui_v2(page)


if __name__ == "__main__":
    import flet as ft

    from invoice_tool.ui_v2.dev_defaults import enable_track_b_dev_defaults_for_local_entry

    # Never open a desktop client with the wrong Flet — that yields a blank blue window.
    _refuse_wrong_flet_before_window()

    enable_track_b_dev_defaults_for_local_entry(app_path=__file__)
    run = getattr(ft, "run", None) or ft.app
    run(main)
