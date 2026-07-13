"""Separate development entry point for UI-v2 — does not replace app_main.py."""


def main(page) -> None:  # type: ignore[no-untyped-def]
    from invoice_tool.ui_v2.app import build_ui_v2

    build_ui_v2(page)


if __name__ == "__main__":
    import flet as ft

    run = getattr(ft, "run", None) or ft.app
    run(main)
