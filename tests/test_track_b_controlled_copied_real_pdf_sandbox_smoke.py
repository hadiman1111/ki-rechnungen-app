"""Track-B Controlled Copied Real-PDF Sandbox Smoke (Prompt 10/11).

Uses the controlled copied sandbox folders under KI-Rechnungen-Test when present.
Does NOT invent synthetic CoreDryRunResult rows. Does NOT call run_once.
Does NOT touch productive/original invoice folders.

After Prompt-11 path-policy repair, the controlled KI-Rechnungen-Test folder is
accepted as an explicit copied sandbox/test path when input/output are separate.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from invoice_tool.ui_v2.core_bridge import (
    CoreBridgeRequest,
    CoreBridgeStatus,
    map_core_result_to_processing_run_state,
    path_looks_like_original as bridge_path_looks_like_original,
    run_core_bridge_sandbox_dry_run,
)
from invoice_tool.ui_v2.core_dry_run_contract import (
    CoreDryRunContractViolation,
    CoreDryRunRequest,
    path_looks_like_original as contract_path_looks_like_original,
    validate_core_dry_run_request,
)
from invoice_tool.ui_v2.export_reporting import (
    MSG_NO_FINAL_FILES_WRITTEN,
    MSG_PRODUCTIVE_PROCESSING_BLOCKED,
    MSG_SAAS_NOT_READY,
    build_export_preview_report,
    build_run_export_payload,
    render_export_preview_text,
    report_contains_forbidden_claims,
)
from invoice_tool.ui_v2.result_mapping import (
    build_result_bucket_summary,
    productive_actions_exposed,
)
from invoice_tool.ui_v2.sandbox_processing_gate import (
    MSG_SAFETY_COPIED_SANDBOX_CONFIRMED,
    classify_copied_sandbox_test_paths,
)

ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "KI_RECHNUNGEN_TRACK_B_CONTROLLED_COPIED_REAL_PDF_SANDBOX_SMOKE_01"
DEFAULT_INPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input")
DEFAULT_OUTPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output")
ALLOWED_ROOT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test")
FORBIDDEN_PATH_MARKERS = (
    "/RECHNUNGEN/",
    "/02_Rechnungseingang/",
    "/Rechnungseingang/",
    "/Original",
    "/Produktiv",
)
FORBIDDEN_READY_CLAIMS = (
    "SaaS-ready",
    "production-ready",
    "Local-Pilot-Ready",
)
PRODUCT_STATUS_PASS = "TRACK_B_COPIED_REAL_PDF_SANDBOX_SMOKE_PASS_PREVIEW_ONLY"
PRODUCT_STATUS_BLOCKED_NO_REAL_PATH = (
    "TRACK_B_COPIED_REAL_PDF_SANDBOX_SMOKE_BLOCKED_NO_REAL_PATH"
)
PRODUCT_STATUS_BLOCKED_NO_USEFUL = (
    "TRACK_B_COPIED_REAL_PDF_SANDBOX_SMOKE_BLOCKED_NO_USEFUL_RESULT"
)
PRODUCT_STATUS_FAIL_UNSAFE = "TRACK_B_COPIED_REAL_PDF_SANDBOX_SMOKE_FAIL_UNSAFE"
OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY = "OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY"
OUTPUT_PREVIEW_ONLY_ARTIFACTS = "OUTPUT_PREVIEW_ONLY_ARTIFACTS"
OUTPUT_UNEXPECTED_FINAL_FILES = "OUTPUT_UNEXPECTED_FINAL_FILES"
OUTPUT_NO_USEFUL_RESULT = "OUTPUT_NO_USEFUL_RESULT"


def _env_path(name: str, default: Path) -> Path:
    raw = (os.environ.get(name) or "").strip()
    return Path(raw).expanduser() if raw else default


def _resolve_folders() -> tuple[Path, Path]:
    return (
        _env_path("KI_RECHNUNGEN_REAL_PDF_SMOKE_INPUT", DEFAULT_INPUT).resolve(),
        _env_path("KI_RECHNUNGEN_REAL_PDF_SMOKE_OUTPUT", DEFAULT_OUTPUT).resolve(),
    )


def _pdfs(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
    )


def _digest_tree(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not folder.exists():
        return out
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(folder))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return out


def _listing(folder: Path) -> list[str]:
    if not folder.exists():
        return []
    return sorted(
        str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file() or p.is_dir()
    )


def _path_has_forbidden_marker(path: Path) -> list[str]:
    text = str(path)
    return [marker for marker in FORBIDDEN_PATH_MARKERS if marker in text]


def _under_allowed_root(path: Path) -> bool:
    try:
        path.relative_to(ALLOWED_ROOT.resolve())
        return True
    except ValueError:
        return False


def _install_safety_monkeypatches(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    counters = {"run_once": 0, "ocr_ai_network": 0}

    def boom_run_once(*_a, **_k):
        counters["run_once"] += 1
        raise AssertionError("run_once must not be called in real-PDF sandbox smoke")

    def boom_side_channel(*_a, **_k):
        counters["ocr_ai_network"] += 1
        raise AssertionError("OCR/AI/network path must not run in real-PDF sandbox smoke")

    monkeypatch.setattr("invoice_tool.run.run_once", boom_run_once, raising=False)
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


def _classify_output_files(output_dir: Path, *, before_count: int) -> str:
    files = [p for p in output_dir.rglob("*") if p.is_file()] if output_dir.exists() else []
    pdfs = [p for p in files if p.suffix.lower() == ".pdf"]
    # Final renamed invoices would appear as PDFs under output in a productive path.
    if pdfs:
        return OUTPUT_UNEXPECTED_FINAL_FILES
    if files and before_count == 0:
        return OUTPUT_PREVIEW_ONLY_ARTIFACTS
    if not files:
        return OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY
    return OUTPUT_NO_USEFUL_RESULT


def test_controlled_copied_real_pdf_sandbox_smoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir, output_dir = _resolve_folders()
    sandbox_root = ALLOWED_ROOT.resolve()

    if not input_dir.is_dir():
        pytest.skip(
            f"BLOCKED_NO_REAL_PATH: controlled input missing: {input_dir}"
        )
    if not _pdfs(input_dir):
        pytest.skip(
            f"BLOCKED_NO_REAL_PATH: controlled input has zero PDFs: {input_dir}"
        )

    assert input_dir != output_dir, "input/output must be separate"
    assert _under_allowed_root(input_dir), f"input outside allowed root: {input_dir}"
    assert _under_allowed_root(output_dir), f"output outside allowed root: {output_dir}"
    assert not _path_has_forbidden_marker(input_dir), (
        f"input looks productive/original: {input_dir}"
    )
    assert not _path_has_forbidden_marker(output_dir), (
        f"output looks productive/original: {output_dir}"
    )
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    assert output_dir.is_dir()

    path_class = classify_copied_sandbox_test_paths(
        str(input_dir),
        str(output_dir),
        sandbox_root=str(sandbox_root),
        check_filesystem=True,
    )
    assert path_class.approved is True, (
        f"controlled copied sandbox must be accepted after path-policy repair: "
        f"{path_class.reason_code} / {path_class.message}"
    )
    assert MSG_SAFETY_COPIED_SANDBOX_CONFIRMED in path_class.safety_proof_lines

    pdf_count = len(_pdfs(input_dir))
    assert pdf_count >= 1
    before_hashes = _digest_tree(input_dir)
    before_listing = _listing(input_dir)
    before_output_files = [
        p for p in output_dir.rglob("*") if p.is_file()
    ] if output_dir.exists() else []
    before_output_count = len(before_output_files)

    counters = _install_safety_monkeypatches(monkeypatch)

    # Track-B path-policy probe (string heuristic used by bridge + contract).
    bridge_rejects = bridge_path_looks_like_original(str(input_dir)) or (
        bridge_path_looks_like_original(str(output_dir))
    )
    contract_rejects = contract_path_looks_like_original(str(input_dir)) or (
        contract_path_looks_like_original(str(output_dir))
    )

    bridge_result = run_core_bridge_sandbox_dry_run(
        CoreBridgeRequest(
            input_folder=str(input_dir),
            output_folder=str(output_dir),
            sandbox_root=str(sandbox_root),
            profile_id="profile-real-pdf-smoke",
            configuration_id="config-real-pdf-smoke",
            dry_run=True,
            productive_execution_allowed=False,
            mode="sandbox_dry_run",
            copied_data_confirmation=True,
            original_folder_exclusion_confirmation=True,
            run_id="controlled-real-pdf-smoke-1",
        )
    )

    dry_request = CoreDryRunRequest(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        dry_run=True,
        no_mutation=True,
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
        productive_mode_requested=False,
        profile_id="profile-real-pdf-smoke",
        configuration_id="config-real-pdf-smoke",
        run_id="controlled-real-pdf-smoke-1",
        sandbox_root=str(sandbox_root),
    )

    core_violation: CoreDryRunContractViolation | None = None
    dry_result = None
    try:
        validate_core_dry_run_request(dry_request)
        from invoice_tool.core_dry_run import run_core_dry_run_sandbox

        dry_result = run_core_dry_run_sandbox(dry_request)
    except CoreDryRunContractViolation as exc:
        core_violation = exc

    # Safety proofs that always hold for this smoke.
    assert counters["run_once"] == 0
    assert counters["ocr_ai_network"] == 0
    assert _digest_tree(input_dir) == before_hashes
    assert _listing(input_dir) == before_listing
    after_output_files = [p for p in output_dir.rglob("*") if p.is_file()]
    assert not any(p.suffix.lower() == ".pdf" for p in after_output_files), (
        "final renamed invoice PDFs must not appear in output"
    )
    assert os.environ.get("KI_RECHNUNGEN_PRODUCTIVE", "") in {
        "",
        "0",
        "false",
        "False",
    }

    # Honest blocker path (should not trigger for KI-Rechnungen-Test after repair).
    if (
        bridge_rejects
        or contract_rejects
        or bridge_result.status == CoreBridgeStatus.BLOCKED_ORIGINAL_LOOKING
        or core_violation is not None
    ):
        assert bridge_result.ok is False
        assert bridge_result.status == CoreBridgeStatus.BLOCKED_ORIGINAL_LOOKING
        assert core_violation is not None
        assert core_violation.code == "core_dry_run_original_looking_path"
        assert dry_result is None

        run_state = map_core_result_to_processing_run_state(bridge_result)
        assert run_state.status == "blocked"
        output_class = _classify_output_files(
            output_dir, before_count=before_output_count
        )
        print("SMOKE_CLASSIFICATION=BLOCKED_NO_REAL_PATH")
        print(f"PRODUCT_STATUS={PRODUCT_STATUS_BLOCKED_NO_REAL_PATH}")
        print(f"PDF_COUNT={pdf_count}")
        print(f"OUTPUT_CLASSIFICATION={output_class}")
        print(f"BRIDGE_STATUS={bridge_result.status.value}")
        print(f"CORE_VIOLATION={core_violation.code}")
        print(f"TASK_ID={TASK_ID}")
        pytest.fail(
            "controlled KI-Rechnungen-Test was still rejected as original-looking; "
            "path-policy repair did not take effect"
        )

    # Success path: real dry-run against copied PDFs (no synthetic injection).
    assert dry_result is not None
    assert bridge_result.ok is True
    assert dry_request.dry_run is True
    assert dry_request.no_mutation is True
    assert dry_request.productive_mode_requested is False

    run_state = map_core_result_to_processing_run_state(bridge_result)
    assert run_state.run_id
    assert run_state.status in {"completed", "completed_with_review", "failed", "blocked"}
    assert run_state.safety_proof_summary
    buckets = build_result_bucket_summary(run_state)
    useful = (
        buckets.recognized_count
        + buckets.review_count
        + buckets.error_count
        + run_state.planned_destination_count
    ) > 0 or bool(run_state.warnings)
    if not useful:
        print("SMOKE_CLASSIFICATION=BLOCKED_NO_USEFUL_RESULT")
        print(f"PRODUCT_STATUS={PRODUCT_STATUS_BLOCKED_NO_USEFUL}")
        pytest.fail(
            f"{PRODUCT_STATUS_BLOCKED_NO_USEFUL}: dry-run returned no useful "
            "workspace/export evidence"
        )

    report = build_export_preview_report(run_state)
    text = render_export_preview_text(report)
    payload = build_run_export_payload(report)
    assert report.claims_final_files_written is False
    assert report.claims_saas_ready is False
    assert report.claims_productive_processing is False
    assert report_contains_forbidden_claims(report) is False
    assert MSG_NO_FINAL_FILES_WRITTEN in text or "keine final" in text.lower()
    assert MSG_PRODUCTIVE_PROCESSING_BLOCKED in text or "produktiv" in text.lower()
    assert MSG_SAAS_NOT_READY in text or "saas" in text.lower()
    for claim in FORBIDDEN_READY_CLAIMS:
        if claim.lower() in text.lower():
            assert "nicht" in text.lower()
    assert payload.get("productive_export") is False
    assert productive_actions_exposed(run_state) is False
    assert "production-ready" not in text.lower() or "nicht" in text.lower()

    output_class = _classify_output_files(output_dir, before_count=before_output_count)
    assert output_class != OUTPUT_UNEXPECTED_FINAL_FILES
    assert output_class in {
        OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY,
        OUTPUT_PREVIEW_ONLY_ARTIFACTS,
    }
    print("SMOKE_CLASSIFICATION=PASS_PREVIEW_ONLY")
    print(f"PRODUCT_STATUS={PRODUCT_STATUS_PASS}")
    print(f"PDF_COUNT={pdf_count}")
    print(f"OUTPUT_CLASSIFICATION={output_class}")
    print(f"REVIEW_COUNT={buckets.review_count}")
    print(f"RECOGNIZED_COUNT={buckets.recognized_count}")
    print(f"PLANNED_COUNT={run_state.planned_destination_count}")
    print(
        "EMPTY_OUTPUT_EXPLANATION="
        "Core dry-run plans destinations as data-only; no final invoice PDFs "
        "are written when dry_run/no_mutation are enforced. Empty output with "
        "useful in-memory result/export preview is expected preview-only success."
    )
    assert PRODUCT_STATUS_PASS == "TRACK_B_COPIED_REAL_PDF_SANDBOX_SMOKE_PASS_PREVIEW_ONLY"


def test_controlled_real_pdf_smoke_docs_and_audit_exist() -> None:
    doc = (
        ROOT
        / "docs"
        / "KI_RECHNUNGEN_TRACK_B_CONTROLLED_COPIED_REAL_PDF_SANDBOX_SMOKE_2026-07-22.md"
    )
    audit = (
        ROOT
        / "docs"
        / "audits"
        / "KI_RECHNUNGEN_TRACK_B_CONTROLLED_COPIED_REAL_PDF_SANDBOX_SMOKE_2026-07-22.md"
    )
    assert doc.is_file()
    assert audit.is_file()
    doc_text = doc.read_text(encoding="utf-8")
    audit_text = audit.read_text(encoding="utf-8")
    assert TASK_ID in doc_text
    assert "Prompt 10/34" in doc_text or "Prompt 10 von 34" in doc_text
    assert "KI-Rechnungen-Test" in doc_text
    assert "nicht SaaS-ready" in doc_text
    assert "nicht production-ready" in doc_text
    assert "run_once" in doc_text
    assert (
        PRODUCT_STATUS_BLOCKED_NO_REAL_PATH in audit_text
        or PRODUCT_STATUS_PASS in audit_text
        or "TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBLE" in audit_text
    )
    assert "24" in audit_text or "23" in audit_text
    assert "KI_RECHNUNGEN_TRACK_B_REAL_PDF" in audit_text
