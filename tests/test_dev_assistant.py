"""Tests für scripts/dev_assistant.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

# Skript-Pfad relativ zum Repo
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "dev_assistant.py"


def _import_dev_assistant():
    """Lädt dev_assistant als Modul ohne Package-Struktur."""
    spec = importlib.util.spec_from_file_location("dev_assistant", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _run_mode(mode: str, extra: Optional[list[str]] = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), "--mode", mode] + (extra or [])
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


def _make_run_dir(
    tmp_path: Path,
    *,
    profile_applied: bool = True,
    summary: Optional[dict] = None,
    run_id: str = "20990101_120000",
) -> Path:
    """Erstellt eine minimale gültige Run-Ordner-Struktur."""
    run_dir = tmp_path / run_id
    report_dir = run_dir / "output" / "_runs" / run_id
    report_dir.mkdir(parents=True)

    if summary is None:
        summary = {
            "processed": 25,
            "documents": 1,
            "duplicates": 3,
            "unklar": 1,
            "errors": 0,
            "system_fallbacks": 0,
        }

    report = {
        "run_id": run_id,
        "date": "2099-01-01 12:00:00",
        "preset": "office_default",
        "input_files": 30,
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
    (run_dir / "runtime_rules.json").write_text(
        json.dumps({"active_preset": "office_default", "presets": {}, "_meta": meta}),
        encoding="utf-8",
    )
    if profile_applied:
        (run_dir / "profile_snapshot.json").write_text(
            json.dumps({"profile": "test"}), encoding="utf-8"
        )
    return run_dir


# ---------------------------------------------------------------------------
# find_latest_run_dir
# ---------------------------------------------------------------------------

class TestFindLatestRunDir:
    def test_returns_none_for_missing_dir(self, tmp_path):
        m = _import_dev_assistant()
        result = m.find_latest_run_dir(str(tmp_path / "nonexistent"))
        assert result is None

    def test_returns_none_for_empty_dir(self, tmp_path):
        m = _import_dev_assistant()
        result = m.find_latest_run_dir(str(tmp_path))
        assert result is None

    def test_returns_latest_run_by_name(self, tmp_path):
        m = _import_dev_assistant()
        (tmp_path / "20260101_100000").mkdir()
        (tmp_path / "20260102_100000").mkdir()
        (tmp_path / "20260103_100000").mkdir()
        result = m.find_latest_run_dir(str(tmp_path))
        assert result is not None
        assert result.name == "20260103_100000"

    def test_ignores_non_digit_dirs(self, tmp_path):
        m = _import_dev_assistant()
        (tmp_path / "logs").mkdir()
        (tmp_path / "20260101_100000").mkdir()
        result = m.find_latest_run_dir(str(tmp_path))
        assert result is not None
        assert result.name == "20260101_100000"


# ---------------------------------------------------------------------------
# Baseline-Vergleich (über check_profile_run-Logik)
# ---------------------------------------------------------------------------

class TestBaselineComparison:
    def test_check_last_run_pass_with_matching_baseline(self, tmp_path):
        m = _import_dev_assistant()
        run_dir = _make_run_dir(tmp_path)
        found = m.find_latest_run_dir(str(tmp_path))
        assert found is not None
        assert found.name == "20990101_120000"

    def test_check_last_run_via_subprocess_pass(self, tmp_path):
        # Erstelle Basis-Output mit gültigem Run-Dir
        base = tmp_path / "smoke_out"
        base.mkdir()
        _make_run_dir(base, summary={
            "processed": 25, "documents": 1, "duplicates": 3,
            "unklar": 1, "errors": 0, "system_fallbacks": 0
        })
        result = _run_mode("check-last-run", ["--base-output", str(base)])
        assert result.returncode == 0
        assert "PASS" in result.stdout or "WEITER IN CURSOR" in result.stdout

    def test_check_last_run_via_subprocess_fail_on_baseline(self, tmp_path):
        base = tmp_path / "smoke_out_fail"
        base.mkdir()
        _make_run_dir(base, summary={
            "processed": 10, "documents": 0, "duplicates": 0,
            "unklar": 5, "errors": 2, "system_fallbacks": 0
        })
        result = _run_mode("check-last-run", ["--base-output", str(base)])
        assert result.returncode == 1
        assert "FAIL" in result.stdout or "STOPP" in result.stdout

    def test_check_last_run_stopp_when_no_run_dir(self, tmp_path):
        base = tmp_path / "empty"
        base.mkdir()
        result = _run_mode("check-last-run", ["--base-output", str(base)])
        assert result.returncode == 1
        assert "STOPP" in result.stdout or "FEHLER" in result.stdout


# ---------------------------------------------------------------------------
# Entscheidungssignal-Format
# ---------------------------------------------------------------------------

class TestSignalOutput:
    def test_status_mode_outputs_signal(self):
        result = _run_mode("status")
        assert "ENTSCHEIDUNGSSIGNAL:" in result.stdout

    def test_status_clean_tree_yields_weiter(self, tmp_path):
        import io
        from contextlib import redirect_stdout
        m = _import_dev_assistant()
        buf = io.StringIO()
        with redirect_stdout(buf):
            m.print_signal(m.Signal.WEITER, modus="Agent", chatgpt="nein")
        output = buf.getvalue()
        assert "WEITER IN CURSOR" in output
        assert "ZAUBERWORT" in output

    def test_stopp_signal_format(self):
        import io
        from contextlib import redirect_stdout
        m = _import_dev_assistant()
        buf = io.StringIO()
        with redirect_stdout(buf):
            m.print_signal(
                m.Signal.STOPP,
                modus="Ask",
                chatgpt="nein",
                begruendung="Testgrund",
                naechster_schritt="Testschritt",
            )
        output = buf.getvalue()
        assert "STOPP" in output
        assert "Testgrund" in output
        assert "Testschritt" in output

    def test_nutzerfreigabe_signal_format(self):
        import io
        from contextlib import redirect_stdout
        m = _import_dev_assistant()
        buf = io.StringIO()
        with redirect_stdout(buf):
            m.print_signal(
                m.Signal.FREIGABE,
                freigabefrage="Soll ich pushen?",
                empfehlung="freigeben",
                begruendung="Alles grün.",
            )
        output = buf.getvalue()
        assert "NUTZERFREIGABE" in output
        assert "freigeben" in output
        assert "Soll ich pushen?" in output

    def test_chatgpt_signal_format(self):
        import io
        from contextlib import redirect_stdout
        m = _import_dev_assistant()
        buf = io.StringIO()
        with redirect_stdout(buf):
            m.print_signal(
                m.Signal.CHATGPT,
                chatgpt="ja",
                frage_an_chatgpt="Was ist die Ursache?",
            )
        output = buf.getvalue()
        assert "CHATGPT FRAGEN" in output
        assert "Was ist die Ursache?" in output


# ---------------------------------------------------------------------------
# Akustisches Signal
# ---------------------------------------------------------------------------

class TestBeep:
    def test_beep_does_not_raise_on_failure(self):
        """_beep() darf keinen harten Fehler erzeugen, auch wenn osascript fehlt."""
        m = _import_dev_assistant()
        with patch.object(m, "subprocess") as mock_sub:
            mock_sub.run.side_effect = FileNotFoundError("not found")
            m._beep()  # darf nicht werfen

    def test_beep_is_called_for_stopp_signal(self):
        m = _import_dev_assistant()
        with patch.object(m, "_beep") as mock_beep:
            m.print_signal(m.Signal.STOPP, begruendung="x", naechster_schritt="y")
        mock_beep.assert_called_once()

    def test_beep_is_called_for_freigabe_signal(self):
        m = _import_dev_assistant()
        with patch.object(m, "_beep") as mock_beep:
            m.print_signal(m.Signal.FREIGABE, freigabefrage="?")
        mock_beep.assert_called_once()

    def test_beep_is_called_for_chatgpt_signal(self):
        m = _import_dev_assistant()
        with patch.object(m, "_beep") as mock_beep:
            m.print_signal(m.Signal.CHATGPT, frage_an_chatgpt="?")
        mock_beep.assert_called_once()

    def test_beep_not_called_for_weiter_signal(self):
        m = _import_dev_assistant()
        with patch.object(m, "_beep") as mock_beep:
            m.print_signal(m.Signal.WEITER)
        mock_beep.assert_not_called()


# ---------------------------------------------------------------------------
# check-last-run mit vollständiger Dummy-Struktur
# ---------------------------------------------------------------------------

class TestCheckLastRunDummy:
    def test_full_valid_structure_passes(self, tmp_path):
        base = tmp_path / "runs"
        base.mkdir()
        _make_run_dir(base, profile_applied=True)
        result = _run_mode("check-last-run", ["--base-output", str(base)])
        assert result.returncode == 0

    def test_missing_profile_snapshot_fails(self, tmp_path):
        base = tmp_path / "runs"
        base.mkdir()
        run_dir = _make_run_dir(base, profile_applied=True)
        (run_dir / "profile_snapshot.json").unlink()
        result = _run_mode("check-last-run", ["--base-output", str(base)])
        assert result.returncode == 1

    def test_missing_runtime_rules_fails(self, tmp_path):
        base = tmp_path / "runs"
        base.mkdir()
        run_dir = _make_run_dir(base, profile_applied=True)
        (run_dir / "runtime_rules.json").unlink()
        result = _run_mode("check-last-run", ["--base-output", str(base)])
        assert result.returncode == 1

    def test_latest_run_selected_correctly(self, tmp_path):
        """Wenn zwei Runs vorhanden sind, wird der neuere gewählt."""
        m = _import_dev_assistant()
        base = tmp_path / "multi"
        base.mkdir()
        _make_run_dir(base, run_id="20260101_090000")
        _make_run_dir(base, run_id="20260102_100000")
        latest = m.find_latest_run_dir(str(base))
        assert latest is not None
        assert latest.name == "20260102_100000"
