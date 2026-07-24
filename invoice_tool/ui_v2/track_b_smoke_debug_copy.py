"""Track-B developer smoke copy/debug text helpers + simple user review labels.

Builds plain-text diagnostics and German review-surface labels.
No file mutation, no run_once, no auto-oracle execution.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from invoice_tool.ui_v2.configuration_duplicate_remediation import (
    analyze_active_configuration_duplicates,
)

ACTION_COPY_CASE = "Prüffall als Text kopieren"
ACTION_COPY_DIAGNOSIS = "Technische Diagnose kopieren"
ACTION_COPY_ORACLE = "Oracle-Befehl kopieren"
ACTION_OPEN_WORKSPACE = "Arbeitsbereich öffnen"

# Layout marker for focused smoke UI tests / visual QA.
SMOKE_DEV_UI_LAYOUT_MARKER = "track_b_smoke_dev_ui_layout_v1_no_overlap"
REVIEW_DECLUTTER_LAYOUT_MARKER = "track_b_review_surface_declutter_v1"
REVIEW_USER_MODE_LAYOUT_MARKER = "track_b_simple_user_review_mode_v1"

MSG_SAFETY_LINE_NO_FINAL = "Vorschau — keine finalen Dateien geschrieben"
MSG_FINAL_WRITE_USER_ANSWER = (
    "Nein — nur Vorschau/Sandbox. Es wird nichts final geschrieben."
)
MSG_ORACLE_AVAILABLE = "Automatischer Smoke-Test verfügbar"
ORACLE_COMMAND = (
    "KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python "
    "scripts/dev/track_b_automated_smoke_oracle.py"
)
MSG_ORACLE_NO_AUTO_RUN = (
    "Der Oracle wird nicht automatisch aus der UI gestartet — "
    "Befehl kopieren und im Terminal ausführen."
)
MSG_ER_ER_NOTE = (
    "Hinweis: Das aktuelle technische Muster enthält einen festen er-Präfix "
    "und die Dokumentart. Das wird später vereinfacht."
)
MSG_FILENAME_PREVIEW_ONLY = (
    "Dateiname ist nur Vorschau — noch keine finalen Dateien geschrieben."
)
MSG_NO_READY_CASES = "Noch keine Fälle bereit."
MSG_NO_REVIEW_CASES = "Keine offenen Prüffälle."
MSG_USER_REVIEW_SUBTITLE = (
    "Einfache Prüfung: erkennen, entscheiden, Vorschau — ohne Technikjargon."
)

# Simple user review questions (primary surface).
SECTION_ERKANNT = "Was wurde erkannt?"
SECTION_UNKLAR = "Was ist unklar?"
SECTION_DATEINAME = "Welcher Dateiname wird vorgeschlagen?"
SECTION_ENTSCHEIDEN = "Was muss ich entscheiden?"
SECTION_FINAL_WRITE_Q = "Wird etwas final geschrieben?"
SECTION_BEREIT = "Welche Fälle sind bereit?"
SECTION_PRUEFUNG = "Welche Fälle bleiben zur Prüfung?"
SECTION_TECHNISCHE = "Technische Details"

# Compatibility aliases for declutter-era imports / tests.
SECTION_KURZPRUEFUNG = SECTION_ERKANNT
SECTION_VORSCHLAG = SECTION_DATEINAME
SECTION_WARUM = SECTION_UNKLAR
SECTION_NAECHSTE = SECTION_ENTSCHEIDEN
SECTION_FINALISIERUNG = SECTION_FINAL_WRITE_Q

REVIEW_SECTION_TITLES = (
    SECTION_ERKANNT,
    SECTION_UNKLAR,
    SECTION_DATEINAME,
    SECTION_ENTSCHEIDEN,
    SECTION_FINAL_WRITE_Q,
    SECTION_BEREIT,
    SECTION_PRUEFUNG,
    SECTION_TECHNISCHE,
)
USER_REVIEW_SECTION_TITLES = REVIEW_SECTION_TITLES

BADGE_PAYPAL = "PayPal"
BADGE_UNKLAR = "Unklar"
BADGE_MISSING_PAYMENT = "Zahlung unklar"
BADGE_NOT_AMEX = "Keine AMEX"
BADGE_STORNO = "Storno"
BADGE_READY = "Bereit"
BADGE_BLOCKED = "Blockiert"

PRIMARY_PRUEFEN = "Prüfen"
PRIMARY_ACCEPT = "Vorschlag akzeptieren"
PRIMARY_PAYPAL = "PayPal-Regel anwenden"
PRIMARY_UNKLAR = "Unklar lassen"

MSG_WHY_MISSING_PAYMENT = (
    "Zahlungsfeld fehlt oder konnte nicht sicher erkannt werden."
)
MSG_WHY_MISSING_CATEGORY = "Geschäftskategorie fehlt oder ist unklar."
MSG_WHY_PAYPAL_MISSING = (
    "PayPal erkannt, aber keine passende PayPal-Regel vorhanden."
)
MSG_WHY_PAYPAL_APPLIED = "PayPal-Regel ist vorhanden bzw. wurde angewendet."
MSG_WHY_NOT_AMEX = (
    "Kartenzahlung erkannt, aber AMEX ist nicht belegt — daher keine AMEX-Zuordnung."
)
MSG_WHY_STORNO = "Storno erkannt — der Beleg bleibt zur Prüfung."
MSG_WHY_GENERIC = "Der Beleg ist unklar und muss geprüft werden."

ACTION_PAYPAL_SAVE_RERUN = "PayPal-Regel speichern und Matching neu berechnen"
ACTION_ACCEPT_SUGGESTION = "Vorschlag akzeptieren"
ACTION_KEEP_UNCLEAR = "als Unklar belassen"
ACTION_DEFER = "zurückstellen"
ACTION_IGNORE_EXPORT = "ignorieren / nicht exportieren"


def _g(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def filename_has_er_er(name: str | None) -> bool:
    return "_er_er_" in str(name or "")


def er_er_note_for_filename(name: str | None) -> str | None:
    if filename_has_er_er(name):
        return MSG_ER_ER_NOTE
    return None


def build_oracle_command_copy_text() -> str:
    return ORACLE_COMMAND


def _blob(*parts: Any) -> str:
    return " ".join(_norm(part) for part in parts if part is not None)


def paypal_action_relevant(detail: Any) -> bool:
    """True when PayPal CTA is useful for this document."""

    missing_type = _norm(_g(detail, "missing_configuration_type"))
    coverage = _norm(_g(detail, "configuration_coverage_status"))
    guidance = _norm(_g(detail, "user_guidance"))
    payment = _norm(
        _g(detail, "selected_payment_field") or _g(detail, "payment_account")
    )
    matched = _norm(_g(detail, "matched_configuration_name"))
    if missing_type == "paypal":
        return True
    if "paypal" in guidance and (
        "keine" in guidance or "fehl" in guidance or "missing" in coverage
    ):
        return True
    if payment == "paypal" and matched in {"", "unklar", "unmatched", "fallback"}:
        return True
    if payment == "paypal" and "missing" in coverage:
        return True
    return False


def derive_status_badges(
    detail: Any,
    *,
    finalization_ready: bool = False,
    finalization_blockers: Sequence[str] = (),
) -> tuple[str, ...]:
    """Compact status badges for review list / Kurzprüfung."""

    badges: list[str] = []
    payment = _norm(
        _g(detail, "selected_payment_field") or _g(detail, "payment_account")
    )
    art = _norm(_g(detail, "selected_art") or _g(detail, "document_type"))
    matched = _norm(_g(detail, "matched_configuration_name"))
    missing_type = _norm(_g(detail, "missing_configuration_type"))
    coverage = _norm(_g(detail, "configuration_coverage_status"))
    guidance = _norm(_g(detail, "user_guidance"))
    reason = _norm(_g(detail, "review_reason") or _g(detail, "reason"))
    blob = _blob(guidance, coverage, reason, missing_type, matched)

    if art == "storno" or "storno" in blob:
        badges.append(BADGE_STORNO)
    if payment == "paypal" or "paypal" in blob:
        badges.append(BADGE_PAYPAL)
    if (
        missing_type in {"payment field", "payment_field", "missing payment field"}
        or "missing_payment_field" in coverage
        or "zahlungsfeld" in guidance
        or "payment_field fehlt" in reason
        or "fehlt payment" in blob
        or str(_g(detail, "suggested_filename") or "").endswith(
            "FEHLT_payment_field.pdf"
        )
        or "fehlt_payment_field" in _norm(_g(detail, "suggested_filename"))
    ):
        if BADGE_MISSING_PAYMENT not in badges:
            badges.append(BADGE_MISSING_PAYMENT)
    if (
        missing_type in {"generic card", "generic_card"}
        or "amex not proven" in blob
        or "nicht-amex" in blob
        or "amex nicht belegt" in blob
        or ("card" in payment and "amex" not in matched)
    ):
        if BADGE_NOT_AMEX not in badges:
            badges.append(BADGE_NOT_AMEX)
    if matched in {"unklar", "unmatched", "fallback"} or "unklar" in reason:
        if BADGE_UNKLAR not in badges:
            badges.append(BADGE_UNKLAR)
    if finalization_ready:
        badges.append(BADGE_READY)
    elif finalization_blockers:
        badges.append(BADGE_BLOCKED)
    elif not badges:
        badges.append(BADGE_UNKLAR)
    # Stable unique order
    seen: set[str] = set()
    ordered: list[str] = []
    for badge in badges:
        if badge not in seen:
            seen.add(badge)
            ordered.append(badge)
    return tuple(ordered)


def derive_why_review_plain_german(detail: Any) -> tuple[str, ...]:
    """Plain-German reasons — no raw internal enums as primary text."""

    reasons: list[str] = []
    payment = _norm(
        _g(detail, "selected_payment_field") or _g(detail, "payment_account")
    )
    art = _norm(_g(detail, "selected_art") or _g(detail, "document_type"))
    missing_type = _norm(_g(detail, "missing_configuration_type"))
    coverage = _norm(_g(detail, "configuration_coverage_status"))
    guidance = str(_g(detail, "user_guidance") or "").strip()
    category = _norm(
        _g(detail, "business_category_display") or _g(detail, "business_category")
    )
    matched = _norm(_g(detail, "matched_configuration_name"))
    blob = _blob(guidance, coverage, missing_type, _g(detail, "review_reason"))

    if art == "storno" or "storno" in blob:
        reasons.append(MSG_WHY_STORNO)
    if (
        missing_type in {"payment field", "payment_field"}
        or "missing_payment_field" in coverage
        or "zahlungsfeld" in _norm(guidance)
        or not payment
        and (
            "payment" in blob
            or "zahlungs" in blob
            or "fehlt_payment_field" in _norm(_g(detail, "suggested_filename"))
        )
    ):
        reasons.append(MSG_WHY_MISSING_PAYMENT)
    if paypal_action_relevant(detail) or (
        payment == "paypal" and matched in {"", "unklar"}
    ):
        if matched == "paypal" or "paypal" in matched:
            reasons.append(MSG_WHY_PAYPAL_APPLIED)
        else:
            reasons.append(MSG_WHY_PAYPAL_MISSING)
    elif payment == "paypal" and "paypal" in matched:
        reasons.append(MSG_WHY_PAYPAL_APPLIED)
    if (
        missing_type in {"generic card", "generic_card"}
        or "amex not proven" in blob
        or "amex nicht belegt" in blob
        or ("card" in payment and "amex" not in matched)
    ):
        reasons.append(MSG_WHY_NOT_AMEX)
    if not category or category in {
        "unklare zuordnung",
        "unklar",
        "missing",
        "fehlt",
    }:
        if "kategorie" in blob or not category:
            reasons.append(MSG_WHY_MISSING_CATEGORY)
    if guidance and guidance not in reasons:
        # Prefer plain German guidance already produced by coverage helper.
        if not any(ch.isupper() and "_" in guidance for ch in [guidance]):
            reasons.append(guidance)
    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for item in reasons:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    if not ordered:
        ordered.append(MSG_WHY_GENERIC)
    return tuple(ordered)


def derive_primary_list_action(
    detail: Any,
    *,
    finalization_ready: bool = False,
) -> str:
    if paypal_action_relevant(detail):
        return PRIMARY_PAYPAL
    if finalization_ready:
        return PRIMARY_ACCEPT
    badges = derive_status_badges(detail, finalization_ready=finalization_ready)
    if BADGE_MISSING_PAYMENT in badges or BADGE_UNKLAR in badges:
        return PRIMARY_UNKLAR
    return PRIMARY_PRUEFEN


def next_action_labels_for_detail(detail: Any) -> tuple[str, ...]:
    labels: list[str] = []
    if paypal_action_relevant(detail):
        labels.append(ACTION_PAYPAL_SAVE_RERUN)
    labels.extend(
        [
            ACTION_ACCEPT_SUGGESTION,
            ACTION_KEEP_UNCLEAR,
            ACTION_DEFER,
            ACTION_IGNORE_EXPORT,
        ]
    )
    return tuple(labels)


def payment_display_label(detail: Any) -> str:
    """User-facing payment label — never expose the raw key ``payment_field``."""

    raw = _g(detail, "selected_payment_field") or _g(detail, "payment_account")
    text = str(raw or "").strip()
    if not text:
        return "nicht sicher erkannt"
    mapping = {
        "paypal": "PayPal",
        "card": "Karte",
        "credit card": "Karte",
        "amex": "AMEX",
        "bank": "Bank",
        "ueberweisung": "Überweisung",
        "überweisung": "Überweisung",
    }
    return mapping.get(_norm(text), text)


def document_art_display_label(detail: Any) -> str:
    art = str(
        _g(detail, "selected_art") or _g(detail, "document_type") or ""
    ).strip()
    if art.casefold() == "storno":
        return "Storno"
    if art.casefold() in {"er", "rechnung", "invoice"}:
        return "Rechnung"
    return art or "Rechnung"


def derive_recognized_fields(detail: Any) -> tuple[tuple[str, str], ...]:
    """Fields for „Was wurde erkannt?“ — plain German, no technical keys."""

    return (
        (
            "Originaldatei",
            str(
                _g(detail, "source_filename")
                or _g(detail, "document_label")
                or "—"
            ),
        ),
        (
            "Lieferant / Name",
            str(
                _g(detail, "counterparty_name")
                or _g(detail, "supplier")
                or "—"
            ),
        ),
        ("Datum", str(_g(detail, "invoice_date") or "—")),
        (
            "Betrag",
            str(
                _g(detail, "selected_amount")
                or _g(detail, "amount")
                or "—"
            ),
        ),
        ("Zahlungsart", payment_display_label(detail)),
        ("Dokumentart", document_art_display_label(detail)),
    )


def derive_decision_prompt(detail: Any) -> str:
    """Single plain-German decision question for the selected case."""

    if paypal_action_relevant(detail):
        return (
            "PayPal-Regel speichern und Matching neu berechnen, "
            "oder den Vorschlag akzeptieren / als unklar belassen?"
        )
    badges = derive_status_badges(detail)
    if BADGE_MISSING_PAYMENT in badges:
        return (
            "Zahlungsart prüfen und entscheiden: Vorschlag akzeptieren, "
            "als unklar belassen oder zurückstellen?"
        )
    if BADGE_NOT_AMEX in badges:
        return (
            "Kartenzahlung ohne AMEX: passende Zuordnung wählen, "
            "Vorschlag akzeptieren oder als unklar belassen?"
        )
    if BADGE_STORNO in badges:
        return "Storno prüfen: Vorschlag akzeptieren oder zur Prüfung belassen?"
    if BADGE_READY in badges:
        return "Vorschlag akzeptieren oder noch zurückstellen?"
    return "Vorschlag akzeptieren, als unklar belassen oder zurückstellen?"


def case_summary_line(detail: Any) -> str:
    name = str(
        _g(detail, "source_filename")
        or _g(detail, "document_label")
        or "Dokument"
    )
    supplier = str(
        _g(detail, "counterparty_name") or _g(detail, "supplier") or ""
    ).strip()
    amount = str(
        _g(detail, "selected_amount") or _g(detail, "amount") or ""
    ).strip()
    parts = [name]
    if supplier:
        parts.append(supplier)
    if amount:
        parts.append(amount)
    return " · ".join(parts)


def split_ready_and_review_cases(
    details: Sequence[Any],
    *,
    readiness_by_key: Mapping[str, Any] | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Partition cases into ready vs. still-in-review summary lines."""

    readiness_by_key = readiness_by_key or {}
    ready: list[str] = []
    review: list[str] = []
    for detail in details:
        key = str(
            _g(detail, "item_key")
            or _g(detail, "document_id")
            or _g(detail, "source_filename")
            or ""
        )
        readiness = readiness_by_key.get(key)
        is_ready = bool(getattr(readiness, "ready", False))
        line = case_summary_line(detail)
        if is_ready:
            ready.append(line)
        else:
            review.append(line)
    return tuple(ready), tuple(review)


