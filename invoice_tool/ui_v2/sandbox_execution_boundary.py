"""Track-B UI-v2 sandbox execution call boundary.

Single seam between LocalProcessingAdapter and a future/live processing call.
Never imports processing-core at module level. Default runner is unbound so
unit tests and UI cannot accidentally trigger OCR/AI/PDF processing.

Tests monkeypatch ``sandbox_core_runner`` (or inject a runner into the adapter)
to prove sandbox-only paths are passed and results map into ProcessingRunState.

Original source folders are never part of the core call args.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from invoice_tool.ui_v2.clarity_copy import (
    MSG_CLARITY_NO_ORIGINAL_FOLDERS,
    MSG_CLARITY_SANDBOX_COPIED_RUN,
)
from invoice_tool.ui_v2.processing_state import (
    MSG_COMPLETED,
    MSG_FAILED,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)

MSG_SANDBOX_RUNNER_UNBOUND = (
    "Sandbox nicht verbunden. "
    "Echte Verarbeitung benötigt noch eine sichere Dry-Run-Schnittstelle im Core. "
    "Keine Originalordner wurden verwendet. "
    "Keine Dateien wurden verarbeitet."
)
MSG_SANDBOX_EXECUTION_COMPLETED = (
    f"{MSG_CLARITY_SANDBOX_COPIED_RUN} "
    "Sandbox-Lauf abgeschlossen (kopierte Testdaten)."
)
MSG_SANDBOX_EXECUTION_FAILED = "Sandbox-Lauf fehlgeschlagen."
MSG_SANDBOX_BOUNDARY_REFUSED_ORIGINAL = (
    "Sandbox-Ausführungsgrenze verweigert Original-Quellordner als Eingang. "
    f"{MSG_CLARITY_NO_ORIGINAL_FOLDERS}"
)


@dataclass(frozen=True)
class SandboxCoreCallArgs:
    """Arguments passed across the sandbox → core call boundary.

    ``original_source_folder`` is recorded only for exclusion checks and must
    never be used as ``input_folder`` / ``output_folder``.
    """

    input_folder: str
    output_folder: str
    sandbox_root: str
    profile_id: str
    configuration_id: str
    original_source_folder: str | None = None


@dataclass(frozen=True)
class SandboxCoreCallResult:
    """Generic outcome from the sandbox core call boundary — no invented fields."""

    ok: bool
    message: str
    run_id: str | None = None
    results: tuple[ProcessingResultSummary, ...] = field(default_factory=tuple)
    review_items: tuple[ProcessingReviewItem, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)


class SandboxCoreRunner(Protocol):
    def __call__(self, args: SandboxCoreCallArgs) -> SandboxCoreCallResult: ...


def build_sandbox_core_call_args(
    *,
    input_folder: str,
    output_folder: str,
    sandbox_root: str,
    profile_id: str,
    configuration_id: str,
    original_source_folder: str | None,
) -> SandboxCoreCallArgs:
    """Build boundary args — processing paths are sandbox-only."""

    return SandboxCoreCallArgs(
        input_folder=input_folder,
        output_folder=output_folder,
        sandbox_root=sandbox_root,
        profile_id=profile_id,
        configuration_id=configuration_id,
        original_source_folder=original_source_folder,
    )


def assert_call_args_exclude_original(args: SandboxCoreCallArgs) -> str | None:
    """Return an error message if original is used as input/output; else None."""

    original = (args.original_source_folder or "").strip()
    if not original:
        return None
    # Normalize lightly for string compare (no FS access).
    norm = lambda p: p.replace("\\", "/").rstrip("/")  # noqa: E731
    o = norm(original)
    if norm(args.input_folder) == o or norm(args.input_folder).startswith(o + "/"):
        return MSG_SANDBOX_BOUNDARY_REFUSED_ORIGINAL
    if norm(args.output_folder) == o or norm(args.output_folder).startswith(o + "/"):
        return MSG_SANDBOX_BOUNDARY_REFUSED_ORIGINAL
    return None


def sandbox_core_runner(args: SandboxCoreCallArgs) -> SandboxCoreCallResult:
    """Sandbox → core-bridge seam (Path B: dry-run contract required).

    After sandbox-gate approval this seam validates a CoreBridgeRequest and
    returns REQUIRES_CORE_DRY_RUN_CONTRACT. It never imports or calls
    ``invoice_tool.run.run_once`` / processing-core, because the core has no
    safe dry/no-mutation API today (output writes, archive moves, App Support).
    """

    refused = assert_call_args_exclude_original(args)
    if refused is not None:
        return SandboxCoreCallResult(
            ok=False,
            message=refused,
            errors=(refused,),
        )

    # Lazy import keeps module-level boundary free of accidental core coupling.
    from invoice_tool.ui_v2.core_bridge import (  # noqa: PLC0415
        ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED,
        core_bridge_request_from_sandbox_args,
        run_core_bridge_sandbox_dry_run,
    )

    bridge_request = core_bridge_request_from_sandbox_args(
        input_folder=args.input_folder,
        output_folder=args.output_folder,
        sandbox_root=args.sandbox_root,
        profile_id=args.profile_id,
        configuration_id=args.configuration_id,
        original_source_folder=args.original_source_folder,
    )
    bridge_result = run_core_bridge_sandbox_dry_run(bridge_request)
    errors = tuple(bridge_result.errors)
    # Keep legacy token for existing workspace / test detection paths.
    if ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED in errors:
        errors = errors + ("sandbox_core_runner_unbound",)
    return SandboxCoreCallResult(
        ok=False,
        message=bridge_result.message or MSG_SANDBOX_RUNNER_UNBOUND,
        run_id=bridge_result.run_id,
        results=tuple(bridge_result.results),
        review_items=tuple(bridge_result.review_items),
        errors=errors,
    )


def map_sandbox_core_result_to_run_state(
    result: SandboxCoreCallResult,
    *,
    execution_gate: str | None = "ready_for_sandbox_execution",
    dry_run_gate: str | None = None,
    core_dry_run_status: str | None = None,
) -> ProcessingRunState:
    """Map boundary outcome to UI-v2 state — only fields provided by the result."""

    if result.ok:
        return ProcessingRunState(
            status="completed",
            message=result.message or MSG_SANDBOX_EXECUTION_COMPLETED or MSG_COMPLETED,
            run_id=result.run_id,
            results=tuple(result.results),
            review_items=tuple(result.review_items),
            errors=tuple(result.errors),
            execution_gate=execution_gate,  # type: ignore[arg-type]
            dry_run_gate=dry_run_gate,  # type: ignore[arg-type]
            core_dry_run_status=core_dry_run_status,  # type: ignore[arg-type]
        )
    return ProcessingRunState(
        status="failed",
        message=result.message or MSG_SANDBOX_EXECUTION_FAILED or MSG_FAILED,
        run_id=result.run_id,
        results=tuple(result.results),
        review_items=tuple(result.review_items),
        errors=tuple(result.errors),
        execution_gate=execution_gate,  # type: ignore[arg-type]
        dry_run_gate=dry_run_gate,  # type: ignore[arg-type]
        core_dry_run_status=core_dry_run_status,  # type: ignore[arg-type]
    )


# Re-export helpers kept for callers that map counts into display shells.
def result_counts(state: ProcessingRunState) -> tuple[int, int, int]:
    """Return (result_count, review_count, error_count) from real state only."""

    return (len(state.results), len(state.review_items), len(state.errors))


def invoke_sandbox_execution(
    args: SandboxCoreCallArgs,
    *,
    runner: SandboxCoreRunner | Callable[[SandboxCoreCallArgs], SandboxCoreCallResult] | None = None,
) -> SandboxCoreCallResult:
    """Invoke the sandbox core call boundary with an optional injected runner."""

    refused = assert_call_args_exclude_original(args)
    if refused is not None:
        return SandboxCoreCallResult(ok=False, message=refused, errors=(refused,))
    active = runner if runner is not None else sandbox_core_runner
    return active(args)


__all__ = (
    "MSG_SANDBOX_BOUNDARY_REFUSED_ORIGINAL",
    "MSG_SANDBOX_EXECUTION_COMPLETED",
    "MSG_SANDBOX_EXECUTION_FAILED",
    "MSG_SANDBOX_RUNNER_UNBOUND",
    "SandboxCoreCallArgs",
    "SandboxCoreCallResult",
    "SandboxCoreRunner",
    "assert_call_args_exclude_original",
    "build_sandbox_core_call_args",
    "invoke_sandbox_execution",
    "map_sandbox_core_result_to_run_state",
    "sandbox_core_runner",
)
