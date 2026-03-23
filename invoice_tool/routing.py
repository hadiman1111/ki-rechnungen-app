from __future__ import annotations

import re
from dataclasses import dataclass

from invoice_tool.matching import contains_fuzzy_phrase, normalize_for_matching
from invoice_tool.models import (
    AccountDecision,
    ExtractedData,
    PaymentDecision,
    PriorityRouteRule,
    ProcessingPreset,
    RoutingDecision,
)


@dataclass(frozen=True)
class Match:
    rule_name: str
    konto: str | None
    payment_field: str | None
    art_override: str | None
    source: str
    clue: str


def _normalize_search_text(extracted: ExtractedData) -> str:
    parts = [
        extracted.raw_text,
        extracted.payment_method_raw or "",
        " ".join(extracted.provider_mentions),
        " ".join(extracted.address_fragments),
        " ".join(extracted.context_markers),
        " ".join(extracted.document_type_indicators),
    ]
    return normalize_for_matching(" ".join(part for part in parts if part))


def _rule_matches_provider_hint(search_text: str, rule) -> list[Match]:
    if not any(normalize_for_matching(hint) in search_text for hint in rule.anbieter_hinweise):
        return []
    if rule.zuweisungs_hinweise and not any(
        normalize_for_matching(hint) in search_text for hint in rule.zuweisungs_hinweise
    ):
        return []
    return [
        Match(
            rule_name=rule.name,
            konto=rule.konto,
            payment_field=rule.payment_field,
            art_override=rule.art_override,
            source="provider",
            clue="provider-text",
        )
    ]


def resolve_account(extracted: ExtractedData, preset: ProcessingPreset) -> AccountDecision:
    search_text = _normalize_search_text(extracted)
    source_matches: dict[str, list[Match]] = {"card": [], "apple": [], "provider": []}

    for rule in preset.routing.konten:
        for ending in extracted.card_endings:
            if ending in rule.karten_endungen:
                source_matches["card"].append(
                    Match(
                        rule_name=rule.name,
                        konto=rule.konto,
                        payment_field=rule.payment_field,
                        art_override=rule.art_override,
                        source="card",
                        clue=ending,
                    )
                )
        for ending in extracted.apple_pay_endings:
            if ending in rule.apple_pay_endungen:
                source_matches["apple"].append(
                    Match(
                        rule_name=rule.name,
                        konto=rule.konto,
                        payment_field=rule.payment_field,
                        art_override=rule.art_override,
                        source="apple",
                        clue=ending,
                    )
                )
        source_matches["provider"].extend(_rule_matches_provider_hint(search_text, rule))

    contradiction = False
    trusted_match: Match | None = None
    for source in ("card", "apple", "provider"):
        matches = source_matches[source]
        unique_rules = {match.rule_name for match in matches}
        if len(unique_rules) == 1 and matches:
            trusted_match = matches[0]
            break
        if len(unique_rules) > 1:
            contradiction = True
            break

    if trusted_match:
        for source, matches in source_matches.items():
            if source == trusted_match.source:
                continue
            if any(match.rule_name != trusted_match.rule_name for match in matches):
                contradiction = True
                break

    if contradiction:
        return AccountDecision(
            konto=trusted_match.konto if trusted_match else None,
            payment_field=trusted_match.payment_field if trusted_match else None,
            art_override=trusted_match.art_override if trusted_match else None,
            ist_unklar=True,
            ist_widerspruechlich=True,
            begruendung="Widerspruechliche Konto- oder Anbieterhinweise erkannt.",
            matched_rule=trusted_match.rule_name if trusted_match else None,
        )

    if trusted_match:
        return AccountDecision(
            konto=trusted_match.konto,
            payment_field=trusted_match.payment_field,
            art_override=trusted_match.art_override,
            ist_unklar=False,
            ist_widerspruechlich=False,
            begruendung=f"Aufloesung ueber {trusted_match.source}: {trusted_match.clue}",
            matched_rule=trusted_match.rule_name,
        )

    return AccountDecision(
        konto=None,
        payment_field=None,
        art_override=None,
        ist_unklar=True,
        ist_widerspruechlich=False,
        begruendung="Keine belastbaren Kontohinweise gefunden.",
        matched_rule=None,
    )


def detect_street(extracted: ExtractedData, preset: ProcessingPreset) -> str | None:
    search_text = _normalize_search_text(extracted)
    for street_rule in preset.routing.strassen:
        for variante in street_rule.varianten:
            if contains_fuzzy_phrase(search_text, variante, street_rule.fuzzy_threshold):
                return street_rule.key
    return None


def resolve_priority_routing(
    extracted: ExtractedData,
    account_decision: AccountDecision,
    street_key: str | None,
    preset: ProcessingPreset,
) -> RoutingDecision | None:
    search_text = _normalize_search_text(extracted)
    for rule in preset.routing.prioritaetsregeln:
        if not _priority_rule_matches(rule, search_text, account_decision, street_key):
            continue
        return RoutingDecision(
            art=rule.art,
            zielordner=preset.routing.zielordner[rule.zielordner],
            status=rule.status,
            konto=account_decision.konto,
            payment_field=account_decision.payment_field or preset.routing.unklar_konto,
            street_key=street_key,
            begruendung=f"Prioritaetsregel '{rule.name}' hat Standardrouting ueberschrieben.",
        )
    return None


