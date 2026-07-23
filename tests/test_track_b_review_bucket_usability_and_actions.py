"""Track-B Review-bucket usability and preview-only actions (Prompt 15/34).

No GUI window, no PDF processing, no run_once, no real invoice folders,
no final file writes. Verifies list/detail/actions against UI-v2 state only.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_preview_state import (
    ACTION_EXCLUDE_EXPORT_PREVIEW,
    ACTION_KEEP_IN_REVIEW,
    ACTION_MARK_CHECKED_PREVIEW,
    ACTION_RESET_SELECTION,
    MSG_BADGE_NO_FINAL_WRITE,
    MSG_BADGE_PREVIEW,
    MSG_CATEGORY_REVIEW,
    MSG_EMPTY_OUTPUT_EXPLAIN,
    MSG_NO_PRODUCTION_READY,
    MSG_NO_SAAS_READY,
    exclude_from_export_preview,
    keep_in_review,
    mark_checked_preview,
    preview_action_mutates_files,
    preview_actions_call_run_once,
    preview_actions_claim_production_ready,
    preview_actions_claim_saas_ready,
    preview_actions_process_pdfs,
    preview_actions_touch_real_invoice_folders,
    reset_preview_selection,
    select_review_item,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
REVIEW_PREVIEW = ROOT / "invoice_tool" / "ui_v2" / "review_preview_state.py"
REVIEW_WORKFLOW = ROOT / "invoice_tool" / "ui_v2" / "review_workflow.py"

PROCESSING_CORE = (
    "invoice_tool.processing",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
    "invoice_tool.run",
    "invoice_tool.core_dry_run",
)

FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)

PRIVATE_MARKERS = ("Hadi", "SOMAA", "Bismarck", "AMEX", "voba")


def _five_review_run() -> ProcessingRunState:
    names = (
        "320262919974.pdf",
        "420260091336.pdf",
        "FA011466.pdf",
        "Rechnung RE-202605-14594.pdf",
        "Rechnung-2026156019-102201.pdf",
    )
    review_items = tuple(
        ProcessingReviewItem(
            document_name=name,
            reason=f"Zuordnung unklar für {name}",
            status_label="unklar",
            document_id=f"doc-{index}",
            evidence_summary="Sandbox-Dry-Run: Prüfung erforderlich",
            next_action_hint="Manuell prüfen (Preview)",
        )
        for index, name in enumerate(names, start=1)
    )
    planned = tuple(
        ProcessingPlannedDestination(
            document_name=name,
            planned_path=f"preview/ziel/{name}",
            destination_label="Geplantes Ziel",
            reason="Vorschau",
            applied=False,
            preview_only=True,
        )
        for name in names
    )
    return ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="sandbox-review-5",
        review_items=review_items,
        planned_destinations=planned,
        planned_destination_count=5,
        safety_proof_summary=(
            "Originale unverändert · Produktiv gesperrt · Export Vorschau"
        ),
        outcome_kind="all_review",
    )


def _state_with_five() -> UiV2State:
    return UiV2State(processing_run_state=_five_review_run())


def test_review_bucket_renders_visible_list_for_five_items() -> None:
    vm = build_review_page_vm(_state_with_five())
    assert vm.empty is False
    assert vm.review_count == 5
    assert len(vm.list_items) == 5
    assert len(vm.items) == 5


def test_each_review_item_exposes_source_filename() -> None:
    vm = build_review_page_vm(_state_with_five())
    names = {row.source_filename for row in vm.list_items}
    assert "320262919974.pdf" in names
    assert "FA011466.pdf" in names
    assert len(names) == 5


def test_each_review_item_exposes_review_reason_and_status() -> None:
    vm = build_review_page_vm(_state_with_five())
    for row in vm.list_items:
        assert row.category == MSG_CATEGORY_REVIEW
        assert row.reason
        assert "unklar" in row.reason.lower() or "Zuordnung" in row.reason
        assert row.confidence_or_status


def test_each_review_item_exposes_planned_action_or_destination() -> None:
    vm = build_review_page_vm(_state_with_five())
    for row in vm.list_items:
        assert row.planned_destination or row.planned_action
        if row.planned_destination:
            assert "preview/ziel/" in row.planned_destination


def test_each_review_item_exposes_preview_only_and_no_final_write_marker() -> None:
    vm = build_review_page_vm(_state_with_five())
    for row in vm.list_items:
        assert row.preview_only_badge == MSG_BADGE_PREVIEW
        assert row.no_final_write_badge == MSG_BADGE_NO_FINAL_WRITE
        assert "Produktiv" in row.productive_blocked_badge


def test_selecting_item_renders_detail_view() -> None:
    state = _state_with_five()
    vm = build_review_page_vm(state)
    assert vm.selected_detail is not None
    target = vm.list_items[2].item_key
    select_review_item(state, target)
    vm2 = build_review_page_vm(state)
    assert vm2.selected_item_key == target
    assert vm2.selected_detail is not None
    assert vm2.selected_detail.item_key == target


def test_detail_view_includes_source_filename() -> None:
    vm = build_review_page_vm(_state_with_five())
    assert vm.selected_detail is not None
    assert vm.selected_detail.source_filename.endswith(".pdf")


def test_detail_view_includes_review_reason() -> None:
    vm = build_review_page_vm(_state_with_five())
    assert vm.selected_detail is not None
    assert vm.selected_detail.review_reason


def test_detail_view_includes_planned_target_or_action() -> None:
    vm = build_review_page_vm(_state_with_five())
    detail = vm.selected_detail
    assert detail is not None
    assert detail.planned_target or detail.planned_action


def test_detail_view_includes_safety_proof_status() -> None:
    vm = build_review_page_vm(_state_with_five())
    detail = vm.selected_detail
    assert detail is not None
    blob = " ".join(
        (
            detail.safety_status,
            detail.no_productive_processing_status,
            detail.preview_only_banner,
            detail.originals_unchanged,
        )
    )
    assert "Produktiv" in blob
    assert "Originale" in blob or "unverändert" in blob.lower()
    assert "Vorschau" in blob or "Preview" in blob


def test_mark_checked_preview_only_mutates_local_ui_state() -> None:
    state = _state_with_five()
    build_review_page_vm(state)
    key = state.review_preview_ui.selected_item_key
    assert key
    before_run = state.processing_run_state
    mark_checked_preview(state, key)
    assert key in state.review_preview_ui.checked_preview_keys
    assert state.processing_run_state is before_run
    vm = build_review_page_vm(state)
    assert vm.mutates_files is False
    assert vm.writes_final_files is False
    selected = next(r for r in vm.list_items if r.item_key == key)
    assert selected.checked_preview is True
    # Item remains in Review bucket list.
    assert len(vm.list_items) == 5


def test_keep_in_review_keeps_item_in_review_bucket() -> None:
    state = _state_with_five()
    build_review_page_vm(state)
    key = state.review_preview_ui.selected_item_key
    mark_checked_preview(state, key)
    keep_in_review(state, key)
    assert key not in state.review_preview_ui.checked_preview_keys
    vm = build_review_page_vm(state)
    assert len(vm.list_items) == 5
    selected = next(r for r in vm.list_items if r.item_key == key)
    assert selected.checked_preview is False
    assert selected.category == MSG_CATEGORY_REVIEW


def test_exclude_from_export_preview_only_changes_inclusion_state() -> None:
    state = _state_with_five()
    build_review_page_vm(state)
    key = state.review_preview_ui.selected_item_key
    exclude_from_export_preview(state, key)
    assert key in state.review_preview_ui.excluded_from_export_preview_keys
    vm = build_review_page_vm(state)
    selected = next(r for r in vm.list_items if r.item_key == key)
    assert selected.excluded_from_export_preview is True
    assert len(vm.list_items) == 5
    assert vm.writes_final_files is False
    assert "Export" in (vm.selected_detail.export_preview_status if vm.selected_detail else "")


def test_reset_selection_returns_to_initial_preview_state() -> None:
    state = _state_with_five()
    build_review_page_vm(state)
    key = state.review_preview_ui.selected_item_key
    mark_checked_preview(state, key)
    exclude_from_export_preview(state, key)
    reset_preview_selection(state)
    assert state.review_preview_ui.selected_item_key is None
    assert not state.review_preview_ui.checked_preview_keys
    assert not state.review_preview_ui.excluded_from_export_preview_keys
    vm = build_review_page_vm(state)
    # Auto-select restores first item for usability; checked/excluded stay clear.
    assert all(not row.checked_preview for row in vm.list_items)
    assert all(not row.excluded_from_export_preview for row in vm.list_items)


def test_actions_do_not_call_run_once() -> None:
    assert preview_actions_call_run_once() is False
    for path in (REVIEW_PREVIEW, REVIEW_PAGE):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        call_names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        attr_calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert "run_once" not in call_names
        assert "run_once" not in attr_calls
        assert "from invoice_tool.run" not in src
        assert "import invoice_tool.run" not in src
    vm = build_review_page_vm(_state_with_five())
    assert vm.calls_run_once is False


def test_actions_do_not_process_pdfs() -> None:
    assert preview_actions_process_pdfs() is False
    for path in (REVIEW_PREVIEW, REVIEW_PAGE):
        src = path.read_text(encoding="utf-8")
        for token in ("PyPDF", "pdf2image", "pytesseract", "Path.write"):
            assert token not in src


def test_actions_do_not_write_files() -> None:
    assert preview_action_mutates_files() is False
    state = _state_with_five()
    build_review_page_vm(state)
    mark_checked_preview(state)
    exclude_from_export_preview(state)
    reset_preview_selection(state)
    for path in (REVIEW_PREVIEW, REVIEW_PAGE, REVIEW_WORKFLOW):
        src = path.read_text(encoding="utf-8")
        for token in ("unlink(", "rename(", "shutil.", "mkdir(", "write_bytes("):
            assert token not in src, f"{path.name}: {token}"


def test_actions_do_not_mutate_input() -> None:
    state = _state_with_five()
    before = state.processing_run_state.review_items
    build_review_page_vm(state)
    mark_checked_preview(state)
    keep_in_review(state)
    exclude_from_export_preview(state)
    reset_preview_selection(state)
    assert state.processing_run_state.review_items is before
    vm = build_review_page_vm(state)
    assert vm.mutates_input is False


def test_actions_do_not_touch_real_invoice_folders() -> None:
    assert preview_actions_touch_real_invoice_folders() is False
    for path in (REVIEW_PREVIEW, REVIEW_PAGE):
        src = path.read_text(encoding="utf-8")
        for folder in FORBIDDEN_FOLDERS:
            assert folder not in src
    vm = build_review_page_vm(_state_with_five())
    assert vm.touches_real_invoice_folders is False


def test_actions_do_not_claim_saas_ready() -> None:
    assert preview_actions_claim_saas_ready() is False
    vm = build_review_page_vm(_state_with_five())
    assert vm.claims_saas_ready is False
    page_blob = " ".join(
        (
            vm.preview_only_banner,
            vm.empty_output_explanation,
            *(vm.honest_copy or ()),
            *vm.preview_action_labels,
        )
    ).lower()
    assert "saas ready" not in page_blob
    assert "saas-ready" not in page_blob
    assert MSG_NO_SAAS_READY == "nicht SaaS-ready"


def test_actions_do_not_claim_production_ready() -> None:
    assert preview_actions_claim_production_ready() is False
    vm = build_review_page_vm(_state_with_five())
    assert vm.claims_production_ready is False
    page_blob = " ".join(
        (
            vm.preview_only_banner,
            vm.empty_output_explanation,
            *(vm.honest_copy or ()),
            *vm.preview_action_labels,
        )
    ).lower()
    assert "production-ready" not in page_blob
    assert "production ready" not in page_blob
    assert MSG_NO_PRODUCTION_READY == "nicht production-ready"


def test_empty_output_explanation_remains_visible() -> None:
    vm = build_review_page_vm(_state_with_five())
    assert MSG_EMPTY_OUTPUT_EXPLAIN in vm.empty_output_explanation
    assert "leer" in vm.empty_output_explanation.lower()
    assert "Keine finalen Dateien geschrieben" in vm.empty_output_explanation
    assert vm.selected_detail is not None
    assert MSG_EMPTY_OUTPUT_EXPLAIN in vm.selected_detail.empty_output_explanation


def test_preview_action_labels_are_present() -> None:
    vm = build_review_page_vm(_state_with_five())
    labels = set(vm.preview_action_labels)
    assert ACTION_MARK_CHECKED_PREVIEW in labels
    assert ACTION_KEEP_IN_REVIEW in labels
    assert ACTION_EXCLUDE_EXPORT_PREVIEW in labels
    assert ACTION_RESET_SELECTION in labels
    # Legacy final/readiness actions stay disabled.
    assert vm.actions_disabled is True
    assert vm.productive_actions_exposed is False
    assert vm.final_actions_blocked is True


def test_no_private_hardcoded_defaults_in_review_usability_modules() -> None:
    for path in (REVIEW_PREVIEW, REVIEW_PAGE):
        src = path.read_text(encoding="utf-8")
        for marker in PRIVATE_MARKERS:
            assert marker not in src, f"{path.name}: {marker}"


def test_review_modules_have_no_processing_core_import() -> None:
    for path in (REVIEW_PREVIEW, REVIEW_PAGE, REVIEW_WORKFLOW):
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


def test_track_a_protection_module_still_importable() -> None:
    """Track A protection test still passes as a separate pytest module."""

    import tests.test_track_a_internal_app_protection as track_a

    assert hasattr(track_a, "TRACK_A_PROTECTED")
    assert (ROOT / "app_main.py").exists()
    assert (ROOT / "app_ui_v2.py").exists()
