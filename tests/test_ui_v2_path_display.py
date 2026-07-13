"""Tests for UI-v2 destination path resolution."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from invoice_tool.ui_v2.adapters.path_display import (
    destination_is_missing,
    destination_summary_for_display,
    resolve_destination_path,
)


class DestinationPathResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.root = Path(self._tmpdir.name)
        self.output_root = self.root / "outbox"
        self.output_root.mkdir()
        self.config_path = self.root / "invoice_config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "eingangsordner": str(self.root / "inbox"),
                    "ausgangsordner": str(self.output_root),
                    "api_key_pfad": str(self.root / ".env"),
                    "archiv_aktiv": True,
                    "regeln_datei": str(self.root / "office_rules.json"),
                }
            ),
            encoding="utf-8",
        )
        (self.root / "inbox").mkdir()
        (self.root / "office_rules.json").write_text("{}", encoding="utf-8")

        from invoice_tool import app_paths

        self._orig_resolver = app_paths.resolve_invoice_config_path
        app_paths.resolve_invoice_config_path = lambda: self.config_path

    def tearDown(self) -> None:
        from invoice_tool import app_paths

        app_paths.resolve_invoice_config_path = self._orig_resolver

    def test_legacy_relative_resolves_under_output_root(self) -> None:
        destination = {"type": "legacy_relative", "path": "ep"}
        resolved = resolve_destination_path(destination)
        self.assertEqual(resolved, (self.output_root / "ep").resolve())

    def test_legacy_relative_not_missing_when_output_root_exists(self) -> None:
        destination = {"type": "legacy_relative", "path": "ep"}
        self.assertFalse(destination_is_missing(destination))

    def test_legacy_relative_display_uses_output_root(self) -> None:
        destination = {"type": "legacy_relative", "path": "ep"}
        summary = destination_summary_for_display(destination)
        self.assertIn("outbox/ep", summary.replace("\\", "/"))

    def test_absolute_local_folder_requires_existing_directory(self) -> None:
        missing = self.root / "missing-dir"
        destination = {"type": "local_folder", "path": str(missing)}
        self.assertTrue(destination_is_missing(destination))
        missing.mkdir()
        self.assertFalse(destination_is_missing(destination))


if __name__ == "__main__":
    unittest.main()