def determine_business_context(
    extracted: ExtractedData,
    account_decision: AccountDecision,
    preset: ProcessingPreset,
) -> tuple[str, str]:
    search_text = _normalize_search_text(extracted)
    for rule in preset.routing.business_context_rules:
        if rule.text_all and not all(
            normalize_for_matching(text) in search_text for text in rule.text_all
        ):
            continue
        if rule.text_any and not any(
            normalize_for_matching(text) in search_text for text in rule.text_any
        ):
            continue
        return rule.art, f"Business-Context-Regel '{rule.name}' getroffen."

    if account_decision.art_override and account_decision.art_override != "private":
        return account_decision.art_override, "Art aus Kontozuordnung abgeleitet."

    return preset.routing.default_art, f"Kein Business-Kontext erkannt, Default={preset.routing.default_art}."


def detect_payment_method(extracted: ExtractedData, preset: ProcessingPreset) -> PaymentDecision:
    search_text = _normalize_search_text(extracted)
    for rule in preset.routing.payment_detection_rules:
        matched_signals: list[str] = []
        if rule.text_all:
            all_hits = _matching_payment_hints(search_text, rule.text_all)
            if len(all_hits) != len(rule.text_all):
                continue
            matched_signals.extend(all_hits)
        if rule.text_any:
            any_hits = _matching_payment_hints(search_text, rule.text_any)
            if not any_hits:
                continue
            matched_signals.extend(any_hits)
        signal_text = ", ".join(dict.fromkeys(matched_signals)) if matched_signals else "keine"
        return PaymentDecision(
            payment_method=rule.payment_method,
            explicit=rule.explicit,
            begruendung=f"Payment-Regel '{rule.name}' getroffen. Signale: {signal_text}.",
        )
    return PaymentDecision(
        payment_method=preset.routing.default_payment_method,
        explicit=False,
        begruendung="Keine explizite Payment-Regel getroffen. Signale: keine.",
    )


def apply_final_assignment(
    *,
    art: str,
    payment_decision: PaymentDecision,
    account_decision: AccountDecision,
    street_key: str | None,
    preset: ProcessingPreset,
) -> RoutingDecision:
    for rule in preset.routing.final_assignment_rules:
        if rule.art_any and art not in set(rule.art_any):
            continue
        if rule.payment_method_any and payment_decision.payment_method not in set(
            rule.payment_method_any
        ):
            continue
        if rule.account_payment_field_any:
            if (account_decision.payment_field or "") not in set(rule.account_payment_field_any):
                continue
        if rule.account_konto_any:
            if (account_decision.konto or "") not in set(rule.account_konto_any):
                continue

        final_art = account_decision.art_override if rule.use_account_art else rule.output_art or art
        final_konto = account_decision.konto if rule.use_account_konto else rule.output_konto
        final_payment_field = (
            account_decision.payment_field
            if rule.use_account_payment_field
            else rule.output_payment_field
        )
        final_payment_field = final_payment_field or preset.routing.default_payment_field
        zielordner, status = resolve_output_route(
            art=final_art or art,
            payment_field=final_payment_field,
            preset=preset,
        )
        return RoutingDecision(
            art=final_art or art,
            zielordner=zielordner,
            status=status,
            konto=final_konto,
            payment_field=final_payment_field,
            street_key=street_key,
            begruendung=(
                f"{account_decision.begruendung}; {payment_decision.begruendung}; "
                f"Final-Assignment-Regel '{rule.name}' getroffen."
            ),
        )

    zielordner, status = resolve_output_route(
        art=art,
        payment_field=preset.routing.default_payment_field,
        preset=preset,
    )
    return RoutingDecision(
        art=art,
        zielordner=zielordner,
        status=status,
        konto=None,
        payment_field=preset.routing.default_payment_field,
        street_key=street_key,
        begruendung=(
            f"{account_decision.begruendung}; {payment_decision.begruendung}; "
            "Keine Final-Assignment-Regel getroffen."
        ),
    )


def resolve_output_route(*, art: str, payment_field: str, preset: ProcessingPreset) -> tuple[str, str]:
    for rule in preset.routing.output_route_rules:
        if rule.art_any and art not in set(rule.art_any):
            continue
        if rule.payment_field_any and payment_field not in set(rule.payment_field_any):
            continue
        return preset.routing.zielordner[rule.zielordner], rule.status
    return (
        preset.routing.zielordner[preset.routing.default_zielordner],
        preset.routing.default_status,
    )


def _priority_rule_matches(
    rule: PriorityRouteRule,
    search_text: str,
    account_decision: AccountDecision,
    street_key: str | None,
) -> bool:
    if rule.text_all and not all(
        normalize_for_matching(text) in search_text for text in rule.text_all
    ):
        return False
    if rule.text_any and not any(
        normalize_for_matching(text) in search_text for text in rule.text_any
    ):
        return False
    if rule.provider_any and not any(
        normalize_for_matching(provider) in search_text for provider in rule.provider_any
    ):
        return False
    if rule.street_any and (street_key or "none") not in set(rule.street_any):
        return False
    if rule.require_no_clear_payment and _has_clear_payment(account_decision):
        return False
    return True


def _has_clear_payment(account_decision: AccountDecision) -> bool:
    return bool(account_decision.payment_field) and not account_decision.ist_widerspruechlich


def _contains_payment_hint(search_text: str, hint: str) -> bool:
    normalized_hint = normalize_for_matching(hint)
    if not normalized_hint:
        return False
    pattern = rf"(?<![a-z0-9]){re.escape(normalized_hint)}(?![a-z0-9])"
    return re.search(pattern, search_text) is not None


def _matching_payment_hints(search_text: str, hints: tuple[str, ...]) -> list[str]:
    return [hint for hint in hints if _contains_payment_hint(search_text, hint)]
