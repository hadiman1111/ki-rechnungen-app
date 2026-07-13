"""Shared UI-v2 page state — no Flet Page mutation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from invoice_tool.ui_v2.draft_models import ConfigurationDraftVM, DeleteConfirmationVM, EditMode, ProfileDraftVM
from invoice_tool.ui_v2.navigation import NAV_WORKSPACE
from invoice_tool.ui_v2.view_models import FoundationSnapshot, UiV2ReadOnlySnapshot


@dataclass
class UiV2State:
    active_nav_id: str = NAV_WORKSPACE
    selected_profile_id: str = "local"
    snapshot: UiV2ReadOnlySnapshot | FoundationSnapshot | None = None
    warnings: list[str] = field(default_factory=list)

    profile_edit_mode: EditMode = "view"
    profile_draft: ProfileDraftVM | None = None
    profile_list_selected_id: str | None = None
    profile_feedback: str = ""
    profile_feedback_error: bool = False
    profile_field_errors: dict[str, str] = field(default_factory=dict)

    config_edit_mode: EditMode = "view"
    config_draft: ConfigurationDraftVM | None = None
    config_list_selected_id: str | None = None
    config_feedback: str = ""
    config_feedback_error: bool = False
    config_field_errors: dict[str, str] = field(default_factory=dict)

    pending_delete: DeleteConfirmationVM | None = None
    workspace_tab: str = "zielordner"
    workspace_input_folder_override: str | None = None
    workspace_expanded_results: set[str] = field(default_factory=set)
    workspace_rename_drafts: dict[str, str] = field(default_factory=dict)

    page: Any = None
    refresh: Callable[[], None] | None = None
    navigate: Callable[[str], None] | None = None
    open_dialog: Callable[[Any], None] | None = None
    close_dialog: Callable[[], None] | None = None

    def has_unsaved_profile_changes(self) -> bool:
        return self.profile_edit_mode in ("create", "edit") and self.profile_draft is not None

    def has_unsaved_config_changes(self) -> bool:
        return self.config_edit_mode in ("create", "edit", "unmatched") and self.config_draft is not None

    def has_unsaved_changes(self) -> bool:
        return self.has_unsaved_profile_changes() or self.has_unsaved_config_changes()

    def discard_profile_edit(self) -> None:
        self.profile_edit_mode = "view"
        self.profile_draft = None
        self.profile_feedback = ""
        self.profile_feedback_error = False
        self.profile_field_errors = {}

    def discard_config_edit(self) -> None:
        self.config_edit_mode = "view"
        self.config_draft = None
        self.config_feedback = ""
        self.config_feedback_error = False
        self.config_field_errors = {}

    def discard_all_edits(self) -> None:
        self.discard_profile_edit()
        self.discard_config_edit()
        self.pending_delete = None
