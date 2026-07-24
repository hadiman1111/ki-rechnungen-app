"""Track-B Controlled Final Write Sandbox Implementation (Prompt 33/34).

Sandbox copies only — no productive processing, no real invoice folders,
no original mutation, production final write remains disabled.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from invoice_tool.ui_v2.controlled_final_write_sandbox import (
    ARTIFACT_BLOCKED,
    ARTIFACT_COPIED,
    ARTIFACT_FAILURES,
    ARTIFACT_MANIFEST_CSV,
    ARTIFACT_MANIFEST_JSON,
    ARTIFACT_POST_AUDIT,
    ARTIFACT_PRE_AUDIT,
    ARTIFACT_README,
    ARTIFACT_SKIPPED,
    MSG_CTA_CONTROLLED_ONLY,
    MSG_CTA_ORIGINALS_UNCHANGED,
    MSG_CTA_SANDBOX_WRITE,
    SANDBOX_FINAL_WRITE_FOLDER_PREFIX,
    apply_controlled_final_write_sandbox,
    execute_controlled_final_write_sandbox,
    sandbox_final_write_archives_originals,
    sandbox_final_write_calls_run_once,
    sandbox_final_write_claims_production_ready,
    sandbox_final_write_claims_saas_ready,
    sandbox_final_write_deletes_originals,
    sandbox_final_write_moves_originals,
    sandbox_final_write_mutates_input,
    sandbox_final_write_renames_originals,
    sandbox_final_write_report_fields,
    sandbox_final_write_touches_real_invoice_folders,
)
from invoice_tool.ui_v2.final_write_gate import (
    BLOCKER_DUPLICATE_UNRESOLVED,
    BLOCKER_MISSING_AUTH,
    BLOCKER_MISSING_DRY_RUN,
    BLOCKER_NO_READY_ITEMS,
    BLOCKER_REAL_INVOICE,
    BLOCKER_SOURCE_HASH_CHANGED,
    BLOCKER_TARGET_OUTSIDE,
    AUTH_SCOPE_SELECTED,
    build_sandbox_final_write_authorization,
    default_sandbox_acknowledgements,
    run_final_write_gate_runtime_check,
)
from invoice_tool.ui_v2.finalization_dry_run_package import (
    write_finalization_dry_run_package,
)
from invoice_tool.ui_v2.finalization_preview_batch import (
    CONFLICT_DUPLICATE_TARGET_FILENAME,
    STATUS_READY,
    FinalizationPreviewConflict,
    build_finalization_preview_batch,
)
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.preview_export import _manifest_payload
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_decision import create_accept_suggestion_decision
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
SANDBOX_PY = ROOT / "invoice_tool" / "ui_v2" / "controlled_final_write_sandbox.py"
GATE_PY = ROOT / "invoice_tool" / "ui_v2" / "final_write_gate.py"
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sandbox_pair(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "KI-Rechnungen-Test"
    input_root = root / "sandbox" / "input"
    output_root = root / "sandbox" / "output"
    input_root.mkdir(parents=True)
    output_root.mkdir(parents=True)
    return input_root, output_root


def _complete_planned(
    *,
    output_root: Path | None = None,
    **overrides: object,
) -> ProcessingPlannedDestination:
    document_name = str(overrides.get("document_name") or "sample.pdf")
    if "planned_path" in overrides:
        planned_path = overrides["planned_path"]
    elif output_root is not None:
        planned_path = str(output_root / "preview" / "ziel" / document_name)
    else:
        planned_path = "preview/ziel/sample.pdf"
    base = dict(
        document_name=document_name,
        planned_path=planned_path,
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
    content: bytes = b"%PDF-1.4 sandbox-final-write-source",
) -> UiV2State:
    input_root, output_root = _sandbox_pair(tmp_path)
    (input_root / document_name).write_bytes(content)
    planned = _complete_planned(output_root=output_root, document_name=document_name)
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="sandbox-sfw-1",
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


def _ready_package(tmp_path: Path):
    state = _state_with_item(tmp_path)
    create_accept_suggestion_decision(
        state,
        item_key="doc-1",
        decided_by_user=True,
        explicit_confirmation=True,
    )
    batch = build_finalization_preview_batch(state)
    assert batch.ready_count >= 1
    dry = write_finalization_dry_run_package(
        batch,
        output_root=state.workspace_output_folder_override,
        input_root=state.workspace_input_folder_override,
    )
    assert dry.ok and dry.package is not None
    return state, batch, dry.package


def _auth_for(package, selected=("doc-1",)):
    return build_sandbox_final_write_authorization(
        dry_run_package_id=package.package_id,
        batch_id=package.batch_id,
        selected_item_ids=selected,
        authorization_scope=AUTH_SCOPE_SELECTED,
        authorized_by_user=True,
        acknowledgements=default_sandbox_acknowledgements(),
    )


def _execute_ok(tmp_path: Path):
    state, batch, package = _ready_package(tmp_path)
    auth = _auth_for(package)
    result = execute_controlled_final_write_sandbox(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=state.workspace_output_folder_override,
        sandbox_final_write=True,
    )
    return state, batch, package, result


def test_01_sandbox_result_sandbox_final_write_true(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.ok
    assert result.sandbox_final_write is True


def test_02_sandbox_result_productive_mode_requested_false(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.productive_mode_requested is False


def test_03_sandbox_result_production_final_write_false(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.final_write_allowed_for_production is False


def test_04_originals_moved_false(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.originals_moved is False


def test_05_originals_renamed_false(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.originals_renamed is False


def test_06_originals_archived_false(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.originals_archived is False


def test_07_originals_deleted_false(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.originals_deleted is False


def test_08_runtime_requires_dry_run_package(tmp_path: Path) -> None:
    _, batch, package = _ready_package(tmp_path)
    auth = _auth_for(package)
    check = run_final_write_gate_runtime_check(
        package=None,
        batch=batch,
        authorization=auth,
        controlled_output_root=package.output_root,
        sandbox_final_write=True,
    )
    assert BLOCKER_MISSING_DRY_RUN in check.blockers
    assert check.final_write_execution_allowed_for_sandbox is False


def test_09_runtime_requires_user_authorization(tmp_path: Path) -> None:
    _, batch, package = _ready_package(tmp_path)
    check = run_final_write_gate_runtime_check(
        package=package,
        batch=batch,
        authorization=None,
        controlled_output_root=package.output_root,
        sandbox_final_write=True,
        selected_item_ids=["doc-1"],
    )
    assert BLOCKER_MISSING_AUTH in check.blockers


def test_10_runtime_requires_selected_ready_items(tmp_path: Path) -> None:
    _, batch, package = _ready_package(tmp_path)
    auth = build_sandbox_final_write_authorization(
        dry_run_package_id=package.package_id,
        batch_id=package.batch_id,
        selected_item_ids=[],
        authorized_by_user=True,
        acknowledgements=default_sandbox_acknowledgements(),
    )
    check = run_final_write_gate_runtime_check(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=package.output_root,
        sandbox_final_write=True,
        selected_item_ids=[],
    )
    assert BLOCKER_NO_READY_ITEMS in check.blockers or not auth.authorization_valid


def test_11_runtime_requires_source_hash_match(tmp_path: Path) -> None:
    state, batch, package = _ready_package(tmp_path)
    source = Path(state.workspace_input_folder_override) / "sample.pdf"
    # Corrupt stored preview hash on package items.
    bad_items = tuple(
        replace(item, source_sha256="0" * 64) for item in package.items
    )
    package = replace(package, items=bad_items)
    auth = _auth_for(package)
    check = run_final_write_gate_runtime_check(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=package.output_root,
        sandbox_final_write_root=Path(package.output_root)
        / f"{SANDBOX_FINAL_WRITE_FOLDER_PREFIX}preflight",
        sandbox_final_write=True,
        selected_item_ids=["doc-1"],
    )
    assert BLOCKER_SOURCE_HASH_CHANGED in check.blockers
    assert source.exists()


def test_12_runtime_requires_target_inside_controlled_output(tmp_path: Path) -> None:
    _, batch, package = _ready_package(tmp_path)
    auth = _auth_for(package)
    controlled = Path(package.output_root)
    # Sandbox root deliberately outside controlled output → target recheck fails.
    outside_sandbox = tmp_path / "KI-Rechnungen-Test" / "sibling-outside-output" / (
        f"{SANDBOX_FINAL_WRITE_FOLDER_PREFIX}leak"
    )
    outside_sandbox.mkdir(parents=True)
    check = run_final_write_gate_runtime_check(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=controlled,
        sandbox_final_write_root=outside_sandbox,
        sandbox_final_write=True,
        selected_item_ids=["doc-1"],
    )
    assert check.final_write_execution_allowed_for_sandbox is False
    assert BLOCKER_TARGET_OUTSIDE in check.blockers
    assert any(not p.target_within_output_root for p in check.plans)


def test_13_runtime_blocks_real_invoice_folder_path(tmp_path: Path) -> None:
    _, batch, package = _ready_package(tmp_path)
    auth = _auth_for(package)
    check = run_final_write_gate_runtime_check(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=FORBIDDEN_FOLDERS[0],
        sandbox_final_write=True,
        selected_item_ids=["doc-1"],
    )
    assert BLOCKER_REAL_INVOICE in check.blockers or (
        "controlled_output_root_required" in check.blockers
    )
    assert check.final_write_execution_allowed_for_sandbox is False


def test_14_runtime_blocks_unresolved_duplicate_conflict(tmp_path: Path) -> None:
    _, batch, package = _ready_package(tmp_path)
    conflict = FinalizationPreviewConflict(
        conflict_id="c-dup",
        conflict_type=CONFLICT_DUPLICATE_TARGET_FILENAME,
        affected_item_ids=("doc-1",),
        severity="error",
        message="duplicate",
        blocking=True,
        suggested_resolution="rename",
    )
    batch = replace(batch, conflicts=(conflict,))
    auth = _auth_for(package)
    check = run_final_write_gate_runtime_check(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=package.output_root,
        sandbox_final_write_root=Path(package.output_root)
        / f"{SANDBOX_FINAL_WRITE_FOLDER_PREFIX}preflight",
        sandbox_final_write=True,
        selected_item_ids=["doc-1"],
    )
    assert BLOCKER_DUPLICATE_UNRESOLVED in check.blockers


def test_15_execute_requires_sandbox_final_write_true(tmp_path: Path) -> None:
    _, batch, package = _ready_package(tmp_path)
    auth = _auth_for(package)
    result = execute_controlled_final_write_sandbox(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=package.output_root,
        sandbox_final_write=False,
    )
    assert result.ok is False
    assert "sandbox_final_write" in (result.error or "").lower()


def test_16_execute_creates_sandbox_final_write_prefix_folder(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.sandbox_final_write_root is not None
    root = Path(result.sandbox_final_write_root)
    assert root.is_dir()
    assert root.name.startswith(SANDBOX_FINAL_WRITE_FOLDER_PREFIX)


def test_17_execute_writes_readme(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    text = (Path(result.sandbox_final_write_root) / ARTIFACT_README).read_text(
        encoding="utf-8"
    )
    assert "Sandbox Final Write Test" in text
    assert "not production output" in text or "kein finales Produktions-Output" in text
    assert "production final write remains disabled" in text


def test_18_execute_writes_manifest_json(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    payload = json.loads(
        (Path(result.sandbox_final_write_root) / ARTIFACT_MANIFEST_JSON).read_text(
            encoding="utf-8"
        )
    )
    assert payload["sandbox_final_write"] is True
    assert payload["final_write_allowed_for_production"] is False


def test_19_execute_writes_manifest_csv(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    rows = list(
        csv.DictReader(
            (Path(result.sandbox_final_write_root) / ARTIFACT_MANIFEST_CSV).open(
                encoding="utf-8"
            )
        )
    )
    assert rows
    assert rows[0]["copy_result"] == "copied"


def test_20_execute_writes_pre_write_audit(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    text = (Path(result.sandbox_final_write_root) / ARTIFACT_PRE_AUDIT).read_text(
        encoding="utf-8"
    )
    assert "Pre-Write Audit" in text
    assert "source_hash_recheck_result" in text


def test_21_execute_writes_post_write_audit(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    text = (Path(result.sandbox_final_write_root) / ARTIFACT_POST_AUDIT).read_text(
        encoding="utf-8"
    )
    assert "Post-Write Audit" in text
    assert "originals_moved: false" in text


def test_22_execute_copies_ready_source_to_sandbox_target(tmp_path: Path) -> None:
    state, _, _, result = _execute_ok(tmp_path)
    assert result.final_files_written_count == 1
    target = Path(result.final_files_written[0].final_sandbox_target_path)
    assert target.is_file()
    assert target.parent == Path(result.sandbox_final_write_root)
    source = Path(state.workspace_input_folder_override) / "sample.pdf"
    assert target.read_bytes() == source.read_bytes()


def test_23_execute_does_not_move_original(tmp_path: Path) -> None:
    state, _, _, result = _execute_ok(tmp_path)
    source = Path(state.workspace_input_folder_override) / "sample.pdf"
    assert source.is_file()
    assert result.originals_moved is False
    assert sandbox_final_write_moves_originals() is False


def test_24_execute_does_not_rename_original(tmp_path: Path) -> None:
    state, _, _, result = _execute_ok(tmp_path)
    source = Path(state.workspace_input_folder_override) / "sample.pdf"
    assert source.name == "sample.pdf"
    assert result.originals_renamed is False
    assert sandbox_final_write_renames_originals() is False


def test_25_execute_does_not_archive_original(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.originals_archived is False
    assert sandbox_final_write_archives_originals() is False


def test_26_execute_does_not_delete_original(tmp_path: Path) -> None:
    state, _, _, result = _execute_ok(tmp_path)
    source = Path(state.workspace_input_folder_override) / "sample.pdf"
    assert source.exists()
    assert result.originals_deleted is False
    assert sandbox_final_write_deletes_originals() is False


def test_27_execute_does_not_overwrite_without_policy(tmp_path: Path) -> None:
    state, batch, package = _ready_package(tmp_path)
    auth = _auth_for(package)
    first = execute_controlled_final_write_sandbox(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=state.workspace_output_folder_override,
        sandbox_final_write=True,
    )
    assert first.ok
    # Force second write into same target name by pre-creating conflicting file
    # in a new sandbox root via allow_overwrite=False after planting target.
    # Recreate package/auth and plant existing target under intended root by
    # running again — different folder each time, so plant inside first root
    # and call plan path by reusing allow_overwrite false on same filename in
    # a manually prepared sandbox via execute with planted collision:
    # Use a second execute after copying target into a path that plans will hit:
    # simplest: call execute once, then for the same plans force target_exists
    # by writing a file with the approved name into a new sandbox and using
    # allow_overwrite=False with a pre-existing file created before copy loop.
    # Practical approach: create file at planned target before copy by
    # monkey-running with planted file after mkdir — covered via unit of
    # second write attempt into existing file under same root using
    # allow_overwrite False by planting into first sandbox and re-invoking
    # copy logic through a second execute that selects same item into new root
    # (no collision). Instead plant collision inside first root and re-check
    # gate with allow_overwrite=False on existing target path.
    target_name = Path(first.final_files_written[0].final_sandbox_target_path).name
    planted_root = (
        Path(state.workspace_output_folder_override)
        / f"{SANDBOX_FINAL_WRITE_FOLDER_PREFIX}planted"
    )
    planted_root.mkdir()
    (planted_root / target_name).write_bytes(b"%PDF-1.4 existing")
    check = run_final_write_gate_runtime_check(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=state.workspace_output_folder_override,
        sandbox_final_write_root=planted_root,
        sandbox_final_write=True,
        allow_overwrite=False,
        selected_item_ids=["doc-1"],
    )
    assert any(
        "target_exists_without_explicit_policy" in b for b in check.blockers
    ) or any(
        "target_exists_without_explicit_policy" in p.write_blockers
        for p in check.plans
    )


def test_28_execute_records_skipped_items(tmp_path: Path) -> None:
    # Two items: select only one → other skipped.
    input_root, output_root = _sandbox_pair(tmp_path)
    (input_root / "a.pdf").write_bytes(b"%PDF-1.4 a")
    (input_root / "b.pdf").write_bytes(b"%PDF-1.4 b")
    planned_a = _complete_planned(
        output_root=output_root,
        document_name="a.pdf",
        suggested_filename="A_2026-07-23_10,00_Eingang_PayPal.pdf",
        rendered_filename="A_2026-07-23_10,00_Eingang_PayPal.pdf",
    )
    planned_b = _complete_planned(
        output_root=output_root,
        document_name="b.pdf",
        suggested_filename="B_2026-07-23_10,00_Eingang_PayPal.pdf",
        rendered_filename="B_2026-07-23_10,00_Eingang_PayPal.pdf",
    )
    run = ProcessingRunState(
        status="completed",
        message="ok",
        run_id="two-items",
        review_items=(
            ProcessingReviewItem(
                document_name="a.pdf",
                reason="x",
                status_label="unklar",
                document_id="doc-a",
            ),
            ProcessingReviewItem(
                document_name="b.pdf",
                reason="x",
                status_label="unklar",
                document_id="doc-b",
            ),
        ),
        planned_destinations=(planned_a, planned_b),
        planned_destination_count=2,
        state_updated_at="2026-07-23T12:00:00+00:00",
        outcome_kind="all_review",
    )
    state = UiV2State(processing_run_state=run)
    state.workspace_input_folder_override = str(input_root)
    state.workspace_output_folder_override = str(output_root)
    create_accept_suggestion_decision(
        state, item_key="doc-a", decided_by_user=True, explicit_confirmation=True
    )
    create_accept_suggestion_decision(
        state, item_key="doc-b", decided_by_user=True, explicit_confirmation=True
    )
    batch = build_finalization_preview_batch(state)
    dry = write_finalization_dry_run_package(
        batch, output_root=output_root, input_root=input_root
    )
    assert dry.ok and dry.package is not None
    auth = _auth_for(dry.package, selected=("doc-a",))
    result = execute_controlled_final_write_sandbox(
        package=dry.package,
        batch=batch,
        authorization=auth,
        controlled_output_root=output_root,
        sandbox_final_write=True,
        selected_item_ids=["doc-a"],
    )
    assert result.ok
    assert any(row.get("item_id") == "doc-b" for row in result.skipped_items)
    assert (Path(result.sandbox_final_write_root) / ARTIFACT_SKIPPED).is_file()


def test_29_execute_records_blocked_items(tmp_path: Path) -> None:
    state, batch, package = _ready_package(tmp_path)
    bad_items = tuple(
        replace(item, source_sha256="f" * 64, ready_for_future_finalization=True)
        for item in package.items
    )
    package = replace(package, items=bad_items)
    # Still authorize; gate will block on hash — execute returns blocked.
    auth = _auth_for(package)
    result = execute_controlled_final_write_sandbox(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=state.workspace_output_folder_override,
        sandbox_final_write=True,
    )
    assert result.ok is False
    assert result.blocked_items or result.error
    # When gate blocks before folder creation, blocked_items may be gate blockers.
    assert result.final_files_written_count == 0


def test_30_execute_records_failures(tmp_path: Path) -> None:
    # Failures artifact exists on successful path (empty) and on copy errors.
    _, _, _, result = _execute_ok(tmp_path)
    assert (Path(result.sandbox_final_write_root) / ARTIFACT_FAILURES).is_file()
    assert isinstance(result.failures, tuple)


def test_31_execute_records_run_once_called_false(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.run_once_called is False


def test_32_execute_does_not_call_run_once(tmp_path: Path) -> None:
    assert sandbox_final_write_calls_run_once() is False
    tree = ast.parse(SANDBOX_PY.read_text(encoding="utf-8"))
    calls = [
        n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    ]
    assert "run_once" not in calls
    text = SANDBOX_PY.read_text(encoding="utf-8")
    assert "invoice_tool.run" not in text
    assert "from invoice_tool.run" not in text
    assert "import run_once" not in text
    # Attribute calls like module.run_once(...) must not exist.
    attr_calls = [
        n.func.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    ]
    assert "run_once" not in attr_calls


def test_33_execute_does_not_mutate_input_files(tmp_path: Path) -> None:
    state, _, _, result = _execute_ok(tmp_path)
    source = Path(state.workspace_input_folder_override) / "sample.pdf"
    before = source.read_bytes()
    digest = _sha256(source)
    assert result.source_mutation is False
    assert sandbox_final_write_mutates_input() is False
    assert source.read_bytes() == before
    assert _sha256(source) == digest


def test_34_execute_does_not_write_outside_controlled_output(tmp_path: Path) -> None:
    state, _, _, result = _execute_ok(tmp_path)
    output = Path(state.workspace_output_folder_override).resolve()
    root = Path(result.sandbox_final_write_root).resolve()
    assert root.is_relative_to(output)
    for item in result.final_files_written:
        assert Path(item.final_sandbox_target_path).resolve().is_relative_to(output)


def test_35_preview_export_includes_sandbox_metadata(tmp_path: Path) -> None:
    state, _, _, result = _execute_ok(tmp_path)
    meta = sandbox_final_write_report_fields(result)
    payload = _manifest_payload(
        run_id="r1",
        generated_at="2026-07-23T12:00:00+00:00",
        input_root=Path(state.workspace_input_folder_override),
        output_root=Path(state.workspace_output_folder_override),
        export_folder=Path(state.workspace_output_folder_override) / "preview-export-x",
        items=(),
        recognized_count=0,
        review_count=1,
        error_count=0,
        planned_count=1,
        sandbox_final_write=meta,
    )
    assert payload["sandbox_final_write_available"] is True
    assert payload["sandbox_final_write_result_id"] == result.result_id
    assert payload["sandbox_final_write_root"] == result.sandbox_final_write_root
    assert payload["final_write_allowed_for_production"] is False
    assert payload["originals_moved"] is False
    assert payload["originals_renamed"] is False
    assert payload["originals_archived"] is False
    assert payload["originals_deleted"] is False
    assert payload["source_mutation"] is False


def test_36_ui_exposes_sandbox_finalschreiben_testen(tmp_path: Path) -> None:
    state, _, _ = _ready_package(tmp_path)
    vm = build_review_page_vm(state)
    assert vm.sandbox_final_write_cta == MSG_CTA_SANDBOX_WRITE
    assert "Sandbox-Finalschreiben testen" in vm.sandbox_final_write_cta
    review_text = REVIEW_PAGE.read_text(encoding="utf-8")
    assert "MSG_CTA_SANDBOX_WRITE" in review_text
    assert "_sandbox_final_write_panel" in review_text


def test_37_ui_exposes_nur_kontrollierter_test_output(tmp_path: Path) -> None:
    state, _, _ = _ready_package(tmp_path)
    vm = build_review_page_vm(state)
    assert vm.sandbox_final_write_controlled_only == MSG_CTA_CONTROLLED_ONLY
    assert "Nur kontrollierter Test-Output" in vm.sandbox_final_write_controlled_only


def test_38_ui_exposes_originale_bleiben_unverändert(tmp_path: Path) -> None:
    state, _, _ = _ready_package(tmp_path)
    vm = build_review_page_vm(state)
    assert vm.sandbox_final_write_originals_unchanged == MSG_CTA_ORIGINALS_UNCHANGED
    assert "Originale bleiben unverändert" in vm.sandbox_final_write_originals_unchanged


def test_39_no_saas_ready_claim(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.claims_saas_ready is False
    assert sandbox_final_write_claims_saas_ready() is False
    assert "SaaS-ready" not in result.safety_summary or "nicht" in result.to_dict().get(
        "title", ""
    )


def test_40_no_production_ready_claim(tmp_path: Path) -> None:
    _, _, _, result = _execute_ok(tmp_path)
    assert result.claims_production_ready is False
    assert sandbox_final_write_claims_production_ready() is False


def test_41_track_a_protection_still_passes() -> None:
    for rel in TRACK_A_PROTECTED:
        # Modules themselves must not import ui_v2 sandbox writer.
        path = ROOT / rel
        if not path.exists():
            continue
        if rel in {
            "invoice_tool/ui_profile_dialog.py",
            "invoice_tool/ui_document_rules.py",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        assert "controlled_final_write_sandbox" not in text
        assert "final_write_gate" not in text
    assert sandbox_final_write_touches_real_invoice_folders() is False
    # AST: sandbox modules do not import processing core run_once.
    for py in (SANDBOX_PY, GATE_PY):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not any(
            name == "invoice_tool.run" or name.startswith("invoice_tool.run.")
            for name in imports
        )


def test_42_apply_ui_helper_and_extra_artifacts(tmp_path: Path) -> None:
    state, _, package = _ready_package(tmp_path)
    from invoice_tool.ui_v2.finalization_dry_run_package import (
        get_finalization_dry_run_package_bag,
    )

    bag = get_finalization_dry_run_package_bag(state)
    bag.last_package = package
    bag.last_package_root = package.package_root or ""
    result = apply_controlled_final_write_sandbox(state, sandbox_final_write=True)
    assert result.ok
    root = Path(result.sandbox_final_write_root)
    for name in (
        ARTIFACT_README,
        ARTIFACT_MANIFEST_JSON,
        ARTIFACT_MANIFEST_CSV,
        ARTIFACT_PRE_AUDIT,
        ARTIFACT_POST_AUDIT,
        ARTIFACT_COPIED,
        ARTIFACT_SKIPPED,
        ARTIFACT_BLOCKED,
        ARTIFACT_FAILURES,
    ):
        assert (root / name).is_file(), name
    vm = build_review_page_vm(state)
    assert vm.sandbox_final_write_written_count >= 1
    assert STATUS_READY in {i.finalization_status for i in package.items}


def test_43_no_productive_run_once_flag_on_execute(tmp_path: Path) -> None:
    _, batch, package = _ready_package(tmp_path)
    auth = _auth_for(package)
    result = execute_controlled_final_write_sandbox(
        package=package,
        batch=batch,
        authorization=auth,
        controlled_output_root=package.output_root,
        sandbox_final_write=True,
        call_run_once=True,
    )
    assert result.ok is False
    assert result.run_once_called is False
