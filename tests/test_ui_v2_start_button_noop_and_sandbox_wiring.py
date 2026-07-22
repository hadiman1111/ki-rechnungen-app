"""Track-B start-button no-op diagnosis — visible CTA feedback + sandbox wiring."""

from __future__ import annotations

import ast
import dataclasses
import importlib
import sys
from pathlib import Path

from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.pages.workspace import (
    MSG_SANDBOX_BLOCKED_CORE_BRIDGE,
    MSG_SANDBOX_BLOCKED_FOLDERS,
    MSG_SANDBOX_BLOCKED_PRODUCTIVE,
    MSG_SANDBOX_BRIDGE_NOT_CONNECTED,
    MSG_SANDBOX_NO_ORIGINALS_USED,
    MSG_SANDBOX_RESULTS_AFTER_SUCCESS,
    START_CTA_LABEL,
    apply_start_processing,
    build_processing_run_request,
    build_start_button_feedback,
    derive_sandbox_root_from_folders,
    prepare_sandbox_intent_for_cta,
)
from invoice_tool.ui_v2.processing_contract import NotYetConnectedProcessingService
from invoice_tool.ui_v2.processing_state import (
    ProcessingRunState,
    blocked_processing_state,
    not_configured_processing_state,
)
from invoice_tool.ui_v2.sandbox_execution_boundary import (
    MSG_SANDBOX_RUNNER_UNBOUND,
    SandboxCoreCallArgs,
    SandboxCoreCallResult,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.view_models import (
    ConfigurationsPageVM,
    ProfileDetailVM,
    ReviewSummaryVM,
    RunSummaryVM,
    UiV2ReadOnlySnapshot,
    WorkspaceSummaryVM,
)

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
APP = ROOT / "invoice_tool" / "ui_v2" / "app.py"

FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.run",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
)


def _minimal_snapshot() -> UiV2ReadOnlySnapshot:
    profile = ProfileDetailVM(
        profile_id="profile-a",
        profile_name="Pilot",
        scan_model_id="local",
        scan_model_name="local",
        feature_summary="",
        configuration_count=0,
        active_configuration_count=0,
        unmatched_configured=False,
        unmatched_destination_missing=False,
        profiles=tuple(),
        warnings=tuple(),
    )
    workspace = WorkspaceSummaryVM(
        input_folder_summary="nicht gewählt",
        input_folder_state="not_configured",
        input_file_count=None,
        latest_run=RunSummaryVM(availability="no_run"),
        result_count=None,
        review_count=None,
        destination_count=0,
        missing_destination_count=0,
        destinations=tuple(),
        results=tuple(),
        warnings=tuple(),
    )
    configurations = ConfigurationsPageVM(
        profile_name="Pilot",
        configurations=tuple(),
        unmatched=None,
        total_count=0,
        active_count=0,
        missing_destination_count=0,
        unmatched_present=False,
        warnings=tuple(),
    )
    review = ReviewSummaryVM(
        availability="no_run",
        review_count=None,
        items=tuple(),
        warnings=tuple(),
    )
    return UiV2ReadOnlySnapshot(
        profile=profile,
        configurations=configurations,
        workspace=workspace,
        review=review,
        warnings=tuple(),
    )


def _state_with_adapter(**kwargs) -> UiV2State:
    return UiV2State(processing_service=LocalProcessingAdapter(), **kwargs)


def test_start_cta_label_is_sandbox_honest() -> None:
    assert "Sandbox" in START_CTA_LABEL
    assert "starten" in START_CTA_LABEL.lower()


def test_workspace_start_handler_has_on_click_wiring_in_source() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "on_start=start_processing" in src
    assert "_schedule_start_processing" in src
    assert "apply_start_processing" in src
    assert "workspace_start_feedback" in src
    assert "summary_alert(start_feedback)" in src


def test_app_injects_local_processing_adapter() -> None:
    src = APP.read_text(encoding="utf-8")
    assert "make_local_processing_adapter" in src
    assert "processing_service=make_local_processing_adapter()" in src


def test_click_start_without_folders_shows_visible_blocked_reason() -> None:
    state = _state_with_adapter()
    before = state.processing_run_state.status
    result = apply_start_processing(state, profile_id="profile-a")
    assert before == "idle"
    assert result.status in {"not_configured", "blocked"}
    assert state.workspace_start_feedback
    assert MSG_SANDBOX_BLOCKED_FOLDERS in state.workspace_start_feedback
    assert MSG_SANDBOX_NO_ORIGINALS_USED in state.workspace_start_feedback
    assert state.processing_run_state.message == state.workspace_start_feedback


