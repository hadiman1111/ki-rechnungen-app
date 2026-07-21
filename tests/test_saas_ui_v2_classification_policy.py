"""UI-v2 generic ClassificationPolicy defaults, persistence, and UI texts."""
from __future__ import annotations

import json
from pathlib import Path

from invoice_tool.saas_product_model import (
    ClassificationPolicy,
    build_blank_saas_profile,
    classification_policy_from_dict,
    classification_policy_ui_texts,
    default_classification_policy,
)
from invoice_tool.ui_v2.saas_profile_state import new_saas_profile_state_store
from invoice_tool.ui_v2.saas_profile_store import new_saas_profile_disk_store
from invoice_tool.ui_v2.saas_profile_surface import (
    build_saas_profile_surface_vm,
    surface_payload_as_dict,
)

PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "AMEX-1005",
    "vobaai",
    "vobaep",
    "Bismarck",
    "Rötestr",
    "97368",
    "DE189",
)

CLOUD_MARKERS = (
    "Mandant",
    "Cloud-Sync",
    "Multi-Tenant",
    "SaaS-Cloud",
)


def test_blank_saas_profile_has_safe_classification_policy_defaults() -> None:
    blank = build_blank_saas_profile()
    policy = blank.classification_policy
    assert isinstance(policy, ClassificationPolicy)
    assert policy.supplier_bank_details_are_payment_evidence is False
    assert policy.require_explicit_payer_payment_evidence is True
    assert policy.apple_pay_requires_known_card_reference is True
    assert policy.unknown_payment_target == "unklar"
    assert policy.detect_invoice_direction is True
    assert policy.outgoing_invoices_target in {"unklar", "documents"}
    assert policy.detect_accounting_reports is True
    assert policy.accounting_reports_target in {"unklar", "documents"}
    assert policy.mixed_business_private_address_target == "unklar"
    assert policy.address_policy.billing_address_takes_precedence is True
    assert policy.address_policy.delivery_address_only_is_not_business_evidence is True
    assert policy.address_policy.mixed_billing_delivery_address_target == "unklar"
    assert policy.address_policy.private_billing_business_delivery_target == "unklar"
    assert policy.business_document_policy.classify_order_confirmations is True
    assert policy.business_document_policy.order_confirmation_is_not_invoice is True
    assert (
        policy.business_document_policy.non_invoice_business_document_target == "unklar"
    )
    idp = policy.invoice_detection_policy
    assert idp.invoice_indicators_override_format_notes is True
    assert idp.format_availability_notes_are_not_document_type is True
    assert idp.filename_is_not_source_of_truth is True
    pep = policy.payment_evidence_policy
    assert pep.generic_credit_card_without_identifier_target == "unklar"
    assert pep.card_payment_requires_known_reference is True
    assert pep.supplier_bank_details_are_not_payer_evidence is True
    bap = policy.business_assignment_policy
    assert bap.business_billing_address_assigns_business_context is True
    assert bap.ambiguous_items_do_not_override_business_billing_address is True
    assert bap.organization_identifiers_are_profile_configured is True
    tool = policy.software_ai_tool_policy
    assert tool.detect_ai_coding_tools is True
    assert tool.require_business_signal_for_ai_tool_assignment is True
    assert tool.preserve_category_for_refunds is True
    assert tool.unknown_tool_context_target == "unklar"


def test_default_policy_flags() -> None:
    policy = default_classification_policy()
    assert policy.supplier_bank_details_are_payment_evidence is False
    assert policy.require_explicit_payer_payment_evidence is True
    assert policy.apple_pay_requires_known_card_reference is True
    assert policy.unknown_payment_target == "unklar"
    assert policy.detect_invoice_direction is True
    assert policy.outgoing_invoices_target in {"unklar", "documents"}
    assert policy.detect_accounting_reports is True
    assert policy.accounting_reports_target in {"unklar", "documents"}
    assert policy.mixed_business_private_address_target == "unklar"
    assert policy.software_ai_tool_policy.detect_ai_coding_tools is True
    assert policy.software_ai_tool_policy.preserve_category_for_refunds is True


