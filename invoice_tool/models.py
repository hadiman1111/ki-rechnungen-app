from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    eingangsordner: Path
    ausgangsordner: Path
    api_key_pfad: Path
    archiv_aktiv: bool
    regeln_datei: Path
    openai_model: str
    stale_lock_seconds: int
    runtime_ordner: Path
    log_ordner: Path
    aktives_preset: str | None
    zielgroesse_kb: int


@dataclass(frozen=True)
class FilenameField:
    typ: str
    aktiv: bool = True
    quelle: str | None = None
    wert: str | None = None
    format: str | None = None


@dataclass(frozen=True)
class FilenameSchema:
    separator: str
    max_laenge: int
    erweiterung: str
    felder: tuple[FilenameField, ...]


@dataclass(frozen=True)
class InvoiceFallbacks:
    invoice_date: str | None
    supplier: str | None
    amount: str | None
    konto: str | None


@dataclass(frozen=True)
class AccountRule:
    name: str
    konto: str | None = None
    payment_field: str | None = None
    art_override: str | None = None
    karten_endungen: tuple[str, ...] = ()
    apple_pay_endungen: tuple[str, ...] = ()
    anbieter_hinweise: tuple[str, ...] = ()
    zuweisungs_hinweise: tuple[str, ...] = ()
    iban_endungen: tuple[str, ...] = ()


@dataclass(frozen=True)
class StreetRule:
    key: str
    varianten: tuple[str, ...]
    fuzzy_threshold: float
    art: str | None = None


@dataclass(frozen=True)
class InvoiceRouteRule:
    konto: str
    strasse: str
    zielordner: str
    art: str
    status: str


@dataclass(frozen=True)
class PriorityRouteRule:
    name: str
    text_all: tuple[str, ...] = ()
    text_any: tuple[str, ...] = ()
    provider_any: tuple[str, ...] = ()
    street_any: tuple[str, ...] = ()
    text_none_any: tuple[str, ...] = ()
    require_no_clear_payment: bool = False
    zielordner: str = ""
    art: str = ""
    status: str = "processed"


@dataclass(frozen=True)
class ClassificationRules:
    invoice_keywords: tuple[str, ...]
    document_keywords: tuple[str, ...]
    internal_invoice_keywords: tuple[str, ...]
    invoice_like_indicators: tuple[str, ...] = ()
    invoice_like_threshold: int = 3


@dataclass(frozen=True)
class BusinessContextRule:
    name: str
    text_all: tuple[str, ...] = ()
    text_any: tuple[str, ...] = ()
    art: str = ""


@dataclass(frozen=True)
class PaymentDetectionRule:
    name: str
    text_all: tuple[str, ...] = ()
    text_any: tuple[str, ...] = ()
    payment_method: str = ""
    explicit: bool = True


@dataclass(frozen=True)
class FinalAssignmentRule:
    name: str
    payment_method_any: tuple[str, ...] = ()
    art_any: tuple[str, ...] = ()
    account_payment_field_any: tuple[str, ...] = ()
    account_konto_any: tuple[str, ...] = ()
    output_art: str | None = None
    output_konto: str | None = None
    output_payment_field: str | None = None
    use_account_art: bool = False
    use_account_konto: bool = False
    use_account_payment_field: bool = False


@dataclass(frozen=True)
class OutputRouteRule:
    name: str
    art_any: tuple[str, ...] = ()
    payment_field_any: tuple[str, ...] = ()
    zielordner: str = ""
    status: str = "processed"


@dataclass(frozen=True)
class SupplierCleaningRules:
    remove_suffix_patterns: tuple[str, ...]
    supplier_aliases: dict[str, str]


@dataclass(frozen=True)
class DuplicateHandlingRules:
    report_folder: str
    report_extension: str


@dataclass(frozen=True)
class DocumentKeywordRule:
    name: str
    hinweise: tuple[str, ...]


@dataclass(frozen=True)
class DocumentRules:
    basis_pfad: Path
    prefix: str
    suffix_placeholder: str
    fallback_name: str
    max_woerter: int
    schlagwoerter: tuple[DocumentKeywordRule, ...]


@dataclass(frozen=True)
class RoutingRules:
    unklar_konto: str
    default_art: str
    default_payment_method: str
    default_payment_field: str
    default_zielordner: str
    default_status: str
    zielordner: dict[str, str]
    strassen: tuple[StreetRule, ...]
    prioritaetsregeln: tuple[PriorityRouteRule, ...]
    business_context_rules: tuple[BusinessContextRule, ...]
    payment_detection_rules: tuple[PaymentDetectionRule, ...]
    final_assignment_rules: tuple[FinalAssignmentRule, ...]
    output_route_rules: tuple[OutputRouteRule, ...]
    konten: tuple[AccountRule, ...]


@dataclass(frozen=True)
class ArchiveRules:
    basis_ordnername: str
    lauf_ordner_suffix: str


@dataclass(frozen=True)
class ProcessingPreset:
    key: str
    filename_schema: FilenameSchema
    invoice_fallbacks: InvoiceFallbacks
    classification: ClassificationRules
    routing: RoutingRules
    archivierung: ArchiveRules
    dokumente: DocumentRules
    duplicate_handling: DuplicateHandlingRules
    supplier_cleaning: SupplierCleaningRules


@dataclass(frozen=True)
class OfficeRules:
    active_preset: str
    presets: dict[str, ProcessingPreset]

    @property
    def preset(self) -> ProcessingPreset:
        return self.presets[self.active_preset]


@dataclass
class ExtractedData:
    invoice_date_raw: str | None
    supplier_raw: str | None
    amount_raw: str | None
    invoice_number_raw: str | None = None
    document_name_raw: str | None = None
    payment_method_raw: str | None = None
    card_endings: list[str] = field(default_factory=list)
    apple_pay_endings: list[str] = field(default_factory=list)
    provider_mentions: list[str] = field(default_factory=list)
    address_fragments: list[str] = field(default_factory=list)
    context_markers: list[str] = field(default_factory=list)
    document_type_indicators: list[str] = field(default_factory=list)
    raw_text: str = ""
    source_method: str = ""
    fallback_used: bool = False


@dataclass(frozen=True)
class NormalizedInvoice:
    invoice_date: str
    supplier: str
    amount: str


@dataclass(frozen=True)
class AccountDecision:
    konto: str | None
    payment_field: str | None
    art_override: str | None
    ist_unklar: bool
    ist_widerspruechlich: bool
    begruendung: str
    matched_rule: str | None = None


@dataclass(frozen=True)
class PaymentDecision:
    payment_method: str
    explicit: bool
    begruendung: str


@dataclass(frozen=True)
class RoutingDecision:
    art: str
    zielordner: str
    status: str
    konto: str | None
    payment_field: str
    street_key: str | None
    begruendung: str


@dataclass(frozen=True)
class ClassificationDecision:
    dokumenttyp: str
    begruendung: str


@dataclass(frozen=True)
class ProcessResult:
    input_file: Path
    dokumenttyp: str
    status: str
    storage_file: Path
    archive_file: Path | None
    used_extractor: str
    fallback_used: bool
    fingerprint: str
    supplier: str | None = None
    date: str | None = None
    amount: str | None = None
    art: str | None = None
    konto: str | None = None
    payment_field: str | None = None
    street: str | None = None
