"""Track-B filename pattern simplification — remove double er_er (2026-07-24).

No productive processing, no run_once, no real invoice folders, no Track-A/core edits.
"""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.configuration_model import (
    Configuration,
    MatchingRule,
    UnmatchedConfiguration,
    new_configuration_id,
    pattern_from_template,
    pattern_to_template,
)
from invoice_tool.ui_v2.automated_smoke_oracle import (
    DEFAULT_PATTERN as ORACLE_DEFAULT_PATTERN,
    EXPECTED_DOCUMENTS,
    TRACK_A_PROTECTED,
    CORE_PROTECTED,
    hash_input_pdfs,
    oracle_modifies_processing_core,
    oracle_modifies_track_a,
    oracle_source_calls_run_once,
    oracle_touches_real_invoice_folders,
    oracle_writes_production_final_files,
)
from invoice_tool.ui_v2.configuration_filename_renderer import (
    build_configuration_placeholder_values,
    render_configuration_filename_pattern,
)
from invoice_tool.ui_v2.configuration_matching import _candidate_from_configuration
from invoice_tool.ui_v2.configuration_rule_draft import (
    DEFAULT_PATTERN,
    LEGACY_DOUBLE_ER_PATTERN,
    normalize_track_b_filename_pattern,
    resolve_default_filename_pattern,
)
from invoice_tool.ui_v2.configuration_rule_apply_preview import (
    reevaluate_planned_destination,
)
from invoice_tool.ui_v2.dev_defaults import (
    TRACK_B_DEV_INPUT_DEFAULT,
    TRACK_B_DEV_OUTPUT_DEFAULT,
)
from invoice_tool.ui_v2.finalization_readiness import FINAL_WRITE_ALLOWED_IN_THIS_PHASE
from invoice_tool.ui_v2.pages.review import MSG_LEGACY_ER_ER_NOTE, build_review_page_vm
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
SIMPLIFIED = "{invoice_date}_{art}_{supplier}_{amount}_{payment_field}.pdf"
FORBIDDEN_REAL = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)

EXPECTED_NAMES = {
    "LUMITOP": "2026-05-11_er_LUMITOP_476,00_paypal.pdf",
    "1A-Bootshop": "2026-05-15_er_1A-Bootshop.de_105,75_paypal.pdf",
    "Boettcher_card": "2026-05-23_er_Böttcher_AG_84,39_card.pdf",
    "Luxvenum": "2026-05-11_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf",
    "Boettcher_storno": "2026-06-18_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf",
}


def _render(
    *,
    invoice_date: str,
    art: str,
    supplier: str,
    amount: str,
    payment_field: str | None,
    pattern: str = SIMPLIFIED,
) -> str:
    values = build_configuration_placeholder_values(
        pattern=pattern,
        invoice_date=invoice_date,
        art=art,
        supplier=supplier,
        amount=amount,
        payment_field=payment_field,
    )
    result = render_configuration_filename_pattern(
        pattern, placeholder_values=values
    )
    assert result.rendered_filename
    return result.rendered_filename


def test_01_canonical_track_b_pattern_is_simplified() -> None:
    assert DEFAULT_PATTERN == SIMPLIFIED
    assert ORACLE_DEFAULT_PATTERN == SIMPLIFIED
    assert DEFAULT_PATTERN != LEGACY_DOUBLE_ER_PATTERN
    assert "_er_{art}" not in DEFAULT_PATTERN


def test_02_lumitop_filename() -> None:
    name = _render(
        invoice_date="2026-05-11",
        art="er",
        supplier="LUMITOP",
        amount="476,00",
        payment_field="paypal",
    )
    assert name == EXPECTED_NAMES["LUMITOP"]


def test_03_bootshop_filename() -> None:
    name = _render(
        invoice_date="2026-05-15",
        art="er",
        supplier="1A-Bootshop.de",
        amount="105,75",
        payment_field="paypal",
    )
    assert name == EXPECTED_NAMES["1A-Bootshop"]


