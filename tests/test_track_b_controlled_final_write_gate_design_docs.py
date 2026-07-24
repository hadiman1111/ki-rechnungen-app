"""Doc-gate for Track-B Controlled Final Write Gate Design (Prompt 32/34).

Docs/spec evidence only — no productive processing, no real invoice folders,
no final write execution, no Track-A/core runtime changes.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_CONTROLLED_FINAL_WRITE_GATE_DESIGN_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_CONTROLLED_FINAL_WRITE_GATE_DESIGN_2026-07-23.md"
)

PRODUCT_STATUS = "TRACK_B_CONTROLLED_FINAL_WRITE_GATE_DESIGN_READY"
NEXT_TASK = "KI_RECHNUNGEN_TRACK_B_CONTROLLED_FINAL_WRITE_SANDBOX_IMPLEMENTATION_01"

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


def test_docs_define_final_write_gate_model() -> None:
    text = _combined()
    assert "FinalWriteGate" in text
    for field in (
        "gate_id",
        "source_run_id",
        "preview_state_id",
        "dry_run_package_id",
        "batch_id",
        "created_at",
        "final_write_allowed",
        "productive_mode_requested",
        "gate_status",
        "closed",
        "open_for_future_authorized_write",
        "blocked",
        "required_preconditions",
        "blockers",
        "warnings",
        "user_authorization_required",
        "audit_required",
        "source_recheck_required",
        "target_recheck_required",
        "conflict_recheck_required",
        "stale_state_recheck_required",
        "final_write_execution_available",
    ):
        assert field in text, f"missing FinalWriteGate field: {field}"


def test_docs_define_final_write_authorization_model() -> None:
    text = _combined()
    assert "FinalWriteAuthorization" in text
    for field in (
        "authorization_id",
        "authorized_by_user",
        "authorization_timestamp",
        "authorization_scope",
        "selected_items",
        "whole_ready_batch",
        "selected_item_ids",
        "user_acknowledged",
        "final_write_will_copy_or_rename",
        "originals_policy",
        "conflicts_resolved",
        "source_hash_recheck",
        "target_path_recheck",
        "no_rollback_guarantee_without_backup",
        "dry_run_package_id",
        "finalization_preview_batch_id",
        "confirmation_phrase_required",
        "confirmation_phrase_entered",
        "authorization_valid",
        "authorization_blockers",
    ):
        assert field in text, f"missing FinalWriteAuthorization field: {field}"


def test_docs_define_final_write_plan_model() -> None:
    text = _combined()
    assert "FinalWritePlan" in text
    for field in (
        "item_id",
        "source_path",
        "source_sha256_at_preview",
        "source_sha256_at_write_check",
        "source_hash_match",
        "approved_final_filename",
        "final_target_path",
        "target_within_output_root",
        "target_exists",
        "duplicate_policy",
        "conflict_status",
        "operation_type",
        "copy_to_final_output",
        "rename_copy_to_final_output",
        "no_op",
        "original_file_policy",
        "leave_original_unchanged",
        "archive_after_success_later",
        "ready_for_write",
        "write_blockers",
        "audit_record_id",
    ):
        assert field in text, f"missing FinalWritePlan field: {field}"


def test_docs_define_mandatory_dry_run_package_precondition() -> None:
    text = _combined()
    assert "mandatory dry-run package precondition" in text
    assert "dry-run package exists" in text.lower() or "dry-run package exists" in text


def test_docs_define_user_authorization_precondition() -> None:
    text = _combined()
    assert "user authorization precondition" in text
    assert "FinalWriteAuthorization" in text
    assert "authorization_valid" in text


def test_docs_define_source_hash_recheck() -> None:
    text = _combined()
    assert "source hash" in text.lower()
    assert "source_sha256_at_write_check" in text
    assert "source_hash_match" in text
    assert "source_recheck_required" in text or "Source-Hash-Recheck" in text


def test_docs_define_target_path_recheck() -> None:
    text = _combined()
    assert "target path recheck" in text.lower() or "Target-Path-Recheck" in text
    assert "target_within_output_root" in text
    assert "target_recheck_required" in text or "target_recheck_result" in text


def test_docs_define_conflict_recheck() -> None:
    text = _combined()
    assert "conflict recheck" in text.lower() or "Conflict-Recheck" in text
    assert "conflict_recheck_required" in text or "conflict_recheck_result" in text


def test_docs_define_stale_preview_blocker() -> None:
    text = _combined()
    assert "stale preview" in text.lower() or "stale_preview_state" in text
    assert "stale preview blocker" in text.lower() or "stale_preview_state" in text


def test_docs_define_source_hash_changed_blocker() -> None:
    text = _combined()
    assert "source hash changed" in text or "source_hash_changed" in text


def test_docs_define_target_outside_output_root_blocker() -> None:
    text = _combined()
    assert (
        "target outside output root" in text
        or "target_outside_output_root" in text
    )


def test_docs_define_duplicate_target_blocker() -> None:
    text = _combined()
    assert (
        "duplicate target" in text.lower()
        or "duplicate_target_unresolved" in text
        or "duplicate target blocker" in text.lower()
    )


def test_docs_define_missing_final_write_authorization_blocker() -> None:
    text = _combined()
    assert (
        "missing final-write authorization" in text
        or "missing_final_write_authorization" in text
        or "missing explicit final-write authorization" in text
    )


def test_docs_define_real_invoice_folder_path_blocker() -> None:
    text = _combined()
    assert (
        "real invoice folder path" in text.lower()
        or "real_invoice_folder_path_detected" in text
    )


def test_docs_define_final_write_allowed_false_as_blocker_in_this_phase() -> None:
    text = _combined()
    assert "final_write_allowed=false" in text
    assert (
        "blocker in this phase" in text.lower()
        or "as blocker in this phase" in text.lower()
        or "final_write_allowed_false" in text
    )


def test_docs_define_ui_confirmation_design() -> None:
    text = _combined()
    assert "UI confirmation design" in text or "User-facing confirmation design" in text
    assert "Finales Schreiben vorbereiten" in text
    assert "Dies ist kein Trockenlauf mehr" in text
    assert "Finales Schreiben ausführen" in text
    assert "disabled state if any blocker exists" in text or "disabled" in text.lower()
    assert "design-only" in text.lower() or "not implemented as active final writer" in text


def test_docs_define_confirmation_phrase_option() -> None:
    text = _combined()
    assert "confirmation phrase" in text.lower()
    assert "confirmation_phrase_required" in text
    assert "confirmation phrase option" in text.lower()


def test_docs_define_pre_write_audit_fields() -> None:
    text = _combined()
    for field in (
        "final_write_gate_id",
        "dry_run_package_id",
        "batch_id",
        "selected_item_ids",
        "authorization_id",
        "preflight_timestamp",
        "source_hash_recheck_result",
        "target_recheck_result",
        "conflict_recheck_result",
        "final_write_allowed_at_preflight",
        "execution_available=false",
    ):
        assert field in text, f"missing pre-write audit field: {field}"


def test_docs_define_post_write_audit_fields_for_later_task() -> None:
    text = _combined()
    assert "Post-write audit fields" in text or "post-write audit fields" in text.lower()
    assert "for later task" in text.lower() or "for later task" in text
    for field in (
        "execution_started_at",
        "execution_finished_at",
        "file_results",
        "final_files_written",
        "originals_moved",
        "originals_renamed",
        "originals_archived",
        "originals_deleted",
        "failures",
        "rollback_or_abort_notes",
    ):
        assert field in text, f"missing post-write audit field: {field}"


def test_docs_state_final_write_execution_available_false_in_this_phase() -> None:
    text = _combined()
    assert "final_write_execution_available=false" in text
    assert "in this phase" in text or "in dieser Phase" in text


def test_docs_state_no_final_files_written() -> None:
    text = _combined()
    assert "no final files written" in text.lower() or "No final files written" in text


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
    # Must not claim positive SaaS-ready without negation nearby.
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
    assert "Prompt 32/34" in text
    assert "Remaining prompts:** 2" in text or "Remaining prompts: 2" in text


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

    text = _read(DOC)
    assert "No runtime/code changes" in text or "reines Design/Spec" in text
    assert "final write" in text.lower()
    assert "Out-of-scope" in text or "Out of scope" in text
