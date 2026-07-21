"""Canonical configuration model and compilation to CFG-001 target_routing."""

from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from invoice_tool.filename_schema import (
    CANONICAL_RECHNUNGEN_FILENAME_TOKENS,
    tokenize_filename_stem,
)
from invoice_tool.matching import normalize_for_matching
from invoice_tool.scan_models import NEUTRAL_PREVIEW_VALUES, ScanModel, get_scan_model
from invoice_tool.target_routing import (
    DEST_TYPE_LEGACY_RELATIVE,
    DEST_TYPE_LOCAL,
    load_target_routing_config,
    new_target_id,
    normalize_routing_value,
    render_routing_filename_template,
    sync_target_routing_to_profile,
    validate_target_routing_config,
)

DATE_FORMATS: dict[str, str] = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "YYYYMMDD": "%Y%m%d",
    "YYMMDD": "%y%m%d",
    "DD.MM.YYYY": "%d.%m.%Y",
    "DDMMYY": "%d%m%y",
    "DDMMYYYY": "%d%m%Y",
}

SEPARATORS: dict[str, str] = {
    "underscore": "_",
    "hyphen": "-",
    "space": " ",
    "dot": ".",
}

_SYSTEM_FILENAME_COMPONENTS: tuple[dict[str, str], ...] = (
    {"type": "system", "key": "extension", "label": "Dateityp"},
    {"type": "system", "key": "custom_text", "label": "Eigener Text"},
)

SOMAA_CANONICAL_FILENAME_TEMPLATE = (
    "{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf"
)

_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f{}]')
_BRACED_TOKEN_RE = re.compile(r"^\{([^}]+)\}$")


@dataclass
class MatchingRule:
    feature_key: str
    operator: str = "ist"
    values: list[str] = field(default_factory=list)

    def summary(self, feature_label: str) -> str:
        cleaned = [value.strip() for value in self.values if value.strip()]
        if not cleaned:
            return "Noch keine Zuordnungsregel"
        if len(cleaned) == 1:
            return f'{feature_label} ist „{cleaned[0]}"'
        joined = '" oder „'.join(cleaned)
        return f'{feature_label} ist „{joined}"'


@dataclass
class FilenameComponent:
    type: str  # feature | system | separator
    key: str
    label: str = ""
    custom_text: str = ""
    date_format: str = "YYYYMMDD"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type,
            "key": self.key,
            "label": self.label,
        }
        if self.custom_text:
            payload["custom_text"] = self.custom_text
        if self.date_format:
            payload["date_format"] = self.date_format
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilenameComponent:
        return cls(
            type=str(data.get("type") or "feature"),
            key=str(data.get("key") or ""),
            label=str(data.get("label") or ""),
            custom_text=str(data.get("custom_text") or ""),
            date_format=str(data.get("date_format") or "YYYYMMDD"),
        )


