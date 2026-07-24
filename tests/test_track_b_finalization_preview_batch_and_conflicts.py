"""Track-B Finalization Preview Batch & Conflicts (Prompt 30/34).

No productive processing, no real invoice folders, no final writes.
"""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

import pytest

from invoice_tool.ui_v2.finalization_preview_batch import (
    CONFLICT_CHANGED_SOURCE_HASH,
    CONFLICT_DUPLICATE_TARGET_FILENAME,
    CONFLICT_DUPLICATE_TARGET_PATH,
    CONFLICT_INCOMPLETE_FILENAME,
    CONFLICT_MISSING_APPROVAL,
    CONFLICT_MISSING_REQUIRED_FIELD,
    CONFLICT_STALE_PREVIEW_STATE,
    CONFLICT_UNRESOLVED_CONFIGURATION,
    CONFLICT_UNSAFE_TARGET_PATH,
    MSG_BATCH_BLOCKED,
    MSG_BATCH_NO_FINAL_WRITE,
    MSG_BATCH_READY,
    MSG_BATCH_TITLE,
    STATUS_BLOCKED,
    STATUS_DEFERRED,
    STATUS_IGNORED,
    STATUS_READY,
    STATUS_STILL_REVIEW,
    batch_builder_calls_run_once,
    batch_builder_claims_production_ready,
    batch_builder_claims_saas_ready,
    batch_builder_mutates_input,
    batch_builder_touches_real_invoice_folders,
    batch_builder_writes_final_pdfs,
    batch_report_fields,
    batch_summary_lines,
    build_finalization_preview_batch,
    item_batch_export_fields,
)
from invoice_tool.ui_v2.finalization_readiness import (
    BLOCKER_DUPLICATE_TARGET_FILENAME,
    BLOCKER_INCOMPLETE_FILENAME,
    BLOCKER_MISSING_OR_UNCLEAR_CONFIGURATION,
    BLOCKER_MISSING_SUPPLIER,
    BLOCKER_NO_EXPLICIT_USER_APPROVAL,
    BLOCKER_SOURCE_HASH_CHANGED,
    BLOCKER_STALE_PREVIEW_STATE,
    BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT,
    compute_finalization_readiness,
)
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.preview_export import (
    PreviewExportItem,
    _manifest_payload,
    _with_decision_fields,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_decision import (
    DECISION_ACCEPT,
    DECISION_DEFER,
    DECISION_EDIT,
    DECISION_IGNORE,
    DECISION_KEEP_REVIEW,
    ReviewDecision,
    apply_review_decision_to_item,
    create_accept_suggestion_decision,
    create_defer_decision,
    create_ignore_for_export_decision,
    create_keep_review_required_decision,
    decision_report_fields_for_item,
    get_review_decision_bag,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
BATCH_PY = ROOT / "invoice_tool" / "ui_v2" / "finalization_preview_batch.py"
REVIEW_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
PREVIEW_EXPORT_PY = ROOT / "invoice_tool" / "ui_v2" / "preview_export.py"

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
        run_id="sandbox-batch-1",
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


def _state_with_two_items() -> UiV2State:
    run = ProcessingRunState(
        status="completed",
        run_id="sandbox-batch-2",
        review_items=(
            ProcessingReviewItem(
                document_name="sample.pdf", reason="a", document_id="doc-1"
            ),
            ProcessingReviewItem(
                document_name="other.pdf", reason="b", document_id="doc-2"
            ),
        ),
        planned_destinations=(
            _complete_planned(document_name="sample.pdf"),
            _complete_planned(
                document_name="other.pdf",
                planned_path="preview/ziel/other.pdf",
                suggested_filename="Other_2026-07-23_10,00_Eingang_PayPal.pdf",
                rendered_filename="Other_2026-07-23_10,00_Eingang_PayPal.pdf",
            ),
        ),
        planned_destination_count=2,
        state_updated_at="2026-07-23T12:00:00+00:00",
    )
    return UiV2State(processing_run_state=run)


def test_01_batch_model_final_write_allowed_false() -> None:
    state = _state_with_item()
    batch = build_finalization_preview_batch(state)
    assert batch.final_write_allowed is False
    assert all(item.final_write_allowed is False for item in batch.items)


def test_02_batch_includes_total_items() -> None:
    state = _state_with_item()
    batch = build_finalization_preview_batch(state)
    assert batch.total_items == 1


def test_03_batch_counts_ready_items() -> None:
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    assert batch.ready_count >= 1
    assert any(i.finalization_status == STATUS_READY for i in batch.items)


def test_04_batch_counts_blocked_items() -> None:
    planned = _complete_planned(supplier="", counterparty_name="")
    state = _state_with_item(planned=planned)
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    assert batch.blocked_count >= 1
    assert any(i.finalization_status == STATUS_BLOCKED for i in batch.items)


def test_05_batch_counts_ignored_items() -> None:
    state = _state_with_item()
    create_ignore_for_export_decision(state, item_key="doc-1", decided_by_user=True)
    batch = build_finalization_preview_batch(state)
    assert batch.ignored_count == 1


def test_06_batch_counts_deferred_items() -> None:
    state = _state_with_item()
    create_defer_decision(state, item_key="doc-1", decided_by_user=True)
    batch = build_finalization_preview_batch(state)
    assert batch.deferred_count == 1


def test_07_batch_counts_still_review_required_items() -> None:
    state = _state_with_item()
    create_keep_review_required_decision(
        state, item_key="doc-1", decided_by_user=True
    )
    batch = build_finalization_preview_batch(state)
    assert batch.still_review_required_count == 1


def test_08_accepted_clean_item_ready_for_future_finalization() -> None:
    state = _state_with_item()
    result = create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    assert result.ok is True
    batch = build_finalization_preview_batch(state)
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_READY
    assert item.final_write_allowed is False


def test_09_item_without_explicit_approval_blocked() -> None:
    state = _state_with_item()
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "supplier": "Lieferant",
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "selected_payment_field": "PayPal",
            "matched_configuration_name": "PayPal",
            "filename_pattern": "{supplier}.pdf",
            "approved_preview_filename": "Lieferant.pdf",
        },
        approved=False,
        decision_type=DECISION_ACCEPT,
        target_preview_path="preview/Lieferant.pdf",
    )
    decision = ReviewDecision(
        decision_id="rd-test",
        source_item_id="doc-1",
        source_filename="sample.pdf",
        decision_type=DECISION_ACCEPT,
        decided_by_user=False,
        decision_timestamp="2026-07-23T12:00:00+00:00",
        approved_preview_filename="Lieferant.pdf",
        approved_target_preview_path="preview/Lieferant.pdf",
        finalization_ready=False,
        finalization_blockers=(BLOCKER_NO_EXPLICIT_USER_APPROVAL,),
        final_write_allowed=False,
    )
    apply_review_decision_to_item(state, decision, readiness)
    batch = build_finalization_preview_batch(state)
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_BLOCKED
    assert BLOCKER_NO_EXPLICIT_USER_APPROVAL in item.blockers
    assert any(c.conflict_type == CONFLICT_MISSING_APPROVAL for c in batch.conflicts)


