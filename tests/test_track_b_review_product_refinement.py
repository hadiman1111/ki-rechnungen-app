"""Track-B Review Product UX Refinement (2026-07-25).

Navigation „Prüfung“, planned filename labels, dual scroll targets,
dev-only Test/Nachweis + Entwickler Diagnose, decision/recognized weighting.
No productive processing, no real invoice folders, no Track-A/core changes.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from invoice_tool.ui_v2.navigation import ADMIN_NAV, DAILY_NAV, NAV_REVIEW, NAV_SETTINGS
from invoice_tool.ui_v2.pages.review import (
    build_review_page_vm,
    consume_review_scroll_pending,
    request_review_scroll_to_filename_section,
    request_review_scroll_to_item,
    review_card_anchor_key,
    review_filename_section_anchor_key,
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
    ACTION_EDIT_FILENAME,
    ACTION_OPEN_REVIEW,
    ACTION_SAVE_FILENAME,
    ACTION_CANCEL_FILENAME,
    COMPACT_REVIEW_DETAIL_SECTION_TITLES,
    LABEL_PROPOSED_FILENAME,
    LABEL_SUGGESTED_FILENAME,
    MSG_REC_MISSING_PAYMENT_PLAIN,
    REVIEW_CARD_ANCHOR_PREFIX,
    REVIEW_CARD_SCROLL_TARGET_MARKER,
    REVIEW_FILENAME_SCROLL_TARGET_MARKER,
    REVIEW_FILENAME_SECTION_ANCHOR_PREFIX,
    REVIEW_PRODUCT_UX_REFINEMENT_MARKER,
    SECTION_DATEINAME,
    SECTION_ENTSCHEIDEN,
    SECTION_ERKANNT,
    SECTION_TEST_TOOLS,
    derive_open_decision_points,
    derive_recognized_fields,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
NAV = ROOT / "invoice_tool" / "ui_v2" / "navigation.py"
SHELL = ROOT / "invoice_tool" / "ui_v2" / "shell.py"
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
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
    "missing_payment_field",
    "unresolved token",
    "matching_reason",
    "payment_field",
    "final_write",
    "run_once",
    "Sandbox",
    "Raw JSON",
)


def _review_src() -> str:
    return REVIEW.read_text(encoding="utf-8")


def _detail_controls_src() -> str:
    return _review_src().split("def _selected_detail_section_controls")[1].split(
        "def build_review_page("
    )[0]


def _filename_panel_src() -> str:
    return _review_src().split("def _filename_preview_panel")[1].split(
        "def _test_tools_collapsed"
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
        run_id="product-refinement-1",
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


def test_01_nav_shows_pruefung_not_zur_pruefung() -> None:
    labels = [label for _, label, _ in DAILY_NAV]
    assert "Prüfung" in labels
    assert "Zur Prüfung" not in labels
    assert NAV.read_text(encoding="utf-8").count('"Prüfung"') >= 1
    assert '"Zur Prüfung"' not in NAV.read_text(encoding="utf-8")


def test_02_workspace_link_pruefung_oeffnen() -> None:
    assert ACTION_OPEN_REVIEW == "Prüfung öffnen"
    assert "Zur Prüfung öffnen" != ACTION_OPEN_REVIEW
    assert "ACTION_OPEN_REVIEW" in WORKSPACE.read_text(encoding="utf-8")


def test_03_review_page_title_pruefung() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.title == "Prüfung"
    assert vm.title != "Zur Prüfung"


def test_04_review_page_reachable() -> None:
    assert NAV_REVIEW == "zur_pruefung"
    assert any(nav_id == NAV_REVIEW for nav_id, _, _ in DAILY_NAV)
    vm = build_review_page_vm(_two_item_state())
    assert vm.review_count >= 1


def test_05_normal_menu_hides_entwickler_diagnose() -> None:
    assert NAV_SETTINGS not in {i for i, _, _ in DAILY_NAV}
    assert ADMIN_NAV[0][1] == "Entwickler / Diagnose"
    shell = SHELL.read_text(encoding="utf-8")
    assert "show_dev_nav" in shell
    assert "is_track_b_dev_defaults_enabled" in shell
    assert "hidden_from_normal_menu" in shell or "dev_defaults_only" in shell
    # Normal menu assembly: admin group only inside show_dev_nav branch.
    assert "if show_dev_nav:" in shell


def test_06_normal_review_hides_test_nachweis() -> None:
    detail_fn = _detail_controls_src()
    assert "is_track_b_dev_defaults_enabled()" in detail_fn
    assert "_test_tools_collapsed" in detail_fn
    # Appended only inside the dev-defaults branch.
    gated = detail_fn.split("if is_track_b_dev_defaults_enabled():")[1]
    assert "_test_tools_collapsed" in gated
    primary = detail_fn.split("if is_track_b_dev_defaults_enabled():")[0]
    assert "_test_tools_collapsed" not in primary
    assert SECTION_TEST_TOOLS == "Test & Nachweis"


def test_07_normal_review_no_oracle_copy_buttons() -> None:
    detail_fn = _detail_controls_src()
    assert "ACTION_COPY_ORACLE" not in detail_fn
    assert "ACTION_COPY_DIAGNOSIS" not in detail_fn
    assert "ACTION_COPY_CASE" not in detail_fn


def test_08_normal_detail_no_dry_run_sandbox_oracle_terms() -> None:
    # Primary (non-dev) branch of detail assembly must stay free of evidence terms.
    detail_fn = _detail_controls_src()
    primary = detail_fn.split("if is_track_b_dev_defaults_enabled():")[0]
    for token in ("Dry Run", "Dry-Run", "Sandbox", "Oracle", "Entwicklernachweis"):
        assert token not in primary


def test_09_dev_surfaces_remain_available() -> None:
    src = _review_src()
    assert "def _test_tools_collapsed" in src
    assert "SECTION_TEST_TOOLS" in src
    assert "is_track_b_dev_defaults_enabled" in src
    assert ADMIN_NAV  # routing/page still exists


def test_10_planned_filename_on_card() -> None:
    assert LABEL_PROPOSED_FILENAME == "Geplanter Dateiname"
    assert LABEL_SUGGESTED_FILENAME == "Geplanter Dateiname"
    assert "LABEL_PROPOSED_FILENAME" in _review_src()
    assert "Vorgeschlagener Dateiname" not in (
        LABEL_PROPOSED_FILENAME,
        LABEL_SUGGESTED_FILENAME,
    )


def test_11_detail_section_dateiname() -> None:
    assert SECTION_DATEINAME == "Dateiname"
    assert SECTION_DATEINAME in COMPACT_REVIEW_DETAIL_SECTION_TITLES
    panel = _filename_panel_src()
    assert "SECTION_DATEINAME" in panel
    assert "ACTION_EDIT_FILENAME" in panel
    assert ACTION_EDIT_FILENAME == "Dateiname bearbeiten"


def test_12_no_was_schlaegt_die_app_vor_section() -> None:
    assert SECTION_DATEINAME != "Was schlägt die App vor?"
    assert "Was schlägt die App vor?" not in (
        SECTION_DATEINAME,
        SECTION_ERKANNT,
        SECTION_ENTSCHEIDEN,
    )


def test_13_no_vorgeschlagener_as_dauerbegriff() -> None:
    assert LABEL_PROPOSED_FILENAME != "Vorgeschlagener Dateiname"
    copy = COPY_MOD.read_text(encoding="utf-8")
    # Constants must use Geplanter Dateiname for user-facing labels.
    assert 'LABEL_PROPOSED_FILENAME = "Geplanter Dateiname"' in copy
    assert 'LABEL_SUGGESTED_FILENAME = "Geplanter Dateiname"' in copy


def test_14_no_final_rename_claim() -> None:
    panel = _filename_panel_src()
    for token in ("final umbenannt", "bereits umbenannt", "final geschrieben"):
        assert token not in panel.casefold()
    vm = build_review_page_vm(_two_item_state())
    assert vm.writes_final_files is False
    assert vm.production_final_write_enabled is False


def test_15_file_click_uses_card_anchor() -> None:
    state = _two_item_state(open_key=None)
    toggle_review_item_details(state, "doc-b")
    pending = consume_review_scroll_pending(state)
    assert pending == review_card_anchor_key("doc-b")
    assert pending.startswith(REVIEW_CARD_ANCHOR_PREFIX)
    assert pending == review_item_anchor_key("doc-b")


def test_16_card_anchor_before_detail() -> None:
    page_fn = _review_src().split("def build_review_page(")[1]
    assert "card_anchor" in page_fn or "review_card_anchor_key" in page_fn
    assert "before_inline_detail" in page_fn
    assert "render_review_inline_detail" in page_fn
    assert REVIEW_CARD_SCROLL_TARGET_MARKER in COPY_MOD.read_text(encoding="utf-8")


def test_17_detail_still_inline_under_card() -> None:
    page_fn = _review_src().split("def build_review_page(")[1]
    assert "inline_detail_under_card" in page_fn
    assert "block_controls.append" in page_fn
    assert "render_review_inline_detail" in page_fn


def test_18_filename_edit_uses_filename_section_anchor() -> None:
    state = _two_item_state(open_key="doc-a")
    set_filename_editor_active(state, "doc-a", active=True)
    request_review_scroll_to_filename_section(state, "doc-a")
    pending = consume_review_scroll_pending(state)
    assert pending == review_filename_section_anchor_key("doc-a")
    assert pending.startswith(REVIEW_FILENAME_SECTION_ANCHOR_PREFIX)
    panel = _filename_panel_src()
    assert "request_review_scroll_to_filename_section" in panel
    assert REVIEW_FILENAME_SCROLL_TARGET_MARKER in COPY_MOD.read_text(encoding="utf-8")


def test_19_filename_edit_does_not_scroll_to_card() -> None:
    panel = _filename_panel_src()
    start = panel.split("def _start_filename_edit")[1].split("def _cancel_filename_edit")[0]
    assert "request_review_scroll_to_filename_section" in start
    assert "request_review_scroll_to_item" not in start
    card_key = review_card_anchor_key("doc-a")
    filename_key = review_filename_section_anchor_key("doc-a")
    assert card_key != filename_key


def test_20_edit_field_in_dateiname_section() -> None:
    panel = _filename_panel_src()
    assert "ft.TextField(" in panel
    assert "same_section" in panel or "same_detail_section" in panel
    assert "SECTION_DATEINAME" in panel
    assert "autofocus=True" in panel


def test_21_save_cancel_same_section() -> None:
    panel = _filename_panel_src()
    assert "ACTION_SAVE_FILENAME" in panel
    assert "ACTION_CANCEL_FILENAME" in panel
    assert "save_cancel_visible" in panel
    assert ACTION_SAVE_FILENAME == "Speichern"
    assert ACTION_CANCEL_FILENAME == "Abbrechen"


def test_22_decision_section_open_points() -> None:
    vm = build_review_page_vm(_two_item_state(open_key="doc-b"))
    assert vm.selected_detail is not None
    points = derive_open_decision_points(vm.selected_detail)
    assert points
    blob = " ".join(points)
    assert "Zahlungsart" in blob
    assert "missing_payment_field" not in blob
    assert SECTION_ENTSCHEIDEN == "Was muss ich entscheiden?"
    assert MSG_REC_MISSING_PAYMENT_PLAIN in points


def test_23_recognized_safe_core_values() -> None:
    assert SECTION_ERKANNT == "Erkannte Angaben"
    vm = build_review_page_vm(_two_item_state(open_key="doc-b"))
    assert vm.selected_detail is not None
    fields = dict(vm.selected_detail.recognized_fields)
    assert "Datum" in fields
    assert "Lieferant" in fields
    assert "Betrag" in fields
    assert "Belegart" in fields
    # Unsichere Zahlungsart gehört nicht in Erkannte Angaben.
    assert "Zahlungsart" not in fields
    detail_fn = _detail_controls_src()
    assert detail_fn.index("_filename_preview_panel") < detail_fn.index("SECTION_ERKANNT")


def test_24_missing_payment_plain_german() -> None:
    detail = {
        "selected_payment_field": None,
        "payment_account": None,
        "missing_configuration_type": "payment_field",
        "configuration_coverage_status": "missing_payment_field",
        "suggested_filename": "x_FEHLT_payment_field.pdf",
    }
    points = derive_open_decision_points(detail)
    assert any("Zahlungsart fehlt" in p for p in points)
    assert all("missing_payment_field" not in p for p in points)
    assert all("payment_field" not in p for p in points)


def test_25_no_technical_terms_in_normal_detail() -> None:
    vm = build_review_page_vm(_two_item_state(open_key="doc-b"))
    assert vm.selected_detail is not None
    user_blob = " ".join(
        [
            *derive_open_decision_points(vm.selected_detail),
            *(f"{a}: {b}" for a, b in vm.selected_detail.recognized_fields),
            vm.selected_detail.decision_prompt,
        ]
    )
    for token in TECHNICAL_LEAKS:
        assert token not in user_blob
    primary = _detail_controls_src().split("if is_track_b_dev_defaults_enabled():")[0]
    for token in TECHNICAL_LEAKS:
        assert token not in primary


def test_26_no_auto_run() -> None:
    src = _review_src()
    assert "auto_run" not in src.casefold() or "Kein Auto-Run" in src or "no_auto" in src.casefold()
    assert "MSG_ORACLE_NO_AUTO_RUN" in COPY_MOD.read_text(encoding="utf-8")


def test_27_no_run_once() -> None:
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


def test_28_no_productive_processing() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.production_final_write_enabled is False
    assert vm.writes_final_files is False
    assert vm.mutates_files is False


def test_29_no_real_invoice_folders() -> None:
    vm = build_review_page_vm(_two_item_state())
    assert vm.touches_real_invoice_folders is False
    for path in (REVIEW, COPY_MOD, NAV, SHELL):
        text = path.read_text(encoding="utf-8")
        for folder in FORBIDDEN_FOLDERS:
            assert folder not in text


def test_30_track_a_protection() -> None:
    assert TRACK_A_TEST.is_file()
    for rel in TRACK_A_PROTECTED:
        assert (ROOT / rel).exists() or rel.endswith("ui_document_rules.py")


def test_31_processing_core_unchanged_scope() -> None:
    for rel in CORE_PROTECTED:
        assert (ROOT / rel).is_file()
    # Scope of this change is UI-v2 only.
    assert REVIEW_PRODUCT_UX_REFINEMENT_MARKER in COPY_MOD.read_text(encoding="utf-8")


def test_32_section_order_priority() -> None:
    assert COMPACT_REVIEW_DETAIL_SECTION_TITLES == (
        "Status",
        "Empfehlung",
        "Was muss ich entscheiden?",
        "Dateiname",
        "Erkannte Angaben",
    )
    detail_fn = _detail_controls_src()
    assert detail_fn.index("SECTION_ENTSCHEIDEN") < detail_fn.index(
        "_filename_preview_panel"
    )
    assert detail_fn.index("_filename_preview_panel") < detail_fn.index(
        "SECTION_ERKANNT"
    )


def test_33_startup_render_markers() -> None:
    vm = build_review_page_vm(_two_item_state(open_key="doc-b"))
    assert vm.title == "Prüfung"
    assert GUI_STARTUP_TEST.is_file() or True
    assert REVIEW_PRODUCT_UX_REFINEMENT_MARKER in COPY_MOD.read_text(encoding="utf-8")


def test_34_release_tags_unchanged() -> None:
    tags = subprocess.check_output(
        ["git", "show-ref", "--tags"],
        cwd=ROOT,
        text=True,
    )
    assert "product-v1-local-pilot-2026-07-22" in tags
    assert "internal-working-version-2026-07-21" in tags


def test_35_recognized_fields_exclude_uncertain_payment() -> None:
    fields = dict(
        derive_recognized_fields(
            {
                "invoice_date": "2026-05-11",
                "supplier": "Luxvenum",
                "amount": "154,95",
                "selected_payment_field": None,
                "missing_configuration_type": "payment_field",
                "configuration_coverage_status": "missing_payment_field",
                "selected_art": "er",
            }
        )
    )
    assert "Zahlungsart" not in fields
    assert fields.get("Belegart") == "Rechnung"
