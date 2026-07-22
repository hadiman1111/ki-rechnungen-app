"""Einstellungen page — Track-B UI-v2 settings readiness shell.

Generic readiness sections only. No private defaults, no local private
paths, no account/payment hardcoding, no productive execution toggle,
no processing-core imports, no settings persistence beyond UI state.
"""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from invoice_tool.ui_v2.components import (
    make_info_banner,
    make_metadata_row,
    make_section_label,
    make_settings_panel,
    page_header,
    page_scaffold,
)
from invoice_tool.ui_v2.state import UiV2State

SETTINGS_SUBTITLE = "Allgemeine Programmeinstellungen und Readiness-Hinweise."
PRODUCTIVE_EXECUTION_NOTICE = (
    "Produktive lokale Ausführung ist noch nicht freigegeben."
)
READINESS_BANNER = (
    "Track-B Einstellungen sind vorbereitet; produktive lokale Ausführung "
    "ist noch nicht aktiviert."
)

SETTINGS_SECTIONS = (
    ("Allgemein", "Allgemeine Anzeige- und Programmhinweise (Readiness)."),
    ("Verarbeitung", "Verarbeitungsoptionen bleiben deaktiviert, bis ein PO-Gate freigibt."),
    ("Sicherheit", "Sicherheitsoptionen sind noch nicht konfigurierbar."),
    ("Export", "Exportoptionen sind noch nicht konfigurierbar."),
)

SECTION_STATUS_DISABLED = "Nicht verfügbar"
SECTION_STATUS_READINESS = "Readiness — keine Speicherung"


@dataclass(frozen=True)
class SettingsSectionVM:
    title: str
    detail: str
    status: str


@dataclass(frozen=True)
class SettingsPageVM:
    """View-model for Track-B settings readiness — testable without a GUI window."""

    title: str
    subtitle: str
    banner: str
    productive_execution_enabled: bool
    productive_execution_notice: str
    sections: tuple[SettingsSectionVM, ...]
    has_productive_toggle: bool


def build_settings_page_vm(state: UiV2State | None = None) -> SettingsPageVM:
    """Build generic settings readiness state — ignores private profile data."""

    _ = state  # reserved for future safe transient UI settings only
    sections = tuple(
        SettingsSectionVM(
            title=title,
            detail=detail,
            status=SECTION_STATUS_READINESS,
        )
        for title, detail in SETTINGS_SECTIONS
    )
    return SettingsPageVM(
        title="Einstellungen",
        subtitle=SETTINGS_SUBTITLE,
        banner=READINESS_BANNER,
        productive_execution_enabled=False,
        productive_execution_notice=PRODUCTIVE_EXECUTION_NOTICE,
        sections=sections,
        has_productive_toggle=False,
    )


def build_settings_page(state: UiV2State) -> ft.Control:
    vm = build_settings_page_vm(state)
    controls: list[ft.Control] = [
        page_header(vm.title, subtitle=vm.subtitle),
        make_info_banner(vm.banner),
        make_section_label("Status"),
        make_settings_panel(
            make_metadata_row("Produktive Ausführung", "Deaktiviert"),
            make_metadata_row("Hinweis", vm.productive_execution_notice),
            make_metadata_row("Persistenz", "Keine Speicherung in diesem Schritt"),
        ),
    ]

    for section in vm.sections:
        controls.append(make_section_label(section.title))
        controls.append(
            make_settings_panel(
                make_metadata_row("Status", SECTION_STATUS_DISABLED),
                make_metadata_row("Hinweis", section.detail),
                make_metadata_row("Modus", section.status),
            )
        )

    return page_scaffold(*controls)
