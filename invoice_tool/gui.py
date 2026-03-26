from __future__ import annotations

import json
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable

import flet as ft

from invoice_tool.config import ConfigError, load_app_config, load_office_rules
from invoice_tool.extraction import ExtractionCoordinator, OpenAIVisionExtractor, TesseractExtractor
from invoice_tool.logging_utils import RunLogger
from invoice_tool.processing import InvoiceProcessor


def _open_path(path: Path) -> None:
    system = platform.system().lower()
    if system == "darwin":
        subprocess.Popen(["open", str(path)])
    elif system == "windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _extract_pruefbedarf_block(report_text: str) -> str | None:
    lines = report_text.splitlines()
    if "PRÜFBEDARF: keiner" in lines:
        return "PRÜFBEDARF: keiner"
    if "PRÜFBEDARF:" not in lines:
        return None
    start_index = lines.index("PRÜFBEDARF:")
    collected: list[str] = []
    for line in lines[start_index:]:
        if line == "SUMMARY:":
            break
        collected.append(line)
    return "\n".join(collected).strip() or None


class UiRunLogger(RunLogger):
    def __init__(self, logs_dir: Path, on_log_line: Callable[[str], None]) -> None:
        super().__init__(logs_dir)
        self.on_log_line = on_log_line

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self.on_log_line(line)


