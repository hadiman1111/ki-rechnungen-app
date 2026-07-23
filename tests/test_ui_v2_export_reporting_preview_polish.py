"""Track-B Export-/Reporting-Vorschau Polish (Prompt 5/34)."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from invoice_tool.ui_v2.core_dry_run_contract import (
    CoreDryRunDocumentResult,
    CoreDryRunErrorItem,
    CoreDryRunPlannedDestination,
    CoreDryRunResult,
    CoreDryRunReviewItem,
    CoreDryRunStatus,
    CoreDryRunSummary,
    empty_safety_proof,
)
from invoice_tool.ui_v2.export_reporting import (
    MSG_ALL_REVIEW_HEAVY,
    MSG_EMPTY_RUN_STATE,
    MSG_EXPORT_EMPTY,
    MSG_LOCAL_PILOT_NOT_READY,
    MSG_NO_FINAL_FILES_WRITTEN,
    MSG_NO_SANDBOX_RUN,
    MSG_ORIGINALS_UNCHANGED,
    MSG_PRODUCTIVE_PROCESSING_BLOCKED,
    MSG_SAAS_NOT_READY,
    MSG_TARGET_PATHS_VORSCHAU_ONLY,
    MSG_VORSCHAU_NOT_PRODUCTIVE_RUN,
    REPORT_TITLE,
    ExportPreviewContext,
    build_export_preview_report,
    build_run_export_payload,
    build_run_report_view_model,
    export_processing_run_state,
    render_export_preview_text,
    report_contains_forbidden_claims,
    write_run_report_export,
)
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.pages.workspace import (
    apply_workspace_export_preview,
    build_workspace_export_preview_text,
    build_workspace_run_report_vm,
)
from invoice_tool.ui_v2.processing_state import (
    MSG_SAFETY_PROOF_COMPACT,
    ProcessingErrorItem,
    ProcessingPlannedDestination,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.result_mapping import (
    map_core_dry_run_result_to_processing_run_state,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
EXPORT_MODULE = ROOT / "invoice_tool" / "ui_v2" / "export_reporting.py"
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.run",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
    "invoice_tool.core_dry_run",
)


def _digest_tree(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _dry(
    *,
    status: CoreDryRunStatus = CoreDryRunStatus.COMPLETED,
    recognized=(),
    review=(),
    errors=(),
    planned=(),
    warnings=(),
    message: str | None = None,
    run_id: str = "preview-run-1",
) -> CoreDryRunResult:
    summary = CoreDryRunSummary(
        total_documents=len(recognized) + len(review) + len(errors),
        recognized_count=len(recognized),
        review_count=len(review),
        error_count=len(errors),
        planned_destination_count=len(planned),
    )
    return CoreDryRunResult(
        status=status,
        run_id=run_id,
        recognized=tuple(recognized),
        review=tuple(review),
        errors=tuple(errors),
        planned_destinations=tuple(planned),
        summary=summary,
        warnings=tuple(warnings),
        safety_proof=empty_safety_proof(evidence_notes=("no_source_mutation",)),
        message=message or "Core-Dry-Run abgeschlossen ohne Source-Mutation.",
    )


def _mixed_state() -> ProcessingRunState:
    dry = _dry(
        status=CoreDryRunStatus.COMPLETED_WITH_REVIEW,
        recognized=(
            CoreDryRunDocumentResult(
                document_name="invoice.txt",
                document_type="invoice",
                classification_status="recognized",
                status_label="erkannt",
                target_hint="geplant/erkannt",
            ),
        ),
        review=(
            CoreDryRunReviewItem(
                document_name="scan.pdf",
                reason="OCR/AI nicht ausgeführt",
                status_label="unklar",
            ),
        ),
        errors=(
            CoreDryRunErrorItem(
                document_name="bad.bin",
                error_code="unsupported_file_type",
                message="Nicht unterstützt",
            ),
        ),
        planned=(
            CoreDryRunPlannedDestination(
                document_name="invoice.txt",
                planned_path="/sandbox/out/geplant/erkannt/invoice.txt",
                destination_label="erkannt",
                applied=False,
            ),
            CoreDryRunPlannedDestination(
                document_name="scan.pdf",
                planned_path="/sandbox/out/geplant/unklar/scan.pdf",
                destination_label="unklar",
                applied=False,
            ),
        ),
        warnings=("ocr_not_run",),
    )
    return map_core_dry_run_result_to_processing_run_state(dry)


def test_preview_report_uses_real_processing_run_state() -> None:
    state = _mixed_state()
    ctx = ExportPreviewContext(
        sandbox_input_path="/sandbox/in",
        sandbox_output_path="/sandbox/out",
        profile_display="Profil A",
        config_display="Konfig B",
    )
    report = build_export_preview_report(state, ctx)
    assert report.title == REPORT_TITLE
    assert report.run_id == "preview-run-1"
    assert report.sandbox_input_path == "/sandbox/in"
    assert report.sandbox_output_path == "/sandbox/out"
    assert "Profil A" in (report.profile_display or "")
    assert report.recognized_count == 1
    assert report.review_count == 1
    assert report.error_count == 1
    assert report.warning_count == 1
    assert report.planned_destination_count == 2
    assert report.safety_proof
    assert report.preview_only is True
    assert report.starts_processing is False
    assert report.mutates_original_files is False


def test_no_run_shows_no_fake_report() -> None:
    report = build_run_report_view_model(ProcessingRunState())
    assert report.no_run is True
    assert report.export_available is False
    assert report.recognized == ()
    assert report.unclear == ()
    assert report.failed == ()
    assert report.user_summary.headline == MSG_NO_SANDBOX_RUN
    text = render_export_preview_text(report)
    assert MSG_NO_SANDBOX_RUN in text
    assert "invoice.pdf" not in text
    assert report.claims_final_files_written is False


def test_successful_mixed_dry_run_shows_counts() -> None:
    report = build_export_preview_report(_mixed_state())
    assert report.outcome_kind == "mixed"
    assert report.recognized_count == 1
    assert report.review_count == 1
    assert report.error_count == 1
    assert report.planned_destination_count == 2
    text = render_export_preview_text(report)
    assert "Erkannt: 1" in text
    assert "Zur Prüfung: 1" in text
    assert "Fehler: 1" in text


def test_all_review_dry_run_shows_review_heavy_status() -> None:
    dry = _dry(
        status=CoreDryRunStatus.COMPLETED_WITH_REVIEW,
        review=(
            CoreDryRunReviewItem(
                document_name="a.pdf",
                reason="unklar",
                status_label="unklar",
            ),
            CoreDryRunReviewItem(
                document_name="b.pdf",
                reason="unklar",
                status_label="unklar",
            ),
        ),
    )
    state = map_core_dry_run_result_to_processing_run_state(dry)
    report = build_export_preview_report(state)
    assert report.outcome_kind == "all_review"
    assert report.review_count == 2
    assert report.recognized_count == 0
    assert MSG_ALL_REVIEW_HEAVY in report.user_summary.headline
    assert report.status_label == "Mit Prüffällen"


def test_failed_dry_run_shows_failure_blocker_text() -> None:
    dry = _dry(
        status=CoreDryRunStatus.FAILED,
        errors=(
            CoreDryRunErrorItem(
                document_name="x.bin",
                error_code="unsupported_file_type",
                message="fail",
            ),
        ),
        message="Dry-Run fehlgeschlagen: Blocker.",
    )
    state = map_core_dry_run_result_to_processing_run_state(dry)
    report = build_export_preview_report(state)
    assert report.status == "failed"
    assert report.export_available is True
    assert any("fail" in item.message.lower() or "blocker" in item.message.lower()
               or "fehl" in item.message.lower() for item in report.failed)
    text = render_export_preview_text(report)
    assert "fehl" in text.lower() or "fail" in text.lower() or "Blocker" in text
    assert report.claims_final_files_written is False


def test_empty_run_shows_honest_empty_state() -> None:
    dry = _dry(status=CoreDryRunStatus.COMPLETED, message="Leerer Sandbox-Eingang.")
    state = map_core_dry_run_result_to_processing_run_state(dry)
    report = build_export_preview_report(state)
    assert report.outcome_kind == "empty"
    assert report.recognized_count == 0
    assert report.review_count == 0
    assert MSG_EMPTY_RUN_STATE in report.user_summary.headline
    assert report.claims_final_files_written is False


def test_planned_destinations_labelled_preview_only() -> None:
    report = build_export_preview_report(_mixed_state())
    assert report.destinations
    assert all(item.planned_only for item in report.destinations)
    assert all(MSG_TARGET_PATHS_VORSCHAU_ONLY in item.preview_only_label for item in report.destinations)
    text = render_export_preview_text(report)
    assert MSG_TARGET_PATHS_VORSCHAU_ONLY in text
    payload = build_run_export_payload(report)
    assert payload["questions"]["destinations"]["preview_only"] is True
    assert payload["questions"]["destinations"]["planned_only"] is True


def test_report_includes_safety_proof() -> None:
    report = build_export_preview_report(_mixed_state())
    assert report.safety_proof == MSG_SAFETY_PROOF_COMPACT or "Originale" in report.safety_proof
    text = render_export_preview_text(report)
    assert "Sicherheitsnachweis" in text
    assert MSG_ORIGINALS_UNCHANGED in text or "Originale" in report.safety_proof


def test_report_says_originals_unchanged() -> None:
    report = build_export_preview_report(_mixed_state())
    text = render_export_preview_text(report)
    assert MSG_ORIGINALS_UNCHANGED in text
    assert MSG_ORIGINALS_UNCHANGED in report.honest_copy


def test_report_says_productive_processing_blocked() -> None:
    report = build_export_preview_report(_mixed_state())
    text = render_export_preview_text(report)
    assert MSG_PRODUCTIVE_PROCESSING_BLOCKED in text
    assert MSG_PRODUCTIVE_PROCESSING_BLOCKED in report.honest_copy


def test_report_does_not_claim_final_files_written() -> None:
    report = build_export_preview_report(_mixed_state())
    text = render_export_preview_text(report)
    assert MSG_NO_FINAL_FILES_WRITTEN in text
    assert report.claims_final_files_written is False
    assert "final geschrieben" not in text.lower().replace("keine dateien wurden final geschrieben", "")


def test_report_does_not_claim_local_pilot_ready() -> None:
    report = build_export_preview_report(_mixed_state())
    text = render_export_preview_text(report).lower()
    assert MSG_LOCAL_PILOT_NOT_READY.lower() in text
    assert report.claims_local_pilot_ready is False
    assert "local_pilot_ready" not in text.replace("local-pilot-ready ist nicht erreicht", "")


def test_report_does_not_claim_saas_ready() -> None:
    report = build_export_preview_report(_mixed_state())
    text = render_export_preview_text(report).lower()
    assert MSG_SAAS_NOT_READY.lower() in text
    assert report.claims_saas_ready is False
    assert report_contains_forbidden_claims(report) is False


def test_export_reporting_does_not_call_run_once(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"run_once": 0}

    def boom(*_a, **_k):
        called["run_once"] += 1
        raise AssertionError("run_once must not be called")

    monkeypatch.setattr("invoice_tool.run.run_once", boom, raising=False)
    report = build_export_preview_report(_mixed_state())
    _ = render_export_preview_text(report)
    _ = build_run_export_payload(report)
    assert called["run_once"] == 0
    src = EXPORT_MODULE.read_text(encoding="utf-8")
    assert "run_once" not in src
    assert "invoice_tool.run" not in src


def test_export_reporting_does_not_mutate_original_files(tmp_path: Path) -> None:
    originals = tmp_path / "originals"
    originals.mkdir()
    sample = originals / "beleg.pdf"
    sample.write_bytes(b"%PDF-1.4 original")
    before = _digest_tree(originals)
    report = build_export_preview_report(_mixed_state())
    export_dir = tmp_path / "export_only"
    result = write_run_report_export(report, export_dir)
    assert result.ok is True
    assert _digest_tree(originals) == before
    assert sample.read_bytes() == b"%PDF-1.4 original"


def test_export_reporting_does_not_write_outside_tmp_path(tmp_path: Path) -> None:
    report = build_export_preview_report(_mixed_state())
    target = tmp_path / "nested" / "vorschau.json"
    result = export_processing_run_state(
        _mixed_state(),
        target,
        context=ExportPreviewContext(
            sandbox_input_path=str(tmp_path / "in"),
            sandbox_output_path=str(tmp_path / "out"),
        ),
    )
    assert result.ok is True
    assert target.is_file()
    for written in result.written_files:
        assert str(written).startswith(str(tmp_path))


def test_workspace_export_uses_same_dry_run_state(tmp_path: Path) -> None:
    state = UiV2State(processing_run_state=_mixed_state())
    state.workspace_input_folder_override = str(tmp_path / "sandbox-in")
    state.workspace_output_folder_override = str(tmp_path / "sandbox-out")
    report = build_workspace_run_report_vm(state)
    assert report.run_id == "preview-run-1"
    assert report.sandbox_input_path == str(tmp_path / "sandbox-in")
    assert report.sandbox_output_path == str(tmp_path / "sandbox-out")
    text = build_workspace_export_preview_text(state)
    assert REPORT_TITLE in text
    assert MSG_NO_FINAL_FILES_WRITTEN in text
    out = tmp_path / "ws-export.json"
    result = apply_workspace_export_preview(state, str(out))
    assert result is not None and result.ok is True
    assert out.is_file()


def test_review_shows_export_preview_summary_without_final_action() -> None:
    ui = UiV2State(processing_run_state=_mixed_state())
    page = build_review_page_vm(ui)
    assert page.export_preview_only is True
    assert page.final_actions_blocked is True
    assert page.actions_disabled is True
    assert page.productive_actions_exposed is False
    assert page.export_preview_summary
    assert REPORT_TITLE in page.export_preview_summary or "Export-Vorschau" in page.export_preview_summary
    assert MSG_NO_FINAL_FILES_WRITTEN in page.export_preview_summary
    idle = build_review_page_vm(UiV2State())
    assert idle.export_preview_summary == MSG_NO_SANDBOX_RUN


def test_failed_run_without_rows_surfaces_blocker() -> None:
    state = ProcessingRunState(
        status="failed",
        run_id="fail-1",
        message="Sandbox-Gate blockiert: Ordner fehlt.",
        outcome_kind="failed",
        safety_proof_summary=MSG_SAFETY_PROOF_COMPACT,
    )
    report = build_export_preview_report(state)
    assert report.no_run is False
    assert report.export_available is True
    assert report.failed
    assert "blockiert" in report.error_summary.lower() or "fehlt" in report.error_summary.lower()


def test_preview_text_includes_required_polish_wording() -> None:
    text = render_export_preview_text(build_export_preview_report(_mixed_state()))
    for required in (
        REPORT_TITLE,
        MSG_NO_FINAL_FILES_WRITTEN,
        MSG_ORIGINALS_UNCHANGED,
        MSG_PRODUCTIVE_PROCESSING_BLOCKED,
        MSG_TARGET_PATHS_VORSCHAU_ONLY,
        MSG_VORSCHAU_NOT_PRODUCTIVE_RUN,
        MSG_LOCAL_PILOT_NOT_READY,
        MSG_SAAS_NOT_READY,
    ):
        assert required in text


def test_export_empty_blocks_file_write_for_no_run(tmp_path: Path) -> None:
    result = write_run_report_export(
        build_run_report_view_model(None),
        tmp_path / "should-not-exist.json",
    )
    assert result.ok is False
    assert result.error == MSG_EXPORT_EMPTY
    assert not (tmp_path / "should-not-exist.json").exists()


def test_modules_do_not_import_processing_core() -> None:
    for path in (EXPORT_MODULE, WORKSPACE, REVIEW):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        for core in FORBIDDEN_CORE:
            assert core not in imported


def test_structured_planned_and_errors_from_processing_state() -> None:
    state = ProcessingRunState(
        status="completed",
        run_id="struct-1",
        outcome_kind="mixed",
        results=(
            ProcessingResultSummary(
                document_name="ok.pdf",
                document_type="rechnung",
                classification_status="ok",
                status_label="OK",
            ),
        ),
        review_items=(
            ProcessingReviewItem(
                document_name="rev.pdf",
                reason="unklar",
                status_label="unklar",
            ),
        ),
        error_items=(
            ProcessingErrorItem(
                document_name="err.pdf",
                error_code="E1",
                message="kaputt",
            ),
        ),
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="ok.pdf",
                planned_path="/sandbox/out/ok.pdf",
                destination_label="geplant",
                preview_only=True,
                applied=False,
            ),
        ),
        planned_destination_count=1,
        warnings=("hint",),
        safety_proof_summary=MSG_SAFETY_PROOF_COMPACT,
    )
    report = build_export_preview_report(state)
    assert report.recognized_count == 1
    assert report.review_count == 1
    assert report.error_count == 1
    assert report.planned_destination_count == 1
    assert report.destinations[0].destination_hint == "/sandbox/out/ok.pdf"
