"""Track-B UI-v2 local pilot onboarding and product-status helpers.

Honest packaging/status wording for local pilot readiness only.
No processing-core imports, no private defaults, no productive toggle,
no SaaS readiness claim and no DATEV productive export claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from invoice_tool.ui_v2.clarity_copy import (
    MSG_CLARITY_EXPORT_PREVIEW,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
)

# Required pilot onboarding copy (Prompt 10).
MSG_LOCAL_PILOT_SANDBOX = "Lokale Pilotversion: Sandbox mit kopierten Daten."
MSG_PRODUCTIVE_BLOCKED = MSG_CLARITY_PRODUCTIVE_NOT_RELEASED
MSG_ORIGINAL_FOLDERS_PROTECTED = "Originalordner bleiben geschützt."
MSG_EXPORT_PREVIEW_NOT_DATEV = MSG_CLARITY_EXPORT_PREVIEW
MSG_SAAS_NOT_INCLUDED = (
    "SaaS-Funktionen wie Login, Mandanten und Abrechnung sind nicht Teil "
    "dieser lokalen Pilotversion."
)

TRACK_B_ONBOARDING_STATUS_LINES = (
    MSG_LOCAL_PILOT_SANDBOX,
    MSG_PRODUCTIVE_BLOCKED,
    MSG_ORIGINAL_FOLDERS_PROTECTED,
    MSG_EXPORT_PREVIEW_NOT_DATEV,
    MSG_SAAS_NOT_INCLUDED,
)

MSG_NEXT_STEP_PILOT_ACCEPTANCE = (
    "Nächster Schritt: Pilot-Acceptance-Gate steht noch aus."
)
MSG_REVIEW_IS_MANUAL = (
    "Prüfung ist ein manueller Kontrollfluss, keine automatische Buchungsfreigabe."
)
MSG_FILENAME_NOT_TRUTH = "Dateinamen sind keine Belegwahrheit."
MSG_NO_PRIVATE_DEFAULTS = "Keine privaten Standardwerte."
MSG_NO_PRODUCTIVE_TOGGLE = "Kein Produktiv-Ausführungs-Schalter vorhanden."
MSG_STAGE_LOCAL_PILOT = "Lokale Pilotreife — nicht SaaS-bereit."

CapabilityStatus = Literal["ready", "verified", "blocked", "not_included", "preview"]


class ProductReadinessStage(str, Enum):
    """Honest product readiness stages for Track B."""

    LOCAL_PILOT_READINESS = "local_pilot_readiness"
    SAAS_READY = "saas_ready"  # declared only so tests can assert it is NOT active


@dataclass(frozen=True)
class OnboardingChecklistItem:
    key: str
    label: str
    done: bool
    required: bool = True


@dataclass(frozen=True)
class CapabilityMatrixItem:
    key: str
    label: str
    status: CapabilityStatus
    status_label: str


@dataclass(frozen=True)
class LocalPilotReadinessViewModel:
    """Testable local-pilot readiness view — no GUI, no private paths."""

    stage: ProductReadinessStage
    stage_label: str
    status_lines: tuple[str, ...]
    checklist: tuple[OnboardingChecklistItem, ...]
    next_step: str
    capability_matrix: tuple[CapabilityMatrixItem, ...]
    productive_processing_enabled: bool
    has_productive_toggle: bool
    saas_ready: bool
    datev_productive_export_ready: bool
    original_folders_protected: bool
    export_is_preview: bool
    review_is_manual: bool
    filename_is_source_of_truth: bool
    has_private_defaults: bool
    safe_start_guidance: tuple[str, ...]


def build_onboarding_checklist(
    *,
    profile_prepared: bool = False,
    copied_test_data_ready: bool = False,
    original_folders_separated: bool = True,
    sandbox_validation_run: bool = False,
    unclear_cases_reviewed: bool = False,
    export_preview_read: bool = False,
) -> tuple[OnboardingChecklistItem, ...]:
    """Build the safe local-pilot checklist (defaults remain incomplete)."""

    return (
        OnboardingChecklistItem(
            key="profile",
            label="Profil wählen oder vorbereiten.",
            done=bool(profile_prepared),
        ),
        OnboardingChecklistItem(
            key="copied_data",
            label="Kopierte Testdaten verwenden.",
            done=bool(copied_test_data_ready),
        ),
        OnboardingChecklistItem(
            key="originals_separate",
            label="Originalordner getrennt halten.",
            done=bool(original_folders_separated),
        ),
        OnboardingChecklistItem(
            key="sandbox_validation",
            label="Sandbox-Validierung ausführen.",
            done=bool(sandbox_validation_run),
        ),
        OnboardingChecklistItem(
            key="review_unclear",
            label="Unklare Fälle prüfen.",
            done=bool(unclear_cases_reviewed),
        ),
        OnboardingChecklistItem(
            key="export_preview",
            label="Exportvorschau lesen.",
            done=bool(export_preview_read),
        ),
    )


def build_local_pilot_capability_matrix() -> tuple[CapabilityMatrixItem, ...]:
    """Honest capability matrix for settings / product status."""

    return (
        CapabilityMatrixItem(
            key="sandbox_gate",
            label="Sandbox-Gate",
            status="ready",
            status_label="bereit",
        ),
        CapabilityMatrixItem(
            key="sandbox_execution_boundary",
            label="Sandbox-Ausführungsgrenze",
            status="ready",
            status_label="bereit",
        ),
        CapabilityMatrixItem(
            key="review_workflow",
            label="Prüfungs-Workflow",
            status="ready",
            status_label="bereit",
        ),
        CapabilityMatrixItem(
            key="profile_policy",
            label="Profil-/Policy-Reife",
            status="ready",
            status_label="bereit",
        ),
        CapabilityMatrixItem(
            key="export_reporting_preview",
            label="Export-/Reporting-Vorschau",
            status="preview",
            status_label="Vorschau bereit",
        ),
        CapabilityMatrixItem(
            key="track_a_protection",
            label="Track-A-Schutz",
            status="verified",
            status_label="verifiziert",
        ),
        CapabilityMatrixItem(
            key="productive_processing",
            label="Produktive Verarbeitung",
            status="blocked",
            status_label="blockiert",
        ),
        CapabilityMatrixItem(
            key="saas_login_tenant_billing",
            label="SaaS Login/Mandant/Abrechnung",
            status="not_included",
            status_label="nicht enthalten",
        ),
    )


def build_safe_start_guidance() -> tuple[str, ...]:
    """Short safe first-run guidance for pilot users."""

    return (
        MSG_LOCAL_PILOT_SANDBOX,
        MSG_PRODUCTIVE_BLOCKED,
        MSG_ORIGINAL_FOLDERS_PROTECTED,
        "Nur kopierte Testdaten verwenden — keine Originalordner als Eingang.",
        MSG_EXPORT_PREVIEW_NOT_DATEV,
        MSG_REVIEW_IS_MANUAL,
        MSG_FILENAME_NOT_TRUTH,
        MSG_SAAS_NOT_INCLUDED,
        MSG_NEXT_STEP_PILOT_ACCEPTANCE,
    )


def build_local_pilot_readiness(
    *,
    profile_prepared: bool = False,
    copied_test_data_ready: bool = False,
    original_folders_separated: bool = True,
    sandbox_validation_run: bool = False,
    unclear_cases_reviewed: bool = False,
    export_preview_read: bool = False,
) -> LocalPilotReadinessViewModel:
    """Build Track-B local pilot readiness — never claims SaaS readiness."""

    checklist = build_onboarding_checklist(
        profile_prepared=profile_prepared,
        copied_test_data_ready=copied_test_data_ready,
        original_folders_separated=original_folders_separated,
        sandbox_validation_run=sandbox_validation_run,
        unclear_cases_reviewed=unclear_cases_reviewed,
        export_preview_read=export_preview_read,
    )
    return LocalPilotReadinessViewModel(
        stage=ProductReadinessStage.LOCAL_PILOT_READINESS,
        stage_label=MSG_STAGE_LOCAL_PILOT,
        status_lines=TRACK_B_ONBOARDING_STATUS_LINES,
        checklist=checklist,
        next_step=MSG_NEXT_STEP_PILOT_ACCEPTANCE,
        capability_matrix=build_local_pilot_capability_matrix(),
        productive_processing_enabled=False,
        has_productive_toggle=False,
        saas_ready=False,
        datev_productive_export_ready=False,
        original_folders_protected=True,
        export_is_preview=True,
        review_is_manual=True,
        filename_is_source_of_truth=False,
        has_private_defaults=False,
        safe_start_guidance=build_safe_start_guidance(),
    )


def onboarding_status_blob(vm: LocalPilotReadinessViewModel | None = None) -> str:
    """Join status/guidance for assertion helpers."""

    model = vm or build_local_pilot_readiness()
    parts = [
        model.stage_label,
        model.next_step,
        *model.status_lines,
        *model.safe_start_guidance,
        *(item.label for item in model.checklist),
        *(f"{item.label}: {item.status_label}" for item in model.capability_matrix),
    ]
    return " ".join(parts)


__all__ = (
    "CapabilityMatrixItem",
    "CapabilityStatus",
    "LocalPilotReadinessViewModel",
    "MSG_EXPORT_PREVIEW_NOT_DATEV",
    "MSG_FILENAME_NOT_TRUTH",
    "MSG_LOCAL_PILOT_SANDBOX",
    "MSG_NEXT_STEP_PILOT_ACCEPTANCE",
    "MSG_NO_PRIVATE_DEFAULTS",
    "MSG_NO_PRODUCTIVE_TOGGLE",
    "MSG_ORIGINAL_FOLDERS_PROTECTED",
    "MSG_PRODUCTIVE_BLOCKED",
    "MSG_REVIEW_IS_MANUAL",
    "MSG_SAAS_NOT_INCLUDED",
    "MSG_STAGE_LOCAL_PILOT",
    "OnboardingChecklistItem",
    "ProductReadinessStage",
    "TRACK_B_ONBOARDING_STATUS_LINES",
    "build_local_pilot_capability_matrix",
    "build_local_pilot_readiness",
    "build_onboarding_checklist",
    "build_safe_start_guidance",
    "onboarding_status_blob",
)
