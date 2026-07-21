"""UI-v2 policy → runtime-intent bridge — non-GUI, no PDF, no processing-core."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

from invoice_tool.saas_product_model import (
    ClassificationPolicy,
    InvoiceDetectionPolicy,
    PaymentEvidencePolicy,
    BusinessAssignmentPolicy,
    default_classification_policy,
)
from invoice_tool.ui_v2.policy_runtime_bridge import (
    MSG_FILENAME_NOT_SOURCE_OF_TRUTH,
    MSG_GENERIC_CARD_UNCLEAR,
    MSG_POLICY_INCOMPLETE,
    MSG_SUPPLIER_IBAN_NOT_PAYER,
    MSG_UNKNOWN_EVIDENCE_REVIEW,
    RuntimePolicyIntent,
    build_default_safe_runtime_policy_intent,
    build_runtime_policy_intent,
    describe_future_local_processing_adapter_consumption,
)
from invoice_tool.ui_v2.processing_contract import (
    SOURCE_EXPLICIT_USER_SELECTION,
    NotYetConnectedProcessingService,
    ProcessingRunRequest,
)

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "invoice_tool" / "ui_v2" / "policy_runtime_bridge.py"

PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX-1005",
    "vobaai",
    "vobaep",
    "/Users/",
    "Desktop/Programm Belegerfassung",
    "Rötestr",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "invoice_tool.processing",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
    "invoice_tool.run",
    "invoice_tool.gui",
    "invoice_tool.ui_shell",
    "invoice_tool.ui_workspace",
    "app_main",
)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


def test_bridge_produces_structured_runtime_policy_intent() -> None:
    result = build_runtime_policy_intent(default_classification_policy())
    assert result.status == "ready"
    assert isinstance(result.intent, RuntimePolicyIntent)
    payload = result.intent.to_dict()
    for key in (
        "invoice_detection_policy",
        "payment_evidence_policy",
        "business_assignment_policy",
        "review_policy",
        "filename_policy",
        "unknown_evidence_policy",
        "source_of_truth_policy",
    ):
        assert key in payload
        assert isinstance(payload[key], dict)


def test_filename_is_never_source_of_truth() -> None:
    result = build_runtime_policy_intent(default_classification_policy())
    assert result.intent is not None
    assert result.intent.filename_policy["filename_is_source_of_truth"] is False
    assert result.intent.filename_policy["filename_is_not_source_of_truth"] is True
    assert result.intent.invoice_detection_policy["filename_is_not_source_of_truth"] is True
    assert result.intent.source_of_truth_policy["filename_is_source_of_truth"] is False
    assert MSG_FILENAME_NOT_SOURCE_OF_TRUTH in result.warnings


def test_unknown_payment_and_business_evidence_map_to_review() -> None:
    result = build_runtime_policy_intent(default_classification_policy())
    assert result.intent is not None
    assert result.intent.review_policy["unknown_payment_target"] == "unklar"
    assert result.intent.review_policy["unknown_business_target"] == "unklar"
    assert result.intent.unknown_evidence_policy["unknown_payment_evidence_target"] == "unklar"
    assert result.intent.unknown_evidence_policy["unknown_business_evidence_target"] == "unklar"
    assert result.intent.review_policy["unknown_evidence_goes_to_review"] is True
    assert MSG_UNKNOWN_EVIDENCE_REVIEW in (result.review_required_reason or "")


def test_business_payment_account_rules_require_profile_config() -> None:
    result = build_runtime_policy_intent(default_classification_policy())
    assert result.intent is not None
    bap = result.intent.business_assignment_policy
    assert bap["organization_identifiers_are_profile_configured"] is True
    assert bap["business_payment_account_rules_are_profile_configured"] is True
    assert result.intent.source_of_truth_policy["profile_configured_evidence_required"] is True
    assert result.intent.source_of_truth_policy["private_defaults_allowed"] is False


def test_supplier_iban_alone_is_not_payer_evidence() -> None:
    result = build_runtime_policy_intent(default_classification_policy())
    assert result.intent is not None
    pep = result.intent.payment_evidence_policy
    assert pep["supplier_bank_details_are_payment_evidence"] is False
    assert pep["supplier_bank_details_are_not_payer_evidence"] is True
    assert result.intent.unknown_evidence_policy["supplier_iban_alone_is_not_payer_evidence"] is True
    assert MSG_SUPPLIER_IBAN_NOT_PAYER in result.warnings


def test_generic_card_text_without_account_reference_is_unclear() -> None:
    result = build_runtime_policy_intent(default_classification_policy())
    assert result.intent is not None
    pep = result.intent.payment_evidence_policy
    assert pep["card_payment_requires_known_reference"] is True
    assert pep["generic_credit_card_without_identifier_target"] == "unklar"
    assert (
        result.intent.unknown_evidence_policy[
            "generic_card_text_without_configured_account_reference_target"
        ]
        == "unklar"
    )
    assert MSG_GENERIC_CARD_UNCLEAR in result.warnings


def test_no_private_hardcoded_defaults_in_bridge_source_or_intent() -> None:
    src = BRIDGE.read_text(encoding="utf-8")
    result = build_default_safe_runtime_policy_intent()
    blob = src + "\n" + str(result.to_dict())
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    # Generic product wording only — no private tenant names as defaults.
    assert "Hadi" not in blob
    assert "SOMAA" not in blob


def test_bridge_does_not_import_or_call_processing_core() -> None:
    for name in _imported_modules(BRIDGE):
        assert not any(
            name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_IMPORT_PREFIXES
        ), name

    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    importlib.import_module("invoice_tool.ui_v2.policy_runtime_bridge")
    build_runtime_policy_intent(default_classification_policy())
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in (
        "invoice_tool.processing",
        "invoice_tool.run",
        "invoice_tool.routing",
        "invoice_tool.classification",
        "invoice_tool.target_routing",
        "invoice_tool.routing_guards",
    ):
        assert forbidden not in newly, forbidden


def test_missing_policy_is_incomplete() -> None:
    result = build_runtime_policy_intent(None)
    assert result.status == "incomplete"
    assert result.intent is None
    assert "classification_policy" in result.missing_fields
    assert MSG_POLICY_INCOMPLETE in result.warnings


def test_unsafe_filename_truth_policy_is_blocked() -> None:
    unsafe = ClassificationPolicy(
        invoice_detection_policy=InvoiceDetectionPolicy(filename_is_not_source_of_truth=False),
    )
    result = build_runtime_policy_intent(unsafe)
    assert result.status == "blocked"
    assert result.intent is not None
    # Safe overlay still present for future adapters.
    assert result.intent.filename_policy["filename_is_source_of_truth"] is False


def test_unsafe_supplier_iban_as_payment_is_blocked() -> None:
    unsafe = ClassificationPolicy(supplier_bank_details_are_payment_evidence=True)
    result = build_runtime_policy_intent(unsafe)
    assert result.status == "blocked"
    assert MSG_SUPPLIER_IBAN_NOT_PAYER in result.warnings


def test_profile_dict_and_draft_shapes_are_accepted() -> None:
    policy = default_classification_policy()
    from_dict = build_runtime_policy_intent({"classification_policy": policy.to_dict()})
    assert from_dict.status == "ready"
    assert from_dict.intent is not None

    class _Draft:
        classification_policy = policy

    from_draft = build_runtime_policy_intent(_Draft())
    assert from_draft.status == "ready"


def test_processing_run_request_carries_policy_intent_safely() -> None:
    bridge = build_runtime_policy_intent(default_classification_policy())
    request = ProcessingRunRequest(
        input_folder="selected-inbox",
        source=SOURCE_EXPLICIT_USER_SELECTION,
        dry_run=True,
        policy_intent=bridge.intent,
        policy_bridge_result=bridge,
    )
    assert request.policy_intent is not None
    assert request.policy_bridge_result is not None
    assert request.policy_bridge_result.status == "ready"
    assert request.effective_policy_bridge_result() is bridge


def test_not_yet_connected_still_does_not_process_with_ready_policy(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    pdf = inbox / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    before = pdf.read_bytes()
    bridge = build_runtime_policy_intent(default_classification_policy())
    service = NotYetConnectedProcessingService()
    state = service.start_run(
        ProcessingRunRequest(
            input_folder=str(inbox),
            source=SOURCE_EXPLICIT_USER_SELECTION,
            policy_intent=bridge.intent,
            policy_bridge_result=bridge,
        )
    )
    assert state.status == "blocked"
    assert state.results == tuple()
    assert state.review_items == tuple()
    assert pdf.exists()
    assert pdf.read_bytes() == before


def test_incomplete_policy_yields_not_configured() -> None:
    service = NotYetConnectedProcessingService()
    state = service.validate_request(
        ProcessingRunRequest(
            input_folder="selected-inbox",
            source=SOURCE_EXPLICIT_USER_SELECTION,
            policy_bridge_result=build_runtime_policy_intent(None),
        )
    )
    assert state.status == "not_configured"
    assert MSG_POLICY_INCOMPLETE in state.message or "vollständig konfiguriert" in state.message
    assert state.results == tuple()


def test_future_adapter_placeholder_documents_consumption() -> None:
    text = describe_future_local_processing_adapter_consumption()
    assert "RuntimePolicyIntent" in text
    assert "processing.py" in text or "PO-gated" in text
    assert "filename" in text.lower()


def test_org_ids_not_profile_configured_blocks() -> None:
    unsafe = ClassificationPolicy(
        business_assignment_policy=BusinessAssignmentPolicy(
            organization_identifiers_are_profile_configured=False
        ),
        payment_evidence_policy=PaymentEvidencePolicy(),
    )
    result = build_runtime_policy_intent(unsafe)
    assert result.status == "blocked"
