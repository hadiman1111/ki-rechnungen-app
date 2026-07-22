"""Track-B quality fixes after sandbox validation — pure/non-GUI tests."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.clarity_copy import (
    MSG_CLARITY_BUCKETS_SEPARATED,
    MSG_CLARITY_EXPORT_PREVIEW,
    MSG_CLARITY_FILENAME_NOT_TRUTH,
    MSG_CLARITY_NO_ORIGINAL_FOLDERS,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
    MSG_CLARITY_SANDBOX_COPIED_RUN,
    MSG_CLARITY_UNCLEAR_STAYS_REVIEW,
    TRACK_B_CLARITY_LINES,
    track_b_clarity_lines,
)
from invoice_tool.ui_v2.copied_real_data_validation import (
    MSG_BUSINESS_UNCLEAR,
    MSG_PAYMENT_UNCLEAR,
    validate_copied_real_data_sandbox,
)
from invoice_tool.ui_v2.export_reporting import (
    MSG_EXPORT_FROM_REAL_RUN,
    MSG_EXPORT_IS_PREVIEW,
    build_run_export_payload,
    build_run_report_view_model,
)
from invoice_tool.ui_v2.pages.settings import (
    EXPORT_SECTION_DETAIL,
    PRODUCTIVE_EXECUTION_NOTICE,
    build_settings_page_vm,
)
from invoice_tool.ui_v2.pages.workspace import (
    EMPTY_NO_RUN_DETAIL,
    SANDBOX_READINESS_LINES,
    workspace_honesty_copy,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_workflow import (
    MSG_BUCKETS_SEPARATED,
    MSG_UNCLEAR_CASES_STAY_REVIEW,
    build_review_actions,
    build_review_queue_view_model,
)
from invoice_tool.ui_v2.sandbox_processing_gate import workspace_sandbox_readiness_copy
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
CLARITY_MODULE = ROOT / "invoice_tool" / "ui_v2" / "clarity_copy.py"
UI_V2_ROOT = ROOT / "invoice_tool" / "ui_v2"
FORBIDDEN_CORE = (
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
    "Volksbank",
    "Privat",
)


def _completed_sandbox_state() -> ProcessingRunState:
    return ProcessingRunState(
        status="completed",
        message=MSG_CLARITY_SANDBOX_COPIED_RUN,
        run_id="quality-run-1",
        results=(
            ProcessingResultSummary(
                document_name="ok.pdf",
                document_type="rechnung",
                classification_status="ok",
                status_label="OK",
                target_hint="ziel/ok.pdf",
            ),
        ),
        review_items=(
            ProcessingReviewItem(
                document_name="payment.pdf",
                reason=MSG_PAYMENT_UNCLEAR,
                status_label="unklar",
                evidence_summary="Kein Zahlungsnachweis",
                next_action_hint="Manuell prüfen",
            ),
            ProcessingReviewItem(
                document_name="business.pdf",
                reason=MSG_BUSINESS_UNCLEAR,
                status_label="unklar",
                evidence_summary="Kein betrieblicher Nachweis",
                next_action_hint="Manuell prüfen",
            ),
        ),
        errors=("Fehlerfall getrennt",),
    )


def test_required_clarity_lines_are_stable() -> None:
    lines = track_b_clarity_lines()
    assert lines == TRACK_B_CLARITY_LINES
    assert MSG_CLARITY_SANDBOX_COPIED_RUN in lines
    assert MSG_CLARITY_NO_ORIGINAL_FOLDERS in lines
    assert MSG_CLARITY_PRODUCTIVE_NOT_RELEASED in lines
    assert MSG_CLARITY_UNCLEAR_STAYS_REVIEW in lines
    assert MSG_CLARITY_FILENAME_NOT_TRUTH in lines
    assert MSG_CLARITY_EXPORT_PREVIEW in lines
    assert MSG_CLARITY_BUCKETS_SEPARATED in lines


def test_workspace_includes_sandbox_and_non_productive_clarity() -> None:
    honesty = workspace_honesty_copy(has_real_results=False)
    blob = " ".join(
        [
            honesty.results_detail or "",
            EMPTY_NO_RUN_DETAIL,
            *honesty.sandbox_readiness_lines,
            *SANDBOX_READINESS_LINES,
            *workspace_sandbox_readiness_copy(),
        ]
    )
    assert MSG_CLARITY_SANDBOX_COPIED_RUN in blob
    assert MSG_CLARITY_NO_ORIGINAL_FOLDERS in blob
    assert MSG_CLARITY_PRODUCTIVE_NOT_RELEASED in blob
    assert MSG_CLARITY_BUCKETS_SEPARATED in blob
    assert MSG_CLARITY_FILENAME_NOT_TRUTH in blob


def test_workspace_five_question_sections_are_distinct() -> None:
    report = build_run_report_view_model(_completed_sandbox_state())
    assert report.section_titles == (
        "Was wurde erkannt?",
        "Was ist unklar?",
        "Was ist fehlgeschlagen?",
        "Welche Dateien wären wohin gegangen?",
        "Welche Zusammenfassung bekommt der Nutzer?",
    )
    assert len(report.recognized) == 1
    assert len(report.unclear) == 2
    assert len(report.failed) == 1
    assert MSG_CLARITY_BUCKETS_SEPARATED in report.honest_copy
    assert MSG_CLARITY_SANDBOX_COPIED_RUN in report.message
    # Sections stay distinct buckets — no cross-mix of document names.
    recognized_names = {item.document_name for item in report.recognized}
    unclear_names = {item.document_name for item in report.unclear}
    failed_messages = {item.message for item in report.failed}
    assert recognized_names.isdisjoint(unclear_names)
    assert "Fehlerfall getrennt" in failed_messages


def test_review_payment_and_business_reasons_are_human_readable() -> None:
    queue = build_review_queue_view_model(_completed_sandbox_state())
    reasons = " ".join(item.reason for item in queue.items)
    assert "Zahlungsnachweis unklar" in reasons
    assert "bitte manuell prüfen" in reasons
    assert "Betrieblich/persönlicher Nachweis unklar" in reasons
    assert "Dateiname ist keine Belegwahrheit" in reasons
    assert MSG_UNCLEAR_CASES_STAY_REVIEW in queue.honest_copy
    assert MSG_BUCKETS_SEPARATED in queue.separation_notes


def test_review_actions_remain_disabled_readiness_only() -> None:
    actions = build_review_actions(has_items=True)
    assert actions
    assert all(action.enabled is False for action in actions)
    assert all(action.persists is False for action in actions)
    assert all(action.mutates_files is False for action in actions)
    assert all(action.opens_pdf is False for action in actions)


def test_export_preview_says_preview_and_not_datev_cloud() -> None:
    report = build_run_report_view_model(_completed_sandbox_state())
    payload = build_run_export_payload(report)
    assert MSG_EXPORT_IS_PREVIEW in report.honest_copy
    assert MSG_EXPORT_FROM_REAL_RUN in report.honest_copy
    assert "keine Vorschau-Daten" not in MSG_EXPORT_FROM_REAL_RUN
    assert payload["preview"] is True
    assert payload["productive_export"] is False
    assert payload["datev_export"] is False
    assert payload["cloud_export"] is False
    assert payload["cloud"] is False
    assert payload["disclaimer"] == MSG_CLARITY_EXPORT_PREVIEW
    blob = " ".join(report.honest_copy) + " " + EXPORT_SECTION_DETAIL
    assert "DATEV" in blob
    assert "Vorschau" in blob
    assert "DATEV-/Cloud-Export" in blob


def test_sandbox_validation_report_clarity(tmp_path: Path) -> None:
    result = validate_copied_real_data_sandbox(tmp_path)
    report = result.validation_report
    assert report.original_excluded_from_input is True
    assert MSG_CLARITY_NO_ORIGINAL_FOLDERS in report.user_clarity_lines
    assert MSG_CLARITY_SANDBOX_COPIED_RUN in report.user_clarity_lines
    assert report.original_folders_excluded_message == MSG_CLARITY_NO_ORIGINAL_FOLDERS
    assert "kopierte" in report.copied_data_only_message.lower()
    assert report.no_filename_as_truth is True
    assert report.filename_not_truth_message == MSG_CLARITY_FILENAME_NOT_TRUTH
    assert report.productive_blocked is True
    assert report.productive_blocked_message == MSG_CLARITY_PRODUCTIVE_NOT_RELEASED
    for line in TRACK_B_CLARITY_LINES:
        assert line in report.user_clarity_lines


def test_filename_as_truth_absent_and_no_private_tokens() -> None:
    report = build_run_report_view_model(_completed_sandbox_state())
    queue = build_review_queue_view_model(_completed_sandbox_state())
    settings = build_settings_page_vm(UiV2State())
    blob = " ".join(
        [
            *report.honest_copy,
            *queue.honest_copy,
            settings.productive_execution_notice,
            settings.banner,
            EXPORT_SECTION_DETAIL,
            PRODUCTIVE_EXECUTION_NOTICE,
            CLARITY_MODULE.read_text(encoding="utf-8"),
        ]
    )
    assert MSG_CLARITY_FILENAME_NOT_TRUTH in blob
    assert "filename_is_source_of_truth=True" not in blob
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker


def test_no_productive_execution_toggle_in_settings() -> None:
    vm = build_settings_page_vm()
    assert vm.has_productive_toggle is False
    assert vm.productive_execution_enabled is False
    assert vm.productive_execution_notice == MSG_CLARITY_PRODUCTIVE_NOT_RELEASED
    assert PRODUCTIVE_EXECUTION_NOTICE == MSG_CLARITY_PRODUCTIVE_NOT_RELEASED


def test_no_processing_core_imports_in_clarity_and_quality_modules() -> None:
    modules = (
        CLARITY_MODULE,
        UI_V2_ROOT / "export_reporting.py",
        UI_V2_ROOT / "review_workflow.py",
        UI_V2_ROOT / "sandbox_processing_gate.py",
        UI_V2_ROOT / "copied_real_data_validation.py",
        UI_V2_ROOT / "pages" / "workspace.py",
        UI_V2_ROOT / "pages" / "settings.py",
        UI_V2_ROOT / "pages" / "review.py",
    )
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(
                        alias.name == core or alias.name.startswith(core + ".")
                        for core in FORBIDDEN_CORE
                    ), (path.name, alias.name)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(
                    node.module == core or node.module.startswith(core + ".")
                    for core in FORBIDDEN_CORE
                ), (path.name, node.module)


def test_track_a_protection_module_still_importable() -> None:
    # Static presence check — full Track-A suite remains in dedicated test module.
    protection = ROOT / "tests" / "test_track_a_internal_app_protection.py"
    assert protection.is_file()
    src = protection.read_text(encoding="utf-8")
    assert "app_main" in src
    assert "app_ui_v2" in src or "ui_v2" in src
