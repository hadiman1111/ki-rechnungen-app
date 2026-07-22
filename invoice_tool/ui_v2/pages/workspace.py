"""Arbeitsbereich — Figma Make port (single run panel + Ergebnisliste).

Honest empty state: no preview/mock invoice rows, no private/local demo data.
Results appear only after a real workspace.results payload or injected contract results.
Processing starts only via the bounded UI-v2 contract (default: not connected).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Literal

import flet as ft
from invoice_tool.ui_v2.adapters.folder_picker_adapter import choose_target_folder
from invoice_tool.ui_v2.components import (
    collapsible_details,
    compact_info_row,
    compact_run_status_panel,
    compact_status_banner,
    dense_card,
    display_path_value,
    divider,
    empty_state,
    form_field_group,
    inline_warning,
    make_context_strip,
    make_destination_list_row,
    make_ergebnis_row,
    make_full_width_panel,
    make_section_label,
    make_tab_bar,
    make_workspace_folder_selection_panel,
    make_workspace_run_panel,
    page_header,
    page_scaffold,
    summary_alert,
)
from invoice_tool.ui_v2.edit_components import (
    action_button,
    full_width_field,
    helper_text,
    outlined_field_kwargs,
)
from invoice_tool.ui_v2.clarity_copy import (
    MSG_CLARITY_BUCKETS_SEPARATED,
    MSG_CLARITY_FILENAME_NOT_TRUTH,
    MSG_CLARITY_UNCLEAR_STAYS_REVIEW,
)
from invoice_tool.ui_v2.onboarding import (
    COMPACT_PILOT_STATUS_ITEMS,
    MSG_NEXT_STEP_FINAL_RELEASE_GATE,
    MSG_SAAS_NOT_INCLUDED,
    TRACK_B_ONBOARDING_STATUS_LINES,
    LocalPilotReadinessViewModel,
    OnboardingChecklistItem,
    build_local_pilot_readiness,
)
from invoice_tool.ui_v2.export_reporting import (
    MSG_DESTINATIONS_EMPTY,
    MSG_EXPORT_FROM_REAL_RUN,
    MSG_EXPORT_IS_PREVIEW,
    MSG_EXPORT_NO_FILE_MUTATION_OF_ORIGINALS,
    MSG_FAILED_EMPTY,
    MSG_NO_RUN_PAYLOAD,
    MSG_PLANNED_DESTINATION_HINT,
    MSG_RECOGNIZED_EMPTY,
    MSG_UNCLEAR_EMPTY,
    RunReportViewModel,
    SECTION_DESTINATIONS,
    SECTION_FAILED,
    SECTION_RECOGNIZED,
    SECTION_SUMMARY,
    SECTION_UNCLEAR,
    build_run_report_view_model,
)
from invoice_tool.ui_v2.navigation import NAV_CONFIGURATIONS
from invoice_tool.saas_product_model import default_classification_policy
from invoice_tool.ui_v2.policy_runtime_bridge import (
    MSG_POLICY_INCOMPLETE,
    MSG_UNKNOWN_EVIDENCE_REVIEW,
    RuntimePolicyBridgeResult,
    build_runtime_policy_intent,
)
from invoice_tool.ui_v2.processing_contract import (
    SOURCE_EXPLICIT_USER_SELECTION,
    SOURCE_UNSET,
    ProcessingRunRequest,
)
from invoice_tool.ui_v2.local_processing_adapter import (
    MSG_MISSING_INPUT,
    MSG_MISSING_OUTPUT,
)
from invoice_tool.ui_v2.processing_state import (
    MSG_BLOCKED_ADAPTER,
    MSG_DRY_RUN_UNAVAILABLE,
    MSG_IDLE,
    MSG_NOT_CONFIGURED,
    MSG_POLICY_NOT_READY,
    MSG_PRODUCTIVE_NOT_RELEASED,
    ProcessingResultSummary,
    ProcessingRunState,
    ProcessingStatus,
)
from invoice_tool.ui_v2.sandbox_execution_boundary import MSG_SANDBOX_RUNNER_UNBOUND
from invoice_tool.ui_v2.sandbox_processing_gate import (
    MSG_SANDBOX_COPIED_DATA_ONLY,
    MSG_SANDBOX_COPIED_RUN,
    MSG_SANDBOX_CORE_DRY_ABSENT,
    MSG_SANDBOX_EXECUTION_WIRED,
    MSG_SANDBOX_MODE_PREPARED,
    MSG_SANDBOX_NO_ORIGINAL_INPUT,
    MSG_SANDBOX_PRODUCTIVE_BLOCKED,
    WORKSPACE_SANDBOX_READINESS_LINES,
    workspace_sandbox_readiness_copy,
)
from invoice_tool.ui_v2.run_result_display import (
    MSG_ERROR_SUMMARY_SECTION,
    MSG_PRODUCTIVE_HOLD,
    MSG_RESULTS_SECTION,
    MSG_REVIEW_DETAILS_HINT,
    MSG_REVIEW_SUMMARY_SECTION,
    RunResultDisplayShellVM,
    build_run_result_display_shell,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.view_models import ResultSummaryVM, UiV2ReadOnlySnapshot
from invoice_tool.ui_v2.workspace_configuration_selection import (
    MAX_BLOCKED_DETAIL_LINES,
    MSG_CONFIGURATION_CHANGE_HINT,
    MSG_CORE_BRIDGE_TECHNICAL,
    MSG_EXPORT_REMAINS_DRAFT,
    MSG_NO_ACTIVE_CONFIGURATION,
    MSG_NO_ORIGINALS_USED,
    MSG_PRODUCTIVE_LOCKED,
    MSG_PROFILE_MISSING,
    DEFAULT_PROFILE_ID_SENTINEL,
    WorkspaceConfigurationSelection,
    build_compact_blocked_details,
    resolve_selection_from_state,
    resolve_workspace_configuration_selection,
)

ErgebnisAction = Literal["neue-konfiguration", "konfiguration-bearbeiten"]

# Honest empty-state copy (generic product UI-v2 — no private/demo run data).
EMPTY_NO_RUN_TITLE = "Noch kein Laufergebnis."
EMPTY_NO_RUN_DETAIL = (
    "Ordner wählen und Sandbox-Lauf starten. Ergebnisse erscheinen erst nach "
    "einem erfolgreichen Lauf. Unklare Fälle bleiben zur Prüfung."
)
EMPTY_NO_RUN_DETAIL_EXPANDED = (
    "Wähle Eingangs- und Ausgabeordner explizit und starte eine Verarbeitung erst, "
    "wenn Dry-Run und produktive Ausführung freigegeben sind. "
    "Ergebnisse erscheinen hier erst nach einem echten Lauf. "
    "Unklare Dokumente werden später im Prüfbereich angezeigt. "
    f"{MSG_CLARITY_UNCLEAR_STAYS_REVIEW} "
    f"{MSG_CLARITY_BUCKETS_SEPARATED} "
    f"{MSG_CLARITY_FILENAME_NOT_TRUTH}"
)
EMPTY_NO_RESULTS_TITLE = "Keine Ergebnisse vorhanden"
EMPTY_NO_RESULTS_DETAIL = "Keine Dokumente verarbeitet. Kein Lauf gestartet."
EMPTY_NO_RUN_STATUS = "Kein Lauf gestartet"
EMPTY_RESULT_COMPACT_TITLE = "Noch kein Laufergebnis."
START_CTA_LABEL = "Sandbox-Lauf starten"
ADAPTER_NOT_CONNECTED_HINT = MSG_BLOCKED_ADAPTER

# Preferred CTA feedback copy — always visible after click (no silent no-op).
MSG_RUN_STATUS_READY = "Bereit"
MSG_RUN_STATUS_CHECKING = "Prüfung läuft …"
MSG_RUN_STATUS_BLOCKED = "Blockiert"
MSG_RUN_STATUS_SANDBOX_NOT_CONNECTED = "Sandbox nicht verbunden"
MSG_RUN_STATUS_COMPLETED = "Abgeschlossen"
MSG_RUN_STATUS_FAILED = "Fehler"
MSG_SANDBOX_STARTED = "Sandbox-Lauf gestartet."
MSG_SANDBOX_BLOCKED_FOLDERS = (
    "Sandbox-Lauf blockiert: Bitte Eingangsordner und Ausgangsordner prüfen."
)
MSG_SANDBOX_BLOCKED_PRODUCTIVE = (
    "Sandbox-Lauf blockiert: Produktive Verarbeitung ist nicht freigegeben."
)
MSG_SANDBOX_BLOCKED_CORE_BRIDGE = (
    "Echte Verarbeitung noch nicht sicher verbunden."
)
MSG_SANDBOX_BRIDGE_NOT_CONNECTED = (
    "Sandbox nicht verbunden: Die echte Verarbeitung ist in Track B noch nicht "
    "sicher angebunden."
)
MSG_SANDBOX_NEXT_CORE_BRIDGE = (
    "Nächster technischer Schritt: sichere Core-Bridge für Sandbox/Dry-Run."
)
MSG_SANDBOX_NO_ORIGINALS_USED = MSG_NO_ORIGINALS_USED
MSG_SANDBOX_RESULTS_AFTER_SUCCESS = (
    "Ergebnisse erscheinen hier nach einem erfolgreichen Sandbox-Lauf."
)
MSG_SANDBOX_BLOCKED_PROFILE = (
    "Sandbox-Lauf blockiert: Bitte Profil und Konfiguration prüfen."
)
MSG_SANDBOX_BLOCKED_PROFILE_MISSING = f"Sandbox-Lauf blockiert: {MSG_PROFILE_MISSING}"
MSG_SANDBOX_BLOCKED_NO_ACTIVE_CONFIG = (
    f"Sandbox-Lauf blockiert: {MSG_NO_ACTIVE_CONFIGURATION}"
)
MSG_DETAIL_PRODUCTIVE_LOCKED = MSG_PRODUCTIVE_LOCKED
MSG_DETAIL_EXPORT_DRAFT = MSG_EXPORT_REMAINS_DRAFT
MSG_DETAIL_CORE_BRIDGE = MSG_CORE_BRIDGE_TECHNICAL
RUN_SETUP_SECTION_LABEL = "Lauf-Setup"
MSG_SANDBOX_COMPLETED = "Sandbox-Lauf abgeschlossen."
MSG_SANDBOX_FAILED = "Sandbox-Lauf fehlgeschlagen."
MSG_EXPORT_DISCLAIMER_COMPACT = (
    "Exportvorschau · kein produktiver DATEV-/Cloud-Export"
)

# Explicit folder selection copy — no private/default paths.
EMPTY_INPUT_FOLDER_TEXT = "Kein Eingangsordner gewählt."
EMPTY_OUTPUT_FOLDER_TEXT = "Kein Ausgabeordner gewählt."
PICK_INPUT_FOLDER_LABEL = "Eingangsordner wählen"
PICK_OUTPUT_FOLDER_LABEL = "Ausgabeordner wählen"
FOLDER_SELECTION_SECTION_LABEL = "Ordnerauswahl"
RUN_REPORT_SECTION_LABEL = "Ergebnisbericht"
EXPORT_PATH_HINT = "Lokaler Export-Vorschau-Pfad (JSON oder Ordner)"
EXPORT_ACTION_LABEL = "Ergebnisvorschau exportieren"
START_FEEDBACK_SECTION_LABEL = "Laufstatus"
ONBOARDING_SECTION_LABEL_COMPACT = "Pilotstatus"

# Honest sandbox readiness copy — no productive toggle, no folder create/scan.
SANDBOX_COPIED_RUN = MSG_SANDBOX_COPIED_RUN
SANDBOX_MODE_PREPARED = MSG_SANDBOX_MODE_PREPARED
SANDBOX_COPIED_DATA_ONLY = MSG_SANDBOX_COPIED_DATA_ONLY
SANDBOX_NO_ORIGINAL_INPUT = MSG_SANDBOX_NO_ORIGINAL_INPUT
SANDBOX_PRODUCTIVE_BLOCKED = MSG_SANDBOX_PRODUCTIVE_BLOCKED
SANDBOX_EXECUTION_WIRED = MSG_SANDBOX_EXECUTION_WIRED
SANDBOX_CORE_DRY_ABSENT = MSG_SANDBOX_CORE_DRY_ABSENT
SANDBOX_READINESS_LINES = WORKSPACE_SANDBOX_READINESS_LINES

# Local pilot onboarding panel (Prompt 10) — packaging/status only.
ONBOARDING_SECTION_LABEL = "Lokale Pilotversion / Onboarding"
ONBOARDING_STATUS_LINES = TRACK_B_ONBOARDING_STATUS_LINES
ONBOARDING_COMPACT_STATUS_ITEMS = COMPACT_PILOT_STATUS_ITEMS
ONBOARDING_NEXT_STEP = MSG_NEXT_STEP_FINAL_RELEASE_GATE


@dataclass(frozen=True)
class WorkspaceOnboardingPanelVM:
    """Pure onboarding/status panel for workspace — no GUI, no FS, no run."""

    section_label: str
    status_lines: tuple[str, ...]
    compact_status_items: tuple[str, ...]
    checklist: tuple[OnboardingChecklistItem, ...]
    next_step: str
    readiness: LocalPilotReadinessViewModel
    implies_saas_ready: bool
    implies_productive_export: bool
    has_productive_toggle: bool
    uses_compact_status_ui: bool


def build_workspace_onboarding_panel_vm(
    state: UiV2State | None = None,
) -> WorkspaceOnboardingPanelVM:
    """Build honest local-pilot onboarding for the workspace entry surface."""

    _ = state  # reserved for future safe checklist progress only
    readiness = build_local_pilot_readiness()
    return WorkspaceOnboardingPanelVM(
        section_label=ONBOARDING_SECTION_LABEL,
        status_lines=ONBOARDING_STATUS_LINES,
        compact_status_items=ONBOARDING_COMPACT_STATUS_ITEMS,
        checklist=readiness.checklist,
        next_step=ONBOARDING_NEXT_STEP,
        readiness=readiness,
        implies_saas_ready=False,
        implies_productive_export=False,
        has_productive_toggle=False,
        uses_compact_status_ui=True,
    )


@dataclass(frozen=True)
class _WorkspaceResultDisplay:
    result_id: str
    source_filename: str
    target_filename: str
    configuration_label: str
    destination_summary: str
    failed: bool
    reason: str | None = None
    suggestion: str | None = None
    action: ErgebnisAction | None = None


def _snapshot(state: UiV2State) -> UiV2ReadOnlySnapshot | None:
    snap = state.snapshot
    return snap if isinstance(snap, UiV2ReadOnlySnapshot) else None


def _navigate_to_configurations(state: UiV2State) -> None:
    if state.navigate:
        state.navigate(NAV_CONFIGURATIONS)


def _action_label(action: ErgebnisAction | None) -> str | None:
    if action == "neue-konfiguration":
        return "Konfiguration anlegen →"
    if action == "konfiguration-bearbeiten":
        return "Konfiguration bearbeiten →"
    return None


def _result_from_vm(index: int, result: ResultSummaryVM) -> _WorkspaceResultDisplay:
    target = result.destination_summary.rsplit("/", 1)[-1] if result.destination_summary else result.filename
    if target in {"", "—"}:
        target = result.filename
    failed = "fehl" in result.status_label.lower() or "error" in result.status_label.lower()
    return _WorkspaceResultDisplay(
        result_id=f"run-{index}",
        source_filename=result.filename,
        target_filename=target,
        configuration_label=result.configuration_label,
        destination_summary=result.destination_summary,
        failed=failed,
        reason=result.status_label if failed else None,
    )


def _result_from_processing_summary(
    index: int, result: ProcessingResultSummary
) -> _WorkspaceResultDisplay:
    """Map contract result rows only — never invent payment/account/business values."""

    target = (result.target_hint or "").strip() or result.document_name
    failed = (
        "fehl" in result.status_label.lower()
        or "error" in result.status_label.lower()
        or "fail" in result.classification_status.lower()
    )
    configuration_label = (result.document_type or "").strip() or "—"
    return _WorkspaceResultDisplay(
        result_id=f"contract-run-{index}",
        source_filename=result.document_name,
        target_filename=target,
        configuration_label=configuration_label,
        destination_summary=result.target_hint or "—",
        failed=failed,
        reason=result.status_label if failed else None,
    )


def _display_results(workspace_results: tuple[ResultSummaryVM, ...]) -> tuple[_WorkspaceResultDisplay, ...]:
    """Only real run results — never invent preview/mock rows."""
    if not workspace_results:
        return tuple()
    return tuple(_result_from_vm(index, item) for index, item in enumerate(workspace_results[:16]))


def _display_processing_results(
    contract_results: tuple[ProcessingResultSummary, ...],
) -> tuple[_WorkspaceResultDisplay, ...]:
    """Display only ProcessingResultSummary items provided by real run state."""

    if not contract_results:
        return tuple()
    return tuple(
        _result_from_processing_summary(index, item)
        for index, item in enumerate(contract_results[:16])
    )


def _display_mappings(results: tuple[_WorkspaceResultDisplay, ...]) -> tuple[tuple[str, str], ...]:
    """Map only successful real results; never invent filename-based preview mappings."""
    return tuple((item.source_filename, item.target_filename) for item in results if not item.failed)


def _has_real_run_results(
    workspace_results: tuple[ResultSummaryVM, ...],
    *,
    processing_results: tuple[ProcessingResultSummary, ...] = (),
) -> bool:
    return bool(workspace_results) or bool(processing_results)


def build_workspace_run_result_shell(state: UiV2State) -> RunResultDisplayShellVM:
    """Pure workspace run-result shell from ProcessingRunState — no GUI / no FS."""

    return build_run_result_display_shell(state.processing_run_state)


def build_workspace_run_report_vm(state: UiV2State) -> RunReportViewModel:
    """Five-question run report from ProcessingRunState — no GUI / no FS invent."""

    return build_run_report_view_model(state.processing_run_state)


def _report_item_lines(report: RunReportViewModel) -> list[tuple[str, str]]:
    """Compact metadata rows for the five report questions."""

    if report.empty:
        return [
            (SECTION_RECOGNIZED, MSG_RECOGNIZED_EMPTY),
            (SECTION_UNCLEAR, MSG_UNCLEAR_EMPTY),
            (SECTION_FAILED, MSG_FAILED_EMPTY),
            (SECTION_DESTINATIONS, MSG_DESTINATIONS_EMPTY),
            (SECTION_SUMMARY, MSG_NO_RUN_PAYLOAD),
        ]

    recognized_detail = (
        ", ".join(
            f"{item.document_name} ({item.document_type}/{item.status_label})"
            for item in report.recognized[:8]
        )
        or MSG_RECOGNIZED_EMPTY
    )
    unclear_detail = (
        ", ".join(f"{item.document_name}: {item.reason}" for item in report.unclear[:8])
        or MSG_UNCLEAR_EMPTY
    )
    failed_detail = (
        ", ".join(
            (f"{item.document_name}: {item.message}" if item.document_name else item.message)
            for item in report.failed[:8]
        )
        or MSG_FAILED_EMPTY
    )
    destination_detail = (
        ", ".join(
            f"{item.document_name} → {item.destination_hint}"
            for item in report.destinations[:8]
        )
        or MSG_DESTINATIONS_EMPTY
    )
    return [
        (SECTION_RECOGNIZED, recognized_detail),
        (SECTION_UNCLEAR, unclear_detail),
        (SECTION_FAILED, failed_detail),
        (SECTION_DESTINATIONS, destination_detail),
        (SECTION_SUMMARY, report.user_summary.headline),
    ]


def _build_run_report_panel(state: UiV2State, report: RunReportViewModel) -> list[ft.Control]:
    """Workspace Ergebnisbericht + Export — no original mutation, no processing start."""

    def _refresh() -> None:
        if state.refresh:
            state.refresh()

    def _export_click(_e: ft.ControlEvent, field: ft.TextField | None = None) -> None:
        path = (field.value if field is not None else state.workspace_export_path_draft) or ""
        state.export_run_report(path)
        _refresh()

    rows: list[ft.Control] = [
        compact_info_row("Status", report.status_label),
        compact_info_row("Lauf-ID", report.run_id or "—"),
    ]
    for label, value in _report_item_lines(report):
        rows.append(compact_info_row(label, value))
    rows.append(compact_info_row("Zusammenfassung", report.user_summary.detail))
    panel_controls: list[ft.Control] = [
        make_section_label(RUN_REPORT_SECTION_LABEL),
        dense_card(*rows),
        helper_text(MSG_EXPORT_DISCLAIMER_COMPACT),
        collapsible_details(
            MSG_EXPORT_IS_PREVIEW,
            MSG_EXPORT_FROM_REAL_RUN,
            MSG_EXPORT_NO_FILE_MUTATION_OF_ORIGINALS,
            MSG_PLANNED_DESTINATION_HINT,
            MSG_CLARITY_BUCKETS_SEPARATED,
            MSG_CLARITY_FILENAME_NOT_TRUTH,
            title="Export-Details anzeigen",
        ),
    ]
    if report.export_available:
        export_field = ft.TextField(
            value=state.workspace_export_path_draft,
            hint_text=EXPORT_PATH_HINT,
            expand=True,
            **outlined_field_kwargs(),
        )
        panel_controls.extend(
            [
                form_field_group(
                    "Exportpfad",
                    full_width_field(export_field),
                    helper=EXPORT_PATH_HINT,
                ),
                action_button(
                    EXPORT_ACTION_LABEL,
                    on_click=lambda e, field=export_field: _export_click(e, field),
                    primary=True,
                ),
            ]
        )
    if state.workspace_export_feedback:
        panel_controls.append(
            inline_warning(state.workspace_export_feedback)
            if state.workspace_export_feedback_error
            else summary_alert(state.workspace_export_feedback)
        )
    return panel_controls


@dataclass(frozen=True)
class WorkspaceReadinessDisplayVM:
    """Honest aggregated workspace readiness display — no fake counters/results."""

    input_folder_selected: bool
    output_folder_selected: bool
    input_folder_display: str | None
    output_folder_display: str | None
    run_status: ProcessingStatus
    run_status_label: str
    run_message: str
    dry_gate_blocked: bool
    dry_gate_message: str | None
    productive_hold: bool
    result_count: int
    review_count: int
    error_count: int
    implies_successful_processing: bool
    offers_productive_execution: bool
    has_fake_counters: bool


def build_workspace_readiness_display_vm(state: UiV2State) -> WorkspaceReadinessDisplayVM:
    """Aggregate folder/run/dry-gate/result/review/error state without inventing data."""

    folders = build_workspace_folder_selection_vm(state)
    shell = build_workspace_run_result_shell(state)
    run_state = state.processing_run_state or ProcessingRunState()
    dry_gate_blocked = (
        run_state.dry_run_gate == "unsupported_without_core_change"
        or run_state.core_dry_run_status == "unsupported_without_core_change"
        or run_state.execution_gate == "unsupported_without_core_change"
        or MSG_DRY_RUN_UNAVAILABLE in (run_state.message or "")
        or MSG_DRY_RUN_UNAVAILABLE in shell.blocked_hints
    )
    productive_hold = (
        MSG_PRODUCTIVE_HOLD in shell.blocked_hints
        or MSG_PRODUCTIVE_NOT_RELEASED in (run_state.message or "")
        or run_state.execution_gate == "productive_blocked"
    )
    return WorkspaceReadinessDisplayVM(
        input_folder_selected=bool(folders.input_folder),
        output_folder_selected=bool(folders.output_folder),
        input_folder_display=folders.input_folder_display,
        output_folder_display=folders.output_folder_display,
        run_status=shell.status,
        run_status_label=shell.status_label,
        run_message=shell.message or EMPTY_NO_RUN_STATUS,
        dry_gate_blocked=dry_gate_blocked,
        dry_gate_message=MSG_DRY_RUN_UNAVAILABLE if dry_gate_blocked else None,
        productive_hold=productive_hold,
        result_count=shell.result_count,
        review_count=shell.review.count,
        error_count=shell.errors.count,
        implies_successful_processing=shell.status == "completed",
        offers_productive_execution=False,
        has_fake_counters=False,
    )


def resolve_workspace_policy_bridge(state: UiV2State) -> RuntimePolicyBridgeResult:
    """Map active SaaS draft policy (or safe blank defaults) into runtime intent."""

    draft = state.saas_draft_store.profile_draft
    if draft is not None and getattr(draft, "classification_policy", None) is not None:
        return build_runtime_policy_intent(draft)
    # Honest safe defaults — no private tenant policy, still structured intent.
    return build_runtime_policy_intent(default_classification_policy())


def apply_workspace_input_folder_selection(state: UiV2State, path: str | None) -> None:
    """Apply an explicit input folder path string to UI state — no FS create/scan/PDF IO."""

    state.set_workspace_input_folder(path)


def apply_workspace_output_folder_selection(state: UiV2State, path: str | None) -> None:
    """Apply an explicit output folder path string to UI state — no FS create/scan/PDF IO."""

    state.set_workspace_output_folder(path)


@dataclass(frozen=True)
class WorkspaceFolderSelectionVM:
    """Pure folder-selection display state for workspace (no Flet / no filesystem)."""

    input_folder: str | None
    output_folder: str | None
    input_folder_display: str | None
    output_folder_display: str | None
    input_empty_text: str
    output_empty_text: str
    input_pick_label: str
    output_pick_label: str
    input_source: str
    output_source: str
    picker_wired: bool


def build_workspace_folder_selection_vm(state: UiV2State) -> WorkspaceFolderSelectionVM:
    """Build honest input/output folder display state from explicit UI overrides only."""

    input_folder = (state.workspace_input_folder_override or "").strip() or None
    output_folder = (state.workspace_output_folder_override or "").strip() or None
    input_source = state.workspace_input_folder_source or SOURCE_UNSET
    output_source = state.workspace_output_folder_source or SOURCE_UNSET
    if input_folder and input_source == SOURCE_UNSET:
        input_source = SOURCE_EXPLICIT_USER_SELECTION
    if output_folder and output_source == SOURCE_UNSET:
        output_source = SOURCE_EXPLICIT_USER_SELECTION
    return WorkspaceFolderSelectionVM(
        input_folder=input_folder,
        output_folder=output_folder,
        input_folder_display=display_path_value(input_folder) if input_folder else None,
        output_folder_display=display_path_value(output_folder) if output_folder else None,
        input_empty_text=EMPTY_INPUT_FOLDER_TEXT,
        output_empty_text=EMPTY_OUTPUT_FOLDER_TEXT,
        input_pick_label=PICK_INPUT_FOLDER_LABEL,
        output_pick_label=PICK_OUTPUT_FOLDER_LABEL,
        input_source=input_source,
        output_source=output_source,
        # Native FilePicker is wired to state only — no scan/create/PDF processing.
        picker_wired=True,
    )


def derive_sandbox_root_from_folders(
    input_folder: str | None,
    output_folder: str | None,
) -> str | None:
    """Derive a shared sandbox root from explicit folder strings — no FS access."""

    left = (input_folder or "").strip().replace("\\", "/")
    right = (output_folder or "").strip().replace("\\", "/")
    if not left or not right:
        return None
    try:
        common = os.path.commonpath([left, right])
    except ValueError:
        return None
    normalized = (common or "").replace("\\", "/").rstrip("/")
    if not normalized or normalized in {".", "/", "\\"}:
        return None
    # Reject drive roots like "C:" / "C:/".
    if len(normalized) <= 3 and ":" in normalized:
        return None
    return normalized


def prepare_sandbox_intent_for_cta(state: UiV2State) -> None:
    """CTA prepares sandbox-only intent from explicit folders — no originals invented."""

    state.workspace_sandbox_mode = True
    state.workspace_copied_data_confirmed = True
    if not (state.workspace_sandbox_root or "").strip():
        derived = derive_sandbox_root_from_folders(
            state.workspace_input_folder_override,
            state.workspace_output_folder_override,
        )
        if derived:
            state.workspace_sandbox_root = derived


@dataclass(frozen=True)
class StartInteractionFeedback:
    """Structured start-button feedback — primary line + secondary details."""

    interaction_status: str
    status_label: str
    primary: str
    details: tuple[str, ...]
    tone: str

    @property
    def combined(self) -> str:
        parts = [self.primary, *self.details]
        return " ".join(part for part in parts if part).strip()


def _compact_details(
    *,
    configuration_label: str | None = None,
    core_bridge_relevant: bool = False,
    extra: tuple[str, ...] = (),
) -> tuple[str, ...]:
    base = build_compact_blocked_details(
        configuration_label=configuration_label,
        core_bridge_relevant=core_bridge_relevant,
    )
    merged: list[str] = []
    for item in (*extra, *base):
        text = str(item or "").strip()
        if text and text not in merged:
            merged.append(text)
    return tuple(merged[:MAX_BLOCKED_DETAIL_LINES])


def _feedback(
    *,
    interaction_status: str,
    status_label: str,
    primary: str,
    details: tuple[str, ...] = (),
    tone: str = "blocked",
) -> StartInteractionFeedback:
    cleaned = tuple(dict.fromkeys(item for item in details if str(item or "").strip()))
    cleaned = cleaned[:MAX_BLOCKED_DETAIL_LINES]
    return StartInteractionFeedback(
        interaction_status=interaction_status,
        status_label=status_label,
        primary=primary.strip(),
        details=cleaned,
        tone=tone,
    )


def build_start_interaction_feedback(
    result: ProcessingRunState,
    *,
    configuration_label: str | None = None,
) -> StartInteractionFeedback:
    """Map ProcessingRunState into compact primary + secondary details."""

    message = (result.message or "").strip()
    status = result.status
    gate = result.execution_gate
    errors = " ".join(str(item) for item in (result.errors or ()))
    blob = f"{message} {errors}".lower()
    config_label = (configuration_label or "").strip() or None

    if status == "completed":
        return _feedback(
            interaction_status="completed",
            status_label=MSG_RUN_STATUS_COMPLETED,
            primary=MSG_SANDBOX_COMPLETED,
            details=_compact_details(
                configuration_label=config_label,
                extra=(MSG_SANDBOX_STARTED, message),
            ),
            tone="completed",
        )

    if status in {"running", "ready"}:
        return _feedback(
            interaction_status="checking",
            status_label=MSG_RUN_STATUS_CHECKING,
            primary=message or MSG_SANDBOX_STARTED,
            details=_compact_details(configuration_label=config_label),
            tone="checking",
        )

    unbound = (
        "sandbox_core_runner_unbound" in errors
        or MSG_SANDBOX_RUNNER_UNBOUND in message
        or "noch nicht mit der verarbeitung verbunden" in blob
        or "noch nicht sicher verbunden" in blob
        or "noch nicht sicher angebunden" in blob
        or (status == "failed" and gate == "ready_for_sandbox_execution")
    )
    if unbound or status == "failed":
        if unbound or "sandbox" in blob or "core" in blob or "verbunden" in blob or "angebunden" in blob:
            return _feedback(
                interaction_status="sandbox_not_connected",
                status_label=MSG_RUN_STATUS_SANDBOX_NOT_CONNECTED,
                primary=MSG_SANDBOX_BRIDGE_NOT_CONNECTED,
                details=_compact_details(
                    configuration_label=config_label,
                    core_bridge_relevant=True,
                ),
                tone="sandbox_not_connected",
            )
        return _feedback(
            interaction_status="failed",
            status_label=MSG_RUN_STATUS_FAILED,
            primary=f"{MSG_SANDBOX_FAILED} {message}".strip(),
            details=_compact_details(configuration_label=config_label),
            tone="failed",
        )

    if (
        gate in {"blocked_productive_execution", "productive_blocked"}
        or MSG_PRODUCTIVE_NOT_RELEASED in message
        or ("produktive" in blob and "nicht freigegeben" in blob)
    ):
        return _feedback(
            interaction_status="blocked",
            status_label=MSG_RUN_STATUS_BLOCKED,
            primary=MSG_SANDBOX_BLOCKED_PRODUCTIVE,
            details=_compact_details(configuration_label=config_label),
            tone="blocked",
        )

    if (
        MSG_BLOCKED_ADAPTER in message
        or "noch nicht angebunden" in blob
        or "lauf-adapter" in blob
    ):
        return _feedback(
            interaction_status="sandbox_not_connected",
            status_label=MSG_RUN_STATUS_SANDBOX_NOT_CONNECTED,
            primary=MSG_SANDBOX_BRIDGE_NOT_CONNECTED,
            details=_compact_details(
                configuration_label=config_label,
                core_bridge_relevant=True,
            ),
            tone="sandbox_not_connected",
        )

    missing_folders = (
        MSG_MISSING_INPUT in message
        or MSG_MISSING_OUTPUT in message
        or "eingangsordner" in blob
        or "ausgabeordner" in blob
        or "benutzerauswahl" in blob
        or "quelle gesetzt" in blob
        or (status == "not_configured" and "ordner" in blob)
    )
    if missing_folders:
        return _feedback(
            interaction_status="blocked",
            status_label=MSG_RUN_STATUS_BLOCKED,
            primary=MSG_SANDBOX_BLOCKED_FOLDERS,
            details=_compact_details(
                configuration_label=config_label,
                extra=(message or MSG_SANDBOX_BLOCKED_FOLDERS,),
            ),
            tone="blocked",
        )

    if MSG_PROFILE_MISSING in message or "profil fehlt" in blob:
        return _feedback(
            interaction_status="blocked",
            status_label=MSG_RUN_STATUS_BLOCKED,
            primary=MSG_SANDBOX_BLOCKED_PROFILE_MISSING,
            details=_compact_details(
                configuration_label=config_label,
                extra=(MSG_PROFILE_MISSING,),
            ),
            tone="blocked",
        )

    if MSG_NO_ACTIVE_CONFIGURATION in message or "keine aktive konfiguration" in blob:
        return _feedback(
            interaction_status="blocked",
            status_label=MSG_RUN_STATUS_BLOCKED,
            primary=MSG_SANDBOX_BLOCKED_NO_ACTIVE_CONFIG,
            details=_compact_details(
                configuration_label="fehlt",
                extra=(MSG_NO_ACTIVE_CONFIGURATION, MSG_CONFIGURATION_CHANGE_HINT),
            ),
            tone="blocked",
        )

    if "profil" in blob or "konfiguration" in blob or status == "not_configured":
        return _feedback(
            interaction_status="blocked",
            status_label=MSG_RUN_STATUS_BLOCKED,
            primary=MSG_SANDBOX_BLOCKED_PROFILE,
            details=_compact_details(
                configuration_label=config_label,
                extra=(message or MSG_SANDBOX_BLOCKED_PROFILE,),
            ),
            tone="blocked",
        )

    if status == "blocked":
        return _feedback(
            interaction_status="sandbox_not_connected",
            status_label=MSG_RUN_STATUS_SANDBOX_NOT_CONNECTED,
            primary=MSG_SANDBOX_BRIDGE_NOT_CONNECTED,
            details=_compact_details(
                configuration_label=config_label,
                core_bridge_relevant=True,
            ),
            tone="sandbox_not_connected",
        )

    detail = message or EMPTY_NO_RUN_STATUS
    return _feedback(
        interaction_status="blocked",
        status_label=MSG_RUN_STATUS_BLOCKED,
        primary=f"Sandbox-Lauf blockiert: {detail}",
        details=_compact_details(configuration_label=config_label),
        tone="blocked",
    )


def build_start_button_feedback(result: ProcessingRunState) -> str:
    """Map ProcessingRunState into preferred German CTA feedback (always visible)."""

    return build_start_interaction_feedback(result).combined


def mark_start_checking(state: UiV2State) -> None:
    """Immediately surface checking state before the adapter returns."""

    selection = resolve_selection_from_state(state)
    state.workspace_run_interaction_status = "checking"
    state.workspace_start_feedback_primary = MSG_RUN_STATUS_CHECKING
    state.workspace_start_feedback = MSG_RUN_STATUS_CHECKING
    state.workspace_start_feedback_details = list(
        _compact_details(configuration_label=selection.configuration_display)
    )
    state.processing_run_state = ProcessingRunState(
        status="running",
        message=MSG_RUN_STATUS_CHECKING,
        run_id=state.processing_run_state.run_id,
        results=tuple(state.processing_run_state.results or ()),
        review_items=tuple(state.processing_run_state.review_items or ()),
        errors=tuple(state.processing_run_state.errors or ()),
        execution_gate=state.processing_run_state.execution_gate,
        dry_run_gate=state.processing_run_state.dry_run_gate,
        core_dry_run_status=state.processing_run_state.core_dry_run_status,
    )


def resolve_workspace_configuration_selection_for_state(
    state: UiV2State,
    *,
    profile_id: str | None = None,
    explicit_configuration_id: str | None = None,
) -> WorkspaceConfigurationSelection:
    """Resolve profile + active configuration for workspace sandbox start."""

    snap = state.snapshot if isinstance(state.snapshot, UiV2ReadOnlySnapshot) else None
    selected_profile = (profile_id or "").strip() or None
    if selected_profile is None:
        selected_profile = (state.selected_profile_id or "").strip() or None
        if selected_profile == DEFAULT_PROFILE_ID_SENTINEL and snap is not None:
            selected_profile = None
    explicit = (explicit_configuration_id or "").strip() or None
    if explicit is None:
        explicit = (state.config_list_selected_id or "").strip() or None
    return resolve_workspace_configuration_selection(
        snapshot=snap,
        profile_id=selected_profile,
        explicit_configuration_id=explicit,
    )


def build_processing_run_request(
    state: UiV2State,
    *,
    profile_id: str | None = None,
    configuration_id: str | None = None,
    user_confirmed_start: bool = False,
) -> ProcessingRunRequest:
    """Build a contract request from UI-v2 selection + resolved active configuration."""

    folder = (state.workspace_input_folder_override or "").strip() or None
    output_folder = (state.workspace_output_folder_override or "").strip() or None
    source = (
        SOURCE_EXPLICIT_USER_SELECTION
        if state.has_explicit_workspace_folder_selection()
        else SOURCE_UNSET
    )
    policy_bridge = resolve_workspace_policy_bridge(state)
    # Folders only from explicit overrides — never Desktop/private defaults.
    # Profile from caller / snapshot; configuration from explicit id or active
    # snapshot configurations (auto/default). Never invent private tenant defaults.
    selection = resolve_workspace_configuration_selection_for_state(
        state,
        profile_id=profile_id,
        explicit_configuration_id=(
            (configuration_id or "").strip()
            or (state.config_list_selected_id or "").strip()
            or None
        ),
    )
    resolved_configuration = selection.selected_configuration_id
    resolved_profile = selection.profile_id or ((profile_id or "").strip() or None)
    sandbox_root = (state.workspace_sandbox_root or "").strip() or None
    original_source = (state.workspace_original_source_folder or "").strip() or None
    sandbox_mode = bool(state.workspace_sandbox_mode)
    return ProcessingRunRequest(
        input_folder=folder,
        output_folder=output_folder,
        profile_id=resolved_profile,
        configuration_id=resolved_configuration,
        dry_run=True,
        source=source,
        policy_intent=policy_bridge.intent,
        policy_bridge_result=policy_bridge,
        user_confirmed_start=bool(user_confirmed_start),
        sandbox_mode=sandbox_mode,
        sandbox_root=sandbox_root,
        original_source_folder=original_source,
        copied_data_confirmed=bool(state.workspace_copied_data_confirmed),
        productive_execution_allowed=False,
        execution_scope="sandbox" if sandbox_mode else "blocked",
    )


def apply_start_processing(state: UiV2State, *, profile_id: str | None = None) -> ProcessingRunState:
    """Invoke the bounded processing service — never imports processing-core.

    Live Track-B UI injects LocalProcessingAdapter. CTA prepares sandbox intent,
    resolves an active configuration when available, sets user_confirmed_start=True,
    and always writes visible workspace feedback.
    Still no productive execution and no original-folder mutation.
    """

    mark_start_checking(state)
    prepare_sandbox_intent_for_cta(state)
    selection = resolve_workspace_configuration_selection_for_state(
        state,
        profile_id=profile_id,
        explicit_configuration_id=(state.config_list_selected_id or "").strip() or None,
    )
    if selection.selected_configuration_id:
        state.config_list_selected_id = selection.selected_configuration_id

    request = build_processing_run_request(
        state,
        profile_id=selection.profile_id or profile_id,
        configuration_id=selection.selected_configuration_id,
        user_confirmed_start=True,
    )
    result = state.processing_service.start_run(request)
    # Prefer compact workspace selection copy when the gate only knows “config missing”.
    if (
        not selection.is_ready
        and selection.blocker_message
        and result.status in {"not_configured", "blocked"}
        and (
            "konfiguration" in (result.message or "").lower()
            or "profil" in (result.message or "").lower()
            or result.execution_gate
            in {"blocked_missing_configuration", "blocked_missing_profile"}
        )
    ):
        result = ProcessingRunState(
            status=result.status,
            message=selection.blocker_message,
            run_id=result.run_id,
            results=tuple(result.results or ()),
            review_items=tuple(result.review_items or ()),
            errors=tuple(result.errors or ()),
            execution_gate=(
                "blocked_missing_profile"
                if selection.resolution == "missing_profile"
                else result.execution_gate or "blocked_missing_configuration"
            ),
            dry_run_gate=result.dry_run_gate,
            core_dry_run_status=result.core_dry_run_status,
        )
    interaction = build_start_interaction_feedback(
        result,
        configuration_label=selection.configuration_display,
    )
    feedback = interaction.combined
    # Keep adapter status/results; surface preferred German CTA copy in message.
    state.processing_run_state = ProcessingRunState(
        status=result.status,
        message=feedback,
        run_id=result.run_id,
        results=tuple(result.results or ()),
        review_items=tuple(result.review_items or ()),
        errors=tuple(result.errors or ()),
        execution_gate=result.execution_gate,
        dry_run_gate=result.dry_run_gate,
        core_dry_run_status=result.core_dry_run_status,
    )
    state.workspace_run_interaction_status = interaction.interaction_status
    state.workspace_start_feedback_primary = interaction.primary
    state.workspace_start_feedback_details = list(interaction.details)
    state.workspace_start_feedback = feedback
    return state.processing_run_state


@dataclass(frozen=True)
class WorkspaceHonestyCopy:
    """Pure empty-state copy for the workspace (no Flet / no processing)."""

    has_real_results: bool
    status_line: str | None
    results_title: str | None
    results_detail: str | None
    processing_status: ProcessingStatus = "idle"
    start_cta_label: str = START_CTA_LABEL
    start_cta_disabled: bool = True
    adapter_hint: str | None = ADAPTER_NOT_CONNECTED_HINT
    policy_intent_status: str | None = None
    policy_intent_hint: str | None = None
    sandbox_readiness_lines: tuple[str, ...] = ()


def workspace_honesty_copy(
    *,
    has_real_results: bool,
    processing_state: ProcessingRunState | None = None,
    policy_bridge: RuntimePolicyBridgeResult | None = None,
) -> WorkspaceHonestyCopy:
    """Return honest empty-state copy when no real UI-v2 run results exist."""
    proc = processing_state or ProcessingRunState()
    status = proc.status
    policy_status = policy_bridge.status if policy_bridge is not None else None
    policy_hint = None
    sandbox_lines = workspace_sandbox_readiness_copy()
    if policy_bridge is not None and policy_bridge.status in {"incomplete", "blocked"}:
        policy_hint = f"{MSG_POLICY_NOT_READY} {MSG_UNKNOWN_EVIDENCE_REVIEW}"
        if policy_bridge.status == "incomplete":
            policy_hint = f"{MSG_POLICY_INCOMPLETE} {MSG_UNKNOWN_EVIDENCE_REVIEW}"

    if has_real_results:
        return WorkspaceHonestyCopy(
            has_real_results=True,
            status_line=None,
            results_title=None,
            results_detail=None,
            processing_status=status,
            start_cta_label=START_CTA_LABEL,
            start_cta_disabled=False,
            adapter_hint=None,
            policy_intent_status=policy_status,
            policy_intent_hint=policy_hint,
            sandbox_readiness_lines=sandbox_lines,
        )

    if status == "blocked":
        # Prefer the CTA message — never imply a silent no-op / "no run attempted".
        if proc.message and proc.message not in {MSG_IDLE, "", MSG_BLOCKED_ADAPTER}:
            status_line = proc.message
        else:
            status_line = (
                f"{MSG_SANDBOX_BRIDGE_NOT_CONNECTED} {MSG_SANDBOX_BLOCKED_CORE_BRIDGE} "
                f"{ADAPTER_NOT_CONNECTED_HINT}"
            )
        if policy_hint and MSG_POLICY_NOT_READY in (proc.message or ""):
            status_line = f"{policy_hint} {MSG_SANDBOX_RESULTS_AFTER_SUCCESS}"
        elif policy_hint and "blockieren" in (proc.message or "").lower():
            status_line = f"{policy_hint} {MSG_SANDBOX_RESULTS_AFTER_SUCCESS}"
        detail = (
            f"{status_line} {ADAPTER_NOT_CONNECTED_HINT} {MSG_BLOCKED_ADAPTER} "
            f"{MSG_SANDBOX_NO_ORIGINALS_USED} {MSG_SANDBOX_RESULTS_AFTER_SUCCESS} "
            "Unklare Dokumente werden später im Prüfbereich angezeigt."
        )
        if policy_hint and policy_hint not in detail:
            detail = f"{policy_hint} {detail}"
    elif status == "not_configured":
        if proc.message and proc.message not in {MSG_IDLE, "", MSG_NOT_CONFIGURED}:
            status_line = proc.message
        else:
            status_line = f"{MSG_SANDBOX_BLOCKED_FOLDERS} {MSG_NOT_CONFIGURED}"
        if MSG_MISSING_INPUT in (proc.message or ""):
            status_line = f"{MSG_SANDBOX_BLOCKED_FOLDERS} {MSG_MISSING_INPUT}"
        elif MSG_MISSING_OUTPUT in (proc.message or ""):
            status_line = f"{MSG_SANDBOX_BLOCKED_FOLDERS} {MSG_MISSING_OUTPUT}"
        elif policy_hint and (
            MSG_POLICY_INCOMPLETE in (proc.message or "")
            or MSG_POLICY_NOT_READY in (proc.message or "")
        ):
            status_line = f"{policy_hint} {MSG_SANDBOX_RESULTS_AFTER_SUCCESS}"
        detail = (
            f"{status_line} {MSG_SANDBOX_NO_ORIGINALS_USED} "
            f"{MSG_SANDBOX_RESULTS_AFTER_SUCCESS}"
        )
        if policy_hint and policy_hint not in detail:
            detail = f"{policy_hint} {detail}"
    elif status in {"failed", "completed", "running"}:
        status_line = proc.message or (
            MSG_SANDBOX_COMPLETED if status == "completed" else MSG_SANDBOX_FAILED
        )
        detail = (
            f"{status_line} {MSG_SANDBOX_NO_ORIGINALS_USED} "
            f"{MSG_SANDBOX_RESULTS_AFTER_SUCCESS}"
        )
        if policy_hint:
            detail = f"{policy_hint} {detail}"
    else:
        status_line = f"{EMPTY_NO_RUN_STATUS}. {EMPTY_NO_RESULTS_TITLE}."
        if proc.message and proc.message not in {MSG_IDLE, ""}:
            status_line = f"{proc.message} {EMPTY_NO_RESULTS_TITLE}."
        detail = EMPTY_NO_RUN_DETAIL_EXPANDED
        if policy_hint:
            detail = f"{policy_hint} {detail}"

    # Surface dry/no-mutation gate honestly when adapter reports it.
    if status == "blocked" and MSG_DRY_RUN_UNAVAILABLE in (proc.message or ""):
        status_line = f"{MSG_DRY_RUN_UNAVAILABLE} {EMPTY_NO_RUN_STATUS}."
        detail = (
            f"{MSG_DRY_RUN_UNAVAILABLE} "
            f"{MSG_PRODUCTIVE_HOLD} "
            f"{MSG_PRODUCTIVE_NOT_RELEASED} "
            "Ergebnisse erscheinen hier erst nach einem echten Lauf über einen "
            "angebundenen Adapter. Unklare Dokumente werden später im Prüfbereich angezeigt."
        )
    elif status == "blocked" and (
        proc.execution_gate in {"productive_blocked", "unsupported_without_core_change"}
        or MSG_PRODUCTIVE_NOT_RELEASED in (proc.message or "")
    ):
        # Honest productive hold — never implies a completed run or fake results.
        if MSG_PRODUCTIVE_HOLD not in (status_line or ""):
            status_line = f"{MSG_PRODUCTIVE_HOLD} {EMPTY_NO_RUN_STATUS}."
        if MSG_PRODUCTIVE_HOLD not in detail:
            detail = f"{MSG_PRODUCTIVE_HOLD} {detail}"

    # Always surface sandbox readiness honestly (no productive toggle / no auto-create).
    sandbox_block = " ".join(sandbox_lines)
    if sandbox_block and sandbox_block not in detail:
        detail = f"{detail} {sandbox_block}"

    return WorkspaceHonestyCopy(
        has_real_results=False,
        status_line=status_line,
        results_title=EMPTY_NO_RUN_TITLE,
        results_detail=detail,
        processing_status=status,
        start_cta_label=START_CTA_LABEL,
        # Clickable so the contract handler can return an honest blocked/not_configured state.
        start_cta_disabled=False,
        adapter_hint=ADAPTER_NOT_CONNECTED_HINT,
        policy_intent_status=policy_status,
        policy_intent_hint=policy_hint,
        sandbox_readiness_lines=sandbox_lines,
    )


def _schedule_folder_picker(
    state: UiV2State,
    refresh: Callable[[], None],
    *,
    role: Literal["input", "output"],
) -> Callable[[ft.ControlEvent], None]:
    """Wire native folder picker to UI state only — no scan, create, or PDF processing."""

    dialog_title = (
        "Eingangsordner auswählen" if role == "input" else "Ausgabeordner auswählen"
    )

    async def _pick_folder(_event: ft.ControlEvent) -> None:
        path = await choose_target_folder(dialog_title=dialog_title)
        if not path:
            return
        if role == "input":
            apply_workspace_input_folder_selection(state, path)
        else:
            apply_workspace_output_folder_selection(state, path)
        refresh()

    def _handler(event: ft.ControlEvent) -> None:
        page = state.page
        if page is not None and hasattr(page, "run_task"):
            page.run_task(_pick_folder, event)

    return _handler


def _schedule_start_processing(
    state: UiV2State,
    refresh: Callable[[], None],
    *,
    profile_id: str | None,
) -> Callable[[ft.ControlEvent], None]:
    def _handler(_event: ft.ControlEvent) -> None:
        # Immediate visible transition before the adapter finishes.
        mark_start_checking(state)
        refresh()
        apply_start_processing(state, profile_id=profile_id)
        refresh()

    return _handler


def build_workspace_page(state: UiV2State) -> ft.Control:
    snapshot = _snapshot(state)
    if snapshot is None:
        return page_scaffold(
            page_header(
                "Arbeitsbereich",
                subtitle="Dokumente auswählen, verarbeiten und Ergebnisse prüfen.",
            ),
            inline_warning("Arbeitsbereichsdaten vorübergehend nicht verfügbar."),
        )

    workspace = snapshot.workspace
    profile_name = snapshot.profile.profile_name
    scan_model = snapshot.profile.scan_model_name
    active_tab = state.workspace_tab if state.workspace_tab in {"zielordner", "ergebnisse"} else "zielordner"

    def _refresh() -> None:
        if state.refresh:
            state.refresh()

    def _set_tab(tab_id: str) -> None:
        state.workspace_tab = tab_id
        _refresh()

    folder_selection = build_workspace_folder_selection_vm(state)
    run_shell = build_workspace_run_result_shell(state)
    readiness = build_workspace_readiness_display_vm(state)
    onboarding = build_workspace_onboarding_panel_vm(state)
    run_report = build_workspace_run_report_vm(state)
    config_selection = resolve_workspace_configuration_selection_for_state(
        state,
        profile_id=snapshot.profile.profile_id,
    )
    contract_results = tuple(state.processing_run_state.results or ())
    snapshot_display = _display_results(workspace.results)
    contract_display = _display_processing_results(contract_results)
    # Prefer explicit contract results when present; otherwise keep snapshot payload.
    display_results = contract_display or snapshot_display
    has_real_results = _has_real_run_results(
        workspace.results,
        processing_results=contract_results,
    )
    policy_bridge = resolve_workspace_policy_bridge(state)
    honesty = workspace_honesty_copy(
        has_real_results=has_real_results,
        processing_state=state.processing_run_state,
        policy_bridge=policy_bridge,
    )
    # Display only explicit UI override — never invent Desktop/private snapshot defaults.
    input_path = folder_selection.input_folder_display
    output_path = folder_selection.output_folder_display

    pick_input_folder = _schedule_folder_picker(state, _refresh, role="input")
    pick_output_folder = _schedule_folder_picker(state, _refresh, role="output")
    start_processing = _schedule_start_processing(
        state,
        _refresh,
        profile_id=snapshot.profile.profile_id,
    )
    mappings = _display_mappings(display_results) if has_real_results else tuple()
    fail_count = sum(1 for result in display_results if result.failed) if has_real_results else 0
    ok_count = (len(display_results) - fail_count) if has_real_results else None
    fail_count_display = fail_count if has_real_results else None

    folder_selection_panel = make_workspace_folder_selection_panel(
        input_path_display=input_path,
        output_path_display=output_path,
        input_empty_text=folder_selection.input_empty_text,
        output_empty_text=folder_selection.output_empty_text,
        input_pick_label=folder_selection.input_pick_label,
        output_pick_label=folder_selection.output_pick_label,
        on_pick_input=pick_input_folder if folder_selection.picker_wired else None,
        on_pick_output=pick_output_folder if folder_selection.picker_wired else None,
        pick_disabled=not folder_selection.picker_wired,
    )

    run_panel = make_workspace_run_panel(
        folder_path=input_path,
        on_change_folder=pick_input_folder if input_path else None,
        on_pick_folder=pick_input_folder if not input_path else None,
        on_start=start_processing,
        start_label=honesty.start_cta_label,
        start_disabled=honesty.start_cta_disabled,
        on_restart=(lambda _e: _refresh()) if (input_path and has_real_results) else None,
        on_details=(lambda _e: _set_tab("ergebnisse")) if has_real_results else None,
        ok_count=ok_count if input_path else None,
        fail_count=fail_count_display if input_path else None,
        mappings=mappings if input_path else tuple(),
        pick_folder_label=PICK_INPUT_FOLDER_LABEL,
        empty_folder_text=EMPTY_INPUT_FOLDER_TEXT,
    )

    tab_bar = make_tab_bar(
        (("zielordner", "Zielordner"), ("ergebnisse", "Letzte Ergebnisse")),
        active_id=active_tab,
        on_select=_set_tab,
        badges={"ergebnisse": fail_count} if fail_count else None,
    )

    tab_blocks: list[ft.Control] = []
    if active_tab == "zielordner":
        if workspace.destinations:
            missing_count = sum(1 for destination in workspace.destinations if destination.destination_missing)
            if missing_count:
                total = len(workspace.destinations)
                tab_blocks.append(
                    summary_alert(
                        f"{missing_count} von {total} Zielordnern fehlen oder sind nicht erreichbar. "
                        "Bitte Pfade in den Konfigurationen korrigieren."
                    )
                )
            destination_rows: list[ft.Control] = []
            for index, destination in enumerate(workspace.destinations):
                if index > 0:
                    destination_rows.append(divider())
                destination_rows.append(
                    make_destination_list_row(
                        destination.configuration_name,
                        display_path_value(destination.destination_summary),
                        missing=destination.destination_missing,
                        on_correct=lambda _e: _navigate_to_configurations(state),
                    )
                )
            tab_blocks.append(make_full_width_panel(ft.Column(destination_rows, spacing=0)))
        else:
            tab_blocks.append(
                make_full_width_panel(
                    empty_state(
                        "Keine Zielordner konfiguriert",
                        detail="Richten Sie Zielordner in den Konfigurationen ein.",
                        icon=ft.Icons.FOLDER_OFF_OUTLINED,
                    )
                )
            )
    else:
        if not has_real_results:
            tab_blocks.append(
                make_full_width_panel(
                    empty_state(
                        EMPTY_RESULT_COMPACT_TITLE,
                        detail=None,
                        icon=ft.Icons.INBOX_OUTLINED,
                        compact=True,
                    )
                )
            )
        else:
            if fail_count:
                tab_blocks.append(
                    summary_alert(
                        f"{fail_count} Dateien konnten nicht verarbeitet werden. "
                        "Eintrag aufklappen für Details und manuelle Korrektur."
                    )
                )
            result_rows: list[ft.Control] = []
            for index, result in enumerate(display_results):
                if index > 0:
                    result_rows.append(divider())

                def _toggle(_e: ft.ControlEvent, rid: str = result.result_id) -> None:
                    if rid in state.workspace_expanded_results:
                        state.workspace_expanded_results.discard(rid)
                    else:
                        state.workspace_expanded_results.add(rid)
                    _refresh()

                result_rows.append(
                    make_ergebnis_row(
                        result_id=result.result_id,
                        source_filename=result.source_filename,
                        target_filename=result.target_filename,
                        configuration_label=result.configuration_label,
                        failed=result.failed,
                        reason=result.reason,
                        suggestion=result.suggestion,
                        action_label=_action_label(result.action),
                        expanded=result.result_id in state.workspace_expanded_results,
                        on_toggle=_toggle if result.failed else None,
                        on_action=lambda _e: _navigate_to_configurations(state) if result.action else None,
                    )
                )
            tab_blocks.append(make_full_width_panel(ft.Column(result_rows, spacing=0)))

    interaction_status = (state.workspace_run_interaction_status or "idle").strip() or "idle"
    primary_feedback = (state.workspace_start_feedback_primary or "").strip()
    if not primary_feedback and state.processing_run_state.status != "idle":
        primary_feedback = (state.processing_run_state.message or "").strip()
    detail_feedback = list(state.workspace_start_feedback_details or [])
    core_bridge_relevant = interaction_status == "sandbox_not_connected" or (
        "core-bridge" in primary_feedback.lower()
        or "nicht sicher angebunden" in primary_feedback.lower()
        or "nicht verbunden" in primary_feedback.lower()
    )
    if interaction_status == "idle" and not primary_feedback:
        status_label = MSG_RUN_STATUS_READY
        if not config_selection.is_ready and config_selection.blocker_message:
            primary_feedback = config_selection.blocker_message
            tone = "blocked"
            status_label = MSG_RUN_STATUS_BLOCKED
        else:
            primary_feedback = "Ordner wählen und Sandbox-Lauf starten."
            tone = "ready"
        detail_feedback = list(
            _compact_details(
                configuration_label=config_selection.configuration_display,
                core_bridge_relevant=False,
            )
        )
    elif interaction_status == "checking":
        status_label = MSG_RUN_STATUS_CHECKING
        primary_feedback = primary_feedback or MSG_RUN_STATUS_CHECKING
        tone = "checking"
    elif interaction_status == "sandbox_not_connected":
        status_label = MSG_RUN_STATUS_SANDBOX_NOT_CONNECTED
        primary_feedback = primary_feedback or MSG_SANDBOX_BRIDGE_NOT_CONNECTED
        tone = "sandbox_not_connected"
        core_bridge_relevant = True
    elif interaction_status == "completed":
        status_label = MSG_RUN_STATUS_COMPLETED
        tone = "completed"
    elif interaction_status == "failed":
        status_label = MSG_RUN_STATUS_FAILED
        tone = "failed"
    else:
        status_label = MSG_RUN_STATUS_BLOCKED
        tone = "blocked"

    # Compact details only — no sandbox readiness bullet wall.
    sandbox_detail_lines = list(
        _compact_details(
            configuration_label=config_selection.configuration_display,
            core_bridge_relevant=core_bridge_relevant,
            extra=tuple(detail_feedback),
        )
    )

    run_status_panel = compact_run_status_panel(
        status_label=status_label,
        primary_reason=primary_feedback,
        details=tuple(sandbox_detail_lines[:MAX_BLOCKED_DETAIL_LINES]),
        tone=tone,
        details_title="Details anzeigen",
    )

    run_setup_panel = make_context_strip(
        ("Profil", config_selection.profile_display or profile_name),
        ("Konfiguration", config_selection.configuration_display),
        ("Eingang", "gewählt" if readiness.input_folder_selected else "fehlt"),
        ("Ausgang", "gewählt" if readiness.output_folder_selected else "fehlt"),
    )
    run_setup_hint = None
    if config_selection.is_ready and config_selection.change_hint:
        run_setup_hint = helper_text(config_selection.change_hint)
    elif config_selection.blocker_message:
        run_setup_hint = helper_text(config_selection.blocker_message)

    onboarding_panel = ft.Column(
        [
            compact_status_banner(
                "Lokale Pilotversion",
                onboarding.compact_status_items,
            ),
            collapsible_details(
                MSG_SAAS_NOT_INCLUDED,
                onboarding.next_step,
                *[item.label for item in onboarding.checklist],
                title="Pilot-Details anzeigen",
            ),
        ],
        spacing=2,
        tight=True,
    )

    items: list[ft.Control] = [
        page_header(
            "Arbeitsbereich",
            subtitle="Ordner wählen, Sandbox starten, Ergebnis prüfen.",
        ),
        make_context_strip(("Profil", profile_name), ("Modell", scan_model)),
        make_section_label(RUN_SETUP_SECTION_LABEL),
        run_setup_panel,
    ]
    if run_setup_hint is not None:
        items.append(run_setup_hint)
    items.extend(
        [
            make_section_label(ONBOARDING_SECTION_LABEL_COMPACT),
            onboarding_panel,
            make_section_label(FOLDER_SELECTION_SECTION_LABEL),
            folder_selection_panel,
            make_section_label(START_FEEDBACK_SECTION_LABEL),
            run_status_panel,
            make_context_strip(
                ("Ergebnisse", str(readiness.result_count)),
                ("Prüffälle", str(readiness.review_count)),
            ),
            run_panel,
        ]
    )
    items.extend(_build_run_report_panel(state, run_report))
    if run_shell.review.has_items:
        items.append(
            summary_alert(
                f"{MSG_REVIEW_SUMMARY_SECTION}: {run_shell.review.count}. "
                f"{MSG_REVIEW_DETAILS_HINT}"
            )
        )
    if run_shell.errors.has_items:
        items.append(
            summary_alert(
                f"{MSG_ERROR_SUMMARY_SECTION}: {run_shell.errors.count}."
            )
        )
    if has_real_results and contract_display:
        items.append(make_section_label(MSG_RESULTS_SECTION))
    items.extend(
        [
            tab_bar,
            ft.Column(tab_blocks, spacing=4),
        ]
    )

    for warning in workspace.warnings:
        items.append(inline_warning(warning))

    return page_scaffold(*items)
