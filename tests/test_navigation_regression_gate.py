"""Focused navigation regression tests for Flet 0.85 (unittest runner)."""

from __future__ import annotations

import asyncio
import json
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.gui_workspace_helpers import collect_labels, find_controls_by_label, iter_controls, control_label


def _flet_version_tuple() -> tuple[int, int, int]:
    try:
        from flet.version import flet_version
    except Exception:
        return (0, 0, 0)
    parts = [int(part) for part in str(flet_version).split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _install_gui_stubs() -> None:
    config_mod = types.ModuleType("invoice_tool.config")

    class ConfigError(Exception):
        pass

    config_mod.ConfigError = ConfigError
    config_mod.load_app_config = lambda _config_path=None: SimpleNamespace(
        source_dir=Path("/tmp/in"),
        output_dir=Path("/tmp/out"),
        preset_name="test",
        regeln_datei=Path("/tmp/office_rules.json"),
        aktives_preset="test",
        eingangsordner=Path("/tmp/in"),
        ausgangsordner=Path("/tmp/out"),
    )
    config_mod.load_office_rules = lambda _rules_path, active_preset_override=None: SimpleNamespace(
        active_preset=active_preset_override or "test"
    )
    sys.modules["invoice_tool.config"] = config_mod

    run_mod = types.ModuleType("invoice_tool.run")

    class RunError(Exception):
        pass

    run_mod.RunError = RunError
    run_mod.run_once = lambda *_args, **_kwargs: Path("/tmp/run")
    sys.modules["invoice_tool.run"] = run_mod


def _build_test_page() -> MagicMock:
    _install_gui_stubs()
    page = MagicMock()
    page.controls = []
    page.services = SimpleNamespace(register_service=lambda _service: None)

    def _run_task(handler: object, *args: object, **kwargs: object) -> None:
        asyncio.run(handler(*args, **kwargs))  # type: ignore[misc,operator]

    page.add.side_effect = lambda *controls: page.controls.extend(controls)
    page.update = MagicMock()
    page.run_task = _run_task
    page.run_thread = MagicMock()
    return page


def _find_nav_handler(root: object, label: str):
    from invoice_tool.ui_v2.control_tree import find_nav_handler
    return find_nav_handler(root, label)


def _sidebar_labels(root: object) -> set[str]:
    return collect_labels(root) & {
        "Arbeitsbereich",
        "Konfigurationen",
        "Zur Prüfung",
        "Profile",
        "Einstellungen",
        "KI-Rechnungen",
    }


class NavigationRegressionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if _flet_version_tuple() < (0, 85, 0):
            raise unittest.SkipTest("Erfordert Flet >= 0.85")

    def setUp(self) -> None:
        self._tmpdir = Path(__file__).resolve().parents[1] / "testing" / "tmp_nav_gate"
        self._tmpdir.mkdir(parents=True, exist_ok=True)
        self._support = self._tmpdir / "support"
        self._support.mkdir(parents=True, exist_ok=True)
        (self._support / "profiles").mkdir(parents=True, exist_ok=True)
        (self._support / "profile_state.json").write_text(
            json.dumps({"active_profile_id": "local"}),
            encoding="utf-8",
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
                        "destination": {"type": "local_folder", "path": str(self._tmpdir / "ziel")},
                        "overrides_enabled": False,
                        "overrides": {},
                    }
                ],
                "fallback": {
                    "display_name": "Nicht zugeordnete Dokumente",
                    "destination": {"type": "local_folder", "path": str(self._tmpdir / "review")},
                },
            },
        }
        (self._support / "profile_config.local.json").write_text(
            json.dumps(legacy, indent=2),
            encoding="utf-8",
        )

        import invoice_tool.app_paths as app_paths
        import invoice_tool.profile_store as profile_store

        self._orig_support = app_paths.user_support_dir
        self._orig_storage = app_paths.profile_storage_dir
        self._orig_store_storage = profile_store.app_paths.profile_storage_dir
        app_paths.user_support_dir = lambda: self._support
        app_paths.profile_storage_dir = lambda: self._support
        profile_store.app_paths.profile_storage_dir = lambda: self._support

        self.page = _build_test_page()
        from invoice_tool.profile_store import migrate_all_profiles
        from invoice_tool.gui import build_ui

        migrate_all_profiles(force=True)
        build_ui(self.page)

    def tearDown(self) -> None:
        import invoice_tool.app_paths as app_paths
        import invoice_tool.profile_store as profile_store

        app_paths.user_support_dir = self._orig_support
        app_paths.profile_storage_dir = self._orig_storage
        profile_store.app_paths.profile_storage_dir = self._orig_store_storage

    def _root(self):
        return self.page.controls[0]

    def test_all_five_navigation_labels_exist(self) -> None:
        labels = _sidebar_labels(self._root())
        for label in ("Arbeitsbereich", "Konfigurationen", "Zur Prüfung", "Profile", "Einstellungen"):
            self.assertIn(label, labels, f"Navigation fehlt: {label}")

    def test_all_five_callbacks_bound(self) -> None:
        for label in ("Arbeitsbereich", "Konfigurationen", "Zur Prüfung", "Profile", "Einstellungen"):
            self.assertIsNotNone(_find_nav_handler(self._root(), label), f"Callback fehlt: {label}")

    def test_all_destinations_use_same_content_host(self) -> None:
        root_before = self._root()
        row = getattr(root_before, "content", None)
        self.assertIsNotNone(row)
        host = getattr(row, "controls", [None, None])[1]
        for label in ("Konfigurationen", "Zur Prüfung", "Profile", "Einstellungen", "Arbeitsbereich"):
            handler = _find_nav_handler(root_before, label)
            assert handler is not None
            handler(MagicMock())
            root_after = self._root()
            self.assertIs(root_before, root_after, "Root-Shell wurde ersetzt")
            row_after = getattr(root_after, "content", None)
            children = getattr(row_after, "controls", [])
            self.assertGreaterEqual(len(children), 2)
            self.assertIs(children[1], host, f"Content-Host gewechselt bei {label}")

    def test_sidebar_remains_after_each_navigation(self) -> None:
        for label in ("Konfigurationen", "Zur Prüfung", "Profile", "Einstellungen", "Arbeitsbereich"):
            handler = _find_nav_handler(self._root(), label)
            assert handler is not None
            handler(MagicMock())
            sidebar = _sidebar_labels(self._root())
            self.assertIn("KI-Rechnungen", sidebar)
            self.assertIn(label, sidebar)

    def test_settings_page_renders_minimal_copy(self) -> None:
        handler = _find_nav_handler(self._root(), "Einstellungen")
        assert handler is not None
        handler(MagicMock())
        labels = collect_labels(self._root())
        self.assertIn("Einstellungen", labels)
        joined = " ".join(sorted(labels))
        self.assertIn("Hier werden allgemeine Programmeinstellungen verwaltet.", joined)
        self.assertIn("Derzeit sind keine weiteren Einstellungen verfügbar.", joined)

    def test_repeated_navigation_cycles_keep_callbacks(self) -> None:
        cycles = [
            ["Arbeitsbereich", "Konfigurationen", "Zur Prüfung", "Profile", "Einstellungen"],
            ["Einstellungen", "Profile", "Zur Prüfung", "Konfigurationen", "Arbeitsbereich"],
            ["Profile", "Arbeitsbereich", "Konfigurationen", "Einstellungen", "Zur Prüfung"],
        ]
        for cycle in cycles:
            for label in cycle:
                handler = _find_nav_handler(self._root(), label)
                self.assertIsNotNone(handler, f"Callback verloren: {label}")
                handler(MagicMock())
                headings = collect_labels(self._root())
                if label != "Arbeitsbereich":
                    self.assertIn(label, headings, f"Zielüberschrift fehlt: {label}")

    def test_no_root_page_replacement_on_navigation(self) -> None:
        initial_len = len(self.page.controls)
        self.assertEqual(initial_len, 1)
        for label in ("Konfigurationen", "Profile", "Einstellungen"):
            handler = _find_nav_handler(self._root(), label)
            assert handler is not None
            handler(MagicMock())
            self.assertEqual(len(self.page.controls), 1)

    def test_configuration_destination_action_opens_editor(self) -> None:
        handler = _find_nav_handler(self._root(), "Arbeitsbereich")
        assert handler is not None
        handler(MagicMock())
        open_buttons = find_controls_by_label(self._root(), "Konfiguration öffnen")
        self.assertTrue(open_buttons, "Konfiguration-öffnen-Aktion fehlt im Arbeitsbereich")
        open_buttons[0].on_click(MagicMock())
        labels = collect_labels(self._root())
        self.assertIn("Konfigurationen", labels)
        self.assertIn("Konfiguration bearbeiten", labels)
        self.assertIn("Ordner auswählen", labels)


if __name__ == "__main__":
    unittest.main()