def test_10_missing_required_field_blocks_item() -> None:
    planned = _complete_planned(supplier="", counterparty_name="")
    state = _state_with_item(planned=planned)
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_BLOCKED
    assert BLOCKER_MISSING_SUPPLIER in item.blockers
    assert any(
        c.conflict_type == CONFLICT_MISSING_REQUIRED_FIELD for c in batch.conflicts
    )


def test_11_unresolved_configuration_blocks_item() -> None:
    planned = _complete_planned(
        matched_configuration_name="",
        matched_configuration_id="",
    )
    state = _state_with_item(planned=planned)
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_BLOCKED
    assert BLOCKER_MISSING_OR_UNCLEAR_CONFIGURATION in item.blockers
    assert any(
        c.conflict_type == CONFLICT_UNRESOLVED_CONFIGURATION for c in batch.conflicts
    )


def test_12_incomplete_filename_blocks_item() -> None:
    planned = _complete_planned(
        suggested_filename="REVIEW_REQUIRED_sample.pdf",
        rendered_filename="REVIEW_REQUIRED_sample.pdf",
        missing_placeholders=("amount",),
    )
    state = _state_with_item(planned=planned)
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="REVIEW_REQUIRED_sample.pdf",
    )
    batch = build_finalization_preview_batch(state)
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_BLOCKED
    assert BLOCKER_INCOMPLETE_FILENAME in item.blockers or any(
        "missing_" in b for b in item.blockers
    )
    assert any(
        c.conflict_type == CONFLICT_INCOMPLETE_FILENAME for c in batch.conflicts
    )


