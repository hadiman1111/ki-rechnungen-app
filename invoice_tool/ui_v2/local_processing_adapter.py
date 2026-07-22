"""Track-B UI-v2 bounded LocalProcessingAdapter.

Implements ProcessingServiceProtocol with explicit-user-input validation and a
safe blocked execution path. Processing-core is never imported at module level
and is not called while no safe dry/no-mutation core API exists.

Does not process real PDFs, does not scan folders, does not invent results,
does not touch Track A.
"""

from __future__ import annotations

from invoice_tool.ui_v2.policy_runtime_bridge import (
    MSG_POLICY_INCOMPLETE,
    MSG_UNKNOWN_EVIDENCE_REVIEW,
    RuntimePolicyIntent,
)
from invoice_tool.ui_v2.processing_contract import ProcessingRunRequest
from invoice_tool.ui_v2.processing_state import (
    MSG_IDLE,
    MSG_POLICY_BLOCKED,
    MSG_POLICY_NOT_READY,
    MSG_PRODUCTIVE_NOT_RELEASED,
    ProcessingRunState,
    blocked_processing_state,
    idle_processing_state,
    not_configured_processing_state,
    ready_processing_state,
)

MSG_MISSING_INPUT = "Eingangsordner fehlt. Bitte einen Ordner explizit wählen."
MSG_MISSING_OUTPUT = "Zielordner fehlt. Bitte einen Ausgabeordner explizit wählen."
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
MSG_READY_LOCAL_ADAPTER = (
    "Anfrage ist vollständig und policy-ready; "
    "produktive Ausführung ist noch nicht freigegeben (kein sicherer Core-Dry-Pfad)."
)
MSG_UNKNOWN_RUN = "Kein aktiver Lauf (run_id unbekannt)."
MSG_CORE_DRY_UNAVAILABLE = (
    "Kein sicherer dry/no-mutation Core-Aufruf verfügbar ohne Processing-Core-Änderung."
)


class LocalProcessingAdapter:
    """Bounded Track-B adapter: validate explicitly, never auto-run, no fake results."""

    def __init__(self) -> None:
        # In-memory run states only — never populated from filesystem scans.
        self._runs: dict[str, ProcessingRunState] = {}

    def validate_request(self, request: ProcessingRunRequest) -> ProcessingRunState:
        """Validate request structure and policy readiness — no folder IO, no PDFs."""

        if not request.has_explicit_user_source():
            return not_configured_processing_state(MSG_MISSING_SOURCE)
        if request.normalized_input_folder() is None:
            return not_configured_processing_state(MSG_MISSING_INPUT)
        if request.normalized_output_folder() is None:
            return not_configured_processing_state(MSG_MISSING_OUTPUT)
        if request.normalized_profile_id() is None:
            return not_configured_processing_state(MSG_MISSING_PROFILE)
        if request.normalized_configuration_id() is None:
            return not_configured_processing_state(MSG_MISSING_CONFIGURATION)

        policy = request.effective_policy_bridge_result()
        if policy is None or policy.status == "incomplete":
            return not_configured_processing_state(MSG_MISSING_POLICY_INTENT)
        if policy.status == "blocked":
            detail = "; ".join(policy.warnings) if policy.warnings else MSG_POLICY_BLOCKED
            return blocked_processing_state(f"{MSG_POLICY_BLOCKED} {detail}")

        intent = request.policy_intent or (policy.intent if policy is not None else None)
        if intent is None:
            return not_configured_processing_state(MSG_MISSING_POLICY_INTENT)

        filename_gate = self._filename_not_source_of_truth(intent)
        if filename_gate is not None:
            return blocked_processing_state(filename_gate)

        # Structure + policy ready — does not imply productive or dry core execution.
        return ready_processing_state(MSG_READY_LOCAL_ADAPTER)

    def start_run(self, request: ProcessingRunRequest) -> ProcessingRunState:
        """Start only after validate is ready and user confirmed; never auto-runs."""

        validated = self.validate_request(request)
        if validated.status in {"not_configured", "blocked"}:
            return validated

        if not request.user_confirmed_start:
            return blocked_processing_state(MSG_USER_CONFIRMATION_REQUIRED)

        # Productive mutation is not PO-released in this task.
        if not request.dry_run:
            return blocked_processing_state(MSG_PRODUCTIVE_NOT_RELEASED)

        # Core has no safe dry/no-mutation flag — refuse without importing core.
        return self._run_core_dry_no_mutation(request)

    def get_status(self, run_id: str | None) -> ProcessingRunState:
        """Return adapter-memory state only — no filesystem scan."""

        key = (run_id or "").strip()
        if not key:
            return idle_processing_state(MSG_IDLE)
        known = self._runs.get(key)
        if known is not None:
            return known
        return blocked_processing_state(MSG_UNKNOWN_RUN)

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
        )

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
        """Future wrapper marker for a safe dry/no-mutation core call.

        invoice_tool.run.run_once has no dry/no-mutation mode today. Calling it
        would snapshot/process PDFs and mutate outputs — forbidden without a
        separate productive PO gate and/or CORE_CHANGE_REQUIRED.

        This method therefore returns blocked by default and must not import
        invoice_tool.processing / invoice_tool.run / routing / classification.
        """

        _ = request  # explicit: request already validated; unused until dry API exists
        return blocked_processing_state(
            f"{MSG_PRODUCTIVE_NOT_RELEASED} {MSG_CORE_DRY_UNAVAILABLE}"
        )
