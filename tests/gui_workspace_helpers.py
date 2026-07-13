"""Hilfsfunktionen zum Prüfen der sichtbaren Workspace-Struktur in build_ui()."""

from __future__ import annotations

from typing import Any, Iterable

from invoice_tool.ui_tokens import CENTER_COL_WIDTH, FOLDER_CARD_RADIUS, SURFACE, SURFACE_2


def iter_controls(root: Any) -> Iterable[Any]:
    if root is None:
        return
    yield root

    content = getattr(root, "content", None)
    if content is not None:
        if isinstance(content, list):
            for item in content:
                yield from iter_controls(item)
        else:
            yield from iter_controls(content)

    controls = getattr(root, "controls", None)
    if controls:
        for item in controls:
            yield from iter_controls(item)


def control_label(control: Any) -> str | None:
    if control.__class__.__name__ == "Text":
        value = getattr(control, "value", None)
        if isinstance(value, str) and value:
            return value

    if control.__class__.__name__ == "ListTile":
        title = getattr(control, "title", None)
        title_label = control_label(title)
        if title_label:
            return title_label

    content = getattr(control, "content", None)
    if isinstance(content, str) and content:
        return content
    return None


def collect_labels(root: Any) -> set[str]:
    labels: set[str] = set()
    for control in iter_controls(root):
        label = control_label(control)
        if label:
            labels.add(label)
    return labels


def find_controls_by_label(root: Any, label: str) -> list[Any]:
    return [
        control
        for control in iter_controls(root)
        if control_label(control) == label
    ]


def _border_radius_top_pair(control: Any) -> tuple[Any, Any] | None:
    border_radius = getattr(control, "border_radius", None)
    if border_radius is None:
        return None
    if isinstance(border_radius, (int, float)):
        return (border_radius, border_radius)
    top_left = getattr(border_radius, "top_left", None)
    top_right = getattr(border_radius, "top_right", None)
    if top_left is None or top_right is None:
        return None
    return (top_left, top_right)


def _find_folder_cards(root: Any) -> list[Any]:
    return [
        control
        for control in iter_controls(root)
        if control.__class__.__name__ == "Container"
        and getattr(control, "clip_behavior", None) is not None
        and getattr(control, "border_radius", None) == FOLDER_CARD_RADIUS
    ]


def _find_center_column(root: Any) -> Any | None:
    for control in iter_controls(root):
        if control.__class__.__name__ == "Container" and getattr(control, "width", None) == CENTER_COL_WIDTH:
            return control
    return None


def _assert_no_simulated_traffic_lights(root: Any) -> None:
    traffic_light_colors = {"#ff5f57", "#febc2e", "#28c840"}
    for control in iter_controls(root):
        if control.__class__.__name__ != "Container":
            continue
        bgcolor = getattr(control, "bgcolor", None)
        if bgcolor in traffic_light_colors:
            raise AssertionError("Simulierte Traffic-Light-Titelleiste ist noch im UI vorhanden")


def assert_workspace_present(page_controls: list[Any]) -> dict[str, Any]:
    assert page_controls, "build_ui sollte mindestens ein Root-Control hinzufügen"

    root = page_controls[-1]
    labels = collect_labels(root)

    required_labels = {
        "Eingang",
        "Ergebnisse",
        "Verarbeitung",
        "Verarbeitung starten",
        "Ordner auswählen",
        "Arbeitsbereich",
        "Konfigurationen",
    }
    missing = required_labels - labels
    assert not missing, f"Workspace-Labels fehlen: {sorted(missing)}"

    added_types = {type(control).__name__ for control in page_controls}
    assert "FilePicker" not in added_types, (
        "FilePicker ist ein Service und darf nicht via page.add() sichtbar gemountet werden"
    )

    read_only_path_fields = [
        control
        for control in iter_controls(root)
        if control.__class__.__name__ == "TextField"
        and getattr(control, "read_only", False)
        and control_label(control) is None
    ]
    assert len(read_only_path_fields) >= 1, (
        "Eingangspfad sollte als read-only TextField vorhanden sein"
    )

    pick_buttons = find_controls_by_label(root, "Ordner auswählen")
    assert len(pick_buttons) >= 1, "Eingang braucht einen Ordner-auswählen-Button"

    start_buttons = find_controls_by_label(root, "Verarbeitung starten")
    assert start_buttons, "Verarbeitungs-Startbutton fehlt"
    assert start_buttons[0].on_click is not None

    return {
        "root": root,
        "labels": labels,
        "pick_buttons": pick_buttons,
        "read_only_path_fields": read_only_path_fields,
        "start_buttons": start_buttons,
    }