def _ui(page: ft.Page) -> None:
    page.title = "KI-Rechnungen-App"
    page.window_width = 1180
    page.window_height = 860
    page.padding = 16
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO

    config_path = Path("invoice_config.json").resolve()
    app_config = None
    office_rules = None
    last_report_txt: Path | None = None
    last_report_json: Path | None = None
    run_in_progress = False

    preset_value = ft.Text("-", selectable=True)
    input_value = ft.Text("-", selectable=True)
    output_value = ft.Text("-", selectable=True)
    status_value = ft.Text("bereit", color=ft.Colors.BLUE_700, size=16, weight=ft.FontWeight.W_600)
    summary_processed = ft.Text("Processed: -")
    summary_documents = ft.Text("Documents: -")
    summary_duplicates = ft.Text("Duplicates: -")
    summary_unklar = ft.Text("Unklar: -")
    summary_errors = ft.Text("Errors: -")
    summary_fallbacks = ft.Text("System Fallbacks: -")
    log_output = ft.TextField(
        value="",
        multiline=True,
        min_lines=12,
        max_lines=12,
        read_only=True,
        expand=True,
    )
    pruefbedarf_title = ft.Text("PRÜFBEDARF", weight=ft.FontWeight.W_700, color=ft.Colors.RED_700)
    pruefbedarf_text = ft.Text("-", selectable=True)
    pruefbedarf_box = ft.Container(
        visible=False,
        bgcolor=ft.Colors.RED_50,
        border=ft.border.all(1, ft.Colors.RED_200),
        border_radius=8,
        padding=12,
        content=ft.Column([pruefbedarf_title, pruefbedarf_text], spacing=6),
    )
    report_text = ft.TextField(
        value="",
        multiline=True,
        min_lines=16,
        read_only=True,
        expand=True,
    )
    latest_report_hint = ft.Text("Kein Report geladen.")

    start_button = ft.ElevatedButton(
        "Lauf starten",
        icon=ft.Icons.PLAY_ARROW,
        style=ft.ButtonStyle(
            text_style=ft.TextStyle(size=18, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=20, vertical=18),
        ),
    )

    def append_log_line(line: str) -> None:
        log_output.value = (log_output.value + "\n" + line).strip()
        page.update()

    def set_status(text: str, color: str) -> None:
        status_value.value = text
        status_value.color = color

    def reset_report_view() -> None:
        summary_processed.value = "Processed: -"
        summary_documents.value = "Documents: -"
        summary_duplicates.value = "Duplicates: -"
        summary_unklar.value = "Unklar: -"
        summary_errors.value = "Errors: -"
        summary_fallbacks.value = "System Fallbacks: -"
        pruefbedarf_box.visible = False
        pruefbedarf_text.value = "-"
        report_text.value = ""
        latest_report_hint.value = "Kein Report geladen."

    def load_runtime_context() -> None:
        nonlocal app_config, office_rules
        try:
            app_config = load_app_config(config_path)
            office_rules = load_office_rules(
                app_config.regeln_datei,
                active_preset_override=app_config.aktives_preset,
            )
            preset_value.value = office_rules.active_preset
            input_value.value = str(app_config.eingangsordner)
            output_value.value = str(app_config.ausgangsordner)
        except (ConfigError, RuntimeError) as exc:
            app_config = None
            office_rules = None
            preset_value.value = "Konfigurationsfehler"
            input_value.value = "-"
            output_value.value = "-"
            log_output.value = f"Konfiguration konnte nicht geladen werden: {exc}"
            set_status("Fehler", ft.Colors.RED_700)

    def load_report_views(report_txt: Path, report_json: Path | None) -> None:
        nonlocal last_report_txt, last_report_json
        last_report_txt = report_txt
        last_report_json = report_json
        if report_txt.exists():
            text = report_txt.read_text(encoding="utf-8")
            report_text.value = text
            latest_report_hint.value = str(report_txt)
            pruefbedarf = _extract_pruefbedarf_block(text)
            if pruefbedarf:
                pruefbedarf_text.value = pruefbedarf
                pruefbedarf_box.visible = True
            else:
                pruefbedarf_box.visible = False
        if report_json and report_json.exists():
            data = json.loads(report_json.read_text(encoding="utf-8"))
            summary = data.get("summary", {})
            summary_processed.value = f"Processed: {summary.get('processed', '-')}"
            summary_documents.value = f"Documents: {summary.get('documents', '-')}"
            summary_duplicates.value = f"Duplicates: {summary.get('duplicates', '-')}"
            summary_unklar.value = f"Unklar: {summary.get('unklar', '-')}"
            summary_errors.value = f"Errors: {summary.get('errors', '-')}"
            summary_fallbacks.value = (
                f"System Fallbacks: {summary.get('system_fallbacks', '-')}"
            )

    def find_latest_report() -> Path | None:
        if app_config is None:
            return None
        runs_dir = app_config.ausgangsordner / "_runs"
        if not runs_dir.exists():
            return None
        reports = sorted(runs_dir.glob("*/report.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        return reports[0] if reports else None

    def run_processing() -> None:
        nonlocal run_in_progress
        try:
            config = load_app_config(config_path)
            rules = load_office_rules(
                config.regeln_datei,
                active_preset_override=config.aktives_preset,
            )
            logger = UiRunLogger(config.log_ordner, append_log_line)
            try:
                fallback = TesseractExtractor()
            except Exception as exc:  # noqa: BLE001
                append_log_line(f"Tesseract-Fallback ist nicht verfuegbar: {exc}")
                fallback = None
            extractor = ExtractionCoordinator(
                primary=OpenAIVisionExtractor(config.api_key_pfad, config.openai_model),
                fallback=fallback,
            )
            processor = InvoiceProcessor(config, extractor, office_rules=rules, logger=logger)
            processor.process_all()

            report_dir = config.ausgangsordner / "_runs" / logger.run_id
            report_txt = report_dir / "report.txt"
            report_json = report_dir / "report.json"

            run_in_progress = False
            set_status("fertig", ft.Colors.GREEN_700)
            start_button.disabled = False
            load_runtime_context()
            load_report_views(report_txt, report_json if report_json.exists() else None)
            page.update()
        except Exception as exc:  # noqa: BLE001
            run_in_progress = False
            set_status("Fehler", ft.Colors.RED_700)
            start_button.disabled = False
            log_output.value = (log_output.value + "\n" + f"Fehler: {exc}").strip()
            page.update()

    def on_start_run(_event: ft.ControlEvent) -> None:
        nonlocal run_in_progress
        if run_in_progress:
            return
        if app_config is None:
            set_status("Fehler", ft.Colors.RED_700)
            page.update()
            return
        run_in_progress = True
        log_output.value = ""
        reset_report_view()
        set_status("läuft", ft.Colors.ORANGE_700)
        start_button.disabled = True
        page.update()
        page.run_thread(run_processing)

    def on_open_input(_event: ft.ControlEvent) -> None:
        if app_config is not None:
            _open_path(app_config.eingangsordner)

    def on_open_output(_event: ft.ControlEvent) -> None:
        if app_config is not None:
            _open_path(app_config.ausgangsordner)

    def on_open_latest_report(_event: ft.ControlEvent) -> None:
        target = last_report_txt if last_report_txt and last_report_txt.exists() else find_latest_report()
        if target is not None and target.exists():
            _open_path(target)

    start_button.on_click = on_start_run

    controls = ft.Column(
        [
            ft.Text("KI-Rechnungen-App", size=30, weight=ft.FontWeight.BOLD),
            ft.Container(
                bgcolor=ft.Colors.BLUE_GREY_50,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    [
                        ft.Row([ft.Text("Aktives Preset:", weight=ft.FontWeight.W_600), preset_value]),
                        ft.Row([ft.Text("Input-Ordner:", weight=ft.FontWeight.W_600), input_value]),
                        ft.Row([ft.Text("Output-Ordner:", weight=ft.FontWeight.W_600), output_value]),
                    ],
                    spacing=6,
                ),
            ),
            ft.Row(
                [
                    ft.OutlinedButton("Input-Ordner öffnen", icon=ft.Icons.FOLDER_OPEN, on_click=on_open_input),
                    start_button,
                    ft.OutlinedButton("Output-Ordner öffnen", icon=ft.Icons.FOLDER_OPEN, on_click=on_open_output),
                    ft.OutlinedButton(
                        "Letzten Report öffnen",
                        icon=ft.Icons.DESCRIPTION,
                        on_click=on_open_latest_report,
                    ),
                ],
                wrap=True,
                spacing=10,
            ),
            ft.Row([ft.Text("Status:", weight=ft.FontWeight.W_600), status_value]),
            ft.Text("Lauflog", size=18, weight=ft.FontWeight.W_600),
            log_output,
            ft.Text("Report", size=18, weight=ft.FontWeight.W_600),
            latest_report_hint,
            pruefbedarf_box,
            ft.Container(
                bgcolor=ft.Colors.BLUE_GREY_50,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    [
                        ft.Text("Summary (report.json)", weight=ft.FontWeight.W_600),
                        summary_processed,
                        summary_documents,
                        summary_duplicates,
                        summary_unklar,
                        summary_errors,
                        summary_fallbacks,
                    ],
                    spacing=2,
                ),
            ),
            report_text,
        ],
        spacing=10,
        expand=True,
    )
    page.add(controls)

    load_runtime_context()
    latest = find_latest_report()
    if latest is not None:
        json_candidate = latest.with_name("report.json")
        load_report_views(latest, json_candidate if json_candidate.exists() else None)
    page.update()


def main() -> None:
    ft.app(target=_ui)


if __name__ == "__main__":
    main()
