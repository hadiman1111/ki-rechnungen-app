"""Track-B UI-v2 profile / policy view-models (pure, testable).

Represents generic, profile-configurable business / payment / account
evidence rules without private tenant defaults, without productive
execution, and without processing-core imports or filesystem access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

from invoice_tool.ui_v2.policy_runtime_bridge import (
    MSG_FILENAME_NOT_SOURCE_OF_TRUTH,
    MSG_GENERIC_CARD_UNCLEAR,
    MSG_SUPPLIER_IBAN_NOT_PAYER,
    MSG_UNKNOWN_EVIDENCE_REVIEW,
    RuntimePolicyBridgeResult,
    build_runtime_policy_intent,
)

ReadinessStatus = Literal["empty", "incomplete", "review", "ready", "blocked"]

# Required honest product copy — profiles page.
MSG_PROFILES_CONTAIN_RULES = (
    "Profile enthalten die Regeln eines Nutzers oder Mandanten."
)
MSG_PAYMENT_BUSINESS_PER_PROFILE = (
    "Zahlungs- und Geschäftsnachweise werden pro Profil gepflegt."
)
MSG_WITHOUT_EVIDENCE_REVIEW = (
    "Ohne eindeutigen Nachweis bleibt ein Beleg zur Prüfung."
)

# Required honest product copy — configurations page.
MSG_CONFIGS_APPLY_RULES = (
    "Konfigurationen bestimmen, wann welche Regeln angewendet werden."
)
MSG_UNCLEAR_NOT_AUTO = "Unklare Fälle werden nicht automatisch entschieden."
MSG_TARGETS_AFTER_SAFE_CONFIG = (
    "Zielorte werden erst nach sicherer Konfiguration verwendet."
)

# Required honest product copy — policy editor (shared with controls module).
MSG_FILENAME_NOT_TRUTH = "Dateinamen sind keine Belegwahrheit."
MSG_UNCLEAR_STAYS_REVIEW = "Unklare Fälle bleiben zur Prüfung."
MSG_SUPPLIER_IBAN_NOT_USER_PAYMENT = (
    "Lieferanten-IBAN ist kein Zahlungsnachweis des Nutzers."
)
MSG_CARD_HINT_WITHOUT_REF_UNCLEAR = (
    "Kartenhinweise ohne konfigurierte Referenz bleiben unklar."
)

MSG_NO_PRIVATE_DEFAULT_PROFILE = "Kein privates Standardprofil vorhanden."
MSG_PROFILE_RULES_SPECIFIC = (
    "Geschäfts-, Zahlungs- und Kontoregeln sind profilspezifisch."
)
MSG_READINESS_ONLY = "Readiness — Speichern der Policy ist hier noch nicht freigegeben."
MSG_NO_PRODUCTIVE_EXECUTION = "Produktive Verarbeitung ist noch nicht freigegeben."
MSG_EMPTY_PROFILES = "Noch kein Profil vorhanden."
MSG_EMPTY_PROFILES_DETAIL = (
    "Legen Sie bei Bedarf ein generisches Profil an — "
    "es werden keine privaten Standardwerte vorbefüllt."
)

PRIVATE_DEFAULT_MARKERS: tuple[str, ...] = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX",
    "voba",
    "/Users/",
    "Desktop/",
)


@dataclass(frozen=True)
class ProfilePolicyIdentity:
    """Generic profile identity — display name only, no private defaults."""

    display_name: str = ""
    profile_id: str = ""

    def is_blank(self) -> bool:
        return not str(self.display_name or "").strip() and not str(
            self.profile_id or ""
        ).strip()


@dataclass(frozen=True)
class BusinessEvidenceRule:
    """Profile-configurable business / organization identifiers."""

    organization_identifiers: tuple[str, ...] = ()
    billing_address_hints: tuple[str, ...] = ()
    notes: str = ""

    def has_configured_evidence(self) -> bool:
        return bool(self.organization_identifiers) or bool(self.billing_address_hints)


@dataclass(frozen=True)
class PaymentEvidenceRule:
    """Profile-configurable payment evidence identifiers."""

    payment_identifiers: tuple[str, ...] = ()
    require_explicit_payer_evidence: bool = True
    supplier_iban_alone_is_payer_evidence: bool = False
    notes: str = ""

    def has_configured_evidence(self) -> bool:
        return bool(self.payment_identifiers)


@dataclass(frozen=True)
class AccountEvidenceRule:
    """Profile-configurable account / card reference hints."""

    account_reference_hints: tuple[str, ...] = ()
    card_reference_hints: tuple[str, ...] = ()
    generic_card_without_reference_is_clear: bool = False
    notes: str = ""

    def has_configured_evidence(self) -> bool:
        return bool(self.account_reference_hints) or bool(self.card_reference_hints)


@dataclass(frozen=True)
class ProfilePolicyViewModel:
    """Combined profile-policy readiness view-model for Track-B UI-v2."""

    identity: ProfilePolicyIdentity = field(default_factory=ProfilePolicyIdentity)
    business: BusinessEvidenceRule = field(default_factory=BusinessEvidenceRule)
    payment: PaymentEvidenceRule = field(default_factory=PaymentEvidenceRule)
    account: AccountEvidenceRule = field(default_factory=AccountEvidenceRule)
    readiness_status: ReadinessStatus = "empty"
    readiness_reasons: tuple[str, ...] = ()
    honest_copy: tuple[str, ...] = ()
    filename_is_source_of_truth: bool = False
    supplier_iban_alone_is_payer_evidence: bool = False
    generic_card_without_account_ref_is_clear: bool = False
    unclear_evidence_goes_to_review: bool = True
    has_private_defaults: bool = False
    has_productive_execution_toggle: bool = False
    productive_execution_enabled: bool = False
    persistence_enabled: bool = False
    rules_are_profile_specific: bool = True
    policy_intent_status: str = "incomplete"


@dataclass(frozen=True)
class ProfilesPagePolicyPanelVM:
    """Readiness panel copy/state for the Track-B profiles page."""

    banner: str
    honest_copy: tuple[str, ...]
    empty: bool
    empty_title: str
    empty_detail: str
    selected_readiness_label: str
    selected_readiness_status: ReadinessStatus
    rules_profile_specific_label: str
    no_private_default_label: str
    actions_readiness_only: bool
    actions_label: str
    has_private_defaults: bool
    has_productive_execution_toggle: bool


@dataclass(frozen=True)
class ConfigurationsPagePolicyPanelVM:
    """Readiness panel copy/state for the Track-B configurations page."""

    banner: str
    honest_copy: tuple[str, ...]
    linked_profile_label: str
    linked_policy_status: str
    unmatched_concept_label: str
    unclear_not_auto_label: str
    targets_after_safe_config_label: str
    has_private_destination_defaults: bool
    has_productive_execution_toggle: bool
    scans_folders: bool
    processes_pdfs: bool


def _normalize_strings(values: Sequence[Any] | None) -> tuple[str, ...]:
    if not values:
        return ()
    out: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return tuple(dict.fromkeys(out))


def _contains_private_marker(text: str) -> bool:
    lowered = text.lower()
    for marker in PRIVATE_DEFAULT_MARKERS:
        if marker.lower() in lowered:
            return True
    return False


def build_profile_policy_view_model(
    *,
    display_name: str = "",
    profile_id: str = "",
    organization_identifiers: Sequence[str] | None = None,
    billing_address_hints: Sequence[str] | None = None,
    payment_identifiers: Sequence[str] | None = None,
    account_reference_hints: Sequence[str] | None = None,
    card_reference_hints: Sequence[str] | None = None,
    classification_policy: Any = None,
    configuration_present: bool = False,
) -> ProfilePolicyViewModel:
    """Build a generic profile-policy VM from explicit inputs only.

    Empty / missing evidence yields incomplete or review readiness — never
    fake certainty and never private tenant defaults.
    """

    identity = ProfilePolicyIdentity(
        display_name=str(display_name or "").strip(),
        profile_id=str(profile_id or "").strip(),
    )
    business = BusinessEvidenceRule(
        organization_identifiers=_normalize_strings(organization_identifiers),
        billing_address_hints=_normalize_strings(billing_address_hints),
    )
    payment = PaymentEvidenceRule(
        payment_identifiers=_normalize_strings(payment_identifiers),
        require_explicit_payer_evidence=True,
        supplier_iban_alone_is_payer_evidence=False,
    )
    account = AccountEvidenceRule(
        account_reference_hints=_normalize_strings(account_reference_hints),
        card_reference_hints=_normalize_strings(card_reference_hints),
        generic_card_without_reference_is_clear=False,
    )

    # Private markers in a user-chosen display name are not treated as product
    # defaults; defaults themselves must stay empty/generic (enforced in tests).
    bridge = align_profile_policy_with_runtime_intent(
        classification_policy=classification_policy,
        profile_policy=None,
    )
    policy_intent_status = bridge.status

    readiness_status, reasons = validate_profile_policy_readiness(
        identity=identity,
        business=business,
        payment=payment,
        account=account,
        has_private_defaults=False,
        configuration_present=configuration_present,
        policy_intent_status=policy_intent_status,
    )

    honest_copy = (
        MSG_PROFILES_CONTAIN_RULES,
        MSG_PAYMENT_BUSINESS_PER_PROFILE,
        MSG_WITHOUT_EVIDENCE_REVIEW,
        MSG_FILENAME_NOT_TRUTH,
        MSG_UNCLEAR_STAYS_REVIEW,
        MSG_SUPPLIER_IBAN_NOT_USER_PAYMENT,
        MSG_CARD_HINT_WITHOUT_REF_UNCLEAR,
        MSG_NO_PRODUCTIVE_EXECUTION,
    )
    return ProfilePolicyViewModel(
        identity=identity,
        business=business,
        payment=payment,
        account=account,
        readiness_status=readiness_status,
        readiness_reasons=reasons,
        honest_copy=honest_copy,
        filename_is_source_of_truth=False,
        supplier_iban_alone_is_payer_evidence=False,
        generic_card_without_account_ref_is_clear=False,
        unclear_evidence_goes_to_review=True,
        has_private_defaults=False,
        has_productive_execution_toggle=False,
        productive_execution_enabled=False,
        persistence_enabled=False,
        rules_are_profile_specific=True,
        policy_intent_status=policy_intent_status,
    )


def validate_profile_policy_readiness(
    *,
    identity: ProfilePolicyIdentity,
    business: BusinessEvidenceRule,
    payment: PaymentEvidenceRule,
    account: AccountEvidenceRule,
    has_private_defaults: bool = False,
    configuration_present: bool = False,
    policy_intent_status: str = "incomplete",
) -> tuple[ReadinessStatus, tuple[str, ...]]:
    """Derive readiness from explicit profile/policy state only."""

    reasons: list[str] = []

    if has_private_defaults:
        reasons.append("Private Standardwerte sind nicht erlaubt.")
        return "blocked", tuple(reasons)

    if identity.is_blank():
        reasons.append(MSG_EMPTY_PROFILES)
        return "empty", tuple(reasons)

    if policy_intent_status == "blocked":
        reasons.append("Policy-Intent ist blockiert — unsichere Regelkombination.")
        return "blocked", tuple(reasons)

    missing_evidence = (
        not business.has_configured_evidence()
        or not payment.has_configured_evidence()
        or not account.has_configured_evidence()
    )
    if missing_evidence:
        reasons.append(MSG_WITHOUT_EVIDENCE_REVIEW)
        reasons.append(MSG_UNCLEAR_STAYS_REVIEW)
        # Missing configured evidence → review/unclear readiness, not fake certainty.
        return "review", tuple(dict.fromkeys(reasons))

    if not configuration_present:
        reasons.append(MSG_CONFIGS_APPLY_RULES)
        reasons.append(MSG_TARGETS_AFTER_SAFE_CONFIG)
        return "incomplete", tuple(reasons)

    if policy_intent_status == "incomplete":
        reasons.append("Verarbeitungsregeln sind noch nicht vollständig konfiguriert.")
        return "incomplete", tuple(reasons)

    reasons.append(MSG_PAYMENT_BUSINESS_PER_PROFILE)
    reasons.append(MSG_FILENAME_NOT_TRUTH)
    return "ready", tuple(reasons)


def blank_profile_policy_view_model() -> ProfilePolicyViewModel:
    """Safe empty defaults — no private tenant profile."""

    return build_profile_policy_view_model()


def build_profiles_page_policy_panel_vm(
    *,
    profile_count: int = 0,
    selected_display_name: str = "",
    selected_profile_id: str = "",
    organization_identifiers: Sequence[str] | None = None,
    payment_identifiers: Sequence[str] | None = None,
    account_reference_hints: Sequence[str] | None = None,
    card_reference_hints: Sequence[str] | None = None,
    classification_policy: Any = None,
    configuration_present: bool = False,
) -> ProfilesPagePolicyPanelVM:
    """Build readiness panel VM for the profiles page (no GUI)."""

    empty = profile_count <= 0
    if empty:
        vm = blank_profile_policy_view_model()
    else:
        vm = build_profile_policy_view_model(
            display_name=selected_display_name,
            profile_id=selected_profile_id,
            organization_identifiers=organization_identifiers,
            payment_identifiers=payment_identifiers,
            account_reference_hints=account_reference_hints,
            card_reference_hints=card_reference_hints,
            classification_policy=classification_policy,
            configuration_present=configuration_present,
        )

    status_labels = {
        "empty": "Leer — kein Profil",
        "incomplete": "Unvollständig",
        "review": "Zur Prüfung / unklar",
        "ready": "Readiness ok (noch keine produktive Ausführung)",
        "blocked": "Blockiert",
    }
    return ProfilesPagePolicyPanelVM(
        banner=(
            f"{MSG_PROFILES_CONTAIN_RULES} {MSG_PAYMENT_BUSINESS_PER_PROFILE} "
            f"{MSG_WITHOUT_EVIDENCE_REVIEW}"
        ),
        honest_copy=(
            MSG_PROFILES_CONTAIN_RULES,
            MSG_PAYMENT_BUSINESS_PER_PROFILE,
            MSG_WITHOUT_EVIDENCE_REVIEW,
            MSG_PROFILE_RULES_SPECIFIC,
            MSG_NO_PRIVATE_DEFAULT_PROFILE,
            MSG_NO_PRODUCTIVE_EXECUTION,
        ),
        empty=empty,
        empty_title=MSG_EMPTY_PROFILES,
        empty_detail=MSG_EMPTY_PROFILES_DETAIL,
        selected_readiness_label=status_labels.get(
            vm.readiness_status, vm.readiness_status
        ),
        selected_readiness_status=vm.readiness_status,
        rules_profile_specific_label=MSG_PROFILE_RULES_SPECIFIC,
        no_private_default_label=MSG_NO_PRIVATE_DEFAULT_PROFILE,
        actions_readiness_only=True,
        actions_label=MSG_READINESS_ONLY,
        has_private_defaults=False,
        has_productive_execution_toggle=False,
    )


def build_configurations_page_policy_panel_vm(
    *,
    active_profile_name: str = "",
    policy_readiness_status: str = "incomplete",
    unmatched_configured: bool | None = None,
) -> ConfigurationsPagePolicyPanelVM:
    """Build readiness panel VM for the configurations page (no GUI)."""

    profile_label = str(active_profile_name or "").strip() or "Kein aktives Profil"
    if _contains_private_marker(profile_label):
        # Never surface private tokens as configuration defaults/labels.
        profile_label = "Aktives Profil (Name ausgeblendet — generische Anzeige)"

    if unmatched_configured is True:
        unmatched_label = "Unklar-/Nicht-zugeordnet-Konfiguration ist eingerichtet."
    elif unmatched_configured is False:
        unmatched_label = (
            "Unklar-/Nicht-zugeordnet-Konfiguration ist noch nicht eingerichtet."
        )
    else:
        unmatched_label = (
            "Unklare Fälle nutzen eine Nicht-zugeordnet-/Prüf-Konfiguration — "
            "ohne automatische Entscheidung."
        )

    return ConfigurationsPagePolicyPanelVM(
        banner=(
            f"{MSG_CONFIGS_APPLY_RULES} {MSG_UNCLEAR_NOT_AUTO} "
            f"{MSG_TARGETS_AFTER_SAFE_CONFIG}"
        ),
        honest_copy=(
            MSG_CONFIGS_APPLY_RULES,
            MSG_UNCLEAR_NOT_AUTO,
            MSG_TARGETS_AFTER_SAFE_CONFIG,
            MSG_WITHOUT_EVIDENCE_REVIEW,
            MSG_NO_PRODUCTIVE_EXECUTION,
        ),
        linked_profile_label=f"Aktives Profil: {profile_label}",
        linked_policy_status=f"Policy-Readiness: {policy_readiness_status}",
        unmatched_concept_label=unmatched_label,
        unclear_not_auto_label=MSG_UNCLEAR_NOT_AUTO,
        targets_after_safe_config_label=MSG_TARGETS_AFTER_SAFE_CONFIG,
        has_private_destination_defaults=False,
        has_productive_execution_toggle=False,
        scans_folders=False,
        processes_pdfs=False,
    )


def align_profile_policy_with_runtime_intent(
    *,
    classification_policy: Any = None,
    profile_policy: ProfilePolicyViewModel | None = None,
) -> RuntimePolicyBridgeResult:
    """Align profile/policy readiness with RuntimePolicyIntent (no processing).

    Missing configured evidence or missing policy → incomplete / blocked /
    review semantics via the existing bridge. No private defaults, no
    filename-as-truth, no supplier-IBAN payer assumption.
    """

    source: Any = classification_policy
    if source is None and profile_policy is not None:
        # Derive a minimal explicit policy payload from the view-model flags.
        source = {
            "require_explicit_payer_payment_evidence": True,
            "supplier_bank_details_are_payment_evidence": False,
            "unknown_payment_target": "unklar",
            "mixed_business_private_address_target": "unklar",
            "apple_pay_requires_known_card_reference": True,
            "invoice_detection_policy": {
                "filename_is_not_source_of_truth": True,
            },
            "payment_evidence_policy": {
                "supplier_bank_details_are_not_payer_evidence": True,
                "card_payment_requires_known_reference": True,
                "generic_credit_card_without_identifier_target": "unklar",
            },
            "business_assignment_policy": {
                "organization_identifiers_are_profile_configured": True,
            },
        }
        # If the VM has no configured evidence, keep bridge incomplete by
        # omitting a full classification_policy and signalling via wrapper.
        if (
            not profile_policy.business.has_configured_evidence()
            and not profile_policy.payment.has_configured_evidence()
            and not profile_policy.account.has_configured_evidence()
            and profile_policy.identity.is_blank()
        ):
            return build_runtime_policy_intent(None)

    return build_runtime_policy_intent(source)


def profile_policy_core_rule_messages() -> tuple[str, ...]:
    """Core policy rule messages for UI surfaces / tests."""

    return (
        MSG_FILENAME_NOT_TRUTH,
        MSG_UNCLEAR_STAYS_REVIEW,
        MSG_SUPPLIER_IBAN_NOT_USER_PAYMENT,
        MSG_CARD_HINT_WITHOUT_REF_UNCLEAR,
        MSG_FILENAME_NOT_SOURCE_OF_TRUTH,
        MSG_SUPPLIER_IBAN_NOT_PAYER,
        MSG_GENERIC_CARD_UNCLEAR,
        MSG_UNKNOWN_EVIDENCE_REVIEW,
    )


def assert_no_private_profile_policy_defaults(payload: Any) -> None:
    """Raise AssertionError if private markers appear in a policy payload."""

    text = str(payload)
    for marker in PRIVATE_DEFAULT_MARKERS:
        if marker in text:
            raise AssertionError(f"Private default marker present: {marker}")
