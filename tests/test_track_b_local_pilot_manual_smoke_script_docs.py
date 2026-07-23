"""Doc-gate for Track-B Local Pilot Manual Smoke Script (Prompt 7/34).

Docs + fixture only — no GUI, no real invoice folders, no productive processing.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "docs" / "KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_MANUAL_SMOKE_SCRIPT_2026-07-22.md"
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_MANUAL_SMOKE_SCRIPT_2026-07-22.md"
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing doc: {path}"
    return path.read_text(encoding="utf-8")


def test_smoke_script_exists() -> None:
    assert SMOKE.is_file()


def test_smoke_script_requires_copied_sandbox_input() -> None:
    text = _read(SMOKE)
    assert "kopiert" in text.lower() or "copied" in text.lower()
    assert "input_copy" in text
    assert "Sandbox" in text


def test_smoke_script_requires_explicit_separate_sandbox_output() -> None:
    text = _read(SMOKE)
    assert "output_preview" in text
    assert "separat" in text.lower()
    assert "Input ≠ Output" in text or "nicht dem Input" in text or "verschieden" in text


def test_smoke_script_forbids_original_folders() -> None:
    text = _read(SMOKE)
    assert "Originalordner" in text or "Original" in text
    assert "verboten" in text.lower() or "Forbidden" in text or "nicht" in text


def test_smoke_script_forbids_productive_processing() -> None:
    text = _read(SMOKE)
    assert "produktive Verarbeitung" in text.lower() or "Produktiv" in text
    assert "nicht freigegeben" in text or "gesperrt" in text or "Verboten" in text


def test_smoke_script_says_no_saas_ready() -> None:
    text = _read(SMOKE)
    assert "nicht SaaS-ready" in text


def test_smoke_script_says_no_production_ready() -> None:
    text = _read(SMOKE)
    assert "nicht production-ready" in text


def test_smoke_script_includes_evidence_checklist() -> None:
    text = _read(SMOKE)
    assert "Evidence checklist" in text or "Evidenz" in text
    assert "recognized count" in text
    assert "safety proof visible" in text


def test_smoke_script_includes_stop_conditions() -> None:
    text = _read(SMOKE)
    assert "Stop rules" in text or "Stopbedingungen" in text or "Sofort stoppen" in text
    assert "Fake-Success" in text
    assert "produktive Verarbeitung startet" in text.lower() or "Produktive Verarbeitung startet" in text


def test_smoke_script_includes_return_classifications() -> None:
    text = _read(SMOKE)
    for label in (
        "MANUAL_SMOKE_PASS",
        "MANUAL_SMOKE_PASS_WITH_NOTES",
        "MANUAL_SMOKE_BLOCKED",
        "MANUAL_SMOKE_FAIL_UNSAFE",
    ):
        assert label in text


def test_audit_exists() -> None:
    assert AUDIT.is_file()


def test_audit_states_no_code_runtime_change() -> None:
    text = _read(AUDIT)
    assert "No code/runtime change" in text or "Keine Code-/Runtime-Änderung" in text
    assert "nur Docs" in text or "Docs + Doc-Test" in text


def test_audit_states_no_real_invoice_folders_touched() -> None:
    text = _read(AUDIT)
    assert "No real invoice folders touched" in text or "keine realen Rechnungsordner" in text.lower()


def test_audit_states_release_tags_unchanged() -> None:
    text = _read(AUDIT)
    assert "No release tag changes" in text or "Release-Tags unverändert" in text
    assert "product-v1-local-pilot-2026-07-22" in text


def test_audit_gives_next_task() -> None:
    text = _read(AUDIT)
    assert "KI_RECHNUNGEN_TRACK_B_MANUAL_SMOKE_EVIDENCE_INTAKE_01" in text
    assert "Remaining prompts: 27" in text or "27" in text
    assert (
        "TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY_MANUAL_SMOKE_SCRIPT_READY" in text
    )