def build_prueffall_copy_text(
    detail: Any,
    *,
    draft: Any | None = None,
    profile_id: str | None = None,
) -> str:
    """Copy text for a single review case — includes PayPal guidance when present."""

    badges = derive_status_badges(detail)
    why = derive_why_review_plain_german(detail)
    lines = [
        "# Prüffall (Track-B Review)",
        f"source_file: {_g(detail, 'source_filename') or '—'}",
        f"supplier: {_g(detail, 'counterparty_name') or _g(detail, 'supplier') or '—'}",
        f"date: {_g(detail, 'invoice_date') or '—'}",
        f"amount: {_g(detail, 'selected_amount') or _g(detail, 'amount') or '—'}",
        f"payment_field: {_g(detail, 'selected_payment_field') or _g(detail, 'payment_account') or '—'}",
        f"document_art: {_g(detail, 'selected_art') or _g(detail, 'document_type') or '—'}",
        f"configuration: {_g(detail, 'matched_configuration_name') or '—'}",
        f"status_badges: {', '.join(badges) if badges else '—'}",
        f"suggested_filename: {_g(detail, 'suggested_filename') or _g(detail, 'preview_filename') or '—'}",
        f"why_review:",
        *[f"  - {line}" for line in why],
        f"config/matching_status: {_g(detail, 'matched_configuration_name') or '—'}",
        f"matched_configuration_reason: {_g(detail, 'matched_configuration_reason') or '—'}",
        f"configuration_coverage_status: {_g(detail, 'configuration_coverage_status') or '—'}",
        f"user_guidance: {_g(detail, 'user_guidance') or '—'}",
        f"suggested_configuration_action: {_g(detail, 'suggested_configuration_action') or '—'}",
        f"missing_configuration_type: {_g(detail, 'missing_configuration_type') or '—'}",
        f"target_folder: {_g(detail, 'planned_target') or '—'}",
        f"review_decision: {_g(detail, 'review_decision_status') or _g(detail, 'category') or '—'}",
        f"finalization_state: {_g(detail, 'finalization_ready') or _g(detail, 'finalization_status') or '—'}",
        "safety_flags:",
        "  - preview_only",
        "  - no_final_write",
        "  - originals_unchanged",
        "  - final_write_allowed_for_production=false",
        "  - no productive processing",
        f"safety_line: {MSG_SAFETY_LINE_NO_FINAL}",
    ]
    guidance = str(_g(detail, "user_guidance") or "")
    missing_type = str(_g(detail, "missing_configuration_type") or "").casefold()
    if "paypal" in guidance.casefold() or missing_type == "paypal":
        lines.append("paypal_guidance: present")
        lines.append(
            "  - PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden."
        )
    if draft is not None:
        lines.extend(
            [
                "proposed_config:",
                f"  - proposed_configuration_name: {_g(draft, 'proposed_configuration_name') or '—'}",
                f"  - proposed_condition: {_g(draft, 'proposed_condition') or '—'}",
                f"  - proposed_filename_pattern: {_g(draft, 'proposed_filename_pattern') or '—'}",
                f"  - proposed_destination_path: {_g(draft, 'proposed_destination_path') or '—'}",
            ]
        )
    if profile_id:
        lines.append(f"profile_id: {profile_id}")
    return "\n".join(lines)


