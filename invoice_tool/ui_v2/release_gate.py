"""Track-B Product Version 1 final release gate helpers.

Pure classification of documented final release criteria and limitations.
No filesystem writes, no processing, no OCR/AI, no private defaults,
no SaaS-ready claim and no productive DATEV/cloud export claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ProductVersionReleaseStatus(str, Enum):
    """Overall Product Version 1 local pilot release outcome."""

    PRODUCT_VERSION_1_LOCAL_PILOT_RELEASED = "product_version_1_local_pilot_released"
    PRODUCT_VERSION_1_LOCAL_PILOT_RELEASED_WITH_LIMITATIONS = (
        "product_version_1_local_pilot_released_with_limitations"
    )
    PRODUCT_VERSION_1_FINAL_GATE_BLOCKED = "product_version_1_final_gate_blocked"
    PRODUCT_VERSION_1_FINAL_GATE_FAIL_UNSAFE = "product_version_1_final_gate_fail_unsafe"


@dataclass(frozen=True)
class ProductVersionReleaseCriterion:
    key: str
    label: str
    met: bool
    detail: str


@dataclass(frozen=True)
class PromptCompletionRow:
    prompt: int
    title: str
    complete: bool


@dataclass(frozen=True)
class ProductVersionReleaseMatrix:
    criteria: tuple[ProductVersionReleaseCriterion, ...]
    prompts: tuple[PromptCompletionRow, ...]
    status: ProductVersionReleaseStatus
    status_label: str
    saas_ready: bool
    productive_processing_ready: bool
    original_folder_processing_allowed: bool
    datev_cloud_productive_export_ready: bool
    local_pilot_with_limitations: bool
    release_tag_name: str
    remaining_prompts: int


# Final release criteria (Prompt 12 §4) — exactly 20.
FINAL_RELEASE_CRITERION_KEYS: tuple[str, ...] = (
    "prompts_1_to_11_documented_complete",
    "pilot_acceptance_accepted_local_pilot",
    "track_b_entry_separate_from_track_a",
    "track_a_protection_test_passes",
    "track_a_protected_files_unchanged",
    "processing_core_untouched",
    "sandbox_gate_active",
    "sandbox_execution_boundary_active",
    "synthetic_e2e_passes",
    "copied_realistic_validation_passes",
    "review_workflow_passes",
    "profile_policy_readiness_passes",
    "export_reporting_preview_passes",
    "onboarding_and_limitations_docs_exist",
    "productive_processing_blocked",
    "original_folder_use_forbidden",
    "saas_readiness_excluded",
    "datev_cloud_productive_export_excluded",
    "no_private_defaults",
    "full_ui_v2_suite_passes",
)

PROMPT_COMPLETION_TABLE: tuple[tuple[int, str], ...] = (
    (1, "Sandbox Processing Run Gate"),
    (2, "Sandbox Execution Wiring"),
    (3, "Review Workflow Completion"),
    (4, "Profile Policy Completion"),
    (5, "Export / Reporting Completion"),
    (6, "Track A Internal App Regression and Protection Gate"),
    (7, "Synthetic Track-B E2E Product Flow"),
    (8, "Sandbox Copied Real Data Validation"),
    (9, "Quality Fixes after Sandbox Validation"),
    (10, "Product Packaging and Onboarding Readiness"),
    (11, "Pilot Readiness Acceptance Gate"),
    (12, "Product Version 1 Finalization and Release Gate"),
)

RELEASE_TAG_NAME = "product-v1-local-pilot-2026-07-22"

MSG_STATUS_RELEASED = "Produktversion 1 lokale Pilotversion freigegeben."
MSG_STATUS_RELEASED_WITH_LIMITATIONS = (
    "Produktversion 1 lokale Pilotversion mit Limitationen freigegeben "
    "(nicht SaaS-/produktiv-bereit)."
)
MSG_STATUS_BLOCKED = "Produktversion 1 Final-Release-Gate blockiert."
MSG_STATUS_FAIL_UNSAFE = "Produktversion 1 Final-Release-Gate unsicher fehlgeschlagen."

MSG_LOCAL_PILOT_RULE = (
    "Nur Sandbox mit kopierten Daten; Originalordner, produktive Verarbeitung, "
    "SaaS-Reife und DATEV-/Cloud-Produktivexport bleiben ausgeschlossen."
)


def _criterion(
    key: str,
    label: str,
    met: bool,
    detail: str,
) -> ProductVersionReleaseCriterion:
    return ProductVersionReleaseCriterion(
        key=key,
        label=label,
        met=bool(met),
        detail=detail,
    )


def build_prompt_completion_table(
    *,
    prompts_1_to_11_complete: bool = True,
    prompt_12_complete: bool = True,
) -> tuple[PromptCompletionRow, ...]:
    """Build the Prompt 1–12 completion table for Product Version 1."""

    rows: list[PromptCompletionRow] = []
    for number, title in PROMPT_COMPLETION_TABLE:
        if number <= 11:
            complete = prompts_1_to_11_complete
        else:
            complete = prompt_12_complete
        rows.append(
            PromptCompletionRow(prompt=number, title=title, complete=bool(complete))
        )
    return tuple(rows)


def build_product_v1_release_matrix(
    *,
    prompts_1_to_11_documented_complete: bool = True,
    pilot_acceptance_accepted_local_pilot: bool = True,
    track_b_entry_separate_from_track_a: bool = True,
    track_a_protection_test_passes: bool = True,
    track_a_protected_files_unchanged: bool = True,
    processing_core_untouched: bool = True,
    sandbox_gate_active: bool = True,
    sandbox_execution_boundary_active: bool = True,
    synthetic_e2e_passes: bool = True,
    copied_realistic_validation_passes: bool = True,
    review_workflow_passes: bool = True,
    profile_policy_readiness_passes: bool = True,
    export_reporting_preview_passes: bool = True,
    onboarding_and_limitations_docs_exist: bool = True,
    productive_processing_blocked: bool = True,
    original_folder_use_forbidden: bool = True,
    saas_readiness_excluded: bool = True,
    datev_cloud_productive_export_excluded: bool = True,
    no_private_defaults: bool = True,
    full_ui_v2_suite_passes: bool = True,
    prompt_12_complete: bool = True,
    unsafe_failure: bool = False,
) -> ProductVersionReleaseMatrix:
    """Build the formal Product Version 1 local pilot release matrix."""

    criteria = (
        _criterion(
            "prompts_1_to_11_documented_complete",
            "Prompt 1 bis 11 sind dokumentiert abgeschlossen",
            prompts_1_to_11_documented_complete,
            "Masterplan-Prompts 1–11 haben abgeschlossene Audits/Reports.",
        ),
        _criterion(
            "pilot_acceptance_accepted_local_pilot",
            "Pilot-Abnahme ist ACCEPTED_LOCAL_PILOT",
            pilot_acceptance_accepted_local_pilot,
            "Prompt-11-Abnahmeentscheidung bleibt ACCEPTED_LOCAL_PILOT.",
        ),
        _criterion(
            "track_b_entry_separate_from_track_a",
            "Track-B-Einstieg bleibt von Track A getrennt",
            track_b_entry_separate_from_track_a,
            "app_ui_v2.py bleibt paralleler Einstieg zu app_main.py.",
        ),
        _criterion(
            "track_a_protection_test_passes",
            "Track-A-Schutztest besteht",
            track_a_protection_test_passes,
            "test_track_a_internal_app_protection.py bleibt Teil der Freigabebasis.",
        ),
        _criterion(
            "track_a_protected_files_unchanged",
            "Track-A-geschützte Dateien sind unverändert",
            track_a_protected_files_unchanged,
            "Keine Track-A-Behavior-Änderung in diesem Release-Gate.",
        ),
        _criterion(
            "processing_core_untouched",
            "Processing-Core ist unberührt",
            processing_core_untouched,
            "processing/routing/classification/target_routing/run unverändert.",
        ),
        _criterion(
            "sandbox_gate_active",
            "Sandbox-Gate bleibt aktiv",
            sandbox_gate_active,
            "Sandbox-Gate blockiert unsichere/Originalpfade.",
        ),
        _criterion(
            "sandbox_execution_boundary_active",
            "Sandbox-Ausführungsgrenze bleibt aktiv",
            sandbox_execution_boundary_active,
            "Ausführung bleibt an Sandbox-Grenze gebunden.",
        ),
        _criterion(
            "synthetic_e2e_passes",
            "Synthetischer E2E besteht",
            synthetic_e2e_passes,
            "Synthetic Track-B E2E ohne reale Rechnungen/OCR/AI.",
        ),
        _criterion(
            "copied_realistic_validation_passes",
            "Copied-realistic Validation besteht",
            copied_realistic_validation_passes,
            "Sandbox mit kopierten Daten, ohne Originalmutation.",
        ),
        _criterion(
            "review_workflow_passes",
            "Review-Workflow besteht",
            review_workflow_passes,
            "Ergebnisse/Prüfung/Fehler getrennt; keine Buchungsfreigabe.",
        ),
        _criterion(
            "profile_policy_readiness_passes",
            "Profil-/Policy-Reife besteht",
            profile_policy_readiness_passes,
            "Profile/Policy ohne private Defaults.",
        ),
        _criterion(
            "export_reporting_preview_passes",
            "Export-/Reporting-Vorschau besteht",
            export_reporting_preview_passes,
            "Export ist Vorschau, kein Produktivexport.",
        ),
        _criterion(
            "onboarding_and_limitations_docs_exist",
            "Onboarding- und Limitations-Docs existieren",
            onboarding_and_limitations_docs_exist,
            "Lokale Pilot-Docs und Limitations sind vorhanden.",
        ),
        _criterion(
            "productive_processing_blocked",
            "Produktive Verarbeitung bleibt blockiert",
            productive_processing_blocked,
            "Kein Produktiv-Ausführungs-Schalter, keine Produktivfreigabe.",
        ),
        _criterion(
            "original_folder_use_forbidden",
            "Originalordner-Nutzung bleibt verboten",
            original_folder_use_forbidden,
            "Originalordner bleiben geschützt und getrennt.",
        ),
        _criterion(
            "saas_readiness_excluded",
            "SaaS-Reife bleibt ausgeschlossen",
            saas_readiness_excluded,
            "Lokale Pilotversion ist ausdrücklich nicht SaaS-bereit.",
        ),
        _criterion(
            "datev_cloud_productive_export_excluded",
            "DATEV-/Cloud-Produktivexport bleibt ausgeschlossen",
            datev_cloud_productive_export_excluded,
            "Keine produktive DATEV-/Cloud-Exportfreigabe.",
        ),
        _criterion(
            "no_private_defaults",
            "Keine privaten Defaults",
            no_private_defaults,
            "Keine Mandanten-/Pfad-Hardcodes in der Release-Oberfläche.",
        ),
        _criterion(
            "full_ui_v2_suite_passes",
            "Vollständige UI-v2-Testsuite besteht",
            full_ui_v2_suite_passes,
            "Track-B UI-v2 / saas_ui_v2 Tests als Freigabebasis.",
        ),
    )

    prompts = build_prompt_completion_table(
        prompts_1_to_11_complete=prompts_1_to_11_documented_complete,
        prompt_12_complete=prompt_12_complete,
    )
    return classify_product_v1_release(
        criteria,
        prompts=prompts,
        unsafe_failure=unsafe_failure,
    )


def classify_product_v1_release(
    criteria: Iterable[ProductVersionReleaseCriterion],
    *,
    prompts: Iterable[PromptCompletionRow] | None = None,
    unsafe_failure: bool = False,
) -> ProductVersionReleaseMatrix:
    """Classify Product Version 1 release from the final criteria matrix."""

    rows = tuple(criteria)
    by_key = {row.key: row for row in rows}
    prompt_rows = (
        tuple(prompts)
        if prompts is not None
        else build_prompt_completion_table()
    )

    # Hard safety flags — never claim SaaS/productive/original/DATEV productive.
    saas_ready = False
    productive_processing_ready = False
    original_folder_processing_allowed = False
    datev_cloud_productive_export_ready = False

    if unsafe_failure:
        return ProductVersionReleaseMatrix(
            criteria=rows,
            prompts=prompt_rows,
            status=ProductVersionReleaseStatus.PRODUCT_VERSION_1_FINAL_GATE_FAIL_UNSAFE,
            status_label=MSG_STATUS_FAIL_UNSAFE,
            saas_ready=saas_ready,
            productive_processing_ready=productive_processing_ready,
            original_folder_processing_allowed=original_folder_processing_allowed,
            datev_cloud_productive_export_ready=datev_cloud_productive_export_ready,
            local_pilot_with_limitations=False,
            release_tag_name=RELEASE_TAG_NAME,
            remaining_prompts=1,
        )

    keys_present = all(key in by_key for key in FINAL_RELEASE_CRITERION_KEYS)
    criteria_ok = keys_present and all(row.met for row in rows)
    prompts_ok = (
        len(prompt_rows) == 12
        and all(row.complete for row in prompt_rows)
        and {row.prompt for row in prompt_rows} == set(range(1, 13))
    )
    safety_ok = (
        bool(by_key.get("productive_processing_blocked") and by_key["productive_processing_blocked"].met)
        and bool(by_key.get("original_folder_use_forbidden") and by_key["original_folder_use_forbidden"].met)
        and bool(by_key.get("saas_readiness_excluded") and by_key["saas_readiness_excluded"].met)
        and bool(
            by_key.get("datev_cloud_productive_export_excluded")
            and by_key["datev_cloud_productive_export_excluded"].met
        )
        and bool(by_key.get("no_private_defaults") and by_key["no_private_defaults"].met)
        and bool(by_key.get("processing_core_untouched") and by_key["processing_core_untouched"].met)
    )

    if criteria_ok and prompts_ok and safety_ok:
        status = (
            ProductVersionReleaseStatus.PRODUCT_VERSION_1_LOCAL_PILOT_RELEASED_WITH_LIMITATIONS
        )
        status_label = MSG_STATUS_RELEASED_WITH_LIMITATIONS
        local_pilot_with_limitations = True
        remaining_prompts = 0
    else:
        status = ProductVersionReleaseStatus.PRODUCT_VERSION_1_FINAL_GATE_BLOCKED
        status_label = MSG_STATUS_BLOCKED
        local_pilot_with_limitations = False
        remaining_prompts = 1

    return ProductVersionReleaseMatrix(
        criteria=rows,
        prompts=prompt_rows,
        status=status,
        status_label=status_label,
        saas_ready=saas_ready,
        productive_processing_ready=productive_processing_ready,
        original_folder_processing_allowed=original_folder_processing_allowed,
        datev_cloud_productive_export_ready=datev_cloud_productive_export_ready,
        local_pilot_with_limitations=local_pilot_with_limitations,
        release_tag_name=RELEASE_TAG_NAME,
        remaining_prompts=remaining_prompts,
    )


def release_status_blob(matrix: ProductVersionReleaseMatrix | None = None) -> str:
    """Join matrix labels for assertion helpers."""

    model = matrix or build_product_v1_release_matrix()
    parts = [
        model.status.value,
        model.status_label,
        model.release_tag_name,
        MSG_LOCAL_PILOT_RULE,
        f"remaining_prompts:{model.remaining_prompts}",
        *(f"{item.key}:{item.label}:{item.detail}" for item in model.criteria),
        *(
            f"prompt{row.prompt}:{row.title}:{'complete' if row.complete else 'open'}"
            for row in model.prompts
        ),
    ]
    return " ".join(parts)


__all__ = (
    "FINAL_RELEASE_CRITERION_KEYS",
    "MSG_LOCAL_PILOT_RULE",
    "MSG_STATUS_BLOCKED",
    "MSG_STATUS_FAIL_UNSAFE",
    "MSG_STATUS_RELEASED",
    "MSG_STATUS_RELEASED_WITH_LIMITATIONS",
    "PROMPT_COMPLETION_TABLE",
    "ProductVersionReleaseCriterion",
    "ProductVersionReleaseMatrix",
    "ProductVersionReleaseStatus",
    "PromptCompletionRow",
    "RELEASE_TAG_NAME",
    "build_product_v1_release_matrix",
    "build_prompt_completion_table",
    "classify_product_v1_release",
    "release_status_blob",
)
