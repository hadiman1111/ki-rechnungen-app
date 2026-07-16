"""Flet UI for the internal SOMAA launcher."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import flet as ft

from invoice_tool.internal_launcher.path_validation import (
    default_internal_deny_paths,
    run_paths_ready,
    validate_output_path,
    validate_run_paths,
    validate_source_path,
)
from invoice_tool.internal_launcher.profile_display import load_active_profile_display
from invoice_tool.internal_launcher.result_reader import RunResultSummary, _list_run_dirs, read_run_result
from invoice_tool.internal_launcher.run_controller import RunController, RunOutcome

_WINDOW_TITLE = "KI-Rechnungen — Interner Verarbeitungsstart"
_WINDOW_WIDTH = 720
_WINDOW_HEIGHT = 620
_SAFETY_NOTICE = (
    "Die verarbeiteten Dateien werden nach erfolgreichem Lauf entsprechend dem "
    "Programmlauf archiviert. Verwende für die erste produktive Nutzung ausschließlich "
    "Kopien oder einen kontrollierten Eingangsordner."
)
_RUNNING_NOTICE = (
    "Die Verarbeitung läuft. Ein sicherer Abbruch wird derzeit nicht unterstützt."
)


def open_path_in_finder(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False, shell=False)
        return True
    return False


def build_internal_launcher(page: ft.Page) -> None:
    profile_info = load_active_profile_display()
    deny_paths = default_internal_deny_paths()

    page.title = _WINDOW_TITLE
    page.window.width = _WINDOW_WIDTH
    page.window.height = _WINDOW_HEIGHT
    page.window.min_width = 640
    page.window.min_height = 560
    page.padding = 20
    page.spacing = 12

    source_path_value: Path | None = None
    output_path_value: Path | None = None
    last_result: RunResultSummary | None = None
    last_log_path: Path | None = None
    before_run_dirs: set[Path] = set()

    profile_name_text = ft.Text(
        f"Profil: {profile_info.profile_name}" if profile_info.ok else "Profil: —",
        size=14,
        weight=ft.FontWeight.W_600,
    )
    scan_model_text = ft.Text(
        f"Scan-Modell: {profile_info.scan_model_label}" if profile_info.ok else "Scan-Modell: —",
        size=13,
    )
    profile_path_text = ft.Text(
        f"Profilpfad: {profile_info.profile_path}" if profile_info.profile_path else "",
        size=11,
        color=ft.Colors.ON_SURFACE_VARIANT,
        selectable=True,
    )
    profile_error_text = ft.Text(
        profile_info.error_message or "",
        size=12,
        color=ft.Colors.ERROR,
        visible=not profile_info.ok,
    )

    source_field = ft.TextField(
        label="Eingangsordner",
        read_only=True,
        expand=True,
        hint_text="Noch kein Ordner gewählt",
    )
    source_pdf_count = ft.Text("PDFs: —", size=12)
    source_validation = ft.Text("", size=12, color=ft.Colors.ERROR)

    output_field = ft.TextField(
        label="Ausgabeordner",
        read_only=True,
        expand=True,
        hint_text="Noch kein Ordner gewählt",
    )
    output_validation = ft.Text("", size=12, color=ft.Colors.ERROR)

    status_text = ft.Text("Bereit", size=14, weight=ft.FontWeight.W_600)
    running_ring = ft.ProgressRing(visible=False, width=22, height=22)
    running_summary = ft.Text("", size=12, visible=False)

    processed_text = ft.Text("Verarbeitet: —", size=13)
    error_text = ft.Text("Fehler: —", size=13)
    review_text = ft.Text("Prüfung/Unklar: —", size=13)
    review_notice = ft.Text("", size=12, color=ft.Colors.TERTIARY, visible=False)
    technical_details = ft.Text("", size=11, color=ft.Colors.ON_SURFACE_VARIANT, visible=False)

    start_button = ft.FilledButton("Verarbeitung starten", icon=ft.Icons.PLAY_ARROW)
    pick_source_button = ft.OutlinedButton("Ordner auswählen", icon=ft.Icons.FOLDER_OPEN)
    pick_output_button = ft.OutlinedButton("Ordner auswählen", icon=ft.Icons.FOLDER_OPEN)
    open_output_button = ft.OutlinedButton("Ausgabeordner öffnen", icon=ft.Icons.OPEN_IN_NEW, visible=False)
    open_report_button = ft.OutlinedButton("Bericht öffnen", icon=ft.Icons.DESCRIPTION, visible=False)
    open_unklar_button = ft.OutlinedButton("Unklar-Ordner öffnen", icon=ft.Icons.RULE_FOLDER, visible=False)
    open_log_button = ft.OutlinedButton("Log öffnen", icon=ft.Icons.ARTICLE, visible=False)
    new_run_button = ft.TextButton("Neuer Lauf", icon=ft.Icons.RESTART_ALT, visible=False)

    controller: RunController | None = None
    if profile_info.ok and profile_info.profile_path is not None:
        controller = RunController(profile_path=profile_info.profile_path)

    directory_picker = ft.FilePicker()

    def _set_controls_enabled(enabled: bool) -> None:
        pick_source_button.disabled = not enabled
        pick_output_button.disabled = not enabled
        start_button.disabled = not enabled

    def _refresh_start_enabled() -> None:
        if controller is None or controller.is_running():
            start_button.disabled = True
            return
        source_result, output_result = validate_run_paths(
            source_path_value,
            output_path_value,
            deny_paths=deny_paths,
        )
        start_button.disabled = not run_paths_ready(source_result, output_result)

    def _apply_source_validation() -> None:
        nonlocal source_path_value
        result = validate_source_path(source_path_value, deny_paths=deny_paths)
        if result.resolved_path is not None:
            source_field.value = str(result.resolved_path)
            source_path_value = result.resolved_path
        source_pdf_count.value = f"PDFs: {result.pdf_count}" if result.ok else "PDFs: 0"
        source_validation.value = result.messages[0] if result.messages else ""
        source_validation.color = ft.Colors.ERROR if result.messages else ft.Colors.ON_SURFACE_VARIANT

    def _apply_output_validation() -> None:
        nonlocal output_path_value
        source_resolved = None
        if source_path_value is not None:
            source_check = validate_source_path(source_path_value, deny_paths=deny_paths)
            source_resolved = source_check.resolved_path if source_check.ok else None
        result = validate_output_path(
            output_path_value,
            source=source_resolved,
            deny_paths=deny_paths,
        )
        if result.resolved_path is not None:
            output_field.value = str(result.resolved_path)
            output_path_value = result.resolved_path
        output_validation.value = result.messages[0] if result.messages else ""
        output_validation.color = ft.Colors.ERROR if result.messages else ft.Colors.ON_SURFACE_VARIANT

    def _reset_result_panel() -> None:
        nonlocal last_result, last_log_path
        last_result = None
        last_log_path = None
        processed_text.value = "Verarbeitet: —"
        error_text.value = "Fehler: —"
        review_text.value = "Prüfung/Unklar: —"
        review_notice.visible = False
        technical_details.visible = False
        open_output_button.visible = False
        open_report_button.visible = False
        open_unklar_button.visible = False
        open_log_button.visible = False
        new_run_button.visible = False

    def _show_running() -> None:
        status_text.value = "Verarbeitung läuft …"
        running_ring.visible = True
        running_summary.visible = True
        running_summary.value = (
            f"Quelle: {source_path_value}\nZiel: {output_path_value}\n{_RUNNING_NOTICE}"
        )
        _set_controls_enabled(False)
        page.window.prevent_close = True

    def _show_outcome(outcome: RunOutcome) -> None:
        nonlocal last_result, last_log_path, before_run_dirs
        last_log_path = outcome.log_path
        result = read_run_result(
            outcome,
            output_root=output_path_value,
            before_run_dirs=before_run_dirs,
        )
        last_result = result
        before_run_dirs = set()

        status_text.value = result.status_label
        running_ring.visible = False
        running_summary.visible = False
        processed_text.value = f"Verarbeitet: {result.processed_count}"
        error_text.value = f"Fehler: {result.error_count}"
        review_text.value = f"Prüfung/Unklar: {result.review_count}"
        review_notice.visible = result.review_count > 0
        review_notice.value = "Einige Dateien müssen geprüft werden." if result.review_count > 0 else ""

        details: list[str] = []
        if outcome.exit_code != 0:
            details.append(f"Exit-Code: {outcome.exit_code}")
        if result.stderr_summary:
            details.append(result.stderr_summary)
        if result.warnings:
            details.extend(result.warnings)
        if last_log_path:
            details.append(f"Log: {last_log_path}")
        technical_details.value = "\n".join(details)
        technical_details.visible = bool(details)

        open_output_button.visible = output_path_value is not None and output_path_value.exists()
        open_report_button.visible = result.report_txt_path is not None or result.report_json_path is not None
        open_unklar_button.visible = result.unklar_folder_path is not None
        open_log_button.visible = last_log_path is not None
        new_run_button.visible = True
        _set_controls_enabled(True)
        _refresh_start_enabled()
        page.window.prevent_close = False
        page.update()

    async def pick_source(_event: ft.ControlEvent) -> None:
        nonlocal source_path_value
        if controller and controller.is_running():
            return
        initial = str(source_path_value) if source_path_value else None
        picked = await directory_picker.get_directory_path(
            dialog_title="Eingangsordner auswählen",
            initial_directory=initial,
        )
        if picked and str(picked).strip():
            source_path_value = Path(str(picked).strip())
            _apply_source_validation()
            _apply_output_validation()
            _refresh_start_enabled()
            page.update()

    async def pick_output(_event: ft.ControlEvent) -> None:
        nonlocal output_path_value
        if controller and controller.is_running():
            return
        initial = str(output_path_value) if output_path_value else None
        picked = await directory_picker.get_directory_path(
            dialog_title="Ausgabeordner auswählen",
            initial_directory=initial,
        )
        if picked and str(picked).strip():
            output_path_value = Path(str(picked).strip())
            _apply_output_validation()
            _refresh_start_enabled()
            page.update()

    def start_processing(_event: ft.ControlEvent) -> None:
        if controller is None or controller.is_running():
            return
        source_result, output_result = validate_run_paths(
            source_path_value,
            output_path_value,
            deny_paths=deny_paths,
        )
        if not run_paths_ready(source_result, output_result):
            _apply_source_validation()
            _apply_output_validation()
            _refresh_start_enabled()
            page.update()
            return
        assert source_result.resolved_path is not None
        assert output_result.resolved_path is not None
        nonlocal before_run_dirs
        before_run_dirs = _list_run_dirs()
        _reset_result_panel()
        _show_running()
        page.update()

        def _on_complete(outcome: RunOutcome) -> None:
            async def _finish_async() -> None:
                _show_outcome(outcome)

            page.run_task(_finish_async)

        started = controller.start_async(
            source_result.resolved_path,
            output_result.resolved_path,
            on_complete=_on_complete,
        )
        if not started:
            status_text.value = "Verarbeitung läuft bereits."
            page.update()

    def open_output(_event: ft.ControlEvent) -> None:
        open_path_in_finder(output_path_value)

    def open_report(_event: ft.ControlEvent) -> None:
        if last_result is None:
            return
        target = last_result.report_txt_path or last_result.report_json_path
        open_path_in_finder(target)

    def open_unklar(_event: ft.ControlEvent) -> None:
        if last_result is None:
            return
        target = last_result.unklar_folder_path or output_path_value
        open_path_in_finder(target)

    def open_log(_event: ft.ControlEvent) -> None:
        open_path_in_finder(last_log_path)

    def begin_new_run(_event: ft.ControlEvent) -> None:
        if controller and controller.is_running():
            return
        _reset_result_panel()
        status_text.value = "Bereit"
        _refresh_start_enabled()
        page.update()

    def on_window_event(event: ft.WindowEvent) -> None:
        if event.type == ft.WindowEventType.CLOSE and controller and controller.is_running():
            page.window.prevent_close = True
            status_text.value = "Schließen während der Verarbeitung: Der Lauf wird fortgesetzt."
            running_summary.visible = True
            running_summary.value = _RUNNING_NOTICE
            page.update()

    page.window.on_event = on_window_event

    pick_source_button.on_click = lambda _event: page.run_task(pick_source, _event)
    pick_output_button.on_click = lambda _event: page.run_task(pick_output, _event)
    start_button.on_click = start_processing
    open_output_button.on_click = open_output
    open_report_button.on_click = open_report
    open_unklar_button.on_click = open_unklar
    open_log_button.on_click = open_log
    new_run_button.on_click = begin_new_run

    start_button.disabled = True
    if not profile_info.ok:
        pick_source_button.disabled = True
        pick_output_button.disabled = True

    page.add(
        ft.Text("KI-Rechnungen — Interner Verarbeitungsstart", size=20, weight=ft.FontWeight.W_700),
        ft.Text(
            "Wähle Eingangs- und Ausgabeordner und starte die Verarbeitung über den geprüften Backend-Kern.",
            size=13,
        ),
        profile_name_text,
        scan_model_text,
        profile_path_text,
        profile_error_text,
        ft.Divider(),
        ft.Text("Eingangsordner", size=15, weight=ft.FontWeight.W_600),
        ft.Row([source_field, pick_source_button]),
        source_pdf_count,
        source_validation,
        ft.Text("Ausgabeordner", size=15, weight=ft.FontWeight.W_600),
        ft.Row([output_field, pick_output_button]),
        output_validation,
        ft.Text(_SAFETY_NOTICE, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        ft.Row([start_button, running_ring], alignment=ft.MainAxisAlignment.START),
        running_summary,
        status_text,
        processed_text,
        error_text,
        review_text,
        review_notice,
        technical_details,
        ft.Row(
            [
                open_output_button,
                open_report_button,
                open_unklar_button,
                open_log_button,
                new_run_button,
            ],
            wrap=True,
            spacing=8,
        ),
    )


def main(page: ft.Page) -> None:
    build_internal_launcher(page)