def test_13_duplicate_target_filename_creates_conflict() -> None:
    state = _state_with_two_items()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="same.pdf",
    )
    create_accept_suggestion_decision(
        state,
        item_key="doc-2",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="same.pdf",
    )
    batch = build_finalization_preview_batch(state)
    assert any(
        c.conflict_type == CONFLICT_DUPLICATE_TARGET_FILENAME for c in batch.conflicts
    )


def test_14_duplicate_target_path_creates_conflict() -> None:
    state = _state_with_two_items()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="a.pdf",
    )
    create_accept_suggestion_decision(
        state,
        item_key="doc-2",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="b.pdf",
    )
    bag = get_review_decision_bag(state)
    # Force identical absolute-style preview paths while keeping distinct names.
    bag.decisions_by_item_key["doc-1"] = replace(
        bag.decisions_by_item_key["doc-1"],
        approved_preview_filename="a.pdf",
        approved_target_preview_path="preview/ziel/collision.pdf",
    )
    bag.decisions_by_item_key["doc-2"] = replace(
        bag.decisions_by_item_key["doc-2"],
        approved_preview_filename="b.pdf",
        approved_target_preview_path="preview/ziel/collision.pdf",
    )
    batch = build_finalization_preview_batch(state)
    assert any(
        c.conflict_type == CONFLICT_DUPLICATE_TARGET_PATH for c in batch.conflicts
    )


def test_15_duplicate_target_conflict_blocks_affected_items() -> None:
    state = _state_with_two_items()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="same.pdf",
    )
    create_accept_suggestion_decision(
        state,
        item_key="doc-2",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="same.pdf",
    )
    batch = build_finalization_preview_batch(state)
    blocked = {
        i.item_id for i in batch.items if i.finalization_status == STATUS_BLOCKED
    }
    assert "doc-1" in blocked
    assert "doc-2" in blocked
    assert all(
        BLOCKER_DUPLICATE_TARGET_FILENAME in i.blockers
        for i in batch.items
        if i.item_id in {"doc-1", "doc-2"}
    )


def test_16_unsafe_target_path_creates_blocker(tmp_path: Path) -> None:
    out = tmp_path / "allowed-out"
    out.mkdir()
    state = _state_with_item()
    state.workspace_output_folder_override = str(out)
    readiness = compute_finalization_readiness(
        item_id="doc-1",
        context={
            "supplier": "Lieferant",
            "invoice_date": "2026-07-23",
            "amount": "10,00",
            "selected_payment_field": "PayPal",
            "matched_configuration_name": "PayPal",
            "filename_pattern": "{supplier}.pdf",
            "approved_preview_filename": "Lieferant.pdf",
        },
        approved=True,
        decision_type=DECISION_ACCEPT,
        output_root=str(out),
        target_preview_path="/tmp/outside-root/Lieferant.pdf",
    )
    decision = ReviewDecision(
        decision_id="rd-unsafe",
        source_item_id="doc-1",
        source_filename="sample.pdf",
        decision_type=DECISION_ACCEPT,
        decided_by_user=True,
        decision_timestamp="2026-07-23T12:00:00+00:00",
        approved_preview_filename="Lieferant.pdf",
        approved_target_preview_path="/tmp/outside-root/Lieferant.pdf",
        finalization_ready=False,
        finalization_blockers=(BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT,),
        final_write_allowed=False,
    )
    apply_review_decision_to_item(state, decision, readiness)
    batch = build_finalization_preview_batch(state)
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_BLOCKED
    assert BLOCKER_TARGET_OUTSIDE_OUTPUT_ROOT in item.blockers
    assert any(c.conflict_type == CONFLICT_UNSAFE_TARGET_PATH for c in batch.conflicts)


