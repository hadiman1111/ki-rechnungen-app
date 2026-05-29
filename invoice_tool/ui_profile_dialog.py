from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import flet as ft

from invoice_tool.profile_editor import (
    ProfileEditorError,
    hints_from_textarea,
    load_profile_for_edit,
    save_profile_atomic,
    update_document_profile,
    validate_profile_for_save,
)

# Menschenlesbare Bezeichnungen für document_type-Schlüssel aus dem Profil-JSON.
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


# ---------------------------------------------------------------------------
# Primitive Hilfsfunktionen (Modul-Ebene)
# ---------------------------------------------------------------------------


def _label_row(label: str, value: str, mono: bool = False) -> ft.Row:
    """Zweispaltige Zeile: Beschriftung links, selektierbarer Wert rechts."""
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
    """Abschnittsüberschrift im Dialog."""
    return ft.Text(
        title,
        size=14,
        weight=ft.FontWeight.W_600,
        color=ft.Colors.BLUE_GREY_700,
    )


def _hints_col(items: list) -> ft.Column:
    """Aufzählungsspalte für Erkennungs- oder Ausschlusshinweise."""
    return ft.Column(
        [
            ft.Text(f"• {h}", size=12, color=ft.Colors.BLUE_GREY_700, selectable=True)
            for h in items
        ],
        spacing=1,
        expand=True,
    )


# ---------------------------------------------------------------------------
# JSON-Lesehelfer (rein, keine Seiteneffekte)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Einfacher Fehler-Dialog (intern)
# ---------------------------------------------------------------------------


