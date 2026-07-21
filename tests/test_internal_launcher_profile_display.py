from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from invoice_tool.internal_launcher.profile_display import (
    ProfileDisplayInfo,
    load_active_profile_display,
)


def test_valid_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile_path = tmp_path / "profile_config.local.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_name": "SOMAA Profil – Lokale Arbeitskopie",
                "scan_model_id": "rechnungen",
                "configurations": [],
                "unmatched": {
                    "filename_pattern": {"components": []},
                    "destination": {"type": "local_folder", "path": "unklar"},
                },
            }
        ),
        encoding="utf-8",
    )

    with patch(
        "invoice_tool.internal_launcher.profile_display.compile_profile_to_rules",
        return_value={"preset": "office_default"},
    ), patch(
        "invoice_tool.internal_launcher.profile_display.load_profile_bundle",
    ) as load_bundle:
        bundle = type(
            "Bundle",
            (),
            {"name": "SOMAA Profil – Lokale Arbeitskopie", "scan_model_id": "rechnungen"},
        )()
        load_bundle.return_value = bundle
        info = load_active_profile_display(profile_path)
    assert info.ok
    assert "SOMAA" in info.profile_name
    assert info.scan_model_label == "Rechnungsdaten"


def test_missing_profile(tmp_path: Path) -> None:
    info = load_active_profile_display(tmp_path / "missing.json")
    assert not info.ok
    assert info.error_message is not None


def test_invalid_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    info = load_active_profile_display(bad)
    assert not info.ok
    assert "JSON" in (info.error_message or "")


def test_missing_active_scan_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({"profile_name": "Test"}), encoding="utf-8")
    with patch(
        "invoice_tool.internal_launcher.profile_display.compile_profile_to_rules",
        return_value={},
    ), patch(
        "invoice_tool.internal_launcher.profile_display.load_profile_bundle",
    ) as load_bundle:
        bundle = type("Bundle", (), {"name": "Test", "scan_model_id": ""})()
        load_bundle.return_value = bundle
        info = load_active_profile_display(profile_path)
    assert not info.ok


def test_read_only_behavior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile_path = tmp_path / "profile.json"
    original = {
        "profile_name": "Read Only",
        "scan_model_id": "rechnungen",
        "configurations": [],
        "unmatched": {
            "filename_pattern": {"components": []},
            "destination": {"type": "local_folder", "path": "unklar"},
        },
    }
    profile_path.write_text(json.dumps(original), encoding="utf-8")
    before = profile_path.read_text(encoding="utf-8")
    with patch(
        "invoice_tool.internal_launcher.profile_display.compile_profile_to_rules",
        return_value={"preset": "office_default"},
    ), patch(
        "invoice_tool.internal_launcher.profile_display.load_profile_bundle",
    ) as load_bundle:
        bundle = type("Bundle", (), {"name": "Read Only", "scan_model_id": "rechnungen"})()
        load_bundle.return_value = bundle
        info: ProfileDisplayInfo = load_active_profile_display(profile_path)
    after = profile_path.read_text(encoding="utf-8")
    assert info.ok
    assert before == after
