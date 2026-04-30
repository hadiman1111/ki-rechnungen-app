"""Tests für scripts/check_profile_run.py."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest


# ---------------------------------------------------------------------------
# Fixtures: minimaler Run-Ordner
# ---------------------------------------------------------------------------

def _make_run_dir(tmp_path: Path, *, profile_applied: bool = True, summary: Optional[dict] = None) -> Path:
    run_id = "20990101_120000"
    run_dir = tmp_path / run_id
    report_dir = run_dir / "output" / "_runs" / run_id
    report_dir.mkdir(parents=True)

    if summary is None:
        summary = {"processed": 5, "documents": 1, "duplicates": 0, "unklar": 0, "errors": 0, "system_fallbacks": 0}

    report = {
        "run_id": run_id,
        "date": "2099-01-01 12:00:00",
        "preset": "office_default",
        "input_files": 6,
        "summary": summary,
        "files": [],
    }
    (report_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    (report_dir / "routing_summary.csv").write_text("run_id,filename\n", encoding="utf-8")
    (report_dir / "decision_trace.jsonl").write_text("", encoding="utf-8")

    meta = {
        "profile_applied": profile_applied,
        "base_rules_source": "/fake/office_rules.json",
        "profile_source": "/fake/profile.json",
        "generated_sections": ["routing.strassen"],
        "prepended_sections": ["routing.payment_detection_rules"],
        "protected_sections": ["routing.final_assignment_rules"],
        "merge_strategy": "replace_generated_sections_prepend_payment_detection",
    }
    runtime_rules = {"active_preset": "office_default", "presets": {}, "_meta": meta}
    (run_dir / "runtime_rules.json").write_text(json.dumps(runtime_rules), encoding="utf-8")

    if profile_applied:
        (run_dir / "profile_snapshot.json").write_text(json.dumps({"profile": "test"}), encoding="utf-8")

    return run_dir


def _run_script(run_dir: Path, baseline: Optional[str] = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "scripts/check_profile_run.py", "--run-dir", str(run_dir)]
    if baseline:
        cmd += ["--baseline", baseline]
    return subprocess.run(cmd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckProfileRunPass:
    def test_pass_without_baseline(self, tmp_path):
        run_dir = _make_run_dir(tmp_path)
        result = _run_script(run_dir)
        assert result.returncode == 0
        assert "ERGEBNIS: PASS" in result.stdout

    def test_pass_with_matching_baseline(self, tmp_path):
        run_dir = _make_run_dir(tmp_path)
        result = _run_script(run_dir, baseline="5,1,0,0,0")
        assert result.returncode == 0
        assert "ERGEBNIS: PASS" in result.stdout

    def test_decision_signal_weiter_on_pass(self, tmp_path):
        run_dir = _make_run_dir(tmp_path)
        result = _run_script(run_dir, baseline="5,1,0,0,0")
        assert "ENTSCHEIDUNGSSIGNAL: WEITER IN CURSOR" in result.stdout

    def test_meta_shown(self, tmp_path):
        run_dir = _make_run_dir(tmp_path)
        result = _run_script(run_dir)
        assert "profile_applied" in result.stdout
        assert "generated_sections" in result.stdout
        assert "prepended_sections" in result.stdout
        assert "protected_sections" in result.stdout


class TestCheckProfileRunFail:
    def test_fail_on_baseline_mismatch(self, tmp_path):
        run_dir = _make_run_dir(tmp_path)
        result = _run_script(run_dir, baseline="99,0,0,0,0")
        assert result.returncode == 1
        assert "ERGEBNIS: FAIL" in result.stdout

    def test_decision_signal_stopp_on_fail(self, tmp_path):
        run_dir = _make_run_dir(tmp_path)
        result = _run_script(run_dir, baseline="99,0,0,0,0")
        assert "ENTSCHEIDUNGSSIGNAL: STOPP" in result.stdout

    def test_fail_missing_report(self, tmp_path):
        run_dir = _make_run_dir(tmp_path)
        (run_dir / "output" / "_runs" / "20990101_120000" / "report.json").unlink()
        result = _run_script(run_dir)
        assert result.returncode == 1
        assert "ERGEBNIS: FAIL" in result.stdout

    def test_fail_missing_runtime_rules(self, tmp_path):
        run_dir = _make_run_dir(tmp_path)
        (run_dir / "runtime_rules.json").unlink()
        result = _run_script(run_dir)
        assert result.returncode == 1

    def test_fail_missing_profile_snapshot_when_profile_active(self, tmp_path):
        run_dir = _make_run_dir(tmp_path, profile_applied=True)
        (run_dir / "profile_snapshot.json").unlink()
        result = _run_script(run_dir)
        assert result.returncode == 1

    def test_fail_invalid_run_dir(self, tmp_path):
        result = _run_script(tmp_path / "nonexistent")
        assert result.returncode == 2

    def test_fail_invalid_baseline_format(self, tmp_path):
        run_dir = _make_run_dir(tmp_path)
        result = _run_script(run_dir, baseline="5,1,0")
        assert result.returncode == 2


class TestCheckProfileRunUnklar:
    def test_unklar_cases_shown(self, tmp_path):
        run_id = "20990101_120000"
        run_dir = tmp_path / run_id
        report_dir = run_dir / "output" / "_runs" / run_id
        report_dir.mkdir(parents=True)

        summary = {"processed": 4, "documents": 0, "duplicates": 0, "unklar": 1, "errors": 0, "system_fallbacks": 0}
        report = {"run_id": run_id, "date": "x", "preset": "x", "input_files": 5, "summary": summary, "files": []}
        (report_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
        (report_dir / "routing_summary.csv").write_text("", encoding="utf-8")

        trace_entry = {
            "run_id": run_id,
            "original_filename": "unclear.pdf",
            "final_filename": "unklar.pdf",
            "final_status": "unklar",
            "final_art": "ai",
            "final_payment_field": "unklar",
            "final_assignment_rule_name": "somaa-unclear-payment",
            "account_match_reason": "Keine belastbaren Kontohinweise gefunden.",
            "conflicts": [],
        }
        (report_dir / "decision_trace.jsonl").write_text(json.dumps(trace_entry) + "\n", encoding="utf-8")

        meta = {"profile_applied": False, "generated_sections": [], "prepended_sections": [], "protected_sections": []}
        (run_dir / "runtime_rules.json").write_text(json.dumps({"_meta": meta}), encoding="utf-8")

        result = _run_script(run_dir)
        assert "unclear.pdf" in result.stdout
        assert "somaa-unclear-payment" in result.stdout
