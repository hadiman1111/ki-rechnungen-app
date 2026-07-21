"""Flet-Build-Einstiegspunkt für die Standalone-macOS-App.

Wichtig: Vor ft.run() keine schweren Imports und keine Standalone-Vorbereitung –
Flutter verbindet sich sofort und erwartet den UDS-Server.
"""


def main(page) -> None:  # type: ignore[no-untyped-def]
    from invoice_tool.app_paths import (
        configure_tesseract_runtime,
        ensure_user_config_layout,
        is_standalone_bundle,
    )
    from invoice_tool.startup_log import log_startup, log_startup_exception

    log_startup("app_main.main(page) betreten")
    log_startup(f"Page-Objekt vorhanden: {page is not None}")

    if is_standalone_bundle():
        ensure_user_config_layout()
        configure_tesseract_runtime()
        log_startup("Standalone-Konfiguration und Tesseract vorbereitet")

    try:
        from invoice_tool.gui import build_ui

        log_startup("invoice_tool.gui importiert (lazy)")
        log_startup("UI-Aufbau begonnen")
        build_ui(page)
        log_startup("UI-Aufbau abgeschlossen")
        log_startup(f"page.controls={len(page.controls)}")
        page.update()
        log_startup("erstes Page-Update abgeschlossen")
    except Exception:
        log_startup_exception("Exception während UI-Aufbau")
        raise


if __name__ == "__main__":
    import flet as ft

    from invoice_tool.startup_log import install_exception_hook, log_startup

    install_exception_hook()
    log_startup("app_main.py Entry-Point – starte ft.run sofort")
    run = getattr(ft, "run", None) or ft.app
    run(main)
