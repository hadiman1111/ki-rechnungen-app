"""Track-B Product Version 1 final release gate — pure non-GUI tests."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.pilot_acceptance import (
    PilotAcceptanceStatus,
    build_pilot_acceptance_matrix,
)
from invoice_tool.ui_v2.release_gate import (
    FINAL_RELEASE_CRITERION_KEYS,
    MSG_LOCAL_PILOT_RULE,
    MSG_STATUS_RELEASED_WITH_LIMITATIONS,
    PROMPT_COMPLETION_TABLE,
    ProductVersionReleaseStatus,
    RELEASE_TAG_NAME,
    build_product_v1_release_matrix,
    build_prompt_completion_table,
    classify_product_v1_release,
    release_status_blob,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASE_GATE_MODULE = ROOT / "invoice_tool" / "ui_v2" / "release_gate.py"
RELEASE_REPORT = (
    ROOT / "docs" / "KI_RECHNUNGEN_PRODUCT_VERSION_1_RELEASE_REPORT_2026-07-22.md"
)
RELEASE_NOTES = (
    ROOT / "docs" / "KI_RECHNUNGEN_PRODUCT_VERSION_1_RELEASE_NOTES_2026-07-22.md"
)
NEXT_PHASE_DOC = (
    ROOT / "docs" / "KI_RECHNUNGEN_NEXT_PHASE_AFTER_LOCAL_PILOT_2026-07-22.md"
)
AUDIT_DOC = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_PRODUCT_VERSION_1_FINALIZATION_AND_RELEASE_GATE_2026-07-22.md"
)
PILOT_ACCEPTANCE_REPORT = (
    ROOT / "docs" / "KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_ACCEPTANCE_REPORT_2026-07-22.md"
)
LIMITATIONS_DOC = (
    ROOT / "docs" / "KI_RECHNUNGEN_TRACK_B_PILOT_LIMITATIONS_2026-07-22.md"
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


def test_release_matrix_includes_all_20_final_criteria() -> None:
    matrix = build_product_v1_release_matrix()
    keys = {row.key for row in matrix.criteria}
    assert len(FINAL_RELEASE_CRITERION_KEYS) == 20
    for key in FINAL_RELEASE_CRITERION_KEYS:
        assert key in keys, key
    assert len(matrix.criteria) == 20
    assert all(row.met for row in matrix.criteria)


def test_release_classification_is_local_pilot_with_limitations() -> None:
    matrix = build_product_v1_release_matrix()
    assert (
        matrix.status
        is ProductVersionReleaseStatus.PRODUCT_VERSION_1_LOCAL_PILOT_RELEASED_WITH_LIMITATIONS
    )
    assert matrix.local_pilot_with_limitations is True
    assert MSG_STATUS_RELEASED_WITH_LIMITATIONS in matrix.status_label
    assert "Limitationen" in matrix.status_label
    assert MSG_LOCAL_PILOT_RULE in release_status_blob(matrix)


def test_release_classification_is_not_saas_ready() -> None:
    matrix = build_product_v1_release_matrix()
    assert matrix.saas_ready is False
    by_key = {row.key: row for row in matrix.criteria}
    assert by_key["saas_readiness_excluded"].met is True
    blob = release_status_blob(matrix)
    assert "nicht SaaS" in blob or "SaaS-Reife bleibt ausgeschlossen" in blob


def test_release_classification_is_not_productive_ready() -> None:
    matrix = build_product_v1_release_matrix()
    assert matrix.productive_processing_ready is False
    by_key = {row.key: row for row in matrix.criteria}
    assert by_key["productive_processing_blocked"].met is True


def test_release_classification_excludes_original_folder_processing() -> None:
    matrix = build_product_v1_release_matrix()
    assert matrix.original_folder_processing_allowed is False
    by_key = {row.key: row for row in matrix.criteria}
    assert by_key["original_folder_use_forbidden"].met is True


def test_release_classification_excludes_datev_cloud_productive_export() -> None:
    matrix = build_product_v1_release_matrix()
    assert matrix.datev_cloud_productive_export_ready is False
    by_key = {row.key: row for row in matrix.criteria}
    assert by_key["datev_cloud_productive_export_excluded"].met is True


def test_prompt_completion_table_covers_1_to_12() -> None:
    prompts = build_prompt_completion_table()
    assert len(PROMPT_COMPLETION_TABLE) == 12
    assert len(prompts) == 12
    assert [row.prompt for row in prompts] == list(range(1, 13))
    assert all(row.complete for row in prompts)
    matrix = build_product_v1_release_matrix()
    assert matrix.remaining_prompts == 0
    assert {row.prompt for row in matrix.prompts} == set(range(1, 13))


def test_failed_criterion_blocks_release() -> None:
    matrix = build_product_v1_release_matrix(synthetic_e2e_passes=False)
    assert matrix.status is ProductVersionReleaseStatus.PRODUCT_VERSION_1_FINAL_GATE_BLOCKED
    assert matrix.local_pilot_with_limitations is False
    assert matrix.saas_ready is False
    assert matrix.remaining_prompts == 1


def test_classify_never_marks_saas_or_productive() -> None:
    matrix = build_product_v1_release_matrix()
    reclassified = classify_product_v1_release(matrix.criteria, prompts=matrix.prompts)
    assert reclassified.saas_ready is False
    assert reclassified.productive_processing_ready is False
    assert reclassified.original_folder_processing_allowed is False
    assert reclassified.datev_cloud_productive_export_ready is False
    assert (
        reclassified.status
        is ProductVersionReleaseStatus.PRODUCT_VERSION_1_LOCAL_PILOT_RELEASED_WITH_LIMITATIONS
    )
    assert reclassified.release_tag_name == RELEASE_TAG_NAME


def test_unsafe_failure_classification() -> None:
    matrix = build_product_v1_release_matrix(unsafe_failure=True)
    assert (
        matrix.status
        is ProductVersionReleaseStatus.PRODUCT_VERSION_1_FINAL_GATE_FAIL_UNSAFE
    )
    assert matrix.local_pilot_with_limitations is False


def test_pilot_acceptance_still_accepted_local_pilot() -> None:
    acceptance = build_pilot_acceptance_matrix()
    assert acceptance.status is PilotAcceptanceStatus.ACCEPTED_LOCAL_PILOT
    release = build_product_v1_release_matrix()
    by_key = {row.key: row for row in release.criteria}
    assert by_key["pilot_acceptance_accepted_local_pilot"].met is True


def test_no_private_tokens_in_release_surface() -> None:
    blob = release_status_blob()
    src = RELEASE_GATE_MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
        assert marker not in src, marker


def test_forbidden_claims_absent_from_release_blob() -> None:
    blob = release_status_blob()
    for claim in FORBIDDEN_CLAIMS:
        assert claim not in blob, claim


def test_release_documentation_exists_and_is_honest() -> None:
    for path in (RELEASE_REPORT, RELEASE_NOTES, NEXT_PHASE_DOC, AUDIT_DOC):
        assert path.is_file(), path.name
        text = path.read_text(encoding="utf-8")
        assert "Sandbox" in text
        assert "Original" in text
        lower = text.lower()
        assert "nicht saas" in lower or "saas-reif" in lower or "saas readiness" in lower
        assert "DATEV" in text
        for marker in ("Hadi", "SOMAA", "Bismarck", "/Users/"):
            assert marker not in text, (path.name, marker)


def test_pilot_docs_still_present_for_release_basis() -> None:
    assert PILOT_ACCEPTANCE_REPORT.is_file()
    assert LIMITATIONS_DOC.is_file()
    acceptance_text = PILOT_ACCEPTANCE_REPORT.read_text(encoding="utf-8")
    assert "ACCEPTED_LOCAL_PILOT" in acceptance_text


def test_release_gate_module_has_no_processing_core_imports() -> None:
    tree = ast.parse(RELEASE_GATE_MODULE.read_text(encoding="utf-8"))
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
