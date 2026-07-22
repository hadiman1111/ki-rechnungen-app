"""Workspace wiring for UI-v2 processing contract — non-GUI, no PDF processing."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

from invoice_tool.ui_v2.local_processing_adapter import (
    MSG_MISSING_INPUT,
    MSG_MISSING_OUTPUT,
    LocalProcessingAdapter,
)
from invoice_tool.ui_v2.pages.workspace import (
    ADAPTER_NOT_CONNECTED_HINT,
    EMPTY_INPUT_FOLDER_TEXT,
    EMPTY_OUTPUT_FOLDER_TEXT,
    SANDBOX_COPIED_DATA_ONLY,
    SANDBOX_CORE_DRY_ABSENT,
    SANDBOX_EXECUTION_WIRED,
    SANDBOX_MODE_PREPARED,
    SANDBOX_NO_ORIGINAL_INPUT,
    SANDBOX_PRODUCTIVE_BLOCKED,
    START_CTA_LABEL,
    apply_start_processing,
    apply_workspace_input_folder_selection,
    apply_workspace_output_folder_selection,
    build_processing_run_request,
    build_workspace_folder_selection_vm,
    resolve_workspace_policy_bridge,
    workspace_honesty_copy,
)
from invoice_tool.ui_v2.processing_contract import (
    SOURCE_EXPLICIT_USER_SELECTION,
    NotYetConnectedProcessingService,
)
from invoice_tool.ui_v2.processing_state import (
    MSG_BLOCKED_ADAPTER,
    MSG_DRY_RUN_UNAVAILABLE,
    blocked_processing_state,
    idle_processing_state,
    not_configured_processing_state,
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
)


def test_workspace_renders_honest_adapter_not_connected_empty_state() -> None:
    copy = workspace_honesty_copy(
        has_real_results=False,
        processing_state=blocked_processing_state(),
    )
    assert copy.has_real_results is False
    assert copy.processing_status == "blocked"
    assert ADAPTER_NOT_CONNECTED_HINT in (copy.status_line or "")
    assert MSG_BLOCKED_ADAPTER in (copy.results_detail or "")
    assert copy.start_cta_label == START_CTA_LABEL
    for marker in PRIVATE_MARKERS:
        blob = " ".join(filter(None, (copy.status_line, copy.results_title, copy.results_detail)))
        assert marker not in blob, marker


def test_workspace_not_configured_honesty_copy() -> None:
    copy = workspace_honesty_copy(
        has_real_results=False,
        processing_state=not_configured_processing_state(),
    )
    assert copy.processing_status == "not_configured"
    assert "konfiguriert" in (copy.status_line or "").lower()


def test_start_handler_does_not_import_or_call_processing_core() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    state = UiV2State(processing_service=NotYetConnectedProcessingService())
    state.workspace_input_folder_override = "selected-inbox"
    result = apply_start_processing(state, profile_id="local")
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in (
        "invoice_tool.processing",
        "invoice_tool.run",
        "invoice_tool.routing",
        "invoice_tool.classification",
        "invoice_tool.target_routing",
        "invoice_tool.routing_guards",
    ):
        assert forbidden not in newly, forbidden
    assert result.status == "blocked"
    assert result.results == tuple()
    assert state.processing_run_state.status == "blocked"


def test_start_without_folder_is_not_configured() -> None:
    state = UiV2State()
    result = apply_start_processing(state)
    assert result.status == "not_configured"
    assert result.results == tuple()
    assert result.review_items == tuple()


def test_request_builder_uses_explicit_selection_only() -> None:
    state = UiV2State()
    empty = build_processing_run_request(state)
    assert empty.input_folder is None
    assert empty.output_folder is None
    assert empty.user_confirmed_start is False
    assert empty.source != SOURCE_EXPLICIT_USER_SELECTION
    assert empty.policy_bridge_result is not None
    assert empty.policy_bridge_result.status == "ready"

    state.workspace_input_folder_override = "user-selected-folder"
    filled = build_processing_run_request(state, profile_id="local")
    assert filled.input_folder == "user-selected-folder"
    assert filled.output_folder is None
    assert filled.source == SOURCE_EXPLICIT_USER_SELECTION
    assert filled.dry_run is True
    assert filled.user_confirmed_start is False
    assert filled.policy_intent is not None
    assert filled.policy_intent.filename_policy["filename_is_source_of_truth"] is False
    for marker in PRIVATE_MARKERS:
        assert marker not in (filled.input_folder or "")
        assert marker not in (filled.output_folder or "")


def test_cta_sets_user_confirmed_start_without_auto_processing() -> None:
    state = UiV2State(processing_service=NotYetConnectedProcessingService())
    state.workspace_input_folder_override = "selected-inbox"
    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status == "blocked"
    assert result.results == tuple()
    # CTA marks confirmation; default service still refuses productive work.
    request = build_processing_run_request(
        state, profile_id="profile-a", user_confirmed_start=True
    )
    assert request.user_confirmed_start is True
    assert request.output_folder is None


def test_workspace_reports_missing_output_folder_honestly() -> None:
    state = UiV2State(processing_service=LocalProcessingAdapter())
    state.workspace_input_folder_override = "selected-inbox"
    state.workspace_output_folder_override = None
    result = apply_start_processing(
        state, profile_id="profile-a"
    )
    # Local adapter requires explicit output; profile/config may also be missing.
    # Force validate path with full args via request builder + adapter.
    request = build_processing_run_request(
        state,
        profile_id="profile-a",
        configuration_id="config-a",
        user_confirmed_start=True,
    )
    assert request.output_folder is None
    validated = state.processing_service.validate_request(request)
    assert validated.status == "not_configured"
    assert MSG_MISSING_OUTPUT in validated.message

    copy = workspace_honesty_copy(
        has_real_results=False,
        processing_state=validated,
    )
    assert copy.processing_status == "not_configured"
    assert MSG_MISSING_OUTPUT in (copy.status_line or "")
    assert MSG_MISSING_OUTPUT in (copy.results_detail or "")
    assert result.results == tuple()


def test_workspace_output_override_is_explicit_only_never_defaulted() -> None:
    state = UiV2State()
    assert state.workspace_output_folder_override is None
    empty = build_processing_run_request(state)
    assert empty.output_folder is None

    state.workspace_output_folder_override = "user-selected-outbox"
    filled = build_processing_run_request(
        state,
        profile_id="profile-a",
        configuration_id="config-a",
    )
    assert filled.output_folder == "user-selected-outbox"
    for marker in PRIVATE_MARKERS:
        assert marker not in (filled.output_folder or "")


def test_workspace_folder_selection_vm_empty_copy() -> None:
    vm = build_workspace_folder_selection_vm(UiV2State())
    assert vm.input_empty_text == EMPTY_INPUT_FOLDER_TEXT
    assert vm.output_empty_text == EMPTY_OUTPUT_FOLDER_TEXT
    assert vm.input_folder is None
    assert vm.output_folder is None


def test_workspace_reports_missing_input_folder_honestly() -> None:
    state = UiV2State(processing_service=LocalProcessingAdapter())
    apply_workspace_output_folder_selection(state, "selected-outbox")
    request = build_processing_run_request(
        state,
        profile_id="profile-a",
        configuration_id="config-a",
        user_confirmed_start=True,
    )
    assert request.input_folder is None
    validated = state.processing_service.validate_request(request)
    assert validated.status == "not_configured"
    assert MSG_MISSING_INPUT in validated.message
    copy = workspace_honesty_copy(has_real_results=False, processing_state=validated)
    assert MSG_MISSING_INPUT in (copy.status_line or "")


def test_workspace_folder_setters_feed_request_builder() -> None:
    state = UiV2State()
    apply_workspace_input_folder_selection(state, "in-folder")
    apply_workspace_output_folder_selection(state, "out-folder")
    request = build_processing_run_request(state)
    assert request.input_folder == "in-folder"
    assert request.output_folder == "out-folder"
    assert request.source == SOURCE_EXPLICIT_USER_SELECTION


def test_workspace_dry_gate_unavailable_honesty_copy() -> None:
    copy = workspace_honesty_copy(
        has_real_results=False,
        processing_state=blocked_processing_state(
            MSG_DRY_RUN_UNAVAILABLE,
            execution_gate="unsupported_without_core_change",
            dry_run_gate="unsupported_without_core_change",
            core_dry_run_status="unsupported_without_core_change",
        ),
    )
    assert copy.processing_status == "blocked"
    assert MSG_DRY_RUN_UNAVAILABLE in (copy.status_line or "")
    assert "running" not in (copy.status_line or "").lower()
    assert "abgeschlossen" not in (copy.status_line or "").lower()


def test_workspace_policy_bridge_ready_hint_is_optional() -> None:
    state = UiV2State()
    bridge = resolve_workspace_policy_bridge(state)
    assert bridge.status == "ready"
    copy = workspace_honesty_copy(
        has_real_results=False,
        processing_state=idle_processing_state(),
        policy_bridge=bridge,
    )
    assert copy.policy_intent_status == "ready"
    assert copy.policy_intent_hint is None


def test_default_state_idle_has_no_fake_results() -> None:
    state = UiV2State()
    assert state.processing_run_state.status == "idle"
    assert state.processing_run_state.results == tuple()
    copy = workspace_honesty_copy(
        has_real_results=False,
        processing_state=idle_processing_state(),
    )
    assert "AMEX" not in (copy.results_detail or "")
    assert copy.adapter_hint == ADAPTER_NOT_CONNECTED_HINT


def test_workspace_sandbox_readiness_copy_is_honest() -> None:
    state = UiV2State()
    assert state.workspace_sandbox_mode is False
    assert state.workspace_sandbox_root is None
    assert state.workspace_copied_data_confirmed is False
    request = build_processing_run_request(state)
    assert request.sandbox_mode is False
    assert request.productive_execution_allowed is False
    assert request.execution_scope == "blocked"

    copy = workspace_honesty_copy(
        has_real_results=False,
        processing_state=idle_processing_state(),
    )
    assert SANDBOX_MODE_PREPARED in copy.sandbox_readiness_lines
    assert SANDBOX_COPIED_DATA_ONLY in copy.sandbox_readiness_lines
    assert SANDBOX_NO_ORIGINAL_INPUT in copy.sandbox_readiness_lines
    assert SANDBOX_PRODUCTIVE_BLOCKED in copy.sandbox_readiness_lines
    assert SANDBOX_EXECUTION_WIRED in copy.sandbox_readiness_lines
    assert SANDBOX_CORE_DRY_ABSENT in copy.sandbox_readiness_lines
    detail = copy.results_detail or ""
    assert SANDBOX_MODE_PREPARED in detail
    assert SANDBOX_COPIED_DATA_ONLY in detail
    for marker in PRIVATE_MARKERS:
        assert marker not in detail


def test_workspace_contract_source_has_no_private_tokens() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in src, marker


def test_workspace_ast_does_not_import_processing_core() -> None:
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
        "invoice_tool.ui_workspace",
    )
    for name in imported:
        assert not any(name == f or name.startswith(f + ".") for f in forbidden), name


def test_workspace_module_reload_stays_core_free() -> None:
    before = set(sys.modules)
    importlib.reload(importlib.import_module("invoice_tool.ui_v2.pages.workspace"))
    after = set(sys.modules)
    newly = after - before
    for forbidden in (
        "invoice_tool.processing",
        "invoice_tool.run",
        "invoice_tool.routing",
        "invoice_tool.classification",
    ):
        assert forbidden not in newly
