"""Track-B Finalization Dry-Run Package & Audit (Prompt 31/34).

No productive processing, no real invoice folders, no final writes.
"""

from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

from invoice_tool.ui_v2.finalization_dry_run_package import (
    ARTIFACT_AUDIT,
    ARTIFACT_BLOCKED,
    ARTIFACT_CONFLICTS,
    ARTIFACT_MANIFEST_CSV,
    ARTIFACT_MANIFEST_JSON,
    ARTIFACT_PLAN,
    ARTIFACT_READY,
    ARTIFACT_README,
    DRY_RUN_PACKAGE_FOLDER_PREFIX,
    MSG_CTA_CHECK_ONLY,
    MSG_CTA_CREATE_AUDIT,
    MSG_CTA_CREATE_DRY_RUN,
    MSG_FINAL_WRITE_FALSE,
    MSG_NO_FINAL_PRODUCTION,
    MSG_ORIGINALS_UNCHANGED,
    MSG_PACKAGE_OUTSIDE_OUTPUT,
    apply_finalization_dry_run_package,
    build_finalization_dry_run_package_model,
    dry_run_package_archives_originals,
    dry_run_package_calls_run_once,
    dry_run_package_claims_production_ready,
    dry_run_package_claims_saas_ready,
    dry_run_package_deletes_originals,
    dry_run_package_moves_originals,
    dry_run_package_mutates_input,
    dry_run_package_renames_originals,
    dry_run_package_report_fields,
    dry_run_package_touches_real_invoice_folders,
    dry_run_package_writes_final_pdfs,
    write_finalization_dry_run_package,
)
from invoice_tool.ui_v2.finalization_preview_batch import (
    STATUS_READY,
    build_finalization_preview_batch,
)
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.preview_export import _manifest_payload
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_decision import (
    create_accept_suggestion_decision,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
DRY_RUN_PY = ROOT / "invoice_tool" / "ui_v2" / "finalization_dry_run_package.py"
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


def _sandbox_pair(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "KI-Rechnungen-Test"
    input_root = root / "sandbox" / "input"
    output_root = root / "sandbox" / "output"
    input_root.mkdir(parents=True)
    output_root.mkdir(parents=True)
    return input_root, output_root


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
    tmp_path: Path,
    *,
    document_name: str = "sample.pdf",
    document_id: str = "doc-1",
) -> UiV2State:
    input_root, output_root = _sandbox_pair(tmp_path)
    (input_root / document_name).write_bytes(b"%PDF-1.4 dry-run-source")
    planned = _complete_planned(document_name=document_name)
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="sandbox-dry-run-1",
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
    state.workspace_input_folder_override = str(input_root)
    state.workspace_output_folder_override = str(output_root)
    state.review_preview_ui.selected_item_key = document_id
    return state


def _accepted_batch(tmp_path: Path):
    state = _state_with_item(tmp_path)
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    return state, batch


def test_01_model_dry_run_package_true(tmp_path: Path) -> None:
    _, batch = _accepted_batch(tmp_path)
    package = build_finalization_dry_run_package_model(batch)
    assert package.dry_run_package is True


def test_02_model_final_write_allowed_false(tmp_path: Path) -> None:
    _, batch = _accepted_batch(tmp_path)
    package = build_finalization_dry_run_package_model(batch)
    assert package.final_write_allowed is False


def test_03_writer_creates_folder_under_controlled_output(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    output_root = Path(state.workspace_output_folder_override or "")
    result = write_finalization_dry_run_package(batch, output_root=output_root)
    assert result.ok is True
    assert result.package_root is not None
    assert result.package_root.is_dir()
    assert result.package_root.resolve().is_relative_to(output_root.resolve())


def test_04_writer_rejects_package_root_outside_output(tmp_path: Path) -> None:
    _, batch = _accepted_batch(tmp_path)
    output_root = tmp_path / "KI-Rechnungen-Test" / "sandbox" / "output"
    outside = tmp_path / "outside-of-output" / "finalization-dry-run-bad"
    outside.mkdir(parents=True)
    result = write_finalization_dry_run_package(
        batch,
        output_root=output_root,
        package_root=outside,
    )
    assert result.ok is False
    assert result.error == MSG_PACKAGE_OUTSIDE_OUTPUT


def test_05_writer_uses_finalization_dry_run_prefix(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert result.ok is True
    assert result.package_root is not None
    assert result.package_root.name.startswith(DRY_RUN_PACKAGE_FOLDER_PREFIX)


def test_06_readme_states_no_final_production(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    text = (result.package_root / ARTIFACT_README).read_text(encoding="utf-8")
    assert MSG_NO_FINAL_PRODUCTION in text or "no final production output" in text


def test_07_readme_states_originals_unchanged(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    text = (result.package_root / ARTIFACT_README).read_text(encoding="utf-8")
    assert "Originale unverändert" in text or MSG_ORIGINALS_UNCHANGED in text


def test_08_readme_states_final_write_allowed_false(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    text = (result.package_root / ARTIFACT_README).read_text(encoding="utf-8")
    assert MSG_FINAL_WRITE_FALSE in text


def test_09_manifest_json_exists(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert (result.package_root / ARTIFACT_MANIFEST_JSON).is_file()


def test_10_manifest_json_dry_run_package_true(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    payload = json.loads(
        (result.package_root / ARTIFACT_MANIFEST_JSON).read_text(encoding="utf-8")
    )
    assert payload["dry_run_package"] is True


def test_11_manifest_json_final_write_allowed_false(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    payload = json.loads(
        (result.package_root / ARTIFACT_MANIFEST_JSON).read_text(encoding="utf-8")
    )
    assert payload["final_write_allowed"] is False


def test_12_manifest_json_source_mutation_false(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    payload = json.loads(
        (result.package_root / ARTIFACT_MANIFEST_JSON).read_text(encoding="utf-8")
    )
    assert payload["source_mutation"] is False


def test_13_manifest_json_final_files_written_false(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    payload = json.loads(
        (result.package_root / ARTIFACT_MANIFEST_JSON).read_text(encoding="utf-8")
    )
    assert payload["final_files_written"] is False


def test_14_manifest_json_originals_moved_false(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    payload = json.loads(
        (result.package_root / ARTIFACT_MANIFEST_JSON).read_text(encoding="utf-8")
    )
    assert payload["originals_moved"] is False


def test_15_manifest_json_originals_renamed_false(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    payload = json.loads(
        (result.package_root / ARTIFACT_MANIFEST_JSON).read_text(encoding="utf-8")
    )
    assert payload["originals_renamed"] is False


def test_16_manifest_json_originals_archived_false(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    payload = json.loads(
        (result.package_root / ARTIFACT_MANIFEST_JSON).read_text(encoding="utf-8")
    )
    assert payload["originals_archived"] is False


def test_17_manifest_json_originals_deleted_false(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    payload = json.loads(
        (result.package_root / ARTIFACT_MANIFEST_JSON).read_text(encoding="utf-8")
    )
    assert payload["originals_deleted"] is False


def test_18_manifest_csv_exists(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert (result.package_root / ARTIFACT_MANIFEST_CSV).is_file()


def test_19_audit_markdown_exists(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert (result.package_root / ARTIFACT_AUDIT).is_file()


def test_20_finalization_plan_exists(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert (result.package_root / ARTIFACT_PLAN).is_file()


def test_21_conflicts_report_exists(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert (result.package_root / ARTIFACT_CONFLICTS).is_file()


def test_22_blocked_items_report_exists(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert (result.package_root / ARTIFACT_BLOCKED).is_file()


def test_23_ready_items_report_exists(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert (result.package_root / ARTIFACT_READY).is_file()


def test_24_manifest_csv_one_row_per_item(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    rows = list(
        csv.DictReader(
            (result.package_root / ARTIFACT_MANIFEST_CSV).read_text(encoding="utf-8").splitlines()
        )
    )
    assert len(rows) == len(batch.items) == result.package.total_items


def test_25_plan_describes_future_ops_not_executed(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    plan = (result.package_root / ARTIFACT_PLAN).read_text(encoding="utf-8")
    assert "would_copy_or_rename_source_to_target" in plan
    assert "executed: false" in plan
    assert "not executed" in plan.lower() or "nicht ausgeführt" in plan.lower()


def test_26_preview_export_includes_dry_run_metadata(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert result.package is not None
    meta = dry_run_package_report_fields(result.package)
    payload = _manifest_payload(
        run_id="sandbox-dry-run-1",
        generated_at="2026-07-23T12:00:00+00:00",
        input_root=Path(state.workspace_input_folder_override or tmp_path),
        output_root=Path(state.workspace_output_folder_override or tmp_path),
        export_folder=Path(state.workspace_output_folder_override or tmp_path)
        / "preview-export-test",
        items=(),
        recognized_count=0,
        review_count=1,
        error_count=0,
        planned_count=1,
        finalization_dry_run_package=meta,
    )
    assert payload["finalization_dry_run_package_available"] is True
    assert payload["finalization_dry_run_package_id"] == result.package.package_id
    assert payload["finalization_dry_run_package_path"] == result.package.package_root
    assert payload["final_write_allowed"] is False
    text = PREVIEW_EXPORT_PY.read_text(encoding="utf-8")
    assert "finalization_dry_run_package_available" in text


def test_27_ui_exposes_create_dry_run_cta(tmp_path: Path) -> None:
    state = _state_with_item(tmp_path)
    vm = build_review_page_vm(state)
    assert vm.finalization_dry_run_cta_create == MSG_CTA_CREATE_DRY_RUN
    assert "Finalisierungs-Trockenlauf erstellen" in vm.finalization_dry_run_cta_create
    assert "MSG_CTA_CREATE_DRY_RUN" in REVIEW_PAGE.read_text(encoding="utf-8")
    assert MSG_CTA_CREATE_DRY_RUN in DRY_RUN_PY.read_text(encoding="utf-8")


def test_28_ui_exposes_create_audit_cta(tmp_path: Path) -> None:
    state = _state_with_item(tmp_path)
    vm = build_review_page_vm(state)
    assert vm.finalization_dry_run_cta_audit == MSG_CTA_CREATE_AUDIT
    assert "Audit-Paket erzeugen" in vm.finalization_dry_run_cta_audit
    assert "MSG_CTA_CREATE_AUDIT" in REVIEW_PAGE.read_text(encoding="utf-8")
    assert MSG_CTA_CREATE_AUDIT in DRY_RUN_PY.read_text(encoding="utf-8")


def test_29_ui_shows_check_only_label(tmp_path: Path) -> None:
    state = _state_with_item(tmp_path)
    vm = build_review_page_vm(state)
    assert vm.finalization_dry_run_check_only == MSG_CTA_CHECK_ONLY
    assert "Nur prüfen — nichts final schreiben" in vm.finalization_dry_run_check_only
    assert "MSG_CTA_CHECK_ONLY" in REVIEW_PAGE.read_text(encoding="utf-8")
    assert MSG_CTA_CHECK_ONLY in DRY_RUN_PY.read_text(encoding="utf-8")


def test_30_package_creation_does_not_call_run_once(tmp_path: Path) -> None:
    assert dry_run_package_calls_run_once() is False
    state, _ = _accepted_batch(tmp_path)
    result = apply_finalization_dry_run_package(state)
    assert result.ok is True
    assert result.called_run_once is False
    assert state.finalization_dry_run_package_ui.called_run_once is False
    tree = ast.parse(DRY_RUN_PY.read_text(encoding="utf-8"))
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "run_once" not in calls


def test_31_package_creation_does_not_mutate_input(tmp_path: Path) -> None:
    assert dry_run_package_mutates_input() is False
    state, batch = _accepted_batch(tmp_path)
    input_root = Path(state.workspace_input_folder_override or "")
    before = {
        p.name: p.read_bytes() for p in input_root.iterdir() if p.is_file()
    }
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert result.ok is True
    after = {
        p.name: p.read_bytes() for p in input_root.iterdir() if p.is_file()
    }
    assert before == after
    assert result.mutated_input is False


def test_32_package_creation_does_not_write_final_pdfs(tmp_path: Path) -> None:
    assert dry_run_package_writes_final_pdfs() is False
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert result.ok is True
    assert result.wrote_final_pdfs is False
    assert list(result.package_root.glob("**/*.pdf")) == []


def test_33_package_creation_does_not_move_originals(tmp_path: Path) -> None:
    assert dry_run_package_moves_originals() is False
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert result.package is not None
    assert result.package.originals_moved is False


def test_34_package_creation_does_not_rename_originals(tmp_path: Path) -> None:
    assert dry_run_package_renames_originals() is False
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert result.package is not None
    assert result.package.originals_renamed is False


def test_35_package_creation_does_not_archive_originals(tmp_path: Path) -> None:
    assert dry_run_package_archives_originals() is False
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert result.package is not None
    assert result.package.originals_archived is False


def test_36_package_creation_does_not_delete_originals(tmp_path: Path) -> None:
    assert dry_run_package_deletes_originals() is False
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert result.package is not None
    assert result.package.originals_deleted is False


def test_37_package_creation_does_not_touch_real_invoice_folders(tmp_path: Path) -> None:
    assert dry_run_package_touches_real_invoice_folders() is False
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    assert result.ok is True
    assert result.touched_real_invoice_folders is False
    for forbidden in FORBIDDEN_FOLDERS:
        assert forbidden not in str(result.package_root)


def test_38_no_saas_ready_claim() -> None:
    assert dry_run_package_claims_saas_ready() is False
    text = DRY_RUN_PY.read_text(encoding="utf-8")
    assert "claims_saas_ready" in text
    assert "nicht SaaS-ready" in text


def test_39_no_production_ready_claim() -> None:
    assert dry_run_package_claims_production_ready() is False
    text = DRY_RUN_PY.read_text(encoding="utf-8")
    assert "claims_production_ready" in text
    assert "nicht production-ready" in text


def test_40_track_a_protection_still_passes() -> None:
    import tests.test_track_a_internal_app_protection as protection

    protection.test_track_a_protected_files_unchanged_vs_head()
    for protected in TRACK_A_PROTECTED:
        assert (ROOT / protected).exists() or protected.endswith(
            "ui_document_rules.py"
        )


def test_ready_status_separated_in_reports(tmp_path: Path) -> None:
    state, batch = _accepted_batch(tmp_path)
    result = write_finalization_dry_run_package(
        batch, output_root=state.workspace_output_folder_override
    )
    ready_text = (result.package_root / ARTIFACT_READY).read_text(encoding="utf-8")
    if any(item.finalization_status == STATUS_READY for item in batch.items):
        assert "sample.pdf" in ready_text
    audit = (result.package_root / ARTIFACT_AUDIT).read_text(encoding="utf-8")
    assert "no final files written" in audit
    assert "no run_once productive path" in audit
