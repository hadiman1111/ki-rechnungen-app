"""Structural tests for shared UI components and theme usage."""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_tool import ui_components, ui_theme

try:
    from flet.version import flet_version

    _FLET_VERSION = tuple(int(part) for part in str(flet_version).split(".")[:3])
except Exception:
    _FLET_VERSION = (0, 0, 0)

requires_flet_085 = pytest.mark.skipif(
    _FLET_VERSION < (0, 85, 0),
    reason="Erfordert Flet >= 0.85 für Padding/Border-Klassen-API",
)


def test_ui_components_use_theme_not_raw_hex() -> None:
    source = Path(ui_components.__file__).read_text(encoding="utf-8")
    assert "#" not in source
    assert "ui_theme" in source


@requires_flet_085
def test_primary_and_secondary_buttons_construct() -> None:
    import flet as ft

    from invoice_tool.ui_components import primary_button, secondary_button

    primary = primary_button("Speichern")
    secondary = secondary_button("Abbrechen")
    assert isinstance(primary, ft.ElevatedButton)
    assert isinstance(secondary, ft.OutlinedButton)


@requires_flet_085
def test_navigation_item_active_state() -> None:
    import flet as ft

    from invoice_tool.ui_components import nav_item

    item = nav_item("Arbeitsbereich", icon=ft.Icons.HOME, active=True)
    assert item.__class__.__name__ == "Container"


@requires_flet_085
def test_configuration_card_summary_fields() -> None:
    from invoice_tool.ui_components import configuration_card

    card = configuration_card(
        name="Beispiel",
        active=True,
        matching_summary="Konto ist beispiel",
        filename_example="20260708_beispiel.pdf",
        destination="~/Beispiel",
    )
    assert card.__class__.__name__ == "Container"


@requires_flet_085
def test_page_heading_and_empty_state() -> None:
    from invoice_tool.ui_components import empty_state, page_heading

    heading = page_heading("Konfigurationen", subtitle="Erklärung")
    assert heading.__class__.__name__ == "Column"
    state = empty_state("Leer", message="Noch keine Einträge")
    assert state.__class__.__name__ == "Container"


def test_theme_tokens_are_semantic() -> None:
    assert ui_theme.COLOR_PRIMARY
    assert ui_theme.NAV_WIDTH > 0
    assert ui_theme.BORDER_WIDTH == 1


@requires_flet_085
def test_form_field_and_status_badge() -> None:
    import flet as ft

    from invoice_tool.ui_components import form_field, status_badge

    field = form_field("Name", value="Test")
    badge = status_badge("Aktiv", tone="success")
    assert isinstance(field, ft.TextField)
    assert badge.__class__.__name__ == "Container"
