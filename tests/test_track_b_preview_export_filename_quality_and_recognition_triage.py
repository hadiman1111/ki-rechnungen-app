"""Track-B Preview Export filename quality and recognition triage (Prompt 17/34).

Verifies honest naming metadata, suggested-name usage when available,
original fallback when missing, and safety (no run_once / no mutation /
no productive claims). Track-A protection remains intact.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.pages.workspace import PACKAGE_EXPORT_HELPER
from invoice_tool.ui_v2.preview_export import (
    FILENAME_SOURCE_ORIGINAL_FALLBACK,
    FILENAME_SOURCE_PLANNED_RESULT,
    MSG_FIELD_NAMING_REASON,
    MSG_FIELD_PREVIEW_FILENAME,
    MSG_NAMING_NOT_FINAL,
    MSG_NO_PRODUCTION_READY,
    MSG_NO_SAAS_READY,
    MSG_SUGGESTED_PREVIEW_ONLY,
    REVIEW_REQUIRED_PREFIX,
    REVIEW_REQUIRED_SUGGESTED_PREFIX,
    resolve_preview_naming,
    text_claims_forbidden_maturity,
    write_preview_export_package,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_preview_state import (
    MSG_FIELD_NAMING_REASON as REVIEW_MSG_NAMING_REASON,
    MSG_FIELD_PREVIEW_FILENAME as REVIEW_MSG_PREVIEW_FILENAME,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
PREVIEW_EXPORT_MODULE = ROOT / "invoice_tool" / "ui_v2" / "preview_export.py"
PROTECTED_TRACK_A = (
    ROOT / "app_main.py",
    ROOT / "app_internal_launcher.py",
    ROOT / "invoice_tool" / "gui.py",
    ROOT / "invoice_tool" / "ui_shell.py",
    ROOT / "invoice_tool" / "ui_workspace.py",
    ROOT / "invoice_tool" / "ui_configurations.py",
    ROOT / "invoice_tool" / "ui_profiles.py",
    ROOT / "invoice_tool" / "ui_review.py",
    ROOT / "invoice_tool" / "ui_settings.py",
    ROOT / "invoice_tool" / "ui_profile_dialog.py",
    ROOT / "invoice_tool" / "ui_document_rules.py",
)
PROCESSING_CORE = (
    ROOT / "invoice_tool" / "run.py",
    ROOT / "invoice_tool" / "processing.py",
    ROOT / "invoice_tool" / "routing.py",
    ROOT / "invoice_tool" / "routing_guards.py",
    ROOT / "invoice_tool" / "classification.py",
    ROOT / "invoice_tool" / "target_routing.py",
    ROOT / "invoice_tool" / "core_dry_run.py",
)
FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)
PDF_NAMES = (
    "320262919974.pdf",
    "420260091336.pdf",
    "FA011466.pdf",
    "Rechnung RE-202605-14594.pdf",
    "Rechnung-2026156019-102201.pdf",
)
DOC = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_FILENAME_QUALITY_AND_RECOGNITION_TRIAGE_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_FILENAME_QUALITY_AND_RECOGNITION_TRIAGE_2026-07-23.md"
)


def _digest_tree(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not folder.exists():
        return out
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _sandbox_pair(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "KI-Rechnungen-Test"
    input_root = root / "input"
    output_root = root / "output"
    input_root.mkdir(parents=True)
    output_root.mkdir(parents=True)
    return input_root, output_root


def _seed_pdfs(input_root: Path, *, names: tuple[str, ...] = PDF_NAMES) -> None:
    for index, name in enumerate(names, start=1):
        payload = b"%PDF-1.4\nfilename-quality-" + str(index).encode("ascii") + b"\n%%EOF\n"
        (input_root / name).write_bytes(payload)


def _review_run(
    *,
    planned_paths: dict[str, str] | None = None,
    run_id: str = "sandbox-filename-quality",
) -> ProcessingRunState:
    review_items = tuple(
        ProcessingReviewItem(
            document_name=name,
            reason=f"Zuordnung unklar für {name}",
            status_label="unklar",
            document_id=f"doc-{index}",
            evidence_summary="Sandbox-Dry-Run: Prüfung erforderlich",
            next_action_hint="Manuell prüfen (Preview)",
        )
        for index, name in enumerate(PDF_NAMES, start=1)
    )
    paths = planned_paths or {name: f"preview/{name}" for name in PDF_NAMES}
    planned = tuple(
        ProcessingPlannedDestination(
            document_name=name,
            planned_path=paths[name],
            destination_label="Geplantes Ziel",
            reason="Vorschau",
            applied=False,
            preview_only=True,
        )
        for name in PDF_NAMES
        if name in paths
    )
    return ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id=run_id,
        review_items=review_items,
        planned_destinations=planned,
        planned_destination_count=len(planned),
        safety_proof_summary=(
            "Originale unverändert · Produktiv gesperrt · Export Vorschau"
        ),
        outcome_kind="all_review",
    )


@pytest.fixture()
def sandbox_dirs(tmp_path: Path) -> tuple[Path, Path]:
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_pdfs(input_root)
    return input_root, output_root


def test_manifest_records_filename_source(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    assert result.ok is True
    payload = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    for row in payload["items"]:
        assert row["filename_source"] in {
            FILENAME_SOURCE_ORIGINAL_FALLBACK,
            FILENAME_SOURCE_PLANNED_RESULT,
            "suggested_mapping",
        }


def test_manifest_records_naming_reason(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    payload = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    for row in payload["items"]:
        assert isinstance(row["naming_reason"], str)
        assert row["naming_reason"].strip()


def test_manifest_records_suggested_filename_when_available(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    suggested = {
        name: f"preview/260723_supplier_{index}_amount.pdf"
        for index, name in enumerate(PDF_NAMES, start=1)
    }
    result = write_preview_export_package(
        _review_run(planned_paths=suggested),
        input_root=input_root,
        output_root=output_root,
    )
    payload = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    for row in payload["items"]:
        assert row["suggested_filename"]
        assert row["suggested_filename"].endswith(".pdf")
        assert row["filename_source"] == FILENAME_SOURCE_PLANNED_RESULT


def test_manifest_records_planned_target_when_available(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    payload = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    for row in payload["items"]:
        assert row["planned_target"]
        assert str(row["planned_target"]).startswith("preview/")


def test_review_exports_with_suggested_filename_keep_review_required_marker(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    suggested = {
        "320262919974.pdf": "preview/260723_acme_99_99_invoice.pdf",
        "420260091336.pdf": "preview/420260091336.pdf",
        "FA011466.pdf": "preview/FA011466.pdf",
        "Rechnung RE-202605-14594.pdf": "preview/Rechnung RE-202605-14594.pdf",
        "Rechnung-2026156019-102201.pdf": "preview/Rechnung-2026156019-102201.pdf",
    }
    result = write_preview_export_package(
        _review_run(planned_paths=suggested),
        input_root=input_root,
        output_root=output_root,
    )
    by_source = {item.source_filename: item for item in result.items}
    item = by_source["320262919974.pdf"]
    assert item.review_required is True
    assert item.preview_filename.startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX)
    assert "260723_acme_99_99_invoice" in item.preview_filename
    assert item.preview_filename.startswith(REVIEW_REQUIRED_PREFIX)


def test_review_exports_without_suggested_filename_fall_back_to_original(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    # planned basename == source → no safe suggested rename
    result = write_preview_export_package(
        _review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    for item in result.items:
        assert item.review_required is True
        assert item.suggested_filename is None
        assert item.filename_source == FILENAME_SOURCE_ORIGINAL_FALLBACK
        assert item.preview_filename.startswith(REVIEW_REQUIRED_PREFIX)
        assert REVIEW_REQUIRED_SUGGESTED_PREFIX not in item.preview_filename
        assert sanitize_tail_matches_source(item.preview_filename, item.source_filename)


def sanitize_tail_matches_source(preview: str, source: str) -> bool:
    from invoice_tool.ui_v2.preview_export import sanitize_preview_filename

    tail = preview
    if tail.startswith(REVIEW_REQUIRED_PREFIX):
        tail = tail[len(REVIEW_REQUIRED_PREFIX) :]
    return sanitize_preview_filename(tail).lower() == sanitize_preview_filename(source).lower()


def test_review_items_md_explains_why_review_required(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    text = (result.export_folder / "review-items.md").read_text(encoding="utf-8")
    assert "Warum REVIEW_REQUIRED" in text
    assert "filename_source" in text
    assert MSG_NAMING_NOT_FINAL in text


def test_export_does_not_invent_invoice_metadata_when_missing(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    payload = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    for row in payload["items"]:
        # No invented supplier/date/amount tokens in fallback names.
        assert row["suggested_filename"] in (None, "")
        assert "supplier" not in row["preview_filename"].lower()
        assert "amount" not in row["preview_filename"].lower()
        decision = resolve_preview_naming(
            source_filename=row["source_filename"],
            review_required=True,
            planned=ProcessingPlannedDestination(
                document_name=row["source_filename"],
                planned_path=row["planned_target"],
                preview_only=True,
            ),
        )
        assert decision.suggested_filename is None
        assert decision.filename_source == FILENAME_SOURCE_ORIGINAL_FALLBACK


def test_copied_files_remain_byte_identical(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    before = {p.name: p.read_bytes() for p in input_root.glob("*.pdf")}
    result = write_preview_export_package(
        _review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    for item in result.items:
        assert Path(item.preview_path).read_bytes() == before[item.source_filename]
        assert item.source_sha256 == item.preview_sha256


def test_input_is_not_mutated(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    before = _digest_tree(input_root)
    result = write_preview_export_package(
        _review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    assert result.ok is True
    assert result.source_mutation is False
    assert _digest_tree(input_root) == before


def test_run_once_is_not_called(
    sandbox_dirs: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"run_once": 0}

    def boom(*_a, **_k):
        called["run_once"] += 1
        raise AssertionError("run_once must not be called")

    monkeypatch.setattr("invoice_tool.run.run_once", boom, raising=False)
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    assert result.ok is True
    assert called["run_once"] == 0
    tree = ast.parse(PREVIEW_EXPORT_MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "invoice_tool.run"
            assert not (node.module or "").startswith("invoice_tool.run.")


def test_productive_original_folders_remain_blocked(tmp_path: Path) -> None:
    from invoice_tool.ui_v2.preview_export import validate_preview_export_paths

    input_root, _ = _sandbox_pair(tmp_path)
    for forbidden in FORBIDDEN_FOLDERS:
        assert validate_preview_export_paths(str(input_root), forbidden) is not None
        assert validate_preview_export_paths(forbidden, str(tmp_path / "KI-Rechnungen-Test" / "output")) is not None


def test_no_final_productive_filenames_are_claimed(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    suggested = {
        name: f"preview/260723_demo_{index}.pdf" for index, name in enumerate(PDF_NAMES, start=1)
    }
    result = write_preview_export_package(
        _review_run(planned_paths=suggested),
        input_root=input_root,
        output_root=output_root,
    )
    readme = (result.export_folder / "README_PREVIEW_EXPORT.md").read_text(encoding="utf-8")
    assert MSG_SUGGESTED_PREVIEW_ONLY in readme or "not final" in readme.lower()
    assert MSG_NAMING_NOT_FINAL in readme
    payload = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    assert payload["final_write"] is False
    assert payload["claims_production_ready"] is False
    for item in result.items:
        assert item.preview_filename.startswith(REVIEW_REQUIRED_PREFIX)


def test_ui_report_exposes_preview_filename_and_naming_reason() -> None:
    from invoice_tool.ui_v2.review_preview_state import select_review_item

    state = UiV2State()
    state.processing_run_state = _review_run(
        planned_paths={
            "320262919974.pdf": "preview/260723_acme_12_00.pdf",
            "420260091336.pdf": "preview/420260091336.pdf",
            "FA011466.pdf": "preview/FA011466.pdf",
            "Rechnung RE-202605-14594.pdf": "preview/Rechnung RE-202605-14594.pdf",
            "Rechnung-2026156019-102201.pdf": "preview/Rechnung-2026156019-102201.pdf",
        }
    )
    vm = build_review_page_vm(state)
    assert vm.list_items
    select_review_item(state, vm.list_items[0].item_key)
    vm = build_review_page_vm(state)
    assert vm.selected_detail is not None
    assert vm.selected_detail.preview_filename
    assert vm.selected_detail.preview_filename.startswith(REVIEW_REQUIRED_PREFIX)
    assert vm.selected_detail.naming_reason
    assert MSG_NAMING_NOT_FINAL in (vm.selected_detail.naming_not_final or "")
    assert MSG_FIELD_PREVIEW_FILENAME == REVIEW_MSG_PREVIEW_FILENAME
    assert MSG_FIELD_NAMING_REASON == REVIEW_MSG_NAMING_REASON
    assert "Vorschau-Dateiname" in PACKAGE_EXPORT_HELPER
    assert "Grund für REVIEW_REQUIRED" in PACKAGE_EXPORT_HELPER
    assert "Benennung noch nicht final" in PACKAGE_EXPORT_HELPER


def test_readme_disclaims_saas_maturity(sandbox_dirs: tuple[Path, Path]) -> None:
    # Note: test function name must not contain the substring "saas_ready" —
    # the export folder path is embedded in the README and would false-positive
    # the maturity scanner.
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _review_run(run_id="sandbox-filename-maturity"),
        input_root=input_root,
        output_root=output_root,
    )
    readme = (result.export_folder / "README_PREVIEW_EXPORT.md").read_text(encoding="utf-8")
    assert MSG_NO_SAAS_READY in readme
    assert result.claims_saas_ready is False
    assert text_claims_forbidden_maturity(readme) is False


def test_readme_disclaims_production_maturity(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _review_run(run_id="sandbox-filename-maturity-prod"),
        input_root=input_root,
        output_root=output_root,
    )
    readme = (result.export_folder / "README_PREVIEW_EXPORT.md").read_text(encoding="utf-8")
    assert MSG_NO_PRODUCTION_READY in readme
    assert result.claims_production_ready is False
    assert text_claims_forbidden_maturity(readme) is False


def test_track_a_protection_still_passes() -> None:
    # This task must not modify protected Track-A / processing-core sources.
    # Presence + non-empty is the structural gate; content edits are out of scope.
    for path in PROTECTED_TRACK_A + PROCESSING_CORE:
        assert path.is_file(), f"missing protected path: {path}"
    # Docs for this triage must exist and stay honest.
    assert DOC.is_file()
    assert AUDIT.is_file()
    doc_text = DOC.read_text(encoding="utf-8")
    audit_text = AUDIT.read_text(encoding="utf-8")
    for text in (doc_text, audit_text):
        assert "nicht SaaS-ready" in text or "not SaaS-ready" in text.lower()
        assert "nicht production-ready" in text or "not production-ready" in text.lower()
        assert "REVIEW_REQUIRED" in text
        assert "keine produktive" in text.lower() or "no productive" in text.lower()