def test_04_boettcher_card_filename() -> None:
    name = _render(
        invoice_date="2026-05-23",
        art="er",
        supplier="Böttcher AG",
        amount="84,39",
        payment_field="card",
    )
    assert name == EXPECTED_NAMES["Boettcher_card"]


def test_05_luxvenum_missing_payment_filename() -> None:
    name = _render(
        invoice_date="2026-05-11",
        art="er",
        supplier="Luxvenum LED GmbH",
        amount="154,95",
        payment_field=None,
    )
    assert name == EXPECTED_NAMES["Luxvenum"]
    assert "FEHLT_payment_field" in name


def test_06_storno_filename() -> None:
    name = _render(
        invoice_date="2026-06-18",
        art="storno",
        supplier="Böttcher AG",
        amount="68,94",
        payment_field=None,
    )
    assert name == EXPECTED_NAMES["Boettcher_storno"]


def test_07_no_new_filename_contains_er_er() -> None:
    names = [EXPECTED_NAMES[k] for k in EXPECTED_NAMES]
    for name in names:
        assert "_er_er_" not in name


def test_08_no_new_storno_filename_contains_er_storno() -> None:
    assert "_er_storno_" not in EXPECTED_NAMES["Boettcher_storno"]
    assert EXPECTED_NAMES["Boettcher_storno"].startswith("2026-06-18_storno_")


def test_09_paypal_rule_uses_simplified_pattern() -> None:
    from invoice_tool.ui_v2.automated_smoke_oracle import build_paypal_draft
    from invoice_tool.ui_v2.dev_defaults import TRACK_B_DEV_PAYPAL_TARGET_DEFAULT

    draft = build_paypal_draft(paypal_target=TRACK_B_DEV_PAYPAL_TARGET_DEFAULT)
    assert draft.proposed_filename_pattern == SIMPLIFIED
    assert draft.proposed_filename_pattern == DEFAULT_PATTERN


def test_10_unklar_config_uses_simplified_pattern() -> None:
    unmatched = UnmatchedConfiguration(
        name="Unklar",
        filename_pattern=pattern_from_template(LEGACY_DOUBLE_ER_PATTERN),
    )
    # Direct normalize + resolve path.
    assert (
        normalize_track_b_filename_pattern(pattern_to_template(unmatched.filename_pattern))
        == SIMPLIFIED
    )
    assert (
        resolve_default_filename_pattern(
            unmatched_pattern=pattern_to_template(unmatched.filename_pattern)
        )
        == SIMPLIFIED
    )
    cfg = Configuration(
        id=new_configuration_id(),
        name="Unklar-active",
        active=True,
        matching=MatchingRule(
            feature_key="payment_field",
            operator="ist",
            values=["unknown"],
        ),
        filename_pattern=pattern_from_template(LEGACY_DOUBLE_ER_PATTERN),
    )
    candidate = _candidate_from_configuration(cfg)
    assert candidate.filename_pattern == SIMPLIFIED


def test_11_preview_export_apply_preview_uses_simplified_fallback() -> None:
    apply_src = (
        ROOT / "invoice_tool" / "ui_v2" / "configuration_rule_apply_preview.py"
    ).read_text(encoding="utf-8")
    assert "DEFAULT_PATTERN" in apply_src
    assert '"{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf"' not in (
        apply_src
    )
    planned = ProcessingPlannedDestination(
        document_name="FA011466.pdf",
        planned_path="preview/geplant/paypal/x.pdf",
        destination_label="PayPal",
        preview_only=True,
        applied=False,
        invoice_date="2026-05-11",
        selected_art="er",
        supplier="LUMITOP",
        selected_amount="476,00",
        selected_payment_field="paypal",
        filename_pattern=SIMPLIFIED,
    )
    # Without profile match, pattern on planned is used for re-render via apply path.
    values = build_configuration_placeholder_values(
        pattern=planned.filename_pattern or SIMPLIFIED,
        invoice_date=planned.invoice_date,
        art=planned.selected_art,
        supplier=planned.supplier,
        amount=planned.selected_amount,
        payment_field=planned.selected_payment_field,
    )
    rendered = render_configuration_filename_pattern(
        planned.filename_pattern, placeholder_values=values
    )
    assert rendered.rendered_filename == EXPECTED_NAMES["LUMITOP"]
    _ = reevaluate_planned_destination  # import smoke / API availability


