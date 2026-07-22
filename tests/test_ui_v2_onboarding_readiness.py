"""Track-B product packaging / onboarding readiness — pure non-GUI tests."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.onboarding import (
    MSG_EXPORT_PREVIEW_NOT_DATEV,
    MSG_LOCAL_PILOT_SANDBOX,
    MSG_NEXT_STEP_PILOT_ACCEPTANCE,
    MSG_ORIGINAL_FOLDERS_PROTECTED,
    MSG_PRODUCTIVE_BLOCKED,
    MSG_SAAS_NOT_INCLUDED,
    MSG_STAGE_LOCAL_PILOT,
    ProductReadinessStage,
    TRACK_B_ONBOARDING_STATUS_LINES,
    build_local_pilot_readiness,
    build_onboarding_checklist,
    build_safe_start_guidance,
    onboarding_status_blob,
)
from invoice_tool.ui_v2.pages.settings import build_settings_page_vm
from invoice_tool.ui_v2.pages.workspace import (
    ONBOARDING_STATUS_LINES,
    build_workspace_onboarding_panel_vm,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
ONBOARDING_MODULE = ROOT / "invoice_tool" / "ui_v2" / "onboarding.py"
WORKSPACE_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
SETTINGS_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "settings.py"
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


def test_onboarding_says_local_pilot_sandbox_only() -> None:
    vm = build_local_pilot_readiness()
    assert vm.stage is ProductReadinessStage.LOCAL_PILOT_READINESS
    assert MSG_LOCAL_PILOT_SANDBOX in vm.status_lines
    assert MSG_STAGE_LOCAL_PILOT in vm.stage_label
    assert "SaaS" in MSG_SAAS_NOT_INCLUDED
    assert vm.saas_ready is False


def test_onboarding_says_productive_processing_blocked() -> None:
    vm = build_local_pilot_readiness()
    assert MSG_PRODUCTIVE_BLOCKED in vm.status_lines
    assert vm.productive_processing_enabled is False
    assert "noch nicht freigegeben" in MSG_PRODUCTIVE_BLOCKED


def test_onboarding_says_original_folders_protected() -> None:
    vm = build_local_pilot_readiness()
    assert MSG_ORIGINAL_FOLDERS_PROTECTED in vm.status_lines
    assert vm.original_folders_protected is True


def test_onboarding_says_export_is_preview_not_datev_cloud() -> None:
    vm = build_local_pilot_readiness()
    assert MSG_EXPORT_PREVIEW_NOT_DATEV in vm.status_lines
    assert vm.export_is_preview is True
    assert vm.datev_productive_export_ready is False
    assert "DATEV" in MSG_EXPORT_PREVIEW_NOT_DATEV
    assert "Vorschau" in MSG_EXPORT_PREVIEW_NOT_DATEV


def test_onboarding_says_saas_not_included() -> None:
    vm = build_local_pilot_readiness()
    assert MSG_SAAS_NOT_INCLUDED in vm.status_lines
    blob = onboarding_status_blob(vm)
    assert "Login" in blob
    assert "Mandanten" in blob
    assert "Abrechnung" in blob
    assert vm.saas_ready is False


def test_workspace_shows_safe_onboarding_checklist() -> None:
    panel = build_workspace_onboarding_panel_vm(UiV2State())
    labels = [item.label for item in panel.checklist]
    assert panel.status_lines == ONBOARDING_STATUS_LINES
    assert panel.status_lines == TRACK_B_ONBOARDING_STATUS_LINES
    assert "Profil wählen oder vorbereiten." in labels
    assert "Kopierte Testdaten verwenden." in labels
    assert "Originalordner getrennt halten." in labels
    assert "Sandbox-Validierung ausführen." in labels
    assert "Unklare Fälle prüfen." in labels
    assert "Exportvorschau lesen." in labels
    assert panel.next_step == MSG_NEXT_STEP_PILOT_ACCEPTANCE
    assert panel.implies_saas_ready is False
    assert panel.implies_productive_export is False
    assert panel.has_productive_toggle is False


def test_settings_capability_matrix_is_honest() -> None:
    settings = build_settings_page_vm(UiV2State())
    by_key = {item.key: item for item in settings.capability_matrix}
    assert by_key["sandbox_gate"].status == "ready"
    assert by_key["sandbox_execution_boundary"].status == "ready"
    assert by_key["review_workflow"].status == "ready"
    assert by_key["profile_policy"].status == "ready"
    assert by_key["export_reporting_preview"].status == "preview"
    assert by_key["track_a_protection"].status == "verified"
    assert by_key["productive_processing"].status == "blocked"
    assert by_key["saas_login_tenant_billing"].status == "not_included"
    assert settings.saas_ready is False
    assert settings.datev_productive_export_ready is False
    assert settings.productive_execution_enabled is False
    blob = " ".join(
        [
            settings.banner,
            *(section.detail for section in settings.sections),
            MSG_LOCAL_PILOT_SANDBOX,
            MSG_SAAS_NOT_INCLUDED,
        ]
    )
    assert MSG_LOCAL_PILOT_SANDBOX in blob
    assert MSG_SAAS_NOT_INCLUDED in blob


def test_no_productive_execution_toggle_appears() -> None:
    vm = build_local_pilot_readiness()
    settings = build_settings_page_vm()
    panel = build_workspace_onboarding_panel_vm()
    assert vm.has_productive_toggle is False
    assert settings.has_productive_toggle is False
    assert panel.has_productive_toggle is False
    for path in (ONBOARDING_MODULE, WORKSPACE_PAGE, SETTINGS_PAGE):
        src = path.read_text(encoding="utf-8")
        for token in (
            "ft.Switch",
            "ft.Checkbox",
            "productive_execution_toggle",
            "enable_productive",
        ):
            assert token not in src, (path.name, token)


def test_no_saas_ready_or_datev_ready_claim() -> None:
    # User-facing strings only — module comments may negate claims in English prose.
    blob = " ".join(
        [
            onboarding_status_blob(),
            *build_safe_start_guidance(),
            build_settings_page_vm().banner,
            *(section.detail for section in build_settings_page_vm().sections),
            *(item.label for item in build_onboarding_checklist()),
            *build_workspace_onboarding_panel_vm().status_lines,
        ]
    )
    for claim in FORBIDDEN_CLAIMS:
        assert claim not in blob, claim
    assert "nicht SaaS-bereit" in MSG_STAGE_LOCAL_PILOT
    assert "kein produktiver DATEV" in MSG_EXPORT_PREVIEW_NOT_DATEV
    # Affirmative readiness must stay false on the readiness model.
    vm = build_local_pilot_readiness()
    assert vm.saas_ready is False
    assert vm.datev_productive_export_ready is False


def test_no_private_tokens_in_onboarding_surface() -> None:
    blob = onboarding_status_blob()
    src = ONBOARDING_MODULE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
        assert marker not in src, marker


def test_onboarding_modules_have_no_processing_core_imports() -> None:
    for path in (ONBOARDING_MODULE, WORKSPACE_PAGE, SETTINGS_PAGE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(
                        alias.name == core or alias.name.startswith(core + ".")
                        for core in FORBIDDEN_CORE
                    ), (path.name, alias.name)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(
                    node.module == core or node.module.startswith(core + ".")
                    for core in FORBIDDEN_CORE
                ), (path.name, node.module)


def test_track_a_protection_module_still_present() -> None:
    protection = ROOT / "tests" / "test_track_a_internal_app_protection.py"
    assert protection.is_file()
    src = protection.read_text(encoding="utf-8")
    assert "app_main" in src
    assert "app_ui_v2" in src or "ui_v2" in src
