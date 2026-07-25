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
REVIEW_UI_POLISH_LAYOUT_MARKER = "track_b_simple_user_review_ui_polish_v1"
REVIEW_ACCORDION_LAYOUT_MARKER = "track_b_review_accordion_layout_v1"
REVIEW_GUIDED_LAYOUT_MARKER = "track_b_guided_review_ux_cleanup_v1"
REVIEW_CLARIFICATION_MARKER = "track_b_review_clarification_mode_v1"
REVIEW_DETAIL_VISIBILITY_MARKER = "track_b_review_detail_visibility_and_cards_v1"
REVIEW_DETAIL_ANCHOR_MARKER = "review_detail_anchor_selected_top"
REVIEW_ACTIVE_SECTION_MARKER = "review_active_section_selected"
COMPACT_DETAIL_CARD_MARKER = "review_compact_detail_card_v1"
SECTION_HEADER_MARKER = "review_section_header_compact"
IA_CLEANUP_LAYOUT_MARKER = "track_b_ui_v2_information_architecture_cleanup_v1"
SECOND_UX_CLEANUP_MARKER = "track_b_ui_v2_second_ux_cleanup_v1"
PRODUCT_UX_CLEANUP_MARKER = "track_b_ui_v2_product_ux_audit_workspace_cleanup_v1"
WORKSPACE_COMPACT_STATUS_MARKER = "workspace_compact_status_line_v1"
WORKSPACE_NO_PRIMARY_DEV_MARKER = "workspace_no_primary_dev_test_evidence_v1"
OUTPUT_ROW_ACTIONABLE_MARKER = "workspace_output_row_actionable_v1"
OUTPUT_ROW_PLACEHOLDER_MARKER = "workspace_output_row_placeholder_non_clickable_v1"
OUTPUT_ACTION_ICON_MARKER = "workspace_output_action_icon_v1"
MENU_COMPACT_ROW_MARKER = "menu_compact_row_spacing_v2"
WORKSPACE_SHARED_SUMMARY_MARKER = "workspace_profile_config_shared_summary_v2"
WORKSPACE_FILE_PAIR_MARKER = "workspace_input_output_file_pairs_v2"
WORKSPACE_LIVE_FILE_PAIRS_MARKER = "workspace_live_file_pairs_v1"
WORKSPACE_CTA_PRIMARY_MARKER = "workspace_run_cta_primary_v2"
WORKSPACE_CTA_BLACK_PRIMARY_MARKER = "workspace_cta_black_primary_v1"
WORKSPACE_CTA_DISABLED_MARKER = "workspace_cta_disabled_muted_v1"
REVIEW_DOCUMENT_PREVIEW_MARKER = "review_document_preview_open_non_mutating_v2"
WORKSPACE_DOCUMENT_SHOW_MARKER = "workspace_document_show_open_non_mutating_v1"
WORKSPACE_IA_SECTION_ORDER = (
    "Profil",
    "Konfiguration",
    "Ordner",
    "Belegnamen ändern",
)
REVIEW_CARD_COLLAPSED_SUMMARY_ONLY = "review_card_collapsed_summary_only"
REVIEW_CARD_ACTIVE_HIGHLIGHT = "review_card_active_highlight"
INLINE_DETAIL_UNDER_SELECTED_CARD = "inline_detail_under_selected_card"
DETAIL_PANEL_DISTINCT_BACKGROUND = "detail_panel_distinct_background"
FILENAME_PREVIEW_ONLY_MARKER = "review_filename_preview_only_default"
GUIDED_STATUS_PANEL_MARKER = "guided_status_panel_top"
DECISION_FIRST_PANEL_MARKER = "decision_first_panel"
FILENAME_EDIT_SECONDARY_MARKER = "filename_edit_secondary_not_primary"
FILENAME_EDIT_FOCUS_MARKER = "review_filename_edit_focus_in_place_v1"
CLEAN_USER_FILENAME_MARKER = "clean_user_facing_filename_no_internal_prefix"

