"""Doc-gate for Track-B Review Decision to Finalization Design (Prompt 28/34).

Docs/spec evidence only — no productive processing, no real invoice folders,
no final write, no Track-A/core runtime changes.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_REVIEW_DECISION_TO_FINALIZATION_DESIGN_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_REVIEW_DECISION_TO_FINALIZATION_DESIGN_2026-07-23.md"
)

PRODUCT_STATUS = "TRACK_B_REVIEW_DECISION_TO_FINALIZATION_DESIGN_READY"
NEXT_TASK = "KI_RECHNUNGEN_TRACK_B_REVIEW_DECISION_STATE_AND_UI_FLOW_01"

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
    return _read(DOC) + "\n" + _read(AUDIT)


def test_docs_exist() -> None:
    assert DOC.is_file()
    assert AUDIT.is_file()


def test_docs_define_review_decision_model() -> None:
    text = _combined()
    assert "ReviewDecision" in text
    for field in (
        "decision_id",
        "source_item_id",
        "source_filename",
        "decision_type",
        "decided_by_user",
        "decision_timestamp",
        "approved_preview_filename",
        "approved_target_preview_path",
        "edited_fields",
        "finalization_ready",
        "finalization_blockers",
        "audit_note",
    ):
        assert field in text, f"missing ReviewDecision field: {field}"


def test_docs_define_finalization_readiness_model() -> None:
    text = _combined()
    assert "FinalizationReadiness" in text
    for field in (
        "item_id",
        "ready",
        "approved",
        "required_fields_present",
        "configuration_resolved",
        "filename_complete",
        "output_root_safe",
        "target_conflict_status",
        "source_unchanged_since_preview",
        "preview_state_fresh",
        "blockers",
        "warnings",
        "next_action",
    ):
        assert field in text, f"missing FinalizationReadiness field: {field}"


def test_docs_define_accept_suggestion_behavior() -> None:
    text = _combined()
    assert "accept_suggestion" in text
    assert "Vorschlag akzeptieren" in text
    assert "required fields present" in text
    assert "explizit" in text.lower() or "explicit" in text.lower()


def test_docs_define_edit_suggestion_behavior() -> None:
    text = _combined()
    assert "edit_suggestion" in text
    assert "Vorschlag bearbeiten" in text
    assert "edited filename must be validated" in text.lower() or (
        "Edited filename must be validated" in text
    )
    assert "edited_fields" in text


def test_docs_define_keep_review_required_behavior() -> None:
    text = _combined()
    assert "keep_review_required" in text
    assert "als Unklar belassen" in text
    assert "Keine Finalization" in text or "no finalization" in text.lower()


def test_docs_define_ignore_for_export_behavior() -> None:
    text = _combined()
    assert "ignore_for_export" in text
    assert "ignorieren / nicht exportieren" in text
    assert "No file operation" in text or "no file operation" in text.lower()


def test_docs_define_defer_behavior() -> None:
    text = _combined()
    assert "defer" in text
    assert "zurückstellen" in text
    assert "pending" in text.lower()


def test_docs_define_needs_configuration_change_behavior() -> None:
    text = _combined()
    assert "needs_configuration_change" in text
    assert "Konfiguration anpassen und neu prüfen" in text
    assert "configuration rule" in text.lower() or "configuration rule flow" in text


def test_docs_list_missing_field_blockers() -> None:
    text = _combined()
    assert "missing payment_field" in text or "missing_payment_field" in text
    assert "missing supplier" in text or "missing_supplier" in text
    assert "missing amount" in text or "missing_amount" in text
    assert "missing date" in text or "missing_date" in text


def test_docs_list_duplicate_target_blocker() -> None:
    text = _combined()
    assert "duplicate target filename" in text or "duplicate_target_filename" in text


def test_docs_list_unsafe_target_path_blocker() -> None:
    text = _combined()
    assert (
        "unsafe target path" in text
        or "target outside output root" in text
        or "target_outside_output_root" in text
        or "output root unsafe" in text
    )


def test_docs_list_stale_state_blocker() -> None:
    text = _combined()
    assert "stale state" in text or "stale_preview_state" in text


def test_docs_list_source_hash_changed_blocker() -> None:
    text = _combined()
    assert "source hash changed" in text or "source_hash_changed" in text


def test_docs_list_no_explicit_approval_blocker() -> None:
    text = _combined()
    assert (
        "no explicit approval" in text
        or "no explicit user approval" in text
        or "no_explicit_user_approval" in text
    )


def test_docs_define_ui_decision_elements() -> None:
    text = _combined()
    assert "decision buttons" in text
    assert "Vorschau-Dateiname" in text
    assert "editable proposed filename" in text or "editable proposed filename field" in text
    assert "target preview path" in text
    assert "warnings/blockers panel" in text or "blockers panel" in text
    assert "finalization-ready" in text
    assert "not final yet" in text or "noch keine finale" in text


def test_docs_define_manifest_audit_fields() -> None:
    text = _combined()
    for field in (
        "review_decision",
        "decision_timestamp",
        "approved_by_user",
        "finalization_ready",
        "finalization_blockers",
        "approved_preview_filename",
        "target_preview_path",
        "user_edited_fields",
        "warnings_acknowledged",
        "source_hash_at_decision",
        "preview_state_id",
    ):
        assert field in text, f"missing manifest/audit field: {field}"


def test_docs_define_safety_gates_before_final_write() -> None:
    text = _combined()
    assert "explicit approval exists" in text
    assert "finalization_ready=true" in text or "`finalization_ready=true`" in text
    assert "no blockers" in text
    assert "source hash unchanged" in text
    assert "target path safe" in text
    assert "duplicate policy resolved" in text
    assert "preview state fresh" in text
    assert "finalization mode explicitly enabled" in text
    assert "productive write path still separately gated" in text
    assert "audit record written" in text


def test_docs_state_final_write_allowed_false_in_this_phase() -> None:
    text = _combined()
    assert "final_write_allowed=false" in text
    assert "in this phase" in text or "in dieser Phase" in text


def test_docs_state_no_productive_processing() -> None:
    text = _combined()
    assert "keine produktive Verarbeitung" in text
    assert "No productive processing" in text or "no productive processing" in text


def test_docs_state_no_real_invoice_folders() -> None:
    text = _combined()
    assert "keine realen Rechnungsordner" in text
    assert "No real invoice folders" in text or "no real invoice folders" in text


def test_docs_do_not_claim_saas_ready() -> None:
    text = _combined().lower()
    assert "nicht saas-ready" in text or "not saas-ready" in text
    assert "saas-ready." not in text.replace("nicht saas-ready", "").replace(
        "not saas-ready", ""
    )


def test_docs_do_not_claim_production_ready() -> None:
    text = _combined().lower()
    assert "nicht production-ready" in text or "not production-ready" in text


def test_docs_record_product_status_and_next_task() -> None:
    text = _combined()
    assert PRODUCT_STATUS in text
    assert NEXT_TASK in text
    assert "Prompt 28/34" in text
    assert "Remaining prompts:** 6" in text or "Remaining prompts: 6" in text


def test_track_a_protection_still_passes_for_this_task_files() -> None:
    """This task may only add docs/tests — protected Track A/core must stay unstaged."""

    import subprocess

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

    # Allowed task files exist; runtime modules for decisions are not claimed implemented.
    text = _read(DOC)
    assert "No runtime/code changes" in text or "reines Design/Spec" in text
    assert "final write" in text.lower()
    assert "Out-of-scope" in text or "Out of scope" in text
