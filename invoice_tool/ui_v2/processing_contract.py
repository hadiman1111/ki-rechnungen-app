"""UI-v2 bounded processing service contract (Track B).

Defines how UI-v2 will later request a processing run and read status/results.
Default implementation never processes PDFs, never reads real folders, and
never emits fake results. Real processing bridge is a separate PO-gated task.

Does not import invoice_tool.processing / invoice_tool.run / routing / classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from invoice_tool.ui_v2.processing_state import (
    MSG_BLOCKED_ADAPTER,
    MSG_IDLE,
    MSG_NOT_CONFIGURED,
    ProcessingRunState,
    blocked_processing_state,
    idle_processing_state,
    not_configured_processing_state,
)

# Explicit request provenance — never invent private/local default paths.
SOURCE_EXPLICIT_USER_SELECTION = "explicit_user_selection"
SOURCE_UNSET = "unset"

ALLOWED_REQUEST_SOURCES = frozenset({SOURCE_EXPLICIT_USER_SELECTION})


@dataclass(frozen=True)
class ProcessingRunRequest:
    """User-scoped run request. Folders must come from explicit UI selection."""

    input_folder: str | None = None
    output_folder: str | None = None
    profile_id: str | None = None
    configuration_id: str | None = None
    dry_run: bool = True
    source: str = SOURCE_UNSET

    def normalized_input_folder(self) -> str | None:
        value = (self.input_folder or "").strip()
        return value or None

    def normalized_output_folder(self) -> str | None:
        value = (self.output_folder or "").strip()
        return value or None

    def has_explicit_user_source(self) -> bool:
        return self.source in ALLOWED_REQUEST_SOURCES


def empty_processing_request() -> ProcessingRunRequest:
    """Safe blank request — no private/local path defaults."""

    return ProcessingRunRequest(
        input_folder=None,
        output_folder=None,
        profile_id=None,
        configuration_id=None,
        dry_run=True,
        source=SOURCE_UNSET,
    )


@runtime_checkable
class ProcessingServiceProtocol(Protocol):
    """Contract for UI-v2 → processing adapter (validate / start / status / results)."""

    def validate_request(self, request: ProcessingRunRequest) -> ProcessingRunState:
        """Validate a run request without starting productive processing."""

    def start_run(self, request: ProcessingRunRequest) -> ProcessingRunState:
        """Start a run if the adapter allows it; otherwise return an honest blocked state."""

    def get_status(self, run_id: str | None) -> ProcessingRunState:
        """Return current status for a run id (or idle when unknown)."""

    def get_results(self, run_id: str | None) -> ProcessingRunState:
        """Return results for a run id — empty unless a real adapter injects them."""


class NotYetConnectedProcessingService:
    """Safe default service: no PDFs, no folder IO, no fake results, no core imports."""

    def validate_request(self, request: ProcessingRunRequest) -> ProcessingRunState:
        if not request.has_explicit_user_source() or request.normalized_input_folder() is None:
            return not_configured_processing_state(MSG_NOT_CONFIGURED)
        # Even with folders selected, productive adapter is not connected.
        return blocked_processing_state(MSG_BLOCKED_ADAPTER)

    def start_run(self, request: ProcessingRunRequest) -> ProcessingRunState:
        validated = self.validate_request(request)
        if validated.status == "not_configured":
            return validated
        # Never process files — honest blocked state only.
        return blocked_processing_state(
            f"{MSG_BLOCKED_ADAPTER} Keine produktive Verarbeitung gestartet."
        )

    def get_status(self, run_id: str | None) -> ProcessingRunState:
        if not (run_id or "").strip():
            return idle_processing_state(MSG_IDLE)
        return blocked_processing_state(
            f"{MSG_BLOCKED_ADAPTER} Kein aktiver Lauf (run_id unbekannt)."
        )

    def get_results(self, run_id: str | None) -> ProcessingRunState:
        state = self.get_status(run_id)
        # Explicitly empty — never invent result/review rows.
        return ProcessingRunState(
            status=state.status,
            message=state.message,
            run_id=None,
            results=tuple(),
            review_items=tuple(),
            errors=state.errors,
        )


# Alias preferred in task wording.
NullProcessingService = NotYetConnectedProcessingService


class FutureProcessingAdapter:
    """Reserved slot for a future local/runtime bridge.

    Must not import processing.py / run.py here. Wiring a real bounded adapter
    is a separate next task under PO gate (policy-to-runtime + processing adapter).
    """

    def __init__(self) -> None:
        self._inner = NotYetConnectedProcessingService()

    def validate_request(self, request: ProcessingRunRequest) -> ProcessingRunState:
        return self._inner.validate_request(request)

    def start_run(self, request: ProcessingRunRequest) -> ProcessingRunState:
        return self._inner.start_run(request)

    def get_status(self, run_id: str | None) -> ProcessingRunState:
        return self._inner.get_status(run_id)

    def get_results(self, run_id: str | None) -> ProcessingRunState:
        return self._inner.get_results(run_id)


LocalProcessingAdapterProtocol = ProcessingServiceProtocol


def default_processing_service() -> NotYetConnectedProcessingService:
    return NotYetConnectedProcessingService()
