"""Track-B UI-v2 compactness / overlap hotfix after local pilot release."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.onboarding import (
    COMPACT_PILOT_STATUS_ITEMS,
    MSG_EXPORT_PREVIEW_NOT_DATEV,
    MSG_LOCAL_PILOT_SANDBOX,
    MSG_ORIGINAL_FOLDERS_PROTECTED,
    MSG_PRODUCTIVE_BLOCKED,
    MSG_SAAS_NOT_INCLUDED,
    build_local_pilot_readiness,
    onboarding_status_blob,
)
from invoice_tool.ui_v2.pages.settings import build_settings_page_vm
from invoice_tool.ui_v2.pages.workspace import (
    ONBOARDING_COMPACT_STATUS_ITEMS,
    build_workspace_onboarding_panel_vm,
)
from invoice_tool.ui_v2.saas_profile_draft_list_view import (
    DRAFT_LIST_TITLE,
    NO_CLOUD_HELP,
)
from invoice_tool.ui_v2.saas_profile_persistence_view import SCOPE_LABEL
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
UI_V2 = ROOT / "invoice_tool" / "ui_v2"
COMPONENTS = UI_V2 / "components.py"
WORKSPACE = UI_V2 / "pages" / "workspace.py"
SETTINGS = UI_V2 / "pages" / "settings.py"
PROFILES = UI_V2 / "pages" / "profiles.py"
CONFIGS = UI_V2 / "pages" / "configurations.py"
DRAFT_LIST = UI_V2 / "saas_profile_draft_list_view.py"
PERSISTENCE = UI_V2 / "saas_profile_persistence_view.py"

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
    "AMEX-1005",
    "/Users/",
    "Volksbank",
)
FORBIDDEN_CLAIMS = (
    "SaaS-ready",
    "SaaS bereit",
    "ist SaaS-bereit",
    "DATEV-ready",
    "DATEV bereit",
    "produktiver DATEV-Export freigegeben",
    "Cloud-Export freigegeben",
    "DATEV-Produktivexport freigegeben",
)
CONFUSING_SAAS_WORDING = (
    "SaaS-Profilentwurf",
    "Lokale SaaS-Entwürfe",
)


def test_workspace_onboarding_uses_compact_status_not_large_table() -> None:
    panel = build_workspace_onboarding_panel_vm(UiV2State())
    assert panel.uses_compact_status_ui is True
    assert panel.compact_status_items == COMPACT_PILOT_STATUS_ITEMS
    assert panel.compact_status_items == ONBOARDING_COMPACT_STATUS_ITEMS
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "compact_status_banner" in src
    assert "collapsible_details" in src
    # Large repeated Status metadata-table for onboarding is gone.
    assert 'make_metadata_row("Status", line)' not in src


def test_workspace_compact_status_keeps_pilot_meanings() -> None:
    items = " ".join(COMPACT_PILOT_STATUS_ITEMS)
    assert "Lokale Pilotversion" in items
    assert "Sandbox mit kopierten Daten" in items
    assert "Produktiv gesperrt" in items
    assert "Originalordner geschützt" in items
    assert "Export nur Vorschau" in items
    panel = build_workspace_onboarding_panel_vm(UiV2State())
    blob = " ".join(panel.status_lines) + " " + " ".join(panel.compact_status_items)
    assert MSG_LOCAL_PILOT_SANDBOX in panel.status_lines
    assert MSG_PRODUCTIVE_BLOCKED in panel.status_lines
    assert MSG_ORIGINAL_FOLDERS_PROTECTED in panel.status_lines
    assert MSG_EXPORT_PREVIEW_NOT_DATEV in panel.status_lines
    assert "Pilot" in blob or "Pilotversion" in blob
    assert "Sandbox" in blob
    assert "Produktiv" in blob
    assert "Original" in blob
    assert "Export" in blob or "Vorschau" in blob


def _assigned_string_constants(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                values.append(node.value.value)
            elif isinstance(node.value, ast.JoinedStr):
                parts: list[str] = []
                for part in node.value.values:
                    if isinstance(part, ast.Constant) and isinstance(part.value, str):
                        parts.append(part.value)
                if parts:
                    values.append("".join(parts))
    return values


def test_profile_wording_no_confusing_saas_draft_labels() -> None:
    assert DRAFT_LIST_TITLE == "Lokale Profilentwürfe"
    assert SCOPE_LABEL == "Lokaler Entwurf"
    assert NO_CLOUD_HELP == "Nicht Cloud-synchronisiert."
    for path in (DRAFT_LIST, PERSISTENCE, PROFILES, CONFIGS):
        for value in _assigned_string_constants(path):
            for phrase in CONFUSING_SAAS_WORDING:
                assert phrase not in value, (path.name, phrase, value)
    draft_src = DRAFT_LIST.read_text(encoding="utf-8")
    assert 'DRAFT_LIST_TITLE = "Lokale Profilentwürfe"' in draft_src
    assert "Nicht Cloud-synchronisiert" in draft_src
    persist_src = PERSISTENCE.read_text(encoding="utf-8")
    assert 'SCOPE_LABEL = "Lokaler Entwurf"' in persist_src


def test_settings_capability_status_remains_honest_and_compact() -> None:
    settings = build_settings_page_vm(UiV2State())
    assert settings.uses_compact_status_ui is True
    assert settings.compact_status_items == COMPACT_PILOT_STATUS_ITEMS
    assert settings.saas_ready is False
    assert settings.datev_productive_export_ready is False
    assert settings.productive_execution_enabled is False
    assert settings.has_productive_toggle is False
    by_key = {item.key: item for item in settings.capability_matrix}
    assert by_key["productive_processing"].status == "blocked"
    assert by_key["saas_login_tenant_billing"].status == "not_included"
    assert by_key["export_reporting_preview"].status == "preview"
    src = SETTINGS.read_text(encoding="utf-8")
    assert "compact_status_banner" in src
    assert "compact_capability_matrix" in src
    assert "dense_card" in src


def test_no_saas_ready_or_productive_export_claims() -> None:
    readiness = build_local_pilot_readiness()
    blob = onboarding_status_blob(readiness).lower()
    settings = build_settings_page_vm(UiV2State())
    settings_blob = " ".join(
        [
            settings.banner,
            *(section.detail for section in settings.sections),
            MSG_SAAS_NOT_INCLUDED,
        ]
    ).lower()
    for claim in FORBIDDEN_CLAIMS:
        # Honest negation "nicht SaaS-ready" is required in the compact product line.
        if claim.lower() == "saas-ready" and "nicht saas-ready" in settings_blob:
            continue
        assert claim.lower() not in blob, claim
        if claim.lower() == "saas-ready":
            assert "nicht saas-ready" in settings_blob
            continue
        assert claim.lower() not in settings_blob, claim
    assert "nicht saas-ready" in settings_blob
    assert readiness.saas_ready is False
    assert readiness.datev_productive_export_ready is False
    assert readiness.has_productive_toggle is False


def test_no_productive_execution_toggle_in_settings_or_workspace() -> None:
    settings = build_settings_page_vm(UiV2State())
    panel = build_workspace_onboarding_panel_vm(UiV2State())
    assert settings.has_productive_toggle is False
    assert panel.has_productive_toggle is False
    for path in (SETTINGS, WORKSPACE, PROFILES, CONFIGS):
        src = path.read_text(encoding="utf-8")
        for token in (
            "ft.Switch",
            "ft.Checkbox",
            "productive_execution_toggle",
            "enable_productive",
        ):
            assert token not in src, (path.name, token)


def test_no_private_tokens_in_hotfix_surfaces() -> None:
    readiness_blob = onboarding_status_blob()
    settings = build_settings_page_vm(UiV2State())
    settings_blob = " ".join(
        [
            settings.banner,
            settings.subtitle,
            *(section.detail for section in settings.sections),
            DRAFT_LIST_TITLE,
            SCOPE_LABEL,
            NO_CLOUD_HELP,
            *COMPACT_PILOT_STATUS_ITEMS,
        ]
    )
    for marker in PRIVATE_MARKERS:
        assert marker not in readiness_blob, marker
        assert marker not in settings_blob, marker
    for path in (DRAFT_LIST, PERSISTENCE):
        for value in _assigned_string_constants(path):
            # Guard-marker tuples intentionally list private tokens; skip those.
            if value in PRIVATE_MARKERS:
                continue
            for marker in PRIVATE_MARKERS:
                assert marker not in value, (path.name, marker, value)


def test_overlap_prevention_uses_label_above_fields() -> None:
    workspace_src = WORKSPACE.read_text(encoding="utf-8")
    draft_src = DRAFT_LIST.read_text(encoding="utf-8")
    assert "form_field_group" in workspace_src
    assert 'label=EXPORT_PATH_HINT' not in workspace_src
    assert "hint_text=EXPORT_PATH_HINT" in workspace_src or "hint_text=vm.export_path_hint" in draft_src
    assert 'label=vm.rename_field_hint' not in draft_src
    assert "hint_text=vm.rename_field_hint" in draft_src
    assert "dense_card" in PROFILES.read_text(encoding="utf-8")
    assert "dense_card" in CONFIGS.read_text(encoding="utf-8")
    assert "Regeln ordnen Dokumente zu" in CONFIGS.read_text(encoding="utf-8")


def test_compact_helpers_exist() -> None:
    src = COMPONENTS.read_text(encoding="utf-8")
    for name in (
        "compact_status_banner",
        "compact_info_row",
        "compact_hint_block",
        "compact_capability_matrix",
        "compact_checklist_block",
        "dense_card",
        "compact_run_status_panel",
        "collapsible_details",
    ):
        assert f"def {name}" in src


def test_hotfix_modules_do_not_import_processing_core() -> None:
    for path in (
        COMPONENTS,
        WORKSPACE,
        SETTINGS,
        PROFILES,
        CONFIGS,
        DRAFT_LIST,
        PERSISTENCE,
        UI_V2 / "onboarding.py",
        UI_V2 / "policy_editor_controls.py",
        UI_V2 / "state.py",
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for module in FORBIDDEN_CORE:
            assert module not in imported, (path.name, module)
