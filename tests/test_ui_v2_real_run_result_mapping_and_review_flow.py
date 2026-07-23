"""Track-B real run result mapping and review flow (Prompt 4/34)."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from invoice_tool.ui_v2.core_bridge import (
    MSG_BRIDGE_SAFETY_PROOF,
    CoreBridgeRequest,
    map_core_dry_run_result_to_bridge_result,
    map_core_result_to_processing_run_state,
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
    MSG_EXPORT_IS_PREVIEW,
    build_run_export_payload,
    build_run_report_view_model,
)
from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.pages.workspace import (
    apply_start_processing,
    build_start_interaction_feedback,
    build_workspace_run_result_shell,
)
from invoice_tool.ui_v2.processing_state import MSG_EMPTY_DRY_RUN, MSG_SAFETY_PROOF_COMPACT
from invoice_tool.ui_v2.result_mapping import (
    FORBIDDEN_PRODUCTIVE_ACTION_LABELS,
    MSG_SAFETY_PROOF_LINE,
    build_result_bucket_summary,
    map_core_dry_run_result_to_processing_run_state,
    planned_destinations_are_preview_only,
    productive_actions_exposed,
)
from invoice_tool.ui_v2.review_state import (
    MSG_NO_FINAL_APPROVAL,
    build_review_flow_state,
)
from invoice_tool.ui_v2.run_result_display import build_run_result_display_shell
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
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


def _digest_tree(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _dry(
    *,
    status: CoreDryRunStatus = CoreDryRunStatus.COMPLETED,
    recognized=(),
    review=(),
    errors=(),
    planned=(),
    warnings=(),
    message: str | None = None,
    run_id: str = "map-run-1",
) -> CoreDryRunResult:
    summary = CoreDryRunSummary(
        total_documents=len(recognized) + len(review) + len(errors),
        recognized_count=len(recognized),
        review_count=len(review),
        error_count=len(errors),
        planned_destination_count=len(planned),
    )
    return CoreDryRunResult(
        status=status,
        run_id=run_id,
        recognized=tuple(recognized),
        review=tuple(review),
        errors=tuple(errors),
        planned_destinations=tuple(planned),
        summary=summary,
        warnings=tuple(warnings),
        safety_proof=empty_safety_proof(evidence_notes=("no_source_mutation",)),
        message=message or "Core-Dry-Run abgeschlossen ohne Source-Mutation.",
    )


def _mixed_dry() -> CoreDryRunResult:
    return _dry(
        status=CoreDryRunStatus.COMPLETED_WITH_REVIEW,
        recognized=(
            CoreDryRunDocumentResult(
                document_name="invoice.txt",
                document_type="invoice",
                classification_status="recognized",
                status_label="erkannt",
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
        planned=(
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
        warnings=("ocr_not_run", "no_write_performed"),
    )


def test_counts_map_into_processing_run_state() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_mixed_dry())
    assert state.recognized_count == 1
    assert state.review_count == 1
    assert state.error_count == 1
    assert state.planned_destination_count == 2
    assert state.run_id == "map-run-1"
    assert state.status == "completed"
    assert state.outcome_kind == "mixed"


def test_warnings_map_into_display_state() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_mixed_dry())
    shell = build_run_result_display_shell(state)
    assert "ocr_not_run" in shell.warnings
    assert "no_write_performed" in shell.warnings


def test_safety_proof_maps_into_display_state() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_mixed_dry())
    shell = build_run_result_display_shell(state)
    assert shell.safety_proof_line == MSG_SAFETY_PROOF_LINE
    assert MSG_SAFETY_PROOF_COMPACT in shell.bucket_lines[-3] or MSG_BRIDGE_SAFETY_PROOF in (
        shell.safety_proof_line,
    )


def test_planned_destinations_display_as_preview_only() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_mixed_dry())
    assert planned_destinations_are_preview_only(state)
    shell = build_run_result_display_shell(state)
    assert shell.planned.preview_only is True
    assert shell.planned.count == 2
    assert all(item.preview_only and not item.applied for item in shell.planned.items)


def test_review_needed_items_appear_in_review_flow() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_mixed_dry())
    flow = build_review_flow_state(state)
    assert flow.review_count == 1
    assert flow.review_items[0].document_name == "scan.pdf"
    ui = UiV2State()
    ui.processing_run_state = state
    page = build_review_page_vm(ui)
    assert page.review_count == 1
    assert page.items[0].document_name == "scan.pdf"


def test_error_items_appear_separately_from_review() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_mixed_dry())
    flow = build_review_flow_state(state)
    assert flow.error_count == 1
    assert flow.error_items[0].document_name == "bad.bin"
    review_names = {item.document_name for item in flow.review_items}
    assert "bad.bin" not in review_names
    assert flow.review_items[0].document_name == "scan.pdf"


def test_recognized_items_not_falsely_marked_review_needed() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_mixed_dry())
    flow = build_review_flow_state(state)
    review_names = {item.document_name for item in flow.review_items}
    assert "invoice.txt" not in review_names
    assert state.results[0].document_name == "invoice.txt"


def test_empty_result_shows_honest_empty_state() -> None:
    dry = _dry(
        status=CoreDryRunStatus.COMPLETED,
        message="Core-Dry-Run abgeschlossen ohne Source-Mutation.",
    )
    state = map_core_dry_run_result_to_processing_run_state(dry)
    assert state.outcome_kind == "empty"
    shell = build_run_result_display_shell(state)
    assert shell.show_empty_state is True
    assert shell.fake_success is False
    assert MSG_EMPTY_DRY_RUN in (shell.empty_detail or shell.message)
    buckets = build_result_bucket_summary(state)
    assert buckets.empty is True


def test_failed_result_shows_failure_not_fake_success() -> None:
    dry = _dry(
        status=CoreDryRunStatus.FAILED,
        errors=(
            CoreDryRunErrorItem(
                document_name="x.bin",
                error_code="unsupported_file_type",
                message="fail",
            ),
        ),
        message="Dry-Run fehlgeschlagen.",
    )
    state = map_core_dry_run_result_to_processing_run_state(dry)
    assert state.status == "failed"
    assert state.outcome_kind == "failed"
    shell = build_run_result_display_shell(state)
    assert shell.fake_success is False
    assert shell.status == "failed"
    assert state.results == ()


def test_all_review_result_shows_mit_prueffaellen() -> None:
    dry = _dry(
        status=CoreDryRunStatus.COMPLETED_WITH_REVIEW,
        review=(
            CoreDryRunReviewItem(
                document_name="a.pdf",
                reason="unklar",
                status_label="unklar",
            ),
        ),
        planned=(
            CoreDryRunPlannedDestination(
                document_name="a.pdf",
                planned_path="/out/geplant/unklar/a.pdf",
                applied=False,
            ),
        ),
    )
    state = map_core_dry_run_result_to_processing_run_state(dry)
    assert state.outcome_kind == "all_review"
    buckets = build_result_bucket_summary(state)
    assert buckets.all_review is True
    assert buckets.all_review is True
    assert "Prüffäll" in buckets.status_label
    feedback = build_start_interaction_feedback(state)
    assert "Prüffäll" in feedback.primary


def test_mixed_result_shows_bucket_counts_honestly() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_mixed_dry())
    buckets = build_result_bucket_summary(state)
    assert buckets.mixed is True
    assert buckets.recognized_count == 1
    assert buckets.review_count == 1
    assert buckets.error_count == 1
    assert buckets.planned_destination_count == 2
    shell = build_run_result_display_shell(state)
    joined = " ".join(shell.bucket_lines)
    assert "Erkannt / geplant: 1" in joined
    assert "Zur Prüfung: 1" in joined
    assert "Fehler: 1" in joined


def test_export_reporting_remains_preview_only() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_mixed_dry())
    report = build_run_report_view_model(state)
    payload = build_run_export_payload(report)
    assert payload["preview"] is True
    assert payload["productive_export"] is False
    assert payload["datev_export"] is False
    assert MSG_EXPORT_IS_PREVIEW in report.honest_copy
    assert all(item.planned_only for item in report.destinations)


def test_no_productive_action_exposed() -> None:
    state = map_core_dry_run_result_to_processing_run_state(_mixed_dry())
    assert productive_actions_exposed(state) is False
    flow = build_review_flow_state(state)
    assert flow.productive_actions_exposed is False
    assert flow.actions_disabled is True
    assert all(not action.enabled for action in flow.actions)
    ui = UiV2State()
    ui.processing_run_state = state
    page = build_review_page_vm(ui)
    assert page.productive_actions_exposed is False
    assert page.actions_disabled is True
    labels = " ".join(page.action_labels).lower()
    for forbidden in FORBIDDEN_PRODUCTIVE_ACTION_LABELS:
        assert forbidden not in labels
    assert MSG_NO_FINAL_APPROVAL in page.honest_copy


def test_run_once_not_called(tmp_path: Path, monkeypatch) -> None:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    (inbox / "note.txt").write_text("Rechnung Nr 1 Gesamtbetrag MwSt", encoding="utf-8")
    called = {"run_once": 0}

    def boom(*_a, **_k):
        called["run_once"] += 1
        raise AssertionError("run_once must not be called")

    monkeypatch.setattr("invoice_tool.run.run_once", boom, raising=False)
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: _mixed_dry(),
    )
    result = run_core_bridge_sandbox_dry_run(
        CoreBridgeRequest(
            input_folder=str(inbox),
            output_folder=str(outbox),
            sandbox_root=str(sandbox),
            profile_id="p1",
            configuration_id="c1",
            dry_run=True,
            productive_execution_allowed=False,
            mode="sandbox_dry_run",
            copied_data_confirmation=True,
            original_folder_exclusion_confirmation=True,
        )
    )
    assert result.productive_execution_enabled is False
    assert called["run_once"] == 0


def test_original_files_unchanged_in_tmp_path(tmp_path: Path, monkeypatch) -> None:
    original = tmp_path / "original-never-used"
    original.mkdir()
    sample = original / "keep.txt"
    sample.write_text("original-bytes", encoding="utf-8")
    before = _digest_tree(original)
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    (inbox / "copy.txt").write_text("Rechnung Gesamtbetrag MwSt", encoding="utf-8")
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: _mixed_dry(),
    )
    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_sandbox_root = str(sandbox)
    state.workspace_original_source_folder = str(original)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.workspace_sandbox_mode = True
    state.workspace_copied_data_confirmed = True
    state.config_list_selected_id = "config-a"
    apply_start_processing(state, profile_id="profile-a")
    assert _digest_tree(original) == before
    assert sample.read_text(encoding="utf-8") == "original-bytes"


def test_integration_dry_result_through_bridge_to_workspace_and_review(
    tmp_path: Path, monkeypatch
) -> None:
    sandbox, inbox, outbox = _sandbox_dirs(tmp_path)
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        lambda request: _mixed_dry(),
    )
    bridge = run_core_bridge_sandbox_dry_run(
        CoreBridgeRequest(
            input_folder=str(inbox),
            output_folder=str(outbox),
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
    run_state = map_core_result_to_processing_run_state(bridge)
    ui = UiV2State(processing_service=LocalProcessingAdapter())
    ui.processing_run_state = run_state
    shell = build_workspace_run_result_shell(ui)
    review = build_review_page_vm(ui)
    assert shell.outcome_kind == "mixed"
    assert shell.review.count == 1
    assert shell.errors.count == 1
    assert shell.planned.preview_only is True
    assert shell.safety_proof_line == MSG_SAFETY_PROOF_LINE
    assert review.review_count == 1
    assert review.error_count == 1
    assert review.result_count == 1
    assert "invoice.txt" not in {item.document_name for item in review.items}
    assert review.actions_disabled is True


def test_bridge_mapping_delegates_to_result_mapping() -> None:
    mapped = map_core_dry_run_result_to_bridge_result(_mixed_dry())
    assert mapped.recognized_count == 1
    assert len(mapped.error_items) == 1
    assert len(mapped.planned_destinations) == 2
    assert mapped.outcome_kind == "mixed"
    assert mapped.safety_proof_summary == MSG_BRIDGE_SAFETY_PROOF


def test_mapping_modules_do_not_import_processing_core() -> None:
    for rel in (
        "invoice_tool/ui_v2/result_mapping.py",
        "invoice_tool/ui_v2/review_state.py",
        "invoice_tool/ui_v2/run_result_display.py",
    ):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        for forbidden in FORBIDDEN_CORE:
            assert forbidden not in imports
            assert not any(name.startswith(forbidden + ".") for name in imports)


def test_ui_v2_workspace_processing_contract_still_importable() -> None:
    from invoice_tool.ui_v2.processing_contract import ProcessingRunRequest

    req = ProcessingRunRequest(
        input_folder=None,
        output_folder=None,
        profile_id=None,
        configuration_id=None,
        dry_run=True,
    )
    assert req.dry_run is True
