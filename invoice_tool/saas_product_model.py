"""Generic SaaS product profile/configuration surface.

This module is the product-facing contract for the external UI-v2 / SaaS variant.
It deliberately contains no private tenant defaults (SOMAA, Hadi, AMEX-1005, EP, …).

Internal Dock/Launcher code must not import this module as a runtime dependency for
SOMAA operations; local/private profiles remain outside SaaS defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

# Markers that must never appear in SaaS blank defaults or product-default payloads.
FORBIDDEN_PRIVATE_DEFAULT_MARKERS: tuple[str, ...] = (
    "SOMAA",
    "Somaa",
    "somaa",
    "Hadi",
    "hadi",
    "AMEX-1005",
    "amex-1005",
    "AMEX_1005",
    "amex_1005",
    # Tenant-specific category shortcuts used in the local Hadi/SOMAA working profile.
    # Allowed only inside local example/working profiles — never as SaaS product defaults.
)

# Category / folder ids that are private-tenant conventions, not SaaS blanks.
FORBIDDEN_PRIVATE_CATEGORY_DEFAULTS: frozenset[str] = frozenset(
    {
        "ai",
        "ep",
        "amex",
        "vobaai",
    }
)

GENERIC_SCAN_MODELS: tuple[tuple[str, str, str], ...] = (
    ("rechnungen", "Rechnungsdaten", "Rechnungen"),
    ("angebote", "Angebotsdaten", "Angebote"),
    ("freitext-dokumente", "Freitext-Dokumente", "Freitext-Dokumente"),
)

DEFAULT_SAAS_SCAN_MODEL_ID = "rechnungen"
DEFAULT_SAAS_PROFILE_NAME = "Neues Profil"
DEFAULT_SAAS_REVIEW_FOLDER = "unklar"
DEFAULT_SAAS_FILENAME_PATTERN = (
    "{invoice_date}_{supplier}_{amount}_{payment_field}.pdf"
)


@dataclass(frozen=True)
class SaasMatchingCondition:
    """One user-editable matching condition (no regex exposure)."""

    feature_key: str
    operator: str = "ist"
    values: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_key": self.feature_key,
            "operator": self.operator,
            "values": list(self.values),
        }


@dataclass(frozen=True)
class SaasConfigurationSurface:
    """One routing/naming configuration inside a SaaS profile."""

    name: str
    active: bool = True
    document_type: str = ""
    matching_conditions: tuple[SaasMatchingCondition, ...] = ()
    destination_category: str = ""
    destination_folder: str = ""
    filename_pattern: str = ""
    review_rule: str = "unclear_on_no_match"
    payment_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "active": self.active,
            "document_type": self.document_type,
            "matching_conditions": [item.to_dict() for item in self.matching_conditions],
            "destination_category": self.destination_category,
            "destination_folder": self.destination_folder,
            "filename_pattern": self.filename_pattern,
            "review_rule": self.review_rule,
            "payment_hint": self.payment_hint,
        }


@dataclass(frozen=True)
class SaasProfileSurface:
    """Editable SaaS profile surface shown/managed by UI-v2."""

    profile_name: str
    scan_model_id: str
    document_type: str = "Rechnungen"
    configurations: tuple[SaasConfigurationSurface, ...] = ()
    review_unclear_folder: str = DEFAULT_SAAS_REVIEW_FOLDER
    default_filename_pattern: str = DEFAULT_SAAS_FILENAME_PATTERN
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "scan_model_id": self.scan_model_id,
            "document_type": self.document_type,
            "configurations": [item.to_dict() for item in self.configurations],
            "review_unclear_folder": self.review_unclear_folder,
            "default_filename_pattern": self.default_filename_pattern,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SaasProfileEditorField:
    """Descriptor for a generic profile/configuration editor field."""

    key: str
    label: str
    kind: str
    required: bool = False
    help_text: str = ""


@dataclass(frozen=True)
class SaasProductBoundary:
    """Hard product-stream boundary for the SaaS / internal split."""

    internal_launcher_entry: str = "app_internal_launcher.py"
    saas_ui_entry: str = "app_ui_v2.py"
    internal_package: str = "invoice_tool.internal_launcher"
    saas_ui_package: str = "invoice_tool.ui_v2"
    processing_core_entry: str = "invoice_tool.run"
    private_profile_role: str = "local_example_or_working_profile_only"


def list_generic_scan_models() -> tuple[dict[str, str], ...]:
    return tuple(
        {"id": model_id, "label": label, "document_domain": domain}
        for model_id, label, domain in GENERIC_SCAN_MODELS
    )


def build_blank_saas_profile(
    *,
    profile_name: str = DEFAULT_SAAS_PROFILE_NAME,
    scan_model_id: str = DEFAULT_SAAS_SCAN_MODEL_ID,
) -> SaasProfileSurface:
    """Return a blank SaaS profile with no private tenant defaults."""

    resolved_name = (profile_name or "").strip() or DEFAULT_SAAS_PROFILE_NAME
    resolved_model = (scan_model_id or "").strip() or DEFAULT_SAAS_SCAN_MODEL_ID
    known_ids = {item[0] for item in GENERIC_SCAN_MODELS}
    if resolved_model not in known_ids:
        raise ValueError(f"Unbekanntes Scanmodell für SaaS-Default: {resolved_model}")

    document_type = next(
        domain for model_id, _label, domain in GENERIC_SCAN_MODELS if model_id == resolved_model
    )
    surface = SaasProfileSurface(
        profile_name=resolved_name,
        scan_model_id=resolved_model,
        document_type=document_type,
        configurations=(),
        review_unclear_folder=DEFAULT_SAAS_REVIEW_FOLDER,
        default_filename_pattern=DEFAULT_SAAS_FILENAME_PATTERN,
        notes="",
    )
    violations = find_private_saas_default_violations(surface.to_dict())
    if violations:
        raise RuntimeError(
            "Blank SaaS profile contains forbidden private defaults: "
            + ", ".join(violations)
        )
    return surface


def saas_profile_editor_fields() -> tuple[SaasProfileEditorField, ...]:
    """UI-v2 field contract for Block A (Profile/Configuration Model Surface)."""

    return (
        SaasProfileEditorField(
            key="profile_name",
            label="Profilname",
            kind="text",
            required=True,
            help_text="Nutzerdefinierter Name ohne private Produktdefaults.",
        ),
        SaasProfileEditorField(
            key="scan_model_id",
            label="Aktives Scanmodell",
            kind="scan_model_choice",
            required=True,
            help_text="Generisches Erkennungsmodell (z. B. Rechnungen).",
        ),
        SaasProfileEditorField(
            key="document_type",
            label="Dokumenttyp",
            kind="text",
            required=True,
        ),
        SaasProfileEditorField(
            key="matching_conditions",
            label="Matching Conditions",
            kind="condition_list",
            help_text="Nutzerregeln je Konfiguration; leer im Blank-Profil.",
        ),
        SaasProfileEditorField(
            key="destination_category",
            label="Zielkategorie",
            kind="text",
            help_text="Frei wählbar; keine ai/ep/amex-Defaults.",
        ),
        SaasProfileEditorField(
            key="destination_folder",
            label="Zielordner",
            kind="folder_path",
            help_text="Leer bis der Nutzer einen Pfad setzt.",
        ),
        SaasProfileEditorField(
            key="filename_pattern",
            label="Dateinamensmuster",
            kind="filename_pattern",
            help_text="Generisches Muster ohne SOMAA-spezifische Tokens.",
        ),
        SaasProfileEditorField(
            key="review_rule",
            label="Review-Regel",
            kind="review_rule_choice",
            help_text="Standard: unklar bei Nicht-Treffer.",
        ),
        SaasProfileEditorField(
            key="payment_hint",
            label="Zahlungs-/Kontierungshinweis",
            kind="text",
            help_text="Optional; nie mit privaten Kartenendungen vorbelegen.",
        ),
    )


def product_stream_boundary() -> SaasProductBoundary:
    return SaasProductBoundary()


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_strings(nested)
        return
    if isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _iter_strings(nested)


def find_private_saas_default_violations(payload: Mapping[str, Any] | SaasProfileSurface) -> list[str]:
    """Return human-readable violations if private markers leak into SaaS defaults."""

    data = payload.to_dict() if isinstance(payload, SaasProfileSurface) else dict(payload)
    violations: list[str] = []

    for text in _iter_strings(data):
        for marker in FORBIDDEN_PRIVATE_DEFAULT_MARKERS:
            if marker in text:
                violations.append(f"marker:{marker}")

    for key in ("destination_category", "review_unclear_folder"):
        raw = data.get(key)
        if isinstance(raw, str) and raw.strip().lower() in FORBIDDEN_PRIVATE_CATEGORY_DEFAULTS:
            violations.append(f"category_default:{raw.strip().lower()}")

    for config in data.get("configurations") or []:
        if not isinstance(config, Mapping):
            continue
        for key in ("destination_category", "destination_folder", "payment_hint"):
            raw = config.get(key)
            if isinstance(raw, str) and raw.strip().lower() in FORBIDDEN_PRIVATE_CATEGORY_DEFAULTS:
                violations.append(f"config_{key}:{raw.strip().lower()}")
            if isinstance(raw, str):
                for marker in FORBIDDEN_PRIVATE_DEFAULT_MARKERS:
                    if marker in raw:
                        violations.append(f"config_marker:{marker}")

    # Stable unique order
    seen: set[str] = set()
    ordered: list[str] = []
    for item in violations:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def assert_saas_defaults_are_generic(payload: Mapping[str, Any] | SaasProfileSurface) -> None:
    violations = find_private_saas_default_violations(payload)
    if violations:
        raise AssertionError(
            "SaaS-Defaults enthalten private Tenant-Werte: " + ", ".join(violations)
        )


def blank_saas_profile_as_dict(
    *,
    profile_name: str = DEFAULT_SAAS_PROFILE_NAME,
    scan_model_id: str = DEFAULT_SAAS_SCAN_MODEL_ID,
) -> dict[str, Any]:
    surface = build_blank_saas_profile(profile_name=profile_name, scan_model_id=scan_model_id)
    payload = surface.to_dict()
    assert_saas_defaults_are_generic(payload)
    return payload


def editor_field_keys() -> tuple[str, ...]:
    return tuple(field.key for field in saas_profile_editor_fields())