def test_click_start_missing_output_shows_visible_blocked_reason() -> None:
    state = _state_with_adapter()
    state.workspace_input_folder_override = "/tmp/ui-v2-sandbox/copied-inbox"
    state.workspace_input_folder_source = "explicit_user_selection"
    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status == "not_configured"
    assert MSG_SANDBOX_BLOCKED_FOLDERS in state.workspace_start_feedback
    assert "Ausgabeordner" in state.workspace_start_feedback or "ausgang" in (
        state.workspace_start_feedback.lower()
    )


def test_click_start_missing_input_shows_visible_blocked_reason() -> None:
    state = _state_with_adapter()
    state.workspace_output_folder_override = "/tmp/ui-v2-sandbox/copied-outbox"
    state.workspace_output_folder_source = "explicit_user_selection"
    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status == "not_configured"
    assert MSG_SANDBOX_BLOCKED_FOLDERS in state.workspace_start_feedback


def test_click_start_missing_configuration_shows_visible_blocked_reason() -> None:
    state = _state_with_adapter()
    state.workspace_input_folder_override = "/tmp/ui-v2-sandbox/copied-inbox"
    state.workspace_output_folder_override = "/tmp/ui-v2-sandbox/copied-outbox"
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status == "not_configured"
    feedback = state.workspace_start_feedback
    assert feedback
    assert "Konfiguration" in feedback or "Profil" in feedback or "Sandbox-Lauf blockiert" in feedback
    assert MSG_SANDBOX_RESULTS_AFTER_SUCCESS in feedback


def test_productive_execution_remains_blocked() -> None:
    state = _state_with_adapter()
    state.workspace_input_folder_override = "/tmp/ui-v2-sandbox/copied-inbox"
    state.workspace_output_folder_override = "/tmp/ui-v2-sandbox/copied-outbox"
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"
    prepare_sandbox_intent_for_cta(state)
    request = build_processing_run_request(
        state,
        profile_id="profile-a",
        configuration_id="config-a",
        user_confirmed_start=True,
    )
    # Force productive request — adapter must refuse.
    productive = dataclasses.replace(
        request,
        dry_run=False,
        productive_execution_allowed=True,
        execution_scope="productive",
    )
    started = state.processing_service.start_run(productive)
    assert started.status == "blocked"
    feedback = build_start_button_feedback(started)
    assert MSG_SANDBOX_BLOCKED_PRODUCTIVE in feedback


def test_core_bridge_unavailable_shows_visible_blocked_not_noop(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)

    state = _state_with_adapter()
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"

    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status in {"failed", "blocked"}
    feedback = state.workspace_start_feedback
    assert feedback
    assert MSG_SANDBOX_BRIDGE_NOT_CONNECTED in feedback or MSG_SANDBOX_BLOCKED_CORE_BRIDGE in feedback
    assert MSG_SANDBOX_NO_ORIGINALS_USED in feedback
    assert MSG_SANDBOX_RESULTS_AFTER_SUCCESS in feedback
    # Default runner is unbound — core bridge required for real OCR/AI.
    if result.status == "failed":
        assert "sandbox_core_runner_unbound" in result.errors or MSG_SANDBOX_RUNNER_UNBOUND in (
            result.message + " ".join(result.errors)
        )


