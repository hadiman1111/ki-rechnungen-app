"""UX hardening for local SaaS UI-v2 profile draft persistence status."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

from invoice_tool.ui_v2.saas_profile_persistence_view import (
    NO_CLOUD_HELP,
    SEPARATION_HELP,
    UX_STATUS_CORRUPTED,
    UX_STATUS_LOADED,
    UX_STATUS_SAVED,
    UX_STATUS_UNSAVED,
    build_blank_saas_persistence_status_vm,
    build_saas_persistence_status_vm,
    find_forbidden_cloud_claim_violations,
    find_private_persistence_ux_violations,
)
from invoice_tool.ui_v2.saas_profile_store import (
    STATUS_CORRUPTED,
    STATUS_LOADED,
    STATUS_MISSING_BLANK,
    STATUS_SAVED,
    new_saas_profile_disk_store,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "invoice_tool" / "ui_v2" / "saas_profile_persistence_view.py"
PROFILES = ROOT / "invoice_tool" / "ui_v2" / "pages" / "profiles.py"
CONFIGS = ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py"

INTERNAL_LAUNCHER_PATHS = (
    ROOT / "app_internal_launcher.py",
    ROOT / "invoice_tool" / "internal_launcher",
    ROOT / "scripts" / "macos_dock_launcher.c",
    ROOT / "scripts" / "macos_fletview_bootstrap.c",
    ROOT / "scripts" / "build_macos_dock_app.sh",
)

PRIVATE_MARKERS = (
    "SOMAA",
    "Hadi",
    "AMEX-1005",
    "EP",
    "Bismarck",
    "97368",
    "DE189",
    "voba",
)


def test_blank_draft_status_is_unsaved() -> None:
    vm = build_blank_saas_persistence_status_vm()
    assert vm.status_label == UX_STATUS_UNSAVED
    assert vm.store_status == STATUS_MISSING_BLANK
    assert vm.is_error is False
    assert vm.locally_persisted is False


def test_saved_status_after_save(tmp_path: Path) -> None:
    state = UiV2State()
    state.configure_saas_disk_store(tmp_path / "draft.json")
    state.saas_draft_store.begin_blank_profile()
    result = state.save_saas_drafts_to_disk()
    assert result.ok is True
    assert result.status == STATUS_SAVED

    vm = state.saas_persistence_status_vm()
    assert vm.status_label == UX_STATUS_SAVED
    assert vm.locally_persisted is True
    assert state.saas_disk_last_saved_at is not None
    assert "lokal gespeichert" in vm.timestamp_text.lower()


def test_loaded_status_after_load(tmp_path: Path) -> None:
    path = tmp_path / "draft.json"
    store = new_saas_profile_disk_store(path)
    state = UiV2State()
    state.configure_saas_disk_store(path)
    state.saas_draft_store.begin_blank_profile()
    assert state.save_saas_drafts_to_disk().ok is True

    state.saas_draft_store.reset()
    loaded = state.load_saas_drafts_from_disk()
    assert loaded.ok is True
    assert loaded.status == STATUS_LOADED

    vm = state.saas_persistence_status_vm()
    assert vm.status_label == UX_STATUS_LOADED
    assert "lokal geladen" in vm.timestamp_text.lower()
    assert store.load().ok is True


def test_corrupted_load_status(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{ not valid json", encoding="utf-8")
    state = UiV2State()
    state.configure_saas_disk_store(path)
    result = state.load_saas_drafts_from_disk()
    assert result.ok is False
    assert result.status == STATUS_CORRUPTED

    vm = state.saas_persistence_status_vm()
    assert vm.status_label == UX_STATUS_CORRUPTED
    assert vm.is_error is True
    assert vm.error_text
    assert "beschädigt" in vm.error_text.lower() or "JSON" in vm.error_text


def test_help_text_separates_saas_draft_from_internal_profile() -> None:
    vm = build_saas_persistence_status_vm(store_status=STATUS_SAVED, last_saved_at="18.07.2026 10:00:00")
    texts = " ".join(vm.all_ui_texts())
    assert SEPARATION_HELP in texts
    assert "SaaS-/UI-v2-Variante" in texts
    assert "nicht das interne Arbeitsprofil" in texts
    assert "interne Arbeitsprofil" in texts
    assert vm.scope_label == "SaaS-Profilentwurf (lokal)"


def test_no_private_defaults_in_persistence_ux_copy() -> None:
    cases = [
        build_blank_saas_persistence_status_vm(),
        build_saas_persistence_status_vm(
            store_status=STATUS_SAVED,
            last_saved_at="18.07.2026 10:00:00",
        ),
        build_saas_persistence_status_vm(
            store_status=STATUS_LOADED,
            last_loaded_at="18.07.2026 11:00:00",
        ),
        build_saas_persistence_status_vm(
            store_status=STATUS_CORRUPTED,
            last_error="Ungültiges JSON: Expecting property name",
        ),
    ]
    for vm in cases:
        violations = find_private_persistence_ux_violations(vm.all_ui_texts())
        assert violations == [], (vm.status_label, violations)
        joined = " ".join(vm.all_ui_texts())
        for marker in PRIVATE_MARKERS:
            assert marker not in joined, marker


def test_no_cloud_sync_promise_in_ux_copy() -> None:
    vm = build_saas_persistence_status_vm(store_status=STATUS_SAVED, last_saved_at="18.07.2026 10:00:00")
    texts = vm.all_ui_texts()
    assert NO_CLOUD_HELP in texts
    assert find_forbidden_cloud_claim_violations(texts) == []
    joined = " ".join(texts).lower()
    assert "noch keine cloud-synchronisierung" in joined
    assert "cloud-sync aktiv" not in joined
    assert "in der cloud gespeichert" not in joined
    assert "mandantenbackend" not in joined


def test_vm_from_store_result_corrupted() -> None:
    result_path = Path("/tmp/does-not-matter.json")
    from invoice_tool.ui_v2.saas_profile_store import SaasProfileStoreResult

    result = SaasProfileStoreResult(
        ok=False,
        status=STATUS_CORRUPTED,
        path=result_path,
        error="Ungültiges JSON: Expecting value",
    )
    vm = build_saas_persistence_status_vm(store_result=result)
    assert vm.status_label == UX_STATUS_CORRUPTED
    assert vm.is_error is True
    assert "Ungültiges JSON" in vm.error_text


def test_pages_wire_persistence_status_panel() -> None:
    profiles = PROFILES.read_text(encoding="utf-8")
    configs = CONFIGS.read_text(encoding="utf-8")
    assert "build_saas_persistence_status_panel" in profiles
    assert "saas_persistence_status_vm" in profiles
    assert "build_saas_persistence_status_panel" in configs
    assert "saas_persistence_status_vm" in configs
    view_src = VIEW.read_text(encoding="utf-8")
    assert "interne Arbeitsprofil" in view_src
    assert "Noch keine Cloud-Synchronisierung" in view_src


def test_no_private_defaults_in_view_module_source() -> None:
    src = VIEW.read_text(encoding="utf-8")
    # Guard list may mention markers; value-bearing UX constants must not embed tenants.
    tree = ast.parse(src)
    assigned: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {
                    "SEPARATION_HELP",
                    "NO_CLOUD_HELP",
                    "SCOPE_LABEL",
                    "UX_STATUS_UNSAVED",
                    "UX_STATUS_SAVED",
                    "UX_STATUS_LOADED",
                    "UX_STATUS_CORRUPTED",
                }:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        assigned.append(node.value.value)
    blob = " ".join(assigned)
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker


def test_internal_launcher_files_not_in_changeset() -> None:
    for path in INTERNAL_LAUNCHER_PATHS:
        assert path.exists(), path

    result = subprocess.run(
        ["git", "status", "--short", "--"]
        + [str(path.relative_to(ROOT)) for path in INTERNAL_LAUNCHER_PATHS],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "", result.stdout

    tree = ast.parse(VIEW.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("internal_launcher" in name for name in imported)


def test_saved_json_still_local_disk_only(tmp_path: Path) -> None:
    state = UiV2State()
    path = tmp_path / "draft.json"
    state.configure_saas_disk_store(path)
    state.saas_draft_store.begin_blank_profile()
    assert state.save_saas_drafts_to_disk().ok is True
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["cloud"] is False
    assert payload["persistence"] == "local_disk_only"