def test_17_stale_preview_state_creates_blocker() -> None:
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state, preview_state_fresh=False)
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_BLOCKED
    assert BLOCKER_STALE_PREVIEW_STATE in item.blockers
    assert any(
        c.conflict_type == CONFLICT_STALE_PREVIEW_STATE for c in batch.conflicts
    )


def test_18_changed_source_hash_creates_blocker() -> None:
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
        source_hash_at_decision="hash-aaa",
    )
    batch = build_finalization_preview_batch(
        state,
        current_source_hashes={"doc-1": "hash-bbb"},
    )
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_BLOCKED
    assert BLOCKER_SOURCE_HASH_CHANGED in item.blockers
    assert any(
        c.conflict_type == CONFLICT_CHANGED_SOURCE_HASH for c in batch.conflicts
    )


def test_19_ignored_item_is_not_ready() -> None:
    state = _state_with_item()
    create_ignore_for_export_decision(state, item_key="doc-1")
    batch = build_finalization_preview_batch(state)
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_IGNORED
    assert item.finalization_status != STATUS_READY


def test_20_deferred_item_is_not_ready() -> None:
    state = _state_with_item()
    create_defer_decision(state, item_key="doc-1")
    batch = build_finalization_preview_batch(state)
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_DEFERRED
    assert item.finalization_status != STATUS_READY


def test_21_keep_review_required_remains_still_review_required() -> None:
    state = _state_with_item()
    create_keep_review_required_decision(state, item_key="doc-1")
    batch = build_finalization_preview_batch(state)
    item = next(i for i in batch.items if i.item_id == "doc-1")
    assert item.finalization_status == STATUS_STILL_REVIEW


def test_22_batch_conflict_includes_suggested_resolution() -> None:
    state = _state_with_two_items()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="same.pdf",
    )
    create_accept_suggestion_decision(
        state,
        item_key="doc-2",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="same.pdf",
    )
    batch = build_finalization_preview_batch(state)
    conflict = next(
        c
        for c in batch.conflicts
        if c.conflict_type == CONFLICT_DUPLICATE_TARGET_FILENAME
    )
    assert conflict.suggested_resolution
    assert len(conflict.suggested_resolution) > 10


def test_23_ui_exposes_finalisierungs_vorschau() -> None:
    vm = build_review_page_vm(_state_with_item())
    assert vm.finalization_preview_batch_title == MSG_BATCH_TITLE
    assert "Finalisierungs-Vorschau" in vm.finalization_preview_batch_title
    assert MSG_BATCH_TITLE in BATCH_PY.read_text(encoding="utf-8")
    assert "MSG_BATCH_TITLE" in REVIEW_PAGE.read_text(encoding="utf-8")
    assert MSG_BATCH_TITLE in " ".join(vm.finalization_preview_batch_summary_lines)


def test_24_ui_exposes_bereit_fuer_spaetere_finalisierung() -> None:
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    vm = build_review_page_vm(state)
    assert MSG_BATCH_READY in " ".join(vm.finalization_preview_batch_summary_lines)
    assert "Bereit für spätere Finalisierung" in BATCH_PY.read_text(encoding="utf-8")
    assert "MSG_BATCH_READY" in REVIEW_PAGE.read_text(encoding="utf-8")


def test_25_ui_exposes_blockiert() -> None:
    vm = build_review_page_vm(_state_with_item())
    assert MSG_BATCH_BLOCKED in " ".join(vm.finalization_preview_batch_summary_lines)
    assert "Blockiert" in BATCH_PY.read_text(encoding="utf-8")
    assert "MSG_BATCH_BLOCKED" in REVIEW_PAGE.read_text(encoding="utf-8")


