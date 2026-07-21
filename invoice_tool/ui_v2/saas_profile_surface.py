"""UI-v2 adapter: generic SaaS profile surface bound to saas_product_model.

Create/edit defaults for the external SaaS UI come from build_blank_saas_profile().
No Hadi/SOMAA/AMEX-1005/EP tenant defaults are introduced here.
Processing is not started from this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from invoice_tool.saas_product_model import (
    CLASSIFICATION_POLICY_UI_TEXTS,
    DEFAULT_SAAS_FILENAME_PATTERN,
    DEFAULT_SAAS_PROFILE_NAME,
    DEFAULT_SAAS_REVIEW_FOLDER,
    ClassificationPolicy,
    SaasConfigurationSurface,
    SaasProfileEditorField,
    SaasProfileSurface,
    assert_saas_defaults_are_generic,
    blank_saas_profile_as_dict,
    build_blank_saas_profile,
    classification_policy_ui_texts,
    find_private_saas_default_violations,
    list_generic_scan_models,
    saas_profile_editor_fields,
)
from invoice_tool.ui_v2.draft_models import ProfileDraftVM

# Explicit UI copy for the SaaS profile/configuration surface (Block wiring).
SAAS_SURFACE_UI_LABELS: dict[str, str] = {
    "new_profile": "Neues Profil",
    "scan_model": "Scanmodell wählen",
    "document_type": "Dokumenttyp",
    "matching_conditions": "Matching-Bedingungen",
    "destination": "Ziel",
    "filename_pattern": "Dateinamensmuster",
    "review_rule": "Review-Regel",
    "payment_hint": "Zahlung/Kontierung optional",
    "classification_policy": "Klassifikations-Policy",
    "payment_evidence": "Zahlungsweg-Erkennung",
    "invoice_direction": "Rechnungsrichtung erkennen",
    "document_type_detection": "Dokumenttyp-Erkennung",
    "mixed_address": "Gemischte geschäftliche/private Adresssignale",
    "address_policy": "Rechnungsadresse und Lieferadresse",
    "business_document_policy": "Geschäftliche Nicht-Rechnungs-Belege",
    "invoice_detection_policy": "Rechnungs-Erkennung",
    "payment_evidence_policy": "Zahlungsweg-Erkennung",
    "business_assignment_policy": "Geschäftliche Zuordnung",
    "software_ai_tools": "Software- und AI-Tools erkennen",
}

DEFAULT_SAAS_REVIEW_RULE_LABEL = "Unklar bei Nicht-Treffer"
DEFAULT_SAAS_CONFIG_NAME = "Neue Konfiguration"
GENERIC_CONFIG_NAME_HINT = "z. B. Lieferant Hauptkonto"

# Additional private-leak markers checked on UI surface payloads (beyond model guard).
_EXTRA_PRIVATE_UI_MARKERS: tuple[str, ...] = (
    "SOMAA",
    "Hadi",
    "AMEX-1005",
    "EP",
    "Bismarck",
    "97368",
    "DE189",
    "USt-IdNr",
    "UStId",
)


@dataclass(frozen=True)
class SaasSurfaceFieldDisplay:
    """One field row for the UI-v2 profile/configuration surface."""

    key: str
    label: str
    value: str
    kind: str
    required: bool = False
    help_text: str = ""
    editable: bool = True


@dataclass(frozen=True)
class SaasProfileSurfaceVM:
    """Presenter VM for create/edit defaults and surface display."""

    profile_name: str
    scan_model_id: str
    document_type: str
    matching_conditions_summary: str
    destination_category: str
    destination_folder: str
    filename_pattern: str
    review_rule: str
    payment_hint: str
    review_unclear_folder: str
    notes: str
    scan_model_options: tuple[dict[str, str], ...]
    fields: tuple[SaasSurfaceFieldDisplay, ...]
    review_hints: tuple[str, ...]
    ui_labels: Mapping[str, str]
    classification_policy: ClassificationPolicy = field(default_factory=ClassificationPolicy)
    classification_policy_texts: tuple[str, ...] = CLASSIFICATION_POLICY_UI_TEXTS


@dataclass(frozen=True)
class SaasConfigurationCreateDefaultsVM:
    """Generic create defaults for a configuration inside a SaaS profile."""

    name: str
    active: bool
    document_type: str
    matching_conditions_summary: str
    destination_category: str
    destination_folder: str
    filename_pattern: str
    review_rule: str
    payment_hint: str
    name_hint: str


def load_blank_saas_profile() -> SaasProfileSurface:
    """Load the canonical blank SaaS profile (guarded against private defaults)."""

    surface = build_blank_saas_profile()
    assert_saas_defaults_are_generic(surface)
    return surface


def blank_profile_draft() -> ProfileDraftVM:
    """ProfileDraftVM for UI-v2 create from generic SaaS defaults.

    Name starts empty so the editor requires an explicit user value
    (surface label/default remains DEFAULT_SAAS_PROFILE_NAME).
    """

    blank = load_blank_saas_profile()
    return ProfileDraftVM(
        name="",
        scan_model_id=blank.scan_model_id,
        is_new=True,
    )


def blank_configuration_create_defaults(
    *,
    document_type: str | None = None,
) -> SaasConfigurationCreateDefaultsVM:
    """Empty/generic configuration create defaults (no private tenant values)."""

    blank = load_blank_saas_profile()
    config = SaasConfigurationSurface(
        name="",
        active=True,
        document_type=document_type or blank.document_type,
        matching_conditions=(),
        destination_category="",
        destination_folder="",
        filename_pattern=blank.default_filename_pattern or DEFAULT_SAAS_FILENAME_PATTERN,
        review_rule="unclear_on_no_match",
        payment_hint="",
    )
    payload = {
        "profile_name": blank.profile_name,
        "scan_model_id": blank.scan_model_id,
        "document_type": blank.document_type,
        "configurations": [config.to_dict()],
        "review_unclear_folder": blank.review_unclear_folder,
        "default_filename_pattern": blank.default_filename_pattern,
        "notes": "",
    }
    assert_saas_defaults_are_generic(payload)
    return SaasConfigurationCreateDefaultsVM(
        name=config.name,
        active=config.active,
        document_type=config.document_type,
        matching_conditions_summary=_matching_summary(config),
        destination_category=config.destination_category,
        destination_folder=config.destination_folder,
        filename_pattern=config.filename_pattern,
        review_rule=DEFAULT_SAAS_REVIEW_RULE_LABEL,
        payment_hint=config.payment_hint,
        name_hint=GENERIC_CONFIG_NAME_HINT,
    )


def build_saas_profile_surface_vm(
    surface: SaasProfileSurface | None = None,
) -> SaasProfileSurfaceVM:
    """Build UI display data from a blank or provided SaaS profile surface."""

    profile = surface or load_blank_saas_profile()
    assert_saas_defaults_are_generic(profile)
    primary_config = profile.configurations[0] if profile.configurations else None
    matching_summary = _matching_summary(primary_config) if primary_config else "Keine Bedingungen (leer)"
    destination_category = primary_config.destination_category if primary_config else ""
    destination_folder = primary_config.destination_folder if primary_config else ""
    filename_pattern = (
        primary_config.filename_pattern
        if primary_config and primary_config.filename_pattern
        else profile.default_filename_pattern
    )
    payment_hint = primary_config.payment_hint if primary_config else ""
    review_rule = DEFAULT_SAAS_REVIEW_RULE_LABEL

    fields = _surface_fields(
        profile_name=profile.profile_name,
        scan_model_id=profile.scan_model_id,
        document_type=profile.document_type,
        matching_summary=matching_summary,
        destination_category=destination_category,
        destination_folder=destination_folder,
        filename_pattern=filename_pattern,
        review_rule=review_rule,
        payment_hint=payment_hint,
    )
    return SaasProfileSurfaceVM(
        profile_name=profile.profile_name,
        scan_model_id=profile.scan_model_id,
        document_type=profile.document_type,
        matching_conditions_summary=matching_summary,
        destination_category=destination_category,
        destination_folder=destination_folder,
        filename_pattern=filename_pattern,
        review_rule=review_rule,
        payment_hint=payment_hint,
        review_unclear_folder=profile.review_unclear_folder or DEFAULT_SAAS_REVIEW_FOLDER,
        notes=profile.notes,
        scan_model_options=list_generic_scan_models(),
        fields=fields,
        review_hints=saas_surface_review_hints(profile),
        ui_labels=dict(SAAS_SURFACE_UI_LABELS),
        classification_policy=profile.classification_policy,
        classification_policy_texts=classification_policy_ui_texts(),
    )


def saas_surface_review_hints(surface: SaasProfileSurface | None = None) -> tuple[str, ...]:
    """Validation/review hints derived from the generic SaaS model."""

    profile = surface or load_blank_saas_profile()
    hints = [
        f'Profilname-Default: „{DEFAULT_SAAS_PROFILE_NAME}" (frei änderbar).',
        "Scanmodell bestimmt Dokumenttyp und verfügbare Erkennungsfelder.",
        "Matching-Bedingungen sind je Konfiguration leer, bis der Nutzer Regeln setzt.",
        "Zielkategorie und Zielordner bleiben leer — keine ai/ep/amex-Vorbelegung.",
        f'Dateinamensmuster-Default: {profile.default_filename_pattern or DEFAULT_SAAS_FILENAME_PATTERN}',
        f'Review: nicht zugeordnete Dokumente → Ordner „{profile.review_unclear_folder}".',
        "Zahlungs-/Kontierungshinweis ist optional und nie mit privaten Kartenwerten vorbelegt.",
        "Zahlungsweg-Erkennung: Lieferanten-IBAN/BIC nicht als Zahlungsweg werten.",
        "Apple Pay ohne Karten-/Konto-Endung zur Prüfung.",
        "Rechnungsrichtung erkennen: Ausgangsrechnung nicht als Eingangsrechnung.",
        "Dokumenttyp-Erkennung: Buchhaltungsauswertungen zur Prüfung.",
        "Gemischte geschäftliche/private Adresssignale zur Prüfung.",
        "Rechnungsadresse vor Lieferadresse priorisieren.",
        "Geschäftliche Lieferadresse allein reicht nicht für geschäftliche Zuordnung.",
        "Abweichende private Rechnungsadresse zur Prüfung.",
        "Gemischte Rechnungs-/Lieferadresssignale zur Prüfung.",
        "Bestellbestätigungen von Rechnungen unterscheiden.",
        "Geschäftliche Bestelldokumente fachlich zuordnen.",
        "Rechnungsadresse kann AI/Business-Kontext setzen.",
        "Nicht buchbare Geschäftsdokumente zur Prüfung.",
        "Zahlungsmethode auch bei Nicht-Rechnungen erkennen.",
        "Starke Rechnungsindikatoren vor Format-/Dokumentphrasen.",
        "Format-Verfügbarkeitshinweise sind kein Dokumenttyp.",
        "Dateiname ist keine Beweisquelle.",
        "Unspezifische Kreditkarte ohne Kennung zur Prüfung.",
        "Kartenzahlung erfordert bekannte Referenz.",
        "Geschäftliche Rechnungsadresse setzt Business-Kontext.",
        "Mehrdeutige Positionen überschreiben keine Rechnungsadresse.",
        "Organisationskennungen sind profilkonfiguriert.",
        "Verarbeitung wird von dieser Oberfläche nicht gestartet.",
        "Kein Cloud-/Mandantenbetrieb in dieser lokalen Oberfläche.",
    ]
    return tuple(hints)


def editor_fields_for_ui() -> tuple[SaasProfileEditorField, ...]:
    return saas_profile_editor_fields()


def expected_surface_field_keys() -> tuple[str, ...]:
    return (
        "profile_name",
        "scan_model_id",
        "document_type",
        "matching_conditions",
        "destination",
        "filename_pattern",
        "review_rule",
        "payment_hint",
    )


def surface_payload_as_dict(vm: SaasProfileSurfaceVM | None = None) -> dict[str, Any]:
    """Serialize surface VM values for display/tests (not educational help texts)."""

    if vm is None:
        blank = blank_saas_profile_as_dict()
        display = build_saas_profile_surface_vm()
        return {
            **blank,
            "matching_conditions_summary": display.matching_conditions_summary,
            "destination_category": display.destination_category,
            "destination_folder": display.destination_folder,
            "filename_pattern": display.filename_pattern,
            "review_rule": display.review_rule,
            "payment_hint": display.payment_hint,
            "classification_policy": display.classification_policy.to_dict(),
            "classification_policy_texts": list(display.classification_policy_texts),
            "ui_labels": dict(display.ui_labels),
            "field_values": {field.key: field.value for field in display.fields},
            "field_labels": {field.key: field.label for field in display.fields},
        }
    return {
        "profile_name": vm.profile_name,
        "scan_model_id": vm.scan_model_id,
        "document_type": vm.document_type,
        "matching_conditions_summary": vm.matching_conditions_summary,
        "destination_category": vm.destination_category,
        "destination_folder": vm.destination_folder,
        "filename_pattern": vm.filename_pattern,
        "review_rule": vm.review_rule,
        "payment_hint": vm.payment_hint,
        "review_unclear_folder": vm.review_unclear_folder,
        "notes": vm.notes,
        "configurations": [],
        "default_filename_pattern": vm.filename_pattern,
        "classification_policy": vm.classification_policy.to_dict(),
        "classification_policy_texts": list(vm.classification_policy_texts),
        "ui_labels": dict(vm.ui_labels),
        "field_values": {field.key: field.value for field in vm.fields},
        "field_labels": {field.key: field.label for field in vm.fields},
    }


def find_private_ui_surface_violations(payload: Mapping[str, Any] | SaasProfileSurfaceVM) -> list[str]:
    """Check value-bearing surface data only (help texts may mention forbidden markers as docs)."""

    data = surface_payload_as_dict(payload) if isinstance(payload, SaasProfileSurfaceVM) else dict(payload)
    model_slice = {
        "profile_name": data.get("profile_name", ""),
        "scan_model_id": data.get("scan_model_id", ""),
        "document_type": data.get("document_type", ""),
        "configurations": data.get("configurations") or [],
        "review_unclear_folder": data.get("review_unclear_folder", DEFAULT_SAAS_REVIEW_FOLDER),
        "default_filename_pattern": data.get("default_filename_pattern")
        or data.get("filename_pattern")
        or "",
        "notes": data.get("notes", ""),
        "destination_category": data.get("destination_category", ""),
        "destination_folder": data.get("destination_folder", ""),
        "payment_hint": data.get("payment_hint", ""),
        "matching_conditions_summary": data.get("matching_conditions_summary", ""),
        "review_rule": data.get("review_rule", ""),
        "ui_labels": data.get("ui_labels") or {},
        "field_values": data.get("field_values") or {},
        "field_labels": data.get("field_labels") or {},
    }
    violations = list(find_private_saas_default_violations(model_slice))
    blob = str(model_slice)
    for marker in _EXTRA_PRIVATE_UI_MARKERS:
        if marker in blob:
            violations.append(f"ui_marker:{marker}")
    seen: set[str] = set()
    ordered: list[str] = []
    for item in violations:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def assert_ui_surface_defaults_are_generic(
    payload: Mapping[str, Any] | SaasProfileSurfaceVM | None = None,
) -> None:
    if payload is None:
        data: Mapping[str, Any] | SaasProfileSurfaceVM = surface_payload_as_dict()
    else:
        data = payload
    violations = find_private_ui_surface_violations(data)
    if violations:
        raise AssertionError(
            "UI-v2 SaaS-Surface enthält private Defaults: " + ", ".join(violations)
        )


def _matching_summary(config: SaasConfigurationSurface | None) -> str:
    if config is None or not config.matching_conditions:
        return "Keine Bedingungen (leer)"
    parts: list[str] = []
    for condition in config.matching_conditions:
        values = ", ".join(condition.values) if condition.values else "—"
        parts.append(f"{condition.feature_key} {condition.operator} {values}")
    return "; ".join(parts)


def _surface_fields(
    *,
    profile_name: str,
    scan_model_id: str,
    document_type: str,
    matching_summary: str,
    destination_category: str,
    destination_folder: str,
    filename_pattern: str,
    review_rule: str,
    payment_hint: str,
) -> tuple[SaasSurfaceFieldDisplay, ...]:
    labels = SAAS_SURFACE_UI_LABELS
    destination_value = " / ".join(
        part for part in (destination_category, destination_folder) if part
    ) or "—"
    model_fields = {field.key: field for field in saas_profile_editor_fields()}

    def _help(key: str) -> str:
        field = model_fields.get(key)
        return field.help_text if field else ""

    return (
        SaasSurfaceFieldDisplay(
            key="profile_name",
            label=labels["new_profile"] if not profile_name else "Profilname",
            value=profile_name,
            kind="text",
            required=True,
            help_text=_help("profile_name"),
        ),
        SaasSurfaceFieldDisplay(
            key="scan_model_id",
            label=labels["scan_model"],
            value=scan_model_id,
            kind="scan_model_choice",
            required=True,
            help_text=_help("scan_model_id"),
        ),
        SaasSurfaceFieldDisplay(
            key="document_type",
            label=labels["document_type"],
            value=document_type,
            kind="text",
            required=True,
            help_text=_help("document_type"),
        ),
        SaasSurfaceFieldDisplay(
            key="matching_conditions",
            label=labels["matching_conditions"],
            value=matching_summary,
            kind="condition_list",
            help_text=_help("matching_conditions"),
        ),
        SaasSurfaceFieldDisplay(
            key="destination",
            label=labels["destination"],
            value=destination_value,
            kind="destination",
            help_text="Zielkategorie und Zielordner; leer bis der Nutzer setzt.",
        ),
        SaasSurfaceFieldDisplay(
            key="filename_pattern",
            label=labels["filename_pattern"],
            value=filename_pattern,
            kind="filename_pattern",
            help_text=_help("filename_pattern"),
        ),
        SaasSurfaceFieldDisplay(
            key="review_rule",
            label=labels["review_rule"],
            value=review_rule,
            kind="review_rule_choice",
            help_text=_help("review_rule"),
        ),
        SaasSurfaceFieldDisplay(
            key="payment_hint",
            label=labels["payment_hint"],
            value=payment_hint or "—",
            kind="text",
            required=False,
            help_text=_help("payment_hint"),
        ),
    )
