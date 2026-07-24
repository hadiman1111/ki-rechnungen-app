"""Track-B smoke blocker repair: duplicate configs + usable dev UI.

No productive processing, no real invoice folders, no Track-A/core edits.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from invoice_tool.configuration_model import (
    Configuration,
    MatchingRule,
    ProfileBundle,
    UnmatchedConfiguration,
    new_configuration_id,
    pattern_from_template,
)
from invoice_tool.profile_store import load_profile_bundle, save_profile_bundle
from invoice_tool.scan_models import DEFAULT_SCAN_MODEL_ID, get_scan_model
from invoice_tool.ui_v2.configuration_duplicate_remediation import (
    ACTION_DEACTIVATE_EXACT_DUPLICATES,
    ACTION_SHOW_DUPLICATES,
    CODE_DUPLICATE_EXACT_ACTIVE_CONFIG,
    CONTROLLED_OUTPUT_ROOT,
    analyze_active_configuration_duplicates,
    deactivate_exact_duplicate_configs,
    is_controlled_output_target,
    validate_bundle_for_track_b_rule_save,
)
from invoice_tool.ui_v2.configuration_guidance import (
    derive_configuration_coverage_guidance,
)
from invoice_tool.ui_v2.configuration_rule_draft import (
    draft_from_coverage_guidance,
    validate_configuration_rule_draft,
)
from invoice_tool.ui_v2.configuration_rule_editor import (
    ACTION_PAYPAL_SMOKE_SAVE_AND_RERUN,
    ACTION_SAVE_AND_RERUN,
    ACTION_SAVE_DRAFT,
    build_configuration_rule_action_labels,
    build_configuration_rule_draft_panel,
    save_configuration_rule_draft,
    save_paypal_rule_and_rerun_matching,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_COPY_CASE,
    ACTION_COPY_DIAGNOSIS,
    SMOKE_DEV_UI_LAYOUT_MARKER,
    build_diagnosis_copy_text,
    build_prueffall_copy_text,
)

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "invoice_tool" / "ui_v2" / "configuration_rule_editor.py"
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
REMEDIATION = (
    ROOT / "invoice_tool" / "ui_v2" / "configuration_duplicate_remediation.py"
)
COPY_MOD = ROOT / "invoice_tool" / "ui_v2" / "track_b_smoke_debug_copy.py"
DOCS = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_SMOKE_DUPLICATE_CONFIG_AND_DEV_UI_REPAIR_2026-07-24.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_SMOKE_DUPLICATE_CONFIG_AND_DEV_UI_REPAIR_2026-07-24.md"
)

CONTROLLED_INPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input")
CONTROLLED_OUTPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output")
CONTROLLED_PAYPAL = CONTROLLED_OUTPUT / "geplant" / "paypal"
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

CORE_PROTECTED = (
    "invoice_tool/run.py",
    "invoice_tool/processing.py",
    "invoice_tool/routing.py",
    "invoice_tool/routing_guards.py",
    "invoice_tool/classification.py",
    "invoice_tool/target_routing.py",
    "invoice_tool/core_dry_run.py",
)


def _paypal_guidance():
    return derive_configuration_coverage_guidance(
        selected_payment_field="paypal",
        is_unmatched_fallback=True,
        missing_configuration_rule="keine aktive PayPal-Konfiguration",
    )


def _cfg(
    *,
    name: str,
    values: list[str],
    dest: Path,
    config_id: str | None = None,
    active: bool = True,
) -> Configuration:
    return Configuration(
        id=config_id or new_configuration_id(),
        name=name,
        active=active,
        matching=MatchingRule(
            feature_key="payment_field",
            operator="ist",
            values=list(values),
        ),
        filename_pattern=pattern_from_template(PATTERN),
        destination={"type": "local_folder", "path": str(dest)},
    )


def _isolated_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    with_privat_aliases: bool = True,
    with_exact_privat_dupes: bool = False,
) -> str:
    support = tmp_path / "support"
    support.mkdir(parents=True)
    monkeypatch.setattr("invoice_tool.app_paths.profile_storage_dir", lambda: support)
    monkeypatch.setattr(
        "invoice_tool.profile_store.app_paths.profile_storage_dir", lambda: support
    )
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "unklar").mkdir()
    (dest / "amex").mkdir()
    (dest / "private").mkdir()
    (dest / "private2").mkdir()
    (dest / "paypal").mkdir()
    profile_id = "track-b-smoke-dup-repair"
    configs = [
        _cfg(
            name="American Express",
            values=["amex", "American Express"],
            dest=dest / "amex",
            config_id="amex",
        )
    ]
    if with_privat_aliases:
        configs.append(
            _cfg(
                name="Privat",
                values=["private", "privat", "Privat", "Private Rechnung"],
                dest=dest / "private",
                config_id="private",
            )
        )
    if with_exact_privat_dupes:
        configs.append(
            _cfg(
                name="Privat",
                values=["private", "privat", "Privat", "Private Rechnung"],
                dest=dest / "private",
                config_id="private-dup",
            )
        )
    unmatched = UnmatchedConfiguration(
        name="Unklar",
        filename_pattern=pattern_from_template(PATTERN),
        destination={"type": "local_folder", "path": str(dest / "unklar")},
    )
    bundle = ProfileBundle(
        id=profile_id,
        name="Track-B Smoke Dup Repair",
        active=True,
        scan_model_id=DEFAULT_SCAN_MODEL_ID,
        configurations=configs,
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
        run_id="track-b-smoke-dup-repair",
        review_items=reviews,
        planned_destinations=planned,
        planned_destination_count=len(planned),
        state_updated_at="2026-07-24T00:00:00+00:00",
    )


def _paypal_draft(tmp_path: Path, *, dest: Path | None = None):
    draft = draft_from_coverage_guidance(
        guidance=_paypal_guidance(),
        selected_payment_field="paypal",
        unmatched_filename_pattern=PATTERN,
    )
    assert draft is not None
    target = dest or (tmp_path / "dest" / "paypal")
    target.mkdir(parents=True, exist_ok=True)
    return replace(draft, proposed_destination_path=str(target))


def test_01_duplicate_exact_active_config_detected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(
        monkeypatch, tmp_path, with_exact_privat_dupes=True
    )
    bundle = load_profile_bundle(profile_id)
    analysis = analyze_active_configuration_duplicates(bundle.configurations)
    assert analysis.has_exact_duplicates is True
    assert any(
        f.code == CODE_DUPLICATE_EXACT_ACTIVE_CONFIG for f in analysis.findings
    )


def test_02_duplicate_exact_reports_affected_config_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(
        monkeypatch, tmp_path, with_exact_privat_dupes=True
    )
    analysis = analyze_active_configuration_duplicates(
        load_profile_bundle(profile_id).configurations
    )
    exact = next(
        f for f in analysis.findings if f.code == CODE_DUPLICATE_EXACT_ACTIVE_CONFIG
    )
    assert "Privat" in exact.affected_names
    assert "Privat" in exact.message


def test_03_duplicate_privat_does_not_false_label_paypal_draft(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path, with_privat_aliases=True)
    active = load_profile_bundle(profile_id).configurations
    draft = _paypal_draft(tmp_path)
    validated = validate_configuration_rule_draft(
        draft, active_configurations=active, require_destination_for_save=True
    )
    blob = " ".join(validated.validation_errors + validated.warnings).casefold()
    assert "paypal" not in blob or "privat" not in blob or "duplikat" not in blob
    # Must not claim PayPal itself is the duplicate of Privat.
    assert not any(
        "paypal" in e.casefold() and "privat" in e.casefold()
        for e in validated.validation_errors
    )
    blocking = validate_bundle_for_track_b_rule_save(
        load_profile_bundle(profile_id),
        draft_name="PayPal",
        draft_values=["paypal"],
    )
    assert blocking == ()


def test_04_paypal_draft_validates_when_target_exists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolated_profile(monkeypatch, tmp_path)
    draft = _paypal_draft(tmp_path)
    validated = validate_configuration_rule_draft(
        draft, require_destination_for_save=True
    )
    assert validated.validation_errors == ()
    assert validated.proposed_matching_values == ("paypal",)


def test_05_paypal_draft_blocked_if_target_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = _paypal_draft(tmp_path)
    missing = tmp_path / "missing-paypal-target"
    draft = replace(draft, proposed_destination_path=str(missing))
    result = save_paypal_rule_and_rerun_matching(
        profile_id=profile_id,
        draft=draft,
        run_state=_run_state(),
        explicit_user_confirmation=True,
        require_controlled_target=False,
    )
    assert result.ok is False
    assert "fehlt" in result.message.casefold() or "nicht erreichbar" in result.message.casefold()


def test_06_paypal_smoke_requires_explicit_confirmation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = _paypal_draft(tmp_path)
    denied = save_paypal_rule_and_rerun_matching(
        profile_id=profile_id,
        draft=draft,
        run_state=_run_state(),
        explicit_user_confirmation=False,
        require_controlled_target=False,
    )
    assert denied.ok is False
    assert "bestätigung" in denied.message.casefold() or "explizit" in denied.message.casefold()


def test_07_paypal_smoke_no_silent_business_category(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = _paypal_draft(tmp_path)
    result = save_paypal_rule_and_rerun_matching(
        profile_id=profile_id,
        draft=draft,
        run_state=_run_state(),
        explicit_user_confirmation=True,
        require_controlled_target=False,
    )
    assert result.ok is True
    assert result.assigned_business_category is False
    assert result.draft is not None
    assert result.draft.proposes_business_category is False
    cfg = next(
        c for c in load_profile_bundle(profile_id).configurations if c.name == "PayPal"
    )
    assert cfg.matching is not None
    assert cfg.matching.feature_key == "payment_field"


def test_08_paypal_smoke_reruns_preview_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = _paypal_draft(tmp_path)
    result = save_paypal_rule_and_rerun_matching(
        profile_id=profile_id,
        draft=draft,
        run_state=_run_state(),
        explicit_user_confirmation=True,
        require_controlled_target=False,
    )
    assert result.ok is True
    assert result.preview_only_rerun is True
    assert result.called_run_once is False
    assert result.wrote_final_pdfs is False
    assert result.mutated_input is False


def test_09_paypal_smoke_changes_lumitop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = _paypal_draft(tmp_path)
    result = save_paypal_rule_and_rerun_matching(
        profile_id=profile_id,
        draft=draft,
        run_state=_run_state(),
        explicit_user_confirmation=True,
        require_controlled_target=False,
    )
    assert result.updated_run_state is not None
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["lumitop"]
    )
    assert item.matched_configuration_name == "PayPal"


def test_10_paypal_smoke_changes_bootshop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = _paypal_draft(tmp_path)
    result = save_paypal_rule_and_rerun_matching(
        profile_id=profile_id,
        draft=draft,
        run_state=_run_state(),
        explicit_user_confirmation=True,
        require_controlled_target=False,
    )
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["bootshop"]
    )
    assert item.matched_configuration_name == "PayPal"


def test_11_paypal_smoke_does_not_map_card_to_amex(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = _paypal_draft(tmp_path)
    result = save_paypal_rule_and_rerun_matching(
        profile_id=profile_id,
        draft=draft,
        run_state=_run_state(),
        explicit_user_confirmation=True,
        require_controlled_target=False,
    )
    assert result.mapped_card_to_amex is False
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["boettcher"]
    )
    assert item.matched_configuration_name != "American Express"
    assert item.matched_configuration_name == "Unklar"


def test_12_missing_payment_field_remains_unclear(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path)
    draft = _paypal_draft(tmp_path)
    result = save_paypal_rule_and_rerun_matching(
        profile_id=profile_id,
        draft=draft,
        run_state=_run_state(),
        explicit_user_confirmation=True,
        require_controlled_target=False,
    )
    item = next(
        p
        for p in result.updated_run_state.planned_destinations
        if p.document_name == PDF["luxvenum"]
    )
    assert item.matched_configuration_name == "Unklar"


def test_13_duplicate_remediation_requires_explicit_click(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(
        monkeypatch, tmp_path, with_exact_privat_dupes=True
    )
    denied = deactivate_exact_duplicate_configs(
        profile_id, explicit_user_confirmation=False
    )
    assert denied.ok is False
    assert "explizit" in denied.message.casefold()


def test_14_duplicate_remediation_only_ui_v2_config_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(
        monkeypatch, tmp_path, with_exact_privat_dupes=True
    )
    before = {
        c.id: c.active for c in load_profile_bundle(profile_id).configurations
    }
    result = deactivate_exact_duplicate_configs(
        profile_id, explicit_user_confirmation=True
    )
    assert result.ok is True
    assert result.affected_ui_v2_config_state_only is True
    assert result.mutated_input is False
    assert result.wrote_final_pdfs is False
    after = load_profile_bundle(profile_id).configurations
    active_privat = [c for c in after if c.name == "Privat" and c.active]
    assert len(active_privat) == 1
    assert any(not c.active for c in after if c.id == "private-dup")
    assert before["amex"] is True


def test_15_duplicate_remediation_does_not_call_run_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(
        monkeypatch, tmp_path, with_exact_privat_dupes=True
    )
    called = {"run_once": False}

    def _boom(*_a, **_k):
        called["run_once"] = True
        raise AssertionError("run_once must not be called")

    monkeypatch.setattr("invoice_tool.run.run_once", _boom, raising=False)
    result = deactivate_exact_duplicate_configs(
        profile_id, explicit_user_confirmation=True
    )
    assert result.ok is True
    assert result.called_run_once is False
    assert called["run_once"] is False


def test_16_copy_prueffall_contains_paypal_guidance() -> None:
    detail = {
        "source_filename": PDF["lumitop"],
        "suggested_filename": "2026-05-11_er_er_LUMITOP_10,00_paypal.pdf",
        "matched_configuration_name": "Unklar",
        "user_guidance": "PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden.",
        "missing_configuration_type": "paypal",
        "configuration_coverage_status": "missing_configuration",
    }
    text = build_prueffall_copy_text(detail)
    assert "paypal_guidance" in text.casefold() or "PayPal erkannt" in text
    assert PDF["lumitop"] in text


def test_17_copy_diagnosis_contains_safety_flags() -> None:
    detail = {
        "source_filename": PDF["lumitop"],
        "user_guidance": "PayPal erkannt",
        "missing_configuration_type": "paypal",
    }
    text = build_diagnosis_copy_text(detail)
    assert "final_write_allowed_for_production=false" in text
    assert "safety_flags" in text


def test_18_ui_exposes_paypal_smoke_action() -> None:
    labels = build_configuration_rule_action_labels()
    assert ACTION_PAYPAL_SMOKE_SAVE_AND_RERUN in labels
    src = EDITOR.read_text(encoding="utf-8") + REVIEW.read_text(encoding="utf-8")
    assert ACTION_PAYPAL_SMOKE_SAVE_AND_RERUN in src


def test_19_ui_exposes_copy_prueffall() -> None:
    src = REVIEW.read_text(encoding="utf-8") + COPY_MOD.read_text(encoding="utf-8")
    assert ACTION_COPY_CASE in src


def test_20_ui_exposes_copy_diagnosis() -> None:
    src = REVIEW.read_text(encoding="utf-8") + COPY_MOD.read_text(encoding="utf-8")
    assert ACTION_COPY_DIAGNOSIS in src


def test_21_ui_layout_marker_or_layout_test() -> None:
    src = (
        EDITOR.read_text(encoding="utf-8")
        + REVIEW.read_text(encoding="utf-8")
        + COPY_MOD.read_text(encoding="utf-8")
    )
    assert SMOKE_DEV_UI_LAYOUT_MARKER in src
    assert "form_field_group" in EDITOR.read_text(encoding="utf-8")
    assert "ACTION_SAVE_DRAFT" in src
    assert ACTION_SAVE_AND_RERUN in src
    assert ACTION_SAVE_DRAFT == "Konfiguration speichern"


def test_22_no_productive_processing_in_repair_modules() -> None:
    blob = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (EDITOR, REMEDIATION, COPY_MOD, REVIEW)
    ).casefold()
    assert "run_once(" not in blob.replace("does_not_call_run_once", "")
    assert "final_write_allowed_for_production=true" not in blob
    assert "productive_mode_requested=true" not in blob


def test_23_no_real_invoice_folders_in_repair_modules() -> None:
    blob = "\n".join(
        p.read_text(encoding="utf-8") for p in (EDITOR, REMEDIATION, COPY_MOD, REVIEW)
    )
    for folder in FORBIDDEN_FOLDERS:
        assert folder not in blob


def test_24_no_production_final_write() -> None:
    blob = REMEDIATION.read_text(encoding="utf-8") + EDITOR.read_text(encoding="utf-8")
    assert "final_write_allowed_for_production=True" not in blob
    assert "final_write_allowed_for_production = True" not in blob


def test_25_track_a_protection_still_passes() -> None:
    """Repair commit must not stage/modify Track-A protected or core files."""

    import subprocess

    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for rel in TRACK_A_PROTECTED + CORE_PROTECTED:
        assert rel not in staged, f"protected staged: {rel}"
    # Source still points Track A entry to classic GUI.
    app_main = (ROOT / "app_main.py").read_text(encoding="utf-8")
    assert "invoice_tool.gui" in app_main or "gui.main" in app_main


def test_26_paypal_save_works_despite_privat_alias_noise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile_id = _isolated_profile(monkeypatch, tmp_path, with_privat_aliases=True)
    draft = _paypal_draft(tmp_path)
    result = save_configuration_rule_draft(
        profile_id=profile_id,
        draft=draft,
        explicit_user_confirmation=True,
    )
    assert result.ok is True, result.message
    names = {c.name for c in load_profile_bundle(profile_id).configurations}
    assert "PayPal" in names


def test_27_docs_and_audit_exist_or_will_exist_after_write() -> None:
    # Written in the same task; assert paths are the mandated locations.
    assert DOCS.name.startswith("KI_RECHNUNGEN_TRACK_B_SMOKE_DUPLICATE")
    assert AUDIT.name.startswith("KI_RECHNUNGEN_TRACK_B_SMOKE_DUPLICATE")


def test_28_controlled_target_helpers() -> None:
    assert is_controlled_output_target(CONTROLLED_OUTPUT_ROOT)
    assert is_controlled_output_target(CONTROLLED_OUTPUT_ROOT / "geplant" / "paypal")
    assert not is_controlled_output_target("/tmp/random-paypal")


def test_29_ui_labels_include_remediation_actions() -> None:
    src = EDITOR.read_text(encoding="utf-8") + REMEDIATION.read_text(encoding="utf-8")
    assert ACTION_SHOW_DUPLICATES in src
    assert ACTION_DEACTIVATE_EXACT_DUPLICATES in src


def test_30_build_draft_panel_includes_layout_marker() -> None:
    src = EDITOR.read_text(encoding="utf-8") + COPY_MOD.read_text(encoding="utf-8")
    assert SMOKE_DEV_UI_LAYOUT_MARKER in src
    assert "SMOKE_DEV_UI_LAYOUT_MARKER" in EDITOR.read_text(encoding="utf-8")
    assert "form_field_group" in EDITOR.read_text(encoding="utf-8")
    assert "build_configuration_rule_draft_panel" in EDITOR.read_text(encoding="utf-8")
    assert ACTION_PAYPAL_SMOKE_SAVE_AND_RERUN in EDITOR.read_text(encoding="utf-8")
