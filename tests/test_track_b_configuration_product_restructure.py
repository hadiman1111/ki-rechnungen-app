"""Track-B Configuration Product Restructure (2026-07-27).

Product-understandable configurations page: layout, labels, document-type
dropdown, recognition rule group, review choice, full target path.
No productive processing, no Track-A/core changes.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.configuration_model import (
    CONFIGURATION_PRODUCT_RESTRUCTURE_MARKER,
    CONFIG_PREVIEW_SUMMARY_MARKER,
    CREATE_NEAR_LIST_MARKER,
    DOCUMENT_TYPE_DROPDOWN_MARKER,
    FULL_WIDTH_PROFILE_SUMMARY_MARKER,
    LABEL_CONFIG_NAME,
    LABEL_RECOGNIZE_WHEN,
    LABEL_REVIEW_BEHAVIOR,
    LABEL_VALUES,
    LOGIC_ANY,
    RECOGNITION_RULE_GROUP_MARKER,
    REVIEW_BEHAVIOR_CHOICE_MARKER,
    SUPPORTED_DOCUMENT_TYPES,
    SUPPORTED_REVIEW_BEHAVIORS,
    TARGET_PATH_FULL_VISIBLE_MARKER,
    format_target_path_display,
    normalize_document_type,
    plain_language_configuration_summary,
    rule_group_from_matching,
    synonym_helper_text,
)
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_NEW_CONFIGURATION,
    SECTION_ADVANCED_CONFIG,
    SECTION_IMPORT_EXPORT_ADVANCED,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py"
MODEL = ROOT / "invoice_tool" / "ui_v2" / "configuration_model.py"
DOC = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PRODUCT_RESTRUCTURE_2026-07-27.md"
)

TRACK_A = (
    "app_main.py",
    "invoice_tool/gui.py",
    "invoice_tool/ui_configurations.py",
    "invoice_tool/run.py",
    "invoice_tool/processing.py",
)


def _src() -> str:
    return CONFIGS.read_text(encoding="utf-8")


def test_01_active_profile_full_width() -> None:
    src = _src()
    assert "FULL_WIDTH_PROFILE_SUMMARY_MARKER" in src
    assert "full_width" in src
    assert FULL_WIDTH_PROFILE_SUMMARY_MARKER == "config_active_profile_full_width_v1"


def test_02_create_button_near_list_not_only_header() -> None:
    src = _src()
    assert "CREATE_NEAR_LIST_MARKER" in src
    assert "near_configuration_list" in src
    assert "on_click=lambda _e: _start_create()" in src
    assert ACTION_NEW_CONFIGURATION == "Neue Konfiguration erstellen"
    # Header must not be the only create placement.
    header = src.split("page_header(")[1].split(")", 1)[0]
    assert "ACTION_NEW_CONFIGURATION" not in header


def test_03_advanced_hints_not_primary_open() -> None:
    src = _src()
    assert "SECTION_ADVANCED_CONFIG" in src
    assert SECTION_ADVANCED_CONFIG == "Erweiterte Hinweise"
    assert "is_track_b_show_dev_surfaces_enabled" in src


def test_04_import_export_collapsed_dev_only() -> None:
    src = _src()
    assert "SECTION_IMPORT_EXPORT_ADVANCED" in src
    assert SECTION_IMPORT_EXPORT_ADVANCED == "Import / Export (erweitert)"
    assert "initially_expanded=False" in src
    assert "dev_surfaces_only" in src or "is_track_b_show_dev_surfaces_enabled" in src


def test_05_labels_product_language() -> None:
    assert LABEL_CONFIG_NAME == "Name der Konfiguration"
    assert LABEL_RECOGNIZE_WHEN == "Erkennen, wenn …"
    assert LABEL_REVIEW_BEHAVIOR == "Prüfverhalten"
    assert LABEL_VALUES == "Erkannte Schreibweisen / Werte"
    src = _src()
    assert "LABEL_CONFIG_NAME" in src
    assert "LABEL_RECOGNIZE_WHEN" in src


def test_06_document_type_dropdown() -> None:
    src = _src()
    assert "DOCUMENT_TYPE_DROPDOWN_MARKER" in src
    assert "SUPPORTED_DOCUMENT_TYPES" in src
    assert "ft.Dropdown(" in src
    assert set(SUPPORTED_DOCUMENT_TYPES) == {
        "Rechnung",
        "Storno",
        "Gutschrift",
        "Sonstiges",
    }
    assert DOCUMENT_TYPE_DROPDOWN_MARKER == "config_document_type_dropdown_v1"
    assert normalize_document_type("invoice") == "Rechnung"


def test_07_recognition_rule_group() -> None:
    src = _src()
    assert "RECOGNITION_RULE_GROUP_MARKER" in src
    assert "_build_recognition_rule_group_editor" in src
    assert "LABEL_RULE_LOGIC" in src or "LOGIC_LABELS" in src
    assert RECOGNITION_RULE_GROUP_MARKER == "config_recognition_rule_group_v1"
    group = rule_group_from_matching(
        feature_key="payment_field",
        operator="enthält",
        values=["amex", "American Express"],
        logic=LOGIC_ANY,
    )
    assert len(group.clauses) == 1
    assert group.flattened_values() == ["amex", "American Express"]
    helper = synonym_helper_text(["amex", "American Express"])
    assert "amex" in helper and "American Express" in helper


def test_08_review_behavior_selection() -> None:
    src = _src()
    assert "REVIEW_BEHAVIOR_CHOICE_MARKER" in src
    assert "SUPPORTED_REVIEW_BEHAVIORS" in src
    assert REVIEW_BEHAVIOR_CHOICE_MARKER == "config_review_behavior_choice_v1"
    assert SUPPORTED_REVIEW_BEHAVIORS[0][0] == "unclear_on_no_match"
    assert "Bei Unsicherheit" in SUPPORTED_REVIEW_BEHAVIORS[0][1]


def test_09_payment_not_primary_unexplained_freetext() -> None:
    src = _src()
    # Payment free text must not be unconditional primary form content.
    assert "LABEL_PAYMENT_ADVANCED" in src
    assert "payment_accounting_advanced_collapsed" in src or "is_track_b_show_dev_surfaces_enabled" in src


def test_10_target_path_full_visible() -> None:
    primary, full = format_target_path_display(
        "/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output/geplant/Amex"
    )
    assert "Amex" in primary
    assert primary == full
    assert not primary == "Amex" or "/" in primary  # full path, not basename alone
    assert "/" in primary
    src = _src()
    assert "TARGET_PATH_FULL_VISIBLE_MARKER" in src
    assert "Vollständiger" in src or "full_path" in src
    assert TARGET_PATH_FULL_VISIBLE_MARKER == "config_target_path_full_visible_v1"


def test_11_plain_language_preview_summary() -> None:
    lines = plain_language_configuration_summary(
        name="AMEX",
        document_type="Rechnung",
        rule_group=rule_group_from_matching(
            feature_key="payment_field",
            operator="enthält",
            values=["amex", "American Express"],
        ),
        filename_preview="2026-01-01_er_Beispiel_10,00_amex.pdf",
        destination_path="/tmp/out/Amex",
        review_key="unclear_on_no_match",
    )
    blob = " ".join(lines)
    assert "erkennt Belege" in blob
    assert "Dateiname geplant" in blob
    assert "Zielordner" in blob
    assert "Prüfverhalten" in blob
    src = _src()
    assert "CONFIG_PREVIEW_SUMMARY_MARKER" in src
    assert CONFIG_PREVIEW_SUMMARY_MARKER == "config_plain_language_preview_summary_v1"


def test_12_marker_and_docs() -> None:
    assert CONFIGURATION_PRODUCT_RESTRUCTURE_MARKER.startswith("track_b_configuration")
    assert MODEL.is_file()
    assert DOC.is_file()
    assert "CONFIGURATION" in DOC.read_text(encoding="utf-8").upper() or "Konfiguration" in DOC.read_text(
        encoding="utf-8"
    )


def test_13_sources_parse_and_no_core_imports_in_model() -> None:
    ast.parse(_src())
    ast.parse(MODEL.read_text(encoding="utf-8"))
    model = MODEL.read_text(encoding="utf-8")
    assert "invoice_tool.processing" not in model
    assert "invoice_tool.run" not in model
    for rel in TRACK_A:
        assert (ROOT / rel).exists() or rel.endswith("ui_document_rules.py")


def test_14_create_near_list_marker_constant() -> None:
    assert CREATE_NEAR_LIST_MARKER == "config_create_button_near_list_v1"
