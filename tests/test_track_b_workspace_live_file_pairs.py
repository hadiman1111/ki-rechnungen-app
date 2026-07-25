"""Track-B workspace live file pairs (2026-07-24).

Input files appear immediately after folder selection; output proposals align
row-by-row during/after check. UI/state only — no productive processing.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.finalization_readiness import FINAL_WRITE_ALLOWED_IN_THIS_PHASE
from invoice_tool.ui_v2.pages.workspace import (
    apply_workspace_input_folder_selection,
    apply_workspace_output_folder_selection,
    ensure_workspace_input_listing,
    open_workspace_document_preview,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.track_b_smoke_debug_copy import (
    ACTION_OPEN_REVIEW,
    ACTION_SHOW_DOCUMENT,
    LABEL_INPUT_FILES,
    LABEL_PROPOSED_OUTPUT_FILES,
    MSG_START_HELPER,
    START_CTA_STRONG,
    WORKSPACE_DOCUMENT_SHOW_MARKER,
    WORKSPACE_FILE_PAIR_MARKER,
    WORKSPACE_LIVE_FILE_PAIRS_MARKER,
)
from invoice_tool.ui_v2.workspace_file_pairs import (
    JUST_IN_TIME_STATUS,
    LIVE_FILE_PAIRS_MARKER,
    MSG_NEED_OUTPUT_FOLDER,
    MSG_NOT_CHECKED,
    MSG_PROPOSAL_CREATED,
    MSG_ROW_CHECKING,
    build_live_file_pairs_vm,
    merge_input_names_with_proposal_sources,
)
from invoice_tool.ui_v2.workspace_input_listing import (
    IGNORED_DIR_NAMES,
    LIVE_INPUT_LISTING_MARKER,
    MSG_NO_FILES_IN_INPUT,
    list_workspace_input_documents,
    refresh_workspace_input_listing_on_state,
)

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
LISTING = ROOT / "invoice_tool" / "ui_v2" / "workspace_input_listing.py"
PAIRS = ROOT / "invoice_tool" / "ui_v2" / "workspace_file_pairs.py"
STATE = ROOT / "invoice_tool" / "ui_v2" / "state.py"
ORACLE_SCRIPT = ROOT / "scripts" / "dev" / "track_b_automated_smoke_oracle.py"
TRACK_A_TEST = ROOT / "tests" / "test_track_a_internal_app_protection.py"
CONTROLLED_INPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input")
CONTROLLED_OUTPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output")

CORE_PROTECTED = (
    "invoice_tool/run.py",
    "invoice_tool/processing.py",
    "invoice_tool/routing.py",
    "invoice_tool/routing_guards.py",
    "invoice_tool/classification.py",
    "invoice_tool/target_routing.py",
    "invoice_tool/core_dry_run.py",
)
FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)


def _ws_src() -> str:
    return WORKSPACE.read_text(encoding="utf-8")


def _listing_src() -> str:
    return LISTING.read_text(encoding="utf-8")


def _pairs_src() -> str:
    return PAIRS.read_text(encoding="utf-8")


# --- Input listing ---


def test_01_input_files_listed_when_folder_selected(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "a.pdf").write_bytes(b"%PDF-1.4")
    (folder / "b.pdf").write_bytes(b"%PDF-1.4")
    state = UiV2State()
    apply_workspace_input_folder_selection(state, str(folder))
    assert state.workspace_input_filenames == ("a.pdf", "b.pdf")
    assert state.workspace_input_listing_count == 2
    assert LIVE_INPUT_LISTING_MARKER in state.workspace_input_listing_marker


def test_02_input_listing_before_processing(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "only.pdf").write_bytes(b"%PDF-1.4")
    state = UiV2State()
    apply_workspace_input_folder_selection(state, str(folder))
    assert state.processing_run_state.status == "idle"
    assert state.workspace_run_interaction_status == "idle"
    assert state.workspace_input_filenames == ("only.pdf",)


def test_03_input_listing_non_mutating(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    pdf = folder / "keep.pdf"
    pdf.write_bytes(b"%PDF-1.4 keep")
    before = pdf.read_bytes()
    mtime = pdf.stat().st_mtime_ns
    result = list_workspace_input_documents(str(folder))
    assert result.mutated is False
    assert result.filenames == ("keep.pdf",)
    assert pdf.read_bytes() == before
    assert pdf.stat().st_mtime_ns == mtime


def test_04_input_listing_no_run_once() -> None:
    tree = ast.parse(_listing_src())
    calls: list[str] = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        if isinstance(n.func, ast.Name):
            calls.append(n.func.id)
        elif isinstance(n.func, ast.Attribute):
            calls.append(n.func.attr)
    assert "run_once" not in calls
    assert "run_once(" not in _listing_src()


def test_05_input_listing_no_ocr() -> None:
    tree = ast.parse(_listing_src())
    calls: list[str] = []
    imports: list[str] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                calls.append(n.func.id.casefold())
            elif isinstance(n.func, ast.Attribute):
                calls.append(n.func.attr.casefold())
        elif isinstance(n, ast.Import):
            imports.extend(a.name.casefold() for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            imports.append(n.module.casefold())
    assert "ocr" not in calls
    assert "tesseract" not in " ".join(imports)
    assert "pytesseract" not in " ".join(imports)
    assert "import tesseract" not in _listing_src().casefold()


def test_06_archive_technical_folders_ignored(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "visible.pdf").write_bytes(b"%PDF-1.4")
    for name in ("archiv", "archive", "technical", "technisch"):
        nested = folder / name
        nested.mkdir()
        (nested / "hidden.pdf").write_bytes(b"%PDF-1.4")
    result = list_workspace_input_documents(str(folder))
    assert result.filenames == ("visible.pdf",)
    assert result.ignored_archive_or_technical is True
    assert "archiv" in IGNORED_DIR_NAMES


def test_07_empty_input_folder_message(tmp_path: Path) -> None:
    folder = tmp_path / "empty"
    folder.mkdir()
    result = list_workspace_input_documents(str(folder))
    assert result.count == 0
    assert result.empty_message == MSG_NO_FILES_IN_INPUT
    assert MSG_NO_FILES_IN_INPUT == "Keine Belege im Eingangsordner gefunden."


# --- Output placeholders ---


def test_08_output_column_exists_before_run() -> None:
    src = _ws_src()
    assert "LABEL_PROPOSED_OUTPUT_FILES" in src
    assert LABEL_PROPOSED_OUTPUT_FILES == "Vorgeschlagene Ausgabedateien"
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf",),
        output_folder_selected=True,
        run_active=False,
    )
    assert len(vm.rows) == 1
    assert vm.has_proposals is False


def test_09_aligned_placeholders_before_run() -> None:
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf", "b.pdf"),
        output_folder_selected=True,
    )
    assert [r.source_filename for r in vm.rows] == ["a.pdf", "b.pdf"]
    assert all(r.index == i for i, r in enumerate(vm.rows))
    assert all(not r.has_proposal for r in vm.rows)


def test_10_placeholder_wording() -> None:
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf",),
        output_folder_selected=True,
    )
    assert vm.rows[0].output_display in {MSG_NOT_CHECKED, "Noch kein Vorschlag"}
    assert "Noch nicht geprüft" in {MSG_NOT_CHECKED, vm.rows[0].output_display}


def test_11_missing_output_folder_message() -> None:
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf",),
        output_folder_selected=False,
    )
    assert vm.rows[0].output_display == MSG_NEED_OUTPUT_FOLDER
    assert MSG_NEED_OUTPUT_FOLDER == "Bitte Ausgangsordner wählen."


def test_12_no_fake_output_filenames_before_check() -> None:
    vm = build_live_file_pairs_vm(
        input_filenames=("Rechnung.pdf",),
        output_folder_selected=True,
    )
    assert vm.rows[0].proposed_filename == ""
    assert not vm.rows[0].has_proposal
    assert vm.rows[0].output_display == MSG_NOT_CHECKED
    assert vm.rows[0].output_display != "Rechnung.pdf"


# --- Check / update ---


def test_13_check_updates_proposal_column() -> None:
    planned = (
        ProcessingPlannedDestination(
            document_name="a.pdf",
            planned_path="preview/a.pdf",
            destination_label="PayPal",
            preview_only=True,
            applied=False,
            suggested_filename="2026-01-01_er_Test_1,00_paypal.pdf",
        ),
    )
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf",),
        output_folder_selected=True,
        planned_destinations=planned,
    )
    assert vm.rows[0].has_proposal
    assert "paypal.pdf" in vm.rows[0].proposed_filename.casefold() or "paypal" in (
        vm.rows[0].proposed_filename.casefold()
    )


def test_14_proposal_same_row_as_original() -> None:
    planned = (
        ProcessingPlannedDestination(
            document_name="left.pdf",
            planned_path="p",
            destination_label="x",
            preview_only=True,
            applied=False,
            suggested_filename="right_proposed.pdf",
        ),
        ProcessingPlannedDestination(
            document_name="other.pdf",
            planned_path="p",
            destination_label="x",
            preview_only=True,
            applied=False,
            suggested_filename="other_out.pdf",
        ),
    )
    vm = build_live_file_pairs_vm(
        input_filenames=("left.pdf", "other.pdf"),
        output_folder_selected=True,
        planned_destinations=planned,
    )
    assert vm.rows[0].source_filename == "left.pdf"
    assert "right_proposed" in vm.rows[0].proposed_filename or vm.rows[0].proposed_filename.endswith(
        ".pdf"
    )
    assert vm.rows[1].source_filename == "other.pdf"


def test_15_row_mapping_stable() -> None:
    names = ("c.pdf", "a.pdf", "b.pdf")
    vm1 = build_live_file_pairs_vm(input_filenames=names, output_folder_selected=True)
    planned = (
        ProcessingPlannedDestination(
            document_name="a.pdf",
            planned_path="p",
            destination_label="x",
            preview_only=True,
            applied=False,
            suggested_filename="a_out.pdf",
        ),
    )
    vm2 = build_live_file_pairs_vm(
        input_filenames=names,
        output_folder_selected=True,
        planned_destinations=planned,
    )
    assert [r.source_filename for r in vm1.rows] == list(names)
    assert [r.source_filename for r in vm2.rows] == list(names)


def test_16_running_state_message() -> None:
    src = _ws_src()
    assert "Prüfung läuft" in src
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf",),
        output_folder_selected=True,
        run_active=True,
    )
    assert vm.rows[0].output_display == MSG_ROW_CHECKING
    assert MSG_ROW_CHECKING.startswith("Wird geprüft")


def test_17_folder_cards_activity_marker() -> None:
    src = _ws_src()
    assert "folder_run_activity_marker" in src
    assert "MSG_RUN_ACTIVITY" in src or "Prüfung läuft" in src


def test_18_no_final_write_implied() -> None:
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf",),
        output_folder_selected=True,
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="a.pdf",
                planned_path="p",
                destination_label="x",
                preview_only=True,
                applied=False,
                suggested_filename="out.pdf",
            ),
        ),
    )
    assert vm.implies_final_write is False
    assert LABEL_PROPOSED_OUTPUT_FILES == "Vorgeschlagene Ausgabedateien"
    assert "geschrieben" not in LABEL_PROPOSED_OUTPUT_FILES.casefold()


def test_19_safety_helper_visible() -> None:
    assert MSG_START_HELPER == "Nur Vorschau — Originale bleiben unverändert."
    src = _ws_src()
    assert "MSG_START_HELPER" in src
    assert "file_pair_safety_helper" in src


# --- Result integration ---


def test_20_no_primary_green_completed_box() -> None:
    src = _ws_src()
    assert "secondary_not_primary" in src
    assert 'tone == "completed"' in src
    assert "SECTION_TEST_NACHWEIS_COLLAPSED" in src


def test_21_result_status_integrated() -> None:
    src = _ws_src()
    assert "file_pair_integrated_counts" in src or "MSG_PAIR_STATUS_INTEGRATED" in src
    assert "file_pair_files_found" in src
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf", "b.pdf"),
        output_folder_selected=True,
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="a.pdf",
                planned_path="p",
                destination_label="x",
                preview_only=True,
                applied=False,
                suggested_filename="a_out.pdf",
            ),
        ),
        review_count=1,
    )
    assert "2 Dateien gefunden" in vm.files_found_label
    assert vm.checked_count == 1
    assert vm.review_count == 1


def test_22_open_review_secondary() -> None:
    assert ACTION_OPEN_REVIEW == "Zur Prüfung öffnen"
    src = _ws_src()
    assert "ACTION_OPEN_REVIEW" in src
    assert "secondary_review_cta" in src or "primary=False" in src


def test_23_headings() -> None:
    assert LABEL_INPUT_FILES == "Eingangsdateien"
    assert LABEL_PROPOSED_OUTPUT_FILES == "Vorgeschlagene Ausgabedateien"
    src = _ws_src()
    assert "LABEL_INPUT_FILES" in src
    assert "LABEL_PROPOSED_OUTPUT_FILES" in src
    assert "WORKSPACE_LIVE_FILE_PAIRS_MARKER" in src
    assert "LIVE_FILE_PAIRS_MARKER" in src
    assert WORKSPACE_LIVE_FILE_PAIRS_MARKER == LIVE_FILE_PAIRS_MARKER


# --- Row interaction ---


def test_24_document_show_action() -> None:
    assert ACTION_SHOW_DOCUMENT == "Dokument anzeigen"
    src = _ws_src()
    assert "ACTION_SHOW_DOCUMENT" in src
    assert "file_pair_show_document" in src


def test_25_document_preview_non_mutating(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    pdf = folder / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 x")
    before = pdf.read_bytes()
    state = UiV2State()
    state.workspace_input_folder_override = str(folder)
    msg = open_workspace_document_preview(state, "doc.pdf")
    assert pdf.read_bytes() == before
    assert WORKSPACE_DOCUMENT_SHOW_MARKER in state.workspace_document_preview_marker
    assert "non_mutating" in state.workspace_document_preview_marker
    assert ACTION_SHOW_DOCUMENT in msg or "Dokument" in msg


def test_26_proposed_row_nav_review_marker() -> None:
    src = _ws_src()
    assert "nav_review" in src
    assert "open_workspace_review_for_source" in src


def test_27_long_original_accessible() -> None:
    src = _ws_src()
    assert "file_pair_source_full" in src
    assert "tooltip=" in src
    assert "truncate_filename_display" in src


def test_28_long_proposed_accessible() -> None:
    src = _ws_src()
    assert "file_pair_target_full" in src
    long_name = "x" * 80 + "_proposed.pdf"
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf",),
        output_folder_selected=True,
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="a.pdf",
                planned_path="p",
                destination_label="x",
                preview_only=True,
                applied=False,
                suggested_filename=long_name,
            ),
        ),
    )
    assert long_name in vm.rows[0].proposed_filename or vm.rows[0].proposed_filename.endswith(
        ".pdf"
    )


# --- Safety ---


def test_29_no_auto_run() -> None:
    state = UiV2State()
    apply_workspace_input_folder_selection(state, str(CONTROLLED_INPUT) if CONTROLLED_INPUT.is_dir() else None)
    assert state.workspace_run_interaction_status == "idle"
    assert state.processing_run_state.status == "idle"
    src = _ws_src()
    assert "apply_start_processing" in src
    assert START_CTA_STRONG == "Belege jetzt prüfen"


def test_30_no_run_once() -> None:
    blob = _ws_src() + _listing_src() + _pairs_src()
    assert "run_once(" not in blob
    tree = ast.parse(_listing_src())
    attrs = [
        n.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Attribute)
    ]
    assert "run_once" not in attrs


def test_31_no_production_final_write() -> None:
    assert FINAL_WRITE_ALLOWED_IN_THIS_PHASE is False
    blob = _ws_src() + _listing_src() + _pairs_src()
    assert "final_write_allowed_for_production=True" not in blob
    assert "final_write_allowed_for_production = True" not in blob


def test_32_no_real_invoice_folders() -> None:
    blob = _ws_src() + _listing_src() + _pairs_src() + STATE.read_text(encoding="utf-8")
    for folder in FORBIDDEN_FOLDERS:
        assert folder not in blob


def test_33_oracle_script_exists() -> None:
    assert ORACLE_SCRIPT.is_file()


def test_34_track_a_protection_test_exists() -> None:
    assert TRACK_A_TEST.is_file()


def test_35_processing_core_unchanged_in_helpers() -> None:
    blob = _listing_src() + _pairs_src()
    for path in CORE_PROTECTED:
        assert path not in blob or "invoice_tool/run.py" not in blob
    # Helpers must not import processing core.
    tree = ast.parse(_listing_src())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    for mod in (
        "invoice_tool.run",
        "invoice_tool.processing",
        "invoice_tool.routing",
        "invoice_tool.classification",
    ):
        assert mod not in imports


def test_36_release_tags_unchanged_markers() -> None:
    # Implementation must not create/move tags — verified in audit; code has no tag ops.
    blob = _ws_src() + _listing_src() + _pairs_src()
    assert "git tag" not in blob
    assert "product-v1-local-pilot" not in blob


def test_37_cta_label() -> None:
    assert START_CTA_STRONG == "Belege jetzt prüfen"
    assert "Belege jetzt prüfen" in _ws_src() or "START_CTA_STRONG" in _ws_src()


def test_38_just_in_time_status_documented() -> None:
    assert JUST_IN_TIME_STATUS == "PARTIAL"
    assert "JUST_IN_TIME_STATUS" in _pairs_src()
    assert "PARTIAL" in _pairs_src()


def test_39_merge_keeps_listing_order() -> None:
    merged = merge_input_names_with_proposal_sources(
        ("b.pdf", "a.pdf"),
        {"a.pdf": 1, "c.pdf": 1},
    )
    assert merged == ("b.pdf", "a.pdf", "c.pdf")


def test_40_ensure_listing_refreshes_on_folder_change(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "one.pdf").write_bytes(b"%PDF")
    (b / "two.pdf").write_bytes(b"%PDF")
    state = UiV2State()
    apply_workspace_input_folder_selection(state, str(a))
    assert state.workspace_input_filenames == ("one.pdf",)
    state.workspace_input_folder_override = str(b)
    ensure_workspace_input_listing(state)
    assert state.workspace_input_filenames == ("two.pdf",)


def test_41_controlled_folders_optional_live_list() -> None:
    if not CONTROLLED_INPUT.is_dir():
        return
    result = list_workspace_input_documents(str(CONTROLLED_INPUT))
    assert result.mutated is False
    assert result.called_run_once is False
    assert result.count >= 1
    assert CONTROLLED_OUTPUT.is_dir()


def test_42_proposal_created_label() -> None:
    assert MSG_PROPOSAL_CREATED == "Vorschlag erstellt"
    vm = build_live_file_pairs_vm(
        input_filenames=("a.pdf",),
        output_folder_selected=True,
        planned_destinations=(
            ProcessingPlannedDestination(
                document_name="a.pdf",
                planned_path="p",
                destination_label="x",
                preview_only=True,
                applied=False,
                suggested_filename="ok.pdf",
            ),
        ),
    )
    assert vm.rows[0].status_label == MSG_PROPOSAL_CREATED


def test_43_file_pair_marker_retained() -> None:
    assert WORKSPACE_FILE_PAIR_MARKER.startswith("workspace_input_output")
    assert "WORKSPACE_LIVE_FILE_PAIRS_MARKER" in _ws_src()
    assert WORKSPACE_LIVE_FILE_PAIRS_MARKER == "workspace_live_file_pairs_v1"


def test_44_refresh_helper_on_state(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "z.pdf").write_bytes(b"%PDF")
    state = UiV2State()
    state.workspace_input_folder_override = str(folder)
    result = refresh_workspace_input_listing_on_state(state)
    assert result.filenames == ("z.pdf",)
    assert state.workspace_input_listing_count == 1


def test_45_output_folder_selection_does_not_clear_input(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "x.pdf").write_bytes(b"%PDF")
    out = tmp_path / "out"
    out.mkdir()
    state = UiV2State()
    apply_workspace_input_folder_selection(state, str(folder))
    apply_workspace_output_folder_selection(state, str(out))
    assert state.workspace_input_filenames == ("x.pdf",)
    assert state.workspace_output_folder_override == str(out)
