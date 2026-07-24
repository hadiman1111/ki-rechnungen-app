"""Doc-gate for Track-B SaaS Readiness Final Audit and Manual Smoke (Prompt 34/34).

Docs/audit/checklist evidence only — no productive processing, no real invoice
folders, no production final-write, no Track-A/core runtime changes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_SAAS_READINESS_FINAL_AUDIT_AND_MANUAL_SMOKE_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_SAAS_READINESS_FINAL_AUDIT_AND_MANUAL_SMOKE_2026-07-23.md"
)
SMOKE = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_MANUAL_SMOKE_CHECKLIST_2026-07-23.md"
)
CHAIN = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_FINAL_CHAIN_INDEX_2026-07-23.md"
)

PRODUCT_STATUS = (
    "TRACK_B_INTERNAL_PILOT_READY_WITH_MANUAL_SMOKE_PENDING_NOT_SAAS_READY"
)
SAAS_READY_VERIFIED = "TRACK_B_SAAS_READY_VERIFIED"

TRACK_A_PROTECTED = (
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


def _read(path: Path) -> str:
    assert path.is_file(), f"missing doc: {path}"
    return path.read_text(encoding="utf-8")


def _combined() -> str:
    return "\n".join(_read(p) for p in (DOC, AUDIT, SMOKE, CHAIN))


def test_final_audit_docs_exist() -> None:
    assert DOC.is_file()
    assert AUDIT.is_file()


def test_manual_smoke_checklist_exists() -> None:
    assert SMOKE.is_file()


def test_audit_docs_define_capability_matrix() -> None:
    text = _combined()
    assert "Capability matrix" in text or "## Capability matrix" in text
    assert "| Capability | Status | Evidence | Limitation | Next action |" in text


def test_audit_docs_define_safety_matrix() -> None:
    text = _combined()
    assert "Safety matrix" in text or "## Safety matrix" in text
    assert "| Safety property | Status | Evidence | Remaining risk |" in text


def test_audit_docs_mention_controlled_sandbox_final_write() -> None:
    text = _combined().lower()
    assert "controlled sandbox final write" in text or "controlled sandbox final-write" in text
    assert "sandbox-final-write" in text


def test_audit_docs_mention_final_write_allowed_for_production_false() -> None:
    text = _combined()
    assert "final_write_allowed_for_production=false" in text


def test_audit_docs_mention_no_real_invoice_folders() -> None:
    text = _combined()
    assert "keine realen Rechnungsordner" in text
    assert "no real invoice folders" in text.lower() or "No real invoice folders" in text


def test_audit_docs_mention_no_productive_processing() -> None:
    text = _combined()
    assert "keine produktive Verarbeitung" in text
    assert "No productive processing" in text or "no productive processing" in text


def test_audit_docs_mention_track_a_protection() -> None:
    text = _combined()
    assert "Track A" in text
    assert "Track A protection" in text or "Track A protected" in text or "Track A/Core" in text


def test_audit_docs_mention_not_saas_ready_unless_verified() -> None:
    text = _combined()
    assert "Not SaaS-ready unless genuinely verified" in text or "nicht SaaS-ready" in text
    assert "unless" in text.lower() or "objektiv verifiziert" in text


def test_audit_docs_list_saas_auth_gap_if_not_implemented() -> None:
    text = _combined()
    assert "SaaS auth" in text or "SaaS auth gap" in text
    assert "authentication" in text.lower() or "Auth" in text


def test_audit_docs_list_tenant_isolation_gap_if_not_implemented() -> None:
    text = _combined()
    assert "tenant isolation" in text.lower() or "Tenant isolation gap" in text


def test_audit_docs_list_billing_plans_gap_if_not_implemented() -> None:
    text = _combined()
    assert "billing/plans" in text.lower() or "Billing/plans gap" in text or "billing" in text.lower()


def test_audit_docs_list_cloud_storage_deployment_gap_if_not_implemented() -> None:
    text = _combined()
    assert (
        "cloud storage" in text.lower()
        or "cloud storage/deployment gap" in text.lower()
        or "deployment storage" in text.lower()
    )


def test_manual_smoke_checklist_includes_ui_start_command() -> None:
    text = _read(SMOKE)
    assert ".venv-flet085/bin/python app_ui_v2.py" in text


def test_manual_smoke_checklist_includes_controlled_input_path() -> None:
    text = _read(SMOKE)
    assert "/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input" in text


def test_manual_smoke_checklist_includes_controlled_output_path() -> None:
    text = _read(SMOKE)
    assert "/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output" in text


def test_manual_smoke_checklist_includes_lumitop_476() -> None:
    text = _read(SMOKE)
    assert "LUMITOP" in text
    assert "476,00" in text


def test_manual_smoke_checklist_includes_1a_bootshop_105_75() -> None:
    text = _read(SMOKE)
    assert "1A-Bootshop" in text
    assert "105,75" in text


def test_manual_smoke_checklist_includes_boettcher_generic_card_not_amex() -> None:
    text = _read(SMOKE)
    assert "Böttcher" in text or "Boettcher" in text
    assert "generic card" in text.lower()
    assert "not AMEX" in text or "nicht AMEX" in text or "**nicht** AMEX" in text


def test_manual_smoke_checklist_includes_paypal_rule_rerun() -> None:
    text = _read(SMOKE)
    assert "PayPal" in text
    assert "Rerun preview" in text or "rerun" in text.lower()


def test_manual_smoke_checklist_includes_sandbox_final_write_folder_check() -> None:
    text = _read(SMOKE)
    assert "sandbox-final-write" in text


def test_manual_smoke_checklist_includes_originals_unchanged_check() -> None:
    text = _read(SMOKE)
    assert "original" in text.lower()
    assert "unchanged" in text.lower() or "unverändert" in text


def test_docs_do_not_claim_saas_ready_unless_status_verified() -> None:
    text = _combined()
    assert PRODUCT_STATUS in text
    assert "NOT_SAAS_READY" in text
    assert "nicht SaaS-ready" in text
    # May mention the verified status only as an unused / rejected classification.
    if SAAS_READY_VERIFIED in text:
        assert "Not used" in text or "not used" in text or "**not**" in text
        assert PRODUCT_STATUS in text
        assert SAAS_READY_VERIFIED != PRODUCT_STATUS
    # Must never set the product status to verified SaaS-ready.
    assert f"Product status (after this task):** `{SAAS_READY_VERIFIED}`" not in text
    assert f"Product status after task:** `{SAAS_READY_VERIFIED}`" not in text


def test_docs_do_not_claim_production_ready() -> None:
    text = _combined().lower()
    assert "nicht production-ready" in text or "not production-ready" in text
    assert (
        "nicht production final-write-ready" in text
        or "not production final-write-ready" in text
    )
    # Avoid bare positive production-ready claim without negation context.
    stripped = (
        text.replace("nicht production-ready", "")
        .replace("not production-ready", "")
        .replace("nicht production final-write-ready", "")
        .replace("not production final-write-ready", "")
    )
    assert "production-ready." not in stripped


def test_track_a_protection_still_passes() -> None:
    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    forbidden = {
        p.relative_to(ROOT).as_posix() for p in TRACK_A_PROTECTED + PROCESSING_CORE
    }
    overlap = sorted(set(staged) & forbidden)
    assert overlap == [], f"protected files staged: {overlap}"

    text = _read(DOC)
    assert "Track A" in text
    assert PRODUCT_STATUS in text
    assert "Prompt 34/34" in text
    assert "Remaining prompts:** 0" in text or "Remaining prompts: 0" in text
