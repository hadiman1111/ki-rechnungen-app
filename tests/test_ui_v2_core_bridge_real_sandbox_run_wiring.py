"""Track-B Core Bridge ↔ real Core Dry-Run wiring (Prompt 3/34)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from invoice_tool.ui_v2.core_bridge import (
    ERROR_MISSING_CONFIGURATION,
    ERROR_MISSING_INPUT,
    ERROR_MISSING_OUTPUT,
    ERROR_ORIGINAL_LOOKING,
    ERROR_SAME_INPUT_OUTPUT,
    MSG_BRIDGE_SAFETY_PROOF,
    CoreBridgeRequest,
    CoreBridgeStatus,
    build_core_dry_run_request_from_bridge,
    core_bridge_request_from_sandbox_args,
    map_core_dry_run_result_to_bridge_result,
    run_core_bridge_sandbox_dry_run,
)
from invoice_tool.ui_v2.core_dry_run_contract import (
    CoreDryRunDocumentResult,
    CoreDryRunErrorItem,
    CoreDryRunPlannedDestination,
    CoreDryRunResult,
    CoreDryRunReviewItem,
    CoreDryRunStatus,
    CoreDryRunSummary,
    empty_safety_proof,
)
from invoice_tool.ui_v2.export_reporting import (
    build_run_export_payload,
    build_run_report_view_model,
)
from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.pages.workspace import (
    MSG_RUN_STATUS_CHECKING,
    MSG_SANDBOX_COMPLETED,
    MSG_SANDBOX_COMPLETED_WITH_REVIEW,
    MSG_SANDBOX_FAILED,
    apply_start_processing,
    build_start_interaction_feedback,
    mark_start_checking,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
CORE_BRIDGE = ROOT / "invoice_tool" / "ui_v2" / "core_bridge.py"
FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.run",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
)


def _sandbox_dirs(tmp_path: Path) -> tuple[Path, Path, Path]:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    return sandbox, inbox, outbox


def _bridge_request(tmp_path: Path, **overrides) -> CoreBridgeRequest:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    data = dict(
        input_folder=str(inbox),
        output_folder=str(outbox),
        sandbox_root=str(sandbox),
        profile_id="profile-a",
        configuration_id="config-a",
        original_source_folder=str(tmp_path / "original-never-used"),
        dry_run=True,
        productive_execution_allowed=False,
        mode="sandbox_dry_run",
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
    )
    data.update(overrides)
    return CoreBridgeRequest(**data)


def _fake_dry_result(**overrides) -> CoreDryRunResult:
    data = dict(
        status=CoreDryRunStatus.COMPLETED,
        run_id="dry-run-1",
        recognized=(
            CoreDryRunDocumentResult(
                document_name="invoice.txt",
                document_type="invoice",
                classification_status="recognized",
                status_label="erkannt",
                confidence_label="limited_text_evidence",
                target_hint="geplant/erkannt",
            ),
        ),
        review=(
            CoreDryRunReviewItem(
                document_name="scan.pdf",
                reason="OCR/AI nicht ausgeführt",
                status_label="unklar",
            ),
        ),
        errors=(
            CoreDryRunErrorItem(
                document_name="bad.bin",
                error_code="unsupported_file_type",
                message="Nicht unterstützt",
            ),
        ),
        planned_destinations=(
            CoreDryRunPlannedDestination(
                document_name="invoice.txt",
                planned_path="/sandbox/out/geplant/erkannt/invoice.txt",
                applied=False,
            ),
            CoreDryRunPlannedDestination(
                document_name="scan.pdf",
                planned_path="/sandbox/out/geplant/unklar/scan.pdf",
                applied=False,
            ),
        ),
        summary=CoreDryRunSummary(
            total_documents=3,
            recognized_count=1,
            review_count=1,
            error_count=1,
            planned_destination_count=2,
        ),
        warnings=("ocr_not_run", "no_write_performed"),
        safety_proof=empty_safety_proof(evidence_notes=("no_source_mutation",)),
        message="Core-Dry-Run abgeschlossen ohne Source-Mutation.",
    )
    data.update(overrides)
    return CoreDryRunResult(**data)


def test_start_click_calls_run_core_dry_run_sandbox(tmp_path: Path, monkeypatch) -> None:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    called: list[object] = []

    def fake(request):
        called.append(request)
        return _fake_dry_result(run_id="wired-1")

    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        fake,
    )
    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"
    result = apply_start_processing(state, profile_id="profile-a")
    assert called, "run_core_dry_run_sandbox was not called"
    assert result.status == "completed"
    assert result.run_id == "wired-1"
    assert len(result.results) == 1
    assert len(result.review_items) == 1


def test_bridge_builds_request_with_dry_run_true(tmp_path: Path) -> None:
    req = _bridge_request(tmp_path)
    dry = build_core_dry_run_request_from_bridge(
        req,
        input_folder=req.input_folder or "",
        output_folder=req.output_folder or "",
        sandbox_root=req.sandbox_root or "",
        profile_id="profile-a",
        configuration_id="config-a",
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
    )
    assert dry.dry_run is True


def test_bridge_builds_request_with_no_mutation_true(tmp_path: Path) -> None:
    req = _bridge_request(tmp_path)
    dry = build_core_dry_run_request_from_bridge(
        req,
        input_folder=req.input_folder or "",
        output_folder=req.output_folder or "",
        sandbox_root=req.sandbox_root or "",
        profile_id="profile-a",
        configuration_id="config-a",
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
    )
    assert dry.no_mutation is True


def test_bridge_sets_productive_mode_requested_false(tmp_path: Path) -> None:
    req = _bridge_request(tmp_path)
    dry = build_core_dry_run_request_from_bridge(
        req,
        input_folder=req.input_folder or "",
        output_folder=req.output_folder or "",
        sandbox_root=req.sandbox_root or "",
        profile_id="profile-a",
        configuration_id="config-a",
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
    )
    assert dry.productive_mode_requested is False


def test_bridge_rejects_missing_input_without_core_call(tmp_path: Path, monkeypatch) -> None:
    called = []
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: called.append(request) or _fake_dry_result(),
    )
    result = run_core_bridge_sandbox_dry_run(
        _bridge_request(tmp_path, input_folder=None)
    )
    assert result.status == CoreBridgeStatus.BLOCKED_MISSING_INPUT
    assert ERROR_MISSING_INPUT in result.errors
    assert called == []


def test_bridge_rejects_missing_output_without_core_call(tmp_path: Path, monkeypatch) -> None:
    called = []
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: called.append(request) or _fake_dry_result(),
    )
    result = run_core_bridge_sandbox_dry_run(
        _bridge_request(tmp_path, output_folder="  ")
    )
    assert result.status == CoreBridgeStatus.BLOCKED_MISSING_OUTPUT
    assert ERROR_MISSING_OUTPUT in result.errors
    assert called == []


def test_bridge_rejects_same_input_output_without_core_call(
    tmp_path: Path, monkeypatch
) -> None:
    called = []
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: called.append(request) or _fake_dry_result(),
    )
    sandbox = tmp_path / "sandbox"
    shared = sandbox / "same-folder"
    shared.mkdir(parents=True)
    result = run_core_bridge_sandbox_dry_run(
        CoreBridgeRequest(
            input_folder=str(shared),
            output_folder=str(shared),
            sandbox_root=str(sandbox),
            profile_id="profile-a",
            configuration_id="config-a",
            dry_run=True,
            productive_execution_allowed=False,
            mode="sandbox_dry_run",
            copied_data_confirmation=True,
            original_folder_exclusion_confirmation=True,
        )
    )
    assert result.status == CoreBridgeStatus.BLOCKED_SAME_INPUT_OUTPUT
    assert ERROR_SAME_INPUT_OUTPUT in result.errors
    assert called == []


def test_bridge_rejects_original_looking_folder_without_core_call(
    tmp_path: Path, monkeypatch
) -> None:
    called = []
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: called.append(request) or _fake_dry_result(),
    )
    original = tmp_path / "Desktop" / "Rechnungen_AMEX"
    original.mkdir(parents=True)
    result = run_core_bridge_sandbox_dry_run(
        _bridge_request(
            tmp_path,
            input_folder=str(original),
            output_folder=str(tmp_path / "sandbox" / "copied-outbox"),
            sandbox_root=str(tmp_path),
            original_source_folder=str(original),
        )
    )
    assert result.status == CoreBridgeStatus.BLOCKED_ORIGINAL_LOOKING
    assert ERROR_ORIGINAL_LOOKING in result.errors
    assert called == []


def test_bridge_rejects_missing_profile_config_without_core_call(
    tmp_path: Path, monkeypatch
) -> None:
    called = []
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: called.append(request) or _fake_dry_result(),
    )
    result = run_core_bridge_sandbox_dry_run(
        _bridge_request(tmp_path, configuration_id=None, configuration_name=None)
    )
    assert result.status == CoreBridgeStatus.BLOCKED_MISSING_CONFIGURATION
    assert ERROR_MISSING_CONFIGURATION in result.errors
    assert called == []


def test_bridge_maps_recognized_review_error_planned_counts() -> None:
    mapped = map_core_dry_run_result_to_bridge_result(_fake_dry_result())
    assert mapped.recognized_count == 1
    assert mapped.review_count == 1
    assert mapped.error_count == 1
    assert mapped.planned_destination_count == 2
    assert len(mapped.results) == 1
    assert len(mapped.review_items) == 1
    assert len(mapped.planned_moves) == 2


def test_bridge_maps_warnings_and_safety_proof() -> None:
    mapped = map_core_dry_run_result_to_bridge_result(_fake_dry_result())
    assert "ocr_not_run" in mapped.warnings
    assert mapped.safety_proof_summary == MSG_BRIDGE_SAFETY_PROOF


def test_workspace_shows_status_from_real_result(tmp_path: Path, monkeypatch) -> None:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)

    def fake_completed(request):
        return _fake_dry_result(
            status=CoreDryRunStatus.COMPLETED_WITH_REVIEW,
            recognized=(),
            summary=CoreDryRunSummary(
                total_documents=1,
                recognized_count=0,
                review_count=1,
                error_count=1,
                planned_destination_count=2,
            ),
        )

    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        fake_completed,
    )
    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"
    mark_start_checking(state)
    assert state.workspace_start_feedback_primary == MSG_RUN_STATUS_CHECKING
    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status == "completed"
    feedback = build_start_interaction_feedback(result)
    assert MSG_SANDBOX_COMPLETED_WITH_REVIEW in feedback.primary
    assert "Erkannt:" in " ".join(feedback.details)


def test_no_fake_success_result_is_created(tmp_path: Path, monkeypatch) -> None:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)

    def fake_failed(request):
        return _fake_dry_result(
            status=CoreDryRunStatus.FAILED,
            recognized=(),
            review=(),
            planned_destinations=(),
            summary=CoreDryRunSummary(total_documents=1, error_count=1),
            message="Dry-Run fehlgeschlagen.",
        )

    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        fake_failed,
    )
    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"
    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status == "failed"
    assert result.results == ()
    assert MSG_SANDBOX_COMPLETED not in (state.workspace_start_feedback_primary or "")
    assert MSG_SANDBOX_FAILED in (state.workspace_start_feedback_primary or "")


def test_export_reporting_remains_preview_only(tmp_path: Path, monkeypatch) -> None:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: _fake_dry_result(),
    )
    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"
    apply_start_processing(state, profile_id="profile-a")
    report = build_run_report_view_model(state.processing_run_state)
    payload = build_run_export_payload(report)
    assert payload["preview"] is True
    assert payload["productive_export"] is False
    assert payload["datev_export"] is False
    assert payload["sourced_from_real_dry_run"] is True


def test_run_once_is_not_called(tmp_path: Path, monkeypatch) -> None:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    calls: list[str] = []

    def boom(*_a, **_k):
        calls.append("run_once")
        raise AssertionError("run_once must not be called")

    monkeypatch.setattr("invoice_tool.run.run_once", boom, raising=False)
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: _fake_dry_result(),
    )
    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"
    apply_start_processing(state, profile_id="profile-a")
    assert calls == []


def test_original_files_remain_unchanged_in_tmp_path(tmp_path: Path) -> None:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    original = tmp_path / "original-never-used"
    original.mkdir()
    src = original / "keep.txt"
    src.write_text("do-not-touch", encoding="utf-8")
    before = src.read_bytes()
    before_names = sorted(p.name for p in original.iterdir())

    # Real dry-run on copied inbox only.
    (inbox / "note.txt").write_text(
        "Rechnung\nRechnungsnummer 1\nGesamtbetrag 10\n",
        encoding="utf-8",
    )
    result = run_core_bridge_sandbox_dry_run(
        core_bridge_request_from_sandbox_args(
            input_folder=str(inbox),
            output_folder=str(outbox),
            sandbox_root=str(sandbox),
            profile_id="profile-a",
            configuration_id="config-a",
            original_source_folder=str(original),
        )
    )
    assert result.ok is True
    assert src.read_bytes() == before
    assert sorted(p.name for p in original.iterdir()) == before_names
    assert list(outbox.iterdir()) == []


def test_integration_real_dry_run_on_synthetic_copied_files(tmp_path: Path) -> None:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    (inbox / "invoice.txt").write_text(
        "Rechnung\nRechnungsnummer ABC\nUSt-ID DE1\nGesamtbetrag 12,00\n",
        encoding="utf-8",
    )
    (inbox / "scan.pdf").write_bytes(b"%PDF-1.4 synthetic")
    before_inbox = {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in inbox.iterdir() if p.is_file()
    }
    result = run_core_bridge_sandbox_dry_run(
        core_bridge_request_from_sandbox_args(
            input_folder=str(inbox),
            output_folder=str(outbox),
            sandbox_root=str(sandbox),
            profile_id="profile-a",
            configuration_id="config-a",
        )
    )
    assert result.ok is True
    assert result.recognized_count >= 1
    assert result.review_count >= 1  # PDF without OCR → review
    assert result.planned_destination_count >= 1
    assert all(not Path(path).exists() for path in result.planned_moves)
    after_inbox = {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in inbox.iterdir() if p.is_file()
    }
    assert after_inbox == before_inbox
    assert list(outbox.iterdir()) == []
    # Guarantee this call path did not import processing-core in core_bridge source.
    tree = ast.parse(CORE_BRIDGE.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for name in imported:
        assert not any(
            name == forbidden or name.startswith(forbidden + ".")
            for forbidden in FORBIDDEN_CORE
        ), name


def test_adapter_reports_dry_run_available() -> None:
    adapter = LocalProcessingAdapter()
    assert adapter.core_dry_run_status() == "dry_run_available"
    assert adapter.dry_run_gate() == "dry_run_available"
    assert adapter.execution_gate(dry_run=True) == "dry_run_available"