def assert_layout_regressions_fixed(page_controls: list[Any]) -> None:
    root = page_controls[-1]
    labels = collect_labels(root)

    assert "KI-Rechnungen UI gestartet" not in labels
    assert "lokal · keine Cloud" not in labels

    _assert_no_simulated_traffic_lights(root)

    assert getattr(root, "expand", False) is True, "App-Shell soll expand=True für responsive Breite nutzen"
    assert getattr(root, "width", None) in (None, 0), "App-Shell soll keine feste Breite mehr haben"

    folder_cards = _find_folder_cards(root)
    assert len(folder_cards) >= 2, "Eingangs- und Zielordner-Karte brauchen clip_behavior am Container"

    for card in folder_cards:
        column = getattr(card, "content", None)
        assert column is not None and column.__class__.__name__ == "Column", (
            "Ordnerkarte erwartet Column als direkten Inhalt"
        )
        controls = getattr(column, "controls", None) or []
        assert controls, "Ordnerkarte braucht einen farbigen Kopfbereich"
        header = controls[0]
        assert header.__class__.__name__ == "Container", "Ordnerkopf muss ein Container sein"
        header_top = _border_radius_top_pair(header)
        assert header_top == (FOLDER_CARD_RADIUS, FOLDER_CARD_RADIUS), (
            "Ordnerkopf braucht passende obere Eckenradien"
        )
        assert getattr(header, "bgcolor", None) not in (None, "transparent"), (
            "Ordnerkopf braucht einen farbigen Hintergrund ohne separate Rechteck-Schicht"
        )

    start_button = find_controls_by_label(root, "Verarbeitung starten")[0]
    button_width = getattr(start_button, "width", None)
    assert button_width is None or button_width >= 180, (
        "Verarbeitung-starten-Button braucht genug Breite für eine Zeile"
    )
    assert getattr(start_button, "icon", None) is not None, (
        "Verarbeitung-starten-Button braucht ein integriertes Icon"
    )

    center_col = _find_center_column(root)
    assert center_col is not None, "Mittelachse mit fester Breite fehlt"
    center_content = getattr(center_col, "content", None)
    assert center_content is not None and center_content.__class__.__name__ == "Column"
    direct_controls = getattr(center_content, "controls", None) or []
    standalone_icons = [
        control for control in direct_controls if control.__class__.__name__ == "Icon"
    ]
    assert not standalone_icons, (
        "Pfeil-Icon darf nicht als separates Control über dem Startbutton stehen"
    )


def assert_document_rules_layout(rules_root: Any) -> None:
    labels = collect_labels(rules_root)

    assert "Verarbeitung einrichten" in labels
    assert "← Arbeitsbereich" in labels
    assert "Allgemeine Regeln" in labels
    assert "Zuordnung testen" in labels
    assert "Zielordner" in labels
    assert "Wenn keine Zuordnung möglich ist" in labels
    assert "lokal · keine Cloud" not in labels
    assert "Globale Dokumentregeln" not in labels
    assert "Routing-Vorschau" not in labels

    _assert_no_simulated_traffic_lights(rules_root)

    assert getattr(rules_root, "expand", False) is True, (
        "Rules-View-Root soll expand=True für responsive Breite nutzen"
    )
    assert getattr(rules_root, "width", None) in (None, 0), (
        "Rules-View-Root soll keine feste Breite mehr haben"
    )

    nav_strip_candidates = [
        control
        for control in iter_controls(rules_root)
        if control.__class__.__name__ == "Container"
        and getattr(control, "height", None) == 50
        and getattr(control, "bgcolor", None) == SURFACE_2
    ]
    assert not nav_strip_candidates, (
        "Rules-View darf keine zweite Vollbreiten-Navigationsleiste unter der Titelleiste haben"
    )

    scroll_columns = [
        control
        for control in iter_controls(rules_root)
        if control.__class__.__name__ == "Column"
        and getattr(control, "scroll", None) is not None
    ]
    assert scroll_columns, "Konfigurationsansicht soll eine scrollbare Hauptspalte haben"

    back_buttons = find_controls_by_label(rules_root, "← Arbeitsbereich")
    assert back_buttons, "Zurück-Navigation in der Rules-View fehlt"
    assert back_buttons[0].on_click is not None


def _collect_tab_texts(root: Any) -> set[str]:
    texts: set[str] = set()
    for control in iter_controls(root):
        if control.__class__.__name__ == "Tab":
            text = getattr(control, "text", None)
            if isinstance(text, str) and text:
                texts.add(text)
        if control.__class__.__name__ == "Tabs":
            for tab in getattr(control, "tabs", None) or []:
                text = getattr(tab, "text", None)
                if isinstance(text, str) and text:
                    texts.add(text)
    return texts


