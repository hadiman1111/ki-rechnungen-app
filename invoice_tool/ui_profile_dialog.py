from __future__ import annotations

import json
from pathlib import Path

import flet as ft

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
        [ft.Text(f"• {h}", size=12, color=ft.Colors.BLUE_GREY_700) for h in items],
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
# Dokumenttyp-Kachel
# ---------------------------------------------------------------------------


def _build_doc_profile_tile(
    dp: dict,
    folder_label_by_id: dict[str, str],
) -> ft.ExpansionTile:
    """Baut eine ExpansionTile für einen einzelnen document_profile-Eintrag.

    Korrekturen gegenüber dem ursprünglichen gui.py-Code:
    a) dp.get("description") wird oben in den detail_controls angezeigt,
       unterhalb von Bezeichnung/Badge, vor der technischen ID.
    b) confidence_threshold None/fehlend → "0,5 (Standard)" statt "–".
    c) _hints_col ist jetzt Modul-Funktion statt Loop-Closure.
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
) -> ft.Column:
    """Erstellt den Inhalt des read-only Profildetail-Dialogs.

    Parameters
    ----------
    profile_path:
        Pfad zur profile_config.local.json oder None, falls nicht gefunden.
    preset_label_value:
        Anzeigetext des aktiven Presets (z. B. aus rules.active_preset).
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
            rows.append(_build_doc_profile_tile(dp, folder_label_by_id))

    return ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO)


# ---------------------------------------------------------------------------
# Öffentliche API
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
    content = _build_profile_dialog_content(profile_path, preset_label)
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
