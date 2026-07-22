"""Track-B UI-v2 workspace configuration selection for sandbox start.

Pure helpers — no Flet, no filesystem IO, no processing-core, no Track A.
Resolves an active run configuration from the read-only snapshot / UI state
so the workspace does not block with a false “Konfiguration fehlt” when
active configurations already exist on the configurations page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from invoice_tool.ui_v2.view_models import (
    ConfigurationSummaryVM,
    ConfigurationsPageVM,
    ProfileDetailVM,
    UiV2ReadOnlySnapshot,
)

UNMATCHED_CONFIGURATION_ID = "unmatched"

MSG_PROFILE_MISSING = "Profil fehlt. Bitte Profil vorbereiten."
MSG_NO_ACTIVE_CONFIGURATION = "Keine aktive Konfiguration vorhanden."
MSG_CONFIGURATION_CHANGE_HINT = "Ändern über Konfigurationen"
MSG_CONFIGURATION_MISSING_EXPLICIT = (
    "Konfiguration fehlt. Bitte eine Konfiguration explizit wählen."
)
MSG_PRODUCTIVE_LOCKED = "Produktive Verarbeitung ist gesperrt."
MSG_EXPORT_REMAINS_DRAFT = "Export bleibt Vorschau."
MSG_CORE_BRIDGE_TECHNICAL = "Technischer Blocker: Core-Bridge fehlt."
MSG_NO_ORIGINALS_USED = "Keine Originalordner wurden verwendet."
DEFAULT_PROFILE_ID_SENTINEL = "local"

MAX_BLOCKED_DETAIL_LINES = 5

ResolutionKind = Literal[
    "missing_profile",
    "no_active_configuration",
    "auto_single",
    "default_multiple",
    "explicit",
]


@dataclass(frozen=True)
class WorkspaceConfigurationOption:
    """Selectable workspace run configuration (unmatched excluded from defaults)."""

    configuration_id: str
    name: str
    active: bool
    is_unmatched: bool
    sort_index: int


@dataclass(frozen=True)
class WorkspaceConfigurationSelection:
    """Resolved workspace profile/configuration for sandbox run readiness."""

    profile_id: str | None
    profile_name: str | None
    selected_configuration_id: str | None
    selected_configuration_name: str | None
    options: tuple[WorkspaceConfigurationOption, ...]
    active_count: int
    resolution: ResolutionKind
    blocker_message: str | None
    change_hint: str | None
    is_ready: bool

    @property
    def configuration_display(self) -> str:
        if self.selected_configuration_name:
            return self.selected_configuration_name
        if self.blocker_message:
            return "fehlt"
        return "fehlt"

    @property
    def profile_display(self) -> str:
        return (self.profile_name or "").strip() or "fehlt"

    @property
    def summary_lines(self) -> tuple[str, ...]:
        lines = [
            f"Profil: {self.profile_display}",
            f"Konfiguration: {self.configuration_display}",
        ]
        if self.is_ready and self.change_hint:
            lines.append(self.change_hint)
        elif self.blocker_message and not self.is_ready:
            lines.append(self.blocker_message)
        return tuple(lines)


def build_workspace_configuration_options(
    configurations: Sequence[ConfigurationSummaryVM] | ConfigurationsPageVM | None,
    *,
    unmatched: ConfigurationSummaryVM | None = None,
) -> tuple[WorkspaceConfigurationOption, ...]:
    """Build ordered options from page VM / summaries — unmatched kept separate."""

    items: list[ConfigurationSummaryVM] = []
    unmatched_vm = unmatched
    if isinstance(configurations, ConfigurationsPageVM):
        items = list(configurations.configurations or ())
        unmatched_vm = configurations.unmatched if unmatched_vm is None else unmatched_vm
    elif configurations is not None:
        items = list(configurations)

    options: list[WorkspaceConfigurationOption] = []
    for index, config in enumerate(items):
        config_id = str(config.configuration_id or "").strip()
        if not config_id or config_id == UNMATCHED_CONFIGURATION_ID:
            continue
        options.append(
            WorkspaceConfigurationOption(
                configuration_id=config_id,
                name=str(config.name or "").strip() or config_id,
                active=bool(config.active),
                is_unmatched=False,
                sort_index=int(getattr(config, "sort_index", index)),
            )
        )

    if unmatched_vm is not None:
        unmatched_id = str(unmatched_vm.configuration_id or UNMATCHED_CONFIGURATION_ID).strip()
        options.append(
            WorkspaceConfigurationOption(
                configuration_id=unmatched_id or UNMATCHED_CONFIGURATION_ID,
                name=str(unmatched_vm.name or "").strip() or "Nicht zugeordnete Dokumente",
                active=bool(unmatched_vm.active),
                is_unmatched=True,
                sort_index=int(getattr(unmatched_vm, "sort_index", len(options))),
            )
        )

    options.sort(key=lambda item: (item.sort_index, item.name.lower(), item.configuration_id))
    return tuple(options)


def select_default_workspace_configuration(
    options: Sequence[WorkspaceConfigurationOption],
) -> WorkspaceConfigurationOption | None:
    """Stable default = first active non-unmatched configuration in display order."""

    active = [
        item
        for item in options
        if item.active and not item.is_unmatched and (item.configuration_id or "").strip()
    ]
    if not active:
        return None
    return active[0]


def explain_workspace_configuration_blocker(
    selection: WorkspaceConfigurationSelection,
) -> str | None:
    """Compact blocker copy for missing profile / missing active configuration."""

    return selection.blocker_message


def build_compact_blocked_details(
    *,
    configuration_label: str | None = None,
    core_bridge_relevant: bool = False,
    include_productive: bool = True,
    include_export: bool = True,
) -> tuple[str, ...]:
    """Default expanded details — max 5 short lines, no sandbox bullet wall."""

    lines: list[str] = [MSG_NO_ORIGINALS_USED]
    if include_productive:
        lines.append(MSG_PRODUCTIVE_LOCKED)
    if include_export:
        lines.append(MSG_EXPORT_REMAINS_DRAFT)
    if core_bridge_relevant:
        lines.append(MSG_CORE_BRIDGE_TECHNICAL)
    label = (configuration_label or "").strip() or "fehlt"
    lines.append(f"Konfiguration: {label}")
    # Deduplicate while preserving order, then hard-cap.
    cleaned: list[str] = []
    for line in lines:
        text = str(line or "").strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return tuple(cleaned[:MAX_BLOCKED_DETAIL_LINES])


def resolve_workspace_configuration_selection(
    *,
    profile: ProfileDetailVM | None = None,
    profile_id: str | None = None,
    profile_name: str | None = None,
    configurations: Sequence[ConfigurationSummaryVM] | ConfigurationsPageVM | None = None,
    explicit_configuration_id: str | None = None,
    snapshot: UiV2ReadOnlySnapshot | None = None,
) -> WorkspaceConfigurationSelection:
    """Resolve active profile + run configuration for workspace sandbox start."""

    if snapshot is not None:
        profile = snapshot.profile if profile is None else profile
        configurations = (
            snapshot.configurations if configurations is None else configurations
        )

    resolved_profile_id = (profile_id or "").strip() or None
    resolved_profile_name = (profile_name or "").strip() or None
    if profile is not None:
        resolved_profile_id = resolved_profile_id or (profile.profile_id or "").strip() or None
        resolved_profile_name = (
            resolved_profile_name or (profile.profile_name or "").strip() or None
        )

    options = build_workspace_configuration_options(configurations)
    active_options = tuple(
        item for item in options if item.active and not item.is_unmatched
    )
    active_count = len(active_options)

    if not resolved_profile_id:
        return WorkspaceConfigurationSelection(
            profile_id=None,
            profile_name=resolved_profile_name,
            selected_configuration_id=None,
            selected_configuration_name=None,
            options=options,
            active_count=active_count,
            resolution="missing_profile",
            blocker_message=MSG_PROFILE_MISSING,
            change_hint=None,
            is_ready=False,
        )

    explicit = (explicit_configuration_id or "").strip() or None
    # Explicit unmatched is never a normal sandbox run target.
    if explicit == UNMATCHED_CONFIGURATION_ID:
        explicit = None

    if explicit:
        for item in active_options:
            if item.configuration_id == explicit:
                return WorkspaceConfigurationSelection(
                    profile_id=resolved_profile_id,
                    profile_name=resolved_profile_name,
                    selected_configuration_id=item.configuration_id,
                    selected_configuration_name=item.name,
                    options=options,
                    active_count=active_count,
                    resolution="explicit",
                    blocker_message=None,
                    change_hint=MSG_CONFIGURATION_CHANGE_HINT,
                    is_ready=True,
                )
        # Snapshot had no matching active row, but UI already carries an explicit id
        # (tests / direct wiring). Keep it — do not invent unmatched.
        if active_count == 0:
            return WorkspaceConfigurationSelection(
                profile_id=resolved_profile_id,
                profile_name=resolved_profile_name,
                selected_configuration_id=explicit,
                selected_configuration_name=explicit,
                options=options,
                active_count=0,
                resolution="explicit",
                blocker_message=None,
                change_hint=MSG_CONFIGURATION_CHANGE_HINT,
                is_ready=True,
            )

    if active_count == 0:
        return WorkspaceConfigurationSelection(
            profile_id=resolved_profile_id,
            profile_name=resolved_profile_name,
            selected_configuration_id=None,
            selected_configuration_name=None,
            options=options,
            active_count=0,
            resolution="no_active_configuration",
            blocker_message=MSG_NO_ACTIVE_CONFIGURATION,
            change_hint=MSG_CONFIGURATION_CHANGE_HINT,
            is_ready=False,
        )

    default = select_default_workspace_configuration(active_options)
    assert default is not None  # active_count > 0
    resolution: ResolutionKind = (
        "auto_single" if active_count == 1 else "default_multiple"
    )
    return WorkspaceConfigurationSelection(
        profile_id=resolved_profile_id,
        profile_name=resolved_profile_name,
        selected_configuration_id=default.configuration_id,
        selected_configuration_name=default.name,
        options=options,
        active_count=active_count,
        resolution=resolution,
        blocker_message=None,
        change_hint=MSG_CONFIGURATION_CHANGE_HINT,
        is_ready=True,
    )


def resolve_selection_from_state(
    state: object,
    *,
    profile_id: str | None = None,
) -> WorkspaceConfigurationSelection:
    """Convenience: resolve from UiV2State snapshot + list selection fields."""

    snapshot = getattr(state, "snapshot", None)
    snap = snapshot if isinstance(snapshot, UiV2ReadOnlySnapshot) else None
    explicit = (getattr(state, "config_list_selected_id", None) or "").strip() or None
    selected_profile = (profile_id or "").strip() or None
    if selected_profile is None:
        selected_profile = (getattr(state, "selected_profile_id", None) or "").strip() or None
        # Ignore the default sentinel profile id when a real snapshot is present.
        if selected_profile == DEFAULT_PROFILE_ID_SENTINEL and snap is not None:
            selected_profile = None
    return resolve_workspace_configuration_selection(
        snapshot=snap,
        profile_id=selected_profile,
        explicit_configuration_id=explicit,
    )
