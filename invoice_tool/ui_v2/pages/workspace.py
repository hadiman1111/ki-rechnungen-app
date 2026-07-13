"""Arbeitsbereich — Figma Make port (single run panel + Ergebnisliste)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import flet as ft
from invoice_tool.ui_v2.adapters.folder_picker_adapter import choose_target_folder
from invoice_tool.ui_v2.adapters.read_only_backend import list_input_pdf_filenames
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
from invoice_tool.ui_v2.state import UiV2State
from invoice_tool.ui_v2.view_models import ResultSummaryVM, UiV2ReadOnlySnapshot

ErgebnisAction = Literal["neue-konfiguration", "konfiguration-bearbeiten"]


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


_PREVIEW_INPUT_PATH = "~/Desktop/Programm Belegerfassung/KI-Rechnungen-App/eingang"

_PREVIEW_MAPPINGS: tuple[tuple[str, str], ...] = (
    ("rechnung_2024-03_american-express_125,00.pdf", "2024-03-15_rechnung_amex_125,00.pdf"),
    ("event_production_invoice_04_2024.pdf", "2024-01-20_er_Event-Production_125,00.pdf"),
    ("privat_strom_februar_2024.pdf", "2024-01-20_er_Privat_42,50.pdf"),
    ("kreditkarte_visa_maerz_2024.pdf", "2024-04-15_rechnung_shell_89,90.pdf"),
    ("rechnung_baumarkt_xyz.pdf", "2024-02-20_er_Privat_88,90.pdf"),
    ("rechnung_2024-03_amex_125,00.pdf", "2024-03-15_rechnung_amex_125,00.pdf"),
    ("honorar_architektur_q1.pdf", "2024-03-01_er_Architektur_450,00.pdf"),
    ("event_backline_miete.pdf", "2024-02-15_er_Event-Production_220,00.pdf"),
    ("strom_privat_januar.pdf", "2024-01-10_er_Privat_62,30.pdf"),
    ("amex_januar_2024.pdf", "2024-01-05_er_American-Express_310,00.pdf"),
    ("event_sound_q4.pdf", "2023-12-20_er_Event-Production_980,00.pdf"),
    ("privat_internet_2024.pdf", "2024-02-01_er_Privat_39,99.pdf"),
)

_PREVIEW_RESULTS: tuple[_WorkspaceResultDisplay, ...] = (
    _WorkspaceResultDisplay(
        "preview-1",
        "rechnung_2024-03_amex_125,00.pdf",
        "2024-03-15_rechnung_amex_125,00.pdf",
        "American Express",
        "~/Dokumente/Belege/American-Express",
        False,
    ),
    _WorkspaceResultDisplay(
        "preview-2",
        "event_production_invoice_04_2024.pdf",
        "2024-02-01_er_Event-Production_890,00.pdf",
        "Event Production",
        "~/Dokumente/Belege/Event",
        False,
    ),
    _WorkspaceResultDisplay(
        "preview-3",
        "privat_strom_februar_2024.pdf",
        "2024-01-20_er_Privat_42,50.pdf",
        "Privat",
        "~/Dokumente/Belege/Privat",
        False,
    ),
    _WorkspaceResultDisplay(
        "preview-4",
        "unbekannt_lieferant_xyz_2024.pdf",
        "unbekannt_lieferant_xyz_2024.pdf",
        "—",
        "—",
        True,
        reason="Keine passende Konfiguration gefunden.",
        suggestion="Kein Erkennungsmuster passt zu diesem Dokument. Legen Sie eine neue Konfiguration mit einer passenden Erkennungsregel an.",
        action="neue-konfiguration",
    ),
    _WorkspaceResultDisplay(
        "preview-5",
        "architektur_honorar_2024-03.pdf",
        "architektur_honorar_2024-03.pdf",
        "Architektur & Innenarchitektur",
        "~/Dokumente/Belege/Architektur",
        True,
        reason="Zielordner nicht erreichbar.",
        suggestion='Der Zielordner der Konfiguration „Architektur & Innenarchitektur" existiert nicht oder ist nicht zugänglich. Bitte Pfad korrigieren.',
        action="konfiguration-bearbeiten",
    ),
    _WorkspaceResultDisplay(
        "preview-6",
        "doppelte_zuordnung_test.pdf",
        "doppelte_zuordnung_test.pdf",
        "—",
        "—",
        True,
        reason="Mehrere Konfigurationen zutreffend.",
        suggestion="Mehr als eine aktive Konfiguration passt zu diesem Dokument. Prüfen Sie die Erkennungsregeln und grenzen Sie die Werte ein.",
        action="konfiguration-bearbeiten",
    ),
    _WorkspaceResultDisplay(
        "preview-7",
        "scan_unlesbar_001.pdf",
        "scan_unlesbar_001.pdf",
        "—",
        "—",
        True,
        reason="Keine passende Konfiguration gefunden.",
        suggestion="Kein Erkennungsmuster passt zu diesem Dokument. Legen Sie eine neue Konfiguration mit einer passenden Erkennungsregel an.",
        action="neue-konfiguration",
    ),
)


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
    if workspace_results:
        return tuple(_result_from_vm(index, item) for index, item in enumerate(workspace_results[:16]))
    return _PREVIEW_RESULTS


def _display_mappings(
    results: tuple[_WorkspaceResultDisplay, ...],
    pdf_files: tuple[str, ...],
    *,
    use_preview: bool,
) -> tuple[tuple[str, str], ...]:
    if not use_preview:
        return tuple((item.source_filename, item.target_filename) for item in results if not item.failed)
    if pdf_files:
        mapped = {source: target for source, target in _PREVIEW_MAPPINGS}
        return tuple((name, mapped.get(name, name)) for name in pdf_files)
    return _PREVIEW_MAPPINGS


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
    run = workspace.latest_run
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
    pdf_files = list_input_pdf_filenames(limit=12, folder_override=folder_override)
    display_results = _display_results(workspace.results)
    use_preview = not workspace.results
    input_configured = bool(folder_override) or (
        workspace.input_folder_state == "configured" and bool(workspace.input_folder_summary.strip())
    )
    if folder_override:
        input_path = display_path_value(folder_override)
    elif input_configured:
        input_path = display_path_value(workspace.input_folder_summary)
    elif use_preview:
        input_path = _PREVIEW_INPUT_PATH
    else:
        input_path = None

    pick_folder = _schedule_folder_picker(state, _refresh)
    mappings = _display_mappings(display_results, pdf_files, use_preview=use_preview)
    fail_count = sum(1 for result in display_results if result.failed)
    ok_count = len(display_results) - fail_count if not use_preview else 12

    if use_preview and input_path:
        ok_count = 12
        fail_count = 4

    run_panel = make_workspace_run_panel(
        folder_path=input_path,
        on_change_folder=pick_folder if input_path else None,
        on_pick_folder=pick_folder if not input_path else None,
        on_restart=lambda _e: _refresh(),
        on_details=lambda _e: _set_tab("ergebnisse"),
        ok_count=ok_count if input_path else None,
        fail_count=fail_count if input_path else None,
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
        run_panel,
        tab_bar,
        ft.Column(tab_blocks, spacing=10),
    ]

    for warning in workspace.warnings:
        items.append(inline_warning(warning))

    return page_scaffold(*items)
