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

MSG_IDLE = "Noch kein Lauf gestartet."
MSG_NOT_CONFIGURED = (
    "Verarbeitung noch nicht konfiguriert. "
    "Profil, Konfiguration und Ordner müssen später explizit gewählt werden."
)
MSG_BLOCKED_ADAPTER = "Lauf-Adapter noch nicht angebunden."
MSG_READY = "Anfrage ist vorbereitet; produktive Verarbeitung ist noch nicht angebunden."
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


@dataclass(frozen=True)
class ProcessingRunState:
    """Bounded processing run state for UI-v2 workspace."""

    status: ProcessingStatus = "idle"
    message: str = MSG_IDLE
    run_id: str | None = None
    results: tuple[ProcessingResultSummary, ...] = field(default_factory=tuple)
    review_items: tuple[ProcessingReviewItem, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_results(self) -> bool:
        return bool(self.results)

    @property
    def has_review_items(self) -> bool:
        return bool(self.review_items)


def idle_processing_state(message: str = MSG_IDLE) -> ProcessingRunState:
    return ProcessingRunState(status="idle", message=message)


def not_configured_processing_state(message: str = MSG_NOT_CONFIGURED) -> ProcessingRunState:
    return ProcessingRunState(status="not_configured", message=message)


def blocked_processing_state(message: str = MSG_BLOCKED_ADAPTER) -> ProcessingRunState:
    return ProcessingRunState(status="blocked", message=message)


def ready_processing_state(message: str = MSG_READY) -> ProcessingRunState:
    """Logical readiness only — does not imply a connected productive adapter."""

    return ProcessingRunState(status="ready", message=message)
