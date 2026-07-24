"""Track-B Review Surface Declutter (2026-07-24).

UI-v2 presentation only — no productive processing, no real invoice folders.
Uses view-models + source contracts (no live Flet page render required).
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.dev_defaults import MSG_EMPTY_REVIEW_HELP
from invoice_tool.ui_v2.pages.review import (
    MSG_ER_ER_NOTE,
    MSG_LEGACY_ER_ER_NOTE,
    build_review_page_vm,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_COPY_CASE,
    ACTION_COPY_DIAGNOSIS,
    ACTION_COPY_ORACLE,
    ACTION_OPEN_WORKSPACE,
    BADGE_MISSING_PAYMENT,
    BADGE_NOT_AMEX,
    BADGE_PAYPAL,
    BADGE_STORNO,
    MSG_SAFETY_LINE_NO_FINAL,
    MSG_WHY_MISSING_PAYMENT,
    MSG_WHY_NOT_AMEX,
    MSG_WHY_STORNO,
    ORACLE_COMMAND,
    PRIMARY_PAYPAL,
    REVIEW_DECLUTTER_LAYOUT_MARKER,
    SECTION_FINALISIERUNG,
    SECTION_KURZPRUEFUNG,
    SECTION_NAECHSTE,
    SECTION_TECHNISCHE,
    SECTION_VORSCHLAG,
    SECTION_WARUM,
    derive_why_review_plain_german,
    paypal_action_relevant,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
DEV_DEFAULTS = ROOT / "invoice_tool" / "ui_v2" / "dev_defaults.py"
DOCS = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_REVIEW_SURFACE_DECLUTTER_2026-07-24.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_REVIEW_SURFACE_DECLUTTER_2026-07-24.md"
)
ORACLE_SCRIPT = ROOT / "scripts" / "dev" / "track_b_automated_smoke_oracle.py"
ORACLE_TEST = ROOT / "tests" / "test_track_b_automated_smoke_oracle.py"
TRACK_A_TEST = ROOT / "tests" / "test_track_a_internal_app_protection.py"

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


def _state_for(
    *,
    document_name: str,
    document_id: str,
    planned: ProcessingPlannedDestination,
    reason: str = "Prüfung erforderlich",
) -> UiV2State:
    run = ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="declutter-review-1",
        review_items=(
            ProcessingReviewItem(
                document_name=document_name,
                reason=reason,
                status_label="unklar",
                document_id=document_id,
            ),
        ),
        planned_destinations=(planned,),
        planned_destination_count=1,
        outcome_kind="all_review",
    )
    state = UiV2State(processing_run_state=run)
    state.review_preview_ui.selected_item_key = document_id
    return state


def _paypal_state() -> UiV2State:
    return _state_for(
        document_name="FA011466.pdf",
        document_id="doc-paypal",
        planned=_planned(),
        reason="PayPal-Regel fehlt",
    )


def _boettcher_card_state() -> UiV2State:
    return _state_for(
        document_name="320262919974.pdf",
        document_id="doc-card",
        planned=_planned(
            document_name="320262919974.pdf",
            suggested_filename="2026-05-23_er_Böttcher_AG_84,39_card.pdf",
            supplier="Böttcher AG",
            counterparty_name="Böttcher AG",
            invoice_date="2026-05-23",
            amount="84,39",
            selected_amount="84,39",
            selected_payment_field="card",
            payment_account="card",
            matched_configuration_name="Unklar",
            missing_configuration_type="generic_card",
            configuration_coverage_status="no_safe_card_configuration",
            user_guidance=(
                "Kreditkarte erkannt, aber AMEX nicht belegt; keine passende "
                "Nicht-AMEX-Karten-Konfiguration vorhanden."
            ),
        ),
        reason="Kartenzahlung — AMEX nicht belegt",
    )


def _missing_payment_state() -> UiV2State:
    return _state_for(
        document_name="Rechnung-2026156019-102201.pdf",
        document_id="doc-missing",
        planned=_planned(
            document_name="Rechnung-2026156019-102201.pdf",
            suggested_filename=(
                "2026-05-11_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf"
            ),
            supplier="Luxvenum LED GmbH",
            counterparty_name="Luxvenum LED GmbH",
            selected_payment_field=None,
            payment_account=None,
            matched_configuration_name="Unklar",
            missing_configuration_type="payment_field",
            configuration_coverage_status="missing_payment_field",
            user_guidance=(
                "Zahlungsfeld nicht sicher erkannt; Konfiguration konnte deshalb "
                "nicht eindeutig gewählt werden."
            ),
        ),
        reason="Zahlungsfeld fehlt",
    )


def _storno_state() -> UiV2State:
    return _state_for(
        document_name="420260091336.pdf",
        document_id="doc-storno",
        planned=_planned(
            document_name="420260091336.pdf",
            suggested_filename=(
                "2026-06-18_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
            ),
            supplier="Böttcher AG",
            counterparty_name="Böttcher AG",
            invoice_date="2026-06-18",
            amount="68,94",
            selected_amount="68,94",
            selected_art="storno",
            document_type="storno",
            selected_payment_field=None,
            payment_account=None,
            matched_configuration_name="Unklar",
            missing_configuration_type="payment_field",
            configuration_coverage_status="missing_payment_field",
            user_guidance="Storno erkannt; Zahlungsfeld fehlt.",
        ),
        reason="Storno zur Prüfung",
    )


def test_01_review_list_exposes_compact_document_cards() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.list_items
    row = vm.list_items[0]
    assert row.compact_card is True
    assert row.source_filename.endswith(".pdf")
    assert row.supplier
    assert row.invoice_date
    assert row.amount
    assert row.payment_field
    assert row.document_art
    assert row.configuration
    assert row.status_badges
    assert row.suggested_filename
    assert row.primary_action
    assert MSG_SAFETY_LINE_NO_FINAL in row.safety_line
    src = REVIEW.read_text(encoding="utf-8")
    assert "Kompakte Review-Karten" in src
    assert "Lieferant / Name" in src


def test_02_detail_exposes_kurzpruefung_section() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    assert SECTION_KURZPRUEFUNG in vm.selected_detail.section_titles
    labels = {label for label, _ in vm.selected_detail.kurzpruefung_fields}
    assert "Originaldatei" in labels
    assert "erkannter Lieferant" in labels
    assert "SECTION_KURZPRUEFUNG" in REVIEW.read_text(encoding="utf-8")


def test_03_detail_exposes_vorschlag_section() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    assert SECTION_VORSCHLAG in vm.selected_detail.section_titles
    assert any("Dateiname" in k for k, _ in vm.selected_detail.vorschlag_fields)
    assert "SECTION_VORSCHLAG" in REVIEW.read_text(encoding="utf-8")


def test_04_detail_exposes_warum_section() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    assert SECTION_WARUM in vm.selected_detail.section_titles
    assert vm.selected_detail.why_review_plain
    assert "SECTION_WARUM" in REVIEW.read_text(encoding="utf-8")


def test_05_detail_exposes_naechste_aktion_section() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    assert SECTION_NAECHSTE in vm.selected_detail.section_titles
    assert vm.selected_detail.next_action_labels_relevant
    assert "_next_action_row" in REVIEW.read_text(encoding="utf-8")


def test_06_detail_exposes_finalisierung_section() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.selected_detail is not None
    assert SECTION_FINALISIERUNG in vm.selected_detail.section_titles
    assert any(
        "final_write_allowed=false" in line
        for line in vm.selected_detail.finalization_summary_lines
    )
    assert "_finalization_declutter_panel" in REVIEW.read_text(encoding="utf-8")


def test_07_technical_details_collapsed_by_default() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.technical_details_collapsed_by_default is True
    assert vm.selected_detail is not None
    assert vm.selected_detail.technical_details_collapsed_by_default is True
    src = REVIEW.read_text(encoding="utf-8")
    assert "initially_expanded=False" in src
    assert "SECTION_TECHNISCHE" in src
    assert SECTION_TECHNISCHE == "Technische Details"


def test_08_paypal_action_visible_only_when_relevant() -> None:
    paypal_vm = build_review_page_vm(_paypal_state())
    assert paypal_vm.selected_detail is not None
    assert paypal_vm.selected_detail.paypal_action_visible is True
    assert paypal_vm.list_items[0].primary_action == PRIMARY_PAYPAL
    assert paypal_action_relevant(paypal_vm.selected_detail) is True

    card_vm = build_review_page_vm(_boettcher_card_state())
    assert card_vm.selected_detail is not None
    assert card_vm.selected_detail.paypal_action_visible is False


def test_09_boettcher_card_shows_not_amex_explanation() -> None:
    vm = build_review_page_vm(_boettcher_card_state())
    assert vm.selected_detail is not None
    assert BADGE_NOT_AMEX in vm.selected_detail.status_badges
    why = " ".join(vm.selected_detail.why_review_plain)
    assert MSG_WHY_NOT_AMEX in why or "AMEX" in why
    assert "amex" not in (vm.selected_detail.matched_configuration_name or "").casefold()


def test_10_missing_payment_plain_german() -> None:
    vm = build_review_page_vm(_missing_payment_state())
    assert vm.selected_detail is not None
    assert BADGE_MISSING_PAYMENT in vm.selected_detail.status_badges
    why = derive_why_review_plain_german(vm.selected_detail)
    assert MSG_WHY_MISSING_PAYMENT in why or any(
        "Zahlungsfeld" in line for line in why
    )


def test_11_storno_plain_german() -> None:
    vm = build_review_page_vm(_storno_state())
    assert vm.selected_detail is not None
    assert BADGE_STORNO in vm.selected_detail.status_badges
    why = " ".join(vm.selected_detail.why_review_plain)
    assert MSG_WHY_STORNO in why or "Storno" in why


def test_12_safety_line_visible() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert MSG_SAFETY_LINE_NO_FINAL in vm.safety_line_declutter
    assert "keine finalen Dateien geschrieben" in MSG_SAFETY_LINE_NO_FINAL
    assert "MSG_SAFETY_LINE_NO_FINAL" in REVIEW.read_text(encoding="utf-8")
    assert vm.list_items[0].safety_line == MSG_SAFETY_LINE_NO_FINAL


def test_13_oracle_command_copy_available() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert ACTION_COPY_ORACLE in vm.copy_action_labels
    assert ORACLE_COMMAND == vm.oracle_command
    assert "track_b_automated_smoke_oracle.py" in vm.oracle_command
    src = REVIEW.read_text(encoding="utf-8")
    assert "ACTION_COPY_ORACLE" in src
    assert "_oracle_dev_box" in src


def test_14_prueffall_copy_available() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert ACTION_COPY_CASE in vm.copy_action_labels
    assert ACTION_COPY_CASE == "Prüffall als Text kopieren"
    assert "ACTION_COPY_CASE" in REVIEW.read_text(encoding="utf-8")


def test_15_technical_diagnosis_copy_available() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert ACTION_COPY_DIAGNOSIS in vm.copy_action_labels
    assert ACTION_COPY_DIAGNOSIS == "Technische Diagnose kopieren"
    assert "ACTION_COPY_DIAGNOSIS" in REVIEW.read_text(encoding="utf-8")


def test_16_empty_state_explains_preview_or_oracle() -> None:
    state = UiV2State()
    vm = build_review_page_vm(state)
    assert vm.empty is True
    assert ACTION_OPEN_WORKSPACE in vm.empty_state_workspace_action
    assert ACTION_COPY_ORACLE in vm.empty_state_oracle_action
    assert "Oracle" in MSG_EMPTY_REVIEW_HELP
    assert "Prüffälle" in MSG_EMPTY_REVIEW_HELP
    src = REVIEW.read_text(encoding="utf-8")
    assert "ACTION_OPEN_WORKSPACE" in src
    assert "MSG_EMPTY_REVIEW_HELP" in src


def test_17_er_er_filename_note_when_applicable() -> None:
    """``_er_er_`` is legacy-only; current names must not contain it."""

    current = build_review_page_vm(_paypal_state())
    assert current.selected_detail is not None
    assert current.selected_detail.er_er_note is None
    assert "_er_er_" not in (current.selected_detail.suggested_filename or "")

    legacy = build_review_page_vm(
        _state_for(
            document_name="legacy-er-er.pdf",
            document_id="doc-legacy-er-er",
            planned=_planned(
                document_name="legacy-er-er.pdf",
                suggested_filename=(
                    "2026-05-11_er_er_LUMITOP_476,00_paypal.pdf"
                ),
            ),
        )
    )
    assert legacy.selected_detail is not None
    assert legacy.selected_detail.er_er_note == MSG_LEGACY_ER_ER_NOTE
    assert legacy.selected_detail.er_er_note == MSG_ER_ER_NOTE
    assert "_er_er_" in (legacy.selected_detail.suggested_filename or "")
    assert "Altes technisches Muster aus früherem Preview-Export." in (
        legacy.selected_detail.er_er_note or ""
    )
    src = REVIEW.read_text(encoding="utf-8")
    assert "MSG_LEGACY_ER_ER_NOTE" in src
    assert "MSG_ER_ER_NOTE" in src


def test_18_no_auto_run() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.auto_runs_oracle is False
    src = REVIEW.read_text(encoding="utf-8")
    assert "nicht automatisch" in src or "Kein Auto-Run" in src
    assert "run_automated_smoke_oracle(" not in src


def test_19_no_run_once() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.calls_run_once is False
    src = REVIEW.read_text(encoding="utf-8")
    tree = ast.parse(src)
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


def test_20_no_production_final_write() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.production_final_write_enabled is False
    assert vm.writes_final_files is False
    assert vm.selected_detail is not None
    assert vm.selected_detail.final_write_allowed is False


def test_21_no_real_invoice_folders() -> None:
    vm = build_review_page_vm(_paypal_state())
    assert vm.touches_real_invoice_folders is False
    for path in (REVIEW, COPY_MOD, DEV_DEFAULTS):
        src = path.read_text(encoding="utf-8")
        for folder in FORBIDDEN_FOLDERS:
            assert folder not in src


def test_22_track_a_protection_still_passes() -> None:
    assert TRACK_A_TEST.is_file()
    import tests.test_track_a_internal_app_protection as track_a

    assert hasattr(track_a, "TRACK_A_PROTECTED")
    for rel in TRACK_A_PROTECTED:
        assert (ROOT / rel).exists() or rel.endswith("ui_document_rules.py")
    for rel in CORE_PROTECTED:
        assert (ROOT / rel).is_file()


def test_23_automated_smoke_oracle_test_still_present() -> None:
    assert ORACLE_SCRIPT.is_file()
    assert ORACLE_TEST.is_file()
    src = ORACLE_TEST.read_text(encoding="utf-8")
    assert "TRACK_B_AUTOMATED_SMOKE_ORACLE" in src or "automated_smoke_oracle" in src


def test_docs_and_marker_present() -> None:
    assert DOCS.is_file()
    assert AUDIT.is_file()
    assert REVIEW_DECLUTTER_LAYOUT_MARKER in COPY_MOD.read_text(encoding="utf-8")
    assert "REVIEW_DECLUTTER_LAYOUT_MARKER" in REVIEW.read_text(encoding="utf-8")
    assert BADGE_PAYPAL == "PayPal"
