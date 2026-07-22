"""Track-B UI-v2 workspace folder selection state — non-GUI, no PDF processing."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.local_processing_adapter import (
    MSG_MISSING_INPUT,
    MSG_MISSING_OUTPUT,
    LocalProcessingAdapter,
)
from invoice_tool.ui_v2.pages.workspace import (
    EMPTY_INPUT_FOLDER_TEXT,
    EMPTY_OUTPUT_FOLDER_TEXT,
    PICK_INPUT_FOLDER_LABEL,
    PICK_OUTPUT_FOLDER_LABEL,
    apply_start_processing,
    apply_workspace_input_folder_selection,
    apply_workspace_output_folder_selection,
    build_processing_run_request,
    build_workspace_folder_selection_vm,
    workspace_honesty_copy,
)
from invoice_tool.ui_v2.processing_contract import (
    SOURCE_EXPLICIT_USER_SELECTION,
    SOURCE_UNSET,
)
from invoice_tool.ui_v2.sandbox_processing_gate import (
    MSG_BLOCKED_MISSING_SANDBOX,
    MSG_SANDBOX_CORE_DRY_ABSENT,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"

PRIVATE_MARKERS = (
    "AMEX",
    "Privat",
    "SOMAA",
    "Hadi",
    "Bismarck",
    "voba",
    "/Users/",
    "Desktop/Programm Belegerfassung",
    "TEST Rechnungen",
)


def test_default_input_and_output_folder_are_empty() -> None:
    state = UiV2State()
    assert state.workspace_input_folder_override is None
    assert state.workspace_output_folder_override is None
    assert state.workspace_input_folder_source == SOURCE_UNSET
    assert state.workspace_output_folder_source == SOURCE_UNSET
    assert state.has_explicit_workspace_folder_selection() is False
    vm = build_workspace_folder_selection_vm(state)
    assert vm.input_folder is None
    assert vm.output_folder is None
    assert vm.input_folder_display is None
    assert vm.output_folder_display is None


def test_no_private_or_desktop_defaults_in_folder_state() -> None:
    state = UiV2State()
    request = build_processing_run_request(state)
    blob = " ".join(
        filter(
            None,
            (
                state.workspace_input_folder_override,
                state.workspace_output_folder_override,
                request.input_folder,
                request.output_folder,
            ),
        )
    )
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
        assert marker not in (state.workspace_input_folder_source or "")
        assert marker not in (state.workspace_output_folder_source or "")


def test_ui_text_honestly_says_no_folders_selected() -> None:
    vm = build_workspace_folder_selection_vm(UiV2State())
    assert vm.input_empty_text == EMPTY_INPUT_FOLDER_TEXT
    assert vm.output_empty_text == EMPTY_OUTPUT_FOLDER_TEXT
    assert "Kein Eingangsordner gewählt" in vm.input_empty_text
    assert "Kein Ausgabeordner gewählt" in vm.output_empty_text
    assert vm.input_pick_label == PICK_INPUT_FOLDER_LABEL
    assert vm.output_pick_label == PICK_OUTPUT_FOLDER_LABEL


def test_explicit_selection_updates_state_and_source_markers() -> None:
    state = UiV2State()
    apply_workspace_input_folder_selection(state, "  selected-inbox  ")
    apply_workspace_output_folder_selection(state, "selected-outbox")
    assert state.workspace_input_folder_override == "selected-inbox"
    assert state.workspace_output_folder_override == "selected-outbox"
    assert state.workspace_input_folder_source == SOURCE_EXPLICIT_USER_SELECTION
    assert state.workspace_output_folder_source == SOURCE_EXPLICIT_USER_SELECTION
    vm = build_workspace_folder_selection_vm(state)
    assert vm.input_folder == "selected-inbox"
    assert vm.output_folder == "selected-outbox"
    assert vm.input_source == SOURCE_EXPLICIT_USER_SELECTION
    assert vm.output_source == SOURCE_EXPLICIT_USER_SELECTION
    assert vm.input_folder_display is not None
    assert vm.output_folder_display is not None


def test_folder_selection_does_not_create_folders_or_touch_fs(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox-not-created"
    outbox = tmp_path / "outbox-not-created"
    assert not inbox.exists()
    assert not outbox.exists()
    state = UiV2State()
    apply_workspace_input_folder_selection(state, str(inbox))
    apply_workspace_output_folder_selection(state, str(outbox))
    request = build_processing_run_request(state)
    assert request.input_folder == str(inbox)
    assert request.output_folder == str(outbox)
    assert not inbox.exists()
    assert not outbox.exists()
    assert list(tmp_path.iterdir()) == []


def test_folder_selection_does_not_process_pdfs(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    before = pdf.read_bytes()
    listing_before = sorted(p.name for p in tmp_path.iterdir())
    state = UiV2State(processing_service=LocalProcessingAdapter())
    apply_workspace_input_folder_selection(state, str(tmp_path))
    apply_workspace_output_folder_selection(state, str(tmp_path / "out"))
    request = build_processing_run_request(
        state,
        profile_id="profile-a",
        configuration_id="config-a",
        user_confirmed_start=True,
    )
    started = state.processing_service.start_run(request)
    assert started.status == "blocked"
    assert MSG_BLOCKED_MISSING_SANDBOX in started.message
    assert MSG_SANDBOX_CORE_DRY_ABSENT not in started.message
    assert started.core_dry_run_status == "dry_run_available"
    assert pdf.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == listing_before


def test_request_builder_uses_only_explicit_folder_state() -> None:
    state = UiV2State()
    empty = build_processing_run_request(state)
    assert empty.input_folder is None
    assert empty.output_folder is None
    assert empty.source == SOURCE_UNSET

    apply_workspace_input_folder_selection(state, "explicit-in")
    apply_workspace_output_folder_selection(state, "explicit-out")
    filled = build_processing_run_request(state)
    assert filled.input_folder == "explicit-in"
    assert filled.output_folder == "explicit-out"
    assert filled.source == SOURCE_EXPLICIT_USER_SELECTION
    for marker in PRIVATE_MARKERS:
        assert marker not in (filled.input_folder or "")
        assert marker not in (filled.output_folder or "")


def test_missing_input_folder_blocks_adapter() -> None:
    state = UiV2State(processing_service=LocalProcessingAdapter())
    apply_workspace_output_folder_selection(state, "explicit-out")
    request = build_processing_run_request(
        state,
        profile_id="profile-a",
        configuration_id="config-a",
    )
    assert request.input_folder is None
    validated = state.processing_service.validate_request(request)
    assert validated.status == "not_configured"
    assert MSG_MISSING_INPUT in validated.message
    copy = workspace_honesty_copy(has_real_results=False, processing_state=validated)
    assert MSG_MISSING_INPUT in (copy.status_line or "")


def test_missing_output_folder_blocks_adapter() -> None:
    state = UiV2State(processing_service=LocalProcessingAdapter())
    apply_workspace_input_folder_selection(state, "explicit-in")
    request = build_processing_run_request(
        state,
        profile_id="profile-a",
        configuration_id="config-a",
    )
    assert request.output_folder is None
    validated = state.processing_service.validate_request(request)
    assert validated.status == "not_configured"
    assert MSG_MISSING_OUTPUT in validated.message
    copy = workspace_honesty_copy(has_real_results=False, processing_state=validated)
    assert MSG_MISSING_OUTPUT in (copy.status_line or "")


def test_explicit_test_folder_strings_do_not_touch_filesystem(tmp_path: Path) -> None:
    # Synthetic path strings only — directories intentionally absent.
    in_path = str(tmp_path / "synthetic-in")
    out_path = str(tmp_path / "synthetic-out")
    state = UiV2State()
    apply_workspace_input_folder_selection(state, in_path)
    apply_workspace_output_folder_selection(state, out_path)
    request = build_processing_run_request(state)
    assert request.input_folder == in_path
    assert request.output_folder == out_path
    assert not Path(in_path).exists()
    assert not Path(out_path).exists()


def test_cta_remains_blocked_by_sandbox_gate() -> None:
    state = UiV2State(processing_service=LocalProcessingAdapter())
    apply_workspace_input_folder_selection(state, "explicit-in")
    apply_workspace_output_folder_selection(state, "explicit-out")
    # Provide profile/config so sandbox-gate (not missing folders) is the blocker.
    request = build_processing_run_request(
        state,
        profile_id="profile-a",
        configuration_id="config-a",
        user_confirmed_start=True,
    )
    started = state.processing_service.start_run(request)
    assert started.status == "blocked"
    assert MSG_BLOCKED_MISSING_SANDBOX in started.message
    assert MSG_SANDBOX_CORE_DRY_ABSENT not in started.message
    assert started.execution_gate == "blocked_missing_sandbox"
    assert started.core_dry_run_status == "dry_run_available"
    assert started.results == tuple()
    # Workspace CTA path also stays non-productive without sandbox root/copy flags.
    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status in {"blocked", "not_configured", "failed"}
    assert result.results == tuple()


def test_native_folder_picker_is_wired_to_state_only() -> None:
    vm = build_workspace_folder_selection_vm(UiV2State())
    assert vm.picker_wired is True
    workspace_src = WORKSPACE.read_text(encoding="utf-8")
    assert "choose_target_folder" in workspace_src
    assert "apply_workspace_input_folder_selection" in workspace_src
    assert "apply_workspace_output_folder_selection" in workspace_src
    # Picker path must not process PDFs or invent private defaults.
    assert "list_input_pdf" not in workspace_src
    assert "run_once" not in workspace_src


def test_clear_folder_selection_resets_sources() -> None:
    state = UiV2State()
    apply_workspace_input_folder_selection(state, "in")
    apply_workspace_output_folder_selection(state, "out")
    state.clear_workspace_folder_selection()
    assert state.workspace_input_folder_override is None
    assert state.workspace_output_folder_override is None
    assert state.workspace_input_folder_source == SOURCE_UNSET
    assert state.workspace_output_folder_source == SOURCE_UNSET


def test_folder_selection_sources_have_no_private_defaults() -> None:
    # Folder-selection defaults must not invent private/local paths.
    state = UiV2State()
    vm = build_workspace_folder_selection_vm(state)
    request = build_processing_run_request(state)
    blob = " ".join(
        filter(
            None,
            (
                vm.input_folder,
                vm.output_folder,
                vm.input_folder_display,
                vm.output_folder_display,
                request.input_folder,
                request.output_folder,
                EMPTY_INPUT_FOLDER_TEXT,
                EMPTY_OUTPUT_FOLDER_TEXT,
            ),
        )
    )
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    # Workspace folder UX module must not hardcode private path defaults.
    workspace_src = WORKSPACE.read_text(encoding="utf-8")
    for marker in ("/Users/", "Desktop/Programm", "TEST Rechnungen"):
        assert marker not in workspace_src, marker


def test_workspace_folder_selection_ast_stays_core_free() -> None:
    tree = ast.parse(WORKSPACE.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = (
        "invoice_tool.processing",
        "invoice_tool.run",
        "invoice_tool.routing",
        "invoice_tool.classification",
        "app_main",
    )
    for name in imported:
        assert not any(name == f or name.startswith(f + ".") for f in forbidden), name
