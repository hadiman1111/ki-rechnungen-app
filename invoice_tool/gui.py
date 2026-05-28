from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path

import flet as ft

from invoice_tool.config import ConfigError, load_app_config, load_office_rules
from invoice_tool.run import RunError, run_once


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


def _find_report_in_run_dir(run_dir: Path) -> tuple[Path | None, Path | None]:
    """Sucht report.txt und report.json im von run_once() zurückgegebenen run_dir."""
    runs_dir = run_dir / "output" / "_runs"
    if not runs_dir.exists():
        return None, None
    reports = sorted(
        runs_dir.glob("*/report.txt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not reports:
        return None, None
    report_txt = reports[0]
    report_json = report_txt.with_name("report.json")
    return report_txt, report_json if report_json.exists() else None


def _ui(page: ft.Page) -> None:
    page.title = "KI-Rechnungen-App"
    page.window_width = 1180
    page.window_height = 900
    page.padding = 16
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO

    config_path = Path("invoice_config.json").resolve()
    profile_path: Path | None = None
    last_run_dir: Path | None = None
    last_report_txt: Path | None = None
    run_in_progress = False

    # Profil automatisch neben invoice_config.json suchen
    _profile_candidate = config_path.parent / "profile_config.local.json"
    if _profile_candidate.exists():
        profile_path = _profile_candidate

    # --- Preset- und Profilanzeige ---
    preset_label = ft.Text("-", selectable=True)
    profile_label = ft.Text(
        str(profile_path) if profile_path else "nicht gefunden – nur Basis-Regeln",
        selectable=True,
        color=ft.Colors.GREEN_700 if profile_path else ft.Colors.ORANGE_700,
    )

    # --- Source- und Output-Felder ---
    source_field = ft.TextField(
        label="Source-Ordner (Eingangs-PDFs, wird nie verändert)",
        expand=True,
        hint_text="Pfad zum Ordner mit den Original-PDFs …",
    )
    output_field = ft.TextField(
        label="Output-Ordner (Basis für Lauf-Unterordner)",
        expand=True,
        hint_text="Pfad zum Ausgabe-Basisordner …",
    )

    # --- FilePicker (in Flet eingebaut, keine neue Dependency) ---
    source_picker = ft.FilePicker()
    output_picker = ft.FilePicker()

    def on_source_picked(e: ft.FilePickerResultEvent) -> None:
        if e.path:
            source_field.value = e.path
            page.update()

    def on_output_picked(e: ft.FilePickerResultEvent) -> None:
        if e.path:
            output_field.value = e.path
            page.update()

    source_picker.on_result = on_source_picked
    output_picker.on_result = on_output_picked
    page.overlay.extend([source_picker, output_picker])

    # --- Status / Log ---
    status_value = ft.Text(
        "bereit", color=ft.Colors.BLUE_700, size=16, weight=ft.FontWeight.W_600
    )
    log_output = ft.TextField(
        value="",
        multiline=True,
        min_lines=10,
        max_lines=12,
        read_only=True,
        expand=True,
    )

    # --- Summary ---
    summary_processed = ft.Text("Processed: -")
    summary_documents = ft.Text("Documents: -")
    summary_duplicates = ft.Text("Duplicates: -")
    summary_unklar = ft.Text("Unklar: -")
    summary_errors = ft.Text("Errors: -")
    summary_fallbacks = ft.Text("System Fallbacks: -")

    # --- Prüfbedarf ---
    pruefbedarf_title = ft.Text(
        "PRÜFBEDARF", weight=ft.FontWeight.W_700, color=ft.Colors.RED_700
    )
    pruefbedarf_text = ft.Text("-", selectable=True)
    pruefbedarf_box = ft.Container(
        visible=False,
        bgcolor=ft.Colors.RED_50,
        border=ft.border.all(1, ft.Colors.RED_200),
        border_radius=8,
        padding=12,
        content=ft.Column([pruefbedarf_title, pruefbedarf_text], spacing=6),
    )

    # --- Report ---
    report_text = ft.TextField(
        value="",
        multiline=True,
        min_lines=16,
        read_only=True,
        expand=True,
    )
    latest_report_hint = ft.Text("Kein Report geladen.")

    # --- Start-Button ---
    start_button = ft.ElevatedButton(
        "Lauf starten",
        icon=ft.Icons.PLAY_ARROW,
        style=ft.ButtonStyle(
            text_style=ft.TextStyle(size=18, weight=ft.FontWeight.W_600),
            padding=ft.padding.symmetric(horizontal=20, vertical=18),
        ),
    )

    # --- Hilfsfunktionen ---

    def append_log(line: str) -> None:
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

    def load_report_views(report_txt: Path, report_json: Path | None) -> None:
        nonlocal last_report_txt
        last_report_txt = report_txt
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

    def load_preset_info() -> None:
        """Lädt Preset-Info aus invoice_config.json und befüllt Felder vor, falls leer."""
        try:
            app_config = load_app_config(config_path)
            rules = load_office_rules(
                app_config.regeln_datei,
                active_preset_override=app_config.aktives_preset,
            )
            preset_label.value = rules.active_preset
            if not source_field.value:
                source_field.value = str(app_config.eingangsordner)
            if not output_field.value:
                output_field.value = str(app_config.ausgangsordner)
        except (ConfigError, RuntimeError) as exc:
            preset_label.value = f"Fehler: {exc}"

    # --- Kernfunktion: run_once anbinden ---

    def run_processing() -> None:
        nonlocal run_in_progress, last_run_dir
        try:
            source = Path(source_field.value.strip())
            output = Path(output_field.value.strip())

            append_log(f"[start] source={source}")
            append_log(f"[start] output={output}")
            if profile_path:
                append_log(f"[start] profil={profile_path}")
            else:
                append_log("[start] kein Profil – nur Basis-Regeln")

            run_dir = run_once(
                source=source,
                output=output,
                config_path=config_path,
                profile_path=profile_path,
            )
            last_run_dir = run_dir

            report_txt, report_json = _find_report_in_run_dir(run_dir)

            run_in_progress = False
            set_status("fertig", ft.Colors.GREEN_700)
            start_button.disabled = False
            append_log(f"[fertig] Run-Ordner: {run_dir}")

            if report_txt:
                load_report_views(report_txt, report_json)
            else:
                latest_report_hint.value = (
                    f"Kein Report gefunden unter {run_dir / 'output' / '_runs'}"
                )
            page.update()

        except (RunError, ConfigError) as exc:
            run_in_progress = False
            set_status("Fehler", ft.Colors.RED_700)
            start_button.disabled = False
            append_log(f"[fehler] {exc}")
            page.update()

        except Exception as exc:  # noqa: BLE001
            run_in_progress = False
            set_status("Fehler", ft.Colors.RED_700)
            start_button.disabled = False
            append_log(f"[unerwarteter fehler] {exc}")
            page.update()

    def on_start_run(_event: ft.ControlEvent) -> None:
        nonlocal run_in_progress
        if run_in_progress:
            return
        if not source_field.value or not source_field.value.strip():
            append_log("Bitte einen Source-Ordner angeben.")
            page.update()
            return
        if not output_field.value or not output_field.value.strip():
            append_log("Bitte einen Output-Ordner angeben.")
            page.update()
            return
        run_in_progress = True
        log_output.value = ""
        reset_report_view()
        set_status("läuft …", ft.Colors.ORANGE_700)
        start_button.disabled = True
        page.update()
        page.run_thread(run_processing)

    def on_open_source(_event: ft.ControlEvent) -> None:
        if source_field.value and source_field.value.strip():
            _open_path(Path(source_field.value.strip()))

    def on_open_output_folder(_event: ft.ControlEvent) -> None:
        # Nach einem Lauf: letzten Run-Output-Ordner öffnen
        if last_run_dir is not None:
            target = last_run_dir / "output"
            if target.exists():
                _open_path(target)
                return
        # Fallback: Basis-Output-Ordner
        if output_field.value and output_field.value.strip():
            _open_path(Path(output_field.value.strip()))

    def on_open_latest_report(_event: ft.ControlEvent) -> None:
        if last_report_txt and last_report_txt.exists():
            _open_path(last_report_txt)

    start_button.on_click = on_start_run

    # --- Layout ---
    controls = ft.Column(
        [
            ft.Text("KI-Rechnungen-App", size=30, weight=ft.FontWeight.BOLD),

            # Info-Box: Preset + Profil
            ft.Container(
                bgcolor=ft.Colors.BLUE_GREY_50,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    [
                        ft.Row(
                            [ft.Text("Aktives Preset:", weight=ft.FontWeight.W_600), preset_label]
                        ),
                        ft.Row(
                            [ft.Text("Profil:", weight=ft.FontWeight.W_600), profile_label]
                        ),
                    ],
                    spacing=6,
                ),
            ),

            # Source-Ordner-Zeile
            ft.Row(
                [
                    source_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Source-Ordner wählen",
                        on_click=lambda _: source_picker.get_directory_path(
                            dialog_title="Source-Ordner wählen (Eingangs-PDFs)"
                        ),
                    ),
                    ft.OutlinedButton(
                        "Im Finder öffnen",
                        icon=ft.Icons.OPEN_IN_NEW,
                        on_click=on_open_source,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),

            # Output-Ordner-Zeile
            ft.Row(
                [
                    output_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Output-Ordner wählen",
                        on_click=lambda _: output_picker.get_directory_path(
                            dialog_title="Output-Ordner wählen (Lauf-Ausgabe)"
                        ),
                    ),
                    ft.OutlinedButton(
                        "Im Finder öffnen",
                        icon=ft.Icons.OPEN_IN_NEW,
                        on_click=on_open_output_folder,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),

            # Aktions-Buttons
            ft.Row(
                [
                    start_button,
                    ft.OutlinedButton(
                        "Letzten Report öffnen",
                        icon=ft.Icons.DESCRIPTION,
                        on_click=on_open_latest_report,
                    ),
                ],
                wrap=True,
                spacing=10,
            ),

            # Status
            ft.Row([ft.Text("Status:", weight=ft.FontWeight.W_600), status_value]),

            # Log
            ft.Text("Lauflog", size=18, weight=ft.FontWeight.W_600),
            log_output,

            # Report
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

    load_preset_info()
    page.update()


def main() -> None:
    ft.app(target=_ui)


if __name__ == "__main__":
    main()
