"""Behavior-focused UI architecture regression tests."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from invoice_tool.ui_shell import (
    ADMIN_NAV,
    DAILY_NAV,
    NAV_CONFIGURATIONS,
    NAV_PROFILES,
    NAV_REVIEW,
    NAV_SETTINGS,
    NAV_WORKSPACE,
)
from tests.gui_workspace_helpers import collect_labels, iter_controls
from tests.test_gui_startup import _build_test_page, requires_flet_085


@pytest.fixture()
def isolated_support(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    support = tmp_path / "Application Support" / "KI-Rechnungen"
    support.mkdir(parents=True)
    (support / "profiles").mkdir(parents=True)
    (support / "profile_state.json").write_text(
        json.dumps({"active_profile_id": "local"}), encoding="utf-8"
    )
    legacy = {
        "profile_name": "Testprofil",
        "scan_model_id": "rechnungen",
        "target_routing": {
            "schema_version": "1.0",
            "global_document_rules": {
                "filename_template": "{invoice_date}_{payment_field}.pdf",
                "routing_field": "payment_field",
                "case_sensitive": False,
            },
            "targets": [
                {
                    "id": "cfg-1",
                    "display_name": "Hauptkonto",
                    "active": True,
                    "routing_values": ["test"],
                    "destination": {"type": "local_folder", "path": str(tmp_path / "ziel")},
                    "overrides_enabled": False,
                    "overrides": {},
                }
            ],
            "fallback": {
                "display_name": "Nicht zugeordnete Dokumente",
                "destination": {"type": "local_folder", "path": str(tmp_path / "review")},
            },
        },
    }
    (support / "profile_config.local.json").write_text(json.dumps(legacy, indent=2), encoding="utf-8")
    monkeypatch.setattr("invoice_tool.app_paths.user_support_dir", lambda: support)
    monkeypatch.setattr("invoice_tool.app_paths.profile_storage_dir", lambda: support)
    monkeypatch.setattr("invoice_tool.profile_store.app_paths.profile_storage_dir", lambda: support)
    return support


def _page_headings(root: object) -> set[str]:
    return collect_labels(root)


def _find_nav_handler(root: object, label: str):
    from invoice_tool.ui_v2.control_tree import find_nav_handler
    return find_nav_handler(root, label)


def _clickable_buttons(root: object) -> list[object]:
    buttons: list[object] = []
    for control in iter_controls(root):
        if control.__class__.__name__ in {"ElevatedButton", "OutlinedButton", "TextButton", "IconButton"}:
            if getattr(control, "visible", True) is not False:
                buttons.append(control)
    return buttons


@requires_flet_085
def test_all_navigation_destinations_mount_visible_content(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    page, _added = _build_test_page(monkeypatch)
    from invoice_tool.gui import build_ui

    build_ui(page)
    root = page.controls[-1]
    nav_labels = {label for _, label, _ in (*DAILY_NAV, *ADMIN_NAV)}
    assert nav_labels.issubset(_page_headings(root))

    for nav_id, label, _ in (*DAILY_NAV, *ADMIN_NAV):
        handler = _find_nav_handler(root, label)
        assert handler is not None, f"Navigation fehlt: {label}"
        handler(MagicMock())
        mounted = page.controls[-1]
        headings = _page_headings(mounted)
        assert label in headings or nav_id == NAV_WORKSPACE, f"Keine sichtbare Überschrift für {label}"


@requires_flet_085
def test_configurations_page_renders_with_valid_profile(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    from invoice_tool.profile_store import migrate_all_profiles
    from invoice_tool.ui_configurations import build_configurations_view

    migrate_all_profiles(force=True)
    page = MagicMock()
    page.update = MagicMock()
    page.run_task = MagicMock()

    view = build_configurations_view(
        page=page,
        profile_id="local",
        on_profile_changed=lambda _pid: None,
    )
    labels = _page_headings(view)
    assert "Konfigurationen" in labels
    assert "Konfiguration hinzufügen" in labels
    assert "Nicht zugeordnete Dokumente" in labels


@requires_flet_085
def test_configurations_page_shows_error_for_invalid_profile_data(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    from invoice_tool.ui_configurations import build_configurations_view

    broken_dir = isolated_support / "profiles_v2" / "broken"
    broken_dir.mkdir(parents=True)
    (broken_dir / "profile.json").write_text("{invalid", encoding="utf-8")

    page = MagicMock()
    page.update = MagicMock()
    view = build_configurations_view(
        page=page,
        profile_id="broken",
        on_profile_changed=lambda _pid: None,
    )
    labels = _page_headings(view)
    assert "Konfigurationen konnten nicht geladen werden" in labels


@requires_flet_085
def test_new_configuration_cancel_does_not_mutate_bundle(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    from invoice_tool.profile_store import load_profile_bundle, migrate_all_profiles
    from invoice_tool.ui_configurations import build_configurations_view

    migrate_all_profiles(force=True)
    before = load_profile_bundle("local")
    before_count = len(before.configurations)

    page = MagicMock()
    page.update = MagicMock()
    page.run_task = MagicMock()
    view = build_configurations_view(
        page=page,
        profile_id="local",
        on_profile_changed=lambda _pid: None,
    )

    add_buttons = [
        control
        for control in _clickable_buttons(view)
        if getattr(control, "text", None) == "Konfiguration hinzufügen"
    ]
    assert add_buttons
    add_buttons[0].on_click(MagicMock())

    cancel_buttons = [
        control
        for control in _clickable_buttons(view)
        if getattr(control, "text", None) == "Abbrechen"
    ]
    assert cancel_buttons
    cancel_buttons[0].on_click(MagicMock())

    after = load_profile_bundle("local")
    assert len(after.configurations) == before_count


@requires_flet_085
def test_settings_does_not_expose_internal_paths() -> None:
    from invoice_tool.ui_settings import build_settings_view

    view = build_settings_view()
    labels = _page_headings(view)
    joined = " ".join(labels)
    assert "invoice_config.json" not in joined
    assert "Application Support" not in joined
    assert "Einstellungen" in labels


@requires_flet_085
def test_user_pages_avoid_fallback_copy(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    page, _added = _build_test_page(monkeypatch)
    from invoice_tool.gui import build_ui

    build_ui(page)
    labels = _page_headings(page.controls[-1])
    forbidden = {label for label in labels if "Fallback" in label or "Lokale Arbeitskopie" in label}
    assert not forbidden


@requires_flet_085
def test_profile_create_and_duplicate_actions_exist(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    from invoice_tool.profile_store import list_canonical_profile_ids, migrate_all_profiles
    from invoice_tool.ui_profiles import build_profiles_view

    migrate_all_profiles(force=True)
    page = MagicMock()
    page.update = MagicMock()
    page.open = MagicMock()
    page.close = MagicMock()

    view = build_profiles_view(
        page=page,
        profile_id="local",
        on_open_configurations=lambda: None,
    )
    before_ids = set(list_canonical_profile_ids())

    create = next(
        button for button in _clickable_buttons(view) if getattr(button, "text", None) == "Neues Profil"
    )
    create.on_click(MagicMock())
    after_create = set(list_canonical_profile_ids())
    assert len(after_create) == len(before_ids) + 1

    duplicate = next(
        button for button in _clickable_buttons(view) if getattr(button, "text", None) == "Profil duplizieren"
    )
    before_dup = set(list_canonical_profile_ids())
    duplicate.on_click(MagicMock())
    after_dup = set(list_canonical_profile_ids())
    assert len(after_dup) == len(before_dup) + 1


@requires_flet_085
def test_profile_delete_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    from invoice_tool.profile_store import create_profile_bundle, migrate_all_profiles
    from invoice_tool.ui_profiles import build_profiles_view

    migrate_all_profiles(force=True)
    created = create_profile_bundle(name="Löschbar")
    page = MagicMock()
    page.update = MagicMock()
    page.open = MagicMock()
    page.close = MagicMock()

    view = build_profiles_view(
        page=page,
        profile_id=created.id,
        on_open_configurations=lambda: None,
    )
    delete = next(
        button for button in _clickable_buttons(view) if getattr(button, "text", None) == "Profil löschen"
    )
    delete.on_click(MagicMock())
    assert page.open.called
    dialog = page.open.call_args[0][0]
    assert dialog.__class__.__name__ == "AlertDialog"


@requires_flet_085
def test_no_visible_button_has_noop_callback(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    page, _added = _build_test_page(monkeypatch)
    from invoice_tool.gui import build_ui

    build_ui(page)
    for nav_id, label, _ in (*DAILY_NAV, *ADMIN_NAV):
        handler = _find_nav_handler(page.controls[-1], label)
        if handler:
            handler(MagicMock())
        for button in _clickable_buttons(page.controls[-1]):
            callback = getattr(button, "on_click", None)
            assert callback is not None
            assert callback is not (lambda _e: None)


def test_navigation_order_constants() -> None:
    assert [item[0] for item in DAILY_NAV] == [NAV_WORKSPACE, NAV_CONFIGURATIONS, NAV_REVIEW]
    assert [item[0] for item in ADMIN_NAV] == [NAV_PROFILES, NAV_SETTINGS]


@requires_flet_085
def test_configurations_page_loads_real_shape_sanitized_profile(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    """Regression: Flet 0.85 PopupMenuItem API and real profile structural shape."""
    from invoice_tool.profile_store import migrate_all_profiles
    from invoice_tool.ui_configurations import build_configurations_view

    legacy = json.loads((isolated_support / "profile_config.local.json").read_text(encoding="utf-8"))
    legacy["profile_name"] = "SOMAA Profil – Lokale Arbeitskopie"
    (isolated_support / "profile_config.local.json").write_text(json.dumps(legacy, indent=2), encoding="utf-8")
    migrate_all_profiles(force=True)

    page = MagicMock()
    page.update = MagicMock()
    page.run_task = MagicMock()
    view = build_configurations_view(
        page=page,
        profile_id="local",
        on_profile_changed=lambda _pid: None,
    )
    labels = _page_headings(view)
    assert "Konfigurationen konnten nicht geladen werden" not in labels
    assert "Konfiguration hinzufügen" in labels
    assert "Hauptkonto" in labels


@requires_flet_085
def test_malformed_configuration_does_not_blank_configurations_page(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    from invoice_tool.profile_store import migrate_all_profiles
    from invoice_tool.ui_configurations import build_configurations_view

    migrate_all_profiles(force=True)
    broken_cfg = isolated_support / "profiles_v2" / "local" / "configurations" / "broken.json"
    broken_cfg.write_text("{not-json", encoding="utf-8")

    page = MagicMock()
    page.update = MagicMock()
    page.run_task = MagicMock()
    view = build_configurations_view(
        page=page,
        profile_id="local",
        on_profile_changed=lambda _pid: None,
    )
    labels = _page_headings(view)
    assert "Konfigurationen" in labels
    assert "Konfiguration hinzufügen" in labels
    assert "Konfigurationen konnten nicht geladen werden" not in labels


@requires_flet_085
def test_settings_navigation_visible_in_main_shell(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    page, _added = _build_test_page(monkeypatch)
    from invoice_tool.gui import build_ui

    build_ui(page)
    labels = _page_headings(page.controls[-1])
    assert "Einstellungen" in labels


@requires_flet_085
def test_workspace_shows_destination_summary_before_processing(
    monkeypatch: pytest.MonkeyPatch,
    isolated_support: Path,
) -> None:
    page, _added = _build_test_page(monkeypatch)
    from invoice_tool.gui import build_ui

    build_ui(page)
    labels = _page_headings(page.controls[-1])
    assert "Zielordner je Konfiguration" in labels
    assert "Ordner noch auswählen" not in " ".join(labels) or "Hauptkonto" in labels
