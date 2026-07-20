"""Profile-driven supplier routing rules (e.g. Anthropic → EP / AMEX 1005 / amex)."""
from __future__ import annotations

from dataclasses import dataclass

from invoice_tool.matching import normalize_for_matching
from invoice_tool.models import ExtractedData, ProcessingPreset, RoutingDecision
from invoice_tool.recipient_guard import _contains_any, _recipient_search_text


@dataclass(frozen=True)
class SupplierRoutingMatch:
    rule_id: str
    routing: RoutingDecision
    exclusive: bool
    source: str = "profile_rule"
    economic_assignment: str | None = None
    payment_reference: str | None = None
    value_not_extracted_from_document: bool = True
    art_deferred: bool = False
    trace_rule: str | None = None


def _tuple_hints(raw) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(str(item).strip() for item in raw if str(item or "").strip())


def _supplier_matches_hint(supplier_normalized: str, hint: str) -> bool:
    normalized_hint = normalize_for_matching(hint)
    if not normalized_hint or not supplier_normalized:
        return False
    if supplier_normalized == normalized_hint:
        return True
    if supplier_normalized.startswith(normalized_hint + " "):
        return True
    if supplier_normalized.endswith(" " + normalized_hint):
        return True
    if f" {normalized_hint} " in f" {supplier_normalized} ":
        return True
    return False


def _hint_in_supplier_only(extracted: ExtractedData, hints: tuple[str, ...]) -> str | None:
    supplier_normalized = normalize_for_matching(extracted.supplier_raw or "")
    if not supplier_normalized:
        return None
    for hint in hints:
        if _supplier_matches_hint(supplier_normalized, hint):
            return hint
    return None


def _hint_in_normalized_text(text: str, hints: tuple[str, ...]) -> str | None:
    normalized = normalize_for_matching(text or "")
    if not normalized:
        return None
    for hint in hints:
        normalized_hint = normalize_for_matching(hint)
        if normalized_hint and normalized_hint in normalized:
            return hint
    return None


def _match_supplier_or_issuer(
    extracted: ExtractedData,
    recognition_hints: tuple[str, ...],
    issuer_hints: tuple[str, ...],
) -> tuple[str | None, str]:
    """Match Lieferant/Aussteller; issuer_hints only for document issuer, not bare text mentions."""
    matched = _hint_in_supplier_only(extracted, recognition_hints)
    if matched:
        return matched, "supplier"
    if issuer_hints:
        matched = _hint_in_normalized_text(extracted.raw_text or "", issuer_hints)
        if matched:
            return matched, "issuer"
    return None, ""


def resolve_supplier_profile_routing(
    extracted: ExtractedData,
    preset: ProcessingPreset,
    profile_data: dict | None,
) -> SupplierRoutingMatch | None:
    if not isinstance(profile_data, dict):
        return None

    vendor_profiles = profile_data.get("vendor_profiles")
    if not isinstance(vendor_profiles, list):
        return None

    for profile in vendor_profiles:
        if not isinstance(profile, dict) or profile.get("enabled", True) is False:
            continue

        rule_id = str(profile.get("id") or "").strip()
        if not rule_id:
            continue

        hints = _tuple_hints(profile.get("recognition_hints"))
        if not hints:
            continue

        issuer_hints = _tuple_hints(profile.get("issuer_hints"))
        match_scope = str(profile.get("match_scope") or "supplier").strip().lower()
        match_source = "supplier"

        if match_scope == "supplier":
            matched_hint, match_source = _match_supplier_or_issuer(extracted, hints, issuer_hints)
        else:
            search_text = normalize_for_matching(
                " ".join(
                    part
                    for part in [
                        extracted.raw_text,
                        extracted.supplier_raw or "",
                    ]
                    if part
                )
            )
            matched_hint = next(
                (hint for hint in hints if normalize_for_matching(hint) in search_text),
                None,
            )
            if matched_hint and match_scope == "supplier_text":
                if not _hint_in_supplier_only(extracted, (matched_hint,)):
                    matched_hint = None

        if not matched_hint:
            continue

        required_recipient_hints = _tuple_hints(profile.get("required_recipient_hints"))
        if required_recipient_hints:
            recipient_text = _recipient_search_text(extracted)
            recipient_match = _contains_any(recipient_text, required_recipient_hints)
            if not recipient_match:
                continue

        category = str(profile.get("category") or profile.get("economic_assignment") or "").strip()
        payment_field = str(profile.get("payment_field") or "").strip()
        target_folder = str(profile.get("target_folder") or payment_field or category or "").strip()
        if target_folder in preset.routing.zielordner:
            zielordner = preset.routing.zielordner[target_folder]
        elif payment_field in preset.routing.zielordner:
            zielordner = preset.routing.zielordner[payment_field]
        elif category in preset.routing.zielordner:
            zielordner = preset.routing.zielordner[category]
        else:
            zielordner = preset.routing.zielordner.get("unklar", "unklar")

        # Payment-only vendor profiles (e.g. cursor-anysphere with payment_field=amex
        # but no category) must NOT fall back to default_art=private. Art is deferred
        # to business-context / software-AI-tool refinement in processing.
        art_deferred = not bool(category)
        art = category if category else preset.routing.unklar_konto
        exclusive = bool(profile.get("exclusive", True))
        payment_reference = str(profile.get("payment_reference") or "").strip() or None

        defer_note = "; art_deferred=True (no category — not default_art)" if art_deferred else ""
        routing = RoutingDecision(
            art=art,
            zielordner=zielordner,
            status="processed",
            konto=None,
            payment_field=payment_field or preset.routing.default_payment_field,
            street_key=None,
            begruendung=(
                f"Supplier-Profilregel '{rule_id}' getroffen "
                f"(hint={matched_hint}, match_source={match_source}, "
                f"source=profile_rule, exclusive={exclusive}){defer_note}."
            ),
        )
        return SupplierRoutingMatch(
            rule_id=rule_id,
            routing=routing,
            exclusive=exclusive,
            economic_assignment=category or None,
            payment_reference=payment_reference,
            art_deferred=art_deferred,
            trace_rule=f"{rule_id}_EP_AMEX_1005" if rule_id.startswith("anthropic") else rule_id,
        )

    return None
