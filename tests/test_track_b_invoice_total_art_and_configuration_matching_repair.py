"""Track-B invoice total / art / configuration matching repair (Prompt 21/34)."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from invoice_tool.ui_v2.configuration_matching import (
    ConfigurationCandidate,
    match_active_configuration,
)
from invoice_tool.ui_v2.extraction_mapping import (
    enrich_planned_destinations_with_local_extraction,
    extract_local_fields_from_pdf,
    read_pdf_text_layer,
)
from invoice_tool.ui_v2.invoice_field_candidates import (
    select_document_art_candidates,
    select_invoice_amount_candidates,
    select_payment_field_candidates,
)
from invoice_tool.ui_v2.preview_export import (
    text_claims_forbidden_maturity,
    write_preview_export_package,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
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
DOC = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_INVOICE_TOTAL_ART_AND_CONFIGURATION_MATCHING_REPAIR_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_INVOICE_TOTAL_ART_AND_CONFIGURATION_MATCHING_REPAIR_2026-07-23.md"
)


def _require_controlled() -> None:
    if not CONTROLLED_INPUT.exists():
        pytest.skip("controlled input missing")


def _text(name: str) -> str:
    _require_controlled()
    return read_pdf_text_layer(CONTROLLED_INPUT / name)


def _digest_tree(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not folder.exists():
        return out
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _amex_and_unclear() -> tuple[tuple[ConfigurationCandidate, ...], ConfigurationCandidate]:
    active = (
        ConfigurationCandidate(
            configuration_id="amex",
            name="American Express",
            active=True,
            matching_feature_key="payment_field",
            matching_values=("amex", "American Express"),
            filename_pattern="{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf",
        ),
    )
    unmatched = ConfigurationCandidate(
        configuration_id="unmatched",
        name="Unklar",
        active=True,
        is_unmatched=True,
        filename_pattern="{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf",
    )
    return active, unmatched


def test_01_lumitop_selects_476_not_500() -> None:
    result = select_invoice_amount_candidates(_text(PDF["lumitop"]))
    assert result.selected_amount == "476,00"
    assert result.selected_amount != "500,00"
    assert any(c.display_value_comma == "500,00" for c in result.amount_candidates)
    assert any(
        c.display_value_comma == "500,00"
        and (
            c.rejection_reason
            or c.is_base_price_candidate
            or not c.is_final_total_candidate
        )
        for c in list(result.amount_candidates) + list(result.rejected_amount_candidates)
    )


def test_02_lumitop_detects_paypal() -> None:
    result = select_payment_field_candidates(_text(PDF["lumitop"]))
    assert result.selected_payment_field == "paypal"
    assert "PayPal" in (result.selected_payment_field_reason or "")


def test_03_bootshop_selects_105_75_not_80_55() -> None:
    result = select_invoice_amount_candidates(_text(PDF["bootshop"]))
    assert result.selected_amount == "105,75"
    assert result.selected_amount != "80,55"


def test_04_bootshop_detects_paypal() -> None:
    result = select_payment_field_candidates(_text(PDF["bootshop"]))
    assert result.selected_payment_field == "paypal"


def test_05_boettcher_selects_84_39() -> None:
    result = select_invoice_amount_candidates(_text(PDF["boettcher"]))
    assert result.selected_amount == "84,39"


def test_06_boettcher_generic_card_without_amex() -> None:
    result = select_payment_field_candidates(_text(PDF["boettcher"]))
    assert result.selected_payment_field == "card"
    assert "AMEX" in (result.selected_payment_field_reason or "")
    assert not any(c.payment_field == "amex" for c in result.payment_field_candidates)


def test_07_generic_card_does_not_match_american_express() -> None:
    active, unmatched = _amex_and_unclear()
    hit = match_active_configuration(
        payment_field="card",
        configurations=active,
        unmatched=unmatched,
    )
    assert hit.is_unmatched_fallback is True
    assert hit.matched_configuration_name == "Unklar"
    assert "American Express" not in (hit.matched_configuration_reason or "") or "nicht" in (
        hit.matched_configuration_reason or ""
    ).lower()
    assert "card" in (hit.matched_configuration_reason or "").lower()


def test_08_amex_only_with_explicit_proof() -> None:
    active, unmatched = _amex_and_unclear()
    no_amex = match_active_configuration(
        payment_field="card",
        configurations=active,
        unmatched=unmatched,
    )
    assert no_amex.matched_configuration_name == "Unklar"
    yes_amex = match_active_configuration(
        payment_field="amex",
        configurations=active,
        unmatched=unmatched,
    )
    assert yes_amex.matched_configuration_name == "American Express"
    text_amex = select_payment_field_candidates(
        "Zahlung per American Express AMEX Karte"
    )
    assert text_amex.selected_payment_field == "amex"


def test_09_luxvenum_selects_154_95() -> None:
    result = select_invoice_amount_candidates(_text(PDF["luxvenum"]))
    assert result.selected_amount == "154,95"


def test_10_luxvenum_missing_payment_field_explicit() -> None:
    result = select_payment_field_candidates(_text(PDF["luxvenum"]))
    assert result.selected_payment_field is None
    assert "fehlend" in (result.selected_payment_field_reason or "").lower()


def test_11_storno_selects_68_94() -> None:
    result = select_invoice_amount_candidates(_text(PDF["storno"]))
    assert result.selected_amount == "68,94"


def test_12_storno_detected_as_storno_or_art_ambiguity() -> None:
    art = select_document_art_candidates(_text(PDF["storno"]))
    assert art.selected_art == "storno"
    assert art.document_type == "storno"
    assert art.art_ambiguity is True
    assert "storno" in (art.selected_art_reason or "").lower()


def test_13_amount_candidates_include_rejected_line_base_net() -> None:
    result = select_invoice_amount_candidates(_text(PDF["lumitop"]))
    rejected = result.rejected_amount_candidates
    assert rejected
    assert any(
        c.is_base_price_candidate
        or c.is_net_candidate
        or (c.rejection_reason and "base" in c.rejection_reason)
        or c.display_value_comma == "500,00"
        for c in list(result.amount_candidates) + list(rejected)
    )


def test_14_selected_amount_reason_recorded() -> None:
    result = select_invoice_amount_candidates(_text(PDF["bootshop"]))
    assert result.selected_amount_reason
    assert "105,75" in result.selected_amount_reason


def test_15_payment_candidates_include_proof_reason() -> None:
    result = select_payment_field_candidates(_text(PDF["boettcher"]))
    assert result.payment_field_candidates
    assert result.payment_field_candidates[0].proof
    assert result.selected_payment_field_reason


def test_16_matched_configuration_reason_explains_unclear() -> None:
    active, unmatched = _amex_and_unclear()
    paypal = match_active_configuration(
        payment_field="paypal",
        configurations=active,
        unmatched=unmatched,
    )
    assert paypal.is_unmatched_fallback
    assert "paypal" in (paypal.matched_configuration_reason or "").lower()
    missing = match_active_configuration(
        payment_field=None,
        configurations=active,
        unmatched=unmatched,
    )
    assert "fehlt" in (missing.matched_configuration_reason or "").lower()


def test_17_rendered_filename_uses_corrected_amount_comma() -> None:
    mapped = map_suggested_filename(
        SuggestedFilenameFields(
            supplier="LUMITOP",
            invoice_date="260511",
            amount="476,00",
            selected_amount="476,00",
            selected_amount_reason="test",
            payment_field="paypal",
            selected_payment_field="paypal",
            art="er",
            selected_art="er",
            document_type="rechnung",
            source_filename="FA011466.pdf",
        )
    )
    assert mapped.suggested_filename is not None
    assert "476,00" in mapped.suggested_filename
    assert "500,00" not in mapped.suggested_filename


def test_18_preview_export_pdf_names_use_corrected_amounts(tmp_path: Path) -> None:
    _require_controlled()
    sandbox_in = tmp_path / "KI-Rechnungen-Test" / "input"
    sandbox_out = tmp_path / "KI-Rechnungen-Test" / "output"
    sandbox_in.mkdir(parents=True)
    sandbox_out.mkdir(parents=True)
    for name in PDF.values():
        data = (CONTROLLED_INPUT / name).read_bytes()
        (sandbox_in / name).write_bytes(data)
    planned = enrich_planned_destinations_with_local_extraction(
        tuple(
            ProcessingPlannedDestination(
                document_name=name,
                planned_path=f"geplant/unklar/{name}",
                preview_only=True,
                reason="test",
            )
            for name in PDF.values()
        ),
        input_folder=sandbox_in,
    )
    by_name = {item.document_name: item for item in planned}
    assert "476,00" in (by_name[PDF["lumitop"]].suggested_filename or "")
    assert "105,75" in (by_name[PDF["bootshop"]].suggested_filename or "")
    assert "storno" in (by_name[PDF["storno"]].suggested_filename or "").lower()
    run = ProcessingRunState(
        status="completed",
        run_id="prompt21-amount-repair",
        review_items=tuple(
            ProcessingReviewItem(
                document_id=item.document_name,
                document_name=item.document_name,
                reason="review",
                status_label="unklar",
            )
            for item in planned
        ),
        planned_destinations=planned,
        planned_destination_count=len(planned),
        detailed_item_mapping_complete=True,
    )
    result = write_preview_export_package(
        run,
        input_root=sandbox_in,
        output_root=sandbox_out,
    )
    assert result.ok
    names = [item.preview_filename for item in result.items]
    assert any("476,00" in n for n in names)
    assert any("105,75" in n for n in names)
    assert any("storno" in n.lower() for n in names)
    assert not any("500,00" in n for n in names)
    assert not any("80,55" in n for n in names)


def test_19_to_24_manifest_includes_candidate_fields(tmp_path: Path) -> None:
    _require_controlled()
    sandbox_in = tmp_path / "KI-Rechnungen-Test" / "input"
    sandbox_out = tmp_path / "KI-Rechnungen-Test" / "output"
    sandbox_in.mkdir(parents=True)
    sandbox_out.mkdir(parents=True)
    src = CONTROLLED_INPUT / PDF["lumitop"]
    (sandbox_in / PDF["lumitop"]).write_bytes(src.read_bytes())
    planned = enrich_planned_destinations_with_local_extraction(
        (
            ProcessingPlannedDestination(
                document_name=PDF["lumitop"],
                planned_path=f"geplant/{PDF['lumitop']}",
                preview_only=True,
            ),
        ),
        input_folder=sandbox_in,
    )
    run = ProcessingRunState(
        status="completed",
        run_id="prompt21-manifest",
        review_items=(
            ProcessingReviewItem(
                document_id=PDF["lumitop"],
                document_name=PDF["lumitop"],
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
    payload = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    item = payload["items"][0]
    assert item["amount_candidates"]
    assert item["selected_amount_reason"]
    assert item["payment_field_candidates"]
    assert item["selected_payment_field_reason"]
    assert item["document_art_candidates"]
    assert item["selected_art_reason"]
    assert item["selected_amount"] == "476,00"


def test_25_copied_pdfs_byte_identical(tmp_path: Path) -> None:
    _require_controlled()
    sandbox_in = tmp_path / "KI-Rechnungen-Test" / "input"
    sandbox_out = tmp_path / "KI-Rechnungen-Test" / "output"
    sandbox_in.mkdir(parents=True)
    sandbox_out.mkdir(parents=True)
    src = CONTROLLED_INPUT / PDF["boettcher"]
    (sandbox_in / PDF["boettcher"]).write_bytes(src.read_bytes())
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    planned = enrich_planned_destinations_with_local_extraction(
        (
            ProcessingPlannedDestination(
                document_name=PDF["boettcher"],
                planned_path=f"x/{PDF['boettcher']}",
                preview_only=True,
            ),
        ),
        input_folder=sandbox_in,
    )
    run = ProcessingRunState(
        status="completed",
        run_id="prompt21-bytes",
        review_items=(
            ProcessingReviewItem(
                document_id=PDF["boettcher"],
                document_name=PDF["boettcher"],
                reason="r",
                status_label="unklar",
            ),
        ),
        planned_destinations=planned,
        planned_destination_count=1,
    )
    result = write_preview_export_package(
        run, input_root=sandbox_in, output_root=sandbox_out
    )
    assert result.ok
    item = result.items[0]
    assert item.source_sha256 == digest
    assert item.preview_sha256 == digest


def test_26_input_files_not_mutated() -> None:
    _require_controlled()
    before = _digest_tree(CONTROLLED_INPUT)
    _ = extract_local_fields_from_pdf(CONTROLLED_INPUT / PDF["lumitop"])
    after = _digest_tree(CONTROLLED_INPUT)
    assert before == after


def test_27_output_outside_controlled_folder_blocked(tmp_path: Path) -> None:
    _require_controlled()
    bad_out = tmp_path / "not-controlled-output"
    bad_out.mkdir()
    run = ProcessingRunState(
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
    )
    result = write_preview_export_package(
        run,
        input_root=CONTROLLED_INPUT,
        output_root=bad_out,
    )
    assert result.ok is False


def test_28_productive_original_folders_remain_blocked() -> None:
    for folder in FORBIDDEN_FOLDERS:
        result = write_preview_export_package(
            ProcessingRunState(status="completed", run_id="x"),
            input_root=folder,
            output_root=CONTROLLED_OUTPUT,
        )
        assert result.ok is False


def test_29_run_once_not_called() -> None:
    modules = [
        ROOT / "invoice_tool" / "ui_v2" / "invoice_field_candidates.py",
        ROOT / "invoice_tool" / "ui_v2" / "extraction_mapping.py",
        ROOT / "invoice_tool" / "ui_v2" / "configuration_matching.py",
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


def test_30_no_final_write_move_archive_delete_behavior() -> None:
    text = (ROOT / "invoice_tool" / "ui_v2" / "invoice_field_candidates.py").read_text(
        encoding="utf-8"
    )
    assert "shutil.move" not in text
    assert "os.remove" not in text
    assert "unlink(" not in text


def test_31_no_real_invoice_folders_touched() -> None:
    module = (
        ROOT / "invoice_tool" / "ui_v2" / "invoice_field_candidates.py"
    ).read_text(encoding="utf-8")
    assert "/Users/hadi_neu/Desktop/RECHNUNGEN" not in module
    assert "02_Rechnungseingang" not in module


def test_32_no_saas_ready_claim() -> None:
    assert text_claims_forbidden_maturity("nicht SaaS-ready") is False
    assert text_claims_forbidden_maturity("SaaS-ready") is True
    if DOC.exists():
        docs = DOC.read_text(encoding="utf-8")
        assert "nicht SaaS-ready" in docs or "Not SaaS-ready" in docs


def test_33_no_production_ready_claim() -> None:
    assert text_claims_forbidden_maturity("nicht production-ready") is False
    assert text_claims_forbidden_maturity("production-ready") is True


def test_34_track_a_protection_still_passes() -> None:
    for path in PROTECTED_TRACK_A:
        assert path.exists() or path.name == "ui_document_rules.py"
    for path in PROCESSING_CORE:
        assert path.exists()
    candidates = ROOT / "invoice_tool" / "ui_v2" / "invoice_field_candidates.py"
    tree = ast.parse(candidates.read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "invoice_tool.run" not in imported_modules
    assert "invoice_tool.processing" not in imported_modules


def test_controlled_enrichment_expected_amounts() -> None:
    _require_controlled()
    planned = enrich_planned_destinations_with_local_extraction(
        tuple(
            ProcessingPlannedDestination(
                document_name=name,
                planned_path=f"preview/{name}",
                preview_only=True,
            )
            for name in PDF.values()
        ),
        input_folder=CONTROLLED_INPUT,
    )
    by_name = {item.document_name: item for item in planned}
    assert by_name[PDF["lumitop"]].amount == "476,00"
    assert by_name[PDF["bootshop"]].amount == "105,75"
    assert by_name[PDF["boettcher"]].amount == "84,39"
    assert by_name[PDF["luxvenum"]].amount == "154,95"
    assert by_name[PDF["storno"]].amount == "68,94"
    assert by_name[PDF["storno"]].selected_art == "storno"
    assert by_name[PDF["boettcher"]].selected_payment_field == "card"
    assert by_name[PDF["lumitop"]].selected_payment_field == "paypal"
