from __future__ import annotations

import json
import os
from pathlib import Path

from invoice_tool.models import (
    AccountRule,
    AppConfig,
    ArchiveRules,
    BusinessContextRule,
    ClassificationRules,
    DuplicateHandlingRules,
    DocumentKeywordRule,
    DocumentRules,
    FilenameField,
    FilenameSchema,
    InvoiceFallbacks,
    FinalAssignmentRule,
    OfficeRules,
    OutputRouteRule,
    PaymentDetectionRule,
    ProcessingPreset,
    PriorityRouteRule,
    RoutingRules,
    SupplierCleaningRules,
    StreetRule,
)


class ConfigError(RuntimeError):
    pass


def _require_string(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Konfigurationswert '{key}' fehlt oder ist ungültig.")
    return value


def _require_bool(data: dict, key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ConfigError(f"Konfigurationswert '{key}' fehlt oder ist kein Bool.")
    return value


def _resolve_path(raw_path: str, *, base_dir: Path) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(raw_path))
    path = Path(expanded)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def load_app_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        raise ConfigError(f"Konfigurationsdatei fehlt: {config_path}")

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Konfigurationsdatei ist kein gueltiges JSON: {exc}") from exc

    base_dir = config_path.parent.resolve()
    eingangsordner = _resolve_path(_require_string(raw, "eingangsordner"), base_dir=base_dir)
    ausgangsordner = _resolve_path(_require_string(raw, "ausgangsordner"), base_dir=base_dir)
    api_key_pfad = _resolve_path(_require_string(raw, "api_key_pfad"), base_dir=base_dir)
    regeln_datei = _resolve_path(_require_string(raw, "regeln_datei"), base_dir=base_dir)
    archiv_aktiv = _require_bool(raw, "archiv_aktiv")

    if not eingangsordner.exists() or not eingangsordner.is_dir():
        raise ConfigError(
            f"Eingangsordner existiert nicht oder ist kein Verzeichnis: {eingangsordner}"
        )

    if not archiv_aktiv:
        raise ConfigError(
            "archiv_aktiv muss aktuell auf true stehen, da die Archivierung in dieser Version verpflichtend ist."
        )

    if not regeln_datei.exists():
        raise ConfigError(f"Regeldatei fehlt: {regeln_datei}")

    return AppConfig(
        config_path=config_path.resolve(),
        eingangsordner=eingangsordner,
        ausgangsordner=ausgangsordner,
        api_key_pfad=api_key_pfad,
        archiv_aktiv=archiv_aktiv,
        regeln_datei=regeln_datei,
        openai_model=str(raw.get("openai_model", "gpt-4.1-mini")),
        stale_lock_seconds=int(raw.get("stale_lock_seconds", 21600)),
        runtime_ordner=_resolve_path(str(raw.get("runtime_ordner", "./runtime")), base_dir=base_dir),
        log_ordner=_resolve_path(str(raw.get("log_ordner", "./logs")), base_dir=base_dir),
        aktives_preset=raw.get("aktives_preset"),
        zielgroesse_kb=int(raw.get("zielgroesse_kb", 200)),
    )


def load_office_rules(rules_path: Path, active_preset_override: str | None = None) -> OfficeRules:
    try:
        raw = json.loads(rules_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Regeldatei ist kein gueltiges JSON: {exc}") from exc

    presets_raw = raw.get("presets")
    if not isinstance(presets_raw, dict) or not presets_raw:
        raise ConfigError("Regeldatei enthaelt keine gueltigen 'presets'.")

    active_preset = active_preset_override or raw.get("active_preset")
    if not isinstance(active_preset, str) or active_preset not in presets_raw:
        raise ConfigError("Aktives Preset fehlt oder ist in der Regeldatei ungueltig.")

    base_dir = rules_path.parent.resolve()
    presets: dict[str, ProcessingPreset] = {}
    for preset_key, preset_raw in presets_raw.items():
        if not isinstance(preset_raw, dict):
            raise ConfigError(f"Preset '{preset_key}' ist ungueltig.")
        presets[preset_key] = _parse_preset(preset_key, preset_raw, base_dir)

    return OfficeRules(active_preset=active_preset, presets=presets)


# Routing sections that the Profile Compiler may safely replace.
# All other sections remain unchanged from the base rules.
_MERGEABLE_ROUTING_SECTIONS: tuple[str, ...] = (
    "strassen",
    "prioritaetsregeln",
    "konten",
)


def merge_rules_dicts(base: dict, patch: dict) -> dict:
    """Merge generated profile rules into a base rules dict.

    MVP scope: only presets[*].routing.strassen and
    presets[*].routing.prioritaetsregeln may be replaced.
    All other sections remain unchanged from base.

    Neither base nor patch is mutated. Returns a deep copy of base
    with the patch applied.
    """
    import copy as _copy  # local import to avoid module-level side effects

    merged = _copy.deepcopy(base)
    patch_presets = patch.get("presets") or {}

    for preset_key, patch_preset in patch_presets.items():
        if not isinstance(patch_preset, dict):
            continue
        base_preset = merged.get("presets", {}).get(preset_key)
        if not isinstance(base_preset, dict):
            continue  # only patch presets that exist in base

        patch_routing = patch_preset.get("routing") or {}
        base_routing = base_preset.setdefault("routing", {})

        for section in _MERGEABLE_ROUTING_SECTIONS:
            if section in patch_routing:
                base_routing[section] = _copy.deepcopy(patch_routing[section])

    return merged


def load_office_rules_from_dict(
    rules_dict: dict,
    base_dir: Path,
    active_preset_override: str | None = None,
) -> OfficeRules:
    """Build an OfficeRules instance from an in-memory dict.

    Identical parsing behaviour to load_office_rules(), but accepts an
    already-loaded dict instead of a file path. No file I/O is performed.
    Used to apply runtime rules without touching office_rules.json.

    The dict may contain a top-level "_meta" key (written for traceability);
    it is silently ignored during parsing.
    """
    presets_raw = rules_dict.get("presets")
    if not isinstance(presets_raw, dict) or not presets_raw:
        raise ConfigError("Regeldatei enthaelt keine gueltigen 'presets'.")

    active_preset = active_preset_override or rules_dict.get("active_preset")
    if not isinstance(active_preset, str) or active_preset not in presets_raw:
        raise ConfigError("Aktives Preset fehlt oder ist ungueltig.")

    presets: dict[str, ProcessingPreset] = {}
    for preset_key, preset_raw in presets_raw.items():
        if not isinstance(preset_raw, dict):
            raise ConfigError(f"Preset '{preset_key}' ist ungueltig.")
        presets[preset_key] = _parse_preset(preset_key, preset_raw, base_dir)

    return OfficeRules(active_preset=active_preset, presets=presets)


def _parse_preset(preset_key: str, preset_raw: dict, base_dir: Path) -> ProcessingPreset:
    schema_raw = preset_raw.get("dateiname_schema")
    if not isinstance(schema_raw, dict):
        raise ConfigError(f"Preset '{preset_key}' enthaelt kein gueltiges 'dateiname_schema'.")

    fields: list[FilenameField] = []
    for item in schema_raw.get("felder", []):
        if not isinstance(item, dict):
            raise ConfigError("Dateinamenschema enthaelt einen ungueltigen Feldeintrag.")
        fields.append(
            FilenameField(
                typ=str(item.get("typ", "")),
                aktiv=bool(item.get("aktiv", True)),
                quelle=item.get("quelle"),
                wert=item.get("wert"),
                format=item.get("format"),
            )
        )

    routing_raw = preset_raw.get("routing")
    if not isinstance(routing_raw, dict):
        raise ConfigError(f"Preset '{preset_key}' enthaelt kein gueltiges 'routing'.")

    account_rules: list[AccountRule] = []
    for item in routing_raw.get("konten", []):
        if not isinstance(item, dict):
            raise ConfigError("Routing-Regeln enthalten einen ungueltigen Kontoeintrag.")
        account_rules.append(
            AccountRule(
                name=str(item.get("name", item.get("konto", ""))),
                konto=item.get("konto"),
                payment_field=item.get("payment_field"),
                art_override=item.get("art_override"),
                karten_endungen=tuple(item.get("karten_endungen", [])),
                apple_pay_endungen=tuple(item.get("apple_pay_endungen", [])),
                anbieter_hinweise=tuple(item.get("anbieter_hinweise", [])),
                zuweisungs_hinweise=tuple(item.get("zuweisungs_hinweise", [])),
                iban_endungen=tuple(item.get("iban_endungen", [])),
            )
        )

    street_rules: list[StreetRule] = []
    for item in routing_raw.get("strassen", []):
        if not isinstance(item, dict):
            raise ConfigError("Strassenregeln enthalten einen ungueltigen Eintrag.")
        street_rules.append(
            StreetRule(
                key=str(item.get("key", "")),
                varianten=tuple(item.get("varianten", [])),
                fuzzy_threshold=float(item.get("fuzzy_threshold", 0.84)),
                art=item.get("art") or None,
            )
        )

    archive_raw = preset_raw.get("archivierung")
    if not isinstance(archive_raw, dict):
        raise ConfigError(f"Preset '{preset_key}' enthaelt keine gueltige 'archivierung'.")

    classification_raw = preset_raw.get("classification")
    if not isinstance(classification_raw, dict):
        raise ConfigError(f"Preset '{preset_key}' enthaelt keine gueltige 'classification'.")

    documents_raw = preset_raw.get("dokumente")
    if not isinstance(documents_raw, dict):
        raise ConfigError(f"Preset '{preset_key}' enthaelt keine gueltigen 'dokumente'.")

    naming_raw = documents_raw.get("dateiname")
    if not isinstance(naming_raw, dict):
        raise ConfigError(f"Preset '{preset_key}' enthaelt keine gueltigen Dokument-Dateinamensregeln.")

    document_keywords: list[DocumentKeywordRule] = []
    for item in naming_raw.get("schlagwoerter", []):
        if not isinstance(item, dict):
            raise ConfigError("Dokument-Schlagwortregeln enthalten einen ungueltigen Eintrag.")
        document_keywords.append(
            DocumentKeywordRule(
                name=str(item.get("name", "")),
                hinweise=tuple(item.get("hinweise", [])),
            )
        )

    duplicate_raw = preset_raw.get("duplicate_handling")
    if not isinstance(duplicate_raw, dict):
        raise ConfigError(f"Preset '{preset_key}' enthaelt kein gueltiges 'duplicate_handling'.")

    supplier_cleaning_raw = preset_raw.get("supplier_cleaning")
    if not isinstance(supplier_cleaning_raw, dict):
        raise ConfigError(f"Preset '{preset_key}' enthaelt keine gueltige 'supplier_cleaning'.")

    return ProcessingPreset(
        key=preset_key,
        filename_schema=FilenameSchema(
            separator=str(schema_raw.get("separator", "_")),
            max_laenge=int(schema_raw.get("max_laenge", 50)),
            erweiterung=str(schema_raw.get("erweiterung", ".pdf")),
            felder=tuple(fields),
        ),
        invoice_fallbacks=InvoiceFallbacks(
            invoice_date=preset_raw.get("invoice_fallbacks", {}).get("invoice_date"),
            supplier=preset_raw.get("invoice_fallbacks", {}).get("supplier"),
            amount=preset_raw.get("invoice_fallbacks", {}).get("amount"),
            konto=preset_raw.get("invoice_fallbacks", {}).get("konto"),
        ),
        classification=ClassificationRules(
            invoice_keywords=tuple(classification_raw.get("invoice_keywords", [])),
            document_keywords=tuple(classification_raw.get("document_keywords", [])),
            internal_invoice_keywords=tuple(
                classification_raw.get("internal_invoice_keywords", [])
            ),
            invoice_like_indicators=tuple(classification_raw.get("invoice_like_indicators", [])),
            invoice_like_threshold=int(classification_raw.get("invoice_like_threshold", 3)),
        ),
        routing=RoutingRules(
            unklar_konto=str(routing_raw.get("unklar_konto", "unklar")),
            default_art=str(routing_raw.get("default_art", "private")),
            default_payment_method=str(routing_raw.get("default_payment_method", "unknown")),
            default_payment_field=str(routing_raw.get("default_payment_field", "unklar")),
            default_zielordner=str(routing_raw.get("default_zielordner", "unklar")),
            default_status=str(routing_raw.get("default_status", "unklar")),
            zielordner=dict(routing_raw.get("zielordner", {})),
            strassen=tuple(street_rules),
            prioritaetsregeln=tuple(_parse_priority_rules(routing_raw.get("prioritaetsregeln", []))),
            business_context_rules=tuple(
                _parse_business_context_rules(routing_raw.get("business_context_rules", []))
            ),
            payment_detection_rules=tuple(
                _parse_payment_detection_rules(routing_raw.get("payment_detection_rules", []))
            ),
            final_assignment_rules=tuple(
                _parse_final_assignment_rules(routing_raw.get("final_assignment_rules", []))
            ),
            output_route_rules=tuple(
                _parse_output_route_rules(routing_raw.get("output_route_rules", []))
            ),
            konten=tuple(account_rules),
        ),
        archivierung=ArchiveRules(
            basis_ordnername=str(archive_raw.get("basis_ordnername", "archiv")),
            lauf_ordner_suffix=str(archive_raw.get("lauf_ordner_suffix", "archiv")),
        ),
        dokumente=DocumentRules(
            basis_pfad=_resolve_path(
                _require_string(documents_raw, "basis_pfad"),
                base_dir=base_dir,
            ),
            prefix=str(naming_raw.get("prefix", "d")),
            suffix_placeholder=str(naming_raw.get("suffix_placeholder", "vn")),
            fallback_name=str(naming_raw.get("fallback_name", "unknown-document")),
            max_woerter=int(naming_raw.get("max_woerter", 5)),
            schlagwoerter=tuple(document_keywords),
        ),
        duplicate_handling=DuplicateHandlingRules(
            report_folder=str(duplicate_raw.get("report_folder", "_duplicate_reports")),
            report_extension=str(duplicate_raw.get("report_extension", ".txt")),
        ),
        supplier_cleaning=SupplierCleaningRules(
            remove_suffix_patterns=tuple(supplier_cleaning_raw.get("remove_suffix_patterns", [])),
            supplier_aliases=dict(supplier_cleaning_raw.get("supplier_aliases", {})),
        ),
    )


def _parse_priority_rules(raw_rules: list[dict]) -> list[PriorityRouteRule]:
    priority_rules: list[PriorityRouteRule] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            raise ConfigError("Prioritaetsregeln enthalten einen ungueltigen Eintrag.")
        priority_rules.append(
            PriorityRouteRule(
                name=str(item.get("name", "")),
                text_all=tuple(item.get("text_all", [])),
                text_any=tuple(item.get("text_any", [])),
                provider_any=tuple(item.get("provider_any", [])),
                street_any=tuple(item.get("street_any", [])),
                text_none_any=tuple(item.get("text_none_any", [])),
                require_no_clear_payment=bool(item.get("require_no_clear_payment", False)),
                zielordner=str(item.get("zielordner", "")),
                art=str(item.get("art", "")),
                status=str(item.get("status", "processed")),
            )
        )
    return priority_rules


def _parse_business_context_rules(raw_rules: list[dict]) -> list[BusinessContextRule]:
    rules: list[BusinessContextRule] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            raise ConfigError("Business-Context-Regeln enthalten einen ungueltigen Eintrag.")
        rules.append(
            BusinessContextRule(
                name=str(item.get("name", "")),
                text_all=tuple(item.get("text_all", [])),
                text_any=tuple(item.get("text_any", [])),
                art=str(item.get("art", "")),
                match_source=str(item.get("match_source", "enriched_text")),
            )
        )
    return rules


def _parse_payment_detection_rules(raw_rules: list[dict]) -> list[PaymentDetectionRule]:
    rules: list[PaymentDetectionRule] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            raise ConfigError("Payment-Detection-Regeln enthalten einen ungueltigen Eintrag.")
        rules.append(
            PaymentDetectionRule(
                name=str(item.get("name", "")),
                text_all=tuple(item.get("text_all", [])),
                text_any=tuple(item.get("text_any", [])),
                payment_method=str(item.get("payment_method", "")),
                explicit=bool(item.get("explicit", True)),
            )
        )
    return rules


def _parse_final_assignment_rules(raw_rules: list[dict]) -> list[FinalAssignmentRule]:
    rules: list[FinalAssignmentRule] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            raise ConfigError("Final-Assignment-Regeln enthalten einen ungueltigen Eintrag.")
        rules.append(
            FinalAssignmentRule(
                name=str(item.get("name", "")),
                payment_method_any=tuple(item.get("payment_method_any", [])),
                art_any=tuple(item.get("art_any", [])),
                account_payment_field_any=tuple(item.get("account_payment_field_any", [])),
                account_konto_any=tuple(item.get("account_konto_any", [])),
                output_art=item.get("output_art"),
                output_konto=item.get("output_konto"),
                output_payment_field=item.get("output_payment_field"),
                use_account_art=bool(item.get("use_account_art", False)),
                use_account_konto=bool(item.get("use_account_konto", False)),
                use_account_payment_field=bool(item.get("use_account_payment_field", False)),
            )
        )
    return rules


def _parse_output_route_rules(raw_rules: list[dict]) -> list[OutputRouteRule]:
    rules: list[OutputRouteRule] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            raise ConfigError("Output-Route-Regeln enthalten einen ungueltigen Eintrag.")
        rules.append(
            OutputRouteRule(
                name=str(item.get("name", "")),
                art_any=tuple(item.get("art_any", [])),
                payment_field_any=tuple(item.get("payment_field_any", [])),
                zielordner=str(item.get("zielordner", "")),
                status=str(item.get("status", "processed")),
            )
        )
    return rules
