"""Doc-gate for Track-B Real-PDF GUI Visual Smoke Rerun (Prompt 14/34).

Docs evidence only — no GUI launch, no PDF processing, no productive runs,
no real invoice folders.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_RERUN_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_RERUN_2026-07-23.md"
)

CONTROLLED_INPUT = "/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input"
CONTROLLED_OUTPUT = "/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output"
START_CMD = ".venv-flet085/bin/python app_ui_v2.py"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing doc: {path}"
    return path.read_text(encoding="utf-8")


def test_doc_exists() -> None:
    assert DOC.is_file()


def test_audit_exists() -> None:
    assert AUDIT.is_file()


def test_doc_includes_corrected_start_command() -> None:
    assert START_CMD in _read(DOC)


def test_doc_includes_controlled_input_path() -> None:
    assert CONTROLLED_INPUT in _read(DOC)


def test_doc_includes_controlled_output_path() -> None:
    assert CONTROLLED_OUTPUT in _read(DOC)


def test_doc_includes_input_count_5() -> None:
    text = _read(DOC)
    assert "Input count:** 5" in text or "Input count: 5" in text or "**Input count:** 5" in text


def test_doc_includes_output_count_0() -> None:
    text = _read(DOC)
    assert "Output count:** 0" in text or "Output count: 0" in text or "**Output count:** 0" in text


def test_doc_includes_abgeschlossen() -> None:
    assert "Abgeschlossen" in _read(DOC)


def test_doc_includes_sandbox_completed_text() -> None:
    assert "Sandbox-Lauf mit Prüffällen abgeschlossen" in _read(DOC)


def test_doc_includes_erkannt_0() -> None:
    text = _read(DOC)
    assert "Erkannt" in text and "0" in text
    assert "Erkannt | 0" in text or "Erkannt: 0" in text or "Erkannt 0" in text


def test_doc_includes_pruefung_5() -> None:
    text = _read(DOC)
    assert "Prüfung" in text
    assert "Prüfung | 5" in text or "Prüfung: 5" in text or "Prüfung 5" in text


def test_doc_includes_fehler_0() -> None:
    text = _read(DOC)
    assert "Fehler" in text
    assert "Fehler | 0" in text or "Fehler: 0" in text or "Fehler 0" in text


def test_doc_includes_geplant_5() -> None:
    text = _read(DOC)
    assert "Geplant" in text
    assert "Geplant | 5" in text or "Geplant: 5" in text or "Geplant 5" in text


def test_doc_includes_originale_unveraendert() -> None:
    assert "Originale unverändert" in _read(DOC)


def test_doc_includes_produktiv_gesperrt() -> None:
    assert "Produktiv gesperrt" in _read(DOC)


def test_doc_includes_export_vorschau() -> None:
    assert "Export Vorschau" in _read(DOC)


def test_doc_includes_keine_originalordner() -> None:
    assert "Keine Originalordner" in _read(DOC)


def test_doc_states_output_empty_expected_preview_only() -> None:
    text = _read(DOC)
    assert "expected preview-only" in text.lower() or "erwartetes Preview-Only" in text or "expected preview-only" in text
    assert "Result-State" in text
    assert "Export Preview" in text or "Export-Vorschau" in text or "Export Vorschau" in text


def test_doc_states_gui_visual_smoke_pass() -> None:
    assert "GUI_VISUAL_SMOKE_PASS" in _read(DOC)


def test_doc_states_no_productive_processing() -> None:
    text = _read(DOC)
    assert "keine produktive Verarbeitung" in text.lower() or "No productive processing" in text


def test_doc_states_no_real_invoice_folders() -> None:
    text = _read(DOC)
    assert "keine realen Rechnungsordner" in text.lower() or "No real invoice folders" in text


def test_doc_states_not_saas_ready() -> None:
    text = _read(DOC)
    assert "nicht SaaS-ready" in text


def test_doc_states_not_production_ready() -> None:
    text = _read(DOC)
    assert "nicht production-ready" in text


def test_audit_states_product_status_after_task() -> None:
    text = _read(AUDIT)
    assert "TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_PASS_RECORDED" in text
    assert "Product status after task" in text


def test_audit_states_next_task() -> None:
    text = _read(AUDIT)
    assert "KI_RECHNUNGEN_TRACK_B_REVIEW_BUCKET_USABILITY_AND_ACTIONS_01" in text
    assert "Exact next task" in text or "next task" in text.lower()
