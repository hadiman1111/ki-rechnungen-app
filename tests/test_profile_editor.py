"""Tests für invoice_tool/profile_editor.py (Phase 2a).

Ausschließlich tmp_path-Fixtures; keine echten Produktionsdateien.
Kein Import von GUI, Flet oder processing-Modulen.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from invoice_tool.profile_editor import (
    ProfileEditorError,
    hints_from_textarea,
    load_profile_for_edit,
    save_profile_atomic,
    update_document_profile,
    validate_profile_for_save,
)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _minimal_profile(*, with_doc_profiles: bool = True) -> dict:
    """Gibt ein minimales, valides Profil-dict zurück."""
    profile: dict = {
        "schema_version": "1.0",
        "profile_name": "Test-Profil",
        "folders": [
            {"id": "inbox", "label": "Posteingang", "folder_name": "inbox"},
            {"id": "archive", "label": "Archiv", "folder_name": "archive"},
        ],
    }
    if with_doc_profiles:
        profile["document_profiles"] = [
            {
                "id": "dp-001",
                "label": "Vertrag",
                "document_type": "contract",
                "target_folder_id": "inbox",
                "fallback_folder_id": "",
                "enabled": True,
                "classification_hints": ["vertrag", "mietvertrag"],
                "negative_hints": [],
                "confidence_threshold": 0.75,
                "naming_schema": {"pattern": "{date}_{label}"},
                "_custom_field": "bewahren",
            }
        ]
    return profile


def _write_profile(path: Path, profile: dict) -> None:
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# load_profile_for_edit
# ---------------------------------------------------------------------------


class TestLoadProfileForEdit:
    def test_success(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        p = tmp_path / "profile.json"
        _write_profile(p, profile)

        result = load_profile_for_edit(p)

        assert result == profile
        assert result is not profile

    def test_missing_file(self, tmp_path: Path) -> None:
        p = tmp_path / "nonexistent.json"
        with pytest.raises(ProfileEditorError, match="nicht gefunden"):
            load_profile_for_edit(p)

    def test_invalid_json(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{ungültiges json: }", encoding="utf-8")
        with pytest.raises(ProfileEditorError, match="ungültiges JSON"):
            load_profile_for_edit(p)

    def test_non_dict_json(self, tmp_path: Path) -> None:
        p = tmp_path / "list.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ProfileEditorError, match="kein JSON-Objekt"):
            load_profile_for_edit(p)

    def test_returns_deep_copy(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        p = tmp_path / "profile.json"
        _write_profile(p, profile)

        result = load_profile_for_edit(p)
        result["profile_name"] = "geändert"

        # Original auf Platte unverändert
        reloaded = json.loads(p.read_text(encoding="utf-8"))
        assert reloaded["profile_name"] == profile["profile_name"]


# ---------------------------------------------------------------------------
# hints_from_textarea
# ---------------------------------------------------------------------------


class TestHintsFromTextarea:
    def test_normal_multiline(self) -> None:
        assert hints_from_textarea("vertrag\nmietvertrag") == ["vertrag", "mietvertrag"]

    def test_leading_trailing_spaces(self) -> None:
        assert hints_from_textarea("  vertrag  \n  mietvertrag  ") == [
            "vertrag",
            "mietvertrag",
        ]

    def test_empty_lines_stripped(self) -> None:
        assert hints_from_textarea("vertrag\n\n\nmietvertrag\n\n") == [
            "vertrag",
            "mietvertrag",
        ]

    def test_empty_string(self) -> None:
        assert hints_from_textarea("") == []

    def test_mixed_whitespace_only_lines(self) -> None:
        assert hints_from_textarea("   \nvertrag\n   \n") == ["vertrag"]

    def test_trailing_newlines_example_from_spec(self) -> None:
        assert hints_from_textarea("vertrag\n mietvertrag \n\n") == [
            "vertrag",
            "mietvertrag",
        ]

    def test_order_preserved(self) -> None:
        result = hints_from_textarea("c\na\nb")
        assert result == ["c", "a", "b"]


# ---------------------------------------------------------------------------
# update_document_profile
# ---------------------------------------------------------------------------


class TestUpdateDocumentProfile:
    def test_applies_allowed_patch(self) -> None:
        profile = _minimal_profile()
        patch = {"label": "Neuer Vertrag", "confidence_threshold": 0.9}

        result = update_document_profile(profile, "dp-001", patch)

        dp = result["document_profiles"][0]
        assert dp["label"] == "Neuer Vertrag"
        assert dp["confidence_threshold"] == 0.9

    def test_preserves_naming_schema(self) -> None:
        profile = _minimal_profile()
        result = update_document_profile(profile, "dp-001", {"label": "X"})
        dp = result["document_profiles"][0]
        assert dp["naming_schema"] == {"pattern": "{date}_{label}"}

    def test_preserves_unknown_fields(self) -> None:
        profile = _minimal_profile()
        result = update_document_profile(profile, "dp-001", {"label": "X"})
        dp = result["document_profiles"][0]
        assert dp["_custom_field"] == "bewahren"

    def test_rejects_disallowed_key_id(self) -> None:
        profile = _minimal_profile()
        with pytest.raises(ProfileEditorError, match="Nicht erlaubte Patch-Schlüssel"):
            update_document_profile(profile, "dp-001", {"id": "hack"})

    def test_rejects_disallowed_key_naming_schema(self) -> None:
        profile = _minimal_profile()
        with pytest.raises(ProfileEditorError, match="Nicht erlaubte Patch-Schlüssel"):
            update_document_profile(profile, "dp-001", {"naming_schema": {}})

    def test_raises_on_missing_document_profiles(self) -> None:
        profile = _minimal_profile(with_doc_profiles=False)
        with pytest.raises(ProfileEditorError, match="document_profiles"):
            update_document_profile(profile, "dp-001", {"label": "X"})

    def test_raises_when_profile_id_not_found(self) -> None:
        profile = _minimal_profile()
        with pytest.raises(ProfileEditorError, match="nicht gefunden"):
            update_document_profile(profile, "does-not-exist", {"label": "X"})

    def test_original_profile_not_mutated(self) -> None:
        profile = _minimal_profile()
        original_label = profile["document_profiles"][0]["label"]

        update_document_profile(profile, "dp-001", {"label": "Geändert"})

        assert profile["document_profiles"][0]["label"] == original_label

    def test_patch_not_dict_raises(self) -> None:
        profile = _minimal_profile()
        with pytest.raises(ProfileEditorError, match="dict"):
            update_document_profile(profile, "dp-001", ["label", "X"])  # type: ignore[arg-type]

    def test_applies_classification_hints(self) -> None:
        profile = _minimal_profile()
        result = update_document_profile(
            profile, "dp-001", {"classification_hints": ["neu"]}
        )
        assert result["document_profiles"][0]["classification_hints"] == ["neu"]


# ---------------------------------------------------------------------------
# validate_profile_for_save
# ---------------------------------------------------------------------------


class TestValidateProfileForSave:
    def test_valid_profile_returns_empty_list(self) -> None:
        assert validate_profile_for_save(_minimal_profile()) == []

    def test_missing_folders_list_returns_error(self) -> None:
        profile = _minimal_profile()
        del profile["folders"]
        errors = validate_profile_for_save(profile)
        assert any("folders" in e for e in errors)

    def test_duplicate_document_profile_id_returns_error(self) -> None:
        profile = _minimal_profile()
        dup = dict(profile["document_profiles"][0])
        profile["document_profiles"].append(dup)
        errors = validate_profile_for_save(profile)
        assert any("mehrfach" in e for e in errors)

    def test_empty_label_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["label"] = ""
        errors = validate_profile_for_save(profile)
        assert any("label" in e.lower() for e in errors)

    def test_document_type_invoice_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["document_type"] = "invoice"
        errors = validate_profile_for_save(profile)
        assert any("invoice" in e for e in errors)

    def test_unknown_document_type_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["document_type"] = "totally_unknown"
        errors = validate_profile_for_save(profile)
        assert any("totally_unknown" in e for e in errors)

    def test_invalid_target_folder_id_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["target_folder_id"] = "ghost"
        errors = validate_profile_for_save(profile)
        assert any("target_folder_id" in e and "ghost" in e for e in errors)

    def test_invalid_fallback_folder_id_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["fallback_folder_id"] = "ghost"
        errors = validate_profile_for_save(profile)
        assert any("fallback_folder_id" in e and "ghost" in e for e in errors)

    def test_empty_fallback_folder_id_is_allowed(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["fallback_folder_id"] = ""
        errors = validate_profile_for_save(profile)
        assert errors == []

    def test_confidence_threshold_below_zero_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["confidence_threshold"] = -0.1
        errors = validate_profile_for_save(profile)
        assert any("confidence_threshold" in e for e in errors)

    def test_confidence_threshold_above_one_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["confidence_threshold"] = 1.1
        errors = validate_profile_for_save(profile)
        assert any("confidence_threshold" in e for e in errors)

    def test_confidence_threshold_zero_is_valid(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["confidence_threshold"] = 0.0
        assert validate_profile_for_save(profile) == []

    def test_confidence_threshold_one_is_valid(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["confidence_threshold"] = 1.0
        assert validate_profile_for_save(profile) == []

    def test_classification_hints_not_list_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["classification_hints"] = "kein-list"
        errors = validate_profile_for_save(profile)
        assert any("classification_hints" in e for e in errors)

    def test_classification_hints_non_string_item_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["classification_hints"] = [42]
        errors = validate_profile_for_save(profile)
        assert any("classification_hints" in e for e in errors)

    def test_negative_hints_not_list_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["negative_hints"] = 123
        errors = validate_profile_for_save(profile)
        assert any("negative_hints" in e for e in errors)

    def test_negative_hints_non_string_item_returns_error(self) -> None:
        profile = _minimal_profile()
        profile["document_profiles"][0]["negative_hints"] = [True]
        errors = validate_profile_for_save(profile)
        assert any("negative_hints" in e for e in errors)

    def test_missing_document_profiles_is_allowed(self) -> None:
        profile = _minimal_profile(with_doc_profiles=False)
        assert validate_profile_for_save(profile) == []

    def test_missing_document_type_returns_error(self) -> None:
        profile = _minimal_profile()
        del profile["document_profiles"][0]["document_type"]
        errors = validate_profile_for_save(profile)
        assert any("document_type" in e and "fehlt" in e for e in errors)


# ---------------------------------------------------------------------------
# save_profile_atomic
# ---------------------------------------------------------------------------


class TestSaveProfileAtomic:
    def _read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_creates_backup(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)

        backup = save_profile_atomic(p, profile)

        assert backup.exists()
        assert backup.name.startswith("profile_config.local.json.bak_")

    def test_backup_contains_original_content(self, tmp_path: Path) -> None:
        original = _minimal_profile()
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, original)
        original_text = p.read_text(encoding="utf-8")

        backup = save_profile_atomic(p, original)

        assert backup.read_text(encoding="utf-8") == original_text

    def test_new_file_contains_updated_json(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)

        updated = dict(profile)
        updated["profile_name"] = "Geändert"
        save_profile_atomic(p, updated)

        result = self._read_json(p)
        assert result["profile_name"] == "Geändert"

    def test_json_has_trailing_newline(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)

        save_profile_atomic(p, profile)

        assert p.read_text(encoding="utf-8").endswith("\n")

    def test_preserves_unicode(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        profile["profile_name"] = "Prüfäußerung – ü ö ä ß €"
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)

        save_profile_atomic(p, profile)

        raw = p.read_text(encoding="utf-8")
        assert "Prüfäußerung" in raw
        assert "\\u" not in raw

    def test_returns_backup_path(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)

        backup = save_profile_atomic(p, profile)

        assert isinstance(backup, Path)
        assert backup.parent == tmp_path

    def test_temp_file_not_left_behind_on_success(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)

        save_profile_atomic(p, profile)

        tmp_files = list(tmp_path.glob(f"*.tmp_{os.getpid()}"))
        assert tmp_files == []

    def test_temp_file_in_same_directory(self, tmp_path: Path) -> None:
        """Temp-Datei wird im selben Verzeichnis erstellt (gleiche Partition)."""
        profile = _minimal_profile()
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)

        # Wir prüfen dies indirekt: nach erfolgreichem Speichern darf keine
        # .tmp_* Datei übrig bleiben; während des Schreibens wäre sie sichtbar,
        # aber da save_profile_atomic synchron ist, können wir nur nachher prüfen.
        save_profile_atomic(p, profile)
        assert not list(tmp_path.glob("*.tmp_*"))

    def test_raises_if_file_not_found(self, tmp_path: Path) -> None:
        p = tmp_path / "ghost.json"
        with pytest.raises(ProfileEditorError, match="nicht gefunden"):
            save_profile_atomic(p, {})

    def test_profile_unknown_keys_preserved(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        profile["_zukünftiges_feld"] = "unbekannt"
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)

        save_profile_atomic(p, profile)

        result = self._read_json(p)
        assert result["_zukünftiges_feld"] == "unbekannt"

    def test_indent_two_spaces(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)

        save_profile_atomic(p, profile)

        raw = p.read_text(encoding="utf-8")
        assert '  "' in raw

    def test_two_rapid_saves_produce_distinct_backups(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)

        backup1 = save_profile_atomic(p, profile)
        backup2 = save_profile_atomic(p, profile)

        assert backup1.exists()
        assert backup2.exists()
        assert backup1 != backup2

    def test_non_serializable_profile_raises_profile_editor_error(self, tmp_path: Path) -> None:
        profile = _minimal_profile()
        p = tmp_path / "profile_config.local.json"
        _write_profile(p, profile)
        original_text = p.read_text(encoding="utf-8")

        bad_profile = dict(profile)
        bad_profile["unserializable"] = datetime.now()

        with pytest.raises(ProfileEditorError, match="serialisiert"):
            save_profile_atomic(p, bad_profile)

        assert p.read_text(encoding="utf-8") == original_text


# ---------------------------------------------------------------------------
# Smoke-Tests: Modulimport
# ---------------------------------------------------------------------------


class TestUiProfileDialogImport:
    def test_ui_profile_dialog_importable(self) -> None:
        """Stellt sicher, dass ui_profile_dialog ohne Fehler importiert werden kann.

        Prüft, dass Flet, profile_editor und alle Typen korrekt eingebunden sind.
        """
        import invoice_tool.ui_profile_dialog as mod  # noqa: F401

        assert hasattr(mod, "show_profile_details_dialog")
        assert hasattr(mod, "show_edit_document_profile_dialog")

    def test_show_profile_details_dialog_is_callable(self) -> None:
        from invoice_tool.ui_profile_dialog import show_profile_details_dialog

        assert callable(show_profile_details_dialog)

    def test_show_edit_document_profile_dialog_is_callable(self) -> None:
        from invoice_tool.ui_profile_dialog import show_edit_document_profile_dialog

        assert callable(show_edit_document_profile_dialog)
