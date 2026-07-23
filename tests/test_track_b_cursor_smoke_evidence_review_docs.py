"""Doc-gate for Track-B Cursor Smoke Evidence Review and Next Gate (Prompt 9/34).

Docs + fixture only — no GUI, no real invoice folders, no productive processing.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_CURSOR_SMOKE_EVIDENCE_REVIEW_AND_NEXT_GATE_2026-07-22.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_CURSOR_SMOKE_EVIDENCE_REVIEW_AND_NEXT_GATE_2026-07-22.md"
)
NEXT_TASK = "KI_RECHNUNGEN_TRACK_B_CONTROLLED_COPIED_REAL_PDF_SANDBOX_SMOKE_01"
PRODUCT_STATUS_AFTER = (
    "TRACK_B_CURSOR_SMOKE_EVIDENCE_ACCEPTED_SYNTHETIC_LIMITATION_DISCLOSED"
)
EVIDENCE_CLASSIFICATION = (
    "TECHNICAL_CURSOR_SMOKE_ACCEPTED_WITH_SYNTHETIC_LIMITATION"
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing doc: {path}"
    return path.read_text(encoding="utf-8")


def test_evidence_review_doc_exists() -> None:
    assert DOC.is_file()


def test_audit_exists() -> None:
    assert AUDIT.is_file()


def test_doc_states_synthetic_limitation() -> None:
    text = _read(DOC)
    assert "Synthetic limitation" in text or "synthetisch" in text.lower()
    assert "Fake-`CoreDryRunResult`" in text or "Fake-CoreDryRunResult" in text or (
        "CoreDryRunResult" in text and "synthet" in text.lower()
    )
    assert EVIDENCE_CLASSIFICATION in text


def test_doc_states_not_full_visual_manual_gui_smoke() -> None:
    text = _read(DOC)
    assert "visuell" in text.lower() or "visual" in text.lower()
    assert "GUI" in text
    assert "nicht" in text.lower()
    assert "manuell" in text.lower() or "manual" in text.lower()


def test_doc_states_no_productive_processing() -> None:
    text = _read(DOC)
    lowered = text.lower()
    assert "keine produktive verarbeitung" in lowered or (
        "no productive processing" in lowered
    )


def test_doc_states_no_real_invoice_folders() -> None:
    text = _read(DOC)
    lowered = text.lower()
    assert "keine realen rechnungsordner" in lowered or (
        "no real invoice folders" in lowered
    )
    assert "/Users/hadi_neu/Desktop/RECHNUNGEN" in text


def test_doc_states_not_saas_ready() -> None:
    text = _read(DOC)
    assert "nicht SaaS-ready" in text


def test_doc_states_not_production_ready() -> None:
    text = _read(DOC)
    assert "nicht production-ready" in text


def test_doc_selects_exact_next_task() -> None:
    text = _read(DOC)
    assert NEXT_TASK in text
    assert "Next gate decision" in text or "next gate" in text.lower()


def test_audit_states_release_tags_unchanged() -> None:
    text = _read(AUDIT)
    assert "No release tag changes" in text or "Release-Tags unverändert" in text
    assert "product-v1-local-pilot-2026-07-22" in text
    assert "internal-working-version-2026-07-21" in text


def test_audit_states_product_status_after_task() -> None:
    text = _read(AUDIT)
    assert PRODUCT_STATUS_AFTER in text
    assert "Remaining prompts: 25" in text or "25" in text
    assert NEXT_TASK in text
    assert EVIDENCE_CLASSIFICATION in text
