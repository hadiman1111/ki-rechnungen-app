"""Track-B UI-v2 sandbox execution call boundary.

Single seam between LocalProcessingAdapter and the Core Bridge / Core Dry-Run.
Never imports processing-core (``run`` / ``processing`` / routing) at module level.
Default runner calls the Track-B core bridge, which invokes
``run_core_dry_run_sandbox`` after sandbox validation.

Tests may monkeypatch ``sandbox_core_runner`` (or inject a runner into the adapter).
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
    MSG_COMPLETED_WITH_REVIEW,
    MSG_FAILED,
    MSG_SAFETY_PROOF_COMPACT,
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
    ProcessingStatus,
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
MSG_SANDBOX_EXECUTION_COMPLETED_WITH_REVIEW = (
    f"{MSG_CLARITY_SANDBOX_COPIED_RUN} "
    "Sandbox-Lauf mit Prüffällen abgeschlossen (kopierte Testdaten)."
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
    warnings: tuple[str, ...] = field(default_factory=tuple)
    planned_moves: tuple[str, ...] = field(default_factory=tuple)
    planned_destination_count: int = 0
    safety_proof_summary: str | None = None
    bridge_status: str | None = None


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
    """Sandbox → core-bridge → Core Dry-Run seam.

    After sandbox-gate approval this seam validates a CoreBridgeRequest and
    calls ``run_core_dry_run_sandbox`` via the core bridge. It never imports or
    calls ``invoice_tool.run.run_once`` / productive processing-core paths.
    """

    refused = assert_call_args_exclude_original(args)
    if refused is not None:
        return SandboxCoreCallResult(
            ok=False,
            message=refused,
            errors=(refused,),
            safety_proof_summary=MSG_SAFETY_PROOF_COMPACT,
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
    # Legacy token only when the historical contract-required path is hit.
    if ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED in errors:
        errors = errors + ("sandbox_core_runner_unbound",)

    message = bridge_result.message or (
        MSG_SANDBOX_EXECUTION_COMPLETED
        if bridge_result.ok
        else MSG_SANDBOX_EXECUTION_FAILED
    )
    if bridge_result.safety_proof_summary and bridge_result.safety_proof_summary not in (
        message or ""
    ):
        message = f"{message} {bridge_result.safety_proof_summary}".strip()

    return SandboxCoreCallResult(
        ok=bridge_result.ok,
        message=message,
        run_id=bridge_result.run_id,
        results=tuple(bridge_result.results),
        review_items=tuple(bridge_result.review_items),
        errors=errors,
        warnings=tuple(bridge_result.warnings),
        planned_moves=tuple(bridge_result.planned_moves),
        planned_destination_count=bridge_result.planned_destination_count,
        safety_proof_summary=bridge_result.safety_proof_summary
        or MSG_SAFETY_PROOF_COMPACT,
        bridge_status=bridge_result.status.value,
    )


def map_sandbox_core_result_to_run_state(
    result: SandboxCoreCallResult,
    *,
    execution_gate: str | None = "ready_for_sandbox_execution",
    dry_run_gate: str | None = None,
    core_dry_run_status: str | None = None,
) -> ProcessingRunState:
    """Map boundary outcome to UI-v2 state — only fields provided by the result."""

    bridge_status = (result.bridge_status or "").strip()
    status: ProcessingStatus
    if result.ok and bridge_status == "completed_with_review":
        status = "completed"
        default_message = MSG_SANDBOX_EXECUTION_COMPLETED_WITH_REVIEW or MSG_COMPLETED_WITH_REVIEW
    elif result.ok:
        status = "completed"
        default_message = MSG_SANDBOX_EXECUTION_COMPLETED or MSG_COMPLETED
    elif bridge_status.startswith("blocked_missing"):
        status = "not_configured"
        default_message = result.message or MSG_SANDBOX_EXECUTION_FAILED
    elif bridge_status.startswith("blocked"):
        status = "blocked"
        default_message = result.message or MSG_SANDBOX_EXECUTION_FAILED
    else:
        status = "failed"
        default_message = result.message or MSG_SANDBOX_EXECUTION_FAILED or MSG_FAILED

    return ProcessingRunState(
        status=status,
        message=result.message or default_message,
        run_id=result.run_id,
        results=tuple(result.results),
        review_items=tuple(result.review_items),
        errors=tuple(result.errors),
        execution_gate=execution_gate,  # type: ignore[arg-type]
        dry_run_gate=dry_run_gate,  # type: ignore[arg-type]
        core_dry_run_status=core_dry_run_status,  # type: ignore[arg-type]
        warnings=tuple(result.warnings),
        planned_destination_count=result.planned_destination_count
        or len(result.planned_moves),
        safety_proof_summary=result.safety_proof_summary or MSG_SAFETY_PROOF_COMPACT,
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
    "MSG_SANDBOX_EXECUTION_COMPLETED_WITH_REVIEW",
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
