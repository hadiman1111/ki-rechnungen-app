"""Synthetic Track-B end-to-end product flow — no real invoices / OCR / GUI."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

from invoice_tool.ui_v2.export_reporting import (
    SECTION_DESTINATIONS,
    SECTION_FAILED,
    SECTION_RECOGNIZED,
    SECTION_SUMMARY,
    SECTION_UNCLEAR,
)
from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.pages.workspace import (
    build_workspace_run_report_vm,
    build_workspace_run_result_shell,
)
from invoice_tool.ui_v2.review_workflow import MSG_ERRORS_SEPARATED, MSG_RESULTS_SEPARATED
from invoice_tool.ui_v2.sandbox_processing_gate import evaluate_sandbox_gate
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.synthetic_e2e_flow import (
    DOC_ERROR,
    DOC_REVIEW,
    DOC_SUCCESS,
    MSG_SYNTHETIC_ERROR,
    SYNTHETIC_MARKERS,
    SYNTHETIC_RUN_ID,
    build_synthetic_boundary_result,
    build_synthetic_e2e_case,
    build_synthetic_processing_state,
    build_synthetic_profile_policy,
    build_synthetic_sandbox_request,
    make_synthetic_boundary_runner,
    run_synthetic_track_b_product_flow,
)

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_MODULE = ROOT / "invoice_tool" / "ui_v2" / "synthetic_e2e_flow.py"
FLOW_MODULES = (
    SYNTHETIC_MODULE,
    ROOT / "invoice_tool" / "ui_v2" / "sandbox_processing_gate.py",
    ROOT / "invoice_tool" / "ui_v2" / "sandbox_execution_boundary.py",
    ROOT / "invoice_tool" / "ui_v2" / "local_processing_adapter.py",
    ROOT / "invoice_tool" / "ui_v2" / "export_reporting.py",
    ROOT / "invoice_tool" / "ui_v2" / "review_workflow.py",
)

FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.run",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
)
PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX",
    "voba",
    "/Users/",
    "Desktop/",
    "Volksbank",
    "Privat",
)


def test_synthetic_e2e_fixture_contains_result_review_error(tmp_path: Path) -> None:
    case = build_synthetic_e2e_case(tmp_path)
    boundary = build_synthetic_boundary_result(case)
    state = build_synthetic_processing_state(case)

    assert DOC_SUCCESS in {item.document_name for item in boundary.results}
    assert DOC_ERROR in {item.document_name for item in boundary.results}
    assert len(boundary.review_items) == 1
    assert boundary.review_items[0].document_name == DOC_REVIEW
    assert MSG_SYNTHETIC_ERROR in boundary.errors

    assert len(state.results) == 2
    assert len(state.review_items) == 1
    assert len(state.errors) == 1
    for marker in SYNTHETIC_MARKERS:
        blob = json.dumps(
            {
                "docs": [DOC_SUCCESS, DOC_REVIEW, DOC_ERROR],
                "error": MSG_SYNTHETIC_ERROR,
                "run": SYNTHETIC_RUN_ID,
            }
        )
        assert marker in blob or marker in SYNTHETIC_RUN_ID or marker.startswith("document")


def test_synthetic_e2e_request_passes_sandbox_gate_with_copied_data(
    tmp_path: Path,
) -> None:
    case = build_synthetic_e2e_case(tmp_path)
    request = build_synthetic_sandbox_request(case, copied_data_confirmed=True)
    gate = evaluate_sandbox_gate(request)
    assert gate.approved is True
    assert gate.reason_code == "ready_for_sandbox_execution"
    assert gate.execution_scope == "sandbox"
    assert gate.processes_pdfs is False
    assert gate.scans_folders is False


def test_synthetic_e2e_request_fails_without_copied_data_confirmation(
    tmp_path: Path,
) -> None:
    case = build_synthetic_e2e_case(tmp_path)
    request = build_synthetic_sandbox_request(case, copied_data_confirmed=False)
    gate = evaluate_sandbox_gate(request)
    assert gate.approved is False
    assert gate.reason_code == "blocked_missing_copied_data_confirmation"

    calls: list = []

    def runner(args):
        calls.append(args)
        return build_synthetic_boundary_result(case)

    started = LocalProcessingAdapter(sandbox_runner=runner).start_run(request)
    assert started.status == "blocked"
    assert started.execution_gate == "blocked_missing_copied_data_confirmation"
    assert calls == []


def test_sandbox_boundary_receives_only_sandbox_input_output(tmp_path: Path) -> None:
    flow = run_synthetic_track_b_product_flow(tmp_path)
    assert flow.boundary_args is not None
    args = flow.boundary_args
    assert args.input_folder == flow.case.input_folder
    assert args.output_folder == flow.case.output_folder
    assert args.sandbox_root == flow.case.sandbox_root
    assert args.input_folder.startswith(flow.case.sandbox_root)
    assert args.output_folder.startswith(flow.case.sandbox_root)


def test_original_source_folder_not_passed_to_execution_boundary(
    tmp_path: Path,
) -> None:
    flow = run_synthetic_track_b_product_flow(tmp_path)
    assert flow.boundary_args is not None
    args = flow.boundary_args
    original = flow.case.original_source_folder
    assert args.input_folder != original
    assert args.output_folder != original
    assert not args.input_folder.startswith(original.rstrip("/") + "/")
    assert not args.output_folder.startswith(original.rstrip("/") + "/")
    # Exclusion metadata only — never used as processing path.
    assert args.original_source_folder == original
    assert args.input_folder != args.original_source_folder
    assert args.output_folder != args.original_source_folder


def test_adapter_maps_synthetic_success_review_error_counts(tmp_path: Path) -> None:
    case = build_synthetic_e2e_case(tmp_path)
    request = build_synthetic_sandbox_request(case)
    state = LocalProcessingAdapter(
        sandbox_runner=make_synthetic_boundary_runner(case)
    ).start_run(request)

    assert state.status == "completed"
    assert state.run_id == SYNTHETIC_RUN_ID
    assert len(state.results) == 2
    assert len(state.review_items) == 1
    assert len(state.errors) == 1
    assert state.errors[0] == MSG_SYNTHETIC_ERROR
    assert {item.document_name for item in state.results} == {DOC_SUCCESS, DOC_ERROR}
    assert state.review_items[0].document_name == DOC_REVIEW
    assert state.execution_gate == "ready_for_sandbox_execution"


def test_workspace_result_view_answers_five_product_questions(tmp_path: Path) -> None:
    flow = run_synthetic_track_b_product_flow(tmp_path)
    ui = UiV2State(processing_run_state=flow.run_state)
    shell = build_workspace_run_result_shell(ui)
    report = build_workspace_run_report_vm(ui)

    assert shell.status == "completed"
    assert shell.result_count == 2
    assert shell.review.count == 1
    assert shell.errors.count == 1
    assert shell.show_empty_state is False

    assert report.section_titles == (
        SECTION_RECOGNIZED,
        SECTION_UNCLEAR,
        SECTION_FAILED,
        SECTION_DESTINATIONS,
        SECTION_SUMMARY,
    )
    assert report.section_titles[0] == "Was wurde erkannt?"
    assert report.section_titles[1] == "Was ist unklar?"
    assert report.section_titles[2] == "Was ist fehlgeschlagen?"
    assert report.section_titles[3] == "Welche Dateien wären wohin gegangen?"
    assert report.section_titles[4] == "Welche Zusammenfassung bekommt der Nutzer?"

    recognized_names = {item.document_name for item in report.recognized}
    assert DOC_SUCCESS in recognized_names
    assert DOC_ERROR not in recognized_names

    assert len(report.unclear) == 1
    assert report.unclear[0].document_name == DOC_REVIEW

    failed_names = {item.document_name for item in report.failed if item.document_name}
    failed_messages = {item.message for item in report.failed}
    assert DOC_ERROR in failed_names
    assert MSG_SYNTHETIC_ERROR in failed_messages

    destinations = {
        item.document_name: item.destination_hint for item in report.destinations
    }
    assert flow.case.output_folder in destinations[DOC_SUCCESS]
    assert destinations[DOC_REVIEW] == "Zur Prüfung"
    assert all(item.planned_only for item in report.destinations)
    assert report.user_summary.recognized_count == 1
    assert report.user_summary.unclear_count == 1
    assert report.user_summary.failed_count >= 2


def test_review_workflow_shows_only_synthetic_review_item(tmp_path: Path) -> None:
    flow = run_synthetic_track_b_product_flow(tmp_path)
    queue = flow.review_queue
    assert queue.empty is False
    assert queue.review_count == 1
    assert queue.items[0].document_label == DOC_REVIEW
    assert queue.result_count == 2
    assert queue.error_count == 1
    assert MSG_RESULTS_SEPARATED in queue.separation_notes
    assert MSG_ERRORS_SEPARATED in queue.separation_notes
    assert queue.mutates_files is False
    # Results/errors are counted but not mixed into the review item list.
    assert {item.document_label for item in queue.items} == {DOC_REVIEW}


def test_export_reporting_preview_contains_five_product_sections(
    tmp_path: Path,
) -> None:
    flow = run_synthetic_track_b_product_flow(tmp_path)
    payload = flow.export_payload
    questions = payload["questions"]
    assert questions["recognized"]["title"] == SECTION_RECOGNIZED
    assert questions["unclear"]["title"] == SECTION_UNCLEAR
    assert questions["failed"]["title"] == SECTION_FAILED
    assert questions["destinations"]["title"] == SECTION_DESTINATIONS
    assert questions["user_summary"]["title"] == SECTION_SUMMARY
    assert questions["recognized"]["count"] == 1
    assert questions["unclear"]["count"] == 1
    assert questions["failed"]["count"] >= 2
    assert questions["destinations"]["planned_only"] is True
    assert payload["cloud"] is False
    assert payload["persistence"] == "local_export_only"


def test_export_reporting_preview_has_no_private_payment_account_data(
    tmp_path: Path,
) -> None:
    flow = run_synthetic_track_b_product_flow(tmp_path)
    blob = json.dumps(flow.export_payload, ensure_ascii=False)
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    # Explicit synthetic fixtures only — no invented IBAN/account/payment fields.
    lowered = blob.lower()
    for token in ("iban", "amex", "volksbank", "konto", "kreditkarte"):
        assert token not in lowered


def test_productive_execution_remains_blocked(tmp_path: Path) -> None:
    flow = run_synthetic_track_b_product_flow(tmp_path)
    assert flow.productive_blocked is True

    case = build_synthetic_e2e_case(tmp_path / "prod-block")
    request = build_synthetic_sandbox_request(
        case,
        dry_run=False,
        productive_execution_allowed=True,
    )
    calls: list = []

    def runner(args):
        calls.append(args)
        return build_synthetic_boundary_result(case)

    started = LocalProcessingAdapter(sandbox_runner=runner).start_run(request)
    assert started.status == "blocked"
    assert started.execution_gate == "blocked_productive_execution"
    assert calls == []


def test_track_a_entry_remains_separate() -> None:
    app_main = ROOT / "app_main.py"
    app_ui_v2 = ROOT / "app_ui_v2.py"
    assert app_main.is_file()
    assert app_ui_v2.is_file()
    assert app_main.resolve() != app_ui_v2.resolve()
    assert app_main.read_text(encoding="utf-8") != app_ui_v2.read_text(encoding="utf-8")
    synthetic_src = SYNTHETIC_MODULE.read_text(encoding="utf-8")
    assert "app_main" not in synthetic_src
    assert "invoice_tool.gui" not in synthetic_src
    assert "app_internal_launcher" not in synthetic_src


def test_no_processing_core_import_introduced() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    flow_module = "invoice_tool.ui_v2.synthetic_e2e_flow"
    sys.modules.pop(flow_module, None)
    import importlib

    importlib.import_module(flow_module)
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in FORBIDDEN_CORE:
        # Only reject core modules newly pulled in by this import.
        assert forbidden not in newly, forbidden

    for path in FLOW_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for name in imported:
            assert not any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in FORBIDDEN_CORE
            ), f"{path.name}: {name}"


def test_full_synthetic_product_flow_coherent(tmp_path: Path) -> None:
    flow = run_synthetic_track_b_product_flow(tmp_path)
    policy = build_synthetic_profile_policy(flow.case)

    assert flow.gate.approved is True
    assert policy.readiness_status == "ready"
    assert policy.has_private_defaults is False
    assert policy.productive_execution_enabled is False
    assert flow.run_state.status == "completed"
    assert flow.workspace_shell.has_run_payload is True
    assert flow.workspace_report.empty is False
    assert flow.review_queue.review_count == 1
    assert flow.export_payload["run_id"] == SYNTHETIC_RUN_ID
    assert flow.productive_blocked is True
    # No write outside tmp_path by the pure flow helper.
    assert str(tmp_path) in flow.case.sandbox_root
    assert Path(flow.case.sandbox_root).is_relative_to(tmp_path)
    assert Path(flow.case.original_source_folder).is_relative_to(tmp_path)


def test_synthetic_module_has_no_private_defaults() -> None:
    src = SYNTHETIC_MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in src, marker
    assert "filename_is_source_of_truth" not in src