def test_sandbox_stub_path_produces_run_state_and_result_display(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)

    def stub(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        assert str(sandbox) in args.input_folder
        assert str(sandbox) in args.output_folder
        return SandboxCoreCallResult(
            ok=True,
            message="stub sandbox ok",
            run_id="stub-run-1",
            results=tuple(),
            review_items=tuple(),
            errors=tuple(),
        )

    state = UiV2State(processing_service=LocalProcessingAdapter(sandbox_runner=stub))
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"

    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status == "completed"
    assert state.processing_run_state.status == "completed"
    assert state.workspace_start_feedback
    assert MSG_SANDBOX_NO_ORIGINALS_USED in state.workspace_start_feedback
    assert state.workspace_sandbox_mode is True
    assert state.workspace_copied_data_confirmed is True
    assert state.workspace_sandbox_root is not None


def test_result_panel_refreshes_after_run_state_update() -> None:
    from invoice_tool.ui_v2.pages.workspace import (
        build_workspace_readiness_display_vm,
        build_workspace_run_result_shell,
        workspace_honesty_copy,
    )

    state = _state_with_adapter()
    state.snapshot = _minimal_snapshot()
    refreshed: list[str] = []

    def _refresh() -> None:
        # Mimic app refresh: re-read run shell / readiness from updated state.
        shell = build_workspace_run_result_shell(state)
        readiness = build_workspace_readiness_display_vm(state)
        honesty = workspace_honesty_copy(
            has_real_results=False,
            processing_state=state.processing_run_state,
        )
        refreshed.append(
            f"{shell.message}|{readiness.run_message}|{honesty.status_line}|"
            f"{state.workspace_start_feedback}"
        )

    state.refresh = _refresh
    apply_start_processing(state, profile_id="profile-a")
    assert state.refresh is _refresh
    state.refresh()
    assert refreshed
    blob = refreshed[0]
    assert state.workspace_start_feedback
    assert "Sandbox-Lauf blockiert" in blob or state.workspace_start_feedback[:32] in blob
    assert state.processing_run_state.status != "idle"


def test_errors_shown_in_ui_state_not_only_terminal() -> None:
    state = _state_with_adapter()
    result = apply_start_processing(state)
    assert state.processing_run_state.message
    assert state.workspace_start_feedback
    assert state.processing_run_state.status != "idle"


def test_no_original_folder_path_passed_to_execution(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    original = tmp_path / "original-never-used"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    original.mkdir()
    seen: list[SandboxCoreCallArgs] = []

    def stub(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        seen.append(args)
        return SandboxCoreCallResult(ok=True, message="ok", run_id="r1")

    state = UiV2State(processing_service=LocalProcessingAdapter(sandbox_runner=stub))
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_original_source_folder = str(original)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"
    apply_start_processing(state, profile_id="profile-a")
    assert seen
    assert seen[0].input_folder != str(original)
    assert seen[0].output_folder != str(original)
    assert str(original) not in seen[0].input_folder
    assert str(original) not in seen[0].output_folder


def test_no_processing_core_import_introduced() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    state = _state_with_adapter()
    apply_start_processing(state, profile_id="profile-a")
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in FORBIDDEN_CORE:
        assert forbidden not in newly, forbidden

    tree = ast.parse(WORKSPACE.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for name in imported:
        assert not any(name == f or name.startswith(f + ".") for f in FORBIDDEN_CORE), name


def test_derive_sandbox_root_from_sibling_folders() -> None:
    root = derive_sandbox_root_from_folders(
        "/tmp/ui-v2-sandbox/copied-inbox",
        "/tmp/ui-v2-sandbox/copied-outbox",
    )
    assert root == "/tmp/ui-v2-sandbox"


def test_not_yet_connected_still_shows_visible_feedback() -> None:
    state = UiV2State(processing_service=NotYetConnectedProcessingService())
    state.workspace_input_folder_override = "/tmp/ui-v2-sandbox/copied-inbox"
    state.workspace_input_folder_source = "explicit_user_selection"
    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status in {"blocked", "not_configured"}
    assert state.workspace_start_feedback
    assert "Sandbox-Lauf blockiert" in state.workspace_start_feedback
    assert MSG_SANDBOX_NO_ORIGINALS_USED in state.workspace_start_feedback
    assert MSG_SANDBOX_RESULTS_AFTER_SUCCESS in state.workspace_start_feedback


def test_feedback_builder_covers_blocked_states() -> None:
    blocked = build_start_button_feedback(blocked_processing_state())
    assert MSG_SANDBOX_BRIDGE_NOT_CONNECTED in blocked
    missing = build_start_button_feedback(
        not_configured_processing_state("Eingangsordner fehlt. Bitte einen Ordner explizit wählen.")
    )
    assert MSG_SANDBOX_BLOCKED_FOLDERS in missing
    failed = build_start_button_feedback(
        ProcessingRunState(
            status="failed",
            message=MSG_SANDBOX_RUNNER_UNBOUND,
            errors=("sandbox_core_runner_unbound",),
            execution_gate="ready_for_sandbox_execution",
        )
    )
    assert MSG_SANDBOX_BLOCKED_CORE_BRIDGE in failed


def test_module_reload_stays_core_free() -> None:
    before = set(sys.modules)
    importlib.reload(importlib.import_module("invoice_tool.ui_v2.pages.workspace"))
    after = set(sys.modules)
    newly = after - before
    for forbidden in FORBIDDEN_CORE:
        assert forbidden not in newly
