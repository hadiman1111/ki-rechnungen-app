"""Track-B local pilot readiness acceptance gate helpers.

Pure classification of documented acceptance criteria and non-goals.
No filesystem writes, no processing, no OCR/AI, no private defaults,
no SaaS-ready claim and no productive DATEV/cloud export claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class PilotAcceptanceStatus(str, Enum):
    """Overall local pilot acceptance outcome."""

    ACCEPTED_LOCAL_PILOT = "accepted_local_pilot"
    NOT_ACCEPTED = "not_accepted"


class CriterionKind(str, Enum):
    """Whether a matrix row is a required acceptance criterion or a non-goal."""

    ACCEPTED_REQUIRED = "accepted_required"
    EXPLICIT_NON_GOAL = "explicit_non_goal"


@dataclass(frozen=True)
class PilotAcceptanceCriterion:
    key: str
    label: str
    kind: CriterionKind
    met: bool
    detail: str


@dataclass(frozen=True)
class PilotAcceptanceMatrix:
    criteria: tuple[PilotAcceptanceCriterion, ...]
    status: PilotAcceptanceStatus
    status_label: str
    saas_ready: bool
    productive_processing_accepted: bool
    original_folder_use_accepted: bool
    datev_cloud_productive_export_accepted: bool
    local_pilot_under_sandbox_limits: bool
    remaining_release_gate: str


# Required accepted criteria (Prompt 11 §4).
REQUIRED_ACCEPTED_KEYS: tuple[str, ...] = (
    "track_b_entry_separate",
    "track_a_protection_passes",
    "sandbox_gate_blocks_unsafe",
    "sandbox_execution_boundary_exists",
    "synthetic_e2e_passes",
    "copied_realistic_validation_passes",
    "review_workflow_separates_buckets",
    "profile_policy_readiness_exists",
    "export_reporting_preview_exists",
    "onboarding_local_pilot_sandbox_only",
    "productive_processing_blocked",
    "export_preview_only",
    "no_saas_ready_claim",
    "no_private_defaults",
    "no_processing_core_change",
    "full_ui_v2_suite_passes",
)

# Explicit non-goals (must remain not accepted).
EXPLICIT_NON_GOAL_KEYS: tuple[str, ...] = (
    "not_saas_ready",
    "no_login_tenant_billing",
    "no_productive_datev_cloud_export",
    "no_productive_original_folder_processing",
    "no_real_ocr_ai_validation_in_gate",
    "no_macos_packaged_app_build",
    "no_legal_tax_approval",
    "no_production_classification_guarantee",
)

MSG_STATUS_ACCEPTED_LOCAL_PILOT = (
    "Lokale Pilotversion unter Sandbox-/Kopie-/Nicht-Produktiv-Grenzen abgenommen."
)
MSG_STATUS_NOT_ACCEPTED = "Lokale Pilot-Abnahme nicht freigegeben."
MSG_REMAINING_RELEASE_GATE = (
    "KI_RECHNUNGEN_PRODUCT_VERSION_1_FINALIZATION_AND_RELEASE_GATE_01"
)
MSG_PILOT_USER_RULE = (
    "Nur Sandbox mit kopierten Daten; Originalordner und produktive Verarbeitung bleiben gesperrt."
)


def _criterion(
    key: str,
    label: str,
    kind: CriterionKind,
    met: bool,
    detail: str,
) -> PilotAcceptanceCriterion:
    return PilotAcceptanceCriterion(
        key=key,
        label=label,
        kind=kind,
        met=bool(met),
        detail=detail,
    )


def build_pilot_acceptance_matrix(
    *,
    track_b_entry_separate: bool = True,
    track_a_protection_passes: bool = True,
    sandbox_gate_blocks_unsafe: bool = True,
    sandbox_execution_boundary_exists: bool = True,
    synthetic_e2e_passes: bool = True,
    copied_realistic_validation_passes: bool = True,
    review_workflow_separates_buckets: bool = True,
    profile_policy_readiness_exists: bool = True,
    export_reporting_preview_exists: bool = True,
    onboarding_local_pilot_sandbox_only: bool = True,
    productive_processing_blocked: bool = True,
    export_preview_only: bool = True,
    no_saas_ready_claim: bool = True,
    no_private_defaults: bool = True,
    no_processing_core_change: bool = True,
    full_ui_v2_suite_passes: bool = True,
    # Explicit non-goals: True means "correctly classified as non-goal / excluded".
    not_saas_ready_declared: bool = True,
    no_login_tenant_billing_declared: bool = True,
    no_productive_datev_cloud_export_declared: bool = True,
    no_productive_original_folder_processing_declared: bool = True,
    no_real_ocr_ai_validation_in_gate_declared: bool = True,
    no_macos_packaged_app_build_declared: bool = True,
    no_legal_tax_approval_declared: bool = True,
    no_production_classification_guarantee_declared: bool = True,
) -> PilotAcceptanceMatrix:
    """Build the formal Track-B local pilot acceptance matrix."""

    accepted_rows = (
        _criterion(
            "track_b_entry_separate",
            "Track-B-Einstieg ist von Track A getrennt",
            CriterionKind.ACCEPTED_REQUIRED,
            track_b_entry_separate,
            "app_ui_v2.py / UI-v2 bleibt paralleler Einstieg zu app_main.py.",
        ),
        _criterion(
            "track_a_protection_passes",
            "Track-A-Schutztest besteht",
            CriterionKind.ACCEPTED_REQUIRED,
            track_a_protection_passes,
            "test_track_a_internal_app_protection.py verifiziert Trennung und Schutz.",
        ),
        _criterion(
            "sandbox_gate_blocks_unsafe",
            "Sandbox-Gate blockiert unsichere/Originalpfade",
            CriterionKind.ACCEPTED_REQUIRED,
            sandbox_gate_blocks_unsafe,
            "Sandbox-Gate verhindert Original-/Unsicherheitsnutzung.",
        ),
        _criterion(
            "sandbox_execution_boundary_exists",
            "Sandbox-Ausführungsgrenze existiert",
            CriterionKind.ACCEPTED_REQUIRED,
            sandbox_execution_boundary_exists,
            "Ausführung bleibt an Sandbox-Grenze gebunden.",
        ),
        _criterion(
            "synthetic_e2e_passes",
            "Synthetischer E2E-Produktfluss besteht",
            CriterionKind.ACCEPTED_REQUIRED,
            synthetic_e2e_passes,
            "Synthetic Track-B E2E ohne reale Rechnungen/OCR/AI.",
        ),
        _criterion(
            "copied_realistic_validation_passes",
            "Copied-realistic Validation besteht",
            CriterionKind.ACCEPTED_REQUIRED,
            copied_realistic_validation_passes,
            "Sandbox mit kopierten Daten, ohne Originalmutation.",
        ),
        _criterion(
            "review_workflow_separates_buckets",
            "Review-Workflow trennt Ergebnisse/Prüfung/Fehler",
            CriterionKind.ACCEPTED_REQUIRED,
            review_workflow_separates_buckets,
            "Manuelle Prüfung; keine Buchungsfreigabe.",
        ),
        _criterion(
            "profile_policy_readiness_exists",
            "Profil-/Policy-Reife existiert",
            CriterionKind.ACCEPTED_REQUIRED,
            profile_policy_readiness_exists,
            "Profile/Policy ohne private Defaults.",
        ),
        _criterion(
            "export_reporting_preview_exists",
            "Export-/Reporting-Vorschau existiert",
            CriterionKind.ACCEPTED_REQUIRED,
            export_reporting_preview_exists,
            "Export ist Vorschau, kein Produktivexport.",
        ),
        _criterion(
            "onboarding_local_pilot_sandbox_only",
            "Onboarding erklärt lokale Pilotversion / Sandbox only",
            CriterionKind.ACCEPTED_REQUIRED,
            onboarding_local_pilot_sandbox_only,
            "Lokale Pilotreife, nicht SaaS-bereit.",
        ),
        _criterion(
            "productive_processing_blocked",
            "Produktive Verarbeitung bleibt blockiert",
            CriterionKind.ACCEPTED_REQUIRED,
            productive_processing_blocked,
            "Kein Produktiv-Ausführungs-Schalter, keine Produktivfreigabe.",
        ),
        _criterion(
            "export_preview_only",
            "Export ist nur Vorschau (kein DATEV-/Cloud-Produktivexport)",
            CriterionKind.ACCEPTED_REQUIRED,
            export_preview_only,
            "Keine produktive DATEV-/Cloud-Exportfreigabe.",
        ),
        _criterion(
            "no_saas_ready_claim",
            "Kein SaaS-Ready-Claim",
            CriterionKind.ACCEPTED_REQUIRED,
            no_saas_ready_claim,
            "Status kommuniziert ausdrücklich Nicht-SaaS.",
        ),
        _criterion(
            "no_private_defaults",
            "Keine privaten Defaults",
            CriterionKind.ACCEPTED_REQUIRED,
            no_private_defaults,
            "Keine Mandanten-/Pfad-Hardcodes.",
        ),
        _criterion(
            "no_processing_core_change",
            "Kein Processing-Core-Change in diesem Gate",
            CriterionKind.ACCEPTED_REQUIRED,
            no_processing_core_change,
            "processing/routing/classification/run unberührt.",
        ),
        _criterion(
            "full_ui_v2_suite_passes",
            "Vollständige UI-v2-Testsuite besteht",
            CriterionKind.ACCEPTED_REQUIRED,
            full_ui_v2_suite_passes,
            "Track-B UI-v2 / saas_ui_v2 Tests als Abnahmebasis.",
        ),
    )

    non_goal_rows = (
        _criterion(
            "not_saas_ready",
            "Nicht als SaaS bereit",
            CriterionKind.EXPLICIT_NON_GOAL,
            not_saas_ready_declared,
            "SaaS-Reife ist kein Abnahmeziel dieses Gates.",
        ),
        _criterion(
            "no_login_tenant_billing",
            "Kein Login/Mandant/Abrechnung",
            CriterionKind.EXPLICIT_NON_GOAL,
            no_login_tenant_billing_declared,
            "Auth/Tenant/Billing bleiben außerhalb des lokalen Pilots.",
        ),
        _criterion(
            "no_productive_datev_cloud_export",
            "Kein produktiver DATEV-/Cloud-Export",
            CriterionKind.EXPLICIT_NON_GOAL,
            no_productive_datev_cloud_export_declared,
            "Nur Exportvorschau; kein Produktivexport.",
        ),
        _criterion(
            "no_productive_original_folder_processing",
            "Keine produktive Originalordner-Verarbeitung",
            CriterionKind.EXPLICIT_NON_GOAL,
            no_productive_original_folder_processing_declared,
            "Originalordner bleiben verboten/geschützt.",
        ),
        _criterion(
            "no_real_ocr_ai_validation_in_gate",
            "Keine echte OCR/AI-Validierung in diesem Gate",
            CriterionKind.EXPLICIT_NON_GOAL,
            no_real_ocr_ai_validation_in_gate_declared,
            "Gate ohne OCR/AI-Lauf und ohne reale Rechnungen.",
        ),
        _criterion(
            "no_macos_packaged_app_build",
            "Kein macOS-App-Build in diesem Task",
            CriterionKind.EXPLICIT_NON_GOAL,
            no_macos_packaged_app_build_declared,
            "Kein flet build / keine Packaging-Pipeline.",
        ),
        _criterion(
            "no_legal_tax_approval",
            "Keine steuer-/rechtliche Freigabe",
            CriterionKind.EXPLICIT_NON_GOAL,
            no_legal_tax_approval_declared,
            "Keine steuerliche oder rechtliche Abnahme.",
        ),
        _criterion(
            "no_production_classification_guarantee",
            "Keine Garantie für produktive Belegklassifikation",
            CriterionKind.EXPLICIT_NON_GOAL,
            no_production_classification_guarantee_declared,
            "Keine Produktionsgarantie für Klassifikation.",
        ),
    )

    criteria = accepted_rows + non_goal_rows
    return classify_local_pilot_readiness(criteria)


def classify_local_pilot_readiness(
    criteria: Iterable[PilotAcceptanceCriterion],
) -> PilotAcceptanceMatrix:
    """Classify local pilot readiness from an acceptance matrix."""

    rows = tuple(criteria)
    by_key = {row.key: row for row in rows}

    required = [row for row in rows if row.kind is CriterionKind.ACCEPTED_REQUIRED]
    non_goals = [row for row in rows if row.kind is CriterionKind.EXPLICIT_NON_GOAL]

    required_ok = all(row.met for row in required) and all(
        key in by_key for key in REQUIRED_ACCEPTED_KEYS
    )
    non_goals_ok = all(row.met for row in non_goals) and all(
        key in by_key for key in EXPLICIT_NON_GOAL_KEYS
    )

    # Hard safety: never accept SaaS/productive/original/DATEV productive flags.
    saas_ready = False
    productive_processing_accepted = False
    original_folder_use_accepted = False
    datev_cloud_productive_export_accepted = False

    accepted = (
        required_ok
        and non_goals_ok
        and not saas_ready
        and not productive_processing_accepted
        and not original_folder_use_accepted
        and not datev_cloud_productive_export_accepted
        and bool(by_key.get("productive_processing_blocked") and by_key["productive_processing_blocked"].met)
        and bool(by_key.get("export_preview_only") and by_key["export_preview_only"].met)
        and bool(by_key.get("no_saas_ready_claim") and by_key["no_saas_ready_claim"].met)
        and bool(
            by_key.get("no_productive_original_folder_processing")
            and by_key["no_productive_original_folder_processing"].met
        )
    )

    status = (
        PilotAcceptanceStatus.ACCEPTED_LOCAL_PILOT
        if accepted
        else PilotAcceptanceStatus.NOT_ACCEPTED
    )
    status_label = (
        MSG_STATUS_ACCEPTED_LOCAL_PILOT if accepted else MSG_STATUS_NOT_ACCEPTED
    )

    return PilotAcceptanceMatrix(
        criteria=rows,
        status=status,
        status_label=status_label,
        saas_ready=saas_ready,
        productive_processing_accepted=productive_processing_accepted,
        original_folder_use_accepted=original_folder_use_accepted,
        datev_cloud_productive_export_accepted=datev_cloud_productive_export_accepted,
        local_pilot_under_sandbox_limits=accepted,
        remaining_release_gate=MSG_REMAINING_RELEASE_GATE,
    )


def acceptance_status_blob(matrix: PilotAcceptanceMatrix | None = None) -> str:
    """Join matrix labels for assertion helpers."""

    model = matrix or build_pilot_acceptance_matrix()
    parts = [
        model.status.value,
        model.status_label,
        model.remaining_release_gate,
        MSG_PILOT_USER_RULE,
        *(f"{item.key}:{item.label}:{item.detail}" for item in model.criteria),
    ]
    return " ".join(parts)


__all__ = (
    "CriterionKind",
    "EXPLICIT_NON_GOAL_KEYS",
    "MSG_PILOT_USER_RULE",
    "MSG_REMAINING_RELEASE_GATE",
    "MSG_STATUS_ACCEPTED_LOCAL_PILOT",
    "MSG_STATUS_NOT_ACCEPTED",
    "PilotAcceptanceCriterion",
    "PilotAcceptanceMatrix",
    "PilotAcceptanceStatus",
    "REQUIRED_ACCEPTED_KEYS",
    "acceptance_status_blob",
    "build_pilot_acceptance_matrix",
    "classify_local_pilot_readiness",
)
