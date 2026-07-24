"""UI-v2 Track-B development-only default folders for manual smoke.

TEMPORARY / DEVELOPMENT ONLY — not product defaults, not SaaS behavior.
Safe to remove later. Never enables productive processing or auto-run.
Does not touch Track A UI or processing-core.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

# Opt-in / opt-out for Track-B UI-v2 manual smoke convenience.
ENV_TRACK_B_DEV_DEFAULTS = "KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS"

# Controlled test tree only — never real invoice folders.
CONTROLLED_TEST_ROOT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test")
TRACK_B_DEV_INPUT_DEFAULT = CONTROLLED_TEST_ROOT / "input"
TRACK_B_DEV_OUTPUT_DEFAULT = CONTROLLED_TEST_ROOT / "output"
TRACK_B_DEV_PAYPAL_TARGET_DEFAULT = (
    TRACK_B_DEV_OUTPUT_DEFAULT / "geplant" / "paypal"
)

SOURCE_TRACK_B_DEV_DEFAULT = "track_b_dev_default"

MSG_DEV_NOTE = "Entwicklungsmodus: kontrollierte Testordner sind vorbelegt."
MSG_MISSING_CONTROLLED_FOLDERS = (
    "Kontrollierte Testordner fehlen. Bitte Testordner erstellen."
)
MSG_PAYPAL_TARGET_MISSING = (
    "Der kontrollierte PayPal-Zielordner fehlt. Bitte Testordner erstellen."
)
MSG_EMPTY_REVIEW_HELP = (
    "Keine Prüffälle geladen. Im Entwicklungsmodus sind Eingangs- und "
    "Ausgangsordner vorbelegt. Bitte im Arbeitsbereich einen kontrollierten "
    "Preview-/Sandbox-Lauf starten."
)
ACTION_CREATE_CONTROLLED_FOLDERS = "Kontrollierte Testordner erstellen"
ACTION_START_CONTROLLED_PREVIEW = "Kontrollierten Preview-Lauf starten"

# Set only by app_ui_v2 local entry (or tests). Never a silent product default.
_ENABLED_BY_LOCAL_ENTRY = False


def enable_track_b_dev_defaults_for_local_entry(
    *,
    env: Mapping[str, str] | None = None,
    app_path: str | Path | None = None,
) -> bool:
    """Enable Track-B UI-v2 smoke defaults from the local app_ui_v2 entrypoint.

    Respects ``KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=0`` as hard off.
    When unset, enables only for the local ``KI-Rechnungen-App`` worktree.
    """

    global _ENABLED_BY_LOCAL_ENTRY
    environ = env if env is not None else os.environ
    raw = str(environ.get(ENV_TRACK_B_DEV_DEFAULTS, "")).strip().casefold()
    if raw in {"0", "false", "no", "off"}:
        _ENABLED_BY_LOCAL_ENTRY = False
        return False
    if raw in {"1", "true", "yes", "on"}:
        _ENABLED_BY_LOCAL_ENTRY = True
        return True
    path = str(app_path or Path(__file__).resolve()).replace("\\", "/")
    _ENABLED_BY_LOCAL_ENTRY = "KI-Rechnungen-App" in path
    return _ENABLED_BY_LOCAL_ENTRY


def reset_track_b_dev_defaults_entry_flag() -> None:
    """Test helper — clear local-entry enablement."""

    global _ENABLED_BY_LOCAL_ENTRY
    _ENABLED_BY_LOCAL_ENTRY = False


def is_track_b_dev_defaults_enabled(
    *,
    env: Mapping[str, str] | None = None,
    app_path: str | Path | None = None,
) -> bool:
    """True only for UI-v2 Track-B manual-smoke / local-dev defaults."""

    environ = env if env is not None else os.environ
    raw = str(environ.get(ENV_TRACK_B_DEV_DEFAULTS, "")).strip().casefold()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    if _ENABLED_BY_LOCAL_ENTRY:
        return True
    # Pure helper path check for unit tests that pass app_path without entry flag.
    if app_path is not None:
        return "KI-Rechnungen-App" in str(app_path).replace("\\", "/")
    return False


def get_track_b_dev_input_default() -> str:
    return str(TRACK_B_DEV_INPUT_DEFAULT)


def get_track_b_dev_output_default() -> str:
    return str(TRACK_B_DEV_OUTPUT_DEFAULT)


def get_track_b_dev_paypal_target_default() -> str:
    return str(TRACK_B_DEV_PAYPAL_TARGET_DEFAULT)


def track_b_dev_controlled_folder_paths() -> tuple[Path, Path, Path]:
    """Exact folders the safe create action may touch — nothing else."""

    return (
        TRACK_B_DEV_INPUT_DEFAULT,
        TRACK_B_DEV_OUTPUT_DEFAULT,
        TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )


def missing_track_b_dev_folders() -> tuple[Path, ...]:
    missing: list[Path] = []
    for path in track_b_dev_controlled_folder_paths():
        try:
            if not path.is_dir():
                missing.append(path)
        except OSError:
            missing.append(path)
    return tuple(missing)


def controlled_folders_status_message() -> str | None:
    if not missing_track_b_dev_folders():
        return None
    return MSG_MISSING_CONTROLLED_FOLDERS


def paypal_target_status_message() -> str | None:
    try:
        if TRACK_B_DEV_PAYPAL_TARGET_DEFAULT.is_dir():
            return None
    except OSError:
        pass
    return MSG_PAYPAL_TARGET_MISSING


@dataclass(frozen=True)
class EnsureTrackBDevFoldersResult:
    ok: bool
    created: tuple[str, ...]
    already_present: tuple[str, ...]
    message: str
    touched_only_controlled: bool
    auto_run: bool = False
    called_run_once: bool = False
    productive_final_write: bool = False


def ensure_track_b_dev_folders_if_requested(
    *,
    explicit_user_action: bool = False,
) -> EnsureTrackBDevFoldersResult:
    """Create only the three controlled test folders after an explicit click.

    Never creates real invoice folders. Never runs processing.
    """

    if not explicit_user_action:
        return EnsureTrackBDevFoldersResult(
            ok=False,
            created=(),
            already_present=(),
            message="Ordnererstellung erfordert expliziten Klick.",
            touched_only_controlled=True,
        )

    allowed = {p.resolve() for p in track_b_dev_controlled_folder_paths()}
    created: list[str] = []
    already: list[str] = []
    for path in track_b_dev_controlled_folder_paths():
        resolved = path.expanduser().resolve()
        if resolved not in allowed:
            return EnsureTrackBDevFoldersResult(
                ok=False,
                created=tuple(created),
                already_present=tuple(already),
                message="Abbruch: Pfad außerhalb der kontrollierten Testordner.",
                touched_only_controlled=False,
            )
        if resolved.is_dir():
            already.append(str(resolved))
            continue
        resolved.mkdir(parents=True, exist_ok=True)
        created.append(str(resolved))

    if created:
        message = f"Kontrollierte Testordner erstellt ({len(created)})."
    else:
        message = "Kontrollierte Testordner waren bereits vorhanden."
    return EnsureTrackBDevFoldersResult(
        ok=True,
        created=tuple(created),
        already_present=tuple(already),
        message=message,
        touched_only_controlled=True,
    )


@dataclass(frozen=True)
class ApplyTrackBDevDefaultsResult:
    applied: bool
    input_prefilled: bool
    output_prefilled: bool
    input_path: str | None
    output_path: str | None
    note: str
    missing_folders_message: str | None
    auto_run: bool = False
    called_run_once: bool = False
    paypal_rule_saved: bool = False
    productive_final_write: bool = False


def apply_track_b_dev_folder_defaults_to_state(
    state: Any,
    *,
    enabled: bool | None = None,
) -> ApplyTrackBDevDefaultsResult:
    """Prefill empty workspace folders when Track-B UI-v2 dev defaults are on.

    Never overrides an existing user selection. Never starts a run.
    """

    active = is_track_b_dev_defaults_enabled() if enabled is None else bool(enabled)
    if not active:
        return ApplyTrackBDevDefaultsResult(
            applied=False,
            input_prefilled=False,
            output_prefilled=False,
            input_path=(getattr(state, "workspace_input_folder_override", None) or None),
            output_path=(
                getattr(state, "workspace_output_folder_override", None) or None
            ),
            note="",
            missing_folders_message=None,
        )

    input_existing = str(
        getattr(state, "workspace_input_folder_override", None) or ""
    ).strip()
    output_existing = str(
        getattr(state, "workspace_output_folder_override", None) or ""
    ).strip()

    input_prefilled = False
    output_prefilled = False
    if not input_existing:
        state.workspace_input_folder_override = get_track_b_dev_input_default()
        state.workspace_input_folder_source = SOURCE_TRACK_B_DEV_DEFAULT
        input_prefilled = True
    if not output_existing:
        state.workspace_output_folder_override = get_track_b_dev_output_default()
        state.workspace_output_folder_source = SOURCE_TRACK_B_DEV_DEFAULT
        output_prefilled = True

    setattr(state, "track_b_dev_defaults_active", True)
    setattr(state, "track_b_dev_defaults_note", MSG_DEV_NOTE)

    return ApplyTrackBDevDefaultsResult(
        applied=True,
        input_prefilled=input_prefilled,
        output_prefilled=output_prefilled,
        input_path=str(getattr(state, "workspace_input_folder_override", None) or "")
        or None,
        output_path=str(getattr(state, "workspace_output_folder_override", None) or "")
        or None,
        note=MSG_DEV_NOTE,
        missing_folders_message=controlled_folders_status_message(),
    )


def is_payment_field_ist_paypal_condition(draft: Any) -> bool:
    """True when proposed_condition is payment_field ist paypal."""

    if draft is None:
        return False
    feature = str(
        getattr(draft, "proposed_matching_feature_key", None) or ""
    ).strip().casefold()
    operator = str(
        getattr(draft, "proposed_matching_operator", None) or ""
    ).strip().casefold()
    values = {
        str(v).strip().casefold()
        for v in (getattr(draft, "proposed_matching_values", ()) or ())
        if str(v).strip()
    }
    condition = str(getattr(draft, "proposed_condition", None) or "").strip().casefold()
    condition_norm = condition.replace("_", " ")
    if condition_norm == "payment field ist paypal":
        return True
    if condition == "payment_field ist paypal":
        return True
    return (
        feature in {"payment_field", "payment field"}
        and operator == "ist"
        and "paypal" in values
    )


def paypal_target_under_controlled_output(path: str | Path | None) -> bool:
    raw = str(path or "").strip()
    if not raw:
        return False
    try:
        candidate = Path(raw).expanduser().resolve()
        root = TRACK_B_DEV_OUTPUT_DEFAULT.expanduser().resolve()
    except OSError:
        return False
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class PrefillPayPalTargetResult:
    applied: bool
    draft: Any
    target_path: str | None
    message: str | None
    auto_saved: bool = False
    under_controlled_output: bool = False


def maybe_prefill_track_b_dev_paypal_target(
    draft: Any,
    *,
    enabled: bool | None = None,
) -> PrefillPayPalTargetResult:
    """Prefill empty PayPal draft destination with controlled paypal folder.

    Only for payment_field ist paypal + UI-v2 dev defaults. Never auto-saves.
    """

    active = is_track_b_dev_defaults_enabled() if enabled is None else bool(enabled)
    if draft is None or not active:
        return PrefillPayPalTargetResult(
            applied=False,
            draft=draft,
            target_path=None,
            message=None,
        )
    if not is_payment_field_ist_paypal_condition(draft):
        return PrefillPayPalTargetResult(
            applied=False,
            draft=draft,
            target_path=str(getattr(draft, "proposed_destination_path", "") or "")
            or None,
            message=None,
        )

    existing = str(getattr(draft, "proposed_destination_path", "") or "").strip()
    if existing:
        under = paypal_target_under_controlled_output(existing)
        return PrefillPayPalTargetResult(
            applied=False,
            draft=draft,
            target_path=existing,
            message=paypal_target_status_message() if under else None,
            under_controlled_output=under,
        )

    target = get_track_b_dev_paypal_target_default()
    if not paypal_target_under_controlled_output(target):
        return PrefillPayPalTargetResult(
            applied=False,
            draft=draft,
            target_path=None,
            message="PayPal-Ziel liegt nicht unter dem kontrollierten Output.",
            under_controlled_output=False,
        )

    from dataclasses import replace

    updated = replace(draft, proposed_destination_path=target)
    msg = paypal_target_status_message()
    return PrefillPayPalTargetResult(
        applied=True,
        draft=updated,
        target_path=target,
        message=msg,
        auto_saved=False,
        under_controlled_output=True,
    )


__all__ = (
    "ACTION_CREATE_CONTROLLED_FOLDERS",
    "ACTION_START_CONTROLLED_PREVIEW",
    "ApplyTrackBDevDefaultsResult",
    "CONTROLLED_TEST_ROOT",
    "ENV_TRACK_B_DEV_DEFAULTS",
    "EnsureTrackBDevFoldersResult",
    "MSG_DEV_NOTE",
    "MSG_EMPTY_REVIEW_HELP",
    "MSG_MISSING_CONTROLLED_FOLDERS",
    "MSG_PAYPAL_TARGET_MISSING",
    "PrefillPayPalTargetResult",
    "SOURCE_TRACK_B_DEV_DEFAULT",
    "TRACK_B_DEV_INPUT_DEFAULT",
    "TRACK_B_DEV_OUTPUT_DEFAULT",
    "TRACK_B_DEV_PAYPAL_TARGET_DEFAULT",
    "apply_track_b_dev_folder_defaults_to_state",
    "controlled_folders_status_message",
    "enable_track_b_dev_defaults_for_local_entry",
    "ensure_track_b_dev_folders_if_requested",
    "get_track_b_dev_input_default",
    "get_track_b_dev_output_default",
    "get_track_b_dev_paypal_target_default",
    "is_payment_field_ist_paypal_condition",
    "is_track_b_dev_defaults_enabled",
    "maybe_prefill_track_b_dev_paypal_target",
    "missing_track_b_dev_folders",
    "paypal_target_status_message",
    "paypal_target_under_controlled_output",
    "reset_track_b_dev_defaults_entry_flag",
    "track_b_dev_controlled_folder_paths",
)
