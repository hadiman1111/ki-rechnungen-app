"""Track-B UI-v2 bounded LocalProcessingAdapter.

Implements ProcessingServiceProtocol with explicit-user-input validation and a
sandbox-gated execution path. Processing-core is never imported at module level.
Live core calls go only through the injectable sandbox execution boundary after
sandbox-gate approval, never against original folders, never productive.

Does not invent results, does not touch Track A, does not auto-run on import.
"""

from __future__ import annotations

import re
from typing import Callable

from invoice_tool.ui_v2.policy_runtime_bridge import (
    MSG_POLICY_INCOMPLETE,
    MSG_UNKNOWN_EVIDENCE_REVIEW,
    RuntimePolicyIntent,
)
from invoice_tool.ui_v2.processing_contract import ProcessingRunRequest
from invoice_tool.ui_v2.processing_state import (
    MSG_DRY_RUN_AVAILABLE,
    MSG_DRY_RUN_UNAVAILABLE,
    MSG_IDLE,
    MSG_POLICY_BLOCKED,
    MSG_POLICY_NOT_READY,
    MSG_PRODUCTIVE_NOT_RELEASED,
    MSG_READY_FOR_SANDBOX_EXECUTION,
    ExecutionGateStatus,
    ProcessingRunState,
    blocked_processing_state,
    idle_processing_state,
    not_configured_processing_state,
    ready_processing_state,
)
from invoice_tool.ui_v2.sandbox_execution_boundary import (
    SandboxCoreCallArgs,
    SandboxCoreCallResult,
    build_sandbox_core_call_args,
    invoke_sandbox_execution,
    map_sandbox_core_result_to_run_state,
    sandbox_core_runner,
)
from invoice_tool.ui_v2.sandbox_processing_gate import (
    MSG_SANDBOX_CORE_DRY_ABSENT,
    SandboxPathValidationResult,
    evaluate_sandbox_gate,
)

MSG_MISSING_INPUT = "Eingangsordner fehlt. Bitte einen Ordner explizit wählen."
MSG_MISSING_OUTPUT = (
    "Ausgabeordner fehlt. Bitte wähle einen Zielordner, "
    "bevor eine Verarbeitung vorbereitet wird."
)
MSG_MISSING_PROFILE = "Profil fehlt. Bitte ein Profil explizit wählen."
MSG_MISSING_CONFIGURATION = "Konfiguration fehlt. Bitte eine Konfiguration explizit wählen."
MSG_MISSING_SOURCE = "Keine explizite Benutzerauswahl als Quelle gesetzt."
MSG_MISSING_POLICY_INTENT = (
    f"{MSG_POLICY_NOT_READY} {MSG_POLICY_INCOMPLETE} {MSG_UNKNOWN_EVIDENCE_REVIEW}"
)
MSG_USER_CONFIRMATION_REQUIRED = (
    "Explizite Benutzerbestätigung fehlt. Verarbeitung startet nur nach CTA-Bestätigung."
)
MSG_FILENAME_SOT_BLOCKED = (
    "Dateiname darf keine Beweisquelle sein; Lauf-Intent ist blockiert."
)
MSG_PRIVATE_OUTPUT_BLOCKED = (
    "Ausgabeordner ist ungültig. Private oder lokale Standardpfade sind nicht erlaubt; "
    "bitte einen explizit gewählten Zielordner setzen."
)
MSG_READY_LOCAL_ADAPTER = (
    "Anfrage ist vollständig und policy-ready; "
    "sicherer Core-Dry-Run ist angebunden; produktive Ausführung bleibt gesperrt."
)
MSG_UNKNOWN_RUN = "Kein aktiver Lauf (run_id unbekannt)."
# Backward-compatible alias for the required dry-gate wording.
MSG_CORE_DRY_UNAVAILABLE = MSG_DRY_RUN_UNAVAILABLE
MSG_READY_SANDBOX_EXECUTION = MSG_READY_FOR_SANDBOX_EXECUTION
MSG_SANDBOX_CALL_ARGS_INCOMPLETE = (
    "Sandbox-Aufrufargumente unvollständig; Ausführung wurde nicht gestartet."
)

# Core dry/no-mutation API (invoice_tool.core_dry_run) is wired via core_bridge.
CORE_DRY_RUN_STATUS: ExecutionGateStatus = "dry_run_available"