def _label_positions(root: Any, label: str) -> list[int]:
    positions: list[int] = []
    for index, control in enumerate(iter_controls(root)):
        if control_label(control) == label:
            positions.append(index)
    return positions


def assert_navigation_shell(root: Any) -> None:
    labels = collect_labels(root)
    for label in ("Arbeitsbereich", "Konfigurationen", "Zur Prüfung", "Profile", "Einstellungen"):
        assert label in labels, f"Navigationseintrag fehlt: {label}"
    assert "Scanprofile" not in labels
    assert "Verarbeitung einrichten" not in labels


def assert_no_raw_hex_in_ui_modules() -> None:
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "invoice_tool"
    allowed = {"ui_tokens.py", "ui_theme.py"}
    pattern = re.compile(r"#[0-9a-fA-F]{3,8}")
    offenders: list[str] = []
    for path in sorted(root.glob("ui_*.py")):
        if path.name in allowed:
            continue
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if pattern.search(line) and "ui_theme" not in line:
                offenders.append(f"{path.name}:{index}")
    assert not offenders, f"Roh-Hex außerhalb des Theme-Layers: {offenders[:10]}"


def assert_cfg_001_document_rules_layout(rules_root: Any) -> None:
    """CFG-001 structural checks for destination configuration controls."""
    labels = collect_labels(rules_root)

    assert "Allgemeine Regeln" in labels
    assert "Zuordnung testen" in labels
    assert "Zielordner" in labels
    assert "Wenn keine Zuordnung möglich ist" in labels
    assert "Zuordnung prüfen" in labels
    assert "Zielordner hinzufügen" in labels
    assert "Dateiname anpassen" in labels
    assert "Technische Details anzeigen" in labels
    assert "Routing-Vorschau" not in labels
    assert "Globale Dokumentregeln" not in labels
    assert "Nutzerdefinierte Zielordner" not in labels
    assert "Nicht eindeutig zuordenbare Dokumente" not in labels
    assert "Vorschau berechnen" not in labels
    assert "Routing-Feld" not in labels

    legacy_tab_labels = {"Zielordner", "Dokumentenregeln"}
    tab_texts = _collect_tab_texts(rules_root)
    assert not (legacy_tab_labels & tab_texts), "Separate Tab-Labels dürfen nicht erscheinen"

    global_pos = _label_positions(rules_root, "Allgemeine Regeln")
    assignment_pos = _label_positions(rules_root, "Zuordnung testen")
    targets_pos = _label_positions(rules_root, "Zielordner")
    fallback_pos = _label_positions(rules_root, "Wenn keine Zuordnung möglich ist")
    assert global_pos and assignment_pos and targets_pos and fallback_pos, "Hauptabschnitte fehlen"
    assert min(global_pos) < min(assignment_pos) < min(targets_pos) < min(fallback_pos), (
        "Reihenfolge muss Allgemeine Regeln → Zuordnung testen → Zielordner → Fallback sein"
    )

    pick_buttons = find_controls_by_label(rules_root, "Ordner auswählen")
    assert pick_buttons, "Nativer Ordner-auswählen-Button fehlt"
    assert pick_buttons[0].on_click is not None

    edit_buttons = find_controls_by_label(rules_root, "Bearbeiten")
    assert edit_buttons, "Bearbeiten-Aktion fehlt"

    delete_buttons = find_controls_by_label(rules_root, "Löschen")
    assert delete_buttons, "Löschen-Aktion fehlt"

    switches = [
        control
        for control in iter_controls(rules_root)
        if control.__class__.__name__ == "Switch"
    ]
    assert switches, "Aktiv/Inaktiv- oder Override-Schalter fehlen"

    radio_groups = [
        control
        for control in iter_controls(rules_root)
        if control.__class__.__name__ == "RadioGroup"
    ]
    assert not radio_groups, "Relativ/Absolut-Auswahl darf in der neuen UI nicht erscheinen"

    file_pickers = [
        control
        for control in iter_controls(rules_root)
        if control.__class__.__name__ == "FilePicker"
    ]
    assert not file_pickers, "FilePicker darf nicht als sichtbares Control erscheinen"

    technical_panels = [
        control
        for control in iter_controls(rules_root)
        if control.__class__.__name__ == "Column"
        and getattr(control, "visible", True) is False
    ]
    assert technical_panels, "Technische Details sollen standardmäßig eingeklappt sein"