def test_26_ui_shows_no_final_write_safety_text() -> None:
    vm = build_review_page_vm(_state_with_item())
    assert vm.finalization_preview_batch_no_final_write_text == MSG_BATCH_NO_FINAL_WRITE
    assert "Noch kein finales Schreiben" in vm.finalization_preview_batch_no_final_write_text
    assert MSG_BATCH_NO_FINAL_WRITE in vm.finalization_preview_batch_summary_lines
    assert "MSG_BATCH_NO_FINAL_WRITE" in REVIEW_PAGE.read_text(encoding="utf-8")


def test_27_preview_export_manifest_includes_finalization_preview_batch(
    tmp_path: Path,
) -> None:
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    report = batch_report_fields(batch)
    payload = _manifest_payload(
        run_id="sandbox-batch-1",
        generated_at="2026-07-23T12:00:00+00:00",
        input_root=tmp_path / "in",
        output_root=tmp_path / "out",
        export_folder=tmp_path / "out" / "preview-export-test",
        items=(),
        recognized_count=0,
        review_count=1,
        error_count=0,
        planned_count=1,
        finalization_preview_batch=report,
    )
    assert payload["finalization_preview_batch"] is not None
    assert payload["finalization_preview_batch"]["batch_id"]


def test_28_manifest_includes_final_write_allowed_false(tmp_path: Path) -> None:
    batch = build_finalization_preview_batch(_state_with_item())
    report = batch_report_fields(batch)
    payload = _manifest_payload(
        run_id="r",
        generated_at="t",
        input_root=tmp_path / "in",
        output_root=tmp_path / "out",
        export_folder=tmp_path / "export",
        items=(),
        recognized_count=0,
        review_count=0,
        error_count=0,
        planned_count=0,
        finalization_preview_batch=report,
    )
    assert payload["final_write_allowed"] is False
    assert payload["finalization_preview_batch"]["final_write_allowed"] is False


def test_29_manifest_includes_ready_count(tmp_path: Path) -> None:
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    report = batch_report_fields(batch)
    payload = _manifest_payload(
        run_id="r",
        generated_at="t",
        input_root=tmp_path / "in",
        output_root=tmp_path / "out",
        export_folder=tmp_path / "export",
        items=(),
        recognized_count=0,
        review_count=1,
        error_count=0,
        planned_count=1,
        finalization_preview_batch=report,
    )
    assert "ready_count" in payload
    assert payload["ready_count"] == batch.ready_count


def test_30_manifest_includes_blocked_count(tmp_path: Path) -> None:
    planned = _complete_planned(supplier="", counterparty_name="")
    state = _state_with_item(planned=planned)
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    report = batch_report_fields(batch)
    payload = _manifest_payload(
        run_id="r",
        generated_at="t",
        input_root=tmp_path / "in",
        output_root=tmp_path / "out",
        export_folder=tmp_path / "export",
        items=(),
        recognized_count=0,
        review_count=1,
        error_count=0,
        planned_count=1,
        finalization_preview_batch=report,
    )
    assert payload["blocked_count"] == batch.blocked_count
    assert payload["blocked_count"] >= 1


def test_31_manifest_includes_conflicts(tmp_path: Path) -> None:
    state = _state_with_two_items()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="same.pdf",
    )
    create_accept_suggestion_decision(
        state,
        item_key="doc-2",
        decided_by_user=True,
        explicit_confirmation=True,
        approved_preview_filename="same.pdf",
    )
    batch = build_finalization_preview_batch(state)
    report = batch_report_fields(batch)
    payload = _manifest_payload(
        run_id="r",
        generated_at="t",
        input_root=tmp_path / "in",
        output_root=tmp_path / "out",
        export_folder=tmp_path / "export",
        items=(),
        recognized_count=0,
        review_count=2,
        error_count=0,
        planned_count=2,
        finalization_preview_batch=report,
    )
    assert payload["conflicts"]
    assert any(
        c.get("conflict_type") == CONFLICT_DUPLICATE_TARGET_FILENAME
        for c in payload["conflicts"]
    )


