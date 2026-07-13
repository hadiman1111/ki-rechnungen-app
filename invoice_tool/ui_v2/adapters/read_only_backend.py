"""Read-only backend orchestration for UI-v2."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from invoice_tool import app_paths
from invoice_tool.app_paths import resolve_active_profile_id, resolve_invoice_config_path
from invoice_tool.ui_v2.adapters.configuration_reader import (
    get_configurations_page_vm,
    get_destination_summaries,
)
from invoice_tool.ui_v2.adapters.profile_reader import get_active_profile_detail, list_profiles_summary
from invoice_tool.ui_v2.adapters.review_reader import get_review_summary
from invoice_tool.ui_v2.adapters.run_reader import (
    count_result_items,
    get_latest_result_summaries,
    get_latest_run_summary,
)
from invoice_tool.ui_v2.view_models import (
    FoundationSnapshot,
    ProfileSummaryVM,
    UiV2ReadOnlySnapshot,
    WorkspaceSummaryVM,
)

logger = logging.getLogger(__name__)


def get_configuration_count() -> int | None:
    page = get_configurations_page_vm()
    return page.total_count if page.configurations or page.warnings else None


def get_review_count() -> int | None:
    review = get_review_summary()
    if review.availability == "no_run":
        return None
    return review.review_count


def get_destination_summary_count() -> int | None:
    destinations = get_destination_summaries()
    return len(destinations) if destinations else 0


def get_active_profile_summary() -> ProfileSummaryVM:
    detail = get_active_profile_detail()
    return ProfileSummaryVM(
        profile_id=detail.profile_id,
        profile_name=detail.profile_name,
        scan_model_id=detail.scan_model_id,
        scan_model_name=detail.scan_model_name,
        is_active=True,
        warnings=detail.warnings,
    )


def get_scan_model_display_name() -> str:
    return get_active_profile_summary().scan_model_name


def _input_folder_state() -> tuple[str, str, int | None]:
    config_path = resolve_invoice_config_path()
    if not config_path.is_file():
        return "Nicht konfiguriert", "not_configured", None

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "Nicht verfügbar", "unknown", None

    folder_raw = raw.get("eingangsordner") if isinstance(raw, dict) else None
    if not isinstance(folder_raw, str) or not folder_raw.strip():
        return "Nicht konfiguriert", "not_configured", None

    from invoice_tool.ui_v2.adapters.path_display import resolve_configured_path, sanitize_path_for_display

    base_dir = config_path.parent
    folder_path = resolve_configured_path(folder_raw, base_dir=base_dir)
    summary = sanitize_path_for_display(folder_raw)
    if folder_path is None:
        return summary, "not_configured", None
    if not folder_path.exists():
        return summary, "missing", None
    if not folder_path.is_dir():
        return summary, "inaccessible", None
    try:
        pdf_count = len(list(folder_path.glob("*.pdf")))
    except OSError as exc:
        logger.warning("Eingangsordner nicht lesbar: %s", exc)
        return summary, "inaccessible", None
    return summary, "configured", pdf_count


def list_input_pdf_filenames(*, limit: int = 10, folder_override: str | None = None) -> tuple[str, ...]:
    """Return PDF basenames from configured or overridden input folder."""
    if folder_override and folder_override.strip():
        folder_path = Path(folder_override.strip()).expanduser()
        if not folder_path.is_dir():
            return tuple()
        try:
            names = sorted(path.name for path in folder_path.glob("*.pdf") if path.is_file())
        except OSError as exc:
            logger.warning("Eingangsordner-Override nicht lesbar: %s", exc)
            return tuple()
        return tuple(names[:limit])

    config_path = resolve_invoice_config_path()
    if not config_path.is_file():
        return tuple()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return tuple()
    folder_raw = raw.get("eingangsordner") if isinstance(raw, dict) else None
    if not isinstance(folder_raw, str) or not folder_raw.strip():
        return tuple()
    from invoice_tool.ui_v2.adapters.path_display import resolve_configured_path

    folder_path = resolve_configured_path(folder_raw, base_dir=config_path.parent)
    if folder_path is None or not folder_path.is_dir():
        return tuple()
    try:
        names = sorted(path.name for path in folder_path.glob("*.pdf") if path.is_file())
    except OSError as exc:
        logger.warning("Eingangsordner nicht lesbar: %s", exc)
        return tuple()
    return tuple(names[:limit])


def get_workspace_summary() -> WorkspaceSummaryVM:
    warnings: list[str] = []
    input_summary, input_state, input_count = _input_folder_state()
    latest_run = get_latest_run_summary()
    destinations = get_destination_summaries()
    config_page = get_configurations_page_vm()
    results = get_latest_result_summaries()
    result_count = count_result_items()
    review = get_review_summary()

    if input_state == "missing":
        warnings.append("Der konfigurierte Eingangsordner ist nicht erreichbar.")
    elif input_state == "inaccessible":
        warnings.append("Der Eingangsordner konnte nicht gelesen werden.")
    warnings.extend(latest_run.warnings)

    return WorkspaceSummaryVM(
        input_folder_summary=input_summary,
        input_folder_state=input_state,  # type: ignore[arg-type]
        input_file_count=input_count,
        latest_run=latest_run,
        result_count=result_count,
        review_count=review.review_count,
        destination_count=len(destinations),
        missing_destination_count=config_page.missing_destination_count,
        destinations=destinations,
        results=results,
        warnings=tuple(warnings),
    )


def load_read_only_snapshot() -> UiV2ReadOnlySnapshot:
    warnings: list[str] = []
    profile = get_active_profile_detail()
    configurations = get_configurations_page_vm()
    workspace = get_workspace_summary()
    review = get_review_summary()

    warnings.extend(profile.warnings)
    warnings.extend(configurations.warnings)
    warnings.extend(workspace.warnings)
    warnings.extend(review.warnings)

    return UiV2ReadOnlySnapshot(
        profile=profile,
        configurations=configurations,
        workspace=workspace,
        review=review,
        warnings=tuple(warnings),
    )


def load_foundation_snapshot() -> FoundationSnapshot:
    snapshot = load_read_only_snapshot()
    return FoundationSnapshot(
        profile=ProfileSummaryVM(
            profile_id=snapshot.profile.profile_id,
            profile_name=snapshot.profile.profile_name,
            scan_model_id=snapshot.profile.scan_model_id,
            scan_model_name=snapshot.profile.scan_model_name,
            is_active=True,
            warnings=snapshot.profile.warnings,
        ),
        configuration_count=snapshot.configurations.total_count,
        review_count=snapshot.review.review_count,
        destination_count=snapshot.workspace.destination_count,
        warnings=snapshot.warnings,
    )


__all__ = [
    "get_active_profile_detail",
    "get_active_profile_summary",
    "get_configuration_count",
    "get_configurations_page_vm",
    "get_destination_summaries",
    "get_destination_summary_count",
    "get_latest_result_summaries",
    "get_latest_run_summary",
    "get_review_count",
    "get_review_summary",
    "get_scan_model_display_name",
    "get_workspace_summary",
    "list_configuration_summaries",
    "list_profiles_summary",
    "load_foundation_snapshot",
    "load_read_only_snapshot",
    "list_input_pdf_filenames",
]
