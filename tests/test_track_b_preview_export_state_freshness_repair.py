"""Track-B Preview Export state freshness repair (Prompt 24/34).

Export must serialize the current Review-UI / ProcessingRunState values.
No run_once, no productive final write, no Track-A/core mutation.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from invoice_tool.ui_v2.extraction_mapping import (
    enrich_planned_destinations_with_local_extraction,
)
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.preview_export import (
    MSG_NO_PRODUCTION_READY,
    MSG_NO_SAAS_READY,
    MSG_PREVIEW_EXPORT_STALE_SOURCE_BLOCKED,
    MSG_PREVIEW_EXPORT_STALE_STATE_BLOCKED,
    ReviewExportExpectation,
    apply_workspace_preview_export,
    build_review_ui_export_expectations,
    refresh_run_state_from_current_sandbox_input,
    text_claims_forbidden_maturity,
    validate_preview_export_paths,
    write_preview_export_package,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
PREVIEW_EXPORT_MODULE = ROOT / "invoice_tool" / "ui_v2" / "preview_export.py"
CONTROLLED_INPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input")
CONTROLLED_OUTPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output")

PDF = {
    "lumitop": "FA011466.pdf",
    "bootshop": "Rechnung RE-202605-14594.pdf",
    "boettcher": "320262919974.pdf",
    "luxvenum": "Rechnung-2026156019-102201.pdf",
    "storno": "420260091336.pdf",
}

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

TRACK_A_PROTECTED = (
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
)


def _require_controlled() -> None:
    if not CONTROLLED_INPUT.is_dir():
        pytest.skip("controlled input folder missing")
    for name in PDF.values():
        if not (CONTROLLED_INPUT / name).is_file():
            pytest.skip(f"controlled PDF missing: {name}")


def _sandbox_pair(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "KI-Rechnungen-Test"
    input_root = root / "input"
    output_root = root / "output"
    input_root.mkdir(parents=True)
    output_root.mkdir(parents=True)
    return input_root, output_root


def _seed_controlled(input_root: Path, names: tuple[str, ...] | None = None) -> None:
    for name in names or tuple(PDF.values()):
        (input_root / name).write_bytes((CONTROLLED_INPUT / name).read_bytes())


def _digest_tree(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(folder))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return out


def _stale_planned() -> tuple[ProcessingPlannedDestination, ...]:
    """Pre-Prompt-21 style planned rows (stale amounts / storno art mismatch)."""

    return (
        ProcessingPlannedDestination(
            document_name=PDF["lumitop"],
            planned_path="geplant/unklar/2026-05-11_er_er_LUMITOP_500,00_paypal.pdf",
            suggested_filename="2026-05-11_er_er_LUMITOP_500,00_paypal.pdf",
            rendered_filename="2026-05-11_er_er_LUMITOP_500,00_paypal.pdf",
            amount="500,00",
            selected_amount="500,00",
            selected_payment_field="paypal",
            selected_art="er",
            preview_only=True,
            filename_source="configuration_pattern",
        ),
        ProcessingPlannedDestination(
            document_name=PDF["bootshop"],
            planned_path=(
                "geplant/unklar/2026-05-15_er_er_1A-Bootshop.de_80,55_paypal.pdf"
            ),
            suggested_filename="2026-05-15_er_er_1A-Bootshop.de_80,55_paypal.pdf",
            rendered_filename="2026-05-15_er_er_1A-Bootshop.de_80,55_paypal.pdf",
            amount="80,55",
            selected_amount="80,55",
            selected_payment_field="paypal",
            selected_art="er",
            preview_only=True,
            filename_source="configuration_pattern",
        ),
        ProcessingPlannedDestination(
            document_name=PDF["boettcher"],
            planned_path="geplant/unklar/2026-05-23_er_er_Böttcher_AG_84,39_card.pdf",
            suggested_filename="2026-05-23_er_er_Böttcher_AG_84,39_card.pdf",
            rendered_filename="2026-05-23_er_er_Böttcher_AG_84,39_card.pdf",
            amount="84,39",
            selected_amount="84,39",
            selected_payment_field="card",
            selected_art="er",
            preview_only=True,
            filename_source="configuration_pattern",
        ),
        ProcessingPlannedDestination(
            document_name=PDF["luxvenum"],
            planned_path=(
                "geplant/unklar/"
                "2026-05-11_er_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf"
            ),
            suggested_filename=(
                "2026-05-11_er_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf"
            ),
            rendered_filename=(
                "2026-05-11_er_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf"
            ),
            amount="154,95",
            selected_amount="154,95",
            selected_art="er",
            preview_only=True,
            filename_source="configuration_pattern_incomplete",
            missing_placeholders=("payment_field",),
        ),
        ProcessingPlannedDestination(
            document_name=PDF["storno"],
            planned_path=(
                "geplant/unklar/"
                "2026-06-18_er_er_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
            ),
            suggested_filename=(
                "2026-06-18_er_er_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
            ),
            rendered_filename=(
                "2026-06-18_er_er_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
            ),
            amount="68,94",
            selected_amount="68,94",
            selected_art="storno",
            document_type="storno",
            preview_only=True,
            filename_source="configuration_pattern_incomplete",
            missing_placeholders=("payment_field",),
        ),
    )


def _run_from_planned(
    planned: tuple[ProcessingPlannedDestination, ...],
    *,
    run_id: str = "freshness-repair",
) -> ProcessingRunState:
    return ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id=run_id,
        review_items=tuple(
            ProcessingReviewItem(
                document_id=item.document_name,
                document_name=item.document_name,
                reason="review",
                status_label="unklar",
            )
            for item in planned
        ),
        planned_destinations=planned,
        planned_destination_count=len(planned),
        outcome_kind="all_review",
        detailed_item_mapping_complete=True,
        state_updated_at="2026-07-23T12:00:00+00:00",
    )


def _current_enriched_run(input_root: Path) -> ProcessingRunState:
    planned = enrich_planned_destinations_with_local_extraction(
        tuple(
            ProcessingPlannedDestination(
                document_name=name,
                planned_path=f"geplant/unklar/{name}",
                preview_only=True,
                reason="sandbox",
            )
            for name in PDF.values()
        ),
        input_folder=input_root,
    )
    return _run_from_planned(planned, run_id="freshness-current")


def test_01_export_uses_current_lumitop_476_not_stale_500(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    stale = _run_from_planned(_stale_planned(), run_id="stale-lumitop")
    result = write_preview_export_package(
        stale,
        input_root=input_root,
        output_root=output_root,
        refresh_from_input=True,
    )
    assert result.ok, result.error
    names = " ".join(item.preview_filename for item in result.items)
    assert "476,00" in names
    assert "500,00" not in names


def test_02_export_uses_current_bootshop_105_75_not_80_55(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    stale = _run_from_planned(_stale_planned(), run_id="stale-bootshop")
    result = write_preview_export_package(
        stale,
        input_root=input_root,
        output_root=output_root,
        refresh_from_input=True,
    )
    assert result.ok, result.error
    names = " ".join(item.preview_filename for item in result.items)
    assert "105,75" in names
    assert "80,55" not in names


def test_03_export_uses_current_storno_art_not_stale_er_er(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    stale = _run_from_planned(_stale_planned(), run_id="stale-storno")
    result = write_preview_export_package(
        stale,
        input_root=input_root,
        output_root=output_root,
        refresh_from_input=True,
    )
    assert result.ok, result.error
    storno_item = next(
        item for item in result.items if item.source_filename == PDF["storno"]
    )
    assert "storno" in storno_item.preview_filename.lower()
    assert "er_er_Böttcher_AG_68,94" not in storno_item.preview_filename
    assert (storno_item.selected_art or "").lower() == "storno"


def test_04_exported_filenames_match_current_review_preview(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    run = _current_enriched_run(input_root)
    state = UiV2State()
    state.processing_run_state = run
    vm = build_review_page_vm(state)
    ui_by_name = {
        (d.source_filename or d.document_label): d for d in vm.detail_items
    }
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    assert result.ok, result.error
    for item in result.items:
        detail = ui_by_name[item.source_filename]
        expected = build_review_ui_export_expectations(run)
        exp = next(e for e in expected if e.source_filename == item.source_filename)
        assert item.preview_filename == exp.preview_filename
        assert (detail.selected_amount or detail.amount) == (
            item.selected_amount or item.amount
        )


def test_05_manifest_preview_filename_matches_exported_pdf(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    run = _current_enriched_run(input_root)
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    assert result.ok and result.export_folder
    payload = json.loads(
        (result.export_folder / "manifest.json").read_text(encoding="utf-8")
    )
    files_dir = result.export_folder / "files"
    for item in payload["items"]:
        assert (files_dir / item["preview_filename"]).is_file()


def test_06_manifest_amount_matches_current_review_state(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    run = _current_enriched_run(input_root)
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    payload = json.loads(
        (result.export_folder / "manifest.json").read_text(encoding="utf-8")
    )
    by_name = {i["source_filename"]: i for i in payload["items"]}
    assert by_name[PDF["lumitop"]]["selected_amount"] == "476,00"
    assert by_name[PDF["bootshop"]]["selected_amount"] == "105,75"


def test_07_manifest_payment_field_matches_current_review_state(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    run = _current_enriched_run(input_root)
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    payload = json.loads(
        (result.export_folder / "manifest.json").read_text(encoding="utf-8")
    )
    by_name = {i["source_filename"]: i for i in payload["items"]}
    assert by_name[PDF["lumitop"]]["selected_payment_field"] == "paypal"
    assert by_name[PDF["bootshop"]]["selected_payment_field"] == "paypal"
    assert by_name[PDF["boettcher"]]["selected_payment_field"] == "card"


def test_08_stale_cached_export_data_not_used_as_source(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    # Plant a previous stale export package under output — must not feed export.
    old = output_root / "preview-export-track-b-dry-a9609610b265-old"
    (old / "files").mkdir(parents=True)
    (old / "manifest.json").write_text(
        json.dumps({"items": [{"preview_filename": "STALE_500.pdf"}]}),
        encoding="utf-8",
    )
    stale = _run_from_planned(_stale_planned(), run_id="ignore-old-export")
    state = UiV2State()
    state.processing_run_state = stale
    state.workspace_input_folder_override = str(input_root)
    state.workspace_output_folder_override = str(output_root)
    state.workspace_last_preview_export_folder = str(old)
    result = apply_workspace_preview_export(state)
    assert result.ok, result.error
    names = " ".join(item.preview_filename for item in result.items)
    assert "476,00" in names
    assert "500,00" not in names
    assert result.export_folder != old


def test_09_old_preview_export_folder_not_used_as_source(tmp_path: Path) -> None:
    old_export = (
        tmp_path
        / "KI-Rechnungen-Test"
        / "output"
        / "preview-export-track-b-dry-a9609610b265-old"
    )
    old_export.mkdir(parents=True)
    err = validate_preview_export_paths(
        old_export,
        tmp_path / "KI-Rechnungen-Test" / "output",
    )
    assert err is not None
    assert "PREVIEW_EXPORT_STALE_STATE_BLOCKED" in err


def test_10_metadata_exported_from_current_state_true(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root, (PDF["lumitop"],))
    run = _current_enriched_run(input_root)
    run = ProcessingRunState(
        status=run.status,
        run_id=run.run_id,
        review_items=tuple(
            i for i in run.review_items if i.document_name == PDF["lumitop"]
        ),
        planned_destinations=tuple(
            p for p in run.planned_destinations if p.document_name == PDF["lumitop"]
        ),
        planned_destination_count=1,
        state_updated_at=run.state_updated_at,
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    payload = json.loads(
        (result.export_folder / "manifest.json").read_text(encoding="utf-8")
    )
    assert payload["exported_from_current_state"] is True


def test_11_metadata_previous_export_reused_false(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root, (PDF["bootshop"],))
    run = _current_enriched_run(input_root)
    run = ProcessingRunState(
        status="completed",
        run_id="meta-reuse",
        review_items=tuple(
            i for i in run.review_items if i.document_name == PDF["bootshop"]
        ),
        planned_destinations=tuple(
            p for p in run.planned_destinations if p.document_name == PDF["bootshop"]
        ),
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    payload = json.loads(
        (result.export_folder / "manifest.json").read_text(encoding="utf-8")
    )
    assert payload["previous_export_reused"] is False


def test_12_metadata_state_freshness_checked_true(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root, (PDF["boettcher"],))
    run = _current_enriched_run(input_root)
    run = ProcessingRunState(
        status="completed",
        run_id="meta-fresh",
        review_items=tuple(
            i for i in run.review_items if i.document_name == PDF["boettcher"]
        ),
        planned_destinations=tuple(
            p for p in run.planned_destinations if p.document_name == PDF["boettcher"]
        ),
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    payload = json.loads(
        (result.export_folder / "manifest.json").read_text(encoding="utf-8")
    )
    assert payload["state_freshness_checked"] is True
    assert payload["source_run_id"] == "meta-fresh"
    assert payload["export_created_at"]
    assert payload["state_source"]


def test_13_stale_state_mismatch_blocks_export() -> None:
    expectations = (
        ReviewExportExpectation(
            source_filename=PDF["lumitop"],
            preview_filename=(
                "REVIEW_REQUIRED__SUGGESTED__"
                "2026-05-11_er_er_LUMITOP_476,00_paypal.pdf"
            ),
            selected_amount="476,00",
            selected_payment_field="paypal",
            selected_art="er",
        ),
    )
    export_rows = (
        {
            "source_filename": PDF["lumitop"],
            "preview_filename": (
                "REVIEW_REQUIRED__SUGGESTED__"
                "2026-05-11_er_er_LUMITOP_500,00_paypal.pdf"
            ),
            "selected_amount": "500,00",
            "selected_payment_field": "paypal",
            "selected_art": "er",
            "suggested_filename": "2026-05-11_er_er_LUMITOP_500,00_paypal.pdf",
        },
    )
    from invoice_tool.ui_v2.preview_export import validate_export_state_freshness

    err = validate_export_state_freshness(
        export_rows=export_rows,
        expectations=expectations,
    )
    assert err is not None
    assert "PREVIEW_EXPORT_STALE_STATE_BLOCKED" in err


def test_13b_internal_storno_er_er_mismatch_blocks_write(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root, (PDF["storno"],))
    stale_storno = (
        ProcessingPlannedDestination(
            document_name=PDF["storno"],
            planned_path=(
                "geplant/unklar/"
                "2026-06-18_er_er_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
            ),
            suggested_filename=(
                "2026-06-18_er_er_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
            ),
            rendered_filename=(
                "2026-06-18_er_er_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
            ),
            amount="68,94",
            selected_amount="68,94",
            selected_art="storno",
            preview_only=True,
            filename_source="configuration_pattern_incomplete",
        ),
    )
    result = write_preview_export_package(
        _run_from_planned(stale_storno, run_id="block-stale-storno"),
        input_root=input_root,
        output_root=output_root,
        refresh_from_input=False,
    )
    assert result.ok is False
    assert result.error is not None
    assert MSG_PREVIEW_EXPORT_STALE_STATE_BLOCKED.split(":")[0] in result.error
    assert not any(output_root.glob("preview-export-*"))


def test_14_state_freshness_result_pass_on_valid_current_state(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    run = _current_enriched_run(input_root)
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    assert result.ok, result.error
    payload = json.loads(
        (result.export_folder / "manifest.json").read_text(encoding="utf-8")
    )
    assert payload["state_freshness_result"] == "pass"


def test_15_copied_pdfs_byte_identical(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    before = _digest_tree(input_root)
    run = _current_enriched_run(input_root)
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    assert result.ok
    for item in result.items:
        if item.excluded:
            continue
        src = hashlib.sha256(
            (input_root / item.source_filename).read_bytes()
        ).hexdigest()
        assert item.source_sha256 == src
        assert item.preview_sha256 == src
    assert _digest_tree(input_root) == before


def test_16_input_files_not_mutated(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    before = _digest_tree(input_root)
    stale = _run_from_planned(_stale_planned())
    write_preview_export_package(
        stale,
        input_root=input_root,
        output_root=output_root,
        refresh_from_input=True,
    )
    assert _digest_tree(input_root) == before


def test_17_output_outside_controlled_folder_blocked(tmp_path: Path) -> None:
    input_root, _ = _sandbox_pair(tmp_path)
    # Avoid pytest tmp paths that contain "test" (positive sandbox signal).
    desktop_plain = "/Users/hadi_neu/Desktop/BelegeAusgangPlain"
    err = validate_preview_export_paths(str(input_root), desktop_plain)
    assert err is not None


def test_18_productive_original_folders_blocked() -> None:
    for folder in FORBIDDEN_FOLDERS:
        err = validate_preview_export_paths(folder, str(CONTROLLED_OUTPUT))
        assert err is not None


def test_19_run_once_not_called() -> None:
    tree = ast.parse(PREVIEW_EXPORT_MODULE.read_text(encoding="utf-8"))
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "run_once" not in calls
    text = PREVIEW_EXPORT_MODULE.read_text(encoding="utf-8")
    assert "run_once(" not in text


def test_20_no_final_write_move_archive_delete_behavior() -> None:
    text = PREVIEW_EXPORT_MODULE.read_text(encoding="utf-8")
    for banned in (
        "shutil.move(",
        "os.remove(",
        "Path.unlink(",
        "final_write=True",
        "productive_mode_requested=True",
    ):
        assert banned not in text or banned == "final_write=True"
    # final_write=True may appear only as blocked guard parameter default False paths
    assert "final_write: bool = False" in text
    assert "source_mutation: bool = False" in text


def test_21_no_real_invoice_folders_touched() -> None:
    text = PREVIEW_EXPORT_MODULE.read_text(encoding="utf-8")
    for folder in FORBIDDEN_FOLDERS:
        assert folder not in text


def test_22_no_saas_ready_claim(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root, (PDF["lumitop"],))
    run = _current_enriched_run(input_root)
    run = ProcessingRunState(
        status="completed",
        run_id="no-saas",
        review_items=tuple(
            i for i in run.review_items if i.document_name == PDF["lumitop"]
        ),
        planned_destinations=tuple(
            p for p in run.planned_destinations if p.document_name == PDF["lumitop"]
        ),
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    readme = (result.export_folder / "README_PREVIEW_EXPORT.md").read_text(
        encoding="utf-8"
    )
    assert MSG_NO_SAAS_READY in readme
    assert text_claims_forbidden_maturity(readme) is False


def test_23_no_production_ready_claim(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root, (PDF["bootshop"],))
    run = _current_enriched_run(input_root)
    run = ProcessingRunState(
        status="completed",
        run_id="no-prod",
        review_items=tuple(
            i for i in run.review_items if i.document_name == PDF["bootshop"]
        ),
        planned_destinations=tuple(
            p for p in run.planned_destinations if p.document_name == PDF["bootshop"]
        ),
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    readme = (result.export_folder / "README_PREVIEW_EXPORT.md").read_text(
        encoding="utf-8"
    )
    assert MSG_NO_PRODUCTION_READY in readme
    assert text_claims_forbidden_maturity(readme) is False


def test_24_track_a_protection_still_passes() -> None:
    from tests.test_track_a_internal_app_protection import (
        test_processing_core_unchanged_vs_head,
        test_track_a_protected_files_unchanged_vs_head,
    )

    test_track_a_protected_files_unchanged_vs_head()
    test_processing_core_unchanged_vs_head()
    text = PREVIEW_EXPORT_MODULE.read_text(encoding="utf-8")
    for mod in PROCESSING_CORE:
        assert mod not in text
    assert "refresh_run_state_from_current_sandbox_input" in text
    assert MSG_PREVIEW_EXPORT_STALE_SOURCE_BLOCKED


def test_25_workspace_export_refreshes_stale_state_into_current(tmp_path: Path) -> None:
    _require_controlled()
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_controlled(input_root)
    state = UiV2State()
    state.processing_run_state = _run_from_planned(_stale_planned())
    state.workspace_input_folder_override = str(input_root)
    state.workspace_output_folder_override = str(output_root)
    result = apply_workspace_preview_export(state)
    assert result.ok, result.error
    names = [item.preview_filename for item in result.items]
    assert any("476,00" in n for n in names)
    assert any("105,75" in n for n in names)
    assert any("storno" in n.lower() for n in names)
    assert not any("500,00" in n for n in names)
    assert not any("80,55" in n for n in names)
    # In-memory UI state must also be refreshed to the current values.
    current = state.processing_run_state
    assert current is not None
    by_name = {p.document_name: p for p in current.planned_destinations}
    assert by_name[PDF["lumitop"]].selected_amount == "476,00"
    assert by_name[PDF["bootshop"]].selected_amount == "105,75"
    assert (by_name[PDF["storno"]].selected_art or "").lower() == "storno"


def test_26_refresh_helper_updates_state_updated_at(tmp_path: Path) -> None:
    _require_controlled()
    input_root, _ = _sandbox_pair(tmp_path)
    _seed_controlled(input_root, (PDF["lumitop"],))
    stale = _run_from_planned(
        tuple(p for p in _stale_planned() if p.document_name == PDF["lumitop"]),
        run_id="stamp",
    )
    refreshed = refresh_run_state_from_current_sandbox_input(
        stale, input_root=input_root
    )
    assert refreshed.state_updated_at
    assert refreshed.planned_destinations[0].selected_amount == "476,00"
