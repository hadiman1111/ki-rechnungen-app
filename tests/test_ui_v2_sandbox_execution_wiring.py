"""Sandbox execution wiring — non-GUI, no real PDF/OCR/AI, tmp_path only."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

from invoice_tool.saas_product_model import default_classification_policy
from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.pages.workspace import build_workspace_run_result_shell
from invoice_tool.ui_v2.policy_runtime_bridge import build_runtime_policy_intent
from invoice_tool.ui_v2.processing_state import (
    ProcessingResultSummary,
    ProcessingReviewItem,
)
from invoice_tool.ui_v2.run_result_display import build_run_result_display_shell
from invoice_tool.ui_v2.sandbox_execution_boundary import (
    MSG_SANDBOX_EXECUTION_COMPLETED,
    MSG_SANDBOX_RUNNER_UNBOUND,
    SandboxCoreCallArgs,
    SandboxCoreCallResult,
    sandbox_core_runner,
)
from invoice_tool.ui_v2.sandbox_processing_gate import build_sandbox_run_request
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "invoice_tool" / "ui_v2" / "local_processing_adapter.py"
BOUNDARY = ROOT / "invoice_tool" / "ui_v2" / "sandbox_execution_boundary.py"

FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.run",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
)
PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX",
    "voba",
    "/Users/",
    "Desktop/Programm Belegerfassung",
)


def _bridge():
    return build_runtime_policy_intent(default_classification_policy())


def _sandbox_layout(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    original = tmp_path / "original-source"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    original.mkdir()
    return sandbox, inbox, outbox, original


def _sandbox_request(tmp_path: Path, **kwargs):
    sandbox, inbox, outbox, original = _sandbox_layout(tmp_path)
    bridge = _bridge()
    base = dict(
        sandbox_root=str(sandbox),
        input_folder=str(inbox),
        output_folder=str(outbox),
        original_source_folder=str(original),
        profile_id="profile-a",
        configuration_id="config-a",
        copied_data_confirmed=True,
        user_confirmed_start=True,
        dry_run=True,
        policy_intent=bridge.intent,
        policy_bridge_result=bridge,
    )
    base.update(kwargs)
    return build_sandbox_run_request(**base), sandbox, inbox, outbox, original


def test_adapter_blocks_without_sandbox_approval(tmp_path: Path) -> None:
    from invoice_tool.ui_v2.processing_contract import (
        SOURCE_EXPLICIT_USER_SELECTION,
        ProcessingRunRequest,
    )

    bridge = _bridge()
    adapter = LocalProcessingAdapter()
    started = adapter.start_run(
        ProcessingRunRequest(
            input_folder=str(tmp_path / "inbox"),
            output_folder=str(tmp_path / "outbox"),
            profile_id="profile-a",
            configuration_id="config-a",
            dry_run=True,
            source=SOURCE_EXPLICIT_USER_SELECTION,
            policy_intent=bridge.intent,
            policy_bridge_result=bridge,
            user_confirmed_start=True,
            sandbox_mode=False,
        )
    )
    assert started.status == "blocked"
    assert started.execution_gate == "blocked_missing_sandbox"
    assert started.results == tuple()


def test_adapter_blocks_original_source_as_input(tmp_path: Path) -> None:
    sandbox, _inbox, outbox, original = _sandbox_layout(tmp_path)
    bridge = _bridge()
    adapter = LocalProcessingAdapter()
    started = adapter.start_run(
        build_sandbox_run_request(
            sandbox_root=str(sandbox),
            input_folder=str(original),
            output_folder=str(outbox),
            original_source_folder=str(original),
            profile_id="profile-a",
            configuration_id="config-a",
            policy_intent=bridge.intent,
            policy_bridge_result=bridge,
        )
    )
    assert started.status == "blocked"
    assert started.execution_gate == "blocked_original_folder"
    assert started.results == tuple()


def test_adapter_blocks_output_inside_original(tmp_path: Path) -> None:
    sandbox, inbox, _outbox, original = _sandbox_layout(tmp_path)
    nested_out = original / "nested-out"
    nested_out.mkdir()
    bridge = _bridge()
    adapter = LocalProcessingAdapter()
    started = adapter.start_run(
        build_sandbox_run_request(
            sandbox_root=str(sandbox),
            input_folder=str(inbox),
            output_folder=str(nested_out),
            original_source_folder=str(original),
            profile_id="profile-a",
            configuration_id="config-a",
            policy_intent=bridge.intent,
            policy_bridge_result=bridge,
        )
    )
    assert started.status == "blocked"
    assert started.execution_gate == "blocked_original_folder"
    assert started.results == tuple()


def test_adapter_blocks_productive_execution(tmp_path: Path) -> None:
    request, *_ = _sandbox_request(tmp_path, dry_run=False)
    adapter = LocalProcessingAdapter()
    started = adapter.start_run(request)
    assert started.status == "blocked"
    assert started.execution_gate == "blocked_productive_execution"
    assert started.results == tuple()


def test_adapter_requires_copied_data_confirmation(tmp_path: Path) -> None:
    request, *_ = _sandbox_request(tmp_path, copied_data_confirmed=False)
    adapter = LocalProcessingAdapter()
    started = adapter.start_run(request)
    assert started.status == "blocked"
    assert started.execution_gate == "blocked_missing_copied_data_confirmation"
    assert started.results == tuple()


def test_adapter_calls_boundary_only_when_gate_approved(tmp_path: Path) -> None:
    calls: list[SandboxCoreCallArgs] = []

    def stub(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        calls.append(args)
        return SandboxCoreCallResult(
            ok=True,
            message=MSG_SANDBOX_EXECUTION_COMPLETED,
            run_id="sandbox-run-1",
            results=(),
        )

    request, sandbox, inbox, outbox, original = _sandbox_request(tmp_path)
    adapter = LocalProcessingAdapter(sandbox_runner=stub)
    started = adapter.start_run(request)
    assert len(calls) == 1
    assert started.status == "completed"
    assert calls[0].input_folder == str(inbox)
    assert calls[0].output_folder == str(outbox)
    assert calls[0].sandbox_root == str(sandbox)
    assert calls[0].input_folder != str(original)
    assert str(original) not in (calls[0].input_folder, calls[0].output_folder)


def test_adapter_passes_only_sandbox_paths(tmp_path: Path) -> None:
    seen: list[SandboxCoreCallArgs] = []

    def stub(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        seen.append(args)
        return SandboxCoreCallResult(ok=True, message="ok", run_id="r1")

    request, sandbox, inbox, outbox, original = _sandbox_request(tmp_path)
    LocalProcessingAdapter(sandbox_runner=stub).start_run(request)
    args = seen[0]
    assert args.input_folder.startswith(str(sandbox))
    assert args.output_folder.startswith(str(sandbox))
    assert args.input_folder == str(inbox)
    assert args.output_folder == str(outbox)
    assert args.input_folder != str(original)
    assert args.output_folder != str(original)


def test_adapter_does_not_pass_original_as_core_input(tmp_path: Path) -> None:
    seen: list[SandboxCoreCallArgs] = []

    def stub(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        seen.append(args)
        return SandboxCoreCallResult(ok=True, message="ok", run_id="r2")

    request, _sandbox, _inbox, _outbox, original = _sandbox_request(tmp_path)
    LocalProcessingAdapter(sandbox_runner=stub).start_run(request)
    assert seen[0].input_folder != str(original)
    # original may be recorded for exclusion only — never as processing path
    assert seen[0].input_folder != seen[0].original_source_folder
    assert seen[0].output_folder != seen[0].original_source_folder


def test_adapter_maps_stubbed_success_to_completed(tmp_path: Path) -> None:
    summary = ProcessingResultSummary(
        document_name="copy-doc.pdf",
        document_type="dokument",
        classification_status="ok",
        status_label="OK",
    )
    review = ProcessingReviewItem(
        document_name="copy-doc.pdf",
        reason="unklar",
        status_label="unklar",
    )

    def stub(_args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        return SandboxCoreCallResult(
            ok=True,
            message=MSG_SANDBOX_EXECUTION_COMPLETED,
            run_id="sandbox-ok",
            results=(summary,),
            review_items=(review,),
            errors=(),
        )

    request, *_ = _sandbox_request(tmp_path)
    state = LocalProcessingAdapter(sandbox_runner=stub).start_run(request)
    assert state.status == "completed"
    assert state.run_id == "sandbox-ok"
    assert len(state.results) == 1
    assert state.results[0].document_name == "copy-doc.pdf"
    assert len(state.review_items) == 1
    assert state.errors == tuple()
    assert state.execution_gate == "ready_for_sandbox_execution"


def test_adapter_maps_stubbed_failure_to_failed(tmp_path: Path) -> None:
    def stub(_args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        return SandboxCoreCallResult(
            ok=False,
            message="Sandbox stub failure",
            run_id="sandbox-fail",
            errors=("stub_error",),
        )

    request, *_ = _sandbox_request(tmp_path)
    state = LocalProcessingAdapter(sandbox_runner=stub).start_run(request)
    assert state.status == "failed"
    assert state.message == "Sandbox stub failure"
    assert state.errors == ("stub_error",)
    assert state.results == tuple()


def test_workspace_result_display_shows_sandbox_result_state(tmp_path: Path) -> None:
    def stub(_args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        return SandboxCoreCallResult(
            ok=True,
            message=MSG_SANDBOX_EXECUTION_COMPLETED,
            run_id="sandbox-ui",
            results=(
                ProcessingResultSummary(
                    document_name="a.pdf",
                    document_type="dokument",
                    classification_status="ok",
                    status_label="OK",
                ),
            ),
            review_items=(
                ProcessingReviewItem(
                    document_name="a.pdf",
                    reason="nachweis unklar",
                    status_label="unklar",
                ),
            ),
            errors=("warn-1",),
        )

    request, *_ = _sandbox_request(tmp_path)
    state = LocalProcessingAdapter(sandbox_runner=stub).start_run(request)
    ui = UiV2State(processing_run_state=state)
    shell = build_workspace_run_result_shell(ui)
    display = build_run_result_display_shell(state)
    assert shell.status == "completed"
    assert shell.result_count == 1
    assert shell.review.count == 1
    assert shell.errors.count == 1
    assert display.result_count == 1
    assert display.show_empty_state is False


def test_no_fake_results_when_runner_unbound(tmp_path: Path) -> None:
    request, *_ = _sandbox_request(tmp_path)
    before = set(sys.modules)
    state = LocalProcessingAdapter().start_run(request)
    newly = set(sys.modules) - before
    assert state.status == "failed"
    assert MSG_SANDBOX_RUNNER_UNBOUND in state.message
    assert state.results == tuple()
    assert state.review_items == tuple()
    for forbidden in FORBIDDEN_CORE:
        assert forbidden not in newly


def test_no_private_defaults_in_boundary_or_adapter_source() -> None:
    # Reject path-like private defaults; token lists in rejection regexes are allowed.
    path_markers = (
        "/Users/",
        "Desktop/Programm Belegerfassung",
        '"SOMAA',
        "'SOMAA",
        '"Hadi',
        "'Hadi",
        '"Bismarck',
        "'AMEX",
        '"voba',
    )
    for path in (ADAPTER, BOUNDARY):
        src = path.read_text(encoding="utf-8")
        for marker in path_markers:
            assert marker not in src, f"{path.name}: {marker}"
        # No hardcoded absolute desktop invoice defaults.
        assert "TEST Rechnungen" not in src


def test_default_runner_is_unbound_and_core_free() -> None:
    args = SandboxCoreCallArgs(
        input_folder="/tmp/sandbox/in",
        output_folder="/tmp/sandbox/out",
        sandbox_root="/tmp/sandbox",
        profile_id="p",
        configuration_id="c",
        original_source_folder="/tmp/original",
    )
    before = set(sys.modules)
    result = sandbox_core_runner(args)
    newly = set(sys.modules) - before
    assert result.ok is False
    assert MSG_SANDBOX_RUNNER_UNBOUND in result.message
    for forbidden in FORBIDDEN_CORE:
        assert forbidden not in newly


def test_boundary_and_adapter_ast_have_no_core_imports() -> None:
    for path in (ADAPTER, BOUNDARY):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for name in imported:
            assert not any(
                name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_CORE
            ), f"{path.name}: {name}"


def test_boundary_module_import_stays_core_free() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    sys.modules.pop("invoice_tool.ui_v2.sandbox_execution_boundary", None)
    importlib.import_module("invoice_tool.ui_v2.sandbox_execution_boundary")
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in FORBIDDEN_CORE:
        assert forbidden not in newly


def test_blocked_path_does_not_call_runner(tmp_path: Path) -> None:
    calls: list[SandboxCoreCallArgs] = []

    def stub(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
        calls.append(args)
        return SandboxCoreCallResult(ok=True, message="should-not-run")

    request, *_ = _sandbox_request(tmp_path, copied_data_confirmed=False)
    state = LocalProcessingAdapter(sandbox_runner=stub).start_run(request)
    assert state.status == "blocked"
    assert calls == []
