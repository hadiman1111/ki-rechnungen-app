"""Track-B Filename Pattern Builder + Safe Planned Filename Editing (2026-07-27)."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.configuration_model import FilenameComponent, FilenamePattern
from invoice_tool.scan_models import get_scan_model
from invoice_tool.ui_v2.filename_pattern import (
    FILENAME_PATTERN_SAFE_EDIT_MARKER,
    MSG_EMPTY_CUSTOM,
    MSG_ER_ER_DUPLICATION,
    add_custom_text_component,
    filename_has_er_er_duplication,
    rebuild_planned_filename_from_fields,
    sanitize_custom_text,
    strip_er_custom_when_art_present,
    supported_block_catalog,
    validate_pattern_product_rules,
    validate_planned_filename_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "invoice_tool" / "ui_v2" / "filename_builder.py"
PATTERN = ROOT / "invoice_tool" / "ui_v2" / "filename_pattern.py"
CONFIGS = ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py"
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
DOC = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_FILENAME_PATTERN_BUILDER_AND_SAFE_EDITING_2026-07-27.md"
)


def test_01_builder_supports_eigener_text() -> None:
    src = BUILDER.read_text(encoding="utf-8")
    assert "Eigener Text" in src
    assert "add_custom_text_component" in src
    pattern = FilenamePattern(
        components=[
            FilenameComponent(type="feature", key="invoice_date", label="Datum"),
            FilenameComponent(type="system", key="extension", label="Dateityp"),
        ]
    )
    updated = add_custom_text_component(pattern, "Notiz")
    customs = [
        c for c in updated.components if c.key == "custom_text"
    ]
    assert customs and customs[0].custom_text == "Notiz"


def test_02_plus_dropdown_can_add_block() -> None:
    src = BUILDER.read_text(encoding="utf-8")
    assert "plus_dropdown_add" in src
    assert "Baustein hinzufügen" in src
    assert "on_select" in src


def test_03_unsupported_blocks_filtered_by_catalog() -> None:
    model = get_scan_model("rechnungen")
    catalog = supported_block_catalog(model)
    keys = {item.get("key") for item in catalog}
    assert "extension" not in keys
    assert "custom_text" in keys


def test_04_live_preview_label() -> None:
    src = BUILDER.read_text(encoding="utf-8")
    assert "So sieht der Dateiname mit Beispieldaten aus" in src
    assert "live_preview" in src


def test_05_er_er_duplication_detected() -> None:
    assert filename_has_er_er_duplication("2026-01-01_er_er_x.pdf")
    assert MSG_ER_ER_DUPLICATION
    pattern = FilenamePattern(
        components=[
            FilenameComponent(type="feature", key="document_type", label="Art"),
            FilenameComponent(
                type="system", key="custom_text", label="Eigener Text", custom_text="er"
            ),
            FilenameComponent(type="system", key="extension", label="Dateityp"),
        ]
    )
    model = get_scan_model("rechnungen")
    issues = validate_pattern_product_rules(pattern, model, preview="a_er_er_b.pdf")
    assert MSG_ER_ER_DUPLICATION in issues


def test_06_strip_er_custom_when_art_present() -> None:
    pattern = FilenamePattern(
        components=[
            FilenameComponent(type="feature", key="document_type", label="Art"),
            FilenameComponent(
                type="system", key="custom_text", label="Eigener Text", custom_text="er"
            ),
            FilenameComponent(type="system", key="extension", label="Dateityp"),
        ]
    )
    cleaned = strip_er_custom_when_art_present(pattern)
    assert not any(
        c.key == "custom_text" and (c.custom_text or "") == "er"
        for c in cleaned.components
    )


def test_07_unsafe_custom_text_sanitized_or_rejected() -> None:
    assert sanitize_custom_text('bad/name*.txt') == "badname.txt" or "bad" in sanitize_custom_text(
        'bad/name*'
    )
    assert "/" not in sanitize_custom_text('a/b')
    issues = validate_planned_filename_candidate('bad/name.pdf')
    assert issues


def test_08_empty_custom_text_rejected() -> None:
    pattern = FilenamePattern(
        components=[
            FilenameComponent(
                type="system", key="custom_text", label="Eigener Text", custom_text="   "
            ),
            FilenameComponent(type="system", key="extension", label="Dateityp"),
        ]
    )
    model = get_scan_model("rechnungen")
    issues = validate_pattern_product_rules(pattern, model, preview="x.pdf")
    assert MSG_EMPTY_CUSTOM in issues


def test_09_pdf_preserved() -> None:
    name = rebuild_planned_filename_from_fields(
        invoice_date="2026-01-01",
        document_art="er",
        supplier="Firma",
        amount="10,00",
        payment="amex",
    )
    assert name.lower().endswith(".pdf")
    issues = validate_planned_filename_candidate("ohne_endung")
    assert any(".pdf" in i for i in issues)


def test_10_review_edit_not_raw_destructive() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "FILENAME_PATTERN_SAFE_EDIT_MARKER" in src
    assert "structured_not_raw" in src or "no_raw_destructive_edit" in src
    assert "rebuild_planned_filename_from_fields" in src
    assert "validate_planned_filename_candidate" in src


def test_11_structured_edit_keeps_pattern_language() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "Bausteine bearbeiten" in src or "Erkannte Werte korrigieren" in src
    assert "Musterstruktur bleibt erhalten" in src


def test_12_recognized_value_correction_updates_preview() -> None:
    name = rebuild_planned_filename_from_fields(
        invoice_date="2026-05-11",
        document_art="er",
        supplier="LUMITOP",
        amount="476,00",
        payment="paypal",
    )
    assert "LUMITOP" in name
    assert "476,00" in name
    src = REVIEW.read_text(encoding="utf-8")
    assert "live_planned_preview" in src


def test_13_invalid_filename_not_silent() -> None:
    issues = validate_planned_filename_candidate(
        "x_er_y_er.pdf",
        document_art="er",
        custom_text="er",
    )
    assert MSG_ER_ER_DUPLICATION in issues
    src = REVIEW.read_text(encoding="utf-8")
    assert "validation_issues" in src or "validate_planned_filename_candidate" in src


def test_14_configurations_uses_filename_builder() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "filename_builder" in src
    assert "build_filename_pattern_editor" in src


def test_15_marker_and_docs() -> None:
    assert FILENAME_PATTERN_SAFE_EDIT_MARKER.startswith("track_b_filename_pattern")
    assert DOC.is_file()
    assert BUILDER.is_file() and PATTERN.is_file()


def test_16_sources_parse() -> None:
    for path in (BUILDER, PATTERN, CONFIGS, REVIEW):
        ast.parse(path.read_text(encoding="utf-8"))


def test_17_no_run_once_call_in_builder() -> None:
    for path in (BUILDER, PATTERN):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id != "run_once"
                if isinstance(node.func, ast.Attribute):
                    assert node.func.attr != "run_once"
