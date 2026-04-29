"""Profile Compiler
==================
Translates a user-facing profile_config (dict) into the technical
office_rules format. Pure function: no file I/O, no side effects.

Scope:
  address_profiles       →  routing.strassen
  address_profiles       →  routing.prioritaetsregeln
                             (when exclude_if_text_contains is set)
  account_card_profiles  →  routing.konten

All other profile sections (business_context_profiles, vendor_profiles,
classification_profile, naming_profile, supplier_cleaning,
final_assignment_rules, output_route_rules) are NOT yet handled by this
compiler and remain the responsibility of the manually maintained
office_rules.json.

Design principles:
- No SOMAA-specific logic, no user-specific hardcoding.
- No file I/O; callers are responsible for loading/saving.
- dict → dict: easy to unit-test and to preview in a future UI.
"""
from __future__ import annotations

from invoice_tool.matching import normalize_for_matching
from invoice_tool.street_variants import _split_street_suffix, generate_street_variants

# -----------------------------------------------------------------------
# Matching-mode → fuzzy threshold mapping
# -----------------------------------------------------------------------

_MATCHING_MODE_THRESHOLDS: dict[str, float] = {
    "strict": 0.95,
    "normal": 0.84,
    "tolerant": 0.70,
}
_DEFAULT_THRESHOLD: float = 0.84


# -----------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------

def _street_key_from_name(street: str) -> str:
    """Derive a short, stable, normalized routing key from a canonical street name.

    Uses the base part of the street name (without suffix type) and
    normalises it via normalize_for_matching so the result is lowercase ASCII.

    Examples:
        "Rötestraße"    → "roete"
        "Bismarckstraße"→ "bismarck"
        "Hauptweg"      → "haupt"
    """
    base, _ = _split_street_suffix(street)
    return normalize_for_matching(base)


def _compile_address_profiles(
    address_profiles: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Translate a list of address_profile dicts into (strassen, prioritaetsregeln).

    Each enabled address_profile produces:
    - one routing.strassen entry (key, art, varianten, fuzzy_threshold)
    - optionally one routing.prioritaetsregeln entry when
      exclude_if_text_contains is non-empty

    Returns:
        (strassen, prioritaetsregeln) – both are plain dicts matching the
        structure expected by config._parse_street_rules and
        config._parse_priority_rules respectively.
    """
    strassen: list[dict] = []
    prioritaetsregeln: list[dict] = []

    for profile in address_profiles:
        # Respect the enabled flag (default: True when absent)
        if not profile.get("enabled", True):
            continue

        canonical = profile.get("canonical_address") or {}
        street = canonical.get("street", "").strip()
        if not street:
            continue

        house_number: str | None = canonical.get("house_number") or None
        advanced_raw = profile.get("advanced_variants") or []
        advanced: list[str] | None = list(advanced_raw) if advanced_raw else None

        category: str = profile.get("category", "")
        mode: str = profile.get("matching_mode") or "normal"
        threshold: float = _MATCHING_MODE_THRESHOLDS.get(mode, _DEFAULT_THRESHOLD)

        # Derive street key from the canonical street name (general, no hardcoding)
        key: str = _street_key_from_name(street)

        # Use profile id for priority rule naming; fall back to street key
        profile_id: str = profile.get("id") or key

        varianten = generate_street_variants(
            street,
            house_number=house_number,
            advanced_variants=advanced,
        )

        strassen.append({
            "key": key,
            "art": category,
            "varianten": varianten,
            "fuzzy_threshold": threshold,
        })

        # Priority rule: address applies only when exclude terms are absent
        exclude = [t for t in (profile.get("exclude_if_text_contains") or []) if t]
        if exclude:
            prioritaetsregeln.append({
                "name": f"address-profile-{profile_id}-priority",
                "text_all": [],
                "text_any": [],
                "provider_any": [],
                "street_any": [key],
                "text_none_any": exclude,
                "require_no_clear_payment": False,
                "zielordner": category,
                "art": category,
                "status": "processed",
            })

    return strassen, prioritaetsregeln


def _compile_account_card_profiles(
    account_card_profiles: list[dict],
) -> list[dict]:
    """Translate a list of account_card_profile dicts into routing.konten entries.

    Each enabled account_card_profile produces one konten dict entry
    matching the structure expected by config._parse_account_rules.

    Field mapping:
        id              → name
        category        → art_override  (may be None/"unklar" → stored as-is)
        payment_field   → payment_field  AND  konto (same value)
        card_endings    → karten_endungen
        apple_pay_endings → apple_pay_endungen
        iban_endings    → iban_endungen
        provider_hints  → anbieter_hinweise
        assignment_hints → zuweisungs_hinweise

    Note: profile "category": "unklar" maps to art_override=None since "unklar"
    means no explicit art override is desired (the routing engine uses it as a
    fallback, not as a forced category).
    """
    konten: list[dict] = []

    for acp in account_card_profiles:
        if not acp.get("enabled", True):
            continue

        profile_id: str = acp.get("id", "")
        if not profile_id:
            continue

        category = acp.get("category") or None
        # "unklar" as category means no art override – same convention as
        # the manually maintained office_rules.json (amex has art_override=null)
        art_override = category if category and category != "unklar" else None

        payment_field = acp.get("payment_field") or None

        konten.append({
            "name": profile_id,
            "konto": payment_field,          # same as payment_field for bank accounts
            "payment_field": payment_field,
            "art_override": art_override,
            "karten_endungen": list(acp.get("card_endings") or []),
            "apple_pay_endungen": list(acp.get("apple_pay_endings") or []),
            "iban_endungen": list(acp.get("iban_endings") or []),
            "anbieter_hinweise": list(acp.get("provider_hints") or []),
            "zuweisungs_hinweise": list(acp.get("assignment_hints") or []),
        })

    return konten


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------

def compile_profile_to_rules(
    profile: dict,
    *,
    preset_name: str = "office_default",
) -> dict:
    """Compile a profile_config dict into an office_rules-format dict.

    Generates the following routing sections when the corresponding profile
    sections are present:
    - address_profiles      → routing.strassen + routing.prioritaetsregeln
    - account_card_profiles → routing.konten

    All other routing sections (business_context_rules, payment_detection_rules,
    final_assignment_rules, output_route_rules) are not generated here and
    remain in the manually maintained office_rules.json.

    Args:
        profile:     Parsed profile_config, e.g. loaded from profile_config.json.
        preset_name: Name of the generated preset key.

    Returns:
        A dict in office_rules format containing only the generated sections.
        Callers use merge_rules_dicts() to combine this with the base rules.
        No files are read or written by this function.
    """
    address_profiles: list[dict] = list(profile.get("address_profiles") or [])
    strassen, prioritaetsregeln = _compile_address_profiles(address_profiles)

    account_card_profiles: list[dict] = list(profile.get("account_card_profiles") or [])
    konten = _compile_account_card_profiles(account_card_profiles)

    routing: dict = {
        "strassen": strassen,
        "prioritaetsregeln": prioritaetsregeln,
    }
    if konten:
        routing["konten"] = konten

    return {
        "active_preset": preset_name,
        "presets": {
            preset_name: {
                "routing": routing,
            }
        },
    }
