"""User-facing display formatting for UI-v2 — no technical identifiers in normal UI."""

from __future__ import annotations

from invoice_tool.configuration_model import Configuration, MatchingRule
from invoice_tool.scan_models import ScanModel


def user_matching_summary(configuration: Configuration, scan_model: ScanModel) -> str:
    """Concise user-readable matching summary for list and detail views."""
    if configuration.matching is None:
        return "Noch keine Zuordnungsregel"
    rule = configuration.matching
    feature = scan_model.get_feature(rule.feature_key)
    label = feature.label if feature else rule.feature_key
    return _rule_user_summary(label, rule)


def user_matching_summary_from_text(matching_summary: str) -> str:
    """Convert legacy 'Feld ist „x"' summaries to 'Erkannt bei: Feld enthält …'."""
    text = (matching_summary or "").strip()
    if not text or text == "Keine Zuordnungsregel":
        return "Noch keine Zuordnungsregel"
    if text.startswith("Erkannt bei:"):
        return text
    if " ist „" in text:
        field, rest = text.split(" ist „", 1)
        values_part = rest.rstrip('"')
        if '" oder „' in values_part:
            parts = values_part.split('" oder „')
            joined = " oder ".join(f"‚{p}'" for p in parts)
        else:
            joined = f"‚{values_part}'"
        return f"Erkannt bei: {field} enthält {joined}"
    return text


def _rule_user_summary(feature_label: str, rule: MatchingRule) -> str:
    cleaned = [value.strip() for value in rule.values if value.strip()]
    if not cleaned:
        return "Noch keine Zuordnungsregel"
    if len(cleaned) == 1:
        return f"Erkannt bei: {feature_label} enthält ‚{cleaned[0]}'"
    joined = " oder ".join(f"‚{v}'" for v in cleaned)
    return f"Erkannt bei: {feature_label} enthält {joined}"


def folder_status_label(*, path_set: bool, path_missing: bool) -> str:
    if not path_set:
        return "Zielordner fehlt"
    if path_missing:
        return "Zielordner nicht erreichbar"
    return "Zielordner eingerichtet"


def unmatched_setup_label(*, configured: bool) -> str:
    return "eingerichtet" if configured else "nicht eingerichtet"