# Workspace / IA user-facing actions
ACTION_WORKSPACE_EDIT = "Bearbeiten"
ACTION_CHANGE_PROFILE = ACTION_WORKSPACE_EDIT
ACTION_EDIT_CONFIGURATIONS = ACTION_WORKSPACE_EDIT
ACTION_OPEN_REVIEW = "Zur Prüfung öffnen"
ACTION_CREATE_PROFILE = "Profil erstellen"
ACTION_CREATE_CONFIGURATION = "Konfiguration erstellen"
ACTION_SAVE_CONFIGURATION = "Konfiguration speichern"
ACTION_RENAME_PROFILE = "Profil umbenennen"
ACTION_NEW_CONFIGURATION = "Neue Konfiguration erstellen"
ACTION_SHOW_DOCUMENT = "Dokument anzeigen"
ACTION_VIEW_PROPOSAL = "Vorschlag ansehen"
ACTION_SHOW_OUTPUT_FILE = "Datei anzeigen"
LABEL_ACTIVE_STATUS = "Aktiv"
LABEL_ACTIVE_EXPLAIN = "aktiv = wird bei der Prüfung verwendet"
LABEL_WORKSPACE_PROFILE = "Profil"
LABEL_WORKSPACE_CONFIGURATION = "Konfiguration"
LABEL_INPUT_FOLDER = "Eingangsordner"
LABEL_OUTPUT_FOLDER = "Ausgangsordner"
LABEL_INPUT_FILES = "Eingangsdateien"
LABEL_PROPOSED_OUTPUT_FILES = "Vorgeschlagene Ausgabedateien"
LABEL_ORIGINAL_FILE = "Originaldatei"
LABEL_PROPOSED_FILENAME = "Vorgeschlagener Dateiname"
LABEL_NO_PROPOSAL_YET = "Noch kein Vorschlag"
MSG_NOT_CHECKED_YET = "Noch nicht geändert"
MSG_NO_RESULT_YET = "Noch kein Ergebnis vorhanden."
MSG_NEED_OUTPUT_FOLDER = "Bitte Ausgangsordner wählen."
MSG_NO_FILES_IN_INPUT = "Keine Belege im Eingangsordner gefunden."
MSG_FILES_FOUND = "{count} Dateien gefunden"
MSG_ROW_CHECKING = "Wird geprüft …"
MSG_PROPOSAL_CREATED = "Vorschlag erstellt"
MSG_START_HELPER = "Nur Vorschau — Originale bleiben unverändert."
MSG_RUN_ACTIVITY = "Prüfung läuft…"
MSG_FILENAME_FOLLOWS_SCHEMA = (
    "Der Dateiname folgt einem festen Schema. Bitte ergänze fehlende Merkmale."
)
MSG_CLARIFICATION_STATUS = "Zur Prüfung · Vorschlag · Nicht final geschrieben"
SECTION_ADVANCED_HINTS = "Hinweise & Diagnose"
SECTION_ADVANCED_PROFILE = "Erweiterte Profilinformationen"
SECTION_ADVANCED_CONFIG = "Erweiterte Hinweise"
SECTION_IMPORT_EXPORT_ADVANCED = "Import / Export (erweitert)"
SECTION_DEV_DIAGNOSE = "Entwickler / Diagnose"
SECTION_TEST_NACHWEIS_COLLAPSED = "Test & Nachweis"
PROFILE_PAGE_EXPLANATION = (
    "Ein Profil bündelt Konfigurationen, Zielbereiche und Regeln für einen Arbeitskontext."
)
MSG_PROFILE_DRAFT_CURRENT = "Aktueller Profilentwurf"
MSG_PROFILE_DRAFT_UNSAVED = "Noch nicht gespeicherte Änderungen"
MSG_MISSING_TARGETS_CONFIG = "Zielordner fehlen bei {count} Konfiguration(en)"
MSG_MISSING_TARGETS_FILTER = (
    "Bei {count} Konfiguration(en) fehlt ein Zielordner"
)
ACTION_EDIT_PROFILE_CONFIGS = "Konfigurationen dieses Profils bearbeiten"
LABEL_NEW_PROFILE_NAME = "Name des neuen Profils"
PICK_INPUT_FOLDER_CHOOSE = "Eingangsordner wählen"
PICK_INPUT_FOLDER_CHANGE = "Eingangsordner ändern"
PICK_OUTPUT_FOLDER_CHOOSE = "Ausgangsordner wählen"
PICK_OUTPUT_FOLDER_CHANGE = "Ausgangsordner ändern"
START_CTA_STRONG = "Belegnamen jetzt ändern"
START_CTA_HEIGHT_PX = 44