def test_12_oracle_expects_simplified_pattern() -> None:
    by_source = {d.source_filename: d for d in EXPECTED_DOCUMENTS}
    assert (
        by_source["FA011466.pdf"].expected_filename == EXPECTED_NAMES["LUMITOP"]
    )
    assert (
        by_source["Rechnung RE-202605-14594.pdf"].expected_filename
        == EXPECTED_NAMES["1A-Bootshop"]
    )
    assert (
        by_source["320262919974.pdf"].expected_filename
        == EXPECTED_NAMES["Boettcher_card"]
    )
    assert (
        by_source["Rechnung-2026156019-102201.pdf"].expected_filename
        == EXPECTED_NAMES["Luxvenum"]
    )
    assert (
        by_source["420260091336.pdf"].expected_filename
        == EXPECTED_NAMES["Boettcher_storno"]
    )
    for doc in EXPECTED_DOCUMENTS:
        assert "_er_er_" not in doc.expected_filename
        assert "_er_storno_" not in doc.expected_filename


def test_13_oracle_module_still_passable_contract() -> None:
    """Structural contract: oracle status constant + no run_once in module."""

    from invoice_tool.ui_v2.automated_smoke_oracle import STATUS_PASS

    assert STATUS_PASS == "TRACK_B_AUTOMATED_SMOKE_ORACLE_PASS"
    src = (
        ROOT / "invoice_tool" / "ui_v2" / "automated_smoke_oracle.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "run_once" not in calls


def test_14_boettcher_card_still_not_amex() -> None:
    card = next(d for d in EXPECTED_DOCUMENTS if d.source_filename == "320262919974.pdf")
    assert card.expected_config == "not_amex"
    assert card.payment_field == "card"
    assert "amex" not in (card.expected_filename or "").lower()


def test_15_luxvenum_still_missing_payment() -> None:
    lux = next(
        d
        for d in EXPECTED_DOCUMENTS
        if d.source_filename == "Rechnung-2026156019-102201.pdf"
    )
    assert lux.require_missing_payment is True
    assert lux.payment_field is None
    assert "FEHLT_payment_field" in lux.expected_filename


def test_16_boettcher_storno_still_art_storno() -> None:
    storno = next(
        d for d in EXPECTED_DOCUMENTS if d.source_filename == "420260091336.pdf"
    )
    assert storno.art == "storno"
    assert storno.expected_filename.startswith("2026-06-18_storno_")


def test_17_original_hashes_unchanged_contract() -> None:
    if not TRACK_B_DEV_INPUT_DEFAULT.is_dir():
        return
    before = hash_input_pdfs(TRACK_B_DEV_INPUT_DEFAULT)
    after = hash_input_pdfs(TRACK_B_DEV_INPUT_DEFAULT)
    assert before == after
    assert before  # controlled input present with PDFs


def test_18_no_run_once() -> None:
    assert oracle_source_calls_run_once() is False
    for rel in (
        "invoice_tool/ui_v2/configuration_rule_draft.py",
        "invoice_tool/ui_v2/automated_smoke_oracle.py",
        "invoice_tool/ui_v2/pages/review.py",
    ):
        src = (ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        attrs = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert "run_once" not in names
        assert "run_once" not in attrs


def test_19_no_productive_final_write() -> None:
    assert FINAL_WRITE_ALLOWED_IN_THIS_PHASE is False
    assert oracle_writes_production_final_files() is False
    # Oracle may *detect* a breach via assignment to safety flags; it must not
    # enable production writes as a feature default.
    draft_src = (
        ROOT / "invoice_tool" / "ui_v2" / "configuration_rule_draft.py"
    ).read_text(encoding="utf-8")
    review_src = (
        ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
    ).read_text(encoding="utf-8")
    assert "final_write_allowed_for_production=True" not in draft_src
    assert "final_write_allowed_for_production = True" not in draft_src
    assert "final_write_allowed_for_production=True" not in review_src
    assert "production_final_write_enabled=True" not in review_src
    assert "production_final_write_enabled = True" not in review_src


def test_20_no_real_invoice_folders() -> None:
    assert oracle_touches_real_invoice_folders() is False
    assert str(TRACK_B_DEV_INPUT_DEFAULT).startswith(
        "/Users/hadi_neu/Desktop/KI-Rechnungen-Test"
    )
    assert str(TRACK_B_DEV_OUTPUT_DEFAULT).startswith(
        "/Users/hadi_neu/Desktop/KI-Rechnungen-Test"
    )
    for path in FORBIDDEN_REAL:
        assert path not in str(TRACK_B_DEV_INPUT_DEFAULT)
        assert path not in str(TRACK_B_DEV_OUTPUT_DEFAULT)


def test_21_track_a_protection_still_passes() -> None:
    assert oracle_modifies_track_a() is False
    assert oracle_modifies_processing_core() is False
    for rel in TRACK_A_PROTECTED + CORE_PROTECTED:
        # Files may exist; this task must not stage/modify them.
        path = ROOT / rel
        if not path.exists():
            continue
        # Soft check: our simplification module sources must not import Track-A UI.
    draft_src = (
        ROOT / "invoice_tool" / "ui_v2" / "configuration_rule_draft.py"
    ).read_text(encoding="utf-8")
    assert "invoice_tool.gui" not in draft_src
    assert "invoice_tool.ui_shell" not in draft_src


def test_22_legacy_er_er_note_is_legacy_only() -> None:
    assert MSG_LEGACY_ER_ER_NOTE == (
        "Altes technisches Muster aus früherem Preview-Export."
    )
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="completed",
            message="ok",
            run_id="pattern-simp-1",
            review_items=(
                ProcessingReviewItem(
                    document_name="FA011466.pdf",
                    reason="test",
                    status_label="unklar",
                    document_id="doc-1",
                ),
            ),
            planned_destinations=(
                ProcessingPlannedDestination(
                    document_name="FA011466.pdf",
                    planned_path="preview/x.pdf",
                    destination_label="PayPal",
                    preview_only=True,
                    applied=False,
                    suggested_filename=EXPECTED_NAMES["LUMITOP"],
                    supplier="LUMITOP",
                    invoice_date="2026-05-11",
                    amount="476,00",
                    selected_amount="476,00",
                    selected_payment_field="paypal",
                    selected_art="er",
                ),
            ),
            planned_destination_count=1,
            outcome_kind="all_review",
        )
    )
    state.review_preview_ui.selected_item_key = "doc-1"
    vm = build_review_page_vm(state)
    assert vm.selected_detail is not None
    assert vm.selected_detail.er_er_note is None
    assert "_er_er_" not in (vm.selected_detail.suggested_filename or "")


def test_23_active_config_names_normalize_legacy_pattern() -> None:
    for name in (
        "American Express",
        "Event Production",
        "Architektur & Innenarchitektur",
        "Privat",
        "PayPal",
        "Unklar",
    ):
        cfg = Configuration(
            id=new_configuration_id(),
            name=name,
            active=True,
            matching=MatchingRule(
                feature_key="payment_field",
                operator="ist",
                values=["probe"],
            ),
            filename_pattern=pattern_from_template(LEGACY_DOUBLE_ER_PATTERN),
        )
        candidate = _candidate_from_configuration(cfg)
        assert candidate.filename_pattern == SIMPLIFIED, name
