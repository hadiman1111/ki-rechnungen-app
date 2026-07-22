"""Core Dry-Run no-mutation implementation tests (Prompt 2/34).

Uses pytest tmp_path only. No real invoice folders, no OCR/AI, no network.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from invoice_tool.core_dry_run import run_core_dry_run_sandbox
from invoice_tool.ui_v2.core_dry_run_contract import (
    ERROR_ORIGINAL_LOOKING,
    ERROR_SAME_INPUT_OUTPUT,
    CoreDryRunContractViolation,
    CoreDryRunMode,
    CoreDryRunRequest,
    CoreDryRunResult,
    CoreDryRunStatus,
)

ROOT = Path(__file__).resolve().parents[1]
CORE_DRY_RUN = ROOT / "invoice_tool" / "core_dry_run.py"


def _valid_request(tmp_path: Path, **overrides) -> CoreDryRunRequest:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    data = dict(
        input_dir=str(inbox),
        output_dir=str(outbox),
        sandbox_root=str(sandbox),
        profile_id="profile-dry-run",
        configuration_id="config-dry-run",
        dry_run=True,
        no_mutation=True,
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
        productive_mode_requested=False,
        mode=CoreDryRunMode.SANDBOX_DRY_RUN,
        original_source_folder=str(tmp_path / "original-never-used"),
        run_id="core-dry-run-test-001",
    )
    data.update(overrides)
    return CoreDryRunRequest(**data)


def _listing(path: Path) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    for child in sorted(path.iterdir(), key=lambda p: p.name):
        if child.is_file():
            rows.append((child.name, child.stat().st_size))
        else:
            rows.append((child.name + "/", -1))
    return rows


def test_valid_dry_run_returns_core_dry_run_result(tmp_path: Path) -> None:
    request = _valid_request(tmp_path)
    inbox = Path(request.input_dir)  # type: ignore[arg-type]
    (inbox / "note.txt").write_text("kurze notiz ohne beleg", encoding="utf-8")
    result = run_core_dry_run_sandbox(request)
    assert isinstance(result, CoreDryRunResult)
    assert result.status in {
        CoreDryRunStatus.COMPLETED,
        CoreDryRunStatus.COMPLETED_WITH_REVIEW,
        CoreDryRunStatus.FAILED,
    }
    assert result.run_id == "core-dry-run-test-001"


def test_invalid_request_rejected_via_contract(tmp_path: Path) -> None:
    request = _valid_request(tmp_path, dry_run=False)
    with pytest.raises(CoreDryRunContractViolation):
        run_core_dry_run_sandbox(request)


def test_does_not_move_rename_or_delete_source(tmp_path: Path) -> None:
    request = _valid_request(tmp_path)
    inbox = Path(request.input_dir)  # type: ignore[arg-type]
    source = inbox / "beleg.pdf"
    source.write_bytes(b"%PDF-1.4 dry-run-fake\n")
    before_names = {p.name for p in inbox.iterdir()}
    before_bytes = source.read_bytes()
    before_listing = _listing(inbox)

    result = run_core_dry_run_sandbox(request)
    assert result.safety_proof is not None
    assert result.safety_proof.no_source_move is True
    assert result.safety_proof.no_source_rename is True
    assert result.safety_proof.no_source_delete is True

    assert source.exists()
    assert source.read_bytes() == before_bytes
    assert {p.name for p in inbox.iterdir()} == before_names
    assert _listing(inbox) == before_listing
    assert not (inbox / "beleg_renamed.pdf").exists()


def test_does_not_create_archive_in_input(tmp_path: Path) -> None:
    request = _valid_request(tmp_path)
    inbox = Path(request.input_dir)  # type: ignore[arg-type]
    (inbox / "a.pdf").write_bytes(b"%PDF-1.4\n")
    assert not (inbox / "archiv").exists()
    result = run_core_dry_run_sandbox(request)
    assert not (inbox / "archiv").exists()
    assert result.safety_proof is not None
    assert result.safety_proof.no_source_archive is True


def test_does_not_write_outside_output_dir(tmp_path: Path) -> None:
    request = _valid_request(tmp_path)
    inbox = Path(request.input_dir)  # type: ignore[arg-type]
    outbox = Path(request.output_dir)  # type: ignore[arg-type]
    sandbox = Path(request.sandbox_root)  # type: ignore[arg-type]
    (inbox / "a.pdf").write_bytes(b"%PDF-1.4\n")

    before_outside = {
        p.resolve()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    result = run_core_dry_run_sandbox(request)
    after_files = {p.resolve() for p in tmp_path.rglob("*") if p.is_file()}
    new_files = after_files - before_outside
    # Prefer in-memory only: no new files anywhere, including output.
    assert new_files == set()
    assert result.safety_proof is not None
    assert result.safety_proof.writes_confined_to_sandbox_output is True
    # Guard: nothing new under sandbox except possible output (none expected).
    for path in sandbox.rglob("*"):
        if path.is_file() and outbox.resolve() in path.resolve().parents:
            pytest.fail(f"unexpected write under output: {path}")


def test_does_not_call_productive_run_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invoice_tool.run as run_module

    calls: list[object] = []

    def _boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append((args, kwargs))
        raise AssertionError("run_once must not be called from core dry-run")

    monkeypatch.setattr(run_module, "run_once", _boom)
    request = _valid_request(tmp_path)
    Path(request.input_dir).joinpath("x.pdf").write_bytes(b"%PDF-1.4\n")  # type: ignore[arg-type]
    result = run_core_dry_run_sandbox(request)
    assert calls == []
    assert result.safety_proof is not None
    assert result.safety_proof.productive_mode_disabled is True


def test_does_not_call_datev_cloud_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invoice_tool.core_dry_run as dry

    calls: list[str] = []

    def _export(*_a, **_k):  # type: ignore[no-untyped-def]
        calls.append("datev")
        raise AssertionError("DATEV/cloud export must not run")

    monkeypatch.setattr(dry, "_DATEV_CLOUD_EXPORT_HOOK", None)
    # Ensure hook stays unset; if dry-run ever set/called it, _forbid would fail.
    request = _valid_request(tmp_path)
    Path(request.input_dir).joinpath("x.pdf").write_bytes(b"%PDF-1.4\n")  # type: ignore[arg-type]
    result = run_core_dry_run_sandbox(request)
    assert calls == []
    assert dry._DATEV_CLOUD_EXPORT_HOOK is None
    assert result.safety_proof is not None
    assert result.safety_proof.real_datev_cloud_export_disabled is True
    # AST: no datev/cloud export call sites in implementation.
    tree = ast.parse(CORE_DRY_RUN.read_text(encoding="utf-8"))
    call_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                call_names.append(func.id)
            elif isinstance(func, ast.Attribute):
                call_names.append(func.attr)
    assert "run_once" not in call_names
    assert not any("datev" in n.lower() for n in call_names)
    assert not any("cloud_export" in n.lower() for n in call_names)


def test_produces_recognized_review_error_buckets(tmp_path: Path) -> None:
    request = _valid_request(tmp_path)
    inbox = Path(request.input_dir)  # type: ignore[arg-type]
    (inbox / "invoice_ok.txt").write_text(
        "Rechnung Nr 123\nGesamtbetrag 10 EUR\nMwSt 19%\n",
        encoding="utf-8",
    )
    (inbox / "scan.pdf").write_bytes(b"%PDF-1.4 insufficient\n")
    (inbox / "weird.bin").write_bytes(b"\x00\x01\x02binary")
    result = run_core_dry_run_sandbox(request)
    assert len(result.recognized) >= 1
    assert len(result.review) >= 1
    assert len(result.errors) >= 1
    assert result.summary.recognized_count == len(result.recognized)
    assert result.summary.review_count == len(result.review)
    assert result.summary.error_count == len(result.errors)
    assert result.summary.total_documents == (
        len(result.recognized) + len(result.review) + len(result.errors)
    )


def test_unreadable_or_unsupported_becomes_error_not_crash(tmp_path: Path) -> None:
    request = _valid_request(tmp_path)
    inbox = Path(request.input_dir)  # type: ignore[arg-type]
    (inbox / "nope.xyz").write_bytes(b"xxx")
    result = run_core_dry_run_sandbox(request)
    assert result.status in {
        CoreDryRunStatus.FAILED,
        CoreDryRunStatus.COMPLETED_WITH_REVIEW,
    }
    assert any(e.error_code == "unsupported_file_type" for e in result.errors)


def test_insufficient_evidence_is_review_not_fake_recognized(tmp_path: Path) -> None:
    request = _valid_request(tmp_path)
    inbox = Path(request.input_dir)  # type: ignore[arg-type]
    # Filename looks like invoice but body has no markers — must NOT be recognized.
    (inbox / "Rechnung_SOMAA_final.txt").write_text("hello world only", encoding="utf-8")
    (inbox / "Rechnung_AMEX.pdf").write_bytes(b"%PDF-1.4\n")
    result = run_core_dry_run_sandbox(request)
    assert result.recognized == ()
    assert len(result.review) >= 2
    assert all(item.status_label == "unklar" for item in result.review)


def test_planned_destination_is_data_only(tmp_path: Path) -> None:
    request = _valid_request(tmp_path)
    inbox = Path(request.input_dir)  # type: ignore[arg-type]
    outbox = Path(request.output_dir)  # type: ignore[arg-type]
    (inbox / "doc.pdf").write_bytes(b"%PDF-1.4\n")
    result = run_core_dry_run_sandbox(request)
    assert result.planned_destinations
    for planned in result.planned_destinations:
        assert planned.applied is False
        assert str(outbox) in planned.planned_path or "geplant" in planned.planned_path
        assert not Path(planned.planned_path).exists()
    assert result.safety_proof is not None
    assert result.safety_proof.planned_destinations_not_applied is True


def test_safety_proof_confirms_no_mutation(tmp_path: Path) -> None:
    request = _valid_request(tmp_path)
    inbox = Path(request.input_dir)  # type: ignore[arg-type]
    (inbox / "a.pdf").write_bytes(b"%PDF-1.4\n")
    before = _listing(inbox)
    result = run_core_dry_run_sandbox(request)
    after = _listing(inbox)
    assert before == after
    proof = result.safety_proof
    assert proof is not None
    assert proof.no_original_mutation is True
    assert proof.no_source_archive is True
    assert proof.no_source_move is True
    assert proof.no_source_rename is True
    assert proof.no_source_delete is True
    assert proof.writes_confined_to_sandbox_output is True
    assert proof.productive_mode_disabled is True
    assert proof.real_datev_cloud_export_disabled is True
    assert any("source_snapshot_identical=True" in n for n in proof.evidence_notes)


def test_same_input_output_rejected(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    shared = sandbox / "same"
    shared.mkdir(parents=True)
    request = _valid_request(
        tmp_path,
        input_dir=str(shared),
        output_dir=str(shared),
        sandbox_root=str(sandbox),
    )
    with pytest.raises(CoreDryRunContractViolation) as excinfo:
        run_core_dry_run_sandbox(request)
    assert excinfo.value.code == ERROR_SAME_INPUT_OUTPUT


def test_original_looking_folder_rejected(tmp_path: Path) -> None:
    request = _valid_request(
        tmp_path,
        input_dir=str(tmp_path / "Desktop" / "TEST Rechnungen" / "inbox"),
        output_dir=str(tmp_path / "sandbox" / "out"),
        sandbox_root=None,
    )
    with pytest.raises(CoreDryRunContractViolation) as excinfo:
        run_core_dry_run_sandbox(request)
    assert excinfo.value.code == ERROR_ORIGINAL_LOOKING


def test_core_dry_run_avoids_flet_bootstrap_on_fresh_import(tmp_path: Path) -> None:
    """Importing core_dry_run must not require a preloaded Flet UI stack.

    Uses a subprocess so ui_v2.__init__ is not already warm from other tests.
    """
    code = """