@dataclass
class FilenamePattern:
    separator: str = "_"
    components: list[FilenameComponent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "separator": self.separator,
            "components": [component.to_dict() for component in self.components],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> FilenamePattern:
        if not isinstance(data, dict):
            return cls()
        components = [
            FilenameComponent.from_dict(item)
            for item in (data.get("components") or [])
            if isinstance(item, dict)
        ]
        separator_key = str(data.get("separator") or "underscore")
        separator = SEPARATORS.get(separator_key, data.get("separator") or "_")
        if separator_key in SEPARATORS:
            separator = SEPARATORS[separator_key]
        elif separator not in SEPARATORS.values():
            separator = "_"
        pattern = cls(separator=separator, components=components)
        return repair_filename_pattern(pattern)


@dataclass
class Configuration:
    id: str
    name: str
    active: bool = True
    matching: MatchingRule | None = None
    filename_pattern: FilenamePattern = field(default_factory=FilenamePattern)
    destination: dict[str, str] = field(default_factory=lambda: {"type": DEST_TYPE_LOCAL, "path": ""})

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "active": self.active,
            "filename_pattern": self.filename_pattern.to_dict(),
            "destination": copy.deepcopy(self.destination),
        }
        if self.matching is not None:
            payload["matching"] = {
                "feature_key": self.matching.feature_key,
                "operator": self.matching.operator,
                "values": list(self.matching.values),
            }
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Configuration:
        matching_data = data.get("matching")
        matching: MatchingRule | None = None
        if isinstance(matching_data, dict):
            matching = MatchingRule(
                feature_key=str(matching_data.get("feature_key") or ""),
                operator=str(matching_data.get("operator") or "ist"),
                values=[str(v) for v in (matching_data.get("values") or [])],
            )
        destination = data.get("destination")
        if not isinstance(destination, dict):
            destination = {"type": DEST_TYPE_LOCAL, "path": ""}
        return cls(
            id=str(data.get("id") or new_configuration_id()),
            name=str(data.get("name") or "Neue Konfiguration"),
            active=data.get("active", True) is not False,
            matching=matching,
            filename_pattern=FilenamePattern.from_dict(
                data.get("filename_pattern") if isinstance(data.get("filename_pattern"), dict) else None
            ),
            destination={
                "type": str(destination.get("type") or DEST_TYPE_LOCAL),
                "path": str(destination.get("path") or ""),
            },
        )


@dataclass
class UnmatchedConfiguration:
    name: str = "Nicht zugeordnete Dokumente"
    filename_pattern: FilenamePattern = field(default_factory=FilenamePattern)
    destination: dict[str, str] = field(default_factory=lambda: {"type": DEST_TYPE_LOCAL, "path": ""})

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "filename_pattern": self.filename_pattern.to_dict(),
            "destination": copy.deepcopy(self.destination),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> UnmatchedConfiguration:
        if not isinstance(data, dict):
            return cls()
        destination = data.get("destination")
        if not isinstance(destination, dict):
            destination = {"type": DEST_TYPE_LOCAL, "path": ""}
        return cls(
            name=str(data.get("name") or "Nicht zugeordnete Dokumente"),
            filename_pattern=FilenamePattern.from_dict(
                data.get("filename_pattern") if isinstance(data.get("filename_pattern"), dict) else None
            ),
            destination={
                "type": str(destination.get("type") or DEST_TYPE_LOCAL),
                "path": str(destination.get("path") or ""),
            },
        )


@dataclass
class ProfileBundle:
    id: str
    name: str
    active: bool
    scan_model_id: str
    configurations: list[Configuration]
    unmatched: UnmatchedConfiguration
    legacy_profile: dict[str, Any] = field(default_factory=dict)

    @property
    def scan_model(self) -> ScanModel:
        return get_scan_model(self.scan_model_id)


def new_configuration_id() -> str:
    return f"config-{uuid.uuid4().hex[:12]}"


def new_profile_id() -> str:
    return f"profile-{uuid.uuid4().hex[:12]}"


def default_filename_pattern(scan_model: ScanModel) -> FilenamePattern:
    components: list[FilenameComponent] = []
    for feature in scan_model.features[:4]:
        components.append(
            FilenameComponent(type="feature", key=feature.key, label=feature.label)
        )
    components.append(FilenameComponent(type="system", key="extension", label="Dateityp"))
    return FilenamePattern(separator="_", components=components)


def available_filename_components(scan_model: ScanModel) -> list[dict[str, str]]:
    items = [
        {"type": "feature", "key": feature.key, "label": feature.label}
        for feature in scan_model.features
        if feature.filename_supported
    ]
    items.extend(_SYSTEM_FILENAME_COMPONENTS)
    return items


