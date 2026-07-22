"""LocalProcessingAdapter — non-GUI, no PDF processing, no processing-core import."""

from __future__ import annotations

import ast
import importlib
import sys
from dataclasses import replace
from pathlib import Path

from invoice_tool.saas_product_model import default_classification_policy
from invoice_tool.ui_v2.local_processing_adapter import (
    CORE_DRY_RUN_STATUS,
    MSG_MISSING_CONFIGURATION,
    MSG_MISSING_INPUT,
    MSG_MISSING_OUTPUT,
    MSG_MISSING_PROFILE,
    MSG_PRIVATE_OUTPUT_BLOCKED,
    MSG_PRODUCTIVE_NOT_RELEASED,
    MSG_USER_CONFIRMATION_REQUIRED,
    LocalProcessingAdapter,
)
from invoice_tool.ui_v2.sandbox_execution_boundary import MSG_SANDBOX_RUNNER_UNBOUND
from invoice_tool.ui_v2.sandbox_processing_gate import (
    MSG_BLOCKED_MISSING_SANDBOX,
    MSG_SANDBOX_CORE_DRY_ABSENT,
    build_sandbox_run_request,
)
from invoice_tool.ui_v2.policy_runtime_bridge import build_runtime_policy_intent
from invoice_tool.ui_v2.processing_contract import (
    SOURCE_EXPLICIT_USER_SELECTION,
    ProcessingRunRequest,
    empty_processing_request,
    make_local_processing_adapter,
)
from invoice_tool.ui_v2.processing_state import MSG_DRY_RUN_UNAVAILABLE
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "invoice_tool" / "ui_v2" / "local_processing_adapter.py"

