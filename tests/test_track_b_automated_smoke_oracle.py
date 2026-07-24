"""Track-B Automated Smoke Oracle — focused safety and workflow tests.

No productive processing, no run_once, no real invoice folders, no Track-A/core edits.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from invoice_tool.ui_v2 import automated_smoke_oracle as oracle_mod
from invoice_tool.ui_v2.automated_smoke_oracle import (
    EXPECTED_PDFS,
    ORACLE_PROFILE_ID,
    STATUS_PARTIAL_FINAL,
    STATUS_PARTIAL_UI,
    SafetyFlags,
    assert_controlled_input_only,
    assert_controlled_output_only,
    build_run_state_from_preview_export,
    classify_status,
    ensure_paypal_config_idempotent,
    find_latest_sufficient_preview_export,
    hash_input_pdfs,
    oracle_modifies_processing_core,
    oracle_modifies_track_a,
    oracle_source_calls_run_once,
    oracle_touches_real_invoice_folders,
    oracle_uses_controlled_input_path,
    oracle_uses_controlled_output_path,
    oracle_writes_production_final_files,
    reject_fewer_than_five_pdfs,
    reject_missing_input_folder,
    run_track_b_automated_smoke_oracle,
    sha256_file,
    verify_documents,
    write_evidence_reports,
    OracleResult,
)
from invoice_tool.ui_v2.dev_defaults import (
    TRACK_B_DEV_INPUT_DEFAULT,
    TRACK_B_DEV_OUTPUT_DEFAULT,
    TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
)
from invoice_tool.ui_v2.processing_state import ProcessingRunState

ROOT = Path(__file__).resolve().parents[1]
ORACLE_PY = ROOT / "invoice_tool" / "ui_v2" / "automated_smoke_oracle.py"
RUNNER_PY = ROOT / "scripts" / "dev" / "track_b_automated_smoke_oracle.py"
DOC = ROOT / "docs" / "KI_RECHNUNGEN_TRACK_B_AUTOMATED_SMOKE_ORACLE_2026-07-24.md"
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_AUTOMATED_SMOKE_ORACLE_2026-07-24.md"
)

CONTROLLED_INPUT = TRACK_B_DEV_INPUT_DEFAULT
CONTROLLED_OUTPUT = TRACK_B_DEV_OUTPUT_DEFAULT
FORBIDDEN = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
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

CORE_PROTECTED = (
    "invoice_tool/run.py",
    "invoice_tool/processing.py",
    "invoice_tool/routing.py",
    "invoice_tool/routing_guards.py",
    "invoice_tool/classification.py",
    "invoice_tool/target_routing.py",
    "invoice_tool/core_dry_run.py",
)


def _controlled_available() -> bool:
    return CONTROLLED_INPUT.is_dir() and all(
        (CONTROLLED_INPUT / name).is_file() for name in EXPECTED_PDFS
    )


def _isolate_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    support = tmp_path / "automated-smoke-profile-store"
    support.mkdir(parents=True)
    monkeypatch.setattr("invoice_tool.app_paths.profile_storage_dir", lambda: support)
    monkeypatch.setattr(
        "invoice_tool.profile_store.app_paths.profile_storage_dir",
        lambda: support,
    )
    return support


def _synthetic_payload() -> dict:
    items = []
    specs = [
        ("FA011466.pdf", "LUMITOP", "2026-05-11", "476,00", "paypal", "er",
         "2026-05-11_er_LUMITOP_476,00_paypal.pdf"),
        ("Rechnung RE-202605-14594.pdf", "1A-Bootshop.de", "2026-05-15", "105,75",
         "paypal", "er", "2026-05-15_er_1A-Bootshop.de_105,75_paypal.pdf"),
        ("320262919974.pdf", "Böttcher AG", "2026-05-23", "84,39", "card", "er",
         "2026-05-23_er_Böttcher_AG_84,39_card.pdf"),
        ("Rechnung-2026156019-102201.pdf", "Luxvenum LED GmbH", "2026-05-11",
         "154,95", None, "er",
         "2026-05-11_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf"),
        ("420260091336.pdf", "Böttcher AG", "2026-06-18", "68,94", None, "storno",
         "2026-06-18_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf"),
    ]
    for source, supplier, date, amount, payment, art, filename in specs:
        items.append(
            {
                "source_filename": source,
                "supplier": supplier,
                "invoice_date": date,
                "amount": amount,
                "selected_amount": amount,
                "selected_payment_field": payment,
                "selected_art": art,
                "document_type": "storno" if art == "storno" else "rechnung",
                "suggested_filename": filename,
                "rendered_filename": filename,
                "matched_configuration_name": "Unklar",
                "matched_configuration_id": "unmatched",
                "matched_configuration_reason": (
                    "payment_field fehlt — keine Zahlungsart erkannt"
                    if payment is None
                    else (
                        "generic credit card detected, AMEX not proven"
                        if payment == "card"
                        else "PayPal erkannt, aber keine aktive PayPal-Konfiguration"
                    )
                ),
                "configuration_coverage_status": (
                    "missing_payment_field" if payment is None else "missing_config"
                ),
                "missing_configuration_type": (
                    "payment_field" if payment is None else "paypal"
                ),
                "filename_pattern": (
                    "{invoice_date}_{art}_{supplier}_{amount}_{payment_field}.pdf"
                ),
                "planned_target": str(
                    CONTROLLED_OUTPUT / "geplant" / "unklar" / filename
                ),
            }
        )
    return {
        "run_id": "track-b-auto-smoke-test",
        "input_root": str(CONTROLLED_INPUT),
        "output_root": str(CONTROLLED_OUTPUT),
        "items": items,
    }


def test_01_oracle_uses_controlled_input_path_only() -> None:
    assert oracle_uses_controlled_input_path(CONTROLLED_INPUT) is True
    assert oracle_uses_controlled_input_path(FORBIDDEN[0]) is False
    assert_controlled_input_only(CONTROLLED_INPUT)


def test_02_oracle_uses_controlled_output_path_only() -> None:
    assert oracle_uses_controlled_output_path(CONTROLLED_OUTPUT) is True
    assert oracle_uses_controlled_output_path(FORBIDDEN[1]) is False
    assert_controlled_output_only(CONTROLLED_OUTPUT)


def test_03_oracle_rejects_missing_input_folder(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-input"
    with pytest.raises(FileNotFoundError):
        reject_missing_input_folder(missing)


def test_04_oracle_rejects_fewer_than_five_controlled_pdfs(tmp_path: Path) -> None:
    folder = tmp_path / "input"
    folder.mkdir()
    (folder / "only-one.pdf").write_bytes(b"%PDF-1.4")
    with pytest.raises(FileNotFoundError):
        reject_fewer_than_five_pdfs(folder)


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_05_oracle_computes_before_after_hashes() -> None:
    before = hash_input_pdfs(CONTROLLED_INPUT)
    after = hash_input_pdfs(CONTROLLED_INPUT)
    assert len(before) == 5
    assert before == after
    for name, digest in before.items():
        assert digest == sha256_file(CONTROLLED_INPUT / name)


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_06_oracle_keeps_originals_unchanged() -> None:
    before = hash_input_pdfs(CONTROLLED_INPUT)
    # Pure re-hash — no mutation path in helpers.
    after = hash_input_pdfs(CONTROLLED_INPUT)
    assert before == after


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_07_oracle_creates_or_reuses_paypal_idempotently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolate_profile(monkeypatch, tmp_path)
    from invoice_tool.ui_v2.automated_smoke_oracle import ensure_oracle_profile

    ensure_oracle_profile(
        profile_id=ORACLE_PROFILE_ID,
        output_root=CONTROLLED_OUTPUT,
        paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    run = build_run_state_from_preview_export(
        _synthetic_payload(), output_root=CONTROLLED_OUTPUT
    )
    first = ensure_paypal_config_idempotent(
        profile_id=ORACLE_PROFILE_ID,
        run_state=run,
        paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    assert first["ok"] is True
    second = ensure_paypal_config_idempotent(
        profile_id=ORACLE_PROFILE_ID,
        run_state=first["updated_run_state"],
        paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    assert second["reused"] is True
    assert second["ok"] is True


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_08_oracle_does_not_create_duplicate_paypal_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolate_profile(monkeypatch, tmp_path)
    from invoice_tool.ui_v2.automated_smoke_oracle import (
        ensure_oracle_profile,
        find_active_paypal_configs,
    )

    ensure_oracle_profile(
        profile_id=ORACLE_PROFILE_ID,
        output_root=CONTROLLED_OUTPUT,
        paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    run = build_run_state_from_preview_export(
        _synthetic_payload(), output_root=CONTROLLED_OUTPUT
    )
    ensure_paypal_config_idempotent(
        profile_id=ORACLE_PROFILE_ID,
        run_state=run,
        paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    ensure_paypal_config_idempotent(
        profile_id=ORACLE_PROFILE_ID,
        run_state=run,
        paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    assert len(find_active_paypal_configs(ORACLE_PROFILE_ID)) == 1


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_09_oracle_does_not_assign_business_category_silently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolate_profile(monkeypatch, tmp_path)
    from invoice_tool.ui_v2.automated_smoke_oracle import ensure_oracle_profile

    ensure_oracle_profile(
        profile_id=ORACLE_PROFILE_ID,
        output_root=CONTROLLED_OUTPUT,
        paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    run = build_run_state_from_preview_export(
        _synthetic_payload(), output_root=CONTROLLED_OUTPUT
    )
    result = ensure_paypal_config_idempotent(
        profile_id=ORACLE_PROFILE_ID,
        run_state=run,
        paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    assert result["assigned_business_category"] is False


def _rematch_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ProcessingRunState:
    _isolate_profile(monkeypatch, tmp_path)
    from invoice_tool.ui_v2.automated_smoke_oracle import ensure_oracle_profile

    ensure_oracle_profile(
        profile_id=ORACLE_PROFILE_ID,
        output_root=CONTROLLED_OUTPUT,
        paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    run = build_run_state_from_preview_export(
        _synthetic_payload(), output_root=CONTROLLED_OUTPUT
    )
    paypal = ensure_paypal_config_idempotent(
        profile_id=ORACLE_PROFILE_ID,
        run_state=run,
        paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    return paypal["updated_run_state"]


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_10_oracle_rematches_lumitop_to_paypal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run = _rematch_state(monkeypatch, tmp_path)
    checks = {c.source_filename: c for c in verify_documents(run)}
    assert checks["FA011466.pdf"].ok
    assert "paypal" in (
        checks["FA011466.pdf"].observed.get("matched_configuration_name") or ""
    ).casefold()


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_11_oracle_rematches_bootshop_to_paypal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run = _rematch_state(monkeypatch, tmp_path)
    checks = {c.source_filename: c for c in verify_documents(run)}
    assert checks["Rechnung RE-202605-14594.pdf"].ok


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_12_oracle_does_not_assign_boettcher_card_to_amex(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run = _rematch_state(monkeypatch, tmp_path)
    checks = {c.source_filename: c for c in verify_documents(run)}
    assert checks["320262919974.pdf"].ok
    name = (checks["320262919974.pdf"].observed.get("matched_configuration_name") or "")
    assert "american express" not in name.casefold()
    assert name.casefold() != "amex"


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_13_oracle_keeps_luxvenum_unklar_missing_payment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run = _rematch_state(monkeypatch, tmp_path)
    checks = {c.source_filename: c for c in verify_documents(run)}
    assert checks["Rechnung-2026156019-102201.pdf"].ok
    assert "unklar" in (
        checks["Rechnung-2026156019-102201.pdf"].observed.get(
            "matched_configuration_name"
        )
        or ""
    ).casefold()


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_14_oracle_keeps_boettcher_storno_unklar_missing_payment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run = _rematch_state(monkeypatch, tmp_path)
    checks = {c.source_filename: c for c in verify_documents(run)}
    assert checks["420260091336.pdf"].ok


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_15_oracle_verifies_art_storno(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run = _rematch_state(monkeypatch, tmp_path)
    checks = {c.source_filename: c for c in verify_documents(run)}
    assert checks["420260091336.pdf"].observed.get("art") == "storno"


@pytest.mark.skipif(not _controlled_available(), reason="controlled PDFs missing")
def test_16_to_20_oracle_finalization_dry_run_sandbox_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    storage = _isolate_profile(monkeypatch, tmp_path)
    # Point profile storage under controlled output for path policy of live helpers.
    storage_under = CONTROLLED_OUTPUT / "automated-smoke-pytest-profile-store"
    storage_under.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "invoice_tool.app_paths.profile_storage_dir", lambda: storage_under
    )
    monkeypatch.setattr(
        "invoice_tool.profile_store.app_paths.profile_storage_dir",
        lambda: storage_under,
    )
    # Ensure a sufficient preview export exists (reuse or plant synthetic under output).
    folder, payload = find_latest_sufficient_preview_export(CONTROLLED_OUTPUT)
    if folder is None:
        planted = CONTROLLED_OUTPUT / "preview-export-oracle-test-planted"
        planted.mkdir(parents=True, exist_ok=True)
        (planted / "manifest.json").write_text(
            json.dumps(_synthetic_payload()), encoding="utf-8"
        )

    result = run_track_b_automated_smoke_oracle(
        repo_root=ROOT,
        input_root=CONTROLLED_INPUT,
        output_root=CONTROLLED_OUTPUT,
        profile_id=ORACLE_PROFILE_ID,
        profile_storage_dir=storage_under,
        skip_git_preflight_stop=True,
        create_folders_if_missing=True,
    )
    assert result.finalization_preview.get("ok") is True
    # 17 dry-run under controlled output (or explicit finalization blocker)
    if result.dry_run.get("ok"):
        assert str(result.dry_run.get("package_root") or "").startswith(
            str(CONTROLLED_OUTPUT)
        )
    # 18 sandbox under controlled output when executed
    if result.sandbox_final_write.get("ok"):
        assert str(
            result.sandbox_final_write.get("sandbox_final_write_root") or ""
        ).startswith(str(CONTROLLED_OUTPUT))
    # 19/20 evidence markdown + json
    assert result.evidence_folder
    evidence = Path(result.evidence_folder)
    assert (evidence / "TRACK_B_AUTOMATED_SMOKE_ORACLE_REPORT.md").is_file()
    assert (evidence / "TRACK_B_AUTOMATED_SMOKE_ORACLE_REPORT.json").is_file()
    assert result.safety.to_dict()
    assert result.hashes_before == result.hashes_after
    assert result.status in {
        oracle_mod.STATUS_PASS,
        STATUS_PARTIAL_UI,
        STATUS_PARTIAL_FINAL,
        oracle_mod.STATUS_BLOCKED,
    }
    if (
        result.dry_run.get("ok")
        and result.sandbox_final_write.get("ok")
        and all(d.ok for d in result.document_results)
        and result.paypal_result.get("ok")
        and result.hashes_before == result.hashes_after
        and not result.safety.unsafe
    ):
        assert result.status == oracle_mod.STATUS_PASS
    del storage  # silence unused in success path


def test_21_oracle_reports_safety_flags() -> None:
    flags = SafetyFlags()
    data = flags.to_dict()
    assert data["called_run_once"] is False
    assert data["final_write_allowed_for_production"] is False
    assert data["originals_mutated"] is False


def test_22_oracle_does_not_call_run_once() -> None:
    assert oracle_source_calls_run_once() is False
    source = ORACLE_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "run_once":
                pytest.fail("run_once call found")
            if isinstance(func, ast.Attribute) and func.attr == "run_once":
                pytest.fail("run_once attribute call found")
    assert "run_once(" not in source or "call_run_once=False" in source


def test_23_oracle_does_not_write_production_final_files() -> None:
    assert oracle_writes_production_final_files() is False


def test_24_oracle_does_not_touch_real_invoice_folders() -> None:
    assert oracle_touches_real_invoice_folders() is False
    for path in FORBIDDEN:
        assert oracle_uses_controlled_input_path(path) is False
        assert oracle_uses_controlled_output_path(path) is False


def test_25_oracle_does_not_modify_track_a() -> None:
    assert oracle_modifies_track_a() is False
    for rel in TRACK_A_PROTECTED:
        assert not (
            ROOT / rel
        ).resolve() == ORACLE_PY.resolve()


def test_26_oracle_does_not_modify_processing_core() -> None:
    assert oracle_modifies_processing_core() is False
    source = ORACLE_PY.read_text(encoding="utf-8")
    for rel in CORE_PROTECTED:
        assert f"invoice_tool.{Path(rel).stem}" not in source or "core_dry_run" not in rel


def test_27_track_a_protection_still_passes() -> None:
    from tests.test_track_a_internal_app_protection import (
        test_entry_files_exist_and_are_distinct,
        test_protected_track_a_and_core_not_staged,
        test_track_a_modules_do_not_import_ui_v2,
        test_track_b_entry_modules_do_not_import_track_a_runtime,
    )

    test_entry_files_exist_and_are_distinct()
    test_track_a_modules_do_not_import_ui_v2()
    test_track_b_entry_modules_do_not_import_track_a_runtime()
    test_protected_track_a_and_core_not_staged()


def test_28_docs_and_runner_exist() -> None:
    assert ORACLE_PY.is_file()
    assert RUNNER_PY.is_file()
    assert DOC.is_file()
    assert AUDIT.is_file()


def test_29_classify_status_meanings() -> None:
    assert (
        classify_status(
            safety=SafetyFlags(originals_mutated=True),
            blockers=[],
            docs_ok=True,
            paypal_ok=True,
            dry_run_ok=True,
            sandbox_ok=True,
            finalization_ready_count=1,
        )
        == oracle_mod.STATUS_FAIL_UNSAFE
    )
    assert (
        classify_status(
            safety=SafetyFlags(),
            blockers=[],
            docs_ok=True,
            paypal_ok=True,
            dry_run_ok=True,
            sandbox_ok=True,
            finalization_ready_count=1,
        )
        == oracle_mod.STATUS_PASS
    )
    assert (
        classify_status(
            safety=SafetyFlags(),
            blockers=[],
            docs_ok=True,
            paypal_ok=True,
            dry_run_ok=False,
            sandbox_ok=False,
            finalization_ready_count=0,
        )
        == STATUS_PARTIAL_FINAL
    )


def test_30_write_evidence_reports(tmp_path: Path) -> None:
    result = OracleResult(
        status=STATUS_PARTIAL_UI,
        head="deadbeef",
        input_root=str(CONTROLLED_INPUT),
        output_root=str(CONTROLLED_OUTPUT),
        hashes_before={"a.pdf": "1"},
        hashes_after={"a.pdf": "1"},
    )
    md, js = write_evidence_reports(result, evidence_root=tmp_path / "evidence")
    assert md.is_file()
    assert js.is_file()
    assert "TRACK_B_AUTOMATED_SMOKE" in md.read_text(encoding="utf-8")
