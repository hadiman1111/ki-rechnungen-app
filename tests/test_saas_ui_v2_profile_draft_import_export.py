"""Bounded local import/export for generic UI-v2 SaaS profile drafts."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

from invoice_tool.ui_v2.saas_profile_draft_list_view import (
    ACTION_EXPORT,
    ACTION_IMPORT,
    IMPORT_EXPORT_HELP,
    NO_CLOUD_HELP,
    SEPARATION_HELP,
    build_saas_draft_list_vm,
)
from invoice_tool.ui_v2.saas_profile_store import (
    EXPORT_KIND,
    SCHEMA_VERSION,
    STATUS_CORRUPTED,
    STATUS_EXPORTED,
    STATUS_IMPORTED,
    STATUS_PRIVATE_DEFAULTS,
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
    "Architektur",
    "97368",
    "DE189",
    "voba",
)


def test_export_draft_writes_valid_envelope(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    created = store.create_draft(display_name="Export-Quelle")
    assert created.ok and created.draft_id
    export_path = tmp_path / "out" / "draft_export.json"

    result = store.export_draft(created.draft_id, export_path)
    assert result.ok is True
    assert result.status == STATUS_EXPORTED
    assert export_path.is_file()

    envelope = json.loads(export_path.read_text(encoding="utf-8"))
    assert envelope["schema_version"] == SCHEMA_VERSION
    assert envelope["kind"] == EXPORT_KIND
    assert envelope["cloud"] is False
    assert "exported_at" in envelope
    assert isinstance(envelope["draft"], dict)
    assert isinstance(envelope["draft"]["profile"], dict)
    assert envelope["draft"]["display_name"] == "Export-Quelle"


def test_export_draft_cloud_false_and_no_private_defaults(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    created = store.create_draft(display_name="Generic Export")
    assert created.ok and created.draft_id
    export_path = tmp_path / "export.json"
    assert store.export_draft(created.draft_id, export_path).ok

    blob = export_path.read_text(encoding="utf-8")
    payload = json.loads(blob)
    assert payload["cloud"] is False
    assert payload.get("persistence") == "local_export_only"
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker


def test_export_draft_does_not_include_invoice_files_or_internal_profiles(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    created = store.create_draft(display_name="Nur Meta")
    assert created.ok and created.draft_id
    export_path = tmp_path / "meta_export.json"
    assert store.export_draft(created.draft_id, export_path).ok

    envelope = json.loads(export_path.read_text(encoding="utf-8"))
    blob = json.dumps(envelope)
    # Filename patterns may mention ".pdf"; real invoice payloads / internal profiles must not.
    assert "profile_config.local.json" not in blob
    assert "Application Support/KI-Rechnungen/" not in blob
    assert "invoice_files" not in blob
    assert "working_profile" not in blob
    assert "binary_pdf" not in blob
    assert "%PDF-" not in blob
    assert not any(key in envelope for key in ("files", "invoices", "attachments"))


def test_import_draft_creates_new_id(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    created = store.create_draft(display_name="Quelle")
    assert created.ok and created.draft_id
    export_path = tmp_path / "roundtrip.json"
    assert store.export_draft(created.draft_id, export_path).ok

    imported = store.import_draft(export_path)
    assert imported.ok is True
    assert imported.status == STATUS_IMPORTED
    assert imported.draft_id
    assert imported.draft_id != created.draft_id
    assert imported.path.is_file()
    assert imported.path.parent == store.drafts_root
    assert imported.display_name == "Quelle"

    items = store.list_drafts()
    ids = {item.draft_id for item in items}
    assert created.draft_id in ids
    assert imported.draft_id in ids


def test_import_draft_does_not_silently_overwrite_existing(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    existing = store.create_draft(display_name="Bleibt")
    assert existing.ok and existing.draft_id and existing.profile_draft is not None
    existing.profile_draft.notes = "original-notes"
    assert store.save_draft(existing.draft_id, existing.profile_draft, None).ok

    other = store.create_draft(display_name="Andere")
    assert other.ok and other.draft_id
    export_path = tmp_path / "other.json"
    assert store.export_draft(other.draft_id, export_path).ok

    before = existing.path.read_bytes()
    imported = store.import_draft(export_path, preferred_display_name="Importiert")
    assert imported.ok
    assert imported.draft_id != existing.draft_id
    assert existing.path.read_bytes() == before
    reloaded = store.load_draft(existing.draft_id)
    assert reloaded.ok and reloaded.profile_draft is not None
    assert reloaded.profile_draft.notes == "original-notes"
    assert reloaded.display_name == "Bleibt"


def test_import_draft_rejects_wrong_kind(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    bad = tmp_path / "wrong_kind.json"
    bad.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "kind": "saas_ui_v2_profile_draft",
                "cloud": False,
                "draft": {"profile": {"profile_name": "X", "scan_model_id": "rechnungen"}},
            }
        ),
        encoding="utf-8",
    )
    result = store.import_draft(bad)
    assert result.ok is False
    assert result.status == STATUS_VALIDATION_ERROR
    assert "kind" in (result.error or "").lower()
    assert len(store.list_drafts()) == 0


def test_import_draft_rejects_corrupt_json(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    bad = tmp_path / "corrupt.json"
    bad.write_text("{ not-json", encoding="utf-8")
    result = store.import_draft(bad)
    assert result.ok is False
    assert result.status == STATUS_CORRUPTED
    assert len(store.list_drafts()) == 0


def test_import_draft_rejects_private_markers(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    for marker in ("SOMAA", "Hadi", "AMEX-1005", "EP", "Bismarck", "Architektur", "97368", "DE189", "voba"):
        path = tmp_path / f"private_{marker}.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "kind": EXPORT_KIND,
                    "cloud": False,
                    "exported_at": "2026-07-20T00:00:00+00:00",
                    "draft": {
                        "display_name": f"Leak {marker}",
                        "profile": {
                            "profile_name": f"Profil {marker}",
                            "scan_model_id": "rechnungen",
                            "document_type": "Rechnungen",
                            "matching_conditions": "",
                            "destination_category": "",
                            "destination_folder": "",
                            "filename_pattern": "{invoice_date}_{supplier}_{amount}_{payment_field}.pdf",
                            "review_rule": "unclear_on_no_match",
                            "payment_hint": "",
                            "review_unclear_folder": "unklar",
                            "notes": "",
                            "is_new": True,
                            "configurations": [],
                        },
                        "configuration": None,
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        result = store.import_draft(path)
        assert result.ok is False, marker
        assert result.status == STATUS_PRIVATE_DEFAULTS, marker
    assert len(store.list_drafts()) == 0


def test_import_draft_strips_dangerous_paths_and_stays_in_store(tmp_path: Path) -> None:
    store = new_saas_profile_disk_store(tmp_path / "drafts")
    outside = tmp_path / "outside_should_not_appear.json"
    import_path = tmp_path / "with_paths.json"
    import_path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "kind": EXPORT_KIND,
                "cloud": False,
                "exported_at": "2026-07-20T00:00:00+00:00",
                "draft": {
                    "display_name": "Pfad-Sanitized",
                    "profile": {
                        "profile_name": "Neues Profil",
                        "scan_model_id": "rechnungen",
                        "document_type": "Rechnungen",
                        "matching_conditions": "",
                        "destination_category": "",
                        "destination_folder": "/Users/hadi_neu/Desktop/RECHNUNGEN/inbox",
                        "filename_pattern": "{invoice_date}_{supplier}_{amount}_{payment_field}.pdf",
                        "review_rule": "unclear_on_no_match",
                        "payment_hint": "",
                        "review_unclear_folder": "~/Library/Application Support/KI-Rechnungen/unklar",
                        "notes": "",
                        "is_new": True,
                        "configurations": [],
                    },
                    "configuration": None,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = store.import_draft(import_path)
    assert result.ok is True
    assert result.path.parent == store.drafts_root
    assert str(result.path).startswith(str(tmp_path / "drafts"))
    assert not outside.exists()
    assert result.profile_draft is not None
    assert result.profile_draft.destination_folder == ""
    # Dangerous path stripped; blank/default generic folder may be applied.
    assert "/Users/" not in (result.profile_draft.review_unclear_folder or "")
    assert "Application Support" not in (result.profile_draft.review_unclear_folder or "")
    assert "RECHNUNGEN" not in (result.profile_draft.review_unclear_folder or "")


def test_profile_config_local_untouched_by_import_export(tmp_path: Path) -> None:
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
    state.configure_saas_disk_store(tmp_path / "drafts")
    created = state.create_saas_draft(display_name="Guard-IO")
    assert created.ok and created.draft_id
    export_path = tmp_path / "guard_export.json"
    assert state.export_saas_draft(export_path).ok
    assert state.import_saas_draft(export_path).ok

    assert PROFILE_LOCAL.read_bytes() == before
    assert PROFILE_LOCAL.stat().st_mtime_ns == before_mtime
    if app_before is not None and APP_SUPPORT_PROFILE.is_file():
        assert APP_SUPPORT_PROFILE.read_bytes() == app_before
        assert APP_SUPPORT_PROFILE.stat().st_mtime_ns == app_mtime


def test_state_selects_imported_draft(tmp_path: Path) -> None:
    state = UiV2State()
    state.configure_saas_disk_store(tmp_path / "drafts")
    first = state.create_saas_draft(display_name="Erste")
    assert first.ok and first.draft_id
    export_path = tmp_path / "state_export.json"
    assert state.export_saas_draft(export_path).ok
    assert state.saas_selected_draft_id == first.draft_id

    imported = state.import_saas_draft(export_path)
    assert imported.ok and imported.draft_id
    assert state.saas_selected_draft_id == imported.draft_id
    assert imported.draft_id != first.draft_id
    assert state.saas_disk_last_status == STATUS_IMPORTED


def test_ui_texts_separate_saas_and_no_cloud() -> None:
    vm = build_saas_draft_list_vm(())
    texts = " ".join(vm.all_ui_texts())
    assert ACTION_EXPORT in texts
    assert ACTION_IMPORT in texts
    assert IMPORT_EXPORT_HELP in texts
    assert SEPARATION_HELP in texts
    assert "nicht das interne Arbeitsprofil" in texts
    assert NO_CLOUD_HELP in texts
    assert "Cloud-Synchronisierung" in texts
    assert "Cloud-Sync aktiv" not in texts
    assert "Mandantenbackend" not in texts
    assert "ohne Mandanten-Anbindung" in texts
    for marker in PRIVATE_MARKERS:
        assert marker not in texts, marker


def test_pages_wire_import_export() -> None:
    profiles = PROFILES.read_text(encoding="utf-8")
    configs = CONFIGS.read_text(encoding="utf-8")
    list_src = LIST_VIEW.read_text(encoding="utf-8")
    state_src = STATE.read_text(encoding="utf-8")
    assert "on_export" in profiles
    assert "on_import" in profiles
    assert "export_saas_draft" in profiles
    assert "import_saas_draft" in profiles
    assert "on_export" in configs
    assert "on_import" in configs
    assert "export_saas_draft" in state_src
    assert "import_saas_draft" in state_src
    assert "Exportieren" in list_src
    assert "Importieren" in list_src


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
