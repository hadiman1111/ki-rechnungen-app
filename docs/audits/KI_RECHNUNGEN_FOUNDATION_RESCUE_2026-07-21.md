# KI-Rechnungen — Foundation Rescue Commit (2026-07-21)

**Task ID:** `KI_RECHNUNGEN_DIRTY_STATE_FOUNDATION_RESCUE_COMMIT_01`

## Problem

`origin/main` importierte bereits UI-v2-/Launcher-Foundation-Module, die nur untracked im Worktree lagen:

- `invoice_tool/configuration_model.py`
- `invoice_tool/profile_store.py`
- `invoice_tool/scan_models.py`

Ohne diese Dateien ist ein Checkout von `main` potenziell unvollständig (ImportError in committed Callern).

## Scope dieses Commits

Committed:

- die drei Foundation-Module
- `tests/test_somaa_filename_token_repair.py` (direkt `configuration_model` / Token-Repair)
- dieses Audit

Nicht committed (bewusst):

- GUI-Shell / UI-v2 WIP / Launcher / Build / Evidence / `.venv*`
- `tests/test_profile_configuration_architecture.py` (modul-level Import von untracked `ui_shell` / `ui_theme`)
- `tests/test_cfg_001_profile_ui_runtime_integration.py` (nicht direkt Foundation-Import)

## Import-Abhängigkeit (committed HEAD → Foundation)

Beispiele tracked Importer: `gui.py`, `ui_v2/validation.py`, `ui_v2/adapters/*`, `ui_v2/pages/*`, `internal_launcher/profile_display.py`, `ui_v2/draft_models.py`, `ui_v2/filename_editor.py`.

## Secrets / Private Data

Geprüft: keine API-Keys, keine privaten Pfade, keine echten Rechnungsdaten.
`SOMAA_CANONICAL_FILENAME_TEMPLATE` ist ein generisches Dateinamen-Muster; Preview-Werte in `scan_models` sind neutral (Musterfirma).

## Tests (lokal, vor Commit)

- Primary SaaS: 50 passed
- Foundation-bezogen: 36 passed (`test_profile_configuration_architecture`, `test_cfg_001_*`, `test_somaa_filename_token_repair`)

## Grenzen

Kein Push. Keine produktive Verarbeitung. Keine realen Rechnungsordner verändert.
