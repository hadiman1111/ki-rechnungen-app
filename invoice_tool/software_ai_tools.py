"""Software-/AI-/Coding-Tool category refinement for routing.

Stabilizes Cursor/Anysphere-class invoices: payment-only vendor profiles must not
blindly force default_art=private, and AI-tool usage without business signals
must go to review (unklar) rather than private or blind ai.
"""
from __future__ import annotations

from dataclasses import dataclass

from invoice_tool.matching import normalize_for_matching
from invoice_tool.models import ExtractedData, ProcessingPreset, RoutingDecision

# Supplier / issuer markers for AI coding / developer tools (generic, not tenant-specific).
_AI_TOOL_SUPPLIER_HINTS = (
    "anysphere",
    "cursor",
    "cursor.com",
    "hi@cursor.com",
    "hi cursor com",
)

# Usage / product markers that indicate AI / token / coding tooling.
_AI_TOOL_USAGE_HINTS = (
    "cursor usage",
    "cursor pro",
    "token-based usage",
    "token based usage",
    "ai usage",
    "developer tool",
    "coding tool",
    "programming tool",
    "gpt",
    "claude",
    "codex",
)

# Refund/credit lines must not flip the economic category away from AI tooling.
_REFUND_CREDIT_HINTS = (
    "refund",
    "credit",
    "gutschrift",
    "mid-month usage paid",
    "mid month usage paid",
)


@dataclass(frozen=True)
class SoftwareAiToolDecision:
    is_ai_coding_tool: bool
    has_business_signal: bool
    art: str | None
    reason: str
    preserve_despite_refund: bool = False


def _search_blob(extracted: ExtractedData) -> str:
    return normalize_for_matching(
        " ".join(
            part
            for part in [
                extracted.raw_text or "",
                extracted.supplier_raw or "",
                extracted.payment_method_raw or "",
                " ".join(extracted.provider_mentions),
                " ".join(extracted.context_markers),
                " ".join(extracted.address_fragments),
                " ".join(extracted.document_type_indicators),
            ]
            if part
        )
    )


def is_software_ai_coding_tool_invoice(extracted: ExtractedData) -> bool:
    blob = _search_blob(extracted)
    has_supplier = any(normalize_for_matching(h) in blob for h in _AI_TOOL_SUPPLIER_HINTS)
    if not has_supplier:
        return False
    has_usage = any(normalize_for_matching(h) in blob for h in _AI_TOOL_USAGE_HINTS)
    # Cursor/Anysphere invoices are AI tooling even when usage wording is sparse,
    # as long as the supplier/issuer is clearly that product family.
    compact = blob.replace(" ", "")
    return (
        has_usage
        or "anysphere" in blob
        or "cursor.com" in compact
        or "hi@cursor.com" in compact
    )


def has_refund_or_credit_lines(extracted: ExtractedData) -> bool:
    blob = _search_blob(extracted)
    return any(normalize_for_matching(h) in blob for h in _REFUND_CREDIT_HINTS)


def has_business_signal_for_ai_tool(
    *,
    art: str,
    art_reason: str,
    street_key: str | None,
    preset: ProcessingPreset,
) -> bool:
    if art in {"ai", "ep"}:
        return True
    if "Business-Context-Regel" in (art_reason or ""):
        return True
    if "Strassenadresse" in (art_reason or "") and "Geschaeftskontext" in (art_reason or ""):
        return True
    if street_key is not None:
        for street_rule in preset.routing.strassen:
            if street_rule.key == street_key and street_rule.art and street_rule.art != "private":
                return True
    return False


def evaluate_software_ai_tool_context(
    extracted: ExtractedData,
    *,
    art: str,
    art_reason: str,
    street_key: str | None,
    preset: ProcessingPreset,
) -> SoftwareAiToolDecision:
    if not is_software_ai_coding_tool_invoice(extracted):
        return SoftwareAiToolDecision(
            is_ai_coding_tool=False,
            has_business_signal=False,
            art=None,
            reason="Kein Software-/AI-Coding-Tool erkannt.",
        )

    business = has_business_signal_for_ai_tool(
        art=art,
        art_reason=art_reason,
        street_key=street_key,
        preset=preset,
    )
    refund = has_refund_or_credit_lines(extracted)
    if business:
        return SoftwareAiToolDecision(
            is_ai_coding_tool=True,
            has_business_signal=True,
            art="ai",
            reason=(
                "Software-/AI-Coding-Tool mit beruflichem Signal → ai"
                + ("; Refund/Credit behält wirtschaftliche Kategorie" if refund else "")
            ),
            preserve_despite_refund=refund,
        )
    return SoftwareAiToolDecision(
        is_ai_coding_tool=True,
        has_business_signal=False,
        art="unklar",
        reason="Software-/AI-Coding-Tool ohne berufliches Signal → unklar (Zur Prüfung).",
        preserve_despite_refund=refund,
    )


def refine_routing_for_software_ai_tool(
    routing: RoutingDecision,
    extracted: ExtractedData,
    *,
    art: str,
    art_reason: str,
    street_key: str | None,
    preset: ProcessingPreset,
) -> tuple[RoutingDecision, str, str]:
    """Refine art/folder for AI coding tools; keep payment when business signal present."""
    decision = evaluate_software_ai_tool_context(
        extracted,
        art=art,
        art_reason=art_reason,
        street_key=street_key,
        preset=preset,
    )
    if not decision.is_ai_coding_tool or decision.art is None:
        return routing, art, art_reason

    new_art = decision.art
    new_reason = f"{art_reason}; {decision.reason}"
    if new_art == "unklar":
        refined = RoutingDecision(
            art="unklar",
            zielordner=preset.routing.zielordner.get("unklar", "unklar"),
            status="unklar",
            konto=None,
            payment_field=preset.routing.unklar_konto,
            street_key=street_key,
            begruendung=f"{routing.begruendung}; {decision.reason}",
        )
        return refined, new_art, new_reason

    # Business signal: keep payment_field / amex folder from routing, force art=ai.
    refined = RoutingDecision(
        art="ai",
        zielordner=routing.zielordner,
        status=routing.status if routing.status else "processed",
        konto=routing.konto,
        payment_field=routing.payment_field,
        street_key=street_key if street_key is not None else routing.street_key,
        begruendung=f"{routing.begruendung}; {decision.reason}",
    )
    return refined, new_art, new_reason
