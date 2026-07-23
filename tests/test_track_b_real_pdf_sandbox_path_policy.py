"""Track-B Real-PDF sandbox path policy (Prompt 11/34).

Positive copied sandbox/test override without weakening original/productive blocks.
No productive processing, no run_once, no Track-A changes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_tool.ui_v2.sandbox_processing_gate import (
    MSG_PATH_COPIED_SANDBOX_MISSING,
    MSG_PATH_ORIGINAL_LOOKING,
    MSG_PATH_PRODUCTIVE_BLOCKED,
    MSG_PATH_SAME_INPUT_OUTPUT,
    MSG_SAFETY_COPIED_SANDBOX_CONFIRMED,
    MSG_SAFETY_DRY_RUN_NO_MUTATION,
    MSG_SAFETY_ORIGINAL_EXCLUDED,
    MSG_SAFETY_PRODUCTIVE_BLOCKED,
    classify_copied_sandbox_test_paths,
    is_explicit_copied_sandbox_test_path,
    path_has_positive_sandbox_test_signal,
    path_looks_like_original,
)

CONTROLLED_ROOT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test")
CONTROLLED_INPUT = CONTROLLED_ROOT / "input"
CONTROLLED_OUTPUT = CONTROLLED_ROOT / "output"


def test_controlled_ki_rechnungen_test_classified_as_copied_sandbox() -> None:
    assert path_has_positive_sandbox_test_signal(str(CONTROLLED_INPUT))
    assert is_explicit_copied_sandbox_test_path(str(CONTROLLED_INPUT))
    assert path_looks_like_original(str(CONTROLLED_INPUT)) is False
    assert path_looks_like_original(str(CONTROLLED_OUTPUT)) is False

    result = classify_copied_sandbox_test_paths(
        str(CONTROLLED_INPUT),
        str(CONTROLLED_OUTPUT),
        sandbox_root=str(CONTROLLED_ROOT),
        check_filesystem=CONTROLLED_INPUT.is_dir() and CONTROLLED_OUTPUT.is_dir(),
    )
    assert result.approved is True
    assert result.kind == "safe_copied_sandbox_test"
    assert result.message == MSG_SAFETY_COPIED_SANDBOX_CONFIRMED


def test_desktop_rechnungen_remains_blocked() -> None:
    path = "/Users/hadi_neu/Desktop/RECHNUNGEN/inbox"
    assert path_looks_like_original(path) is True
    result = classify_copied_sandbox_test_paths(
        path,
        "/Users/hadi_neu/Desktop/RECHNUNGEN/out",
        sandbox_root="/Users/hadi_neu/Desktop/RECHNUNGEN",
    )
    assert result.approved is False
    assert result.message == MSG_PATH_ORIGINAL_LOOKING


def test_desktop_02_rechnungseingang_remains_blocked() -> None:
    path = "/Users/hadi_neu/Desktop/02_Rechnungseingang/inbox"
    assert path_looks_like_original(path) is True
    result = classify_copied_sandbox_test_paths(
        path,
        "/Users/hadi_neu/Desktop/02_Rechnungseingang/out",
    )
    assert result.approved is False
    assert "Original" in result.message or "Produktiv" in result.message


def test_rechnungseingang_remains_blocked() -> None:
    path = "/tmp/data/Rechnungseingang/inbox"
    assert path_looks_like_original(path) is True
    result = classify_copied_sandbox_test_paths(
        path,
        "/tmp/data/Rechnungseingang/out",
    )
    assert result.approved is False
    assert result.message == MSG_PATH_ORIGINAL_LOOKING


def test_original_folder_remains_blocked() -> None:
    path = "/tmp/sandbox-copy/Original/inbox"
    assert path_looks_like_original(path) is True
    result = classify_copied_sandbox_test_paths(
        path,
        "/tmp/sandbox-copy/out",
        sandbox_root="/tmp/sandbox-copy",
    )
    assert result.approved is False
    assert result.message == MSG_PATH_ORIGINAL_LOOKING


def test_produktiv_folder_remains_blocked() -> None:
    path = "/tmp/workspace/Produktiv/inbox"
    assert path_looks_like_original(path) is True
    result = classify_copied_sandbox_test_paths(
        path,
        "/tmp/workspace/Produktiv/out",
    )
    assert result.approved is False
    assert result.message == MSG_PATH_ORIGINAL_LOOKING


def test_identical_input_output_blocked(tmp_path: Path) -> None:
    shared = tmp_path / "sandbox" / "shared"
    shared.mkdir(parents=True)
    result = classify_copied_sandbox_test_paths(
        str(shared),
        str(shared),
        sandbox_root=str(tmp_path / "sandbox"),
        check_filesystem=True,
    )
    assert result.approved is False
    assert result.message == MSG_PATH_SAME_INPUT_OUTPUT


def test_missing_input_blocked(tmp_path: Path) -> None:
    missing = tmp_path / "sandbox" / "missing-input"
    out = tmp_path / "sandbox" / "output_preview"
    out.mkdir(parents=True)
    result = classify_copied_sandbox_test_paths(
        str(missing),
        str(out),
        sandbox_root=str(tmp_path / "sandbox"),
        check_filesystem=True,
    )
    assert result.approved is False
    assert result.reason_code == "blocked_input_not_dir"


def test_non_directory_blocked(tmp_path: Path) -> None:
    root = tmp_path / "sandbox"
    root.mkdir()
    file_input = root / "input_copy.txt"
    file_input.write_text("not a dir", encoding="utf-8")
    out = root / "output_preview"
    out.mkdir()
    result = classify_copied_sandbox_test_paths(
        str(file_input),
        str(out),
        sandbox_root=str(root),
        check_filesystem=True,
    )
    assert result.approved is False
    assert result.reason_code == "blocked_input_not_dir"


def test_productive_mode_requested_blocked(tmp_path: Path) -> None:
    inbox = tmp_path / "sandbox" / "input_copy"
    outbox = tmp_path / "sandbox" / "output_preview"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    result = classify_copied_sandbox_test_paths(
        str(inbox),
        str(outbox),
        sandbox_root=str(tmp_path / "sandbox"),
        productive_mode_requested=True,
        check_filesystem=True,
    )
    assert result.approved is False
    assert result.message == MSG_PATH_PRODUCTIVE_BLOCKED


def test_positive_sandbox_test_marker_required() -> None:
    # Use string paths without "test"/"sandbox" tokens (pytest tmp_path names
    # often contain "test" and would falsely satisfy the positive signal).
    inbox = "/Users/demo/Documents/plain-data/in"
    outbox = "/Users/demo/Documents/plain-data/out"
    assert path_has_positive_sandbox_test_signal(inbox) is False
    result = classify_copied_sandbox_test_paths(
        inbox,
        outbox,
        sandbox_root="/Users/demo/Documents/plain-data",
    )
    assert result.approved is False
    assert result.message == MSG_PATH_COPIED_SANDBOX_MISSING


def test_safety_proof_says_copied_sandbox_confirmed(tmp_path: Path) -> None:
    inbox = tmp_path / "sandbox" / "input_copy"
    outbox = tmp_path / "sandbox" / "output_preview"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    result = classify_copied_sandbox_test_paths(
        str(inbox),
        str(outbox),
        sandbox_root=str(tmp_path / "sandbox"),
        check_filesystem=True,
    )
    assert result.approved is True
    assert MSG_SAFETY_COPIED_SANDBOX_CONFIRMED in result.safety_proof_lines
    assert MSG_SAFETY_ORIGINAL_EXCLUDED in result.safety_proof_lines
    assert MSG_SAFETY_PRODUCTIVE_BLOCKED in result.safety_proof_lines
    assert MSG_SAFETY_DRY_RUN_NO_MUTATION in result.safety_proof_lines


def test_blocker_reason_specific_for_original_looking() -> None:
    result = classify_copied_sandbox_test_paths(
        "/Users/demo/Desktop/Rechnungen/Inbox",
        "/Users/demo/Desktop/Rechnungen/Out",
    )
    assert result.approved is False
    assert result.message == MSG_PATH_ORIGINAL_LOOKING
    assert result.reason_code == "blocked_original_looking"


def test_no_blanket_desktop_rechnung_allow() -> None:
    # Desktop + Rechnung without positive sandbox/test signal stays blocked.
    desktop_invoice = "/Users/demo/Desktop/Rechnungen/Inbox"
    assert path_looks_like_original(desktop_invoice) is True
    assert is_explicit_copied_sandbox_test_path(desktop_invoice) is False

    # Named "TEST Rechnungen" remains original-looking (not a sandbox override).
    test_rechnungen = "/Users/demo/Desktop/TEST Rechnungen/inbox"
    assert path_looks_like_original(test_rechnungen) is True
    assert is_explicit_copied_sandbox_test_path(test_rechnungen) is False

    # Controlled test folder is allowed only via positive test signal.
    assert path_looks_like_original(str(CONTROLLED_INPUT)) is False
    assert is_explicit_copied_sandbox_test_path(str(CONTROLLED_INPUT)) is True


def test_env_scoped_test_root_allows_without_name_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "controlled-root"
    inbox = root / "input"
    outbox = root / "output"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)
    monkeypatch.setenv(
        "KI_RECHNUNGEN_COPIED_SANDBOX_TEST_ROOTS",
        str(root),
    )
    assert path_has_positive_sandbox_test_signal(str(inbox)) is True
    result = classify_copied_sandbox_test_paths(
        str(inbox),
        str(outbox),
        sandbox_root=str(root),
        check_filesystem=True,
    )
    assert result.approved is True
