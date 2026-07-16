"""CFG-001 canonical target-folder routing model, migration, and resolver.

Provides a user-facing configuration shape (global rules, targets, fallback)
while remaining backward-compatible with legacy ``folders[]`` persistence.
"""
from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from invoice_tool.folder_destination import (
    MODE_ABSOLUTE,
    MODE_RELATIVE,
    migrate_profile_destinations,
    normalize_folder_destination,
    validate_destination,
)
from invoice_tool.matching import normalize_for_matching
from invoice_tool.filename_schema import tokenize_filename_stem

DEST_TYPE_LOCAL = "local_folder"
DEST_TYPE_LEGACY_RELATIVE = "legacy_relative"

_ROUTING_FIELD_ALIASES: dict[str, str] = {
    "date": "invoice_date",
    "document_type": "document_type",
    "account": "payment_field",
    "routing_key": "payment_field",
    "konto": "payment_field",
}

_ROUTING_FIELD_LABELS: dict[str, str] = {
    "invoice_date": "Datum",
    "art": "Kategorie",
    "supplier": "Lieferant",
    "amount": "Betrag",
    "payment_field": "Zahlungsfeld / Konto",
    "document_type": "Dokumenttyp",
}

_DEFAULT_ROUTING_FIELDS: tuple[str, ...] = (
    "invoice_date",
    "art",
    "payment_field",
    "supplier",
    "amount",
    "document_type",
)

_TEMPLATE_TOKEN_RE = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class RoutingAssignmentResult:
    """Outcome of :func:`resolve_target_assignment`."""

    routing_field: str
    input_value: str
    normalized_value: str
    matched_target_id: str | None
    matched_display_name: str | None
    matched_routing_value: str | None
    destination_path: str | None
    destination_type: str | None
    is_fallback: bool
    is_ambiguous: bool
    ambiguous_target_ids: tuple[str, ...] = ()
    uses_global_rules: bool = True
    overrides_used: bool = False
    override_fields: tuple[str, ...] = ()
    message: str = ""


class TargetRoutingError(RuntimeError):
    """Raised when configured target routing cannot be applied safely."""


