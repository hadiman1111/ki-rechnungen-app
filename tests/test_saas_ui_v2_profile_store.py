"""Bounded local disk persistence for generic UI-v2 SaaS profile drafts."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

from invoice_tool.saas_product_model import (
    DEFAULT_SAAS_FILENAME_PATTERN,
    DEFAULT_SAAS_PROFILE_NAME,
    DEFAULT_SAAS_SCAN_MODEL_ID,
)
from invoice_tool.ui_v2.saas_profile_state import SaasConfigurationDraft, SaasProfileDraft
from invoice_tool.ui_v2.saas_profile_store import (
    FORBIDDEN_WRITE_BASENAMES,
    SAAS_UI_V2_SUPPORT_DIR_NAME,
    STATUS_CORRUPTED,
    STATUS_LOADED,
    STATUS_MISSING_BLANK,
    STATUS_PRIVATE_DEFAULTS,
    STATUS_SAVED,
    SaasProfileDiskStore,
    default_saas_ui_v2_draft_path,
    new_saas_profile_disk_store,
)
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "invoice_tool" / "ui_v2" / "saas_profile_store.py"
PROFILE_LOCAL = ROOT / "profile_config.local.json"

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


def _blank_draft(**overrides) -> SaasProfileDraft:
    draft = SaasProfileDraft(
        profile_name=DEFAULT_SAAS_PROFILE_NAME,
        scan_model_id=DEFAULT_SAAS_SCAN_MODEL_ID,
        document_type="Rechnungen",
        matching_conditions_text="",
        destination_category="",
        destination_folder="",
        filename_pattern=DEFAULT_SAAS_FILENAME_PATTERN,
        review_rule="unclear_on_no_match",
        payment_hint="",
        review_unclear_folder="unklar",
        notes="",
        is_new=True,
        configurations=[],
    )
    for key, value in overrides.items():
        setattr(draft, key, value)
    return draft


def test_blank_draft_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "saas_profile_draft.json"
    store = new_saas_profile_disk_store(path)
    draft = _blank_draft()

    saved = store.save(draft)
    assert saved.ok is True
    assert saved.status == STATUS_SAVED
    assert path.is_file()
    assert saved.locally_persisted is True

    loaded = store.load()
    assert loaded.ok is True
    assert loaded.status == STATUS_LOADED
    assert loaded.profile_draft is not None
    assert loaded.profile_draft.profile_name == DEFAULT_SAAS_PROFILE_NAME
    assert loaded.profile_draft.scan_model_id == DEFAULT_SAAS_SCAN_MODEL_ID
    assert loaded.profile_draft.filename_pattern == DEFAULT_SAAS_FILENAME_PATTERN
    assert loaded.profile_draft.destination_folder == ""
    assert loaded.profile_draft.payment_hint == ""


def test_changed_fields_survive_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "draft.json"
    store = SaasProfileDiskStore.for_path(path)
    draft = _blank_draft(
        profile_name="Mandant Beta",
        scan_model_id="angebote",
        document_type="Angebote",
        matching_conditions_text="lieferant ist Muster AG",
        destination_category="einkauf",
        destination_folder="/tmp/saas-ziel",
        filename_pattern="{invoice_date}_{supplier}.pdf",
        payment_hint="Konto 4400",
        notes="lokaler Entwurf",
    )
    config = SaasConfigurationDraft(
        name="Lieferant Hauptkonto",
        active=True,
        document_type="Angebote",
        matching_conditions_text="lieferant ist Muster AG",
        destination_category="einkauf",
        destination_folder="/tmp/saas-ziel",
        filename_pattern="{invoice_date}_{supplier}.pdf",
        review_rule="unclear_on_no_match",
        payment_hint="Konto 4400",
        is_new=True,
    )

    assert store.save(draft, config).ok is True
    loaded = store.load()
    assert loaded.ok is True
    assert loaded.profile_draft is not None
    assert loaded.profile_draft.profile_name == "Mandant Beta"
    assert loaded.profile_draft.scan_model_id == "angebote"
    assert loaded.profile_draft.destination_folder == "/tmp/saas-ziel"
    assert loaded.profile_draft.payment_hint == "Konto 4400"
    assert loaded.configuration_draft is not None
    assert loaded.configuration_draft.name == "Lieferant Hauptkonto"
    assert loaded.configuration_draft.destination_folder == "/tmp/saas-ziel"


def test_no_private_defaults_in_saved_json(tmp_path: Path) -> None:
    path = tmp_path / "draft.json"
    store = new_saas_profile_disk_store(path)
    assert store.save(_blank_draft()).ok is True

    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    blob = json.dumps(payload, ensure_ascii=False)
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    assert payload["cloud"] is False
    assert payload["persistence"] == "local_disk_only"
    assert payload["profile"]["destination_category"] == ""
    assert payload["profile"]["payment_hint"] == ""


def test_private_defaults_are_rejected_on_save(tmp_path: Path) -> None:
    path = tmp_path / "draft.json"
    store = new_saas_profile_disk_store(path)
    dirty = _blank_draft(profile_name="SOMAA Arbeitsprofil", payment_hint="AMEX-1005")
    result = store.save(dirty)
    assert result.ok is False
    assert result.status == STATUS_PRIVATE_DEFAULTS
    assert not path.exists()


def test_missing_file_returns_generic_blank(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"
    store = new_saas_profile_disk_store(path)
    result = store.load()
    assert result.ok is True
    assert result.status == STATUS_MISSING_BLANK
    assert result.locally_persisted is False
    assert result.persistence_label == "Nicht gespeichert"
    assert result.profile_draft is not None
    assert result.profile_draft.profile_name == DEFAULT_SAAS_PROFILE_NAME
    assert result.profile_draft.scan_model_id == DEFAULT_SAAS_SCAN_MODEL_ID


def test_corrupted_json_returns_safe_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{ not valid json", encoding="utf-8")
    store = new_saas_profile_disk_store(path)
    result = store.load()
    assert result.ok is False
    assert result.status == STATUS_CORRUPTED
    assert result.profile_draft is None
    assert result.error is not None
    assert "JSON" in result.error or "Ungültig" in result.error


def test_store_uses_injected_tmp_path(tmp_path: Path) -> None:
    path = tmp_path / "isolated" / "saas_profile_draft.json"
    store = new_saas_profile_disk_store(path)
    assert store.store_path == path
    assert store.save(_blank_draft()).ok is True
    assert path.is_file()
    # Must not write into the default Application Support draft path during tests.
    default_path = default_saas_ui_v2_draft_path()
    assert path != default_path
    assert not str(path).startswith(str(Path.home() / "Library" / "Application Support" / "KI-Rechnungen" / "profiles"))


def test_store_does_not_modify_profile_config_local(tmp_path: Path) -> None:
    assert PROFILE_LOCAL.is_file()
    before = PROFILE_LOCAL.read_bytes()
    before_mtime = PROFILE_LOCAL.stat().st_mtime_ns

    path = tmp_path / "saas_profile_draft.json"
    store = new_saas_profile_disk_store(path)
    assert store.save(_blank_draft(profile_name="Mandant Gamma")).ok is True
    assert store.load().ok is True

    after = PROFILE_LOCAL.read_bytes()
    after_mtime = PROFILE_LOCAL.stat().st_mtime_ns
    assert after == before
    assert after_mtime == before_mtime
    assert "profile_config.local.json" in FORBIDDEN_WRITE_BASENAMES


def test_default_path_is_isolated_from_hadi_working_profile() -> None:
    path = default_saas_ui_v2_draft_path()
    assert SAAS_UI_V2_SUPPORT_DIR_NAME in path.parts
    assert "KI-Rechnungen-SaaS-UI-v2" in str(path)
    assert path.name == "saas_profile_draft.json"
    # Not the mutable Hadi/SOMAA profile root.
    assert path.name != "profile_config.local.json"
    assert "profiles" not in path.parts or SAAS_UI_V2_SUPPORT_DIR_NAME in path.parts
    assert path.parent.name == "drafts"


def test_ui_v2_state_save_load_hooks(tmp_path: Path) -> None:
    state = UiV2State()
    state.configure_saas_disk_store(tmp_path / "state_draft.json")
    draft = state.saas_draft_store.begin_blank_profile()
    state.saas_draft_store.update_profile_field("profile_name", "Mandant Delta")
    state.saas_draft_store.update_profile_field("destination_folder", "/tmp/delta")

    saved = state.save_saas_drafts_to_disk()
    assert saved.ok is True
    assert state.saas_disk_persistence_label == "Lokal gespeichert"

    state.saas_draft_store.reset()
    assert state.saas_draft_store.profile_draft is None
    loaded = state.load_saas_drafts_from_disk()
    assert loaded.ok is True
    assert state.saas_draft_store.profile_draft is not None
    assert state.saas_draft_store.profile_draft.profile_name == "Mandant Delta"
    assert state.saas_draft_store.profile_draft.destination_folder == "/tmp/delta"
    assert state.saas_disk_persistence_label == "Lokal geladen"
    assert draft is not state.saas_draft_store.profile_draft


def test_no_private_defaults_in_store_module_defaults() -> None:
    src = STORE.read_text(encoding="utf-8")
    # Documentation may mention markers; value-bearing defaults must not embed them.
    assert 'profile_name="SOMAA"' not in src
    assert 'destination_category="ep"' not in src
    assert "AMEX-1005" not in src
    assert "97368" not in src
    assert "Bismarck" not in src
    assert "/Users/hadi_neu/Desktop/RECHNUNGEN" not in src


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

    tree = ast.parse(STORE.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("internal_launcher" in name for name in imported)


def test_profiles_page_exposes_local_persistence_status() -> None:
    profiles = (ROOT / "invoice_tool" / "ui_v2" / "pages" / "profiles.py").read_text(encoding="utf-8")
    configs = (ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py").read_text(encoding="utf-8")
    assert "saas_persistence_status_vm" in profiles
    assert "build_saas_persistence_status_panel" in profiles
    assert "save_saas_drafts_to_disk" in profiles
    assert "load_saas_drafts_from_disk" in profiles
    assert "Cloud-Synchronisierung" in profiles or "keine Cloud" in profiles
    assert "saas_persistence_status_vm" in configs
    assert "build_saas_persistence_status_panel" in configs
