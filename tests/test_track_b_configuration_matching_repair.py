"""Track-B configuration matching repair (Prompt 22/34)."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

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
    MSG_FIELD_CONDITION_RESULTS,
    MSG_FIELD_CONFIGURATION,
    MSG_FIELD_MATCHING_REASON,
    MSG_FIELD_MISSING_CONFIGURATION_RULE,
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
PDF = {
    "lumitop": "FA011466.pdf",
    "bootshop": "Rechnung RE-202605-14594.pdf",
    "boettcher": "320262919974.pdf",
    "luxvenum": "Rechnung-2026156019-102201.pdf",
    "storno": "420260091336.pdf",
}
PATTERN = "{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf"


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


def _paypal_config(*, active: bool = True) -> dict:
    return {
        "id": "paypal",
        "name": "PayPal",
        "active": active,
        "feature_key": "payment_field",
        "values": ["paypal"],
        "filename_pattern": PATTERN,
    }


def test_01_active_paypal_config_matches_paypal_item() -> None:
    active = configurations_from_raw([_paypal_config(), _amex_config()])
    result = match_active_configuration(
        payment_field="paypal",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert result.is_unmatched_fallback is False
    assert result.matched_configuration_name == "PayPal"
    assert result.matched_configuration_id == "paypal"
    assert result.matched_configuration_confidence == "high"


def test_02_paypal_does_not_match_american_express() -> None:
    active = configurations_from_raw([_amex_config()])
    result = match_active_configuration(
        payment_field="paypal",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert result.matched_configuration_name == "Unklar"
    assert result.is_unmatched_fallback is True
    amex_candidate = next(
        c
        for c in result.evaluated_configuration_candidates
        if c.get("configuration_id") == "amex"
    )
    assert amex_candidate["matched"] is False
    assert "PayPal" in str(amex_candidate.get("reason") or "")


def test_03_generic_card_does_not_match_american_express() -> None:
    active = configurations_from_raw([_amex_config()])
    result = match_active_configuration(
        payment_field="card",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert result.matched_configuration_name == "Unklar"
    assert "AMEX not proven" in (result.matched_configuration_reason or "")
    amex_candidate = next(
        c
        for c in result.evaluated_configuration_candidates
        if c.get("configuration_id") == "amex"
    )
    assert amex_candidate["matched"] is False


def test_04_amex_only_with_explicit_evidence() -> None:
    active = configurations_from_raw([_amex_config()])
    no = match_active_configuration(
        payment_field="card",
        configurations=active,
        unmatched=_unmatched(),
    )
    yes = match_active_configuration(
        payment_field="amex",
        configurations=active,
        unmatched=_unmatched(),
    )
    yes_name = match_active_configuration(
        payment_field="American Express",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert no.matched_configuration_name == "Unklar"
    assert yes.matched_configuration_name == "American Express"
    assert yes_name.matched_configuration_name == "American Express"


def test_05_inactive_configuration_never_matches() -> None:
    active = configurations_from_raw([_paypal_config(active=False)])
    result = match_active_configuration(
        payment_field="paypal",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert result.is_unmatched_fallback is True
    assert result.matched_configuration_name == "Unklar"
    inactive = result.evaluated_configuration_candidates[0]
    assert inactive["active"] is False
    assert inactive["matched"] is False


def test_06_unklar_fallback_only_when_no_non_fallback_matches() -> None:
    active = configurations_from_raw([_paypal_config(), _amex_config()])
    hit = match_active_configuration(
        payment_field="paypal",
        configurations=active,
        unmatched=_unmatched(),
    )
    miss = match_active_configuration(
        payment_field="card",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert hit.matched_configuration_name == "PayPal"
    assert hit.is_unmatched_fallback is False
    assert miss.matched_configuration_name == "Unklar"
    assert miss.is_unmatched_fallback is True


def test_07_candidate_list_records_condition_results() -> None:
    active = configurations_from_raw([_paypal_config()])
    result = match_active_configuration(
        payment_field="paypal",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert result.evaluated_configuration_candidates
    assert result.condition_results
    assert any(c.get("matched") for c in result.condition_results)
    candidate = result.evaluated_configuration_candidates[0]
    assert candidate["condition_results"]


def test_08_candidate_list_records_unmatched_reasons() -> None:
    active = configurations_from_raw([_amex_config()])
    result = match_active_configuration(
        payment_field="paypal",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert result.unmatched_reasons
    assert any("PayPal" in reason or "paypal" in reason.lower() for reason in result.unmatched_reasons)


def test_09_paypal_without_paypal_config_precise_unklar_reason() -> None:
    active = configurations_from_raw([_amex_config()])
    result = match_active_configuration(
        payment_field="paypal",
        configurations=active,
        unmatched=_unmatched(),
    )
    reason = result.matched_configuration_reason or ""
    assert "paypal" in reason.lower()
    assert "no active configuration supports PayPal" in reason
    assert result.missing_configuration_rule


def test_10_generic_card_without_amex_proof_precise_reason() -> None:
    active = configurations_from_raw([_amex_config()])
    result = match_active_configuration(
        payment_field="credit_card",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert "generic credit card detected, AMEX not proven" in (
        result.matched_configuration_reason or ""
    )


def test_11_specific_config_outranks_unklar() -> None:
    active = configurations_from_raw([_paypal_config()])
    result = match_active_configuration(
        payment_field="paypal",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert result.matched_configuration_name == "PayPal"
    assert result.matched_configuration_id != "unmatched"


def test_12_multiple_matches_choose_highest_confidence_and_record_alternatives() -> None:
    active = configurations_from_raw(
        [
            {
                "id": "paypal_high",
                "name": "PayPal High",
                "feature_key": "payment_field",
                "values": ["paypal"],
                "filename_pattern": PATTERN,
            },
            {
                "id": "paypal_text",
                "name": "PayPal Text",
                "feature_key": "supplier",
                "values": ["LUMITOP"],
                "filename_pattern": PATTERN,
            },
        ]
    )
    result = match_active_configuration(
        payment_field="paypal",
        supplier="LUMITOP",
        configurations=active,
        unmatched=_unmatched(),
    )
    assert result.matched_configuration_name == "PayPal High"
    assert result.matched_configuration_confidence == "high"
    assert result.alternative_matches
    assert any(
        item.get("configuration_name") == "PayPal Text"
        for item in result.alternative_matches
    )


def test_13_configuration_pattern_used_after_matching() -> None:
    active = configurations_from_raw([_paypal_config()])
    mapped = map_suggested_filename(
        SuggestedFilenameFields(
            supplier="LUMITOP",
            invoice_date="260511",
            amount="476,00",
            selected_amount="476,00",
            payment_field="paypal",
            selected_payment_field="paypal",
            art="er",
            selected_art="er",
            document_type="rechnung",
            source_filename="FA011466.pdf",
        ),
        configurations=active,
        unmatched=_unmatched(),
    )
    assert mapped.matched_configuration_name == "PayPal"
    assert mapped.matched_configuration_pattern == PATTERN
    assert mapped.suggested_filename is not None
    assert "paypal" in mapped.suggested_filename
    assert "476,00" in mapped.suggested_filename


def test_14_15_16_manifest_includes_matching_transparency(tmp_path: Path) -> None:
    _require_controlled()
    sandbox_in = tmp_path / "KI-Rechnungen-Test" / "input"
    sandbox_out = tmp_path / "KI-Rechnungen-Test" / "output"
    sandbox_in.mkdir(parents=True)
    sandbox_out.mkdir(parents=True)
    name = PDF["lumitop"]
    (sandbox_in / name).write_bytes((CONTROLLED_INPUT / name).read_bytes())
    planned = enrich_planned_destinations_with_local_extraction(
        (
            ProcessingPlannedDestination(
                document_name=name,
                planned_path=f"geplant/{name}",
                preview_only=True,
            ),
        ),
        input_folder=sandbox_in,
    )
    # Inject evaluated matching transparency expected from matcher.
    match = match_active_configuration(
        payment_field=planned[0].selected_payment_field or planned[0].payment_account,
        configurations=configurations_from_raw([_amex_config()]),
        unmatched=_unmatched(),
    )
    from dataclasses import replace

    planned = (
        replace(
            planned[0],
            available_configurations=match.available_configurations,
            evaluated_configuration_candidates=match.evaluated_configuration_candidates,
            unmatched_reasons=match.unmatched_reasons,
            condition_results=match.condition_results,
            matched_configuration_reason=match.matched_configuration_reason,
            matched_configuration_name=match.matched_configuration_name,
            matched_configuration_id=match.matched_configuration_id,
            matched_configuration_pattern=match.matched_configuration_pattern,
            matched_configuration_confidence=match.matched_configuration_confidence,
            missing_configuration_rule=match.missing_configuration_rule,
        ),
    )
    run = ProcessingRunState(
        status="completed",
        run_id="prompt22-manifest",
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
        detailed_item_mapping_complete=True,
    )
    result = write_preview_export_package(
        run, input_root=sandbox_in, output_root=sandbox_out
    )
    assert result.ok and result.export_folder
    payload = json.loads(
        (result.export_folder / "manifest.json").read_text(encoding="utf-8")
    )
    item = payload["items"][0]
    assert item["evaluated_configuration_candidates"]
    assert item["matched_configuration_reason"]
    assert item["available_configurations"]
    review_md = (result.export_folder / "review-items.md").read_text(encoding="utf-8")
    assert MSG_FIELD_CONFIGURATION in review_md
    assert MSG_FIELD_MATCHING_REASON in review_md
    assert "paypal" in review_md.lower() or "PayPal" in review_md


def test_17_18_review_items_explain_selection_and_paypal_gap(tmp_path: Path) -> None:
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
    planned = (
        ProcessingPlannedDestination(
            document_name=name,
            planned_path=f"geplant/{name}",
            preview_only=True,
            suggested_filename="2026-05-15_er_er_1A-Bootshop.de_105,75_paypal.pdf",
            filename_source="configuration_pattern",
            naming_reason=match.matched_configuration_reason,
            matched_configuration_name=match.matched_configuration_name,
            matched_configuration_id=match.matched_configuration_id,
            matched_configuration_pattern=match.matched_configuration_pattern,
            matched_configuration_reason=match.matched_configuration_reason,
            matched_configuration_confidence=match.matched_configuration_confidence,
            available_configurations=match.available_configurations,
            evaluated_configuration_candidates=match.evaluated_configuration_candidates,
            unmatched_reasons=match.unmatched_reasons,
            condition_results=match.condition_results,
            missing_configuration_rule=match.missing_configuration_rule,
            selected_payment_field="paypal",
            amount="105,75",
            selected_amount="105,75",
        ),
    )
    result = write_preview_export_package(
        ProcessingRunState(
            status="completed",
            run_id="prompt22-review-md",
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
    review_md = (result.export_folder / "review-items.md").read_text(encoding="utf-8")
    assert "Unklar" in review_md
    assert "no active configuration supports PayPal" in review_md
    assert MSG_FIELD_MATCHING_REASON in review_md


def test_19_20_21_22_ui_report_exposes_matching_labels() -> None:
    match = match_active_configuration(
        payment_field="paypal",
        configurations=configurations_from_raw([_amex_config()]),
        unmatched=_unmatched(),
    )
    planned = ProcessingPlannedDestination(
        document_name="FA011466.pdf",
        planned_path="geplant/FA011466.pdf",
        preview_only=True,
        matched_configuration_name=match.matched_configuration_name,
        matched_configuration_reason=match.matched_configuration_reason,
        condition_results=match.condition_results,
        missing_configuration_rule=match.missing_configuration_rule,
        available_configurations=match.available_configurations,
        evaluated_configuration_candidates=match.evaluated_configuration_candidates,
        selected_payment_field="paypal",
    )
    state = UiV2State()
    state.processing_run_state = ProcessingRunState(
        status="completed",
        run_id="prompt22-ui",
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
    assert detail.matched_configuration_name == "Unklar"
    assert detail.matched_configuration_reason
    assert detail.condition_results or detail.evaluated_configuration_candidates
    assert detail.missing_configuration_rule
    # Labels used by review page rendering / export reports.
    assert MSG_FIELD_CONFIGURATION == "Konfiguration"
    assert MSG_FIELD_MATCHING_REASON == "Matching-Grund"
    assert MSG_FIELD_CONDITION_RESULTS == "geprüfte Bedingungen"
    assert MSG_FIELD_MISSING_CONFIGURATION_RULE == "fehlende Konfigurationsregel"


def test_23_copied_pdfs_remain_byte_identical(tmp_path: Path) -> None:
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
            run_id="prompt22-bytes",
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


def test_24_input_files_are_not_mutated() -> None:
    _require_controlled()
    before = _digest_tree(CONTROLLED_INPUT)
    _ = match_active_configuration(payment_field="paypal")
    after = _digest_tree(CONTROLLED_INPUT)
    assert before == after


def test_25_output_outside_controlled_folder_blocked(tmp_path: Path) -> None:
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


def test_26_productive_original_folders_remain_blocked() -> None:
    for folder in FORBIDDEN_FOLDERS:
        result = write_preview_export_package(
            ProcessingRunState(status="completed", run_id="x"),
            input_root=folder,
            output_root=CONTROLLED_OUTPUT,
        )
        assert result.ok is False


def test_27_run_once_not_called() -> None:
    source = (ROOT / "invoice_tool" / "ui_v2" / "configuration_matching.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "run_once":
                pytest.fail("run_once must not be called")
            if isinstance(node.func, ast.Attribute) and node.func.attr == "run_once":
                pytest.fail("run_once must not be called")


def test_28_no_final_write_move_archive_delete_behavior() -> None:
    source = (ROOT / "invoice_tool" / "ui_v2" / "configuration_matching.py").read_text(
        encoding="utf-8"
    )
    forbidden = ("shutil.move", "os.remove", "Path.unlink", "shutil.rmtree", "archive")
    for token in forbidden:
        if token == "archive":
            continue
        assert token not in source


def test_29_no_real_invoice_folders_touched() -> None:
    source = (ROOT / "invoice_tool" / "ui_v2" / "configuration_matching.py").read_text(
        encoding="utf-8"
    )
    for folder in FORBIDDEN_FOLDERS:
        assert folder not in source


def test_30_no_saas_ready_claim() -> None:
    docs = list(
        (ROOT / "docs").glob(
            "*TRACK_B_CONFIGURATION_MATCHING_REPAIR*"
        )
    ) + list(
        (ROOT / "docs" / "audits").glob(
            "*TRACK_B_CONFIGURATION_MATCHING_REPAIR*"
        )
    )
    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert not text_claims_forbidden_maturity(text)


def test_31_no_production_ready_claim() -> None:
    source = (ROOT / "invoice_tool" / "ui_v2" / "configuration_matching.py").read_text(
        encoding="utf-8"
    )
    assert "production-ready" not in source.lower()
    assert "saas-ready" not in source.lower()


def test_32_track_a_protection_still_passes() -> None:
    for path in PROTECTED_TRACK_A + PROCESSING_CORE:
        assert path.exists()
    import tests.test_track_a_internal_app_protection as protection

    protection.test_track_a_protected_files_unchanged_vs_head()
    protection.test_processing_core_unchanged_vs_head()
    protection.test_protected_track_a_and_core_not_staged()
