"""In-memory SaaS profile/configuration draft state for UI-v2.

Holds editable generic drafts derived from build_blank_saas_profile().
No cloud/user persistence and no private tenant defaults in blank drafts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from invoice_tool.saas_product_model import (
    DEFAULT_SAAS_FILENAME_PATTERN,
    DEFAULT_SAAS_PROFILE_NAME,
    DEFAULT_SAAS_REVIEW_FOLDER,
    DEFAULT_SAAS_SCAN_MODEL_ID,
    GENERIC_SCAN_MODELS,
    ClassificationPolicy,
    assert_saas_defaults_are_generic,
    build_blank_saas_profile,
    default_classification_policy,
    find_private_saas_default_violations,
    list_generic_scan_models,
    saas_profile_editor_fields,
)
from invoice_tool.ui_v2.saas_profile_surface import (
    DEFAULT_SAAS_REVIEW_RULE_LABEL,
    GENERIC_CONFIG_NAME_HINT,
    build_saas_profile_surface_vm,
)

REQUIRED_PROFILE_FIELDS: tuple[str, ...] = (
    "profile_name",
    "scan_model_id",
    "document_type",
)

REQUIRED_CONFIGURATION_FIELDS: tuple[str, ...] = (
    "name",
    "document_type",
    "destination_folder",
    "filename_pattern",
)

_REVIEW_RULE_LABELS: dict[str, str] = {
    "unclear_on_no_match": DEFAULT_SAAS_REVIEW_RULE_LABEL,
}


@dataclass
class SaasConfigurationDraft:
    """Mutable in-memory configuration draft (generic SaaS fields)."""

    name: str = ""
    active: bool = True
    document_type: str = ""
    matching_conditions_text: str = ""
    destination_category: str = ""
    destination_folder: str = ""
    filename_pattern: str = ""
    review_rule: str = "unclear_on_no_match"
    payment_hint: str = ""
    is_new: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "active": self.active,
            "document_type": self.document_type,
            "matching_conditions": self.matching_conditions_text,
            "destination_category": self.destination_category,
            "destination_folder": self.destination_folder,
            "filename_pattern": self.filename_pattern,
            "review_rule": self.review_rule,
            "payment_hint": self.payment_hint,
        }

    def review_rule_label(self) -> str:
        return _REVIEW_RULE_LABELS.get(self.review_rule, self.review_rule or DEFAULT_SAAS_REVIEW_RULE_LABEL)


@dataclass
class SaasProfileDraft:
    """Mutable in-memory profile draft for the UI-v2 SaaS surface."""

    profile_name: str = DEFAULT_SAAS_PROFILE_NAME
    scan_model_id: str = DEFAULT_SAAS_SCAN_MODEL_ID
    document_type: str = "Rechnungen"
    matching_conditions_text: str = ""
    destination_category: str = ""
    destination_folder: str = ""
    filename_pattern: str = DEFAULT_SAAS_FILENAME_PATTERN
    review_rule: str = "unclear_on_no_match"
    payment_hint: str = ""
    review_unclear_folder: str = DEFAULT_SAAS_REVIEW_FOLDER
    notes: str = ""
    is_new: bool = True
    configurations: list[SaasConfigurationDraft] = field(default_factory=list)
    classification_policy: ClassificationPolicy = field(default_factory=default_classification_policy)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "scan_model_id": self.scan_model_id,
            "document_type": self.document_type,
            "matching_conditions": self.matching_conditions_text,
            "destination_category": self.destination_category,
            "destination_folder": self.destination_folder,
            "filename_pattern": self.filename_pattern,
            "review_rule": self.review_rule,
            "payment_hint": self.payment_hint,
            "review_unclear_folder": self.review_unclear_folder,
            "default_filename_pattern": self.filename_pattern,
            "notes": self.notes,
            "configurations": [item.to_dict() for item in self.configurations],
            "classification_policy": self.classification_policy.to_dict(),
        }

    def review_rule_label(self) -> str:
        return _REVIEW_RULE_LABELS.get(self.review_rule, self.review_rule or DEFAULT_SAAS_REVIEW_RULE_LABEL)


@dataclass
class SaasDraftValidation:
    """Validation outcome for a profile or configuration draft."""

    ok: bool
    field_errors: dict[str, str] = field(default_factory=dict)
    private_default_violations: list[str] = field(default_factory=list)

    @property
    def missing_required(self) -> tuple[str, ...]:
        return tuple(self.field_errors.keys())


@dataclass
class SaasProfileStateStore:
    """UI-v2 in-memory store for generic SaaS profile/configuration drafts."""

    profile_draft: SaasProfileDraft | None = None
    configuration_draft: SaasConfigurationDraft | None = None

    def reset(self) -> None:
        self.profile_draft = None
        self.configuration_draft = None

    def begin_blank_profile(self) -> SaasProfileDraft:
        blank = build_blank_saas_profile()
        assert_saas_defaults_are_generic(blank)
        draft = SaasProfileDraft(
            profile_name=blank.profile_name,
            scan_model_id=blank.scan_model_id,
            document_type=blank.document_type,
            matching_conditions_text="",
            destination_category="",
            destination_folder="",
            filename_pattern=blank.default_filename_pattern or DEFAULT_SAAS_FILENAME_PATTERN,
            review_rule="unclear_on_no_match",
            payment_hint="",
            review_unclear_folder=blank.review_unclear_folder or DEFAULT_SAAS_REVIEW_FOLDER,
            notes=blank.notes,
            is_new=True,
            configurations=[],
            classification_policy=blank.classification_policy,
        )
        self.profile_draft = draft
        self._assert_draft_generic(draft.to_dict())
        return draft

    def begin_blank_configuration(self, *, document_type: str | None = None) -> SaasConfigurationDraft:
        blank = build_blank_saas_profile()
        draft = SaasConfigurationDraft(
            name="",
            active=True,
            document_type=document_type or blank.document_type,
            matching_conditions_text="",
            destination_category="",
            destination_folder="",
            filename_pattern=blank.default_filename_pattern or DEFAULT_SAAS_FILENAME_PATTERN,
            review_rule="unclear_on_no_match",
            payment_hint="",
            is_new=True,
        )
        self.configuration_draft = draft
        self._assert_draft_generic({"configurations": [draft.to_dict()], **blank.to_dict()})
        return draft

    def update_profile_field(self, key: str, value: str) -> SaasProfileDraft:
        draft = self.profile_draft or self.begin_blank_profile()
        normalized = (value or "").strip() if isinstance(value, str) else value
        if key == "profile_name":
            draft.profile_name = str(normalized)
        elif key == "scan_model_id":
            draft.scan_model_id = str(normalized)
            known = {model_id: domain for model_id, _label, domain in GENERIC_SCAN_MODELS}
            if draft.scan_model_id in known and not draft.document_type:
                draft.document_type = known[draft.scan_model_id]
            elif draft.scan_model_id in known:
                # Keep document_type aligned with scan model when still on a generic default.
                if draft.document_type in {domain for _mid, _lbl, domain in GENERIC_SCAN_MODELS}:
                    draft.document_type = known[draft.scan_model_id]
        elif key == "document_type":
            draft.document_type = str(normalized)
        elif key == "matching_conditions":
            draft.matching_conditions_text = str(normalized)
        elif key in {"destination", "destination_folder"}:
            draft.destination_folder = str(normalized)
        elif key == "destination_category":
            draft.destination_category = str(normalized)
        elif key == "filename_pattern":
            draft.filename_pattern = str(normalized)
        elif key == "review_rule":
            draft.review_rule = str(normalized) or "unclear_on_no_match"
        elif key == "payment_hint":
            draft.payment_hint = str(normalized)
        elif key == "review_unclear_folder":
            draft.review_unclear_folder = str(normalized)
        elif key == "notes":
            draft.notes = str(normalized)
        else:
            raise KeyError(f"Unbekanntes SaaS-Profilfeld: {key}")
        self.profile_draft = draft
        return draft

    def update_configuration_field(self, key: str, value: str | bool) -> SaasConfigurationDraft:
        draft = self.configuration_draft or self.begin_blank_configuration()
        if key == "active":
            draft.active = bool(value)
        else:
            normalized = (value or "").strip() if isinstance(value, str) else str(value)
            if key == "name":
                draft.name = normalized
            elif key == "document_type":
                draft.document_type = normalized
            elif key == "matching_conditions":
                draft.matching_conditions_text = normalized
            elif key in {"destination", "destination_folder"}:
                draft.destination_folder = normalized
            elif key == "destination_category":
                draft.destination_category = normalized
            elif key == "filename_pattern":
                draft.filename_pattern = normalized
            elif key == "review_rule":
                draft.review_rule = normalized or "unclear_on_no_match"
            elif key == "payment_hint":
                draft.payment_hint = normalized
            else:
                raise KeyError(f"Unbekanntes SaaS-Konfigurationsfeld: {key}")
        self.configuration_draft = draft
        return draft

    def validate_profile_draft(self, draft: SaasProfileDraft | None = None) -> SaasDraftValidation:
        target = draft or self.profile_draft
        if target is None:
            return SaasDraftValidation(
                ok=False,
                field_errors={"profile_name": "Profilentwurf fehlt."},
            )
        errors: dict[str, str] = {}
        if not (target.profile_name or "").strip():
            errors["profile_name"] = "Profilname ist erforderlich."
        if not (target.scan_model_id or "").strip():
            errors["scan_model_id"] = "Scanmodell ist erforderlich."
        else:
            known_ids = {model_id for model_id, _label, _domain in GENERIC_SCAN_MODELS}
            if target.scan_model_id not in known_ids:
                errors["scan_model_id"] = "Unbekanntes Scanmodell."
        if not (target.document_type or "").strip():
            errors["document_type"] = "Dokumenttyp ist erforderlich."
        violations = find_private_saas_default_violations(target.to_dict())
        return SaasDraftValidation(
            ok=not errors and not violations,
            field_errors=errors,
            private_default_violations=violations,
        )

    def validate_configuration_draft(
        self, draft: SaasConfigurationDraft | None = None
    ) -> SaasDraftValidation:
        target = draft or self.configuration_draft
        if target is None:
            return SaasDraftValidation(
                ok=False,
                field_errors={"name": "Konfigurationsentwurf fehlt."},
            )
        errors: dict[str, str] = {}
        if not (target.name or "").strip():
            errors["name"] = "Konfigurationsname ist erforderlich."
        if not (target.document_type or "").strip():
            errors["document_type"] = "Dokumenttyp ist erforderlich."
        if not (target.destination_folder or "").strip():
            errors["destination_folder"] = "Zielordner ist erforderlich."
        if not (target.filename_pattern or "").strip():
            errors["filename_pattern"] = "Dateinamensmuster ist erforderlich."
        payload = {
            "profile_name": DEFAULT_SAAS_PROFILE_NAME,
            "scan_model_id": DEFAULT_SAAS_SCAN_MODEL_ID,
            "document_type": target.document_type,
            "configurations": [target.to_dict()],
            "review_unclear_folder": DEFAULT_SAAS_REVIEW_FOLDER,
            "default_filename_pattern": target.filename_pattern,
            "notes": "",
        }
        violations = find_private_saas_default_violations(payload)
        return SaasDraftValidation(
            ok=not errors and not violations,
            field_errors=errors,
            private_default_violations=violations,
        )

    def editor_field_keys(self) -> tuple[str, ...]:
        return tuple(field.key for field in saas_profile_editor_fields())

    def generic_editor_fields(self) -> tuple[dict[str, Any], ...]:
        """Prepared generic editor descriptors for the config/profile UI."""

        draft = self.profile_draft
        config = self.configuration_draft
        values = {
            "profile_name": draft.profile_name if draft else DEFAULT_SAAS_PROFILE_NAME,
            "scan_model_id": draft.scan_model_id if draft else DEFAULT_SAAS_SCAN_MODEL_ID,
            "document_type": (config.document_type if config else None)
            or (draft.document_type if draft else "Rechnungen"),
            "matching_conditions": (config.matching_conditions_text if config else None)
            or (draft.matching_conditions_text if draft else ""),
            "destination_category": (config.destination_category if config else None)
            or (draft.destination_category if draft else ""),
            "destination_folder": (config.destination_folder if config else None)
            or (draft.destination_folder if draft else ""),
            "filename_pattern": (config.filename_pattern if config else None)
            or (draft.filename_pattern if draft else DEFAULT_SAAS_FILENAME_PATTERN),
            "review_rule": (config.review_rule_label() if config else None)
            or (draft.review_rule_label() if draft else DEFAULT_SAAS_REVIEW_RULE_LABEL),
            "payment_hint": (config.payment_hint if config else None)
            or (draft.payment_hint if draft else ""),
        }
        rows: list[dict[str, Any]] = []
        for item in saas_profile_editor_fields():
            rows.append(
                {
                    "key": item.key,
                    "label": item.label,
                    "kind": item.kind,
                    "required": item.required,
                    "help_text": item.help_text,
                    "value": values.get(item.key, ""),
                    "editable": True,
                }
            )
        return tuple(rows)

    def surface_vm_from_draft(self):
        """Build a display VM from the current profile draft (blank if unset)."""

        if self.profile_draft is None:
            return build_saas_profile_surface_vm()
        from invoice_tool.saas_product_model import SaasProfileSurface

        surface = SaasProfileSurface(
            profile_name=self.profile_draft.profile_name,
            scan_model_id=self.profile_draft.scan_model_id,
            document_type=self.profile_draft.document_type,
            configurations=(),
            review_unclear_folder=self.profile_draft.review_unclear_folder,
            default_filename_pattern=self.profile_draft.filename_pattern,
            notes=self.profile_draft.notes,
            classification_policy=self.profile_draft.classification_policy,
        )
        return build_saas_profile_surface_vm(surface)

    def scan_model_options(self) -> tuple[dict[str, str], ...]:
        return list_generic_scan_models()

    def config_name_hint(self) -> str:
        return GENERIC_CONFIG_NAME_HINT

    def private_default_violations(self) -> list[str]:
        violations: list[str] = []
        if self.profile_draft is not None:
            violations.extend(find_private_saas_default_violations(self.profile_draft.to_dict()))
        if self.configuration_draft is not None:
            payload = {
                "profile_name": DEFAULT_SAAS_PROFILE_NAME,
                "scan_model_id": DEFAULT_SAAS_SCAN_MODEL_ID,
                "document_type": self.configuration_draft.document_type,
                "configurations": [self.configuration_draft.to_dict()],
                "review_unclear_folder": DEFAULT_SAAS_REVIEW_FOLDER,
                "default_filename_pattern": self.configuration_draft.filename_pattern,
                "notes": "",
            }
            violations.extend(find_private_saas_default_violations(payload))
        seen: set[str] = set()
        ordered: list[str] = []
        for item in violations:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered

    @staticmethod
    def _assert_draft_generic(payload: Mapping[str, Any]) -> None:
        assert_saas_defaults_are_generic(payload)


def new_saas_profile_state_store() -> SaasProfileStateStore:
    return SaasProfileStateStore()
