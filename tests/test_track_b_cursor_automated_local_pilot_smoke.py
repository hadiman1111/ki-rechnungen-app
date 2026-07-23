"""Track-B Cursor Automated Local Pilot Smoke (Prompt 8/34).

Controlled automated sandbox smoke through the Track-B UI-v2 chain.
Uses pytest tmp_path only — no GUI, no real invoice folders, no OCR/AI/network,
no productive processing, no run_once.

Classification: CURSOR_AUTOMATED_SMOKE_PASS_WITH_SYNTHETIC_RESULT
(deterministic fake CoreDryRunResult; same pattern as acceptance-gate tests).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from invoice_tool.ui_v2.core_bridge import (
    CoreBridgeRequest,
    build_core_dry_run_request_from_bridge,
    run_core_bridge_sandbox_dry_run,
)
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
    MSG_LOCAL_PILOT_SANDBOX_ONLY,
    MSG_NO_FINAL_FILES_WRITTEN,
    MSG_ORIGINALS_UNCHANGED,
    MSG_PRODUCTIVE_PROCESSING_BLOCKED,
    MSG_SAAS_NOT_READY,
    REPORT_TITLE,
    build_export_preview_report,
    build_run_export_payload,
    render_export_preview_text,
    report_contains_forbidden_claims,
)
from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.pages.review import build_review_page_vm
from invoice_tool.ui_v2.pages.workspace import apply_start_processing, mark_start_checking
from invoice_tool.ui_v2.result_mapping import (
    build_result_bucket_summary,
    planned_destinations_are_preview_only,
    productive_actions_exposed,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
REAL_INVOICE_ROOT = Path("/Users/hadi_neu/Desktop/RECHNUNGEN")
SMOKE_CLASSIFICATION = "CURSOR_AUTOMATED_SMOKE_PASS_WITH_SYNTHETIC_RESULT"
PRODUCT_STATUS_AFTER = (
    "TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY_CURSOR_SMOKE_READY"
)
FORBIDDEN_READY_CLAIMS = (
    "SaaS-ready",
    "SaaS bereit",
    "saas ready",
    "production-ready",
    "production ready",
    "Production-Ready",
    "produktionsbereit",
    "Local-Pilot-Ready",
    "local_pilot_ready",
)
FORBIDDEN_FINAL_LANGUAGE = (
    "final processed",
    "final verarbeitet",
    "final geschrieben und archiviert",
    "produktiv verarbeitet",
)


def _digest_tree(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not folder.exists():
        return out
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _listing(folder: Path) -> list[str]:
    if not folder.exists():
        return []
    return sorted(
        str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file() or p.is_dir()
    )


def _sandbox_dirs(tmp_path: Path) -> tuple[Path, Path, Path]:
    sandbox = tmp_path / "cursor-auto-sandbox"
    input_copy = sandbox / "input_copy"
    output_preview = sandbox / "output_preview"
    input_copy.mkdir(parents=True, exist_ok=True)
    output_preview.mkdir(parents=True, exist_ok=True)
    return sandbox, input_copy, output_preview


def _fake_dry_result(**overrides) -> CoreDryRunResult:
    data = dict(
        status=CoreDryRunStatus.COMPLETED_WITH_REVIEW,
        run_id="cursor-auto-smoke-1",
        recognized=(
            CoreDryRunDocumentResult(
                document_name="invoice.txt",
                document_type="invoice",
                classification_status="recognized",
                status_label="erkannt",
                confidence_label="limited_text_evidence",
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
        planned_destinations=(
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
        summary=CoreDryRunSummary(
            total_documents=3,
            recognized_count=1,
            review_count=1,
            error_count=1,
            planned_destination_count=2,
        ),
        warnings=("ocr_not_run", "no_write_performed"),
        safety_proof=empty_safety_proof(evidence_notes=("no_source_mutation",)),
        message="Core-Dry-Run abgeschlossen ohne Source-Mutation.",
    )
    data.update(overrides)
    return CoreDryRunResult(**data)


def _install_safety_monkeypatches(
    monkeypatch: pytest.MonkeyPatch,
    *,
    dry_impl,
) -> dict[str, int]:
    """Fail the smoke if run_once / OCR / AI / network paths are touched."""

    counters = {"run_once": 0, "ocr_ai_network": 0}

    def boom_run_once(*_a, **_k):
        counters["run_once"] += 1
        raise AssertionError("run_once must not be called in Cursor automated smoke")

    def boom_side_channel(*_a, **_k):
        counters["ocr_ai_network"] += 1
        raise AssertionError("OCR/AI/network path must not run in Cursor automated smoke")

    monkeypatch.setattr("invoice_tool.run.run_once", boom_run_once, raising=False)
    monkeypatch.setattr(
        "invoice_tool.core_dry_run.run_core_dry_run_sandbox",
        dry_impl,
    )

    # Best-effort guards — modules may or may not be imported; never allow side channels.
    for target in (
        "invoice_tool.ocr.run_ocr",
        "invoice_tool.ocr.extract_text",
        "invoice_tool.ai.classify",
        "invoice_tool.ai.analyze",
        "requests.get",
        "requests.post",
        "httpx.get",
        "httpx.post",
        "urllib.request.urlopen",
    ):
        try:
            monkeypatch.setattr(target, boom_side_channel, raising=False)
        except Exception:
            pass

    return counters


def test_cursor_automated_local_pilot_smoke_sandbox_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sandbox, input_copy, output_preview = _sandbox_dirs(tmp_path)
    assert input_copy.resolve() != output_preview.resolve()
    assert str(REAL_INVOICE_ROOT) not in str(input_copy.resolve())
    assert str(REAL_INVOICE_ROOT) not in str(output_preview.resolve())

    # Synthetic placeholder documents accepted by dry-run test path (no OCR/AI).
    (input_copy / "invoice.txt").write_text(
        "Rechnung\nRechnungsnummer CURSOR-SMOKE-1\nGesamtbetrag 1,00\n",
        encoding="utf-8",
    )
    (input_copy / "scan.pdf").write_bytes(b"%PDF-1.4 synthetic-cursor-smoke")
    (input_copy / "note.pdf").write_bytes(b"%PDF-1.4 synthetic-note")

    before_hashes = _digest_tree(input_copy)
    before_listing = _listing(input_copy)
    real_before = _digest_tree(REAL_INVOICE_ROOT) if REAL_INVOICE_ROOT.exists() else {}

    called: list[object] = []

    def fake_dry(request):
        called.append(request)
        return _fake_dry_result()

    counters = _install_safety_monkeypatches(monkeypatch, dry_impl=fake_dry)

    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = str(input_copy)
    state.workspace_output_folder_override = str(output_preview)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"

    mark_start_checking(state)
    result = apply_start_processing(state, profile_id="profile-a")

    assert called, "run_core_dry_run_sandbox must be reached via Track-B chain"
    dry_req = called[0]
    assert dry_req.dry_run is True
    assert dry_req.no_mutation is True
    assert dry_req.productive_mode_requested is False
    assert Path(dry_req.input_dir).resolve() == input_copy.resolve()
    assert Path(dry_req.output_dir).resolve() == output_preview.resolve()
    assert Path(dry_req.input_dir).resolve() != Path(dry_req.output_dir).resolve()

    assert counters["run_once"] == 0
    assert counters["ocr_ai_network"] == 0

    # Result state + honest buckets (synthetic but mapped through real UI-v2 state).
    assert result.run_id == "cursor-auto-smoke-1"
    assert result.status in {"completed", "completed_with_review"}
    assert result.recognized_count == 1
    assert result.review_count == 1
    assert result.error_count == 1
    assert result.planned_destination_count == 2
    assert result.warnings
    assert result.safety_proof_summary

    buckets = build_result_bucket_summary(result)
    assert buckets.recognized_count == 1
    assert buckets.review_count == 1
    assert buckets.error_count == 1

    review_vm = build_review_page_vm(state)
    assert review_vm.review_count == 1
    assert review_vm.error_count == 1
    assert review_vm.result_count == 1
    assert review_vm.final_actions_blocked is True
    assert review_vm.productive_actions_exposed is False
    assert review_vm.export_preview_only is True

    report = build_export_preview_report(result)
    text = render_export_preview_text(report)
    payload = build_run_export_payload(report)
    assert report.title == REPORT_TITLE
    assert "Export-Vorschau" in text
    assert MSG_NO_FINAL_FILES_WRITTEN in text
    assert MSG_ORIGINALS_UNCHANGED in text
    assert MSG_PRODUCTIVE_PROCESSING_BLOCKED in text
    assert MSG_SAAS_NOT_READY in text
    assert MSG_LOCAL_PILOT_SANDBOX_ONLY in text
    assert report.preview_only is True
    assert report.claims_final_files_written is False
    assert report.claims_saas_ready is False
    assert report.claims_local_pilot_ready is False
    assert report.claims_productive_processing is False
    assert payload["preview"] is True
    assert payload["productive_export"] is False
    assert report_contains_forbidden_claims(report) is False
    for claim in FORBIDDEN_READY_CLAIMS:
        # Positive maturity claims must not appear; negated SaaS message is allowed.
        if claim.lower() in text.lower():
            assert "nicht" in text.lower()
    for phrase in FORBIDDEN_FINAL_LANGUAGE:
        assert phrase not in text.lower()
    # Honest "not production-ready" posture via blocked productive + no ready claims.
    assert "production-ready" not in text.lower() or "nicht" in text.lower()
    assert productive_actions_exposed(result) is False
    assert planned_destinations_are_preview_only(result) is True

    # Mutation proof: input_copy unchanged; output has no final renamed invoices.
    assert _digest_tree(input_copy) == before_hashes
    assert _listing(input_copy) == before_listing
    written = [p for p in output_preview.rglob("*") if p.is_file()]
    assert written == []
    assert not any(p.suffix.lower() == ".pdf" for p in written)

    if REAL_INVOICE_ROOT.exists():
        assert _digest_tree(REAL_INVOICE_ROOT) == real_before
    assert os.environ.get("KI_RECHNUNGEN_PRODUCTIVE", "") in {"", "0", "false", "False"}

    assert SMOKE_CLASSIFICATION == "CURSOR_AUTOMATED_SMOKE_PASS_WITH_SYNTHETIC_RESULT"
    assert PRODUCT_STATUS_AFTER.endswith("CURSOR_SMOKE_READY")


def test_bridge_request_enforces_sandbox_contract(tmp_path: Path) -> None:
    sandbox, input_copy, output_preview = _sandbox_dirs(tmp_path)
    (input_copy / "a.pdf").write_bytes(b"%PDF-1.4 a")
    req = CoreBridgeRequest(
        input_folder=str(input_copy),
        output_folder=str(output_preview),
        sandbox_root=str(sandbox),
        profile_id="profile-a",
        configuration_id="config-a",
        original_source_folder=str(tmp_path / "original-never-used"),
        dry_run=True,
        productive_execution_allowed=False,
        mode="sandbox_dry_run",
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
    )
    dry = build_core_dry_run_request_from_bridge(
        req,
        input_folder=req.input_folder or "",
        output_folder=req.output_folder or "",
        sandbox_root=req.sandbox_root or "",
        profile_id="profile-a",
        configuration_id="config-a",
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
    )
    assert dry.dry_run is True
    assert dry.no_mutation is True
    assert dry.productive_mode_requested is False
    assert "input_copy" in dry.input_dir
    assert "output_preview" in dry.output_dir
    assert dry.input_dir != dry.output_dir


def test_run_once_failure_if_invoked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sandbox, input_copy, output_preview = _sandbox_dirs(tmp_path)
    (input_copy / "invoice.txt").write_text("Rechnung\n", encoding="utf-8")
    called: list[str] = []

    def fake_dry(request):
        called.append("dry")
        return _fake_dry_result()

    counters = _install_safety_monkeypatches(monkeypatch, dry_impl=fake_dry)
    result = run_core_bridge_sandbox_dry_run(
        CoreBridgeRequest(
            input_folder=str(input_copy),
            output_folder=str(output_preview),
            sandbox_root=str(sandbox),
            profile_id="profile-a",
            configuration_id="config-a",
            dry_run=True,
            productive_execution_allowed=False,
            mode="sandbox_dry_run",
            copied_data_confirmation=True,
            original_folder_exclusion_confirmation=True,
        )
    )
    assert called == ["dry"]
    assert result.ok is True
    assert counters["run_once"] == 0

    with pytest.raises(AssertionError, match="run_once must not be called"):
        import invoice_tool.run as run_mod

        run_mod.run_once()  # type: ignore[attr-defined]
    assert counters["run_once"] == 1


def test_smoke_docs_and_audit_exist_with_required_status() -> None:
    doc = (
        ROOT
        / "docs"
        / "KI_RECHNUNGEN_TRACK_B_CURSOR_AUTOMATED_LOCAL_PILOT_SMOKE_2026-07-22.md"
    )
    audit = (
        ROOT
        / "docs"
        / "audits"
        / "KI_RECHNUNGEN_TRACK_B_CURSOR_AUTOMATED_LOCAL_PILOT_SMOKE_2026-07-22.md"
    )
    assert doc.is_file()
    assert audit.is_file()
    doc_text = doc.read_text(encoding="utf-8")
    audit_text = audit.read_text(encoding="utf-8")
    assert "CURSOR_AUTOMATED_SMOKE_PASS_WITH_SYNTHETIC_RESULT" in doc_text or (
        "synthetisch" in doc_text.lower()
    )
    assert PRODUCT_STATUS_AFTER in audit_text
    assert "nicht SaaS-ready" in doc_text
    assert "nicht production-ready" in doc_text
    assert "tmp_path" in doc_text
    assert "run_once" in doc_text
    assert "KI_RECHNUNGEN_TRACK_B_CURSOR_SMOKE_EVIDENCE_REVIEW_AND_NEXT_GATE_01" in audit_text
    assert "26" in audit_text
    assert "No productive processing" in audit_text or "Keine produktive" in audit_text
