"""Tests for profile folder destination editing (CFG-001)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from invoice_tool.folder_destination import MODE_ABSOLUTE, MODE_RELATIVE
from invoice_tool.profile_editor import (
    ProfileEditorError,
    prepare_profile_for_edit,
    save_profile_atomic,
    update_folder_destination,
    update_review_fallback_folder,
    validate_profile_for_save,
)


def _base_profile() -> dict:
    return {
        "schema_version": "1.0",
        "profile_name": "CFG-001 Test",
        "folders": [
            {"id": "target", "label": "Ziel", "folder_name": "target"},
            {"id": "fallback", "label": "Fallback", "folder_name": "fallback", "role": "unclear"},
        ],
        "document_profiles": [],
        "review_policy": {
            "unclear_folder": "fallback",
            "business_unclear_payment_goes_to_unclear": True,
            "private_unclear_attributes_stay_private": True,
        },
    }


def test_prepare_profile_for_edit_adds_destination() -> None:
    profile = _base_profile()
    prepared = prepare_profile_for_edit(profile)
    assert prepared["folders"][0]["destination"]["path"] == "target"


def test_update_folder_destination_relative() -> None:
    profile = prepare_profile_for_edit(_base_profile())
    updated = update_folder_destination(
        profile,
        "target",
        mode=MODE_RELATIVE,
        path="neuer/unterordner",
    )
    assert updated["folders"][0]["destination"] == {
        "mode": MODE_RELATIVE,
        "path": "neuer/unterordner",
    }
    assert updated["folders"][0]["folder_name"] == "neuer/unterordner"


def test_update_folder_destination_absolute() -> None:
    profile = prepare_profile_for_edit(_base_profile())
    updated = update_folder_destination(
        profile,
        "target",
        mode=MODE_ABSOLUTE,
        path="/tmp/abs-target",
    )
    assert updated["folders"][0]["destination"]["mode"] == MODE_ABSOLUTE


def test_update_folder_destination_rejects_traversal() -> None:
    profile = prepare_profile_for_edit(_base_profile())
    with pytest.raises(ProfileEditorError, match="\\.\\."):
        update_folder_destination(profile, "target", mode=MODE_RELATIVE, path="../escape")


def test_update_review_fallback_folder() -> None:
    profile = prepare_profile_for_edit(_base_profile())
    updated = update_review_fallback_folder(profile, unclear_folder_id="fallback")
    assert updated["review_policy"]["unclear_folder_id"] == "fallback"


def test_validate_profile_for_save_checks_destinations() -> None:
    profile = prepare_profile_for_edit(_base_profile())
    profile["folders"][0]["destination"] = {"mode": MODE_RELATIVE, "path": "../bad"}
    errors = validate_profile_for_save(profile)
    assert any("folders[0]" in err for err in errors)


def test_save_profile_atomic_preserves_destination(tmp_path: Path) -> None:
    profile = prepare_profile_for_edit(_base_profile())
    updated = update_folder_destination(
        profile,
        "target",
        mode=MODE_ABSOLUTE,
        path="/tmp/saved-target",
    )
    path = tmp_path / "profile_config.local.json"
    path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    save_profile_atomic(path, updated)
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded["folders"][0]["destination"]["mode"] == MODE_ABSOLUTE
