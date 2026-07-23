"""Track-B extraction + suggested filename mapping repair (Prompt 18/34).

Verifies local sandbox extraction → suggested filename mapping → preview export
naming, without productive processing, run_once, or real invoice folders.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from invoice_tool.ui_v2.extraction_mapping import (
    MSG_AI_OCR_NOT_USED,
    assert_safe_sandbox_extraction_root,
    enrich_planned_destinations_with_local_extraction,
    extract_local_fields_from_pdf,
)
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.preview_export import (
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
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.suggested_filename_mapping import (
    FORBIDDEN_SENSITIVE_FIELD_KEYS,
    SuggestedFilenameFields,
    map_suggested_filename,
    render_suggested_filename,
    sanitize_filename_component,
)

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_INPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input")
CONTROLLED_OUTPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output")
FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)
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
    / "KI_RECHNUNGEN_TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_REPAIR_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_REPAIR_2026-07-23.md"
)
MAPPING_MODULE = ROOT / "invoice_tool" / "ui_v2" / "suggested_filename_mapping.py"
EXTRACTION_MODULE = ROOT / "invoice_tool" / "ui_v2" / "extraction_mapping.py"


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


def test_01_suggested_filename_from_structured_fields() -> None:
    result = map_suggested_filename(
        SuggestedFilenameFields(
            supplier="Böttcher AG",
            invoice_date="260523",
            amount="84.39",
            document_type="rechnung",
            source_filename="320262919974.pdf",
        )
    )
    assert result.suggested_filename == (
        "260523_Eingangsrechnung_Unklare_Zuordnung_Böttcher_AG_84.39.pdf"
    )
    assert result.filename_source == "suggested_mapping"
    assert result.naming_confidence in {"medium", "high"}
    assert result.document_direction == "Eingangsrechnung"
    assert result.business_category == "Unklare_Zuordnung"


def test_02_mapping_sanitizes_unsafe_characters() -> None:
    cleaned = sanitize_filename_component('Acme/Corp<>:"|?*')
    assert "/" not in cleaned
    assert ":" not in cleaned
    assert "*" not in cleaned
    rendered = render_suggested_filename(
        SuggestedFilenameFields(
            supplier='Bad/Name<>',
            invoice_date="260101",
            amount="12.00",
        )
    )
    assert rendered is not None
    assert "/" not in rendered
    assert "<" not in rendered
    assert rendered.endswith(".pdf")


def test_03_mapping_rejects_forbidden_sensitive_extra_fields() -> None:
    assert "iban" in FORBIDDEN_SENSITIVE_FIELD_KEYS
    with pytest.raises(ValueError, match="Forbidden sensitive"):
        render_suggested_filename(
            SuggestedFilenameFields(supplier="Acme", invoice_date="260101", amount="1.00"),
            extra_values={"iban": "DE001122"},
        )
    # Allowed mapping still omits IBAN-like values from the default pattern.
    result = map_suggested_filename(
        SuggestedFilenameFields(
            supplier="Acme GmbH",
            invoice_date="260101",
            amount="10.00",
            payment_account="paypal",
        )
    )
    assert result.suggested_filename is not None
    assert "DE00" not in result.suggested_filename
    assert "iban" not in (result.suggested_filename or "").lower()


def test_04_review_keeps_review_required_marker() -> None:
    naming = resolve_preview_naming(
        source_filename="a.pdf",
        review_required=True,
        suggested_filename="260523_Acme_10.00.pdf",
    )
    assert naming.review_required is True
    assert naming.preview_filename.startswith(REVIEW_REQUIRED_PREFIX)


def test_05_suggested_review_uses_suggested_prefix() -> None:
    naming = resolve_preview_naming(
        source_filename="a.pdf",
        review_required=True,
        suggested_filename="260523_Acme_10.00.pdf",
    )
    assert naming.preview_filename.startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX)
    assert naming.suggested_filename == "260523_Acme_10.00.pdf"


def test_06_original_fallback_when_structured_data_missing() -> None:
    result = map_suggested_filename(
        SuggestedFilenameFields(source_filename="original.pdf")
    )
    assert result.suggested_filename is None
    assert result.filename_source == "original_fallback"
    naming = resolve_preview_naming(
        source_filename="original.pdf",
        review_required=True,
        planned=ProcessingPlannedDestination(
            document_name="original.pdf",
            planned_path="preview/original.pdf",
            preview_only=True,
        ),
    )
    assert naming.preview_filename == f"{REVIEW_REQUIRED_PREFIX}original.pdf"
    assert naming.suggested_filename is None


def test_07_to_12_manifest_and_preview_export_suggested_fields(tmp_path: Path) -> None:
    input_root, output_root = _sandbox_pair(tmp_path)
    source = input_root / "invoice.pdf"
    payload = b"%PDF-1.4\nmapping-repair\n%%EOF\n"
    source.write_bytes(payload)
    before = hashlib.sha256(payload).hexdigest()
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen",
        run_id="mapping-repair-export",
        review_items=(
            ProcessingReviewItem(
                document_name="invoice.pdf",
                reason="Prüffall",
                status_label="unklar",
                document_id="doc-1",
            ),
        ),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="invoice.pdf",
                planned_path="preview/260523_Acme_GmbH_12.00.pdf",
                preview_only=True,
                applied=False,
                suggested_filename="260523_Acme_GmbH_12.00.pdf",
                filename_source="suggested_mapping",
                naming_confidence="high",
                naming_reason="Vorschlagsname aus lokalen Extraktionsfeldern",
                supplier="Acme GmbH",
                invoice_date="260523",
                amount="12.00",
                document_type="rechnung",
                suggested_filename_fields=("supplier", "invoice_date", "amount"),
            ),
        ),
        planned_destination_count=1,
        outcome_kind="all_review",
    )
    result = write_preview_export_package(
        run,
        input_root=input_root,
        output_root=output_root,
    )
    assert result.ok
    assert result.export_folder is not None
    manifest = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    item = manifest["items"][0]
    assert item["suggested_filename"] == "260523_Acme_GmbH_12.00.pdf"
    assert item["filename_source"] == "suggested_mapping"
    assert item["naming_confidence"] == "high"
    assert item["naming_reason"]
    assert item["preview_filename"].startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX)
    assert "260523_Acme_GmbH_12.00" in item["preview_filename"]
    review_md = (result.export_folder / "review-items.md").read_text(encoding="utf-8")
    assert "260523_Acme_GmbH_12.00.pdf" in review_md
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_11_review_ui_exposes_suggested_filename() -> None:
    state = UiV2State()
    state.processing_run_state = ProcessingRunState(
        status="completed",
        message="ok",
        run_id="ui-suggest",
        review_items=(
            ProcessingReviewItem(
                document_name="a.pdf",
                reason="unklar",
                status_label="unklar",
                document_id="a",
            ),
        ),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="a.pdf",
                planned_path="preview/260101_Vendor_9.99.pdf",
                suggested_filename="260101_Vendor_9.99.pdf",
                naming_confidence="medium",
                naming_reason="Teilfelder",
                filename_source="suggested_mapping",
                supplier="Vendor",
                invoice_date="260101",
                amount="9.99",
                preview_only=True,
            ),
        ),
        planned_destination_count=1,
        outcome_kind="all_review",
    )
    vm = build_review_page_vm(state)
    assert vm.selected_detail is not None
    assert vm.selected_detail.suggested_filename == "260101_Vendor_9.99.pdf"
    assert vm.selected_detail.preview_filename is not None
    assert vm.selected_detail.preview_filename.startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX)


def test_13_14_copied_pdfs_byte_identical_and_input_not_mutated() -> None:
    assert CONTROLLED_INPUT.is_dir()
    before = _digest_tree(CONTROLLED_INPUT)
    planned = tuple(
        ProcessingPlannedDestination(
            document_name=name,
            planned_path=f"preview/{name}",
            preview_only=True,
        )
        for name in PDF_NAMES
        if (CONTROLLED_INPUT / name).is_file()
    )
    enriched = enrich_planned_destinations_with_local_extraction(
        planned, input_folder=CONTROLLED_INPUT
    )
    assert any(item.suggested_filename for item in enriched)
    after = _digest_tree(CONTROLLED_INPUT)
    assert before == after


def test_15_output_outside_controlled_folder_blocked(tmp_path: Path) -> None:
    input_root, _ = _sandbox_pair(tmp_path)
    (input_root / "a.pdf").write_bytes(b"%PDF-1.4\nx\n%%EOF\n")
    # Hard productive marker path — must never receive preview exports.
    outside = tmp_path / "RECHNUNGEN" / "produktiv-output"
    outside.mkdir(parents=True)
    run = ProcessingRunState(
        status="completed",
        review_items=(ProcessingReviewItem(document_name="a.pdf", reason="x"),),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="a.pdf",
                planned_path="preview/a.pdf",
                preview_only=True,
            ),
        ),
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=outside
    )
    assert result.ok is False


def test_16_productive_original_folders_blocked_for_extraction() -> None:
    for folder in FORBIDDEN_FOLDERS:
        assert assert_safe_sandbox_extraction_root(folder) is not None


def test_17_run_once_not_called_by_mapping_modules() -> None:
    for path in (MAPPING_MODULE, EXTRACTION_MODULE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id != "run_once"
                if isinstance(node.func, ast.Attribute):
                    assert node.func.attr != "run_once"
        text = path.read_text(encoding="utf-8")
        assert "from invoice_tool.run" not in text
        assert "import invoice_tool.run" not in text
        assert "invoice_tool.run.run_once" not in text


def test_18_no_final_write_move_archive_delete_in_modules() -> None:
    for path in (MAPPING_MODULE, EXTRACTION_MODULE):
        text = path.read_text(encoding="utf-8")
        assert "shutil.move" not in text
        assert "os.remove" not in text
        assert "archive_original" not in text
        assert "publish_output_atomically" not in text
        assert "invoice_tool.run.run_once" not in text


def test_19_no_real_invoice_folders_touched_by_enrichment() -> None:
    # Enrichment with forbidden root must be a no-op (no FS writes either way).
    planned = (
        ProcessingPlannedDestination(
            document_name="x.pdf",
            planned_path="preview/x.pdf",
            preview_only=True,
        ),
    )
    out = enrich_planned_destinations_with_local_extraction(
        planned, input_folder=FORBIDDEN_FOLDERS[0]
    )
    assert out[0].suggested_filename is None
    assert out[0].planned_path == "preview/x.pdf"


def test_20_21_no_saas_or_production_ready_claims() -> None:
    for path in (MAPPING_MODULE, EXTRACTION_MODULE, DOC, AUDIT):
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert not text_claims_forbidden_maturity(text)
        lowered = text.lower()
        assert "saas ready" not in lowered
        assert "production ready" not in lowered
        if path.suffix == ".md":
            assert "nicht saas-ready" in lowered
            assert "nicht production-ready" in lowered


def test_22_track_a_protection_still_passes() -> None:
    for path in PROTECTED_TRACK_A:
        assert path.exists() or path.name in {
            "ui_document_rules.py",
            "ui_profile_dialog.py",
        }
    # Core must remain unmodified by this task's intentional edits.
    for path in PROCESSING_CORE:
        assert path.exists()


def test_controlled_five_pdf_local_extraction_meaningful() -> None:
    assert CONTROLLED_INPUT.is_dir()
    before = _digest_tree(CONTROLLED_INPUT)
    meaningful = 0
    for name in PDF_NAMES:
        path = CONTROLLED_INPUT / name
        assert path.is_file()
        result = extract_local_fields_from_pdf(path)
        assert MSG_AI_OCR_NOT_USED in result.warnings
        if result.ok and (result.supplier or result.invoice_date or result.amount):
            mapped = map_suggested_filename(
                SuggestedFilenameFields(
                    supplier=result.supplier,
                    invoice_date=result.invoice_date,
                    amount=result.amount,
                    source_filename=name,
                )
            )
            if mapped.suggested_filename:
                meaningful += 1
                assert mapped.suggested_filename.lower() != name.lower()
    assert meaningful >= 1
    assert _digest_tree(CONTROLLED_INPUT) == before


def test_docs_exist_with_required_status_markers() -> None:
    assert DOC.is_file()
    assert AUDIT.is_file()
    doc_text = DOC.read_text(encoding="utf-8")
    audit_text = AUDIT.read_text(encoding="utf-8")
    assert "KI_RECHNUNGEN_TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_REPAIR_01" in doc_text
    assert "Prompt 18" in doc_text or "18/34" in doc_text
    assert "TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_READY" in audit_text
    assert "nicht SaaS-ready" in doc_text
    assert "nicht production-ready" in doc_text


def test_preview_export_controlled_output_uses_suggested_names(tmp_path: Path) -> None:
    """Optional controlled package write under a temp sandbox mirror of names."""

    if not CONTROLLED_INPUT.is_dir():
        pytest.skip("controlled input missing")
    input_root, output_root = _sandbox_pair(tmp_path)
    before_ctrl = _digest_tree(CONTROLLED_INPUT)
    for name in PDF_NAMES:
        src = CONTROLLED_INPUT / name
        if src.is_file():
            (input_root / name).write_bytes(src.read_bytes())
    planned = enrich_planned_destinations_with_local_extraction(
        tuple(
            ProcessingPlannedDestination(
                document_name=name,
                planned_path=f"preview/{name}",
                preview_only=True,
                applied=False,
            )
            for name in PDF_NAMES
            if (input_root / name).is_file()
        ),
        input_folder=input_root,
    )
    assert any(p.suggested_filename for p in planned)
    run = ProcessingRunState(
        status="completed",
        message="Sandbox enrichment",
        run_id="extract-map-18",
        review_items=tuple(
            ProcessingReviewItem(
                document_name=p.document_name,
                reason="PDF ohne Core-OCR/AI",
                status_label="unklar",
                document_id=f"d-{index}",
            )
            for index, p in enumerate(planned, start=1)
        ),
        planned_destinations=planned,
        planned_destination_count=len(planned),
        outcome_kind="all_review",
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    assert result.ok
    suggested_exports = [
        item
        for item in result.items
        if item.suggested_filename
        and item.preview_filename.startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX)
    ]
    assert len(suggested_exports) >= 1
    assert _digest_tree(CONTROLLED_INPUT) == before_ctrl
