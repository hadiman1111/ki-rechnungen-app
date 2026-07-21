from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
from pathlib import Path

import flet as ft

from invoice_tool.app_paths import (
    ensure_user_config_layout,
    list_profile_entries,
    resolve_active_profile_id,
    resolve_invoice_config_path,
    resolve_profile_path,
    set_active_profile_id,
)
from invoice_tool.profile_store import migrate_all_profiles
from invoice_tool.ui_components import page_error_state
from invoice_tool.ui_shell import (
    NAV_CONFIGURATIONS,
    NAV_PROFILES,
    NAV_REVIEW,
    NAV_SETTINGS,
    NAV_WORKSPACE,
    ShellState,
    build_app_shell_state,
)
from invoice_tool.ui_workspace import (
    build_destination_summary_panel,
    build_ergebnis_panel,
    build_ergebnisse_card,
    build_folder_card,
    build_manual_review_panel,
    build_processing_column,
    build_workspace_view,
)
from invoice_tool.ui_theme import (
    COLOR_PRIMARY as ACCENT,
    COLOR_NAV_ACTIVE_BG as ACCENT_SOFT,
    COLOR_PAGE_BG as BG,
    COLOR_CANVAS as CANVAS,
    COLOR_ERROR as ERR,
    COLOR_ERROR_SOFT as ERR_SOFT,
    COLOR_TEXT_SECONDARY as INK_2,
    COLOR_BORDER as LINE,
    FONT_MONO as MONO_FONT,
    COLOR_TEXT_MUTED as MUTED,
    COLOR_TEXT_MUTED_2 as MUTED_2,
    COLOR_SUCCESS as OK,
    COLOR_SUCCESS_SOFT as OK_SOFT,
    RADIUS_LG as RADIUS_CARD,
    RADIUS_PILL,
    SPACE_XXS as SP_4,
    SPACE_SM as SP_8,
    SPACE_MD as SP_12,
    SPACE_LG as SP_16,
    SPACE_XL as SP_24,
    SPACE_XXL as SP_32,
    APP_MIN_WIDTH as APP_SHELL_WIDTH,
    WORKSPACE_CENTER_WIDTH as CENTER_COL_WIDTH,
    COLOR_SURFACE as SURFACE,
    COLOR_SURFACE_ALT as SURFACE_2,
    COLOR_WARNING as WARN,
    COLOR_WARNING_SOFT as WARN_SOFT,
)
from invoice_tool.ui_tokens import WARN_EDGE

logger = logging.getLogger(__name__)

# Farbpalette für Status-Badges (bg, border, text_color)
_STATUS_BADGE_PALETTE: dict[str, tuple[str, str, str]] = {
    "Bereit":        (ACCENT_SOFT, ACCENT, ACCENT),
    "Läuft":         (ACCENT_SOFT, ACCENT, ACCENT),
    "Fertig":        (OK_SOFT,     OK,     OK),
    "Prüfung nötig": (ERR_SOFT,    ERR,    ERR),
    "Fehler":        (ERR_SOFT,    ERR,    ERR),
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
    output   = item.get("output") or ""
    notes    = item.get("notes") or ""
    status   = item.get("status") or "unklar"

    is_error       = status in ("error", "failed")
    badge_text_color = ERR if is_error else WARN
    badge_bg         = ERR_SOFT if is_error else WARN_SOFT
    badge_border     = ERR if is_error else WARN_EDGE

    _STATUS_LABELS = {
        "unklar": "unklar",
        "error":  "Fehler",
        "failed": "Fehlgeschlagen",
    }
    badge_label = _STATUS_LABELS.get(status, status)

    status_badge = ft.Container(
        content=ft.Text(badge_label, size=11, color=badge_text_color, weight=ft.FontWeight.W_600),
        bgcolor=badge_bg,
        border=ft.Border.all(1, badge_border),
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
    )

    detail_rows: list[ft.Control] = [
        ft.Row(
            [
                ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=14, color=MUTED_2),
                ft.Text("Original:", size=12, color=MUTED, width=80),
                ft.Text(filename, size=12, font_family=MONO_FONT, selectable=True, expand=True),
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
                    ft.Text(notes, size=12, color=INK_2, expand=True, selectable=True),
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
                    ft.Text(Path(output).name, size=12, font_family=MONO_FONT,
                            selectable=True, expand=True),
                ],
                spacing=4,
            )
        )

    return ft.Container(
        bgcolor=WARN_SOFT,
        border=ft.Border.all(1, WARN_EDGE),
        border_radius=8,
        padding=10,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=16, color=WARN),
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
    """Sucht report.txt und report.json im technischen Run-Ordner (Application Support)."""
    runs_dir = run_dir / "_runs"
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


