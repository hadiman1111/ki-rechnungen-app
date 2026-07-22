"""Track-B UI-v2 review workflow completion — pure/non-GUI tests."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.pages.workspace import build_workspace_readiness_display_vm
from invoice_tool.ui_v2.processing_state import (
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_workflow import (
    ACTION_CHECK_EVIDENCE,
    ACTION_MARK_REVIEWED,
    ACTION_SAVE_LATER,
    EMPTY_REVIEW_DETAIL,
    EMPTY_REVIEW_TITLE,
    MSG_ACTION_NOT_CONNECTED,
    MSG_ERRORS_SEPARATED,
    MSG_RESULTS_SEPARATED,
    MSG_REVIEW_FROM_REAL_RUN,
    MSG_REVIEW_NO_FILE_MUTATION,
    build_review_item_view_model,
    build_review_queue_view_model,
)
from invoice_tool.ui_v2.run_result_display import MSG_REVIEW_DETAILS_HINT
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
REVIEW_WORKFLOW = ROOT / "invoice_tool" / "ui_v2" / "review_workflow.py"
REVIEW_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
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
    "Desktop/",
    "Privat",
    "Volksbank",
)


def test_review_page_empty_state_is_honest() -> None:
    vm = build_review_page_vm(UiV2State())
    assert vm.empty is True
    assert vm.empty_title == EMPTY_REVIEW_TITLE
    assert vm.empty_detail == EMPTY_REVIEW_DETAIL
    assert vm.empty_title == "Keine Prüffälle vorhanden."
    assert vm.empty_detail == "Prüffälle entstehen erst aus einem echten Verarbeitungslauf."
    assert MSG_REVIEW_FROM_REAL_RUN in vm.honest_copy
    assert MSG_REVIEW_NO_FILE_MUTATION in vm.honest_copy
    assert "Diese Ansicht verändert keine Dateien." in vm.honest_copy


def test_review_page_says_it_does_not_change_files() -> None:
    vm = build_review_page_vm(UiV2State())
    assert vm.mutates_files is False
    assert MSG_REVIEW_NO_FILE_MUTATION in vm.honest_copy
    assert "Diese Ansicht verändert keine Dateien." in MSG_REVIEW_NO_FILE_MUTATION
    src_page = REVIEW_PAGE.read_text(encoding="utf-8")
    src_workflow = REVIEW_WORKFLOW.read_text(encoding="utf-8")
    assert "MSG_REVIEW_NO_FILE_MUTATION" in src_page
    assert MSG_REVIEW_NO_FILE_MUTATION in src_workflow
    for token in ("unlink(", "rename(", "shutil.", "Path.write", "mkdir("):
        assert token not in src_page, token
        assert token not in src_workflow, token


def test_review_page_displays_only_injected_review_items() -> None:
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="completed",
            run_id="run-42",
            review_items=(
                ProcessingReviewItem(
                    document_name="beispiel.pdf",
                    reason="Zuordnung unklar",
                    status_label="unklar",
                    document_id="doc-1",
                    evidence_summary="Kein eindeutiger Zahlernachweis",
                    next_action_hint="Profilregel prüfen",
                ),
            ),
        )
    )
    vm = build_review_page_vm(state)
    assert vm.empty is False
    assert vm.review_count == 1
    assert len(vm.items) == 1
    assert vm.items[0].document_name == "beispiel.pdf"
    detail = vm.detail_items[0]
    assert detail.reason == "Zuordnung unklar"
    assert detail.evidence_summary == "Kein eindeutiger Zahlernachweis"
    assert detail.next_action_hint == "Profilregel prüfen"
    assert detail.source_run_id == "run-42"


def test_review_page_does_not_display_successful_results_as_review_items() -> None:
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="completed",
            results=(
                ProcessingResultSummary(
                    document_name="ok.pdf",
                    document_type="beleg",
                    classification_status="ok",
                    status_label="OK",
                ),
            ),
            review_items=(
                ProcessingReviewItem(
                    document_name="review-only.pdf",
                    reason="Konflikt",
                ),
            ),
        )
    )
    vm = build_review_page_vm(state)
    assert {item.document_name for item in vm.items} == {"review-only.pdf"}
    assert all(item.document_name != "ok.pdf" for item in vm.items)
    assert vm.result_count == 1
    assert MSG_RESULTS_SEPARATED in vm.separation_notes


def test_review_page_does_not_display_errors_as_review_items() -> None:
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="failed",
            review_items=(
                ProcessingReviewItem(
                    document_name="check.pdf",
                    reason="Unklar",
                ),
            ),
            errors=("IO-Fehler", "Ziel fehlt"),
        )
    )
    vm = build_review_page_vm(state)
    assert len(vm.items) == 1
    assert vm.items[0].document_name == "check.pdf"
    assert vm.error_count == 2
    assert all("IO-Fehler" not in item.reason for item in vm.items)
    assert all("Ziel fehlt" not in item.reason for item in vm.items)
    assert MSG_ERRORS_SEPARATED in vm.separation_notes


def test_review_item_shows_reason_evidence_next_action_when_provided() -> None:
    item = ProcessingReviewItem(
        document_name="doc.pdf",
        reason="Mehrdeutige Zuordnung",
        status_label="manuell",
        evidence_summary="Zwei Konfigurationen passen teilweise",
        next_action_hint="Regel im Profil prüfen",
        document_id="id-9",
    )
    vm = build_review_item_view_model(item, source_run_id="sandbox-1")
    assert vm.reason == "Mehrdeutige Zuordnung"
    assert vm.evidence_summary == "Zwei Konfigurationen passen teilweise"
    assert vm.next_action_hint == "Regel im Profil prüfen"
    assert vm.suggested_status == "manuell"
    assert vm.source_run_id == "sandbox-1"
    assert vm.document_id == "id-9"


def test_review_item_does_not_infer_from_filename() -> None:
    item = ProcessingReviewItem(
        document_name="AMEX_Privat_SOMAA_Rechnung.pdf",
        reason="Zuordnung unklar",
        status_label="unklar",
    )
    vm = build_review_item_view_model(item)
    # Label may echo the provided document_name, but no inferred private class fields.
    assert vm.reason == "Zuordnung unklar"
    assert vm.suggested_status == "unklar"
    assert "payment" not in vm.reason.lower()
    assert "account" not in vm.suggested_status.lower()
    assert "business" not in (vm.evidence_summary or "").lower()
    assert vm.evidence_summary == "Kein Nachweiszusammenfassung bereitgestellt."
    # Must not invent vendor/payment classification from the filename tokens.
    blob = f"{vm.reason} {vm.suggested_status} {vm.evidence_summary} {vm.next_action_hint}"
    assert "Privatkonto" not in blob
    assert "Geschäftskonto" not in blob
    assert "American Express" not in blob


def test_review_page_contains_no_fake_invoice_rows() -> None:
    vm = build_review_page_vm(UiV2State())
    assert vm.items == ()
    assert vm.detail_items == ()
    assert vm.review_count == 0
    blob = " ".join(
        filter(
            None,
            (
                vm.empty_title,
                vm.empty_detail,
                *(item.document_name for item in vm.items),
                *(detail.document_label for detail in vm.detail_items),
            ),
        )
    ).lower()
    for marker in ("unklar-1", "preview", "demo-invoice", "fake-invoice"):
        assert marker not in blob


def test_review_page_contains_no_private_defaults() -> None:
    src_workflow = REVIEW_WORKFLOW.read_text(encoding="utf-8")
    src_page = REVIEW_PAGE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in src_workflow, marker
        assert marker not in src_page, marker
    vm = build_review_page_vm(UiV2State())
    blob = " ".join(
        filter(
            None,
            (vm.empty_title, vm.empty_detail, *vm.honest_copy, *vm.action_labels),
        )
    )
    for marker in ("Hadi", "SOMAA", "Bismarck", "AMEX", "voba"):
        assert marker not in blob


def test_review_actions_are_disabled_readiness_only() -> None:
    queue = build_review_queue_view_model(
        ProcessingRunState(
            status="completed",
            review_items=(
                ProcessingReviewItem(document_name="a.pdf", reason="Unklar"),
            ),
        )
    )
    assert queue.actions
    assert all(not action.enabled for action in queue.actions)
    assert all(action.persists is False for action in queue.actions)
    assert all(action.mutates_files is False for action in queue.actions)
    assert all(action.opens_pdf is False for action in queue.actions)
    labels = {action.label for action in queue.actions}
    assert ACTION_MARK_REVIEWED in labels
    assert ACTION_SAVE_LATER in labels
    assert ACTION_CHECK_EVIDENCE in labels
    assert any(MSG_ACTION_NOT_CONNECTED in action.readiness_label for action in queue.actions)

    page_vm = build_review_page_vm(
        UiV2State(
            processing_run_state=ProcessingRunState(
                review_items=(
                    ProcessingReviewItem(document_name="a.pdf", reason="Unklar"),
                ),
            )
        )
    )
    assert page_vm.actions_disabled is True
    assert ACTION_MARK_REVIEWED in page_vm.action_labels


def test_workspace_review_count_remains_separated() -> None:
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="completed",
            results=(
                ProcessingResultSummary(
                    document_name="ok.pdf",
                    document_type="beleg",
                    classification_status="ok",
                    status_label="OK",
                ),
            ),
            review_items=(
                ProcessingReviewItem(document_name="r1.pdf", reason="A"),
                ProcessingReviewItem(document_name="r2.pdf", reason="B"),
            ),
            errors=("E1",),
        )
    )
    readiness = build_workspace_readiness_display_vm(state)
    assert readiness.result_count == 1
    assert readiness.review_count == 2
    assert readiness.error_count == 1
    assert readiness.has_fake_counters is False
    assert MSG_REVIEW_DETAILS_HINT == "Details unter Zur Prüfung."


def test_empty_queue_with_errors_still_has_no_fake_review_items() -> None:
    queue = build_review_queue_view_model(
        ProcessingRunState(status="failed", errors=("X",), review_items=())
    )
    assert queue.empty is True
    assert queue.review_count == 0
    assert queue.items == ()
    assert queue.error_count == 1
    assert MSG_ERRORS_SEPARATED in queue.separation_notes


def test_review_workflow_has_no_processing_core_import() -> None:
    for path in (REVIEW_WORKFLOW, REVIEW_PAGE):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        for forbidden in PROCESSING_CORE:
            assert forbidden not in imported
            assert forbidden not in src
