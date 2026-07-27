"""UI-v2 bootstrap — owns the single Flet root mount."""

from __future__ import annotations

import flet as ft

from invoice_tool.app_paths import ensure_profile_storage_layout, resolve_active_profile_id
from invoice_tool.ui_v2.adapters.read_only_backend import load_read_only_snapshot
from invoice_tool.ui_v2.edit_components import unsaved_changes_dialog
from invoice_tool.ui_v2.navigation import (
    NAV_CONFIGURATIONS,
    NAV_PROFILES,
    NAV_REVIEW,
    NAV_SETTINGS,
    NAV_WORKSPACE,
)
from invoice_tool.ui_v2.pages.configurations import build_configurations_page
from invoice_tool.ui_v2.pages.profiles import build_profiles_page
from invoice_tool.ui_v2.pages.review import build_review_page
from invoice_tool.ui_v2.pages.settings import build_settings_page
from invoice_tool.ui_v2.pages.workspace import build_workspace_page
from invoice_tool.ui_v2.dev_defaults import (
    apply_track_b_dev_folder_defaults_to_state,
    is_track_b_dev_defaults_enabled,
)
from invoice_tool.ui_v2.processing_contract import make_local_processing_adapter
from invoice_tool.ui_v2.control_tree import collect_labels
from invoice_tool.ui_v2.shell import ShellHandles, build_shell, replace_content, set_active_nav
from invoice_tool.ui_v2.state import UiV2State, is_track_b_show_dev_surfaces_enabled
from invoice_tool.ui_v2.theme import APP_MIN_WIDTH, COLOR_PAGE_BG

# Labels that must be present after a successful product-shell mount.
_REQUIRED_PRODUCT_NAV_LABELS = frozenset(
    {"Arbeitsbereich", "Profile", "Konfigurationen", "Prüfung", "NAME.IT PRO"}
)
_FORBIDDEN_NORMAL_NAV_LABELS = frozenset(
    {"Entwickler / Diagnose", "Oracle", "Test & Nachweis", "Dry Run", "Sandbox"}
)


def _assert_visible_product_shell(page: ft.Page, shell: ShellHandles) -> None:
    """Fail loud if mount produced an empty / non-product surface (blank window risk)."""

    if not getattr(page, "controls", None):
        raise RuntimeError("UI-v2 mount failed: page.controls is empty")
    if shell.root is None or shell.content_host is None:
        raise RuntimeError("UI-v2 mount failed: shell root/content host missing")
    if shell.content_host.content is None:
        raise RuntimeError("UI-v2 mount failed: content host has no page content")
    if not shell.nav_items:
        raise RuntimeError("UI-v2 mount failed: navigation items missing")
    for nav_id in (NAV_WORKSPACE, NAV_PROFILES, NAV_CONFIGURATIONS, NAV_REVIEW):
        if nav_id not in shell.nav_items:
            raise RuntimeError(f"UI-v2 mount failed: nav item missing: {nav_id}")

    labels = collect_labels(shell.root)
    missing = _REQUIRED_PRODUCT_NAV_LABELS - labels
    if missing:
        raise RuntimeError(
            "UI-v2 mount failed: required product labels missing: "
            + ", ".join(sorted(missing))
        )
    content_labels = collect_labels(shell.content_host.content)
    if not content_labels:
        raise RuntimeError(
            "UI-v2 mount failed: default Arbeitsbereich content is empty"
        )
    if "Arbeitsbereich" not in content_labels:
        raise RuntimeError(
            "UI-v2 mount failed: default page is not Arbeitsbereich"
        )

    if not is_track_b_show_dev_surfaces_enabled():
        # Normal mode: sidebar must not expose developer / diagnosis entries.
        sidebar_labels = collect_labels(shell.sidebar)
        leaked_sidebar = _FORBIDDEN_NORMAL_NAV_LABELS & sidebar_labels
        if leaked_sidebar:
            raise RuntimeError(
                "UI-v2 mount failed: developer surfaces leaked into normal nav: "
                + ", ".join(sorted(leaked_sidebar))
            )


