"""Track-B UI-v2 export/reporting completion — pure/non-GUI tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from invoice_tool.ui_v2.export_reporting import (
    EXPORT_KIND,
    MSG_DESTINATION_REVIEW,
    MSG_EXPORT_EMPTY,
    MSG_EXPORT_FROM_REAL_RUN,
    MSG_EXPORT_IS_PREVIEW,
    MSG_EXPORT_NEEDS_PATH,
    MSG_EXPORT_NO_FILE_MUTATION_OF_ORIGINALS,
    MSG_EXPORT_OK,
    MSG_NO_RUN_PAYLOAD,
    MSG_PLANNED_DESTINATION_HINT,
    SECTION_DESTINATIONS,
    SECTION_FAILED,
    SECTION_RECOGNIZED,
    SECTION_SUMMARY,
    SECTION_UNCLEAR,
    build_run_export_payload,
    build_run_report_view_model,
    export_processing_run_state,
    render_run_export_csv,
    render_run_export_json,
    write_run_report_export,
)
from invoice_tool.ui_v2.pages.settings import EXPORT_SECTION_DETAIL, build_settings_page_vm
from invoice_tool.ui_v2.pages.workspace import build_workspace_run_report_vm
from invoice_tool.ui_v2.processing_state import (
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "invoice_tool" / "ui_v2" / "export_reporting.py"
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
SETTINGS = ROOT / "invoice_tool" / "ui_v2" / "pages" / "settings.py"
PROCESSING_CORE = (
    "invoice_tool.processing",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
    "invoice_tool.run",
)
PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX",
    "voba",
    "/Users/",
    "Desktop/",
    "Privat",
    "Volksbank",
)


def _completed_state() -> ProcessingRunState:
    return ProcessingRunState(
        status="completed",
        message=(
            "Dies ist ein Sandbox-Lauf mit kopierten Daten. "
            "Sandbox-Lauf abgeschlossen (kopierte Testdaten)."
        ),
        run_id="run-export-1",
        results=(
            ProcessingResultSummary(
                document_name="ok.pdf",
                document_type="rechnung",
                classification_status="ok",
                status_label="OK",
                confidence_label="hoch",
                target_hint="ziel/ok.pdf",
            ),
            ProcessingResultSummary(
                document_name="fail.pdf",
                document_type="beleg",
                classification_status="failed",
                status_label="fehlgeschlagen",
                target_hint="ziel/fail.pdf",
            ),
        ),
        review_items=(
            ProcessingReviewItem(
                document_name="unklar.pdf",
                reason="Zuordnung unklar",
                status_label="unklar",
                evidence_summary="Kein eindeutiger Nachweis",
                next_action_hint="Profil prüfen",
            ),
        ),
        errors=("Extraktion fehlgeschlagen: bad.pdf",),
    )


def test_empty_report_is_honest() -> None:
    report = build_run_report_view_model(ProcessingRunState())
    assert report.empty is True
    assert report.export_available is False
    assert report.recognized == ()
    assert report.unclear == ()
    assert report.failed == ()
    assert report.user_summary.headline == MSG_NO_RUN_PAYLOAD
    assert MSG_EXPORT_IS_PREVIEW in report.honest_copy
    assert MSG_EXPORT_FROM_REAL_RUN in report.honest_copy
    assert MSG_EXPORT_NO_FILE_MUTATION_OF_ORIGINALS in report.honest_copy
    assert "keine Vorschau-Daten" not in MSG_EXPORT_FROM_REAL_RUN
    assert report.mutates_original_files is False
    assert report.starts_processing is False


def test_report_answers_five_user_questions() -> None:
    report = build_run_report_view_model(_completed_state())
    assert report.empty is False
    assert report.section_titles == (
        SECTION_RECOGNIZED,
        SECTION_UNCLEAR,
        SECTION_FAILED,
        SECTION_DESTINATIONS,
        SECTION_SUMMARY,
    )
    assert report.section_titles[0] == "Was wurde erkannt?"
    assert report.section_titles[1] == "Was ist unklar?"
    assert report.section_titles[2] == "Was ist fehlgeschlagen?"
    assert report.section_titles[3] == "Welche Dateien wären wohin gegangen?"
    assert report.section_titles[4] == "Welche Zusammenfassung bekommt der Nutzer?"

    assert len(report.recognized) == 1
    assert report.recognized[0].document_name == "ok.pdf"
    assert report.recognized[0].target_hint == "ziel/ok.pdf"

    assert len(report.unclear) == 1
    assert report.unclear[0].document_name == "unklar.pdf"
    assert report.unclear[0].reason == "Zuordnung unklar"

    assert len(report.failed) == 2
    failed_names = {item.document_name for item in report.failed}
    failed_messages = {item.message for item in report.failed}
    assert "fail.pdf" in failed_names
    assert "Extraktion fehlgeschlagen: bad.pdf" in failed_messages

    destinations = {item.document_name: item.destination_hint for item in report.destinations}
    assert destinations["ok.pdf"] == "ziel/ok.pdf"
    assert destinations["fail.pdf"] == "ziel/fail.pdf"
    assert destinations["unklar.pdf"] == MSG_DESTINATION_REVIEW
    assert all(item.planned_only for item in report.destinations)
    assert MSG_PLANNED_DESTINATION_HINT in report.honest_copy

    assert report.user_summary.recognized_count == 1
    assert report.user_summary.unclear_count == 1
    assert report.user_summary.failed_count == 2
    assert "1 erkannt" in report.user_summary.headline
    assert "1 unklar" in report.user_summary.headline
    assert "2 fehlgeschlagen" in report.user_summary.headline


def test_export_payload_contains_five_question_blocks() -> None:
    report = build_run_report_view_model(_completed_state())
    payload = build_run_export_payload(report)
    assert payload["kind"] == EXPORT_KIND
    assert payload["cloud"] is False
    assert payload["preview"] is True
    assert payload["productive_export"] is False
    assert payload["datev_export"] is False
    assert payload["disclaimer"] == MSG_EXPORT_IS_PREVIEW
    assert payload["persistence"] == "local_export_only"
    questions = payload["questions"]
    assert set(questions) == {
        "recognized",
        "unclear",
        "failed",
        "destinations",
        "user_summary",
    }
    assert questions["recognized"]["title"] == SECTION_RECOGNIZED
    assert questions["unclear"]["title"] == SECTION_UNCLEAR
    assert questions["failed"]["title"] == SECTION_FAILED
    assert questions["destinations"]["title"] == SECTION_DESTINATIONS
    assert questions["destinations"]["planned_only"] is True
    assert questions["user_summary"]["title"] == SECTION_SUMMARY
    parsed = json.loads(render_run_export_json(payload))
    assert parsed["run_id"] == "run-export-1"
    csv_text = render_run_export_csv(report)
    assert "document_name" in csv_text
    assert "ok.pdf" in csv_text
    assert "unklar.pdf" in csv_text
    assert "recognized" in csv_text


def test_write_export_requires_real_payload_and_path(tmp_path: Path) -> None:
    empty = write_run_report_export(build_run_report_view_model(None), tmp_path / "x.json")
    assert empty.ok is False
    assert empty.error == MSG_EXPORT_EMPTY

    report = build_run_report_view_model(_completed_state())
    missing = write_run_report_export(report, "")
    assert missing.ok is False
    assert missing.error == MSG_EXPORT_NEEDS_PATH

    target = tmp_path / "bericht.json"
    ok = write_run_report_export(report, target)
    assert ok.ok is True
    assert ok.status == "exported"
    assert target.is_file()
    csv_path = tmp_path / "bericht_routing.csv"
    assert csv_path.is_file()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["questions"]["recognized"]["count"] == 1


def test_directory_export_writes_default_filenames(tmp_path: Path) -> None:
    out_dir = tmp_path / "export_dir"
    result = export_processing_run_state(_completed_state(), out_dir)
    assert result.ok is True
    assert (out_dir / "laufbericht.json").is_file()
    assert (out_dir / "laufbericht_routing.csv").is_file()


def test_workspace_report_vm_uses_processing_run_state_only() -> None:
    state = UiV2State(processing_run_state=_completed_state())
    report = build_workspace_run_report_vm(state)
    assert report.run_id == "run-export-1"
    assert len(report.recognized) == 1
    assert len(report.unclear) == 1


def test_state_export_run_report_sets_feedback(tmp_path: Path) -> None:
    state = UiV2State(processing_run_state=_completed_state())
    missing = state.export_run_report("")
    assert missing is None
    assert state.workspace_export_feedback_error is True
    assert state.workspace_export_feedback == MSG_EXPORT_NEEDS_PATH

    target = tmp_path / "lauf.json"
    result = state.export_run_report(target)
    assert result is not None and result.ok is True
    assert state.workspace_export_feedback_error is False
    assert state.workspace_export_feedback == MSG_EXPORT_OK
    assert target.is_file()


def test_settings_export_section_points_to_workspace_report() -> None:
    from invoice_tool.ui_v2.pages.settings import EXPORT_SECTION_DETAIL_EXPANDED

    vm = build_settings_page_vm(UiV2State())
    export_sections = [section for section in vm.sections if section.title == "Export"]
    assert len(export_sections) == 1
    assert export_sections[0].detail == EXPORT_SECTION_DETAIL
    assert EXPORT_SECTION_DETAIL == "Exportvorschau · kein produktiver DATEV-/Cloud-Export"
    assert "DATEV" in EXPORT_SECTION_DETAIL
    assert "Arbeitsbereich" in EXPORT_SECTION_DETAIL_EXPANDED
    assert "erkannt" in EXPORT_SECTION_DETAIL_EXPANDED
    assert MSG_EXPORT_IS_PREVIEW in EXPORT_SECTION_DETAIL_EXPANDED


def test_module_has_no_processing_core_imports() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    for core in PROCESSING_CORE:
        assert core not in imported
    src = MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        # Markers may appear only as rejection tokens, not as defaults.
        if marker in src and marker not in ("/Users/", "Desktop/"):
            assert marker not in (
                'display_name = "',
                'target_hint = "',
                'destination_hint = "',
            )


def test_workspace_wires_export_reporting_without_core() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "build_run_report_view_model" in src
    assert "Ergebnisvorschau exportieren" in src or "EXPORT_ACTION_LABEL" in src
    assert "MSG_EXPORT_IS_PREVIEW" in src
    assert "Was wurde erkannt?" in src or "SECTION_RECOGNIZED" in src
    for core in ("invoice_tool.processing", "invoice_tool.run", "invoice_tool.routing"):
        assert core not in src
    settings_src = SETTINGS.read_text(encoding="utf-8")
    assert "EXPORT_SECTION_DETAIL" in settings_src
    assert "Noch nicht konfigurierbar" not in EXPORT_SECTION_DETAIL


def test_report_does_not_mix_successful_into_unclear_or_failed() -> None:
    report = build_run_report_view_model(_completed_state())
    recognized_names = {item.document_name for item in report.recognized}
    unclear_names = {item.document_name for item in report.unclear}
    failed_doc_names = {item.document_name for item in report.failed if item.document_name}
    assert "ok.pdf" in recognized_names
    assert "ok.pdf" not in unclear_names
    assert "ok.pdf" not in failed_doc_names
    assert "unklar.pdf" not in recognized_names
    assert "fail.pdf" not in recognized_names
