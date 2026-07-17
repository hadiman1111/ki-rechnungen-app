"""Entry point for the internal SOMAA processing launcher (separate from UI-v2)."""

from __future__ import annotations

import os


def _prefer_env_flet_view_path() -> None:
    """Make FLET_VIEW_PATH win over cwd ``build/macos`` (Flet default order).

    Flet desktop resolves macOS clients as: build/macos → FLET_VIEW_PATH → cache.
    The Dock-App bundles a branded LSUIElement client and sets FLET_VIEW_PATH; if a
    leftover ``build/macos/*.app`` exists, Flet would otherwise ignore it and spawn
    a second Dock identity (Flet/fish).
    """
    view_path = os.environ.get("FLET_VIEW_PATH")
    if not view_path:
        return
    try:
        import flet_desktop as fd
    except ImportError:
        return
    if getattr(fd, "_ki_flet_view_patched", False):
        return

    original = fd.__locate_and_unpack_flet_view
    build_macos = os.path.normpath(os.path.join(os.getcwd(), "build", "macos"))

    def locate(page_url, assets_dir, hidden):  # type: ignore[no-untyped-def]
        real_exists = os.path.exists

        def exists(path):  # type: ignore[no-untyped-def]
            try:
                if real_exists(path) and os.path.normpath(str(path)) == build_macos:
                    return False
            except (OSError, ValueError, TypeError):
                pass
            return real_exists(path)

        os.path.exists = exists  # type: ignore[assignment]
        try:
            return original(page_url, assets_dir, hidden)
        finally:
            os.path.exists = real_exists  # type: ignore[assignment]

    fd.__locate_and_unpack_flet_view = locate  # type: ignore[method-assign]
    fd._ki_flet_view_patched = True  # type: ignore[attr-defined]


def main(page) -> None:  # type: ignore[no-untyped-def]
    from invoice_tool.internal_launcher.app import build_internal_launcher

    build_internal_launcher(page)


if __name__ == "__main__":
    import flet as ft

    _prefer_env_flet_view_path()
    run = getattr(ft, "run", None) or ft.app
    run(main)
