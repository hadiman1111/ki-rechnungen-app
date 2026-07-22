"""Track-B UI-v2 workspace configuration selection + compact blocked details."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.pages.workspace import (
    MAX_BLOCKED_DETAIL_LINES,
    MSG_DETAIL_CORE_BRIDGE,
    MSG_DETAIL_EXPORT_DRAFT,
    MSG_DETAIL_PRODUCTIVE_LOCKED,
    MSG_SANDBOX_BRIDGE_NOT_CONNECTED,
    MSG_SANDBOX_NO_ORIGINALS_USED,
    RUN_SETUP_SECTION_LABEL,
    apply_start_processing,
    build_processing_run_request,
    build_start_interaction_feedback,
    resolve_workspace_configuration_selection_for_state,
)
from invoice_tool.ui_v2.processing_state import ProcessingRunState
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.view_models import (
    ConfigurationSummaryVM,
    ConfigurationsPageVM,
    ProfileDetailVM,
    ReviewSummaryVM,
    RunSummaryVM,
    UiV2ReadOnlySnapshot,
    WorkspaceSummaryVM,
)
from invoice_tool.ui_v2.workspace_configuration_selection import (
    MSG_CONFIGURATION_CHANGE_HINT,
    MSG_NO_ACTIVE_CONFIGURATION,
    MSG_PROFILE_MISSING,
    build_compact_blocked_details,
    build_workspace_configuration_options,
    resolve_workspace_configuration_selection,
    select_default_workspace_configuration,
)

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
SELECTION = ROOT / "invoice_tool" / "ui_v2" / "workspace_configuration_selection.py"

FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.run",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
)

LONG_WALL_MARKERS = (
    "Dies ist ein Sandbox-Lauf",
    "Sandbox-Modus: vorbereitet",
    "Verarbeitung ist nur im expliziten Sandbox-Modus",
    "Core-Dry-Run ist noch nicht vorhanden",
    "Nächster technischer Schritt: sichere Core-Bridge",
    "Ergebnisse erscheinen hier nach einem erfolgreichen Sandbox-Lauf",
)


def _config(
    config_id: str,
    name: str,
    *,
    active: bool = True,
    sort_index: int = 0,
) -> ConfigurationSummaryVM:
    return ConfigurationSummaryVM(
        configuration_id=config_id,
        name=name,
        active=active,
        matching_summary="",
        filename_pattern_summary="",
        filename_example=None,
        destination_summary="—",
        destination_missing=False,
        sort_index=sort_index,
    )


def _snapshot(
    *,
    profile_id: str = "profile-a",
    profile_name: str = "Pilot",
    configurations: tuple[ConfigurationSummaryVM, ...] = (),
    unmatched: ConfigurationSummaryVM | None = None,
) -> UiV2ReadOnlySnapshot:
    active_count = sum(1 for item in configurations if item.active)
    profile = ProfileDetailVM(
        profile_id=profile_id,
        profile_name=profile_name,
        scan_model_id="local",
        scan_model_name="local",
        feature_summary="",
        configuration_count=len(configurations),
        active_configuration_count=active_count,
        unmatched_configured=unmatched is not None,
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
    configurations_page = ConfigurationsPageVM(
        profile_name=profile_name,
        configurations=configurations,
        unmatched=unmatched,
        total_count=len(configurations),
        active_count=active_count,
        missing_destination_count=0,
        unmatched_present=unmatched is not None,
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
        configurations=configurations_page,
        workspace=workspace,
        review=review,
        warnings=tuple(),
    )


def _state_with_adapter(**kwargs) -> UiV2State:
    return UiV2State(processing_service=LocalProcessingAdapter(), **kwargs)


def test_resolves_single_active_configuration_automatically() -> None:
    selection = resolve_workspace_configuration_selection(
        profile_id="profile-a",
        profile_name="Pilot",
        configurations=(_config("cfg-1", "Regel A", sort_index=0),),
    )
    assert selection.is_ready
    assert selection.resolution == "auto_single"
    assert selection.selected_configuration_id == "cfg-1"
    assert selection.selected_configuration_name == "Regel A"
    assert selection.blocker_message is None


def test_resolves_stable_default_when_multiple_active_configurations() -> None:
    selection = resolve_workspace_configuration_selection(
        profile_id="profile-a",
        configurations=(
            _config("cfg-b", "Beta", sort_index=1),
            _config("cfg-a", "Alpha", sort_index=0),
            _config("cfg-inactive", "Idle", active=False, sort_index=2),
        ),
    )
    assert selection.is_ready
    assert selection.resolution == "default_multiple"
    assert selection.selected_configuration_id == "cfg-a"
    assert selection.configuration_display == "Alpha"
    assert MSG_CONFIGURATION_CHANGE_HINT in selection.summary_lines


def test_unmatched_is_not_auto_selected() -> None:
    unmatched = _config("unmatched", "Nicht zugeordnet", sort_index=99)
    options = build_workspace_configuration_options(
        (_config("cfg-1", "Regel A"),),
        unmatched=unmatched,
    )
    default = select_default_workspace_configuration(options)
    assert default is not None
    assert default.configuration_id == "cfg-1"
    assert not default.is_unmatched


def test_missing_profile_blocks_compactly() -> None:
    selection = resolve_workspace_configuration_selection(
        profile_id=None,
        configurations=(_config("cfg-1", "Regel A"),),
    )
    assert not selection.is_ready
    assert selection.resolution == "missing_profile"
    assert selection.blocker_message == MSG_PROFILE_MISSING


def test_missing_active_configurations_block_compactly() -> None:
    selection = resolve_workspace_configuration_selection(
        profile_id="profile-a",
        configurations=(_config("cfg-1", "Regel A", active=False),),
    )
    assert not selection.is_ready
    assert selection.resolution == "no_active_configuration"
    assert selection.blocker_message == MSG_NO_ACTIVE_CONFIGURATION


def test_workspace_no_longer_blocks_konfiguration_fehlt_when_active_exists(
    tmp_path: Path,
) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)

    state = _state_with_adapter(
        snapshot=_snapshot(configurations=(_config("cfg-1", "Regel A"),))
    )
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"

    result = apply_start_processing(state, profile_id="profile-a")
    feedback = state.workspace_start_feedback
    assert "Konfiguration fehlt" not in feedback
    assert MSG_NO_ACTIVE_CONFIGURATION not in feedback
    assert state.config_list_selected_id == "cfg-1"
    assert result.status in {"failed", "blocked"}
    assert (
        MSG_SANDBOX_BRIDGE_NOT_CONNECTED in state.workspace_start_feedback_primary
        or "Sandbox nicht verbunden" in feedback
    )


def test_start_with_folders_profile_config_reaches_core_bridge_blocker(
    tmp_path: Path,
) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)

    state = _state_with_adapter(
        snapshot=_snapshot(
            configurations=(
                _config("cfg-1", "Regel A", sort_index=0),
                _config("cfg-2", "Regel B", sort_index=1),
            )
        )
    )
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    # No explicit config_list_selected_id — must auto/default resolve.
    assert state.config_list_selected_id is None

    apply_start_processing(state, profile_id="profile-a")
    assert state.config_list_selected_id == "cfg-1"
    assert state.workspace_run_interaction_status == "sandbox_not_connected"
    assert MSG_SANDBOX_BRIDGE_NOT_CONNECTED in state.workspace_start_feedback_primary
    assert "Konfiguration fehlt" not in state.workspace_start_feedback
    assert not state.processing_run_state.results


def test_workspace_shows_selected_configuration_compactly() -> None:
    state = _state_with_adapter(
        snapshot=_snapshot(configurations=(_config("cfg-1", "Regel A"),))
    )
    selection = resolve_workspace_configuration_selection_for_state(
        state,
        profile_id="profile-a",
    )
    assert "Konfiguration: Regel A" in selection.summary_lines
    src = WORKSPACE.read_text(encoding="utf-8")
    assert RUN_SETUP_SECTION_LABEL in src
    assert '("Konfiguration"' in src or '("Konfiguration",' in src


def test_request_includes_resolved_configuration() -> None:
    state = _state_with_adapter(
        snapshot=_snapshot(configurations=(_config("cfg-9", "Ziel"),))
    )
    request = build_processing_run_request(state, profile_id="profile-a")
    assert request.configuration_id == "cfg-9"
    assert request.profile_id == "profile-a"


def test_blocked_details_max_five_lines() -> None:
    details = build_compact_blocked_details(
        configuration_label="Regel A",
        core_bridge_relevant=True,
    )
    assert len(details) <= MAX_BLOCKED_DETAIL_LINES
    assert MSG_SANDBOX_NO_ORIGINALS_USED in details
    assert MSG_DETAIL_PRODUCTIVE_LOCKED in details
    assert MSG_DETAIL_EXPORT_DRAFT in details
    assert MSG_DETAIL_CORE_BRIDGE in details
    assert "Konfiguration: Regel A" in details


def test_long_sandbox_bullet_wall_not_in_default_feedback() -> None:
    feedback = build_start_interaction_feedback(
        ProcessingRunState(
            status="failed",
            message="sandbox unbound",
            errors=("sandbox_core_runner_unbound",),
            execution_gate="ready_for_sandbox_execution",
        ),
        configuration_label="Regel A",
    )
    assert len(feedback.details) <= MAX_BLOCKED_DETAIL_LINES
    blob = " ".join(feedback.details)
    for marker in LONG_WALL_MARKERS:
        assert marker not in blob, marker
    assert MSG_DETAIL_CORE_BRIDGE in feedback.details


def test_no_fake_success_from_config_resolution(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    state = _state_with_adapter(
        snapshot=_snapshot(configurations=(_config("cfg-1", "Regel A"),))
    )
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    apply_start_processing(state, profile_id="profile-a")
    assert state.processing_run_state.status != "completed"
    assert state.processing_run_state.results == tuple()


def test_missing_profile_start_shows_compact_profile_message(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    state = _state_with_adapter(
        snapshot=_snapshot(profile_id="", configurations=(_config("cfg-1", "A"),))
    )
    state.selected_profile_id = ""
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    apply_start_processing(state, profile_id="")
    assert MSG_PROFILE_MISSING in state.workspace_start_feedback


def test_no_processing_core_import_introduced() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    resolve_workspace_configuration_selection(
        profile_id="p",
        configurations=(_config("c", "C"),),
    )
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in FORBIDDEN_CORE:
        assert forbidden not in newly
    for path in (WORKSPACE, SELECTION):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for module in FORBIDDEN_CORE:
            assert module not in imported, (path.name, module)
