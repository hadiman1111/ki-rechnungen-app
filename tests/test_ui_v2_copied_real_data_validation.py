"""Copied-realistic Track-B sandbox validation — no real invoices / OCR / GUI."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

from invoice_tool.ui_v2.copied_real_data_validation import (
    COPIED_MARKERS,
    COPIED_RUN_ID,
    DOC_ERROR,
    DOC_INVOICE,
    DOC_RECEIPT,
    DOC_UNCLEAR,
    FAKE_FILE_SUFFIX,
    MSG_BUSINESS_UNCLEAR,
    MSG_PAYMENT_UNCLEAR,
    MSG_UNSUPPORTED_ERROR,
    build_copied_boundary_result,
    build_copied_processing_state,
    build_copied_profile_policy,
    build_copied_realistic_fixture,
    build_copied_sandbox_request,
    build_quality_checklist_rows,
    make_copied_boundary_runner,
    validate_copied_real_data_sandbox,
)
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

ROOT = Path(__file__).resolve().parents[1]
COPIED_MODULE = ROOT / "invoice_tool" / "ui_v2" / "copied_real_data_validation.py"
FLOW_MODULES = (
    COPIED_MODULE,
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
    "02_Rechnungseingang",
    "Eingang",
)


def test_copied_realistic_fixture_created_only_in_tmp_path(tmp_path: Path) -> None:
    case = build_copied_realistic_fixture(tmp_path)
    assert Path(case.sandbox_root).is_relative_to(tmp_path)
    assert Path(case.input_folder).is_relative_to(tmp_path)
    assert Path(case.output_folder).is_relative_to(tmp_path)
    assert Path(case.original_source_folder).is_relative_to(tmp_path)
    assert case.fixture_files
    for path in case.fixture_files:
        p = Path(path)
        assert p.is_relative_to(tmp_path)
        assert p.exists()
        # Never lands under known original invoice folder names.
        assert "02_Rechnungseingang" not in str(p)
        assert "/Eingang/" not in str(p)
    # Fake stub files only — no repository PDF fixtures.
    fake_files = [p for p in case.fixture_files if p.endswith(FAKE_FILE_SUFFIX)]
    assert len(fake_files) == 4
    for path in fake_files:
        assert Path(path).read_bytes() == b""


def test_copied_realistic_fixture_contains_recognized_review_error_categories(
    tmp_path: Path,
) -> None:
    case = build_copied_realistic_fixture(tmp_path)
    boundary = build_copied_boundary_result(case)
    state = build_copied_processing_state(case)
    rows = build_quality_checklist_rows(case)

    categories = {row.category for row in rows}
    assert categories == {
        "recognized",
        "review_payment_unclear",
        "review_business_unclear",
        "error_unsupported",
    }
    assert {item.document_name for item in boundary.results} == {DOC_INVOICE, DOC_ERROR}
    assert {item.document_name for item in boundary.review_items} == {
        DOC_RECEIPT,
        DOC_UNCLEAR,
    }
    assert MSG_UNSUPPORTED_ERROR in boundary.errors
    assert len(state.results) == 2
    assert len(state.review_items) == 2
    assert len(state.errors) == 1
    for marker in (DOC_INVOICE, DOC_RECEIPT, DOC_UNCLEAR, DOC_ERROR):
        assert marker in COPIED_MARKERS or marker.startswith("copied-")


def test_sandbox_gate_blocks_original_folder(tmp_path: Path) -> None:
    case = build_copied_realistic_fixture(tmp_path)
    # Attempt to use original as input — must be blocked.
    request = build_copied_sandbox_request(case)
    from invoice_tool.ui_v2.processing_contract import ProcessingRunRequest

    blocked_request = ProcessingRunRequest(
        input_folder=case.original_source_folder,
        output_folder=case.output_folder,
        profile_id=request.profile_id,
        configuration_id=request.configuration_id,
        dry_run=True,
        source=request.source,
        policy_intent=request.policy_intent,
        policy_bridge_result=request.policy_bridge_result,
        user_confirmed_start=True,
        sandbox_mode=True,
        sandbox_root=case.sandbox_root,
        original_source_folder=case.original_source_folder,
        copied_data_confirmed=True,
        productive_execution_allowed=False,
        execution_scope="sandbox",
    )
    gate = evaluate_sandbox_gate(blocked_request)
    assert gate.approved is False
    assert gate.reason_code in {
        "blocked_original_folder",
        "blocked_input_outside_sandbox",
    }


def test_sandbox_gate_accepts_copied_sandbox_input_output(tmp_path: Path) -> None:
    case = build_copied_realistic_fixture(tmp_path)
    request = build_copied_sandbox_request(case, copied_data_confirmed=True)
    gate = evaluate_sandbox_gate(request)
    assert gate.approved is True
    assert gate.reason_code == "ready_for_sandbox_execution"
    assert gate.execution_scope == "sandbox"
    assert gate.processes_pdfs is False
    assert gate.scans_folders is False


def test_productive_mode_remains_blocked(tmp_path: Path) -> None:
    flow = validate_copied_real_data_sandbox(tmp_path)
    assert flow.productive_blocked is True
    assert flow.validation_report.productive_blocked is True

    case = build_copied_realistic_fixture(tmp_path / "prod-block")
    request = build_copied_sandbox_request(
        case,
        dry_run=False,
        productive_execution_allowed=True,
    )
    calls: list = []

    def runner(args):
        calls.append(args)
        return build_copied_boundary_result(case)

    started = LocalProcessingAdapter(sandbox_runner=runner).start_run(request)
    assert started.status == "blocked"
    assert started.execution_gate == "blocked_productive_execution"
    assert calls == []


def test_boundary_receives_copied_sandbox_paths_only(tmp_path: Path) -> None:
    flow = validate_copied_real_data_sandbox(tmp_path)
    assert flow.boundary_args is not None
    args = flow.boundary_args
    assert args.input_folder == flow.case.input_folder
    assert args.output_folder == flow.case.output_folder
    assert args.sandbox_root == flow.case.sandbox_root
    assert args.input_folder.startswith(flow.case.sandbox_root)
    assert args.output_folder.startswith(flow.case.sandbox_root)
    assert flow.validation_report.boundary_paths_sandbox_only is True


def test_original_source_folder_never_used_for_execution(tmp_path: Path) -> None:
    flow = validate_copied_real_data_sandbox(tmp_path)
    assert flow.boundary_args is not None
    args = flow.boundary_args
    original = flow.case.original_source_folder
    assert args.input_folder != original
    assert args.output_folder != original
    assert not args.input_folder.startswith(original.rstrip("/") + "/")
    assert not args.output_folder.startswith(original.rstrip("/") + "/")
    assert args.original_source_folder == original
    assert flow.validation_report.original_excluded_from_input is True


def test_review_workflow_displays_payment_and_business_unclear(tmp_path: Path) -> None:
    flow = validate_copied_real_data_sandbox(tmp_path)
    queue = flow.review_queue
    assert queue.empty is False
    assert queue.review_count == 2
    labels = {item.document_label for item in queue.items}
    assert labels == {DOC_RECEIPT, DOC_UNCLEAR}
    reasons = {item.reason for item in queue.items}
    assert MSG_PAYMENT_UNCLEAR in reasons
    assert MSG_BUSINESS_UNCLEAR in reasons
    assert queue.result_count == 2
    assert queue.error_count == 1
    assert MSG_RESULTS_SEPARATED in queue.separation_notes
    assert MSG_ERRORS_SEPARATED in queue.separation_notes
    assert "Ergebnisse, Prüffälle und Fehler werden getrennt geführt." in queue.separation_notes
    assert "Unklare Fälle bleiben zur Prüfung." in queue.honest_copy
    assert queue.mutates_files is False
    assert flow.validation_report.review_payment_visible is True
    assert flow.validation_report.review_business_visible is True
    assert "bitte manuell prüfen" in " ".join(reasons)


def test_export_report_contains_recognized_review_error_target_summary(
    tmp_path: Path,
) -> None:
    flow = validate_copied_real_data_sandbox(tmp_path)
    payload = flow.export_payload
    questions = payload["questions"]
    assert questions["recognized"]["title"] == SECTION_RECOGNIZED
    assert questions["unclear"]["title"] == SECTION_UNCLEAR
    assert questions["failed"]["title"] == SECTION_FAILED
    assert questions["destinations"]["title"] == SECTION_DESTINATIONS
    assert questions["user_summary"]["title"] == SECTION_SUMMARY
    assert questions["recognized"]["count"] == 1
    assert questions["unclear"]["count"] == 2
    assert questions["failed"]["count"] >= 2
    assert questions["destinations"]["planned_only"] is True
    assert payload["cloud"] is False
    assert payload["preview"] is True
    assert payload["productive_export"] is False
    assert payload["datev_export"] is False
    assert payload["persistence"] == "local_export_only"
    assert "Vorschau" in payload["disclaimer"]
    assert "DATEV" in payload["disclaimer"]
    report = flow.validation_report
    assert report.export_has_recognized
    assert report.export_has_unclear
    assert report.export_has_failed
    assert report.export_has_destinations
    assert report.export_has_summary
    assert report.original_folders_excluded_message == "Originalordner werden nicht verwendet."
    assert "kopierte" in report.copied_data_only_message.lower()
    assert "Dies ist ein Sandbox-Lauf mit kopierten Daten." in report.user_clarity_lines


def test_workspace_answers_five_questions_with_copied_realistic_data(
    tmp_path: Path,
) -> None:
    flow = validate_copied_real_data_sandbox(tmp_path)
    ui = UiV2State(processing_run_state=flow.run_state)
    shell = build_workspace_run_result_shell(ui)
    report = build_workspace_run_report_vm(ui)

    assert shell.status == "completed"
    assert shell.result_count == 2
    assert shell.review.count == 2
    assert shell.errors.count == 1
    assert shell.show_empty_state is False

    assert report.section_titles == (
        SECTION_RECOGNIZED,
        SECTION_UNCLEAR,
        SECTION_FAILED,
        SECTION_DESTINATIONS,
        SECTION_SUMMARY,
    )
    recognized_names = {item.document_name for item in report.recognized}
    assert DOC_INVOICE in recognized_names
    assert DOC_ERROR not in recognized_names

    unclear_names = {item.document_name for item in report.unclear}
    assert unclear_names == {DOC_RECEIPT, DOC_UNCLEAR}

    failed_names = {item.document_name for item in report.failed if item.document_name}
    failed_messages = {item.message for item in report.failed}
    assert DOC_ERROR in failed_names
    assert MSG_UNSUPPORTED_ERROR in failed_messages

    destinations = {
        item.document_name: item.destination_hint for item in report.destinations
    }
    assert flow.case.output_folder in destinations[DOC_INVOICE]
    assert destinations[DOC_RECEIPT] == "Zur Prüfung"
    assert destinations[DOC_UNCLEAR] == "Zur Prüfung"
    assert all(item.planned_only for item in report.destinations)
    assert report.user_summary.recognized_count == 1
    assert report.user_summary.unclear_count == 2
    assert report.user_summary.failed_count >= 2
    assert flow.validation_report.five_questions_answered is True


def test_no_private_tokens_appear(tmp_path: Path) -> None:
    flow = validate_copied_real_data_sandbox(tmp_path)
    blob = json.dumps(
        {
            "export": flow.export_payload,
            "run_id": flow.run_state.run_id,
            "docs": [DOC_INVOICE, DOC_RECEIPT, DOC_UNCLEAR, DOC_ERROR],
            "errors": list(flow.run_state.errors),
        },
        ensure_ascii=False,
    )
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    src = COPIED_MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in src, marker
    assert flow.validation_report.no_private_defaults is True


def test_no_filename_as_truth_behavior(tmp_path: Path) -> None:
    case = build_copied_realistic_fixture(tmp_path)
    rows = build_quality_checklist_rows(case)
    assert all(row.filename_is_not_truth for row in rows)
    # Meta markers declare classification source is fixture metadata, not name.
    meta_files = [
        Path(p) for p in case.fixture_files if p.endswith(".meta.txt")
    ]
    assert len(meta_files) == 4
    for meta in meta_files:
        text = meta.read_text(encoding="utf-8")
        assert "filename_is_not_source_of_truth=true" in text
        assert "classification_source=explicit_fixture_metadata" in text
    src = COPIED_MODULE.read_text(encoding="utf-8")
    assert "filename_is_source_of_truth" not in src
    # Categories are assigned by explicit helper rows, not by parsing names.
    by_id = {row.document_id: row.category for row in rows}
    assert by_id[DOC_INVOICE] == "recognized"
    assert by_id[DOC_RECEIPT] == "review_payment_unclear"
    assert by_id[DOC_UNCLEAR] == "review_business_unclear"
    assert by_id[DOC_ERROR] == "error_unsupported"
    flow = validate_copied_real_data_sandbox(tmp_path / "truth")
    assert flow.validation_report.no_filename_as_truth is True


def test_no_processing_core_import_introduced() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    flow_module = "invoice_tool.ui_v2.copied_real_data_validation"
    sys.modules.pop(flow_module, None)
    import importlib

    importlib.import_module(flow_module)
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in FORBIDDEN_CORE:
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


def test_track_a_entry_remains_separate() -> None:
    app_main = ROOT / "app_main.py"
    app_ui_v2 = ROOT / "app_ui_v2.py"
    assert app_main.is_file()
    assert app_ui_v2.is_file()
    assert app_main.resolve() != app_ui_v2.resolve()
    assert app_main.read_text(encoding="utf-8") != app_ui_v2.read_text(encoding="utf-8")
    copied_src = COPIED_MODULE.read_text(encoding="utf-8")
    assert "app_main" not in copied_src
    assert "invoice_tool.gui" not in copied_src
    assert "app_internal_launcher" not in copied_src


def test_quality_checklist_and_full_validation_report_coherent(tmp_path: Path) -> None:
    flow = validate_copied_real_data_sandbox(tmp_path)
    policy = build_copied_profile_policy(flow.case)
    report = flow.validation_report

    assert flow.gate.approved is True
    assert policy.readiness_status == "ready"
    assert policy.has_private_defaults is False
    assert policy.productive_execution_enabled is False
    assert flow.run_state.status == "completed"
    assert flow.run_state.run_id == COPIED_RUN_ID
    assert flow.workspace_shell.has_run_payload is True
    assert flow.workspace_report.empty is False
    assert flow.review_queue.review_count == 2
    assert flow.export_payload["run_id"] == COPIED_RUN_ID

    assert report.categories_present == (
        "recognized",
        "review_payment_unclear",
        "review_business_unclear",
        "error_unsupported",
    )
    assert report.sandbox_input_under_root is True
    assert report.sandbox_output_under_root is True
    assert report.fixture_inside_tmp is True
    assert report.no_writes_outside_tmp is True
    assert len(report.quality_rows) == 4
    for row in report.quality_rows:
        assert row.document_id
        assert row.category
        assert row.reason
        assert row.expected_ui_section
        assert row.expected_export_section
        assert row.filename_is_not_truth is True


def test_adapter_maps_copied_realistic_counts(tmp_path: Path) -> None:
    case = build_copied_realistic_fixture(tmp_path)
    request = build_copied_sandbox_request(case)
    state = LocalProcessingAdapter(
        sandbox_runner=make_copied_boundary_runner(case)
    ).start_run(request)

    assert state.status == "completed"
    assert state.run_id == COPIED_RUN_ID
    assert len(state.results) == 2
    assert len(state.review_items) == 2
    assert len(state.errors) == 1
    assert state.errors[0] == MSG_UNSUPPORTED_ERROR
    assert {item.document_name for item in state.results} == {DOC_INVOICE, DOC_ERROR}
    assert {item.document_name for item in state.review_items} == {
        DOC_RECEIPT,
        DOC_UNCLEAR,
    }
    assert state.execution_gate == "ready_for_sandbox_execution"


def test_copied_module_has_no_private_defaults() -> None:
    src = COPIED_MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in src, marker
    assert "filename_is_source_of_truth" not in src
    # Default request builder keeps productive execution off.
    assert "productive_execution_allowed: bool = False" in src
