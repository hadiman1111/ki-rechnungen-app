"""Einstellungen page — Track-B UI-v2 settings detail shell.

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
from invoice_tool.ui_v2.policy_editor_controls import (
    PolicyEditorControlsVM,
    build_policy_editor_controls_panel,
    build_policy_editor_controls_vm,
)
from invoice_tool.ui_v2.processing_state import MSG_DRY_RUN_UNAVAILABLE
from invoice_tool.ui_v2.state import UiV2State

SETTINGS_SUBTITLE = "Allgemeine Programmeinstellungen und Readiness-Hinweise."
PRODUCTIVE_EXECUTION_NOTICE = (
    "Produktive lokale Verarbeitung ist noch nicht freigegeben."
)
DRY_RUN_UNAVAILABLE_NOTICE = MSG_DRY_RUN_UNAVAILABLE
PRODUCT_NEUTRAL_NOTICE = (
    "Diese Einstellungen sind produktneutral und enthalten keine privaten Standardwerte."
)
READINESS_BANNER = (
    "Track-B Einstellungen sind vorbereitet; produktive lokale Ausführung "
    "ist noch nicht aktiviert."
)
NO_AUTOMATIC_FOLDER_SCAN = "Kein automatischer Ordner-Scan."
NO_PRIVATE_DEFAULTS = "Keine privaten Standardwerte."

SETTINGS_SECTIONS = (
    ("Allgemein", "Allgemeine Anzeige- und Programmhinweise (Readiness)."),
    ("Verarbeitung", "Verarbeitungsoptionen bleiben deaktiviert, bis ein PO-Gate freigibt."),
    ("Sicherheit", "Sicherheitsoptionen sind noch nicht konfigurierbar."),
    ("Export", "Exportoptionen sind noch nicht konfigurierbar."),
    ("Produktstatus", "Aktueller Sicherheits- und Freigabestatus der lokalen UI-v2."),
)

SECTION_STATUS_DISABLED = "Nicht verfügbar"
SECTION_STATUS_READINESS = "Readiness — keine Speicherung"


@dataclass(frozen=True)
class SettingsSectionVM:
    title: str
    detail: str
    status: str


@dataclass(frozen=True)
class SettingsSafetyStateVM:
    """Visible safety state for the settings detail shell."""

    dry_run_available: bool
    dry_run_notice: str
    productive_execution_enabled: bool
    productive_execution_notice: str
    has_private_defaults: bool
    private_defaults_notice: str
    automatic_folder_scan: bool
    folder_scan_notice: str
    product_neutral_notice: str


@dataclass(frozen=True)
class SettingsPageVM:
    """View-model for Track-B settings readiness — testable without a GUI window."""

    title: str
    subtitle: str
    banner: str
    productive_execution_enabled: bool
    productive_execution_notice: str
    dry_run_available: bool
    dry_run_notice: str
    product_neutral_notice: str
    safety: SettingsSafetyStateVM
    sections: tuple[SettingsSectionVM, ...]
    has_productive_toggle: bool
    policy_editor: PolicyEditorControlsVM


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
    safety = SettingsSafetyStateVM(
        dry_run_available=False,
        dry_run_notice=DRY_RUN_UNAVAILABLE_NOTICE,
        productive_execution_enabled=False,
        productive_execution_notice=PRODUCTIVE_EXECUTION_NOTICE,
        has_private_defaults=False,
        private_defaults_notice=NO_PRIVATE_DEFAULTS,
        automatic_folder_scan=False,
        folder_scan_notice=NO_AUTOMATIC_FOLDER_SCAN,
        product_neutral_notice=PRODUCT_NEUTRAL_NOTICE,
    )
    return SettingsPageVM(
        title="Einstellungen",
        subtitle=SETTINGS_SUBTITLE,
        banner=READINESS_BANNER,
        productive_execution_enabled=False,
        productive_execution_notice=PRODUCTIVE_EXECUTION_NOTICE,
        dry_run_available=False,
        dry_run_notice=DRY_RUN_UNAVAILABLE_NOTICE,
        product_neutral_notice=PRODUCT_NEUTRAL_NOTICE,
        safety=safety,
        sections=sections,
        has_productive_toggle=False,
        policy_editor=build_policy_editor_controls_vm(),
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
            make_metadata_row("Dry-Run", "Nicht verfügbar"),
            make_metadata_row("Dry-Run-Hinweis", vm.dry_run_notice),
            make_metadata_row("Standardwerte", NO_PRIVATE_DEFAULTS),
            make_metadata_row("Ordner-Scan", NO_AUTOMATIC_FOLDER_SCAN),
            make_metadata_row("Produktneutral", vm.product_neutral_notice),
            make_metadata_row("Persistenz", "Keine Speicherung in diesem Schritt"),
        ),
    ]

    for section in vm.sections:
        controls.append(make_section_label(section.title))
        if section.title == "Produktstatus":
            controls.append(
                make_settings_panel(
                    make_metadata_row("Dry-Run", "Nicht verfügbar bis Core-Grenze existiert"),
                    make_metadata_row("Hinweis", vm.dry_run_notice),
                    make_metadata_row("Produktive Ausführung", "Nicht freigegeben"),
                    make_metadata_row("Hinweis", vm.productive_execution_notice),
                    make_metadata_row("Standardwerte", NO_PRIVATE_DEFAULTS),
                    make_metadata_row("Ordner-Scan", NO_AUTOMATIC_FOLDER_SCAN),
                    make_metadata_row("Hinweis", vm.product_neutral_notice),
                    make_metadata_row("Modus", section.status),
                )
            )
        else:
            controls.append(
                make_settings_panel(
                    make_metadata_row("Status", SECTION_STATUS_DISABLED),
                    make_metadata_row("Hinweis", section.detail),
                    make_metadata_row("Modus", section.status),
                )
            )

    controls.extend(build_policy_editor_controls_panel(vm.policy_editor))
    return page_scaffold(*controls)
