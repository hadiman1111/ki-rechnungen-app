"""Bounded local draft list for generic UI-v2 SaaS profile drafts."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

from invoice_tool.saas_product_model import DEFAULT_SAAS_PROFILE_NAME, DEFAULT_SAAS_SCAN_MODEL_ID
from invoice_tool.ui_v2.saas_profile_draft_list_view import (
    DRAFT_LIST_TITLE,
    LOCALITY_LABEL,
    NO_CLOUD_HELP,
    SEPARATION_HELP,
    build_saas_draft_list_vm,
)
from invoice_tool.ui_v2.saas_profile_store import (
    DRAFT_ITEM_CORRUPTED,
    STATUS_CORRUPTED,
    STATUS_LOADED,
    STATUS_MISSING_BLANK,
    STATUS_SAVED,
    new_saas_profile_disk_store,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "invoice_tool" / "ui_v2" / "saas_profile_store.py"
LIST_VIEW = ROOT / "invoice_tool" / "ui_v2" / "saas_profile_draft_list_view.py"
PROFILES = ROOT / "invoice_tool" / "ui_v2" / "pages" / "profiles.py"
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


def test_create_draft_creates_generic_draft(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    result = store.create_draft(display_name="Lokaler Entwurf Alpha")
    assert result.ok is True
    assert result.status == STATUS_SAVED
    assert result.draft_id and result.draft_id.startswith("draft_")
    assert result.display_name == "Lokaler Entwurf Alpha"
    assert result.profile_draft is not None
    assert result.profile_draft.profile_name == DEFAULT_SAAS_PROFILE_NAME
    assert result.profile_draft.scan_model_id == DEFAULT_SAAS_SCAN_MODEL_ID
    assert result.path.is_file()
    assert result.path.parent == tmp_path


def test_list_drafts_shows_multiple(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    a = store.create_draft(display_name="Entwurf A")
    b = store.create_draft(display_name="Entwurf B")
    assert a.ok and b.ok
    items = store.list_drafts()
    assert len(items) >= 2
    names = {item.display_name for item in items}
    assert "Entwurf A" in names
    assert "Entwurf B" in names
    ids = {item.draft_id for item in items}
    assert a.draft_id in ids
    assert b.draft_id in ids


def test_load_draft_loads_correct_draft(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    first = store.create_draft(display_name="Erster")
    second = store.create_draft(display_name="Zweiter")
    assert first.ok and second.ok and first.draft_id and second.draft_id

    store.save_draft(
        first.draft_id,
        first.profile_draft,  # type: ignore[arg-type]
        None,
        display_name="Erster",
    )
    # Mutate second in memory and save
    assert second.profile_draft is not None
    second.profile_draft.profile_name = "Mandant Zweiter"
    second.profile_draft.destination_folder = "/tmp/saas-zweiter"
    assert store.save_draft(second.draft_id, second.profile_draft, None).ok

    loaded = store.load_draft(second.draft_id)
    assert loaded.ok is True
    assert loaded.status == STATUS_LOADED
    assert loaded.draft_id == second.draft_id
    assert loaded.profile_draft is not None
    assert loaded.profile_draft.profile_name == "Mandant Zweiter"
    assert loaded.profile_draft.destination_folder == "/tmp/saas-zweiter"

    other = store.load_draft(first.draft_id)
    assert other.ok is True
    assert other.profile_draft is not None
    assert other.profile_draft.profile_name != "Mandant Zweiter"


def test_save_draft_updates_only_selected(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    a = store.create_draft(display_name="A")
    b = store.create_draft(display_name="B")
    assert a.draft_id and b.draft_id and a.profile_draft and b.profile_draft

    a.profile_draft.notes = "nur-a"
    assert store.save_draft(a.draft_id, a.profile_draft, None).ok is True

    loaded_b = store.load_draft(b.draft_id)
    assert loaded_b.ok and loaded_b.profile_draft is not None
    assert loaded_b.profile_draft.notes != "nur-a"

    loaded_a = store.load_draft(a.draft_id)
    assert loaded_a.ok and loaded_a.profile_draft is not None
    assert loaded_a.profile_draft.notes == "nur-a"


def test_corrupted_draft_listed_and_load_safe(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    good = store.create_draft(display_name="Gut")
    assert good.ok and good.draft_id
    broken_path = tmp_path / "draft_brokenbad01.json"
    broken_path.write_text("{ not json", encoding="utf-8")

    items = store.list_drafts()
    broken = next(item for item in items if item.draft_id == "draft_brokenbad01")
    assert broken.status == DRAFT_ITEM_CORRUPTED
    assert broken.error

    prior_name = "Vorheriger Entwurf"
    state = UiV2State()
    state.configure_saas_disk_store(tmp_path)
    state.saas_draft_store.begin_blank_profile()
    state.saas_draft_store.update_profile_field("profile_name", prior_name)

    result = state.load_saas_draft("draft_brokenbad01")
    assert result.ok is False
    assert result.status == STATUS_CORRUPTED
    assert state.saas_draft_store.profile_draft is not None
    assert state.saas_draft_store.profile_draft.profile_name == prior_name


def test_missing_draft_file_handled_safely(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    result = store.load_draft("draft_doesnotexist")
    assert result.ok is False
    assert result.status == STATUS_MISSING_BLANK
    assert result.profile_draft is None
    assert "nicht gefunden" in (result.error or "").lower()

    state = UiV2State()
    state.configure_saas_disk_store(tmp_path)
    state.saas_draft_store.begin_blank_profile()
    state.saas_draft_store.update_profile_field("profile_name", "Bleibt")
    loaded = state.load_saas_draft("draft_doesnotexist")
    assert loaded.ok is False
    assert state.saas_draft_store.profile_draft is not None
    assert state.saas_draft_store.profile_draft.profile_name == "Bleibt"


def test_saved_json_has_no_private_defaults(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    result = store.create_draft()
    assert result.ok and result.path.is_file()
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    blob = json.dumps(payload, ensure_ascii=False)
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    assert payload["cloud"] is False
    assert payload["persistence"] == "local_disk_only"
    assert payload["draft_id"]
    assert payload["display_name"]
    assert "created_at" in payload
    assert "updated_at" in payload


def test_store_uses_injected_tmp_path(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path)
    assert store.drafts_root == tmp_path
    created = store.create_draft(display_name="Isoliert")
    assert created.ok
    assert created.path.parent == tmp_path
    assert str(created.path).startswith(str(tmp_path))
    assert "KI-Rechnungen/profiles" not in str(created.path)
    support_root = Path.home() / "Library" / "Application Support" / "KI-Rechnungen"
    assert not str(created.path).startswith(str(support_root))


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
    assert state.create_saas_draft(display_name="Guard").ok
    assert state.save_saas_drafts_to_disk().ok

    assert PROFILE_LOCAL.read_bytes() == before
    assert PROFILE_LOCAL.stat().st_mtime_ns == before_mtime
    if app_before is not None and APP_SUPPORT_PROFILE.is_file():
        assert APP_SUPPORT_PROFILE.read_bytes() == app_before
        assert APP_SUPPORT_PROFILE.stat().st_mtime_ns == app_mtime


def test_ui_texts_separate_saas_from_internal_and_no_cloud() -> None:
    vm = build_saas_draft_list_vm(())
    texts = " ".join(vm.all_ui_texts())
    assert DRAFT_LIST_TITLE in texts
    assert SEPARATION_HELP in texts
    assert "nicht das interne Arbeitsprofil" in texts
    assert NO_CLOUD_HELP in texts
    assert "Cloud-Synchronisierung" in texts
    assert "Cloud-Sync aktiv" not in texts
    assert "Mandantenbackend" not in texts
    assert LOCALITY_LABEL in texts
    for marker in PRIVATE_MARKERS:
        assert marker not in texts, marker


def test_state_create_select_load_save_flow(tmp_path: Path) -> None:
    state = UiV2State()
    state.configure_saas_disk_store(tmp_path)
    created = state.create_saas_draft(display_name="Flow Eins")
    assert created.ok
    assert state.saas_selected_draft_id == created.draft_id

    second = state.create_saas_draft(display_name="Flow Zwei")
    assert second.ok and second.draft_id
    state.saas_draft_store.update_profile_field("destination_folder", "/tmp/flow-zwei")
    assert state.save_saas_drafts_to_disk().ok

    state.select_saas_draft(created.draft_id)
    loaded = state.load_saas_draft()
    assert loaded.ok
    assert state.saas_draft_store.profile_draft is not None
    assert state.saas_draft_store.profile_draft.destination_folder != "/tmp/flow-zwei"

    list_vm = state.saas_draft_list_vm()
    assert len(list_vm.rows) >= 2
    assert any(row.display_name == "Flow Eins" for row in list_vm.rows)


def test_pages_wire_draft_list() -> None:
    profiles = PROFILES.read_text(encoding="utf-8")
    configs = (ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py").read_text(
        encoding="utf-8"
    )
    assert "build_saas_draft_list_panel" in profiles
    assert "Lokale SaaS-Entwürfe" in LIST_VIEW.read_text(encoding="utf-8")
    assert "create_saas_draft" in profiles
    assert "build_saas_draft_list_panel" in configs


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

    for module in (STORE, LIST_VIEW):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert not any("internal_launcher" in name for name in imported)
