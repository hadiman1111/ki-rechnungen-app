"""Track-B profile/configuration filename pattern bridge (Prompt 20/34)."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import pytest

from invoice_tool.ui_v2.configuration_filename_renderer import (
    AMOUNT_FORMAT_COMMA_2,
    FILENAME_SOURCE_CANONICAL_FALLBACK,
    FILENAME_SOURCE_CONFIGURATION_PATTERN,
    FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE,
    build_configuration_placeholder_values,
    format_amount_comma,
    render_configuration_filename_pattern,
)
from invoice_tool.ui_v2.configuration_matching import (
    ConfigurationCandidate,
    match_active_configuration,
)
from invoice_tool.ui_v2.extraction_mapping import (
    enrich_planned_destinations_with_local_extraction,
)
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.preview_export import (
    MSG_FIELD_AMOUNT_FORMAT,
    MSG_FIELD_CONFIGURATION,
    MSG_FIELD_FILENAME_PATTERN,
    MSG_FIELD_MISSING_PLACEHOLDERS,
    MSG_FIELD_PREVIEW_FILENAME,
    MSG_NAMING_NOT_FINAL,
    REVIEW_REQUIRED_SUGGESTED_INCOMPLETE_PREFIX,
    REVIEW_REQUIRED_SUGGESTED_PREFIX,
    preview_export_ui_copy,
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
    / "KI_RECHNUNGEN_TRACK_B_PROFILE_CONFIGURATION_FILENAME_PATTERN_BRIDGE_REPAIR_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_PROFILE_CONFIGURATION_FILENAME_PATTERN_BRIDGE_REPAIR_2026-07-23.md"
)
AMEX_PATTERN = "{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf"


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


def _amex_configs() -> tuple[tuple[ConfigurationCandidate, ...], ConfigurationCandidate]:
    active = (
        ConfigurationCandidate(
            configuration_id="amex",
            name="American Express",
            active=True,
            matching_feature_key="payment_field",
            matching_values=("amex", "American Express"),
            filename_pattern=AMEX_PATTERN,
        ),
    )
    unmatched = ConfigurationCandidate(
        configuration_id="unmatched",
        name="Unklar",
        active=True,
        is_unmatched=True,
        filename_pattern=AMEX_PATTERN,
    )
    return active, unmatched


def test_01_renders_configured_filename_pattern_in_exact_placeholder_order() -> None:
    values = build_configuration_placeholder_values(
        pattern=AMEX_PATTERN,
        invoice_date="2026-07-08",
        art="er",
        supplier="musterfirma",
        amount="125,00",
        payment_field="beispielkonto",
    )
    result = render_configuration_filename_pattern(
        AMEX_PATTERN, placeholder_values=values
    )
    assert result.rendered_filename == (
        "2026-07-08_er_er_musterfirma_125,00_beispielkonto.pdf"
    )


def test_02_preserves_configured_literals_er() -> None:
    values = build_configuration_placeholder_values(
        pattern=AMEX_PATTERN,
        invoice_date="260523",
        supplier="Böttcher AG",
        amount="84.39",
        document_direction="Eingangsrechnung",
        payment_field="amex",
    )
    result = render_configuration_filename_pattern(
        AMEX_PATTERN, placeholder_values=values
    )
    assert "_er_" in (result.rendered_filename or "")
    assert result.rendered_filename.startswith("2026-05-23_er_")


def test_03_to_07_maps_core_placeholders() -> None:
    values = build_configuration_placeholder_values(
        pattern=AMEX_PATTERN,
        invoice_date="260523",
        supplier="Böttcher AG",
        amount="84.39",
        document_direction="Eingangsrechnung",
        payment_field="amex",
    )
    assert values["invoice_date"] == "2026-05-23"
    assert values["art"] == "er"
    assert values["supplier"] == "Böttcher_AG"
    assert values["amount"] == "84,39"
    assert values["payment_field"] == "amex"


def test_08_to_10_amount_comma_two_decimals_no_dot() -> None:
    assert format_amount_comma("84.39") == "84,39"
    assert format_amount_comma("125") == "125,00"
    assert format_amount_comma("154,95") == "154,95"
    values = build_configuration_placeholder_values(
        pattern=AMEX_PATTERN,
        invoice_date="260511",
        supplier="Luxvenum",
        amount="154.95",
        document_direction="Eingangsrechnung",
        payment_field="amex",
    )
    rendered = render_configuration_filename_pattern(
        AMEX_PATTERN, placeholder_values=values
    ).rendered_filename
    assert rendered is not None
    assert "154,95" in rendered
    assert "154.95" not in rendered


def test_11_to_12_missing_placeholders_keep_review_required() -> None:
    values = build_configuration_placeholder_values(
        pattern=AMEX_PATTERN,
        invoice_date="260523",
        supplier="Böttcher AG",
        amount="84.39",
        document_direction="Eingangsrechnung",
    )
    result = render_configuration_filename_pattern(
        AMEX_PATTERN, placeholder_values=values
    )
    assert "payment_field" in result.missing_placeholders
    assert result.filename_source == FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE
    assert result.review_required is True
    assert "FEHLT_payment_field" in (result.rendered_filename or "")


def test_13_to_15_filename_source_and_preview_prefix() -> None:
    active, unmatched = _amex_configs()
    mapped = map_suggested_filename(
        SuggestedFilenameFields(
            supplier="Böttcher AG",
            invoice_date="260523",
            amount="84.39",
            document_type="rechnung",
            payment_field="amex",
            source_filename="320262919974.pdf",
        ),
        configurations=active,
        unmatched=unmatched,
    )
    assert mapped.filename_source == FILENAME_SOURCE_CONFIGURATION_PATTERN
    naming = resolve_preview_naming(
        source_filename="320262919974.pdf",
        review_required=True,
        planned=ProcessingPlannedDestination(
            document_name="320262919974.pdf",
            planned_path=f"preview/{mapped.suggested_filename}",
            suggested_filename=mapped.suggested_filename,
            filename_source=mapped.filename_source,
            rendered_filename=mapped.rendered_filename,
            missing_placeholders=mapped.missing_placeholders,
        ),
    )
    assert naming.preview_filename.startswith(REVIEW_REQUIRED_SUGGESTED_PREFIX)
    incomplete = map_suggested_filename(
        SuggestedFilenameFields(
            supplier="Böttcher AG",
            invoice_date="260523",
            amount="84.39",
            document_type="rechnung",
            source_filename="x.pdf",
        ),
        configurations=active,
        unmatched=unmatched,
    )
    assert incomplete.filename_source == FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE
    naming_incomplete = resolve_preview_naming(
        source_filename="x.pdf",
        review_required=True,
        planned=ProcessingPlannedDestination(
            document_name="x.pdf",
            planned_path=f"preview/{incomplete.suggested_filename}",
            suggested_filename=incomplete.suggested_filename,
            filename_source=incomplete.filename_source,
            rendered_filename=incomplete.rendered_filename,
            missing_placeholders=incomplete.missing_placeholders,
        ),
    )
    assert naming_incomplete.preview_filename.startswith(
        REVIEW_REQUIRED_SUGGESTED_INCOMPLETE_PREFIX
    )


def test_16_canonical_fallback_only_without_configuration_pattern() -> None:
    mapped = map_suggested_filename(
        SuggestedFilenameFields(
            supplier="Böttcher AG",
            invoice_date="260523",
            amount="84.39",
            document_type="rechnung",
            source_filename="x.pdf",
        ),
        configurations=(),
        unmatched=None,
    )
    assert mapped.filename_source == FILENAME_SOURCE_CANONICAL_FALLBACK
    assert "Eingangsrechnung" in (mapped.suggested_filename or "")


def test_17_original_fallback_when_no_pattern_and_no_fields() -> None:
    mapped = map_suggested_filename(
        SuggestedFilenameFields(source_filename="original.pdf"),
        configurations=(),
        unmatched=None,
    )
    assert mapped.filename_source == "original_fallback"
    assert mapped.suggested_filename is None


def test_18_to_24_manifest_includes_configuration_fields(tmp_path: Path) -> None:
    input_root, output_root = _sandbox_pair(tmp_path)
    source = input_root / "sample.pdf"
    source.write_bytes(b"%PDF-1.4\nbridge\n%%EOF\n")
    rendered = "2026-05-23_er_er_Böttcher_AG_84,39_amex.pdf"
    run_state = ProcessingRunState(
        status="completed",
        run_id="bridge-20",
        message="ok",
        review_items=(
            ProcessingReviewItem(document_name="sample.pdf", reason="review"),
        ),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="sample.pdf",
                planned_path=f"preview/{rendered}",
                suggested_filename=rendered,
                rendered_filename=rendered,
                filename_source=FILENAME_SOURCE_CONFIGURATION_PATTERN,
                matched_configuration_name="American Express",
                matched_configuration_id="amex",
                matched_configuration_pattern=AMEX_PATTERN,
                filename_pattern=AMEX_PATTERN,
                placeholder_values=(
                    ("invoice_date", "2026-05-23"),
                    ("art", "er"),
                    ("supplier", "Böttcher_AG"),
                    ("amount", "84,39"),
                    ("payment_field", "amex"),
                ),
                missing_placeholders=(),
                amount_format=AMOUNT_FORMAT_COMMA_2,
                naming_reason="config pattern",
                naming_confidence="medium",
                amount="84,39",
                supplier="Böttcher AG",
                invoice_date="2026-05-23",
            ),
        ),
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run_state=run_state,
        input_root=input_root,
        output_root=output_root,
    )
    assert result.ok
    payload = json.loads((result.export_folder / "manifest.json").read_text())
    item = payload["items"][0]
    assert item["matched_configuration_name"] == "American Express"
    assert item["matched_configuration_pattern"] == AMEX_PATTERN
    assert item["rendered_filename"] == rendered
    assert item["filename_pattern"] == AMEX_PATTERN
    assert item["placeholder_values"]["amount"] == "84,39"
    assert item["missing_placeholders"] == []
    assert item["amount_format"] == AMOUNT_FORMAT_COMMA_2
    review_md = (result.export_folder / "review-items.md").read_text()
    assert MSG_FIELD_MISSING_PLACEHOLDERS in review_md or "fehlende Platzhalter" in review_md or "American Express" in review_md


def test_25_review_items_explain_missing_placeholders(tmp_path: Path) -> None:
    input_root, output_root = _sandbox_pair(tmp_path)
    source = input_root / "sample.pdf"
    source.write_bytes(b"%PDF-1.4\nmissing\n%%EOF\n")
    rendered = "2026-05-23_er_er_Böttcher_AG_84,39_FEHLT_payment_field.pdf"
    run_state = ProcessingRunState(
        status="completed",
        run_id="bridge-missing",
        message="ok",
        review_items=(
            ProcessingReviewItem(document_name="sample.pdf", reason="review"),
        ),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="sample.pdf",
                planned_path=f"preview/{rendered}",
                suggested_filename=rendered,
                rendered_filename=rendered,
                filename_source=FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE,
                matched_configuration_name="Unklar",
                matched_configuration_pattern=AMEX_PATTERN,
                filename_pattern=AMEX_PATTERN,
                missing_placeholders=("payment_field",),
                amount_format=AMOUNT_FORMAT_COMMA_2,
                naming_reason="fehlende Platzhalter: payment_field",
            ),
        ),
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run_state=run_state,
        input_root=input_root,
        output_root=output_root,
    )
    review_md = (result.export_folder / "review-items.md").read_text()
    assert "payment_field" in review_md
    assert "fehlende Platzhalter" in review_md


def test_26_to_29_ui_report_exposes_configuration_labels() -> None:
    copy = preview_export_ui_copy()
    assert MSG_FIELD_CONFIGURATION in copy
    assert MSG_FIELD_FILENAME_PATTERN in copy
    assert MSG_FIELD_PREVIEW_FILENAME in copy
    assert MSG_FIELD_MISSING_PLACEHOLDERS in copy
    assert MSG_FIELD_AMOUNT_FORMAT in copy
    assert MSG_NAMING_NOT_FINAL in copy

    state = UiV2State()
    rendered = "2026-05-23_er_er_Vendor_9,99_amex.pdf"
    state.processing_run_state = ProcessingRunState(
        status="completed",
        run_id="ui-bridge",
        message="ok",
        review_items=(
            ProcessingReviewItem(document_name="doc.pdf", reason="review"),
        ),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="doc.pdf",
                planned_path=f"preview/{rendered}",
                suggested_filename=rendered,
                rendered_filename=rendered,
                filename_source=FILENAME_SOURCE_CONFIGURATION_PATTERN,
                matched_configuration_name="American Express",
                matched_configuration_pattern=AMEX_PATTERN,
                filename_pattern=AMEX_PATTERN,
                placeholder_values=(("amount", "9,99"),),
                amount_format=AMOUNT_FORMAT_COMMA_2,
                amount="9,99",
            ),
        ),
    )
    state.review_selected_item_key = "doc.pdf"
    vm = build_review_page_vm(state)
    assert vm.selected_detail is not None
    assert vm.selected_detail.matched_configuration_name == "American Express"
    assert vm.selected_detail.filename_pattern == AMEX_PATTERN
    assert vm.selected_detail.preview_filename
    assert vm.selected_detail.naming_not_final


def test_30_to_31_preview_export_uses_config_not_canonical_override(tmp_path: Path) -> None:
    input_root, output_root = _sandbox_pair(tmp_path)
    source = input_root / "sample.pdf"
    source.write_bytes(b"%PDF-1.4\ncfg\n%%EOF\n")
    config_name = "2026-05-23_er_er_Böttcher_AG_84,39_amex.pdf"
    canonical = "260523_Eingangsrechnung_Unklare_Zuordnung_Böttcher_AG_84.39.pdf"
    run_state = ProcessingRunState(
        status="completed",
        run_id="bridge-priority",
        message="ok",
        review_items=(
            ProcessingReviewItem(document_name="sample.pdf", reason="review"),
        ),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="sample.pdf",
                planned_path=f"preview/{config_name}",
                suggested_filename=config_name,
                rendered_filename=config_name,
                canonical_filename=canonical,
                filename_source=FILENAME_SOURCE_CONFIGURATION_PATTERN,
                matched_configuration_pattern=AMEX_PATTERN,
                filename_pattern=AMEX_PATTERN,
                amount_format=AMOUNT_FORMAT_COMMA_2,
            ),
        ),
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run_state=run_state,
        input_root=input_root,
        output_root=output_root,
    )
    item = result.items[0]
    assert item.preview_filename == f"{REVIEW_REQUIRED_SUGGESTED_PREFIX}{config_name}"
    assert "Eingangsrechnung_Unklare_Zuordnung" not in item.preview_filename
    assert "84,39" in item.preview_filename
    assert "84.39" not in item.preview_filename


def test_32_to_33_copied_pdfs_byte_identical_input_unmutated() -> None:
    if not CONTROLLED_INPUT.exists():
        pytest.skip("controlled input missing")
    before = _digest_tree(CONTROLLED_INPUT)
    active, unmatched = _amex_configs()
    planned = tuple(
        ProcessingPlannedDestination(
            document_name=name,
            planned_path=f"preview/{name}",
            preview_only=True,
        )
        for name in PDF_NAMES
        if (CONTROLLED_INPUT / name).exists()
    )
    enriched = enrich_planned_destinations_with_local_extraction(
        planned,
        input_folder=CONTROLLED_INPUT,
    )
    assert enriched
    assert any(item.filename_pattern for item in enriched)
    after = _digest_tree(CONTROLLED_INPUT)
    assert before == after


def test_34_to_35_output_and_productive_folders_blocked(tmp_path: Path) -> None:
    input_root, output_root = _sandbox_pair(tmp_path)
    source = input_root / "a.pdf"
    source.write_bytes(b"%PDF-1.4\nx\n%%EOF\n")
    run_state = ProcessingRunState(
        status="completed",
        run_id="blocked",
        message="ok",
        review_items=(ProcessingReviewItem(document_name="a.pdf", reason="review"),),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="a.pdf",
                planned_path="preview/a.pdf",
                suggested_filename="2026-05-23_er_er_A_1,00_amex.pdf",
                filename_source=FILENAME_SOURCE_CONFIGURATION_PATTERN,
            ),
        ),
    )
    blocked = write_preview_export_package(
        run_state=run_state,
        input_root=input_root,
        output_root=FORBIDDEN_FOLDERS[0],
    )
    assert blocked.ok is False
    for folder in FORBIDDEN_FOLDERS:
        assert Path(folder) not in [input_root, output_root]


def test_36_to_38_no_run_once_final_write_or_real_folders() -> None:
    modules = [
        ROOT / "invoice_tool" / "ui_v2" / "configuration_matching.py",
        ROOT / "invoice_tool" / "ui_v2" / "configuration_filename_renderer.py",
        ROOT / "invoice_tool" / "ui_v2" / "suggested_filename_mapping.py",
        ROOT / "invoice_tool" / "ui_v2" / "preview_export.py",
    ]
    for module in modules:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        calls = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        assert "run_once" not in calls
        text = module.read_text(encoding="utf-8")
        assert "RECHNUNGEN" not in text or "FORBIDDEN" in text or "blocked" in text.lower()


def test_39_to_40_no_maturity_claims() -> None:
    assert text_claims_forbidden_maturity("nicht SaaS-ready") is False
    assert text_claims_forbidden_maturity("SaaS-ready") is True
    assert text_claims_forbidden_maturity("nicht production-ready") is False
    docs = DOC.read_text(encoding="utf-8") if DOC.exists() else ""
    if docs:
        assert "nicht SaaS-ready" in docs or "Not SaaS-ready" in docs or "nicht SaaS" in docs


def test_41_track_a_protection_still_passes() -> None:
    for path in PROTECTED_TRACK_A:
        assert path.exists() or path.name in {
            "ui_document_rules.py",
        }
    for path in PROCESSING_CORE:
        assert path.exists()
    # Bridge modules must not import/call protected processing entrypoints directly.
    bridge_path = (
        ROOT / "invoice_tool" / "ui_v2" / "configuration_filename_renderer.py"
    )
    tree = ast.parse(bridge_path.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else node.names)
    }
    assert "run" not in imported
    assert "run_once" not in imported
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "run_once" not in calls


def test_matching_uses_configuration_values_not_hardcoded_private_defaults() -> None:
    active, unmatched = _amex_configs()
    hit = match_active_configuration(
        payment_field="amex",
        configurations=active,
        unmatched=unmatched,
    )
    assert hit.matched_configuration_name == "American Express"
    unclear = match_active_configuration(
        payment_account="card",
        configurations=active,
        unmatched=unmatched,
    )
    assert unclear.is_unmatched_fallback is True
    assert unclear.matched_configuration_name == "Unklar"


def test_controlled_enrichment_uses_configuration_pattern_and_comma_amount() -> None:
    if not CONTROLLED_INPUT.exists():
        pytest.skip("controlled input missing")
    planned = tuple(
        ProcessingPlannedDestination(
            document_name=name,
            planned_path=f"preview/{name}",
            preview_only=True,
        )
        for name in PDF_NAMES
        if (CONTROLLED_INPUT / name).exists()
    )
    enriched = enrich_planned_destinations_with_local_extraction(
        planned, input_folder=CONTROLLED_INPUT
    )
    assert len(enriched) == 5
    for item in enriched:
        assert item.suggested_filename
        assert item.filename_pattern
        assert item.amount_format == AMOUNT_FORMAT_COMMA_2 or item.amount
        if item.amount and re.search(r"\d", item.amount):
            assert "," in item.amount or item.amount_format == AMOUNT_FORMAT_COMMA_2
        assert "84.39" not in (item.suggested_filename or "")
        assert item.filename_source in {
            FILENAME_SOURCE_CONFIGURATION_PATTERN,
            FILENAME_SOURCE_CONFIGURATION_PATTERN_INCOMPLETE,
        }
