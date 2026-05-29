"""Pure write/validation module for profile_config.local.json.

Phase 2a – UI-unabhängig. Kein Import von Flet, GUI, ui_profile_dialog
oder profile_compiler. Keine Seiteneffekte außer atomischem Dateischreiben
in save_profile_atomic().

Erlaubte Patch-Schlüssel für update_document_profile():
    label, enabled, document_type, target_folder_id, fallback_folder_id,
    confidence_threshold, classification_hints, negative_hints

Bekannte document_type-Werte (ohne "invoice", das absichtlich gesperrt ist):
    credit_note, contract, delivery_note, tax_notice,
    order_confirmation, internal_document, generic_document
"""

from __future__ import annotations

import copy
import json
import os
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Öffentliche Fehlerbasis
# ---------------------------------------------------------------------------


class ProfileEditorError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Interne Konstanten
# ---------------------------------------------------------------------------

_ALLOWED_PATCH_KEYS: frozenset[str] = frozenset(
    {
        "label",
        "enabled",
        "document_type",
        "target_folder_id",
        "fallback_folder_id",
        "confidence_threshold",
        "classification_hints",
        "negative_hints",
    }
)

_KNOWN_DOCUMENT_TYPES: frozenset[str] = frozenset(
    {
        "credit_note",
        "contract",
        "delivery_note",
        "tax_notice",
        "order_confirmation",
        "internal_document",
        "generic_document",
    }
)


# ---------------------------------------------------------------------------
# 1. load_profile_for_edit
# ---------------------------------------------------------------------------


def load_profile_for_edit(profile_path: Path) -> dict:
    """Liest profile_path als UTF-8-JSON und gibt eine tiefe Kopie zurück.

    Raises:
        ProfileEditorError: Datei nicht gefunden, ungültiges JSON, OSError,
                            oder geparster Wert ist kein dict.
    """
    try:
        raw = profile_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ProfileEditorError(
            f"Profildatei nicht gefunden: {profile_path}"
        ) from exc
    except OSError as exc:
        raise ProfileEditorError(
            f"Profildatei konnte nicht gelesen werden: {profile_path} – {exc}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProfileEditorError(
            f"Profildatei enthält ungültiges JSON: {profile_path} – {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ProfileEditorError(
            f"Profildatei ist kein JSON-Objekt (dict): {profile_path}"
        )

    return copy.deepcopy(data)


# ---------------------------------------------------------------------------
# 2. hints_from_textarea
# ---------------------------------------------------------------------------


def hints_from_textarea(text: str) -> list[str]:
    """Wandelt mehrzeiligen Textfeld-Inhalt in eine bereinigte Hint-Liste um.

    Zeilen werden gesplittet, gestrippt und leere Zeilen entfernt.
    Reihenfolge bleibt erhalten; keine Deduplizierung.

    Beispiele:
        "vertrag\\n mietvertrag \\n\\n" -> ["vertrag", "mietvertrag"]
        ""                              -> []
    """
    result: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            result.append(stripped)
    return result


# ---------------------------------------------------------------------------
# 3. update_document_profile
# ---------------------------------------------------------------------------


def update_document_profile(profile: dict, profile_id: str, patch: dict) -> dict:
    """Wendet erlaubte Patch-Schlüssel auf einen document_profile-Eintrag an.

    Gibt eine tiefe Kopie des gesamten Profils zurück; das Original wird
    nicht verändert.

    Raises:
        ProfileEditorError:
            - patch ist kein dict
            - patch enthält nicht erlaubte Schlüssel
            - document_profiles fehlt oder ist keine Liste
            - profile_id nicht gefunden
            - mehrfache Einträge mit gleicher id
    """
    if not isinstance(patch, dict):
        raise ProfileEditorError("patch muss ein dict sein.")

    disallowed = set(patch.keys()) - _ALLOWED_PATCH_KEYS
    if disallowed:
        raise ProfileEditorError(
            f"Nicht erlaubte Patch-Schlüssel: {sorted(disallowed)}. "
            "Felder wie 'id' oder 'naming_schema' dürfen nicht über den Editor "
            "geändert werden."
        )

    profiles_list = profile.get("document_profiles")
    if profiles_list is None or not isinstance(profiles_list, list):
        raise ProfileEditorError(
            "Profil enthält kein 'document_profiles'-Array."
        )

    matches = [i for i, p in enumerate(profiles_list) if p.get("id") == profile_id]
    if not matches:
        raise ProfileEditorError(
            f"document_profile mit id '{profile_id}' nicht gefunden."
        )
    if len(matches) > 1:
        raise ProfileEditorError(
            f"document_profile mit id '{profile_id}' ist mehrfach vorhanden "
            f"(Indizes: {matches})."
        )

    result = copy.deepcopy(profile)
    target = result["document_profiles"][matches[0]]
    for key, value in patch.items():
        target[key] = value

    return result


# ---------------------------------------------------------------------------
# 4. validate_profile_for_save
# ---------------------------------------------------------------------------


