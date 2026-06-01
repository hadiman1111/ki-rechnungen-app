from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path

import flet as ft

from invoice_tool.config import ConfigError, load_app_config, load_office_rules
from invoice_tool.run import RunError, run_once
from invoice_tool.ui_profile_dialog import show_profile_details_dialog
from invoice_tool.ui_tokens import (
    ACCENT,
    ACCENT_SOFT,
    ERR,
    ERR_SOFT,
    INK_2,
    LINE,
    MONO_FONT,
    MUTED,
    MUTED_2,
    OK,
    OK_SOFT,
    SURFACE_2,
    WARN,
    WARN_EDGE,
    WARN_SOFT,
)

# Farbpalette für Status-Badges (bg, border, text_color)
_STATUS_BADGE_PALETTE: dict[str, tuple[str, str, str]] = {
    "Bereit":        (ACCENT_SOFT, ACCENT,    ACCENT),
    "Läuft":         (ACCENT_SOFT, ACCENT,    ACCENT),
    "Fertig":        (OK_SOFT,     OK,        OK),
    "Prüfung nötig": (ERR_SOFT,    ERR,       ERR),
    "Fehler":        (ERR_SOFT,    ERR,       ERR),
}

# Statuswerte, die manuelle Prüfung erfordern
_REVIEW_STATUSES: frozenset[str] = frozenset({"unklar", "error", "failed"})


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