def normalize_filename_part(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = _UNSAFE_FILENAME_CHARS.sub("_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def _rebuild_stem_from_pattern(pattern: FilenamePattern) -> str:
    parts: list[str] = []
    for component in pattern.components:
        if component.type == "system" and component.key == "extension":
            continue
        if component.type == "feature":
            parts.append(f"{{{component.key}}}")
        elif component.type == "system" and component.key == "custom_text":
            parts.append(component.custom_text or "")
    return pattern.separator.join(part for part in parts if part)


def _component_for_stem_token(
    token: str,
    *,
    scan_model: ScanModel | None = None,
) -> FilenameComponent:
    match = _BRACED_TOKEN_RE.match(token.strip())
    if match:
        key = match.group(1).strip()
        if scan_model is not None and key in scan_model.feature_keys():
            feature = scan_model.get_feature(key)
            return FilenameComponent(type="feature", key=key, label=feature.label if feature else key)
        if key in CANONICAL_RECHNUNGEN_FILENAME_TOKENS:
            return FilenameComponent(type="feature", key=key, label=key)
        return FilenameComponent(
            type="system",
            key="custom_text",
            label="Eigener Text",
            custom_text=token,
        )
    bare = token.strip()
    if scan_model is not None and bare in scan_model.feature_keys():
        feature = scan_model.get_feature(bare)
        return FilenameComponent(type="feature", key=bare, label=feature.label if feature else bare)
    if bare in CANONICAL_RECHNUNGEN_FILENAME_TOKENS:
        return FilenameComponent(type="feature", key=bare, label=bare)
    return FilenameComponent(
        type="system",
        key="custom_text",
        label="Eigener Text",
        custom_text=bare,
    )


def _brace_known_bare_tokens(stem: str) -> str:
    """Wrap known feature token names that appear without braces in a stem."""
    result = stem
    for token in sorted(CANONICAL_RECHNUNGEN_FILENAME_TOKENS, key=len, reverse=True):
        result = re.sub(
            rf"(?<!\{{){re.escape(token)}(?!\}})",
            f"{{{token}}}",
            result,
        )
    return result


def pattern_from_template(
    template: str,
    *,
    scan_model: ScanModel | None = None,
    separator: str = "_",
) -> FilenamePattern:
    """Parse a filename template into a canonical FilenamePattern."""
    stem = template[:-4] if template.lower().endswith(".pdf") else template
    stem = _brace_known_bare_tokens(stem)
    pattern = FilenamePattern(separator=separator)
    for token in tokenize_filename_stem(stem):
        pattern.components.append(_component_for_stem_token(token, scan_model=scan_model))
    pattern.components.append(FilenameComponent(type="system", key="extension", label="Dateityp"))
    return pattern


def repair_filename_pattern(
    pattern: FilenamePattern,
    *,
    scan_model: ScanModel | None = None,
) -> FilenamePattern:
    """Repair fragmented custom_text token pieces into atomic feature tokens."""
    stem = _rebuild_stem_from_pattern(pattern)
    if not stem:
        return pattern
    return pattern_from_template(f"{stem}.pdf", scan_model=scan_model, separator=pattern.separator)


def somaa_canonical_filename_pattern(scan_model: ScanModel | None = None) -> FilenamePattern:
    resolved = scan_model or get_scan_model("rechnungen")
    return pattern_from_template(SOMAA_CANONICAL_FILENAME_TEMPLATE, scan_model=resolved)


def validate_filename_pattern_tokens(
    pattern: FilenamePattern,
    scan_model: ScanModel,
) -> list[str]:
    """Return warnings for split-token fragments or unknown braced tokens."""
    issues: list[str] = []
    allowed = set(scan_model.feature_keys())
    for component in pattern.components:
        if component.type == "system" and component.key == "custom_text":
            text = component.custom_text or ""
            if "{" in text or "}" in text:
                issues.append(
                    f"Fragmentiertes Token-Literal erkannt: {text!r} — bitte als Merkmal speichern."
                )
        elif component.type == "feature" and component.key not in allowed:
            issues.append(f"Unbekanntes Dateinamen-Merkmal: {component.key}")
    return issues


def format_date_preview(date_format_key: str) -> str:
    sample = datetime(2026, 7, 8)
    fmt = DATE_FORMATS.get(date_format_key, DATE_FORMATS["YYYYMMDD"])
    return sample.strftime(fmt)


def pattern_to_template(pattern: FilenamePattern) -> str:
    parts: list[str] = []
    for component in pattern.components:
        if component.type == "system" and component.key == "extension":
            continue
        if component.type == "system" and component.key == "custom_text":
            text = normalize_filename_part(component.custom_text or "text")
            if text:
                parts.append(text)
            continue
        if component.type == "feature" and component.key in {"invoice_date", "quote_date", "creation_date"}:
            parts.append(f"{{{component.key}}}")
            continue
        if component.type == "feature":
            parts.append(f"{{{component.key}}}")
    stem = pattern.separator.join(part for part in parts if part)
    return f"{stem}.pdf" if stem else "dokument.pdf"


def preview_filename(
    pattern: FilenamePattern,
    scan_model: ScanModel,
    *,
    sample_values: dict[str, str] | None = None,
) -> str:
    template = pattern_to_template(pattern)
    values = dict(NEUTRAL_PREVIEW_VALUES)
    if sample_values:
        values.update(sample_values)
    rendered = render_routing_filename_template(template, values)
    stem, _, ext = rendered.rpartition(".")
    if stem:
        normalized_stem = pattern.separator.join(
            normalize_filename_part(part) for part in stem.split(pattern.separator) if part
        )
        return f"{normalized_stem}.{ext or 'pdf'}"
    return normalize_filename_part(rendered) + ".pdf"


def matching_summary(configuration: Configuration, scan_model: ScanModel) -> str:
    if configuration.matching is None:
        return "Keine Zuordnungsregel"
    feature = scan_model.get_feature(configuration.matching.feature_key)
    label = feature.label if feature else configuration.matching.feature_key
    return configuration.matching.summary(label)


def destination_display(path: str) -> str:
    if not path:
        return "Ordner noch auswählen"
    expanded = Path(path).expanduser()
    home = Path.home()
    try:
        rel = expanded.resolve().relative_to(home.resolve())
        return f"~/{rel.as_posix()}"
    except ValueError:
        return str(expanded)


def validate_duplicate_active_rules(configurations: list[Configuration]) -> list[str]:
    seen: dict[tuple[str, str], str] = {}
    errors: list[str] = []
    for config in configurations:
        if not config.active or config.matching is None:
            continue
        for raw in config.matching.values:
            normalized = normalize_routing_value(raw, case_sensitive=False)
            if not normalized:
                continue
            key = (config.matching.feature_key, normalized)
            if key in seen and seen[key] != config.id:
                errors.append(
                    f'Doppelte aktive Regel für "{raw}" in "{config.name}" und "{seen[key]}"'
                )
            else:
                seen[key] = config.name
    return errors


def resolve_configuration_match(
    configurations: list[Configuration],
    *,
    feature_key: str,
    value: str,
) -> tuple[Configuration | None, str | None]:
    normalized = normalize_routing_value(value, case_sensitive=False)
    matches: list[Configuration] = []
    for config in configurations:
        if not config.active or config.matching is None:
            continue
        if config.matching.feature_key != feature_key:
            continue
        rule_values = {
            normalize_routing_value(item, case_sensitive=False)
            for item in config.matching.values
            if str(item or "").strip()
        }
        if normalized in rule_values:
            matches.append(config)
    if not matches:
        return None, "Keine passende Konfiguration"
    if len(matches) > 1:
        names = ", ".join(item.name for item in matches)
        return None, f"Mehrere Konfigurationen passen: {names}"
    return matches[0], None


def compile_profile_bundle_to_legacy(bundle: ProfileBundle) -> dict[str, Any]:
    """Compile canonical bundle back to legacy profile dict for runtime."""
    profile = copy.deepcopy(bundle.legacy_profile) if bundle.legacy_profile else {}
    profile["profile_name"] = bundle.name
    profile["scan_model_id"] = bundle.scan_model_id

    primary_feature = bundle.configurations[0].matching.feature_key if (
        bundle.configurations and bundle.configurations[0].matching
    ) else "payment_field"
    global_template = pattern_to_template(
        bundle.configurations[0].filename_pattern if bundle.configurations else default_filename_pattern(bundle.scan_model)
    )

    targets: list[dict[str, Any]] = []
    for config in bundle.configurations:
        routing_values = list(config.matching.values) if config.matching else [config.name]
        target_template = pattern_to_template(config.filename_pattern) or global_template
        overrides: dict[str, Any] = {}
        overrides_enabled = target_template != global_template
        if overrides_enabled:
            overrides["filename_template"] = target_template
        targets.append(
            {
                "id": config.id,
                "display_name": config.name,
                "active": config.active,
                "destination": copy.deepcopy(config.destination),
                "routing_values": routing_values,
                "overrides_enabled": overrides_enabled,
                "overrides": overrides,
            }
        )

    config = {
        "schema_version": "2.0",
        "global_document_rules": {
            "filename_template": global_template,
            "routing_field": primary_feature,
            "case_sensitive": False,
        },
        "targets": targets,
        "fallback": {
            "display_name": bundle.unmatched.name,
            "destination": copy.deepcopy(bundle.unmatched.destination),
        },
    }
    profile["target_routing"] = config
    return sync_target_routing_to_profile(profile, config)


def load_bundle_from_legacy_profile(profile_id: str, profile: dict[str, Any]) -> ProfileBundle:
    """Build a ProfileBundle from an existing legacy profile dict."""
    scan_model_id = str(profile.get("scan_model_id") or "rechnungen")
    config = load_target_routing_config(profile)
    global_rules = config.get("global_document_rules") if isinstance(config.get("global_document_rules"), dict) else {}
    routing_field = str(global_rules.get("routing_field") or "payment_field")
    global_template = str(global_rules.get("filename_template") or "")

    configurations: list[Configuration] = []
    for target in config.get("targets") or []:
        if not isinstance(target, dict):
            continue
        overrides = target.get("overrides") if isinstance(target.get("overrides"), dict) else {}
        template = str(overrides.get("filename_template") or global_template)
        configurations.append(
            Configuration(
                id=str(target.get("id") or new_configuration_id()),
                name=str(target.get("display_name") or "Konfiguration"),
                active=target.get("active", True) is not False,
                matching=MatchingRule(
                    feature_key=routing_field,
                    operator="ist",
                    values=[str(v) for v in (target.get("routing_values") or [])],
                ),
                filename_pattern=_pattern_from_template(template, scan_model=get_scan_model(scan_model_id)),
                destination={
                    "type": str((target.get("destination") or {}).get("type") or DEST_TYPE_LOCAL),
                    "path": str((target.get("destination") or {}).get("path") or ""),
                },
            )
        )

    fallback = config.get("fallback") if isinstance(config.get("fallback"), dict) else {}
    unmatched = UnmatchedConfiguration(
        name=str(fallback.get("display_name") or "Nicht zugeordnete Dokumente"),
        filename_pattern=_pattern_from_template(global_template, scan_model=get_scan_model(scan_model_id)),
        destination={
            "type": str((fallback.get("destination") or {}).get("type") or DEST_TYPE_LOCAL),
            "path": str((fallback.get("destination") or {}).get("path") or ""),
        },
    )

    return ProfileBundle(
        id=profile_id,
        name=str(profile.get("profile_name") or profile_id),
        active=True,
        scan_model_id=scan_model_id,
        configurations=configurations,
        unmatched=unmatched,
        legacy_profile=copy.deepcopy(profile),
    )


def _pattern_from_template(template: str, *, scan_model: ScanModel | None = None) -> FilenamePattern:
    return pattern_from_template(template, scan_model=scan_model)


def validate_profile_bundle(bundle: ProfileBundle) -> list[str]:
    errors = validate_duplicate_active_rules(bundle.configurations)
    compiled = compile_profile_bundle_to_legacy(bundle)
    errors.extend(validate_target_routing_config(compiled.get("target_routing") or {}))
    return errors


def copy_filename_pattern(source: FilenamePattern) -> FilenamePattern:
    return FilenamePattern(
        separator=source.separator,
        components=[FilenameComponent.from_dict(item.to_dict()) for item in source.components],
    )
