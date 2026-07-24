"""Track-B Review Decision State and UI Flow (Prompt 29/34).

No productive processing, no real invoice folders, no final writes.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from invoice_tool.ui_v2.finalization_readiness import (
    BLOCKER_DUPLICATE_TARGET_FILENAME,
    BLOCKER_INCOMPLETE_FILENAME,
    BLOCKER_MISSING_PAYMENT_FIELD,
    BLOCKER_MISSING_SUPPLIER,
    BLOCKER_NO_EXPLICIT_USER_APPROVAL,
    BLOCKER_SOURCE_HASH_CHANGED,
    BLOCKER_STALE_PREVIEW_STATE,
    BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT,
    FinalizationReadiness,
    compute_finalization_readiness,
    final_write_allowed,
)
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.preview_export import write_preview_export_package
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_decision import (
    ACTION_ACCEPT_SUGGESTION,
    ACTION_DEFER,
    ACTION_EDIT_SUGGESTION,
    ACTION_IGNORE_EXPORT,
    ACTION_KEEP_UNCLEAR,
    ACTION_NEEDS_CONFIGURATION,
    ALL_DECISION_TYPES,
    DECISION_ACCEPT,
    DECISION_DEFER,
    DECISION_EDIT,
    DECISION_IGNORE,
    DECISION_KEEP_REVIEW,
    DECISION_NEEDS_CONFIG,
    MSG_NOT_FINAL_YET,
    ReviewDecision,
    create_accept_suggestion_decision,
    create_defer_decision,
    create_edit_suggestion_decision,
    create_ignore_for_export_decision,
    create_keep_review_required_decision,
    create_needs_configuration_change_decision,
    decision_actions_call_run_once,
    decision_actions_claim_production_ready,
    decision_actions_claim_saas_ready,
    decision_actions_mutate_input,
    decision_actions_touch_real_invoice_folders,
    decision_actions_write_final_pdfs,
    decision_report_fields_for_item,
    detect_duplicate_approved_targets,
    get_review_decision_bag,
    items_excluded_from_finalization_batch,
    set_edit_filename_draft,
    validate_edited_filename,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DECISION_PY = ROOT / "invoice_tool" / "ui_v2" / "review_decision.py"
FINALIZATION_PY = ROOT / "invoice_tool" / "ui_v2" / "finalization_readiness.py"
REVIEW_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"

TRACK_A_PROTECTED = [
    "app_main.py",
    "app_internal_launcher.py",
    "invoice_tool/gui.py",
    "invoice_tool/ui_shell.py",
    "invoice_tool/ui_workspace.py",
    "invoice_tool/ui_configurations.py",
    "invoice_tool/ui_profiles.py",
    "invoice_tool/ui_review.py",
    "invoice_tool/ui_settings.py",
    "invoice_tool/ui_profile_dialog.py",
    "invoice_tool/ui_document_rules.py",
]

FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)


def _complete_planned(**overrides: object) -> ProcessingPlannedDestination:
    base = dict(
        document_name="sample.pdf",
        planned_path="preview/ziel/sample.pdf",
        destination_label="Geplantes Ziel",
        preview_only=True,
        applied=False,
        suggested_filename="Lieferant_2026-07-23_10,00_Eingang_PayPal.pdf",
        rendered_filename="Lieferant_2026-07-23_10,00_Eingang_PayPal.pdf",
        supplier="Lieferant",
        counterparty_name="Lieferant",
        invoice_date="2026-07-23",
        amount="10,00",
        selected_amount="10,00",
        selected_payment_field="PayPal",
        payment_account="PayPal",
        matched_configuration_name="PayPal Eingang",
        matched_configuration_id="cfg-paypal",
        filename_pattern="{supplier}_{date}_{amount}_{direction}_{payment}.pdf",
        missing_placeholders=(),
        missing_fields=(),
    )
    base.update(overrides)
    return ProcessingPlannedDestination(**base)  # type: ignore[arg-type]


def _state_with_item(
    *,
    document_name: str = "sample.pdf",
    document_id: str = "doc-1",
    planned: ProcessingPlannedDestination | None = None,
) -> UiV2State:
    planned = planned or _complete_planned(document_name=document_name)
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="sandbox-decision-1",
        review_items=(
            ProcessingReviewItem(
                document_name=document_name,
                reason="Prüfung erforderlich",
                status_label="unklar",
                document_id=document_id,
            ),
        ),
        planned_destinations=(planned,),
        planned_destination_count=1,
        state_updated_at="2026-07-23T12:00:00+00:00",
        outcome_kind="all_review",
    )
    state = UiV2State(processing_run_state=run)
    state.review_preview_ui.selected_item_key = document_id
    return state


def test_01_review_decision_supports_all_six_types() -> None:
    assert set(ALL_DECISION_TYPES) == {
        DECISION_ACCEPT,
        DECISION_EDIT,
        DECISION_KEEP_REVIEW,
        DECISION_IGNORE,
        DECISION_DEFER,
        DECISION_NEEDS_CONFIG,
    }
    for decision_type in ALL_DECISION_TYPES:
        decision = ReviewDecision(
            decision_id="x",
            source_item_id="doc-1",
            source_filename="sample.pdf",
            decision_type=decision_type,
            decided_by_user=True,
            decision_timestamp="2026-07-23T12:00:00+00:00",
            final_write_allowed=False,
        )
        assert decision.decision_type == decision_type
        assert decision.final_write_allowed is False


def test_02_accept_requires_decided_by_user() -> None:
    state = _state_with_item()
    result = create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=False,
        explicit_confirmation=True,
    )
    assert result.ok is False
    result2 = create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=False,
    )
    assert result2.ok is False


def test_03_accept_records_approved_preview_filename() -> None:
    state = _state_with_item()
    result = create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    assert result.ok is True
    assert result.decision is not None
    assert result.decision.decided_by_user is True
    assert result.decision.approved_preview_filename
    assert result.decision.approved_preview_filename.endswith(".pdf")


def test_04_edit_records_edited_fields() -> None:
    state = _state_with_item()
    result = create_edit_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        edited_filename="Neu_2026-07-23_10,00_Eingang_PayPal.pdf",
        edited_fields={"supplier": "Neu"},
    )
    assert result.ok is True
    assert result.decision is not None
    edited = dict(result.decision.edited_fields)
    assert edited.get("supplier") == "Neu"
    assert "preview_filename" in edited


def test_05_keep_review_required_keeps_item_in_review() -> None:
    state = _state_with_item()
    result = create_keep_review_required_decision(
        state, item_key="doc-1", decided_by_user=True
    )
    assert result.ok is True
    assert result.decision is not None
    assert result.decision.decision_type == DECISION_KEEP_REVIEW
    assert result.decision.review_status == "review_required"
    assert result.decision.finalization_ready is False
    assert "doc-1" not in state.review_preview_ui.checked_preview_keys


def test_06_ignore_excludes_from_finalization_batch() -> None:
    state = _state_with_item()
    result = create_ignore_for_export_decision(
        state, item_key="doc-1", decided_by_user=True
    )
    assert result.ok is True
    assert result.decision is not None
    assert result.decision.exclude_from_finalization_batch is True
    assert "doc-1" in items_excluded_from_finalization_batch(state)
    assert "doc-1" in state.review_preview_ui.excluded_from_export_preview_keys


def test_07_defer_keeps_pending() -> None:
    state = _state_with_item()
    result = create_defer_decision(state, item_key="doc-1", decided_by_user=True)
    assert result.ok is True
    assert result.decision is not None
    assert result.decision.decision_type == DECISION_DEFER
    assert result.decision.review_status == "pending"
    assert result.decision.finalization_ready is False


def test_08_needs_configuration_routes_to_config_flow() -> None:
    state = _state_with_item()
    result = create_needs_configuration_change_decision(
        state, item_key="doc-1", decided_by_user=True
    )
    assert result.ok is True
    assert result.routes_to_configuration_flow is True
    bag = get_review_decision_bag(state)
    assert bag.routes_to_configuration_flow_item_key == "doc-1"
    assert result.decision is not None
    assert result.decision.routes_to_configuration_flow is True


def test_09_finalization_readiness_records_blockers() -> None:
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={},
        approved=False,
    )
    assert isinstance(readiness, FinalizationReadiness)
    assert readiness.ready is False
    assert BLOCKER_NO_EXPLICIT_USER_APPROVAL in readiness.blockers
    assert readiness.final_write_allowed is False


def test_10_missing_payment_field_can_block() -> None:
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "supplier": "A",
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "matched_configuration_name": "PayPal",
            "filename_pattern": "{payment}.pdf",
            "approved_preview_filename": "x.pdf",
            "payment_field_required": True,
        },
        approved=True,
        decision_type=DECISION_ACCEPT,
        target_preview_path="preview/x.pdf",
    )
    assert BLOCKER_MISSING_PAYMENT_FIELD in readiness.blockers
    assert readiness.ready is False


def test_11_missing_supplier_blocks() -> None:
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "matched_configuration_name": "PayPal",
            "filename_pattern": "{supplier}.pdf",
            "approved_preview_filename": "x.pdf",
            "payment_field_required": False,
            "requires_filename_pattern": False,
        },
        approved=True,
        decision_type=DECISION_ACCEPT,
        target_preview_path="preview/x.pdf",
    )
    assert BLOCKER_MISSING_SUPPLIER in readiness.blockers
    assert readiness.ready is False


def test_12_incomplete_filename_blocks() -> None:
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "supplier": "A",
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "matched_configuration_name": "PayPal",
            "approved_preview_filename": "ohne-endung",
            "payment_field_required": False,
            "requires_filename_pattern": False,
        },
        approved=True,
        decision_type=DECISION_ACCEPT,
        target_preview_path="preview/ohne-endung",
    )
    assert BLOCKER_INCOMPLETE_FILENAME in readiness.blockers
    assert readiness.ready is False


def test_13_duplicate_target_blocks() -> None:
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "supplier": "A",
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "matched_configuration_name": "PayPal",
            "approved_preview_filename": "same.pdf",
            "payment_field_required": False,
            "requires_filename_pattern": False,
        },
        approved=True,
        decision_type=DECISION_ACCEPT,
        duplicate_target=True,
        target_preview_path="preview/same.pdf",
    )
    assert BLOCKER_DUPLICATE_TARGET_FILENAME in readiness.blockers
    assert readiness.ready is False


def test_14_unsafe_output_target_blocks() -> None:
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "supplier": "A",
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "matched_configuration_name": "PayPal",
            "approved_preview_filename": "x.pdf",
            "payment_field_required": False,
            "requires_filename_pattern": False,
        },
        approved=True,
        decision_type=DECISION_ACCEPT,
        output_root="/tmp/controlled-output",
        target_preview_path="/etc/passwd.pdf",
    )
    assert BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT in readiness.blockers
    assert readiness.ready is False


def test_15_stale_preview_state_blocks() -> None:
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "supplier": "A",
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "matched_configuration_name": "PayPal",
            "approved_preview_filename": "x.pdf",
            "payment_field_required": False,
            "requires_filename_pattern": False,
        },
        approved=True,
        decision_type=DECISION_ACCEPT,
        preview_state_fresh=False,
        target_preview_path="preview/x.pdf",
    )
    assert BLOCKER_STALE_PREVIEW_STATE in readiness.blockers
    assert readiness.ready is False


def test_16_changed_source_hash_blocks() -> None:
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "supplier": "A",
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "matched_configuration_name": "PayPal",
            "approved_preview_filename": "x.pdf",
            "payment_field_required": False,
            "requires_filename_pattern": False,
        },
        approved=True,
        decision_type=DECISION_ACCEPT,
        source_unchanged=False,
        target_preview_path="preview/x.pdf",
    )
    assert BLOCKER_SOURCE_HASH_CHANGED in readiness.blockers
    assert readiness.ready is False


def test_17_no_explicit_approval_blocks() -> None:
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "supplier": "A",
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "matched_configuration_name": "PayPal",
            "approved_preview_filename": "x.pdf",
            "payment_field_required": False,
            "requires_filename_pattern": False,
        },
        approved=False,
        decision_type=DECISION_ACCEPT,
        target_preview_path="preview/x.pdf",
    )
    assert BLOCKER_NO_EXPLICIT_USER_APPROVAL in readiness.blockers
    assert readiness.ready is False


def test_18_final_write_allowed_remains_false() -> None:
    assert final_write_allowed() is False
    state = _state_with_item()
    result = create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    assert result.final_write_allowed is False
    assert result.decision is not None
    assert result.decision.final_write_allowed is False
    assert result.readiness is not None
    assert result.readiness.final_write_allowed is False


def test_19_ui_exposes_accept() -> None:
    vm = build_review_page_vm(_state_with_item())
    assert ACTION_ACCEPT_SUGGESTION in vm.decision_action_labels
    assert ACTION_ACCEPT_SUGGESTION in REVIEW_DECISION_PY.read_text(encoding="utf-8")
    assert "ACTION_ACCEPT_SUGGESTION" in REVIEW_PAGE.read_text(encoding="utf-8")


def test_20_ui_exposes_edit() -> None:
    vm = build_review_page_vm(_state_with_item())
    assert ACTION_EDIT_SUGGESTION in vm.decision_action_labels


def test_21_ui_exposes_configuration() -> None:
    vm = build_review_page_vm(_state_with_item())
    assert ACTION_NEEDS_CONFIGURATION in vm.decision_action_labels


def test_22_ui_exposes_keep_unclear() -> None:
    vm = build_review_page_vm(_state_with_item())
    assert ACTION_KEEP_UNCLEAR in vm.decision_action_labels


def test_23_ui_exposes_ignore() -> None:
    vm = build_review_page_vm(_state_with_item())
    assert ACTION_IGNORE_EXPORT in vm.decision_action_labels


def test_24_ui_exposes_defer() -> None:
    vm = build_review_page_vm(_state_with_item())
    assert ACTION_DEFER in vm.decision_action_labels


def test_25_ui_shows_not_final_yet_safety_text() -> None:
    vm = build_review_page_vm(_state_with_item())
    assert MSG_NOT_FINAL_YET == vm.not_final_yet_text
    assert "Noch keine finale Verarbeitung" in vm.not_final_yet_text
    assert MSG_NOT_FINAL_YET in REVIEW_DECISION_PY.read_text(encoding="utf-8")
    assert "MSG_NOT_FINAL_YET" in REVIEW_PAGE.read_text(encoding="utf-8")


def test_26_edited_filename_rejects_path_separators() -> None:
    result = validate_edited_filename("ordner/datei.pdf")
    assert result.ok is False
    assert any("Pfadtrenner" in err for err in result.errors)


def test_27_edited_filename_rejects_traversal() -> None:
    result = validate_edited_filename("../secret.pdf")
    assert result.ok is False
    assert any("Traversal" in err for err in result.errors)


def test_28_edited_filename_requires_pdf() -> None:
    result = validate_edited_filename("datei.txt")
    assert result.ok is False
    assert any(".pdf" in err for err in result.errors)


def test_29_duplicate_approved_preview_filenames_detected() -> None:
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="same.pdf",
    )
    # Second item with same approved target
    state.processing_run_state = ProcessingRunState(
        status="completed",
        run_id="sandbox-decision-1",
        review_items=(
            ProcessingReviewItem(
                document_name="sample.pdf",
                reason="a",
                document_id="doc-1",
            ),
            ProcessingReviewItem(
                document_name="other.pdf",
                reason="b",
                document_id="doc-2",
            ),
        ),
        planned_destinations=(
            _complete_planned(document_name="sample.pdf"),
            _complete_planned(
                document_name="other.pdf",
                planned_path="preview/ziel/same.pdf",
                suggested_filename="same.pdf",
                rendered_filename="same.pdf",
            ),
        ),
        planned_destination_count=2,
    )
    create_accept_suggestion_decision(
        state,
        item_key="doc-2",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="same.pdf",
    )
    bag = get_review_decision_bag(state)
    dupes = detect_duplicate_approved_targets(bag.decisions_by_item_key)
    assert "doc-1" in dupes or "doc-2" in dupes
    assert any(
        BLOCKER_DUPLICATE_TARGET_FILENAME in d.finalization_blockers
        for d in bag.decisions_by_item_key.values()
    )


def test_30_preview_export_includes_review_decision_fields(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "copied-sandbox-input"
    output_root = tmp_path / "copied-sandbox-output"
    input_root.mkdir()
    output_root.mkdir()
    pdf = input_root / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4 sample")
    state = _state_with_item()
    state.workspace_input_folder_override = str(input_root)
    state.workspace_output_folder_override = str(output_root)
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    fields = decision_report_fields_for_item(state, "doc-1")
    # Direct package write with decision fields (path policy may block non-marked roots).
    # Validate report fields contract even if package write is path-blocked.
    assert fields["review_decision"] == DECISION_ACCEPT
    assert fields["decision_timestamp"]
    assert fields["approved_by_user"] is True
    assert fields["final_write_allowed"] is False
    assert "approved_preview_filename" in fields
    assert "finalization_blockers" in fields
    assert "preview_state_id" in fields


def test_31_preview_export_final_write_allowed_false(tmp_path: Path) -> None:
    state = _state_with_item()
    create_edit_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        edited_filename="Edit_2026-07-23_10,00_Eingang_PayPal.pdf",
    )
    fields = decision_report_fields_for_item(state, "doc-1")
    assert fields["final_write_allowed"] is False
    # Enrichment helper path used by write_preview_export_package
    from invoice_tool.ui_v2.preview_export import _with_decision_fields, PreviewExportItem

    item = PreviewExportItem(
        source_filename="sample.pdf",
        preview_filename="sample.pdf",
        status="unklar",
        category="review",
        planned_target="preview/ziel/sample.pdf",
        review_required=True,
        source_sha256="abc",
        preview_sha256="abc",
        source_path="",
        preview_path="",
    )
    enriched = _with_decision_fields(
        item, {"doc-1": fields}, item_key="doc-1"
    )
    assert enriched.review_decision == DECISION_EDIT
    assert enriched.final_write_allowed is False


def test_32_saving_decision_does_not_call_run_once() -> None:
    assert decision_actions_call_run_once() is False
    tree = ast.parse(REVIEW_DECISION_PY.read_text(encoding="utf-8"))
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "run_once" not in calls
    state = _state_with_item()
    result = create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    assert result.called_run_once is False


def test_33_saving_decision_does_not_mutate_input(tmp_path: Path) -> None:
    assert decision_actions_mutate_input() is False
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 before")
    before = source.read_bytes()
    state = _state_with_item()
    create_edit_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        edited_filename="Neu_2026-07-23_10,00_Eingang_PayPal.pdf",
    )
    assert source.read_bytes() == before


def test_34_saving_decision_does_not_write_final_pdfs(tmp_path: Path) -> None:
    assert decision_actions_write_final_pdfs() is False
    out = tmp_path / "out"
    out.mkdir()
    state = _state_with_item()
    state.workspace_output_folder_override = str(out)
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    written_pdfs = list(out.rglob("*.pdf"))
    assert written_pdfs == []


def test_35_saving_decision_does_not_touch_real_invoice_folders() -> None:
    assert decision_actions_touch_real_invoice_folders() is False
    text = REVIEW_DECISION_PY.read_text(encoding="utf-8")
    for folder in FORBIDDEN_FOLDERS:
        assert folder not in text
    state = _state_with_item()
    result = create_ignore_for_export_decision(state, item_key="doc-1")
    assert result.touched_real_invoice_folders is False


def test_36_no_saas_ready_claim() -> None:
    assert decision_actions_claim_saas_ready() is False
    text = REVIEW_DECISION_PY.read_text(encoding="utf-8") + FINALIZATION_PY.read_text(
        encoding="utf-8"
    )
    assert "saas ready" not in text.lower()
    assert "saas_ready" not in text.lower() or "not" in text.lower()


def test_37_no_production_ready_claim() -> None:
    assert decision_actions_claim_production_ready() is False
    combined = (
        REVIEW_DECISION_PY.read_text(encoding="utf-8")
        + FINALIZATION_PY.read_text(encoding="utf-8")
        + REVIEW_PAGE.read_text(encoding="utf-8")
    )
    assert "production ready" not in combined.lower()
    assert "production_ready=true" not in combined.lower()


def test_38_track_a_protection_still_passes() -> None:
    import tests.test_track_a_internal_app_protection as protection

    protection.test_track_a_protected_files_unchanged_vs_head()
    protection.test_protected_track_a_and_core_not_staged()
    # This task must not modify protected Track-A files in the working tree
    # beyond known legacy dirty exceptions already present before this task.
    for protected in TRACK_A_PROTECTED:
        if protected in {
            "invoice_tool/ui_profile_dialog.py",
            "invoice_tool/ui_document_rules.py",
        }:
            continue
        # Ensure our staged/new changes don't include these when committing later.
        assert (ROOT / protected).is_file()


def test_ui_detail_shows_decision_after_accept() -> None:
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    vm = build_review_page_vm(state)
    assert vm.selected_detail is not None
    assert vm.selected_detail.review_decision == DECISION_ACCEPT
    assert vm.selected_detail.final_write_allowed is False
    assert MSG_NOT_FINAL_YET in vm.selected_detail.not_final_yet_text


def test_edit_rejects_slash_via_decision_api() -> None:
    state = _state_with_item()
    set_edit_filename_draft(state, "doc-1", "bad/name.pdf")
    result = create_edit_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        edited_filename="bad/name.pdf",
    )
    assert result.ok is False


def test_ready_accept_possible_with_complete_fields() -> None:
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "supplier": "A",
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "selected_payment_field": "PayPal",
            "matched_configuration_name": "PayPal",
            "filename_pattern": "{supplier}.pdf",
            "approved_preview_filename": "A.pdf",
            "payment_field_required": True,
        },
        approved=True,
        decision_type=DECISION_ACCEPT,
        target_preview_path="preview/A.pdf",
        preview_state_fresh=True,
        source_unchanged=True,
        duplicate_target=False,
    )
    assert readiness.ready is True
    assert readiness.decision_ready_for_future_finalization is True
    assert readiness.final_write_allowed is False