def build_diagnosis_copy_text(
    detail: Any,
    *,
    draft: Any | None = None,
    profile_id: str | None = None,
    duplicate_report: str | None = None,
    run_state: Any | None = None,
) -> str:
    """Broader diagnosis blob including safety flags and duplicate report."""

    case = build_prueffall_copy_text(
        detail, draft=draft, profile_id=profile_id
    )
    lines = [
        "# Technische Diagnose (Track-B Review)",
        case,
        "",
        "safety_flags_detail:",
        "  - final_write_allowed_for_production=false",
        "  - production_final_write_disabled",
        "  - no_run_once",
        "  - no_real_invoice_folders",
        "  - track_b_preview_only",
        "  - no_auto_oracle_run",
        f"oracle_command: {ORACLE_COMMAND}",
    ]
    if run_state is not None:
        lines.append(f"run_status: {_g(run_state, 'status') or '—'}")
        lines.append(f"run_id: {_g(run_state, 'run_id') or '—'}")
    technical = {
        "matching_reason": _g(detail, "matched_configuration_reason"),
        "condition_results": _g(detail, "condition_results"),
        "proposed_configuration": _g(detail, "proposed_configuration_name"),
        "proposed_condition": _g(detail, "proposed_condition"),
        "finalization_blockers": _g(detail, "finalization_blockers"),
        "final_write_allowed": False,
    }
    lines.append("technical_fields:")
    for key, value in technical.items():
        lines.append(f"  - {key}: {value if value not in (None, '') else '—'}")
    if duplicate_report:
        lines.append("")
        lines.append(duplicate_report)
    elif profile_id:
        try:
            from invoice_tool.profile_store import load_profile_bundle

            bundle = load_profile_bundle(profile_id)
            report = analyze_active_configuration_duplicates(
                bundle.configurations
            ).report_text()
            lines.append("")
            lines.append(report)
        except Exception as exc:  # noqa: BLE001
            lines.append(f"duplicate_report_error: {exc}")
    return "\n".join(lines)