def test_policy_roundtrip_save_load(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    state = new_saas_profile_state_store()
    draft = state.begin_blank_profile()
    draft.profile_name = "Policy Profil"
    custom = ClassificationPolicy(
        require_explicit_payer_payment_evidence=True,
        supplier_bank_details_are_payment_evidence=False,
        apple_pay_requires_known_card_reference=True,
        unknown_payment_target="unklar",
        detect_invoice_direction=True,
        outgoing_invoices_target="documents",
        detect_accounting_reports=True,
        accounting_reports_target="documents",
        mixed_business_private_address_target="unklar",
    )
    draft.classification_policy = custom
    created = store.create_draft(display_name="Policy Save", profile_draft=draft)
    assert created.ok and created.draft_id
    loaded = store.load_draft(created.draft_id)
    assert loaded.ok and loaded.profile_draft is not None
    assert loaded.profile_draft.classification_policy.to_dict() == custom.to_dict()


def test_policy_roundtrip_export_import(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    state = new_saas_profile_state_store()
    draft = state.begin_blank_profile()
    draft.profile_name = "Export Policy"
    draft.classification_policy = ClassificationPolicy(
        outgoing_invoices_target="documents",
        accounting_reports_target="unklar",
    )
    created = store.create_draft(display_name="Export Policy", profile_draft=draft)
    assert created.ok and created.draft_id
    export_path = tmp_path / "policy_export.json"
    assert store.export_draft(created.draft_id, export_path).ok
    imported = store.import_draft(export_path)
    assert imported.ok and imported.profile_draft is not None
    policy = imported.profile_draft.classification_policy
    assert policy.outgoing_invoices_target == "documents"
    assert policy.accounting_reports_target == "unklar"
    assert policy.require_explicit_payer_payment_evidence is True


def test_policy_survives_draft_list_rename_delete(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    state = new_saas_profile_state_store()
    draft = state.begin_blank_profile()
    draft.classification_policy = ClassificationPolicy(
        mixed_business_private_address_target="unklar",
        accounting_reports_target="documents",
    )
    created = store.create_draft(display_name="Rename Policy", profile_draft=draft)
    assert created.ok and created.draft_id
    renamed = store.rename_draft(created.draft_id, "Umbenannt Policy")
    assert renamed.ok
    loaded = store.load_draft(created.draft_id)
    assert loaded.ok and loaded.profile_draft is not None
    assert (
        loaded.profile_draft.classification_policy.accounting_reports_target
        == "documents"
    )
    other = store.create_draft(display_name="Keep", profile_draft=state.begin_blank_profile())
    assert other.ok
    deleted = store.delete_draft(created.draft_id)
    assert deleted.ok
    remaining = store.load_draft(other.draft_id)
    assert remaining.ok
    assert remaining.profile_draft is not None
    assert remaining.profile_draft.classification_policy.require_explicit_payer_payment_evidence


def test_ui_viewmodel_texts_contain_required_phrases() -> None:
    vm = build_saas_profile_surface_vm()
    blob = " ".join(vm.classification_policy_texts) + " ".join(vm.review_hints)
    blob += " ".join(vm.ui_labels.values())
    required = (
        "Zahlungsweg-Erkennung",
        "Lieferanten-IBAN/BIC nicht als Zahlungsweg",
        "Apple Pay ohne Karten-/Konto-Endung zur Prüfung",
        "Rechnungsrichtung erkennen",
        "Ausgangsrechnung",
        "Dokumenttyp-Erkennung",
        "Buchhaltungsauswertungen zur Prüfung",
        "Gemischte geschäftliche/private Adresssignale",
        "Rechnungsadresse vor Lieferadresse priorisieren",
        "Geschäftliche Lieferadresse allein reicht nicht",
        "Gemischte Rechnungs-/Lieferadresssignale zur Prüfung",
        "Bestellbestätigungen von Rechnungen unterscheiden",
        "Geschäftliche Bestelldokumente fachlich zuordnen",
        "Zahlungsmethode auch bei Nicht-Rechnungen erkennen",
        "Starke Rechnungsindikatoren vor Format-/Dokumentphrasen",
        "Format-Verfügbarkeitshinweise sind kein Dokumenttyp",
        "Dateiname ist keine Beweisquelle",
        "Unspezifische Kreditkarte ohne Kennung zur Prüfung",
        "Kartenzahlung erfordert bekannte Referenz",
        "Geschäftliche Rechnungsadresse setzt Business-Kontext",
        "Organisationskennungen sind profilkonfiguriert",
        "Software- und AI-Tools erkennen",
        "AI-, Coding- und Token-basierten Diensten",
        "Gutschriften/Refunds behalten die wirtschaftliche Kategorie",
        "Berufliche Signale erforderlich",
        "Ohne berufliche Signale: Zur Prüfung",
    )
    for phrase in required:
        assert phrase in blob, phrase


def test_ui_viewmodel_texts_contain_no_private_defaults() -> None:
    payload = surface_payload_as_dict()
    blob = json.dumps(payload, ensure_ascii=False)
    texts = " ".join(classification_policy_ui_texts())
    combined = blob + "\n" + texts
    for marker in PRIVATE_MARKERS:
        assert marker not in combined, marker
    # No private tax / street defaults as policy defaults
    assert "Rötestr." not in combined


def test_no_cloud_tenant_promise_in_policy_surface() -> None:
    vm = build_saas_profile_surface_vm()
    blob = " ".join(vm.review_hints) + " ".join(vm.classification_policy_texts)
    assert "Kein Cloud-/Mandantenbetrieb" in blob or "Cloud" in blob
    for marker in ("Multi-Tenant", "Cloud-Sync", "Mandantenfunktion"):
        assert marker not in blob


def test_classification_policy_from_dict_defaults_missing_keys() -> None:
    policy = classification_policy_from_dict({})
    assert policy.require_explicit_payer_payment_evidence is True
    assert policy.supplier_bank_details_are_payment_evidence is False
    assert policy.unknown_payment_target == "unklar"


def test_blank_draft_state_includes_policy() -> None:
    store = new_saas_profile_state_store()
    draft = store.begin_blank_profile()
    assert draft.classification_policy.apple_pay_requires_known_card_reference is True
    assert "classification_policy" in draft.to_dict()