# Map sandbox reason codes onto ProcessingRunState.execution_gate markers.
_SANDBOX_REASON_TO_GATE: dict[str, ExecutionGateStatus] = {
    "blocked_missing_sandbox": "blocked_missing_sandbox",
    "blocked_missing_sandbox_root": "blocked_missing_sandbox",
    "blocked_missing_copied_data_confirmation": "blocked_missing_copied_data_confirmation",
    "blocked_original_folder": "blocked_original_folder",
    "blocked_output_inside_original": "blocked_original_folder",
    "blocked_productive_execution": "blocked_productive_execution",
    "ready_for_sandbox_execution": "ready_for_sandbox_execution",
}

# Path tokens that must never be invented as defaults and are rejected if present.
# Token/segment checks only — no filesystem access, no directory creation.
# Avoid bare substrings like "hadi" that would false-positive on usernames.
_FORBIDDEN_PRIVATE_PATH_RE = re.compile(
    r"(?:^|[/\\_\-\s])"
    r"(?:somaa|bismarck|amex|voba|volksbank|american express|test rechnungen|"
    r"programm belegerfassung)"
    r"(?:[/\\_\-\s]|$)",
    re.IGNORECASE,
)

SandboxRunner = Callable[[SandboxCoreCallArgs], SandboxCoreCallResult]


