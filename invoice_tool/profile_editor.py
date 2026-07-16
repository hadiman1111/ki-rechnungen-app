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

from invoice_tool.folder_destination import (
    MODE_ABSOLUTE,
    MODE_RELATIVE,
    migrate_profile_destinations,
    normalize_folder_destination,
    validate_destination,
)
from invoice_tool.target_routing import (
    DEST_TYPE_LEGACY_RELATIVE,
    DEST_TYPE_LOCAL,
    load_target_routing_config,
    sync_target_routing_to_profile,
    validate_target_routing_config,
)


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


def prepare_profile_for_edit(profile: dict) -> dict:
    """Return a deep copy with migrated folder destinations for editing."""
    migrated = migrate_profile_destinations(copy.deepcopy(profile))
    migrated["target_routing"] = load_target_routing_config(migrated)
    return migrated


def _persist_target_routing(profile: dict, config: dict) -> dict:
    synced = sync_target_routing_to_profile(profile, config)
    errors = validate_target_routing_config(config)
    if errors:
        raise ProfileEditorError("; ".join(errors))
    validation_errors = validate_profile_for_save(synced, skip_target_routing=True)
    if validation_errors:
        raise ProfileEditorError("; ".join(validation_errors))
    return synced


def update_global_document_rules(profile: dict, patch: dict) -> dict:
    """Update global document rules inside target_routing."""
    if not isinstance(patch, dict):
        raise ProfileEditorError("patch muss ein dict sein.")
    allowed = {
        "filename_template",
        "routing_field",
        "case_sensitive",
        "confidence_threshold",
        "duplicate_detection",
    }
    disallowed = set(patch.keys()) - allowed
    if disallowed:
        raise ProfileEditorError(f"Nicht erlaubte Schlüssel: {sorted(disallowed)}")

    config = load_target_routing_config(profile)
    global_rules = config.setdefault("global_document_rules", {})
    if not isinstance(global_rules, dict):
        global_rules = {}
        config["global_document_rules"] = global_rules
    for key, value in patch.items():
        global_rules[key] = value
    return _persist_target_routing(profile, config)


def add_target_folder(
    profile: dict,
    *,
    display_name: str,
    destination_path: str,
    routing_values: list[str] | None = None,
) -> dict:
    """Add a new active target-folder configuration."""
    from invoice_tool.target_routing import new_target_id

    name = (display_name or "").strip()
    path = (destination_path or "").strip()
    if not name:
        raise ProfileEditorError("Anzeigename fehlt.")
    if not path:
        raise ProfileEditorError("Zielordner fehlt.")

    config = load_target_routing_config(profile)
    targets = list(config.get("targets") or [])
    values = [str(v).strip() for v in (routing_values or [name]) if str(v or "").strip()]
    if not values:
        raise ProfileEditorError("Mindestens ein Routing-Wert ist erforderlich.")
    targets.append(
        {
            "id": new_target_id(),
            "display_name": name,
            "active": True,
            "destination": {"type": DEST_TYPE_LOCAL, "path": path},
            "routing_values": values,
            "overrides_enabled": False,
            "overrides": {},
        }
    )
    config["targets"] = targets
    return _persist_target_routing(profile, config)


