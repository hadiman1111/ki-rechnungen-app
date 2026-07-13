"""Explicit edit-state view models for UI-v2 write controls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from invoice_tool.configuration_model import Configuration, FilenamePattern, MatchingRule, UnmatchedConfiguration


EditMode = Literal["view", "create", "edit", "unmatched"]


@dataclass
class MatchingRuleDraftVM:
    feature_key: str = ""
    operator: str = "ist"
    values: list[str] = field(default_factory=list)

    @classmethod
    def from_rule(cls, rule: MatchingRule | None) -> MatchingRuleDraftVM:
        if rule is None:
            return cls()
        return cls(
            feature_key=rule.feature_key,
            operator=rule.operator or "ist",
            values=list(rule.values),
        )

    def to_rule(self) -> MatchingRule:
        return MatchingRule(
            feature_key=self.feature_key.strip(),
            operator=self.operator or "ist",
            values=[value.strip() for value in self.values if str(value or "").strip()],
        )


@dataclass
class FilenamePreviewVM:
    pattern_summary: str = ""
    example_filename: str = ""
    issues: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class FolderSelectionVM:
    raw_path: str = ""
    display_path: str = ""
    exists_on_disk: bool = False
    issues: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class ValidationIssueVM:
    field: str
    message: str


@dataclass
class ProfileDraftVM:
    profile_id: str | None = None
    name: str = ""
    scan_model_id: str = ""
    is_new: bool = False


@dataclass
class ConfigurationDraftVM:
    configuration_id: str | None = None
    name: str = ""
    active: bool = True
    matching: MatchingRuleDraftVM = field(default_factory=MatchingRuleDraftVM)
    filename_pattern: FilenamePattern = field(default_factory=FilenamePattern)
    destination_path: str = ""
    sort_index: int = 0
    is_new: bool = False
    is_unmatched: bool = False

    @classmethod
    def from_configuration(cls, config: Configuration, *, sort_index: int = 0) -> ConfigurationDraftVM:
        return cls(
            configuration_id=config.id,
            name=config.name,
            active=config.active,
            matching=MatchingRuleDraftVM.from_rule(config.matching),
            filename_pattern=FilenamePattern.from_dict(config.filename_pattern.to_dict()),
            destination_path=str((config.destination or {}).get("path") or ""),
            sort_index=sort_index,
            is_new=False,
            is_unmatched=False,
        )

    @classmethod
    def from_unmatched(cls, unmatched: UnmatchedConfiguration) -> ConfigurationDraftVM:
        return cls(
            configuration_id="unmatched",
            name=unmatched.name,
            active=True,
            matching=MatchingRuleDraftVM(),
            filename_pattern=FilenamePattern.from_dict(unmatched.filename_pattern.to_dict()),
            destination_path=str((unmatched.destination or {}).get("path") or ""),
            sort_index=0,
            is_new=False,
            is_unmatched=True,
        )

    def to_configuration(self) -> Configuration:
        return Configuration(
            id=self.configuration_id or "",
            name=self.name.strip() or "Neue Konfiguration",
            active=self.active,
            matching=self.matching.to_rule(),
            filename_pattern=FilenamePattern.from_dict(self.filename_pattern.to_dict()),
            destination={"type": "local_folder", "path": self.destination_path.strip()},
        )

    def to_unmatched(self) -> UnmatchedConfiguration:
        return UnmatchedConfiguration(
            name=self.name.strip() or "Nicht zugeordnete Dokumente",
            filename_pattern=FilenamePattern.from_dict(self.filename_pattern.to_dict()),
            destination={"type": "local_folder", "path": self.destination_path.strip()},
        )


@dataclass
class DeleteConfirmationVM:
    title: str
    message: str
    confirm_label: str = "Löschen"
    target_id: str = ""
    target_kind: Literal["profile", "configuration"] = "configuration"


@dataclass
class UnsavedChangesVM:
    message: str = "Es gibt ungespeicherte Änderungen."
    pending_action: str = ""