def copy_text_to_state_and_clipboard(
    state: Any,
    text: str,
    *,
    kind: str,
) -> str:
    """Store copy payload on state; push to page clipboard when available."""

    state.track_b_smoke_last_copy_text = text
    state.track_b_smoke_last_copy_kind = kind
    state.track_b_smoke_copy_feedback = f"{kind} in Zwischenablage / State kopiert."
    state.track_b_smoke_copy_feedback_error = False
    page = getattr(state, "page", None)
    if page is not None and hasattr(page, "set_clipboard"):
        try:
            page.set_clipboard(text)
        except Exception:  # noqa: BLE001
            state.track_b_smoke_copy_feedback = (
                f"{kind} im State gespeichert (Clipboard nicht verfügbar)."
            )
    return text


__all__ = (
    "ACTION_ACCEPT_SUGGESTION",
    "ACTION_COPY_CASE",
    "ACTION_COPY_DIAGNOSIS",
    "ACTION_COPY_ORACLE",
    "ACTION_DEFER",
    "ACTION_IGNORE_EXPORT",
    "ACTION_KEEP_UNCLEAR",
    "ACTION_OPEN_WORKSPACE",
    "ACTION_PAYPAL_SAVE_RERUN",
    "BADGE_BLOCKED",
    "BADGE_MISSING_PAYMENT",
    "BADGE_NOT_AMEX",
    "BADGE_PAYPAL",
    "BADGE_READY",
    "BADGE_STORNO",
    "BADGE_UNKLAR",
    "MSG_ER_ER_NOTE",
    "MSG_FILENAME_PREVIEW_ONLY",
    "MSG_FINAL_WRITE_USER_ANSWER",
    "MSG_NO_READY_CASES",
    "MSG_NO_REVIEW_CASES",
    "MSG_ORACLE_AVAILABLE",
    "MSG_ORACLE_NO_AUTO_RUN",
    "MSG_SAFETY_LINE_NO_FINAL",
    "MSG_USER_REVIEW_SUBTITLE",
    "MSG_WHY_GENERIC",
    "MSG_WHY_MISSING_CATEGORY",
    "MSG_WHY_MISSING_PAYMENT",
    "MSG_WHY_NOT_AMEX",
    "MSG_WHY_PAYPAL_APPLIED",
    "MSG_WHY_PAYPAL_MISSING",
    "MSG_WHY_STORNO",
    "ORACLE_COMMAND",
    "PRIMARY_ACCEPT",
    "PRIMARY_PAYPAL",
    "PRIMARY_PRUEFEN",
    "PRIMARY_UNKLAR",
    "REVIEW_DECLUTTER_LAYOUT_MARKER",
    "REVIEW_SECTION_TITLES",
    "REVIEW_USER_MODE_LAYOUT_MARKER",
    "SECTION_BEREIT",
    "SECTION_DATEINAME",
    "SECTION_ENTSCHEIDEN",
    "SECTION_ERKANNT",
    "SECTION_FINALISIERUNG",
    "SECTION_FINAL_WRITE_Q",
    "SECTION_KURZPRUEFUNG",
    "SECTION_NAECHSTE",
    "SECTION_PRUEFUNG",
    "SECTION_TECHNISCHE",
    "SECTION_UNKLAR",
    "SECTION_VORSCHLAG",
    "SECTION_WARUM",
    "SMOKE_DEV_UI_LAYOUT_MARKER",
    "USER_REVIEW_SECTION_TITLES",
    "build_diagnosis_copy_text",
    "build_oracle_command_copy_text",
    "build_prueffall_copy_text",
    "case_summary_line",
    "copy_text_to_state_and_clipboard",
    "derive_decision_prompt",
    "derive_primary_list_action",
    "derive_recognized_fields",
    "derive_status_badges",
    "derive_why_review_plain_german",
    "document_art_display_label",
    "er_er_note_for_filename",
    "filename_has_er_er",
    "next_action_labels_for_detail",
    "payment_display_label",
    "paypal_action_relevant",
    "split_ready_and_review_cases",
)
