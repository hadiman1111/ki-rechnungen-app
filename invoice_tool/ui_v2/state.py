"""Shared UI-v2 page state — no Flet Page mutation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from invoice_tool.ui_v2.configuration_rule_draft import ConfigurationRuleDraft
from invoice_tool.ui_v2.draft_models import ConfigurationDraftVM, DeleteConfirmationVM, EditMode, ProfileDraftVM
from invoice_tool.ui_v2.navigation import NAV_WORKSPACE
from invoice_tool.ui_v2.saas_profile_state import SaasProfileStateStore, new_saas_profile_state_store
from invoice_tool.ui_v2.saas_profile_draft_list_view import (
    SaasDraftListVM,
    build_saas_draft_list_vm,
)
from invoice_tool.ui_v2.saas_profile_persistence_view import (
    SaasPersistenceStatusVM,
    build_saas_persistence_status_vm,
    format_persistence_timestamp,
)
from invoice_tool.ui_v2.saas_profile_store import (
    STATUS_DELETED,
    STATUS_DELETE_NEEDS_CONFIRM,
    STATUS_EXPORTED,
    STATUS_IMPORTED,
    STATUS_LOADED,
    STATUS_MISSING_BLANK,
    STATUS_RENAMED,
    STATUS_SAVED,
    STATUS_VALIDATION_ERROR,
    SaasDraftListItem,
    SaasProfileDiskStore,
    SaasProfileStoreResult,
    new_saas_profile_disk_store,
)
from invoice_tool.ui_v2.processing_contract import (
    SOURCE_EXPLICIT_USER_SELECTION,
    SOURCE_UNSET,
    ProcessingServiceProtocol,
    default_processing_service,
)
from invoice_tool.ui_v2.processing_state import ProcessingRunState, idle_processing_state
from invoice_tool.ui_v2.finalization_dry_run_package import FinalizationDryRunPackageBag
from invoice_tool.ui_v2.finalization_preview_batch import FinalizationPreviewBatchBag
from invoice_tool.ui_v2.review_decision import ReviewDecisionBag
from invoice_tool.ui_v2.review_preview_state import ReviewPreviewUiState
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
    # Selected entry in the bounded local SaaS draft list (not internal working profile).
    saas_selected_draft_id: str | None = None
    # Armed after first delete click on the active local SaaS draft (no silent wipe).
    saas_delete_confirm_pending: bool = False

    pending_delete: DeleteConfirmationVM | None = None
    workspace_tab: str = "zielordner"
    # Explicit user-selected folders only — never Desktop/private defaults; never auto-created.
    workspace_input_folder_override: str | None = None
    workspace_input_folder_source: str = SOURCE_UNSET
    workspace_output_folder_override: str | None = None
    workspace_output_folder_source: str = SOURCE_UNSET
    # Sandbox contract readiness — defaults keep productive execution blocked.
    # No automatic folder creation; paths only from explicit future UI wiring.
    workspace_sandbox_mode: bool = False
    workspace_sandbox_root: str | None = None
    workspace_original_source_folder: str | None = None
    workspace_copied_data_confirmed: bool = False
    workspace_expanded_results: set[str] = field(default_factory=set)
    workspace_rename_drafts: dict[str, str] = field(default_factory=dict)
    # Explicit local path for run-result export (JSON/CSV) — never auto-chosen.
    workspace_export_path_draft: str = ""
    workspace_export_feedback: str = ""
    workspace_export_feedback_error: bool = False
    # Prompt 16/34 — controlled Preview Export package feedback (sandbox output only).
    workspace_preview_export_feedback: str = ""
    workspace_preview_export_feedback_error: bool = False
    workspace_last_preview_export_folder: str = ""
    # Prompt 31/34 — Finalization dry-run package feedback (sandbox output only).
    workspace_finalization_dry_run_feedback: str = ""
    workspace_finalization_dry_run_feedback_error: bool = False
    workspace_last_finalization_dry_run_folder: str = ""
    # Last CTA feedback for the workspace start/sandbox button (always visible after click).
    workspace_start_feedback: str = ""
    # Compact run-interaction state for manual-test UX (idle → checking → blocked/…).
    workspace_run_interaction_status: str = "idle"
    workspace_start_feedback_primary: str = ""
    workspace_start_feedback_details: list[str] = field(default_factory=list)

    # Bounded UI-v2 processing contract (default: not connected — no PDF IO).
    # Live Track-B UI injects LocalProcessingAdapter in app.build_ui_v2.
    processing_service: ProcessingServiceProtocol = field(default_factory=default_processing_service)
    processing_run_state: ProcessingRunState = field(default_factory=idle_processing_state)
    # Prompt 15/34 — Review-bucket preview selection / actions (in-memory only).
    review_preview_ui: ReviewPreviewUiState = field(default_factory=ReviewPreviewUiState)
    # Prompt 29/34 — Review decision / finalization-readiness (in-memory only).
    review_decision_ui: ReviewDecisionBag = field(default_factory=ReviewDecisionBag)
    # Prompt 30/34 — Finalization preview batch & conflicts (in-memory only).
    finalization_preview_batch_ui: FinalizationPreviewBatchBag = field(
        default_factory=FinalizationPreviewBatchBag
    )
    # Prompt 31/34 — Finalization dry-run package & audit (in-memory only).
    finalization_dry_run_package_ui: FinalizationDryRunPackageBag = field(
        default_factory=FinalizationDryRunPackageBag
    )
    # Prompt 26/34 — configuration rule draft from coverage guidance (unsaved until confirm).
    configuration_rule_draft: ConfigurationRuleDraft | None = None
    configuration_rule_draft_feedback: str = ""
    configuration_rule_draft_feedback_error: bool = False
    configuration_rule_manual_keep_unclear: bool = False
    # Prompt 27/34 — after explicit save, expose preview-only apply/rerun action.
    configuration_rule_apply_available: bool = False
    configuration_rule_apply_feedback: str = ""
    configuration_rule_apply_feedback_error: bool = False
    configuration_rule_last_saved_draft: ConfigurationRuleDraft | None = None
    configuration_rule_last_saved_configuration_id: str | None = None
    configuration_rule_apply_last_result: Any | None = None

    # Track-B smoke blocker repair — copy/debug + duplicate remediation (UI-v2 only).
    track_b_smoke_last_copy_text: str = ""
    track_b_smoke_last_copy_kind: str = ""
    track_b_smoke_copy_feedback: str = ""
    track_b_smoke_copy_feedback_error: bool = False
    track_b_duplicate_report_text: str = ""
    track_b_duplicate_remediation_feedback: str = ""
    track_b_duplicate_remediation_feedback_error: bool = False

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

    def set_workspace_input_folder(self, path: str | None) -> None:
        """Store an explicitly selected input folder path string — no FS create/scan."""

        cleaned = (path or "").strip() or None
        self.workspace_input_folder_override = cleaned
        self.workspace_input_folder_source = (
            SOURCE_EXPLICIT_USER_SELECTION if cleaned else SOURCE_UNSET
        )

    def set_workspace_output_folder(self, path: str | None) -> None:
        """Store an explicitly selected output folder path string — no FS create/scan."""

        cleaned = (path or "").strip() or None
        self.workspace_output_folder_override = cleaned
        self.workspace_output_folder_source = (
            SOURCE_EXPLICIT_USER_SELECTION if cleaned else SOURCE_UNSET
        )

    def clear_workspace_folder_selection(self) -> None:
        """Clear both workspace folder overrides and source markers."""

        self.set_workspace_input_folder(None)
        self.set_workspace_output_folder(None)

    def has_explicit_workspace_folder_selection(self) -> bool:
        """True when UI state marks any folder as an explicit user selection."""

        if self.workspace_input_folder_source == SOURCE_EXPLICIT_USER_SELECTION:
            return True
        if self.workspace_output_folder_source == SOURCE_EXPLICIT_USER_SELECTION:
            return True
        # Backward-compatible: tests/direct assign of override path strings.
        if (self.workspace_input_folder_override or "").strip():
            return True
        if (self.workspace_output_folder_override or "").strip():
            return True
        return False

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
        """Inject a store path or drafts directory (tests). Never points at Hadi profiles."""

        self.saas_disk_store = new_saas_profile_disk_store(store_path)
        self.saas_selected_draft_id = None
        self.saas_delete_confirm_pending = False

    def saas_persistence_status_vm(self) -> SaasPersistenceStatusVM:
        """Visible local-draft persistence status for Profile/Configuration pages."""

        return build_saas_persistence_status_vm(
            store_status=self.saas_disk_last_status,
            persistence_label=self.saas_disk_persistence_label,
            last_saved_at=self.saas_disk_last_saved_at,
            last_loaded_at=self.saas_disk_last_loaded_at,
            last_error=self.saas_disk_last_error,
        )

    def list_saas_drafts(self) -> tuple[SaasDraftListItem, ...]:
        return self.saas_disk_store.list_drafts()

    def saas_draft_list_vm(self) -> SaasDraftListVM:
        return build_saas_draft_list_vm(
            self.list_saas_drafts(),
            selected_draft_id=self.saas_selected_draft_id,
            delete_confirm_pending=self.saas_delete_confirm_pending,
        )

    def select_saas_draft(self, draft_id: str | None) -> None:
        self.saas_selected_draft_id = (draft_id or "").strip() or None
        self.saas_delete_confirm_pending = False

    def create_saas_draft(self, display_name: str | None = None) -> SaasProfileStoreResult:
        """Create a new generic local SaaS draft and select it."""

        profile = self.saas_draft_store.begin_blank_profile()
        result = self.saas_disk_store.create_draft(
            display_name=display_name,
            profile_draft=profile,
            configuration_draft=self.saas_draft_store.configuration_draft,
        )
        self._apply_saas_disk_result(result, operation="save")
        if result.ok and result.draft_id:
            self.saas_selected_draft_id = result.draft_id
            self.saas_delete_confirm_pending = False
            if result.profile_draft is not None:
                self.saas_draft_store.profile_draft = result.profile_draft
            self.saas_draft_store.configuration_draft = result.configuration_draft
        return result

    def rename_saas_draft(
        self,
        new_display_name: str,
        draft_id: str | None = None,
    ) -> SaasProfileStoreResult:
        """Rename the selected (or explicit) local SaaS draft display name only."""

        target_id = (draft_id or self.saas_selected_draft_id or "").strip()
        if not target_id:
            result = SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=self.saas_disk_store.store_path,
                error="Kein lokaler Entwurf gewählt.",
            )
            self._apply_saas_disk_result(result, operation="rename")
            return result
        result = self.saas_disk_store.rename_draft(target_id, new_display_name)
        self._apply_saas_disk_result(result, operation="rename")
        if result.ok:
            self.saas_selected_draft_id = result.draft_id or target_id
            self.saas_delete_confirm_pending = False
        return result

    def delete_saas_draft(
        self,
        draft_id: str | None = None,
        *,
        confirmed: bool = False,
    ) -> SaasProfileStoreResult:
        """Delete a local SaaS draft. Active selection requires an explicit confirm step."""

        target_id = (draft_id or self.saas_selected_draft_id or "").strip()
        if not target_id:
            result = SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=self.saas_disk_store.store_path,
                error="Kein lokaler Entwurf gewählt.",
            )
            self._apply_saas_disk_result(result, operation="delete")
            return result

        deleting_selected = target_id == self.saas_selected_draft_id
        if deleting_selected and not confirmed:
            self.saas_delete_confirm_pending = True
            try:
                path = self.saas_disk_store.draft_file_path(target_id)
            except ValueError:
                path = self.saas_disk_store.store_path
            result = SaasProfileStoreResult(
                ok=False,
                status=STATUS_DELETE_NEEDS_CONFIRM,
                path=path,
                error=(
                    "Aktiven lokalen Entwurf löschen? Erneut „Entwurf löschen“ bestätigen. "
                    "Nicht Cloud-synchronisiert — nur lokale Datei."
                ),
                draft_id=target_id,
            )
            self._apply_saas_disk_result(result, operation="delete")
            return result

        result = self.saas_disk_store.delete_draft(target_id)
        self._apply_saas_disk_result(result, operation="delete")
        if not result.ok:
            return result

        self.saas_delete_confirm_pending = False
        if deleting_selected or self.saas_selected_draft_id == target_id:
            # Clear selection safely; do not invent private or blank defaults silently.
            remaining = [item for item in self.list_saas_drafts() if item.draft_id != target_id]
            self.saas_selected_draft_id = remaining[0].draft_id if remaining else None
            self.saas_draft_store.profile_draft = None
            self.saas_draft_store.configuration_draft = None
        return result

    def load_saas_draft(self, draft_id: str | None = None) -> SaasProfileStoreResult:
        """Load a selected (or explicit) local SaaS draft. Corrupt/missing do not overwrite."""

        target_id = (draft_id or self.saas_selected_draft_id or "").strip()
        if not target_id:
            return self.load_saas_drafts_from_disk()
        prior_profile = self.saas_draft_store.profile_draft
        prior_config = self.saas_draft_store.configuration_draft
        result = self.saas_disk_store.load_draft(target_id)
        self._apply_saas_disk_result(result, operation="load")
        if result.ok and result.profile_draft is not None:
            self.saas_selected_draft_id = result.draft_id or target_id
            self.saas_draft_store.profile_draft = result.profile_draft
            self.saas_draft_store.configuration_draft = result.configuration_draft
        else:
            # Keep in-memory drafts unchanged on corrupt/missing.
            self.saas_draft_store.profile_draft = prior_profile
            self.saas_draft_store.configuration_draft = prior_config
        return result

    def save_saas_drafts_to_disk(self) -> SaasProfileStoreResult:
        """Persist current generic SaaS drafts locally (no cloud, no working profile)."""

        profile = self.saas_draft_store.profile_draft or self.saas_draft_store.begin_blank_profile()
        if self.saas_selected_draft_id:
            result = self.saas_disk_store.save_draft(
                self.saas_selected_draft_id,
                profile,
                self.saas_draft_store.configuration_draft,
            )
        else:
            result = self.saas_disk_store.save(
                profile,
                self.saas_draft_store.configuration_draft,
            )
        self._apply_saas_disk_result(result, operation="save")
        if result.ok and result.draft_id:
            self.saas_selected_draft_id = result.draft_id
        return result

    def load_saas_drafts_from_disk(self) -> SaasProfileStoreResult:
        """Load generic SaaS drafts from the local disk store."""

        if self.saas_selected_draft_id:
            return self.load_saas_draft(self.saas_selected_draft_id)
        prior_profile = self.saas_draft_store.profile_draft
        prior_config = self.saas_draft_store.configuration_draft
        result = self.saas_disk_store.load()
        self._apply_saas_disk_result(result, operation="load")
        if result.ok and result.profile_draft is not None:
            self.saas_draft_store.profile_draft = result.profile_draft
            self.saas_draft_store.configuration_draft = result.configuration_draft
            if result.draft_id:
                self.saas_selected_draft_id = result.draft_id
        elif not result.ok:
            self.saas_draft_store.profile_draft = prior_profile
            self.saas_draft_store.configuration_draft = prior_config
        return result

    def export_saas_draft(
        self,
        export_path: Path | str,
        draft_id: str | None = None,
    ) -> SaasProfileStoreResult:
        """Export the selected (or explicit) local SaaS draft to ``export_path``."""

        target_id = (draft_id or self.saas_selected_draft_id or "").strip()
        target = Path(export_path)
        if not target_id:
            result = SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=target,
                error="Kein lokaler Entwurf gewählt.",
            )
            self._apply_saas_disk_result(result, operation="export")
            return result
        result = self.saas_disk_store.export_draft(target_id, target)
        self._apply_saas_disk_result(result, operation="export")
        return result

    def export_run_report(self, export_path: Path | str | None = None):
        """Export the current ProcessingRunState report to an explicit local path.

        Writes only JSON/CSV report artifacts — never mutates original documents
        and never starts processing.
        """

        from invoice_tool.ui_v2.export_reporting import (
            MSG_EXPORT_NEEDS_PATH,
            MSG_EXPORT_OK,
            export_processing_run_state,
        )

        path = str(export_path or self.workspace_export_path_draft or "").strip()
        self.workspace_export_path_draft = path
        if not path:
            self.workspace_export_feedback = MSG_EXPORT_NEEDS_PATH
            self.workspace_export_feedback_error = True
            return None
        result = export_processing_run_state(self.processing_run_state, path)
        if result.ok:
            self.workspace_export_feedback = MSG_EXPORT_OK
            self.workspace_export_feedback_error = False
        else:
            self.workspace_export_feedback = result.error or "Export fehlgeschlagen."
            self.workspace_export_feedback_error = True
        return result

    def write_preview_export_to_output(self):
        """Write a controlled Preview Export package into the sandbox output folder.

        Preview copies + manifests only — never mutates inputs, never final productive
        write, never calls run_once.
        """

        from invoice_tool.ui_v2.preview_export import apply_workspace_preview_export

        return apply_workspace_preview_export(self)

    def write_finalization_dry_run_package_to_output(self):
        """Write a controlled Finalization Dry-Run audit package (text artifacts only).

        Never writes final PDFs, never mutates inputs, never calls run_once,
        never sets final_write_allowed=True.
        """

        from invoice_tool.ui_v2.finalization_dry_run_package import (
            apply_finalization_dry_run_package,
        )

        return apply_finalization_dry_run_package(self)

    def import_saas_draft(
        self,
        import_path: Path | str,
        preferred_display_name: str | None = None,
    ) -> SaasProfileStoreResult:
        """Import a local SaaS draft export as a new draft and select it."""

        source = Path(import_path)
        prior_profile = self.saas_draft_store.profile_draft
        prior_config = self.saas_draft_store.configuration_draft
        prior_selected = self.saas_selected_draft_id
        result = self.saas_disk_store.import_draft(
            source,
            preferred_display_name=preferred_display_name,
        )
        self._apply_saas_disk_result(result, operation="import")
        if result.ok and result.draft_id:
            self.saas_selected_draft_id = result.draft_id
            self.saas_delete_confirm_pending = False
            if result.profile_draft is not None:
                self.saas_draft_store.profile_draft = result.profile_draft
            self.saas_draft_store.configuration_draft = result.configuration_draft
        else:
            # Keep prior selection/drafts unchanged on invalid/corrupt/private import.
            self.saas_selected_draft_id = prior_selected
            self.saas_draft_store.profile_draft = prior_profile
            self.saas_draft_store.configuration_draft = prior_config
        return result

    def _apply_saas_disk_result(self, result: SaasProfileStoreResult, *, operation: str) -> None:
        self.saas_disk_persistence_label = result.persistence_label
        self.saas_disk_last_status = result.status
        self.saas_disk_last_error = result.error
        stamp = format_persistence_timestamp()
        if result.ok and result.status == STATUS_SAVED and operation == "save":
            self.saas_disk_last_saved_at = stamp
        if result.ok and result.status == STATUS_RENAMED and operation == "rename":
            self.saas_disk_last_saved_at = stamp
        if result.ok and result.status == STATUS_DELETED and operation == "delete":
            # Deletion is a local disk change; keep timestamp as last successful mutation.
            self.saas_disk_last_saved_at = stamp
        if result.ok and result.status == STATUS_IMPORTED and operation == "import":
            self.saas_disk_last_saved_at = stamp
            self.saas_disk_last_loaded_at = stamp
        if result.ok and result.status == STATUS_EXPORTED and operation == "export":
            # Export writes outside the store; keep local selection timestamps unchanged
            # but surface a clear success stamp via saved_at for UX feedback.
            self.saas_disk_last_saved_at = stamp
        if result.ok and result.status == STATUS_LOADED and operation == "load":
            self.saas_disk_last_loaded_at = stamp
        if not result.ok:
            # Keep prior timestamps; surface error via last_error / status VM.
            return