ACTION_DETAILS_OPEN = "Details öffnen"
ACTION_DETAILS_CLOSE = "Details schließen"
LABEL_REVIEW_DOC_NAME = "Dokumentname"
LABEL_REVIEW_DATE = "Datum"
LABEL_REVIEW_AMOUNT = "Betrag"
LABEL_SUGGESTED_FILENAME = "Vorgeschlagener Dateiname"
ACTION_EDIT_FILENAME = "Dateiname bearbeiten"
ACTION_SAVE_FILENAME = "Speichern"
ACTION_CANCEL_FILENAME = "Abbrechen"
ACTION_KEEP_UNCLEAR_GUIDED = "Als unklar lassen"
ACTION_KEEP_IN_REVIEW_GUIDED = "Zur Prüfung lassen"
ACTION_ADD_PAYMENT = "Zahlungsart ergänzen"
ACTION_CREATE_CARD_RULE = "Kartenregel anlegen"
SECTION_STATUS = "Status"
SECTION_EMPFEHLUNG = "Empfehlung"
SECTION_GUIDED_STATUS = "Status & Empfehlung"
SECTION_TEST_TOOLS = "Test & Nachweis"
# Scroll/anchor keys for inline review detail visibility (Flet Column.scroll_to).
REVIEW_PAGE_SCROLL_KEY = "review_page_scroll_column"
REVIEW_ITEM_ANCHOR_PREFIX = "review-detail-anchor-"
MSG_GUIDED_SAFETY_LINE = "Nur Vorschau — Originale bleiben unverändert."
MSG_GUIDED_STATUS_REVIEW = "Dieses Dokument bleibt zur Prüfung."
MSG_GUIDED_REC_NOT_AMEX = "Nicht als American Express zuordnen."
MSG_GUIDED_REC_STORNO = "Bitte Betrag, Datum und Zahlungsart prüfen."
MSG_GUIDED_REC_MISSING_PAYMENT = (
    "Bitte Zahlungsart ergänzen oder zur Prüfung lassen."
)
MSG_GUIDED_PAYPAL_OK = "Vorschlag kann geprüft werden."
MSG_WHY_CARD_AMEX_SHORT = "Kartenzahlung erkannt, aber AMEX ist nicht belegt."

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
MSG_FILENAME_PREVIEW_HELPER = (
    "Nur Vorschau — noch keine finale Datei geschrieben."
)
LABEL_VORSCHAU_DATEINAME = "Vorschau-Dateiname"
LABEL_DATEINAME_BEARBEITEN = "Dateiname bearbeiten"
ACTION_COPY_FILENAME = "Dateiname kopieren"
# Marker proving the editable preview filename control is full-width / no-clip.
FILENAME_FIELD_POLISH_MARKER = "track_b_preview_filename_full_width_no_clip_v1"
MSG_NO_READY_CASES = "Noch keine bereiten Dokumente."
MSG_NO_REVIEW_CASES = "Keine Dokumente zur Prüfung."
MSG_USER_REVIEW_SUBTITLE = "Dokumente prüfen und entscheiden."
MSG_REVIEW_SAFETY_ONCE = "Nur Vorschau — Originale bleiben unverändert."

# Simple user review questions (primary surface).
SECTION_ERKANNT = "Was wurde erkannt?"
SECTION_UNKLAR = "Was ist unklar?"
SECTION_DATEINAME = "Was schlägt die App vor?"
SECTION_ENTSCHEIDEN = "Was muss ich entscheiden?"
SECTION_FINAL_WRITE_Q = "Finalisierung / Vorschau-Sicherheit"
SECTION_BEREIT = "Bereite Dokumente"
SECTION_PRUEFUNG = "Dokumente zur Prüfung"
SECTION_TECHNISCHE = "Technische Details"
FILTER_ALL_DOCS = "Alle"
FILTER_REVIEW_DOCS = "Zur Prüfung"
FILTER_READY_DOCS = "Bereit"

# Compatibility aliases for declutter-era imports / tests.
SECTION_KURZPRUEFUNG = SECTION_ERKANNT
SECTION_VORSCHLAG = SECTION_DATEINAME
SECTION_WARUM = SECTION_UNKLAR
SECTION_NAECHSTE = SECTION_ENTSCHEIDEN
SECTION_FINALISIERUNG = SECTION_FINAL_WRITE_Q

