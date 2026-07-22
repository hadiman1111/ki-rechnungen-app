"""Track-B local pilot readiness acceptance gate — pure non-GUI tests."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.onboarding import (
    MSG_EXPORT_PREVIEW_NOT_DATEV,
    MSG_LOCAL_PILOT_SANDBOX,
    MSG_NEXT_STEP_FINAL_RELEASE_GATE,
    MSG_ORIGINAL_FOLDERS_PROTECTED,
    MSG_PILOT_ACCEPTANCE_DONE,
    MSG_PRODUCTIVE_BLOCKED,
    MSG_SAAS_NOT_INCLUDED,
    MSG_STAGE_LOCAL_PILOT,
    build_local_pilot_readiness,
    onboarding_status_blob,
)
from invoice_tool.ui_v2.pilot_acceptance import (
    EXPLICIT_NON_GOAL_KEYS,
    MSG_REMAINING_RELEASE_GATE,
    MSG_STATUS_ACCEPTED_LOCAL_PILOT,
    PilotAcceptanceStatus,
    REQUIRED_ACCEPTED_KEYS,
    acceptance_status_blob,
    build_pilot_acceptance_matrix,
    classify_local_pilot_readiness,
)

ROOT = Path(__file__).resolve().parents[1]
PILOT_ACCEPTANCE_MODULE = ROOT / "invoice_tool" / "ui_v2" / "pilot_acceptance.py"
ONBOARDING_MODULE = ROOT / "invoice_tool" / "ui_v2" / "onboarding.py"
ACCEPTANCE_REPORT = (
    ROOT / "docs" / "KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_ACCEPTANCE_REPORT_2026-07-22.md"
)
LIMITATIONS_DOC = (
    ROOT / "docs" / "KI_RECHNUNGEN_TRACK_B_PILOT_LIMITATIONS_2026-07-22.md"
)
AUDIT_DOC = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_PILOT_READINESS_ACCEPTANCE_GATE_2026-07-22.md"
)

FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
    "invoice_tool.run",
)
PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX",
    "voba",
    "/Users/",
    "Desktop/",
    "Volksbank",
    "Privat",
)
FORBIDDEN_CLAIMS = (
    "SaaS-ready",
    "SaaS bereit",
    "saas ready",
    "DATEV-ready",
    "DATEV bereit",
    "produktiver DATEV-Export freigegeben",
    "Cloud-Export freigegeben",
    "ist SaaS-bereit",
    "als SaaS-bereit",
    "DATEV-Produktivexport freigegeben",
)


def test_acceptance_matrix_includes_all_required_accepted_criteria() -> None:
    matrix = build_pilot_acceptance_matrix()
    keys = {row.key for row in matrix.criteria}
    for key in REQUIRED_ACCEPTED_KEYS:
        assert key in keys, key
    required = [row for row in matrix.criteria if row.key in REQUIRED_ACCEPTED_KEYS]
    assert len(required) == len(REQUIRED_ACCEPTED_KEYS)
    assert all(row.met for row in required)


def test_acceptance_matrix_includes_all_explicit_non_goals() -> None:
    matrix = build_pilot_acceptance_matrix()
    keys = {row.key for row in matrix.criteria}
    for key in EXPLICIT_NON_GOAL_KEYS:
        assert key in keys, key
    non_goals = [row for row in matrix.criteria if row.key in EXPLICIT_NON_GOAL_KEYS]
    assert len(non_goals) == len(EXPLICIT_NON_GOAL_KEYS)
    assert all(row.met for row in non_goals)


def test_local_pilot_readiness_not_classified_as_saas_ready() -> None:
    matrix = build_pilot_acceptance_matrix()
    readiness = build_local_pilot_readiness()
    assert matrix.status is PilotAcceptanceStatus.ACCEPTED_LOCAL_PILOT
    assert matrix.saas_ready is False
    assert readiness.saas_ready is False
    assert "nicht SaaS-bereit" in MSG_STAGE_LOCAL_PILOT
    assert MSG_SAAS_NOT_INCLUDED in readiness.status_lines


def test_local_pilot_readiness_not_classified_as_productive() -> None:
    matrix = build_pilot_acceptance_matrix()
    readiness = build_local_pilot_readiness()
    assert matrix.productive_processing_accepted is False
    assert matrix.local_pilot_under_sandbox_limits is True
    assert readiness.productive_processing_enabled is False
    assert MSG_PRODUCTIVE_BLOCKED in readiness.status_lines


def test_original_folder_use_remains_forbidden() -> None:
    matrix = build_pilot_acceptance_matrix()
    readiness = build_local_pilot_readiness()
    assert matrix.original_folder_use_accepted is False
    by_key = {row.key: row for row in matrix.criteria}
    assert by_key["no_productive_original_folder_processing"].met is True
    assert readiness.original_folders_protected is True
    assert MSG_ORIGINAL_FOLDERS_PROTECTED in readiness.status_lines


def test_productive_export_remains_forbidden() -> None:
    matrix = build_pilot_acceptance_matrix()
    readiness = build_local_pilot_readiness()
    assert matrix.datev_cloud_productive_export_accepted is False
    assert readiness.datev_productive_export_ready is False
    assert readiness.export_is_preview is True
    assert "Vorschau" in MSG_EXPORT_PREVIEW_NOT_DATEV


def test_datev_cloud_productive_export_claim_absent() -> None:
    # Affirmative readiness claims must stay absent; negated wording may mention DATEV/SaaS.
    matrix = build_pilot_acceptance_matrix()
    readiness = build_local_pilot_readiness()
    assert matrix.datev_cloud_productive_export_accepted is False
    assert matrix.saas_ready is False
    assert readiness.datev_productive_export_ready is False
    assert readiness.saas_ready is False
    user_blob = onboarding_status_blob(readiness)
    for claim in FORBIDDEN_CLAIMS:
        assert claim not in user_blob, claim
    assert "kein produktiver DATEV" in MSG_EXPORT_PREVIEW_NOT_DATEV
    assert "Nicht als SaaS bereit" in acceptance_status_blob(matrix)


def test_no_private_tokens_in_acceptance_surface() -> None:
    blob = acceptance_status_blob()
    src = PILOT_ACCEPTANCE_MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
        assert marker not in src, marker


def test_failed_required_criterion_blocks_acceptance() -> None:
    matrix = build_pilot_acceptance_matrix(synthetic_e2e_passes=False)
    assert matrix.status is PilotAcceptanceStatus.NOT_ACCEPTED
    assert matrix.local_pilot_under_sandbox_limits is False
    assert matrix.saas_ready is False


def test_classify_never_marks_saas_or_productive() -> None:
    matrix = build_pilot_acceptance_matrix()
    reclassified = classify_local_pilot_readiness(matrix.criteria)
    assert reclassified.saas_ready is False
    assert reclassified.productive_processing_accepted is False
    assert reclassified.original_folder_use_accepted is False
    assert reclassified.datev_cloud_productive_export_accepted is False
    assert reclassified.status is PilotAcceptanceStatus.ACCEPTED_LOCAL_PILOT
    assert MSG_STATUS_ACCEPTED_LOCAL_PILOT in reclassified.status_label
    assert reclassified.remaining_release_gate == MSG_REMAINING_RELEASE_GATE


def test_onboarding_points_to_final_release_gate_after_acceptance() -> None:
    readiness = build_local_pilot_readiness()
    assert readiness.next_step == MSG_NEXT_STEP_FINAL_RELEASE_GATE
    guidance = " ".join(readiness.safe_start_guidance)
    assert MSG_PILOT_ACCEPTANCE_DONE in guidance
    assert MSG_NEXT_STEP_FINAL_RELEASE_GATE in guidance
    assert MSG_LOCAL_PILOT_SANDBOX in readiness.status_lines


def test_acceptance_documentation_exists_and_is_honest() -> None:
    for path in (ACCEPTANCE_REPORT, LIMITATIONS_DOC, AUDIT_DOC):
        assert path.is_file(), path.name
        text = path.read_text(encoding="utf-8")
        assert "nicht SaaS" in text.lower() or "Nicht SaaS" in text or "nicht SaaS-bereit" in text
        assert "Sandbox" in text
        assert "Original" in text
        assert "DATEV" in text
        for marker in ("Hadi", "SOMAA", "Bismarck", "/Users/"):
            assert marker not in text, (path.name, marker)


def test_pilot_acceptance_module_has_no_processing_core_imports() -> None:
    tree = ast.parse(PILOT_ACCEPTANCE_MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(
                    alias.name == core or alias.name.startswith(core + ".")
                    for core in FORBIDDEN_CORE
                ), alias.name
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not any(
                node.module == core or node.module.startswith(core + ".")
                for core in FORBIDDEN_CORE
            ), node.module


def test_track_a_protection_module_still_present() -> None:
    protection = ROOT / "tests" / "test_track_a_internal_app_protection.py"
    assert protection.is_file()
    src = protection.read_text(encoding="utf-8")
    assert "app_main" in src
    assert "app_ui_v2" in src or "ui_v2" in src