def _render_page(state: UiV2State, nav_id: str) -> ft.Control:
    builders = {
        NAV_WORKSPACE: build_workspace_page,
        NAV_CONFIGURATIONS: build_configurations_page,
        NAV_REVIEW: build_review_page,
        NAV_PROFILES: build_profiles_page,
        NAV_SETTINGS: build_settings_page,
    }
    builder = builders[nav_id]
    return builder(state)


def build_ui_v2(page: ft.Page) -> None:
    page.title = "NAME.IT PRO"
    page.window.width = APP_MIN_WIDTH
    page.window.min_width = APP_MIN_WIDTH
    page.window.height = 800
    page.window.min_height = 720
    page.padding = 0
    page.bgcolor = COLOR_PAGE_BG
    page.theme_mode = ft.ThemeMode.LIGHT

    ensure_profile_storage_layout()

    state = UiV2State(
        active_nav_id=NAV_WORKSPACE,
        selected_profile_id=resolve_active_profile_id(),
        # Track-B live UI: bounded LocalProcessingAdapter (sandbox-gated, no core import).
        processing_service=make_local_processing_adapter(),
    )
    state.page = page
    # Development-only Track-B smoke prefills — no auto-run, no profile mutation.
    if is_track_b_dev_defaults_enabled():
        apply_track_b_dev_folder_defaults_to_state(state)

    dialog_ref: list[ft.AlertDialog | None] = [None]

    def close_dialog() -> None:
        dialog = dialog_ref[0]
        if dialog is not None:
            dialog.open = False
            page.update()
            dialog_ref[0] = None

    def open_dialog(dialog: ft.AlertDialog) -> None:
        close_dialog()
        dialog_ref[0] = dialog
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    state.open_dialog = open_dialog
    state.close_dialog = close_dialog

    handles: list[ShellHandles | None] = [None]

    def refresh_view(*, nav_id: str | None = None) -> None:
        shell = handles[0]
        if shell is None:
            return
        try:
            state.snapshot = load_read_only_snapshot()
            state.warnings = list(state.snapshot.warnings)
            state.selected_profile_id = resolve_active_profile_id()
        except Exception:
            state.snapshot = None
            state.warnings = ["Grunddaten konnten nicht vollständig geladen werden."]
        target = nav_id or state.active_nav_id
        try:
            replace_content(shell, _render_page(state, target))
        except Exception:
            state.discard_config_edit()
            state.discard_profile_edit()
            replace_content(shell, _render_page(state, target))
            state.warnings = [*state.warnings, "Formular konnte nicht dargestellt werden — Ansicht zurückgesetzt."]
        page.update()

    state.refresh = lambda: refresh_view()

    def on_page_resize(_event: ft.ControlEvent | None = None) -> None:
        # Re-render so panels that size themselves off page.height
        # (see resolve_list_detail_height) pick up the new window size.
        refresh_view()

    page.on_resize = on_page_resize

    def do_navigate(nav_id: str) -> None:
        shell = handles[0]
        if shell is None:
            return
        state.active_nav_id = nav_id
        replace_content(shell, _render_page(state, nav_id))
        set_active_nav(shell, nav_id)
        page.update()

    def navigate(nav_id: str) -> None:
        if state.has_unsaved_changes():
            def on_discard() -> None:
                state.discard_all_edits()
                close_dialog()
                do_navigate(nav_id)

            def on_continue() -> None:
                close_dialog()

            open_dialog(unsaved_changes_dialog(on_discard=on_discard, on_continue=on_continue))
            return
        do_navigate(nav_id)

    state.navigate = navigate

    try:
        state.snapshot = load_read_only_snapshot()
        state.warnings = list(state.snapshot.warnings)
    except Exception:
        state.snapshot = None
        state.warnings = ["Grunddaten konnten nicht vollständig geladen werden."]

    initial_content = _render_page(state, state.active_nav_id)
    shell = build_shell(
        active_nav=state.active_nav_id,
        content=initial_content,
        on_navigate=navigate,
    )
    handles[0] = shell
    page.add(shell.root)
    page.update()
    _assert_visible_product_shell(page, shell)