def build_ui(page: ft.Page) -> None:
    from invoice_tool.config import ConfigError, load_app_config, load_office_rules
    from invoice_tool.run import RunError, run_once

    # ── Seiteneinstellungen ──────────────────────────────────────────────────
    page.title = "KI-Rechnungen"
    page.window.width = APP_SHELL_WIDTH
    page.window.min_width = APP_SHELL_WIDTH
    page.window.height = 800
    page.padding = 0
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO

    if os.getenv("FLET_PLATFORM"):
        ensure_user_config_layout()

    from invoice_tool.app_paths import ensure_profile_storage_layout

    ensure_profile_storage_layout()
    migrate_all_profiles()

    config_path = resolve_invoice_config_path()
    current_nav: list[str] = [NAV_WORKSPACE]
    pending_config_id: list[str | None] = [None]
    shell_state: list[ShellState | None] = [None]
    profile_path_ref: list[Path | None] = [resolve_profile_path()]
    profile_path = profile_path_ref[0]
    last_run_dir:  Path | None = None
    last_report_txt: Path | None = None
    run_in_progress = False

    # ── Preset- und Profilanzeige ──────────────────────────────────────────
    preset_label = ft.Text("-", selectable=True, size=12)
    profile_summary_unmatched = ft.Text("Nicht zugeordnet: –", size=12, color=MUTED)
    destination_summary_host = ft.Column([], spacing=4)
    profile_selector_ref: list[ft.Dropdown | None] = [None]

    # ── Quell- und Zielordner-Felder (sekundär in Folder-Cards) ─────────────
    _path_field_style = dict(
        read_only=True,
        dense=True,
        text_size=10,
        height=34,
        hint_text="Noch kein Ordner gewählt …",
        text_style=ft.TextStyle(font_family=MONO_FONT, size=10),
        border_color=LINE,
        focused_border_color=ACCENT,
        content_padding=ft.Padding.symmetric(horizontal=8, vertical=2),
    )
    source_field = ft.TextField(**_path_field_style)
    output_field = ft.TextField(**_path_field_style, visible=False)

    # ── FilePicker (Flet 0.85+: Service, kein sichtbares Control) ──────────
    source_file_count = ft.Text("0 Dateien", size=12, color=MUTED, weight=ft.FontWeight.W_600)
    source_file_list = ft.Column([], spacing=4)

    def refresh_source_inventory() -> None:
        from invoice_tool.source_inventory import discover_source_pdfs

        path_text = (source_field.value or "").strip()
        if not path_text:
            source_file_count.value = "0 Dateien"
            source_file_list.controls = []
            return
        source_path = Path(path_text)
        if not source_path.is_dir():
            source_file_count.value = "Ordner nicht gefunden"
            source_file_list.controls = []
            return
        pdfs = discover_source_pdfs(source_path)
        source_file_count.value = f"{len(pdfs)} Dateien"
        rows: list[ft.Control] = []
        for pdf in pdfs[:5]:
            rows.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.PICTURE_AS_PDF, size=14, color=ERR),
                        ft.Text(pdf.name, size=11, font_family=MONO_FONT, expand=True),
                    ],
                    spacing=4,
                )
            )
        if len(pdfs) > 5:
            rows.append(ft.Text(f"+ {len(pdfs) - 5} weitere Dateien", size=11, color=ACCENT))
        source_file_list.controls = rows

    async def pick_source_directory(_event: ft.ControlEvent) -> None:
        current = (source_field.value or "").strip() or None
        path = await ft.FilePicker().get_directory_path(
            dialog_title="Quellordner wählen (Eingangs-PDFs)",
            initial_directory=current,
        )
        if path:
            source_field.value = path
            refresh_source_inventory()
            page.update()

    async def pick_output_directory(_event: ft.ControlEvent) -> None:
        current = (output_field.value or "").strip() or None
        path = await ft.FilePicker().get_directory_path(
            dialog_title="Zielordner wählen (Lauf-Ausgabe)",
            initial_directory=current,
        )
        if path:
            output_field.value = path
            page.update()

    # ── Status-Pille ────────────────────────────────────────────────────────
    status_value = ft.Text("Bereit", color=ACCENT, size=13, weight=ft.FontWeight.W_600)
    status_badge = ft.Container(
        content=status_value,
        bgcolor=ACCENT_SOFT,
        border=ft.Border.all(1, ACCENT),
        border_radius=RADIUS_PILL,
        padding=ft.Padding.symmetric(horizontal=12, vertical=5),
    )

    # ── Lauf-Protokoll ──────────────────────────────────────────────────────
    log_output = ft.TextField(
        value="",
        multiline=True,
        min_lines=1,
        max_lines=6,
        read_only=True,
        hint_text="Noch kein Lauf – Verlauf erscheint hier.",
        text_style=ft.TextStyle(font_family=MONO_FONT, size=10),
        border_color=LINE,
        content_padding=ft.Padding.symmetric(horizontal=8, vertical=6),
    )

    # ── KPI-Werte (werden von load_report_views() befüllt) ─────────────────
    summary_processed  = ft.Text("–", size=18, weight=ft.FontWeight.W_600, color=MUTED)
    summary_documents  = ft.Text("–", size=18, weight=ft.FontWeight.W_600, color=OK)
    summary_duplicates = ft.Text("–", size=18, weight=ft.FontWeight.W_600, color=ACCENT)
    summary_unklar     = ft.Text("–", size=18, weight=ft.FontWeight.W_600, color=WARN)
    summary_errors     = ft.Text("–", size=18, weight=ft.FontWeight.W_600, color=ERR)
    summary_unmatched  = ft.Text("–", size=18, weight=ft.FontWeight.W_600, color=MUTED)

    # ── Prüffälle ───────────────────────────────────────────────────────────
    prueffaelle_col = ft.Column([], spacing=8)
    pruefbedarf_box = ft.Container(
        visible=False,
        bgcolor=WARN_SOFT,
        border=ft.Border.all(1, WARN_EDGE),
        border_radius=RADIUS_CARD,
        padding=SP_12,
        content=prueffaelle_col,
    )

    # ── Technischer Bericht ─────────────────────────────────────────────────
    report_text = ft.TextField(
        value="",
        multiline=True,
        min_lines=2,
        max_lines=10,
        read_only=True,
        hint_text="Noch kein Lauf – Bericht erscheint hier.",
        text_style=ft.TextStyle(font_family=MONO_FONT, size=10),
        border_color=LINE,
        content_padding=ft.Padding.symmetric(horizontal=8, vertical=6),
    )

    # ── Ausgabeordner-Hinweis (nach Lauf) ──────────────────────────────────
    run_dir_hint = ft.Text(
        "",
        selectable=True,
        font_family=MONO_FONT,
        size=11,
        color=INK_2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    run_dir_row = ft.Container(
        visible=False,
        bgcolor=OK_SOFT,
        border=ft.Border.all(1, OK),
        border_radius=RADIUS_CARD,
        padding=ft.Padding.symmetric(horizontal=SP_12, vertical=SP_8),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=16, color=OK),
                ft.Text("Ausgabeordner:", size=12, color=OK, weight=ft.FontWeight.W_600),
                run_dir_hint,
            ],
            spacing=SP_8,
        ),
    )

    # ── Start-Button (primäre Aktion in der Mittelachse) ─────────────────────
    start_button = ft.ElevatedButton(
        "Verarbeitung starten",
        icon=ft.Icons.ARROW_FORWARD,
        width=CENTER_COL_WIDTH - 8,
        style=ft.ButtonStyle(
            bgcolor=ACCENT,
            color=ft.Colors.WHITE,
            text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_700),
            padding=ft.Padding.symmetric(horizontal=10, vertical=14),
        ),
    )

    # ════════════════════════════════════════════════════════════════════════
    # Hilfsfunktionen (Business-Logik – unverändert)
    # ════════════════════════════════════════════════════════════════════════

    def append_log(line: str) -> None:
        log_output.value = (log_output.value + "\n" + line).strip()
        page.update()

    def set_status(text: str, color: str) -> None:
        status_value.value = text
        status_value.color = color
        palette = _STATUS_BADGE_PALETTE.get(text, (SURFACE_2, LINE, color))
        status_badge.bgcolor = palette[0]
        status_badge.border  = ft.Border.all(1, palette[1])

    def reset_report_view() -> None:
        summary_processed.value  = "–"
        summary_documents.value  = "–"
        summary_duplicates.value = "–"
        summary_unklar.value     = "–"
        summary_errors.value     = "–"
        summary_unmatched.value  = "–"
        pruefbedarf_box.visible  = False
        pruefbedarf_box.bgcolor  = WARN_SOFT
        pruefbedarf_box.border   = ft.Border.all(1, WARN_EDGE)
        prueffaelle_col.controls = []
        report_text.value        = ""
        run_dir_row.visible      = False
        run_dir_hint.value       = ""

    def _show_review_items(items: list[dict]) -> None:
        """Füllt die Prüffälle-Box mit Einzelkarten (aus report.json)."""
        count = len(items)
        count_suffix = "Dokument braucht" if count == 1 else "Dokumente brauchen"
        prueffaelle_col.controls = [
            ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=20, color=WARN),
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
            ft.Text(f"{count} {count_suffix} deine Prüfung.",
                    size=13, weight=ft.FontWeight.W_600, color=WARN),
            ft.Text("Unklare Dokumente", size=12, color=WARN, weight=ft.FontWeight.W_500),
            *[_build_review_item_card(item) for item in items],
        ]
        pruefbedarf_box.bgcolor = WARN_SOFT
        pruefbedarf_box.border  = ft.Border.all(1, WARN_EDGE)
        pruefbedarf_box.visible = True

    def _show_review_empty() -> None:
        """Zeigt eine ruhige Erfolgsmeldung wenn keine Prüffälle vorhanden."""
        prueffaelle_col.controls = [
            ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=16, color=OK),
                    ft.Text("Keine Prüffälle im letzten Lauf.", size=13, color=OK),
                ],
                spacing=6,
            )
        ]
        pruefbedarf_box.bgcolor = OK_SOFT
        pruefbedarf_box.border  = ft.Border.all(1, OK)
        pruefbedarf_box.visible = True

    def _show_review_fallback(txt_content: str) -> None:
        """Fallback: Prüfbedarf-Block aus report.txt extrahieren und anzeigen."""
        pruefbedarf = _extract_pruefbedarf_block(txt_content)
        if pruefbedarf and pruefbedarf != "PRÜFBEDARF: keiner":
            prueffaelle_col.controls = [
                ft.Text("Manuelle Prüfung erforderlich",
                        weight=ft.FontWeight.W_700, size=15, color=WARN),
                ft.Text("Diese Dokumente brauchen deine Prüfung.", size=13, color=WARN),
                ft.Text(pruefbedarf, selectable=True, size=12, font_family=MONO_FONT),
            ]
            pruefbedarf_box.bgcolor = WARN_SOFT
            pruefbedarf_box.border  = ft.Border.all(1, WARN_EDGE)
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

        json_loaded  = False
        review_items: list[dict] = []
        if report_json and report_json.exists():
            try:
                data        = json.loads(report_json.read_text(encoding="utf-8"))
                json_loaded = True
                summary     = data.get("summary", {})
                summary_processed.value  = str(summary.get("processed",    "–"))
                summary_documents.value  = str(summary.get("documents",    "–"))
                summary_duplicates.value = str(summary.get("duplicates",   "–"))
                summary_unklar.value     = str(summary.get("unklar",       "–"))
                summary_errors.value     = str(summary.get("errors",       "–"))
                summary_unmatched.value  = str(summary.get("system_fallbacks", "–"))
                review_items = [
                    f for f in data.get("files", [])
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

    def load_profile_summary() -> None:
        """Lädt Zielordner-Zusammenfassung für den Arbeitsbereich."""
        from invoice_tool.configuration_model import destination_display
        from invoice_tool.profile_editor import load_profile_for_edit, prepare_profile_for_edit
        from invoice_tool.profile_store import load_profile_bundle
        from invoice_tool.target_routing import target_configuration_summary

        active_path = profile_path_ref[0]
        destination_summary_host.controls = []
        if active_path is None or not active_path.exists():
            profile_summary_unmatched.value = "Nicht zugeordnet: nicht konfiguriert"
            profile_summary_unmatched.color = WARN
            return
        try:
            bundle = load_profile_bundle(_active_profile_id())
            prepared = prepare_profile_for_edit(load_profile_for_edit(active_path))
            summary = target_configuration_summary(prepared)
            rows: list[ft.Control] = []
            for config in bundle.configurations:
                if not config.active:
                    continue
                dest_path = config.destination.get("path", "")
                dest = destination_display(dest_path)
                rows.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(vertical=SP_4),
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            config.name,
                                            size=12,
                                            weight=ft.FontWeight.W_600,
                                            width=160,
                                        ),
                                        ft.Text(
                                            dest,
                                            size=12,
                                            color=INK_2,
                                            expand=True,
                                            selectable=True,
                                        ),
                                    ],
                                    spacing=SP_8,
                                ),
                                ft.TextButton(
                                    "Konfiguration öffnen",
                                    icon=ft.Icons.OPEN_IN_NEW,
                                    on_click=lambda _e, cfg_id=config.id: _navigate_to_configuration(cfg_id),
                                    style=ft.ButtonStyle(
                                        color=ACCENT,
                                        padding=ft.Padding.symmetric(horizontal=0, vertical=0),
                                    ),
                                ),
                            ],
                            spacing=0,
                        ),
                    )
                )
            destination_summary_host.controls = rows
            if summary.get("fallback_configured"):
                profile_summary_unmatched.value = (
                    f"Nicht zugeordnet: {summary.get('fallback_display_name') or 'konfiguriert'}"
                )
                profile_summary_unmatched.color = OK
            else:
                profile_summary_unmatched.value = "Nicht zugeordnet: nicht konfiguriert"
                profile_summary_unmatched.color = WARN
        except Exception:  # noqa: BLE001
            profile_summary_unmatched.value = "Nicht zugeordnet: nicht verfügbar"
            profile_summary_unmatched.color = ERR
            destination_summary_host.controls = [
                ft.Text("Zielordner konnten nicht geladen werden.", size=12, color=ERR)
            ]

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
            refresh_source_inventory()
        except (ConfigError, RuntimeError) as exc:
            preset_label.value = f"Fehler: {exc}"
        load_profile_summary()

    def _resolve_technical_output_root() -> Path:
        """Technischer Output-Root für Legacy-Pfade und RUN-001-Artefakte."""
        if output_field.value and output_field.value.strip():
            return Path(output_field.value.strip())
        try:
            app_config = load_app_config(config_path)
            return Path(app_config.ausgangsordner)
        except (ConfigError, RuntimeError):
            from invoice_tool.app_paths import user_support_dir

            fallback = user_support_dir() / "technical-output"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    # ── run_once anbinden ────────────────────────────────────────────────────

    def run_processing() -> None:
        nonlocal run_in_progress, last_run_dir
        try:
            source = Path(source_field.value.strip())
            output = _resolve_technical_output_root()

            append_log(f"[start] source={source}")
            append_log(f"[start] output={output}")
            if profile_path_ref[0]:
                append_log(f"[start] profil={profile_path_ref[0]}")
            else:
                append_log("[start] kein Profil – nur Basis-Regeln")

            run_dir = run_once(
                source=source,
                output=output,
                config_path=config_path,
                profile_path=profile_path_ref[0],
            )
            last_run_dir = run_dir

            report_txt, report_json = _find_report_in_run_dir(run_dir)

            run_in_progress       = False
            set_status("Fertig",  OK)
            start_button.disabled = False
            append_log(f"[fertig] Technischer Run-Ordner: {run_dir}")

            run_dir_hint.value = str(output)
            run_dir_row.visible = True
            page.title = "Lauf abgeschlossen"

            if report_txt:
                load_report_views(report_txt, report_json)
            else:
                report_text.value = ""
            page.update()

        except (RunError, ConfigError) as exc:
            run_in_progress       = False
            set_status("Fehler",  ERR)
            start_button.disabled = False
            append_log(f"[fehler] {exc}")
            page.update()

        except Exception as exc:  # noqa: BLE001
            run_in_progress       = False
            set_status("Fehler",  ERR)
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
        run_in_progress       = True
        log_output.value      = ""
        reset_report_view()
        set_status("Läuft",   ACCENT)
        start_button.disabled = True
        page.update()
        page.run_thread(run_processing)

    def on_open_source(_event: ft.ControlEvent) -> None:
        if source_field.value and source_field.value.strip():
            _open_path(Path(source_field.value.strip()))

    def on_open_output_folder(_event: ft.ControlEvent) -> None:
        if output_field.value and output_field.value.strip():
            _open_path(Path(output_field.value.strip()))
            return
        if last_run_dir is not None:
            mapping_path = last_run_dir / "output_mapping.json"
            if mapping_path.exists():
                _open_path(last_run_dir)

    def on_open_latest_report(_event: ft.ControlEvent) -> None:
        if last_report_txt and last_report_txt.exists():
            _open_path(last_report_txt)

    start_button.on_click = on_start_run

    def _active_profile_id() -> str:
        return resolve_active_profile_id()

    def _on_profile_id_changed(profile_id: str) -> None:
        try:
            set_active_profile_id(profile_id)
        except ValueError:
            return
        for entry_id, path, _ in list_profile_entries():
            if entry_id == profile_id:
                profile_path_ref[0] = path
                _render_shell()
                break

    # ── Arbeitsbereich (Präsentation via ui_workspace) ───────────────────────
    eingang_card = build_folder_card(
        title="Eingang",
        subtitle="Original-PDFs · Die Verarbeitung arbeitet mit Kopien",
        accent=ACCENT,
        soft=ACCENT_SOFT,
        path_field=source_field,
        pick_label="Ordner auswählen",
        on_pick=lambda _event: page.run_task(pick_source_directory, _event),
        on_finder=on_open_source,
        extra_content=ft.Column(
            [
                ft.Divider(height=1, color=LINE),
                source_file_count,
                source_file_list,
            ],
            spacing=SP_8,
        ),
    )

    center_col = build_processing_column(
        start_button=start_button,
        status_badge=status_badge,
        on_open_configurations=lambda: _navigate(NAV_CONFIGURATIONS),
        on_open_latest_report=on_open_latest_report,
    )

    ergebnis_panel = build_ergebnis_panel(
        run_dir_row=run_dir_row,
        pruefbedarf_box=pruefbedarf_box,
        summary_processed=summary_processed,
        summary_documents=summary_documents,
        summary_duplicates=summary_duplicates,
        summary_unklar=summary_unklar,
        summary_errors=summary_errors,
        summary_unmatched=summary_unmatched,
    )

    profile_entries = list_profile_entries()
    profile_controls: list[ft.Control] = [
        ft.Icon(ft.Icons.ACCOUNT_TREE_OUTLINED, size=13, color=MUTED_2),
        ft.Text("Profil:", size=12, color=MUTED_2, weight=ft.FontWeight.W_500),
    ]
    if len(profile_entries) > 1:
        def _on_main_profile_select(profile_id: str) -> None:
            if not profile_id:
                return
            try:
                set_active_profile_id(profile_id)
            except ValueError:
                return
            for entry_id, path, _ in profile_entries:
                if entry_id == profile_id:
                    profile_path_ref[0] = path
                    _render_shell()
                    break

        profile_dropdown = ft.Dropdown(
            value=resolve_active_profile_id(),
            options=[
                ft.dropdown.Option(key=entry_id, text=label)
                for entry_id, _, label in profile_entries
            ],
            on_select=lambda e: _on_main_profile_select(e.control.value or ""),
            width=220,
            dense=True,
            text_size=12,
        )
        profile_selector_ref[0] = profile_dropdown
        profile_controls.append(profile_dropdown)
    else:
        if profile_entries:
            active_label = next(
                (
                    label
                    for entry_id, _, label in profile_entries
                    if entry_id == resolve_active_profile_id()
                ),
                profile_entries[0][2],
            )
            profile_controls.append(ft.Text(active_label, size=12, color=INK_2))
        else:
            profile_controls.append(preset_label)

    config_strip = ft.Container(
        bgcolor=SURFACE_2,
        border=ft.Border.only(bottom=ft.BorderSide(1, LINE)),
        padding=ft.Padding.symmetric(horizontal=SP_24, vertical=SP_8),
        content=ft.Row(
            [
                ft.Row(profile_controls, spacing=SP_8),
                ft.TextButton(
                    "Konfigurationen",
                    icon=ft.Icons.RULE_OUTLINED,
                    on_click=lambda _e: _navigate(NAV_CONFIGURATIONS),
                    style=ft.ButtonStyle(
                        color=ACCENT,
                        padding=ft.Padding.symmetric(horizontal=0, vertical=0),
                    ),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    manual_review_panel = build_manual_review_panel(
        pruefbedarf_box=pruefbedarf_box,
        on_open_review=lambda: _navigate(NAV_REVIEW),
    )

    def _build_workspace_page() -> ft.Container:
        load_profile_summary()
        results_card = build_ergebnisse_card(
            run_dir_row=run_dir_row,
            unmatched_summary=profile_summary_unmatched,
            destination_summary=build_destination_summary_panel(
                configuration_rows=list(destination_summary_host.controls),
                on_open_configurations=lambda: _navigate(NAV_CONFIGURATIONS),
            ),
            on_open_configurations=lambda: _navigate(NAV_CONFIGURATIONS),
        )
        return build_workspace_view(
            profile_strip=config_strip,
            eingang_card=eingang_card,
            center_col=center_col,
            ergebnisse_card=results_card,
            ergebnis_panel=ergebnis_panel,
            manual_review_panel=manual_review_panel,
        )

    def _render_shell() -> None:
        from invoice_tool.ui_configurations import build_configurations_view
        from invoice_tool.ui_profiles import build_profiles_view
        from invoice_tool.ui_review import build_review_view
        from invoice_tool.ui_settings import build_settings_view

        nav = current_nav[0]
        try:
            if nav == NAV_CONFIGURATIONS:
                open_config_id = pending_config_id[0]
                pending_config_id[0] = None
                content = build_configurations_view(
                    page=page,
                    profile_id=_active_profile_id(),
                    on_profile_changed=_on_profile_id_changed,
                    initial_config_id=open_config_id,
                )
            elif nav == NAV_PROFILES:
                content = build_profiles_view(
                    page=page,
                    profile_id=_active_profile_id(),
                    on_open_configurations=lambda: _navigate(NAV_CONFIGURATIONS),
                    on_profiles_changed=_render_shell,
                )
            elif nav == NAV_REVIEW:
                _report_txt, report_json = (
                    _find_report_in_run_dir(last_run_dir) if last_run_dir else (None, None)
                )
                content = build_review_view(last_report_json=report_json)
            elif nav == NAV_SETTINGS:
                content = build_settings_view()
            else:
                content = _build_workspace_page()
        except Exception:  # noqa: BLE001
            logger.exception("Seite konnte nicht geladen werden: %s", nav)
            content = page_error_state(
                "Seite konnte nicht geladen werden",
                "Beim Aufbau dieser Ansicht ist ein Fehler aufgetreten.",
                on_retry=lambda _e, target=nav: _navigate(target),
            )

        active_label = next(
            (label for entry_id, _, label in list_profile_entries() if entry_id == _active_profile_id()),
            "Profil",
        )
        review_badge = summary_unklar.value if summary_unklar.value not in {"–", "0"} else None

        if shell_state[0] is None:
            shell_state[0] = build_app_shell_state(
                active_nav=nav,
                content=content,
                on_navigate=_navigate,
                profile_summary=active_label,
                review_badge=str(review_badge) if review_badge else None,
            )
            page.add(shell_state[0].root)
        else:
            shell_state[0].content_host.content = content
            shell_state[0].update_active_nav(nav)
            shell_state[0].set_profile_summary(active_label)
            shell_state[0].set_review_badge(str(review_badge) if review_badge else None)
        page.update()

    def _navigate(nav_id: str) -> None:
        current_nav[0] = nav_id
        _render_shell()

    def _navigate_to_configuration(config_id: str) -> None:
        pending_config_id[0] = config_id
        _navigate(NAV_CONFIGURATIONS)

    _render_shell()
    load_preset_info()
    page.update()


_ui = build_ui


def main() -> None:
    run = getattr(ft, "run", None) or ft.app
    run(build_ui)


if __name__ == "__main__":
    main()
