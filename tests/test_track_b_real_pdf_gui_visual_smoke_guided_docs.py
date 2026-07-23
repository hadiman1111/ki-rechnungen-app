"""Doc-gate for Track-B Real-PDF GUI Visual Smoke Guided (Prompt 12/34).

Docs + fixture only — no GUI launch, no real invoice folders, no productive processing.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDED_2026-07-22.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDED_2026-07-22.md"
)

CONTROLLED_INPUT = "/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input"
CONTROLLED_OUTPUT = "/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output"
APP_MODULE = ROOT / "invoice_tool" / "ui_v2" / "app.py"
APP_ENTRY = ROOT / "app_ui_v2.py"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing doc: {path}"
    return path.read_text(encoding="utf-8")


def test_guide_doc_exists() -> None:
    assert GUIDE.is_file()


def test_audit_exists() -> None:
    assert AUDIT.is_file()


def test_guide_includes_controlled_input_path() -> None:
    text = _read(GUIDE)
    assert CONTROLLED_INPUT in text


def test_guide_includes_controlled_output_path() -> None:
    text = _read(GUIDE)
    assert CONTROLLED_OUTPUT in text


def test_guide_includes_monitor_command() -> None:
    text = _read(GUIDE)
    assert 'BASE="$HOME/Desktop/KI-Rechnungen-Test"' in text
    assert "while true; do" in text
    assert "OUTPUT COUNT:" in text
    assert "Im Dry-Run darf OUTPUT leer bleiben" in text


def test_guide_includes_app_start_section() -> None:
    text = _read(GUIDE)
    assert "Safe app start" in text or "B. Safe app start" in text
    assert "app_ui_v2.py" in text
    assert ".venv/bin/python" in text


def test_guide_does_not_invent_entrypoint_if_missing() -> None:
    """If -m invoice_tool.ui_v2.app is not runnable, guide must not claim it works."""
    text = _read(GUIDE)
    has_module = APP_MODULE.is_file()
    has_main_block = False
    if has_module:
        module_src = APP_MODULE.read_text(encoding="utf-8")
        has_main_block = (
            '__name__ == "__main__"' in module_src
            or "def main(" in module_src
            or (ROOT / "invoice_tool" / "ui_v2" / "__main__.py").is_file()
        )
    if has_module and not has_main_block:
        assert "kein** unterstützter Runnable-Entrypoint" in text or (
            "kein unterstützter Runnable-Entrypoint" in text
            or "nicht unterstützt" in text.lower()
            or "kein** unterstützter" in text
        )
        assert "nicht erfinden" in text.lower() or "erfindet keinen" in text.lower()
        assert APP_ENTRY.is_file()
        assert "app_ui_v2.py" in text
    else:
        # If a true -m entry exists later, guide may document it; still require a start section.
        assert "app start" in text.lower() or "App start" in text or "app_ui_v2.py" in text


def test_guide_includes_expected_review_planned_counts() -> None:
    text = _read(GUIDE)
    assert "Review" in text or "Prüfung" in text
    assert "5" in text
    assert "Planned" in text or "Geplant" in text
    assert "0" in text  # recognized expected around 0


def test_guide_explains_empty_output_only_with_visible_result_state() -> None:
    text = _read(GUIDE)
    assert "OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY" in text or "leer" in text.lower()
    assert "Result-State" in text or "result state" in text.lower()
    assert (
        "acceptable only with visible result state" in text.lower()
        or "nur** wenn UI nützlichen Result-State" in text
        or "nur wenn UI nützlichen Result-State" in text
        or "Output empty is acceptable only with visible result state" in text
    )


def test_guide_includes_evidence_return_format() -> None:
    text = _read(GUIDE)
    assert "GUI VISUAL SMOKE RESULT" in text
    assert "Classification:" in text
    assert "GUI_VISUAL_SMOKE_PASS" in text
    assert "GUI_VISUAL_SMOKE_PASS_WITH_NOTES" in text
    assert "GUI_VISUAL_SMOKE_BLOCKED" in text
    assert "GUI_VISUAL_SMOKE_FAIL_UNSAFE" in text


def test_guide_includes_stop_conditions() -> None:
    text = _read(GUIDE)
    assert "Stop conditions" in text or "Sofort stoppen" in text
    assert "produktive Verarbeitung" in text.lower() or "Produktiv" in text


def test_guide_states_no_productive_processing() -> None:
    text = _read(GUIDE)
    assert "Keine produktive Verarbeitung" in text or "keine produktive Verarbeitung" in text


def test_guide_states_no_real_invoice_folders() -> None:
    text = _read(GUIDE)
    assert (
        "Keine** realen Rechnungsordner" in text
        or "keine realen Rechnungsordner" in text.lower()
        or "Keine realen Rechnungsordner" in text
    )


def test_guide_states_not_saas_ready() -> None:
    text = _read(GUIDE)
    assert "nicht SaaS-ready" in text


def test_guide_states_not_production_ready() -> None:
    text = _read(GUIDE)
    assert "nicht production-ready" in text


def test_audit_states_product_status_after_task() -> None:
    text = _read(AUDIT)
    assert "TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDE_READY" in text


def test_audit_states_next_task() -> None:
    text = _read(AUDIT)
    assert "KI_RECHNUNGEN_TRACK_B_GUI_VISUAL_SMOKE_EVIDENCE_INTAKE_01" in text
    assert "Remaining prompts: 22" in text or "22" in text
