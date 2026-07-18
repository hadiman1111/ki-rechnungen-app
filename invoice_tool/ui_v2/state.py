"""Shared UI-v2 page state — no Flet Page mutation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from invoice_tool.ui_v2.draft_models import ConfigurationDraftVM, DeleteConfirmationVM, EditMode, ProfileDraftVM
from invoice_tool.ui_v2.navigation import NAV_WORKSPACE
from invoice_tool.ui_v2.saas_profile_state import SaasProfileStateStore, new_saas_profile_state_store
from invoice_tool.ui_v2.saas_profile_persistence_view import (
    SaasPersistenceStatusVM,
    build_saas_persistence_status_vm,
    format_persistence_timestamp,
)
from invoice_tool.ui_v2.saas_profile_store import (
    STATUS_LOADED,
    STATUS_MISSING_BLANK,
    STATUS_SAVED,
    SaasProfileDiskStore,
    SaasProfileStoreResult,
    new_saas_profile_disk_store,
)
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

    # In-memory generic SaaS drafts (no cloud persistence; no private defaults).
    saas_draft_store: SaasProfileStateStore = field(default_factory=new_saas_profile_state_store)
    # Bounded local disk store for SaaS drafts (injectable path; not Hadi/SOMAA profiles).
    saas_disk_store: SaasProfileDiskStore = field(default_factory=new_saas_profile_disk_store)
    saas_disk_persistence_label: str = "Nicht gespeichert"
    saas_disk_last_status: str = STATUS_MISSING_BLANK
    saas_disk_last_error: str | None = None
    saas_disk_last_saved_at: str | None = None
    saas_disk_last_loaded_at: str | None = None

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
        self.saas_draft_store.profile_draft = None

    def discard_config_edit(self) -> None:
        self.config_edit_mode = "view"
        self.config_draft = None
        self.config_feedback = ""
        self.config_feedback_error = False
        self.config_field_errors = {}
        self.saas_draft_store.configuration_draft = None

    def discard_all_edits(self) -> None:
        self.discard_profile_edit()
        self.discard_config_edit()
        self.pending_delete = None

    def configure_saas_disk_store(self, store_path: Path) -> None:
        """Inject a store path (tests / isolated runs). Never points at Hadi profiles."""

        self.saas_disk_store = new_saas_profile_disk_store(store_path)

    def saas_persistence_status_vm(self) -> SaasPersistenceStatusVM:
        """Visible local-draft persistence status for Profile/Configuration pages."""

        return build_saas_persistence_status_vm(
            store_status=self.saas_disk_last_status,
            persistence_label=self.saas_disk_persistence_label,
            last_saved_at=self.saas_disk_last_saved_at,
            last_loaded_at=self.saas_disk_last_loaded_at,
            last_error=self.saas_disk_last_error,
        )

    def save_saas_drafts_to_disk(self) -> SaasProfileStoreResult:
        """Persist current generic SaaS drafts locally (no cloud, no working profile)."""

        profile = self.saas_draft_store.profile_draft or self.saas_draft_store.begin_blank_profile()
        result = self.saas_disk_store.save(
            profile,
            self.saas_draft_store.configuration_draft,
        )
        self._apply_saas_disk_result(result, operation="save")
        return result

    def load_saas_drafts_from_disk(self) -> SaasProfileStoreResult:
        """Load generic SaaS drafts from the local disk store."""

        result = self.saas_disk_store.load()
        self._apply_saas_disk_result(result, operation="load")
        if result.ok and result.profile_draft is not None:
            self.saas_draft_store.profile_draft = result.profile_draft
            self.saas_draft_store.configuration_draft = result.configuration_draft
        return result

    def _apply_saas_disk_result(self, result: SaasProfileStoreResult, *, operation: str) -> None:
        self.saas_disk_persistence_label = result.persistence_label
        self.saas_disk_last_status = result.status
        self.saas_disk_last_error = result.error
        stamp = format_persistence_timestamp()
        if result.ok and result.status == STATUS_SAVED and operation == "save":
            self.saas_disk_last_saved_at = stamp
        if result.ok and result.status == STATUS_LOADED and operation == "load":
            self.saas_disk_last_loaded_at = stamp
        if not result.ok:
            # Keep prior timestamps; surface error via last_error / status VM.
            return
