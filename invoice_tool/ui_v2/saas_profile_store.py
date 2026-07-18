"""Bounded local disk persistence for generic UI-v2 SaaS profile drafts.

Stores only generic SaaS draft JSON under an isolated draft directory.
Does not touch Hadi/SOMAA working profiles, profile_config.local.json,
or Application Support/KI-Rechnungen/profiles/.

No cloud/auth/tenant backend. No productive processing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from invoice_tool.saas_product_model import (
    DEFAULT_SAAS_FILENAME_PATTERN,
    DEFAULT_SAAS_PROFILE_NAME,
    DEFAULT_SAAS_REVIEW_FOLDER,
    DEFAULT_SAAS_SCAN_MODEL_ID,
    GENERIC_SCAN_MODELS,
    assert_saas_defaults_are_generic,
    find_private_saas_default_violations,
)
from invoice_tool.ui_v2.saas_profile_state import SaasConfigurationDraft, SaasProfileDraft

SCHEMA_VERSION = 1
STORE_KIND = "saas_ui_v2_profile_draft"
DEFAULT_DRAFT_FILENAME = "saas_profile_draft.json"

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

    @property
    def persistence_label(self) -> str:
        if self.status == STATUS_SAVED and self.ok:
            return "Lokal gespeichert"
        if self.status == STATUS_LOADED and self.ok:
            return "Lokal geladen"
        if self.status == STATUS_MISSING_BLANK:
            return "Nicht gespeichert"
        if self.status == STATUS_CORRUPTED:
            return "Beschädigte Datei"
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
    """

    store_path: Path
    _last_status: str = field(default="Nicht gespeichert", init=False, repr=False)

    @classmethod
    def default(cls) -> SaasProfileDiskStore:
        return cls(store_path=default_saas_ui_v2_draft_path())

    @classmethod
    def for_path(cls, path: Path) -> SaasProfileDiskStore:
        return cls(store_path=Path(path))

    @property
    def last_persistence_label(self) -> str:
        return self._last_status

    def save(
        self,
        profile_draft: SaasProfileDraft,
        configuration_draft: SaasConfigurationDraft | None = None,
    ) -> SaasProfileStoreResult:
        path = Path(self.store_path)
        if path.name in FORBIDDEN_WRITE_BASENAMES:
            self._last_status = "Speicherfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_IO_ERROR,
                path=path,
                error=f"Verbotener Speicherzielname: {path.name}",
            )

        payload = _drafts_to_payload(profile_draft, configuration_draft)
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
            )

        self._last_status = "Lokal gespeichert"
        return SaasProfileStoreResult(
            ok=True,
            status=STATUS_SAVED,
            path=path,
            profile_draft=profile_draft,
            configuration_draft=configuration_draft,
            locally_persisted=True,
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

        try:
            raw_text = path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
        except (OSError, UnicodeDecodeError) as exc:
            self._last_status = "Beschädigte Datei"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_CORRUPTED,
                path=path,
                error=f"Datei unlesbar: {exc}",
            )
        except json.JSONDecodeError as exc:
            self._last_status = "Beschädigte Datei"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_CORRUPTED,
                path=path,
                error=f"Ungültiges JSON: {exc.msg}",
            )

        if not isinstance(data, dict):
            self._last_status = "Beschädigte Datei"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_CORRUPTED,
                path=path,
                error="Root muss ein JSON-Objekt sein.",
            )

        validation_error = _validate_envelope(data)
        if validation_error:
            self._last_status = "Validierungsfehler"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_VALIDATION_ERROR,
                path=path,
                error=validation_error,
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
            )

        violations = find_private_saas_default_violations(
            _guard_slice(_drafts_to_payload(profile_draft, configuration_draft))
        )
        if violations:
            self._last_status = "Private Defaults blockiert"
            return SaasProfileStoreResult(
                ok=False,
                status=STATUS_PRIVATE_DEFAULTS,
                path=path,
                error="Persistierte Datei enthält private Tenant-Defaults.",
                private_default_violations=tuple(violations),
            )

        self._last_status = "Lokal geladen"
        return SaasProfileStoreResult(
            ok=True,
            status=STATUS_LOADED,
            path=path,
            profile_draft=profile_draft,
            configuration_draft=configuration_draft,
            locally_persisted=True,
        )


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
    return SaasProfileDiskStore.for_path(store_path)


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
    )


def _drafts_to_payload(
    profile_draft: SaasProfileDraft,
    configuration_draft: SaasConfigurationDraft | None,
) -> dict[str, Any]:
    return {
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
    }
