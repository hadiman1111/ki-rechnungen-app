"""Track-B UI-v2 run result display shell — non-GUI, no PDF processing."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.pages.workspace import (
    build_workspace_readiness_display_vm,
    build_workspace_run_result_shell,
    workspace_honesty_copy,
)
from invoice_tool.ui_v2.processing_state import (
    MSG_DRY_RUN_UNAVAILABLE,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
    blocked_processing_state,
    idle_processing_state,
)
from invoice_tool.ui_v2.run_result_display import (
    MSG_PRODUCTIVE_HOLD,
    STATUS_LABELS,
    build_blocked_execution_hints,
    build_run_result_display_shell,
    result_row_from_summary,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
DISPLAY_MODULE = ROOT / "invoice_tool" / "ui_v2" / "run_result_display.py"
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
PROCESSING_CORE = (
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
    "Desktop/Programm Belegerfassung",
    "Volksbank",
)


def test_empty_shell_when_no_run_or_results() -> None:
    shell = build_run_result_display_shell(idle_processing_state())
    assert shell.status == "idle"
    assert shell.status_label == STATUS_LABELS["idle"]
    assert shell.results == ()
    assert shell.review.count == 0
    assert shell.errors.count == 0
    assert shell.show_empty_state is True
    assert shell.empty_results is True
    assert workspace_honesty_copy(
        has_real_results=False,
        processing_state=idle_processing_state(),
    ).has_real_results is False


def test_shell_displays_all_run_statuses() -> None:
    for status in (
        "idle",
        "not_configured",
        "ready",
        "running",
        "completed",
        "failed",
        "blocked",
    ):
        shell = build_run_result_display_shell(
            ProcessingRunState(status=status, message=f"status-{status}")
        )
        assert shell.status == status
        assert shell.status_label == STATUS_LABELS[status]
        assert shell.message == f"status-{status}"


def test_shell_displays_only_provided_result_summaries() -> None:
    provided = (
        ProcessingResultSummary(
            document_name="doc-a.pdf",
            document_type="rechnung",
            classification_status="ok",
            status_label="OK",
            confidence_label="hoch",
            target_hint="Ziel/doc-a.pdf",
        ),
        ProcessingResultSummary(
            document_name="doc-b.pdf",
            document_type="beleg",
            classification_status="ok",
            status_label="OK",
        ),
    )
    shell = build_run_result_display_shell(
        ProcessingRunState(status="completed", results=provided)
    )
    assert shell.result_count == 2
    assert shell.results[0].document_name == "doc-a.pdf"
    assert shell.results[0].target_hint == "Ziel/doc-a.pdf"
    assert shell.results[1].document_name == "doc-b.pdf"
    assert shell.results[1].confidence_label is None
    assert shell.show_empty_state is False


def test_shell_does_not_create_fake_results() -> None:
    shell = build_run_result_display_shell(
        ProcessingRunState(status="completed", message="Lauf abgeschlossen.")
    )
    assert shell.results == ()
    assert shell.result_count == 0
    row = result_row_from_summary(
        ProcessingResultSummary(
            document_name="only-real.pdf",
            document_type="dokument",
            classification_status="ok",
            status_label="OK",
        )
    )
    assert row.document_name == "only-real.pdf"
    assert "payment" not in row.status_label.lower()
    assert "account" not in (row.target_hint or "").lower()


def test_review_items_counted_separately_from_results() -> None:
    state = ProcessingRunState(
        status="completed",
        results=(
            ProcessingResultSummary(
                document_name="ok.pdf",
                document_type="rechnung",
                classification_status="ok",
                status_label="OK",
            ),
        ),
        review_items=(
            ProcessingReviewItem(
                document_name="review.pdf",
                reason="Zuordnung unklar",
                status_label="unklar",
            ),
        ),
        errors=("Fehler A",),
    )
    shell = build_run_result_display_shell(state)
    assert shell.result_count == 1
    assert shell.review.count == 1
    assert shell.errors.count == 1
    assert shell.results[0].document_name == "ok.pdf"
    assert shell.review.items[0].document_name == "review.pdf"
    assert "review.pdf" not in {item.document_name for item in shell.results}
    assert "Fehler A" not in {item.reason for item in shell.review.items}


def test_errors_counted_separately_from_review_items() -> None:
    shell = build_run_result_display_shell(
        ProcessingRunState(
            status="failed",
            review_items=(
                ProcessingReviewItem(
                    document_name="review-only.pdf",
                    reason="Konflikt",
                ),
            ),
            errors=("Lesefehler", "Ziel fehlt"),
        )
    )
    assert shell.review.count == 1
    assert shell.errors.count == 2
    assert shell.errors.messages == ("Lesefehler", "Ziel fehlt")
    assert shell.review.items[0].document_name == "review-only.pdf"


def test_blocked_dry_run_and_productive_messages_are_honest() -> None:
    hints = build_blocked_execution_hints(
        blocked_processing_state(
            MSG_DRY_RUN_UNAVAILABLE,
            execution_gate="unsupported_without_core_change",
            dry_run_gate="unsupported_without_core_change",
            core_dry_run_status="unsupported_without_core_change",
        )
    )
    assert MSG_PRODUCTIVE_HOLD in hints
    assert MSG_DRY_RUN_UNAVAILABLE in hints
    assert hints[0] == MSG_PRODUCTIVE_HOLD
    assert "Produktive Verarbeitung ist noch nicht freigegeben." in hints
    assert "Dry-Run ohne Dateiveränderung ist im lokalen Core noch nicht verfügbar." in hints

    copy = workspace_honesty_copy(
        has_real_results=False,
        processing_state=blocked_processing_state(MSG_DRY_RUN_UNAVAILABLE),
    )
    assert MSG_PRODUCTIVE_HOLD in (copy.results_detail or "")
    assert MSG_DRY_RUN_UNAVAILABLE in (copy.results_detail or "")


def test_workspace_shell_uses_processing_run_state() -> None:
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="ready",
            message="Anfrage vorbereitet.",
            results=(),
        )
    )
    shell = build_workspace_run_result_shell(state)
    assert shell.status == "ready"
    assert shell.status_label == "Bereit"
    assert shell.results == ()
    assert shell.show_empty_state is True


def test_workspace_readiness_shows_folder_run_dry_gate_and_counts_honestly() -> None:
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="blocked",
            message=MSG_DRY_RUN_UNAVAILABLE,
            execution_gate="unsupported_without_core_change",
            dry_run_gate="unsupported_without_core_change",
            core_dry_run_status="unsupported_without_core_change",
            results=(
                ProcessingResultSummary(
                    document_name="only-real.pdf",
                    document_type="beleg",
                    classification_status="ok",
                    status_label="OK",
                ),
            ),
            review_items=(
                ProcessingReviewItem(
                    document_name="review.pdf",
                    reason="Unklar",
                ),
            ),
            errors=("Fehler X",),
        )
    )
    state.set_workspace_input_folder("in-folder")
    state.set_workspace_output_folder("out-folder")
    readiness = build_workspace_readiness_display_vm(state)
    assert readiness.input_folder_selected is True
    assert readiness.output_folder_selected is True
    assert readiness.run_status == "blocked"
    assert readiness.dry_gate_blocked is True
    assert readiness.dry_gate_message == MSG_DRY_RUN_UNAVAILABLE
    assert readiness.productive_hold is True
    assert readiness.result_count == 1
    assert readiness.review_count == 1
    assert readiness.error_count == 1
    assert readiness.implies_successful_processing is False
    assert readiness.offers_productive_execution is False
    assert readiness.has_fake_counters is False


def test_workspace_readiness_has_no_fake_counters_when_idle() -> None:
    readiness = build_workspace_readiness_display_vm(UiV2State())
    assert readiness.result_count == 0
    assert readiness.review_count == 0
    assert readiness.error_count == 0
    assert readiness.implies_successful_processing is False
    assert readiness.has_fake_counters is False
    assert readiness.input_folder_selected is False
    assert readiness.output_folder_selected is False


def test_review_page_keeps_errors_out_of_queue() -> None:
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="failed",
            review_items=(
                ProcessingReviewItem(
                    document_name="check.pdf",
                    reason="Unklar",
                ),
            ),
            errors=("IO-Fehler",),
            results=(
                ProcessingResultSummary(
                    document_name="ok.pdf",
                    document_type="beleg",
                    classification_status="ok",
                    status_label="OK",
                ),
            ),
        )
    )
    vm = build_review_page_vm(state)
    assert vm.empty is False
    assert len(vm.items) == 1
    assert vm.items[0].document_name == "check.pdf"
    assert vm.error_count == 1
    assert vm.result_count == 1
    assert all(item.document_name != "ok.pdf" for item in vm.items)


def test_no_private_tokens_in_display_module() -> None:
    src = DISPLAY_MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in src, marker
    workspace_src = WORKSPACE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in workspace_src, marker


def test_no_filename_as_truth_or_productive_toggle() -> None:
    src = DISPLAY_MODULE.read_text(encoding="utf-8")
    assert "filename_is_source_of_truth" not in src
    assert "Switch" not in src
    assert "Checkbox" not in src
    assert "produktive Ausführung aktivieren" not in src.lower()
    workspace_src = WORKSPACE.read_text(encoding="utf-8")
    assert "filename_is_source_of_truth" not in workspace_src
    assert "list_input_pdf" not in workspace_src


def test_display_module_has_no_processing_core_import() -> None:
    src = DISPLAY_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for forbidden in PROCESSING_CORE:
        assert forbidden not in imported
        assert forbidden not in src


def test_import_does_not_load_processing_core() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    importlib.import_module("invoice_tool.ui_v2.run_result_display")
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in PROCESSING_CORE:
        assert forbidden not in newly, forbidden