def update_target_folder(profile: dict, target_id: str, patch: dict) -> dict:
    """Patch a target-folder configuration by id."""
    if not isinstance(patch, dict):
        raise ProfileEditorError("patch muss ein dict sein.")
    allowed = {
        "display_name",
        "active",
        "destination",
        "routing_values",
        "overrides_enabled",
        "overrides",
    }
    disallowed = set(patch.keys()) - allowed
    if disallowed:
        raise ProfileEditorError(f"Nicht erlaubte Schlüssel: {sorted(disallowed)}")

    config = load_target_routing_config(profile)
    targets = config.get("targets")
    if not isinstance(targets, list):
        raise ProfileEditorError("Zielordner-Liste fehlt.")

    matches = [i for i, t in enumerate(targets) if isinstance(t, dict) and t.get("id") == target_id]
    if not matches:
        raise ProfileEditorError(f"Zielordner '{target_id}' nicht gefunden.")

    target = dict(targets[matches[0]])
    for key, value in patch.items():
        if key == "destination" and isinstance(value, dict):
            dest_type = str(value.get("type") or DEST_TYPE_LOCAL)
            path = str(value.get("path") or "").strip()
            if dest_type not in (DEST_TYPE_LOCAL, DEST_TYPE_LEGACY_RELATIVE):
                raise ProfileEditorError(f"Unbekannter Zieltyp: {dest_type}")
            target["destination"] = {"type": dest_type, "path": path}
        elif key == "routing_values":
            if not isinstance(value, list):
                raise ProfileEditorError("routing_values muss eine Liste sein.")
            cleaned = [str(v).strip() for v in value if str(v or "").strip()]
            if not cleaned:
                raise ProfileEditorError("Mindestens ein Routing-Wert ist erforderlich.")
            target["routing_values"] = cleaned
        else:
            target[key] = value

    updated_targets = list(targets)
    updated_targets[matches[0]] = target
    config["targets"] = updated_targets
    return _persist_target_routing(profile, config)


def delete_target_folder(profile: dict, target_id: str) -> dict:
    """Remove a target-folder configuration without touching real directories."""
    config = load_target_routing_config(profile)
    targets = config.get("targets")
    if not isinstance(targets, list):
        raise ProfileEditorError("Zielordner-Liste fehlt.")

    fallback = config.get("fallback") if isinstance(config.get("fallback"), dict) else {}
    review = profile.get("review_policy") if isinstance(profile.get("review_policy"), dict) else {}
    if str(review.get("unclear_folder_id") or "") == target_id:
        raise ProfileEditorError(
            "Zielordner ist als Fallback referenziert und kann nicht gelöscht werden."
        )

    remaining = [t for t in targets if isinstance(t, dict) and t.get("id") != target_id]
    if len(remaining) == len(targets):
        raise ProfileEditorError(f"Zielordner '{target_id}' nicht gefunden.")
    config["targets"] = remaining
    return _persist_target_routing(profile, config)


def update_fallback_destination(
    profile: dict,
    *,
    display_name: str,
    destination_path: str,
    destination_type: str = DEST_TYPE_LOCAL,
) -> dict:
    """Update the fallback destination block."""
    name = (display_name or "").strip()
    path = (destination_path or "").strip()
    if not name:
        raise ProfileEditorError("Fallback-Anzeigename fehlt.")
    if not path:
        raise ProfileEditorError("Fallback-Zielordner fehlt.")
    if destination_type not in (DEST_TYPE_LOCAL, DEST_TYPE_LEGACY_RELATIVE):
        raise ProfileEditorError(f"Unbekannter Zieltyp: {destination_type}")

    config = load_target_routing_config(profile)
    config["fallback"] = {
        "display_name": name,
        "destination": {"type": destination_type, "path": path},
    }
    return _persist_target_routing(profile, config)


def convert_legacy_target_to_local_folder(
    profile: dict,
    target_id: str,
    *,
    local_path: str,
) -> dict:
    """Convert a legacy relative target to an explicitly selected local folder."""
    path = (local_path or "").strip()
    if not path:
        raise ProfileEditorError("Lokaler Zielordner fehlt.")
    return update_target_folder(
        profile,
        target_id,
        patch={"destination": {"type": DEST_TYPE_LOCAL, "path": path}},
    )


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
# 3b. update_folder_destination
# ---------------------------------------------------------------------------


def update_folder_destination(
    profile: dict,
    folder_id: str,
    *,
    mode: str,
    path: str,
) -> dict:
    """Update destination for a folders[] entry."""
    destination = {"mode": mode, "path": path.strip()}
    errors = validate_destination(destination, prefix=f"folders[{folder_id}]")
    if errors:
        raise ProfileEditorError("; ".join(errors))

    folders = profile.get("folders")
    if not isinstance(folders, list):
        raise ProfileEditorError("'folders' fehlt oder ist keine Liste.")

    matches = [i for i, f in enumerate(folders) if isinstance(f, dict) and f.get("id") == folder_id]
    if not matches:
        raise ProfileEditorError(f"Ordner mit id '{folder_id}' nicht gefunden.")

    result = copy.deepcopy(profile)
    target = result["folders"][matches[0]]
    target["destination"] = destination
    if mode == MODE_RELATIVE:
        target["folder_name"] = destination["path"]
    return result


