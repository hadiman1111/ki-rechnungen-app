"""Focused Flet 0.85 UI-v2 foundation gate tests."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from invoice_tool.ui_v2.navigation import ALL_NAV_IDS, ALL_NAV_ITEMS
from invoice_tool.ui_v2.shell import ShellHandles
from tests.gui_workspace_helpers import collect_labels, control_label, iter_controls

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_V2_ROOT = PROJECT_ROOT / "invoice_tool" / "ui_v2"
APP_UI_V2 = PROJECT_ROOT / "app_ui_v2.py"

NAV_LABELS = tuple(label for _, label, _ in ALL_NAV_ITEMS)

CYCLES = [
    ["Arbeitsbereich", "Konfigurationen", "Profile"],
    ["Profile", "Konfigurationen", "Arbeitsbereich"],
    ["Konfigurationen", "Profile", "Arbeitsbereich"],
]


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
    reason="Erfordert Flet >= 0.85",
)


def _find_by_key(root: object, key: str) -> object | None:
    for control in iter_controls(root):
        if getattr(control, "key", None) == key:
            return control
    return None


def _find_nav_handler(root: object, label: str):
    from invoice_tool.ui_v2.control_tree import find_nav_handler
    return find_nav_handler(root, label)


def _build_test_page(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, list[object]]:
    monkeypatch.delenv("FLET_PLATFORM", raising=False)
    added: list[object] = []
    page = MagicMock()
    page.controls = []
    page.services = SimpleNamespace(register_service=lambda _service: None)

    def _add(*controls: object) -> None:
        added.extend(controls)
        page.controls.extend(controls)

    page.add.side_effect = _add
    page.update = MagicMock()
    return page, added


@pytest.fixture()
def isolated_support(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    support = tmp_path / "Application Support" / "KI-Rechnungen"
    support.mkdir(parents=True)
    (support / "profiles").mkdir(parents=True)
    (support / "profile_state.json").write_text(
        json.dumps({"active_profile_id": "local"}), encoding="utf-8"
    )
    legacy = {
        "profile_name": "SOMAA Profil – Lokale Arbeitskopie",
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

    import invoice_tool.app_paths as app_paths
    import invoice_tool.profile_store as profile_store

    monkeypatch.setattr(app_paths, "user_support_dir", lambda: support)
    monkeypatch.setattr(app_paths, "profile_storage_dir", lambda: support)
    monkeypatch.setattr(profile_store.app_paths, "profile_storage_dir", lambda: support)

    from invoice_tool.profile_store import migrate_all_profiles

    migrate_all_profiles(force=True)
    return support


@requires_flet_085
def test_app_ui_v2_no_legacy_import_at_module_level() -> None:
    tree = ast.parse(APP_UI_V2.read_text(encoding="utf-8"))
    imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module
        and (node.module == "invoice_tool.gui" or node.module.startswith("invoice_tool.ui_"))
        and not node.module.startswith("invoice_tool.ui_v2")
    ]
    assert imports == []


@requires_flet_085
def test_single_shell_root(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    assert len(page.controls) == 1


@requires_flet_085
def test_sidebar_and_content_host(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    root = page.controls[0]
    assert _find_by_key(root, "ui-v2-sidebar") is not None
    assert _find_by_key(root, "ui-v2-content-host") is not None
    assert "NAME.IT PRO" in collect_labels(root)


@requires_flet_085
def test_five_navigation_items(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    labels = collect_labels(page.controls[0])
    for label in NAV_LABELS:
        assert label in labels


@requires_flet_085
def test_navigation_ids_present() -> None:
    assert len(ALL_NAV_IDS) == 5
    assert ALL_NAV_IDS == (
        "arbeitsbereich",
        "konfigurationen",
        "zur_pruefung",
        "profile",
        "einstellungen",
    )


@requires_flet_085
def test_active_state_changes(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    root = page.controls[0]
    for label in NAV_LABELS[1:]:
        handler = _find_nav_handler(root, label)
        assert handler is not None
        handler(MagicMock())
        assert label in collect_labels(page.controls[0])


@requires_flet_085
def test_all_pages_render_in_content_host(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    root = page.controls[0]
    host = _find_by_key(root, "ui-v2-content-host")
    assert host is not None
    for label in NAV_LABELS:
        handler = _find_nav_handler(root, label)
        assert handler is not None
        handler(MagicMock())
        host_after = _find_by_key(page.controls[0], "ui-v2-content-host")
        assert host_after is host
        assert label in collect_labels(page.controls[0])


@requires_flet_085
def test_sidebar_persists_after_navigation(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    for label in NAV_LABELS:
        handler = _find_nav_handler(page.controls[0], label)
        assert handler is not None
        handler(MagicMock())
        assert _find_by_key(page.controls[0], "ui-v2-sidebar") is not None


@requires_flet_085
def test_profile_not_isolated_form(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    handler = _find_nav_handler(page.controls[0], "Profile")
    assert handler is not None
    handler(MagicMock())
    labels = collect_labels(page.controls[0])
    assert "Profile" in labels
    assert "Profil bearbeiten" not in labels
    assert len(page.controls) == 1


@requires_flet_085
def test_configurations_not_replacing_shell(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    handler = _find_nav_handler(page.controls[0], "Konfigurationen")
    assert handler is not None
    handler(MagicMock())
    assert _find_by_key(page.controls[0], "ui-v2-shell") is not None
    assert "Konfiguration hinzufügen" not in collect_labels(page.controls[0])


@requires_flet_085
def test_no_page_clean_in_ui_v2_pages() -> None:
    for path in (UI_V2_ROOT / "pages").glob("*.py"):
        assert "page.clean(" not in path.read_text(encoding="utf-8")


@requires_flet_085
def test_no_page_controls_mutation_in_pages() -> None:
    for path in (UI_V2_ROOT / "pages").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "page.controls" not in text
        assert "page.add(" not in text


@requires_flet_085
def test_import_boundary_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "check_ui_v2_import_boundary.py")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@requires_flet_085
def test_sanitized_profile_summary_renders(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    handler = _find_nav_handler(page.controls[0], "Profile")
    assert handler is not None
    handler(MagicMock())
    joined = " ".join(collect_labels(page.controls[0]))
    assert "SOMAA Profil" in joined
    assert "Lokale Arbeitskopie" not in joined


@requires_flet_085
def test_malformed_optional_data_warning_not_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    support = tmp_path / "support"
    support.mkdir(parents=True)
    (support / "profiles").mkdir(parents=True)
    (support / "profile_state.json").write_text(
        json.dumps({"active_profile_id": "local"}), encoding="utf-8"
    )
    (support / "profile_config.local.json").write_text("{broken", encoding="utf-8")

    import invoice_tool.app_paths as app_paths
    import invoice_tool.profile_store as profile_store

    monkeypatch.setattr(app_paths, "user_support_dir", lambda: support)
    monkeypatch.setattr(app_paths, "profile_storage_dir", lambda: support)
    monkeypatch.setattr(profile_store.app_paths, "profile_storage_dir", lambda: support)

    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    assert len(page.controls) == 1


@requires_flet_085
def test_three_navigation_cycles(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    root_before = page.controls[0]
    host = _find_by_key(root_before, "ui-v2-content-host")
    for cycle in CYCLES:
        for label in cycle:
            handler = _find_nav_handler(page.controls[0], label)
            assert handler is not None
            handler(MagicMock())
            assert page.controls[0] is root_before
            assert _find_by_key(page.controls[0], "ui-v2-content-host") is host


@requires_flet_085
def test_flet_version_is_085() -> None:
    assert _flet_version_tuple() >= (0, 85, 0)