# Hardcoded default-path markers that must never appear as invented paths.
PRIVATE_PATH_DEFAULT_MARKERS = (
    "/Users/",
    "Desktop/Programm Belegerfassung",
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


def _ready_request(**kwargs) -> ProcessingRunRequest:
    bridge = build_runtime_policy_intent(default_classification_policy())
    base = dict(
        input_folder="selected-inbox",
        output_folder="selected-outbox",
        profile_id="profile-a",
        configuration_id="config-a",
        dry_run=True,
        source=SOURCE_EXPLICIT_USER_SELECTION,
        policy_intent=bridge.intent,
        policy_bridge_result=bridge,
        user_confirmed_start=True,
    )
    base.update(kwargs)
    return ProcessingRunRequest(**base)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


def test_validate_requires_explicit_user_inputs() -> None:
    adapter = LocalProcessingAdapter()
    assert adapter.validate_request(_ready_request()).status == "ready"

    assert adapter.validate_request(_ready_request(input_folder=None)).status == "not_configured"
    assert MSG_MISSING_INPUT in adapter.validate_request(_ready_request(input_folder="")).message

    assert adapter.validate_request(_ready_request(output_folder=None)).status == "not_configured"
    assert MSG_MISSING_OUTPUT in adapter.validate_request(_ready_request(output_folder="  ")).message

    assert adapter.validate_request(_ready_request(profile_id=None)).status == "not_configured"
    assert MSG_MISSING_PROFILE in adapter.validate_request(_ready_request(profile_id="")).message

    assert adapter.validate_request(_ready_request(configuration_id=None)).status == "not_configured"
    assert (
        MSG_MISSING_CONFIGURATION
        in adapter.validate_request(_ready_request(configuration_id="")).message
    )


def test_missing_output_folder_blocks_readiness_with_required_message() -> None:
    adapter = LocalProcessingAdapter()
    state = adapter.validate_request(_ready_request(output_folder=None))
    assert state.status == "not_configured"
    assert state.message == MSG_MISSING_OUTPUT
    assert "Ausgabeordner fehlt" in state.message
    assert "Zielordner" in state.message


def test_output_folder_is_never_defaulted() -> None:
    empty = empty_processing_request()
    assert empty.output_folder is None
    for marker in PRIVATE_PATH_DEFAULT_MARKERS:
        assert marker not in (empty.output_folder or "")

    adapter = LocalProcessingAdapter()
    state = adapter.validate_request(
        ProcessingRunRequest(
            input_folder="selected-inbox",
            output_folder=None,
            profile_id="profile-a",
            configuration_id="config-a",
            source=SOURCE_EXPLICIT_USER_SELECTION,
            dry_run=True,
        )
    )
    assert state.status == "not_configured"
    assert MSG_MISSING_OUTPUT in state.message


def test_output_folder_validation_does_not_create_or_write(tmp_path: Path) -> None:
    outbox = tmp_path / "never-created-outbox"
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_text("untouched", encoding="utf-8")
    before = sentinel.read_text(encoding="utf-8")

    adapter = LocalProcessingAdapter()
    state = adapter.validate_request(
        _ready_request(output_folder=str(outbox))
    )
    assert state.status == "ready"
    assert not outbox.exists()
    assert sentinel.read_text(encoding="utf-8") == before
    assert list(tmp_path.iterdir()) == [sentinel]


def test_private_local_output_defaults_are_rejected_without_fs(tmp_path: Path) -> None:
    adapter = LocalProcessingAdapter()
    # Synthetic relative path (not created) — validation must be string-only.
    forbidden = "SOMAA-private-out"
    state = adapter.validate_request(_ready_request(output_folder=forbidden))
    assert state.status == "blocked"
    assert MSG_PRIVATE_OUTPUT_BLOCKED in state.message
    assert not (tmp_path / forbidden).exists()

    # Username-like path segments must not false-positive on private rejection.
    username_like = str(tmp_path / "selected-outbox")
    ok = adapter.validate_request(_ready_request(output_folder=username_like))
    assert ok.status == "ready"
    assert not (tmp_path / "selected-outbox").exists()


def test_missing_or_incomplete_policy_is_not_configured() -> None:
    adapter = LocalProcessingAdapter()
    no_policy = ProcessingRunRequest(
        input_folder="selected-inbox",
        output_folder="selected-outbox",
        profile_id="profile-a",
        configuration_id="config-a",
        source=SOURCE_EXPLICIT_USER_SELECTION,
        dry_run=True,
    )
    state = adapter.validate_request(no_policy)
    assert state.status == "not_configured"
    assert "Verarbeitungsregeln" in state.message
    assert "unklar" in state.message.lower() or "Prüfung" in state.message


def test_user_confirmed_start_required_for_start_run() -> None:
    adapter = LocalProcessingAdapter()
    request = _ready_request(user_confirmed_start=False)
    assert adapter.validate_request(request).status == "ready"
    started = adapter.start_run(request)
    assert started.status == "blocked"
    assert MSG_USER_CONFIRMATION_REQUIRED in started.message
    assert started.results == tuple()


def test_adapter_import_does_not_import_processing_core() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    # Drop adapter module if already loaded so import side-effects are visible.
    sys.modules.pop("invoice_tool.ui_v2.local_processing_adapter", None)
    importlib.import_module("invoice_tool.ui_v2.local_processing_adapter")
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in FORBIDDEN_IMPORT_PREFIXES:
        assert forbidden not in newly, forbidden
        assert not any(name.startswith(forbidden + ".") for name in newly), forbidden


def test_adapter_ast_has_no_core_or_track_a_imports() -> None:
    for name in _imported_modules(ADAPTER):
        assert not any(
            name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_IMPORT_PREFIXES
        ), name


def test_validate_does_not_read_folders_or_process_pdfs(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    pdf = inbox / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    before = pdf.read_bytes()
    # Intentionally do not create outbox — validate must not touch FS.
    adapter = LocalProcessingAdapter()
    state = adapter.validate_request(
        _ready_request(input_folder=str(inbox), output_folder=str(outbox))
    )
    assert state.status == "ready"
    assert not outbox.exists()
    assert pdf.read_bytes() == before
    assert list(inbox.iterdir()) == [pdf]


def test_start_run_blocked_when_sandbox_missing(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    outbox.mkdir()
    pdf = inbox / "rechnung.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    before = list(inbox.iterdir())
    before_bytes = pdf.read_bytes()
    before_out = list(outbox.iterdir())

    before_modules = set(sys.modules)
    adapter = LocalProcessingAdapter()
    assert adapter.core_dry_run_status() == "dry_run_available"
    assert adapter.dry_run_gate() == CORE_DRY_RUN_STATUS
    started = adapter.start_run(
        _ready_request(input_folder=str(inbox), output_folder=str(outbox))
    )
    after_modules = set(sys.modules)
    newly = after_modules - before_modules

    assert started.status == "blocked"
    assert MSG_BLOCKED_MISSING_SANDBOX in started.message
    assert MSG_SANDBOX_CORE_DRY_ABSENT not in started.message
    assert started.core_dry_run_status == "dry_run_available"
    assert started.dry_run_gate == "dry_run_available"
    assert started.execution_gate == "blocked_missing_sandbox"
    assert started.results == tuple()
    assert started.review_items == tuple()
    assert started.run_id is None
    assert list(inbox.iterdir()) == before
    assert pdf.read_bytes() == before_bytes
    assert list(outbox.iterdir()) == before_out
    for forbidden in (
        "invoice_tool.processing",
        "invoice_tool.run",
        "invoice_tool.routing",
        "invoice_tool.classification",
    ):
        assert forbidden not in newly


def test_start_run_sandbox_boundary_without_live_core_call(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    original = tmp_path / "original-source"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    original.mkdir()
    pdf = inbox / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    before = pdf.read_bytes()

    bridge = build_runtime_policy_intent(default_classification_policy())
    before_modules = set(sys.modules)
    adapter = LocalProcessingAdapter()
    started = adapter.start_run(
        build_sandbox_run_request(
            sandbox_root=str(sandbox),
            input_folder=str(inbox),
            output_folder=str(outbox),
            original_source_folder=str(original),
            profile_id="profile-a",
            configuration_id="config-a",
            policy_intent=bridge.intent,
            policy_bridge_result=bridge,
        )
    )
    newly = set(sys.modules) - before_modules

    # Real Core Dry-Run is wired — PDF without OCR lands honestly in review.
    assert started.status == "completed"
    assert started.execution_gate == "ready_for_sandbox_execution"
    assert started.core_dry_run_status == "dry_run_available"
    assert started.results == tuple()
    assert len(started.review_items) == 1
    assert pdf.read_bytes() == before
    assert list(outbox.iterdir()) == []
    for forbidden in (
        "invoice_tool.processing",
        "invoice_tool.run",
        "invoice_tool.routing",
        "invoice_tool.classification",
    ):
        assert forbidden not in newly


def test_dry_gate_visible_on_ready_validate_state() -> None:
    adapter = LocalProcessingAdapter()
    state = adapter.validate_request(_ready_request())
    assert state.status == "ready"
    assert state.core_dry_run_status == "dry_run_available"
    assert state.dry_run_gate == "dry_run_available"
    assert state.execution_gate == "disabled"


def test_no_fake_results_from_status_or_results() -> None:
    adapter = LocalProcessingAdapter()
    started = adapter.start_run(_ready_request())
    assert started.results == tuple()
    assert started.review_items == tuple()
    assert adapter.get_results(None).results == tuple()
    assert adapter.get_results("unknown").results == tuple()
    assert adapter.get_status(None).status == "idle"


def test_adapter_source_has_no_private_path_defaults() -> None:
    src = ADAPTER.read_text(encoding="utf-8")
    for marker in PRIVATE_PATH_DEFAULT_MARKERS:
        assert marker not in src, marker


def test_filename_is_never_source_of_truth_gate() -> None:
    adapter = LocalProcessingAdapter()
    request = _ready_request()
    assert request.policy_intent is not None
    bad_intent = replace(
        request.policy_intent,
        filename_policy={
            **request.policy_intent.filename_policy,
            "filename_is_source_of_truth": True,
            "filename_is_not_source_of_truth": False,
        },
    )
    bad = replace(request, policy_intent=bad_intent)
    state = adapter.validate_request(bad)
    assert state.status == "blocked"
    assert "Dateiname" in state.message


def test_unknown_evidence_remains_review_through_policy_intent() -> None:
    request = _ready_request()
    assert request.policy_intent is not None
    assert request.policy_intent.unknown_evidence_policy["unknown_payment_evidence_target"] == "unklar"
    assert request.policy_intent.review_policy["unknown_evidence_goes_to_review"] is True
    assert request.policy_bridge_result is not None
    assert request.policy_bridge_result.review_required_reason


def test_track_a_not_imported_by_factory_or_adapter() -> None:
    before = set(sys.modules)
    adapter = make_local_processing_adapter()
    assert adapter.__class__.__name__ == "LocalProcessingAdapter"
    after = set(sys.modules)
    newly = after - before
    for forbidden in ("app_main", "invoice_tool.gui", "invoice_tool.ui_workspace"):
        assert forbidden not in newly


def test_productive_dry_run_false_stays_blocked() -> None:
    adapter = LocalProcessingAdapter()
    started = adapter.start_run(_ready_request(dry_run=False))
    assert started.status == "blocked"
    assert MSG_PRODUCTIVE_NOT_RELEASED in started.message
    assert started.execution_gate == "blocked_productive_execution"
    assert started.core_dry_run_status == "dry_run_available"
    assert started.results == tuple()


def test_default_workspace_state_does_not_auto_select_local_adapter() -> None:
    state = UiV2State()
    assert state.processing_service.__class__.__name__ == "NotYetConnectedProcessingService"
    assert state.workspace_output_folder_override is None


def test_run_core_dry_delegate_never_imports_processing_core() -> None:
    adapter = LocalProcessingAdapter()
    before = set(sys.modules)
    # Missing sandbox → blocked before dry-run call; still no processing-core import.
    blocked = adapter._run_core_dry_no_mutation(_ready_request())
    after = set(sys.modules)
    newly = after - before
    assert blocked.status == "blocked"
    assert MSG_BLOCKED_MISSING_SANDBOX in blocked.message
    for forbidden in (
        "invoice_tool.processing",
        "invoice_tool.run",
        "invoice_tool.routing",
        "invoice_tool.classification",
    ):
        assert forbidden not in newly
