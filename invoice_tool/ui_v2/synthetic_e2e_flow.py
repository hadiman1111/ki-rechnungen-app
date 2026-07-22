"""Track-B UI-v2 synthetic end-to-end product flow helpers.

Pure helpers that assemble an explicit synthetic sandbox case and run the
Track-B product modules together without real invoices, OCR/AI, folder scan,
productive execution, or processing-core imports.

Synthetic labels only (document-001 …). Planned destination hints stay under
an explicit sandbox root. Writes are never performed by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from invoice_tool.saas_product_model import default_classification_policy
from invoice_tool.ui_v2.export_reporting import (
    RunReportViewModel,
    build_run_export_payload,
    build_run_report_view_model,
)
from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.policy_runtime_bridge import (
    RuntimePolicyBridgeResult,
    build_runtime_policy_intent,
)
from invoice_tool.ui_v2.processing_contract import ProcessingRunRequest
from invoice_tool.ui_v2.processing_state import (
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.profile_policy import (
    ProfilePolicyViewModel,
    build_profile_policy_view_model,
)
from invoice_tool.ui_v2.review_workflow import (
    ReviewQueueViewModel,
    build_review_queue_view_model,
)
from invoice_tool.ui_v2.run_result_display import (
    RunResultDisplayShellVM,
    build_run_result_display_shell,
)
from invoice_tool.ui_v2.sandbox_execution_boundary import (
    MSG_SANDBOX_EXECUTION_COMPLETED,
    SandboxCoreCallArgs,
    SandboxCoreCallResult,
)
from invoice_tool.ui_v2.sandbox_processing_gate import (
    SandboxPathValidationResult,
    build_sandbox_run_request,
    evaluate_sandbox_gate,
)

SYNTHETIC_PROFILE_ID = "synthetic-profile-001"
SYNTHETIC_CONFIGURATION_ID = "synthetic-config-001"
SYNTHETIC_RUN_ID = "synthetic-e2e-run-001"
SYNTHETIC_PROFILE_DISPLAY = "Synthetic Pilot Profile"

DOC_SUCCESS = "document-001"
DOC_REVIEW = "document-002"
DOC_ERROR = "document-003"

MSG_SYNTHETIC_ERROR = "synthetic extraction failed: document-003"
MSG_SYNTHETIC_REVIEW_REASON = "Zuordnung unklar — synthetischer Prüffall"
MSG_SYNTHETIC_EVIDENCE = "Kein eindeutiger synthetischer Nachweis"
MSG_SYNTHETIC_NEXT_ACTION = "Manuell prüfen (synthetischer Pilotfall)"

SYNTHETIC_MARKERS = (
    "document-001",
    "document-002",
    "document-003",
    "synthetic",
)


@dataclass(frozen=True)
class SyntheticE2ECase:
    """Explicit synthetic sandbox layout + fixture payload — no real invoices."""

    sandbox_root: str
    input_folder: str
    output_folder: str
    original_source_folder: str
    profile_id: str = SYNTHETIC_PROFILE_ID
    configuration_id: str = SYNTHETIC_CONFIGURATION_ID
    run_id: str = SYNTHETIC_RUN_ID
    profile_display_name: str = SYNTHETIC_PROFILE_DISPLAY

    @property
    def success_document(self) -> str:
        return DOC_SUCCESS

    @property
    def review_document(self) -> str:
        return DOC_REVIEW

    @property
    def error_document(self) -> str:
        return DOC_ERROR

    def planned_destination_hint(self, document_name: str) -> str:
        return f"{self.output_folder}/planned/{document_name}.pdf"


@dataclass(frozen=True)
class SyntheticE2EProductFlowResult:
    """Assembled Track-B product-flow outcome from synthetic data only."""

    case: SyntheticE2ECase
    request: ProcessingRunRequest
    gate: SandboxPathValidationResult
    boundary_args: SandboxCoreCallArgs | None
    boundary_result: SandboxCoreCallResult
    run_state: ProcessingRunState
    workspace_shell: RunResultDisplayShellVM
    workspace_report: RunReportViewModel
    review_queue: ReviewQueueViewModel
    export_payload: dict
    profile_policy: ProfilePolicyViewModel
    productive_blocked: bool


def build_synthetic_e2e_case(tmp_root: Path | str) -> SyntheticE2ECase:
    """Build a synthetic sandbox layout under an explicit tmp root only.

    Creates empty sandbox/original directories for path realism in tests.
    Does not copy real invoices, does not write PDF content, does not scan
    outside ``tmp_root``.
    """

    root = Path(tmp_root)
    sandbox = root / "synthetic-sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    original = root / "synthetic-original-source"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    original.mkdir(parents=True, exist_ok=True)
    return SyntheticE2ECase(
        sandbox_root=str(sandbox),
        input_folder=str(inbox),
        output_folder=str(outbox),
        original_source_folder=str(original),
    )


def build_synthetic_policy_bridge() -> RuntimePolicyBridgeResult:
    """Generic policy bridge for synthetic readiness — no private defaults."""

    return build_runtime_policy_intent(default_classification_policy())


def build_synthetic_profile_policy(case: SyntheticE2ECase) -> ProfilePolicyViewModel:
    """Profile/policy readiness VM with generic synthetic identifiers only."""

    return build_profile_policy_view_model(
        display_name=case.profile_display_name,
        profile_id=case.profile_id,
        organization_identifiers=("ORG-SYNTHETIC-001",),
        billing_address_hints=("Synthetic Billing Street 1",),
        payment_identifiers=("PAY-SYNTHETIC-001",),
        account_reference_hints=("ACC-SYNTHETIC-001",),
        card_reference_hints=("CARD-SYNTHETIC-001",),
        classification_policy=default_classification_policy(),
        configuration_present=True,
    )


def build_synthetic_sandbox_request(
    case: SyntheticE2ECase,
    *,
    copied_data_confirmed: bool = True,
    user_confirmed_start: bool = True,
    dry_run: bool = True,
    productive_execution_allowed: bool = False,
) -> ProcessingRunRequest:
    """Build an explicit sandbox request from the synthetic case."""

    bridge = build_synthetic_policy_bridge()
    request = build_sandbox_run_request(
        sandbox_root=case.sandbox_root,
        input_folder=case.input_folder,
        output_folder=case.output_folder,
        original_source_folder=case.original_source_folder,
        profile_id=case.profile_id,
        configuration_id=case.configuration_id,
        copied_data_confirmed=copied_data_confirmed,
        user_confirmed_start=user_confirmed_start,
        dry_run=dry_run,
        policy_intent=bridge.intent,
        policy_bridge_result=bridge,
    )
    if productive_execution_allowed:
        # Explicit override for negative tests — still blocked by gate/adapter.
        return ProcessingRunRequest(
            input_folder=request.input_folder,
            output_folder=request.output_folder,
            profile_id=request.profile_id,
            configuration_id=request.configuration_id,
            dry_run=request.dry_run,
            source=request.source,
            policy_intent=request.policy_intent,
            policy_bridge_result=request.policy_bridge_result,
            user_confirmed_start=request.user_confirmed_start,
            sandbox_mode=request.sandbox_mode,
            sandbox_root=request.sandbox_root,
            original_source_folder=request.original_source_folder,
            copied_data_confirmed=request.copied_data_confirmed,
            productive_execution_allowed=True,
            execution_scope="productive",
        )
    return request


def build_synthetic_boundary_result(case: SyntheticE2ECase) -> SandboxCoreCallResult:
    """Stub boundary payload: one success, one review item, one error."""

    success = ProcessingResultSummary(
        document_name=case.success_document,
        document_type="dokument",
        classification_status="ok",
        status_label="OK",
        confidence_label="hoch",
        target_hint=case.planned_destination_hint(case.success_document),
    )
    # Failed result row remains separated from the free-form error string.
    failed = ProcessingResultSummary(
        document_name=case.error_document,
        document_type="dokument",
        classification_status="failed",
        status_label="fehlgeschlagen",
        target_hint=case.planned_destination_hint(case.error_document),
    )
    review = ProcessingReviewItem(
        document_name=case.review_document,
        reason=MSG_SYNTHETIC_REVIEW_REASON,
        status_label="unklar",
        document_id=case.review_document,
        evidence_summary=MSG_SYNTHETIC_EVIDENCE,
        next_action_hint=MSG_SYNTHETIC_NEXT_ACTION,
    )
    return SandboxCoreCallResult(
        ok=True,
        message=MSG_SANDBOX_EXECUTION_COMPLETED,
        run_id=case.run_id,
        results=(success, failed),
        review_items=(review,),
        errors=(MSG_SYNTHETIC_ERROR,),
    )


def build_synthetic_processing_state(case: SyntheticE2ECase) -> ProcessingRunState:
    """Map the synthetic boundary result into ProcessingRunState without IO."""

    from invoice_tool.ui_v2.sandbox_execution_boundary import (
        map_sandbox_core_result_to_run_state,
    )

    return map_sandbox_core_result_to_run_state(
        build_synthetic_boundary_result(case),
        execution_gate="ready_for_sandbox_execution",
        dry_run_gate="unsupported_without_core_change",
        core_dry_run_status="unsupported_without_core_change",
    )


def make_synthetic_boundary_runner(
    case: SyntheticE2ECase,
) -> Callable[[SandboxCoreCallArgs], SandboxCoreCallResult]:
    """Injectable runner that returns the synthetic fixture and records args."""

    def _runner(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        _ = args
        return build_synthetic_boundary_result(case)

    return _runner


def run_synthetic_track_b_product_flow(
    tmp_root: Path | str,
    *,
    copied_data_confirmed: bool = True,
    user_confirmed_start: bool = True,
) -> SyntheticE2EProductFlowResult:
    """Run the Track-B product modules on synthetic data only.

    Flow: sandbox setup → profile readiness → gate → stubbed boundary →
    adapter mapping → workspace display/report → review queue → export preview.
    Never calls OCR/AI, never imports processing-core, never writes exports.
    """

    case = build_synthetic_e2e_case(tmp_root)
    profile_policy = build_synthetic_profile_policy(case)
    request = build_synthetic_sandbox_request(
        case,
        copied_data_confirmed=copied_data_confirmed,
        user_confirmed_start=user_confirmed_start,
    )
    gate = evaluate_sandbox_gate(request)

    captured: list[SandboxCoreCallArgs] = []

    def runner(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        captured.append(args)
        return build_synthetic_boundary_result(case)

    adapter = LocalProcessingAdapter(sandbox_runner=runner)
    # Productive path must stay blocked even when asked.
    productive_request = build_synthetic_sandbox_request(
        case,
        copied_data_confirmed=True,
        user_confirmed_start=True,
        dry_run=False,
        productive_execution_allowed=True,
    )
    productive_state = adapter.start_run(productive_request)
    productive_blocked = (
        productive_state.status == "blocked"
        and productive_state.execution_gate == "blocked_productive_execution"
    )

    run_state = adapter.start_run(request)
    boundary_args = captured[0] if captured else None
    boundary_result = (
        build_synthetic_boundary_result(case)
        if boundary_args is not None
        else SandboxCoreCallResult(ok=False, message="boundary not invoked", errors=())
    )

    workspace_shell = build_run_result_display_shell(run_state)
    workspace_report = build_run_report_view_model(run_state)
    review_queue = build_review_queue_view_model(run_state)
    export_payload = build_run_export_payload(workspace_report)

    return SyntheticE2EProductFlowResult(
        case=case,
        request=request,
        gate=gate,
        boundary_args=boundary_args,
        boundary_result=boundary_result,
        run_state=run_state,
        workspace_shell=workspace_shell,
        workspace_report=workspace_report,
        review_queue=review_queue,
        export_payload=export_payload,
        profile_policy=profile_policy,
        productive_blocked=productive_blocked,
    )


__all__ = (
    "DOC_ERROR",
    "DOC_REVIEW",
    "DOC_SUCCESS",
    "MSG_SYNTHETIC_ERROR",
    "MSG_SYNTHETIC_EVIDENCE",
    "MSG_SYNTHETIC_NEXT_ACTION",
    "MSG_SYNTHETIC_REVIEW_REASON",
    "SYNTHETIC_CONFIGURATION_ID",
    "SYNTHETIC_MARKERS",
    "SYNTHETIC_PROFILE_DISPLAY",
    "SYNTHETIC_PROFILE_ID",
    "SYNTHETIC_RUN_ID",
    "SyntheticE2ECase",
    "SyntheticE2EProductFlowResult",
    "build_synthetic_boundary_result",
    "build_synthetic_e2e_case",
    "build_synthetic_policy_bridge",
    "build_synthetic_processing_state",
    "build_synthetic_profile_policy",
    "build_synthetic_sandbox_request",
    "make_synthetic_boundary_runner",
    "run_synthetic_track_b_product_flow",
)
