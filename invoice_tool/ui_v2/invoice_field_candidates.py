"""Track-B invoice amount / payment / art candidate selection (Prompt 21/34).

Prefer final payable/gross invoice totals over line-item, base, net or tax
values. Payment and art inference stay conservative. Preview-only — no
productive processing, no Track-A/core mutation.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from invoice_tool.ui_v2.configuration_filename_renderer import format_amount_comma

# Prefer decimal-comma amounts; dotted values only when not a calendar date.
_COMMA_AMOUNT_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})(?!\d)"
)
_DOT_AMOUNT_RE = re.compile(r"(?<![A-Za-z0-9])(\d+\.\d{2})(?!\d)")
_DATE_DOT_RE = re.compile(
    r"(?<![A-Za-z0-9])\d{1,2}\.\d{1,2}\.\d{2,4}(?!\d)"
)

# Higher score = preferred as final payable / gross total.
_FINAL_TOTAL_PATTERNS: tuple[tuple[re.Pattern[str], int, str], ...] = (
    (re.compile(r"\brechnungsbetrag\b", re.I), 100, "rechnungsbetrag"),
    (re.compile(r"\bgesamtpreis\s*brutto\b", re.I), 100, "gesamtpreis_brutto"),
    (re.compile(r"\bzahlungsbetrag\b|\bzahlbetrag\b", re.I), 98, "zahlbetrag"),
    (re.compile(r"\bzahlung\s*\(\s*paypal\s*\)", re.I), 97, "zahlung_paypal"),
    (re.compile(r"\bmoyen\s*de\s*paiement\b", re.I), 96, "moyen_de_paiement"),
    (re.compile(r"\bgesamtwert\b", re.I), 94, "gesamtwert"),
    (re.compile(r"\btotal\s*ttc\b", re.I), 95, "total_ttc"),
    (re.compile(r"\bgesamtbetrag\b", re.I), 92, "gesamtbetrag"),
    (re.compile(r"\bendbetrag\b", re.I), 92, "endbetrag"),
    # Bare "Total" — word-boundary so "totale"/"Totalité" do not match.
    (
        re.compile(
            r"\btotal\b(?!\s*\(?\s*ht\b|\s*produits|\s*excl|\s*excluding|"
            r"\s*ohne|\s*netto|\s*ttc)",
            re.I,
        ),
        85,
        "total",
    ),
)

_PRIMARY_REJECT_LABELS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bprix\s*de\s*base\b|\bpreis\s*de\s*base\b", re.I), "base_price"),
    (re.compile(r"\beinzelpreis\b|\bprix\s*unitaire\b", re.I), "unit_price"),
    (re.compile(r"\bnettobetrag\b|\bgesamtpreis\s*netto\b", re.I), "net_total"),
    (re.compile(r"\bgesamt\s*\(\s*netto\s*\)", re.I), "line_net"),
    (re.compile(r"\btotal\s*\(\s*ht\s*\)|\btotal\s*\(ht\)|\btotal\s+ht\b", re.I), "net_ht"),
    (re.compile(r"\btotal\s*produits\b", re.I), "products_total"),
    (re.compile(r"\btaxe\s*totale\b", re.I), "tax"),
    (re.compile(r"^\s*umsatzsteuer\b|\bumssatzsteuer\s+\d", re.I), "tax"),
    (re.compile(r"^\s*mwst\b|\bmwst\s+\d", re.I), "tax"),
    (re.compile(r"\bsubtotal\b|\bzwischensumme\b", re.I), "subtotal"),
    (re.compile(r"\boffener\s*betrag\b", re.I), "open_balance"),
)

_PAYMENT_PATTERNS: tuple[tuple[re.Pattern[str], str, float], ...] = (
    (re.compile(r"\bamerican\s*express\b|\bamex\b", re.I), "amex", 0.95),
    (re.compile(r"\bpaypal\b", re.I), "paypal", 0.9),
    (
        re.compile(
            r"\bzahlung\s+per\s+kreditkarte\b|\bkreditkarte\b|\bcredit\s*card\b|"
            r"\bcarte\s*bancaire\b",
            re.I,
        ),
        "card",
        0.75,
    ),
    (re.compile(r"\büberweisung\b|\bbank\s*transfer\b|\bvirement\b", re.I), "transfer", 0.7),
    (re.compile(r"\bapple\s*pay\b", re.I), "apple_pay", 0.8),
)

_DOC_ART_PATTERNS: tuple[tuple[re.Pattern[str], str, float], ...] = (
    (
        re.compile(
            r"\bstornorechnung\b|\bcredit\s*note\b|\bavoir\b|\bstorno\s+zu\s+rechnung\b",
            re.I,
        ),
        "storno",
        0.95,
    ),
    (re.compile(r"\brechnung\b|\binvoice\b|\bfacture\b", re.I), "er", 0.7),
)


@dataclass(frozen=True)
class AmountCandidate:
    value_decimal: str
    display_value_comma: str
    source_label: str
    source_text: str
    source_priority: int
    nearby_keywords: tuple[str, ...] = field(default_factory=tuple)
    is_final_total_candidate: bool = False
    is_line_item_candidate: bool = False
    is_tax_candidate: bool = False
    is_net_candidate: bool = False
    is_base_price_candidate: bool = False
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AmountSelectionResult:
    selected_amount: str | None
    selected_amount_reason: str
    amount_candidates: tuple[AmountCandidate, ...] = ()
    rejected_amount_candidates: tuple[AmountCandidate, ...] = ()

    def to_report(self) -> dict[str, Any]:
        return {
            "selected_amount": self.selected_amount,
            "selected_amount_reason": self.selected_amount_reason,
            "amount_candidates": [c.to_dict() for c in self.amount_candidates],
            "rejected_amount_candidates": [
                c.to_dict() for c in self.rejected_amount_candidates
            ],
        }


@dataclass(frozen=True)
class PaymentFieldCandidate:
    payment_field: str
    source_text: str
    confidence: float
    proof: str
    configuration_match_allowed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaymentFieldSelectionResult:
    selected_payment_field: str | None
    selected_payment_field_reason: str
    payment_field_candidates: tuple[PaymentFieldCandidate, ...] = ()

    def to_report(self) -> dict[str, Any]:
        return {
            "selected_payment_field": self.selected_payment_field,
            "selected_payment_field_reason": self.selected_payment_field_reason,
            "payment_field_candidates": [
                c.to_dict() for c in self.payment_field_candidates
            ],
        }


@dataclass(frozen=True)
class DocumentArtCandidate:
    art: str
    source_text: str
    confidence: float
    proof: str
    ambiguity: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentArtSelectionResult:
    selected_art: str | None
    selected_art_reason: str
    document_art_candidates: tuple[DocumentArtCandidate, ...] = ()
    document_type: str | None = None
    art_ambiguity: bool = False

    def to_report(self) -> dict[str, Any]:
        return {
            "selected_art": self.selected_art,
            "selected_art_reason": self.selected_art_reason,
            "document_art_candidates": [c.to_dict() for c in self.document_art_candidates],
            "document_type": self.document_type,
            "art_ambiguity": self.art_ambiguity,
        }


def _normalize_amount_token(raw: str) -> tuple[str, str] | None:
    """Return (dot_decimal, comma_display) or None."""

    text = str(raw or "").strip().replace(" ", "")
    for token in ("€", "EUR", "eur", "usd", "USD", "$"):
        text = text.replace(token, "")
    if not text:
        return None
    last_comma = text.rfind(",")
    last_dot = text.rfind(".")
    if last_comma > last_dot:
        normalized = text.replace(".", "").replace(",", ".")
    else:
        normalized = text.replace(",", "")
    try:
        amount = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None
    if amount <= 0:
        return None
    quantized = amount.quantize(Decimal("0.01"))
    dot = f"{quantized:.2f}"
    comma = format_amount_comma(dot) or dot.replace(".", ",")
    return dot, comma


def _find_amount_tokens(line: str) -> list[str]:
    """Find amount tokens on a line, excluding calendar dates."""

    text = str(line or "")
    # Mask dates so 11.05.2026 does not yield 11.05 as amount.
    masked = _DATE_DOT_RE.sub(" ", text)
    tokens = list(_COMMA_AMOUNT_RE.findall(masked))
    # Dotted amounts only when comma amounts are absent on the line and the line
    # looks monetary (currency marker or pure amount line).
    if not tokens:
        if re.search(r"[€$]|eur|usd|gbp", masked, re.I) or re.fullmatch(
            r"\s*\d+\.\d{2}\s*", masked
        ):
            tokens.extend(_DOT_AMOUNT_RE.findall(masked))
    return tokens


def _primary_label(text: str) -> tuple[str | None, int | None, bool, str | None]:
    """Return (label, priority, is_final, reject_reason) for a label-ish text."""

    hay = str(text or "")
    best_final: tuple[str, int] | None = None
    for pattern, score, label in _FINAL_TOTAL_PATTERNS:
        if pattern.search(hay):
            if best_final is None or score > best_final[1]:
                best_final = (label, score)
    if best_final is not None:
        return best_final[0], best_final[1], True, None

    for pattern, reason in _PRIMARY_REJECT_LABELS:
        if pattern.search(hay):
            return reason, 5, False, f"rejected_{reason}"
    return None, None, False, None


def _pending_label_text(lines: Sequence[str], index: int) -> str:
    parts: list[str] = []
    for back in range(1, 5):
        prev_i = index - back
        if prev_i < 0:
            break
        prev = lines[prev_i].strip()
        if not prev:
            continue
        if _find_amount_tokens(prev):
            break
        parts.insert(0, prev)
        # Stop after collecting a compact label block.
        joined = " ".join(parts)
        label, _, is_final, reject = _primary_label(joined)
        if label and (is_final or reject):
            break
    return " ".join(parts)


def select_invoice_amount_candidates(text: str) -> AmountSelectionResult:
    """Select the final payable/gross amount from labeled candidates."""

    lines = [ln.rstrip() for ln in str(text or "").splitlines()]
    candidates: list[AmountCandidate] = []
    seen: set[tuple[str, str, str]] = set()

    def _add(
        *,
        raw: str,
        label: str,
        priority: int,
        context: str,
        is_final: bool,
        rejection: str | None,
    ) -> None:
        normalized = _normalize_amount_token(raw)
        if normalized is None:
            return
        dot, comma = normalized
        key = (dot, label, rejection or "")
        if key in seen:
            return
        seen.add(key)
        is_tax = rejection == "rejected_tax"
        is_net = rejection in {
            "rejected_net_total",
            "rejected_line_net",
            "rejected_net_ht",
            "rejected_products_total",
        }
        is_base = rejection == "rejected_base_price"
        is_line = rejection in {
            "rejected_unit_price",
            "rejected_line_net",
            "rejected_line_item_column",
            "rejected_subtotal",
        }
        candidates.append(
            AmountCandidate(
                value_decimal=dot,
                display_value_comma=comma,
                source_label=label,
                source_text=context[:240],
                source_priority=priority,
                nearby_keywords=(label,),
                is_final_total_candidate=is_final and rejection is None,
                is_line_item_candidate=is_line,
                is_tax_candidate=is_tax,
                is_net_candidate=is_net,
                is_base_price_candidate=is_base,
                rejection_reason=rejection,
            )
        )

    # Pass 1: label-on-own-line → following amount line(s).
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or _find_amount_tokens(stripped):
            continue
        label, priority, is_final, rejection = _primary_label(stripped)
        # Also join with next non-amount label line ("Gesamtpreis" + "Brutto",
        # "Prix de" + "base").
        joined_label_text = stripped
        if index + 1 < len(lines):
            nxt = lines[index + 1].strip()
            if nxt and not _find_amount_tokens(nxt):
                joined = f"{stripped} {nxt}"
                j_label, j_priority, j_final, j_rejection = _primary_label(joined)
                if j_label and (
                    j_final
                    or j_rejection
                    or (j_priority or 0) >= (priority or 0)
                ):
                    label, priority, is_final, rejection = (
                        j_label,
                        j_priority,
                        j_final,
                        j_rejection,
                    )
                    joined_label_text = joined
        if not label:
            continue
        # Base-price / net column headers may sit several lines above values.
        look_ahead = 8 if rejection or is_final else 5
        for ahead in range(1, look_ahead):
            nxt_i = index + ahead
            if nxt_i >= len(lines):
                break
            nxt_line = lines[nxt_i].strip()
            if not nxt_line:
                continue
            tokens = _find_amount_tokens(nxt_line)
            if not tokens:
                # Stop if another primary label appears (unless hunting base price).
                other, _, other_final, other_rej = _primary_label(nxt_line)
                if other and (other_final or other_rej) and ahead > 1:
                    break
                continue
            context = f"{joined_label_text} | {nxt_line}"
            for raw in tokens:
                _add(
                    raw=raw,
                    label=label,
                    priority=int(priority or 10),
                    context=context,
                    is_final=bool(is_final),
                    rejection=rejection,
                )
            break

    # Pass 2: same-line / pending-label pairing for remaining amounts.
    for index, line in enumerate(lines):
        tokens = _find_amount_tokens(line)
        if not tokens:
            continue
        pending = _pending_label_text(lines, index)
        # Multi-line French/German table headers like "Prix de" + "base".
        wider = " ".join(
            ln.strip()
            for ln in lines[max(0, index - 6) : index + 1]
            if ln.strip() and not _find_amount_tokens(ln)
        )
        same = line.strip()
        context = f"{pending} {wider} {same}".strip()
        label, priority, is_final, rejection = _primary_label(context)
        if label is None:
            # Unlabeled / column line-item amounts.
            if re.search(r"\bgesamt\s*\(\s*netto\s*\)|\bgesamt\s*\(\s*brutto\s*\)", context, re.I):
                label = "line_item_column"
                priority = 5
                is_final = False
                rejection = "rejected_line_item_column"
            else:
                label = "unlabeled_amount"
                priority = 1
                is_final = False
                rejection = None
        for raw in tokens:
            _add(
                raw=raw,
                label=str(label),
                priority=int(priority or 1),
                context=context,
                is_final=bool(is_final),
                rejection=rejection,
            )

    finals = [
        c for c in candidates if c.is_final_total_candidate and not c.rejection_reason
    ]
    rejected = tuple(
        c
        for c in candidates
        if c.rejection_reason
        or c.is_base_price_candidate
        or c.is_tax_candidate
        or c.is_net_candidate
        or c.is_line_item_candidate
    )

    if finals:
        # Prefer higher priority; for equal priority prefer the last occurrence
        # (invoice totals tend to appear after line items).
        indexed = list(enumerate(finals))
        indexed.sort(key=lambda item: (-item[1].source_priority, item[0]))
        # Re-sort: highest priority first; among same priority, last wins.
        by_priority: dict[int, list[AmountCandidate]] = {}
        for c in finals:
            by_priority.setdefault(c.source_priority, []).append(c)
        top_priority = max(by_priority)
        chosen = by_priority[top_priority][-1]
        reason = (
            f"Finaler Rechnungs-/Zahlungsbetrag über „{chosen.source_label}“ "
            f"gewählt ({chosen.display_value_comma})."
        )
        extra_rejected = [
            AmountCandidate(
                value_decimal=c.value_decimal,
                display_value_comma=c.display_value_comma,
                source_label=c.source_label,
                source_text=c.source_text,
                source_priority=c.source_priority,
                nearby_keywords=c.nearby_keywords,
                is_final_total_candidate=c.is_final_total_candidate,
                is_line_item_candidate=c.is_line_item_candidate,
                is_tax_candidate=c.is_tax_candidate,
                is_net_candidate=c.is_net_candidate,
                is_base_price_candidate=c.is_base_price_candidate,
                rejection_reason="not_selected_lower_priority_or_duplicate",
            )
            for c in finals
            if not (
                c.value_decimal == chosen.value_decimal
                and c.source_label == chosen.source_label
            )
        ]
        return AmountSelectionResult(
            selected_amount=chosen.display_value_comma,
            selected_amount_reason=reason,
            amount_candidates=tuple(candidates),
            rejected_amount_candidates=tuple(list(rejected) + extra_rejected),
        )

    usable = [
        c
        for c in candidates
        if not c.rejection_reason
        and not c.is_base_price_candidate
        and not c.is_tax_candidate
        and not c.is_net_candidate
        and not c.is_line_item_candidate
    ]
    if usable:
        usable.sort(key=lambda c: Decimal(c.value_decimal), reverse=True)
        chosen = usable[0]
        return AmountSelectionResult(
            selected_amount=chosen.display_value_comma,
            selected_amount_reason=(
                "Kein eindeutiges Final-Total-Label — größter nicht abgelehnter "
                f"Betrags-Kandidat ({chosen.display_value_comma})."
            ),
            amount_candidates=tuple(candidates),
            rejected_amount_candidates=rejected,
        )

    return AmountSelectionResult(
        selected_amount=None,
        selected_amount_reason="Kein brauchbarer Rechnungsbetrag erkannt.",
        amount_candidates=tuple(candidates),
        rejected_amount_candidates=rejected,
    )


def select_payment_field_candidates(text: str) -> PaymentFieldSelectionResult:
    """Conservatively infer payment_field candidates with proof."""

    hay = str(text or "")
    candidates: list[PaymentFieldCandidate] = []
    for pattern, field_name, confidence in _PAYMENT_PATTERNS:
        match = pattern.search(hay)
        if not match:
            continue
        proof = match.group(0)
        config_allowed = field_name in {"amex", "paypal", "transfer", "apple_pay"}
        # Generic card is never allowed to match AMEX configurations.
        if field_name == "card":
            config_allowed = False
        candidates.append(
            PaymentFieldCandidate(
                payment_field=field_name,
                source_text=proof,
                confidence=confidence,
                proof=proof,
                configuration_match_allowed=config_allowed,
            )
        )

    if not candidates:
        return PaymentFieldSelectionResult(
            selected_payment_field=None,
            selected_payment_field_reason=(
                "Keine Zahlungsart im Text sichtbar — payment_field bleibt fehlend."
            ),
            payment_field_candidates=(),
        )

    priority = {"amex": 0, "paypal": 1, "apple_pay": 2, "card": 3, "transfer": 4}
    candidates.sort(key=lambda c: (priority.get(c.payment_field, 9), -c.confidence))
    # Drop generic card when explicit AMEX exists.
    if any(c.payment_field == "amex" for c in candidates):
        candidates = [c for c in candidates if c.payment_field != "card"]
    chosen = candidates[0]
    if chosen.payment_field == "amex":
        reason = f"Expliziter AMEX-Nachweis („{chosen.proof}“) — payment_field=amex."
    elif chosen.payment_field == "paypal":
        reason = f"PayPal-Text erkannt („{chosen.proof}“) — payment_field=paypal."
    elif chosen.payment_field == "card":
        reason = (
            f"Generische Kreditkarte erkannt („{chosen.proof}“) — "
            "payment_field=card (nicht AMEX; kein AMEX-Nachweis)."
        )
    else:
        reason = f"Zahlungsart „{chosen.payment_field}“ erkannt („{chosen.proof}“)."
    return PaymentFieldSelectionResult(
        selected_payment_field=chosen.payment_field,
        selected_payment_field_reason=reason,
        payment_field_candidates=tuple(candidates),
    )


def select_document_art_candidates(text: str) -> DocumentArtSelectionResult:
    """Infer document art / type; expose storno explicitly when proven."""

    hay = str(text or "")
    candidates: list[DocumentArtCandidate] = []
    for pattern, art, confidence in _DOC_ART_PATTERNS:
        match = pattern.search(hay)
        if not match:
            continue
        proof = match.group(0)
        candidates.append(
            DocumentArtCandidate(
                art=art,
                source_text=proof,
                confidence=confidence,
                proof=proof,
                ambiguity=art == "storno",
            )
        )

    if not candidates:
        return DocumentArtSelectionResult(
            selected_art="er",
            selected_art_reason=(
                "Kein Dokumenttyp-Hinweis — Fallback art=er (Eingangsrechnung); "
                "Review bleibt erforderlich."
            ),
            document_art_candidates=(),
            document_type="rechnung",
            art_ambiguity=True,
        )

    candidates.sort(key=lambda c: -c.confidence)
    storno = next((c for c in candidates if c.art == "storno"), None)
    chosen = storno or candidates[0]
    if chosen.art == "storno":
        return DocumentArtSelectionResult(
            selected_art="storno",
            selected_art_reason=(
                f"Storno erkannt („{chosen.proof}“) — art=storno; "
                "Konfigurationsliteral _er_ bleibt erhalten; Review wegen "
                "Art-Ambiguität (Storno vs. Standard-er) erforderlich."
            ),
            document_art_candidates=tuple(candidates),
            document_type="storno",
            art_ambiguity=True,
        )
    return DocumentArtSelectionResult(
        selected_art="er",
        selected_art_reason=(
            f"Rechnung/Eingangsbeleg erkannt („{chosen.proof}“) — art=er."
        ),
        document_art_candidates=tuple(candidates),
        document_type="rechnung",
        art_ambiguity=False,
    )


def candidates_as_jsonable(
    items: Sequence[
        Mapping[str, Any] | AmountCandidate | PaymentFieldCandidate | DocumentArtCandidate
    ]
    | Sequence[Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if hasattr(item, "to_dict"):
            out.append(item.to_dict())  # type: ignore[union-attr]
        elif isinstance(item, Mapping):
            out.append(dict(item))
    return out


__all__ = (
    "AmountCandidate",
    "AmountSelectionResult",
    "DocumentArtCandidate",
    "DocumentArtSelectionResult",
    "PaymentFieldCandidate",
    "PaymentFieldSelectionResult",
    "candidates_as_jsonable",
    "select_document_art_candidates",
    "select_invoice_amount_candidates",
    "select_payment_field_candidates",
)
