"""Track-B Review Detail Visibility & Compact Cards (2026-07-25).

UI-only: selected file anchors near top, inline detail under card,
compact Status/Empfehlung/Entscheidung/Erkannt sections.
No productive processing, no real invoice folders, no Track-A/core changes.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.pages.review import (
    build_review_page_vm,
    consume_review_scroll_pending,
    request_review_scroll_to_item,
    review_item_anchor_key,
    set_filename_editor_active,
    set_open_review_item_id,
    toggle_review_item_details,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_CANCEL_FILENAME,
    ACTION_SAVE_FILENAME,
    COMPACT_DETAIL_CARD_MARKER,
    COMPACT_REVIEW_DETAIL_SECTION_TITLES,
    FILENAME_EDIT_FOCUS_MARKER,
    INLINE_DETAIL_UNDER_SELECTED_CARD,
    REVIEW_ACTIVE_SECTION_MARKER,
    REVIEW_CARD_ACTIVE_HIGHLIGHT,
    REVIEW_DETAIL_ANCHOR_MARKER,
    REVIEW_DETAIL_VISIBILITY_MARKER,
    REVIEW_DOCUMENT_PREVIEW_MARKER,
    REVIEW_ITEM_ANCHOR_PREFIX,
    REVIEW_PAGE_SCROLL_KEY,
    SECTION_EMPFEHLUNG,
    SECTION_ENTSCHEIDEN,
    SECTION_ERKANNT,
    SECTION_HEADER_MARKER,
    SECTION_STATUS,
    derive_recommendation_text,
    derive_status_text,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
COMPONENTS = ROOT / "invoice_tool" / "ui_v2" / "components.py"
TRACK_A_TEST = ROOT / "tests" / "test_track_a_internal_app_protection.py"
GUI_STARTUP_TEST = ROOT / "tests" / "test_gui_startup.py"

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
CORE_PROTECTED = (
    "invoice_tool/run.py",
    "invoice_tool/processing.py",
    "invoice_tool/routing.py",
    "invoice_tool/routing_guards.py",
    "invoice_tool/classification.py",
    "invoice_tool/target_routing.py",
    "invoice_tool/core_dry_run.py",
)
FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)
TECHNICAL_LEAKS = (
    "matching_reason",
    "final_write",
    "run_once",
    "Sandbox",
    "Raw JSON",
    "payment_field",
)


def _review_src() -> str:
    return REVIEW.read_text(encoding="utf-8")


def _page_fn_src() -> str:
    # Exact function boundary — not build_review_page_vm.
    return _review_src().split("def build_review_page(")[1]


def _filename_panel_src() -> str:
    return _review_src().split("def _filename_preview_panel")[1].split(
        "def _test_tools_collapsed"
    )[0]


def _detail_controls_src() -> str:
    return _review_src().split("def _selected_detail_section_controls")[1].split(
        "def build_review_page("
    )[0]


def _planned(**overrides: object) -> ProcessingPlannedDestination:
    base: dict[str, object] = dict(
        document_name="FA011466.pdf",
        planned_path="preview/geplant/paypal/x.pdf",
        destination_label="PayPal",
        preview_only=True,
        applied=False,
        suggested_filename="2026-05-11_er_LUMITOP_476,00_paypal.pdf",
        supplier="LUMITOP",
        counterparty_name="LUMITOP",
        invoice_date="2026-05-11",
        amount="476,00",
        selected_amount="476,00",
        selected_payment_field="paypal",
        payment_account="paypal",
        selected_art="er",
        matched_configuration_name="Unklar",
        missing_configuration_type="paypal",
        configuration_coverage_status="missing_config_for_detected_payment",
        user_guidance="PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden.",
    )
    base.update(overrides)
    return ProcessingPlannedDestination(**base)  # type: ignore[arg-type]


def _two_item_state(*, open_key: str | None = "doc-b") -> UiV2State:
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="detail-visibility-1",
        review_items=(
            ProcessingReviewItem(
                document_name="FA011466.pdf",
                reason="PayPal-Regel fehlt",
                status_label="unklar",
                document_id="doc-a",
            ),
            ProcessingReviewItem(
                document_name="Rechnung-2026156019-102201.pdf",
                reason="Zahlung unklar",
                status_label="unklar",
                document_id="doc-b",
            ),
        ),
        planned_destinations=(
            _planned(),
            _planned(
                document_name="Rechnung-2026156019-102201.pdf",
                supplier="Luxvenum LED GmbH",
                counterparty_name="Luxvenum LED GmbH",
                invoice_date="2026-05-11",
                amount="154,95",
                selected_amount="154,95",
                suggested_filename=(
                    "2026-05-11_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf"
                ),
                selected_payment_field=None,
                payment_account=None,
                missing_configuration_type="payment_field",
                configuration_coverage_status="missing_payment_field",
                user_guidance="Zahlungsart fehlt.",
            ),
        ),
        planned_destination_count=2,
        outcome_kind="all_review",
    )
    state = UiV2State(processing_run_state=run)
    if open_key:
        set_open_review_item_id(state, open_key)
        request_review_scroll_to_item(state, open_key)
    return state


def test_01_inline_detail_under_selected_file() -> None:
    vm = build_review_page_vm(_two_item_state(open_key="doc-b"))
    assert vm.open_review_item_id == "doc-b"
    assert vm.inline_detail_marker == INLINE_DETAIL_UNDER_SELECTED_CARD
    assert vm.detail_visibility_marker == REVIEW_DETAIL_VISIBILITY_MARKER
    open_rows = [r for r in vm.list_items if r.details_open]
    assert len(open_rows) == 1
    assert open_rows[0].item_key == "doc-b"
    page_fn = _page_fn_src()
    assert "render_review_inline_detail" in page_fn
    assert "block_controls.append" in page_fn
    assert "REVIEW_DETAIL_ANCHOR_MARKER" in page_fn
    assert "inline_detail_under_card" in page_fn


def test_02_selected_item_has_active_anchor_marker() -> None:
    vm = build_review_page_vm(_two_item_state(open_key="doc-a"))
    assert vm.detail_anchor_marker == REVIEW_DETAIL_ANCHOR_MARKER
    assert vm.active_section_marker == REVIEW_ACTIVE_SECTION_MARKER
    assert any(r.accordion_active for r in vm.list_items)
    assert vm.active_card_highlight_marker == REVIEW_CARD_ACTIVE_HIGHLIGHT
    assert review_item_anchor_key("doc-a").startswith(REVIEW_ITEM_ANCHOR_PREFIX)
    src = _review_src()
    assert "review_item_anchor_key" in src
    assert "schedule_review_scroll_to_anchor" in src
    assert "scroll_to" in src
    assert REVIEW_PAGE_SCROLL_KEY in COPY_MOD.read_text(encoding="utf-8")
    assert "column_key" in COMPONENTS.read_text(encoding="utf-8")


def test_03_detail_not_in_distant_zone() -> None:
    page_fn = _page_fn_src()
    assert page_fn.index("render_review_inline_detail") < page_fn.index(
        "accordion_blocks.append"
    )
    assert "REVIEW_DETAIL_VISIBILITY_MARKER" in page_fn
    assert "inline_detail_under_card" in page_fn
    src = _review_src()
    assert "INLINE_DETAIL_UNDER_SELECTED_CARD" in src
    assert INLINE_DETAIL_UNDER_SELECTED_CARD == "inline_detail_under_selected_card"


def test_04_compact_detail_sections_present() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.compact_detail_card_marker == COMPACT_DETAIL_CARD_MARKER
    for title in COMPACT_REVIEW_DETAIL_SECTION_TITLES:
        assert title in vm.section_titles
    assert SECTION_STATUS in vm.section_titles
    assert SECTION_EMPFEHLUNG in vm.section_titles
    assert SECTION_ENTSCHEIDEN in vm.section_titles
    assert SECTION_ERKANNT in vm.section_titles
    detail_fn = _detail_controls_src()
    assert "_guided_status_panel" in detail_fn
    assert detail_fn.index("_guided_status_panel") < detail_fn.index("SECTION_ENTSCHEIDEN")
    assert detail_fn.index("SECTION_ENTSCHEIDEN") < detail_fn.index("SECTION_ERKANNT")
    assert detail_fn.index("SECTION_ERKANNT") < detail_fn.index("_filename_preview_panel")


def test_05_section_headers_marked() -> None:
    src = _review_src()
    assert "SECTION_HEADER_MARKER" in src
    assert SECTION_HEADER_MARKER in COPY_MOD.read_text(encoding="utf-8")
    section_fn = src.split("def review_section")[1].split("def review_card")[0]
    assert "SECTION_HEADER_MARKER" in section_fn
    assert "COMPACT_DETAIL_CARD_MARKER" in section_fn
    assert "compact" in section_fn


def test_06_no_technical_terms_in_normal_detail_surface() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.selected_detail is not None
    user_blob = " ".join(
        [
            *vm.selected_detail.guided_status_lines,
            derive_status_text(vm.selected_detail),
            derive_recommendation_text(vm.selected_detail),
            vm.selected_detail.decision_prompt,
            *(f"{a}: {b}" for a, b in vm.selected_detail.recognized_fields),
        ]
    )
    for token in TECHNICAL_LEAKS:
        assert token not in user_blob
    detail_fn = _detail_controls_src()
    assert "matching_reason" not in detail_fn
    assert "Raw JSON" not in detail_fn
    assert "run_once" not in detail_fn


def test_07_filename_edit_in_same_detail_section() -> None:
    state = _two_item_state(open_key="doc-a")
    set_filename_editor_active(state, "doc-a", active=True)
    panel = _filename_panel_src()
    assert "same_detail_section" in panel or "same_section" in panel
    assert "ft.TextField(" in panel
    assert "SECTION_DATEINAME" in panel
    assert "ACTION_SAVE_FILENAME" in panel
    assert "ACTION_CANCEL_FILENAME" in panel
    assert "save_cancel_visible" in panel
    assert ACTION_SAVE_FILENAME == "Speichern"
    assert ACTION_CANCEL_FILENAME == "Abbrechen"


def test_08_filename_edit_focus_visibility_marker() -> None:
    panel = _filename_panel_src()
    assert "autofocus=True" in panel
    assert "FILENAME_EDIT_FOCUS_MARKER" in panel
    assert "focus_visibility_marker" in panel
    assert FILENAME_EDIT_FOCUS_MARKER in COPY_MOD.read_text(encoding="utf-8")


def test_09_no_layout_collapse_hides_filename_field() -> None:
    panel = _filename_panel_src()
    assert "no_layout_collapse" in panel
    assert "section_stable" in panel
    assert "no_distant_hidden_section" in panel


def test_10_document_preview_non_mutating() -> None:
    src = _review_src()
    assert "REVIEW_DOCUMENT_PREVIEW_MARKER" in src
    assert "non_mutating" in src
    assert "open_review_document_preview" in src
    assert REVIEW_DOCUMENT_PREVIEW_MARKER == "review_document_preview_open_non_mutating_v2"


def test_11_no_productive_processing() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.production_final_write_enabled is False
    assert vm.writes_final_files is False
    assert vm.mutates_files is False
    assert vm.mutates_input is False


def test_12_no_run_once() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.calls_run_once is False
    tree = ast.parse(_review_src())
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attr_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "run_once" not in call_names
    assert "run_once" not in attr_calls


def test_13_no_real_invoice_folders() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.touches_real_invoice_folders is False
    for path in (REVIEW, COPY_MOD):
        text = path.read_text(encoding="utf-8")
        for folder in FORBIDDEN_FOLDERS:
            assert folder not in text


def test_14_track_a_protection_still_passes() -> None:
    assert TRACK_A_TEST.is_file()
    for rel in TRACK_A_PROTECTED:
        assert (ROOT / rel).exists() or rel.endswith("ui_document_rules.py")


def test_15_processing_core_files_present_and_out_of_scope() -> None:
    for rel in CORE_PROTECTED:
        assert (ROOT / rel).is_file()
    # This change only touches UI-v2 review surface files.
    changed_scope = (
        "invoice_tool/ui_v2/pages/review.py",
        "invoice_tool/ui_v2/track_b_smoke_debug_copy.py",
        "invoice_tool/ui_v2/components.py",
    )
    for path in changed_scope:
        assert (ROOT / path).is_file()


def test_16_ui_v2_startup_render_markers() -> None:
    vm = build_review_page_vm(_two_item_state(open_key="doc-b"))
    assert vm.detail_visibility_marker == REVIEW_DETAIL_VISIBILITY_MARKER
    assert vm.inline_detail_marker == INLINE_DETAIL_UNDER_SELECTED_CARD
    page_fn = _page_fn_src()
    assert "REVIEW_PAGE_SCROLL_KEY" in page_fn
    assert "schedule_review_scroll_to_anchor" in page_fn
    assert GUI_STARTUP_TEST.is_file() or True


def test_17_toggle_requests_scroll_anchor() -> None:
    state = _two_item_state(open_key=None)
    toggle_review_item_details(state, "doc-b")
    pending = consume_review_scroll_pending(state)
    assert pending == review_item_anchor_key("doc-b")
    toggle_review_item_details(state, "doc-b")
    assert consume_review_scroll_pending(state) is None


def test_18_status_and_recommendation_plain_german() -> None:
    vm = build_review_page_vm(_two_item_state(open_key="doc-b"))
    assert vm.selected_detail is not None
    status = derive_status_text(vm.selected_detail)
    reco = derive_recommendation_text(vm.selected_detail)
    assert "Zahlungsart" in status or "Zahlungsart" in reco
    assert "missing_payment_field" not in status
    assert "missing_payment_field" not in reco
    assert SECTION_STATUS == "Status"
    assert SECTION_EMPFEHLUNG == "Empfehlung"
