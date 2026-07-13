"""Rendering recovery regression tests for UI-v2 layout and content visibility."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from invoice_tool.ui_v2.app import build_ui_v2
from invoice_tool.ui_v2.navigation import ALL_NAV_ITEMS
from invoice_tool.ui_v2.rendering_checks import audit_all_pages, has_full_page_overlay
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.adapters.read_only_backend import load_read_only_snapshot
from invoice_tool.ui_v2.control_tree import collect_labels, find_nav_handler, iter_controls

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NAV_LABELS = tuple(label for _, label, _ in ALL_NAV_ITEMS)
RESPONSIVE_SIZES = ((1280, 720), (1440, 900), (1728, 1117))


def _flet_version_tuple() -> tuple[int, int, int]:
    try:
        from flet.version import flet_version
    except Exception:
        return (0, 0, 0)
    parts = [int(p) for p in str(flet_version).split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _build_test_page() -> tuple[MagicMock, list[object]]:
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


def _find_nav_handler(root: object, label: str):
    return find_nav_handler(root, label)


def _navigate_to(page: MagicMock, label: str) -> object:
    root = page.controls[0]
    handler = _find_nav_handler(root, label)
    assert handler is not None
    handler(MagicMock())
    return page.controls[0]


def _content_host(root: object) -> object | None:
    for control in iter_controls(root):
        if getattr(control, "key", None) == "ui-v2-content-host":
            return control
    return None


def _setup_isolated_support(tmpdir: Path) -> Path:
    support = tmpdir / "Application Support" / "KI-Rechnungen"
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
                    "destination": {"type": "local_folder", "path": str(tmpdir / "ziel")},
                    "overrides_enabled": False,
                    "overrides": {},
                }
            ],
            "fallback": {
                "display_name": "Nicht zugeordnete Dokumente",
                "destination": {"type": "local_folder", "path": str(tmpdir / "review")},
            },
        },
    }
    (support / "profile_config.local.json").write_text(json.dumps(legacy, indent=2), encoding="utf-8")

    import invoice_tool.app_paths as app_paths
    import invoice_tool.profile_store as profile_store

    app_paths.user_support_dir = lambda: support  # type: ignore[method-assign]
    app_paths.profile_storage_dir = lambda: support  # type: ignore[method-assign]
    profile_store.app_paths.profile_storage_dir = lambda: support  # type: ignore[method-assign]

    from invoice_tool.profile_store import migrate_all_profiles

    migrate_all_profiles(force=True)
    return support


@unittest.skipIf(_flet_version_tuple() < (0, 85, 0), "Erfordert Flet >= 0.85")
class UiV2RenderingRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        import shutil

        self._tmpdir = PROJECT_ROOT / "testing" / f"tmp_ui_v2_rendering_recovery_{self.id().split('.')[-1]}"
        if self._tmpdir.exists():
            shutil.rmtree(self._tmpdir)
        _setup_isolated_support(self._tmpdir)

    def test_no_oversized_empty_opaque_surfaces(self) -> None:
        state = UiV2State(active_nav_id="workspace")
        state.snapshot = load_read_only_snapshot()
        report = audit_all_pages(state)
        self.assertFalse(report.blocking, [f"{f.page}: {f.message}" for f in report.blocking])

    def test_workspace_semantic_content(self) -> None:
        page, _ = _build_test_page()
        build_ui_v2(page)
        root = _navigate_to(page, "Arbeitsbereich")
        labels = collect_labels(root)
        for required in ("WORKFLOW", "EINGANGSORDNER", "ERGEBNISORDNER", "Zielordner", "SOMAA Profil"):
            self.assertIn(required, labels)

    def test_workspace_run_panel_layout(self) -> None:
        from invoice_tool.ui_v2.pages.workspace import build_workspace_page

        state = UiV2State(active_nav_id="workspace")
        state.snapshot = load_read_only_snapshot()
        page_ctrl = build_workspace_page(state)
        labels = collect_labels(page_ctrl)
        self.assertIn("EINGANGSORDNER", labels)
        self.assertIn("ERGEBNISORDNER", labels)
        self.assertIn("Neu starten", labels)

    def test_configurations_list_and_detail_content(self) -> None:
        page, _ = _build_test_page()
        build_ui_v2(page)
        root = _navigate_to(page, "Konfigurationen")
        labels = collect_labels(root)
        self.assertIn("Hauptkonto", labels)
        self.assertIn("Bearbeiten", labels)
        self.assertIn("Konfigurationen", labels)

    def test_profiles_list_and_detail_content(self) -> None:
        page, _ = _build_test_page()
        build_ui_v2(page)
        root = _navigate_to(page, "Profile")
        labels = collect_labels(root)
        self.assertIn("SOMAA Profil", labels)
        self.assertIn("Profile", labels)
        self.assertIn("Erkennungsmodell", labels)

    def test_shell_sidebar_nav_handlers_present(self) -> None:
        page, _ = _build_test_page()
        build_ui_v2(page)
        root = page.controls[0]
        stacks = [ctrl for ctrl in iter_controls(root) if ctrl.__class__.__name__ == "Stack"]
        self.assertTrue(stacks, "Shell muss Stack-Layout nutzen (Sidebar über Content)")
        for _, label, _ in ALL_NAV_ITEMS:
            self.assertIsNotNone(find_nav_handler(root, label), f"Nav-Handler fehlt: {label}")

    def test_page_scaffold_must_not_overflow_sidebar(self) -> None:
        from invoice_tool.ui_v2.control_tree import iter_controls
        from invoice_tool.ui_v2.pages.workspace import build_workspace_page
        from invoice_tool.ui_v2.theme import CONTENT_MAX_WIDTH

        state = UiV2State(active_nav_id="workspace")
        state.snapshot = load_read_only_snapshot()
        page_ctrl = build_workspace_page(state)
        offenders = [
            ctrl
            for ctrl in iter_controls(page_ctrl)
            if ctrl.__class__.__name__ == "Container" and getattr(ctrl, "width", None) == CONTENT_MAX_WIDTH
        ]
        self.assertFalse(
            offenders,
            "page_scaffold darf keine feste CONTENT_MAX_WIDTH setzen — blockiert Sidebar-Klicks",
        )

    def test_responsive_pages_expose_semantic_content(self) -> None:
        for width, height in RESPONSIVE_SIZES:
            with self.subTest(width=width, height=height):
                page, _ = _build_test_page()
                page.window = SimpleNamespace(width=width, height=height, min_width=1280, min_height=720)
                build_ui_v2(page)
                for label in NAV_LABELS:
                    root = _navigate_to(page, label)
                    self.assertGreaterEqual(len(collect_labels(root)), 3)


if __name__ == "__main__":
    unittest.main()
