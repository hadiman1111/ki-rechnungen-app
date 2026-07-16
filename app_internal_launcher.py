"""Entry point for the internal SOMAA processing launcher (separate from UI-v2)."""


def main(page) -> None:  # type: ignore[no-untyped-def]
    from invoice_tool.internal_launcher.app import build_internal_launcher

    build_internal_launcher(page)


if __name__ == "__main__":
    import flet as ft

    run = getattr(ft, "run", None) or ft.app
    run(main)
