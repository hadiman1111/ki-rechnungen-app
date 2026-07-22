"""UI-v2 bounded processing service contract — non-GUI, no PDF, no processing-core."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

from invoice_tool.saas_product_model import default_classification_policy
from invoice_tool.ui_v2.policy_runtime_bridge import build_runtime_policy_intent
from invoice_tool.ui_v2.processing_contract import (
    SOURCE_EXPLICIT_USER_SELECTION,
    FutureProcessingAdapter,
    NotYetConnectedProcessingService,
    NullProcessingService,
    ProcessingRunRequest,
    empty_processing_request,
)
from invoice_tool.ui_v2.processing_state import (
    MSG_BLOCKED_ADAPTER,
    ProcessingRunState,
    idle_processing_state,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "invoice_tool" / "ui_v2" / "processing_contract.py"
STATE_MOD = ROOT / "invoice_tool" / "ui_v2" / "processing_state.py"
BRIDGE = ROOT / "invoice_tool" / "ui_v2" / "policy_runtime_bridge.py"


def _ready_policy_request(**kwargs) -> ProcessingRunRequest:
    bridge = build_runtime_policy_intent(default_classification_policy())
    return ProcessingRunRequest(
        policy_intent=bridge.intent,
        policy_bridge_result=bridge,
        **kwargs,
    )

PRIVATE_MARKERS = (
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


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


def test_null_service_never_emits_fake_results() -> None:
    service = NullProcessingService()
    request = _ready_policy_request(
        input_folder="/tmp/example-inbox",
        source=SOURCE_EXPLICIT_USER_SELECTION,
        dry_run=True,
    )
    started = service.start_run(request)
    assert started.status == "blocked"
    assert MSG_BLOCKED_ADAPTER in started.message
    assert started.results == tuple()
    assert started.review_items == tuple()
    assert started.run_id is None

    results = service.get_results("any-id")
    assert results.results == tuple()
    assert results.review_items == tuple()


def test_default_request_has_no_private_or_local_paths() -> None:
    request = empty_processing_request()
    assert request.input_folder is None
    assert request.output_folder is None
    assert request.profile_id is None
    assert request.configuration_id is None
    assert request.dry_run is True
    assert request.user_confirmed_start is False
    blob = " ".join(
        filter(
            None,
            (
                request.input_folder,
                request.output_folder,
                request.profile_id,
                request.configuration_id,
                request.source,
            ),
        )
    )
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker


def test_service_returns_honest_not_connected_state() -> None:
    service = NotYetConnectedProcessingService()
    missing = service.validate_request(empty_processing_request())
    assert missing.status == "not_configured"
    assert missing.results == tuple()

    with_folder_no_policy = service.validate_request(
        ProcessingRunRequest(
            input_folder="selected-inbox",
            source=SOURCE_EXPLICIT_USER_SELECTION,
        )
    )
    assert with_folder_no_policy.status == "not_configured"
    assert "Verarbeitungsregeln" in with_folder_no_policy.message
    assert with_folder_no_policy.results == tuple()

    with_folder = service.validate_request(
        _ready_policy_request(
            input_folder="selected-inbox",
            source=SOURCE_EXPLICIT_USER_SELECTION,
        )
    )
    assert with_folder.status == "blocked"
    assert MSG_BLOCKED_ADAPTER in with_folder.message
    assert with_folder.results == tuple()


def test_null_service_does_not_process_files(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    pdf = inbox / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    before = pdf.read_bytes()
    service = NullProcessingService()
    state = service.start_run(
        _ready_policy_request(
            input_folder=str(inbox),
            source=SOURCE_EXPLICIT_USER_SELECTION,
        )
    )
    assert state.status == "blocked"
    assert pdf.exists()
    assert pdf.read_bytes() == before
    assert list(inbox.iterdir()) == [pdf]


def test_future_adapter_stub_is_also_safe() -> None:
    adapter = FutureProcessingAdapter()
    state = adapter.start_run(
        _ready_policy_request(
            input_folder="selected-inbox",
            source=SOURCE_EXPLICIT_USER_SELECTION,
        )
    )
    assert state.status == "blocked"
    assert state.results == tuple()


def test_request_can_carry_optional_policy_intent() -> None:
    bridge = build_runtime_policy_intent(default_classification_policy())
    request = ProcessingRunRequest(
        input_folder="selected-inbox",
        source=SOURCE_EXPLICIT_USER_SELECTION,
        policy_intent=bridge.intent,
        policy_bridge_result=bridge,
    )
    assert request.policy_intent is not None
    assert request.policy_bridge_result is not None
    assert request.policy_bridge_result.status == "ready"


def test_idle_state_is_empty() -> None:
    state = idle_processing_state()
    assert state.status == "idle"
    assert isinstance(state, ProcessingRunState)
    assert state.results == tuple()
    assert state.review_items == tuple()
    assert state.execution_gate is None
    assert state.dry_run_gate is None
    assert state.core_dry_run_status is None


def test_processing_run_state_exposes_dry_gate_fields() -> None:
    from invoice_tool.ui_v2.processing_state import blocked_processing_state

    state = blocked_processing_state(
        "Dry-Run ohne Dateiveränderung ist im lokalen Core noch nicht verfügbar.",
        execution_gate="unsupported_without_core_change",
        dry_run_gate="unsupported_without_core_change",
        core_dry_run_status="unsupported_without_core_change",
    )
    assert state.execution_gate == "unsupported_without_core_change"
    assert state.dry_run_gate == "unsupported_without_core_change"
    assert state.core_dry_run_status == "unsupported_without_core_change"
    assert state.results == tuple()


def test_contract_modules_do_not_import_track_a_or_processing_core() -> None:
    for path in (CONTRACT, STATE_MOD, BRIDGE):
        for name in _imported_modules(path):
            assert not any(
                name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_IMPORT_PREFIXES
            ), (path.name, name)
        src = path.read_text(encoding="utf-8")
        for marker in PRIVATE_MARKERS:
            assert marker not in src, (path.name, marker)


def test_contract_import_does_not_load_processing_core() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    importlib.import_module("invoice_tool.ui_v2.processing_contract")
    importlib.import_module("invoice_tool.ui_v2.processing_state")
    importlib.import_module("invoice_tool.ui_v2.policy_runtime_bridge")
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
        "app_main",
    ):
        assert forbidden not in newly, forbidden
