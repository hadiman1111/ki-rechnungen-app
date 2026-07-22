"""Flet 0.85 design-fidelity structural visual tests for UI-v2."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from invoice_tool.ui_v2.navigation import ALL_NAV_ITEMS
from invoice_tool.ui_v2.theme import CONTENT_MAX_WIDTH, NAV_WIDTH
from tests.gui_workspace_helpers import collect_labels, control_label, iter_controls

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_V2_ROOT = PROJECT_ROOT / "invoice_tool" / "ui_v2"
DESIGN_FIDELITY_SCRIPT = PROJECT_ROOT / "scripts" / "check_ui_v2_design_fidelity.py"
FLET085_PYTHON = PROJECT_ROOT / ".venv-flet085" / "bin" / "python"


def _gate_python() -> str:
    if FLET085_PYTHON.is_file():
        return str(FLET085_PYTHON)
    return sys.executable

NAV_LABELS = tuple(label for _, label, _ in ALL_NAV_ITEMS)

RESPONSIVE_SIZES = (
    (1280, 720),
    (1440, 900),
    (1728, 1117),
)


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
    page.overlay = []

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


def _navigate_to(page: MagicMock, label: str) -> object:
    root = page.controls[0]
    handler = _find_nav_handler(root, label)
    assert handler is not None
    handler(MagicMock())
    return page.controls[0]


@requires_flet_085
def test_design_fidelity_validator_passes() -> None:
    result = subprocess.run(
        [_gate_python(), str(DESIGN_FIDELITY_SCRIPT)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@requires_flet_085
def test_all_pages_use_page_header(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    for label in NAV_LABELS:
        root = _navigate_to(page, label)
        labels = collect_labels(root)
        assert label in labels


@requires_flet_085
def test_shell_uses_design_tokens(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2
    from invoice_tool.ui_v2.theme import COLOR_SIDEBAR_BG

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    sidebar = _find_by_key(page.controls[0], "ui-v2-sidebar")
    assert sidebar is not None
    assert getattr(sidebar, "width", None) == NAV_WIDTH
    assert getattr(sidebar, "bgcolor", None) == COLOR_SIDEBAR_BG


@requires_flet_085
def test_sidebar_width_consistent(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    sidebar = _find_by_key(page.controls[0], "ui-v2-sidebar")
    assert getattr(sidebar, "width", None) == 240


@requires_flet_085
def test_sidebar_has_no_static_profile_footer(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    assert _find_by_key(page.controls[0], "ui-v2-active-profile") is None
    assert "Aktives Profil" not in collect_labels(page.controls[0])


@requires_flet_085
def test_configurations_list_detail_structure(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    root = _navigate_to(page, "Konfigurationen")
    labels = collect_labels(root)
    assert "Konfigurationen" in labels
    assert "Neue Konfiguration" in labels


@requires_flet_085
def test_profiles_list_detail_structure(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    root = _navigate_to(page, "Profile")
    labels = collect_labels(root)
    assert "Profile" in labels
    assert "Neues Profil" in labels
    assert "Profile" in labels


@requires_flet_085
def test_workspace_summary_layout(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    root = _navigate_to(page, "Arbeitsbereich")
    labels = collect_labels(root)
    assert "WORKFLOW" in labels
    assert "Zielordner" in labels
    has_mapping_headers = "EINGANGSORDNER" in labels and "ERGEBNISORDNER" in labels
    has_honest_empty = any(
        marker in labels
        for marker in (
            "Kein Lauf gestartet",
            "Keine Ergebnisse vorhanden",
            "Kein Ordner ausgewählt",
            "Noch keine Zuordnungen",
            "Ordner auswählen",
        )
    )
    assert has_mapping_headers or has_honest_empty


@requires_flet_085
def test_nav_includes_review_and_settings(isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    build_ui_v2(page)
    labels = collect_labels(page.controls[0])
    assert "Zur Prüfung" in labels
    assert "Einstellungen" in labels
    assert "Scanprofile" not in labels


@requires_flet_085
def test_status_badges_non_interactive() -> None:
    from invoice_tool.ui_v2.components import status_badge

    badge = status_badge("Aktiv", tone="active")
    assert getattr(badge, "on_click", None) is None


@requires_flet_085
def test_warning_non_interactive() -> None:
    from invoice_tool.ui_v2.components import inline_warning

    warning = inline_warning("Test")
    assert getattr(warning, "on_click", None) is None


@requires_flet_085
def test_content_max_width_defined() -> None:
    assert CONTENT_MAX_WIDTH == 1200


@requires_flet_085
@pytest.mark.parametrize("width,height", RESPONSIVE_SIZES)
def test_responsive_window_sizes(width: int, height: int, isolated_support: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.ui_v2.app import build_ui_v2

    page, _ = _build_test_page(monkeypatch)
    page.window.width = width
    page.window.height = height
    build_ui_v2(page)
    for label in NAV_LABELS:
        root = _navigate_to(page, label)
        assert _find_by_key(root, "ui-v2-shell") is not None
        assert _find_by_key(root, "ui-v2-sidebar") is not None


@requires_flet_085
def test_flet_version_is_085() -> None:
    assert _flet_version_tuple() >= (0, 85, 0)


@requires_flet_085
def test_import_boundary_still_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "check_ui_v2_import_boundary.py")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@requires_flet_085
def test_coherence_still_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "check_ui_v2_data_coherence.py")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@requires_flet_085
def test_handler_contracts_still_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "check_ui_v2_handler_contracts.py")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
