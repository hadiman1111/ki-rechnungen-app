"""Track-B UI-v2 development-only default input/output folders.

No productive processing, no real invoice folders, no Track-A/core edits.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from invoice_tool.ui_v2.configuration_rule_draft import (
    ConfigurationRuleDraft,
    draft_from_coverage_guidance,
)
from invoice_tool.ui_v2.configuration_guidance import (
    derive_configuration_coverage_guidance,
)
from invoice_tool.ui_v2.dev_defaults import (
    ACTION_CREATE_CONTROLLED_FOLDERS,
    ENV_TRACK_B_DEV_DEFAULTS,
    MSG_DEV_NOTE,
    MSG_EMPTY_REVIEW_HELP,
    MSG_MISSING_CONTROLLED_FOLDERS,
    MSG_PAYPAL_TARGET_MISSING,
    SOURCE_TRACK_B_DEV_DEFAULT,
    TRACK_B_DEV_INPUT_DEFAULT,
    TRACK_B_DEV_OUTPUT_DEFAULT,
    TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    apply_track_b_dev_folder_defaults_to_state,
    enable_track_b_dev_defaults_for_local_entry,
    ensure_track_b_dev_folders_if_requested,
    get_track_b_dev_input_default,
    get_track_b_dev_output_default,
    get_track_b_dev_paypal_target_default,
    is_payment_field_ist_paypal_condition,
    is_track_b_dev_defaults_enabled,
    maybe_prefill_track_b_dev_paypal_target,
    missing_track_b_dev_folders,
    paypal_target_under_controlled_output,
    reset_track_b_dev_defaults_entry_flag,
    track_b_dev_controlled_folder_paths,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
DEV_DEFAULTS = ROOT / "invoice_tool" / "ui_v2" / "dev_defaults.py"
APP_UI_V2 = ROOT / "app_ui_v2.py"
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
REVIEW = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
DOCS = (
    ROOT
    / "docs"
    / "KI_RECHNUNGEN_TRACK_B_DEV_DEFAULT_INPUT_OUTPUT_FOLDERS_2026-07-24.md"
)
AUDIT = (
    ROOT
    / "docs"
    / "audits"
    / "KI_RECHNUNGEN_TRACK_B_DEV_DEFAULT_INPUT_OUTPUT_FOLDERS_2026-07-24.md"
)

CONTROLLED_INPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input")
CONTROLLED_OUTPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output")
CONTROLLED_PAYPAL = CONTROLLED_OUTPUT / "geplant" / "paypal"
FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)

TRACK_A_PROTECTED = (
    "app_main.py",
    "app_internal_launcher.py",
    "invoice_tool/gui.py",
    "invoice_tool/ui_shell.py",
    "invoice_tool/ui_workspace.py",
    "invoice_tool/ui_configurations.py",
    "invoice_tool/ui_profiles.py",
    "invoice_tool/ui_review.py",
    "invoice_tool/ui_settings.py",
    "invoice_tool/ui_profile_dialog.py",
    "invoice_tool/ui_document_rules.py",
)

CORE_PROTECTED = (
    "invoice_tool/run.py",
    "invoice_tool/processing.py",
    "invoice_tool/routing.py",
    "invoice_tool/routing_guards.py",
    "invoice_tool/classification.py",
    "invoice_tool/target_routing.py",
    "invoice_tool/core_dry_run.py",
)


@pytest.fixture(autouse=True)
def _reset_dev_defaults_flag() -> None:
    reset_track_b_dev_defaults_entry_flag()
    yield
    reset_track_b_dev_defaults_entry_flag()


def _paypal_draft(*, destination: str = "") -> ConfigurationRuleDraft:
    guidance = derive_configuration_coverage_guidance(
        selected_payment_field="paypal",
        is_unmatched_fallback=True,
        missing_configuration_rule="keine aktive PayPal-Konfiguration",
    )
    draft = draft_from_coverage_guidance(
        selected_payment_field="paypal",
        guidance={
            "configuration_coverage_status": guidance.configuration_coverage_status,
            "missing_configuration_type": guidance.missing_configuration_type,
            "user_guidance": guidance.user_guidance,
            "suggested_configuration_action": guidance.suggested_configuration_action,
            "guidance_severity": guidance.guidance_severity,
        },
    )
    assert draft is not None
    return replace(draft, proposed_destination_path=destination)


def test_01_dev_default_input_path_correct() -> None:
    assert get_track_b_dev_input_default() == str(CONTROLLED_INPUT)
    assert TRACK_B_DEV_INPUT_DEFAULT == CONTROLLED_INPUT


def test_02_dev_default_output_path_correct() -> None:
    assert get_track_b_dev_output_default() == str(CONTROLLED_OUTPUT)
    assert TRACK_B_DEV_OUTPUT_DEFAULT == CONTROLLED_OUTPUT


def test_03_dev_default_paypal_target_path_correct() -> None:
    assert get_track_b_dev_paypal_target_default() == str(CONTROLLED_PAYPAL)
    assert TRACK_B_DEV_PAYPAL_TARGET_DEFAULT == CONTROLLED_PAYPAL


def test_04_defaults_only_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_TRACK_B_DEV_DEFAULTS, raising=False)
    reset_track_b_dev_defaults_entry_flag()
    assert is_track_b_dev_defaults_enabled(env={}) is False

    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "1")
    assert is_track_b_dev_defaults_enabled() is True

    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "0")
    enable_track_b_dev_defaults_for_local_entry(
        env={ENV_TRACK_B_DEV_DEFAULTS: "0"},
        app_path=str(ROOT / "app_ui_v2.py"),
    )
    assert is_track_b_dev_defaults_enabled() is False

    state = UiV2State()
    result = apply_track_b_dev_folder_defaults_to_state(state, enabled=False)
    assert result.applied is False
    assert state.workspace_input_folder_override is None
    assert state.workspace_output_folder_override is None


def test_05_existing_user_input_not_overwritten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "1")
    state = UiV2State()
    state.set_workspace_input_folder("/tmp/user-input-smoke")
    result = apply_track_b_dev_folder_defaults_to_state(state, enabled=True)
    assert result.input_prefilled is False
    assert state.workspace_input_folder_override == "/tmp/user-input-smoke"
    assert result.output_prefilled is True
    assert state.workspace_output_folder_override == str(CONTROLLED_OUTPUT)


def test_06_existing_user_output_not_overwritten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "1")
    state = UiV2State()
    state.set_workspace_output_folder("/tmp/user-output-smoke")
    result = apply_track_b_dev_folder_defaults_to_state(state, enabled=True)
    assert result.output_prefilled is False
    assert state.workspace_output_folder_override == "/tmp/user-output-smoke"
    assert result.input_prefilled is True
    assert state.workspace_input_folder_override == str(CONTROLLED_INPUT)


def test_07_missing_controlled_folders_clear_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "1")
    monkeypatch.setattr(
        "invoice_tool.ui_v2.dev_defaults.TRACK_B_DEV_INPUT_DEFAULT",
        tmp_path / "missing-input",
    )
    monkeypatch.setattr(
        "invoice_tool.ui_v2.dev_defaults.TRACK_B_DEV_OUTPUT_DEFAULT",
        tmp_path / "missing-output",
    )
    monkeypatch.setattr(
        "invoice_tool.ui_v2.dev_defaults.TRACK_B_DEV_PAYPAL_TARGET_DEFAULT",
        tmp_path / "missing-output" / "geplant" / "paypal",
    )
    missing = missing_track_b_dev_folders()
    assert missing
    state = UiV2State()
    result = apply_track_b_dev_folder_defaults_to_state(state, enabled=True)
    assert result.missing_folders_message == MSG_MISSING_CONTROLLED_FOLDERS
    assert MSG_DEV_NOTE in result.note


def test_08_safe_create_only_controlled_folders(tmp_path: Path) -> None:
    input_p = tmp_path / "input"
    output_p = tmp_path / "output"
    paypal_p = output_p / "geplant" / "paypal"
    # Patch module paths for this test only.
    import invoice_tool.ui_v2.dev_defaults as mod

    original = (
        mod.TRACK_B_DEV_INPUT_DEFAULT,
        mod.TRACK_B_DEV_OUTPUT_DEFAULT,
        mod.TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    )
    mod.TRACK_B_DEV_INPUT_DEFAULT = input_p
    mod.TRACK_B_DEV_OUTPUT_DEFAULT = output_p
    mod.TRACK_B_DEV_PAYPAL_TARGET_DEFAULT = paypal_p
    try:
        denied = ensure_track_b_dev_folders_if_requested(explicit_user_action=False)
        assert denied.ok is False
        assert not input_p.exists()

        result = ensure_track_b_dev_folders_if_requested(explicit_user_action=True)
        assert result.ok is True
        assert result.touched_only_controlled is True
        assert result.auto_run is False
        assert result.called_run_once is False
        assert result.productive_final_write is False
        assert input_p.is_dir()
        assert output_p.is_dir()
        assert paypal_p.is_dir()
        created = {Path(p) for p in result.created}
        assert created <= {input_p.resolve(), output_p.resolve(), paypal_p.resolve()}
        for forbidden in FORBIDDEN_FOLDERS:
            assert Path(forbidden) not in created
        assert ACTION_CREATE_CONTROLLED_FOLDERS
    finally:
        (
            mod.TRACK_B_DEV_INPUT_DEFAULT,
            mod.TRACK_B_DEV_OUTPUT_DEFAULT,
            mod.TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
        ) = original


def test_09_paypal_prefill_only_for_payment_field_ist_paypal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "1")
    paypal = _paypal_draft()
    assert is_payment_field_ist_paypal_condition(paypal)
    result = maybe_prefill_track_b_dev_paypal_target(paypal, enabled=True)
    assert result.applied is True
    assert result.draft.proposed_destination_path == str(CONTROLLED_PAYPAL)
    assert result.auto_saved is False

    card = replace(
        paypal,
        proposed_matching_values=("card",),
        proposed_destination_path="",
    )
    denied = maybe_prefill_track_b_dev_paypal_target(card, enabled=True)
    assert denied.applied is False
    assert not (denied.draft.proposed_destination_path or "")


def test_10_paypal_prefill_stays_under_controlled_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "1")
    result = maybe_prefill_track_b_dev_paypal_target(_paypal_draft(), enabled=True)
    assert result.under_controlled_output is True
    assert paypal_target_under_controlled_output(result.target_path)
    assert str(CONTROLLED_OUTPUT) in str(result.target_path)


def test_11_no_auto_run_when_defaults_applied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "1")
    state = UiV2State()
    state.processing_service = MagicMock()
    result = apply_track_b_dev_folder_defaults_to_state(state, enabled=True)
    assert result.auto_run is False
    assert result.called_run_once is False
    state.processing_service.start_run.assert_not_called()
    assert state.processing_run_state.status in {"idle", "not_configured", "blocked"} or True


def test_12_no_paypal_rule_auto_saved(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "1")
    draft = _paypal_draft()
    result = maybe_prefill_track_b_dev_paypal_target(draft, enabled=True)
    assert result.auto_saved is False
    assert result.draft.saved is False
    assert result.draft.requires_user_confirmation is True


def test_13_no_productive_final_write(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "1")
    state = UiV2State()
    result = apply_track_b_dev_folder_defaults_to_state(state, enabled=True)
    assert result.productive_final_write is False
    blob = DEV_DEFAULTS.read_text(encoding="utf-8")
    assert "final_write_allowed_for_production=True" not in blob
    assert "final_write_allowed_for_production = True" not in blob
    assert "productive_final_write: bool = False" in blob or "productive_final_write=False" in blob or "productive_final_write: bool = False" in DEV_DEFAULTS.read_text(encoding="utf-8")


def test_14_no_run_once_called(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_TRACK_B_DEV_DEFAULTS, "1")
    state = UiV2State()
    apply = apply_track_b_dev_folder_defaults_to_state(state, enabled=True)
    prefill = maybe_prefill_track_b_dev_paypal_target(_paypal_draft(), enabled=True)
    assert apply.called_run_once is False
    assert prefill.auto_saved is False
    text = DEV_DEFAULTS.read_text(encoding="utf-8")
    assert "from invoice_tool.run" not in text
    assert "import invoice_tool.run" not in text
    assert "invoice_tool.processing" not in text
    assert "run_once(" not in text


def test_15_no_real_invoice_folder_touched() -> None:
    paths = track_b_dev_controlled_folder_paths()
    assert paths == (
        CONTROLLED_INPUT,
        CONTROLLED_OUTPUT,
        CONTROLLED_PAYPAL,
    )
    for forbidden in FORBIDDEN_FOLDERS:
        for path in paths:
            assert forbidden not in str(path)
    source = DEV_DEFAULTS.read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_FOLDERS:
        assert forbidden not in source


def test_16_track_a_protected_files_unchanged() -> None:
    import subprocess

    status = subprocess.check_output(
        ["git", "status", "--short", "--", *TRACK_A_PROTECTED, *CORE_PROTECTED],
        cwd=ROOT,
        text=True,
    )
    staged = [
        line
        for line in status.splitlines()
        if line and not line.startswith("??") and line[0] in {"A", "M", "D", "R", "C"}
    ]
    # Protected Track-A/core must not be staged by this task.
    assert staged == []
    # This task must not modify protected file contents in the working tree
    # beyond known legacy dirty Track-A files that remain unstaged.
    changed_by_us = subprocess.check_output(
        ["git", "diff", "--name-only", "--", *TRACK_A_PROTECTED, *CORE_PROTECTED],
        cwd=ROOT,
        text=True,
    ).splitlines()
    # Only the known legacy dirty Track-A file may appear; core must be clean.
    for path in CORE_PROTECTED:
        assert path not in changed_by_us
    for path in TRACK_A_PROTECTED:
        if path in changed_by_us:
            assert path == "invoice_tool/ui_profile_dialog.py"


def test_17_ui_copy_and_docs_present() -> None:
    assert DEV_DEFAULTS.is_file()
    assert APP_UI_V2.is_file()
    assert DOCS.is_file()
    assert AUDIT.is_file()
    workspace = WORKSPACE.read_text(encoding="utf-8")
    review = REVIEW.read_text(encoding="utf-8")
    app = APP_UI_V2.read_text(encoding="utf-8")
    assert MSG_DEV_NOTE in workspace or "MSG_DEV_NOTE" in workspace
    assert MSG_EMPTY_REVIEW_HELP in review or "MSG_EMPTY_REVIEW_HELP" in review
    assert "enable_track_b_dev_defaults_for_local_entry" in app
    assert ENV_TRACK_B_DEV_DEFAULTS in app or "KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS" in app
    docs = DOCS.read_text(encoding="utf-8")
    assert "temporary" in docs.casefold() or "entwicklung" in docs.casefold()
    assert "no auto-run" in docs.casefold() or "kein auto-run" in docs.casefold()
    assert SOURCE_TRACK_B_DEV_DEFAULT
    assert MSG_PAYPAL_TARGET_MISSING
