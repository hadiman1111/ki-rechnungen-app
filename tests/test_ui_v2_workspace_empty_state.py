"""UI-v2 workspace honesty: no preview/private mock run data; empty state when no run.

Non-GUI tests only — no window, no PDF processing, no processing-core imports.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

from invoice_tool.ui_v2.pages.workspace import (
    ADAPTER_NOT_CONNECTED_HINT,
    EMPTY_NO_RESULTS_TITLE,
    EMPTY_NO_RUN_DETAIL,
    EMPTY_NO_RUN_STATUS,
    EMPTY_NO_RUN_TITLE,
    START_CTA_LABEL,
    _display_mappings,
    _display_results,
    workspace_honesty_copy,
)
from invoice_tool.ui_v2.processing_state import idle_processing_state
from invoice_tool.ui_v2.view_models import ResultSummaryVM

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
TRACK_A_PATHS = (
    ROOT / "app_main.py",
    ROOT / "invoice_tool" / "gui.py",
    ROOT / "invoice_tool" / "ui_shell.py",
    ROOT / "invoice_tool" / "ui_workspace.py",
    ROOT / "invoice_tool" / "processing.py",
    ROOT / "invoice_tool" / "routing.py",
    ROOT / "invoice_tool" / "routing_guards.py",
    ROOT / "invoice_tool" / "classification.py",
    ROOT / "invoice_tool" / "target_routing.py",
    ROOT / "invoice_tool" / "run.py",
)

PRIVATE_RUNTIME_MARKERS = (
    "AMEX",
    "Privat",
    "SOMAA",
    "Hadi",
    "Bismarck",
    "voba",
    "Volksbank",
    "/Users/",
    "Desktop/Programm Belegerfassung",
    "TEST Rechnungen",
    "American Express",
    "preview-1",
    "_PREVIEW_",
)


def test_workspace_source_has_no_private_or_preview_runtime_data() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    for marker in PRIVATE_RUNTIME_MARKERS:
        assert marker not in src, marker
    assert "_PREVIEW_RESULTS" not in src
    assert "_PREVIEW_MAPPINGS" not in src
    assert "_PREVIEW_INPUT_PATH" not in src
    assert "use_preview" not in src
    assert "list_input_pdf_filenames" not in src


def test_workspace_empty_helpers_return_no_fake_rows() -> None:
    assert _display_results(tuple()) == tuple()
    assert _display_mappings(tuple()) == tuple()


def test_workspace_empty_state_says_no_run_occurred() -> None:
    copy = workspace_honesty_copy(
        has_real_results=False,
        processing_state=idle_processing_state(),
    )
    assert copy.has_real_results is False
    assert copy.status_line is not None
    assert EMPTY_NO_RUN_STATUS in copy.status_line
    assert EMPTY_NO_RESULTS_TITLE in copy.status_line
    assert copy.results_title == EMPTY_NO_RUN_TITLE
    assert EMPTY_NO_RUN_TITLE == "Noch kein Laufergebnis."
    assert "Sandbox-Modus: vorbereitet" in (copy.results_detail or "")
    assert "Noch kein Laufergebnis" in (copy.results_title or "")
    assert "echten Lauf" in (copy.results_detail or "")
    assert "Eingangs- und Ausgabeordner" in (copy.results_detail or "")
    assert "Prüfbereich" in (copy.results_detail or "")
    assert copy.start_cta_label == START_CTA_LABEL
    assert copy.adapter_hint == ADAPTER_NOT_CONNECTED_HINT
    blob = " ".join(filter(None, (copy.status_line, copy.results_title, copy.results_detail)))
    for marker in ("AMEX", "Privat", "SOMAA", "Hadi", "Bismarck", "voba", "/Users/"):
        assert marker not in blob, marker


def test_workspace_does_not_claim_processed_docs_without_run() -> None:
    copy = workspace_honesty_copy(has_real_results=False)
    blob = " ".join(filter(None, (copy.status_line, copy.results_title, copy.results_detail)))
    assert "Dateien konnten nicht verarbeitet werden" not in blob
    assert "12 OK" not in blob
    assert "4 Fehler" not in blob
    assert "rechnung_2024-03_amex" not in blob
    assert "American Express" not in blob
    # Real results still produce display rows only from supplied VMs — never from preview.
    results = (
        ResultSummaryVM(
            filename="doc-a.pdf",
            configuration_label="Allgemein",
            destination_summary="Ziel/Allgemein/doc-a.pdf",
            status_label="OK",
        ),
    )
    display = _display_results(results)
    assert len(display) == 1
    assert display[0].source_filename == "doc-a.pdf"
    assert display[0].configuration_label == "Allgemein"
    assert workspace_honesty_copy(has_real_results=True).results_title is None


def test_workspace_module_does_not_import_processing_core_or_track_a() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden_prefixes = (
        "invoice_tool.processing",
        "invoice_tool.routing",
        "invoice_tool.routing_guards",
        "invoice_tool.classification",
        "invoice_tool.target_routing",
        "invoice_tool.run",
        "invoice_tool.gui",
        "invoice_tool.ui_shell",
        "invoice_tool.ui_workspace",
        "app_main",
    )
    for name in imported:
        assert not any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes), name


def test_workspace_import_does_not_load_processing_core() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    importlib.import_module("invoice_tool.ui_v2.pages.workspace")
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in (
        "invoice_tool.processing",
        "invoice_tool.routing",
        "invoice_tool.routing_guards",
        "invoice_tool.classification",
        "invoice_tool.target_routing",
        "invoice_tool.run",
        "invoice_tool.gui",
        "invoice_tool.ui_workspace",
    ):
        assert forbidden not in newly, forbidden


def test_track_a_files_untouched_by_workspace_module() -> None:
    for path in TRACK_A_PATHS:
        assert path.exists(), path
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "app_main" not in src
    assert "ui_workspace" not in src
    assert "invoice_tool.processing" not in src
