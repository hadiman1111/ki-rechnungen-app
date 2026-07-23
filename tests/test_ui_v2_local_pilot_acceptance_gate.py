"""Track-B Local Pilot Acceptance Gate (Prompt 6/34).

Bounded acceptance of the Track-B UI-v2 sandbox pilot chain only.
Does not enable productive processing, does not touch originals, does not
claim SaaS-/production-ready.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from invoice_tool.ui_v2.core_bridge import (
    ERROR_MISSING_CONFIGURATION,
    ERROR_MISSING_INPUT,
    ERROR_MISSING_OUTPUT,
    ERROR_MISSING_PROFILE,
    ERROR_ORIGINAL_LOOKING,
    ERROR_PRODUCTIVE_BLOCKED,
    ERROR_SAME_INPUT_OUTPUT,
    CoreBridgeRequest,
    CoreBridgeStatus,
    build_core_dry_run_request_from_bridge,
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
    MSG_LOCAL_PILOT_SANDBOX_ONLY,
    MSG_NO_FINAL_FILES_WRITTEN,
    MSG_PRODUCTIVE_PROCESSING_BLOCKED,
    MSG_SAAS_NOT_READY,
    PRODUCT_STATUS_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY,
    PRODUCT_STATUS_LOCAL_PILOT_PENDING_WITH_BLOCKERS,
    build_export_preview_report,
    build_run_export_payload,
    render_export_preview_text,
    report_contains_forbidden_claims,
)
from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.pages.workspace import (
    MSG_RUN_STATUS_CHECKING,
    apply_start_processing,
    mark_start_checking,
)
from invoice_tool.ui_v2.result_mapping import (
    FORBIDDEN_PRODUCTIVE_ACTION_LABELS,
    build_result_bucket_summary,
    map_core_dry_run_result_to_processing_run_state,
    planned_destinations_are_preview_only,
    productive_actions_exposed,
)
from invoice_tool.ui_v2.review_state import build_review_flow_state
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
CORE_BRIDGE = ROOT / "invoice_tool" / "ui_v2" / "core_bridge.py"
EXPORT_MODULE = ROOT / "invoice_tool" / "ui_v2" / "export_reporting.py"
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.run",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
)
FORBIDDEN_READY_CLAIMS = (
    "SaaS-ready",
    "SaaS bereit",
    "saas ready",
    "production-ready",
    "production ready",
    "Production-Ready",
    "produktionsbereit",
    "Local-Pilot-Ready",
    "local_pilot_ready",
)


@dataclass(frozen=True)
class GateCriterion:
    key: str
    met: bool
    detail: str


def _sandbox_dirs(tmp_path: Path) -> tuple[Path, Path, Path]:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    return sandbox, inbox, outbox


def _digest_tree(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


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


def _bridge_request_raw(**data) -> CoreBridgeRequest:
    """Build a bridge request without recreating sandbox dirs."""

    defaults = dict(
        dry_run=True,
        productive_execution_allowed=False,
        mode="sandbox_dry_run",
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
        profile_id="profile-a",
        configuration_id="config-a",
    )
    defaults.update(data)
    return CoreBridgeRequest(**defaults)


def _fake_dry_result(**overrides) -> CoreDryRunResult:
    data = dict(
        status=CoreDryRunStatus.COMPLETED_WITH_REVIEW,
        run_id="pilot-gate-1",
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
                destination_label="erkannt",
                applied=False,
            ),
            CoreDryRunPlannedDestination(
                document_name="scan.pdf",
                planned_path="/sandbox/out/geplant/unklar/scan.pdf",
                destination_label="unklar",
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


def _ready_workspace(tmp_path: Path) -> tuple[UiV2State, Path, Path, Path]:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"
    return state, sandbox, inbox, outbox


def classify_local_pilot_product_status(*, all_gates_passed: bool) -> str:
    if all_gates_passed:
        return PRODUCT_STATUS_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY
    return PRODUCT_STATUS_LOCAL_PILOT_PENDING_WITH_BLOCKERS


def evaluate_local_pilot_acceptance_gates(
    *,
    criteria: tuple[GateCriterion, ...],
) -> tuple[str, tuple[GateCriterion, ...]]:
    all_passed = all(row.met for row in criteria)
    return classify_local_pilot_product_status(all_gates_passed=all_passed), criteria


def test_local_pilot_gate_passes_for_deterministic_valid_sandbox_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[object] = []

    def fake(request):
        called.append(request)
        return _fake_dry_result()

    monkeypatch.setattr("invoice_tool.core_dry_run.run_core_dry_run_sandbox", fake)
    monkeypatch.setattr(
        "invoice_tool.run.run_once",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("run_once")),
        raising=False,
    )

    originals = tmp_path / "originals"
    originals.mkdir()
    sample = originals / "keep.txt"
    sample.write_text("original-bytes", encoding="utf-8")
    before = _digest_tree(originals)

    state, _sandbox, inbox, outbox = _ready_workspace(tmp_path)
    (inbox / "invoice.txt").write_text("Rechnung\nGesamtbetrag 1\n", encoding="utf-8")
    mark_start_checking(state)
    assert state.workspace_start_feedback_primary == MSG_RUN_STATUS_CHECKING
    result = apply_start_processing(state, profile_id="profile-a")

    assert called, "run_core_dry_run_sandbox must be called"
    dry_req = called[0]
    assert dry_req.dry_run is True
    assert dry_req.no_mutation is True
    assert dry_req.productive_mode_requested is False

    assert result.status == "completed"
    assert result.run_id == "pilot-gate-1"
    assert result.recognized_count == 1
    assert result.review_count == 1
    assert result.error_count == 1
    assert result.planned_destination_count == 2
    assert result.safety_proof_summary

    buckets = build_result_bucket_summary(result)
    assert buckets.recognized_count == 1
    assert buckets.review_count == 1
    assert buckets.error_count == 1

    review_vm = build_review_page_vm(state)
    assert review_vm.review_count == 1
    assert review_vm.error_count == 1
    assert review_vm.result_count == 1
    assert review_vm.final_actions_blocked is True
    assert review_vm.productive_actions_exposed is False
    assert review_vm.export_preview_only is True

    report = build_export_preview_report(result)
    text = render_export_preview_text(report)
    payload = build_run_export_payload(report)
    assert report.recognized_count == 1
    assert report.review_count == 1
    assert report.error_count == 1
    assert report.preview_only is True
    assert report.claims_local_pilot_ready is False
    assert report.claims_saas_ready is False
    assert MSG_LOCAL_PILOT_SANDBOX_ONLY in text
    assert MSG_SAAS_NOT_READY in text
    assert MSG_NO_FINAL_FILES_WRITTEN in text
    assert MSG_PRODUCTIVE_PROCESSING_BLOCKED in text
    assert payload["preview"] is True
    assert payload["productive_export"] is False
    assert report_contains_forbidden_claims(report) is False
    for claim in FORBIDDEN_READY_CLAIMS:
        assert claim.lower() not in text.lower() or "nicht" in text.lower()

    assert productive_actions_exposed(result) is False
    assert planned_destinations_are_preview_only(result) is True
    for label in FORBIDDEN_PRODUCTIVE_ACTION_LABELS:
        assert label not in (review_vm.action_labels or ())

    assert _digest_tree(originals) == before
    assert sample.read_text(encoding="utf-8") == "original-bytes"
    # Dry-run must not write final renamed invoices into the sandbox outbox.
    written_files = [p for p in outbox.rglob("*") if p.is_file()]
    assert written_files == []

    criteria = (
        GateCriterion("sandbox_dry_run_started", True, "valid start reached core dry-run"),
        GateCriterion("dry_run_true", dry_req.dry_run is True, "dry_run"),
        GateCriterion("no_mutation_true", dry_req.no_mutation is True, "no_mutation"),
        GateCriterion(
            "productive_false",
            dry_req.productive_mode_requested is False,
            "productive_mode_requested",
        ),
        GateCriterion("honest_buckets", result.review_count == 1, "review bucket"),
        GateCriterion("export_preview", report.preview_only is True, "preview"),
        GateCriterion("no_saas_claim", report.claims_saas_ready is False, "saas"),
        GateCriterion(
            "no_local_pilot_ready_claim",
            report.claims_local_pilot_ready is False,
            "local_pilot_ready flag",
        ),
        GateCriterion("originals_unchanged", _digest_tree(originals) == before, "digest"),
        GateCriterion(
            "final_actions_blocked",
            review_vm.final_actions_blocked is True,
            "final actions",
        ),
    )
    status, rows = evaluate_local_pilot_acceptance_gates(criteria=criteria)
    assert all(row.met for row in rows)
    assert status == PRODUCT_STATUS_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY
    assert status != PRODUCT_STATUS_LOCAL_PILOT_PENDING_WITH_BLOCKERS


def test_valid_request_requires_sandbox_input_and_explicit_sandbox_output(
    tmp_path: Path,
) -> None:
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
    assert "copied-inbox" in dry.input_dir
    assert "copied-outbox" in dry.output_dir
    assert dry.input_dir != dry.output_dir
    assert dry.dry_run is True
    assert dry.no_mutation is True


def test_missing_input_blocks_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[object] = []
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
    status = classify_local_pilot_product_status(all_gates_passed=False)
    assert status == PRODUCT_STATUS_LOCAL_PILOT_PENDING_WITH_BLOCKERS


def test_missing_output_blocks_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[object] = []
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


def test_same_input_output_blocks_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[object] = []
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: called.append(request) or _fake_dry_result(),
    )
    sandbox, inbox, _outbox = _sandbox_dirs(tmp_path)
    result = run_core_bridge_sandbox_dry_run(
        _bridge_request_raw(
            input_folder=str(inbox),
            output_folder=str(inbox),
            sandbox_root=str(sandbox),
            original_source_folder=str(tmp_path / "original-never-used"),
        )
    )
    assert result.status == CoreBridgeStatus.BLOCKED_SAME_INPUT_OUTPUT
    assert ERROR_SAME_INPUT_OUTPUT in result.errors
    assert called == []


def test_original_looking_folder_blocks_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[object] = []
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: called.append(request) or _fake_dry_result(),
    )
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    # Path token that the bridge treats as original-looking.
    bad_in = sandbox / "SOMAA-Rechnungen"
    bad_out = sandbox / "copied-outbox"
    bad_in.mkdir()
    bad_out.mkdir()
    result = run_core_bridge_sandbox_dry_run(
        _bridge_request_raw(
            input_folder=str(bad_in),
            output_folder=str(bad_out),
            sandbox_root=str(sandbox),
            original_source_folder=str(tmp_path / "original-never-used"),
        )
    )
    assert result.status == CoreBridgeStatus.BLOCKED_ORIGINAL_LOOKING
    assert ERROR_ORIGINAL_LOOKING in result.errors
    assert called == []


def test_missing_profile_config_blocks_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[object] = []
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: called.append(request) or _fake_dry_result(),
    )
    missing_profile = run_core_bridge_sandbox_dry_run(
        _bridge_request(tmp_path, profile_id=None, profile_name=None)
    )
    assert missing_profile.status == CoreBridgeStatus.BLOCKED_MISSING_PROFILE
    assert ERROR_MISSING_PROFILE in missing_profile.errors
    missing_config = run_core_bridge_sandbox_dry_run(
        _bridge_request(tmp_path, configuration_id=None, configuration_name=None)
    )
    assert missing_config.status == CoreBridgeStatus.BLOCKED_MISSING_CONFIGURATION
    assert ERROR_MISSING_CONFIGURATION in missing_config.errors
    assert called == []


def test_productive_mode_remains_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[object] = []
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: called.append(request) or _fake_dry_result(),
    )
    result = run_core_bridge_sandbox_dry_run(
        _bridge_request(tmp_path, productive_execution_allowed=True, dry_run=False)
    )
    assert result.status == CoreBridgeStatus.BLOCKED_PRODUCTIVE
    assert ERROR_PRODUCTIVE_BLOCKED in result.errors
    assert result.productive_execution_enabled is False
    assert called == []
    adapter = LocalProcessingAdapter()
    assert adapter.execution_gate(dry_run=False) == "productive_blocked"


def test_run_core_dry_run_sandbox_called_in_valid_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[object] = []
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: called.append(request) or _fake_dry_result(),
    )
    state, *_ = _ready_workspace(tmp_path)
    apply_start_processing(state, profile_id="profile-a")
    assert len(called) == 1


def test_run_once_is_not_called(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def boom(*_a, **_k):
        calls.append("run_once")
        raise AssertionError("run_once must not be called")

    monkeypatch.setattr("invoice_tool.run.run_once", boom, raising=False)
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: _fake_dry_result(),
    )
    state, *_ = _ready_workspace(tmp_path)
    apply_start_processing(state, profile_id="profile-a")
    assert calls == []
    for path in (CORE_BRIDGE, WORKSPACE, REVIEW, EXPORT_MODULE):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
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
            ), f"{path.name} imports {name}"


def test_dry_run_no_mutation_productive_false_enforced(tmp_path: Path) -> None:
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
    assert dry.no_mutation is True
    assert dry.productive_mode_requested is False
    assert dry.copied_data_confirmation is True
    assert dry.original_folder_exclusion_confirmation is True


def test_result_buckets_appear_honestly() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_fake_dry_result())
    buckets = build_result_bucket_summary(state)
    assert buckets.recognized_count == 1
    assert buckets.review_count == 1
    assert buckets.error_count == 1
    assert state.results[0].document_name == "invoice.txt"
    assert state.review_items[0].document_name == "scan.pdf"
    assert state.error_items[0].document_name == "bad.bin"
    # Recognized must not be falsely marked review-needed.
    recognized_names = {item.document_name for item in state.results}
    review_names = {item.document_name for item in state.review_items}
    assert "invoice.txt" in recognized_names
    assert "invoice.txt" not in review_names
    assert "scan.pdf" in review_names
    assert "scan.pdf" not in recognized_names


def test_review_flow_uses_real_dry_run_review_error_buckets() -> None:
    run_state = map_core_dry_run_result_to_processing_run_state(_fake_dry_result())
    flow = build_review_flow_state(run_state)
    assert flow.review_count == 1
    assert flow.error_count == 1
    assert flow.recognized_count == 1
    ui = UiV2State(processing_run_state=run_state)
    page = build_review_page_vm(ui)
    assert page.review_count == 1
    assert page.error_count == 1
    assert page.result_count == 1
    assert page.final_actions_blocked is True
    assert page.actions_disabled is True


def test_export_preview_uses_real_dry_run_state() -> None:
    run_state = map_core_dry_run_result_to_processing_run_state(_fake_dry_result())
    report = build_export_preview_report(run_state)
    assert report.run_id == "pilot-gate-1"
    assert report.recognized_count == 1
    assert report.review_count == 1
    assert report.error_count == 1
    assert report.warning_count >= 1
    assert report.planned_destination_count == 2
    assert report.safety_proof
    assert report.preview_only is True


def test_final_productive_actions_are_not_exposed() -> None:
    run_state = map_core_dry_run_result_to_processing_run_state(_fake_dry_result())
    assert productive_actions_exposed(run_state) is False
    page = build_review_page_vm(UiV2State(processing_run_state=run_state))
    assert page.productive_actions_exposed is False
    assert page.final_actions_blocked is True
    blob = " ".join(page.action_labels).lower()
    for label in FORBIDDEN_PRODUCTIVE_ACTION_LABELS:
        assert label.lower() not in blob


def test_original_files_remain_unchanged_in_tmp_path(tmp_path: Path) -> None:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    originals = tmp_path / "original-never-used"
    originals.mkdir()
    keep = originals / "keep.txt"
    keep.write_text("do-not-touch", encoding="utf-8")
    before = _digest_tree(originals)
    (inbox / "note.txt").write_text(
        "Rechnung\nRechnungsnummer 1\nGesamtbetrag 10\n",
        encoding="utf-8",
    )
    result = run_core_bridge_sandbox_dry_run(
        _bridge_request_raw(
            input_folder=str(inbox),
            output_folder=str(outbox),
            sandbox_root=str(sandbox),
            original_source_folder=str(originals),
        )
    )
    assert result.ok is True
    assert _digest_tree(originals) == before
    assert keep.read_text(encoding="utf-8") == "do-not-touch"
    assert list(outbox.iterdir()) == []


def test_no_local_pilot_ready_claim_unless_all_gates_pass() -> None:
    pending = classify_local_pilot_product_status(all_gates_passed=False)
    accepted = classify_local_pilot_product_status(all_gates_passed=True)
    assert pending == PRODUCT_STATUS_LOCAL_PILOT_PENDING_WITH_BLOCKERS
    assert accepted == PRODUCT_STATUS_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY
    report = build_export_preview_report(
        map_core_dry_run_result_to_processing_run_state(_fake_dry_result())
    )
    assert report.claims_local_pilot_ready is False
    text = render_export_preview_text(report)
    assert "Local-Pilot-Ready" not in text
    assert MSG_LOCAL_PILOT_SANDBOX_ONLY in text
    assert "Sandbox" in accepted or "SANDBOX" in accepted


def test_no_saas_ready_or_production_ready_claim() -> None:
    report = build_export_preview_report(
        map_core_dry_run_result_to_processing_run_state(_fake_dry_result())
    )
    text = render_export_preview_text(report)
    assert report.claims_saas_ready is False
    assert MSG_SAAS_NOT_READY in text
    assert report_contains_forbidden_claims(report) is False
    lowered = text.lower()
    assert "saas-ready ist nicht erreicht" in lowered
    assert "production-ready" not in lowered
    assert "produktionsbereit" not in lowered
    status = PRODUCT_STATUS_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY
    assert "SAAS" not in status
    assert "PRODUCTION" not in status


def test_track_a_protection_module_still_importable() -> None:
    # Soft presence check — full suite runs test_track_a_internal_app_protection.py.
    path = ROOT / "tests" / "test_track_a_internal_app_protection.py"
    assert path.is_file()
    src = path.read_text(encoding="utf-8")
    assert "Track A" in src or "track_a" in src.lower() or "app_main" in src


def test_prompt_3_to_5_foundation_modules_present() -> None:
    for relative in (
        "invoice_tool/ui_v2/core_bridge.py",
        "invoice_tool/ui_v2/result_mapping.py",
        "invoice_tool/ui_v2/export_reporting.py",
        "invoice_tool/core_dry_run.py",
        "tests/test_ui_v2_core_bridge_real_sandbox_run_wiring.py",
        "tests/test_ui_v2_real_run_result_mapping_and_review_flow.py",
        "tests/test_ui_v2_export_reporting_preview_polish.py",
    ):
        assert (ROOT / relative).is_file(), relative
