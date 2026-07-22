"""UI-v2 processing run state — Track B contract only.

No PDF processing, no folder reads, no processing-core imports.
Results/review items stay empty unless a future adapter injects real data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ProcessingStatus = Literal[
    "idle",
    "not_configured",
    "ready",
    "running",
    "completed",
    "failed",
    "blocked",
]

# Explicit dry / execution gate markers for LocalProcessingAdapter readiness.
ExecutionGateStatus = Literal[
    "disabled",
    "dry_run_available",
    "productive_blocked",
    "unsupported_without_core_change",
    # Sandbox processing run gate (Track B only — no core call implied).
    "blocked_missing_sandbox",
    "blocked_original_folder",
    "blocked_missing_copied_data_confirmation",
    "blocked_productive_execution",
    "ready_for_sandbox_execution",
]

MSG_IDLE = "Noch kein Lauf gestartet."
MSG_NOT_CONFIGURED = (
    "Verarbeitung noch nicht konfiguriert. "
    "Profil, Konfiguration und Ordner müssen später explizit gewählt werden."
)
MSG_BLOCKED_ADAPTER = "Lauf-Adapter noch nicht angebunden."
MSG_POLICY_NOT_READY = "Verarbeitungsregeln sind noch nicht vollständig konfiguriert."
MSG_POLICY_BLOCKED = "Verarbeitungsregeln blockieren den Lauf-Intent."
MSG_READY = "Anfrage ist vorbereitet; produktive Verarbeitung ist noch nicht angebunden."
MSG_PRODUCTIVE_NOT_RELEASED = (
    "Lokaler Verarbeitungsadapter ist vorbereitet, aber produktive Ausführung "
    "ist noch nicht freigegeben."
)
MSG_DRY_RUN_UNAVAILABLE = (
    "Dry-Run ohne Dateiveränderung ist im lokalen Core noch nicht verfügbar."
)
MSG_READY_FOR_SANDBOX_EXECUTION = (
    "Sandbox-Gate freigegeben; Sandbox-Ausführung gegen kopierte Testdaten "
    "ist freigegeben. Core-Dry-Run ist noch nicht vorhanden."
)
MSG_RUNNING = "Lauf läuft (nur über einen zukünftigen Adapter)."
MSG_COMPLETED = "Lauf abgeschlossen."
MSG_FAILED = "Lauf fehlgeschlagen."


@dataclass(frozen=True)
class ProcessingResultSummary:
    """Generic result row for UI-v2 — no payment/private fields by default."""

    document_name: str
    document_type: str
    classification_status: str
    status_label: str
    confidence_label: str | None = None
    target_hint: str | None = None


@dataclass(frozen=True)
class ProcessingReviewItem:
    """Generic review row — empty unless a real run injects items."""

    document_name: str
    reason: str
    status_label: str = "unklar"
    # Optional detail-shell fields — never invent private classification values.
    document_id: str | None = None
    evidence_summary: str | None = None
    next_action_hint: str | None = None


@dataclass(frozen=True)
class ProcessingRunState:
    """Bounded processing run state for UI-v2 workspace."""

    status: ProcessingStatus = "idle"
    message: str = MSG_IDLE
    run_id: str | None = None
    results: tuple[ProcessingResultSummary, ...] = field(default_factory=tuple)
    review_items: tuple[ProcessingReviewItem, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    # Dry / no-mutation gate visibility (None = not evaluated / not applicable).
    execution_gate: ExecutionGateStatus | None = None
    dry_run_gate: ExecutionGateStatus | None = None
    core_dry_run_status: ExecutionGateStatus | None = None

    @property
    def has_results(self) -> bool:
        return bool(self.results)

    @property
    def has_review_items(self) -> bool:
        return bool(self.review_items)


def idle_processing_state(message: str = MSG_IDLE) -> ProcessingRunState:
    return ProcessingRunState(status="idle", message=message)


def not_configured_processing_state(
    message: str = MSG_NOT_CONFIGURED,
    *,
    execution_gate: ExecutionGateStatus | None = None,
    dry_run_gate: ExecutionGateStatus | None = None,
    core_dry_run_status: ExecutionGateStatus | None = None,
) -> ProcessingRunState:
    return ProcessingRunState(
        status="not_configured",
        message=message,
        execution_gate=execution_gate,
        dry_run_gate=dry_run_gate,
        core_dry_run_status=core_dry_run_status,
    )


def blocked_processing_state(
    message: str = MSG_BLOCKED_ADAPTER,
    *,
    execution_gate: ExecutionGateStatus | None = None,
    dry_run_gate: ExecutionGateStatus | None = None,
    core_dry_run_status: ExecutionGateStatus | None = None,
) -> ProcessingRunState:
    return ProcessingRunState(
        status="blocked",
        message=message,
        execution_gate=execution_gate,
        dry_run_gate=dry_run_gate,
        core_dry_run_status=core_dry_run_status,
    )


def ready_processing_state(
    message: str = MSG_READY,
    *,
    execution_gate: ExecutionGateStatus | None = None,
    dry_run_gate: ExecutionGateStatus | None = None,
    core_dry_run_status: ExecutionGateStatus | None = None,
) -> ProcessingRunState:
    """Logical readiness only — does not imply a connected productive adapter."""

    return ProcessingRunState(
        status="ready",
        message=message,
        execution_gate=execution_gate,
        dry_run_gate=dry_run_gate,
        core_dry_run_status=core_dry_run_status,
    )