def validate_profile_for_save(profile: dict) -> list[str]:
    """Prüft das Profil auf Konsistenz; gibt deutsche Fehlermeldungen zurück.

    Leere Liste = valide. Ruft weder profile_compiler noch jsonschema auf.
    naming_schema wird in Phase 2a nicht tief geprüft (bekannter Mismatch).
    "invoice" als document_type ist absichtlich gesperrt.
    """
    errors: list[str] = []

    if not isinstance(profile, dict):
        errors.append("Profil ist kein JSON-Objekt (dict).")
        return errors

    folders = profile.get("folders")
    if not isinstance(folders, list):
        errors.append("'folders' fehlt oder ist keine Liste.")
        folder_ids: set[str] = set()
    else:
        folder_ids = {f.get("id") for f in folders if isinstance(f, dict) and f.get("id")}

    raw_dp = profile.get("document_profiles")
    if raw_dp is None:
        return errors

    if not isinstance(raw_dp, list):
        errors.append("'document_profiles' ist keine Liste.")
        return errors

    seen_ids: set[str] = set()
    for idx, dp in enumerate(raw_dp):
        prefix = f"document_profiles[{idx}]"

        if not isinstance(dp, dict):
            errors.append(f"{prefix}: Eintrag ist kein dict.")
            continue

        dp_id = dp.get("id")
        if not dp_id or not isinstance(dp_id, str):
            errors.append(f"{prefix}: 'id' fehlt oder ist leer.")
        elif dp_id in seen_ids:
            errors.append(f"{prefix}: id '{dp_id}' ist mehrfach vorhanden.")
        else:
            seen_ids.add(dp_id)

        label = dp.get("label")
        if not label or not isinstance(label, str):
            errors.append(f"{prefix}: 'label' fehlt oder ist leer.")

        doc_type = dp.get("document_type")
        if doc_type is not None:
            if doc_type == "invoice":
                errors.append(
                    f"{prefix}: document_type 'invoice' ist in bearbeitbaren "
                    "Profilen nicht erlaubt."
                )
            elif doc_type not in _KNOWN_DOCUMENT_TYPES:
                errors.append(
                    f"{prefix}: Unbekannter document_type '{doc_type}'."
                )

        target_id = dp.get("target_folder_id")
        if target_id is not None and target_id != "":
            if target_id not in folder_ids:
                errors.append(
                    f"{prefix}: target_folder_id '{target_id}' existiert nicht "
                    "in folders."
                )

        fallback_id = dp.get("fallback_folder_id")
        if fallback_id is not None and fallback_id != "":
            if fallback_id not in folder_ids:
                errors.append(
                    f"{prefix}: fallback_folder_id '{fallback_id}' existiert "
                    "nicht in folders."
                )

        threshold = dp.get("confidence_threshold")
        if threshold is not None:
            if not isinstance(threshold, (int, float)):
                errors.append(
                    f"{prefix}: confidence_threshold muss eine Zahl sein."
                )
            elif not (0.0 <= float(threshold) <= 1.0):
                errors.append(
                    f"{prefix}: confidence_threshold muss zwischen 0.0 und 1.0 "
                    f"liegen (ist {threshold})."
                )

        for hint_key in ("classification_hints", "negative_hints"):
            hints = dp.get(hint_key)
            if hints is not None:
                if not isinstance(hints, list):
                    errors.append(
                        f"{prefix}: '{hint_key}' muss eine Liste sein."
                    )
                else:
                    for hi, h in enumerate(hints):
                        if not isinstance(h, str):
                            errors.append(
                                f"{prefix}: '{hint_key}[{hi}]' muss ein String "
                                f"sein (ist {type(h).__name__})."
                            )

    return errors


# ---------------------------------------------------------------------------
# 5. save_profile_atomic
# ---------------------------------------------------------------------------


def save_profile_atomic(profile_path: Path, profile: dict) -> Path:
    """Schreibt profile atomar in profile_path; erstellt vorher ein Backup.

    Ablauf:
    1. Originaldatei lesen (Inhalt für Backup).
    2. Backup-Datei anlegen: <name>.bak_YYYYMMDD_HHMMSS (lokale Zeit).
    3. JSON in Temp-Datei schreiben: <name>.tmp_<pid>.
    4. Temp-Datei atomar mit os.replace() umbenennen.
    5. Backup-Pfad zurückgeben.

    Raises:
        ProfileEditorError: bei beliebigem I/O-Fehler.

    Validierung obliegt dem Aufrufer; intern wird nicht validiert.
    """
    try:
        original_content = profile_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ProfileEditorError(
            f"Zieldatei für atomares Speichern nicht gefunden: {profile_path}"
        ) from exc
    except OSError as exc:
        raise ProfileEditorError(
            f"Zieldatei konnte nicht gelesen werden: {profile_path} – {exc}"
        ) from exc

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = profile_path.with_name(
        f"{profile_path.name}.bak_{timestamp}"
    )
    tmp_path = profile_path.with_name(
        f"{profile_path.name}.tmp_{os.getpid()}"
    )

    try:
        backup_path.write_text(original_content, encoding="utf-8")
    except OSError as exc:
        raise ProfileEditorError(
            f"Backup konnte nicht erstellt werden: {backup_path} – {exc}"
        ) from exc

    new_content = json.dumps(profile, indent=2, ensure_ascii=False) + "\n"

    try:
        tmp_path.write_text(new_content, encoding="utf-8")
        os.replace(tmp_path, profile_path)
    except OSError as exc:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise ProfileEditorError(
            f"Atomares Speichern fehlgeschlagen: {profile_path} – {exc}"
        ) from exc

    return backup_path
