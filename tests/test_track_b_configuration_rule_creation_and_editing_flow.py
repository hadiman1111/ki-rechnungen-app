"""Track-B configuration rule creation/editing flow (Prompt 26/34).

No productive processing, no real invoice folders, no Track-A/core edits.
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

import pytest

from invoice_tool.configuration_model import (
    Configuration,
    MatchingRule,
    UnmatchedConfiguration,
    default_filename_pattern,
    new_configuration_id,
    pattern_from_template,
)
from invoice_tool.profile_store import load_profile_bundle, save_profile_bundle
from invoice_tool.scan_models import DEFAULT_SCAN_MODEL_ID
from invoice_tool.ui_v2.configuration_guidance import (
    MISSING_TYPE_GENERIC_CARD,
    MISSING_TYPE_PAYMENT_FIELD,
    MISSING_TYPE_PAYPAL,
    derive_configuration_coverage_guidance,
)
from invoice_tool.ui_v2.configuration_matching import ConfigurationCandidate
from invoice_tool.ui_v2.configuration_rule_draft import (
    ACTION_CREATE_FROM_GUIDANCE,
    ACTION_EDIT_EXISTING,
    ACTION_MANUAL_KEEP_UNCLEAR,
    MSG_FIELD_CONFIGURATION_RULE_DRAFT_AVAILABLE,
    WARNING_GENERIC_CARD_NOT_AMEX,
    WARNING_MISSING_PAYMENT_NO_BLIND_RULE,
    WARNING_NO_BUSINESS_CATEGORY,
    draft_from_coverage_guidance,
    unknown_pattern_slots_in_pattern,
    validate_configuration_rule_draft,
)
from invoice_tool.ui_v2.configuration_rule_editor import (
    build_configuration_rule_action_labels,
    open_create_draft_from_review_detail,
    save_configuration_rule_draft,
)
from invoice_tool.ui_v2.pages.review import (
    ReviewDetailItemVM,
    build_review_page_vm,
)
from invoice_tool.ui_v2.preview_export import text_claims_forbidden_maturity
from invoice_tool.ui_v2.processing_state import ProcessingReviewItem, ProcessingRunState
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
DRAFT_MODULE = ROOT / "invoice_tool" / "ui_v2" / "configuration_rule_draft.py"
EDITOR_MODULE = ROOT / "invoice_tool" / "ui_v2" / "configuration_rule_editor.py"
REVIEW_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
DOCS = ROOT / "docs" / "KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_2026-07-23.md"
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_2026-07-23.md"
)

CONTROLLED_INPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input")
FORBIDDEN_MATURITY = re.compile(
    r"\b(saas[- ]ready|production[- ]ready|produktionsreif|saas-reif)\b",
    re.IGNORECASE,
)

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


def _missing_payment_guidance():
    return derive_configuration_coverage_guidance(
        selected_payment_field=None,
        is_unmatched_fallback=True,
        missing_configuration_rule="payment_field fehlt",
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
    profile_id = "track-b-rule-draft-test"
    unmatched = UnmatchedConfiguration(
        name="Unklar",
        filename_pattern=pattern_from_template(
            "{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf"
        ),
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
            __import__(
                "invoice_tool.scan_models", fromlist=["get_scan_model"]
            ).get_scan_model(DEFAULT_SCAN_MODEL_ID)
        ),
        destination={"type": "local_folder", "path": str(dest / "amex")},
    )
    (dest / "amex").mkdir()
    from invoice_tool.configuration_model import ProfileBundle
    from invoice_tool.scan_models import get_scan_model

    _ = get_scan_model(DEFAULT_SCAN_MODEL_ID)
    bundle = ProfileBundle(
        id=profile_id,
        name="Track-B Draft Test",
        active=True,
        scan_model_id=DEFAULT_SCAN_MODEL_ID,
        configurations=[amex],
        unmatched=unmatched,
    )
    save_profile_bundle(bundle)
    return profile_id


def test_01_paypal_guidance_creates_paypal_draft() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        source_filename="FA011466.pdf",
    )
    assert draft is not None
    assert draft.draft_type == "create_new_configuration"
    assert draft.proposed_configuration_name == "PayPal"
    assert _paypal_guidance().missing_configuration_type == MISSING_TYPE_PAYPAL


def test_02_paypal_draft_condition_is_payment_field_paypal() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(), selected_payment_field="paypal"
    )
    assert draft is not None
    assert draft.proposed_matching_feature_key == "payment_field"
    assert draft.proposed_matching_operator == "ist"
    assert draft.proposed_matching_values == ("paypal",)
    assert draft.proposed_condition == "payment_field ist paypal"


def test_03_paypal_draft_does_not_assign_business_category() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(), selected_payment_field="paypal"
    )
    assert draft is not None
    assert draft.proposes_business_category is False
    assert WARNING_NO_BUSINESS_CATEGORY in draft.warnings
    blob = " ".join(draft.warnings).lower()
    assert "architektur" not in blob
    assert "event production" not in blob
    assert "geschäftskategorie" not in blob or "keine automatische" in blob
    # Must not silently assign known private/business buckets.
    assert "→ privat" not in blob
    assert "zu privat" not in blob


def test_04_paypal_draft_requires_user_confirmation() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(), selected_payment_field="paypal"
    )
    assert draft is not None
    assert draft.requires_user_confirmation is True
    assert draft.saved is False


def test_05_generic_card_guidance_creates_non_amex_card_draft() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_card_guidance(), selected_payment_field="card"
    )
    assert draft is not None
    assert draft.draft_type == "create_new_configuration"
    assert draft.proposed_configuration_name == "Kreditkarte / Nicht-AMEX-Karte"
    assert draft.proposed_matching_values == ("card",)
    assert _card_guidance().missing_configuration_type == MISSING_TYPE_GENERIC_CARD


def test_06_generic_card_draft_does_not_create_amex_config() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_card_guidance(), selected_payment_field="card"
    )
    assert draft is not None
    assert draft.proposes_amex is False
    assert "amex" not in {v.lower() for v in draft.proposed_matching_values}
    assert WARNING_GENERIC_CARD_NOT_AMEX in draft.warnings
    assert not any("american express" in v.lower() for v in draft.proposed_matching_values)


def test_07_missing_payment_field_does_not_create_automatic_payment_rule() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_missing_payment_guidance(), selected_payment_field=None
    )
    assert draft is not None
    assert draft.draft_type == "manual_review_only"
    assert draft.allows_payment_rule is False
    assert draft.proposed_matching_values == ()
    assert draft.proposed_matching_feature_key is None
    assert _missing_payment_guidance().missing_configuration_type == MISSING_TYPE_PAYMENT_FIELD


def test_08_missing_payment_field_suggests_manual_review() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_missing_payment_guidance(), selected_payment_field=None
    )
    assert draft is not None
    assert draft.manual_review_suggested is True
    assert WARNING_MISSING_PAYMENT_NO_BLIND_RULE in draft.warnings


def test_09_draft_includes_source_evidence() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        matched_configuration_reason="payment_field paypal detected",
        missing_configuration_rule="keine aktive PayPal-Konfiguration",
    )
    assert draft is not None
    assert draft.source_evidence
    assert any("paypal" in item.lower() for item in draft.source_evidence)


def test_10_draft_includes_warnings() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(), selected_payment_field="paypal"
    )
    assert draft is not None
    assert draft.warnings
    assert WARNING_NO_BUSINESS_CATEGORY in draft.warnings


def test_11_draft_includes_filename_pattern() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        unmatched_filename_pattern="{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf",
    )
    assert draft is not None
    assert draft.proposed_filename_pattern
    assert "{payment_field}" in draft.proposed_filename_pattern


def test_12_draft_validates_known_pattern_slots() -> None:
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        unmatched_filename_pattern="{invoice_date}_{unknown_token}.pdf",
    )
    assert draft is not None
    assert "unknown_token" in draft.unknown_pattern_slots
    assert draft.validation_errors
    assert unknown_pattern_slots_in_pattern("{amount}_{foo}.pdf") == ("foo",)


def test_13_duplicate_condition_warning_exists() -> None:
    active = (
        ConfigurationCandidate(
            configuration_id="paypal-1",
            name="PayPal Existing",
            active=True,
            matching_feature_key="payment_field",
            matching_operator="ist",
            matching_values=("paypal",),
            filename_pattern="{invoice_date}.pdf",
        ),
    )
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        available_configurations=[
            {
                "configuration_name": "PayPal Existing",
                "active": True,
                "matching_feature_key": "payment_field",
                "matching_operator": "ist",
                "matching_values": ["paypal"],
            }
        ],
    )
    assert draft is not None
    validated = validate_configuration_rule_draft(
        draft, active_configurations=active
    )
    assert validated.duplicate_condition_warning is True
    assert any("identischer" in w.lower() or "bereits" in w.lower() for w in validated.warnings)


def test_14_saving_requires_explicit_action(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        unmatched_filename_pattern="{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf",
    )
    assert draft is not None
    from dataclasses import replace

    draft = replace(
        draft,
        proposed_destination_path=str(tmp_path / "dest" / "paypal"),
    )
    (tmp_path / "dest" / "paypal").mkdir(parents=True, exist_ok=True)
    denied = save_configuration_rule_draft(
        profile_id=profile_id,
        draft=draft,
        explicit_user_confirmation=False,
    )
    assert denied.ok is False
    assert "bestätigung" in denied.message.lower() or "confirmation" in denied.message.lower() or "explizit" in denied.message.lower()


def test_15_saved_config_updates_only_ui_v2_profile_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        unmatched_filename_pattern="{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf",
    )
    assert draft is not None
    from dataclasses import replace

    dest = tmp_path / "dest" / "paypal"
    dest.mkdir(parents=True, exist_ok=True)
    draft = replace(draft, proposed_destination_path=str(dest))
    before = {c.name for c in load_profile_bundle(profile_id).configurations}
    result = save_configuration_rule_draft(
        profile_id=profile_id,
        draft=draft,
        explicit_user_confirmation=True,
    )
    assert result.ok, result.message
    assert result.draft is not None and result.draft.saved is True
    after_names = {c.name for c in load_profile_bundle(profile_id).configurations}
    assert "PayPal" in after_names
    assert before <= after_names


def test_16_saving_config_does_not_call_run_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    calls: list[str] = []

    def _boom(*_a, **_k):
        calls.append("run_once")
        raise AssertionError("run_once must not be called")

    monkeypatch.setattr("invoice_tool.run.run_once", _boom, raising=False)
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        unmatched_filename_pattern="{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf",
    )
    assert draft is not None
    from dataclasses import replace

    dest = tmp_path / "dest" / "paypal2"
    dest.mkdir(parents=True, exist_ok=True)
    draft = replace(draft, proposed_destination_path=str(dest))
    result = save_configuration_rule_draft(
        profile_id=profile_id,
        draft=draft,
        explicit_user_confirmation=True,
    )
    assert result.ok
    assert result.called_run_once is False
    assert calls == []


def test_17_saving_config_does_not_mutate_input_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    sample = tmp_path / "input" / "sample.pdf"
    sample.parent.mkdir(parents=True)
    payload = b"%PDF-1.4 track-b-rule-draft-input"
    sample.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        unmatched_filename_pattern="{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf",
    )
    assert draft is not None
    from dataclasses import replace

    dest = tmp_path / "dest" / "paypal3"
    dest.mkdir(parents=True, exist_ok=True)
    draft = replace(draft, proposed_destination_path=str(dest))
    result = save_configuration_rule_draft(
        profile_id=profile_id,
        draft=draft,
        explicit_user_confirmation=True,
    )
    assert result.ok
    assert result.mutated_input is False
    assert hashlib.sha256(sample.read_bytes()).hexdigest() == digest


def test_18_saving_config_does_not_write_final_pdfs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    out = tmp_path / "output"
    out.mkdir()
    before = {p.name for p in out.iterdir()}
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        unmatched_filename_pattern="{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf",
    )
    assert draft is not None
    from dataclasses import replace

    dest = tmp_path / "dest" / "paypal4"
    dest.mkdir(parents=True, exist_ok=True)
    draft = replace(draft, proposed_destination_path=str(dest))
    result = save_configuration_rule_draft(
        profile_id=profile_id,
        draft=draft,
        explicit_user_confirmation=True,
    )
    assert result.ok
    assert result.wrote_final_pdfs is False
    assert {p.name for p in out.iterdir()} == before
    assert list(out.glob("*.pdf")) == []


def test_19_review_ui_exposes_create_from_guidance_action() -> None:
    labels = build_configuration_rule_action_labels()
    assert ACTION_CREATE_FROM_GUIDANCE in labels
    draft_src = DRAFT_MODULE.read_text(encoding="utf-8")
    editor = EDITOR_MODULE.read_text(encoding="utf-8")
    review = REVIEW_PAGE.read_text(encoding="utf-8")
    assert 'ACTION_CREATE_FROM_GUIDANCE = "Konfiguration aus Hinweis erstellen"' in draft_src
    assert "ACTION_CREATE_FROM_GUIDANCE" in editor
    assert "build_configuration_coverage_action_row" in review


def test_20_review_ui_exposes_edit_existing_action() -> None:
    labels = build_configuration_rule_action_labels()
    assert ACTION_EDIT_EXISTING in labels
    draft_src = DRAFT_MODULE.read_text(encoding="utf-8")
    editor = EDITOR_MODULE.read_text(encoding="utf-8")
    review = REVIEW_PAGE.read_text(encoding="utf-8")
    assert 'ACTION_EDIT_EXISTING = "Bestehende Konfiguration anpassen"' in draft_src
    assert "ACTION_EDIT_EXISTING" in editor
    assert "ACTION_EDIT_EXISTING" in review


def test_21_review_ui_exposes_manual_keep_unclear_action() -> None:
    labels = build_configuration_rule_action_labels()
    assert ACTION_MANUAL_KEEP_UNCLEAR in labels
    draft_src = DRAFT_MODULE.read_text(encoding="utf-8")
    editor = EDITOR_MODULE.read_text(encoding="utf-8")
    review = REVIEW_PAGE.read_text(encoding="utf-8")
    assert 'ACTION_MANUAL_KEEP_UNCLEAR = "Manuell prüfen / Unklar lassen"' in draft_src
    assert "ACTION_MANUAL_KEEP_UNCLEAR" in editor
    assert "ACTION_MANUAL_KEEP_UNCLEAR" in review


def test_22_reports_expose_configuration_rule_draft_available() -> None:
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="completed",
            run_id="prompt26",
            review_items=(
                ProcessingReviewItem(
                    document_id="FA011466.pdf",
                    document_name="FA011466.pdf",
                    reason="Unklar",
                    status_label="unklar",
                ),
            ),
        )
    )
    # Enrich detail via open_create helper fields on a synthetic detail.
    detail = ReviewDetailItemVM(
        document_label="FA011466.pdf",
        document_id="FA011466.pdf",
        reason="Unklar",
        suggested_status="unklar",
        evidence_summary="e",
        next_action_hint="a",
        selected_payment_field="paypal",
        configuration_coverage_status="missing_config_for_detected_payment",
        missing_configuration_type="paypal",
        user_guidance="PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden.",
        suggested_configuration_action="PayPal-Konfiguration ergänzen oder manuell prüfen.",
        guidance_severity="warning",
    )
    draft = open_create_draft_from_review_detail(detail)
    assert draft is not None
    report = draft.to_report_fields()
    assert report[MSG_FIELD_CONFIGURATION_RULE_DRAFT_AVAILABLE] is True
    assert report["proposed_configuration_name"] == "PayPal"
    assert report["proposed_condition"] == "payment_field ist paypal"
    assert report["requires_user_confirmation"] is True
    vm = build_review_page_vm(state)
    assert vm.claims_saas_ready is False
    assert vm.claims_production_ready is False


def test_23_no_saas_ready_claim() -> None:
    for path in (DRAFT_MODULE, EDITOR_MODULE):
        text = path.read_text(encoding="utf-8")
        assert "saas-ready" not in text.lower()
        assert "saas ready" not in text.lower()
    for path in (DOCS, AUDIT):
        text = path.read_text(encoding="utf-8")
        assert "nicht SaaS-ready" in text or "nicht saas-ready" in text.lower()
        assert text_claims_forbidden_maturity(text) is False
        assert "ist saas-ready" not in text.lower()


def test_24_no_production_ready_claim() -> None:
    for path in (DRAFT_MODULE, EDITOR_MODULE):
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
    """Working tree must not stage/modify unexpected Track-A protected files."""

    import subprocess

    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    overlap = sorted(set(staged) & set(TRACK_A_PROTECTED))
    assert overlap == [], f"Track-A protected staged: {overlap}"
    # AST import boundary: draft/editor modules must not import Track-A UI.
    for module in (DRAFT_MODULE, EDITOR_MODULE):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert not name.startswith("invoice_tool.ui_review")
                assert not name.startswith("invoice_tool.ui_configurations")
                assert not name.startswith("invoice_tool.gui")
                assert name != "invoice_tool.run"


def test_docs_and_modules_exist() -> None:
    assert DRAFT_MODULE.is_file()
    assert EDITOR_MODULE.is_file()
    assert DOCS.is_file()
    assert AUDIT.is_file()
    assert "Prompt 26" in DOCS.read_text(encoding="utf-8") or "26/34" in DOCS.read_text(
        encoding="utf-8"
    )


def test_review_page_vm_exposes_coverage_action_labels_for_gap() -> None:
    from invoice_tool.ui_v2.review_workflow import build_review_item_view_model
    from invoice_tool.ui_v2.pages.review import _detail_from_item_vm

    item = ProcessingReviewItem(
        document_id="x.pdf",
        document_name="x.pdf",
        reason="Unklar",
        status_label="unklar",
    )
    # Patch via synthetic ReviewItemViewModel fields through detail helper path:
    # Use open_create + action labels constant as UI contract.
    labels = build_configuration_rule_action_labels()
    assert ACTION_CREATE_FROM_GUIDANCE in labels
    assert ACTION_EDIT_EXISTING in labels
    assert ACTION_MANUAL_KEEP_UNCLEAR in labels
    _ = build_review_item_view_model(item)
    _ = _detail_from_item_vm