def available_routing_fields(profile: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    """Return (field_key, label) pairs derivable from the real naming model."""
    keys: list[str] = []
    if isinstance(profile, dict):
        naming = profile.get("naming_profile")
        if isinstance(naming, dict):
            for item in naming.get("fields") or []:
                if not isinstance(item, dict) or item.get("enabled") is False:
                    continue
                key = str(item.get("key") or "").strip()
                if key.startswith("literal_"):
                    continue
                canonical = _ROUTING_FIELD_ALIASES.get(key, key)
                if canonical not in keys:
                    keys.append(canonical)
        target_routing = profile.get("target_routing")
        if isinstance(target_routing, dict):
            global_rules = target_routing.get("global_document_rules")
            if isinstance(global_rules, dict):
                template = str(global_rules.get("filename_template") or "")
                for token in _TEMPLATE_TOKEN_RE.findall(template):
                    canonical = _ROUTING_FIELD_ALIASES.get(token, token)
                    if canonical not in keys:
                        keys.append(canonical)

    if not keys:
        keys = list(_DEFAULT_ROUTING_FIELDS)
    return [(key, _ROUTING_FIELD_LABELS.get(key, key)) for key in keys]


def normalize_routing_value(value: str, *, case_sensitive: bool = False) -> str:
    """Normalize a routing value for predictable comparison."""
    stripped = (value or "").strip()
    if not stripped:
        return ""
    if case_sensitive:
        return stripped
    return normalize_for_matching(stripped)


def build_filename_template_from_naming_profile(naming_profile: dict[str, Any]) -> str:
    """Derive a human template string from ``naming_profile``."""
    separator = str(naming_profile.get("separator") or "_")
    parts: list[str] = []
    for item in naming_profile.get("fields") or []:
        if not isinstance(item, dict) or item.get("enabled") is False:
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        if key.startswith("literal_"):
            parts.append(key[len("literal_") :])
        else:
            parts.append(f"{{{key}}}")
    stem = separator.join(parts) if parts else "{invoice_date}_{supplier}"
    return f"{stem}.pdf"


def new_target_id() -> str:
    return f"target-{uuid.uuid4().hex[:12]}"


def _new_target_id() -> str:
    return new_target_id()


def _destination_from_legacy_folder(folder: dict[str, Any]) -> dict[str, str]:
    dest = normalize_folder_destination(folder)
    if dest["mode"] == MODE_ABSOLUTE:
        return {"type": DEST_TYPE_LOCAL, "path": dest["path"]}
    return {"type": DEST_TYPE_LEGACY_RELATIVE, "path": dest["path"]}


def _legacy_folder_from_destination(
    folder_id: str,
    display_name: str,
    destination: dict[str, Any],
    *,
    role: str | None = None,
    active: bool = True,
) -> dict[str, Any]:
    dest_type = str(destination.get("type") or DEST_TYPE_LOCAL)
    path = str(destination.get("path") or "").strip()
    entry: dict[str, Any] = {
        "id": folder_id,
        "label": display_name,
        "active": active,
    }
    if role:
        entry["role"] = role
    if dest_type == DEST_TYPE_LEGACY_RELATIVE:
        entry["destination"] = {"mode": MODE_RELATIVE, "path": path}
        entry["folder_name"] = path
    else:
        entry["destination"] = {"mode": MODE_ABSOLUTE, "path": path}
    return entry


def _infer_routing_values(folder: dict[str, Any]) -> list[str]:
    values: list[str] = []
    folder_id = str(folder.get("id") or "").strip()
    label = str(folder.get("label") or "").strip()
    if folder_id:
        values.append(folder_id)
    if label and label not in values:
        values.append(label)
    legacy_name = folder.get("folder_name")
    if legacy_name and str(legacy_name).strip() and str(legacy_name).strip() not in values:
        values.append(str(legacy_name).strip())
    explicit = folder.get("routing_values")
    if isinstance(explicit, list):
        for item in explicit:
            text = str(item or "").strip()
            if text and text not in values:
                values.append(text)
    return values


def load_target_routing_config(profile: dict[str, Any]) -> dict[str, Any]:
    """Return canonical target routing config, migrating legacy profiles on read."""
    profile = migrate_profile_destinations(copy.deepcopy(profile))
    existing = profile.get("target_routing")
    if isinstance(existing, dict) and existing.get("targets") is not None:
        return copy.deepcopy(existing)

    folders = [f for f in (profile.get("folders") or []) if isinstance(f, dict)]
    review = profile.get("review_policy") if isinstance(profile.get("review_policy"), dict) else {}
    unclear_id = str(review.get("unclear_folder_id") or "").strip()
    if not unclear_id:
        for folder in folders:
            role = str(folder.get("role") or folder.get("purpose") or "").lower()
            if role in ("unclear", "review", "unklar"):
                unclear_id = str(folder.get("id") or "")
                break
    if not unclear_id:
        legacy_unclear = str(review.get("unclear_folder") or "").strip()
        if legacy_unclear:
            for folder in folders:
                if str(folder.get("id")) == legacy_unclear:
                    unclear_id = legacy_unclear
                    break
                try:
                    dest = normalize_folder_destination(folder)
                except ValueError:
                    continue
                if dest.get("path") == legacy_unclear:
                    unclear_id = str(folder.get("id") or "")
                    break

    naming = profile.get("naming_profile") if isinstance(profile.get("naming_profile"), dict) else {}
    filename_template = build_filename_template_from_naming_profile(naming)
    routing_field = "payment_field"
    for key, _ in available_routing_fields(profile):
        if key == "payment_field":
            routing_field = key
            break

    targets: list[dict[str, Any]] = []
    fallback: dict[str, Any] | None = None
    for folder in folders:
        folder_id = str(folder.get("id") or "")
        if not folder_id:
            continue
        display_name = str(folder.get("label") or folder_id)
        destination = _destination_from_legacy_folder(folder)
        if folder_id == unclear_id:
            fallback = {
                "display_name": display_name,
                "destination": destination,
            }
            continue
        role = str(folder.get("role") or folder.get("purpose") or "").lower()
        if role in ("unclear", "review", "unklar"):
            if fallback is None:
                fallback = {
                    "display_name": display_name,
                    "destination": destination,
                }
            continue
        targets.append(
            {
                "id": folder_id,
                "display_name": display_name,
                "active": folder.get("active", True) is not False,
                "destination": destination,
                "routing_values": _infer_routing_values(folder),
                "overrides_enabled": False,
                "overrides": {},
            }
        )

    if fallback is None and folders:
        first = folders[0]
        fallback = {
            "display_name": str(first.get("label") or first.get("id") or "Manuelle Prüfung"),
            "destination": _destination_from_legacy_folder(first),
        }

    return {
        "schema_version": "1.0",
        "global_document_rules": {
            "filename_template": filename_template,
            "routing_field": routing_field,
            "case_sensitive": False,
        },
        "targets": targets,
        "fallback": fallback
        or {
            "display_name": "Manuelle Prüfung",
            "destination": {"type": DEST_TYPE_LOCAL, "path": ""},
        },
    }


def sync_target_routing_to_profile(profile: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Write canonical config into profile and rebuild legacy ``folders[]``."""
    result = copy.deepcopy(profile)
    result["target_routing"] = copy.deepcopy(config)

    global_rules = config.get("global_document_rules") if isinstance(config.get("global_document_rules"), dict) else {}
    template = str(global_rules.get("filename_template") or "")
    separator = "_"
    if "{" in template:
        head = template.split("{", 1)[0]
        if head and head[-1] in "_-":
            separator = head[-1]
    naming = result.get("naming_profile")
    if not isinstance(naming, dict):
        naming = {"separator": separator, "max_length": 80, "fields": [], "fallback_values": {}}
        result["naming_profile"] = naming
    naming["separator"] = separator
    fields: list[dict[str, Any]] = []
    stem = template[:-4] if template.lower().endswith(".pdf") else template
    for part in tokenize_filename_stem(stem):
        part = part.strip()
        if not part:
            continue
        if part.startswith("{") and part.endswith("}"):
            key = part[1:-1].strip()
            canonical = _ROUTING_FIELD_ALIASES.get(key, key)
            fields.append(
                {
                    "key": canonical if canonical != key else key,
                    "label": _ROUTING_FIELD_LABELS.get(canonical, key),
                    "enabled": True,
                }
            )
        else:
            fields.append(
                {
                    "key": f"literal_{part}",
                    "label": f"Literal '{part}'",
                    "enabled": True,
                }
            )
    if fields:
        naming["fields"] = fields

    folders: list[dict[str, Any]] = []
    fallback_id: str | None = None
    for target in config.get("targets") or []:
        if not isinstance(target, dict):
            continue
        target_id = str(target.get("id") or _new_target_id())
        display_name = str(target.get("display_name") or target_id)
        destination = target.get("destination") if isinstance(target.get("destination"), dict) else {}
        folder = _legacy_folder_from_destination(
            target_id,
            display_name,
            destination,
            active=target.get("active", True) is not False,
        )
        routing_values = [
            str(v).strip()
            for v in (target.get("routing_values") or [])
            if str(v or "").strip()
        ]
        if routing_values:
            folder["routing_values"] = routing_values
        if target.get("overrides_enabled"):
            folder["overrides_enabled"] = True
            overrides = target.get("overrides")
            if isinstance(overrides, dict):
                folder["overrides"] = copy.deepcopy(overrides)
        folders.append(folder)

    fallback = config.get("fallback") if isinstance(config.get("fallback"), dict) else None
    if fallback:
        fallback_id = f"fallback-{uuid.uuid4().hex[:8]}"
        folders.append(
            _legacy_folder_from_destination(
                fallback_id,
                str(fallback.get("display_name") or "Manuelle Prüfung"),
                fallback.get("destination") if isinstance(fallback.get("destination"), dict) else {},
                role="unclear",
                active=True,
            )
        )

    result["folders"] = folders
    review = result.get("review_policy")
    if not isinstance(review, dict):
        review = {}
        result["review_policy"] = review
    if fallback_id:
        review["unclear_folder_id"] = fallback_id
        fb_dest = fallback.get("destination") if isinstance(fallback, dict) else {}
        if isinstance(fb_dest, dict) and fb_dest.get("path"):
            review["unclear_folder"] = str(fb_dest["path"])
    return result


def validate_target_routing_config(config: dict[str, Any]) -> list[str]:
    """Validate canonical routing config; return German error messages."""
    errors: list[str] = []
    if not isinstance(config, dict):
        return ["Zielordner-Konfiguration muss ein Objekt sein."]

    global_rules = config.get("global_document_rules")
    if not isinstance(global_rules, dict):
        errors.append("Globale Dokumentregeln fehlen.")
        global_rules = {}

    routing_field = str(global_rules.get("routing_field") or "").strip()
    if not routing_field:
        errors.append("Globales Routing-Feld fehlt.")
    elif routing_field not in dict(available_routing_fields()):
        errors.append(f"Unbekanntes Routing-Feld: {routing_field}")

    template = str(global_rules.get("filename_template") or "").strip()
    if not template:
        errors.append("Dateinamen-Vorlage fehlt.")

    case_sensitive = bool(global_rules.get("case_sensitive", False))
    value_index: dict[str, list[str]] = {}
    targets = config.get("targets")
    if not isinstance(targets, list):
        errors.append("Zielordner-Liste fehlt.")
        targets = []

    seen_ids: set[str] = set()
    for idx, target in enumerate(targets):
        prefix = f"targets[{idx}]"
        if not isinstance(target, dict):
            errors.append(f"{prefix}: Eintrag ist kein Objekt.")
            continue
        target_id = str(target.get("id") or "").strip()
        if not target_id:
            errors.append(f"{prefix}: ID fehlt.")
        elif target_id in seen_ids:
            errors.append(f"{prefix}: ID '{target_id}' ist mehrfach vorhanden.")
        else:
            seen_ids.add(target_id)

        display_name = str(target.get("display_name") or "").strip()
        if not display_name:
            errors.append(f"{prefix}: Anzeigename fehlt.")

        if target.get("active", True) is False:
            continue

        destination = target.get("destination")
        if not isinstance(destination, dict):
            errors.append(f"{prefix}: Zielordner fehlt.")
            continue
        dest_type = str(destination.get("type") or DEST_TYPE_LOCAL)
        path = str(destination.get("path") or "").strip()
        if not path:
            errors.append(f"{prefix}: Kein Zielordner ausgewählt.")
        elif dest_type == DEST_TYPE_LOCAL:
            errors.extend(
                validate_destination(
                    {"mode": MODE_ABSOLUTE, "path": path},
                    prefix=f"{prefix}.destination",
                )
            )
        elif dest_type == DEST_TYPE_LEGACY_RELATIVE:
            errors.extend(
                validate_destination(
                    {"mode": MODE_RELATIVE, "path": path},
                    prefix=f"{prefix}.destination",
                )
            )
        else:
            errors.append(f"{prefix}: Unbekannter Zieltyp '{dest_type}'.")

        routing_values = target.get("routing_values")
        if not isinstance(routing_values, list) or not routing_values:
            errors.append(f"{prefix}: Mindestens ein Routing-Wert ist erforderlich.")
        else:
            normalized_seen: set[str] = set()
            for rv_idx, raw in enumerate(routing_values):
                text = str(raw or "").strip()
                if not text:
                    errors.append(f"{prefix}.routing_values[{rv_idx}]: Leerer Wert.")
                    continue
                normalized = normalize_routing_value(text, case_sensitive=case_sensitive)
                if normalized in normalized_seen:
                    errors.append(f"{prefix}: Doppelter Routing-Wert '{text}'.")
                normalized_seen.add(normalized)
                value_index.setdefault(normalized, []).append(target_id or f"index-{idx}")

    duplicates = {
        value: ids for value, ids in value_index.items() if len(set(ids)) > 1
    }
    for value, ids in duplicates.items():
        errors.append(
            f"Routing-Wert '{value}' ist mehreren aktiven Zielordnern zugeordnet: "
            f"{', '.join(sorted(set(ids)))}."
        )

    fallback = config.get("fallback")
    if not isinstance(fallback, dict):
        errors.append("Fallback-Konfiguration fehlt.")
    else:
        fb_name = str(fallback.get("display_name") or "").strip()
        if not fb_name:
            errors.append("Fallback-Anzeigename fehlt.")
        fb_dest = fallback.get("destination")
        if not isinstance(fb_dest, dict):
            errors.append("Fallback-Zielordner fehlt.")
        else:
            fb_type = str(fb_dest.get("type") or DEST_TYPE_LOCAL)
            fb_path = str(fb_dest.get("path") or "").strip()
            if not fb_path:
                errors.append("Fallback-Zielordner ist nicht ausgewählt.")
            elif fb_type == DEST_TYPE_LOCAL:
                errors.extend(
                    validate_destination(
                        {"mode": MODE_ABSOLUTE, "path": fb_path},
                        prefix="fallback.destination",
                    )
                )
            elif fb_type == DEST_TYPE_LEGACY_RELATIVE:
                errors.extend(
                    validate_destination(
                        {"mode": MODE_RELATIVE, "path": fb_path},
                        prefix="fallback.destination",
                    )
                )

    return errors


def extract_routing_value_from_filename(
    filename_or_value: str,
    *,
    routing_field: str,
    filename_template: str,
) -> str:
    """Extract a routing field value from a pasted filename or raw value."""
    text = (filename_or_value or "").strip()
    if not text:
        return ""
    canonical_field = _ROUTING_FIELD_ALIASES.get(routing_field, routing_field)
    if "{" not in filename_template and "." not in text and "/" not in text and "\\" not in text:
        return text

    stem_template = filename_template[:-4] if filename_template.lower().endswith(".pdf") else filename_template
    separator = "_"
    if "{" in stem_template:
        head = stem_template.split("{", 1)[0]
        if head and head[-1] in "_-":
            separator = head[-1]

    stem = Path(text).stem if "." in text else text
    template_parts = stem_template.split(separator)
    value_parts = stem.split(separator)
    if len(template_parts) != len(value_parts):
        return stem

    for token, value in zip(template_parts, value_parts):
        token = token.strip()
        if token.startswith("{") and token.endswith("}"):
            key = token[1:-1].strip()
            key_canonical = _ROUTING_FIELD_ALIASES.get(key, key)
            if key_canonical == canonical_field or key == routing_field:
                return value.strip()
    return text


def resolve_target_assignment(
    config: dict[str, Any],
    field_value: str,
    *,
    filename_template: str | None = None,
) -> RoutingAssignmentResult:
    """Resolve which target folder should receive a document."""
    global_rules = config.get("global_document_rules") if isinstance(config.get("global_document_rules"), dict) else {}
    routing_field = str(global_rules.get("routing_field") or "payment_field")
    case_sensitive = bool(global_rules.get("case_sensitive", False))
    template = filename_template or str(global_rules.get("filename_template") or "")

    extracted = extract_routing_value_from_filename(
        field_value,
        routing_field=routing_field,
        filename_template=template,
    )
    normalized = normalize_routing_value(extracted, case_sensitive=case_sensitive)
    if not normalized:
        fallback = config.get("fallback") if isinstance(config.get("fallback"), dict) else {}
        fb_dest = fallback.get("destination") if isinstance(fallback.get("destination"), dict) else {}
        return RoutingAssignmentResult(
            routing_field=routing_field,
            input_value=field_value,
            normalized_value="",
            matched_target_id=None,
            matched_display_name=str(fallback.get("display_name") or "Fallback"),
            matched_routing_value=None,
            destination_path=str(fb_dest.get("path") or "") or None,
            destination_type=str(fb_dest.get("type") or "") or None,
            is_fallback=True,
            is_ambiguous=False,
            message="Kein Routing-Wert erkannt – Fallback wird verwendet.",
        )

    matches: list[tuple[dict[str, Any], str]] = []
    for target in config.get("targets") or []:
        if not isinstance(target, dict) or target.get("active") is False:
            continue
        for raw in target.get("routing_values") or []:
            raw_text = str(raw)
            candidate = normalize_routing_value(raw_text, case_sensitive=case_sensitive)
            if candidate == normalized:
                matches.append((target, raw_text))
                break

    if len(matches) > 1:
        return RoutingAssignmentResult(
            routing_field=routing_field,
            input_value=field_value,
            normalized_value=extracted,
            matched_target_id=None,
            matched_display_name=None,
            matched_routing_value=None,
            destination_path=None,
            destination_type=None,
            is_fallback=False,
            is_ambiguous=True,
            ambiguous_target_ids=tuple(str(m[0].get("id") or "") for m in matches),
            message="Mehrdeutige Zuordnung – Konfiguration muss bereinigt werden.",
        )

    if len(matches) == 1:
        target, matched_raw = matches[0]
        dest = target.get("destination") if isinstance(target.get("destination"), dict) else {}
        override_fields: list[str] = []
        overrides_used = False
        if target.get("overrides_enabled") and isinstance(target.get("overrides"), dict):
            override_fields = sorted(str(k) for k in target["overrides"])
            overrides_used = bool(override_fields)
        return RoutingAssignmentResult(
            routing_field=routing_field,
            input_value=field_value,
            normalized_value=extracted,
            matched_target_id=str(target.get("id") or ""),
            matched_display_name=str(target.get("display_name") or ""),
            matched_routing_value=matched_raw,
            destination_path=str(dest.get("path") or "") or None,
            destination_type=str(dest.get("type") or "") or None,
            is_fallback=False,
            is_ambiguous=False,
            uses_global_rules=not overrides_used,
            overrides_used=overrides_used,
            override_fields=tuple(override_fields),
            message="Eindeutige Zuordnung.",
        )

    fallback = config.get("fallback") if isinstance(config.get("fallback"), dict) else {}
    fb_dest = fallback.get("destination") if isinstance(fallback.get("destination"), dict) else {}
    return RoutingAssignmentResult(
        routing_field=routing_field,
        input_value=field_value,
        normalized_value=extracted,
        matched_target_id=None,
        matched_display_name=str(fallback.get("display_name") or "Fallback"),
        matched_routing_value=None,
        destination_path=str(fb_dest.get("path") or "") or None,
        destination_type=str(fb_dest.get("type") or "") or None,
        is_fallback=True,
        is_ambiguous=False,
        message="Kein passender Zielordner – Fallback wird verwendet.",
    )


def target_configuration_summary(profile: dict[str, Any]) -> dict[str, Any]:
    """Compact summary for the main workspace card."""
    config = load_target_routing_config(profile)
    targets = [t for t in (config.get("targets") or []) if isinstance(t, dict)]
    active_targets = [t for t in targets if t.get("active", True) is not False]
    fallback = config.get("fallback") if isinstance(config.get("fallback"), dict) else {}
    fb_dest = fallback.get("destination") if isinstance(fallback.get("destination"), dict) else {}
    legacy_relative = any(
        isinstance(t.get("destination"), dict)
        and t["destination"].get("type") == DEST_TYPE_LEGACY_RELATIVE
        for t in targets
    ) or (
        isinstance(fb_dest, dict) and fb_dest.get("type") == DEST_TYPE_LEGACY_RELATIVE
    )
    validation_errors = validate_target_routing_config(config)
    return {
        "active_target_count": len(active_targets),
        "total_target_count": len(targets),
        "fallback_configured": bool(str(fb_dest.get("path") or "").strip()),
        "fallback_display_name": str(fallback.get("display_name") or ""),
        "validation_passes": not validation_errors,
        "validation_errors": validation_errors,
        "has_legacy_relative_destinations": legacy_relative,
    }


def profile_uses_cfg001_runtime_routing(profile: dict[str, Any]) -> bool:
    """True when explicit local-folder target routing should drive processing."""
    if not isinstance(profile.get("target_routing"), dict):
        return False
    config = load_target_routing_config(profile)
    active_targets = [
        t
        for t in (config.get("targets") or [])
        if isinstance(t, dict) and t.get("active", True) is not False
    ]
    if not active_targets:
        return False
    for target in active_targets:
        destination = target.get("destination") if isinstance(target.get("destination"), dict) else {}
        if destination.get("type") == DEST_TYPE_LEGACY_RELATIVE:
            return False
        if not str(destination.get("path") or "").strip():
            return False
        routing_values = target.get("routing_values")
        if not isinstance(routing_values, list) or not routing_values:
            return False
    return True


def _routing_value_from_raw_text(raw_text: str, routing_field: str) -> str:
    """Acceptance-friendly marker: ROUTING_VALUE=<value> inside document text."""
    marker = "ROUTING_VALUE="
    upper = raw_text or ""
    idx = upper.upper().find(marker)
    if idx == -1:
        return ""
    tail = upper[idx + len(marker) :]
    return tail.split()[0].strip() if tail.strip() else ""


def extract_routing_field_value(
    routing_field: str,
    *,
    extracted: Any,
    normalized: Any | None = None,
    classification: Any | None = None,
    account_decision: Any | None = None,
    art: str | None = None,
    payment_decision: Any | None = None,
    document_date: str | None = None,
) -> str:
    """Resolve the configured routing field to a raw string value."""
    canonical = _ROUTING_FIELD_ALIASES.get(routing_field, routing_field)
    if canonical == "invoice_date":
        if normalized is not None and getattr(normalized, "invoice_date", None):
            return str(normalized.invoice_date)
        if document_date:
            return document_date
        return str(getattr(extracted, "invoice_date_raw", None) or "")
    if canonical == "supplier":
        if normalized is not None and getattr(normalized, "supplier", None):
            return str(normalized.supplier)
        return str(getattr(extracted, "supplier_raw", None) or "")
    if canonical == "amount":
        if normalized is not None and getattr(normalized, "amount", None):
            return str(normalized.amount)
        return str(getattr(extracted, "amount_raw", None) or "")
    if canonical == "payment_field":
        if account_decision is not None and getattr(account_decision, "payment_field", None):
            return str(account_decision.payment_field)
        if payment_decision is not None and getattr(payment_decision, "payment_method", None):
            return str(payment_decision.payment_method)
        marker_value = _routing_value_from_raw_text(getattr(extracted, "raw_text", ""), routing_field)
        if marker_value:
            return marker_value
        return str(getattr(extracted, "payment_method_raw", None) or "")
    if canonical == "art":
        return str(art or "")
    if canonical == "document_type":
        if classification is not None:
            return str(getattr(classification, "dokumenttyp", "") or "")
        return ""
    marker_value = _routing_value_from_raw_text(getattr(extracted, "raw_text", ""), routing_field)
    if marker_value:
        return marker_value
    return ""


def resolve_runtime_target_directory(
    config: dict[str, Any],
    routing_input: str,
    *,
    output_root: Path,
) -> tuple[Path, RoutingAssignmentResult]:
    """Resolve configured routing to an absolute target directory."""
    from invoice_tool.file_lifecycle import PathSafetyError, resolve_safe_target_directory

    result = resolve_target_assignment(config, routing_input)
    if result.is_ambiguous:
        raise TargetRoutingError(result.message)
    if not result.destination_path:
        raise TargetRoutingError("Kein Zielordner konfiguriert.")

    dest_type = result.destination_type or DEST_TYPE_LOCAL
    if dest_type == DEST_TYPE_LOCAL:
        target = Path(result.destination_path).expanduser().resolve()
        if not target.is_dir():
            raise TargetRoutingError(f"Zielordner existiert nicht: {target}")
        return target, result
    if dest_type == DEST_TYPE_LEGACY_RELATIVE:
        try:
            return resolve_safe_target_directory(output_root.resolve(), result.destination_path), result
        except PathSafetyError as exc:
            raise TargetRoutingError(str(exc)) from exc
    raise TargetRoutingError(f"Unbekannter Zieltyp: {dest_type}")


def _sanitize_filename_component(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f{}]', "_", value or "")
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unbekannt"


def render_routing_filename_template(template: str, values: dict[str, str]) -> str:
    """Render a routing filename template using available field values."""
    stem_template = template[:-4] if template.lower().endswith(".pdf") else template

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        canonical = _ROUTING_FIELD_ALIASES.get(key, key)
        raw = values.get(canonical) or values.get(key) or "unbekannt"
        return _sanitize_filename_component(str(raw))

    rendered = _TEMPLATE_TOKEN_RE.sub(_replace, stem_template)
    rendered = re.sub(r"_+", "_", rendered).strip("_")
    if not rendered:
        rendered = "dokument-unbekannt"
    return f"{rendered}.pdf" if template.lower().endswith(".pdf") else rendered


def build_runtime_filename(
    config: dict[str, Any],
    assignment: RoutingAssignmentResult,
    *,
    field_values: dict[str, str],
) -> str:
    """Build the output filename using global rules or supported target overrides."""
    global_rules = config.get("global_document_rules") if isinstance(config.get("global_document_rules"), dict) else {}
    template = str(global_rules.get("filename_template") or "{invoice_date}_{supplier}.pdf")
    if assignment.overrides_used and assignment.matched_target_id:
        for target in config.get("targets") or []:
            if not isinstance(target, dict) or target.get("id") != assignment.matched_target_id:
                continue
            overrides = target.get("overrides") if isinstance(target.get("overrides"), dict) else {}
            override_template = str(overrides.get("filename_template") or "").strip()
            if override_template:
                template = override_template
            break
    return render_routing_filename_template(template, field_values)


def build_routing_metadata(assignment: RoutingAssignmentResult) -> dict[str, Any]:
    """Map resolver output to output_mapping.json fields."""
    destination_type = assignment.destination_type or ""
    destination_mode = MODE_ABSOLUTE if destination_type == DEST_TYPE_LOCAL else MODE_RELATIVE
    return {
        "routing_field": assignment.routing_field,
        "raw_routing_value": assignment.input_value,
        "normalized_routing_value": assignment.normalized_value,
        "target_id": assignment.matched_target_id,
        "target_display_name": assignment.matched_display_name,
        "matched_routing_value": assignment.matched_routing_value,
        "destination_type": destination_type,
        "destination_mode": destination_mode,
        "configured_destination_path": assignment.destination_path,
        "overrides_used": assignment.overrides_used,
        "fallback_used": assignment.is_fallback,
        "rule_id": assignment.matched_target_id or "fallback",
    }


def create_subdirectory(parent_path: Path, folder_name: str) -> Path:
    """Create a single subdirectory under an explicitly selected parent."""
    name = (folder_name or "").strip()
    if not name:
        raise ValueError("Ordnername fehlt.")
    if name in (".", ".."):
        raise ValueError("Ungültiger Ordnername.")
    if "/" in name or "\\" in name or "\x00" in name:
        raise ValueError("Ordnername darf keine Pfadtrenner enthalten.")

    parent = parent_path.expanduser().resolve()
    if not parent.is_dir():
        raise ValueError("Übergeordneter Ordner existiert nicht.")
    target = (parent / name).resolve()
    if not str(target).startswith(str(parent)):
        raise ValueError("Zielordner liegt außerhalb des gewählten übergeordneten Ordners.")
    if target.exists():
        if target.is_dir():
            return target
        raise ValueError(f"Eine Datei mit diesem Namen existiert bereits: {target}")
    target.mkdir()
    return target


def destination_display_path(destination: dict[str, Any]) -> str:
    """User-visible path label for a destination object."""
    if not isinstance(destination, dict):
        return "–"
    path = str(destination.get("path") or "").strip()
    if not path:
        return "Noch kein Ordner gewählt"
    if destination.get("type") == DEST_TYPE_LEGACY_RELATIVE:
        return f"Legacy (relativ): {path}"
    return path


def is_local_folder_destination(destination: dict[str, Any]) -> bool:
    return isinstance(destination, dict) and destination.get("type") in (
        DEST_TYPE_LOCAL,
        None,
        "",
    )
