"""UX presenter for local SaaS UI-v2 profile draft persistence status.

Separates generic SaaS drafts from the internal working profile in UI copy.
Surfaces save/load/corrupt status without claiming cloud sync or tenant backend.
No private Hadi/SOMAA/AMEX-1005/EP defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from invoice_tool.ui_v2.saas_profile_store import (
    STATUS_CORRUPTED,
    STATUS_DELETED,
    STATUS_DELETE_NEEDS_CONFIRM,
    STATUS_EXPORTED,
    STATUS_IMPORTED,
    STATUS_IO_ERROR,
    STATUS_LOADED,
    STATUS_MISSING_BLANK,
    STATUS_PRIVATE_DEFAULTS,
    STATUS_RENAMED,
    STATUS_SAVED,
    STATUS_VALIDATION_ERROR,
    SaasProfileStoreResult,
)

if TYPE_CHECKING:
    import flet as ft

# User-facing status labels (SaaS draft only — not internal working profile).
UX_STATUS_UNSAVED = "Nicht gespeichert"
UX_STATUS_SAVED = "Lokal gespeichert"
UX_STATUS_LOADED = "Lokal geladen"
UX_STATUS_RENAMED = "Lokal umbenannt"
UX_STATUS_DELETED = "Lokal gelöscht"
UX_STATUS_EXPORTED = "Lokal exportiert"
UX_STATUS_IMPORTED = "Lokal importiert"
UX_STATUS_DELETE_CONFIRM = "Löschen bestätigen"
UX_STATUS_CORRUPTED = "Lokaler Draft beschädigt"
UX_STATUS_VALIDATION = "Validierungsfehler"
UX_STATUS_PRIVATE = "Private Defaults blockiert"
UX_STATUS_IO = "Speicherfehler"

SEPARATION_HELP = (
    "Dieser Entwurf ist ein lokaler UI-v2-Profilentwurf und nicht das interne Arbeitsprofil."
)
NO_CLOUD_HELP = "Nicht Cloud-synchronisiert."
SCOPE_LABEL = "Lokaler Entwurf"

# Must never appear in user-facing persistence UX copy.
_PRIVATE_UI_MARKERS: tuple[str, ...] = (
    "SOMAA",
    "Hadi",
    "AMEX-1005",
    "EP",
    "Bismarck",
    "97368",
    "DE189",
    "voba",
)

# Phrases that would falsely promise cloud/tenant persistence.
_FORBIDDEN_CLOUD_CLAIMS: tuple[str, ...] = (
    "Cloud-Sync aktiv",
    "mit der Cloud synchronisiert",
    "Mandantenbackend",
    "in der Cloud gespeichert",
)


@dataclass(frozen=True)
class SaasPersistenceStatusVM:
    """Presenter model for local SaaS draft persistence status."""

    status_label: str
    scope_label: str
    separation_help: str
    no_cloud_help: str
    timestamp_text: str
    error_text: str
    is_error: bool
    locally_persisted: bool
    store_status: str
    badge_tone: str

    @property
    def summary_line(self) -> str:
        parts = [f"{self.scope_label}: {self.status_label}"]
        if self.timestamp_text:
            parts.append(self.timestamp_text)
        return " — ".join(parts)

    def all_ui_texts(self) -> tuple[str, ...]:
        return tuple(
            text
            for text in (
                self.status_label,
                self.scope_label,
                self.separation_help,
                self.no_cloud_help,
                self.timestamp_text,
                self.error_text,
                self.summary_line,
            )
            if text
        )


def map_store_status_to_ux_label(store_status: str | None) -> str:
    """Map store status codes to user-facing UX labels."""

    mapping = {
        STATUS_SAVED: UX_STATUS_SAVED,
        STATUS_LOADED: UX_STATUS_LOADED,
        STATUS_RENAMED: UX_STATUS_RENAMED,
        STATUS_DELETED: UX_STATUS_DELETED,
        STATUS_EXPORTED: UX_STATUS_EXPORTED,
        STATUS_IMPORTED: UX_STATUS_IMPORTED,
        STATUS_DELETE_NEEDS_CONFIRM: UX_STATUS_DELETE_CONFIRM,
        STATUS_MISSING_BLANK: UX_STATUS_UNSAVED,
        STATUS_CORRUPTED: UX_STATUS_CORRUPTED,
        STATUS_VALIDATION_ERROR: UX_STATUS_VALIDATION,
        STATUS_PRIVATE_DEFAULTS: UX_STATUS_PRIVATE,
        STATUS_IO_ERROR: UX_STATUS_IO,
        None: UX_STATUS_UNSAVED,
        "": UX_STATUS_UNSAVED,
    }
    if store_status in mapping:
        return mapping[store_status]
    # Fall back for already-localized labels from the store.
    if store_status == "Beschädigte Datei":
        return UX_STATUS_CORRUPTED
    if store_status in {
        UX_STATUS_UNSAVED,
        UX_STATUS_SAVED,
        UX_STATUS_LOADED,
        UX_STATUS_RENAMED,
        UX_STATUS_DELETED,
        UX_STATUS_EXPORTED,
        UX_STATUS_IMPORTED,
        UX_STATUS_DELETE_CONFIRM,
        UX_STATUS_CORRUPTED,
        UX_STATUS_VALIDATION,
        UX_STATUS_PRIVATE,
        UX_STATUS_IO,
    }:
        return store_status
    return UX_STATUS_UNSAVED


def build_saas_persistence_status_vm(
    *,
    store_result: SaasProfileStoreResult | None = None,
    store_status: str | None = None,
    persistence_label: str | None = None,
    last_saved_at: str | None = None,
    last_loaded_at: str | None = None,
    last_error: str | None = None,
) -> SaasPersistenceStatusVM:
    """Derive visible save/load/corrupt status for SaaS drafts."""

    status_code = store_status
    error = last_error
    locally_persisted = False

    if store_result is not None:
        status_code = store_result.status
        error = store_result.error
        locally_persisted = bool(store_result.locally_persisted)
    elif status_code is None and persistence_label:
        status_code = _infer_status_from_label(persistence_label)

    if status_code is None:
        status_code = STATUS_MISSING_BLANK

    label = map_store_status_to_ux_label(status_code)
    is_error = status_code in {
        STATUS_CORRUPTED,
        STATUS_VALIDATION_ERROR,
        STATUS_PRIVATE_DEFAULTS,
        STATUS_IO_ERROR,
    }
    if store_result is not None and not store_result.ok:
        # Needs-confirm is a guarded warn state, not a hard persistence failure.
        is_error = status_code != STATUS_DELETE_NEEDS_CONFIRM
    if status_code == STATUS_DELETE_NEEDS_CONFIRM:
        is_error = False

    timestamp_text = _format_timestamp_text(
        status_code=status_code,
        last_saved_at=last_saved_at,
        last_loaded_at=last_loaded_at,
    )
    error_text = ""
    if error and (is_error or status_code == STATUS_DELETE_NEEDS_CONFIRM):
        if status_code == STATUS_CORRUPTED:
            error_text = f"Lokaler Draft beschädigt: {error}"
        else:
            error_text = error

    badge_tone = (
        "error"
        if is_error
        else (
            "success"
            if locally_persisted
            or status_code
            in {
                STATUS_SAVED,
                STATUS_LOADED,
                STATUS_RENAMED,
                STATUS_DELETED,
                STATUS_EXPORTED,
                STATUS_IMPORTED,
            }
            else "neutral"
        )
    )

    vm = SaasPersistenceStatusVM(
        status_label=label,
        scope_label=SCOPE_LABEL,
        separation_help=SEPARATION_HELP,
        no_cloud_help=NO_CLOUD_HELP,
        timestamp_text=timestamp_text,
        error_text=error_text,
        is_error=is_error,
        locally_persisted=locally_persisted
        or status_code
        in {STATUS_SAVED, STATUS_LOADED, STATUS_RENAMED, STATUS_IMPORTED, STATUS_EXPORTED},
        store_status=status_code,
        badge_tone=badge_tone,
    )
    _assert_ux_copy_safe(vm)
    return vm


def build_blank_saas_persistence_status_vm() -> SaasPersistenceStatusVM:
    return build_saas_persistence_status_vm(store_status=STATUS_MISSING_BLANK)


def format_persistence_timestamp(moment: datetime | None = None) -> str:
    """Local wall-clock stamp for save/load feedback (not a cloud sync time)."""

    value = moment or datetime.now().astimezone()
    return value.strftime("%d.%m.%Y %H:%M:%S")


def find_private_persistence_ux_violations(texts: tuple[str, ...] | list[str]) -> list[str]:
    violations: list[str] = []
    for text in texts:
        for marker in _PRIVATE_UI_MARKERS:
            if marker in text:
                violations.append(f"private_marker:{marker}")
    return violations


def find_forbidden_cloud_claim_violations(texts: tuple[str, ...] | list[str]) -> list[str]:
    violations: list[str] = []
    for text in texts:
        lowered = text.lower()
        for claim in _FORBIDDEN_CLOUD_CLAIMS:
            if claim.lower() in lowered:
                violations.append(f"cloud_claim:{claim}")
        # Positive sync promise variants.
        # "Cloud-synchronisiert" contains the substring "cloud-sync"; allow honest
        # negations such as "Nicht Cloud-synchronisiert" / "keine Cloud-…".
        negation_markers = (
            "keine",
            "kein cloud",
            "noch keine",
            "noch keine cloud",
            "nicht cloud",
            "nicht cloud-synchronisiert",
            "nicht cloud-sync",
        )
        if "cloud-sync" in lowered and not any(marker in lowered for marker in negation_markers):
            violations.append("cloud_claim:cloud-sync")
    return violations


def build_saas_persistence_status_panel(vm: SaasPersistenceStatusVM) -> Any:
    """Flet control showing local SaaS draft persistence status (no cloud claim)."""

    import flet as ft

    from invoice_tool.ui_v2.components import inline_error, status_badge
    from invoice_tool.ui_v2.edit_components import helper_text
    from invoice_tool.ui_v2.theme import COLOR_TEXT_PRIMARY, SPACE_SM, SPACE_XS

    rows: list[ft.Control] = [
        ft.Row(
            [
                status_badge(vm.status_label, tone=vm.badge_tone),
                ft.Text(
                    vm.scope_label,
                    size=12,
                    weight=ft.FontWeight.W_600,
                    color=COLOR_TEXT_PRIMARY,
                ),
            ],
            spacing=SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        ),
        helper_text(vm.separation_help),
        helper_text(vm.no_cloud_help),
    ]
    if vm.timestamp_text:
        rows.append(helper_text(vm.timestamp_text))
    if vm.error_text:
        rows.append(inline_error(vm.error_text))
    return ft.Column(rows, spacing=SPACE_XS, tight=True)


def _infer_status_from_label(label: str) -> str:
    normalized = (label or "").strip()
    reverse = {
        UX_STATUS_SAVED: STATUS_SAVED,
        UX_STATUS_LOADED: STATUS_LOADED,
        UX_STATUS_RENAMED: STATUS_RENAMED,
        UX_STATUS_DELETED: STATUS_DELETED,
        UX_STATUS_EXPORTED: STATUS_EXPORTED,
        UX_STATUS_IMPORTED: STATUS_IMPORTED,
        UX_STATUS_DELETE_CONFIRM: STATUS_DELETE_NEEDS_CONFIRM,
        UX_STATUS_UNSAVED: STATUS_MISSING_BLANK,
        UX_STATUS_CORRUPTED: STATUS_CORRUPTED,
        "Beschädigte Datei": STATUS_CORRUPTED,
        UX_STATUS_VALIDATION: STATUS_VALIDATION_ERROR,
        UX_STATUS_PRIVATE: STATUS_PRIVATE_DEFAULTS,
        UX_STATUS_IO: STATUS_IO_ERROR,
    }
    return reverse.get(normalized, STATUS_MISSING_BLANK)


def _format_timestamp_text(
    *,
    status_code: str,
    last_saved_at: str | None,
    last_loaded_at: str | None,
) -> str:
    if status_code == STATUS_SAVED and last_saved_at:
        return f"Zuletzt lokal gespeichert: {last_saved_at}"
    if status_code == STATUS_IMPORTED and last_loaded_at:
        return f"Zuletzt lokal importiert: {last_loaded_at}"
    if status_code == STATUS_EXPORTED and last_saved_at:
        return f"Zuletzt lokal exportiert: {last_saved_at}"
    if status_code == STATUS_LOADED and last_loaded_at:
        return f"Zuletzt lokal geladen: {last_loaded_at}"
    if status_code == STATUS_LOADED and last_saved_at and not last_loaded_at:
        return f"Zuletzt lokal gespeichert: {last_saved_at}"
    if last_saved_at and status_code == STATUS_MISSING_BLANK:
        return ""
    if last_saved_at and status_code not in {STATUS_CORRUPTED, STATUS_VALIDATION_ERROR}:
        if status_code == STATUS_SAVED:
            return f"Zuletzt lokal gespeichert: {last_saved_at}"
    return ""


def _assert_ux_copy_safe(vm: SaasPersistenceStatusVM) -> None:
    texts = vm.all_ui_texts()
    private = find_private_persistence_ux_violations(texts)
    if private:
        raise AssertionError("Persistenz-UX enthält private Defaults: " + ", ".join(private))
    cloud = find_forbidden_cloud_claim_violations(texts)
    if cloud:
        raise AssertionError("Persistenz-UX behauptet Cloud-Persistenz: " + ", ".join(cloud))
    # Explicit positive guarantees for callers/tests.
    joined = " ".join(texts)
    assert SEPARATION_HELP in joined
    assert NO_CLOUD_HELP in joined
    assert "interne Arbeitsprofil" in joined
    assert "Nicht Cloud-synchronisiert" in joined
    assert "Lokaler Entwurf" in joined
    assert "SaaS-Profilentwurf" not in joined
