"""Track-B UI-v2 profile/policy model — non-GUI, no PDF, no processing-core."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.saas_product_model import default_classification_policy
from invoice_tool.ui_v2.profile_policy import (
    MSG_CARD_HINT_WITHOUT_REF_UNCLEAR,
    MSG_CONFIGS_APPLY_RULES,
    MSG_FILENAME_NOT_TRUTH,
    MSG_PAYMENT_BUSINESS_PER_PROFILE,
    MSG_PROFILES_CONTAIN_RULES,
    MSG_SUPPLIER_IBAN_NOT_USER_PAYMENT,
    MSG_TARGETS_AFTER_SAFE_CONFIG,
    MSG_UNCLEAR_NOT_AUTO,
    MSG_UNCLEAR_STAYS_REVIEW,
    MSG_WITHOUT_EVIDENCE_REVIEW,
    AccountEvidenceRule,
    BusinessEvidenceRule,
    PaymentEvidenceRule,
    ProfilePolicyIdentity,
    align_profile_policy_with_runtime_intent,
    assert_no_private_profile_policy_defaults,
    blank_profile_policy_view_model,
    build_configurations_page_policy_panel_vm,
    build_profile_policy_view_model,
    build_profiles_page_policy_panel_vm,
    profile_policy_core_rule_messages,
    validate_profile_policy_readiness,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "invoice_tool" / "ui_v2" / "profile_policy.py"
PROCESSING_CORE = (
    "invoice_tool.processing",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
    "invoice_tool.run",
)
PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX",
    "voba",
    "/Users/",
    "Desktop/",
)


def test_blank_profile_policy_has_safe_empty_defaults() -> None:
    vm = blank_profile_policy_view_model()
    assert vm.identity.is_blank()
    assert vm.business.organization_identifiers == ()
    assert vm.payment.payment_identifiers == ()
    assert vm.account.account_reference_hints == ()
    assert vm.readiness_status == "empty"
    assert vm.has_private_defaults is False
    assert vm.filename_is_source_of_truth is False
    assert vm.supplier_iban_alone_is_payer_evidence is False
    assert vm.generic_card_without_account_ref_is_clear is False
    assert_no_private_profile_policy_defaults(vm)


def test_no_private_default_profile_exists() -> None:
    vm = blank_profile_policy_view_model()
    assert vm.identity.display_name == ""
    assert vm.identity.profile_id == ""
    panel = build_profiles_page_policy_panel_vm(profile_count=0)
    assert panel.empty is True
    assert panel.has_private_defaults is False
    src = MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        # Markers may appear only inside PRIVATE_DEFAULT_MARKERS guard tuple.
        if marker in ("Hadi", "SOMAA", "Bismarck", "AMEX", "voba", "/Users/", "Desktop/"):
            # Ensure they are not used as assignment defaults outside the guard list.
            assert f'display_name="{marker}"' not in src
            assert f"profile_id=\"{marker}\"" not in src
            assert f'"{marker}"' not in src.split("PRIVATE_DEFAULT_MARKERS")[0]


def test_business_identifiers_are_profile_configurable() -> None:
    vm = build_profile_policy_view_model(
        display_name="Mandant A",
        profile_id="profile-a",
        organization_identifiers=("ORG-1", "ORG-2"),
        billing_address_hints=("Billing Hint"),
    )
    assert vm.business.has_configured_evidence() is True
    assert vm.business.organization_identifiers == ("ORG-1", "ORG-2")
    assert vm.rules_are_profile_specific is True


def test_payment_and_account_evidence_are_profile_configurable() -> None:
    vm = build_profile_policy_view_model(
        display_name="Mandant B",
        profile_id="profile-b",
        payment_identifiers=("PAY-REF-1",),
        account_reference_hints=("ACC-****1234",),
        card_reference_hints=("CARD-****99",),
    )
    assert vm.payment.has_configured_evidence() is True
    assert vm.account.has_configured_evidence() is True
    assert vm.payment.supplier_iban_alone_is_payer_evidence is False
    assert vm.account.generic_card_without_reference_is_clear is False


def test_missing_evidence_goes_to_review_readiness() -> None:
    vm = build_profile_policy_view_model(
        display_name="Mandant C",
        profile_id="profile-c",
    )
    assert vm.readiness_status == "review"
    assert MSG_WITHOUT_EVIDENCE_REVIEW in vm.readiness_reasons
    assert vm.unclear_evidence_goes_to_review is True


def test_filename_is_never_source_of_truth() -> None:
    vm = build_profile_policy_view_model(display_name="Mandant D", profile_id="p-d")
    assert vm.filename_is_source_of_truth is False
    assert MSG_FILENAME_NOT_TRUTH in vm.honest_copy
    messages = profile_policy_core_rule_messages()
    assert MSG_FILENAME_NOT_TRUTH in messages


def test_supplier_iban_alone_is_not_payer_evidence() -> None:
    vm = blank_profile_policy_view_model()
    assert vm.supplier_iban_alone_is_payer_evidence is False
    assert vm.payment.supplier_iban_alone_is_payer_evidence is False
    assert MSG_SUPPLIER_IBAN_NOT_USER_PAYMENT in vm.honest_copy


def test_generic_card_without_configured_account_ref_stays_review() -> None:
    vm = build_profile_policy_view_model(
        display_name="Mandant E",
        profile_id="p-e",
        organization_identifiers=("ORG"),
        payment_identifiers=("PAY"),
        # no account/card refs
    )
    assert vm.generic_card_without_account_ref_is_clear is False
    assert vm.readiness_status == "review"
    assert MSG_CARD_HINT_WITHOUT_REF_UNCLEAR in vm.honest_copy


def test_validate_ready_when_evidence_and_config_present() -> None:
    status, reasons = validate_profile_policy_readiness(
        identity=ProfilePolicyIdentity(display_name="Mandant F", profile_id="p-f"),
        business=BusinessEvidenceRule(organization_identifiers=("ORG",)),
        payment=PaymentEvidenceRule(payment_identifiers=("PAY",)),
        account=AccountEvidenceRule(account_reference_hints=("ACC",)),
        configuration_present=True,
        policy_intent_status="ready",
    )
    assert status == "ready"
    assert MSG_PAYMENT_BUSINESS_PER_PROFILE in reasons


def test_runtime_policy_intent_alignment_generic() -> None:
    result = align_profile_policy_with_runtime_intent(
        classification_policy=default_classification_policy()
    )
    assert result.status == "ready"
    assert result.intent is not None
    assert result.intent.filename_policy["filename_is_source_of_truth"] is False
    assert (
        result.intent.payment_evidence_policy[
            "supplier_bank_details_are_payment_evidence"
        ]
        is False
    )
    assert (
        result.intent.unknown_evidence_policy[
            "generic_card_text_without_configured_account_reference_target"
        ]
        == "unklar"
    )


def test_missing_policy_alignment_is_incomplete() -> None:
    result = align_profile_policy_with_runtime_intent(classification_policy=None)
    assert result.status == "incomplete"
    assert result.intent is None


def test_profiles_panel_copy() -> None:
    panel = build_profiles_page_policy_panel_vm(profile_count=0)
    blob = " ".join(panel.honest_copy + (panel.banner,))
    assert MSG_PROFILES_CONTAIN_RULES in blob
    assert MSG_PAYMENT_BUSINESS_PER_PROFILE in blob
    assert MSG_WITHOUT_EVIDENCE_REVIEW in blob


def test_configurations_panel_copy() -> None:
    panel = build_configurations_page_policy_panel_vm(
        active_profile_name="Mandant G",
        policy_readiness_status="review",
        unmatched_configured=False,
    )
    blob = " ".join(panel.honest_copy + (panel.banner,))
    assert MSG_CONFIGS_APPLY_RULES in blob
    assert MSG_UNCLEAR_NOT_AUTO in blob
    assert MSG_TARGETS_AFTER_SAFE_CONFIG in blob
    assert panel.has_private_destination_defaults is False
    assert panel.has_productive_execution_toggle is False
    assert panel.scans_folders is False
    assert panel.processes_pdfs is False


def test_no_private_tokens_in_module_defaults() -> None:
    src = MODULE.read_text(encoding="utf-8")
    vm = blank_profile_policy_view_model()
    blob = src + "\n" + str(vm)
    # Guard list may mention markers; blank VM payload must not contain them.
    for marker in PRIVATE_MARKERS:
        assert marker not in str(vm), marker
    assert 'display_name="Hadi"' not in src
    assert 'display_name="SOMAA"' not in src


def test_no_productive_execution_toggle() -> None:
    vm = blank_profile_policy_view_model()
    assert vm.has_productive_execution_toggle is False
    assert vm.productive_execution_enabled is False
    panel = build_profiles_page_policy_panel_vm(profile_count=1, selected_display_name="X")
    assert panel.has_productive_execution_toggle is False


def test_no_processing_core_imports() -> None:
    src = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    for forbidden in PROCESSING_CORE:
        assert forbidden not in imported
        assert forbidden not in src


def test_core_rule_messages_include_required_copy() -> None:
    messages = profile_policy_core_rule_messages()
    assert MSG_FILENAME_NOT_TRUTH in messages
    assert MSG_UNCLEAR_STAYS_REVIEW in messages
    assert MSG_SUPPLIER_IBAN_NOT_USER_PAYMENT in messages
    assert MSG_CARD_HINT_WITHOUT_REF_UNCLEAR in messages
