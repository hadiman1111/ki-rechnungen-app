"""Einstellungen page — Track-B UI-v2 settings detail shell.

Generic readiness sections only. No private defaults, no local private
paths, no account/payment hardcoding, no productive execution toggle,
no processing-core imports, no settings persistence beyond UI state.
"""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from invoice_tool.ui_v2.components import (
    compact_capability_matrix,
    compact_hint_block,
    compact_info_row,
    compact_status_banner,
    dense_card,
    make_section_label,
    page_header,
    page_scaffold,
)
from invoice_tool.ui_v2.policy_editor_controls import (
    PolicyEditorControlsVM,
    build_policy_editor_controls_panel,
    build_policy_editor_controls_vm,
)
from invoice_tool.ui_v2.clarity_copy import (
    MSG_CLARITY_BUCKETS_SEPARATED,
    MSG_CLARITY_EXPORT_PREVIEW,
    MSG_CLARITY_FILENAME_NOT_TRUTH,
    MSG_CLARITY_NO_ORIGINAL_FOLDERS,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
    MSG_CLARITY_SANDBOX_COPIED_RUN,
)
from invoice_tool.ui_v2.onboarding import (
    COMPACT_PILOT_STATUS_ITEMS,
    MSG_EXPORT_PREVIEW_NOT_DATEV,
    MSG_LOCAL_PILOT_SANDBOX,
    MSG_ORIGINAL_FOLDERS_PROTECTED,
    MSG_SAAS_NOT_INCLUDED,
    MSG_STAGE_LOCAL_PILOT,
    CapabilityMatrixItem,
    LocalPilotReadinessViewModel,
    build_local_pilot_capability_matrix,
    build_local_pilot_readiness,
)
from invoice_tool.ui_v2.processing_state import MSG_DRY_RUN_UNAVAILABLE
from invoice_tool.ui_v2.state import UiV2State

SETTINGS_SUBTITLE = "Allgemeine Programmeinstellungen und kompakte Readiness-Hinweise."
PRODUCTIVE_EXECUTION_NOTICE = MSG_CLARITY_PRODUCTIVE_NOT_RELEASED
DRY_RUN_UNAVAILABLE_NOTICE = MSG_DRY_RUN_UNAVAILABLE
PRODUCT_NEUTRAL_NOTICE = (
    "Diese Einstellungen sind produktneutral und enthalten keine privaten Standardwerte."
)
READINESS_BANNER = (
    f"{MSG_LOCAL_PILOT_SANDBOX} "
    f"{MSG_CLARITY_PRODUCTIVE_NOT_RELEASED} "
    f"{MSG_SAAS_NOT_INCLUDED} "
    "Track-B Einstellungen sind vorbereitet; produktive lokale Ausführung "
    "ist noch nicht aktiviert."
)
NO_AUTOMATIC_FOLDER_SCAN = "Kein automatischer Ordner-Scan."
NO_PRIVATE_DEFAULTS = "Keine privaten Standardwerte."

EXPORT_SECTION_DETAIL = (
    "Laufergebnisse exportieren Sie im Arbeitsbereich als lokalen JSON-/CSV-Bericht "
    "(erkannt / unklar / fehlgeschlagen / Zielhinweise / Zusammenfassung). "
    f"{MSG_CLARITY_EXPORT_PREVIEW} "
    f"{MSG_CLARITY_BUCKETS_SEPARATED} "
    "Kein Cloud-Sync, keine Originalmutation."
)
STATUS_SECTION_DETAIL = (
    f"{MSG_LOCAL_PILOT_SANDBOX} "
    f"{MSG_ORIGINAL_FOLDERS_PROTECTED} "
    f"{MSG_CLARITY_SANDBOX_COPIED_RUN} "
    f"{MSG_CLARITY_NO_ORIGINAL_FOLDERS} "
    f"{MSG_CLARITY_PRODUCTIVE_NOT_RELEASED} "
    f"{MSG_EXPORT_PREVIEW_NOT_DATEV} "
    f"{MSG_SAAS_NOT_INCLUDED} "
    f"{MSG_CLARITY_FILENAME_NOT_TRUTH} "
    f"{MSG_STAGE_LOCAL_PILOT}"
)

