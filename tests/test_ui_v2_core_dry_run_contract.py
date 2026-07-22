"""Core Dry-Run Sandbox API contract tests — types/validation only.

No PDF processing, no OCR/AI, no processing-core imports, no folder mutation.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from invoice_tool.ui_v2.core_dry_run_contract import (
    ERROR_COPIED_DATA_CONFIRMATION,
    ERROR_DRY_RUN_REQUIRED,
    ERROR_MISSING_CONFIGURATION,
    ERROR_MISSING_INPUT,
    ERROR_MISSING_OUTPUT,
    ERROR_MISSING_PROFILE,
    ERROR_NO_MUTATION_REQUIRED,
    ERROR_ORIGINAL_EXCLUSION_CONFIRMATION,
    ERROR_ORIGINAL_LOOKING,
    ERROR_PRODUCTIVE_BLOCKED,
    ERROR_SAME_INPUT_OUTPUT,
    CoreDryRunContractViolation,
    CoreDryRunDocumentResult,
    CoreDryRunErrorItem,
    CoreDryRunMode,
    CoreDryRunPlannedDestination,
    CoreDryRunRequest,
    CoreDryRunResult,
    CoreDryRunReviewItem,
    CoreDryRunStatus,
    build_core_dry_run_contract_requirements,
    empty_safety_proof,
    summarize_core_dry_run_buckets,
    validate_core_dry_run_request,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "invoice_tool" / "ui_v2" / "core_dry_run_contract.py"
PROCESSING_CORE = (
    ROOT / "invoice_tool" / "processing.py",
    ROOT / "invoice_tool" / "routing.py",
    ROOT / "invoice_tool" / "routing_guards.py",
    ROOT / "invoice_tool" / "classification.py",
    ROOT / "invoice_tool" / "target_routing.py",
    ROOT / "invoice_tool" / "run.py",
)
FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.run",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
)


def _valid_request(tmp_path: Path, **overrides) -> CoreDryRunRequest:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    data = dict(
        input_dir=str(inbox),
        output_dir=str(outbox),
        sandbox_root=str(sandbox),
        profile_id="profile-a",
        configuration_id="config-a",
        dry_run=True,
        no_mutation=True,
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
        productive_mode_requested=False,
        mode=CoreDryRunMode.SANDBOX_DRY_RUN,
        original_source_folder=str(tmp_path / "original-never-used"),
        run_id="dry-run-test-001",
    )
    data.update(overrides)
    return CoreDryRunRequest(**data)


def _expect_code(request: CoreDryRunRequest, code: str) -> None:
    with pytest.raises(CoreDryRunContractViolation) as excinfo:
        validate_core_dry_run_request(request)
    assert excinfo.value.code == code


def test_valid_sandbox_dry_run_request_passes(tmp_path: Path) -> None:
    request = _valid_request(tmp_path)
    validated = validate_core_dry_run_request(request)
    assert validated is request
    assert validated.dry_run is True
    assert validated.no_mutation is True
    assert validated.productive_mode_requested is False


def test_missing_input_rejected(tmp_path: Path) -> None:
    _expect_code(_valid_request(tmp_path, input_dir=None), ERROR_MISSING_INPUT)
    _expect_code(_valid_request(tmp_path, input_dir="  "), ERROR_MISSING_INPUT)


def test_missing_output_rejected(tmp_path: Path) -> None:
    _expect_code(_valid_request(tmp_path, output_dir=None), ERROR_MISSING_OUTPUT)
    _expect_code(_valid_request(tmp_path, output_dir=""), ERROR_MISSING_OUTPUT)


def test_same_input_output_rejected(tmp_path: Path) -> None:
    same = str(tmp_path / "sandbox" / "same")
    _expect_code(
        _valid_request(tmp_path, input_dir=same, output_dir=same),
        ERROR_SAME_INPUT_OUTPUT,
    )


def test_dry_run_false_rejected(tmp_path: Path) -> None:
    _expect_code(_valid_request(tmp_path, dry_run=False), ERROR_DRY_RUN_REQUIRED)


def test_no_mutation_false_rejected(tmp_path: Path) -> None:
    _expect_code(
        _valid_request(tmp_path, no_mutation=False), ERROR_NO_MUTATION_REQUIRED
    )


def test_productive_mode_rejected(tmp_path: Path) -> None:
    _expect_code(
        _valid_request(tmp_path, productive_mode_requested=True),
        ERROR_PRODUCTIVE_BLOCKED,
    )


def test_copied_data_confirmation_missing_rejected(tmp_path: Path) -> None:
    _expect_code(
        _valid_request(tmp_path, copied_data_confirmation=False),
        ERROR_COPIED_DATA_CONFIRMATION,
    )


def test_original_exclusion_confirmation_missing_rejected(tmp_path: Path) -> None:
    _expect_code(
        _valid_request(tmp_path, original_folder_exclusion_confirmation=False),
        ERROR_ORIGINAL_EXCLUSION_CONFIRMATION,
    )


def test_missing_profile_and_config_rejected(tmp_path: Path) -> None:
    _expect_code(
        _valid_request(tmp_path, profile_id=None, profile_name=None),
        ERROR_MISSING_PROFILE,
    )
    _expect_code(
        _valid_request(
            tmp_path,
            configuration_id=None,
            configuration_name=None,
        ),
        ERROR_MISSING_CONFIGURATION,
    )
    # profile_name / configuration_name alone are sufficient
    ok = validate_core_dry_run_request(
        _valid_request(
            tmp_path,
            profile_id=None,
            profile_name="Profil A",
            configuration_id=None,
            configuration_name="Config A",
        )
    )
    assert ok.profile_name == "Profil A"
    assert ok.configuration_name == "Config A"


def test_original_looking_desktop_invoice_folders_rejected(tmp_path: Path) -> None:
    desktop_invoice = "/Users/demo/Desktop/Rechnungen/Inbox"
    _expect_code(
        _valid_request(tmp_path, input_dir=desktop_invoice),
        ERROR_ORIGINAL_LOOKING,
    )
    somaa = str(tmp_path / "sandbox" / "somaa-inbox")
    _expect_code(
        _valid_request(tmp_path, input_dir=somaa, sandbox_root=str(tmp_path / "sandbox")),
        ERROR_ORIGINAL_LOOKING,
    )


def test_result_model_separates_recognized_review_errors() -> None:
    recognized = (
        CoreDryRunDocumentResult(
            document_name="a.pdf",
            document_type="invoice",
            classification_status="recognized",
            status_label="erkannt",
        ),
    )
    review = (
        CoreDryRunReviewItem(
            document_name="b.pdf",
            reason="unclear_vendor",
            status_label="unklar",
        ),
    )
    errors = (
        CoreDryRunErrorItem(
            document_name="c.pdf",
            error_code="extract_failed",
            message="extract failed",
        ),
    )
    planned = (
        CoreDryRunPlannedDestination(
            document_name="a.pdf",
            planned_path="/sandbox/out/documents/a.pdf",
            applied=False,
        ),
    )
    summary = summarize_core_dry_run_buckets(
        recognized=recognized,
        review=review,
        errors=errors,
        planned_destinations=planned,
    )
    result = CoreDryRunResult(
        status=CoreDryRunStatus.COMPLETED_WITH_REVIEW,
        run_id="r1",
        recognized=recognized,
        review=review,
        errors=errors,
        planned_destinations=planned,
        summary=summary,
        safety_proof=empty_safety_proof(
            evidence_notes=("contract_result_shape_ok",)
        ),
    )
    assert result.recognized[0].document_name == "a.pdf"
    assert result.review[0].document_name == "b.pdf"
    assert result.errors[0].document_name == "c.pdf"
    assert result.summary.recognized_count == 1
    assert result.summary.review_count == 1
    assert result.summary.error_count == 1
    assert result.summary.total_documents == 3


def test_planned_destinations_are_data_only_not_file_moves() -> None:
    planned = CoreDryRunPlannedDestination(
        document_name="x.pdf",
        planned_path="/sandbox/out/x.pdf",
        destination_label="documents",
        applied=False,
    )
    assert planned.applied is False
    reqs = build_core_dry_run_contract_requirements()
    assert "planned_destination_records_data_only" in reqs["allowed_sandbox_artifacts"]
    assert reqs["safety_policy"]["planned_destinations_data_only"] is True


def test_safety_proof_exists() -> None:
    proof = empty_safety_proof(evidence_notes=("no_source_mutation",))
    result = CoreDryRunResult(
        status=CoreDryRunStatus.READY,
        safety_proof=proof,
        warnings=("contract_only",),
    )
    assert result.safety_proof is not None
    assert result.safety_proof.no_original_mutation is True
    assert result.safety_proof.no_source_archive is True
    assert result.safety_proof.planned_destinations_not_applied is True
    assert "no_source_mutation" in result.safety_proof.evidence_notes


def test_no_processing_core_import_required_by_contract_module() -> None:
    tree = ast.parse(CONTRACT.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for name in imported:
        assert name not in FORBIDDEN_CORE
        assert not any(name.startswith(f"{mod}.") for mod in FORBIDDEN_CORE)

    # Contract and this test must not import processing-core (AST / import lines).
    assert CONTRACT.is_file()
    for path in PROCESSING_CORE:
        assert path.is_file()
    this_src = Path(__file__).read_text(encoding="utf-8")
    for mod in FORBIDDEN_CORE:
        assert f"import {mod}" not in this_src
        assert f"from {mod}" not in this_src
    # Contract stdlib-only imports — no invoice_tool.* runtime deps.
    for name in imported:
        assert not name.startswith("invoice_tool."), name


def test_contract_requirements_point_to_next_implementation_task() -> None:
    reqs = build_core_dry_run_contract_requirements()
    assert (
        reqs["next_implementation_task"]
        == "KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01"
    )
    assert reqs["processing_core_entrypoint_not_safe"] == "invoice_tool.run.run_once"
    assert "archive_source" in reqs["forbidden_mutations"]