REVIEW_SECTION_TITLES = (
    SECTION_STATUS,
    SECTION_EMPFEHLUNG,
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
COMPACT_REVIEW_DETAIL_SECTION_TITLES = (
    SECTION_STATUS,
    SECTION_EMPFEHLUNG,
    SECTION_ENTSCHEIDEN,
    SECTION_ERKANNT,
    SECTION_DATEINAME,
)

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
PRIMARY_UNKLAR = "Als unklar lassen"

MSG_WHY_MISSING_PAYMENT = "Zahlungsart fehlt. Bitte Zahlungsart prüfen."
MSG_WHY_MISSING_CATEGORY = "Geschäftskategorie fehlt oder ist unklar."
MSG_WHY_PAYPAL_MISSING = (
    "PayPal erkannt, aber keine passende PayPal-Regel vorhanden."
)
MSG_WHY_PAYPAL_APPLIED = "PayPal-Regel ist vorhanden."
MSG_WHY_NOT_AMEX = MSG_WHY_CARD_AMEX_SHORT
MSG_WHY_STORNO = "Storno erkannt."
MSG_WHY_GENERIC = "Der Beleg ist unklar und muss geprüft werden."
MSG_WHY_PAYPAL_DETECTED = "PayPal erkannt."
MSG_REC_MISSING_PAYMENT_PLAIN = (
    "Zahlungsart fehlt. Bitte wählen Sie, ob die Zahlung über PayPal, "
    "Karte oder ein anderes Konto lief."
)
MSG_REC_GENERIC = "Bitte prüfen und eine Entscheidung treffen."
MSG_REC_PAYPAL_DECIDE = "PayPal-Regel prüfen oder Vorschlag entscheiden."

# Internal export prefixes — must never appear in user-facing filename display.
# Include single-underscore variants (some resolvers collapse "__" → "_").
INTERNAL_FILENAME_PREFIXES = (
    "REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__",
    "REVIEW_REQUIRED__SUGGESTED__",
    "REVIEW_REQUIRED_SUGGESTED_INCOMPLETE_",
    "REVIEW_REQUIRED_SUGGESTED_",
    "REVIEW_REQUIRED__",
    "REVIEW_REQUIRED_",
    "SUGGESTED__",
    "SUGGESTED_",
    "INCOMPLETE__",
    "INCOMPLETE_",
)


def clean_user_facing_filename(name: str | None) -> str:
    """Strip internal REVIEW_REQUIRED / SUGGESTED prefixes for user display."""

    safe = str(name or "").strip()
    if not safe:
        return ""
    changed = True
    while changed:
        changed = False
        for prefix in INTERNAL_FILENAME_PREFIXES:
            if safe.startswith(prefix):
                safe = safe[len(prefix) :]
                changed = True
    # Collapse accidental double separators from nested prefixes.
    while "__" in safe:
        safe = safe.replace("__", "_")
    # Final guard: drop leftover technical status tokens at the start.
    for token in ("REVIEW_REQUIRED_", "REVIEW_REQUIRED", "SUGGESTED_", "SUGGESTED"):
        if safe.startswith(token):
            safe = safe[len(token) :].lstrip("_")
    return safe.strip("_ ")


def smart_path_display(raw: str, *, max_chars: int = 64) -> str:
    """Show full path when short; truncate beginning and preserve end when long."""

    text = str(raw or "").strip()
    if not text or text in {"—", "Noch nicht konfiguriert"}:
        return text or "—"
    if len(text) <= max_chars:
        return text
    return "…" + text[-(max_chars - 1) :]


def truncate_filename_display(name: str, *, max_chars: int = 48) -> str:
    """Truncate long filenames visually at the end; keep full name for tooltip/data."""

    text = str(name or "").strip()
    if not text:
        return "—"
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"

ACTION_PAYPAL_SAVE_RERUN = "PayPal-Regel speichern und Matching neu berechnen"
ACTION_ACCEPT_SUGGESTION = "Vorschlag akzeptieren"
ACTION_KEEP_UNCLEAR = "als Unklar belassen"
ACTION_DEFER = "zurückstellen"
ACTION_IGNORE_EXPORT = "ignorieren / nicht exportieren"

CASE_STORNO = "storno"
CASE_PAYPAL = "paypal"
CASE_CARD_NOT_AMEX = "card_not_amex"
CASE_MISSING_PAYMENT = "missing_payment"
CASE_GENERIC = "generic"


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


def _document_payment(detail: Any) -> str:
    return _norm(
        _g(detail, "selected_payment_field") or _g(detail, "payment_account")
    )


def _document_art(detail: Any) -> str:
    return _norm(_g(detail, "selected_art") or _g(detail, "document_type"))


def _is_card_payment(payment: str) -> bool:
    return payment in {"card", "credit card", "karte", "kreditkarte"}


def _is_missing_payment(detail: Any, payment: str) -> bool:
    missing_type = _norm(_g(detail, "missing_configuration_type"))
    coverage = _norm(_g(detail, "configuration_coverage_status"))
    filename = _norm(_g(detail, "suggested_filename"))
    return (
        not payment
        or missing_type in {"payment field", "payment_field", "missing payment field"}
        or "missing_payment_field" in coverage
        or "fehlt_payment_field" in filename
        or str(_g(detail, "suggested_filename") or "").endswith(
            "FEHLT_payment_field.pdf"
        )
    )


def _is_card_not_amex(detail: Any, payment: str) -> bool:
    if not _is_card_payment(payment):
        return False
    missing_type = _norm(_g(detail, "missing_configuration_type"))
    matched = _norm(_g(detail, "matched_configuration_name"))
    coverage = _norm(_g(detail, "configuration_coverage_status"))
    guidance = _norm(_g(detail, "user_guidance"))
    return (
        missing_type in {"generic card", "generic_card"}
        or "amex not proven" in _blob(guidance, coverage)
        or "amex nicht belegt" in guidance
        or "no_safe_card" in coverage
        or "amex" not in matched
    )


def review_case_kind(detail: Any) -> str:
    """Document-specific review case — never mix PayPal into card cases."""

    art = _document_art(detail)
    payment = _document_payment(detail)
    if art == "storno":
        return CASE_STORNO
    if payment == "paypal":
        return CASE_PAYPAL
    if _is_card_payment(payment) and _is_card_not_amex(detail, payment):
        return CASE_CARD_NOT_AMEX
    if _is_missing_payment(detail, payment):
        return CASE_MISSING_PAYMENT
    if _is_card_payment(payment):
        return CASE_CARD_NOT_AMEX
    return CASE_GENERIC


def paypal_action_relevant(detail: Any) -> bool:
    """True when PayPal CTA is useful for this document only."""

    if _document_payment(detail) != "paypal":
        return False
    missing_type = _norm(_g(detail, "missing_configuration_type"))
    coverage = _norm(_g(detail, "configuration_coverage_status"))
    matched = _norm(_g(detail, "matched_configuration_name"))
    if missing_type == "paypal":
        return True
    if matched in {"", "unklar", "unmatched", "fallback"}:
        return True
    if "missing" in coverage:
        return True
    return False


def paypal_rule_present(detail: Any) -> bool:
    """True when this PayPal document already has a usable PayPal rule."""

    if _document_payment(detail) != "paypal":
        return False
    matched = _norm(_g(detail, "matched_configuration_name"))
    return "paypal" in matched and matched not in {"", "unklar", "unmatched", "fallback"}


def derive_status_badges(
    detail: Any,
    *,
    finalization_ready: bool = False,
    finalization_blockers: Sequence[str] = (),
) -> tuple[str, ...]:
    """Compact status badges — document-specific only."""

    badges: list[str] = []
    kind = review_case_kind(detail)
    matched = _norm(_g(detail, "matched_configuration_name"))
    reason = _norm(_g(detail, "review_reason") or _g(detail, "reason"))

    if kind == CASE_STORNO:
        badges.append(BADGE_STORNO)
    elif kind == CASE_PAYPAL:
        badges.append(BADGE_PAYPAL)
    elif kind == CASE_CARD_NOT_AMEX:
        badges.append(BADGE_NOT_AMEX)
    elif kind == CASE_MISSING_PAYMENT:
        badges.append(BADGE_MISSING_PAYMENT)

    if matched in {"unklar", "unmatched", "fallback"} or "unklar" in reason:
        if BADGE_UNKLAR not in badges:
            badges.append(BADGE_UNKLAR)
    if finalization_ready:
        badges.append(BADGE_READY)
    elif finalization_blockers:
        badges.append(BADGE_BLOCKED)
    elif not badges:
        badges.append(BADGE_UNKLAR)
    seen: set[str] = set()
    ordered: list[str] = []
    for badge in badges:
        if badge not in seen:
            seen.add(badge)
            ordered.append(badge)
    return tuple(ordered)


def derive_why_review_plain_german(detail: Any) -> tuple[str, ...]:
    """Plain-German, document-specific reasons — no cross-document PayPal bleed."""

    kind = review_case_kind(detail)
    if kind == CASE_STORNO:
        return (MSG_WHY_STORNO,)
    if kind == CASE_PAYPAL:
        if paypal_rule_present(detail) and not paypal_action_relevant(detail):
            return (MSG_WHY_PAYPAL_DETECTED, MSG_WHY_PAYPAL_APPLIED)
        if paypal_action_relevant(detail):
            return (MSG_WHY_PAYPAL_DETECTED, MSG_WHY_PAYPAL_MISSING)
        if paypal_rule_present(detail):
            return (MSG_WHY_PAYPAL_DETECTED, MSG_WHY_PAYPAL_APPLIED)
        return (MSG_WHY_PAYPAL_DETECTED,)
    if kind == CASE_CARD_NOT_AMEX:
        return (MSG_WHY_NOT_AMEX,)
    if kind == CASE_MISSING_PAYMENT:
        return (MSG_WHY_MISSING_PAYMENT,)
    return (MSG_WHY_GENERIC,)


def derive_status_text(detail: Any) -> str:
    """Plain-German status line for the compact Status card."""

    kind = review_case_kind(detail)
    if kind == CASE_STORNO:
        return MSG_WHY_STORNO
    if kind == CASE_PAYPAL:
        if paypal_rule_present(detail) and not paypal_action_relevant(detail):
            return f"{MSG_WHY_PAYPAL_DETECTED} {MSG_WHY_PAYPAL_APPLIED}"
        if paypal_action_relevant(detail):
            return f"{MSG_WHY_PAYPAL_DETECTED} {MSG_WHY_PAYPAL_MISSING}"
        return MSG_WHY_PAYPAL_DETECTED
    if kind == CASE_CARD_NOT_AMEX:
        return f"{MSG_GUIDED_STATUS_REVIEW} {MSG_WHY_NOT_AMEX}"
    if kind == CASE_MISSING_PAYMENT:
        return MSG_WHY_MISSING_PAYMENT
    why = derive_why_review_plain_german(detail)
    return " ".join((MSG_GUIDED_STATUS_REVIEW, *why)).strip()


def derive_recommendation_text(detail: Any) -> str:
    """Plain-German recommendation for the compact Empfehlung card."""

    kind = review_case_kind(detail)
    if kind == CASE_STORNO:
        return MSG_GUIDED_REC_STORNO
    if kind == CASE_PAYPAL:
        if paypal_rule_present(detail) and not paypal_action_relevant(detail):
            return MSG_GUIDED_PAYPAL_OK
        if paypal_action_relevant(detail):
            return MSG_REC_PAYPAL_DECIDE
        return MSG_GUIDED_PAYPAL_OK
    if kind == CASE_CARD_NOT_AMEX:
        return MSG_GUIDED_REC_NOT_AMEX
    if kind == CASE_MISSING_PAYMENT:
        return MSG_REC_MISSING_PAYMENT_PLAIN
    return MSG_REC_GENERIC


def derive_guided_status_lines(detail: Any) -> tuple[str, ...]:
    """Top guided panel: status, reason, recommendation — document-specific."""

    kind = review_case_kind(detail)
    if kind == CASE_STORNO:
        return (MSG_WHY_STORNO, MSG_GUIDED_REC_STORNO)
    if kind == CASE_PAYPAL:
        if paypal_rule_present(detail) and not paypal_action_relevant(detail):
            return (
                MSG_WHY_PAYPAL_DETECTED,
                MSG_WHY_PAYPAL_APPLIED,
                MSG_GUIDED_PAYPAL_OK,
            )
        if paypal_action_relevant(detail):
            return (
                MSG_WHY_PAYPAL_DETECTED,
                MSG_WHY_PAYPAL_MISSING,
                MSG_REC_PAYPAL_DECIDE,
            )
        return (MSG_WHY_PAYPAL_DETECTED, MSG_GUIDED_PAYPAL_OK)
    if kind == CASE_CARD_NOT_AMEX:
        return (
            MSG_GUIDED_STATUS_REVIEW,
            f"Grund: {MSG_WHY_NOT_AMEX}",
            f"Empfehlung: {MSG_GUIDED_REC_NOT_AMEX}",
        )
    if kind == CASE_MISSING_PAYMENT:
        return (MSG_WHY_MISSING_PAYMENT, MSG_REC_MISSING_PAYMENT_PLAIN)
    why = derive_why_review_plain_german(detail)
    return (MSG_GUIDED_STATUS_REVIEW, *why)


def derive_primary_decision_action(detail: Any) -> str:
    kind = review_case_kind(detail)
    if kind == CASE_PAYPAL:
        return ACTION_ACCEPT_SUGGESTION
    if kind == CASE_CARD_NOT_AMEX:
        return ACTION_KEEP_UNCLEAR_GUIDED
    if kind == CASE_MISSING_PAYMENT:
        return ACTION_KEEP_IN_REVIEW_GUIDED
    if kind == CASE_STORNO:
        return ACTION_KEEP_IN_REVIEW_GUIDED
    return ACTION_KEEP_UNCLEAR_GUIDED


def derive_secondary_decision_actions(detail: Any) -> tuple[str, ...]:
    kind = review_case_kind(detail)
    if kind == CASE_CARD_NOT_AMEX:
        return (ACTION_CREATE_CARD_RULE, ACTION_IGNORE_EXPORT)
    if kind == CASE_PAYPAL:
        return (ACTION_KEEP_IN_REVIEW_GUIDED,)
    if kind == CASE_MISSING_PAYMENT:
        return (ACTION_ADD_PAYMENT, ACTION_IGNORE_EXPORT)
    if kind == CASE_STORNO:
        return (ACTION_ACCEPT_SUGGESTION, ACTION_IGNORE_EXPORT)
    return (ACTION_IGNORE_EXPORT,)


def derive_primary_list_action(
    detail: Any,
    *,
    finalization_ready: bool = False,
) -> str:
    kind = review_case_kind(detail)
    if kind == CASE_PAYPAL and paypal_action_relevant(detail):
        return PRIMARY_PAYPAL
    if kind == CASE_PAYPAL and finalization_ready:
        return PRIMARY_ACCEPT
    if kind == CASE_PAYPAL:
        return PRIMARY_ACCEPT
    if finalization_ready:
        return PRIMARY_ACCEPT
    if kind in {CASE_CARD_NOT_AMEX, CASE_MISSING_PAYMENT, CASE_STORNO}:
        return PRIMARY_UNKLAR
    return PRIMARY_PRUEFEN


def next_action_labels_for_detail(detail: Any) -> tuple[str, ...]:
    primary = derive_primary_decision_action(detail)
    secondary = derive_secondary_decision_actions(detail)
    labels = [primary, *secondary]
    if paypal_action_relevant(detail):
        labels.append(ACTION_PAYPAL_SAVE_RERUN)
    # Stable unique
    seen: set[str] = set()
    ordered: list[str] = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            ordered.append(label)
    return tuple(ordered)


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

    kind = review_case_kind(detail)
    if kind == CASE_PAYPAL:
        return "Was möchten Sie mit diesem PayPal-Vorschlag tun?"
    if kind == CASE_MISSING_PAYMENT:
        return "Zahlungsart fehlt — wie möchten Sie fortfahren?"
    if kind == CASE_CARD_NOT_AMEX:
        return (
            "Kartenzahlung ohne belegte AMEX — als unklar lassen "
            "oder eine Kartenregel anlegen?"
        )
    if kind == CASE_STORNO:
        return "Storno prüfen: zur Prüfung lassen oder Vorschlag akzeptieren?"
    return "Was möchten Sie als Nächstes entscheiden?"


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
    "ACTION_ADD_PAYMENT",
    "ACTION_CHANGE_PROFILE",
    "ACTION_COPY_CASE",
    "ACTION_COPY_DIAGNOSIS",
    "ACTION_COPY_FILENAME",
    "ACTION_CANCEL_FILENAME",
    "ACTION_COPY_ORACLE",
    "ACTION_CREATE_CARD_RULE",
    "ACTION_CREATE_CONFIGURATION",
    "ACTION_CREATE_PROFILE",
    "ACTION_DEFER",
    "ACTION_DETAILS_CLOSE",
    "ACTION_DETAILS_OPEN",
    "ACTION_EDIT_CONFIGURATIONS",
    "ACTION_EDIT_FILENAME",
    "ACTION_EDIT_PROFILE_CONFIGS",
    "ACTION_IGNORE_EXPORT",
    "ACTION_KEEP_IN_REVIEW_GUIDED",
    "ACTION_KEEP_UNCLEAR",
    "ACTION_KEEP_UNCLEAR_GUIDED",
    "ACTION_NEW_CONFIGURATION",
    "ACTION_OPEN_REVIEW",
    "ACTION_OPEN_WORKSPACE",
    "ACTION_PAYPAL_SAVE_RERUN",
    "ACTION_RENAME_PROFILE",
    "ACTION_SAVE_CONFIGURATION",
    "ACTION_SAVE_FILENAME",
    "ACTION_SHOW_DOCUMENT",
    "ACTION_SHOW_OUTPUT_FILE",
    "ACTION_VIEW_PROPOSAL",
    "ACTION_WORKSPACE_EDIT",
    "COMPACT_DETAIL_CARD_MARKER",
    "COMPACT_REVIEW_DETAIL_SECTION_TITLES",
    "BADGE_BLOCKED",
    "BADGE_MISSING_PAYMENT",
    "BADGE_NOT_AMEX",
    "BADGE_PAYPAL",
    "BADGE_READY",
    "BADGE_STORNO",
    "BADGE_UNKLAR",
    "CASE_CARD_NOT_AMEX",
    "CASE_GENERIC",
    "CASE_MISSING_PAYMENT",
    "CASE_PAYPAL",
    "CASE_STORNO",
    "CLEAN_USER_FILENAME_MARKER",
    "DECISION_FIRST_PANEL_MARKER",
    "DETAIL_PANEL_DISTINCT_BACKGROUND",
    "FILENAME_EDIT_FOCUS_MARKER",
    "FILENAME_EDIT_SECONDARY_MARKER",
    "FILENAME_FIELD_POLISH_MARKER",
    "FILENAME_PREVIEW_ONLY_MARKER",
    "GUIDED_STATUS_PANEL_MARKER",
    "IA_CLEANUP_LAYOUT_MARKER",
    "INLINE_DETAIL_UNDER_SELECTED_CARD",
    "INTERNAL_FILENAME_PREFIXES",
    "REVIEW_ACTIVE_SECTION_MARKER",
    "REVIEW_DETAIL_ANCHOR_MARKER",
    "REVIEW_DETAIL_VISIBILITY_MARKER",
    "REVIEW_ITEM_ANCHOR_PREFIX",
    "REVIEW_PAGE_SCROLL_KEY",
    "SECTION_HEADER_MARKER",
    "SECTION_EMPFEHLUNG",
    "SECTION_STATUS",
    "LABEL_ACTIVE_EXPLAIN",
    "LABEL_ACTIVE_STATUS",
    "LABEL_DATEINAME_BEARBEITEN",
    "LABEL_INPUT_FILES",
    "LABEL_INPUT_FOLDER",
    "LABEL_NEW_PROFILE_NAME",
    "LABEL_NO_PROPOSAL_YET",
    "LABEL_ORIGINAL_FILE",
    "LABEL_OUTPUT_FOLDER",
    "LABEL_PROPOSED_FILENAME",
    "LABEL_PROPOSED_OUTPUT_FILES",
    "MSG_FILES_FOUND",
    "MSG_NEED_OUTPUT_FOLDER",
    "MSG_NO_FILES_IN_INPUT",
    "MSG_NOT_CHECKED_YET",
    "MSG_PROPOSAL_CREATED",
    "MSG_ROW_CHECKING",
    "WORKSPACE_DOCUMENT_SHOW_MARKER",
    "WORKSPACE_LIVE_FILE_PAIRS_MARKER",
    "LABEL_REVIEW_AMOUNT",
    "LABEL_REVIEW_DATE",
    "LABEL_REVIEW_DOC_NAME",
    "LABEL_SUGGESTED_FILENAME",
    "LABEL_VORSCHAU_DATEINAME",
    "LABEL_WORKSPACE_CONFIGURATION",
    "LABEL_WORKSPACE_PROFILE",
    "MENU_COMPACT_ROW_MARKER",
    "FILTER_ALL_DOCS",
    "FILTER_READY_DOCS",
    "FILTER_REVIEW_DOCS",
    "MSG_CLARIFICATION_STATUS",
    "MSG_ER_ER_NOTE",
    "MSG_FILENAME_FOLLOWS_SCHEMA",
    "MSG_FILENAME_PREVIEW_HELPER",
    "MSG_FILENAME_PREVIEW_ONLY",
    "MSG_FINAL_WRITE_USER_ANSWER",
    "MSG_GUIDED_SAFETY_LINE",
    "MSG_GUIDED_STATUS_REVIEW",
    "MSG_MISSING_TARGETS_CONFIG",
    "MSG_MISSING_TARGETS_FILTER",
    "MSG_NO_READY_CASES",
    "MSG_NO_RESULT_YET",
    "MSG_NO_REVIEW_CASES",
    "MSG_ORACLE_AVAILABLE",
    "MSG_ORACLE_NO_AUTO_RUN",
    "MSG_PROFILE_DRAFT_CURRENT",
    "MSG_PROFILE_DRAFT_UNSAVED",
    "MSG_REVIEW_SAFETY_ONCE",
    "MSG_RUN_ACTIVITY",
    "MSG_SAFETY_LINE_NO_FINAL",
    "MSG_START_HELPER",
    "MSG_USER_REVIEW_SUBTITLE",
    "PICK_INPUT_FOLDER_CHANGE",
    "PICK_INPUT_FOLDER_CHOOSE",
    "PICK_OUTPUT_FOLDER_CHANGE",
    "PICK_OUTPUT_FOLDER_CHOOSE",
    "MSG_WHY_GENERIC",
    "MSG_WHY_MISSING_CATEGORY",
    "MSG_WHY_MISSING_PAYMENT",
    "MSG_WHY_NOT_AMEX",
    "MSG_WHY_PAYPAL_APPLIED",
    "MSG_WHY_PAYPAL_DETECTED",
    "MSG_WHY_PAYPAL_MISSING",
    "MSG_WHY_STORNO",
    "ORACLE_COMMAND",
    "PRIMARY_ACCEPT",
    "PRIMARY_PAYPAL",
    "PRIMARY_PRUEFEN",
    "PRIMARY_UNKLAR",
    "PROFILE_PAGE_EXPLANATION",
    "REVIEW_ACCORDION_LAYOUT_MARKER",
    "REVIEW_CARD_ACTIVE_HIGHLIGHT",
    "REVIEW_CARD_COLLAPSED_SUMMARY_ONLY",
    "REVIEW_CLARIFICATION_MARKER",
    "REVIEW_DECLUTTER_LAYOUT_MARKER",
    "REVIEW_DOCUMENT_PREVIEW_MARKER",
    "REVIEW_GUIDED_LAYOUT_MARKER",
    "REVIEW_SECTION_TITLES",
    "REVIEW_UI_POLISH_LAYOUT_MARKER",
    "REVIEW_USER_MODE_LAYOUT_MARKER",
    "OUTPUT_ACTION_ICON_MARKER",
    "OUTPUT_ROW_ACTIONABLE_MARKER",
    "OUTPUT_ROW_PLACEHOLDER_MARKER",
    "PRODUCT_UX_CLEANUP_MARKER",
    "SECOND_UX_CLEANUP_MARKER",
    "START_CTA_HEIGHT_PX",
    "START_CTA_STRONG",
    "WORKSPACE_COMPACT_STATUS_MARKER",
    "WORKSPACE_CTA_BLACK_PRIMARY_MARKER",
    "WORKSPACE_CTA_DISABLED_MARKER",
    "WORKSPACE_CTA_PRIMARY_MARKER",
    "WORKSPACE_FILE_PAIR_MARKER",
    "WORKSPACE_NO_PRIMARY_DEV_MARKER",
    "WORKSPACE_SHARED_SUMMARY_MARKER",
    "SECTION_ADVANCED_CONFIG",
    "SECTION_ADVANCED_HINTS",
    "SECTION_ADVANCED_PROFILE",
    "SECTION_BEREIT",
    "SECTION_DATEINAME",
    "SECTION_DEV_DIAGNOSE",
    "SECTION_ENTSCHEIDEN",
    "SECTION_ERKANNT",
    "SECTION_FINALISIERUNG",
    "SECTION_FINAL_WRITE_Q",
    "SECTION_GUIDED_STATUS",
    "SECTION_IMPORT_EXPORT_ADVANCED",
    "SECTION_KURZPRUEFUNG",
    "SECTION_NAECHSTE",
    "SECTION_PRUEFUNG",
    "SECTION_TECHNISCHE",
    "SECTION_TEST_NACHWEIS_COLLAPSED",
    "SECTION_TEST_TOOLS",
    "SECTION_UNKLAR",
    "SECTION_VORSCHLAG",
    "SECTION_WARUM",
    "SMOKE_DEV_UI_LAYOUT_MARKER",
    "USER_REVIEW_SECTION_TITLES",
    "WORKSPACE_IA_SECTION_ORDER",
    "build_diagnosis_copy_text",
    "build_oracle_command_copy_text",
    "build_prueffall_copy_text",
    "case_summary_line",
    "clean_user_facing_filename",
    "copy_text_to_state_and_clipboard",
    "truncate_filename_display",
    "derive_decision_prompt",
    "derive_guided_status_lines",
    "derive_primary_decision_action",
    "derive_primary_list_action",
    "derive_recognized_fields",
    "derive_recommendation_text",
    "derive_secondary_decision_actions",
    "derive_status_badges",
    "derive_status_text",
    "derive_why_review_plain_german",
    "MSG_REC_GENERIC",
    "MSG_REC_MISSING_PAYMENT_PLAIN",
    "MSG_REC_PAYPAL_DECIDE",
    "document_art_display_label",
    "er_er_note_for_filename",
    "filename_has_er_er",
    "next_action_labels_for_detail",
    "payment_display_label",
    "paypal_action_relevant",
    "paypal_rule_present",
    "review_case_kind",
    "smart_path_display",
    "split_ready_and_review_cases",
)
