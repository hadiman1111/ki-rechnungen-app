"""Sandbox processing run gate — non-GUI, no PDF processing, no FS mutation."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

from invoice_tool.saas_product_model import default_classification_policy
from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.policy_runtime_bridge import build_runtime_policy_intent
from invoice_tool.ui_v2.processing_contract import (
    SOURCE_EXPLICIT_USER_SELECTION,
    empty_processing_request,
)
from invoice_tool.ui_v2.sandbox_processing_gate import (
    MSG_BLOCKED_MISSING_COPIED_DATA,
    MSG_BLOCKED_MISSING_SANDBOX,
    MSG_BLOCKED_MISSING_SANDBOX_ROOT,
    MSG_BLOCKED_ORIGINAL_AS_INPUT,
    MSG_BLOCKED_OUTPUT_INSIDE_ORIGINAL,
    MSG_BLOCKED_PRODUCTIVE,
    MSG_BLOCKED_SAME_INPUT_OUTPUT,
    MSG_SANDBOX_CORE_DRY_ABSENT,
    MSG_SANDBOX_MODE_PREPARED,
    MSG_SANDBOX_READY_PENDING_WIRING,
    SandboxProcessingGate,
    build_sandbox_run_request,
    validate_sandbox_paths,
    workspace_sandbox_readiness_copy,
)

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "invoice_tool" / "ui_v2" / "sandbox_processing_gate.py"
ADAPTER = ROOT / "invoice_tool" / "ui_v2" / "local_processing_adapter.py"

PRIVATE_MARKERS = (
    "/Users/",
    "Desktop/Programm Belegerfassung",
    "SOMAA",
    "Hadi",
    "Bismarck",
    "AMEX",
    "voba",
    "TEST Rechnungen",
)

FORBIDDEN_IMPORT_PREFIXES = (
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

SANDBOX_ROOT = "/tmp/ui-v2-sandbox-area"
SANDBOX_INPUT = "/tmp/ui-v2-sandbox-area/copied-inbox"
SANDBOX_OUTPUT = "/tmp/ui-v2-sandbox-area/copied-outbox"
ORIGINAL_SOURCE = "/tmp/original-invoice-source"


def _approved_gate(**kwargs) -> SandboxProcessingGate:
    base = dict(
        mode="sandbox",
        sandbox_root=SANDBOX_ROOT,
        input_folder=SANDBOX_INPUT,
        output_folder=SANDBOX_OUTPUT,
        original_source_folder=ORIGINAL_SOURCE,
        copied_data_confirmed=True,
        user_confirmed_start=True,
        productive_execution_allowed=False,
        dry_run=True,
        profile_id="profile-a",
        configuration_id="config-a",
        has_policy_intent=True,
        has_explicit_user_source=True,
    )
    base.update(kwargs)
    return SandboxProcessingGate(**base)


def _sandbox_request(**kwargs):
    bridge = build_runtime_policy_intent(default_classification_policy())
    base = dict(
        sandbox_root=SANDBOX_ROOT,
        input_folder=SANDBOX_INPUT,
        output_folder=SANDBOX_OUTPUT,
        original_source_folder=ORIGINAL_SOURCE,
        profile_id="profile-a",
        configuration_id="config-a",
        copied_data_confirmed=True,
        user_confirmed_start=True,
        dry_run=True,
        policy_intent=bridge.intent,
        policy_bridge_result=bridge,
    )
    base.update(kwargs)
    return build_sandbox_run_request(**base)


def test_blocks_when_sandbox_mode_missing() -> None:
    result = validate_sandbox_paths(_approved_gate(mode="disabled"))
    assert result.approved is False
    assert result.reason_code == "blocked_missing_sandbox"
    assert MSG_BLOCKED_MISSING_SANDBOX in result.message


def test_blocks_missing_sandbox_root() -> None:
    result = validate_sandbox_paths(_approved_gate(sandbox_root=None))
    assert result.approved is False
    assert result.reason_code == "blocked_missing_sandbox_root"
    assert MSG_BLOCKED_MISSING_SANDBOX_ROOT in result.message


def test_blocks_missing_copied_data_confirmation() -> None:
    result = validate_sandbox_paths(_approved_gate(copied_data_confirmed=False))
    assert result.approved is False
    assert result.reason_code == "blocked_missing_copied_data_confirmation"
    assert MSG_BLOCKED_MISSING_COPIED_DATA in result.message


def test_blocks_original_source_used_as_input() -> None:
    result = validate_sandbox_paths(
        _approved_gate(input_folder=ORIGINAL_SOURCE, sandbox_root=ORIGINAL_SOURCE)
    )
    assert result.approved is False
    assert result.reason_code == "blocked_original_folder"
    assert MSG_BLOCKED_ORIGINAL_AS_INPUT in result.message


def test_blocks_same_input_and_output_folder() -> None:
    result = validate_sandbox_paths(
        _approved_gate(input_folder=SANDBOX_INPUT, output_folder=SANDBOX_INPUT)
    )
    assert result.approved is False
    assert result.reason_code == "blocked_same_input_output"
    assert MSG_BLOCKED_SAME_INPUT_OUTPUT in result.message


def test_blocks_output_inside_original_source() -> None:
    result = validate_sandbox_paths(
        _approved_gate(
            output_folder=f"{ORIGINAL_SOURCE}/nested-out",
            sandbox_root="/tmp",
            input_folder="/tmp/copied-inbox",
        )
    )
    assert result.approved is False
    assert result.reason_code == "blocked_output_inside_original"
    assert MSG_BLOCKED_OUTPUT_INSIDE_ORIGINAL in result.message


def test_blocks_productive_execution() -> None:
    result = validate_sandbox_paths(_approved_gate(dry_run=False))
    assert result.approved is False
    assert result.reason_code == "blocked_productive_execution"
    assert MSG_BLOCKED_PRODUCTIVE in result.message

    allowed = validate_sandbox_paths(_approved_gate(productive_execution_allowed=True))
    assert allowed.approved is False
    assert allowed.reason_code == "blocked_productive_execution"


def test_accepts_explicit_copied_sandbox_paths() -> None:
    result = validate_sandbox_paths(_approved_gate())
    assert result.approved is True
    assert result.reason_code == "ready_for_sandbox_execution"
    assert result.execution_scope == "sandbox"
    assert MSG_SANDBOX_READY_PENDING_WIRING in result.message
    assert result.creates_folders is False
    assert result.scans_folders is False
    assert result.processes_pdfs is False


def test_validation_does_not_create_folders(tmp_path: Path) -> None:
    root = tmp_path / "sandbox-root-never-created"
    inbox = root / "inbox"
    outbox = root / "outbox"
    original = tmp_path / "original-never-created"
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_text("untouched", encoding="utf-8")

    result = validate_sandbox_paths(
        _approved_gate(
            sandbox_root=str(root),
            input_folder=str(inbox),
            output_folder=str(outbox),
            original_source_folder=str(original),
        )
    )
    assert result.approved is True
    assert not root.exists()
    assert not inbox.exists()
    assert not outbox.exists()
    assert not original.exists()
    assert sentinel.read_text(encoding="utf-8") == "untouched"
    assert list(tmp_path.iterdir()) == [sentinel]


def test_validation_does_not_scan_folders(tmp_path: Path) -> None:
    inbox = tmp_path / "sandbox" / "inbox"
    outbox = tmp_path / "sandbox" / "outbox"
    original = tmp_path / "original"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    original.mkdir()
    marker = inbox / "do-not-read.pdf"
    marker.write_bytes(b"%PDF-1.4 fake")
    before = marker.read_bytes()
    before_names = sorted(p.name for p in inbox.iterdir())

    result = validate_sandbox_paths(
        _approved_gate(
            sandbox_root=str(tmp_path / "sandbox"),
            input_folder=str(inbox),
            output_folder=str(outbox),
            original_source_folder=str(original),
        )
    )
    assert result.approved is True
    assert result.scans_folders is False
    assert marker.read_bytes() == before
    assert sorted(p.name for p in inbox.iterdir()) == before_names


def test_validation_does_not_process_pdfs(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "inbox"
    outbox = sandbox / "outbox"
    original = tmp_path / "original"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    original.mkdir()
    pdf = inbox / "invoice.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    before = pdf.read_bytes()

    result = validate_sandbox_paths(
        _approved_gate(
            sandbox_root=str(sandbox),
            input_folder=str(inbox),
            output_folder=str(outbox),
            original_source_folder=str(original),
        )
    )
    assert result.approved is True
    assert result.processes_pdfs is False
    assert pdf.read_bytes() == before
    assert list(outbox.iterdir()) == []


def test_adapter_does_not_call_core_when_sandbox_ready() -> None:
    before = set(sys.modules)
    adapter = LocalProcessingAdapter()
    started = adapter.start_run(_sandbox_request())
    after = set(sys.modules)
    newly = after - before

    assert started.status == "ready"
    assert started.execution_gate == "ready_for_sandbox_execution"
    assert started.results == tuple()
    assert started.review_items == tuple()
    assert started.run_id is None
    assert MSG_SANDBOX_CORE_DRY_ABSENT in started.message
    for forbidden in FORBIDDEN_IMPORT_PREFIXES:
        assert forbidden not in newly
        assert not any(name.startswith(forbidden + ".") for name in newly)


def test_adapter_blocks_without_sandbox_and_keeps_productive_blocked() -> None:
    adapter = LocalProcessingAdapter()
    bridge = build_runtime_policy_intent(default_classification_policy())
    request = empty_processing_request().__class__(
        input_folder="selected-inbox",
        output_folder="selected-outbox",
        profile_id="profile-a",
        configuration_id="config-a",
        dry_run=True,
        source=SOURCE_EXPLICIT_USER_SELECTION,
        policy_intent=bridge.intent,
        policy_bridge_result=bridge,
        user_confirmed_start=True,
        sandbox_mode=False,
    )
    started = adapter.start_run(request)
    assert started.status == "blocked"
    assert started.execution_gate == "blocked_missing_sandbox"
    assert MSG_BLOCKED_MISSING_SANDBOX in started.message

    productive = adapter.start_run(_sandbox_request(dry_run=False))
    assert productive.status == "blocked"
    assert productive.execution_gate == "blocked_productive_execution"


def test_no_private_defaults_in_gate_or_empty_request() -> None:
    empty = empty_processing_request()
    assert empty.sandbox_mode is False
    assert empty.sandbox_root is None
    assert empty.original_source_folder is None
    assert empty.copied_data_confirmed is False
    assert empty.productive_execution_allowed is False
    assert empty.execution_scope == "blocked"

    src = GATE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        # Token may appear only inside forbidden-import/test docs — not as path defaults.
        assert f'"{marker}' not in src
        assert f"'{marker}" not in src

    for line in workspace_sandbox_readiness_copy():
        for marker in PRIVATE_MARKERS:
            assert marker not in line
    assert MSG_SANDBOX_MODE_PREPARED in workspace_sandbox_readiness_copy()


def test_gate_ast_has_no_core_or_track_a_imports() -> None:
    tree = ast.parse(GATE.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for name in imported:
        assert not any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in FORBIDDEN_IMPORT_PREFIXES
        ), name


def test_gate_module_import_stays_core_free() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    sys.modules.pop("invoice_tool.ui_v2.sandbox_processing_gate", None)
    importlib.import_module("invoice_tool.ui_v2.sandbox_processing_gate")
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in FORBIDDEN_IMPORT_PREFIXES:
        assert forbidden not in newly