def test_32_item_export_includes_finalization_status() -> None:
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    fields = {
        **decision_report_fields_for_item(state, "doc-1"),
        **item_batch_export_fields(batch, "doc-1"),
    }
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
    enriched = _with_decision_fields(item, {"doc-1": fields}, item_key="doc-1")
    assert enriched.finalization_status == STATUS_READY
    assert enriched.final_write_allowed is False


def test_33_item_export_includes_finalization_blockers() -> None:
    planned = _complete_planned(supplier="", counterparty_name="")
    state = _state_with_item(planned=planned)
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    fields = {
        **decision_report_fields_for_item(state, "doc-1"),
        **item_batch_export_fields(batch, "doc-1"),
    }
    assert fields["finalization_blockers"]
    assert BLOCKER_MISSING_SUPPLIER in fields["finalization_blockers"]


def test_34_saving_building_batch_does_not_call_run_once() -> None:
    assert batch_builder_calls_run_once() is False
    tree = ast.parse(BATCH_PY.read_text(encoding="utf-8"))
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "run_once" not in calls
    state = _state_with_item()
    build_finalization_preview_batch(state)
    assert state.finalization_preview_batch_ui.called_run_once is False


def test_35_batch_building_does_not_mutate_input(tmp_path: Path) -> None:
    assert batch_builder_mutates_input() is False
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 before-batch")
    before = source.read_bytes()
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    build_finalization_preview_batch(state)
    assert source.read_bytes() == before


def test_36_batch_building_does_not_write_final_pdfs(tmp_path: Path) -> None:
    assert batch_builder_writes_final_pdfs() is False
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
    build_finalization_preview_batch(state)
    assert list(out.rglob("*.pdf")) == []


def test_37_batch_building_does_not_touch_real_invoice_folders() -> None:
    assert batch_builder_touches_real_invoice_folders() is False
    text = BATCH_PY.read_text(encoding="utf-8")
    for folder in FORBIDDEN_FOLDERS:
        assert folder not in text
    state = _state_with_item()
    build_finalization_preview_batch(state)
    assert state.finalization_preview_batch_ui.touched_real_invoice_folders is False


def test_38_no_saas_ready_claim() -> None:
    assert batch_builder_claims_saas_ready() is False
    text = BATCH_PY.read_text(encoding="utf-8")
    assert "saas ready" not in text.lower()
    lowered = text.lower()
    if "saas_ready" in lowered:
        assert "false" in lowered or "not" in lowered


def test_39_no_production_ready_claim() -> None:
    assert batch_builder_claims_production_ready() is False
    batch = build_finalization_preview_batch(_state_with_item())
    assert batch.to_dict()["claims_production_ready"] is False
    assert "production_ready=true" not in BATCH_PY.read_text(encoding="utf-8").lower()
    vm = build_review_page_vm(_state_with_item())
    assert vm.claims_production_ready is False


def test_40_track_a_protection_still_passes() -> None:
    import tests.test_track_a_internal_app_protection as protection

    protection.test_track_a_protected_files_unchanged_vs_head()
    protection.test_protected_track_a_and_core_not_staged()
    for protected in TRACK_A_PROTECTED:
        if protected in {
            "invoice_tool/ui_profile_dialog.py",
            "invoice_tool/ui_document_rules.py",
        }:
            continue
        assert (ROOT / protected).is_file()


def test_batch_summary_lines_include_safety() -> None:
    lines = batch_summary_lines(build_finalization_preview_batch(_state_with_item()))
    assert MSG_BATCH_TITLE in lines
    assert MSG_BATCH_NO_FINAL_WRITE in lines


def test_report_fields_json_serializable() -> None:
    state = _state_with_item()
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    report = batch_report_fields(build_finalization_preview_batch(state))
    json.dumps(report)
