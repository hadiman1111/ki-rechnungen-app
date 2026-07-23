"""Track-B configuration rule apply + preview rerun (Prompt 27/34).

No productive processing, no real invoice folders, no Track-A/core edits.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from invoice_tool.configuration_model import (
    Configuration,
    MatchingRule,
    ProfileBundle,
    UnmatchedConfiguration,
    default_filename_pattern,
    new_configuration_id,
    pattern_from_template,
)
from invoice_tool.profile_store import load_profile_bundle, save_profile_bundle
from invoice_tool.scan_models import DEFAULT_SCAN_MODEL_ID, get_scan_model
from invoice_tool.ui_v2.configuration_guidance import (
    derive_configuration_coverage_guidance,
)
from invoice_tool.ui_v2.configuration_matching import match_active_configuration
from invoice_tool.ui_v2.configuration_rule_apply_preview import (
    ACTION_APPLY_RULE_TO_REVIEW,
    ACTION_RECHECK_MATCHING,
    ACTION_RERUN_PREVIEW_WITH_NEW_RULE,
    MSG_APPLY_PREVIEW_ONLY,
    MSG_NO_FINAL_PROCESSING,
    MSG_ORIGINALS_UNCHANGED,
    MSG_PREVIEW_RECOMPUTED,
    MSG_RULE_SAVED,
    apply_preview_asserts_no_maturity_claim,
    apply_preview_calls_run_once,
    apply_preview_mutates_input,
    apply_preview_touches_real_invoice_folders,
    apply_preview_writes_final_pdfs,
    apply_saved_rule_to_preview_state,
    mark_rule_saved_for_preview_apply,
    preview_rerun_action_labels,
    rerun_preview_matching_after_rule_change,
)
from invoice_tool.ui_v2.configuration_rule_draft import draft_from_coverage_guidance
from invoice_tool.ui_v2.configuration_rule_editor import save_configuration_rule_draft
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.preview_export import (
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
APPLY_MODULE = ROOT / "invoice_tool" / "ui_v2" / "configuration_rule_apply_preview.py"
EDITOR_MODULE = ROOT / "invoice_tool" / "ui_v2" / "configuration_rule_editor.py"
REVIEW_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
DOCS = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_2026-07-23.md"
)

CONTROLLED_INPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input")
CONTROLLED_OUTPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output")
FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)
PATTERN = "{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf"
PDF = {
    "lumitop": "FA011466.pdf",
    "bootshop": "Rechnung RE-202605-14594.pdf",
    "boettcher": "320262919974.pdf",
    "luxvenum": "Rechnung-2026156019-102201.pdf",
    "storno": "420260091336.pdf",
}

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

def _paypal_guidance():
    return derive_configuration_coverage_guidance(
        selected_payment_field="paypal",
        is_unmatched_fallback=True,
        missing_configuration_rule="keine aktive PayPal-Konfiguration",
    )


def _card_guidance():
    return derive_configuration_coverage_guidance(
        selected_payment_field="card",
        is_unmatched_fallback=True,
        matched_configuration_reason="generic credit card detected, AMEX not proven",
    )


def _isolated_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    support = tmp_path / "support"
    support.mkdir(parents=True)
    monkeypatch.setattr("invoice_tool.app_paths.profile_storage_dir", lambda: support)
    monkeypatch.setattr(
        "invoice_tool.profile_store.app_paths.profile_storage_dir", lambda: support
    )
    dest = tmp_path / "dest"
    dest.mkdir()
    profile_id = "track-b-rule-apply-test"
    unmatched = UnmatchedConfiguration(
        name="Unklar",
        filename_pattern=pattern_from_template(PATTERN),
        destination={"type": "local_folder", "path": str(dest / "unklar")},
    )
    (dest / "unklar").mkdir()
    amex = Configuration(
        id=new_configuration_id(),
        name="American Express",
        active=True,
        matching=MatchingRule(
            feature_key="payment_field",
            operator="ist",
            values=["amex", "American Express"],
        ),
        filename_pattern=default_filename_pattern(
            get_scan_model(DEFAULT_SCAN_MODEL_ID)
        ),
        destination={"type": "local_folder", "path": str(dest / "amex")},
    )
    (dest / "amex").mkdir()
    bundle = ProfileBundle(
        id=profile_id,
        name="Track-B Apply Test",
        active=True,
        scan_model_id=DEFAULT_SCAN_MODEL_ID,
        configurations=[amex],
        unmatched=unmatched,
    )
    save_profile_bundle(bundle)
    return profile_id


def _planned(
    name: str,
    *,
    payment_field: str | None,
    matched: str = "Unklar",
    supplier: str = "Supplier",
) -> ProcessingPlannedDestination:
    return ProcessingPlannedDestination(
        document_name=name,
        planned_path="/tmp/preview-unklar",
        destination_label=matched,
        reason="no active matching config" if matched == "Unklar" else "matched",
        preview_only=True,
        applied=False,
        supplier=supplier,
        invoice_date="2026-05-01",
        amount="10,00",
        selected_amount="10,00",
        selected_art="er",
        selected_payment_field=payment_field,
        payment_account=payment_field,
        matched_configuration_name=matched,
        matched_configuration_id="unmatched" if matched == "Unklar" else matched.lower(),
        matched_configuration_pattern=PATTERN,
        matched_configuration_reason=(
            "Keine aktive PayPal-Konfiguration"
            if payment_field == "paypal"
            else "Unklar/Fallback"
        ),
        matched_configuration_confidence="low",
        filename_pattern=PATTERN,
        rendered_filename=f"2026-05-01_er_{supplier}_10,00_{payment_field or 'FEHLT'}.pdf",
        suggested_filename=f"2026-05-01_er_{supplier}_10,00_{payment_field or 'FEHLT'}.pdf",
        configuration_coverage_status="missing_configuration",
        missing_configuration_type=(
            "paypal"
            if payment_field == "paypal"
            else ("generic_card" if payment_field == "card" else "payment_field")
        ),
    )


def _run_state() -> ProcessingRunState:
    planned = (
        _planned(PDF["lumitop"], payment_field="paypal", supplier="LUMITOP"),
        _planned(PDF["bootshop"], payment_field="paypal", supplier="1A-Bootshop"),
        _planned(PDF["boettcher"], payment_field="card", supplier="Boettcher"),
        _planned(PDF["luxvenum"], payment_field=None, supplier="Luxvenum"),
        _planned(PDF["storno"], payment_field=None, supplier="BoettcherStorno"),
    )
    reviews = tuple(
        ProcessingReviewItem(
            document_name=item.document_name,
            reason="configuration coverage gap",
            status_label="unklar",
            document_id=item.document_name,
        )
        for item in planned
    )
    return ProcessingRunState(
        status="completed",
        message="Sandbox preview complete",
        run_id="track-b-apply-rerun-test",
        review_items=reviews,
        planned_destinations=planned,
        planned_destination_count=len(planned),
        state_updated_at="2026-07-23T00:00:00+00:00",
    )


def _save_paypal(profile_id: str, tmp_path: Path):
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        unmatched_filename_pattern=PATTERN,
    )
    assert draft is not None
    dest = tmp_path / "dest" / "paypal"
    dest.mkdir(parents=True, exist_ok=True)
    draft = replace(draft, proposed_destination_path=str(dest))
    result = save_configuration_rule_draft(
        profile_id=profile_id,
        draft=draft,
        explicit_user_confirmation=True,
    )
    assert result.ok, result.message
    return result


def _save_card(profile_id: str, tmp_path: Path):
    draft = draft_from_coverage_guidance(
        guidance=_card_guidance(),
        selected_payment_field="card",
        unmatched_filename_pattern=PATTERN,
    )
    assert draft is not None
    dest = tmp_path / "dest" / "card"
    dest.mkdir(parents=True, exist_ok=True)
    draft = replace(draft, proposed_destination_path=str(dest))
    result = save_configuration_rule_draft(
        profile_id=profile_id,
        draft=draft,
        explicit_user_confirmation=True,
    )
    assert result.ok, result.message
    return result


def test_01_saving_paypal_rule_requires_explicit_confirmation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        unmatched_filename_pattern=PATTERN,
    )
    assert draft is not None
    dest = tmp_path / "dest" / "paypal-denied"
    dest.mkdir(parents=True, exist_ok=True)
    draft = replace(draft, proposed_destination_path=str(dest))
    denied = save_configuration_rule_draft(
        profile_id=profile_id,
        draft=draft,
        explicit_user_confirmation=False,
    )
    assert denied.ok is False
    blob = denied.message.lower()
    assert "bestätigung" in blob or "explizit" in blob or "confirmation" in blob


def test_02_saved_paypal_rule_added_to_ui_v2_active_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    result = _save_paypal(profile_id, tmp_path)
    names = {c.name for c in load_profile_bundle(profile_id).configurations}
    assert "PayPal" in names
    assert result.draft is not None and result.draft.saved is True


def test_03_paypal_rule_condition_is_payment_field_paypal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    result = _save_paypal(profile_id, tmp_path)
    assert result.draft is not None
    assert result.draft.proposed_matching_feature_key == "payment_field"
    assert result.draft.proposed_matching_operator == "ist"
    assert result.draft.proposed_matching_values == ("paypal",)
    cfg = next(
        c for c in load_profile_bundle(profile_id).configurations if c.name == "PayPal"
    )
    assert cfg.matching is not None
    assert cfg.matching.feature_key == "payment_field"
    assert "paypal" in {v.lower() for v in cfg.matching.values}


def test_04_preview_rerun_paypal_changes_lumitop_from_unklar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="PayPal",
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    assert result.ok
    assert result.updated_run_state is not None
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["lumitop"]
    )
    assert item.previous_matched_configuration == "Unklar"
    assert item.new_matched_configuration == "PayPal"
    assert item.matched_configuration_name == "PayPal"


def test_05_preview_rerun_paypal_changes_bootshop_from_unklar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="PayPal",
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["bootshop"]
    )
    assert item.matched_configuration_name == "PayPal"
    assert item.matched_after_rule_change is True


def test_06_paypal_rule_does_not_affect_generic_card(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="PayPal",
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["boettcher"]
    )
    assert item.matched_configuration_name == "Unklar"
    assert item.rule_applied is False


def test_07_paypal_rule_does_not_affect_missing_payment_field(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="PayPal",
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    for key in (PDF["luxvenum"], PDF["storno"]):
        item = next(
            p
            for p in result.updated_run_state.planned_destinations
            if p.document_name == key
        )
        assert item.matched_configuration_name == "Unklar"
        assert item.rule_applied is False


def test_08_paypal_rule_does_not_assign_business_category_silently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    assert saved.draft is not None
    assert saved.draft.proposes_business_category is False
    cfg = next(
        c for c in load_profile_bundle(profile_id).configurations if c.name == "PayPal"
    )
    blob = json.dumps(cfg.__dict__, default=str).lower()
    assert "architektur" not in blob
    assert "event production" not in blob
    assert "privat" not in blob or "keine" in (saved.draft.warnings[0].lower())


def test_09_generic_card_rule_changes_card_item_to_non_amex(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_card(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="Kreditkarte / Nicht-AMEX-Karte",
        applied_configuration_condition="payment_field ist card",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["boettcher"]
    )
    assert item.matched_configuration_name == "Kreditkarte / Nicht-AMEX-Karte"
    assert item.matched_configuration_name != "American Express"


def test_10_generic_card_rule_does_not_match_amex(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    _save_card(profile_id, tmp_path)
    match = match_active_configuration(
        payment_field="amex",
        profile_id=profile_id,
    )
    assert match.matched_configuration_name == "American Express"
    assert match.matched_configuration_name != "Kreditkarte / Nicht-AMEX-Karte"


def test_11_amex_still_requires_explicit_amex_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    _save_card(profile_id, tmp_path)
    match_card = match_active_configuration(
        payment_field="card",
        profile_id=profile_id,
    )
    assert match_card.matched_configuration_name == "Kreditkarte / Nicht-AMEX-Karte"
    match_amex = match_active_configuration(
        payment_field="amex",
        profile_id=profile_id,
    )
    assert match_amex.matched_configuration_name == "American Express"


def test_12_preview_rerun_records_previous_matched_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="PayPal",
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["lumitop"]
    )
    assert item.previous_matched_configuration == "Unklar"


def test_13_preview_rerun_records_new_matched_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="PayPal",
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["lumitop"]
    )
    assert item.new_matched_configuration == "PayPal"


def test_14_preview_rerun_records_rule_applied(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="PayPal",
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["lumitop"]
    )
    assert item.rule_applied is True
    assert item.applied_configuration_name == "PayPal"


def test_15_preview_rerun_records_applied_configuration_condition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="PayPal",
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["lumitop"]
    )
    assert item.applied_configuration_condition == "payment_field ist paypal"


def test_16_ui_exposes_preview_only_rerun_action_after_save(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    state = UiV2State()
    state.selected_profile_id = profile_id
    state.processing_run_state = _run_state()
    mark_rule_saved_for_preview_apply(
        state,
        draft=saved.draft,
        configuration_id=saved.configuration_id,
    )
    vm = build_review_page_vm(state)
    assert vm.configuration_rule_apply_available is True
    labels = set(vm.preview_rerun_action_labels)
    assert ACTION_RERUN_PREVIEW_WITH_NEW_RULE in labels
    assert ACTION_RECHECK_MATCHING in labels
    assert ACTION_APPLY_RULE_TO_REVIEW in labels
    assert preview_rerun_action_labels() == (
        ACTION_RERUN_PREVIEW_WITH_NEW_RULE,
        ACTION_RECHECK_MATCHING,
        ACTION_APPLY_RULE_TO_REVIEW,
    )
    source = REVIEW_PAGE.read_text(encoding="utf-8")
    assert "build_configuration_rule_apply_panel" in source
    assert ACTION_RERUN_PREVIEW_WITH_NEW_RULE in APPLY_MODULE.read_text(encoding="utf-8")


def test_17_preview_export_after_rerun_uses_updated_matched_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    if not CONTROLLED_INPUT.is_dir() or not CONTROLLED_OUTPUT.is_dir():
        pytest.skip("controlled folders missing")
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="PayPal",
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    assert result.ok and result.updated_run_state is not None
    export_root = tmp_path / "preview-out"
    export_root.mkdir()
    export = write_preview_export_package(
        result.updated_run_state,
        input_root=CONTROLLED_INPUT,
        output_root=export_root,
    )
    assert export.ok, export.error
    payload = json.loads((export.export_folder / "manifest.json").read_text())
    by_name = {item["source_filename"]: item for item in payload["items"]}
    assert by_name[PDF["lumitop"]]["matched_configuration_name"] == "PayPal"
    assert by_name[PDF["bootshop"]]["matched_configuration_name"] == "PayPal"
    assert by_name[PDF["boettcher"]]["matched_configuration_name"] == "Unklar"


def test_18_manifest_includes_rerun_preview_after_rule_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    if not CONTROLLED_INPUT.is_dir() or not CONTROLLED_OUTPUT.is_dir():
        pytest.skip("controlled folders missing")
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    result = rerun_preview_matching_after_rule_change(
        run_state=_run_state(),
        profile_id=profile_id,
        applied_configuration_name="PayPal",
        applied_configuration_condition="payment_field ist paypal",
        applied_configuration_id=saved.configuration_id,
        explicit_user_action=True,
    )
    export_root = tmp_path / "preview-out-2"
    export_root.mkdir()
    export = write_preview_export_package(
        result.updated_run_state,
        input_root=CONTROLLED_INPUT,
        output_root=export_root,
    )
    assert export.ok, export.error
    payload = json.loads((export.export_folder / "manifest.json").read_text())
    item = next(i for i in payload["items"] if i["source_filename"] == PDF["lumitop"])
    assert item["rerun_preview_after_rule_change"] is True
    assert item["rule_applied"] is True
    assert item["previous_matched_configuration"] == "Unklar"
    assert item["new_matched_configuration"] == "PayPal"
    assert item["applied_configuration_condition"] == "payment_field ist paypal"
    review_md = (export.export_folder / "review-items.md").read_text(encoding="utf-8")
    assert "rerun_preview_after_rule_change" in review_md
    assert "new_matched_configuration" in review_md


def test_19_saving_rerun_does_not_call_run_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    calls: list[str] = []

    def _boom(*_a, **_k):
        calls.append("run_once")
        raise AssertionError("run_once must not be called")

    monkeypatch.setattr("invoice_tool.run.run_once", _boom, raising=False)
    saved = _save_paypal(profile_id, tmp_path)
    state = UiV2State()
    state.selected_profile_id = profile_id
    state.processing_run_state = _run_state()
    mark_rule_saved_for_preview_apply(
        state, draft=saved.draft, configuration_id=saved.configuration_id
    )
    apply = apply_saved_rule_to_preview_state(state, explicit_user_action=True)
    assert apply.ok
    assert apply.called_run_once is False
    assert apply_preview_calls_run_once() is False
    assert calls == []


def test_20_saving_rerun_does_not_mutate_input_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    sample_dir = tmp_path / "input"
    sample_dir.mkdir()
    sample = sample_dir / "sample.pdf"
    payload = b"%PDF-1.4 track-b-apply-rerun-input"
    sample.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    if CONTROLLED_INPUT.is_dir():
        before = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in CONTROLLED_INPUT.glob("*.pdf")
        }
    saved = _save_paypal(profile_id, tmp_path)
    state = UiV2State()
    state.selected_profile_id = profile_id
    state.processing_run_state = _run_state()
    mark_rule_saved_for_preview_apply(
        state, draft=saved.draft, configuration_id=saved.configuration_id
    )
    apply = apply_saved_rule_to_preview_state(state, explicit_user_action=True)
    assert apply.ok
    assert apply.mutated_input is False
    assert apply_preview_mutates_input() is False
    assert hashlib.sha256(sample.read_bytes()).hexdigest() == digest
    if CONTROLLED_INPUT.is_dir():
        after = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in CONTROLLED_INPUT.glob("*.pdf")
        }
        assert before == after


def test_21_saving_rerun_does_not_write_final_pdfs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    final_dir = tmp_path / "final-out"
    final_dir.mkdir()
    before = list(final_dir.rglob("*"))
    saved = _save_paypal(profile_id, tmp_path)
    state = UiV2State()
    state.selected_profile_id = profile_id
    state.processing_run_state = _run_state()
    mark_rule_saved_for_preview_apply(
        state, draft=saved.draft, configuration_id=saved.configuration_id
    )
    apply = apply_saved_rule_to_preview_state(state, explicit_user_action=True)
    assert apply.ok
    assert apply.wrote_final_pdfs is False
    assert apply.preview_only is True
    assert apply_preview_writes_final_pdfs() is False
    assert list(final_dir.rglob("*")) == before
    assert MSG_NO_FINAL_PROCESSING in MSG_APPLY_PREVIEW_ONLY
    assert MSG_ORIGINALS_UNCHANGED in MSG_APPLY_PREVIEW_ONLY
    assert MSG_RULE_SAVED in MSG_APPLY_PREVIEW_ONLY
    assert MSG_PREVIEW_RECOMPUTED in MSG_APPLY_PREVIEW_ONLY


def test_22_saving_rerun_does_not_touch_real_invoice_folders(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    saved = _save_paypal(profile_id, tmp_path)
    state = UiV2State()
    state.selected_profile_id = profile_id
    state.processing_run_state = _run_state()
    mark_rule_saved_for_preview_apply(
        state, draft=saved.draft, configuration_id=saved.configuration_id
    )
    apply = apply_saved_rule_to_preview_state(state, explicit_user_action=True)
    assert apply.ok
    assert apply.touched_real_invoice_folders is False
    assert apply_preview_touches_real_invoice_folders() is False
    for path in FORBIDDEN_FOLDERS:
        assert path not in json.dumps(
            {
                "msg": apply.message,
                "name": apply.applied_configuration_name,
            }
        )


def test_23_no_saas_ready_claim() -> None:
    assert apply_preview_asserts_no_maturity_claim() is False
    for path in (APPLY_MODULE, EDITOR_MODULE):
        text = path.read_text(encoding="utf-8")
        assert "saas-ready" not in text.lower()
        assert "saas ready" not in text.lower()
    for path in (DOCS, AUDIT):
        text = path.read_text(encoding="utf-8")
        assert "nicht SaaS-ready" in text or "nicht saas-ready" in text.lower()
        assert text_claims_forbidden_maturity(text) is False
        assert "ist saas-ready" not in text.lower()


def test_24_no_production_ready_claim() -> None:
    assert apply_preview_asserts_no_maturity_claim() is False
    for path in (APPLY_MODULE, EDITOR_MODULE):
        text = path.read_text(encoding="utf-8")
        assert "production-ready" not in text.lower()
        assert "production ready" not in text.lower()
        assert "produktionsreif" not in text.lower()
    for path in (DOCS, AUDIT):
        text = path.read_text(encoding="utf-8")
        assert (
            "nicht production-ready" in text.lower()
            or "nicht produktionsreif" in text.lower()
        )
        assert text_claims_forbidden_maturity(text) is False
        assert "ist production-ready" not in text.lower()


def test_25_track_a_protection_still_passes() -> None:
    # Source-level: apply module must not import main Track-A UI modules.
    tree = ast.parse(APPLY_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    for protected in TRACK_A_PROTECTED:
        module = protected.replace("/", ".").removesuffix(".py")
        assert module not in imported
        assert not any(name.startswith(module + ".") for name in imported)
    # Processing-core symbols must not be imported by apply module.
    for core in (
        "invoice_tool.run",
        "invoice_tool.processing",
        "invoice_tool.routing",
        "invoice_tool.classification",
        "invoice_tool.core_dry_run",
    ):
        assert core not in imported


def test_docs_and_audit_exist_or_will_exist() -> None:
    # Soft presence check once docs are written in this task.
    assert APPLY_MODULE.is_file()
    assert "explicit_user_action" in APPLY_MODULE.read_text(encoding="utf-8")
    assert "preview_only" in APPLY_MODULE.read_text(encoding="utf-8")
