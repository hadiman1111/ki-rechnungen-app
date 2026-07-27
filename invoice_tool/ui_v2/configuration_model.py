"""UI-v2 configuration product model — presentation only.

Maps product language for configurations editing without changing Track A /
processing core. Persistence still uses ConfigurationDraftVM + SaaS overlay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

CONFIGURATION_PRODUCT_RESTRUCTURE_MARKER = (
    "track_b_configuration_product_restructure_v1"
)
RECOGNITION_RULE_GROUP_MARKER = "config_recognition_rule_group_v1"
DOCUMENT_TYPE_DROPDOWN_MARKER = "config_document_type_dropdown_v1"
REVIEW_BEHAVIOR_CHOICE_MARKER = "config_review_behavior_choice_v1"
CONFIG_PREVIEW_SUMMARY_MARKER = "config_plain_language_preview_summary_v1"
FULL_WIDTH_PROFILE_SUMMARY_MARKER = "config_active_profile_full_width_v1"
CREATE_NEAR_LIST_MARKER = "config_create_button_near_list_v1"
TARGET_PATH_FULL_VISIBLE_MARKER = "config_target_path_full_visible_v1"

LABEL_CONFIG_NAME = "Name der Konfiguration"
LABEL_DOCUMENT_TYPE = "Dokumenttyp"
LABEL_RECOGNIZE_WHEN = "Erkennen, wenn …"
LABEL_FIELD = "Merkmal"
LABEL_OPERATOR = "Vergleich"
LABEL_VALUES = "Erkannte Schreibweisen / Werte"
LABEL_RULE_LOGIC = "Verknüpfung"
LABEL_REVIEW_BEHAVIOR = "Prüfverhalten"
LABEL_TARGET_FOLDER = "Zielordner"
LABEL_PICK_FOLDER = "Ordner auswählen"
LABEL_FILENAME_PATTERN = "Dateinamenmuster"
LABEL_PAYMENT_ADVANCED = "Zahlung / Kontierung (erweitert)"

LOGIC_ANY = "any"
LOGIC_ALL = "all"
LOGIC_LABELS: dict[str, str] = {
    LOGIC_ANY: "Mindestens eine Bedingung trifft zu",
    LOGIC_ALL: "Alle Bedingungen treffen zu",
}

SUPPORTED_DOCUMENT_TYPES: tuple[str, ...] = (
    "Rechnung",
    "Storno",
    "Gutschrift",
    "Sonstiges",
)

# Only behaviors that the SaaS overlay can store today.
SUPPORTED_REVIEW_BEHAVIORS: tuple[tuple[str, str], ...] = (
    ("unclear_on_no_match", "Bei Unsicherheit in Prüfung"),
)

OPERATOR_OPTIONS: tuple[tuple[str, str], ...] = (
    ("ist", "ist"),
    ("enthält", "enthält"),
    ("beginnt_mit", "beginnt mit"),
    ("endet_mit", "endet mit"),
    ("ist_vorhanden", "ist vorhanden"),
    ("ist_nicht_vorhanden", "ist nicht vorhanden"),
)

# Feature keys preferred in product UI (subset; filtered by scan model later).
PREFERRED_FEATURE_KEYS: tuple[str, ...] = (
    "payment_field",
    "supplier",
    "document_text",
    "invoice_number",
    "amount",
    "document_type",
    "category",
)

FEATURE_LABEL_OVERRIDES: dict[str, str] = {
    "payment_field": "Zahlungsart / Konto",
    "supplier": "Lieferant",
    "document_text": "Dokumenttext",
    "invoice_number": "Rechnungsnummer",
    "amount": "Betrag",
    "document_type": "Dokumentart",
    "category": "Kategorie",
}


@dataclass
class RecognitionClauseVM:
    """One recognition condition row (field / operator / synonym values)."""

    feature_key: str = ""
    operator: str = "ist"
    values: list[str] = field(default_factory=list)


@dataclass
class RecognitionRuleGroupVM:
    """Product presentation of recognition rules."""

    logic: str = LOGIC_ANY
    clauses: list[RecognitionClauseVM] = field(default_factory=list)

    def ensure_clause(self) -> None:
        if not self.clauses:
            self.clauses = [RecognitionClauseVM()]

    def primary_feature_key(self) -> str:
        self.ensure_clause()
        return (self.clauses[0].feature_key or "").strip()

    def primary_operator(self) -> str:
        self.ensure_clause()
        return (self.clauses[0].operator or "ist").strip() or "ist"

    def flattened_values(self) -> list[str]:
        """Values persisted on the single MatchingRule (primary clause)."""

        self.ensure_clause()
        out: list[str] = []
        for value in self.clauses[0].values:
            text = str(value or "").strip()
            if text and text not in out:
                out.append(text)
        return out

    def saas_conditions_text(self) -> str:
        self.ensure_clause()
        parts: list[str] = []
        for clause in self.clauses:
            feature = (clause.feature_key or "").strip() or "Merkmal"
            op = (clause.operator or "ist").strip() or "ist"
            vals = ", ".join(str(v).strip() for v in clause.values if str(v or "").strip())
            if vals:
                parts.append(f"{feature} {op} {vals}")
            else:
                parts.append(f"{feature} {op}")
        joiner = " ODER " if self.logic == LOGIC_ANY else " UND "
        return joiner.join(parts)


def rule_group_from_matching(
    *,
    feature_key: str,
    operator: str,
    values: Sequence[str],
    logic: str = LOGIC_ANY,
) -> RecognitionRuleGroupVM:
    cleaned = [str(v).strip() for v in values if str(v or "").strip()]
    return RecognitionRuleGroupVM(
        logic=logic if logic in LOGIC_LABELS else LOGIC_ANY,
        clauses=[
            RecognitionClauseVM(
                feature_key=str(feature_key or "").strip(),
                operator=str(operator or "ist").strip() or "ist",
                values=cleaned,
            )
        ],
    )


def normalize_document_type(raw: str | None) -> str:
    text = str(raw or "").strip()
    if not text:
        return "Rechnung"
    mapping = {
        "rechnung": "Rechnung",
        "rechnungen": "Rechnung",
        "invoice": "Rechnung",
        "storno": "Storno",
        "gutschrift": "Gutschrift",
        "credit note": "Gutschrift",
        "sonstiges": "Sonstiges",
        "other": "Sonstiges",
    }
    return mapping.get(text.casefold(), text if text in SUPPORTED_DOCUMENT_TYPES else "Sonstiges")


def review_behavior_label(key: str | None) -> str:
    for item_key, label in SUPPORTED_REVIEW_BEHAVIORS:
        if item_key == (key or "").strip():
            return label
    return SUPPORTED_REVIEW_BEHAVIORS[0][1]


def format_target_path_display(path: str | None) -> tuple[str, str]:
    """Return (primary_display, full_path). Never basename-only as sole signal."""

    full = str(path or "").strip()
    if not full:
        return ("—", "")
    return (full, full)


def plain_language_configuration_summary(
    *,
    name: str,
    document_type: str,
    rule_group: RecognitionRuleGroupVM,
    filename_preview: str,
    destination_path: str,
    review_key: str,
) -> tuple[str, ...]:
    rule_group.ensure_clause()
    clause = rule_group.clauses[0]
    feature = FEATURE_LABEL_OVERRIDES.get(
        clause.feature_key, clause.feature_key or "Merkmal"
    )
    op = dict(OPERATOR_OPTIONS).get(clause.operator, clause.operator or "ist")
    values = clause.values or ["…"]
    values_text = " / ".join(values)
    logic = LOGIC_LABELS.get(rule_group.logic, LOGIC_LABELS[LOGIC_ANY])
    dest = format_target_path_display(destination_path)[0]
    review = review_behavior_label(review_key)
    return (
        f"Diese Konfiguration „{name or '—'}“ erkennt Belege ({normalize_document_type(document_type)}), wenn {logic.lower()}: "
        f"{feature} {op} eine der Schreibweisen {values_text}.",
        f"Dann wird der Dateiname geplant als {filename_preview or '—'}.",
        f"Zielordner: {dest}",
        f"Prüfverhalten: {review}",
        CONFIGURATION_PRODUCT_RESTRUCTURE_MARKER,
        CONFIG_PREVIEW_SUMMARY_MARKER,
    )


def synonym_helper_text(values: Sequence[str]) -> str:
    cleaned = [str(v).strip() for v in values if str(v or "").strip()]
    if len(cleaned) >= 2:
        joined = " / ".join(cleaned)
        return (
            f"Diese Schreibweisen gelten als Varianten desselben Werts: {joined}. "
            "Mindestens eine Variante muss passen."
        )
    return "Mehrere Schreibweisen (z. B. amex und American Express) als Varianten hinzufügen."


def basename_hint(path: str | None) -> str:
    full = str(path or "").strip()
    if not full:
        return ""
    return Path(full).name
