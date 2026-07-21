"""Generic SaaS product profile/configuration surface.

This module is the product-facing contract for the external UI-v2 / SaaS variant.
It deliberately contains no private tenant defaults (SOMAA, Hadi, AMEX-1005, EP, …).

Internal Dock/Launcher code must not import this module as a runtime dependency for
SOMAA operations; local/private profiles remain outside SaaS defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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

# Generic classification / payment policy defaults for SaaS UI-v2 (no tenant values).
DEFAULT_UNKNOWN_PAYMENT_TARGET = "unklar"
DEFAULT_OUTGOING_INVOICES_TARGET = "unklar"
DEFAULT_ACCOUNTING_REPORTS_TARGET = "documents"
DEFAULT_MIXED_ADDRESS_TARGET = "unklar"
DEFAULT_UNKNOWN_TOOL_CONTEXT_TARGET = "unklar"

CLASSIFICATION_POLICY_UI_TEXTS: tuple[str, ...] = (
    "Zahlungsweg-Erkennung",
    "Sichere Zahlungsweg-Signale erforderlich",
    "Lieferanten-IBAN/BIC nicht als Zahlungsweg werten",
    "Apple Pay ohne Karten-/Konto-Endung zur Prüfung",
    "Bei unbekanntem Zahlungsweg: Zur Prüfung",
    "Rechnungsrichtung erkennen",
    "Eingangsrechnung",
    "Ausgangsrechnung",
    "Eigene Rechnungen nicht als Eingangsrechnungen verarbeiten",
    "Ausgangsrechnungen zur Prüfung oder separater Zielbereich",
    "Dokumenttyp-Erkennung",
    "Rechnungen von Buchhaltungsauswertungen unterscheiden",
    "Kontoauszüge, Jahreskonten und Buchungslisten zur Prüfung",
    "DATEV-/Kanzlei-Auswertungen nicht als Eingangsrechnung behandeln",
    "Gemischte geschäftliche/private Adresssignale zur Prüfung",
    "Abweichende private Rechnungsadresse als Unsicherheitsmerkmal",
    "Rechnungsadresse und Lieferadresse",
    "Rechnungsadresse vor Lieferadresse priorisieren",
    "Geschäftliche Lieferadresse allein reicht nicht für geschäftliche Zuordnung",
    "Abweichende private Rechnungsadresse zur Prüfung",
    "Gemischte Rechnungs-/Lieferadresssignale zur Prüfung",
    "Geschäftliche Nicht-Rechnungs-Belege",
    "Bestellbestätigungen von Rechnungen unterscheiden",
    "Geschäftliche Bestelldokumente fachlich zuordnen",
    "Rechnungsadresse kann AI/Business-Kontext setzen",
    "Nicht buchbare Geschäftsdokumente zur Prüfung",
    "Zahlungsmethode auch bei Nicht-Rechnungen erkennen",
    "Explizite Zahlungsangabe im Belegtext hat Vorrang",
    "Schwache Vendor-/Tool-AMEX-Signale überschreiben keine explizite Zahlungsart",
    "Rechnungs-Erkennung",
    "Starke Rechnungsindikatoren vor Format-/Dokumentphrasen",
    "Format-Verfügbarkeitshinweise sind kein Dokumenttyp",
    "Dateiname ist keine Beweisquelle",
    "Unspezifische Kreditkarte ohne Kennung zur Prüfung",
    "Kartenzahlung erfordert bekannte Referenz",
    "Geschäftliche Rechnungsadresse setzt Business-Kontext",
    "Mehrdeutige Positionen überschreiben keine Rechnungsadresse",
    "Organisationskennungen sind profilkonfiguriert",
    "Software- und AI-Tools erkennen",
    "Nutzung von AI-, Coding- und Token-basierten Diensten als eigene Regelklasse",
    "Gutschriften/Refunds behalten die wirtschaftliche Kategorie",
    "Berufliche Signale erforderlich",
    "Ohne berufliche Signale: Zur Prüfung",
)


@dataclass(frozen=True)
class AddressPolicy:
    """Generic billing vs delivery address precedence (no private street/tenant defaults)."""

    billing_address_takes_precedence: bool = True
    delivery_address_only_is_not_business_evidence: bool = True
    mixed_billing_delivery_address_target: str = DEFAULT_MIXED_ADDRESS_TARGET
    private_billing_business_delivery_target: str = DEFAULT_MIXED_ADDRESS_TARGET

    def to_dict(self) -> dict[str, Any]:
        return {
            "billing_address_takes_precedence": self.billing_address_takes_precedence,
            "delivery_address_only_is_not_business_evidence": (
                self.delivery_address_only_is_not_business_evidence
            ),
            "mixed_billing_delivery_address_target": self.mixed_billing_delivery_address_target,
            "private_billing_business_delivery_target": (
                self.private_billing_business_delivery_target
            ),
        }


def default_address_policy() -> AddressPolicy:
    return AddressPolicy()


@dataclass(frozen=True)
class InvoiceDetectionPolicy:
    """Generic invoice-vs-document priority (no private tenant defaults)."""

    invoice_indicators_override_format_notes: bool = True
    format_availability_notes_are_not_document_type: bool = True
    filename_is_not_source_of_truth: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "invoice_indicators_override_format_notes": (
                self.invoice_indicators_override_format_notes
            ),
            "format_availability_notes_are_not_document_type": (
                self.format_availability_notes_are_not_document_type
            ),
            "filename_is_not_source_of_truth": self.filename_is_not_source_of_truth,
        }


def default_invoice_detection_policy() -> InvoiceDetectionPolicy:
    return InvoiceDetectionPolicy()


@dataclass(frozen=True)
class PaymentEvidencePolicy:
    """Generic payer-side payment evidence rules (no private card defaults)."""

    generic_credit_card_without_identifier_target: str = DEFAULT_UNKNOWN_PAYMENT_TARGET
    card_payment_requires_known_reference: bool = True
    supplier_bank_details_are_not_payer_evidence: bool = True
    explicit_document_payment_method_takes_precedence: bool = True
    weak_vendor_amex_does_not_override_explicit_payment: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "generic_credit_card_without_identifier_target": (
                self.generic_credit_card_without_identifier_target
            ),
            "card_payment_requires_known_reference": (
                self.card_payment_requires_known_reference
            ),
            "supplier_bank_details_are_not_payer_evidence": (
                self.supplier_bank_details_are_not_payer_evidence
            ),
            "explicit_document_payment_method_takes_precedence": (
                self.explicit_document_payment_method_takes_precedence
            ),
            "weak_vendor_amex_does_not_override_explicit_payment": (
                self.weak_vendor_amex_does_not_override_explicit_payment
            ),
        }


def default_payment_evidence_policy() -> PaymentEvidencePolicy:
    return PaymentEvidencePolicy()


@dataclass(frozen=True)
class BusinessAssignmentPolicy:
    """Generic business-context assignment from billing address / org identifiers."""

    business_billing_address_assigns_business_context: bool = True
    ambiguous_items_do_not_override_business_billing_address: bool = True
    organization_identifiers_are_profile_configured: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_billing_address_assigns_business_context": (
                self.business_billing_address_assigns_business_context
            ),
            "ambiguous_items_do_not_override_business_billing_address": (
                self.ambiguous_items_do_not_override_business_billing_address
            ),
            "organization_identifiers_are_profile_configured": (
                self.organization_identifiers_are_profile_configured
            ),
        }


def default_business_assignment_policy() -> BusinessAssignmentPolicy:
    return BusinessAssignmentPolicy()


def _policy_bool(data: Mapping[str, Any], key: str, fallback: bool) -> bool:
    value = data.get(key, fallback)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ja"}
    return fallback


def _policy_target(data: Mapping[str, Any], key: str, fallback: str) -> str:
    value = data.get(key, fallback)
    text = str(value or "").strip().lower()
    if text in {"unklar", "zur_pruefung", "zur-prüfung", "review"}:
        return "unklar"
    if text in {"documents", "document"}:
        return "documents"
    return fallback


def invoice_detection_policy_from_dict(raw: Mapping[str, Any] | None) -> InvoiceDetectionPolicy:
    data = dict(raw) if isinstance(raw, Mapping) else {}
    defaults = default_invoice_detection_policy()
    return InvoiceDetectionPolicy(
        invoice_indicators_override_format_notes=_policy_bool(
            data,
            "invoice_indicators_override_format_notes",
            defaults.invoice_indicators_override_format_notes,
        ),
        format_availability_notes_are_not_document_type=_policy_bool(
            data,
            "format_availability_notes_are_not_document_type",
            defaults.format_availability_notes_are_not_document_type,
        ),
        filename_is_not_source_of_truth=_policy_bool(
            data,
            "filename_is_not_source_of_truth",
            defaults.filename_is_not_source_of_truth,
        ),
    )


def payment_evidence_policy_from_dict(raw: Mapping[str, Any] | None) -> PaymentEvidencePolicy:
    data = dict(raw) if isinstance(raw, Mapping) else {}
    defaults = default_payment_evidence_policy()
    return PaymentEvidencePolicy(
        generic_credit_card_without_identifier_target=_policy_target(
            data,
            "generic_credit_card_without_identifier_target",
            defaults.generic_credit_card_without_identifier_target,
        ),
        card_payment_requires_known_reference=_policy_bool(
            data,
            "card_payment_requires_known_reference",
            defaults.card_payment_requires_known_reference,
        ),
        supplier_bank_details_are_not_payer_evidence=_policy_bool(
            data,
            "supplier_bank_details_are_not_payer_evidence",
            defaults.supplier_bank_details_are_not_payer_evidence,
        ),
        explicit_document_payment_method_takes_precedence=_policy_bool(
            data,
            "explicit_document_payment_method_takes_precedence",
            defaults.explicit_document_payment_method_takes_precedence,
        ),
        weak_vendor_amex_does_not_override_explicit_payment=_policy_bool(
            data,
            "weak_vendor_amex_does_not_override_explicit_payment",
            defaults.weak_vendor_amex_does_not_override_explicit_payment,
        ),
    )


def business_assignment_policy_from_dict(
    raw: Mapping[str, Any] | None,
) -> BusinessAssignmentPolicy:
    data = dict(raw) if isinstance(raw, Mapping) else {}
    defaults = default_business_assignment_policy()
    return BusinessAssignmentPolicy(
        business_billing_address_assigns_business_context=_policy_bool(
            data,
            "business_billing_address_assigns_business_context",
            defaults.business_billing_address_assigns_business_context,
        ),
        ambiguous_items_do_not_override_business_billing_address=_policy_bool(
            data,
            "ambiguous_items_do_not_override_business_billing_address",
            defaults.ambiguous_items_do_not_override_business_billing_address,
        ),
        organization_identifiers_are_profile_configured=_policy_bool(
            data,
            "organization_identifiers_are_profile_configured",
            defaults.organization_identifiers_are_profile_configured,
        ),
    )


@dataclass(frozen=True)
class BusinessDocumentPolicy:
    """Generic policy for business non-invoice documents (order confirmations, etc.)."""

    classify_order_confirmations: bool = True
    order_confirmation_is_not_invoice: bool = True
    preserve_business_assignment_for_non_invoice_documents: bool = True
    preserve_payment_method_for_non_invoice_documents: bool = True
    non_invoice_business_document_target: str = DEFAULT_MIXED_ADDRESS_TARGET

    def to_dict(self) -> dict[str, Any]:
        return {
            "classify_order_confirmations": self.classify_order_confirmations,
            "order_confirmation_is_not_invoice": self.order_confirmation_is_not_invoice,
            "preserve_business_assignment_for_non_invoice_documents": (
                self.preserve_business_assignment_for_non_invoice_documents
            ),
            "preserve_payment_method_for_non_invoice_documents": (
                self.preserve_payment_method_for_non_invoice_documents
            ),
            "non_invoice_business_document_target": self.non_invoice_business_document_target,
        }


def default_business_document_policy() -> BusinessDocumentPolicy:
    return BusinessDocumentPolicy()


def business_document_policy_from_dict(raw: Mapping[str, Any] | None) -> BusinessDocumentPolicy:
    data = dict(raw) if isinstance(raw, Mapping) else {}
    defaults = default_business_document_policy()

    def _bool(key: str, fallback: bool) -> bool:
        value = data.get(key, fallback)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "ja"}
        return fallback

    def _target(key: str, fallback: str) -> str:
        value = data.get(key, fallback)
        text = str(value or "").strip().lower()
        if text in {"unklar", "zur_pruefung", "zur-prüfung", "review"}:
            return "unklar"
        if text in {"documents", "document"}:
            return "documents"
        return fallback

    return BusinessDocumentPolicy(
        classify_order_confirmations=_bool(
            "classify_order_confirmations", defaults.classify_order_confirmations
        ),
        order_confirmation_is_not_invoice=_bool(
            "order_confirmation_is_not_invoice",
            defaults.order_confirmation_is_not_invoice,
        ),
        preserve_business_assignment_for_non_invoice_documents=_bool(
            "preserve_business_assignment_for_non_invoice_documents",
            defaults.preserve_business_assignment_for_non_invoice_documents,
        ),
        preserve_payment_method_for_non_invoice_documents=_bool(
            "preserve_payment_method_for_non_invoice_documents",
            defaults.preserve_payment_method_for_non_invoice_documents,
        ),
        non_invoice_business_document_target=_target(
            "non_invoice_business_document_target",
            defaults.non_invoice_business_document_target,
        ),
    )


def address_policy_from_dict(raw: Mapping[str, Any] | None) -> AddressPolicy:
    data = dict(raw) if isinstance(raw, Mapping) else {}
    defaults = default_address_policy()

    def _bool(key: str, fallback: bool) -> bool:
        value = data.get(key, fallback)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "ja"}
        return fallback

    def _target(key: str, fallback: str) -> str:
        value = data.get(key, fallback)
        text = str(value or "").strip().lower()
        if text in {"unklar", "zur_pruefung", "zur-prüfung"}:
            return "unklar"
        if text in {"documents", "document"}:
            return "documents"
        return fallback

    return AddressPolicy(
        billing_address_takes_precedence=_bool(
            "billing_address_takes_precedence",
            defaults.billing_address_takes_precedence,
        ),
        delivery_address_only_is_not_business_evidence=_bool(
            "delivery_address_only_is_not_business_evidence",
            defaults.delivery_address_only_is_not_business_evidence,
        ),
        mixed_billing_delivery_address_target=_target(
            "mixed_billing_delivery_address_target",
            defaults.mixed_billing_delivery_address_target,
        ),
        private_billing_business_delivery_target=_target(
            "private_billing_business_delivery_target",
            defaults.private_billing_business_delivery_target,
        ),
    )


@dataclass(frozen=True)
class SoftwareAiToolPolicy:
    """Generic software/AI coding-tool classification policy (no private defaults)."""

    detect_ai_coding_tools: bool = True
    require_business_signal_for_ai_tool_assignment: bool = True
    preserve_category_for_refunds: bool = True
    unknown_tool_context_target: str = DEFAULT_UNKNOWN_TOOL_CONTEXT_TARGET

    def to_dict(self) -> dict[str, Any]:
        return {
            "detect_ai_coding_tools": self.detect_ai_coding_tools,
            "require_business_signal_for_ai_tool_assignment": (
                self.require_business_signal_for_ai_tool_assignment
            ),
            "preserve_category_for_refunds": self.preserve_category_for_refunds,
            "unknown_tool_context_target": self.unknown_tool_context_target,
        }


def default_software_ai_tool_policy() -> SoftwareAiToolPolicy:
    return SoftwareAiToolPolicy()


def software_ai_tool_policy_from_dict(raw: Mapping[str, Any] | None) -> SoftwareAiToolPolicy:
    data = dict(raw) if isinstance(raw, Mapping) else {}
    defaults = default_software_ai_tool_policy()

    def _bool(key: str, fallback: bool) -> bool:
        value = data.get(key, fallback)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "ja"}
        return fallback

    target = str(data.get("unknown_tool_context_target") or defaults.unknown_tool_context_target)
    target = target.strip().lower()
    if target in {"document", "documents"}:
        unknown_target = "documents"
    elif target in {"unklar", "zur_pruefung", "zur-prüfung"}:
        unknown_target = "unklar"
    else:
        unknown_target = defaults.unknown_tool_context_target

    return SoftwareAiToolPolicy(
        detect_ai_coding_tools=_bool("detect_ai_coding_tools", defaults.detect_ai_coding_tools),
        require_business_signal_for_ai_tool_assignment=_bool(
            "require_business_signal_for_ai_tool_assignment",
            defaults.require_business_signal_for_ai_tool_assignment,
        ),
        preserve_category_for_refunds=_bool(
            "preserve_category_for_refunds",
            defaults.preserve_category_for_refunds,
        ),
        unknown_tool_context_target=unknown_target,
    )


@dataclass(frozen=True)
class ClassificationPolicy:
    """Generic scan/classification policy for SaaS profiles (no private defaults)."""

    require_explicit_payer_payment_evidence: bool = True
    supplier_bank_details_are_payment_evidence: bool = False
    apple_pay_requires_known_card_reference: bool = True
    unknown_payment_target: str = DEFAULT_UNKNOWN_PAYMENT_TARGET
    detect_invoice_direction: bool = True
    outgoing_invoices_target: str = DEFAULT_OUTGOING_INVOICES_TARGET
    detect_accounting_reports: bool = True
    accounting_reports_target: str = DEFAULT_ACCOUNTING_REPORTS_TARGET
    mixed_business_private_address_target: str = DEFAULT_MIXED_ADDRESS_TARGET
    address_policy: AddressPolicy = field(default_factory=default_address_policy)
    business_document_policy: BusinessDocumentPolicy = field(
        default_factory=default_business_document_policy
    )
    software_ai_tool_policy: SoftwareAiToolPolicy = field(
        default_factory=default_software_ai_tool_policy
    )
    invoice_detection_policy: InvoiceDetectionPolicy = field(
        default_factory=default_invoice_detection_policy
    )
    payment_evidence_policy: PaymentEvidencePolicy = field(
        default_factory=default_payment_evidence_policy
    )
    business_assignment_policy: BusinessAssignmentPolicy = field(
        default_factory=default_business_assignment_policy
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "require_explicit_payer_payment_evidence": self.require_explicit_payer_payment_evidence,
            "supplier_bank_details_are_payment_evidence": self.supplier_bank_details_are_payment_evidence,
            "apple_pay_requires_known_card_reference": self.apple_pay_requires_known_card_reference,
            "unknown_payment_target": self.unknown_payment_target,
            "detect_invoice_direction": self.detect_invoice_direction,
            "outgoing_invoices_target": self.outgoing_invoices_target,
            "detect_accounting_reports": self.detect_accounting_reports,
            "accounting_reports_target": self.accounting_reports_target,
            "mixed_business_private_address_target": self.mixed_business_private_address_target,
            "address_policy": self.address_policy.to_dict(),
            "business_document_policy": self.business_document_policy.to_dict(),
            "software_ai_tool_policy": self.software_ai_tool_policy.to_dict(),
            "invoice_detection_policy": self.invoice_detection_policy.to_dict(),
            "payment_evidence_policy": self.payment_evidence_policy.to_dict(),
            "business_assignment_policy": self.business_assignment_policy.to_dict(),
        }


def default_classification_policy() -> ClassificationPolicy:
    return ClassificationPolicy()


def classification_policy_from_dict(raw: Mapping[str, Any] | None) -> ClassificationPolicy:
    """Parse policy with safe defaults; ignore unknown keys."""

    data = dict(raw) if isinstance(raw, Mapping) else {}
    defaults = default_classification_policy()

    def _bool(key: str, fallback: bool) -> bool:
        value = data.get(key, fallback)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "ja"}
        return fallback

    def _target(key: str, fallback: str) -> str:
        value = data.get(key, fallback)
        text = str(value or "").strip().lower()
        if text in {"unklar", "documents", "document", "zur_pruefung", "zur-prüfung"}:
            if text in {"document", "zur_pruefung", "zur-prüfung"}:
                return "unklar" if text != "document" else "documents"
            return text
        return fallback

    nested_tool = data.get("software_ai_tool_policy")
    if not isinstance(nested_tool, Mapping):
        nested_tool = {
            "detect_ai_coding_tools": data.get("detect_ai_coding_tools"),
            "require_business_signal_for_ai_tool_assignment": data.get(
                "require_business_signal_for_ai_tool_assignment"
            ),
            "preserve_category_for_refunds": data.get("preserve_category_for_refunds"),
            "unknown_tool_context_target": data.get("unknown_tool_context_target"),
        }

    nested_address = data.get("address_policy")
    if not isinstance(nested_address, Mapping):
        nested_address = {
            "billing_address_takes_precedence": data.get(
                "billing_address_takes_precedence"
            ),
            "delivery_address_only_is_not_business_evidence": data.get(
                "delivery_address_only_is_not_business_evidence"
            ),
            "mixed_billing_delivery_address_target": data.get(
                "mixed_billing_delivery_address_target",
                data.get("mixed_business_private_address_target"),
            ),
            "private_billing_business_delivery_target": data.get(
                "private_billing_business_delivery_target",
                data.get("mixed_business_private_address_target"),
            ),
        }

    nested_business_doc = data.get("business_document_policy")
    if not isinstance(nested_business_doc, Mapping):
        nested_business_doc = {
            "classify_order_confirmations": data.get("classify_order_confirmations"),
            "order_confirmation_is_not_invoice": data.get(
                "order_confirmation_is_not_invoice"
            ),
            "preserve_business_assignment_for_non_invoice_documents": data.get(
                "preserve_business_assignment_for_non_invoice_documents"
            ),
            "preserve_payment_method_for_non_invoice_documents": data.get(
                "preserve_payment_method_for_non_invoice_documents"
            ),
            "non_invoice_business_document_target": data.get(
                "non_invoice_business_document_target"
            ),
        }

    nested_invoice_detection = data.get("invoice_detection_policy")
    if not isinstance(nested_invoice_detection, Mapping):
        nested_invoice_detection = {
            "invoice_indicators_override_format_notes": data.get(
                "invoice_indicators_override_format_notes"
            ),
            "format_availability_notes_are_not_document_type": data.get(
                "format_availability_notes_are_not_document_type"
            ),
            "filename_is_not_source_of_truth": data.get(
                "filename_is_not_source_of_truth"
            ),
        }

    nested_payment_evidence = data.get("payment_evidence_policy")
    if not isinstance(nested_payment_evidence, Mapping):
        nested_payment_evidence = {
            "generic_credit_card_without_identifier_target": data.get(
                "generic_credit_card_without_identifier_target"
            ),
            "card_payment_requires_known_reference": data.get(
                "card_payment_requires_known_reference"
            ),
            "supplier_bank_details_are_not_payer_evidence": data.get(
                "supplier_bank_details_are_not_payer_evidence"
            ),
        }

    nested_business_assignment = data.get("business_assignment_policy")
    if not isinstance(nested_business_assignment, Mapping):
        nested_business_assignment = {
            "business_billing_address_assigns_business_context": data.get(
                "business_billing_address_assigns_business_context"
            ),
            "ambiguous_items_do_not_override_business_billing_address": data.get(
                "ambiguous_items_do_not_override_business_billing_address"
            ),
            "organization_identifiers_are_profile_configured": data.get(
                "organization_identifiers_are_profile_configured"
            ),
        }

    return ClassificationPolicy(
        require_explicit_payer_payment_evidence=_bool(
            "require_explicit_payer_payment_evidence",
            defaults.require_explicit_payer_payment_evidence,
        ),
        supplier_bank_details_are_payment_evidence=_bool(
            "supplier_bank_details_are_payment_evidence",
            defaults.supplier_bank_details_are_payment_evidence,
        ),
        apple_pay_requires_known_card_reference=_bool(
            "apple_pay_requires_known_card_reference",
            defaults.apple_pay_requires_known_card_reference,
        ),
        unknown_payment_target=_target(
            "unknown_payment_target", defaults.unknown_payment_target
        ),
        detect_invoice_direction=_bool(
            "detect_invoice_direction", defaults.detect_invoice_direction
        ),
        outgoing_invoices_target=_target(
            "outgoing_invoices_target", defaults.outgoing_invoices_target
        ),
        detect_accounting_reports=_bool(
            "detect_accounting_reports", defaults.detect_accounting_reports
        ),
        accounting_reports_target=_target(
            "accounting_reports_target", defaults.accounting_reports_target
        ),
        mixed_business_private_address_target=_target(
            "mixed_business_private_address_target",
            defaults.mixed_business_private_address_target,
        ),
        address_policy=address_policy_from_dict(nested_address),
        business_document_policy=business_document_policy_from_dict(nested_business_doc),
        software_ai_tool_policy=software_ai_tool_policy_from_dict(nested_tool),
        invoice_detection_policy=invoice_detection_policy_from_dict(
            nested_invoice_detection
        ),
        payment_evidence_policy=payment_evidence_policy_from_dict(
            nested_payment_evidence
        ),
        business_assignment_policy=business_assignment_policy_from_dict(
            nested_business_assignment
        ),
    )


def classification_policy_ui_texts() -> tuple[str, ...]:
    return CLASSIFICATION_POLICY_UI_TEXTS


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
    classification_policy: ClassificationPolicy = field(default_factory=ClassificationPolicy)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "scan_model_id": self.scan_model_id,
            "document_type": self.document_type,
            "configurations": [item.to_dict() for item in self.configurations],
            "review_unclear_folder": self.review_unclear_folder,
            "default_filename_pattern": self.default_filename_pattern,
            "notes": self.notes,
            "classification_policy": self.classification_policy.to_dict(),
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
        classification_policy=default_classification_policy(),
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
