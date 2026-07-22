"""Track-B UI-v2 sandbox validation with copied-realistic fixture data.

More realistic than synthetic E2E labels, still sandbox-only and safe:
- fixture files only under pytest tmp_path / explicit sandbox root
- monkeypatched boundary results (no OCR/AI, no processing-core)
- original source folders remain exclusion metadata only
- no private vendor/payment defaults, no filename-as-truth

Validation scaffolding only — not production classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from invoice_tool.saas_product_model import default_classification_policy
from invoice_tool.ui_v2.clarity_copy import (
    MSG_CLARITY_COPIED_DATA_ONLY_REPORT,
    MSG_CLARITY_FILENAME_NOT_TRUTH,
    MSG_CLARITY_NO_ORIGINAL_FOLDERS,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
    MSG_CLARITY_SANDBOX_COPIED_RUN,
    track_b_clarity_lines,
)
from invoice_tool.ui_v2.export_reporting import (
    SECTION_DESTINATIONS,
    SECTION_FAILED,
    SECTION_RECOGNIZED,
    SECTION_SUMMARY,
    SECTION_UNCLEAR,
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
    map_sandbox_core_result_to_run_state,
)
from invoice_tool.ui_v2.sandbox_processing_gate import (
    SandboxPathValidationResult,
    build_sandbox_run_request,
    evaluate_sandbox_gate,
)

CopiedRealDataCategory = Literal[
    "recognized",
    "review_payment_unclear",
    "review_business_unclear",
    "error_unsupported",
]

UI_SECTION_RECOGNIZED = "recognized"
UI_SECTION_REVIEW = "review"
UI_SECTION_ERROR = "error"

EXPORT_SECTION_RECOGNIZED = "recognized"
EXPORT_SECTION_UNCLEAR = "unclear"
EXPORT_SECTION_FAILED = "failed"

DOC_INVOICE = "copied-invoice-001"
DOC_RECEIPT = "copied-receipt-002"
DOC_UNCLEAR = "copied-unclear-003"
DOC_ERROR = "copied-error-004"

COPIED_PROFILE_ID = "copied-realistic-profile-001"
COPIED_CONFIGURATION_ID = "copied-realistic-config-001"
COPIED_RUN_ID = "copied-realistic-run-001"
COPIED_PROFILE_DISPLAY = "Copied Realistic Pilot Profile"

MSG_PAYMENT_UNCLEAR = (
    "Zahlungsnachweis unklar — bitte manuell prüfen "
    "(kopierter realistischer Prüffall; Dateiname ist keine Belegwahrheit)"
)
MSG_BUSINESS_UNCLEAR = (
    "Betrieblich/persönlicher Nachweis unklar — bitte manuell prüfen "
    "(kopierter realistischer Prüffall; bleibt zur Prüfung)"
)
MSG_UNSUPPORTED_ERROR = (
    "Dokumenttyp nicht unterstützt — Fehler getrennt von Prüffällen "
    "(kopierter realistischer Fehlerfall: copied-error-004)"
)
MSG_PAYMENT_EVIDENCE = "Kein eindeutiger Zahlungsnachweis in Fixture-Metadaten"
MSG_BUSINESS_EVIDENCE = (
    "Kein eindeutiger betrieblich/persönlicher Nachweis in Fixture-Metadaten"
)
MSG_NEXT_ACTION_PAYMENT = "Manuell Zahlungszuordnung prüfen (Sandbox-Validierung)"
MSG_NEXT_ACTION_BUSINESS = (
    "Manuell betrieblich/persönliche Zuordnung prüfen (Sandbox-Validierung)"
)

COPIED_MARKERS = (
    DOC_INVOICE,
    DOC_RECEIPT,
    DOC_UNCLEAR,
    DOC_ERROR,
    "copied-realistic",
    "copied-",
)

# Neutral fake suffixes only — never real PDF bytes in the repository.
FAKE_FILE_SUFFIX = ".fakepdf"


@dataclass(frozen=True)
class CopiedRealDataValidationCase:
    """Explicit copied-realistic sandbox layout + neutral document labels."""

    sandbox_root: str
    input_folder: str
    output_folder: str
    original_source_folder: str
    fixture_files: tuple[str, ...] = field(default_factory=tuple)
    profile_id: str = COPIED_PROFILE_ID
    configuration_id: str = COPIED_CONFIGURATION_ID
    run_id: str = COPIED_RUN_ID
    profile_display_name: str = COPIED_PROFILE_DISPLAY

    @property
    def recognized_document(self) -> str:
        return DOC_INVOICE

    @property
    def payment_review_document(self) -> str:
        return DOC_RECEIPT

    @property
    def business_review_document(self) -> str:
        return DOC_UNCLEAR

    @property
    def error_document(self) -> str:
        return DOC_ERROR

    def planned_destination_hint(self, document_name: str) -> str:
        return f"{self.output_folder}/planned/{document_name}.pdf"


@dataclass(frozen=True)
class CopiedRealDataQualityRow:
    """Per-case quality checklist row — validation scaffolding only."""

    document_id: str
    category: CopiedRealDataCategory
    reason: str
    expected_ui_section: str
    expected_export_section: str
    filename_is_not_truth: bool = True


@dataclass(frozen=True)
class CopiedRealDataValidationReport:
    """Structured report for copied-realistic sandbox validation."""

    case: CopiedRealDataValidationCase
    quality_rows: tuple[CopiedRealDataQualityRow, ...]
    categories_present: tuple[CopiedRealDataCategory, ...]
    sandbox_input_under_root: bool
    sandbox_output_under_root: bool
    original_excluded_from_input: bool
    productive_blocked: bool
    boundary_paths_sandbox_only: bool
    five_questions_answered: bool
    review_payment_visible: bool
    review_business_visible: bool
    export_has_recognized: bool
    export_has_unclear: bool
    export_has_failed: bool
    export_has_destinations: bool
    export_has_summary: bool
    no_private_defaults: bool
    no_filename_as_truth: bool
    no_writes_outside_tmp: bool
    fixture_inside_tmp: bool
    user_clarity_lines: tuple[str, ...] = ()
    original_folders_excluded_message: str = MSG_CLARITY_NO_ORIGINAL_FOLDERS
    copied_data_only_message: str = MSG_CLARITY_COPIED_DATA_ONLY_REPORT
    sandbox_run_message: str = MSG_CLARITY_SANDBOX_COPIED_RUN
    productive_blocked_message: str = MSG_CLARITY_PRODUCTIVE_NOT_RELEASED
    filename_not_truth_message: str = MSG_CLARITY_FILENAME_NOT_TRUTH


@dataclass(frozen=True)
class CopiedRealDataValidationFlowResult:
    """Full Track-B product-flow outcome from copied-realistic sandbox data."""

    case: CopiedRealDataValidationCase
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
    validation_report: CopiedRealDataValidationReport


def build_copied_realistic_fixture(tmp_root: Path | str) -> CopiedRealDataValidationCase:
    """Create copied-realistic sandbox dirs + neutral fake files under tmp_root.

    Does not copy real invoices, does not write real PDF bytes, does not scan
    Desktop or original user folders. Fake files are empty stub files only.
    """

    root = Path(tmp_root)
    sandbox = root / "copied-realistic-sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    original = root / "copied-original-source-excluded"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    original.mkdir(parents=True, exist_ok=True)

    fixture_names = (DOC_INVOICE, DOC_RECEIPT, DOC_UNCLEAR, DOC_ERROR)
    written: list[str] = []
    for name in fixture_names:
        path = inbox / f"{name}{FAKE_FILE_SUFFIX}"
        # Empty stub file — never real PDF content, never OCR input.
        path.write_text("", encoding="utf-8")
        written.append(str(path))
        # Marker that classification must not treat filename as truth.
        marker = inbox / f"{name}.meta.txt"
        marker.write_text(
            "filename_is_not_source_of_truth=true\n"
            "classification_source=explicit_fixture_metadata\n",
            encoding="utf-8",
        )
        written.append(str(marker))

    return CopiedRealDataValidationCase(
        sandbox_root=str(sandbox),
        input_folder=str(inbox),
        output_folder=str(outbox),
        original_source_folder=str(original),
        fixture_files=tuple(written),
    )


def build_copied_policy_bridge() -> RuntimePolicyBridgeResult:
    """Generic policy bridge — no private tenant defaults."""

    return build_runtime_policy_intent(default_classification_policy())


def build_copied_profile_policy(
    case: CopiedRealDataValidationCase,
) -> ProfilePolicyViewModel:
    """Profile readiness with generic copied-realistic identifiers only."""

    return build_profile_policy_view_model(
        display_name=case.profile_display_name,
        profile_id=case.profile_id,
        organization_identifiers=("ORG-COPIED-REALISTIC-001",),
        billing_address_hints=("Copied Billing Street 1",),
        payment_identifiers=("PAY-COPIED-REALISTIC-001",),
        account_reference_hints=("ACC-COPIED-REALISTIC-001",),
        card_reference_hints=("CARD-COPIED-REALISTIC-001",),
        classification_policy=default_classification_policy(),
        configuration_present=True,
    )


def build_copied_sandbox_request(
    case: CopiedRealDataValidationCase,
    *,
    copied_data_confirmed: bool = True,
    user_confirmed_start: bool = True,
    dry_run: bool = True,
    productive_execution_allowed: bool = False,
) -> ProcessingRunRequest:
    """Build an explicit sandbox request from the copied-realistic case."""

    bridge = build_copied_policy_bridge()
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


def build_copied_boundary_result(
    case: CopiedRealDataValidationCase,
) -> SandboxCoreCallResult:
    """Stub boundary payload with recognized / payment / business / error cases.

    Categories come from explicit fixture metadata in this module — not from
    filename inference and not from OCR/AI.
    """

    recognized = ProcessingResultSummary(
        document_name=case.recognized_document,
        document_type="rechnung",
        classification_status="ok",
        status_label="OK",
        confidence_label="hoch",
        target_hint=case.planned_destination_hint(case.recognized_document),
    )
    failed = ProcessingResultSummary(
        document_name=case.error_document,
        document_type="dokument",
        classification_status="failed",
        status_label="fehlgeschlagen",
        target_hint=case.planned_destination_hint(case.error_document),
    )
    payment_review = ProcessingReviewItem(
        document_name=case.payment_review_document,
        reason=MSG_PAYMENT_UNCLEAR,
        status_label="unklar",
        document_id=case.payment_review_document,
        evidence_summary=MSG_PAYMENT_EVIDENCE,
        next_action_hint=MSG_NEXT_ACTION_PAYMENT,
    )
    business_review = ProcessingReviewItem(
        document_name=case.business_review_document,
        reason=MSG_BUSINESS_UNCLEAR,
        status_label="unklar",
        document_id=case.business_review_document,
        evidence_summary=MSG_BUSINESS_EVIDENCE,
        next_action_hint=MSG_NEXT_ACTION_BUSINESS,
    )
    return SandboxCoreCallResult(
        ok=True,
        message=MSG_SANDBOX_EXECUTION_COMPLETED,
        run_id=case.run_id,
        results=(recognized, failed),
        review_items=(payment_review, business_review),
        errors=(MSG_UNSUPPORTED_ERROR,),
    )


def build_copied_processing_state(
    case: CopiedRealDataValidationCase,
) -> ProcessingRunState:
    """Map the copied-realistic boundary result into ProcessingRunState."""

    return map_sandbox_core_result_to_run_state(
        build_copied_boundary_result(case),
        execution_gate="ready_for_sandbox_execution",
        dry_run_gate="unsupported_without_core_change",
        core_dry_run_status="unsupported_without_core_change",
    )


def make_copied_boundary_runner(
    case: CopiedRealDataValidationCase,
) -> Callable[[SandboxCoreCallArgs], SandboxCoreCallResult]:
    """Injectable runner that returns the copied-realistic fixture payload."""

    def _runner(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        _ = args
        return build_copied_boundary_result(case)

    return _runner


def build_quality_checklist_rows(
    case: CopiedRealDataValidationCase,
) -> tuple[CopiedRealDataQualityRow, ...]:
    """Explicit quality checklist — validation scaffolding, not production class."""

    return (
        CopiedRealDataQualityRow(
            document_id=case.recognized_document,
            category="recognized",
            reason="Explizite Fixture-Metadaten: erkannte Rechnung (Sandbox)",
            expected_ui_section=UI_SECTION_RECOGNIZED,
            expected_export_section=EXPORT_SECTION_RECOGNIZED,
            filename_is_not_truth=True,
        ),
        CopiedRealDataQualityRow(
            document_id=case.payment_review_document,
            category="review_payment_unclear",
            reason=MSG_PAYMENT_UNCLEAR,
            expected_ui_section=UI_SECTION_REVIEW,
            expected_export_section=EXPORT_SECTION_UNCLEAR,
            filename_is_not_truth=True,
        ),
        CopiedRealDataQualityRow(
            document_id=case.business_review_document,
            category="review_business_unclear",
            reason=MSG_BUSINESS_UNCLEAR,
            expected_ui_section=UI_SECTION_REVIEW,
            expected_export_section=EXPORT_SECTION_UNCLEAR,
            filename_is_not_truth=True,
        ),
        CopiedRealDataQualityRow(
            document_id=case.error_document,
            category="error_unsupported",
            reason=MSG_UNSUPPORTED_ERROR,
            expected_ui_section=UI_SECTION_ERROR,
            expected_export_section=EXPORT_SECTION_FAILED,
            filename_is_not_truth=True,
        ),
    )


def build_copied_real_data_validation_report(
    *,
    case: CopiedRealDataValidationCase,
    gate: SandboxPathValidationResult,
    boundary_args: SandboxCoreCallArgs | None,
    workspace_report: RunReportViewModel,
    review_queue: ReviewQueueViewModel,
    export_payload: dict,
    productive_blocked: bool,
    tmp_root: Path | str,
) -> CopiedRealDataValidationReport:
    """Assemble the validation report from observed Track-B product outputs."""

    root = Path(tmp_root)
    quality_rows = build_quality_checklist_rows(case)
    categories = tuple(row.category for row in quality_rows)

    sandbox_input_ok = Path(case.input_folder).is_relative_to(Path(case.sandbox_root))
    sandbox_output_ok = Path(case.output_folder).is_relative_to(Path(case.sandbox_root))
    original_excluded = (
        case.input_folder != case.original_source_folder
        and not Path(case.input_folder).is_relative_to(
            Path(case.original_source_folder)
        )
        and gate.reason_code != "blocked_original_folder"
    )

    boundary_ok = False
    if boundary_args is not None:
        boundary_ok = (
            boundary_args.input_folder == case.input_folder
            and boundary_args.output_folder == case.output_folder
            and boundary_args.sandbox_root == case.sandbox_root
            and boundary_args.input_folder != case.original_source_folder
            and boundary_args.output_folder != case.original_source_folder
        )

    five_ok = workspace_report.section_titles == (
        SECTION_RECOGNIZED,
        SECTION_UNCLEAR,
        SECTION_FAILED,
        SECTION_DESTINATIONS,
        SECTION_SUMMARY,
    )

    review_labels = {item.document_label for item in review_queue.items}
    payment_visible = case.payment_review_document in review_labels
    business_visible = case.business_review_document in review_labels

    questions = export_payload.get("questions") or {}
    export_recognized = bool((questions.get("recognized") or {}).get("count", 0))
    export_unclear = bool((questions.get("unclear") or {}).get("count", 0))
    export_failed = bool((questions.get("failed") or {}).get("count", 0))
    export_dest = "destinations" in questions
    export_summary = "user_summary" in questions

    fixture_inside = all(
        Path(path).is_relative_to(root) for path in case.fixture_files
    )
    no_writes_outside = (
        Path(case.sandbox_root).is_relative_to(root)
        and Path(case.original_source_folder).is_relative_to(root)
        and fixture_inside
    )

    clarity_lines = track_b_clarity_lines() + (
        MSG_CLARITY_COPIED_DATA_ONLY_REPORT,
    )
    return CopiedRealDataValidationReport(
        case=case,
        quality_rows=quality_rows,
        categories_present=categories,
        sandbox_input_under_root=sandbox_input_ok,
        sandbox_output_under_root=sandbox_output_ok,
        original_excluded_from_input=original_excluded,
        productive_blocked=productive_blocked,
        boundary_paths_sandbox_only=boundary_ok,
        five_questions_answered=five_ok,
        review_payment_visible=payment_visible,
        review_business_visible=business_visible,
        export_has_recognized=export_recognized,
        export_has_unclear=export_unclear,
        export_has_failed=export_failed,
        export_has_destinations=export_dest,
        export_has_summary=export_summary,
        no_private_defaults=True,
        no_filename_as_truth=all(row.filename_is_not_truth for row in quality_rows),
        no_writes_outside_tmp=no_writes_outside,
        fixture_inside_tmp=fixture_inside,
        user_clarity_lines=clarity_lines,
        original_folders_excluded_message=MSG_CLARITY_NO_ORIGINAL_FOLDERS,
        copied_data_only_message=MSG_CLARITY_COPIED_DATA_ONLY_REPORT,
        sandbox_run_message=MSG_CLARITY_SANDBOX_COPIED_RUN,
        productive_blocked_message=MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
        filename_not_truth_message=MSG_CLARITY_FILENAME_NOT_TRUTH,
    )


def validate_copied_real_data_sandbox(
    tmp_root: Path | str,
    *,
    copied_data_confirmed: bool = True,
    user_confirmed_start: bool = True,
) -> CopiedRealDataValidationFlowResult:
    """Run Track-B modules against copied-realistic sandbox fixture data only.

    Flow: fixture → profile readiness → gate → stubbed boundary → adapter →
    workspace → review → export preview → validation report.
    Never calls OCR/AI, never imports processing-core, never writes exports
    outside the caller's tmp root (export remains in-memory preview).
    """

    case = build_copied_realistic_fixture(tmp_root)
    profile_policy = build_copied_profile_policy(case)
    request = build_copied_sandbox_request(
        case,
        copied_data_confirmed=copied_data_confirmed,
        user_confirmed_start=user_confirmed_start,
    )
    gate = evaluate_sandbox_gate(request)

    captured: list[SandboxCoreCallArgs] = []

    def runner(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        captured.append(args)
        return build_copied_boundary_result(case)

    adapter = LocalProcessingAdapter(sandbox_runner=runner)
    productive_request = build_copied_sandbox_request(
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
        build_copied_boundary_result(case)
        if boundary_args is not None
        else SandboxCoreCallResult(ok=False, message="boundary not invoked", errors=())
    )

    workspace_shell = build_run_result_display_shell(run_state)
    workspace_report = build_run_report_view_model(run_state)
    review_queue = build_review_queue_view_model(run_state)
    export_payload = build_run_export_payload(workspace_report)
    validation_report = build_copied_real_data_validation_report(
        case=case,
        gate=gate,
        boundary_args=boundary_args,
        workspace_report=workspace_report,
        review_queue=review_queue,
        export_payload=export_payload,
        productive_blocked=productive_blocked,
        tmp_root=tmp_root,
    )

    return CopiedRealDataValidationFlowResult(
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
        validation_report=validation_report,
    )


__all__ = (
    "COPIED_CONFIGURATION_ID",
    "COPIED_MARKERS",
    "COPIED_PROFILE_DISPLAY",
    "COPIED_PROFILE_ID",
    "COPIED_RUN_ID",
    "DOC_ERROR",
    "DOC_INVOICE",
    "DOC_RECEIPT",
    "DOC_UNCLEAR",
    "EXPORT_SECTION_FAILED",
    "EXPORT_SECTION_RECOGNIZED",
    "EXPORT_SECTION_UNCLEAR",
    "FAKE_FILE_SUFFIX",
    "MSG_BUSINESS_EVIDENCE",
    "MSG_BUSINESS_UNCLEAR",
    "MSG_NEXT_ACTION_BUSINESS",
    "MSG_NEXT_ACTION_PAYMENT",
    "MSG_PAYMENT_EVIDENCE",
    "MSG_PAYMENT_UNCLEAR",
    "MSG_UNSUPPORTED_ERROR",
    "UI_SECTION_ERROR",
    "UI_SECTION_RECOGNIZED",
    "UI_SECTION_REVIEW",
    "CopiedRealDataCategory",
    "CopiedRealDataQualityRow",
    "CopiedRealDataValidationCase",
    "CopiedRealDataValidationFlowResult",
    "CopiedRealDataValidationReport",
    "build_copied_boundary_result",
    "build_copied_policy_bridge",
    "build_copied_processing_state",
    "build_copied_profile_policy",
    "build_copied_real_data_validation_report",
    "build_copied_realistic_fixture",
    "build_copied_sandbox_request",
    "build_quality_checklist_rows",
    "make_copied_boundary_runner",
    "validate_copied_real_data_sandbox",
)