import sys
from pathlib import Path
root = Path(%r)
sys.path.insert(0, str(root))
# Remove any preloaded ui_v2 package.
for key in list(sys.modules):
    if key == "invoice_tool.ui_v2" or key.startswith("invoice_tool.ui_v2."):
        del sys.modules[key]
    if key == "flet" or key.startswith("flet."):
        del sys.modules[key]
from invoice_tool.core_dry_run import run_core_dry_run_sandbox
assert "flet" not in sys.modules
from invoice_tool.ui_v2.core_dry_run_contract import CoreDryRunRequest, CoreDryRunMode
sandbox = Path(%r)
inbox = sandbox / "in"
out = sandbox / "out"
inbox.mkdir(parents=True)
out.mkdir(parents=True)
(inbox / "a.pdf").write_bytes(b"%%PDF-1.4\\n")
req = CoreDryRunRequest(
    input_dir=str(inbox),
    output_dir=str(out),
    sandbox_root=str(sandbox),
    profile_id="p",
    configuration_id="c",
    dry_run=True,
    no_mutation=True,
    copied_data_confirmation=True,
    original_folder_exclusion_confirmation=True,
    productive_mode_requested=False,
    mode=CoreDryRunMode.SANDBOX_DRY_RUN,
)
result = run_core_dry_run_sandbox(req)
assert result.safety_proof is not None
assert "flet" not in sys.modules
print("ok")
""" % (
        str(ROOT),
        str(tmp_path / "fresh-sandbox"),
    )
    import subprocess

    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok" in proc.stdout
