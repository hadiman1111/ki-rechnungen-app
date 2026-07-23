"""UI-v2 processing run state — Track B contract only.

No PDF processing, no folder reads, no processing-core imports.
Results/review items stay empty unless a real dry-run / adapter injects data.
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

# Honest outcome buckets for Track-B dry-run result mapping (Prompt 4/34).
OutcomeKind = Literal[
    "idle",
    "empty",
    "recognized_only",
    "all_review",
    "errors_only",
    "mixed",
    "failed",
    "blocked",
    "not_configured",
    "ready",
    "running",
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
MSG_DRY_RUN_AVAILABLE = (
    "Sicherer Core-Dry-Run ist verfügbar (Sandbox, keine Originalmutation)."
)
MSG_READY_FOR_SANDBOX_EXECUTION = (
    "Sandbox-Gate freigegeben; Sandbox-Ausführung gegen kopierte Testdaten "
    "ist freigegeben. Sicherer Core-Dry-Run ist angebunden."
)
MSG_RUNNING = "Prüfung läuft …"
MSG_COMPLETED = "Sandbox-Lauf abgeschlossen."
MSG_COMPLETED_WITH_REVIEW = "Sandbox-Lauf mit Prüffällen abgeschlossen."
MSG_FAILED = "Sandbox-Lauf fehlgeschlagen."
MSG_SAFETY_PROOF_COMPACT = "Originale unverändert · Produktiv gesperrt · Export Vorschau"
MSG_PLANNED_DESTINATION_PREVIEW_ONLY = (
    "Geplante Ziele sind Vorschau — keine Datei wurde geschrieben oder verschoben."
)
MSG_EMPTY_DRY_RUN = (
    "Keine Belege im Sandbox-Eingang — leerer Lauf, kein fingierter Erfolg."
)
MSG_ALL_REVIEW_OUTCOME = "Sandbox-Lauf mit Prüffällen"
MSG_MIXED_OUTCOME = "Sandbox-Lauf mit gemischten Ergebnisbereichen"


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
class ProcessingErrorItem:
    """Structured error row from a real dry-run — never invented."""

    document_name: str
    error_code: str
    message: str
    status_label: str = "fehler"


@dataclass(frozen=True)
class ProcessingPlannedDestination:
    """Data-only planned destination — preview only, never applied."""

    document_name: str
    planned_path: str
    destination_label: str | None = None
    reason: str | None = None
    applied: bool = False
    preview_only: bool = True
    # Track-B suggested naming / local extraction (Prompt 18–19/34) — optional.
    suggested_filename: str | None = None
    filename_source: str | None = None
    naming_confidence: str | None = None
    naming_reason: str | None = None
    supplier: str | None = None
    invoice_date: str | None = None
    amount: str | None = None
    document_type: str | None = None
    payment_account: str | None = None
    suggested_filename_fields: tuple[str, ...] = field(default_factory=tuple)
    extraction_method: str | None = None
    # Prompt 19/34 — canonical filename template fields.
    canonical_filename: str | None = None
    filename_template_version: str | None = None
    document_direction: str | None = None
    business_category: str | None = None
    business_category_display: str | None = None
    counterparty_name: str | None = None
    missing_fields: tuple[str, ...] = field(default_factory=tuple)
    # Prompt 20/34 — configuration filename pattern bridge.
    matched_configuration_name: str | None = None
    matched_configuration_id: str | None = None
    matched_configuration_pattern: str | None = None
    matched_configuration_reason: str | None = None
    matched_configuration_confidence: str | None = None
    filename_pattern: str | None = None
    rendered_filename: str | None = None
    placeholder_values: tuple[tuple[str, str | None], ...] = field(default_factory=tuple)
    missing_placeholders: tuple[str, ...] = field(default_factory=tuple)
    amount_format: str | None = None
    # Prompt 21/34 — amount / payment / art candidate transparency.
    amount_candidates: tuple[dict[str, object], ...] = field(default_factory=tuple)
    selected_amount: str | None = None
    selected_amount_reason: str | None = None
    rejected_amount_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    payment_field_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    selected_payment_field: str | None = None
    selected_payment_field_reason: str | None = None
    document_art_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    selected_art: str | None = None
    selected_art_reason: str | None = None
    art_ambiguity: bool = False
    available_configurations: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    evaluated_configuration_candidates: tuple[dict[str, object], ...] = field(
        default_factory=tuple
    )
    unmatched_reasons: tuple[str, ...] = field(default_factory=tuple)
    condition_results: tuple[dict[str, object], ...] = field(default_factory=tuple)
    alternative_matches: tuple[dict[str, object], ...] = field(default_factory=tuple)
    missing_configuration_rule: str | None = None
    # Prompt 23/34 — configuration coverage guidance (no auto config mutation).
    configuration_coverage_status: str | None = None
    missing_configuration_type: str | None = None
    user_guidance: str | None = None
    suggested_configuration_action: str | None = None
    guidance_severity: str | None = None
    # Prompt 27/34 — apply saved rule + preview-only matching rerun.
    rule_applied: bool = False
    applied_configuration_name: str | None = None
    applied_configuration_condition: str | None = None
    rerun_preview_after_rule_change: bool = False
    matched_after_rule_change: bool = False
    previous_matched_configuration: str | None = None
    new_matched_configuration: str | None = None


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
    warnings: tuple[str, ...] = field(default_factory=tuple)
    planned_destination_count: int = 0
    safety_proof_summary: str | None = None
    # Prompt 4/34 richer mapping — optional structured buckets.
    error_items: tuple[ProcessingErrorItem, ...] = field(default_factory=tuple)
    planned_destinations: tuple[ProcessingPlannedDestination, ...] = field(
        default_factory=tuple
    )
    outcome_kind: OutcomeKind | None = None
    # False when only aggregate counts exist without per-document rows.
    detailed_item_mapping_complete: bool = True
    # Prompt 24/34 — ISO timestamp when this run state was last built/refreshed.
    state_updated_at: str | None = None

    @property
    def has_results(self) -> bool:
        return bool(self.results)

    @property
    def has_review_items(self) -> bool:
        return bool(self.review_items)

    @property
    def recognized_count(self) -> int:
        return len(self.results)

    @property
    def review_count(self) -> int:
        return len(self.review_items)

    @property
    def error_count(self) -> int:
        if self.error_items:
            return len(self.error_items)
        return len(self.errors)


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