def _open_simple_error_dialog(page: ft.Page, title: str, message: str) -> None:
    """Zeigt einen modalen Fehlerdialog mit Schließen-Button."""
    dlg_ref: list[ft.AlertDialog | None] = [None]

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_700),
                ft.Text(title, weight=ft.FontWeight.W_600),
            ],
            spacing=8,
        ),
        content=ft.Text(message, size=13, selectable=True),
        actions=[
            ft.TextButton("Schließen", on_click=lambda _: page.close(dlg_ref[0]))
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dlg_ref[0] = dlg
    page.open(dlg)


# ---------------------------------------------------------------------------
# Dokumenttyp-Kachel
# ---------------------------------------------------------------------------


def _build_doc_profile_tile(
    dp: dict,
    folder_label_by_id: dict[str, str],
    on_edit: Callable[[], None] | None = None,
) -> ft.ExpansionTile:
    """Baut eine ExpansionTile für einen einzelnen document_profile-Eintrag.

    Korrekturen gegenüber dem ursprünglichen gui.py-Code:
    a) dp.get("description") wird oben in den detail_controls angezeigt,
       unterhalb von Bezeichnung/Badge, vor der technischen ID.
    b) confidence_threshold None/fehlend → "0,5 (Standard)" statt "–".
    c) _hints_col ist jetzt Modul-Funktion statt Loop-Closure.

    Phase 2b: on_edit-Callback ergänzt. Wenn gesetzt und dp hat gültige id,
    erscheint ein "Bearbeiten"-Button am Anfang der aufgeklappten Detailansicht.
    """
    dp_id = dp.get("id", "–")
    dp_label = dp.get("label", dp_id)
    dp_description = dp.get("description", "")
    enabled_val = dp.get("enabled", True)

    # Correction b: None/fehlend → "0,5 (Standard)"
    threshold = dp.get("confidence_threshold")
    threshold_str = f"{threshold}" if threshold is not None else "0,5 (Standard)"

    target_fid = str(dp.get("target_folder_id") or "")
    fallback_fid = str(dp.get("fallback_folder_id") or "")
    target_label = folder_label_by_id.get(target_fid, target_fid or "–")
    fallback_label = folder_label_by_id.get(fallback_fid, fallback_fid or "–")

    classification_hints: list = dp.get("classification_hints") or []
    negative_hints: list = dp.get("negative_hints") or []
    naming: dict = dp.get("naming_schema") or {}
    duplicate_policy = dp.get("duplicate_policy") or ""
    required_fields: list = dp.get("required_fields") or []
    optional_fields: list = dp.get("optional_fields") or []
    ui_help_text = dp.get("ui_help_text") or ""

    # Aktiv/Inaktiv-Badge
    if enabled_val is False:
        enabled_badge = ft.Container(
            content=ft.Text(
                "Inaktiv",
                size=11,
                color=ft.Colors.BLUE_GREY_600,
                weight=ft.FontWeight.W_600,
            ),
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_300),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=8, vertical=2),
        )
    else:
        enabled_badge = ft.Container(
            content=ft.Text(
                "Aktiv",
                size=11,
                color=ft.Colors.GREEN_700,
                weight=ft.FontWeight.W_600,
            ),
            bgcolor=ft.Colors.GREEN_50,
            border=ft.border.all(1, ft.Colors.GREEN_200),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=8, vertical=2),
        )

    detail_controls: list[ft.Control] = []

    # Phase 2b: "Bearbeiten"-Button nur wenn Callback gesetzt, id gültig und kein invoice-Typ
    if on_edit is not None and dp_id and dp_id != "–" and dp.get("document_type") != "invoice":
        detail_controls.append(
            ft.Row(
                [
                    ft.TextButton(
                        "Bearbeiten",
                        icon=ft.Icons.EDIT_OUTLINED,
                        on_click=lambda _: on_edit(),
                        style=ft.ButtonStyle(color=ft.Colors.BLUE_700),
                    )
                ],
                alignment=ft.MainAxisAlignment.END,
            )
        )

    # Correction a: Beschreibung oben, vor technischer ID
    if dp_description:
        detail_controls.append(
            ft.Row(
                [
                    ft.Text(
                        "Beschreibung:",
                        weight=ft.FontWeight.W_600,
                        size=12,
                        width=160,
                    ),
                    ft.Text(
                        dp_description,
                        size=12,
                        color=ft.Colors.BLUE_GREY_600,
                        expand=True,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )

    detail_controls += [
        _label_row("ID:", dp_id, mono=True),
        _label_row(
            "Dokumenttyp:",
            _DOC_TYPE_LABELS.get(dp.get("document_type", ""), dp.get("document_type", "–")),
        ),
        _label_row("Zielordner:", target_label),
        _label_row("Fallback-Ordner:", fallback_label),
        _label_row("Konfidenzgrenze:", threshold_str),
    ]

    if duplicate_policy:
        detail_controls.append(_label_row("Duplikat-Policy:", duplicate_policy))

    # Correction c: _hints_col ist Modul-Funktion, kein Loop-Closure
    if classification_hints:
        detail_controls.append(
            ft.Row(
                [
                    ft.Text(
                        "Erkennungshinweise:",
                        weight=ft.FontWeight.W_600,
                        size=12,
                        width=160,
                    ),
                    _hints_col(classification_hints),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )

    if negative_hints:
        detail_controls.append(
            ft.Row(
                [
                    ft.Text(
                        "Ausschlusshinweise:",
                        weight=ft.FontWeight.W_600,
                        size=12,
                        width=160,
                    ),
                    _hints_col(negative_hints),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )

    # Dateinamensschema
    naming_template = naming.get("template", "")
    naming_type_literal = naming.get("type_literal", "")
    naming_fallback = naming.get("fallback_values") or {}
    if naming_template or naming_type_literal or naming_fallback:
        schema_rows: list[ft.Control] = [
            ft.Text(
                "Dateinamensschema",
                size=12,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.BLUE_GREY_700,
            ),
        ]
        if naming_template:
            schema_rows.append(_label_row("Vorlage:", naming_template, mono=True))
        if naming_type_literal:
            schema_rows.append(_label_row("Typ-Literal:", naming_type_literal, mono=True))
        for k, v in naming_fallback.items():
            schema_rows.append(_label_row(f"  {k}:", str(v), mono=True))
        detail_controls.append(
            ft.Container(
                bgcolor=ft.Colors.BLUE_GREY_50,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=4,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                content=ft.Column(schema_rows, spacing=2),
            )
        )

    if required_fields:
        detail_controls.append(
            ft.Row(
                [
                    ft.Text(
                        "Prüfregeln (Pflicht):",
                        weight=ft.FontWeight.W_600,
                        size=12,
                        width=160,
                    ),
                    ft.Text(
                        ", ".join(str(f) for f in required_fields),
                        size=12,
                        expand=True,
                        selectable=True,
                        font_family="Courier New",
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )

    if optional_fields:
        detail_controls.append(
            ft.Row(
                [
                    ft.Text(
                        "Prüfregeln (Optional):",
                        weight=ft.FontWeight.W_600,
                        size=12,
                        width=160,
                    ),
                    ft.Text(
                        ", ".join(str(f) for f in optional_fields),
                        size=12,
                        expand=True,
                        selectable=True,
                        font_family="Courier New",
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )

    if ui_help_text:
        detail_controls.append(
            ft.Row(
                [
                    ft.Text("Hilfetext:", weight=ft.FontWeight.W_600, size=12, width=160),
                    ft.Text(
                        ui_help_text,
                        size=12,
                        color=ft.Colors.BLUE_GREY_600,
                        italic=True,
                        expand=True,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )

    return ft.ExpansionTile(
        title=ft.Row(
            [ft.Text(dp_label, size=13, weight=ft.FontWeight.W_600), enabled_badge],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        subtitle=ft.Text(
            _DOC_TYPE_LABELS.get(dp.get("document_type", ""), dp.get("document_type", "")),
            size=11,
            color=ft.Colors.BLUE_GREY_500,
        ),
        controls=detail_controls,
        initially_expanded=False,
        tile_padding=ft.padding.symmetric(horizontal=8, vertical=2),
    )


# ---------------------------------------------------------------------------
# Dialog-Inhalt
# ---------------------------------------------------------------------------


def _build_profile_dialog_content(
    profile_path: Path | None,
    preset_label_value: str,
    on_edit: Callable[[str], None] | None = None,
) -> ft.Column:
    """Erstellt den Inhalt des read-only Profildetail-Dialogs.

    Parameters
    ----------
    profile_path:
        Pfad zur profile_config.local.json oder None, falls nicht gefunden.
    preset_label_value:
        Anzeigetext des aktiven Presets (z. B. aus rules.active_preset).
    on_edit:
        Optionaler Callback (dp_id: str) → None. Wenn gesetzt und Profil
        erfolgreich geladen, erscheint pro document_profile ein
        "Bearbeiten"-Button. Phase 2b.
    """
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
    rows.append(_label_row("Aktives Preset:", preset_label_value or "–"))

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
        str(f.get("id", "")): str(
            f.get("label") or f.get("folder_name") or f.get("id") or "–"
        )
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
                        ft.Icon(
                            ft.Icons.FOLDER_OUTLINED,
                            size=14,
                            color=ft.Colors.BLUE_GREY_400,
                        ),
                        ft.Text(f_label, size=13, width=240),
                        ft.Text(
                            f_name,
                            size=12,
                            font_family="Courier New",
                            color=ft.Colors.BLUE_GREY_600,
                            selectable=True,
                        ),
                    ],
                    spacing=6,
                )
            )
    else:
        rows.append(
            ft.Text("Keine Ordner konfiguriert.", size=13, color=ft.Colors.BLUE_GREY_500)
        )

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
            dp_id = dp.get("id") if isinstance(dp, dict) else None
            # Phase 2b: Bearbeiten-Callback nur wenn on_edit gesetzt, id gültig und kein invoice-Typ
            if on_edit is not None and dp_id and dp.get("document_type") != "invoice":
                tile_on_edit: Callable[[], None] | None = (
                    lambda did: lambda: on_edit(did)
                )(dp_id)
            else:
                tile_on_edit = None
            rows.append(_build_doc_profile_tile(dp, folder_label_by_id, on_edit=tile_on_edit))

    return ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO)


# ---------------------------------------------------------------------------
# Öffentliche API – read-only Dialog
# ---------------------------------------------------------------------------


def show_profile_details_dialog(
    page: ft.Page,
    profile_path: Path | None,
    preset_label: str,
) -> None:
    """Öffnet den read-only Profildetail-Dialog.

    Parameters
    ----------
    page:
        Das aktive Flet-Page-Objekt (für page.open/page.close).
    profile_path:
        Pfad zur profile_config.local.json oder None, wenn nicht gefunden.
    preset_label:
        Anzeigetext des aktiven Presets (z. B. aus rules.active_preset).
    """
    dialog_ref: list[ft.AlertDialog | None] = [None]

    # Phase 2b: Bearbeiten-Callback – schließt Read-only-Dialog, öffnet Edit-Dialog.
    # on_saved öffnet den Read-only-Dialog nach erfolgreichem Speichern neu.
    def _on_edit_dp(dp_id: str) -> None:
        if dialog_ref[0] is not None:
            page.close(dialog_ref[0])
        show_edit_document_profile_dialog(
            page,
            profile_path,  # type: ignore[arg-type]
            dp_id,
            on_saved=lambda: show_profile_details_dialog(page, profile_path, preset_label),
        )

    # Bearbeiten nur anbieten wenn profile_path vorhanden (Datei existiert/ladbar).
    on_edit_fn: Callable[[str], None] | None = _on_edit_dp if profile_path else None

    content = _build_profile_dialog_content(profile_path, preset_label, on_edit=on_edit_fn)
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
            width=920,
            height=780,
        ),
        actions=[
            ft.TextButton(
                "Schließen",
                on_click=lambda _: page.close(dialog),
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dialog_ref[0] = dialog
    page.open(dialog)


# ---------------------------------------------------------------------------
# Öffentliche API – Bearbeitungs-Dialog (Phase 2b)
# ---------------------------------------------------------------------------


def show_edit_document_profile_dialog(
    page: ft.Page,
    profile_path: Path,
    profile_id: str,
    on_saved: Callable[[], None] | None = None,
) -> None:
    """Öffnet den Bearbeitungsdialog für einen document_profile-Eintrag.

    Bearbeitbare Felder (Phase 2b):
        label, enabled, document_type, target_folder_id,
        fallback_folder_id, confidence_threshold,
        classification_hints, negative_hints

    Alle Schreibvorgänge laufen ausschließlich über save_profile_atomic().
    Alle Mutationen laufen über update_document_profile().

    Parameters
    ----------
    page:
        Das aktive Flet-Page-Objekt.
    profile_path:
        Pfad zur profile_config.local.json (darf nicht None sein).
    profile_id:
        id-Wert des zu bearbeitenden document_profile-Eintrags.
    on_saved:
        Optionaler Callback nach erfolgreichem Speichern (z. B. Dialog
        neu öffnen). Wird aufgerufen nachdem der Edit-Dialog geschlossen
        wurde.
    """
    # ------------------------------------------------------------------ #
    #  1. Profil laden                                                     #
    # ------------------------------------------------------------------ #
    try:
        profile = load_profile_for_edit(profile_path)
    except ProfileEditorError as exc:
        _open_simple_error_dialog(page, "Profil konnte nicht geladen werden", str(exc))
        return

    # ------------------------------------------------------------------ #
    #  2. Eintrag suchen                                                   #
    # ------------------------------------------------------------------ #
    dps: list[dict] = [
        p for p in (profile.get("document_profiles") or []) if isinstance(p, dict)
    ]
    dp = next((p for p in dps if p.get("id") == profile_id), None)
    if dp is None:
        _open_simple_error_dialog(
            page,
            "Dokumentprofil nicht gefunden",
            f"Kein Eintrag mit ID '{profile_id}' in der Profildatei gefunden.",
        )
        return

    # ------------------------------------------------------------------ #
    #  3. Ordner-Optionen                                                  #
    # ------------------------------------------------------------------ #
    folders = [f for f in (profile.get("folders") or []) if isinstance(f, dict)]
    folder_label_by_id: dict[str, str] = {
        str(f.get("id", "")): str(
            f.get("label") or f.get("folder_name") or f.get("id") or "–"
        )
        for f in folders
    }
    folder_opts = [
        ft.dropdown.Option(key=str(f["id"]), text=folder_label_by_id[str(f["id"])])
        for f in folders
        if f.get("id")
    ]
    folder_opts_with_empty = [ft.dropdown.Option(key="", text="– kein –")] + folder_opts

    # ------------------------------------------------------------------ #
    #  4. Zustandsverfolgung                                               #
    # ------------------------------------------------------------------ #
    dirty: list[bool] = [False]
    dialog_ref: list[ft.AlertDialog | None] = [None]

    def _mark_dirty(_: ft.ControlEvent | None = None) -> None:
        dirty[0] = True

    # ------------------------------------------------------------------ #
    #  5. Formular-Controls                                                #
    # ------------------------------------------------------------------ #
    tf_label = ft.TextField(
        label="Bezeichnung *",
        value=dp.get("label", ""),
        expand=True,
        on_change=_mark_dirty,
    )

    sw_enabled = ft.Switch(
        label="Aktiv",
        value=bool(dp.get("enabled", True)),
        on_change=_mark_dirty,
    )

    doc_type_opts = [
        ft.dropdown.Option(key=k, text=v)
        for k, v in _DOC_TYPE_LABELS.items()
        if k != "invoice"
    ]
    dd_doc_type = ft.Dropdown(
        label="Dokumenttyp",
        value=dp.get("document_type") or None,
        options=doc_type_opts,
        expand=True,
        on_change=_mark_dirty,
    )

    current_target = str(dp.get("target_folder_id") or "")
    dd_target = ft.Dropdown(
        label="Zielordner",
        value=current_target if current_target else None,
        options=folder_opts,
        expand=True,
        on_change=_mark_dirty,
    )

    current_fallback = str(dp.get("fallback_folder_id") or "")
    dd_fallback = ft.Dropdown(
        label="Fallback-Ordner (optional)",
        value=current_fallback if current_fallback else "",
        options=folder_opts_with_empty,
        expand=True,
        on_change=_mark_dirty,
    )

    threshold_raw = dp.get("confidence_threshold")
    tf_threshold = ft.TextField(
        label="Konfidenzgrenze (0.0 – 1.0)",
        value=str(threshold_raw) if threshold_raw is not None else "",
        hint_text="leer = Standard (0,5)  ·  Komma oder Punkt möglich",
        expand=True,
        on_change=_mark_dirty,
    )

    tf_class_hints = ft.TextField(
        label="Erkennungshinweise (eine je Zeile)",
        value="\n".join(dp.get("classification_hints") or []),
        multiline=True,
        min_lines=3,
        max_lines=6,
        expand=True,
        on_change=_mark_dirty,
    )

    tf_neg_hints = ft.TextField(
        label="Ausschlusshinweise (eine je Zeile)",
        value="\n".join(dp.get("negative_hints") or []),
        multiline=True,
        min_lines=3,
        max_lines=6,
        expand=True,
        on_change=_mark_dirty,
    )

    # Inline-Fehleranzeige
    err_text = ft.Text("", color=ft.Colors.RED_700, size=12, selectable=True)
    err_container = ft.Container(
        content=err_text,
        bgcolor=ft.Colors.RED_50,
        border=ft.border.all(1, ft.Colors.RED_200),
        border_radius=6,
        padding=8,
        visible=False,
    )

    def _show_err(msg: str) -> None:
        err_text.value = msg
        err_container.visible = True
        page.update()

    def _clear_err() -> None:
        err_container.visible = False
        page.update()

    # ------------------------------------------------------------------ #
    #  6. Nur-lesen-Abschnitt                                              #
    # ------------------------------------------------------------------ #
    naming: dict = dp.get("naming_schema") or {}
    naming_template = naming.get("template") or "–"
    dup_policy = dp.get("duplicate_policy") or "–"
    req_fields: list = dp.get("required_fields") or []
    opt_fields: list = dp.get("optional_fields") or []

    ro_rows: list[ft.Control] = [
        ft.Text(
            "Dateinamensschema und weitere Felder sind in dieser Version nur lesend.",
            size=12,
            color=ft.Colors.BLUE_GREY_600,
            italic=True,
        ),
        _label_row("ID:", profile_id, mono=True),
        _label_row("Namensschema:", naming_template, mono=True),
        _label_row("Duplikat-Policy:", dup_policy),
    ]
    if req_fields:
        ro_rows.append(
            _label_row("Pflichtfelder:", ", ".join(str(f) for f in req_fields))
        )
    if opt_fields:
        ro_rows.append(
            _label_row("Optionale Felder:", ", ".join(str(f) for f in opt_fields))
        )

    ro_section = ft.Container(
        bgcolor=ft.Colors.BLUE_GREY_50,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        content=ft.Column(ro_rows, spacing=3),
    )

    # ------------------------------------------------------------------ #
    #  7. Dialog-Inhalt zusammenbauen                                      #
    # ------------------------------------------------------------------ #
    dialog_content = ft.Column(
        [
            # Warnhinweis: Änderungen wirken ab dem nächsten Lauf
            ft.Container(
                bgcolor=ft.Colors.AMBER_50,
                border=ft.border.all(1, ft.Colors.AMBER_200),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.WARNING_AMBER_OUTLINED,
                            size=15,
                            color=ft.Colors.AMBER_700,
                        ),
                        ft.Text(
                            "Änderungen wirken ab dem nächsten Lauf.",
                            color=ft.Colors.AMBER_700,
                            size=12,
                        ),
                    ],
                    spacing=6,
                ),
            ),
            # Nur-lesen-Abschnitt
            ro_section,
            ft.Divider(height=4),
            _section("Bearbeitbare Felder"),
            tf_label,
            sw_enabled,
            dd_doc_type,
            ft.Row([dd_target, dd_fallback], spacing=8),
            tf_threshold,
            ft.Divider(height=4),
            _section("Hinweise"),
            tf_class_hints,
            tf_neg_hints,
            ft.Divider(height=4),
            err_container,
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
    )

    # ------------------------------------------------------------------ #
    #  8. Speichern-Logik                                                  #
    # ------------------------------------------------------------------ #
    def do_save(_: ft.ControlEvent) -> None:
        _clear_err()
        patch: dict = {}

        # label
        label_val = (tf_label.value or "").strip()
        if not label_val:
            _show_err("Bezeichnung darf nicht leer sein.")
            return
        patch["label"] = label_val

        # enabled
        patch["enabled"] = bool(sw_enabled.value)

        # document_type
        doc_type_val = dd_doc_type.value or ""
        if not doc_type_val:
            _show_err("Bitte einen Dokumenttyp auswählen.")
            return
        patch["document_type"] = doc_type_val

        # target_folder_id: leerer String → None
        patch["target_folder_id"] = dd_target.value or None

        # fallback_folder_id: leerer String (= "– kein –") → None
        fallback_val = dd_fallback.value or ""
        patch["fallback_folder_id"] = fallback_val if fallback_val else None

        # confidence_threshold: leer → None, sonst float
        thresh_str = (tf_threshold.value or "").strip().replace(",", ".")
        if thresh_str:
            try:
                thresh_float = float(thresh_str)
            except ValueError:
                _show_err("Konfidenzgrenze: Ungültige Zahl (z. B. 0.7 oder 0,7).")
                return
            if not (0.0 <= thresh_float <= 1.0):
                _show_err(
                    f"Konfidenzgrenze muss zwischen 0.0 und 1.0 liegen (eingegeben: {thresh_float})."
                )
                return
            patch["confidence_threshold"] = thresh_float
        else:
            patch["confidence_threshold"] = None

        # hints
        patch["classification_hints"] = hints_from_textarea(tf_class_hints.value or "")
        patch["negative_hints"] = hints_from_textarea(tf_neg_hints.value or "")

        # Patch anwenden
        try:
            updated = update_document_profile(profile, profile_id, patch)
        except ProfileEditorError as exc:
            _show_err(f"Patch-Fehler: {exc}")
            return

        # Validieren
        val_errors = validate_profile_for_save(updated)
        if val_errors:
            _show_err(
                "Validierungsfehler:\n" + "\n".join(f"• {e}" for e in val_errors)
            )
            return

        # Atomar speichern
        try:
            backup_path = save_profile_atomic(profile_path, updated)
        except ProfileEditorError as exc:
            _show_err(f"Speichern fehlgeschlagen:\n{exc}")
            return

        # Erfolg: Dialog schließen, Meldung anzeigen, Callback aufrufen
        if dialog_ref[0] is not None:
            page.close(dialog_ref[0])

        page.open(
            ft.SnackBar(
                content=ft.Text(
                    f"Gespeichert. Backup: {backup_path.name}",
                    selectable=True,
                ),
                duration=4000,
            )
        )

        if on_saved is not None:
            on_saved()

    # ------------------------------------------------------------------ #
    #  9. Abbrechen-Logik                                                  #
    # ------------------------------------------------------------------ #
    def do_cancel(_: ft.ControlEvent) -> None:
        if not dirty[0]:
            if dialog_ref[0] is not None:
                page.close(dialog_ref[0])
            return

        # Änderungen vorhanden: Bestätigungsdialog anzeigen
        confirm_ref: list[ft.AlertDialog | None] = [None]

        def _confirm_discard(_: ft.ControlEvent) -> None:
            if confirm_ref[0] is not None:
                page.close(confirm_ref[0])
            if dialog_ref[0] is not None:
                page.close(dialog_ref[0])

        def _cancel_discard(_: ft.ControlEvent) -> None:
            if confirm_ref[0] is not None:
                page.close(confirm_ref[0])

        confirm_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Änderungen verwerfen?", weight=ft.FontWeight.W_600),
            content=ft.Text(
                "Die eingegebenen Änderungen werden nicht gespeichert.",
                size=13,
            ),
            actions=[
                ft.TextButton("Weiter bearbeiten", on_click=_cancel_discard),
                ft.FilledButton(
                    "Verwerfen",
                    on_click=_confirm_discard,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        confirm_ref[0] = confirm_dlg
        page.open(confirm_dlg)

    # ------------------------------------------------------------------ #
    #  10. Dialog öffnen                                                   #
    # ------------------------------------------------------------------ #
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.EDIT_OUTLINED, color=ft.Colors.BLUE_700),
                ft.Text(
                    "Dokumentprofil bearbeiten",
                    weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=8,
        ),
        content=ft.Container(
            content=dialog_content,
            width=920,
            height=720,
        ),
        actions=[
            ft.TextButton("Abbrechen", on_click=do_cancel),
            ft.FilledButton("Speichern", on_click=do_save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    dialog_ref[0] = dialog
    page.open(dialog)
