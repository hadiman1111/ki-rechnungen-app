"""Recipient guard: private routing only with positive recipient proof."""
from __future__ import annotations

from dataclasses import dataclass

from invoice_tool.matching import normalize_for_matching
from invoice_tool.models import ExtractedData, ProcessingPreset, RoutingDecision


@dataclass(frozen=True)
class RecipientGuardDecision:
    outcome: str  # allow | allow_private | force_unklar
    reason: str
    recipient_evidence: str | None = None
    matched_allowlist: str | None = None
    source: str = "recipient_guard"


def _recipient_search_text(extracted: ExtractedData) -> str:
    parts = list(extracted.address_fragments or [])
    if extracted.raw_text:
        for marker in (
            "rechnungsempfaenger",
            "rechnungsempfänger",
            "bill to",
            "billing address",
            "rechnungsadresse",
            "rechnungsanschrift",
            "an:",
            "mandant",
        ):
            normalized = normalize_for_matching(extracted.raw_text)
            marker_norm = normalize_for_matching(marker)
            if marker_norm in normalized:
                parts.append(extracted.raw_text)
                break
    return normalize_for_matching(" ".join(part for part in parts if part))


def _supplier_text(extracted: ExtractedData) -> str:
    return normalize_for_matching(extracted.supplier_raw or "")


def _contains_any(text: str, hints: tuple[str, ...]) -> str | None:
    for hint in hints:
        normalized = normalize_for_matching(hint)
        if normalized and normalized in text:
            return hint
    return None


def _load_policy_lists(profile_data: dict | None) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    if not isinstance(profile_data, dict):
        return (), (), ()
    policy = profile_data.get("recipient_policy")
    if not isinstance(policy, dict):
        return (), (), ()

    def _tuple(key: str) -> tuple[str, ...]:
        raw = policy.get(key)
        if not isinstance(raw, list):
            return ()
        return tuple(str(item).strip() for item in raw if str(item or "").strip())

    return _tuple("business_recipient_hints"), _tuple("private_recipient_hints"), _tuple(
        "foreign_recipient_block_hints"
    )


def _is_default_private_art(proposed_art: str, art_reason: str, preset: ProcessingPreset) -> bool:
    if proposed_art != "private":
        return False
    default_note = f"default={preset.routing.default_art}"
    if default_note in art_reason.lower():
        return True
    return "kein business-kontext erkannt" in art_reason.lower()


def _positive_private_priority_route(priority_routing: RoutingDecision | None) -> bool:
    if priority_routing is None:
        return False
    if priority_routing.art != "private":
        return False
    return "prioritaetsregel" in priority_routing.begruendung.lower()


def evaluate_recipient_guard(
    extracted: ExtractedData,
    preset: ProcessingPreset,
    *,
    profile_data: dict | None,
    proposed_art: str,
    street_key: str | None,
    priority_routing: RoutingDecision | None,
    art_reason: str,
) -> RecipientGuardDecision:
    """Decide whether proposed routing may use private or must go to unklar."""
    business_hints, private_hints, foreign_block_hints = _load_policy_lists(profile_data)
    if not business_hints and not private_hints:
        return RecipientGuardDecision(
            outcome="allow",
            reason="Recipient policy not configured.",
        )

    recipient_text = _recipient_search_text(extracted)
    supplier_text = _supplier_text(extracted)

    if _positive_private_priority_route(priority_routing):
        return RecipientGuardDecision(
            outcome="allow_private",
            reason="Positive private address priority rule matched.",
            recipient_evidence=recipient_text or street_key,
            matched_allowlist="address_priority_rule",
        )

    business_match = _contains_any(recipient_text, business_hints)
    if business_match:
        return RecipientGuardDecision(
            outcome="allow",
            reason=f"Business recipient allowlist matched: {business_match}.",
            recipient_evidence=recipient_text,
            matched_allowlist=business_match,
        )

    private_match = _contains_any(recipient_text, private_hints)
    if private_match:
        return RecipientGuardDecision(
            outcome="allow_private",
            reason=f"Private recipient allowlist matched: {private_match}.",
            recipient_evidence=recipient_text,
            matched_allowlist=private_match,
        )

    if street_key == "roete" and proposed_art == "private":
        if "somaa" not in normalize_for_matching(extracted.raw_text):
            return RecipientGuardDecision(
                outcome="allow_private",
                reason="Private street key matched without SOMAA business marker.",
                recipient_evidence=street_key,
                matched_allowlist="roete-private-street",
            )

    if foreign_block_hints and recipient_text:
        foreign_match = _contains_any(recipient_text, foreign_block_hints)
        if foreign_match:
            return RecipientGuardDecision(
                outcome="force_unklar",
                reason=f"Foreign recipient marker detected: {foreign_match}.",
                recipient_evidence=recipient_text,
                matched_allowlist=foreign_match,
            )

    if recipient_text and business_hints and not business_match:
        if not private_match and _is_default_private_art(proposed_art, art_reason, preset):
            return RecipientGuardDecision(
                outcome="force_unklar",
                reason="Recipient present but not on business/private allowlists.",
                recipient_evidence=recipient_text,
            )

    if _is_default_private_art(proposed_art, art_reason, preset):
        return RecipientGuardDecision(
            outcome="force_unklar",
            reason="Private art would come from default fallback without recipient proof.",
            recipient_evidence=recipient_text or None,
        )

    if proposed_art == "private" and not recipient_text and not street_key:
        return RecipientGuardDecision(
            outcome="force_unklar",
            reason="Private art blocked: no recipient evidence.",
        )

    if proposed_art == "private" and supplier_text and recipient_text == supplier_text:
        return RecipientGuardDecision(
            outcome="force_unklar",
            reason="Supplier name must not be treated as private recipient.",
            recipient_evidence=recipient_text,
        )

    return RecipientGuardDecision(
        outcome="allow",
        reason="Recipient guard did not block routing.",
        recipient_evidence=recipient_text or None,
    )


def apply_recipient_guard_to_routing(
    routing: RoutingDecision,
    guard: RecipientGuardDecision,
    preset: ProcessingPreset,
    *,
    street_key: str | None,
) -> RoutingDecision:
    if guard.outcome != "force_unklar":
        return routing

    unklar_folder = preset.routing.zielordner.get("unklar", "unklar")
    return RoutingDecision(
        art="unklar",
        zielordner=unklar_folder,
        status="unklar",
        konto=None,
        payment_field=preset.routing.unklar_konto,
        street_key=street_key,
        begruendung=f"{routing.begruendung}; Recipient-Guard: {guard.reason}",
    )
