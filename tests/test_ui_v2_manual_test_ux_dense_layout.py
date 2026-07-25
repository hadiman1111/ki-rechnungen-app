"""Track-B UI-v2 manual-test UX: start feedback + dense layout + less help text."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from invoice_tool.ui_v2.export_reporting import MSG_EXPORT_DISCLAIMER_COMPACT
from invoice_tool.ui_v2.local_processing_adapter import LocalProcessingAdapter
from invoice_tool.ui_v2.pages.settings import PRODUCT_STATUS_ONE_LINE, build_settings_page_vm
from invoice_tool.ui_v2.pages.workspace import (
    EMPTY_RESULT_COMPACT_TITLE,
    MAX_BLOCKED_DETAIL_LINES,
    MSG_DETAIL_CORE_BRIDGE,
    MSG_RUN_STATUS_CHECKING,
    MSG_SANDBOX_BLOCKED_CORE_BRIDGE,
    MSG_SANDBOX_BRIDGE_NOT_CONNECTED,
    MSG_SANDBOX_NO_ORIGINALS_USED,
    apply_start_processing,
    build_start_interaction_feedback,
    mark_start_checking,
)
from invoice_tool.ui_v2.processing_state import ProcessingRunState
from invoice_tool.ui_v2.saas_profile_draft_list_view import DRAFT_LIST_TITLE
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
UI_V2 = ROOT / "invoice_tool" / "ui_v2"
WORKSPACE = UI_V2 / "pages" / "workspace.py"
PROFILES = UI_V2 / "pages" / "profiles.py"
CONFIGS = UI_V2 / "pages" / "configurations.py"
SETTINGS = UI_V2 / "pages" / "settings.py"
REVIEW = UI_V2 / "pages" / "review.py"
COMPONENTS = UI_V2 / "components.py"
EXPORT = UI_V2 / "export_reporting.py"

FORBIDDEN_CORE = (
    "invoice_tool.processing",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
    "invoice_tool.run",
)
FORBIDDEN_CLAIMS = (
    "ist SaaS-bereit",
    "SaaS bereit",
    "DATEV-ready",
    "DATEV bereit",
    "produktiver DATEV-Export freigegeben",
    "Cloud-Export freigegeben",
)
CONFUSING_SAAS = ("SaaS-Profilentwurf", "Lokale SaaS-Entwürfe")
GIANT_WORKFLOW_MARKERS = (
    'compact_hint_block(*deduped_hints, title="Sandbox / Laufstatus")',
    "Dies ist ein Sandbox-Lauf mit kopierten Daten",
)


def _state_with_adapter(**kwargs) -> UiV2State:
    return UiV2State(processing_service=LocalProcessingAdapter(), **kwargs)


def test_start_click_sets_checking_then_blocked_state() -> None:
    state = _state_with_adapter()
    assert state.workspace_run_interaction_status == "idle"
    mark_start_checking(state)
    assert state.workspace_run_interaction_status == "checking"
    assert MSG_RUN_STATUS_CHECKING in state.workspace_start_feedback
    assert state.processing_run_state.status == "running"
    result = apply_start_processing(state, profile_id="profile-a")
    assert result.status in {"not_configured", "blocked", "failed"}
    assert state.workspace_run_interaction_status != "idle"
    assert state.workspace_run_interaction_status != "checking"
    assert state.workspace_start_feedback_primary
    assert state.workspace_start_feedback


def test_core_bridge_wired_shows_compact_completed_state(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    inbox = sandbox / "copied-inbox"
    outbox = sandbox / "copied-outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    state = _state_with_adapter()
    state.workspace_input_folder_override = str(inbox)
    state.workspace_output_folder_override = str(outbox)
    state.workspace_input_folder_source = "explicit_user_selection"
    state.workspace_output_folder_source = "explicit_user_selection"
    state.config_list_selected_id = "config-a"
    apply_start_processing(state, profile_id="profile-a")
    assert state.workspace_run_interaction_status == "completed"
    assert ("Sandbox-Lauf abgeschlossen" in state.workspace_start_feedback_primary
            or "Vorschau-Prüfung abgeschlossen" in state.workspace_start_feedback_primary)
    assert MSG_SANDBOX_NO_ORIGINALS_USED in state.workspace_start_feedback_details
    assert any("Originale unverändert" in item for item in state.workspace_start_feedback_details)
    assert len(state.workspace_start_feedback_details) <= MAX_BLOCKED_DETAIL_LINES
    assert not state.processing_run_state.results


def test_no_giant_workflow_bullet_block_in_default_workspace_source() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    for marker in GIANT_WORKFLOW_MARKERS:
        assert marker not in src, marker
    assert "compact_run_status_panel" in src
    assert "collapsible_details" in src
    assert 'title="Sandbox / Laufstatus"' not in src


def test_workflow_details_are_collapsed_or_compact() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert (
        'details_title="Details anzeigen"' in src
        or "Details anzeigen" in src
        or "Technische Details" in src
        or "collapsible_details" in src
    )
    assert "collapsible_details" in src
    components = COMPONENTS.read_text(encoding="utf-8")
    assert "def compact_run_status_panel" in components
    assert "def collapsible_details" in components


def test_workspace_result_empty_state_is_compact() -> None:
    assert EMPTY_RESULT_COMPACT_TITLE == "Noch kein Ergebnis vorhanden."
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "EMPTY_RESULT_COMPACT_TITLE" in src
    assert "detail=None" in src or "MSG_NO_RESULT_YET" in src


def test_five_question_result_view_uses_compact_rows() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "compact_info_row" in src or "WORKSPACE_FILE_PAIR_MARKER" in src
    assert "dense_card(*rows)" in src or "_workspace_file_pair_rows" in src
    assert 'make_metadata_row("Status"' not in src


def test_profile_page_no_confusing_saas_draft_labels() -> None:
    assert DRAFT_LIST_TITLE == "Lokale Profilentwürfe"
    for path in (PROFILES, CONFIGS):
        src = path.read_text(encoding="utf-8")
        for phrase in CONFUSING_SAAS:
            assert phrase not in src, (path.name, phrase)
    draft_src = (UI_V2 / "saas_profile_draft_list_view.py").read_text(encoding="utf-8")
    assert 'DRAFT_LIST_TITLE = "Lokale Profilentwürfe"' in draft_src
    assert 'DRAFT_LIST_TITLE = "Lokale SaaS-Entwürfe"' not in draft_src
    assert 'TITLE = "SaaS-Profilentwurf"' not in draft_src


def test_configurations_page_uses_one_compact_note() -> None:
    src = CONFIGS.read_text(encoding="utf-8")
    assert "Regeln ordnen Dokumente zu; unklare Dokumente bleiben zur Prüfung." in src
    assert 'title="Konfigurations-Hinweise"' not in src
    assert "make_info_banner(config_policy_panel.banner)" not in src


def test_settings_page_has_compact_one_line_product_status() -> None:
    assert "nicht SaaS-ready" in PRODUCT_STATUS_ONE_LINE
    assert "produktiv gesperrt" in PRODUCT_STATUS_ONE_LINE
    settings = build_settings_page_vm(UiV2State())
    assert PRODUCT_STATUS_ONE_LINE in settings.banner
    src = SETTINGS.read_text(encoding="utf-8")
    assert "PRODUCT_STATUS_ONE_LINE" in src
    assert "collapsible_details" in src


def test_export_reporting_disclaimer_is_compact() -> None:
    assert MSG_EXPORT_DISCLAIMER_COMPACT == (
        "Exportvorschau · kein produktiver DATEV-/Cloud-Export"
    )
    assert "MSG_EXPORT_DISCLAIMER_COMPACT" in WORKSPACE.read_text(encoding="utf-8")
    assert "MSG_EXPORT_DISCLAIMER_COMPACT" in EXPORT.read_text(encoding="utf-8")


def test_no_productive_or_saas_ready_claims() -> None:
    blob = " ".join(
        path.read_text(encoding="utf-8")
        for path in (WORKSPACE, SETTINGS, PROFILES, CONFIGS, REVIEW, EXPORT)
    )
    for claim in FORBIDDEN_CLAIMS:
        assert claim not in blob, claim
    # Explicit negation is required; bare readiness claim is forbidden.
    assert "nicht SaaS-ready" in blob
    assert "ist SaaS-ready" not in blob
    assert "SaaS-ready ·" in blob or "nicht SaaS-ready" in blob


def test_no_fake_results_from_start_without_bridge() -> None:
    state = _state_with_adapter()
    apply_start_processing(state, profile_id="profile-a")
    assert state.processing_run_state.results == tuple()
    assert state.processing_run_state.status != "completed"


def test_no_processing_core_import_introduced() -> None:
    before = {name for name in sys.modules if name.startswith("invoice_tool.")}
    state = _state_with_adapter()
    apply_start_processing(state)
    after = {name for name in sys.modules if name.startswith("invoice_tool.")}
    newly = after - before
    for forbidden in FORBIDDEN_CORE:
        assert forbidden not in newly
    for path in (WORKSPACE, COMPONENTS, SETTINGS, PROFILES, CONFIGS, REVIEW):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for module in FORBIDDEN_CORE:
            assert module not in imported, (path.name, module)


def test_interaction_feedback_builder_primary_is_compact() -> None:
    feedback = build_start_interaction_feedback(
        ProcessingRunState(
            status="failed",
            message="sandbox unbound",
            errors=("sandbox_core_runner_unbound",),
            execution_gate="ready_for_sandbox_execution",
        )
    )
    assert feedback.interaction_status == "sandbox_not_connected"
    assert MSG_SANDBOX_BRIDGE_NOT_CONNECTED in feedback.primary
    assert MSG_SANDBOX_BLOCKED_CORE_BRIDGE in feedback.primary
    assert MSG_DETAIL_CORE_BRIDGE in feedback.details
    assert len(feedback.details) <= MAX_BLOCKED_DETAIL_LINES
    assert "Dies ist ein Sandbox-Lauf" not in feedback.primary
    assert "Dies ist ein Sandbox-Lauf" not in " ".join(feedback.details)


def test_review_empty_state_is_compact() -> None:
    src = REVIEW.read_text(encoding="utf-8")
    assert "Keine Prüffälle vorhanden" in (
        (ROOT / "invoice_tool" / "ui_v2" / "review_workflow.py").read_text(encoding="utf-8")
    )
    assert "make_info_banner" not in src
    assert "collapsible_details" in src
