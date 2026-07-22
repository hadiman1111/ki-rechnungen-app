"""Arbeitsbereich — Figma Make port (single run panel + Ergebnisliste).

Honest empty state: no preview/mock invoice rows, no private/local demo data.
Results appear only after a real workspace.results payload or injected contract results.
Processing starts only via the bounded UI-v2 contract (default: not connected).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import flet as ft
from invoice_tool.ui_v2.adapters.folder_picker_adapter import choose_target_folder
from invoice_tool.ui_v2.components import (
    display_path_value,
    divider,
    empty_state,
    inline_warning,
    make_context_strip,
    make_destination_list_row,
    make_ergebnis_row,
    make_full_width_panel,
    make_section_label,
    make_tab_bar,
    make_workspace_run_panel,
    page_header,
    page_scaffold,
    summary_alert,
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
from invoice_tool.ui_v2.local_processing_adapter import MSG_MISSING_OUTPUT
from invoice_tool.ui_v2.processing_state import (
    MSG_BLOCKED_ADAPTER,
    MSG_DRY_RUN_UNAVAILABLE,
    MSG_IDLE,
    MSG_NOT_CONFIGURED,
    MSG_POLICY_NOT_READY,
    ProcessingRunState,
    ProcessingStatus,
)
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.view_models import ResultSummaryVM, UiV2ReadOnlySnapshot

ErgebnisAction = Literal["neue-konfiguration", "konfiguration-bearbeiten"]

# Honest empty-state copy (generic product UI-v2 — no private/demo run data).
EMPTY_NO_RUN_TITLE = "Noch kein Verarbeitungslauf in dieser Oberfläche."
EMPTY_NO_RUN_DETAIL = (
    "Wähle später einen Eingangsordner und starte eine Verarbeitung, "
    "sobald der Lauf-Adapter angebunden ist. "
    "Ergebnisse erscheinen hier erst nach einem echten Lauf. "
    "Unklare Dokumente werden später im Prüfbereich angezeigt."
)
EMPTY_NO_RESULTS_TITLE = "Keine Ergebnisse vorhanden"
EMPTY_NO_RESULTS_DETAIL = "Keine Dokumente verarbeitet. Kein Lauf gestartet."
EMPTY_NO_RUN_STATUS = "Kein Lauf gestartet"
START_CTA_LABEL = "Verarbeitung starten"
ADAPTER_NOT_CONNECTED_HINT = MSG_BLOCKED_ADAPTER


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


def _display_results(workspace_results: tuple[ResultSummaryVM, ...]) -> tuple[_WorkspaceResultDisplay, ...]:
    """Only real run results — never invent preview/mock rows."""
    if not workspace_results:
        return tuple()
    return tuple(_result_from_vm(index, item) for index, item in enumerate(workspace_results[:16]))


def _display_mappings(results: tuple[_WorkspaceResultDisplay, ...]) -> tuple[tuple[str, str], ...]:
    """Map only successful real results; never invent filename-based preview mappings."""
    return tuple((item.source_filename, item.target_filename) for item in results if not item.failed)


def _has_real_run_results(workspace_results: tuple[ResultSummaryVM, ...]) -> bool:
    return bool(workspace_results)


def resolve_workspace_policy_bridge(state: UiV2State) -> RuntimePolicyBridgeResult:
    """Map active SaaS draft policy (or safe blank defaults) into runtime intent."""

    draft = state.saas_draft_store.profile_draft
    if draft is not None and getattr(draft, "classification_policy", None) is not None:
        return build_runtime_policy_intent(draft)
    # Honest safe defaults — no private tenant policy, still structured intent.
    return build_runtime_policy_intent(default_classification_policy())


def build_processing_run_request(
    state: UiV2State,
    *,
    profile_id: str | None = None,
    configuration_id: str | None = None,
    user_confirmed_start: bool = False,
) -> ProcessingRunRequest:
    """Build a contract request from explicit UI-v2 selection only (no private defaults)."""

    folder = (state.workspace_input_folder_override or "").strip() or None
    output_folder = (state.workspace_output_folder_override or "").strip() or None
    source = SOURCE_EXPLICIT_USER_SELECTION if folder else SOURCE_UNSET
    policy_bridge = resolve_workspace_policy_bridge(state)
    # Output folder only from explicit override — never Desktop/private defaults.
    # Profile/config only from explicit caller args or explicit UI selection fields —
    # never invent private tenant defaults (do not fall back to state.selected_profile_id="local").
    resolved_configuration = (
        (configuration_id or "").strip()
        or (state.config_list_selected_id or "").strip()
        or None
    )
    resolved_profile = (profile_id or "").strip() or None
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
    )


def apply_start_processing(state: UiV2State, *, profile_id: str | None = None) -> ProcessingRunState:
    """Invoke the bounded processing service — never imports processing-core.

    Default service remains NotYetConnectedProcessingService. LocalProcessingAdapter
    is used only when explicitly injected into state.processing_service.
    CTA sets user_confirmed_start=True; still no auto-run and no PDF mutation.
    """

    request = build_processing_run_request(
        state,
        profile_id=profile_id,
        user_confirmed_start=True,
    )
    result = state.processing_service.start_run(request)
    state.processing_run_state = result
    return result


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
        )

    if status == "blocked":
        status_line = f"{ADAPTER_NOT_CONNECTED_HINT} {EMPTY_NO_RUN_STATUS}."
        if policy_hint and MSG_POLICY_NOT_READY in (proc.message or ""):
            status_line = f"{policy_hint} {EMPTY_NO_RUN_STATUS}."
        elif policy_hint and "blockieren" in (proc.message or "").lower():
            status_line = f"{policy_hint} {EMPTY_NO_RUN_STATUS}."
        detail = (
            f"{ADAPTER_NOT_CONNECTED_HINT} "
            "Ergebnisse erscheinen hier erst nach einem echten Lauf über einen angebundenen Adapter. "
            "Unklare Dokumente werden später im Prüfbereich angezeigt."
        )
        if policy_hint:
            detail = f"{policy_hint} {detail}"
    elif status == "not_configured":
        status_line = f"{MSG_NOT_CONFIGURED} {EMPTY_NO_RUN_STATUS}."
        if MSG_MISSING_OUTPUT in (proc.message or ""):
            status_line = f"{MSG_MISSING_OUTPUT} {EMPTY_NO_RUN_STATUS}."
        elif policy_hint and (
            MSG_POLICY_INCOMPLETE in (proc.message or "")
            or MSG_POLICY_NOT_READY in (proc.message or "")
        ):
            status_line = f"{policy_hint} {EMPTY_NO_RUN_STATUS}."
        detail = (
            f"{MSG_NOT_CONFIGURED} "
            f"{EMPTY_NO_RUN_DETAIL}"
        )
        if MSG_MISSING_OUTPUT in (proc.message or ""):
            detail = f"{MSG_MISSING_OUTPUT} {EMPTY_NO_RUN_DETAIL}"
        elif policy_hint:
            detail = f"{policy_hint} {detail}"
    else:
        status_line = f"{EMPTY_NO_RUN_STATUS}. {EMPTY_NO_RESULTS_TITLE}."
        if proc.message and proc.message not in {MSG_IDLE, ""}:
            status_line = f"{proc.message} {EMPTY_NO_RESULTS_TITLE}."
        detail = EMPTY_NO_RUN_DETAIL
        if policy_hint:
            detail = f"{policy_hint} {detail}"

    # Surface dry/no-mutation gate honestly when adapter reports it.
    if status == "blocked" and MSG_DRY_RUN_UNAVAILABLE in (proc.message or ""):
        status_line = f"{MSG_DRY_RUN_UNAVAILABLE} {EMPTY_NO_RUN_STATUS}."
        detail = (
            f"{MSG_DRY_RUN_UNAVAILABLE} "
            "Ergebnisse erscheinen hier erst nach einem echten Lauf über einen "
            "angebundenen Adapter. Unklare Dokumente werden später im Prüfbereich angezeigt."
        )

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
    )


def _schedule_folder_picker(state: UiV2State, refresh: Callable[[], None]) -> Callable[[ft.ControlEvent], None]:
    async def _pick_folder(_event: ft.ControlEvent) -> None:
        path = await choose_target_folder(dialog_title="Eingangsordner auswählen")
        if path:
            state.workspace_input_folder_override = path
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

    folder_override = state.workspace_input_folder_override
    display_results = _display_results(workspace.results)
    has_real_results = _has_real_run_results(workspace.results)
    policy_bridge = resolve_workspace_policy_bridge(state)
    honesty = workspace_honesty_copy(
        has_real_results=has_real_results,
        processing_state=state.processing_run_state,
        policy_bridge=policy_bridge,
    )
    input_configured = bool(folder_override) or (
        workspace.input_folder_state == "configured" and bool(workspace.input_folder_summary.strip())
    )
    if folder_override:
        input_path = display_path_value(folder_override)
    elif input_configured:
        input_path = display_path_value(workspace.input_folder_summary)
    else:
        input_path = None

    pick_folder = _schedule_folder_picker(state, _refresh)
    start_processing = _schedule_start_processing(
        state,
        _refresh,
        profile_id=snapshot.profile.profile_id,
    )
    mappings = _display_mappings(display_results) if has_real_results else tuple()
    fail_count = sum(1 for result in display_results if result.failed) if has_real_results else 0
    ok_count = (len(display_results) - fail_count) if has_real_results else None
    fail_count_display = fail_count if has_real_results else None

    run_panel = make_workspace_run_panel(
        folder_path=input_path,
        on_change_folder=pick_folder if input_path else None,
        on_pick_folder=pick_folder if not input_path else None,
        on_start=start_processing,
        start_label=honesty.start_cta_label,
        start_disabled=honesty.start_cta_disabled,
        on_restart=(lambda _e: _refresh()) if (input_path and has_real_results) else None,
        on_details=(lambda _e: _set_tab("ergebnisse")) if has_real_results else None,
        ok_count=ok_count if input_path else None,
        fail_count=fail_count_display if input_path else None,
        mappings=mappings if input_path else tuple(),
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
                        honesty.results_title or EMPTY_NO_RUN_TITLE,
                        detail=honesty.results_detail or EMPTY_NO_RUN_DETAIL,
                        icon=ft.Icons.INBOX_OUTLINED,
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

    items: list[ft.Control] = [
        page_header(
            "Arbeitsbereich",
            subtitle="Dokumente auswählen, verarbeiten und Ergebnisse prüfen.",
        ),
        make_context_strip(("Profil", profile_name), ("Erkennungsmodell", scan_model)),
        make_section_label("Workflow"),
    ]
    if honesty.status_line:
        items.append(inline_warning(honesty.status_line))
    if (
        not has_real_results
        and honesty.policy_intent_hint
        and honesty.policy_intent_hint not in (honesty.status_line or "")
        and honesty.policy_intent_status in {"incomplete", "blocked"}
    ):
        items.append(inline_warning(honesty.policy_intent_hint))
    if (
        not has_real_results
        and state.processing_run_state.status in {"blocked", "not_configured"}
        and state.processing_run_state.message
    ):
        # Surface contract feedback after CTA without inventing result rows.
        if state.processing_run_state.message not in (honesty.status_line or ""):
            items.append(inline_warning(state.processing_run_state.message))
    items.extend(
        [
            run_panel,
            tab_bar,
            ft.Column(tab_blocks, spacing=10),
        ]
    )

    for warning in workspace.warnings:
        items.append(inline_warning(warning))

    return page_scaffold(*items)
