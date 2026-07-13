"""Read-only view models for UI-v2 pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RunAvailability = Literal["no_run", "available", "malformed"]
ReviewAvailability = Literal["no_run", "zero", "items", "unknown", "malformed"]
InputFolderState = Literal["configured", "missing", "inaccessible", "not_configured", "unknown"]


@dataclass(frozen=True)
class InlineWarningVM:
    message: str


@dataclass(frozen=True)
class ProfileSummaryVM:
    profile_id: str
    profile_name: str
    scan_model_id: str
    scan_model_name: str
    is_active: bool = False
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProfileDetailVM:
    profile_id: str
    profile_name: str
    scan_model_id: str
    scan_model_name: str
    feature_summary: str
    configuration_count: int
    active_configuration_count: int
    unmatched_configured: bool
    unmatched_destination_missing: bool
    profiles: tuple[ProfileSummaryVM, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ConfigurationSummaryVM:
    configuration_id: str
    name: str
    active: bool
    matching_summary: str
    filename_pattern_summary: str
    filename_example: str | None
    destination_summary: str
    destination_missing: bool
    sort_index: int
    matching_feature_label: str | None = None
    matching_values: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DestinationSummaryVM:
    configuration_name: str
    destination_summary: str
    destination_missing: bool
    is_unmatched: bool = False


@dataclass(frozen=True)
class RunSummaryVM:
    availability: RunAvailability
    run_id: str | None = None
    run_timestamp: str | None = None
    status_label: str = "Noch kein Lauf"
    processed_count: int | None = None
    success_count: int | None = None
    duplicate_count: int | None = None
    unclear_count: int | None = None
    error_count: int | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResultSummaryVM:
    filename: str
    configuration_label: str
    destination_summary: str
    status_label: str


@dataclass(frozen=True)
class ReviewItemVM:
    filename: str
    reason: str
    run_timestamp: str | None
    status_label: str
    configuration_label: str | None


@dataclass(frozen=True)
class ReviewSummaryVM:
    availability: ReviewAvailability
    review_count: int | None
    items: tuple[ReviewItemVM, ...] = field(default_factory=tuple)
    run_timestamp: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkspaceSummaryVM:
    input_folder_summary: str
    input_folder_state: InputFolderState
    input_file_count: int | None
    latest_run: RunSummaryVM
    result_count: int | None
    review_count: int | None
    destination_count: int
    missing_destination_count: int
    destinations: tuple[DestinationSummaryVM, ...]
    results: tuple[ResultSummaryVM, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ConfigurationsPageVM:
    profile_name: str
    configurations: tuple[ConfigurationSummaryVM, ...]
    unmatched: ConfigurationSummaryVM | None
    total_count: int
    active_count: int
    missing_destination_count: int
    unmatched_present: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class UiV2ReadOnlySnapshot:
    profile: ProfileDetailVM
    configurations: ConfigurationsPageVM
    workspace: WorkspaceSummaryVM
    review: ReviewSummaryVM
    warnings: tuple[str, ...] = field(default_factory=tuple)


# Backward-compatible aliases for Gate-1 tests
ProfileSummary = ProfileSummaryVM


@dataclass(frozen=True)
class FoundationSnapshot:
    profile: ProfileSummaryVM
    configuration_count: int | None
    review_count: int | None
    destination_count: int | None
    warnings: tuple[str, ...] = field(default_factory=tuple)