def update_review_fallback_folder(
    profile: dict,
    *,
    unclear_folder_id: str,
) -> dict:
    """Set the fallback destination for unclear/unmatched documents."""
    result = copy.deepcopy(profile)
    folders = result.get("folders")
    if not isinstance(folders, list):
        raise ProfileEditorError("'folders' fehlt oder ist keine Liste.")

    folder_ids = {
        str(f.get("id"))
        for f in folders
        if isinstance(f, dict) and f.get("id")
    }
    if unclear_folder_id not in folder_ids:
        raise ProfileEditorError(
            f"unclear_folder_id '{unclear_folder_id}' existiert nicht in folders."
        )

    review = result.get("review_policy")
    if not isinstance(review, dict):
        review = {}
        result["review_policy"] = review

    review["unclear_folder_id"] = unclear_folder_id
    try:
        dest = normalize_folder_destination(
            next(f for f in folders if isinstance(f, dict) and f.get("id") == unclear_folder_id)
        )
        review["unclear_folder"] = dest["path"] if dest["mode"] == MODE_RELATIVE else dest["path"]
    except ValueError:
        pass
    return result


# ---------------------------------------------------------------------------
# 4. validate_profile_for_save
# ---------------------------------------------------------------------------


def validate_profile_for_save(profile: dict, *, skip_target_routing: bool = False) -> list[str]:
    """Prüft das Profil auf Konsistenz; gibt deutsche Fehlermeldungen zurück.

    Leere Liste = valide. Ruft weder profile_compiler noch jsonschema auf.
    naming_schema wird in Phase 2a nicht tief geprüft (bekannter Mismatch).
    "invoice" als document_type ist absichtlich gesperrt.
    """
    errors: list[str] = []

    if not isinstance(profile, dict):
        errors.append("Profil ist kein JSON-Objekt (dict).")
        return errors

    if not skip_target_routing:
        try:
            routing_config = load_target_routing_config(profile)
            errors.extend(validate_target_routing_config(routing_config))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Zielordner-Konfiguration: {exc}")

    folders = profile.get("folders")
    if not isinstance(folders, list):
        errors.append("'folders' fehlt oder ist keine Liste.")
        folder_ids: set[str] = set()
    else:
        folder_ids = set()
        for idx, folder in enumerate(folders):
            prefix = f"folders[{idx}]"
            if not isinstance(folder, dict):
                errors.append(f"{prefix}: Eintrag ist kein dict.")
                continue
            fid = folder.get("id")
            if not fid or not isinstance(fid, str):
                errors.append(f"{prefix}: 'id' fehlt oder ist leer.")
            else:
                folder_ids.add(fid)
            label = folder.get("label")
            if not label or not isinstance(label, str):
                errors.append(f"{prefix}: 'label' fehlt oder ist leer.")
            try:
                destination = normalize_folder_destination(folder)
            except ValueError as exc:
                errors.append(f"{prefix}: {exc}")
                continue
            errors.extend(
                validate_destination(destination, prefix=f"{prefix}.destination")
            )

    review = profile.get("review_policy")
    if isinstance(review, dict):
        unclear_id = review.get("unclear_folder_id")
        if unclear_id:
            if unclear_id not in folder_ids:
                errors.append(
                    f"review_policy.unclear_folder_id '{unclear_id}' existiert nicht "
                    "in folders."
                )

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
        if not doc_type or not isinstance(doc_type, str):
            errors.append(f"{prefix}: 'document_type' fehlt oder ist leer.")
        elif doc_type == "invoice":
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
    2. Backup-Datei anlegen: <name>.bak_YYYYMMDD_HHMMSS_ffffff (lokale Zeit, mit Mikrosekunden).
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
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

    try:
        new_content = json.dumps(profile, indent=2, ensure_ascii=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise ProfileEditorError(
            f"Profil konnte nicht als JSON serialisiert werden: {exc}"
        ) from exc

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
