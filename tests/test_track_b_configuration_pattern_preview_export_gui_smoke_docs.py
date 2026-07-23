"""Doc-gate for Track-B Configuration Pattern Preview Export GUI Smoke (Prompt 25/34).

Docs evidence only — no productive processing, no real invoice folders, no code repair.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_2026-07-23.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_2026-07-23.md"
)

LATEST_EXPORT_FOLDER = (
    "preview-export-track-b-dry-61ff6af993d7-20260723T123451630008Z"
)

EXPORTED_PDF_NAMES = (
    "REVIEW_REQUIRED__SUGGESTED__2026-05-11_er_er_LUMITOP_476,00_paypal.pdf",
    "REVIEW_REQUIRED__SUGGESTED__2026-05-15_er_er_1A-Bootshop.de_105,75_paypal.pdf",
    "REVIEW_REQUIRED__SUGGESTED__2026-05-23_er_er_Böttcher_AG_84,39_card.pdf",
    "REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-05-11_er_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf",
    "REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-06-18_er_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf",
)

PRODUCT_STATUS = (
    "TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_PASS_WITH_CONFIG_COVERAGE_GAPS"
)
NEXT_TASK = (
    "KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_01"
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing doc: {path}"
    return path.read_text(encoding="utf-8")


def _combined() -> str:
    return _read(DOC) + "\n" + _read(AUDIT)


def test_docs_exist() -> None:
    assert DOC.is_file()
    assert AUDIT.is_file()


def test_docs_record_latest_export_folder() -> None:
    text = _combined()
    assert LATEST_EXPORT_FOLDER in text


def test_docs_record_all_five_exported_pdf_names() -> None:
    text = _combined()
    for name in EXPORTED_PDF_NAMES:
        assert name in text, f"missing exported PDF name: {name}"


def test_docs_record_lumitop_476_and_absence_of_500() -> None:
    text = _read(DOC)
    assert "LUMITOP" in text
    assert "476,00" in text
    assert "kein LUMITOP `500,00`" in text or "nicht stale `500,00`" in text
    # Stale amount must not appear as the accepted export filename value.
    assert "LUMITOP_500,00" not in text
    assert "LUMITOP `500,00`" in text  # documented as absent/stale signal


def test_docs_record_bootshop_105_and_absence_of_80() -> None:
    text = _read(DOC)
    assert "1A-Bootshop" in text
    assert "105,75" in text
    assert "kein 1A-Bootshop `80,55`" in text or "nicht stale `80,55`" in text
    assert "1A-Bootshop.de_80,55" not in text
    assert "`80,55`" in text  # documented as absent/stale signal


def test_docs_record_boettcher_storno_er_storno_and_absence_of_stale_er_er() -> None:
    text = _read(DOC)
    assert "er_storno" in text
    assert "Böttcher Storno" in text or "Böttcher-Storno" in text
    assert "stale `er_er`" in text or "Storno-`er_er`" in text or "statt `er_storno`" in text
    assert (
        "REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-06-18_er_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
        in text
    )
    assert (
        "REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-06-18_er_er_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
        not in text
    )


def test_docs_record_exported_from_current_state_true() -> None:
    text = _combined()
    assert "exported_from_current_state" in text
    assert "`exported_from_current_state` | `true`" in text or (
        "exported_from_current_state=true" in text
    )


def test_docs_record_previous_export_reused_false() -> None:
    text = _combined()
    assert "previous_export_reused" in text
    assert "`previous_export_reused` | `false`" in text or (
        "previous_export_reused=false" in text
    )


def test_docs_record_state_freshness_result_pass() -> None:
    text = _combined()
    assert "state_freshness_result" in text
    assert "`state_freshness_result` | `pass`" in text or (
        "state_freshness_result=pass" in text
    )


def test_docs_record_final_write_false() -> None:
    text = _combined()
    assert "final_write" in text
    assert "`final_write` | `false`" in text or "final_write=false" in text


def test_docs_record_productive_mode_requested_false() -> None:
    text = _combined()
    assert "productive_mode_requested" in text
    assert "`productive_mode_requested` | `false`" in text or (
        "productive_mode_requested=false" in text
    )


def test_docs_record_source_mutation_false() -> None:
    text = _combined()
    assert "source_mutation" in text
    assert "`source_mutation` | `false`" in text or "source_mutation=false" in text


def test_docs_record_paypal_guidance() -> None:
    text = _combined()
    assert "PayPal" in text
    assert (
        "keine aktive PayPal-Konfiguration" in text
        or "PayPal guidance" in text.lower()
        or "PayPal-Guidance" in text
    )


def test_docs_record_generic_card_no_amex_guidance() -> None:
    text = _combined()
    assert "AMEX" in text
    assert (
        "generic credit card detected, AMEX not proven" in text
        or "AMEX nicht belegt" in text
        or "kein AMEX" in text
    )


def test_docs_record_missing_payment_field_guidance() -> None:
    text = _combined()
    assert "FEHLT_payment_field" in text
    assert (
        "payment_field fehlt" in text
        or "missing payment_field" in text.lower()
        or "Zahlungsfeld nicht sicher erkannt" in text
    )


def test_docs_do_not_claim_saas_ready() -> None:
    text = _combined().lower()
    assert "nicht saas-ready" in text
    assert "saas-ready" in text
    # Positive claim without negation must not appear as maturity claim.
    assert "ist saas-ready" not in text
    assert "claims_saas_ready` | `true`" not in _combined()
    assert "claims_saas_ready=true" not in _combined()


def test_docs_do_not_claim_production_ready() -> None:
    text = _combined().lower()
    assert "nicht production-ready" in text
    assert "ist production-ready" not in text
    assert "claims_production_ready` | `true`" not in _combined()
    assert "claims_production_ready=true" not in _combined()


def test_docs_record_product_status_and_next_task() -> None:
    text = _combined()
    assert PRODUCT_STATUS in text
    assert NEXT_TASK in text
    assert "Remaining prompts: 9" in text or "**Remaining prompts:** 9" in text


def test_docs_state_no_productive_processing_and_no_real_folders() -> None:
    text = _combined().lower()
    assert "keine produktive verarbeitung" in text or "no productive processing" in text
    assert "keine realen rechnungsordner" in text or "no real invoice folders" in text


def test_track_a_protection_still_passes() -> None:
    from tests.test_track_a_internal_app_protection import (
        test_processing_core_unchanged_vs_head,
        test_track_a_protected_files_unchanged_vs_head,
    )

    test_track_a_protected_files_unchanged_vs_head()
    test_processing_core_unchanged_vs_head()
