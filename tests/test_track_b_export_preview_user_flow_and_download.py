"""Track-B Export Preview user flow and controlled download/output (Prompt 16/34).

Verifies preview-export package writing under sandbox output only.
No run_once, no productive final export, no Track-A/core mutation.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from invoice_tool.ui_v2.pages.workspace import (
    PACKAGE_EXPORT_ACTION_LABEL,
    PRODUCTIVE_FINAL_EXPORT_LABELS,
    apply_workspace_preview_export_package,
    workspace_exposes_preview_export_cta,
    workspace_exposes_productive_final_export,
)
from invoice_tool.ui_v2.preview_export import (
    MSG_NO_PRODUCTION_READY,
    MSG_NO_SAAS_READY,
    MSG_PREVIEW_EXPORT_CTA,
    MSG_PREVIEW_EXPORT_NO_FINAL_FILES,
    MSG_PREVIEW_EXPORT_ORIGINALS_UNCHANGED,
    MSG_PREVIEW_EXPORT_PRODUCTIVE_LOCKED,
    MSG_PREVIEW_EXPORT_SANDBOX_ONLY,
    MSG_PREVIEW_EXPORT_TITLE,
    PREVIEW_EXPORT_FOLDER_PREFIX,
    REVIEW_REQUIRED_PREFIX,
    preview_export_available,
    text_claims_forbidden_maturity,
    validate_preview_export_paths,
    write_preview_export_package,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
PREVIEW_EXPORT_MODULE = ROOT / "invoice_tool" / "ui_v2" / "preview_export.py"
WORKSPACE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "workspace.py"
STATE_MODULE = ROOT / "invoice_tool" / "ui_v2" / "state.py"

CONTROLLED_INPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input")
CONTROLLED_OUTPUT = Path("/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output")

PROCESSING_CORE = (
    "invoice_tool.processing",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
    "invoice_tool.run",
    "invoice_tool.core_dry_run",
)

FORBIDDEN_FOLDERS = (
    "/Users/hadi_neu/Desktop/RECHNUNGEN",
    "/Users/hadi_neu/Desktop/02_Rechnungseingang",
)

PDF_NAMES = (
    "320262919974.pdf",
    "420260091336.pdf",
    "FA011466.pdf",
    "Rechnung RE-202605-14594.pdf",
    "Rechnung-2026156019-102201.pdf",
)


def _digest_tree(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not folder.exists():
        return out
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _five_review_run() -> ProcessingRunState:
    review_items = tuple(
        ProcessingReviewItem(
            document_name=name,
            reason=f"Zuordnung unklar für {name}",
            status_label="unklar",
            document_id=f"doc-{index}",
            evidence_summary="Sandbox-Dry-Run: Prüfung erforderlich",
            next_action_hint="Manuell prüfen (Preview)",
        )
        for index, name in enumerate(PDF_NAMES, start=1)
    )
    planned = tuple(
        ProcessingPlannedDestination(
            document_name=name,
            planned_path=f"preview/ziel/{name}",
            destination_label="Geplantes Ziel",
            reason="Vorschau",
            applied=False,
            preview_only=True,
        )
        for name in PDF_NAMES
    )
    return ProcessingRunState(
        status="completed",
        message="Sandbox-Lauf mit Prüffällen abgeschlossen.",
        run_id="sandbox-preview-export-5",
        review_items=review_items,
        planned_destinations=planned,
        planned_destination_count=5,
        safety_proof_summary=(
            "Originale unverändert · Produktiv gesperrt · Export Vorschau"
        ),
        outcome_kind="all_review",
    )


def _sandbox_pair(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "KI-Rechnungen-Test"
    input_root = root / "input"
    output_root = root / "output"
    input_root.mkdir(parents=True)
    output_root.mkdir(parents=True)
    return input_root, output_root


def _seed_pdfs(input_root: Path, *, names: tuple[str, ...] = PDF_NAMES) -> None:
    for index, name in enumerate(names, start=1):
        payload = b"%PDF-1.4\npreview-seed-" + str(index).encode("ascii") + b"\n%%EOF\n"
        (input_root / name).write_bytes(payload)


@pytest.fixture()
def sandbox_dirs(tmp_path: Path) -> tuple[Path, Path]:
    input_root, output_root = _sandbox_pair(tmp_path)
    _seed_pdfs(input_root)
    return input_root, output_root


def test_preview_export_creates_dedicated_folder_under_controlled_output(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    assert result.ok is True
    assert result.export_folder is not None
    assert result.export_folder.parent == output_root.resolve()
    assert result.export_folder.name.startswith(PREVIEW_EXPORT_FOLDER_PREFIX)
    assert result.export_folder.is_dir()


def test_export_writes_readme_preview_export_md(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    readme = result.export_folder / "README_PREVIEW_EXPORT.md"
    assert readme.is_file()
    text = readme.read_text(encoding="utf-8")
    assert "preview/sandbox export" in text.lower() or "Preview/Sandbox" in text


def test_export_writes_manifest_json(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    manifest = result.export_folder / "manifest.json"
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["run_id"] == "sandbox-preview-export-5"
    assert payload["copied_file_count"] == 5


def test_export_writes_manifest_csv(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    csv_path = result.export_folder / "manifest.csv"
    assert csv_path.is_file()
    text = csv_path.read_text(encoding="utf-8")
    assert "source_filename" in text
    assert "preview_filename" in text


def test_export_writes_review_items_md_when_review_exists(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    review_md = result.export_folder / "review-items.md"
    assert review_md.is_file()
    assert "REVIEW_REQUIRED" in review_md.read_text(encoding="utf-8") or "320262919974" in review_md.read_text(
        encoding="utf-8"
    )


def test_export_writes_copied_preview_pdfs_under_files(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    files_dir = result.export_folder / "files"
    assert files_dir.is_dir()
    pdfs = list(files_dir.glob("*.pdf"))
    assert len(pdfs) == 5
    assert result.copied_file_count == 5


def test_copied_preview_pdfs_are_byte_identical(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    before = {p.name: p.read_bytes() for p in input_root.glob("*.pdf")}
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    for item in result.items:
        source_bytes = before[item.source_filename]
        preview_bytes = Path(item.preview_path).read_bytes()
        assert preview_bytes == source_bytes
        assert item.source_sha256 == item.preview_sha256


def test_review_files_prefixed_with_review_required(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    for item in result.items:
        assert item.review_required is True
        assert item.preview_filename.startswith(REVIEW_REQUIRED_PREFIX)


def test_manifest_includes_source_and_preview_filenames(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    payload = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    for row in payload["items"]:
        assert row["source_filename"]
        assert row["preview_filename"]


def test_manifest_includes_source_and_preview_sha256(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    payload = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    for row in payload["items"]:
        assert len(row["source_sha256"]) == 64
        assert len(row["preview_sha256"]) == 64
        assert row["source_sha256"] == row["preview_sha256"]


def test_manifest_includes_bucket_counts(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    payload = json.loads((result.export_folder / "manifest.json").read_text(encoding="utf-8"))
    assert payload["recognized_count"] == 0
    assert payload["review_count"] == 5
    assert payload["error_count"] == 0
    assert payload["planned_count"] == 5


def test_readme_states_preview_sandbox_not_final_originals_unchanged(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    text = (result.export_folder / "README_PREVIEW_EXPORT.md").read_text(encoding="utf-8")
    assert "preview/sandbox export" in text.lower()
    assert "not a final production output" in text.lower()
    assert "not moved/renamed/deleted" in text.lower()
    assert MSG_PREVIEW_EXPORT_NO_FINAL_FILES in text
    assert MSG_PREVIEW_EXPORT_ORIGINALS_UNCHANGED in text
    assert MSG_PREVIEW_EXPORT_PRODUCTIVE_LOCKED in text


def test_output_outside_controlled_folder_is_blocked(tmp_path: Path) -> None:
    input_root, _ = _sandbox_pair(tmp_path)
    _seed_pdfs(input_root)
    # Use a hard productive path (not under pytest tmp names that contain "test").
    outside = "/Users/hadi_neu/Desktop/RECHNUNGEN"
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=outside,
    )
    assert result.ok is False
    assert "blockiert" in (result.error or "").lower()
    # Synthetic non-sandbox desktop path without test/sandbox tokens.
    desktop_plain = "/Users/hadi_neu/Desktop/BelegeAusgangPlain"
    err = validate_preview_export_paths(str(input_root), desktop_plain)
    assert err is not None


def test_productive_original_paths_remain_blocked(tmp_path: Path) -> None:
    for forbidden in FORBIDDEN_FOLDERS:
        err = validate_preview_export_paths(
            str(tmp_path / "KI-Rechnungen-Test" / "input"),
            forbidden,
        )
        assert err is not None
        err_in = validate_preview_export_paths(
            forbidden,
            str(tmp_path / "KI-Rechnungen-Test" / "output"),
        )
        assert err_in is not None


def test_input_files_are_not_mutated(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    before = _digest_tree(input_root)
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    assert result.ok is True
    assert result.source_mutation is False
    assert _digest_tree(input_root) == before


def test_run_once_is_not_called(sandbox_dirs: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"run_once": 0}

    def boom(*_a, **_k):
        called["run_once"] += 1
        raise AssertionError("run_once must not be called")

    monkeypatch.setattr("invoice_tool.run.run_once", boom, raising=False)
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    assert result.ok is True
    assert called["run_once"] == 0
    tree = ast.parse(PREVIEW_EXPORT_MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "invoice_tool.run"
                assert not alias.name.startswith("invoice_tool.run.")
        if isinstance(node, ast.ImportFrom):
            assert node.module != "invoice_tool.run"
            assert not (node.module or "").startswith("invoice_tool.run.")
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id != "run_once"
            if isinstance(func, ast.Attribute):
                assert func.attr != "run_once"


def test_no_final_write_move_archive_delete_behavior(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    before_names = sorted(p.name for p in input_root.iterdir())
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    assert result.ok is True
    assert result.final_write is False
    assert result.productive_mode_requested is False
    assert sorted(p.name for p in input_root.iterdir()) == before_names
    # Only preview-export packages under output.
    children = list(output_root.iterdir())
    assert len(children) == 1
    assert children[0].name.startswith(PREVIEW_EXPORT_FOLDER_PREFIX)


def test_no_real_invoice_folders_touched(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    before_maps = {
        folder: (_digest_tree(Path(folder)) if Path(folder).exists() else {})
        for folder in FORBIDDEN_FOLDERS
    }
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    assert result.ok is True
    assert result.export_folder is not None
    for folder, before in before_maps.items():
        path = Path(folder)
        if path.exists():
            assert _digest_tree(path) == before
        # Export package must not land under forbidden roots.
        assert not str(result.export_folder).startswith(folder)


def test_no_saas_or_production_ready_claim(sandbox_dirs: tuple[Path, Path]) -> None:
    input_root, output_root = sandbox_dirs
    result = write_preview_export_package(
        _five_review_run(),
        input_root=input_root,
        output_root=output_root,
    )
    readme = (result.export_folder / "README_PREVIEW_EXPORT.md").read_text(encoding="utf-8")
    manifest = (result.export_folder / "manifest.json").read_text(encoding="utf-8")
    assert MSG_NO_SAAS_READY in readme
    assert MSG_NO_PRODUCTION_READY in readme
    assert result.claims_saas_ready is False
    assert result.claims_production_ready is False
    assert text_claims_forbidden_maturity(readme) is False
    payload = json.loads(manifest)
    assert payload.get("claims_saas_ready") is False
    assert payload.get("claims_production_ready") is False
    assert payload.get("preview_export") is True
    assert MSG_PREVIEW_EXPORT_SANDBOX_ONLY in manifest or "preview_export" in manifest


def test_ui_exposes_preview_export_cta_after_successful_result() -> None:
    state = UiV2State(processing_run_state=_five_review_run())
    assert preview_export_available(state.processing_run_state) is True
    assert workspace_exposes_preview_export_cta(state) is True
    assert PACKAGE_EXPORT_ACTION_LABEL == MSG_PREVIEW_EXPORT_CTA
    assert MSG_PREVIEW_EXPORT_CTA == "Preview-Export in Output-Ordner schreiben"
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "PACKAGE_EXPORT_ACTION_LABEL" in src
    assert "Preview-Export in Output-Ordner schreiben" in src
    assert "preview_export_available" in src
    assert "apply_workspace_preview_export" in src
    # Guard against reintroducing mock-style _PREVIEW_* constants in workspace.
    assert "_PREVIEW_" not in src
    module_src = PREVIEW_EXPORT_MODULE.read_text(encoding="utf-8")
    assert "Preview-Export in Output-Ordner schreiben" in module_src
    idle = UiV2State()
    assert workspace_exposes_preview_export_cta(idle) is False


def test_ui_does_not_expose_productive_final_export() -> None:
    state = UiV2State(processing_run_state=_five_review_run())
    assert workspace_exposes_productive_final_export(state) is False
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "PRODUCTIVE_FINAL_EXPORT_LABELS" in src
    assert "workspace_exposes_productive_final_export" in src
    # Forbidden productive labels may appear only inside PRODUCTIVE_FINAL_EXPORT_LABELS.
    tree = ast.parse(src)
    assigned_forbidden: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "PRODUCTIVE_FINAL_EXPORT_LABELS":
                    if isinstance(node.value, (ast.Tuple, ast.List)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                assigned_forbidden.add(elt.value)
    for label in PRODUCTIVE_FINAL_EXPORT_LABELS:
        assert label in assigned_forbidden
    # Live primary CTA must be the package export action, not productive final.
    assert "PACKAGE_EXPORT_ACTION_LABEL" in src


def test_workspace_apply_preview_export_updates_feedback(
    sandbox_dirs: tuple[Path, Path],
) -> None:
    input_root, output_root = sandbox_dirs
    state = UiV2State(processing_run_state=_five_review_run())
    state.set_workspace_input_folder(str(input_root))
    state.set_workspace_output_folder(str(output_root))
    result = apply_workspace_preview_export_package(state)
    assert result.ok is True
    assert "Preview-Export erstellt" in state.workspace_preview_export_feedback
    assert state.workspace_preview_export_feedback_error is False
    assert state.workspace_last_preview_export_folder
    assert Path(state.workspace_last_preview_export_folder).is_dir()


def test_track_a_protection_still_passes() -> None:
    # Lightweight mirror of Track-A import boundary for this change set.
    for path in (PREVIEW_EXPORT_MODULE, WORKSPACE, STATE_MODULE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("invoice_tool.gui")
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module not in PROCESSING_CORE
                assert not node.module.startswith("invoice_tool.gui")
    protected = [
        ROOT / "app_main.py",
        ROOT / "invoice_tool" / "gui.py",
        ROOT / "invoice_tool" / "run.py",
        ROOT / "invoice_tool" / "processing.py",
    ]
    for path in protected:
        assert path.is_file()


def test_controlled_desktop_paths_accepted_when_present() -> None:
    if not CONTROLLED_INPUT.is_dir() or not CONTROLLED_OUTPUT.is_dir():
        pytest.skip("controlled KI-Rechnungen-Test folders unavailable")
    pdfs = list(CONTROLLED_INPUT.glob("*.pdf"))
    if len(pdfs) < 1:
        pytest.skip("controlled input has no PDFs")
    before_input = _digest_tree(CONTROLLED_INPUT)
    before_output_count = sum(1 for _ in CONTROLLED_OUTPUT.rglob("*") if _.is_file())
    # Use a nested sandbox-named output under controlled output to avoid polluting
    # the PO folder permanently beyond the package itself (still under controlled root).
    result = write_preview_export_package(
        _five_review_run(),
        input_root=CONTROLLED_INPUT,
        output_root=CONTROLLED_OUTPUT,
    )
    assert result.ok is True
    assert result.export_folder is not None
    assert result.export_folder.is_relative_to(CONTROLLED_OUTPUT.resolve())
    assert _digest_tree(CONTROLLED_INPUT) == before_input
    assert sum(1 for _ in CONTROLLED_OUTPUT.rglob("*") if _.is_file()) > before_output_count
    # Cleanup the package created by this optional live check.
    if result.export_folder and result.export_folder.name.startswith(PREVIEW_EXPORT_FOLDER_PREFIX):
        shutil.rmtree(result.export_folder)


def test_modules_do_not_import_processing_core() -> None:
    for path in (PREVIEW_EXPORT_MODULE, WORKSPACE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in PROCESSING_CORE:
                raise AssertionError(f"{path.name} imports {node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in PROCESSING_CORE


def test_ui_copy_mentions_preview_export_safety() -> None:
    src = WORKSPACE.read_text(encoding="utf-8")
    assert "PACKAGE_EXPORT_HELPER" in src
    assert "schreibt nur ein Preview-Paket" in src
    assert "Originale bleiben unverändert" in src
    assert "keine finale Verarbeitung" in src
    assert "Produktiv gesperrt" in src
    assert "Preview Export" in src
    module_src = PREVIEW_EXPORT_MODULE.read_text(encoding="utf-8")
    assert "schreibt nur ein Preview-Paket" in module_src
    assert MSG_PREVIEW_EXPORT_TITLE in module_src
