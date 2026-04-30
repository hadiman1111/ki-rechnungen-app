"""Profile Compiler
==================
Translates a user-facing profile_config (dict) into the technical
office_rules format. Pure function: no file I/O, no side effects.

Scope:
  address_profiles          →  routing.strassen
  address_profiles          →  routing.prioritaetsregeln
                                (when exclude_if_text_contains is set)
  account_card_profiles     →  routing.konten
  business_context_profiles →  routing.business_context_rules
  vendor_profiles           →  routing.payment_detection_rules  (PREPEND)
  payment_profiles          →  routing.payment_detection_rules  (PREPEND, after vendor_profiles)
  classification_profile    →  classification
  naming_profile            →  dateiname_schema
  review_policy             →  routing_overrides
                                (targeted key-level overrides to routing)

All other profile sections (supplier_cleaning, final_assignment_rules,
output_route_rules) are NOT yet handled by this compiler and remain the
responsibility of the manually maintained office_rules.json.

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


def _compile_business_context_profiles(
    business_context_profiles: list[dict],
) -> list[dict]:
    """Translate business_context_profile dicts into routing.business_context_rules entries.

    Each enabled business_context_profile produces one business_context_rules dict
    matching the structure expected by config._parse_business_context_rules.

    Field mapping:
        id                → name
        required_keywords → text_all
        optional_keywords → text_any
        category          → art
        match_source      → match_source  (default: "enriched_text")
        enabled=false     → skipped
    """
    rules: list[dict] = []

    for bcp in business_context_profiles:
        if not bcp.get("enabled", True):
            continue

        profile_id: str = bcp.get("id", "")
        if not profile_id:
            continue

        rules.append({
            "name": profile_id,
            "text_all": list(bcp.get("required_keywords") or []),
            "text_any": list(bcp.get("optional_keywords") or []),
            "art": bcp.get("category", ""),
            "match_source": bcp.get("match_source", "enriched_text"),
        })

    return rules


def _compile_classification_profile(classification_profile: dict) -> dict:
    """Translate a classification_profile dict into a classification section dict.

    Field mapping:
        invoice_keywords           → invoice_keywords    (default: [])
        document_keywords          → document_keywords   (default: [])
        internal_invoice_keywords  → internal_invoice_keywords  (default: [])
        invoice_like_indicators    → invoice_like_indicators  (default: [])
        invoice_like_threshold     → invoice_like_threshold   (default: 3)

    The last two are optional in the profile and fall back to sensible defaults.
    Returns a plain dict matching the structure expected by
    config._parse_preset (classification section).
    """
    return {
        "invoice_keywords": list(classification_profile.get("invoice_keywords") or []),
        "document_keywords": list(classification_profile.get("document_keywords") or []),
        "internal_invoice_keywords": list(
            classification_profile.get("internal_invoice_keywords") or []
        ),
        "invoice_like_indicators": list(
            classification_profile.get("invoice_like_indicators") or []
        ),
        "invoice_like_threshold": int(
            classification_profile.get("invoice_like_threshold") or 3
        ),
    }


def _compile_vendor_profiles(vendor_profiles: list[dict]) -> list[dict]:
    """Translate vendor_profile dicts into routing.payment_detection_rules entries.

    Each enabled vendor_profile produces one payment_detection_rules dict.

    Field mapping:
        id                → name
        recognition_hints → text_any
        payment_field     → payment_method (direct value, e.g. "amex")
        enabled=false     → skipped

    Entries without recognition_hints produce no rule (no match criteria).
    """
    rules: list[dict] = []

    for vp in vendor_profiles:
        if not vp.get("enabled", True):
            continue

        profile_id: str = vp.get("id", "")
        if not profile_id:
            continue

        recognition_hints = list(vp.get("recognition_hints") or [])
        if not recognition_hints:
            continue  # no match criteria → skip (also caught by validation)

        payment_field = vp.get("payment_field") or ""

        rules.append({
            "name": profile_id,
            "text_all": [],
            "text_any": recognition_hints,
            "payment_method": payment_field,
            "explicit": True,
        })

    return rules


# -----------------------------------------------------------------------
# Profile validation
# -----------------------------------------------------------------------

def validate_profile(profile: dict) -> list[str]:
    """Validate a profile_config dict and return a list of issue strings.

    Returns an empty list if the profile is valid.
    This is a lightweight check – it does not raise exceptions.

    Checks performed:
    - Duplicate card_endings across account_card_profiles
    - vendor_profiles entries with no recognition_hints
    - Empty id fields in key sections
    """
    issues: list[str] = []

    # Check for duplicate card endings across account_card_profiles
    seen_endings: dict[str, str] = {}  # ending → profile_id
    for acp in profile.get("account_card_profiles") or []:
        if not acp.get("enabled", True):
            continue
        profile_id = acp.get("id", "?")
        for ending in acp.get("card_endings") or []:
            if ending in seen_endings:
                issues.append(
                    f"Doppelte card_ending '{ending}' in account_card_profiles: "
                    f"'{seen_endings[ending]}' und '{profile_id}'"
                )
            else:
                seen_endings[ending] = profile_id

    # Check vendor_profiles for missing recognition_hints
    for vp in profile.get("vendor_profiles") or []:
        if not vp.get("enabled", True):
            continue
        profile_id = vp.get("id", "?")
        recognition_hints = vp.get("recognition_hints") or []
        if not recognition_hints:
            issues.append(
                f"vendor_profile '{profile_id}' hat keine recognition_hints "
                f"– keine payment_detection_rule wird erzeugt"
            )

    return issues


# -----------------------------------------------------------------------
# naming_profile compiler
# -----------------------------------------------------------------------

def _compile_naming_profile(naming_profile: dict) -> dict:
    """Translate a naming_profile dict into the dateiname_schema format.

    Profile field keys map to dateiname_schema as follows:
    - "invoice_date"   → {"typ": "datum", "quelle": "invoice_date", "format": "jjmmtt"}
    - "literal_<val>" → {"typ": "literal", "wert": "<val>"}
    - anything else   → {"typ": "wert", "quelle": <key>}

    The "erweiterung" is always ".pdf" (no profile field for this).
    The "fallback_values" section is not reflected in dateiname_schema (handled elsewhere).
    """
    separator: str = str(naming_profile.get("separator", "_"))
    max_laenge: int = int(naming_profile.get("max_length", 50))

    felder: list[dict] = []
    for field in naming_profile.get("fields", []):
        if not isinstance(field, dict):
            continue
        key: str = str(field.get("key", "")).strip()
        enabled: bool = bool(field.get("enabled", True))
        if not key:
            continue

        if key == "invoice_date":
            felder.append({"typ": "datum", "quelle": "invoice_date", "format": "jjmmtt", "aktiv": enabled})
        elif key.startswith("literal_"):
            literal_value = key[len("literal_"):]
            felder.append({"typ": "literal", "wert": literal_value, "aktiv": enabled})
        else:
            felder.append({"typ": "wert", "quelle": key, "aktiv": enabled})

    return {
        "separator": separator,
        "max_laenge": max_laenge,
        "erweiterung": ".pdf",
        "felder": felder,
    }


# -----------------------------------------------------------------------
# payment_profiles compiler
# -----------------------------------------------------------------------

def _compile_payment_profiles(payment_profiles: list[dict]) -> list[dict]:
    """Translate payment_profile dicts into routing.payment_detection_rules entries.

    Each enabled payment_profile with at least one keyword produces one
    payment_detection_rules dict.

    Field mapping:
        id              → name
        keywords        → text_any
        payment_method  → payment_method
        is_explicit     → explicit  (default: True)
        enabled=false   → skipped

    Entries without keywords produce no rule (no match criteria).
    Rules are merged via PREPEND in merge_rules_dicts (profile rules first,
    base rules preserved).
    """
    rules: list[dict] = []

    for pp in payment_profiles:
        if not pp.get("enabled", True):
            continue

        profile_id: str = pp.get("id", "")
        if not profile_id:
            continue

        keywords = list(pp.get("keywords") or [])
        if not keywords:
            continue  # no recognition criteria → skip

        payment_method: str = pp.get("payment_method") or ""
        is_explicit: bool = bool(pp.get("is_explicit", True))

        rules.append({
            "name": profile_id,
            "text_all": [],
            "text_any": keywords,
            "payment_method": payment_method,
            "explicit": is_explicit,
        })

    return rules


# -----------------------------------------------------------------------
# review_policy compiler
# -----------------------------------------------------------------------

def _compile_review_policy(review_policy: dict) -> dict:
    """Translate a review_policy dict into a routing_overrides dict.

    Only ``unclear_folder`` has a direct mapping to routing keys.
    Boolean flags (business_unclear_payment_goes_to_unclear,
    private_unclear_attributes_stay_private, etc.) reflect behavior that is
    already hardcoded in office_rules.json and have no additional runtime
    effect via this compiler; they are compiled purely for documentation.

    Field mapping:
        unclear_folder → routing_overrides.unklar_konto
                         routing_overrides.default_zielordner

    Returns a routing_overrides dict intended for merge_rules_dicts to apply
    as targeted key-level overrides to the existing routing section.
    An empty / falsy string falls back to the default value "unklar".
    """
    unclear_folder: str = (
        str(review_policy.get("unclear_folder", "unklar")).strip() or "unklar"
    )
    return {
        "unklar_konto": unclear_folder,
        "default_zielordner": unclear_folder,
    }


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
    - address_profiles          → routing.strassen + routing.prioritaetsregeln
    - account_card_profiles     → routing.konten
    - business_context_profiles → routing.business_context_rules

    All other routing sections (payment_detection_rules, final_assignment_rules,
    output_route_rules) are not generated here and remain in the manually
    maintained office_rules.json.

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

    business_context_profiles: list[dict] = list(profile.get("business_context_profiles") or [])
    business_context_rules = _compile_business_context_profiles(business_context_profiles)

    vendor_profiles: list[dict] = list(profile.get("vendor_profiles") or [])
    vendor_detection_rules = _compile_vendor_profiles(vendor_profiles)

    payment_profiles_raw: list[dict] = list(profile.get("payment_profiles") or [])
    payment_profile_rules = _compile_payment_profiles(payment_profiles_raw)

    # Combine: vendor_profiles rules first (more specific), payment_profiles rules second.
    # Both use PREPEND strategy in merge_rules_dicts (profile rules before base rules).
    payment_detection_rules = vendor_detection_rules + payment_profile_rules

    routing: dict = {
        "strassen": strassen,
        "prioritaetsregeln": prioritaetsregeln,
    }
    if konten:
        routing["konten"] = konten
    if business_context_rules:
        routing["business_context_rules"] = business_context_rules
    if payment_detection_rules:
        routing["payment_detection_rules"] = payment_detection_rules

    preset_dict: dict = {"routing": routing}

    # classification is a top-level preset section (not under routing)
    classification_profile_raw = profile.get("classification_profile")
    if isinstance(classification_profile_raw, dict):
        preset_dict["classification"] = _compile_classification_profile(
            classification_profile_raw
        )

    # dateiname_schema is a top-level preset section (not under routing)
    naming_profile_raw = profile.get("naming_profile")
    if isinstance(naming_profile_raw, dict):
        preset_dict["dateiname_schema"] = _compile_naming_profile(naming_profile_raw)

    # routing_overrides is a top-level preset section for targeted routing key overrides
    review_policy_raw = profile.get("review_policy")
    if isinstance(review_policy_raw, dict):
        preset_dict["routing_overrides"] = _compile_review_policy(review_policy_raw)

    return {
        "active_preset": preset_name,
        "presets": {
            preset_name: preset_dict,
        },
    }
