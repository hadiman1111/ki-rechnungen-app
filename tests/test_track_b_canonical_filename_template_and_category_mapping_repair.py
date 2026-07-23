"""Track-B canonical filename template + category mapping (Prompt 19/34)."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import pytest

from invoice_tool.ui_v2.canonical_filename_template import (
    BUSINESS_CATEGORY_ARCHITEKTUR,
    BUSINESS_CATEGORY_UNCLEAR,
    DOCUMENT_DIRECTION_EINGANG,
    DOCUMENT_DIRECTION_UNCLEAR,
    FILENAME_TEMPLATE_VERSION,
    CanonicalFilenameFields,
    build_canonical_filename,
    map_business_category,
    map_document_direction,
    sanitize_filename_component,
)
from invoice_tool.ui_v2.extraction_mapping import (
    enrich_planned_destinations_with_local_extraction,
)
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.preview_export import (
    MSG_FIELD_BUSINESS_CATEGORY,
    MSG_FIELD_DOCUMENT_DIRECTION,
    MSG_FIELD_PREVIEW_FILENAME,
    MSG_NAMING_NOT_FINAL,
    REVIEW_REQUIRED_SUGGESTED_PREFIX,
    SUGGESTED_PREFIX,
    preview_export_ui_copy,
    resolve_preview_naming,
    text_claims_forbidden_maturity,
    write_preview_export_package,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.suggested_filename_mapping import (
    SuggestedFilenameFields,
    map_suggested_filename,
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
    / "KI_RECHNUNGEN_TRACK_B_CANONICAL_FILENAME_TEMPLATE_AND_CATEGORY_MAPPING_REPAIR_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_CANONICAL_FILENAME_TEMPLATE_AND_CATEGORY_MAPPING_REPAIR_2026-07-23.md"
)
CANONICAL_MODULE = ROOT / "invoice_tool" / "ui_v2" / "canonical_filename_template.py"
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


_CANONICAL_RE = re.compile(
    r"^(?P<date>\d{6}|Unklar)_"
    r"(?P<direction>Eingangsrechnung|Ausgangsrechnung|Unklare_Rechnungsart)_"
    r"(?P<category>Architektur|Innenarchitektur|Event_and_Production|Privat|Unklare_Zuordnung)_"
    r"(?P<name>.+)_"
    r"(?P<amount>[0-9]+(?:\.[0-9]+)?|Unklar)\.pdf$"
)


def _strip_preview_prefixes(name: str) -> str:
    stem = name
    for prefix in (
        REVIEW_REQUIRED_SUGGESTED_PREFIX,
        SUGGESTED_PREFIX,
        "REVIEW_REQUIRED__",
    ):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
    return stem


def _canonical_parts(name: str) -> dict[str, str]:
    stem = _strip_preview_prefixes(name)
    match = _CANONICAL_RE.match(stem)
    assert match is not None, f"not canonical: {name}"
    return match.groupdict()


def test_01_canonical_filename_contains_date_first() -> None:
    result = build_canonical_filename(
        CanonicalFilenameFields(
            invoice_date="260523",
            document_direction=DOCUMENT_DIRECTION_EINGANG,
            business_category=BUSINESS_CATEGORY_ARCHITEKTUR,
            counterparty_name="Böttcher AG",
            amount="84.39",
        )
    )
    parts = _canonical_parts(result.canonical_filename)
    assert parts["date"] == "260523"


def test_02_canonical_filename_contains_document_direction_second() -> None:
    result = build_canonical_filename(
        CanonicalFilenameFields(
            invoice_date="260523",
            document_direction=DOCUMENT_DIRECTION_EINGANG,
            business_category=BUSINESS_CATEGORY_ARCHITEKTUR,
            counterparty_name="Böttcher AG",
            amount="84.39",
        )
    )
    parts = _canonical_parts(result.canonical_filename)
    assert parts["direction"] == "Eingangsrechnung"


def test_03_canonical_filename_contains_business_category_third() -> None:
    result = build_canonical_filename(
        CanonicalFilenameFields(
            invoice_date="260523",
            document_direction=DOCUMENT_DIRECTION_EINGANG,
            business_category=BUSINESS_CATEGORY_ARCHITEKTUR,
            counterparty_name="Böttcher AG",
            amount="84.39",
        )
    )
    parts = _canonical_parts(result.canonical_filename)
    assert parts["category"] == "Architektur"


def test_04_canonical_filename_contains_counterparty_fourth() -> None:
    result = build_canonical_filename(
        CanonicalFilenameFields(
            invoice_date="260523",
            document_direction=DOCUMENT_DIRECTION_EINGANG,
            business_category=BUSINESS_CATEGORY_ARCHITEKTUR,
            counterparty_name="Böttcher AG",
            amount="84.39",
        )
    )
    # Name may contain underscores (Böttcher_AG) between category and amount.
    assert result.canonical_filename.startswith(
        "260523_Eingangsrechnung_Architektur_Böttcher"
    )
    assert "_Böttcher_AG_" in result.canonical_filename


def test_05_canonical_filename_contains_amount_last() -> None:
    result = build_canonical_filename(
        CanonicalFilenameFields(
            invoice_date="260523",
            document_direction=DOCUMENT_DIRECTION_EINGANG,
            business_category=BUSINESS_CATEGORY_ARCHITEKTUR,
            counterparty_name="Böttcher AG",
            amount="84.39",
        )
    )
    assert result.canonical_filename.endswith("_84.39.pdf")


def test_06_review_preview_keeps_review_required_suggested_prefix() -> None:
    naming = resolve_preview_naming(
        source_filename="a.pdf",
        review_required=True,
        suggested_filename=(
            "260523_Eingangsrechnung_Architektur_Böttcher_AG_84.39.pdf"
        ),
    )
    assert naming.preview_filename.startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX)


def test_07_recognized_preview_may_use_suggested_prefix_only() -> None:
    naming = resolve_preview_naming(
        source_filename="a.pdf",
        review_required=False,
        suggested_filename=(
            "260523_Eingangsrechnung_Architektur_Acme_10.00.pdf"
        ),
    )
    assert naming.preview_filename.startswith(SUGGESTED_PREFIX)
    assert not naming.preview_filename.startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX)


def test_08_missing_document_direction_becomes_unclear() -> None:
    direction, missing = map_document_direction()
    assert direction == DOCUMENT_DIRECTION_UNCLEAR
    assert missing == "document_direction"
    result = build_canonical_filename(
        CanonicalFilenameFields(
            invoice_date="260101",
            counterparty_name="Acme",
            amount="1.00",
        )
    )
    assert "Unklare_Rechnungsart" in result.canonical_filename


def test_09_missing_business_category_becomes_unclear() -> None:
    category, missing = map_business_category()
    assert category == BUSINESS_CATEGORY_UNCLEAR
    assert missing == "business_category"


def test_10_missing_category_does_not_default_to_architektur() -> None:
    category, _ = map_business_category()
    assert category != BUSINESS_CATEGORY_ARCHITEKTUR
    mapped = map_suggested_filename(
        SuggestedFilenameFields(
            supplier="Böttcher AG",
            invoice_date="260523",
            amount="84.39",
            document_type="rechnung",
        )
    )
    assert mapped.business_category == BUSINESS_CATEGORY_UNCLEAR
    assert "Architektur" not in (mapped.suggested_filename or "")
    assert "Unklare_Zuordnung" in (mapped.suggested_filename or "")


def test_11_filename_sanitization_removes_unsafe_path_characters() -> None:
    cleaned = sanitize_filename_component('Acme/Corp<>:"|?*')
    assert "/" not in cleaned
    assert ":" not in cleaned
    assert "*" not in cleaned
    result = build_canonical_filename(
        CanonicalFilenameFields(
            invoice_date="260101",
            document_direction=DOCUMENT_DIRECTION_EINGANG,
            business_category=BUSINESS_CATEGORY_UNCLEAR,
            counterparty_name='Bad/Name<>',
            amount="12.00",
        )
    )
    assert "/" not in result.canonical_filename
    assert "<" not in result.canonical_filename


def test_12_to_16_manifest_includes_canonical_fields(tmp_path: Path) -> None:
    input_root, output_root = _sandbox_pair(tmp_path)
    source = input_root / "invoice.pdf"
    source.write_bytes(b"%PDF-1.4\ncanonical\n%%EOF\n")
    canonical = "260523_Eingangsrechnung_Unklare_Zuordnung_Acme_GmbH_12.00.pdf"
    run = ProcessingRunState(
        status="completed",
        message="Sandbox",
        run_id="canonical-19",
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
                planned_path=f"preview/{canonical}",
                preview_only=True,
                suggested_filename=canonical,
                canonical_filename=canonical,
                filename_template_version=FILENAME_TEMPLATE_VERSION,
                document_direction=DOCUMENT_DIRECTION_EINGANG,
                business_category=BUSINESS_CATEGORY_UNCLEAR,
                business_category_display="Unklare_Zuordnung",
                counterparty_name="Acme GmbH",
                invoice_date="260523",
                amount="12.00",
                missing_fields=("business_category",),
                filename_source="suggested_mapping",
                naming_confidence="medium",
                naming_reason="Zuordnung unklar → Unklare_Zuordnung",
                supplier="Acme GmbH",
            ),
        ),
        planned_destination_count=1,
        outcome_kind="all_review",
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    assert result.ok
    assert result.export_folder is not None
    manifest = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    item = manifest["items"][0]
    assert item["canonical_filename"] == canonical
    assert item["document_direction"] == DOCUMENT_DIRECTION_EINGANG
    assert item["business_category"] == BUSINESS_CATEGORY_UNCLEAR
    assert item["filename_template_version"] == FILENAME_TEMPLATE_VERSION
    assert "business_category" in item["missing_fields"]
    review_md = (result.export_folder / "review-items.md").read_text(encoding="utf-8")
    assert "Unklare_Zuordnung" in review_md
    assert MSG_FIELD_DOCUMENT_DIRECTION in review_md or "Rechnungsart" in review_md


def test_17_review_items_explains_uncertain_category_or_direction(tmp_path: Path) -> None:
    input_root, output_root = _sandbox_pair(tmp_path)
    (input_root / "a.pdf").write_bytes(b"%PDF-1.4\nx\n%%EOF\n")
    canonical = "260101_Unklare_Rechnungsart_Unklare_Zuordnung_Acme_1.00.pdf"
    run = ProcessingRunState(
        status="completed",
        run_id="unclear-19",
        review_items=(
            ProcessingReviewItem(document_name="a.pdf", reason="unklar", document_id="a"),
        ),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="a.pdf",
                planned_path=f"preview/{canonical}",
                suggested_filename=canonical,
                canonical_filename=canonical,
                document_direction=DOCUMENT_DIRECTION_UNCLEAR,
                business_category=BUSINESS_CATEGORY_UNCLEAR,
                missing_fields=("document_direction", "business_category"),
                naming_reason="Rechnungsart unklar; Zuordnung unklar",
                preview_only=True,
            ),
        ),
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    review_md = (result.export_folder / "review-items.md").read_text(encoding="utf-8")
    assert "Unklare_Rechnungsart" in review_md
    assert "Unklare_Zuordnung" in review_md
    assert "Architektur" not in review_md or "Blind-Default" in review_md


def test_18_to_21_ui_report_exposes_canonical_labels() -> None:
    copy = preview_export_ui_copy()
    assert MSG_FIELD_PREVIEW_FILENAME in copy
    assert MSG_FIELD_DOCUMENT_DIRECTION in copy
    assert MSG_FIELD_BUSINESS_CATEGORY in copy
    assert MSG_NAMING_NOT_FINAL in copy
    state = UiV2State()
    canonical = "260523_Eingangsrechnung_Unklare_Zuordnung_Vendor_9.99.pdf"
    state.processing_run_state = ProcessingRunState(
        status="completed",
        message="ok",
        run_id="ui-canonical",
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
                planned_path=f"preview/{canonical}",
                suggested_filename=canonical,
                canonical_filename=canonical,
                document_direction=DOCUMENT_DIRECTION_EINGANG,
                business_category=BUSINESS_CATEGORY_UNCLEAR,
                business_category_display="Unklare_Zuordnung",
                counterparty_name="Vendor",
                amount="9.99",
                invoice_date="260523",
                naming_confidence="medium",
                naming_reason="kanonisch",
                filename_source="suggested_mapping",
                missing_fields=("business_category",),
                preview_only=True,
            ),
        ),
        planned_destination_count=1,
        outcome_kind="all_review",
    )
    vm = build_review_page_vm(state)
    assert vm.selected_detail is not None
    assert vm.selected_detail.preview_filename is not None
    assert vm.selected_detail.preview_filename.startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX)
    assert vm.selected_detail.document_direction == DOCUMENT_DIRECTION_EINGANG
    assert vm.selected_detail.business_category == BUSINESS_CATEGORY_UNCLEAR
    assert vm.selected_detail.naming_not_final == MSG_NAMING_NOT_FINAL


def test_22_preview_export_uses_canonical_suggested_filename(tmp_path: Path) -> None:
    input_root, output_root = _sandbox_pair(tmp_path)
    (input_root / "src.pdf").write_bytes(b"%PDF-1.4\ny\n%%EOF\n")
    canonical = "260523_Eingangsrechnung_Architektur_Böttcher_AG_84.39.pdf"
    run = ProcessingRunState(
        status="completed",
        run_id="canon-export",
        review_items=(
            ProcessingReviewItem(document_name="src.pdf", reason="x", document_id="1"),
        ),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="src.pdf",
                planned_path=f"preview/{canonical}",
                suggested_filename=canonical,
                canonical_filename=canonical,
                document_direction=DOCUMENT_DIRECTION_EINGANG,
                business_category=BUSINESS_CATEGORY_ARCHITEKTUR,
                preview_only=True,
            ),
        ),
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    assert result.ok
    item = result.items[0]
    assert item.preview_filename == f"{REVIEW_REQUIRED_SUGGESTED_PREFIX}{canonical}"
    assert item.canonical_filename == canonical


def test_23_24_copied_pdfs_byte_identical_and_input_not_mutated() -> None:
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
    assert len(enriched) >= 1
    for item in enriched:
        assert item.suggested_filename
        parts = _canonical_parts(item.suggested_filename)
        assert parts["date"].isdigit() and len(parts["date"]) == 6
        assert parts["direction"] in {
            "Eingangsrechnung",
            "Ausgangsrechnung",
            "Unklare_Rechnungsart",
        }
        assert parts["category"] in {
            "Architektur",
            "Innenarchitektur",
            "Event_and_Production",
            "Privat",
            "Unklare_Zuordnung",
        }
    assert _digest_tree(CONTROLLED_INPUT) == before


def test_25_output_outside_controlled_folder_blocked(tmp_path: Path) -> None:
    input_root, _ = _sandbox_pair(tmp_path)
    (input_root / "a.pdf").write_bytes(b"%PDF-1.4\nx\n%%EOF\n")
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


def test_26_productive_original_folders_remain_blocked() -> None:
    from invoice_tool.ui_v2.extraction_mapping import assert_safe_sandbox_extraction_root

    for folder in FORBIDDEN_FOLDERS:
        assert assert_safe_sandbox_extraction_root(folder) is not None


def test_27_run_once_not_called() -> None:
    for path in (CANONICAL_MODULE, MAPPING_MODULE, EXTRACTION_MODULE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id != "run_once"
                if isinstance(node.func, ast.Attribute):
                    assert node.func.attr != "run_once"
        text = path.read_text(encoding="utf-8")
        assert "invoice_tool.run.run_once" not in text


def test_28_no_final_write_move_archive_delete() -> None:
    for path in (CANONICAL_MODULE, MAPPING_MODULE, EXTRACTION_MODULE):
        text = path.read_text(encoding="utf-8")
        assert "shutil.move" not in text
        assert "os.remove" not in text
        assert "archive_original" not in text
        assert "publish_output_atomically" not in text


def test_29_no_real_invoice_folders_touched() -> None:
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


def test_30_31_no_saas_or_production_ready_claims() -> None:
    for path in (CANONICAL_MODULE, MAPPING_MODULE, DOC, AUDIT):
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert not text_claims_forbidden_maturity(text)
        lowered = text.lower()
        assert "saas ready" not in lowered
        assert "production ready" not in lowered
        if path.suffix == ".md":
            assert "nicht saas-ready" in lowered
            assert "nicht production-ready" in lowered


def test_32_track_a_protection_still_passes() -> None:
    for path in PROTECTED_TRACK_A:
        assert path.exists() or path.name in {
            "ui_document_rules.py",
            "ui_profile_dialog.py",
        }
    for path in PROCESSING_CORE:
        assert path.exists()


def test_explicit_category_mapping_from_routing_label() -> None:
    category, missing = map_business_category(routing_category="Innenarchitektur")
    assert category == "Innenarchitektur"
    assert missing is None
    result = build_canonical_filename(
        CanonicalFilenameFields(
            invoice_date="260523",
            document_direction=DOCUMENT_DIRECTION_EINGANG,
            routing_category="Event and Production",
            counterparty_name="Vendor",
            amount="10.00",
        )
    )
    assert "Event_and_Production" in result.canonical_filename


def test_controlled_preview_export_canonical_names(tmp_path: Path) -> None:
    if not CONTROLLED_INPUT.is_dir():
        pytest.skip("controlled input missing")
    input_root, output_root = _sandbox_pair(tmp_path)
    before = _digest_tree(CONTROLLED_INPUT)
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
            )
            for name in PDF_NAMES
            if (input_root / name).is_file()
        ),
        input_folder=input_root,
    )
    run = ProcessingRunState(
        status="completed",
        message="canonical verify",
        run_id="prompt19-verify",
        review_items=tuple(
            ProcessingReviewItem(
                document_name=p.document_name,
                reason="PDF ohne Core-OCR/AI",
                status_label="unklar",
                document_id=f"d-{i}",
            )
            for i, p in enumerate(planned, start=1)
        ),
        results=tuple(
            ProcessingResultSummary(
                document_name=p.document_name,
                document_type="invoice",
                classification_status="review",
                status_label="unklar",
            )
            for p in planned
        ),
        planned_destinations=planned,
        planned_destination_count=len(planned),
        outcome_kind="all_review",
    )
    result = write_preview_export_package(
        run, input_root=input_root, output_root=output_root
    )
    assert result.ok
    for item in result.items:
        assert item.preview_filename.startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX)
        assert item.canonical_filename
        assert item.document_direction
        assert item.business_category
        assert item.filename_template_version == FILENAME_TEMPLATE_VERSION
        parts = _canonical_parts(item.preview_filename)
        assert parts["date"].isdigit()
        assert parts["direction"] in {
            "Eingangsrechnung",
            "Ausgangsrechnung",
            "Unklare_Rechnungsart",
        }
        assert parts["category"] in {
            "Architektur",
            "Innenarchitektur",
            "Event_and_Production",
            "Privat",
            "Unklare_Zuordnung",
        }
    assert _digest_tree(CONTROLLED_INPUT) == before
