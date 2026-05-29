from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path

import flet as ft

from invoice_tool.config import ConfigError, load_app_config, load_office_rules
from invoice_tool.run import RunError, run_once

_DOC_TYPE_LABELS: dict[str, str] = {
    "invoice": "Eingangsrechnung",
    "credit_note": "Gutschrift",
    "contract": "Vertrag",
    "delivery_note": "Lieferschein",
    "tax_notice": "Steuerbescheid",
    "order_confirmation": "Bestellbestätigung",
    "internal_document": "Interner Beleg",
    "generic_document": "Sonstiges Dokument",
}

# Farbpalette für Status-Badges (bg, border, text_color)
_STATUS_BADGE_PALETTE: dict[str, tuple[str, str, str]] = {
    "bereit": (ft.Colors.BLUE_50, ft.Colors.BLUE_200, ft.Colors.BLUE_700),
    "läuft …": (ft.Colors.ORANGE_50, ft.Colors.ORANGE_200, ft.Colors.ORANGE_700),
    "fertig": (ft.Colors.GREEN_50, ft.Colors.GREEN_200, ft.Colors.GREEN_700),
    "Prüfung nötig": (ft.Colors.RED_50, ft.Colors.RED_200, ft.Colors.RED_700),
    "Fehler": (ft.Colors.RED_50, ft.Colors.RED_200, ft.Colors.RED_700),
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
    badge_text_color = ft.Colors.RED_700 if is_error else ft.Colors.AMBER_700
    badge_bg = ft.Colors.RED_50 if is_error else ft.Colors.AMBER_50
    badge_border = ft.Colors.RED_200 if is_error else ft.Colors.AMBER_200

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
                ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=14, color=ft.Colors.BLUE_GREY_400),
                ft.Text("Original:", size=12, color=ft.Colors.BLUE_GREY_600, width=80),
                ft.Text(
                    filename,
                    size=12,
                    font_family="Courier New",
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
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=ft.Colors.BLUE_GREY_400),
                    ft.Text("Prüfgrund:", size=12, color=ft.Colors.BLUE_GREY_600, width=80),
                    ft.Text(
                        notes,
                        size=12,
                        color=ft.Colors.BLUE_GREY_700,
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
                    ft.Icon(ft.Icons.OUTPUT, size=14, color=ft.Colors.BLUE_GREY_400),
                    ft.Text("Vorschlag:", size=12, color=ft.Colors.BLUE_GREY_600, width=80),
                    ft.Text(
                        Path(output).name,
                        size=12,
                        font_family="Courier New",
                        selectable=True,
                        expand=True,
                    ),
                ],
                spacing=4,
            )
        )

    return ft.Container(
        bgcolor=ft.Colors.AMBER_50,
        border=ft.border.all(1, ft.Colors.AMBER_200),
        border_radius=8,
        padding=10,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.WARNING_AMBER_ROUNDED,
                            size=16,
                            color=ft.Colors.AMBER_700,
                        ),
                        ft.Text(
                            "Verarbeitungsfehler" if is_error else "Unklares Dokument",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.AMBER_800,
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


def _load_profile_json(profile_path: Path) -> tuple[dict | None, str | None]:
    """Liest und parst die Profil-JSON-Datei ohne Seiteneffekte.

    Gibt (data, None) bei Erfolg zurück, (None, fehlermeldung) bei Fehler.
    Schreibt keine Dateien und beeinflusst keine Verarbeitung.
    """
    try:
        text = profile_path.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            return None, "Profildatei hat unerwartetes Format (kein JSON-Objekt)."
        return data, None
    except FileNotFoundError:
        return None, f"Profildatei nicht gefunden:\n{profile_path}"
    except json.JSONDecodeError as exc:
        return None, f"Profildatei enthält kein gültiges JSON:\n{exc}"
    except OSError as exc:
        return None, f"Profildatei konnte nicht gelesen werden:\n{exc}"


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
        font_family="Courier New",  # Monospace für Pfadanzeige
    )

    # --- Source- und Output-Felder ---
    source_field = ft.TextField(
        label="Source-Ordner (Original-PDFs, werden nie verändert)",
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

    # --- Status-Badge (farbige Kapsel) ---
    status_value = ft.Text(
        "bereit", color=ft.Colors.BLUE_700, size=16, weight=ft.FontWeight.W_600
    )
    status_badge = ft.Container(
        content=status_value,
        bgcolor=ft.Colors.BLUE_50,
        border=ft.border.all(1, ft.Colors.BLUE_200),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=14, vertical=4),
    )

    # --- Log ---
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

    # --- Prüffälle (Manuelle Prüfung erforderlich) ---
    prueffaelle_col = ft.Column([], spacing=8)
    pruefbedarf_box = ft.Container(
        visible=False,
        bgcolor=ft.Colors.AMBER_50,
        border=ft.border.all(1, ft.Colors.AMBER_200),
        border_radius=8,
        padding=12,
        content=prueffaelle_col,
    )

    # --- Report ---
    report_text = ft.TextField(
        value="",
        multiline=True,
        min_lines=16,
        read_only=True,
        expand=True,
    )
    latest_report_hint = ft.Text(
        "Kein Report geladen.",
        font_family="Courier New",  # Monospace für Pfadanzeige
    )

    # Laufordner-Pfad-Hinweis (nach erfolgreichem Lauf sichtbar)
    run_dir_hint = ft.Text(
        "",
        selectable=True,
        font_family="Courier New",
        size=13,
        color=ft.Colors.BLUE_GREY_700,
        visible=False,
    )
    run_dir_row = ft.Container(
        visible=False,
        content=ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER_OUTLINED, size=15, color=ft.Colors.BLUE_GREY_400),
                ft.Text(
                    "Ausgabeordner dieses Laufs:",
                    size=13,
                    color=ft.Colors.BLUE_GREY_600,
                ),
                run_dir_hint,
            ],
            spacing=6,
        ),
    )

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
        palette = _STATUS_BADGE_PALETTE.get(
            text,
            (ft.Colors.BLUE_GREY_50, ft.Colors.BLUE_GREY_200, color),
        )
        status_badge.bgcolor = palette[0]
        status_badge.border = ft.border.all(1, palette[1])

    def reset_report_view() -> None:
        summary_processed.value = "Processed: -"
        summary_documents.value = "Documents: -"
        summary_duplicates.value = "Duplicates: -"
        summary_unklar.value = "Unklar: -"
        summary_errors.value = "Errors: -"
        summary_fallbacks.value = "System Fallbacks: -"
        pruefbedarf_box.visible = False
        pruefbedarf_box.bgcolor = ft.Colors.AMBER_50
        pruefbedarf_box.border = ft.border.all(1, ft.Colors.AMBER_200)
        prueffaelle_col.controls = []
        report_text.value = ""
        latest_report_hint.value = "Kein Report geladen."
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
                        color=ft.Colors.AMBER_700,
                    ),
                    ft.Text(
                        "Manuelle Prüfung erforderlich",
                        weight=ft.FontWeight.W_700,
                        size=15,
                        color=ft.Colors.AMBER_800,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(
                f"{count} {count_suffix} deine Prüfung.",
                size=13,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.AMBER_800,
            ),
            ft.Text(
                "Unklare Dokumente",
                size=12,
                color=ft.Colors.AMBER_700,
                weight=ft.FontWeight.W_500,
            ),
            *[_build_review_item_card(item) for item in items],
        ]
        pruefbedarf_box.bgcolor = ft.Colors.AMBER_50
        pruefbedarf_box.border = ft.border.all(1, ft.Colors.AMBER_200)
        pruefbedarf_box.visible = True

    def _show_review_empty() -> None:
        """Zeigt eine ruhige Erfolgsmeldung wenn keine Prüffälle vorhanden."""
        prueffaelle_col.controls = [
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE_OUTLINE,
                        size=16,
                        color=ft.Colors.GREEN_600,
                    ),
                    ft.Text(
                        "Keine Prüffälle im letzten Lauf.",
                        size=13,
                        color=ft.Colors.GREEN_700,
                    ),
                ],
                spacing=6,
            )
        ]
        pruefbedarf_box.bgcolor = ft.Colors.GREEN_50
        pruefbedarf_box.border = ft.border.all(1, ft.Colors.GREEN_200)
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
                    color=ft.Colors.AMBER_800,
                ),
                ft.Text(
                    "Diese Dokumente brauchen deine Prüfung.",
                    size=13,
                    color=ft.Colors.AMBER_700,
                ),
                ft.Text(pruefbedarf, selectable=True, size=12, font_family="Courier New"),
            ]
            pruefbedarf_box.bgcolor = ft.Colors.AMBER_50
            pruefbedarf_box.border = ft.border.all(1, ft.Colors.AMBER_200)
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

        json_loaded = False
        review_items: list[dict] = []
        if report_json and report_json.exists():
            try:
                data = json.loads(report_json.read_text(encoding="utf-8"))
                json_loaded = True
                summary = data.get("summary", {})
                summary_processed.value = f"Processed: {summary.get('processed', '-')}"
                summary_documents.value = f"Documents: {summary.get('documents', '-')}"
                summary_duplicates.value = f"Duplicates: {summary.get('duplicates', '-')}"
                summary_unklar.value = f"Unklar: {summary.get('unklar', '-')}"
                summary_errors.value = f"Errors: {summary.get('errors', '-')}"
                summary_fallbacks.value = (
                    f"System Fallbacks: {summary.get('system_fallbacks', '-')}"
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
            set_status("fertig", ft.Colors.GREEN_700)
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

    # --- Profildetail-Dialog (nur lesend) ---

    def _build_profile_dialog_content() -> ft.Column:
        """Erstellt den Inhalt des read-only Profildetail-Dialogs."""
        rows: list[ft.Control] = []

        # Hinweiszeile: nur lesend
        rows.append(
            ft.Container(
                bgcolor=ft.Colors.BLUE_50,
                border=ft.border.all(1, ft.Colors.BLUE_200),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.LOCK_OUTLINE, size=15, color=ft.Colors.BLUE_700),
                        ft.Text(
                            "Diese Ansicht ist nur lesend. Änderungen sind hier nicht möglich.",
                            color=ft.Colors.BLUE_700,
                            size=13,
                            italic=True,
                        ),
                    ],
                    spacing=6,
                ),
            )
        )

        def _label_row(label: str, value: str, mono: bool = False) -> ft.Row:
            return ft.Row(
                [
                    ft.Text(label, weight=ft.FontWeight.W_600, size=13, width=160),
                    ft.Text(
                        value,
                        selectable=True,
                        size=13,
                        font_family="Courier New" if mono else None,
                        expand=True,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )

        def _section(title: str) -> ft.Text:
            return ft.Text(
                title,
                size=14,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.BLUE_GREY_700,
            )

        # Basisdaten
        rows.append(ft.Divider(height=8))
        rows.append(_section("Verarbeitungsprofil"))
        rows.append(
            _label_row(
                "Lokales Profil:",
                "gefunden" if profile_path else "nicht gefunden – nur Basis-Regeln",
            )
        )
        rows.append(
            _label_row(
                "Profildatei:",
                str(profile_path) if profile_path else "–",
                mono=True,
            )
        )
        rows.append(_label_row("Aktives Preset:", preset_label.value or "–"))

        if profile_path is None:
            rows.append(
                ft.Container(
                    bgcolor=ft.Colors.ORANGE_50,
                    border=ft.border.all(1, ft.Colors.ORANGE_200),
                    border_radius=6,
                    padding=8,
                    content=ft.Text(
                        "Kein lokales Profil gefunden. Es gelten nur die Basis-Regeln aus office_rules.json.",
                        color=ft.Colors.ORANGE_700,
                        size=13,
                    ),
                )
            )
            return ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO)

        # Profil-JSON lesen
        data, err = _load_profile_json(profile_path)
        if err:
            rows.append(
                ft.Container(
                    bgcolor=ft.Colors.RED_50,
                    border=ft.border.all(1, ft.Colors.RED_200),
                    border_radius=6,
                    padding=8,
                    content=ft.Column(
                        [
                            ft.Text(
                                "Profildatei konnte nicht gelesen werden:",
                                color=ft.Colors.RED_700,
                                weight=ft.FontWeight.W_600,
                                size=13,
                            ),
                            ft.Text(err, color=ft.Colors.RED_700, size=12, selectable=True),
                        ],
                        spacing=4,
                    ),
                )
            )
            return ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO)

        # Profilname und Beschreibung
        rows.append(_label_row("Profilname:", data.get("profile_name", "–")))
        desc = data.get("description", "")
        if desc:
            rows.append(
                ft.Row(
                    [
                        ft.Text("Beschreibung:", weight=ft.FontWeight.W_600, size=13, width=160),
                        ft.Text(desc, size=12, color=ft.Colors.BLUE_GREY_600, expand=True),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            )

        # Ordner
        folders = data.get("folders", [])
        folder_label_by_id = {
            str(f.get("id", "")): str(f.get("label") or f.get("folder_name") or f.get("id") or "–")
            for f in folders
            if isinstance(f, dict)
        }
        rows.append(ft.Divider(height=8))
        rows.append(_section("Zielordner"))
        if folders:
            for f in folders:
                f_label = f.get("label", "?")
                f_name = f.get("folder_name", "?")
                rows.append(
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.FOLDER_OUTLINED, size=14, color=ft.Colors.BLUE_GREY_400),
                            ft.Text(f_label, size=13, width=240),
                            ft.Text(
                                f_name,
                                size=12,
                                font_family="Courier New",
                                color=ft.Colors.BLUE_GREY_600,
                            ),
                        ],
                        spacing=6,
                    )
                )
        else:
            rows.append(ft.Text("Keine Ordner konfiguriert.", size=13, color=ft.Colors.BLUE_GREY_500))

        # Dokumenttypen (document_profiles)
        doc_profiles = data.get("document_profiles", [])
        rows.append(ft.Divider(height=8))
        rows.append(_section("Dokumenttypen"))
        if not doc_profiles:
            rows.append(
                ft.Container(
                    bgcolor=ft.Colors.BLUE_GREY_50,
                    border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                    border_radius=6,
                    padding=8,
                    content=ft.Text(
                        "In diesem Profil sind noch keine zusätzlichen Dokumenttypen definiert.",
                        size=13,
                        color=ft.Colors.BLUE_GREY_600,
                        italic=True,
                    ),
                )
            )
        else:
            for dp in doc_profiles:
                threshold = dp.get("confidence_threshold")
                threshold_str = f"{threshold}" if threshold is not None else "–"
                rows.append(
                    ft.Container(
                        bgcolor=ft.Colors.BLUE_GREY_50,
                        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                        border_radius=6,
                        padding=8,
                        content=ft.Column(
                            [
                                ft.Text(
                                    dp.get("label", dp.get("id", "?")),
                                    weight=ft.FontWeight.W_600,
                                    size=13,
                                ),
                                ft.Row(
                                    [
                                        ft.Text("id:", size=12, color=ft.Colors.BLUE_GREY_600, width=100),
                                        ft.Text(dp.get("id", "–"), size=12, font_family="Courier New"),
                                    ]
                                ),
                                ft.Row(
                                    [
                                        ft.Text("Typ:", size=12, color=ft.Colors.BLUE_GREY_600, width=100),
                                        ft.Text(
                                            _DOC_TYPE_LABELS.get(dp.get("document_type", ""), dp.get("document_type", "–")),
                                            size=12,
                                        ),
                                    ]
                                ),
                                ft.Row(
                                    [
                                        ft.Text("Zielordner:", size=12, color=ft.Colors.BLUE_GREY_600, width=100),
                                        ft.Text(
                                            folder_label_by_id.get(str(dp.get("target_folder_id", "")), dp.get("target_folder_id", "–")),
                                            size=12,
                                        ),
                                    ]
                                ),
                                ft.Row(
                                    [
                                        ft.Text("Fallback:", size=12, color=ft.Colors.BLUE_GREY_600, width=100),
                                        ft.Text(
                                            folder_label_by_id.get(str(dp.get("fallback_folder_id", "")), dp.get("fallback_folder_id", "–")),
                                            size=12,
                                        ),
                                    ]
                                ),
                                ft.Row(
                                    [
                                        ft.Text("Konfidenz:", size=12, color=ft.Colors.BLUE_GREY_600, width=100),
                                        ft.Text(threshold_str, size=12),
                                    ]
                                ),
                            ],
                            spacing=2,
                        ),
                    )
                )

        return ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO)

    def on_show_profile_details(_event: ft.ControlEvent) -> None:
        content = _build_profile_dialog_content()
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.POLICY_OUTLINED, color=ft.Colors.BLUE_GREY_700),
                    ft.Text(
                        "Verarbeitungsprofil – Details",
                        weight=ft.FontWeight.W_600,
                    ),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=content,
                width=620,
                height=520,
            ),
            actions=[
                ft.TextButton(
                    "Schließen",
                    on_click=lambda _: page.close(dialog),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dialog)

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
                        ft.Row(
                            [
                                ft.TextButton(
                                    "Profildetails ansehen",
                                    icon=ft.Icons.INFO_OUTLINE,
                                    on_click=on_show_profile_details,
                                    style=ft.ButtonStyle(
                                        color=ft.Colors.BLUE_700,
                                        padding=ft.padding.symmetric(horizontal=0, vertical=0),
                                    ),
                                ),
                            ]
                        ),
                    ],
                    spacing=6,
                ),
            ),

            # Abschnitt: Eingang / Ordnerauswahl
            ft.Divider(),
            ft.Text("Eingang", size=18, weight=ft.FontWeight.W_600),

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

            # Originalschutz-Hinweis (dauerhaft sichtbar)
            ft.Row(
                [
                    ft.Icon(ft.Icons.LOCK_OUTLINE, size=16, color=ft.Colors.BLUE_GREY_400),
                    ft.Text(
                        "Originaldateien werden nie verändert.",
                        color=ft.Colors.BLUE_GREY_600,
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
                        "Letzten Report öffnen",
                        icon=ft.Icons.DESCRIPTION,
                        on_click=on_open_latest_report,
                    ),
                ],
                wrap=True,
                spacing=10,
            ),

            # Status-Badge
            ft.Row([ft.Text("Status:", weight=ft.FontWeight.W_600), status_badge]),

            # Abschnitt: Bericht / Ergebnis
            ft.Divider(),
            ft.Text("Bericht / Ergebnis", size=18, weight=ft.FontWeight.W_600),

            # Ausgabeordner-Pfad nach Laufabschluss (selektierbar, Monospace)
            run_dir_row,

            # Lauflog
            ft.Text(
                "Lauflog",
                size=14,
                weight=ft.FontWeight.W_500,
                color=ft.Colors.BLUE_GREY_700,
            ),
            log_output,

            # Report-Pfad-Hinweis (Monospace)
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