def _build_review_item_card(item: dict) -> ft.Container:
    """Erstellt eine Karte für einen einzelnen Prüffall aus report.json."""
    filename = item.get("filename") or "–"
    output = item.get("output") or ""
    notes = item.get("notes") or ""
    status = item.get("status") or "unklar"

    is_error = status in ("error", "failed")
    badge_text_color = ERR if is_error else WARN
    badge_bg = ERR_SOFT if is_error else WARN_SOFT
    badge_border = ERR if is_error else WARN_EDGE

    _STATUS_LABELS = {
        "unklar": "unklar",
        "error": "Fehler",
        "failed": "Fehlgeschlagen",
    }
    badge_label = _STATUS_LABELS.get(status, status)

    status_badge = ft.Container(
        content=ft.Text(badge_label, size=11, color=badge_text_color, weight=ft.FontWeight.W_600),
        bgcolor=badge_bg,
        border=ft.border.all(1, badge_border),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
    )

    detail_rows: list[ft.Control] = [
        ft.Row(
            [
                ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=14, color=MUTED_2),
                ft.Text("Original:", size=12, color=MUTED, width=80),
                ft.Text(
                    filename,
                    size=12,
                    font_family=MONO_FONT,
                    selectable=True,
                    expand=True,
                ),
            ],
            spacing=4,
        ),
    ]
    if notes:
        detail_rows.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=MUTED_2),
                    ft.Text("Prüfgrund:", size=12, color=MUTED, width=80),
                    ft.Text(
                        notes,
                        size=12,
                        color=INK_2,
                        expand=True,
                        selectable=True,
                    ),
                ],
                spacing=4,
            )
        )
    if output:
        detail_rows.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.OUTPUT, size=14, color=MUTED_2),
                    ft.Text("Vorschlag:", size=12, color=MUTED, width=80),
                    ft.Text(
                        Path(output).name,
                        size=12,
                        font_family=MONO_FONT,
                        selectable=True,
                        expand=True,
                    ),
                ],
                spacing=4,
            )
        )

    return ft.Container(
        bgcolor=WARN_SOFT,
        border=ft.border.all(1, WARN_EDGE),
        border_radius=8,
        padding=10,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.WARNING_AMBER_ROUNDED,
                            size=16,
                            color=WARN,
                        ),
                        ft.Text(
                            "Verarbeitungsfehler" if is_error else "Unklares Dokument",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=WARN,
                            expand=True,
                        ),
                        status_badge,
                    ],
                    spacing=6,
                ),
                *detail_rows,
            ],
            spacing=4,
        ),
    )


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
        size=11,
        color=MUTED if profile_path else WARN,
        font_family=MONO_FONT,
    )

    # --- Quell- und Zielordner-Felder ---
    source_field = ft.TextField(
        label="Quellordner",
        expand=True,
        hint_text="Pfad zum Ordner mit den Original-PDFs …",
    )
    output_field = ft.TextField(
        label="Zielordner",
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

    # --- Status-Badge (farbige Kapsel) ---
    status_value = ft.Text(
        "Bereit", color=ACCENT, size=16, weight=ft.FontWeight.W_600
    )
    status_badge = ft.Container(
        content=status_value,
        bgcolor=ACCENT_SOFT,
        border=ft.border.all(1, ACCENT),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=14, vertical=4),
    )

    # --- Log ---
    log_output = ft.TextField(
        value="",
        multiline=True,
        min_lines=4,
        max_lines=12,
        read_only=True,
        expand=True,
        hint_text="Noch kein Lauf gestartet. Nach der Verarbeitung erscheinen hier Verlauf und Meldungen.",
    )

    # --- Zusammenfassung ---
    summary_processed = ft.Text("Verarbeitet: –")
    summary_documents = ft.Text("Dokumente: –")
    summary_duplicates = ft.Text("Duplikate: –")
    summary_unklar = ft.Text("Unklar: –")
    summary_errors = ft.Text("Fehler: –")
    summary_fallbacks = ft.Text("System-Ersatzwerte: –")

    # --- Prüffälle (Manuelle Prüfung erforderlich) ---
    prueffaelle_col = ft.Column([], spacing=8)
    pruefbedarf_box = ft.Container(
        visible=False,
        bgcolor=WARN_SOFT,
        border=ft.border.all(1, WARN_EDGE),
        border_radius=8,
        padding=12,
        content=prueffaelle_col,
    )

    # --- Bericht ---
    report_text = ft.TextField(
        value="",
        multiline=True,
        min_lines=6,
        read_only=True,
        expand=True,
        hint_text="Noch kein Lauf gestartet. Nach der Verarbeitung erscheinen hier Ergebnis und Bericht.",
    )
    latest_report_hint = ft.Text(
        "Kein Bericht geladen.",
    )

    # Laufordner-Pfad-Hinweis (nach erfolgreichem Lauf sichtbar)
    run_dir_hint = ft.Text(
        "",
        selectable=True,
        font_family=MONO_FONT,
        size=13,
        color=INK_2,
        visible=False,
    )
    run_dir_row = ft.Container(
        visible=False,
        content=ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER_OUTLINED, size=15, color=MUTED_2),
                ft.Text(
                    "Ausgabeordner dieses Laufs:",
                    size=13,
                    color=MUTED,
                ),
                run_dir_hint,
            ],
            spacing=6,
        ),
    )

    # --- Start-Button ---
    start_button = ft.ElevatedButton(
        "Verarbeitung starten",
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
        palette = _STATUS_BADGE_PALETTE.get(
            text,
            (SURFACE_2, LINE, color),
        )
        status_badge.bgcolor = palette[0]
        status_badge.border = ft.border.all(1, palette[1])

    def reset_report_view() -> None:
        summary_processed.value = "Verarbeitet: –"
        summary_documents.value = "Dokumente: –"
        summary_duplicates.value = "Duplikate: –"
        summary_unklar.value = "Unklar: –"
        summary_errors.value = "Fehler: –"
        summary_fallbacks.value = "System-Ersatzwerte: –"
        pruefbedarf_box.visible = False
        pruefbedarf_box.bgcolor = WARN_SOFT
        pruefbedarf_box.border = ft.border.all(1, WARN_EDGE)
        prueffaelle_col.controls = []
        report_text.value = ""
        latest_report_hint.value = "Kein Bericht geladen."
        run_dir_row.visible = False
        run_dir_hint.value = ""

    def _show_review_items(items: list[dict]) -> None:
        """Füllt die Prüffälle-Box mit Einzelkarten (aus report.json)."""
        count = len(items)
        count_suffix = "Dokument braucht" if count == 1 else "Dokumente brauchen"
        prueffaelle_col.controls = [
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.WARNING_AMBER_ROUNDED,
                        size=20,
                        color=WARN,
                    ),
                    ft.Text(
                        "Manuelle Prüfung erforderlich",
                        weight=ft.FontWeight.W_700,
                        size=15,
                        color=WARN,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(
                f"{count} {count_suffix} deine Prüfung.",
                size=13,
                weight=ft.FontWeight.W_600,
                color=WARN,
            ),
            ft.Text(
                "Unklare Dokumente",
                size=12,
                color=WARN,
                weight=ft.FontWeight.W_500,
            ),
            *[_build_review_item_card(item) for item in items],
        ]
        pruefbedarf_box.bgcolor = WARN_SOFT
        pruefbedarf_box.border = ft.border.all(1, WARN_EDGE)
        pruefbedarf_box.visible = True

    def _show_review_empty() -> None:
        """Zeigt eine ruhige Erfolgsmeldung wenn keine Prüffälle vorhanden."""
        prueffaelle_col.controls = [
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE_OUTLINE,
                        size=16,
                        color=OK,
                    ),
                    ft.Text(
                        "Keine Prüffälle im letzten Lauf.",
                        size=13,
                        color=OK,
                    ),
                ],
                spacing=6,
            )
        ]
        pruefbedarf_box.bgcolor = OK_SOFT
        pruefbedarf_box.border = ft.border.all(1, OK)
        pruefbedarf_box.visible = True

    def _show_review_fallback(txt_content: str) -> None:
        """Fallback: Prüfbedarf-Block aus report.txt extrahieren und anzeigen."""
        pruefbedarf = _extract_pruefbedarf_block(txt_content)
        if pruefbedarf and pruefbedarf != "PRÜFBEDARF: keiner":
            prueffaelle_col.controls = [
                ft.Text(
                    "Manuelle Prüfung erforderlich",
                    weight=ft.FontWeight.W_700,
                    size=15,
                    color=WARN,
                ),
                ft.Text(
                    "Diese Dokumente brauchen deine Prüfung.",
                    size=13,
                    color=WARN,
                ),
                ft.Text(pruefbedarf, selectable=True, size=12, font_family=MONO_FONT),
            ]
            pruefbedarf_box.bgcolor = WARN_SOFT
            pruefbedarf_box.border = ft.border.all(1, WARN_EDGE)
            pruefbedarf_box.visible = True
        else:
            pruefbedarf_box.visible = False

    def load_report_views(report_txt: Path, report_json: Path | None) -> None:
        nonlocal last_report_txt
        last_report_txt = report_txt
        txt_content = ""
        if report_txt.exists():
            txt_content = report_txt.read_text(encoding="utf-8")
            report_text.value = txt_content
            latest_report_hint.value = str(report_txt)
            latest_report_hint.font_family = MONO_FONT

        json_loaded = False
        review_items: list[dict] = []
        if report_json and report_json.exists():
            try:
                data = json.loads(report_json.read_text(encoding="utf-8"))
                json_loaded = True
                summary = data.get("summary", {})
                summary_processed.value = f"Verarbeitet: {summary.get('processed', '–')}"
                summary_documents.value = f"Dokumente: {summary.get('documents', '–')}"
                summary_duplicates.value = f"Duplikate: {summary.get('duplicates', '–')}"
                summary_unklar.value = f"Unklar: {summary.get('unklar', '–')}"
                summary_errors.value = f"Fehler: {summary.get('errors', '–')}"
                summary_fallbacks.value = (
                    f"System-Ersatzwerte: {summary.get('system_fallbacks', '–')}"
                )
                review_items = [
                    f
                    for f in data.get("files", [])
                    if isinstance(f, dict) and f.get("status", "") in _REVIEW_STATUSES
                ]
            except (json.JSONDecodeError, OSError):
                json_loaded = False

        if json_loaded:
            if review_items:
                _show_review_items(review_items)
            else:
                _show_review_empty()
        else:
            _show_review_fallback(txt_content)

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
            set_status("Fertig", OK)
            start_button.disabled = False
            append_log(f"[fertig] Run-Ordner: {run_dir}")

            # Ausgabeordner-Pfad nach Abschluss anzeigen
            run_dir_hint.value = str(run_dir / "output")
            run_dir_row.visible = True
            page.title = "Lauf abgeschlossen"

            if report_txt:
                load_report_views(report_txt, report_json)
            else:
                latest_report_hint.value = (
                    f"Kein Bericht gefunden unter {run_dir / 'output' / '_runs'}"
                )
            page.update()

        except (RunError, ConfigError) as exc:
            run_in_progress = False
            set_status("Fehler", ERR)
            start_button.disabled = False
            append_log(f"[fehler] {exc}")
            page.update()

        except Exception as exc:  # noqa: BLE001
            run_in_progress = False
            set_status("Fehler", ERR)
            start_button.disabled = False
            append_log(f"[unerwarteter fehler] {exc}")
            page.update()

    def on_start_run(_event: ft.ControlEvent) -> None:
        nonlocal run_in_progress
        if run_in_progress:
            return
        if not source_field.value or not source_field.value.strip():
            append_log("Bitte einen Quellordner angeben.")
            page.update()
            return
        if not output_field.value or not output_field.value.strip():
            append_log("Bitte einen Zielordner angeben.")
            page.update()
            return
        run_in_progress = True
        log_output.value = ""
        reset_report_view()
        set_status("Läuft", ACCENT)
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

    # --- Profildetail-Dialog (nur lesend, Logik in ui_profile_dialog) ---

    def on_show_profile_details(_event: ft.ControlEvent) -> None:
        show_profile_details_dialog(page, profile_path, preset_label.value or "–")

    # --- Layout ---
    controls = ft.Column(
        [
            ft.Text("KI-Rechnungen-App", size=30, weight=ft.FontWeight.BOLD),

            # Info-Box: Profil + Verarbeitungsregeln-Einstieg
            ft.Container(
                bgcolor=SURFACE_2,
                border=ft.border.all(1, LINE),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    [
                        ft.Row(
                            [ft.Text("Profil:", weight=ft.FontWeight.W_600), preset_label]
                        ),
                        ft.Row(
                            [
                                ft.TextButton(
                                    "Verarbeitung einrichten",
                                    icon=ft.Icons.RULE_OUTLINED,
                                    on_click=on_show_profile_details,
                                    style=ft.ButtonStyle(
                                        color=ACCENT,
                                        padding=ft.padding.symmetric(horizontal=0, vertical=0),
                                    ),
                                ),
                            ]
                        ),
                        ft.Text(
                            "Regeln für Erkennung, Benennung und Ablage.",
                            size=12,
                            color=MUTED,
                            italic=True,
                        ),
                        ft.Row(
                            [
                                ft.Text(
                                    "Konfiguration:",
                                    size=11,
                                    color=MUTED_2,
                                    width=88,
                                ),
                                profile_label,
                            ],
                            spacing=4,
                        ),
                    ],
                    spacing=4,
                ),
            ),

            # Abschnitt: Eingang / Ordnerauswahl
            ft.Divider(),
            ft.Text("Eingang", size=18, weight=ft.FontWeight.W_600),

            # Quellordner-Zeile
            ft.Row(
                [
                    source_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Quellordner wählen",
                        on_click=lambda _: source_picker.get_directory_path(
                            dialog_title="Quellordner wählen (Eingangs-PDFs)"
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

            # Zielordner-Zeile
            ft.Row(
                [
                    output_field,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        tooltip="Zielordner wählen",
                        on_click=lambda _: output_picker.get_directory_path(
                            dialog_title="Zielordner wählen (Lauf-Ausgabe)"
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

            # Originalschutz-Hinweis (dauerhaft sichtbar)
            ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=MUTED_2),
                    ft.Text(
                        "Originale bleiben unverändert. Das Programm arbeitet mit Kopien.",
                        color=MUTED,
                        size=13,
                    ),
                ],
                spacing=6,
            ),

            # Abschnitt: Verarbeitung / Start
            ft.Divider(),
            ft.Text("Verarbeitung", size=18, weight=ft.FontWeight.W_600),

            # Aktions-Buttons
            ft.Row(
                [
                    start_button,
                    ft.OutlinedButton(
                        "Letzten Bericht öffnen",
                        icon=ft.Icons.DESCRIPTION,
                        on_click=on_open_latest_report,
                    ),
                ],
                wrap=True,
                spacing=10,
            ),

            # Status-Badge
            ft.Row([ft.Text("Status:", weight=ft.FontWeight.W_600), status_badge]),

            # Abschnitt: Ergebnis
            ft.Divider(),
            ft.Text("Ergebnis", size=18, weight=ft.FontWeight.W_600),

            # Ausgabeordner-Pfad nach Laufabschluss (selektierbar, Monospace)
            run_dir_row,

            # Lauf-Protokoll (Log)
            ft.Text(
                "Lauf-Protokoll",
                size=14,
                weight=ft.FontWeight.W_500,
                color=INK_2,
            ),
            log_output,

            # Bericht-Pfad-Hinweis (Monospace)
            latest_report_hint,
            pruefbedarf_box,
            ft.Container(
                bgcolor=SURFACE_2,
                border=ft.border.all(1, LINE),
                border_radius=8,
                padding=12,
                content=ft.Column(
                    [
                        ft.Text("Ergebnis-Details", weight=ft.FontWeight.W_600),
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
