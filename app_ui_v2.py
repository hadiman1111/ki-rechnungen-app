"""Separate development entry point for UI-v2 — does not replace app_main.py."""


def main(page) -> None:  # type: ignore[no-untyped-def]
    """Mount UI-v2 workspace or a visible startup diagnostic (never blank)."""
    from invoice_tool.ui_v2.app import build_ui_v2  # noqa: F401 — Track-B entry contract
    from invoice_tool.ui_v2.startup_diagnostics import start_ui_v2

    # build_ui_v2 remains the root builder; start_ui_v2 guards blank windows
    # (wrong Flet / swallowed startup exceptions) and calls build_ui_v2 when safe.
    start_ui_v2(page)


if __name__ == "__main__":
    import flet as ft

    run = getattr(ft, "run", None) or ft.app
    run(main)
