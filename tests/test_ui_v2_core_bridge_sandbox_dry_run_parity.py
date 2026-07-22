"""Track-B Core Bridge sandbox/dry-run parity — Path B contract tests."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from invoice_tool.ui_v2.core_bridge import (
    ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED,
    ERROR_MISSING_CONFIGURATION,
    ERROR_MISSING_INPUT,
    ERROR_MISSING_OUTPUT,
    ERROR_ORIGINAL_LOOKING,
    ERROR_PRODUCTIVE_BLOCKED,
    MSG_BRIDGE_DRY_RUN_CONTRACT_REQUIRED,
    MSG_BRIDGE_NO_FILES_PROCESSED,
    MSG_BRIDGE_NO_ORIGINALS,
    MSG_BRIDGE_SANDBOX_NOT_CONNECTED,
    CoreBridgeRequest,
    CoreBridgeStatus,
    map_core_result_to_processing_run_state,
    path_looks_like_original,
    run_core_bridge_sandbox_dry_run,
)
from invoice_tool.ui_v2.export_reporting import (
    build_run_export_payload,
    build_run_report_view_model,
)
from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.pages.workspace import (
    MAX_BLOCKED_DETAIL_LINES,
    MSG_SANDBOX_BLOCKED_CORE_BRIDGE,
    MSG_SANDBOX_BRIDGE_NOT_CONNECTED,
    apply_start_processing,
)
from invoice_tool.ui_v2.sandbox_execution_boundary import (
    SandboxCoreCallArgs,
    sandbox_core_runner,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
CORE_BRIDGE = ROOT / "invoice_tool" / "ui_v2" / "core_bridge.py"
PROCESSING_CORE = (
    ROOT / "invoice_tool" / "processing.py",
    ROOT / "invoice_tool" / "routing.py",
    ROOT / "invoice_tool" / "routing_guards.py",
    ROOT / "invoice_tool" / "classification.py",
    ROOT / "invoice_tool" / "target_routing.py",
    ROOT / "invoice_tool" / "run.py",
)
FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.run",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
)


def _valid_request(tmp_path: Path, **overrides) -> CoreBridgeRequest:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    data = dict(
        input_folder=str(inbox),
        output_folder=str(outbox),
        sandbox_root=str(sandbox),
        profile_id="profile-a",
        configuration_id="config-a",
        original_source_folder=str(tmp_path / "original-never-used"),
        dry_run=True,
        productive_execution_allowed=False,
        mode="sandbox_dry_run",
    )
    data.update(overrides)
    return CoreBridgeRequest(**data)


def test_core_bridge_rejects_missing_input(tmp_path: Path) -> None:
    result = run_core_bridge_sandbox_dry_run(
        _valid_request(tmp_path, input_folder=None)
    )
    assert result.status == CoreBridgeStatus.BLOCKED_MISSING_INPUT
    assert ERROR_MISSING_INPUT in result.errors
    assert result.ok is False
    assert result.results == ()


def test_core_bridge_rejects_missing_output(tmp_path: Path) -> None:
    result = run_core_bridge_sandbox_dry_run(
        _valid_request(tmp_path, output_folder="  ")
    )
    assert result.status == CoreBridgeStatus.BLOCKED_MISSING_OUTPUT
    assert ERROR_MISSING_OUTPUT in result.errors


def test_core_bridge_rejects_original_looking_folders(tmp_path: Path) -> None:
    original = tmp_path / "Desktop" / "Rechnungen_AMEX"
    original.mkdir(parents=True)
    result = run_core_bridge_sandbox_dry_run(
        _valid_request(
            tmp_path,
            input_folder=str(original),
            output_folder=str(tmp_path / "sandbox" / "copied-outbox"),
            sandbox_root=str(tmp_path),
            original_source_folder=str(original),
        )
    )
    assert result.status == CoreBridgeStatus.BLOCKED_ORIGINAL_LOOKING
    assert ERROR_ORIGINAL_LOOKING in result.errors
    assert path_looks_like_original(
        str(original),
        original_source_folder=str(original),
    )


def test_core_bridge_requires_resolved_configuration(tmp_path: Path) -> None:
    result = run_core_bridge_sandbox_dry_run(
        _valid_request(tmp_path, configuration_id=None)
    )
    assert result.status == CoreBridgeStatus.BLOCKED_MISSING_CONFIGURATION
    assert ERROR_MISSING_CONFIGURATION in result.errors


def test_core_bridge_never_enables_productive_mode(tmp_path: Path) -> None:
    result = run_core_bridge_sandbox_dry_run(
        _valid_request(
            tmp_path,
            dry_run=False,
            productive_execution_allowed=True,
        )
    )
    assert result.status == CoreBridgeStatus.BLOCKED_PRODUCTIVE
    assert ERROR_PRODUCTIVE_BLOCKED in result.errors
    assert result.productive_execution_enabled is False


def test_core_bridge_valid_sandbox_reaches_dry_run_contract(tmp_path: Path) -> None:
    result = run_core_bridge_sandbox_dry_run(_valid_request(tmp_path))
    assert result.status == CoreBridgeStatus.REQUIRES_CORE_DRY_RUN_CONTRACT
    assert ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED in result.errors
    assert result.ok is False
    assert result.results == ()
    assert result.review_items == ()
    assert result.planned_moves == ()
    assert MSG_BRIDGE_SANDBOX_NOT_CONNECTED in result.message
    assert MSG_BRIDGE_DRY_RUN_CONTRACT_REQUIRED in result.message
    assert MSG_BRIDGE_NO_ORIGINALS in result.message
    assert MSG_BRIDGE_NO_FILES_PROCESSED in result.message


def test_map_core_result_keeps_empty_rows(tmp_path: Path) -> None:
    bridge = run_core_bridge_sandbox_dry_run(_valid_request(tmp_path))
    state = map_core_result_to_processing_run_state(bridge)
    assert state.status == "failed"
    assert state.results == ()
    assert state.review_items == ()
    assert ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED in state.errors


def test_sandbox_core_runner_uses_core_bridge_without_core_import(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    outcome = sandbox_core_runner(
        SandboxCoreCallArgs(
            input_folder=str(inbox),
            output_folder=str(outbox),
            sandbox_root=str(sandbox),
            profile_id="profile-a",
            configuration_id="config-a",
            original_source_folder=str(tmp_path / "original"),
        )
    )
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in FORBIDDEN_CORE:
        assert forbidden not in newly, forbidden
    assert outcome.ok is False
    assert ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED in outcome.errors
    assert "sandbox_core_runner_unbound" in outcome.errors
    assert outcome.results == ()


def test_clicking_start_reaches_core_dry_run_contract_required(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"

    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    result = apply_start_processing(state, profile_id="profile-a")
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in FORBIDDEN_CORE:
        assert forbidden not in newly, forbidden

    assert result.status == "failed"
    assert ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED in result.errors
    assert state.workspace_run_interaction_status == "sandbox_not_connected"
    assert MSG_SANDBOX_BRIDGE_NOT_CONNECTED in state.workspace_start_feedback_primary
    assert MSG_SANDBOX_BLOCKED_CORE_BRIDGE in state.workspace_start_feedback_primary
    assert len(state.workspace_start_feedback_details) <= MAX_BLOCKED_DETAIL_LINES
    assert not result.results
    assert not result.review_items


def test_no_fake_results_and_export_stays_empty(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"
    apply_start_processing(state, profile_id="profile-a")
    report = build_run_report_view_model(state.processing_run_state)
    payload = build_run_export_payload(report)
    assert state.processing_run_state.results == ()
    assert report.recognized == ()
    assert report.unclear == ()
    # Failed may contain honest bridge errors — never invented document rows.
    assert all(item.document_name is None for item in report.failed)
    assert payload["preview"] is True
    assert payload["productive_export"] is False
    assert payload["questions"]["recognized"]["items"] == []


def test_core_bridge_module_has_no_processing_core_imports() -> None:
    tree = ast.parse(CORE_BRIDGE.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for name in imported:
        assert not any(
            name == forbidden or name.startswith(forbidden + ".")
            for forbidden in FORBIDDEN_CORE
        ), name


def test_processing_core_files_unchanged_vs_head() -> None:
    import subprocess

    for path in PROCESSING_CORE:
        rel = path.relative_to(ROOT).as_posix()
        out = subprocess.run(
            ["git", "diff", "--", rel],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert out == "", f"processing-core dirty: {rel}"
