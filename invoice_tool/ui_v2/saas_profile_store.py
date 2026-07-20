"""Bounded local disk persistence for generic UI-v2 SaaS profile drafts.

Stores only generic SaaS draft JSON under an isolated draft directory.
Does not touch Hadi/SOMAA working profiles, profile_config.local.json,
or Application Support/KI-Rechnungen/profiles/.

No cloud/auth/tenant backend. No productive processing.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from invoice_tool.saas_product_model import (
    DEFAULT_SAAS_FILENAME_PATTERN,
    DEFAULT_SAAS_PROFILE_NAME,
    DEFAULT_SAAS_REVIEW_FOLDER,
    DEFAULT_SAAS_SCAN_MODEL_ID,
    GENERIC_SCAN_MODELS,
    assert_saas_defaults_are_generic,
    classification_policy_from_dict,
    default_classification_policy,
    find_private_saas_default_violations,
)
from invoice_tool.ui_v2.saas_profile_state import SaasConfigurationDraft, SaasProfileDraft

SCHEMA_VERSION = 1
STORE_KIND = "saas_ui_v2_profile_draft"
EXPORT_KIND = "saas_profile_draft_export"
DEFAULT_DRAFT_FILENAME = "saas_profile_draft.json"
GENERIC_DRAFT_DISPLAY_PREFIX = "Lokaler Entwurf"

# Isolated from ~/Library/Application Support/KI-Rechnungen (Hadi/SOMAA working profiles).
SAAS_UI_V2_SUPPORT_DIR_NAME = "KI-Rechnungen-SaaS-UI-v2"
SAAS_UI_V2_DRAFTS_SUBDIR = "drafts"

STATUS_SAVED = "saved"
STATUS_LOADED = "loaded"
STATUS_MISSING_BLANK = "missing_blank"
STATUS_CORRUPTED = "corrupted"
STATUS_VALIDATION_ERROR = "validation_error"
STATUS_PRIVATE_DEFAULTS = "private_defaults"
STATUS_IO_ERROR = "io_error"
STATUS_RENAMED = "renamed"
STATUS_DELETED = "deleted"
STATUS_DELETE_NEEDS_CONFIRM = "delete_needs_confirm"
STATUS_EXPORTED = "exported"
STATUS_IMPORTED = "imported"

# Rejected on import/export validation (broader than product blank defaults).
IMPORT_PRIVATE_MARKERS: tuple[str, ...] = (
    "SOMAA",
    "Hadi",
    "AMEX-1005",
    "EP",
    "Bismarck",
    "Architektur",
    "97368",
    "DE189",
    "voba",
)

# Path fragments that must never be imported into a SaaS draft.
_DANGEROUS_PATH_MARKERS: tuple[str, ...] = (
    "profile_config.local.json",
    "Application Support/KI-Rechnungen/",
    "/Library/Application Support/KI-Rechnungen",
    "Desktop/RECHNUNGEN",
)

DRAFT_ITEM_OK = "ok"
DRAFT_ITEM_CORRUPTED = "corrupted"
DRAFT_ITEM_MISSING = "missing"

_DRAFT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]+")
_MANIFEST_FILENAMES = frozenset({"manifest.json", ".ds_store"})

# Paths that must never be written by this store.
FORBIDDEN_WRITE_BASENAMES: frozenset[str] = frozenset(
    {
        "profile_config.local.json",
        "profile_config.example.json",
        "profile_state.json",
        "invoice_config.json",
        "office_rules.json",
    }
)


@dataclass(frozen=True)
class SaasDraftListItem:
    """Metadata row for one local SaaS draft (not an internal working profile)."""

    draft_id: str
    display_name: str
    created_at: str
    updated_at: str
    status: str
    path: Path
    error: str | None = None

    @property
    def is_usable(self) -> bool:
        return self.status == DRAFT_ITEM_OK

    @property
    def locality_label(self) -> str:
        return "lokal / nicht Cloud"


@dataclass(frozen=True)
class SaasProfileStoreResult:
    """Outcome of a save or load operation."""

    ok: bool
    status: str
    path: Path
    profile_draft: SaasProfileDraft | None = None
    configuration_draft: SaasConfigurationDraft | None = None
    error: str | None = None
    private_default_violations: tuple[str, ...] = ()
    locally_persisted: bool = False
    draft_id: str | None = None
    display_name: str | None = None

    @property
    def persistence_label(self) -> str:
        if self.status == STATUS_SAVED and self.ok:
            return "Lokal gespeichert"
        if self.status == STATUS_LOADED and self.ok:
            return "Lokal geladen"
        if self.status == STATUS_RENAMED and self.ok:
            return "Lokal umbenannt"
        if self.status == STATUS_DELETED and self.ok:
            return "Lokal gelöscht"
        if self.status == STATUS_EXPORTED and self.ok:
            return "Lokal exportiert"
        if self.status == STATUS_IMPORTED and self.ok:
            return "Lokal importiert"
        if self.status == STATUS_DELETE_NEEDS_CONFIRM:
            return "Löschen bestätigen"
        if self.status == STATUS_MISSING_BLANK:
            return "Nicht gespeichert"
        if self.status == STATUS_CORRUPTED:
            return "Lokaler Draft beschädigt"
        if self.status == STATUS_PRIVATE_DEFAULTS:
            return "Private Defaults blockiert"
        if self.status == STATUS_VALIDATION_ERROR:
            return "Validierungsfehler"
        if self.status == STATUS_IO_ERROR:
            return "Speicherfehler"
        return "Nicht gespeichert"


@dataclass
class SaasProfileDiskStore:
    """JSON file store for generic SaaS profile/configuration drafts.

    ``store_path`` is injectable so tests always use ``tmp_path``.
    When ``store_path`` is a ``.json`` file, list/create APIs use its parent
    directory. When it is a directory, the active single-file path becomes
    ``<dir>/saas_profile_draft.json``.
    """

    store_path: Path
    _last_status: str = field(default="Nicht gespeichert", init=False, repr=False)

    def __post_init__(self) -> None:
        path = Path(self.store_path)
        if path.suffix.lower() != ".json":
            self.store_path = path / DEFAULT_DRAFT_FILENAME

    @classmethod
    def default(cls) -> SaasProfileDiskStore:
        return cls(store_path=default_saas_ui_v2_draft_path())

    @classmethod
    def for_path(cls, path: Path) -> SaasProfileDiskStore:
        return cls(store_path=Path(path))

    @property
    def last_persistence_label(self) -> str:
        return self._last_status

    @property
    def drafts_root(self) -> Path:
        """Directory that holds one JSON file per local SaaS draft."""

        return Path(self.store_path).parent

    def draft_file_path(self, draft_id: str) -> Path:
        normalized = _normalize_draft_id(draft_id)
        return self.drafts_root / f"{normalized}.json"

    def list_drafts(self) -> tuple[SaasDraftListItem, ...]:
        root = self.drafts_root
        if not root.is_dir():
            return ()
        items: list[SaasDraftListItem] = []
        for path in sorted(root.glob("*.json"), key=lambda p: p.name.lower()):
            if path.name.lower() in _MANIFEST_FILENAMES:
                continue
            if path.name in FORBIDDEN_WRITE_BASENAMES:
                continue
            items.append(self._list_item_from_path(path))
        items.sort(key=lambda item: (item.updated_at or "", item.display_name.lower()), reverse=True)
        return tuple(items)

    def create_draft(
        self,
        *,
        display_name: str | None = None,
        profile_draft: SaasProfileDraft | None = None,
        configuration_draft: SaasConfigurationDraft | None = None,
    ) -> SaasProfileStoreResult:
        """Create a new generic local SaaS draft file under ``drafts_root``."""

        draft_id = _new_draft_id()
        name = (display_name or "").strip() or self._next_generic_display_name()
        now = _utc_now_iso()
        profile = profile_draft or _blank_profile_draft()
        if not (profile.profile_name or "").strip() or profile.profile_name == DEFAULT_SAAS_PROFILE_NAME:
            # Keep profile_name generic; list label is display_name.
            pass
        path = self.draft_file_path(draft_id)
        return self._write_draft_file(
            path=path,
            profile_draft=profile,
            configuration_draft=configuration_draft,
            draft_id=draft_id,
            display_name=name,
            created_at=now,
            updated_at=now,
        )

    def load_draft(self, draft_id: str) -> SaasProfileStoreResult:
        """Load one draft by id. Missing/corrupt never invent private defaults."""

        try:
            normalized = _normalize_draft_id(draft_id)
        except ValueError as exc:
            path = self.drafts_root / f"{draft_id}.json"
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=path,
                error=str(exc),
                draft_id=str(draft_id or ""),
            )
        path = self.draft_file_path(normalized)
        if not path.is_file():
            self._last_status = "Nicht gespeichert"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_MISSING_BLANK,
                path=path,
                error=f"Lokaler SaaS-Entwurf nicht gefunden: {normalized}",
                draft_id=normalized,
                locally_persisted=False,
            )
        return self._load_from_path(path, expected_draft_id=normalized)

    def save_draft(
        self,
        draft_id: str,
        profile_draft: SaasProfileDraft,
        configuration_draft: SaasConfigurationDraft | None = None,
        *,
        display_name: str | None = None,
    ) -> SaasProfileStoreResult:
        """Update only the selected draft file (local disk, no cloud)."""

        try:
            normalized = _normalize_draft_id(draft_id)
        except ValueError as exc:
            path = self.drafts_root / f"{draft_id}.json"
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=path,
                profile_draft=profile_draft,
                configuration_draft=configuration_draft,
                error=str(exc),
                draft_id=str(draft_id or ""),
            )
        path = self.draft_file_path(normalized)
        created_at = _utc_now_iso()
        existing_name = (display_name or "").strip() or self._next_generic_display_name()
        if path.is_file():
            meta = self._read_meta_soft(path)
            if meta.get("created_at"):
                created_at = str(meta["created_at"])
            if not (display_name or "").strip() and meta.get("display_name"):
                existing_name = str(meta["display_name"])
        return self._write_draft_file(
            path=path,
            profile_draft=profile_draft,
            configuration_draft=configuration_draft,
            draft_id=normalized,
            display_name=existing_name,
            created_at=created_at,
            updated_at=_utc_now_iso(),
        )

    def rename_draft(self, draft_id: str, new_display_name: str) -> SaasProfileStoreResult:
        """Rename only the display name / metadata. Draft-ID stays unchanged."""

        try:
            normalized = _normalize_draft_id(draft_id)
        except ValueError as exc:
            path = self.drafts_root / f"{draft_id}.json"
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=path,
                error=str(exc),
                draft_id=str(draft_id or ""),
            )

        cleaned_name = _normalize_display_name(new_display_name)
        if not cleaned_name:
            path = self.draft_file_path(normalized)
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=path,
                error="Anzeigename darf nicht leer sein.",
                draft_id=normalized,
            )

        path = self.draft_file_path(normalized)
        path_error = self._assert_path_inside_store(path)
        if path_error:
            self._last_status = "Speicherfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_IO_ERROR,
                path=path,
                error=path_error,
                draft_id=normalized,
            )
        if not path.is_file():
            self._last_status = "Nicht gespeichert"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_MISSING_BLANK,
                path=path,
                error=f"Lokaler SaaS-Entwurf nicht gefunden: {normalized}",
                draft_id=normalized,
            )

        loaded = self._load_from_path(path, expected_draft_id=normalized)
        if not loaded.ok or loaded.profile_draft is None:
            # Corrupt / invalid drafts stay listable and deletable, but not silently renamed.
            return SaasProfileStoreResult(
                ok=False,
                status=loaded.status if loaded.status else STATUS_CORRUPTED,
                path=path,
                error=loaded.error or "Lokaler Draft beschädigt — Umbenennen nicht möglich.",
                draft_id=normalized,
                display_name=loaded.display_name,
            )

        created_at = ""
        meta = self._read_meta_soft(path)
        if meta.get("created_at"):
            created_at = str(meta["created_at"])
        else:
            created_at = _utc_now_iso()

        written = self._write_draft_file(
            path=path,
            profile_draft=loaded.profile_draft,
            configuration_draft=loaded.configuration_draft,
            draft_id=normalized,
            display_name=cleaned_name,
            created_at=created_at,
            updated_at=_utc_now_iso(),
        )
        if not written.ok:
            return written
        self._last_status = "Lokal umbenannt"
        return SaasProfileStoreResult(
            ok=True,
            status=STATUS_RENAMED,
            path=path,
            profile_draft=written.profile_draft,
            configuration_draft=written.configuration_draft,
            locally_persisted=True,
            draft_id=normalized,
            display_name=cleaned_name,
        )

    def delete_draft(self, draft_id: str) -> SaasProfileStoreResult:
        """Delete only the JSON file for ``draft_id`` inside the store directory."""

        try:
            normalized = _normalize_draft_id(draft_id)
        except ValueError as exc:
            path = self.drafts_root / f"{draft_id}.json"
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=path,
                error=str(exc),
                draft_id=str(draft_id or ""),
            )

        path = self.draft_file_path(normalized)
        path_error = self._assert_path_inside_store(path)
        if path_error:
            self._last_status = "Speicherfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_IO_ERROR,
                path=path,
                error=path_error,
                draft_id=normalized,
            )
        if path.name in FORBIDDEN_WRITE_BASENAMES:
            self._last_status = "Speicherfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_IO_ERROR,
                path=path,
                error=f"Verbotener Löschzielname: {path.name}",
                draft_id=normalized,
            )
        if not path.is_file():
            self._last_status = "Nicht gespeichert"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_MISSING_BLANK,
                path=path,
                error=f"Lokaler SaaS-Entwurf nicht gefunden: {normalized}",
                draft_id=normalized,
                locally_persisted=False,
            )

        try:
            path.unlink()
        except OSError as exc:
            self._last_status = "Speicherfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_IO_ERROR,
                path=path,
                error=f"Löschen fehlgeschlagen: {exc}",
                draft_id=normalized,
            )

        self._last_status = "Lokal gelöscht"
        return SaasProfileStoreResult(
            ok=True,
            status=STATUS_DELETED,
            path=path,
            locally_persisted=False,
            draft_id=normalized,
        )

    def export_draft(self, draft_id: str, export_path: Path) -> SaasProfileStoreResult:
        """Export one selected local SaaS draft as a portable JSON envelope.

        Writes only to the explicit ``export_path``. Never touches
        ``profile_config.local.json`` or Application Support working profiles.
        """

        try:
            normalized = _normalize_draft_id(draft_id)
        except ValueError as exc:
            path = Path(export_path)
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=path,
                error=str(exc),
                draft_id=str(draft_id or ""),
            )

        loaded = self.load_draft(normalized)
        if not loaded.ok or loaded.profile_draft is None:
            self._last_status = loaded.persistence_label
            return SaasProfileStoreResult(
                ok=False,
                status=loaded.status,
                path=Path(export_path),
                error=loaded.error or "Export nicht möglich — Draft fehlt oder ist beschädigt.",
                private_default_violations=loaded.private_default_violations,
                draft_id=normalized,
                display_name=loaded.display_name,
            )

        target = Path(export_path)
        if target.name in FORBIDDEN_WRITE_BASENAMES:
            self._last_status = "Speicherfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_IO_ERROR,
                path=target,
                error=f"Verbotener Exportzielname: {target.name}",
                draft_id=normalized,
                display_name=loaded.display_name,
            )

        draft_payload = _drafts_to_payload(
            loaded.profile_draft,
            loaded.configuration_draft,
            draft_id=normalized,
            display_name=loaded.display_name or GENERIC_DRAFT_DISPLAY_PREFIX,
            created_at=self._read_meta_soft(loaded.path).get("created_at") or "",
            updated_at=self._read_meta_soft(loaded.path).get("updated_at") or "",
        )
        # Export must stay generic — never ship private tenant markers.
        private = _find_import_private_marker_violations(draft_payload)
        if private:
            self._last_status = "Private Defaults blockiert"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_PRIVATE_DEFAULTS,
                path=target,
                error="Export blockiert: private Tenant-Defaults im Draft.",
                private_default_violations=tuple(private),
                draft_id=normalized,
                display_name=loaded.display_name,
            )

        envelope = {
            "schema_version": SCHEMA_VERSION,
            "kind": EXPORT_KIND,
            "cloud": False,
            "persistence": "local_export_only",
            "exported_at": _utc_now_iso(),
            "draft": {
                "display_name": draft_payload.get("display_name") or GENERIC_DRAFT_DISPLAY_PREFIX,
                "profile": draft_payload["profile"],
                "configuration": draft_payload.get("configuration"),
                # Source id is informational only; import always creates a new id.
                "source_draft_id": normalized,
            },
        }

        try:
            if target.parent and not target.parent.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            self._last_status = "Speicherfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_IO_ERROR,
                path=target,
                error=f"Export fehlgeschlagen: {exc}",
                draft_id=normalized,
                display_name=loaded.display_name,
            )

        self._last_status = "Lokal exportiert"
        return SaasProfileStoreResult(
            ok=True,
            status=STATUS_EXPORTED,
            path=target,
            profile_draft=loaded.profile_draft,
            configuration_draft=loaded.configuration_draft,
            locally_persisted=True,
            draft_id=normalized,
            display_name=loaded.display_name,
        )

    def import_draft(
        self,
        import_path: Path,
        preferred_display_name: str | None = None,
    ) -> SaasProfileStoreResult:
        """Import a portable SaaS draft export as a new local draft (new id).

        Never overwrites an existing draft silently. Never writes outside
        ``drafts_root``. Never touches ``profile_config.local.json``.
        """

        source = Path(import_path)
        if not source.is_file():
            self._last_status = "Nicht gespeichert"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_MISSING_BLANK,
                path=source,
                error=f"Importdatei nicht gefunden: {source}",
                locally_persisted=False,
            )

        try:
            raw_text = source.read_text(encoding="utf-8")
            data = json.loads(raw_text)
        except (OSError, UnicodeDecodeError) as exc:
            self._last_status = "Lokaler Draft beschädigt"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_CORRUPTED,
                path=source,
                error=f"Importdatei unlesbar: {exc}",
            )
        except json.JSONDecodeError as exc:
            self._last_status = "Lokaler Draft beschädigt"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_CORRUPTED,
                path=source,
                error=f"Ungültiges JSON: {exc.msg}",
            )

        if not isinstance(data, dict):
            self._last_status = "Lokaler Draft beschädigt"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_CORRUPTED,
                path=source,
                error="Import-Root muss ein JSON-Objekt sein.",
            )

        envelope_error = _validate_export_envelope(data)
        if envelope_error:
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=source,
                error=envelope_error,
            )

        draft_raw = data["draft"]
        if not isinstance(draft_raw, Mapping):
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=source,
                error="Feld 'draft' fehlt oder ist ungültig.",
            )

        profile_raw = draft_raw.get("profile")
        if not isinstance(profile_raw, Mapping):
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=source,
                error="Feld 'draft.profile' fehlt oder ist ungültig.",
            )

        # Strip absolute / internal working-profile paths before marker checks
        # so path fragments like usernames never look like private defaults.
        sanitized_profile = _sanitize_imported_mapping(dict(profile_raw))
        config_raw = draft_raw.get("configuration")
        sanitized_config: dict[str, Any] | None = None
        if isinstance(config_raw, Mapping):
            sanitized_config = _sanitize_imported_mapping(dict(config_raw))

        display_name_raw = str(draft_raw.get("display_name") or "")
        private_probe = {
            "display_name": display_name_raw,
            "profile": sanitized_profile,
            "configuration": sanitized_config,
        }
        private = _find_import_private_marker_violations(private_probe)
        if private:
            self._last_status = "Private Defaults blockiert"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_PRIVATE_DEFAULTS,
                path=source,
                error="Import blockiert: private Tenant-Defaults in der Importdatei.",
                private_default_violations=tuple(private),
            )

        try:
            profile_draft = _profile_draft_from_dict(sanitized_profile)
            configuration_draft = (
                _configuration_draft_from_dict(sanitized_config)
                if sanitized_config is not None
                else None
            )
        except (TypeError, ValueError, KeyError) as exc:
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=source,
                error=f"Import-Draft-Felder ungültig: {exc}",
            )

        display_name = _normalize_display_name(
            preferred_display_name
            or str(draft_raw.get("display_name") or "")
            or profile_draft.profile_name
            or GENERIC_DRAFT_DISPLAY_PREFIX
        )
        if not display_name:
            display_name = self._next_generic_display_name()

        # Always create a new draft id — never overwrite silently.
        created = self.create_draft(
            display_name=display_name,
            profile_draft=profile_draft,
            configuration_draft=configuration_draft,
        )
        if not created.ok:
            return created

        # Guard: created file must stay inside store directory.
        path_error = self._assert_path_inside_store(created.path)
        if path_error:
            # Best-effort cleanup of the unexpected write target is skipped —
            # create_draft already writes only inside drafts_root.
            self._last_status = "Speicherfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_IO_ERROR,
                path=created.path,
                error=path_error,
                draft_id=created.draft_id,
            )

        self._last_status = "Lokal importiert"
        return SaasProfileStoreResult(
            ok=True,
            status=STATUS_IMPORTED,
            path=created.path,
            profile_draft=created.profile_draft,
            configuration_draft=created.configuration_draft,
            locally_persisted=True,
            draft_id=created.draft_id,
            display_name=created.display_name,
        )

    def _assert_path_inside_store(self, path: Path) -> str | None:
        """Refuse any path that would escape the injectable drafts root."""

        try:
            root = self.drafts_root.resolve()
            resolved = path.resolve()
            resolved.relative_to(root)
            if resolved.parent != root:
                return "Löschen/Umbenennen außerhalb des Store-Verzeichnisses ist nicht erlaubt."
        except (OSError, ValueError):
            return "Löschen/Umbenennen außerhalb des Store-Verzeichnisses ist nicht erlaubt."
        return None

    def save(
        self,
        profile_draft: SaasProfileDraft,
        configuration_draft: SaasConfigurationDraft | None = None,
    ) -> SaasProfileStoreResult:
        path = Path(self.store_path)
        meta = self._read_meta_soft(path) if path.is_file() else {}
        draft_id = str(meta.get("draft_id") or path.stem)
        display_name = str(meta.get("display_name") or GENERIC_DRAFT_DISPLAY_PREFIX)
        created_at = str(meta.get("created_at") or _utc_now_iso())
        return self._write_draft_file(
            path=path,
            profile_draft=profile_draft,
            configuration_draft=configuration_draft,
            draft_id=draft_id if _DRAFT_ID_RE.match(draft_id) else path.stem,
            display_name=display_name,
            created_at=created_at,
            updated_at=_utc_now_iso(),
        )

    def load(self) -> SaasProfileStoreResult:
        path = Path(self.store_path)
        if not path.is_file():
            blank = _blank_profile_draft()
            self._last_status = "Nicht gespeichert"
            return SaasProfileStoreResult(
                ok=True,
                status=STATUS_MISSING_BLANK,
                path=path,
                profile_draft=blank,
                configuration_draft=None,
                locally_persisted=False,
            )
        return self._load_from_path(path)

    def _write_draft_file(
        self,
        *,
        path: Path,
        profile_draft: SaasProfileDraft,
        configuration_draft: SaasConfigurationDraft | None,
        draft_id: str,
        display_name: str,
        created_at: str,
        updated_at: str,
    ) -> SaasProfileStoreResult:
        if path.name in FORBIDDEN_WRITE_BASENAMES:
            self._last_status = "Speicherfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_IO_ERROR,
                path=path,
                error=f"Verbotener Speicherzielname: {path.name}",
                draft_id=draft_id,
                display_name=display_name,
            )

        payload = _drafts_to_payload(
            profile_draft,
            configuration_draft,
            draft_id=draft_id,
            display_name=display_name,
            created_at=created_at,
            updated_at=updated_at,
        )
        violations = find_private_saas_default_violations(_guard_slice(payload))
        if violations:
            self._last_status = "Private Defaults blockiert"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_PRIVATE_DEFAULTS,
                path=path,
                profile_draft=profile_draft,
                configuration_draft=configuration_draft,
                error="Private Tenant-Defaults dürfen nicht persistiert werden.",
                private_default_violations=tuple(violations),
                draft_id=draft_id,
                display_name=display_name,
            )

        try:
            assert_saas_defaults_are_generic(_guard_slice(payload))
        except AssertionError as exc:
            self._last_status = "Private Defaults blockiert"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_PRIVATE_DEFAULTS,
                path=path,
                profile_draft=profile_draft,
                configuration_draft=configuration_draft,
                error=str(exc),
                draft_id=draft_id,
                display_name=display_name,
            )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            self._last_status = "Speicherfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_IO_ERROR,
                path=path,
                profile_draft=profile_draft,
                configuration_draft=configuration_draft,
                error=f"Schreiben fehlgeschlagen: {exc}",
                draft_id=draft_id,
                display_name=display_name,
            )

        self._last_status = "Lokal gespeichert"
        return SaasProfileStoreResult(
            ok=True,
            status=STATUS_SAVED,
            path=path,
            profile_draft=profile_draft,
            configuration_draft=configuration_draft,
            locally_persisted=True,
            draft_id=draft_id,
            display_name=display_name,
        )

    def _load_from_path(
        self,
        path: Path,
        *,
        expected_draft_id: str | None = None,
    ) -> SaasProfileStoreResult:
        try:
            raw_text = path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
        except (OSError, UnicodeDecodeError) as exc:
            self._last_status = "Lokaler Draft beschädigt"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_CORRUPTED,
                path=path,
                error=f"Datei unlesbar: {exc}",
                draft_id=expected_draft_id or path.stem,
            )
        except json.JSONDecodeError as exc:
            self._last_status = "Lokaler Draft beschädigt"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_CORRUPTED,
                path=path,
                error=f"Ungültiges JSON: {exc.msg}",
                draft_id=expected_draft_id or path.stem,
            )

        if not isinstance(data, dict):
            self._last_status = "Lokaler Draft beschädigt"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_CORRUPTED,
                path=path,
                error="Root muss ein JSON-Objekt sein.",
                draft_id=expected_draft_id or path.stem,
            )

        validation_error = _validate_envelope(data)
        if validation_error:
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=path,
                error=validation_error,
                draft_id=expected_draft_id or str(data.get("draft_id") or path.stem),
                display_name=str(data.get("display_name") or "") or None,
            )

        try:
            profile_draft = _profile_draft_from_dict(data["profile"])
            config_raw = data.get("configuration")
            configuration_draft = (
                _configuration_draft_from_dict(config_raw)
                if isinstance(config_raw, Mapping)
                else None
            )
        except (TypeError, ValueError, KeyError) as exc:
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=path,
                error=f"Draft-Felder ungültig: {exc}",
                draft_id=expected_draft_id or str(data.get("draft_id") or path.stem),
            )

        violations = find_private_saas_default_violations(
            _guard_slice(
                _drafts_to_payload(
                    profile_draft,
                    configuration_draft,
                    draft_id=str(data.get("draft_id") or path.stem),
                    display_name=str(data.get("display_name") or GENERIC_DRAFT_DISPLAY_PREFIX),
                    created_at=str(data.get("created_at") or ""),
                    updated_at=str(data.get("updated_at") or ""),
                )
            )
        )
        if violations:
            self._last_status = "Private Defaults blockiert"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_PRIVATE_DEFAULTS,
                path=path,
                error="Persistierte Datei enthält private Tenant-Defaults.",
                private_default_violations=tuple(violations),
                draft_id=expected_draft_id or str(data.get("draft_id") or path.stem),
            )

        draft_id = str(data.get("draft_id") or path.stem)
        display_name = str(data.get("display_name") or profile_draft.profile_name or GENERIC_DRAFT_DISPLAY_PREFIX)
        self._last_status = "Lokal geladen"
        return SaasProfileStoreResult(
            ok=True,
            status=STATUS_LOADED,
            path=path,
            profile_draft=profile_draft,
            configuration_draft=configuration_draft,
            locally_persisted=True,
            draft_id=draft_id,
            display_name=display_name,
        )

    def _list_item_from_path(self, path: Path) -> SaasDraftListItem:
        stem = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return SaasDraftListItem(
                draft_id=stem,
                display_name=stem,
                created_at="",
                updated_at="",
                status=DRAFT_ITEM_CORRUPTED,
                path=path,
                error=f"Lokaler Draft beschädigt: {exc}",
            )
        if not isinstance(data, dict):
            return SaasDraftListItem(
                draft_id=stem,
                display_name=stem,
                created_at="",
                updated_at="",
                status=DRAFT_ITEM_CORRUPTED,
                path=path,
                error="Lokaler Draft beschädigt: Root muss ein JSON-Objekt sein.",
            )
        validation_error = _validate_envelope(data)
        draft_id = str(data.get("draft_id") or stem)
        profile = data.get("profile") if isinstance(data.get("profile"), Mapping) else {}
        display_name = str(
            data.get("display_name")
            or (profile.get("profile_name") if isinstance(profile, Mapping) else "")
            or GENERIC_DRAFT_DISPLAY_PREFIX
        )
        if validation_error:
            return SaasDraftListItem(
                draft_id=draft_id,
                display_name=display_name,
                created_at=str(data.get("created_at") or ""),
                updated_at=str(data.get("updated_at") or ""),
                status=DRAFT_ITEM_CORRUPTED,
                path=path,
                error=validation_error,
            )
        return SaasDraftListItem(
            draft_id=draft_id,
            display_name=display_name,
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            status=DRAFT_ITEM_OK,
            path=path,
        )

    def _read_meta_soft(self, path: Path) -> dict[str, str]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            "draft_id": str(data.get("draft_id") or ""),
            "display_name": str(data.get("display_name") or ""),
            "created_at": str(data.get("created_at") or ""),
            "updated_at": str(data.get("updated_at") or ""),
        }

    def _next_generic_display_name(self) -> str:
        count = len(self.list_drafts()) + 1
        return f"{GENERIC_DRAFT_DISPLAY_PREFIX} {count}"


def default_saas_ui_v2_draft_dir() -> Path:
    """Isolated draft directory — not the Hadi/SOMAA Application Support profile root."""

    return (
        Path.home()
        / "Library"
        / "Application Support"
        / SAAS_UI_V2_SUPPORT_DIR_NAME
        / SAAS_UI_V2_DRAFTS_SUBDIR
    )


def default_saas_ui_v2_draft_path() -> Path:
    return default_saas_ui_v2_draft_dir() / DEFAULT_DRAFT_FILENAME


def new_saas_profile_disk_store(store_path: Path | None = None) -> SaasProfileDiskStore:
    if store_path is None:
        return SaasProfileDiskStore.default()
    return SaasProfileDiskStore.for_path(Path(store_path))


def _new_draft_id() -> str:
    return f"draft_{uuid.uuid4().hex[:12]}"


def _normalize_draft_id(draft_id: str) -> str:
    value = (draft_id or "").strip()
    if not value or not _DRAFT_ID_RE.match(value):
        raise ValueError(f"Ungültige Draft-ID: {draft_id!r}")
    return value


def _normalize_display_name(display_name: str) -> str:
    """Neutralize control characters and collapse whitespace; empty after clean is invalid."""

    cleaned = _CONTROL_CHARS_RE.sub(" ", display_name or "")
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _blank_profile_draft() -> SaasProfileDraft:
    known = {model_id: domain for model_id, _label, domain in GENERIC_SCAN_MODELS}
    return SaasProfileDraft(
        profile_name=DEFAULT_SAAS_PROFILE_NAME,
        scan_model_id=DEFAULT_SAAS_SCAN_MODEL_ID,
        document_type=known.get(DEFAULT_SAAS_SCAN_MODEL_ID, "Rechnungen"),
        matching_conditions_text="",
        destination_category="",
        destination_folder="",
        filename_pattern=DEFAULT_SAAS_FILENAME_PATTERN,
        review_rule="unclear_on_no_match",
        payment_hint="",
        review_unclear_folder=DEFAULT_SAAS_REVIEW_FOLDER,
        notes="",
        is_new=True,
        configurations=[],
        classification_policy=default_classification_policy(),
    )


def _drafts_to_payload(
    profile_draft: SaasProfileDraft,
    configuration_draft: SaasConfigurationDraft | None,
    *,
    draft_id: str | None = None,
    display_name: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": STORE_KIND,
        "persistence": "local_disk_only",
        "cloud": False,
        "profile": _profile_draft_to_dict(profile_draft),
        "configuration": (
            _configuration_draft_to_dict(configuration_draft)
            if configuration_draft is not None
            else None
        ),
    }
    if draft_id:
        payload["draft_id"] = draft_id
    if display_name is not None:
        payload["display_name"] = display_name
    if created_at:
        payload["created_at"] = created_at
    if updated_at:
        payload["updated_at"] = updated_at
    return payload


def _profile_draft_to_dict(draft: SaasProfileDraft) -> dict[str, Any]:
    return {
        "profile_name": draft.profile_name,
        "scan_model_id": draft.scan_model_id,
        "document_type": draft.document_type,
        "matching_conditions": draft.matching_conditions_text,
        "destination_category": draft.destination_category,
        "destination_folder": draft.destination_folder,
        "filename_pattern": draft.filename_pattern,
        "review_rule": draft.review_rule,
        "payment_hint": draft.payment_hint,
        "review_unclear_folder": draft.review_unclear_folder,
        "notes": draft.notes,
        "is_new": bool(draft.is_new),
        "configurations": [item.to_dict() for item in draft.configurations],
        "classification_policy": draft.classification_policy.to_dict(),
    }


def _configuration_draft_to_dict(draft: SaasConfigurationDraft) -> dict[str, Any]:
    return {
        "name": draft.name,
        "active": bool(draft.active),
        "document_type": draft.document_type,
        "matching_conditions": draft.matching_conditions_text,
        "destination_category": draft.destination_category,
        "destination_folder": draft.destination_folder,
        "filename_pattern": draft.filename_pattern,
        "review_rule": draft.review_rule,
        "payment_hint": draft.payment_hint,
        "is_new": bool(draft.is_new),
    }


def _profile_draft_from_dict(raw: Mapping[str, Any]) -> SaasProfileDraft:
    if not isinstance(raw, Mapping):
        raise TypeError("profile muss ein Objekt sein")
    scan_model_id = str(raw.get("scan_model_id") or "").strip() or DEFAULT_SAAS_SCAN_MODEL_ID
    known_ids = {model_id for model_id, _label, _domain in GENERIC_SCAN_MODELS}
    if scan_model_id not in known_ids:
        raise ValueError(f"Unbekanntes Scanmodell: {scan_model_id}")
    configs_raw = raw.get("configurations") or []
    if not isinstance(configs_raw, list):
        raise TypeError("configurations muss eine Liste sein")
    configurations: list[SaasConfigurationDraft] = []
    for item in configs_raw:
        if isinstance(item, Mapping):
            configurations.append(_configuration_draft_from_dict(item))
    policy_raw = raw.get("classification_policy")
    return SaasProfileDraft(
        profile_name=str(raw.get("profile_name") or DEFAULT_SAAS_PROFILE_NAME),
        scan_model_id=scan_model_id,
        document_type=str(raw.get("document_type") or "Rechnungen"),
        matching_conditions_text=str(raw.get("matching_conditions") or ""),
        destination_category=str(raw.get("destination_category") or ""),
        destination_folder=str(raw.get("destination_folder") or ""),
        filename_pattern=str(raw.get("filename_pattern") or DEFAULT_SAAS_FILENAME_PATTERN),
        review_rule=str(raw.get("review_rule") or "unclear_on_no_match"),
        payment_hint=str(raw.get("payment_hint") or ""),
        review_unclear_folder=str(raw.get("review_unclear_folder") or DEFAULT_SAAS_REVIEW_FOLDER),
        notes=str(raw.get("notes") or ""),
        is_new=bool(raw.get("is_new", True)),
        configurations=configurations,
        classification_policy=classification_policy_from_dict(
            policy_raw if isinstance(policy_raw, Mapping) else None
        ),
    )


def _configuration_draft_from_dict(raw: Mapping[str, Any]) -> SaasConfigurationDraft:
    if not isinstance(raw, Mapping):
        raise TypeError("configuration muss ein Objekt sein")
    matching = raw.get("matching_conditions")
    if isinstance(matching, list):
        matching_text = "; ".join(str(item) for item in matching)
    else:
        matching_text = str(matching or "")
    return SaasConfigurationDraft(
        name=str(raw.get("name") or ""),
        active=bool(raw.get("active", True)),
        document_type=str(raw.get("document_type") or ""),
        matching_conditions_text=matching_text,
        destination_category=str(raw.get("destination_category") or ""),
        destination_folder=str(raw.get("destination_folder") or ""),
        filename_pattern=str(raw.get("filename_pattern") or DEFAULT_SAAS_FILENAME_PATTERN),
        review_rule=str(raw.get("review_rule") or "unclear_on_no_match"),
        payment_hint=str(raw.get("payment_hint") or ""),
        is_new=bool(raw.get("is_new", True)),
    )


def _validate_envelope(data: Mapping[str, Any]) -> str | None:
    kind = data.get("kind")
    if kind != STORE_KIND:
        return f"Unerwartetes kind: {kind!r}"
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        return f"Unsupported schema_version: {version!r}"
    if "profile" not in data or not isinstance(data.get("profile"), Mapping):
        return "Feld 'profile' fehlt oder ist ungültig."
    config = data.get("configuration")
    if config is not None and not isinstance(config, Mapping):
        return "Feld 'configuration' muss Objekt oder null sein."
    return None


def _validate_export_envelope(data: Mapping[str, Any]) -> str | None:
    kind = data.get("kind")
    if kind != EXPORT_KIND:
        return f"Unerwartetes kind: {kind!r} (erwartet {EXPORT_KIND!r})"
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        return f"Unsupported schema_version: {version!r}"
    if data.get("cloud") is True:
        return "Cloud-Export wird nicht akzeptiert (cloud muss false sein)."
    if "draft" not in data or not isinstance(data.get("draft"), Mapping):
        return "Feld 'draft' fehlt oder ist ungültig."
    draft = data["draft"]
    assert isinstance(draft, Mapping)
    if "profile" not in draft or not isinstance(draft.get("profile"), Mapping):
        return "Feld 'draft.profile' fehlt oder ist ungültig."
    config = draft.get("configuration")
    if config is not None and not isinstance(config, Mapping):
        return "Feld 'draft.configuration' muss Objekt oder null sein."
    return None


def _find_import_private_marker_violations(payload: Any) -> list[str]:
    """Scan nested import/export payload for private tenant markers."""

    violations: list[str] = []
    for text in _iter_payload_strings(payload):
        for marker in IMPORT_PRIVATE_MARKERS:
            if marker in text:
                violations.append(f"private_marker:{marker}")
    # Also reuse product blank-default guard on profile-shaped slices.
    if isinstance(payload, Mapping):
        draft = payload.get("draft") if "draft" in payload else payload
        if isinstance(draft, Mapping):
            profile = draft.get("profile") if "profile" in draft else draft
            if isinstance(profile, Mapping):
                violations.extend(
                    find_private_saas_default_violations(_guard_slice({"profile": profile}))
                )
                config = draft.get("configuration")
                if isinstance(config, Mapping):
                    violations.extend(
                        find_private_saas_default_violations(
                            _guard_slice({"profile": profile, "configuration": config})
                        )
                    )
    seen: set[str] = set()
    ordered: list[str] = []
    for item in violations:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _iter_payload_strings(value: Any):
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_payload_strings(nested)
        return
    if isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _iter_payload_strings(nested)


def _is_dangerous_imported_path(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    if text.startswith("/") or text.startswith("~"):
        return True
    lowered = text.lower()
    if ".." in text:
        return True
    for marker in _DANGEROUS_PATH_MARKERS:
        if marker.lower() in lowered:
            return True
    if "ki-rechnungen" in lowered and "saas-ui-v2" not in lowered:
        return True
    return False


def _sanitize_imported_mapping(raw: dict[str, Any]) -> dict[str, Any]:
    """Drop dangerous absolute/internal paths; keep generic relative values."""

    path_keys = {
        "destination_folder",
        "review_unclear_folder",
        "destination_category",
    }
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        if key == "configurations" and isinstance(value, list):
            cleaned[key] = [
                _sanitize_imported_mapping(dict(item)) if isinstance(item, Mapping) else item
                for item in value
            ]
            continue
        if key in path_keys and isinstance(value, str) and _is_dangerous_imported_path(value):
            cleaned[key] = ""
            continue
        cleaned[key] = value
    return cleaned


def _guard_slice(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Slice used by the private-default guard (profile + nested configurations)."""

    profile = dict(payload.get("profile") or {})
    configurations = list(profile.get("configurations") or [])
    config = payload.get("configuration")
    if isinstance(config, Mapping):
        configurations = [*configurations, dict(config)]
    return {
        "profile_name": profile.get("profile_name", ""),
        "scan_model_id": profile.get("scan_model_id", ""),
        "document_type": profile.get("document_type", ""),
        "configurations": configurations,
        "review_unclear_folder": profile.get("review_unclear_folder", DEFAULT_SAAS_REVIEW_FOLDER),
        "default_filename_pattern": profile.get("filename_pattern", ""),
        "notes": profile.get("notes", ""),
        "destination_category": profile.get("destination_category", ""),
        "destination_folder": profile.get("destination_folder", ""),
        "payment_hint": profile.get("payment_hint", ""),
        "matching_conditions": profile.get("matching_conditions", ""),
        "classification_policy": profile.get("classification_policy") or {},
    }
