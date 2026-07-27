"""Track-B Configuration Layout & Filename Pattern Cleanup (2026-07-27).

Full-width active profile, create button own row, equal list/detail height,
no _er_er_, clear filename-block reorder (no „nach oben/unten“).
"""

from __future__ import annotations

from pathlib import Path

from invoice_tool.configuration_model import (
    FilenameComponent,
    FilenamePattern,
    preview_filename,
)
from invoice_tool.scan_models import get_scan_model
from invoice_tool.ui_v2.configuration_model import (
    CONFIG_CREATE_ACTION_ROW_MARKER,
    CONFIG_EQUAL_HEIGHT_SPLIT_MARKER,
    CREATE_NEAR_LIST_MARKER,
    FULL_WIDTH_PROFILE_SUMMARY_MARKER,
)
from invoice_tool.ui_v2.filename_pattern import (
    MSG_ER_ER_DUPLICATION,
    filename_has_er_er_duplication,
    strip_er_custom_when_art_present,
    validate_pattern_product_rules,
)
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_CONFIG_REORDER_DOWN,
    ACTION_CONFIG_REORDER_UP,
    ACTION_NEW_CONFIGURATION,
    FILENAME_BLOCK_REORDER_MARKER,
    TOOLTIP_FILENAME_BLOCK_EARLIER,
    TOOLTIP_FILENAME_BLOCK_LATER,
    document_has_open_review_need,
    resolve_document_ui_status,
    STATUS_UI_NEEDS_REVIEW,
    STATUS_UI_OK,
)
from invoice_tool.ui_v2.processing_state import ProcessingPlannedDestination
from invoice_tool.ui_v2.workspace_file_pairs import (
    STATUS_PROPOSED,
    STATUS_REVIEW,
    build_live_file_pairs_vm,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py"
BUILDER = ROOT / "invoice_tool" / "ui_v2" / "filename_builder.py"
PATTERN = ROOT / "invoice_tool" / "ui_v2" / "filename_pattern.py"
COPY = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"


def _src_configs() -> str:
    return CONFIGS.read_text(encoding="utf-8")


def test_01_active_profile_full_width_and_count() -> None:
    src = _src_configs()
    assert "FULL_WIDTH_PROFILE_SUMMARY_MARKER" in src
    assert FULL_WIDTH_PROFILE_SUMMARY_MARKER == "config_active_profile_full_width_v1"
    assert "Aktives Profil" in src
    assert "Konfigurationen" in src
    assert "span_main_width" in src or "full_width" in src
    assert "no_5A_artifact" in src
    count_block = src.split("config_count_label")[1].split("top_summary")[0]
    assert "total_count" in count_block
    assert "active_count" not in count_block


def test_02_create_button_own_row_right() -> None:
    src = _src_configs()
    assert "CONFIG_CREATE_ACTION_ROW_MARKER" in src
    assert CONFIG_CREATE_ACTION_ROW_MARKER == "config_create_button_own_row_right_v1"
    assert "CREATE_NEAR_LIST_MARKER" in src
    assert CREATE_NEAR_LIST_MARKER == "config_create_button_near_list_v1"
    assert "own_row_right" in src
    assert "MainAxisAlignment.END" in src
    assert ACTION_NEW_CONFIGURATION == "Neue Konfiguration erstellen"
    header = src.split("page_header(")[1].split(")", 1)[0]
    assert "ACTION_NEW_CONFIGURATION" not in header
    # Create row appears before the equal-height split.
    assert src.index("create_action_row") < src.index("equal_split")


def test_03_list_and_detail_equal_height() -> None:
    src = _src_configs()
    assert "CONFIG_EQUAL_HEIGHT_SPLIT_MARKER" in src
    assert CONFIG_EQUAL_HEIGHT_SPLIT_MARKER == "config_list_detail_equal_height_v1"
    assert "same_top" in src
    assert "same_base_height" in src
    assert "list_detail_split" in src
    # Create button must not sit inside the list column above the list card.
    assert "create_near_list,\n            list_panel" not in src


def test_04_no_unclear_nach_oben_unten_buttons() -> None:
    src = _src_configs()
    assert '"Nach oben"' not in src
    assert '"Nach unten"' not in src
    assert ACTION_CONFIG_REORDER_UP == "In Liste nach oben"
    assert ACTION_CONFIG_REORDER_DOWN == "In Liste nach unten"
    assert "ACTION_CONFIG_REORDER_UP" in src
    builder = BUILDER.read_text(encoding="utf-8")
    assert "nach oben" not in builder.casefold()
    assert "nach unten" not in builder.casefold()
    assert "FILENAME_BLOCK_REORDER_MARKER" in builder
    assert FILENAME_BLOCK_REORDER_MARKER == "filename_block_reorder_earlier_later_v1"
    assert "TOOLTIP_FILENAME_BLOCK_EARLIER" in builder
    assert "TOOLTIP_FILENAME_BLOCK_LATER" in builder
    assert TOOLTIP_FILENAME_BLOCK_EARLIER.startswith("Baustein früher")
    assert TOOLTIP_FILENAME_BLOCK_LATER.startswith("Baustein später")


def test_05_no_er_er_in_pattern_preview() -> None:
    model = get_scan_model("rechnungen")
    pattern = FilenamePattern(
        components=[
            FilenameComponent(type="feature", key="invoice_date", label="Datum"),
            FilenameComponent(
                type="system", key="custom_text", label="Eigener Text", custom_text="er"
            ),
            FilenameComponent(type="feature", key="document_type", label="Art"),
            FilenameComponent(type="feature", key="supplier", label="Lieferant"),
            FilenameComponent(type="system", key="extension", label="Dateityp"),
        ]
    )
    cleaned = strip_er_custom_when_art_present(pattern)
    preview = preview_filename(cleaned, model)
    assert "_er_er_" not in preview.casefold()
    assert not filename_has_er_er_duplication(preview)
    issues = validate_pattern_product_rules(pattern, model, preview="a_er_er_b.pdf")
    assert MSG_ER_ER_DUPLICATION in issues
    assert "bereits im Muster enthalten" in MSG_ER_ER_DUPLICATION


def test_06_planned_filename_with_unclear_card_is_review() -> None:
    planned = ProcessingPlannedDestination(
        document_name="card.pdf",
        planned_path="preview/geplant/card.pdf",
        destination_label="Karte",
        preview_only=True,
        applied=False,
        suggested_filename="2026-05-11_er_Shop_10,00_card.pdf",
        supplier="Shop",
        counterparty_name="Shop",
        invoice_date="2026-05-11",
        amount="10,00",
        selected_amount="10,00",
        selected_payment_field="card",
        payment_account="card",
        selected_art="er",
        matched_configuration_name="Unklar",
        missing_configuration_type="generic_card",
        configuration_coverage_status="no_safe_card",
        user_guidance="Kartenzahlung erkannt, aber AMEX ist nicht belegt.",
    )
    assert document_has_open_review_need(planned) is True
    assert resolve_document_ui_status(
        output_status=STATUS_PROPOSED, detail=planned
    ) == STATUS_UI_NEEDS_REVIEW
    vm = build_live_file_pairs_vm(
        input_filenames=["card.pdf"],
        output_folder_selected=True,
        planned_destinations=[planned],
    )
    assert vm.rows[0].output_status == STATUS_REVIEW
    assert resolve_document_ui_status(
        output_status=vm.rows[0].output_status
    ) == STATUS_UI_NEEDS_REVIEW


def test_07_clear_ok_file_stays_green() -> None:
    planned = ProcessingPlannedDestination(
        document_name="ok.pdf",
        planned_path="preview/geplant/paypal/ok.pdf",
        destination_label="PayPal",
        preview_only=True,
        applied=False,
        suggested_filename="2026-05-11_er_Shop_10,00_paypal.pdf",
        supplier="Shop",
        counterparty_name="Shop",
        invoice_date="2026-05-11",
        amount="10,00",
        selected_amount="10,00",
        selected_payment_field="paypal",
        payment_account="paypal",
        selected_art="er",
        matched_configuration_name="PayPal",
        missing_configuration_type=None,
        configuration_coverage_status="matched",
        user_guidance="PayPal-Regel angewendet.",
    )
    assert document_has_open_review_need(planned) is False
    assert resolve_document_ui_status(
        output_status=STATUS_PROPOSED, detail=planned
    ) == STATUS_UI_OK


def test_08_card_copy_not_amex_nicht_belegt() -> None:
    text = COPY.read_text(encoding="utf-8")
    assert "Kartenzahlung erkannt, aber die verwendete Karte ist unklar." in text
    assert 'MSG_WHY_CARD_AMEX_SHORT = "Kartenzahlung erkannt, aber AMEX ist nicht belegt."' not in text
    assert "Bitte wählen Sie die verwendete Karte" in text
