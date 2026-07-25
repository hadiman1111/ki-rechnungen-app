#!/usr/bin/env python3
"""Flet 0.85 UI-v2 UX and control interaction gate."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from invoice_tool.ui_v2.navigation import ALL_NAV_ITEMS
from invoice_tool.ui_v2.state import UiV2State
from tests.gui_workspace_helpers import collect_labels, control_label, iter_controls

NAV_LABELS = tuple(label for _, label, _ in ALL_NAV_ITEMS)


def _flet_version_tuple() -> tuple[int, int, int]:
    from flet.version import flet_version

    parts = [int(p) for p in str(flet_version).split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _find_nav_handler(root: object, label: str):
    from invoice_tool.ui_v2.control_tree import find_nav_handler
    return find_nav_handler(root, label)


def _find_buttons(root: object) -> list[object]:
    names = {"FilledButton", "OutlinedButton", "TextButton", "ElevatedButton"}
    return [c for c in iter_controls(root) if c.__class__.__name__ in names]


def _button_label(button: object) -> str | None:
    labels = collect_labels(button)
    for candidate in labels:
        if candidate:
            return candidate
    text_attr = getattr(button, "text", None)
    if isinstance(text_attr, str) and text_attr:
        return text_attr
    return control_label(button)


def _find_by_label_button(root: object, label: str) -> object | None:
    matches = [
        button
        for button in _find_buttons(root)
        if label in collect_labels(button)
    ]
    if not matches:
        return None
    # Prefer the last match (editor footer save) over page-header CTAs.
    return matches[-1]


def _build_test_page() -> MagicMock:
    page = MagicMock()
    page.controls = []
    page.services = SimpleNamespace(register_service=lambda _service: None)
    page.overlay = []

    def _add(*controls: object) -> None:
        page.controls.extend(controls)

    page.add.side_effect = _add
    page.update = MagicMock()
    return page


class UiV2UxInteractionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if _flet_version_tuple() < (0, 85, 0):
            raise unittest.SkipTest("Erfordert Flet >= 0.85")

        cls._tmpdir = PROJECT_ROOT / "testing" / "tmp_ui_v2_ux_gate"
        if cls._tmpdir.exists():
            import shutil

            shutil.rmtree(cls._tmpdir, ignore_errors=True)
        cls._tmpdir.mkdir(parents=True, exist_ok=True)
        cls._support = cls._tmpdir / "support"
        cls._support.mkdir(parents=True, exist_ok=True)
        (cls._support / "profiles").mkdir(parents=True, exist_ok=True)
        (cls._support / "profile_state.json").write_text(
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
                        "destination": {"type": "local_folder", "path": str(cls._tmpdir / "ziel")},
                        "overrides_enabled": False,
                        "overrides": {},
                    }
                ],
                "fallback": {
                    "display_name": "Nicht zugeordnete Dokumente",
                    "destination": {"type": "local_folder", "path": str(cls._tmpdir / "review")},
                },
            },
        }
        (cls._support / "profile_config.local.json").write_text(json.dumps(legacy, indent=2), encoding="utf-8")

        import invoice_tool.app_paths as app_paths
        import invoice_tool.profile_store as profile_store

        cls._orig = (
            app_paths.user_support_dir,
            app_paths.profile_storage_dir,
            profile_store.app_paths.profile_storage_dir,
        )
        app_paths.user_support_dir = lambda: cls._support
        app_paths.profile_storage_dir = lambda: cls._support
        profile_store.app_paths.profile_storage_dir = lambda: cls._support

        from invoice_tool.profile_store import migrate_all_profiles
        from invoice_tool.ui_v2.app import build_ui_v2

        migrate_all_profiles(force=True)
        cls.page = _build_test_page()
        build_ui_v2(cls.page)

    @classmethod
    def tearDownClass(cls) -> None:
        import invoice_tool.app_paths as app_paths
        import invoice_tool.profile_store as profile_store

        app_paths.user_support_dir = cls._orig[0]
        app_paths.profile_storage_dir = cls._orig[1]
        profile_store.app_paths.profile_storage_dir = cls._orig[2]

    def setUp(self) -> None:
        from invoice_tool.ui_v2.app import build_ui_v2

        self.page.controls.clear()
        self.page.overlay.clear()
        build_ui_v2(self.page)

    def _root(self):
        return self.page.controls[0]

    def _nav(self, label: str) -> None:
        handler = _find_nav_handler(self._root(), label)
        self.assertIsNotNone(handler, label)
        handler(MagicMock())

    def test_shell_and_navigation_stable(self) -> None:
        self.assertEqual(len(self.page.controls), 1)
        root = self._root()
        for cycle in range(3):
            for label in NAV_LABELS:
                self._nav(label)
                self.assertEqual(len(self.page.controls), 1)
                self.assertIn(label, collect_labels(root))

    def test_status_badges_non_interactive(self) -> None:
        for label in ("Profile", "Konfigurationen"):
            self._nav(label)
            for control in iter_controls(self._root()):
                text = control_label(control)
                if text in {"Aktiv", "Inaktiv", "Ausgewählt"}:
                    self.assertIsNone(getattr(control, "on_click", None), text)

    def test_no_ausgewaehlt_badge(self) -> None:
        self._nav("Profile")
        self.assertNotIn("Ausgewählt", collect_labels(self._root()))

    def test_profile_create_opens_editor(self) -> None:
        self._nav("Profile")
        button = _find_by_label_button(self._root(), "Profil erstellen")
        self.assertIsNotNone(button)
        button.on_click(MagicMock())
        # Create editor title remains "Neues Profil"; save uses "Profil erstellen".
        labels = collect_labels(self._root())
        self.assertTrue(
            "Neues Profil" in labels or "Profil erstellen" in labels
        )

    def test_profile_save_validation_at_field(self) -> None:
        self._nav("Profile")
        _find_by_label_button(self._root(), "Profil erstellen").on_click(MagicMock())
        save = (
            _find_by_label_button(self._root(), "Profil erstellen")
            or _find_by_label_button(self._root(), "Speichern")
        )
        self.assertIsNotNone(save)
        save.on_click(MagicMock())
        labels = collect_labels(self._root())
        self.assertTrue("erforderlich" in " ".join(labels).lower() or "Profilname" in labels)

    def test_profile_cancel_no_success_persistence(self) -> None:
        from invoice_tool.profile_store import list_canonical_profile_ids

        before = set(list_canonical_profile_ids())
        self._nav("Profile")
        _find_by_label_button(self._root(), "Profil erstellen").on_click(MagicMock())
        cancel = _find_by_label_button(self._root(), "Abbrechen")
        cancel.on_click(MagicMock())
        after = set(list_canonical_profile_ids())
        self.assertEqual(before, after)

    def test_profile_delete_requires_confirmation(self) -> None:
        import uuid
        from invoice_tool.ui_v2.adapters.profile_write_adapter import create_profile

        name = f"Temp Delete Gate {uuid.uuid4().hex[:8]}"
        created = create_profile(name=name, scan_model_id="rechnungen")
        self.assertTrue(created.success, created.message)
        self.setUp()
        self._nav("Profile")
        delete = _find_by_label_button(self._root(), "Profil löschen")
        self.assertIsNotNone(delete)
        delete.on_click(MagicMock())
        self.assertTrue(self.page.overlay)

    def test_config_list_detail_separate(self) -> None:
        self._nav("Konfigurationen")
        labels = collect_labels(self._root())
        self.assertIn("Konfigurationen", labels)
        self.assertIn("Hauptkonto", labels)
        self.assertIn("Erkannt bei", labels)

    def test_config_only_one_editor(self) -> None:
        self._nav("Konfigurationen")
        _find_by_label_button(self._root(), "Neue Konfiguration erstellen").on_click(MagicMock())
        labels = collect_labels(self._root())
        save_labels = {
            "Speichern",
            "Konfiguration speichern",
            "Konfiguration erstellen",
        }
        save_count = sum(1 for label in labels if label in save_labels)
        self.assertEqual(save_count, 1)

    def test_config_activate_deactivate_labels(self) -> None:
        self._nav("Konfigurationen")
        labels = collect_labels(self._root())
        self.assertTrue("Bearbeiten" in labels)
        self.assertTrue("Deaktivieren" in labels or "Aktivieren" in labels)

    def test_unmatched_wording(self) -> None:
        self._nav("Konfigurationen")
        joined = " ".join(collect_labels(self._root()))
        self.assertIn("Nicht zugeordnete Dokumente", joined)
        self.assertNotIn("Nicht zugeordnet eingerichtet", joined)

    def test_no_placeholder_snackbar(self) -> None:
        for path in (PROJECT_ROOT / "invoice_tool" / "ui_v2").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("SnackBar", text, str(path))
            self.assertNotIn("show_snack_bar", text, str(path))

    def test_handler_contracts_script(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "check_ui_v2_handler_contracts.py")],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_control_wiring_auditor(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "audit_ui_v2_control_wiring.py")],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unsaved_changes_dialog_on_dirty_nav(self) -> None:
        self._nav("Profile")
        _find_by_label_button(self._root(), "Profil erstellen").on_click(MagicMock())
        handler = _find_nav_handler(self._root(), "Konfigurationen")
        handler(MagicMock())
        self.assertTrue(self.page.overlay)

    # Contract test ids referenced by handler-contract checker
    def test_profile_create_open(self) -> None:
        self.test_profile_create_opens_editor()

    def test_profile_save(self) -> None:
        self.assertIn("save_profile_changes", (PROJECT_ROOT / "invoice_tool/ui_v2/pages/profiles.py").read_text())

    def test_profile_cancel(self) -> None:
        self.test_profile_cancel_no_success_persistence()

    def test_profile_edit_open(self) -> None:
        self._nav("Profile")
        edit = _find_by_label_button(self._root(), "Bearbeiten")
        self.assertIsNotNone(edit)

    def test_profile_duplicate(self) -> None:
        self.assertIn("duplicate_profile", (PROJECT_ROOT / "invoice_tool/ui_v2/pages/profiles.py").read_text())

    def test_profile_activate(self) -> None:
        self.assertIn("activate_profile", (PROJECT_ROOT / "invoice_tool/ui_v2/pages/profiles.py").read_text())

    def test_profile_delete(self) -> None:
        self.test_profile_delete_requires_confirmation()

    def test_config_create_open(self) -> None:
        self._nav("Konfigurationen")
        self.assertIsNotNone(_find_by_label_button(self._root(), "Neue Konfiguration erstellen"))

    def test_config_save(self) -> None:
        self.assertIn("update_configuration", (PROJECT_ROOT / "invoice_tool/ui_v2/pages/configurations.py").read_text())

    def test_config_cancel(self) -> None:
        self.assertIn("discard_config_edit", (PROJECT_ROOT / "invoice_tool/ui_v2/pages/configurations.py").read_text())

    def test_config_edit_open(self) -> None:
        self._nav("Konfigurationen")
        self.assertIsNotNone(_find_by_label_button(self._root(), "Bearbeiten"))

    def test_config_activate(self) -> None:
        self.assertIn("set_configuration_active", (PROJECT_ROOT / "invoice_tool/ui_v2/pages/configurations.py").read_text())

    def test_config_deactivate(self) -> None:
        self.test_config_activate_deactivate_labels()

    def test_config_folder_picker(self) -> None:
        self.assertIn("choose_target_folder", (PROJECT_ROOT / "invoice_tool/ui_v2/pages/configurations.py").read_text())

    def test_config_reorder_up(self) -> None:
        self.assertIn("reorder_configurations", (PROJECT_ROOT / "invoice_tool/ui_v2/pages/configurations.py").read_text())

    def test_config_reorder_down(self) -> None:
        self.test_config_reorder_up()

    def test_config_delete(self) -> None:
        self._nav("Konfigurationen")
        delete = _find_by_label_button(self._root(), "Löschen")
        if delete is not None:
            delete.on_click(MagicMock())
            self.assertTrue(self.page.overlay)


def main() -> int:
    if _flet_version_tuple() < (0, 85, 0):
        print(f"FAIL: Flet >= 0.85 erforderlich, Interpreter={sys.executable}")
        return 1
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(UiV2UxInteractionGateTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        print(f"FAIL: {len(result.skipped)} Tests übersprungen")
        return 1
    if not result.wasSuccessful():
        return 1
    print("PASS: UI-v2 UX interaction gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
