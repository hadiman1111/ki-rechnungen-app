"""Bounded rename/delete for generic UI-v2 SaaS profile drafts."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

from invoice_tool.ui_v2.saas_profile_draft_list_view import (
    ACTION_DELETE,
    ACTION_RENAME,
    DELETE_WARN,
    NO_CLOUD_HELP,
    SEPARATION_HELP,
    build_saas_draft_list_vm,
)
from invoice_tool.ui_v2.saas_profile_store import (
    DRAFT_ITEM_CORRUPTED,
    STATUS_DELETED,
    STATUS_DELETE_NEEDS_CONFIRM,
    STATUS_MISSING_BLANK,
    STATUS_RENAMED,
    STATUS_VALIDATION_ERROR,
    new_saas_profile_disk_store,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "invoice_tool" / "ui_v2" / "saas_profile_store.py"
LIST_VIEW = ROOT / "invoice_tool" / "ui_v2" / "saas_profile_draft_list_view.py"
STATE = ROOT / "invoice_tool" / "ui_v2" / "state.py"
PROFILES = ROOT / "invoice_tool" / "ui_v2" / "pages" / "profiles.py"
CONFIGS = ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py"
PROFILE_LOCAL = ROOT / "profile_config.local.json"
APP_SUPPORT_PROFILE = (
    Path.home() / "Library" / "Application Support" / "KI-Rechnungen" / "profile_config.local.json"
)

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


def test_rename_draft_changes_display_name_not_id(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    created = store.create_draft(display_name="Altname")
    assert created.ok and created.draft_id
    original_id = created.draft_id
    original_path = created.path

    renamed = store.rename_draft(original_id, "Neuname")
    assert renamed.ok is True
    assert renamed.status == STATUS_RENAMED
    assert renamed.draft_id == original_id
    assert renamed.display_name == "Neuname"
    assert renamed.path == original_path
    assert renamed.path.is_file()

    payload = json.loads(renamed.path.read_text(encoding="utf-8"))
    assert payload["draft_id"] == original_id
    assert payload["display_name"] == "Neuname"

    items = store.list_drafts()
    match = next(item for item in items if item.draft_id == original_id)
    assert match.display_name == "Neuname"


def test_rename_draft_rejects_empty_name(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    created = store.create_draft(display_name="Bleibt")
    assert created.ok and created.draft_id

    result = store.rename_draft(created.draft_id, "   ")
    assert result.ok is False
    assert result.status == STATUS_VALIDATION_ERROR
    assert "leer" in (result.error or "").lower()

    loaded = store.load_draft(created.draft_id)
    assert loaded.ok
    assert loaded.display_name == "Bleibt"


def test_rename_draft_strips_control_characters(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    created = store.create_draft(display_name="Roh")
    assert created.ok and created.draft_id

    result = store.rename_draft(created.draft_id, "Sauber\x00Name\nMit\tSteuer")
    assert result.ok is True
    assert result.display_name == "Sauber Name Mit Steuer"
    assert "\x00" not in (result.display_name or "")
    assert "\n" not in (result.display_name or "")
    assert "\t" not in (result.display_name or "")


def test_delete_draft_removes_only_selected(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    a = store.create_draft(display_name="A")
    b = store.create_draft(display_name="B")
    assert a.ok and b.ok and a.draft_id and b.draft_id
    a_path = a.path
    b_path = b.path

    deleted = store.delete_draft(a.draft_id)
    assert deleted.ok is True
    assert deleted.status == STATUS_DELETED
    assert deleted.draft_id == a.draft_id
    assert not a_path.is_file()
    assert b_path.is_file()

    items = store.list_drafts()
    ids = {item.draft_id for item in items}
    assert a.draft_id not in ids
    assert b.draft_id in ids


def test_delete_draft_leaves_others_unchanged(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    a = store.create_draft(display_name="Keep-A")
    b = store.create_draft(display_name="Keep-B")
    c = store.create_draft(display_name="Remove-C")
    assert a.ok and b.ok and c.ok and c.draft_id
    assert a.profile_draft is not None
    a.profile_draft.notes = "notes-a"
    assert store.save_draft(a.draft_id, a.profile_draft, None).ok  # type: ignore[arg-type]

    assert store.delete_draft(c.draft_id).ok
    loaded_a = store.load_draft(a.draft_id)  # type: ignore[arg-type]
    loaded_b = store.load_draft(b.draft_id)  # type: ignore[arg-type]
    assert loaded_a.ok and loaded_a.profile_draft is not None
    assert loaded_a.profile_draft.notes == "notes-a"
    assert loaded_a.display_name == "Keep-A"
    assert loaded_b.ok and loaded_b.display_name == "Keep-B"


def test_delete_missing_draft_safe_status(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    result = store.delete_draft("draft_doesnotexist")
    assert result.ok is False
    assert result.status == STATUS_MISSING_BLANK
    assert "nicht gefunden" in (result.error or "").lower()


def test_corrupted_draft_deletable(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    good = store.create_draft(display_name="Gut")
    assert good.ok
    broken_path = tmp_path / "draft_brokenren01.json"
    broken_path.write_text("{ not json", encoding="utf-8")

    items = store.list_drafts()
    broken = next(item for item in items if item.draft_id == "draft_brokenren01")
    assert broken.status == DRAFT_ITEM_CORRUPTED

    rename = store.rename_draft("draft_brokenren01", "Neuer Name")
    assert rename.ok is False

    deleted = store.delete_draft("draft_brokenren01")
    assert deleted.ok is True
    assert deleted.status == STATUS_DELETED
    assert not broken_path.exists()
    assert good.path.is_file()


def test_state_selected_draft_safe_after_delete(tmp_path: Path) -> None:
    state = UiV2State()
    state.configure_saas_disk_store(tmp_path)
    first = state.create_saas_draft(display_name="Eins")
    second = state.create_saas_draft(display_name="Zwei")
    assert first.ok and second.ok and second.draft_id
    assert state.saas_selected_draft_id == second.draft_id

    # Active draft: first click arms confirm, does not delete.
    pending = state.delete_saas_draft(confirmed=False)
    assert pending.ok is False
    assert pending.status == STATUS_DELETE_NEEDS_CONFIRM
    assert state.saas_delete_confirm_pending is True
    assert state.saas_selected_draft_id == second.draft_id
    assert second.path.is_file()

    # Second click deletes.
    deleted = state.delete_saas_draft(confirmed=True)
    assert deleted.ok is True
    assert deleted.status == STATUS_DELETED
    assert not second.path.is_file()
    assert state.saas_selected_draft_id == first.draft_id
    assert state.saas_draft_store.profile_draft is None
    assert state.saas_delete_confirm_pending is False


def test_saved_json_has_no_private_defaults_after_rename(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    created = store.create_draft(display_name="Generic")
    assert created.ok and created.draft_id
    renamed = store.rename_draft(created.draft_id, "Lokaler Entwurf X")
    assert renamed.ok
    blob = renamed.path.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    payload = json.loads(blob)
    assert payload["cloud"] is False
    assert payload["persistence"] == "local_disk_only"


def test_store_uses_injected_tmp_path(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    created = store.create_draft(display_name="Pfad")
    assert created.ok and created.draft_id
    renamed = store.rename_draft(created.draft_id, "Pfad Neu")
    assert renamed.ok
    assert str(renamed.path).startswith(str(tmp_path))
    deleted = store.delete_draft(created.draft_id)
    assert deleted.ok
    assert str(deleted.path).startswith(str(tmp_path))
    support_root = Path.home() / "Library" / "Application Support" / "KI-Rechnungen"
    assert not str(renamed.path).startswith(str(support_root))


def test_profile_config_local_untouched(tmp_path: Path) -> None:
    assert PROFILE_LOCAL.is_file()
    before = PROFILE_LOCAL.read_bytes()
    before_mtime = PROFILE_LOCAL.stat().st_mtime_ns
    if APP_SUPPORT_PROFILE.is_file():
        app_before = APP_SUPPORT_PROFILE.read_bytes()
        app_mtime = APP_SUPPORT_PROFILE.stat().st_mtime_ns
    else:
        app_before = None
        app_mtime = None

    state = UiV2State()
    state.configure_saas_disk_store(tmp_path)
    created = state.create_saas_draft(display_name="Guard")
    assert created.ok
    assert state.rename_saas_draft("Guard Neu").ok
    # Two-step delete of active draft.
    assert state.delete_saas_draft(confirmed=False).status == STATUS_DELETE_NEEDS_CONFIRM
    assert state.delete_saas_draft(confirmed=True).ok

    assert PROFILE_LOCAL.read_bytes() == before
    assert PROFILE_LOCAL.stat().st_mtime_ns == before_mtime
    if app_before is not None and APP_SUPPORT_PROFILE.is_file():
        assert APP_SUPPORT_PROFILE.read_bytes() == app_before
        assert APP_SUPPORT_PROFILE.stat().st_mtime_ns == app_mtime


def test_ui_texts_separate_saas_and_no_cloud() -> None:
    vm = build_saas_draft_list_vm(())
    texts = " ".join(vm.all_ui_texts())
    assert ACTION_RENAME in texts
    assert ACTION_DELETE in texts
    assert DELETE_WARN in texts
    assert SEPARATION_HELP in texts
    assert "nicht das interne Arbeitsprofil" in texts
    assert NO_CLOUD_HELP in texts
    assert "Nicht Cloud-synchronisiert" in texts
    assert "SaaS-Profilentwurf" not in texts
    assert "Lokale SaaS-Entwürfe" not in texts
    assert "Cloud-Sync aktiv" not in texts
    assert "Mandantenbackend" not in texts
    for marker in PRIVATE_MARKERS:
        assert marker not in texts, marker


def test_pages_wire_rename_delete() -> None:
    profiles = PROFILES.read_text(encoding="utf-8")
    configs = CONFIGS.read_text(encoding="utf-8")
    list_src = LIST_VIEW.read_text(encoding="utf-8")
    state_src = STATE.read_text(encoding="utf-8")
    assert "on_rename" in profiles
    assert "on_delete" in profiles
    assert "rename_saas_draft" in profiles
    assert "delete_saas_draft" in profiles
    assert "on_rename" in configs
    assert "on_delete" in configs
    assert "rename_saas_draft" in state_src
    assert "delete_saas_draft" in state_src
    assert "Entwurf umbenennen" in list_src
    assert "Entwurf löschen" in list_src


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

    for module in (STORE, LIST_VIEW, STATE):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert not any("internal_launcher" in name for name in imported)
