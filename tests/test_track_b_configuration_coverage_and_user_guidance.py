"""Track-B configuration coverage and user guidance (Prompt 23/34)."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from invoice_tool.ui_v2.configuration_guidance import (
    MSG_ACTION_GENERIC_CARD,
    MSG_ACTION_MISSING_PAYMENT,
    MSG_ACTION_PAYPAL,
    MSG_FIELD_CONFIGURATION_COVERAGE,
    MSG_FIELD_SUGGESTED_ACTION,
    MSG_FIELD_USER_GUIDANCE,
    MSG_GUIDANCE_GENERIC_CARD,
    MSG_GUIDANCE_MISSING_PAYMENT,
    MSG_GUIDANCE_PAYPAL,
    STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT,
    STATUS_MISSING_PAYMENT_FIELD,
    STATUS_NO_SAFE_CARD_CONFIGURATION,
    derive_configuration_coverage_guidance,
)
from invoice_tool.ui_v2.configuration_matching import (
    ConfigurationCandidate,
    configurations_from_raw,
    match_active_configuration,
)
from invoice_tool.ui_v2.extraction_mapping import (
    enrich_planned_destinations_with_local_extraction,
)
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.preview_export import (
    MSG_FIELD_SUGGESTED_CONFIGURATION_ACTION,
    text_claims_forbidden_maturity,
    write_preview_export_package,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State

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
PDF = {
    "lumitop": "FA011466.pdf",
    "bootshop": "Rechnung RE-202605-14594.pdf",
    "boettcher": "320262919974.pdf",
    "luxvenum": "Rechnung-2026156019-102201.pdf",
    "storno": "420260091336.pdf",
}
PATTERN = "{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf"
GUIDANCE_MODULE = ROOT / "invoice_tool" / "ui_v2" / "configuration_guidance.py"
PROFILE_STORE = ROOT / "invoice_tool" / "profile_store.py"


def _require_controlled() -> None:
    if not CONTROLLED_INPUT.is_dir() or not CONTROLLED_OUTPUT.is_dir():
        pytest.skip("controlled KI-Rechnungen-Test folders missing")


def _digest_tree(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(folder))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return out


def _unmatched() -> ConfigurationCandidate:
    return ConfigurationCandidate(
        configuration_id="unmatched",
        name="Unklar",
        active=True,
        is_unmatched=True,
        filename_pattern=PATTERN,
    )


def _amex_config(*, active: bool = True) -> dict:
    return {
        "id": "amex",
        "name": "American Express",
        "active": active,
        "feature_key": "payment_field",
        "values": ["amex", "American Express"],
        "filename_pattern": PATTERN,
    }


def _paypal_guidance():
    return derive_configuration_coverage_guidance(
        selected_payment_field="paypal",
        matched_configuration_name="Unklar",
        is_unmatched_fallback=True,
        matched_configuration_reason=(
            "payment_field paypal detected, but no active configuration supports PayPal"
        ),
        missing_configuration_rule="keine aktive PayPal-Konfiguration",
    )


def _card_guidance():
    return derive_configuration_coverage_guidance(
        selected_payment_field="card",
        matched_configuration_name="Unklar",
        is_unmatched_fallback=True,
        matched_configuration_reason="generic credit card detected, AMEX not proven",
        missing_configuration_rule=(
            "kein AMEX-Nachweis / keine passende Nicht-AMEX-Karten-Konfiguration"
        ),
    )


def _missing_payment_guidance():
    return derive_configuration_coverage_guidance(
        selected_payment_field=None,
        matched_configuration_name="Unklar",
        is_unmatched_fallback=True,
        matched_configuration_reason="payment_field fehlt — keine Zahlungsart erkannt",
        missing_configuration_rule="payment_field fehlt",
        absent_pattern_slots=("payment_field",),
    )


def test_01_paypal_without_config_status() -> None:
    match = match_active_configuration(
        payment_field="paypal",
        configurations=configurations_from_raw([_amex_config()]),
        unmatched=_unmatched(),
    )
    fields = match.transparency_fields()
    assert (
        fields["configuration_coverage_status"]
        == STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT
    )
    assert fields["missing_configuration_type"] == "paypal"


def test_02_paypal_guidance_mentions_paypal_and_no_active_config() -> None:
    guidance = _paypal_guidance()
    assert "PayPal" in guidance.user_guidance
    assert "keine aktive PayPal-Konfiguration" in guidance.user_guidance
    assert guidance.user_guidance == MSG_GUIDANCE_PAYPAL


def test_03_paypal_suggested_action_add_or_manual() -> None:
    guidance = _paypal_guidance()
    assert guidance.suggested_configuration_action == MSG_ACTION_PAYPAL
    assert "PayPal-Konfiguration ergänzen" in guidance.suggested_configuration_action
    assert "manuell prüfen" in guidance.suggested_configuration_action


def test_04_generic_card_without_amex_status() -> None:
    match = match_active_configuration(
        payment_field="card",
        configurations=configurations_from_raw([_amex_config()]),
        unmatched=_unmatched(),
    )
    fields = match.transparency_fields()
    assert fields["configuration_coverage_status"] == STATUS_NO_SAFE_CARD_CONFIGURATION
    assert fields["missing_configuration_type"] == "generic_card"


def test_05_generic_card_guidance_amex_not_proven() -> None:
    guidance = _card_guidance()
    assert guidance.user_guidance == MSG_GUIDANCE_GENERIC_CARD
    assert "AMEX nicht belegt" in guidance.user_guidance


def test_06_generic_card_does_not_recommend_amex_matching() -> None:
    guidance = _card_guidance()
    action = guidance.suggested_configuration_action.lower()
    assert guidance.suggested_configuration_action == MSG_ACTION_GENERIC_CARD
    assert "amex match" not in action
    assert "american express zuordnen" not in action
    assert "als amex" not in action


def test_07_missing_payment_field_status() -> None:
    match = match_active_configuration(
        payment_field=None,
        configurations=configurations_from_raw([_amex_config()]),
        unmatched=_unmatched(),
    )
    fields = match.transparency_fields()
    assert fields["configuration_coverage_status"] == STATUS_MISSING_PAYMENT_FIELD
    assert fields["missing_configuration_type"] == "payment_field"


def test_08_missing_payment_guidance_text() -> None:
    guidance = _missing_payment_guidance()
    assert guidance.user_guidance == MSG_GUIDANCE_MISSING_PAYMENT
    assert "Zahlungsfeld nicht sicher erkannt" in guidance.user_guidance
    assert guidance.suggested_configuration_action == MSG_ACTION_MISSING_PAYMENT


def test_09_10_11_12_manifest_includes_guidance_fields(tmp_path: Path) -> None:
    _require_controlled()
    sandbox_in = tmp_path / "KI-Rechnungen-Test" / "input"
    sandbox_out = tmp_path / "KI-Rechnungen-Test" / "output"
    sandbox_in.mkdir(parents=True)
    sandbox_out.mkdir(parents=True)
    name = PDF["lumitop"]
    (sandbox_in / name).write_bytes((CONTROLLED_INPUT / name).read_bytes())
    match = match_active_configuration(
        payment_field="paypal",
        configurations=configurations_from_raw([_amex_config()]),
        unmatched=_unmatched(),
    )
    guidance = match.transparency_fields()
    planned = (
        ProcessingPlannedDestination(
            document_name=name,
            planned_path=f"geplant/{name}",
            preview_only=True,
            matched_configuration_name=match.matched_configuration_name,
            matched_configuration_reason=match.matched_configuration_reason,
            available_configurations=match.available_configurations,
            evaluated_configuration_candidates=match.evaluated_configuration_candidates,
            unmatched_reasons=match.unmatched_reasons,
            condition_results=match.condition_results,
            missing_configuration_rule=match.missing_configuration_rule,
            selected_payment_field="paypal",
            configuration_coverage_status=guidance["configuration_coverage_status"],
            missing_configuration_type=guidance["missing_configuration_type"],
            user_guidance=guidance["user_guidance"],
            suggested_configuration_action=guidance[
                "suggested_configuration_action"
            ],
            guidance_severity=guidance["guidance_severity"],
        ),
    )
    result = write_preview_export_package(
        ProcessingRunState(
            status="completed",
            run_id="prompt23-manifest",
            review_items=(
                ProcessingReviewItem(
                    document_id=name,
                    document_name=name,
                    reason="review",
                    status_label="unklar",
                ),
            ),
            planned_destinations=planned,
            planned_destination_count=1,
        ),
        input_root=sandbox_in,
        output_root=sandbox_out,
    )
    assert result.ok and result.export_folder
    item = json.loads(
        (result.export_folder / "manifest.json").read_text(encoding="utf-8")
    )["items"][0]
    assert item["configuration_coverage_status"] == STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT
    assert item["missing_configuration_type"] == "paypal"
    assert item["user_guidance"]
    assert item["suggested_configuration_action"]


def test_13_review_items_include_user_guidance(tmp_path: Path) -> None:
    _require_controlled()
    sandbox_in = tmp_path / "KI-Rechnungen-Test" / "input"
    sandbox_out = tmp_path / "KI-Rechnungen-Test" / "output"
    sandbox_in.mkdir(parents=True)
    sandbox_out.mkdir(parents=True)
    name = PDF["bootshop"]
    (sandbox_in / name).write_bytes((CONTROLLED_INPUT / name).read_bytes())
    match = match_active_configuration(
        payment_field="paypal",
        configurations=configurations_from_raw([_amex_config()]),
        unmatched=_unmatched(),
    )
    guidance = match.transparency_fields()
    result = write_preview_export_package(
        ProcessingRunState(
            status="completed",
            run_id="prompt23-review-md",
            review_items=(
                ProcessingReviewItem(
                    document_id=name,
                    document_name=name,
                    reason="review",
                    status_label="unklar",
                ),
            ),
            planned_destinations=(
                ProcessingPlannedDestination(
                    document_name=name,
                    planned_path=f"geplant/{name}",
                    preview_only=True,
                    selected_payment_field="paypal",
                    matched_configuration_name=match.matched_configuration_name,
                    matched_configuration_reason=match.matched_configuration_reason,
                    evaluated_configuration_candidates=(
                        match.evaluated_configuration_candidates
                    ),
                    user_guidance=guidance["user_guidance"],
                    configuration_coverage_status=guidance[
                        "configuration_coverage_status"
                    ],
                    suggested_configuration_action=guidance[
                        "suggested_configuration_action"
                    ],
                    missing_configuration_type=guidance["missing_configuration_type"],
                ),
            ),
            planned_destination_count=1,
        ),
        input_root=sandbox_in,
        output_root=sandbox_out,
    )
    assert result.ok and result.export_folder
    review_md = (result.export_folder / "review-items.md").read_text(encoding="utf-8")
    assert MSG_FIELD_USER_GUIDANCE in review_md
    assert "PayPal erkannt" in review_md
    assert MSG_FIELD_CONFIGURATION_COVERAGE in review_md


def test_14_15_16_ui_report_exposes_coverage_labels() -> None:
    match = match_active_configuration(
        payment_field="paypal",
        configurations=configurations_from_raw([_amex_config()]),
        unmatched=_unmatched(),
    )
    guidance = match.transparency_fields()
    planned = ProcessingPlannedDestination(
        document_name="FA011466.pdf",
        planned_path="geplant/FA011466.pdf",
        preview_only=True,
        matched_configuration_name=match.matched_configuration_name,
        matched_configuration_reason=match.matched_configuration_reason,
        condition_results=match.condition_results,
        evaluated_configuration_candidates=match.evaluated_configuration_candidates,
        selected_payment_field="paypal",
        configuration_coverage_status=guidance["configuration_coverage_status"],
        missing_configuration_type=guidance["missing_configuration_type"],
        user_guidance=guidance["user_guidance"],
        suggested_configuration_action=guidance["suggested_configuration_action"],
        guidance_severity=guidance["guidance_severity"],
    )
    state = UiV2State()
    state.processing_run_state = ProcessingRunState(
        status="completed",
        run_id="prompt23-ui",
        review_items=(
            ProcessingReviewItem(
                document_id="FA011466.pdf",
                document_name="FA011466.pdf",
                reason="review",
                status_label="unklar",
            ),
        ),
        planned_destinations=(planned,),
        planned_destination_count=1,
        detailed_item_mapping_complete=True,
    )
    state.review_selected_item_key = "FA011466.pdf"
    vm = build_review_page_vm(state)
    assert vm.selected_detail is not None
    detail = vm.selected_detail
    assert detail.configuration_coverage_status == STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT
    assert detail.user_guidance
    assert detail.suggested_configuration_action
    assert MSG_FIELD_CONFIGURATION_COVERAGE == "Konfigurationsabdeckung"
    assert MSG_FIELD_USER_GUIDANCE == "Nutzerhinweis"
    assert MSG_FIELD_SUGGESTED_ACTION == "vorgeschlagene Aktion"
    assert MSG_FIELD_SUGGESTED_CONFIGURATION_ACTION == "vorgeschlagene Aktion"


def test_17_18_guidance_does_not_claim_saas_or_production_ready() -> None:
    source = GUIDANCE_MODULE.read_text(encoding="utf-8")
    assert "saas-ready" not in source.lower()
    assert "production-ready" not in source.lower()
    assert "saas ready" not in source.lower()
    assert "production ready" not in source.lower()
    docs = list(
        (ROOT / "docs").glob("*CONFIGURATION_COVERAGE_AND_USER_GUIDANCE*")
    ) + list(
        (ROOT / "docs" / "audits").glob("*CONFIGURATION_COVERAGE_AND_USER_GUIDANCE*")
    )
    for path in docs:
        assert not text_claims_forbidden_maturity(path.read_text(encoding="utf-8"))


def test_19_no_user_config_created_or_edited() -> None:
    source = GUIDANCE_MODULE.read_text(encoding="utf-8")
    forbidden = (
        "save_profile",
        "write_profile",
        "create_configuration",
        "update_configuration",
        "profile_store.save",
        "dump(",
        "Path.write_text",
    )
    for token in forbidden:
        assert token not in source
    before = PROFILE_STORE.stat().st_mtime_ns if PROFILE_STORE.exists() else None
    _ = derive_configuration_coverage_guidance(selected_payment_field="paypal")
    after = PROFILE_STORE.stat().st_mtime_ns if PROFILE_STORE.exists() else None
    assert before == after


def test_20_copied_pdfs_remain_byte_identical(tmp_path: Path) -> None:
    _require_controlled()
    sandbox_in = tmp_path / "KI-Rechnungen-Test" / "input"
    sandbox_out = tmp_path / "KI-Rechnungen-Test" / "output"
    sandbox_in.mkdir(parents=True)
    sandbox_out.mkdir(parents=True)
    name = PDF["boettcher"]
    raw = (CONTROLLED_INPUT / name).read_bytes()
    (sandbox_in / name).write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    planned = enrich_planned_destinations_with_local_extraction(
        (
            ProcessingPlannedDestination(
                document_name=name,
                planned_path=f"x/{name}",
                preview_only=True,
            ),
        ),
        input_folder=sandbox_in,
    )
    result = write_preview_export_package(
        ProcessingRunState(
            status="completed",
            run_id="prompt23-bytes",
            review_items=(
                ProcessingReviewItem(
                    document_id=name,
                    document_name=name,
                    reason="r",
                    status_label="unklar",
                ),
            ),
            planned_destinations=planned,
            planned_destination_count=1,
        ),
        input_root=sandbox_in,
        output_root=sandbox_out,
    )
    assert result.ok
    assert result.items[0].source_sha256 == digest
    assert result.items[0].preview_sha256 == digest
    assert result.items[0].configuration_coverage_status in {
        STATUS_NO_SAFE_CARD_CONFIGURATION,
        STATUS_MISSING_PAYMENT_FIELD,
        STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT,
        "unmatched_other",
        "covered",
    }


def test_21_input_files_are_not_mutated() -> None:
    _require_controlled()
    before = _digest_tree(CONTROLLED_INPUT)
    _ = derive_configuration_coverage_guidance(selected_payment_field="paypal")
    _ = match_active_configuration(payment_field="card")
    after = _digest_tree(CONTROLLED_INPUT)
    assert before == after


def test_22_output_outside_controlled_folder_blocked(tmp_path: Path) -> None:
    _require_controlled()
    bad_out = tmp_path / "not-controlled-output"
    bad_out.mkdir()
    result = write_preview_export_package(
        ProcessingRunState(
            status="completed",
            run_id="blocked",
            review_items=(
                ProcessingReviewItem(
                    document_id="x.pdf",
                    document_name="x.pdf",
                    reason="r",
                    status_label="unklar",
                ),
            ),
        ),
        input_root=CONTROLLED_INPUT,
        output_root=bad_out,
    )
    assert result.ok is False


def test_23_productive_original_folders_remain_blocked() -> None:
    for folder in FORBIDDEN_FOLDERS:
        result = write_preview_export_package(
            ProcessingRunState(status="completed", run_id="x"),
            input_root=folder,
            output_root=CONTROLLED_OUTPUT,
        )
        assert result.ok is False


def test_24_run_once_not_called() -> None:
    source = GUIDANCE_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "run_once":
                pytest.fail("run_once must not be called")
            if isinstance(node.func, ast.Attribute) and node.func.attr == "run_once":
                pytest.fail("run_once must not be called")


def test_25_no_final_write_move_archive_delete_behavior() -> None:
    source = GUIDANCE_MODULE.read_text(encoding="utf-8")
    for token in ("shutil.move", "os.remove", "Path.unlink", "shutil.rmtree"):
        assert token not in source


def test_26_no_real_invoice_folders_touched() -> None:
    source = GUIDANCE_MODULE.read_text(encoding="utf-8")
    for folder in FORBIDDEN_FOLDERS:
        assert folder not in source


def test_27_track_a_protection_still_passes() -> None:
    for path in PROTECTED_TRACK_A + PROCESSING_CORE:
        assert path.exists()
    import tests.test_track_a_internal_app_protection as protection

    protection.test_track_a_protected_files_unchanged_vs_head()
    protection.test_processing_core_unchanged_vs_head()
    protection.test_protected_track_a_and_core_not_staged()


def test_controlled_five_pdf_guidance_cases(tmp_path: Path) -> None:
    """Controlled 5-PDF verification: PayPal / card / missing payment guidance."""

    _require_controlled()
    sandbox_in = tmp_path / "KI-Rechnungen-Test" / "input"
    sandbox_out = tmp_path / "KI-Rechnungen-Test" / "output"
    sandbox_in.mkdir(parents=True)
    sandbox_out.mkdir(parents=True)
    for name in PDF.values():
        (sandbox_in / name).write_bytes((CONTROLLED_INPUT / name).read_bytes())
    planned = enrich_planned_destinations_with_local_extraction(
        tuple(
            ProcessingPlannedDestination(
                document_name=name,
                planned_path=f"geplant/{name}",
                preview_only=True,
            )
            for name in PDF.values()
        ),
        input_folder=sandbox_in,
    )
    result = write_preview_export_package(
        ProcessingRunState(
            status="completed",
            run_id="prompt23-five",
            review_items=tuple(
                ProcessingReviewItem(
                    document_id=name,
                    document_name=name,
                    reason="review",
                    status_label="unklar",
                )
                for name in PDF.values()
            ),
            planned_destinations=planned,
            planned_destination_count=len(planned),
            detailed_item_mapping_complete=True,
        ),
        input_root=sandbox_in,
        output_root=sandbox_out,
    )
    assert result.ok and result.export_folder
    by_name = {item.source_filename: item for item in result.items}
    for paypal_name in (PDF["lumitop"], PDF["bootshop"]):
        item = by_name[paypal_name]
        assert item.configuration_coverage_status == (
            STATUS_MISSING_CONFIG_FOR_DETECTED_PAYMENT
        )
        assert "PayPal" in (item.user_guidance or "")
    card = by_name[PDF["boettcher"]]
    assert card.configuration_coverage_status == STATUS_NO_SAFE_CARD_CONFIGURATION
    assert "AMEX nicht belegt" in (card.user_guidance or "")
    for missing_name in (PDF["luxvenum"], PDF["storno"]):
        item = by_name[missing_name]
        assert item.configuration_coverage_status == STATUS_MISSING_PAYMENT_FIELD
        assert "Zahlungsfeld nicht sicher erkannt" in (item.user_guidance or "")
    review_md = (result.export_folder / "review-items.md").read_text(encoding="utf-8")
    assert MSG_FIELD_CONFIGURATION_COVERAGE in review_md
    assert MSG_FIELD_USER_GUIDANCE in review_md
    assert MSG_FIELD_SUGGESTED_CONFIGURATION_ACTION in review_md