class LocalProcessingAdapter:
    """Bounded Track-B adapter: validate explicitly, sandbox-gated execution only."""

    def __init__(self, *, sandbox_runner: SandboxRunner | None = None) -> None:
        # In-memory run states only — never populated from filesystem scans.
        self._runs: dict[str, ProcessingRunState] = {}
        # Injectable sandbox core seam (tests monkeypatch module runner or inject here).
        self._sandbox_runner: SandboxRunner = sandbox_runner or sandbox_core_runner

    def core_dry_run_status(self) -> ExecutionGateStatus:
        """Whether a safe dry/no-mutation core entrypoint exists (never calls core)."""

        return CORE_DRY_RUN_STATUS

    def dry_run_gate(self) -> ExecutionGateStatus:
        """Adapter-level dry/no-mutation gate status."""

        return CORE_DRY_RUN_STATUS

    def execution_gate(self, *, dry_run: bool = True) -> ExecutionGateStatus:
        """Whether real execution may proceed for the given mode."""

        if not dry_run:
            return "productive_blocked"
        if self.core_dry_run_status() == "dry_run_available":
            return "dry_run_available"
        return "unsupported_without_core_change"

    def validate_request(self, request: ProcessingRunRequest) -> ProcessingRunState:
        """Validate request structure and policy readiness — no folder IO, no PDFs."""

        gate_disabled: ExecutionGateStatus = "disabled"
        dry_status = self.core_dry_run_status()

        if not request.has_explicit_user_source():
            return not_configured_processing_state(
                MSG_MISSING_SOURCE,
                execution_gate=gate_disabled,
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )
        if request.normalized_input_folder() is None:
            return not_configured_processing_state(
                MSG_MISSING_INPUT,
                execution_gate=gate_disabled,
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )
        if request.normalized_output_folder() is None:
            return not_configured_processing_state(
                MSG_MISSING_OUTPUT,
                execution_gate=gate_disabled,
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )
        if self._is_forbidden_private_default_path(request.normalized_output_folder()):
            return blocked_processing_state(
                MSG_PRIVATE_OUTPUT_BLOCKED,
                execution_gate=gate_disabled,
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )
        if request.normalized_profile_id() is None:
            return not_configured_processing_state(
                MSG_MISSING_PROFILE,
                execution_gate=gate_disabled,
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )
        if request.normalized_configuration_id() is None:
            return not_configured_processing_state(
                MSG_MISSING_CONFIGURATION,
                execution_gate=gate_disabled,
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )

        policy = request.effective_policy_bridge_result()
        if policy is None or policy.status == "incomplete":
            return not_configured_processing_state(
                MSG_MISSING_POLICY_INTENT,
                execution_gate=gate_disabled,
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )
        if policy.status == "blocked":
            detail = "; ".join(policy.warnings) if policy.warnings else MSG_POLICY_BLOCKED
            return blocked_processing_state(
                f"{MSG_POLICY_BLOCKED} {detail}",
                execution_gate=gate_disabled,
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )

        intent = request.policy_intent or (policy.intent if policy is not None else None)
        if intent is None:
            return not_configured_processing_state(
                MSG_MISSING_POLICY_INTENT,
                execution_gate=gate_disabled,
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )

        filename_gate = self._filename_not_source_of_truth(intent)
        if filename_gate is not None:
            return blocked_processing_state(
                filename_gate,
                execution_gate=gate_disabled,
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )

        # Structure + policy ready — does not imply productive or dry core execution.
        return ready_processing_state(
            MSG_READY_LOCAL_ADAPTER,
            execution_gate=gate_disabled,
            dry_run_gate=dry_status,
            core_dry_run_status=dry_status,
        )

    def start_run(self, request: ProcessingRunRequest) -> ProcessingRunState:
        """Start only after validate is ready and user confirmed; never auto-runs.

        Sandbox gate must approve before the sandbox execution boundary is called.
        Productive execution stays blocked. Original folders are never passed as
        processing input/output to the boundary.
        """

        validated = self.validate_request(request)
        if validated.status in {"not_configured", "blocked"}:
            return validated

        dry_status = self.core_dry_run_status()
        if not request.user_confirmed_start:
            return blocked_processing_state(
                MSG_USER_CONFIRMATION_REQUIRED,
                execution_gate="disabled",
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )

        # Productive mutation is not PO-released — always blocked.
        if (
            not request.dry_run
            or request.productive_execution_allowed
            or request.execution_scope == "productive"
        ):
            return blocked_processing_state(
                MSG_PRODUCTIVE_NOT_RELEASED,
                execution_gate="blocked_productive_execution",
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )

        sandbox = self.evaluate_sandbox_gate(request)
        if not sandbox.approved:
            return self._blocked_from_sandbox(sandbox, dry_status)

        if sandbox.execution_scope != "sandbox":
            return blocked_processing_state(
                MSG_PRODUCTIVE_NOT_RELEASED,
                execution_gate="blocked_productive_execution",
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )

        if not request.copied_data_confirmed:
            return blocked_processing_state(
                "Bestätigung für kopierte Testdaten fehlt.",
                execution_gate="blocked_missing_copied_data_confirmation",
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )

        return self._execute_sandbox_run(request, sandbox, dry_status)

    def evaluate_sandbox_gate(
        self, request: ProcessingRunRequest
    ) -> SandboxPathValidationResult:
        """Pure sandbox confinement check — no FS IO, no core import."""

        return evaluate_sandbox_gate(request)

    def _execute_sandbox_run(
        self,
        request: ProcessingRunRequest,
        sandbox: SandboxPathValidationResult,
        dry_status: ExecutionGateStatus,
    ) -> ProcessingRunState:
        """Call sandbox execution boundary with sandbox-only paths — no Track-A."""

        input_folder = sandbox.input_folder or request.normalized_input_folder()
        output_folder = sandbox.output_folder or request.normalized_output_folder()
        sandbox_root = sandbox.sandbox_root or request.normalized_sandbox_root()
        profile_id = request.normalized_profile_id()
        configuration_id = request.normalized_configuration_id()
        original = sandbox.original_source_folder or request.normalized_original_source_folder()

        if (
            input_folder is None
            or output_folder is None
            or sandbox_root is None
            or profile_id is None
            or configuration_id is None
        ):
            return blocked_processing_state(
                MSG_SANDBOX_CALL_ARGS_INCOMPLETE,
                execution_gate="blocked_missing_sandbox",
                dry_run_gate=dry_status,
                core_dry_run_status=dry_status,
            )

        # Hard exclusion: never pass original folder as processing input/output.
        if original is not None:
            norm = lambda p: p.replace("\\", "/").rstrip("/")  # noqa: E731
            o = norm(original)
            if norm(input_folder) == o or norm(input_folder).startswith(o + "/"):
                return self._blocked_from_sandbox(
                    SandboxPathValidationResult(
                        approved=False,
                        reason_code="blocked_original_folder",
                        message="Original-Quellordner darf nicht als Verarbeitungseingang verwendet werden.",
                        sandbox_root=sandbox_root,
                        input_folder=input_folder,
                        output_folder=output_folder,
                        original_source_folder=original,
                    ),
                    dry_status,
                )
            if norm(output_folder) == o or norm(output_folder).startswith(o + "/"):
                return self._blocked_from_sandbox(
                    SandboxPathValidationResult(
                        approved=False,
                        reason_code="blocked_output_inside_original",
                        message="Ausgabeordner darf nicht innerhalb des Original-Quellordners liegen.",
                        sandbox_root=sandbox_root,
                        input_folder=input_folder,
                        output_folder=output_folder,
                        original_source_folder=original,
                    ),
                    dry_status,
                )

        args = build_sandbox_core_call_args(
            input_folder=input_folder,
            output_folder=output_folder,
            sandbox_root=sandbox_root,
            profile_id=profile_id,
            configuration_id=configuration_id,
            original_source_folder=original,
        )
        # Boundary call — runner is injectable/monkeypatchable; default unbound.
        outcome = invoke_sandbox_execution(args, runner=self._sandbox_runner)
        state = map_sandbox_core_result_to_run_state(
            outcome,
            execution_gate="ready_for_sandbox_execution",
            dry_run_gate=dry_status,
            core_dry_run_status=dry_status,
        )
        if state.run_id:
            self._runs[state.run_id] = state
        return state

    def _blocked_from_sandbox(
        self,
        sandbox: SandboxPathValidationResult,
        dry_status: ExecutionGateStatus,
    ) -> ProcessingRunState:
        gate = _SANDBOX_REASON_TO_GATE.get(sandbox.reason_code, "blocked_missing_sandbox")
        message = sandbox.message
        # Only append legacy dry-absent copy when dry-run is truly unavailable.
        if (
            dry_status == "unsupported_without_core_change"
            and MSG_DRY_RUN_UNAVAILABLE not in message
            and MSG_SANDBOX_CORE_DRY_ABSENT not in message
            and gate != "blocked_productive_execution"
        ):
            message = f"{message} {MSG_SANDBOX_CORE_DRY_ABSENT}"
        elif dry_status == "dry_run_available" and MSG_SANDBOX_CORE_DRY_ABSENT in message:
            message = message.replace(MSG_SANDBOX_CORE_DRY_ABSENT, MSG_DRY_RUN_AVAILABLE).strip()
        return blocked_processing_state(
            message,
            execution_gate=gate,
            dry_run_gate=dry_status,
            core_dry_run_status=dry_status,
        )

    def get_status(self, run_id: str | None) -> ProcessingRunState:
        """Return adapter-memory state only — no filesystem scan."""

        key = (run_id or "").strip()
        if not key:
            return idle_processing_state(MSG_IDLE)
        known = self._runs.get(key)
        if known is not None:
            return known
        dry_status = self.core_dry_run_status()
        return blocked_processing_state(
            MSG_UNKNOWN_RUN,
            execution_gate="disabled",
            dry_run_gate=dry_status,
            core_dry_run_status=dry_status,
        )

    def get_results(self, run_id: str | None) -> ProcessingRunState:
        """Return real adapter-memory results only — never invent rows."""

        state = self.get_status(run_id)
        return ProcessingRunState(
            status=state.status,
            message=state.message,
            run_id=state.run_id,
            results=tuple(state.results),
            review_items=tuple(state.review_items),
            errors=tuple(state.errors),
            execution_gate=state.execution_gate,
            dry_run_gate=state.dry_run_gate,
            core_dry_run_status=state.core_dry_run_status,
            warnings=tuple(state.warnings),
            planned_destination_count=state.planned_destination_count,
            safety_proof_summary=state.safety_proof_summary,
        )

    def _is_forbidden_private_default_path(self, folder: str | None) -> bool:
        """Reject known private/local default path tokens — string-only, no FS IO."""

        if folder is None:
            return False
        value = folder.strip()
        if not value:
            return False
        # Normalize separators so token boundaries are stable.
        normalized = f"/{value.replace(chr(92), '/')}"
        return _FORBIDDEN_PRIVATE_PATH_RE.search(normalized) is not None

    def _filename_not_source_of_truth(self, intent: RuntimePolicyIntent) -> str | None:
        filename_policy = intent.filename_policy or {}
        source_policy = intent.source_of_truth_policy or {}
        if filename_policy.get("filename_is_source_of_truth") is True:
            return MSG_FILENAME_SOT_BLOCKED
        if filename_policy.get("filename_is_not_source_of_truth") is False:
            return MSG_FILENAME_SOT_BLOCKED
        if source_policy.get("filename_is_source_of_truth") is True:
            return MSG_FILENAME_SOT_BLOCKED
        if source_policy.get("primary_source") == "filename":
            return MSG_FILENAME_SOT_BLOCKED
        return None

    def _run_core_dry_no_mutation(self, request: ProcessingRunRequest) -> ProcessingRunState:
        """Delegate to the sandbox-gated dry-run path (never ``run_once``).

        Must not import invoice_tool.processing / invoice_tool.run / routing /
        classification. Productive execution remains blocked.
        """

        return self.start_run(request)