SETTINGS_SECTIONS = (
    ("Allgemein", "Allgemeine Anzeige- und Programmhinweise (Readiness)."),
    ("Verarbeitung", "Verarbeitungsoptionen bleiben deaktiviert, bis ein PO-Gate freigibt."),
    ("Sicherheit", "Sicherheitsoptionen sind noch nicht konfigurierbar."),
    ("Export", EXPORT_SECTION_DETAIL),
    ("Produktstatus", STATUS_SECTION_DETAIL),
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
    capability_matrix: tuple[CapabilityMatrixItem, ...]
    pilot_readiness: LocalPilotReadinessViewModel
    saas_ready: bool
    datev_productive_export_ready: bool
    compact_status_items: tuple[str, ...]
    uses_compact_status_ui: bool


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
    pilot = build_local_pilot_readiness()
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
        capability_matrix=build_local_pilot_capability_matrix(),
        pilot_readiness=pilot,
        saas_ready=False,
        datev_productive_export_ready=False,
        compact_status_items=COMPACT_PILOT_STATUS_ITEMS,
        uses_compact_status_ui=True,
    )


def build_settings_page(state: UiV2State) -> ft.Control:
    vm = build_settings_page_vm(state)
    controls: list[ft.Control] = [
        page_header(vm.title, subtitle=vm.subtitle),
        compact_status_banner(
            "Lokale Pilotversion",
            vm.compact_status_items,
            detail=MSG_SAAS_NOT_INCLUDED,
        ),
        make_section_label("Status"),
        dense_card(
            compact_info_row("Produktive Ausführung", "Deaktiviert"),
            compact_info_row("Dry-Run", "Nicht verfügbar"),
            compact_info_row("Standardwerte", NO_PRIVATE_DEFAULTS),
            compact_info_row("Ordner-Scan", NO_AUTOMATIC_FOLDER_SCAN),
            compact_info_row("Persistenz", "Keine Speicherung in diesem Schritt"),
        ),
        compact_hint_block(
            vm.productive_execution_notice,
            vm.dry_run_notice,
            vm.product_neutral_notice,
            title="Status-Hinweise",
        ),
    ]

    for section in vm.sections:
        controls.append(make_section_label(section.title))
        if section.title == "Produktstatus":
            controls.append(
                dense_card(
                    compact_info_row("Produktstufe", MSG_STAGE_LOCAL_PILOT),
                    compact_info_row("Produktive Ausführung", "Nicht freigegeben"),
                    compact_info_row("Export", MSG_EXPORT_PREVIEW_NOT_DATEV),
                    compact_info_row("Originalordner", MSG_ORIGINAL_FOLDERS_PROTECTED),
                    compact_info_row("Modus", section.status),
                )
            )
            controls.append(
                compact_capability_matrix(
                    tuple((item.label, item.status_label) for item in vm.capability_matrix),
                    title="Fähigkeiten / Grenzen",
                )
            )
            controls.append(
                compact_hint_block(
                    MSG_SAAS_NOT_INCLUDED,
                    NO_PRIVATE_DEFAULTS,
                    NO_AUTOMATIC_FOLDER_SCAN,
                    title="Produktgrenzen",
                )
            )
        elif section.title == "Export":
            controls.append(
                dense_card(
                    compact_info_row("Status", "Arbeitsbereich — lokaler Laufbericht"),
                    compact_info_row("Cloud-Sync", "Nein"),
                    compact_info_row("Originalmutation", "Nein"),
                    compact_info_row("Modus", SECTION_STATUS_READINESS),
                )
            )
            controls.append(compact_hint_block(section.detail, title="Export"))
        else:
            controls.append(
                dense_card(
                    compact_info_row("Status", SECTION_STATUS_DISABLED),
                    compact_info_row("Modus", section.status),
                )
            )
            controls.append(compact_hint_block(section.detail, title=section.title))

    controls.extend(build_policy_editor_controls_panel(vm.policy_editor))
    return page_scaffold(*controls)
