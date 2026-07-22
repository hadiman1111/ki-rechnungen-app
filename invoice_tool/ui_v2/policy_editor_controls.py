"""Track-B UI-v2 Policy Editor Controls — readiness shell only.

Exposes generic, profile-configurable rule readiness without persistence,
without private defaults, without productive execution, and without
processing-core imports or filesystem access.
"""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from invoice_tool.ui_v2.components import (
    make_info_banner,
    make_metadata_row,
    make_section_label,
    make_settings_panel,
)
from invoice_tool.ui_v2.policy_runtime_bridge import (
    MSG_FILENAME_NOT_SOURCE_OF_TRUTH,
    MSG_GENERIC_CARD_UNCLEAR,
    MSG_SUPPLIER_IBAN_NOT_PAYER,
    MSG_UNKNOWN_EVIDENCE_REVIEW,
)

# Required honest product copy for the policy editor readiness shell.
MSG_RULES_PROFILE_CONFIGURABLE = "Regeln werden pro Profil konfiguriert."
MSG_FILENAME_NOT_TRUTH = "Dateinamen sind keine Belegwahrheit."
MSG_UNCLEAR_STAYS_REVIEW = "Unklare Nachweise bleiben zur Prüfung."
MSG_PRODUCTIVE_NOT_RELEASED = "Produktive Verarbeitung ist noch nicht freigegeben."

POLICY_EDITOR_SECTION_TITLE = "Verarbeitungsregeln (Readiness)"
POLICY_EDITOR_SUBTITLE = (
    "Readiness-Hinweise für generische Belegregeln — noch ohne Speicherung."
)
CONTROL_STATUS_READINESS = "Readiness — nicht speicherbar"
CONTROL_STATUS_DISABLED = "Deaktiviert"


@dataclass(frozen=True)
class PolicyControlVM:
    """Single readiness control row — disabled until safe persistence exists."""

    control_id: str
    label: str
    detail: str
    enabled: bool
    status: str
    value_label: str


@dataclass(frozen=True)
class PolicyEditorControlsVM:
    """Pure policy-editor readiness view-model (no GUI / no FS / no core)."""

    section_title: str
    subtitle: str
    banner: str
    honest_copy: tuple[str, ...]
    controls: tuple[PolicyControlVM, ...]
    rules_profile_configurable: bool
    filename_is_source_of_truth: bool
    unclear_evidence_goes_to_review: bool
    supplier_iban_alone_is_payer_evidence: bool
    generic_card_without_account_ref_is_clear: bool
    has_productive_execution_toggle: bool
    productive_execution_enabled: bool
    persistence_enabled: bool
    has_private_defaults: bool


def build_policy_editor_controls_vm() -> PolicyEditorControlsVM:
    """Build generic policy readiness controls — no private tenant values."""

    controls = (
        PolicyControlVM(
            control_id="filename_not_source_of_truth",
            label="Dateiname als Wahrheitsquelle",
            detail=MSG_FILENAME_NOT_TRUTH,
            enabled=False,
            status=CONTROL_STATUS_DISABLED,
            value_label="Nie — Beleginhalt + Profilnachweise",
        ),
        PolicyControlVM(
            control_id="unknown_evidence_to_review",
            label="Unklare Nachweise",
            detail=MSG_UNCLEAR_STAYS_REVIEW,
            enabled=False,
            status=CONTROL_STATUS_READINESS,
            value_label="Zur Prüfung / unklar",
        ),
        PolicyControlVM(
            control_id="supplier_iban_not_payer",
            label="Lieferanten-IBAN allein",
            detail=MSG_SUPPLIER_IBAN_NOT_PAYER,
            enabled=False,
            status=CONTROL_STATUS_READINESS,
            value_label="Kein Zahlernachweis",
        ),
        PolicyControlVM(
            control_id="generic_card_without_account_ref",
            label="Generischer Kartentext ohne Kontoreferenz",
            detail=MSG_GENERIC_CARD_UNCLEAR,
            enabled=False,
            status=CONTROL_STATUS_READINESS,
            value_label="Zur Prüfung / unklar",
        ),
        PolicyControlVM(
            control_id="profile_configurable_rules",
            label="Geschäfts-/Zahlungs-/Kontoregeln",
            detail=MSG_RULES_PROFILE_CONFIGURABLE,
            enabled=False,
            status=CONTROL_STATUS_READINESS,
            value_label="Profilkonfigurierbar",
        ),
    )
    honest_copy = (
        MSG_RULES_PROFILE_CONFIGURABLE,
        MSG_FILENAME_NOT_TRUTH,
        MSG_UNCLEAR_STAYS_REVIEW,
        MSG_PRODUCTIVE_NOT_RELEASED,
    )
    return PolicyEditorControlsVM(
        section_title=POLICY_EDITOR_SECTION_TITLE,
        subtitle=POLICY_EDITOR_SUBTITLE,
        banner=(
            f"{MSG_RULES_PROFILE_CONFIGURABLE} {MSG_PRODUCTIVE_NOT_RELEASED}"
        ),
        honest_copy=honest_copy,
        controls=controls,
        rules_profile_configurable=True,
        filename_is_source_of_truth=False,
        unclear_evidence_goes_to_review=True,
        supplier_iban_alone_is_payer_evidence=False,
        generic_card_without_account_ref_is_clear=False,
        has_productive_execution_toggle=False,
        productive_execution_enabled=False,
        persistence_enabled=False,
        has_private_defaults=False,
    )


def build_policy_editor_controls_panel(
    vm: PolicyEditorControlsVM | None = None,
) -> list[ft.Control]:
    """Render readiness-only policy controls for Settings (or Configurations)."""

    model = vm or build_policy_editor_controls_vm()
    controls: list[ft.Control] = [
        make_section_label(model.section_title),
        make_info_banner(model.banner),
        make_settings_panel(
            make_metadata_row("Hinweis", MSG_FILENAME_NOT_TRUTH),
            make_metadata_row("Hinweis", MSG_UNCLEAR_STAYS_REVIEW),
            make_metadata_row("Hinweis", MSG_RULES_PROFILE_CONFIGURABLE),
            make_metadata_row("Status", MSG_PRODUCTIVE_NOT_RELEASED),
            make_metadata_row(
                "Bridge",
                f"{MSG_FILENAME_NOT_SOURCE_OF_TRUTH} {MSG_UNKNOWN_EVIDENCE_REVIEW}",
            ),
        ),
    ]
    for item in model.controls:
        controls.append(make_section_label(item.label))
        controls.append(
            make_settings_panel(
                make_metadata_row("Wert", item.value_label),
                make_metadata_row("Hinweis", item.detail),
                make_metadata_row("Steuerung", item.status),
                make_metadata_row(
                    "Interaktiv",
                    "Nein — Readiness only" if not item.enabled else "Ja",
                ),
            )
        )
    return controls
