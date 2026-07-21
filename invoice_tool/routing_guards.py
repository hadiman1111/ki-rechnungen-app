"""Local routing guards: payment evidence, mixed address, direction, document type.

These guards correct unsafe automatic routing (e.g. supplier IBAN → vobaai)
without embedding private SaaS UI defaults. Profile-specific issuer hints may be
read from profile_data when present; blank SaaS defaults never include them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from invoice_tool.matching import normalize_for_matching
from invoice_tool.models import (
    AccountDecision,
    ClassificationDecision,
    ExtractedData,
    PaymentDecision,
    ProcessingPreset,
    RoutingDecision,
)

_UNSAFE_AUTO_PAYMENT_FIELDS = frozenset({"vobaai", "vobaep"})

_APPLE_PAY_MARKERS = (
    "apple pay",
    "applepay",
    "payment via apple pay",
    "bezahlt mit apple pay",
)

_GENERIC_CREDIT_CARD_MARKERS = (
    "zahlung per kreditkarte",
    "bezahlt per kreditkarte",
    "zahlung mit kreditkarte",
    "kreditkarte",
    "kartenzahlung",
    "card payment",
    "paid by card",
    "credit card",
)

# Payment fields that must not be inferred from bare credit-card wording.
_GENERIC_CARD_UNSAFE_PAYMENT_FIELDS = frozenset(
    {"amex", "amex-1005", "vobaai", "vobaep", "private", "card"}
)

_PAYER_DEBIT_MARKERS = (
    "prenotification",
    "von ihrem konto abgebucht",
    "wird abgebucht",
    "sepa lastschrift",
    "sepa-lastschrift",
    "bankeinzug",
    "direct debit",
)

_SECURE_PAYMENT_RULE_NAMES = (
    "explicit-direct-debit",
    "iban-bic-direct-debit-wording",
    "explicit-amex",
    "cursor-anysphere-amex",
)

_ACCOUNT_SOURCE_MARKERS = (
    "aufloesung ueber card",
    "aufloesung ueber apple",
    "aufloesung ueber iban",
)

_BUSINESS_ADDRESS_MARKERS = (
    "somaa",
    "bismarckstrasse",
    "bismarckstraße",
    "bismarck strasse",
)

_PRIVATE_ADDRESS_MARKERS = (
    "roetestrasse",
    "rötestrasse",
    "roetestraße",
    "rötestraße",
    "roete strasse",
    "röte strasse",
    "roetestr",
    "rötestr",
)

_OUTGOING_PHRASES = (
    "berechne ich",
    "leistungszeitraum",
    "endbetrag",
    "honorar",
    "architekturleistung",
    "rechnungs-nr",
    "rechnungsnr",
)

_EXTERNAL_ADDRESSEE_MARKERS = (
    "herrn ",
    "herr ",
    "frau ",
)

# Compound signatures for DATEV / bookkeeping evaluations (not mere DATEV mentions).
_ACCOUNTING_REPORT_SIGNATURE_GROUPS: tuple[tuple[str, ...], ...] = (
    ("jahreskonto", "kanzlei-rechnungswesen"),
    ("jahreskonto", "ungeklaerte posten"),
    ("jahreskonto", "ungeklärte posten"),
    ("konto 1590", "ungeklaerte posten"),
    ("konto 1590", "ungeklärte posten"),
    ("auswertung entspricht dem derzeitigen stand der buchfuehrung",),
    ("auswertung entspricht dem derzeitigen stand der buchführung",),
    ("buchungstext", "gegenkto", "umsatz soll"),
    ("buchungstext", "gegenkto.", "umsatz haben"),
    ("nur nicht ausgezifferte buchungen", "jahreskonto"),
    ("sortierung: belegdatum", "jahreskonto"),
)


@dataclass(frozen=True)
class DocumentTypeGuardDecision:
    force_document: bool
    document_type: str | None
    reason: str


@dataclass(frozen=True)
class InvoiceDirectionGuardDecision:
    is_outgoing: bool
    direction: str | None
    reason: str


@dataclass(frozen=True)
class MixedAddressGuardDecision:
    is_ambiguous: bool
    reason: str
    private_billing_business_delivery: bool = False
    business_signal_only_in_delivery: bool = False


@dataclass(frozen=True)
class PaymentEvidenceGuardDecision:
    has_secure_evidence: bool
    reason: str
    apple_pay_without_card_reference: bool = False


@dataclass(frozen=True)
class RoutingGuardsResult:
    routing: RoutingDecision
    payment: PaymentEvidenceGuardDecision | None = None
    mixed_address: MixedAddressGuardDecision | None = None
    applied: tuple[str, ...] = ()


_BILLING_ADDRESS_LABEL = (
    r"(?:rechnungsadresse|billing\s+address|rechnungsanschrift|"
    r"invoice\s+address|abweichende\s+rechnungsadresse)"
)
_DELIVERY_ADDRESS_LABEL = (
    r"(?:lieferadresse|lieferanschrift|shipping\s+address|"
    r"delivery\s+address|ship\s+to|versandadresse)"
)


def _search_text(extracted: ExtractedData) -> str:
    return normalize_for_matching(
        " ".join(
            part
            for part in [
                extracted.raw_text or "",
                extracted.payment_method_raw or "",
                extracted.supplier_raw or "",
                " ".join(extracted.address_fragments or []),
                " ".join(extracted.context_markers or []),
                " ".join(extracted.document_type_indicators or []),
            ]
            if part
        )
    )


def _section_after_label(
    raw_text: str,
    label_pattern: str,
    *,
    stop_patterns: tuple[str, ...],
    max_chars: int = 320,
) -> str:
    if not raw_text:
        return ""
    match = re.search(label_pattern, raw_text, flags=re.IGNORECASE)
    if not match:
        return ""
    rest = raw_text[match.end() : match.end() + max_chars]
    earliest = len(rest)
    for stop in stop_patterns:
        stop_match = re.search(stop, rest, flags=re.IGNORECASE)
        if stop_match:
            earliest = min(earliest, stop_match.start())
    return normalize_for_matching(rest[:earliest])


def extract_billing_and_delivery_sections(extracted: ExtractedData) -> tuple[str, str]:
    """Return normalized (billing_section, delivery_section) from labeled address blocks."""

    raw = extracted.raw_text or ""
    billing = _section_after_label(
        raw,
        _BILLING_ADDRESS_LABEL,
        stop_patterns=(_DELIVERY_ADDRESS_LABEL, r"\b(?:artikel|zahlungsreferenz|payment\s+reference)\b"),
    )
    delivery = _section_after_label(
        raw,
        _DELIVERY_ADDRESS_LABEL,
        stop_patterns=(_BILLING_ADDRESS_LABEL, r"\b(?:artikel|zahlungsreferenz|payment\s+reference)\b"),
    )
    return billing, delivery


def billing_address_for_recipient_match(extracted: ExtractedData) -> str | None:
    """Billing-scoped recipient text when a Rechnungsadresse/Bill-to block exists.

    Returns None when no labeled billing block is present (caller may fall back).
    """

    billing, _delivery = extract_billing_and_delivery_sections(extracted)
    if billing:
        return billing
    # Soft fallback: labeled billing marker present but section empty — still signal
    # that delivery-only matching must not be used alone.
    raw_norm = normalize_for_matching(extracted.raw_text or "")
    if re.search(_BILLING_ADDRESS_LABEL, raw_norm):
        return billing or ""
    return None


def _contains_any(text: str, markers: tuple[str, ...]) -> str | None:
    for marker in markers:
        normalized = normalize_for_matching(marker)
        if normalized and normalized in text:
            return marker
    return None


def apple_pay_without_known_card_reference(extracted: ExtractedData) -> bool:
    text = _search_text(extracted)
    if not _contains_any(text, _APPLE_PAY_MARKERS):
        return False
    return not bool(extracted.apple_pay_endings)


def has_generic_credit_card_wording_without_known_reference(
    extracted: ExtractedData,
) -> bool:
    """True when only generic card wording exists (no known card/account ending)."""

    text = _search_text(extracted)
    if not _contains_any(text, _GENERIC_CREDIT_CARD_MARKERS):
        return False
    if extracted.card_endings or extracted.apple_pay_endings:
        return False
    return True


def has_secure_payer_payment_evidence(
    extracted: ExtractedData,
    account_decision: AccountDecision,
    payment_decision: PaymentDecision,
) -> PaymentEvidenceGuardDecision:
    """Return whether payer-side payment evidence is strong enough for vobaai/vobaep."""

    if apple_pay_without_known_card_reference(extracted):
        return PaymentEvidenceGuardDecision(
            has_secure_evidence=False,
            reason="Apple Pay ohne bekannte Karten-/Konto-Endung.",
            apple_pay_without_card_reference=True,
        )

    if has_generic_credit_card_wording_without_known_reference(extracted):
        text = _search_text(extracted)
        has_amex_text = bool(_contains_any(text, ("american express",)))
        if not (
            payment_decision.payment_method == "amex"
            and payment_decision.explicit
            and has_amex_text
        ):
            return PaymentEvidenceGuardDecision(
                has_secure_evidence=False,
                reason=(
                    "Unspezifische Kreditkartenangabe ohne bekannte "
                    "Karten-/Konto-Referenz."
                ),
            )

    account_reason = normalize_for_matching(account_decision.begruendung or "")
    if (
        account_decision.payment_field
        and not account_decision.ist_widerspruechlich
        and any(marker in account_reason for marker in _ACCOUNT_SOURCE_MARKERS)
    ):
        return PaymentEvidenceGuardDecision(
            has_secure_evidence=True,
            reason=f"Sichere Kontoauflösung: {account_decision.begruendung}",
        )

    payment_reason = payment_decision.begruendung or ""
    if payment_decision.payment_method == "amex" and payment_decision.explicit:
        return PaymentEvidenceGuardDecision(
            has_secure_evidence=True,
            reason="Explizite AMEX-Zahlungserkennung.",
        )

    if any(name in payment_reason for name in _SECURE_PAYMENT_RULE_NAMES):
        return PaymentEvidenceGuardDecision(
            has_secure_evidence=True,
            reason=f"Sichere Payment-Regel: {payment_reason}",
        )

    text = _search_text(extracted)
    debit_hit = _contains_any(text, _PAYER_DEBIT_MARKERS)
    if debit_hit:
        return PaymentEvidenceGuardDecision(
            has_secure_evidence=True,
            reason=f"Lastschrift-/Abbuchungshinweis des Zahlenden: {debit_hit}.",
        )

    return PaymentEvidenceGuardDecision(
        has_secure_evidence=False,
        reason="Kein sicherer Zahlungsweg des Zahlenden belegt.",
    )


def evaluate_mixed_address_ambiguity(
    extracted: ExtractedData,
    *,
    street_key: str | None = None,
) -> MixedAddressGuardDecision:
    text = _search_text(extracted)
    billing_section, delivery_section = extract_billing_and_delivery_sections(extracted)
    business_hit = _contains_any(text, _BUSINESS_ADDRESS_MARKERS)
    private_hit = _contains_any(text, _PRIVATE_ADDRESS_MARKERS)
    if street_key == "roete" and business_hit:
        private_hit = private_hit or "roete"

    billing_private = bool(_contains_any(billing_section, _PRIVATE_ADDRESS_MARKERS))
    billing_business = bool(_contains_any(billing_section, _BUSINESS_ADDRESS_MARKERS))
    delivery_business = bool(_contains_any(delivery_section, _BUSINESS_ADDRESS_MARKERS))
    business_only_in_delivery = bool(
        delivery_business and not billing_business and (billing_section or billing_private)
    )
    private_billing_business_delivery = bool(
        billing_private and delivery_business and not billing_business
    )

    # Strongest mixed signal: private Rechnungsadresse + business Lieferadresse.
    if private_billing_business_delivery or (
        business_only_in_delivery and (billing_private or street_key == "roete")
    ):
        return MixedAddressGuardDecision(
            is_ambiguous=True,
            reason=(
                "Private Rechnungsadresse + geschäftliche Lieferadresse = "
                "gemischte Adresssignale; Lieferadresse allein ist kein "
                "beruflicher Rechnungsnachweis."
            ),
            private_billing_business_delivery=True,
            business_signal_only_in_delivery=True,
        )

    # Billing address divergence: Rechnungsadresse/abweichend + private street.
    billing_divergence = bool(
        re.search(
            r"(rechnungsadresse|billing\s+address|abweichende\s+rechnungsadresse)",
            text,
        )
    ) and bool(private_hit)

    if business_hit and private_hit:
        return MixedAddressGuardDecision(
            is_ambiguous=True,
            reason=(
                "Gemischte geschäftliche/private Adresssignale "
                f"(business={business_hit}, private={private_hit})."
            ),
            private_billing_business_delivery=private_billing_business_delivery,
            business_signal_only_in_delivery=business_only_in_delivery,
        )
    if billing_divergence and business_hit:
        return MixedAddressGuardDecision(
            is_ambiguous=True,
            reason="Abweichende private Rechnungsadresse bei geschäftlicher Hauptadresse.",
            private_billing_business_delivery=True,
            business_signal_only_in_delivery=business_only_in_delivery,
        )
    return MixedAddressGuardDecision(is_ambiguous=False, reason="Keine gemischte Adresslage.")


def _own_issuer_hints(profile_data: dict | None) -> tuple[str, ...]:
    hints: list[str] = []
    if isinstance(profile_data, dict):
        identity = profile_data.get("identity_policy")
        if isinstance(identity, dict):
            raw = identity.get("own_issuer_hints")
            if isinstance(raw, list):
                hints.extend(str(item).strip() for item in raw if str(item or "").strip())
        recipient = profile_data.get("recipient_policy")
        if isinstance(recipient, dict):
            raw_biz = recipient.get("business_recipient_hints")
            if isinstance(raw_biz, list):
                # Only strong org markers — not person names alone.
                for item in raw_biz:
                    text = str(item or "").strip()
                    if text and normalize_for_matching(text) in {"somaa", "somaa architektur"}:
                        hints.append(text)
    if not hints:
        hints.extend(("somaa", "somaa architektur", "dipl.-ing. alexander tandawardaja", "dipl.ing. alexander tandawardaja"))
    # Deduplicate preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for item in hints:
        key = normalize_for_matching(item)
        if key and key not in seen:
            seen.add(key)
            ordered.append(item)
    return tuple(ordered)


def evaluate_invoice_direction_guard(
    extracted: ExtractedData,
    profile_data: dict | None = None,
) -> InvoiceDirectionGuardDecision:
    """Detect own outgoing invoices so they are not routed as incoming invoices."""

    text = _search_text(extracted)
    supplier = normalize_for_matching(extracted.supplier_raw or "")
    own_hints = _own_issuer_hints(profile_data)

    issuer_is_own = False
    matched_issuer: str | None = None
    for hint in own_hints:
        normalized = normalize_for_matching(hint)
        if not normalized:
            continue
        if normalized in supplier or (supplier and supplier in normalized):
            issuer_is_own = True
            matched_issuer = hint
            break
        # Header/issuer block near the start of the document
        head = text[:800]
        if normalized in head and (
            "rechnung" in head or "rechnungs-nr" in head or "rechnungsnr" in head
        ):
            issuer_is_own = True
            matched_issuer = hint
            break

    if not issuer_is_own:
        return InvoiceDirectionGuardDecision(
            is_outgoing=False,
            direction=None,
            reason="Kein eigener Aussteller erkannt.",
        )

    # Incoming invoices name an external supplier and list own org as recipient.
    # If supplier is clearly external (not own), do not treat as outgoing.
    if supplier and matched_issuer:
        own_norm = normalize_for_matching(matched_issuer)
        if own_norm not in supplier and not any(
            normalize_for_matching(h) in supplier for h in own_hints
        ):
            return InvoiceDirectionGuardDecision(
                is_outgoing=False,
                direction=None,
                reason="Externer Lieferant — Eingangsrechnung.",
            )

    phrase_hit = _contains_any(text, _OUTGOING_PHRASES)
    addressee_hit = _contains_any(text, _EXTERNAL_ADDRESSEE_MARKERS)
    has_project = "projekt" in text

    # Require outgoing phrasing or external addressee + own issuer as supplier/header.
    if not phrase_hit and not (addressee_hit and has_project):
        # Own org as recipient alone is not outgoing.
        if "rechnungsempfaenger" in text or "bill to" in text:
            return InvoiceDirectionGuardDecision(
                is_outgoing=False,
                direction=None,
                reason="Eigene Daten als Empfänger — keine Ausgangsrechnung.",
            )
        return InvoiceDirectionGuardDecision(
            is_outgoing=False,
            direction=None,
            reason="Aussteller-Hinweis ohne ausreichende Ausgangssignale.",
        )

    return InvoiceDirectionGuardDecision(
        is_outgoing=True,
        direction="outgoing_invoice",
        reason=(
            f"Ausgangsrechnung erkannt (Aussteller={matched_issuer}, "
            f"phrase={phrase_hit}, addressee={addressee_hit})."
        ),
    )


def evaluate_document_type_guard(
    extracted: ExtractedData,
    classification: ClassificationDecision | None = None,
) -> DocumentTypeGuardDecision:
    """Force document/accounting_report for DATEV Jahreskonto / booking lists."""

    text = _search_text(extracted)
    for group in _ACCOUNTING_REPORT_SIGNATURE_GROUPS:
        if all(normalize_for_matching(part) in text for part in group):
            return DocumentTypeGuardDecision(
                force_document=True,
                document_type="accounting_report",
                reason=(
                    "Buchhaltungsauswertung/Jahreskonto erkannt "
                    f"(Signatur: {', '.join(group)})."
                ),
            )

    # Soft single markers that are still distinctive when combined with bookkeeping UI terms.
    soft_hits = sum(
        1
        for marker in (
            "jahreskonto",
            "kanzlei-rechnungswesen",
            "ungeklaerte posten",
            "ungeklärte posten",
            "konto 1590",
            "belegfeld",
            "gegenkto",
        )
        if normalize_for_matching(marker) in text
    )
    if soft_hits >= 3:
        return DocumentTypeGuardDecision(
            force_document=True,
            document_type="accounting_report",
            reason=f"Buchhaltungsauswertung erkannt (soft-score={soft_hits}).",
        )

    return DocumentTypeGuardDecision(
        force_document=False,
        document_type=classification.dokumenttyp if classification else None,
        reason="Kein Auswertungs-/Jahreskonto-Guard.",
    )


def apply_payment_evidence_guard(
    routing: RoutingDecision,
    *,
    extracted: ExtractedData,
    account_decision: AccountDecision,
    payment_decision: PaymentDecision,
    preset: ProcessingPreset,
) -> tuple[RoutingDecision, PaymentEvidenceGuardDecision]:
    evidence = has_secure_payer_payment_evidence(
        extracted, account_decision, payment_decision
    )
    payment_field = routing.payment_field or ""
    force_unknown_card = (
        has_generic_credit_card_wording_without_known_reference(extracted)
        and payment_field in _GENERIC_CARD_UNSAFE_PAYMENT_FIELDS
        and not evidence.has_secure_evidence
    )
    if payment_field not in _UNSAFE_AUTO_PAYMENT_FIELDS and not force_unknown_card:
        return routing, evidence
    if evidence.has_secure_evidence and not force_unknown_card:
        return routing, evidence

    from invoice_tool.routing import resolve_output_route

    unklar_field = preset.routing.unklar_konto or "unklar"
    # Keep business-context art (ai/ep) when known; only payment/folder become unklar.
    zielordner, status = resolve_output_route(
        art=routing.art,
        payment_field=unklar_field,
        preset=preset,
    )
    if routing.art in {"ai", "ep"} or force_unknown_card:
        # Prefer explicit unklar folder over ai/ep keep-folder fallbacks.
        zielordner = preset.routing.zielordner.get("unklar", zielordner or "unklar")
        status = "unklar"
    return (
        RoutingDecision(
            art=routing.art,
            zielordner=zielordner,
            status=status,
            konto=None,
            payment_field=unklar_field,
            street_key=routing.street_key,
            begruendung=(
                f"{routing.begruendung}; Payment-Evidence-Guard: {evidence.reason}"
            ),
        ),
        evidence,
    )


def apply_mixed_address_guard(
    routing: RoutingDecision,
    *,
    extracted: ExtractedData,
    preset: ProcessingPreset,
    street_key: str | None,
) -> tuple[RoutingDecision, MixedAddressGuardDecision]:
    decision = evaluate_mixed_address_ambiguity(extracted, street_key=street_key)
    if not decision.is_ambiguous:
        return routing, decision

    # Private billing + business-only delivery must always go to review — including
    # exclusive vendor shortcuts (e.g. amazon-ai-amex) that set payment_field=amex
    # without document payment proof. Delivery-address SOMAA alone is not enough.
    force_review = (
        decision.private_billing_business_delivery
        or decision.business_signal_only_in_delivery
    )

    # Otherwise only force review when payment is unsafe auto-assignment or
    # currently auto-assigned to business payment folders.
    if not force_review:
        if routing.payment_field not in _UNSAFE_AUTO_PAYMENT_FIELDS and routing.zielordner not in {
            preset.routing.zielordner.get("ai", "ai"),
            preset.routing.zielordner.get("ep", "ep"),
            "ai",
            "ep",
            "amex",
            preset.routing.zielordner.get("amex", "amex"),
        }:
            if routing.payment_field in {"amex", "amex-1005", "private", "bar"}:
                return routing, decision

    unklar_folder = preset.routing.zielordner.get("unklar", "unklar")
    return (
        RoutingDecision(
            art="unklar",
            zielordner=unklar_folder,
            status="unklar",
            konto=None,
            payment_field=preset.routing.unklar_konto or "unklar",
            street_key=street_key,
            begruendung=(
                f"{routing.begruendung}; Mixed-Address-Guard: {decision.reason}"
            ),
        ),
        decision,
    )


def apply_routing_guards(
    routing: RoutingDecision,
    *,
    extracted: ExtractedData,
    account_decision: AccountDecision,
    payment_decision: PaymentDecision,
    preset: ProcessingPreset,
    street_key: str | None = None,
) -> RoutingGuardsResult:
    """Apply payment-evidence and mixed-address guards to a routing decision."""

    applied: list[str] = []
    current = routing

    current, payment = apply_payment_evidence_guard(
        current,
        extracted=extracted,
        account_decision=account_decision,
        payment_decision=payment_decision,
        preset=preset,
    )
    if "Payment-Evidence-Guard" in current.begruendung:
        applied.append("payment_evidence")

    current, mixed = apply_mixed_address_guard(
        current,
        extracted=extracted,
        preset=preset,
        street_key=street_key,
    )
    if "Mixed-Address-Guard" in current.begruendung:
        applied.append("mixed_address")

    return RoutingGuardsResult(
        routing=current,
        payment=payment,
        mixed_address=mixed,
        applied=tuple(applied),
    )


def apply_classification_guards(
    extracted: ExtractedData,
    classification: ClassificationDecision,
    *,
    profile_data: dict | None = None,
) -> ClassificationDecision:
    """Apply document-type and invoice-direction guards before invoice processing."""

    doc_guard = evaluate_document_type_guard(extracted, classification)
    if doc_guard.force_document:
        return ClassificationDecision(
            dokumenttyp="document",
            begruendung=(
                f"{classification.begruendung}; Document-Type-Guard: {doc_guard.reason} "
                f"[{doc_guard.document_type or 'document'}]"
            ),
        )

    direction = evaluate_invoice_direction_guard(extracted, profile_data)
    if direction.is_outgoing:
        return ClassificationDecision(
            dokumenttyp="document",
            begruendung=(
                f"{classification.begruendung}; Invoice-Direction-Guard: {direction.reason} "
                f"[{direction.direction}]"
            ),
        )

    return classification


_ORDER_CONFIRMATION_MARKERS = (
    "bestellbestätigung",
    "bestellbestaetigung",
    "order confirmation",
    "bestätigen wir den eingang ihrer bestellung",
    "bestaetigen wir den eingang ihrer bestellung",
    "hiermit bestätigen wir den eingang",
    "hiermit bestaetigen wir den eingang",
    "bestellte artikel",
    "ihre bestellung",
)


@dataclass(frozen=True)
class BusinessNonInvoiceDocumentDecision:
    is_business_non_invoice: bool
    subtype: str | None
    reason: str
    has_business_billing_signal: bool = False
    order_confirmation_marker: str | None = None


def has_business_billing_address_signal(extracted: ExtractedData) -> bool:
    """True when Rechnungsadresse/Bill-to (or whole text fallback) has business markers."""

    billing, _delivery = extract_billing_and_delivery_sections(extracted)
    if billing:
        return bool(_contains_any(billing, _BUSINESS_ADDRESS_MARKERS))
    text = _search_text(extracted)
    # Without labeled blocks, only count business markers outside an exclusive delivery block.
    delivery = _section_after_label(
        extracted.raw_text or "",
        _DELIVERY_ADDRESS_LABEL,
        stop_patterns=(_BILLING_ADDRESS_LABEL,),
    )
    if delivery and _contains_any(delivery, _BUSINESS_ADDRESS_MARKERS):
        # Business only in Lieferadresse is not billing evidence.
        remainder = text.replace(delivery, " ")
        return bool(_contains_any(remainder, _BUSINESS_ADDRESS_MARKERS))
    return bool(_contains_any(text, _BUSINESS_ADDRESS_MARKERS))


def evaluate_business_non_invoice_document(
    extracted: ExtractedData,
    classification: ClassificationDecision | None = None,
) -> BusinessNonInvoiceDocumentDecision:
    """Detect order confirmations / purchase docs that are not bookable invoices.

    Keeps document_type separate from economic assignment (art/payment).
    """

    if classification is not None and classification.dokumenttyp == "invoice":
        return BusinessNonInvoiceDocumentDecision(
            is_business_non_invoice=False,
            subtype=None,
            reason="Als Rechnung klassifiziert — kein Non-Invoice-Guard.",
        )

    text = _search_text(extracted)
    marker = _contains_any(text, _ORDER_CONFIRMATION_MARKERS)
    if not marker:
        return BusinessNonInvoiceDocumentDecision(
            is_business_non_invoice=False,
            subtype=None,
            reason="Keine Bestellbestätigungs-/Kaufdokument-Signale.",
        )

    # Do not reclassify clear invoices that somehow still carry order wording.
    if extracted.invoice_number_raw and re.search(
        r"(?<![a-z])(?:rechnung|invoice)(?![a-z])", text
    ):
        if not re.search(r"bestellbestätigung|bestellbestaetigung|order confirmation", text):
            return BusinessNonInvoiceDocumentDecision(
                is_business_non_invoice=False,
                subtype=None,
                reason="Echte Rechnung mit Rechnungsnummer — Guard greift nicht.",
            )

    business_billing = has_business_billing_address_signal(extracted)
    return BusinessNonInvoiceDocumentDecision(
        is_business_non_invoice=True,
        subtype="order_confirmation",
        reason=(
            f"Geschäftliches Nicht-Rechnungsdokument erkannt "
            f"(marker={marker}, business_billing={business_billing})."
        ),
        has_business_billing_signal=business_billing,
        order_confirmation_marker=marker,
    )
