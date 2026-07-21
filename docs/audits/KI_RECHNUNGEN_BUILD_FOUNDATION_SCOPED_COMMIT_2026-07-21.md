# KI-Rechnungen — Build Foundation Scoped Commit

**Task ID:** `KI_RECHNUNGEN_BUILD_FOUNDATION_SCOPED_COMMIT_01`  
**Datum:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Build Foundation / Standalone Internal App  
**HEAD vor Commit:** `ec857225c85272e6f15bcdce9e810abb781b0179` (= `origin/main`, ahead/behind `0/0`)

## 1. Purpose

Scoped Commit der Build/Foundation-Dateien für den internen lokalen macOS-App-Pfad (Track A). Kein Processing-Core, keine Legacy-UI, keine echten Rechnungsordner, keine PDFs, keine Evidence/Venvs.

## 2. Files reviewed

- `app_main.py`
- `invoice_tool/startup_log.py`
- `pyproject.toml`
- `scripts/build_macos_app.sh`
- `resources/standalone/invoice_config.json`
- `tests/test_build_macos_cleanup.py`
- `docs/audits/KI_RECHNUNGEN_GUI_SHELL_RUNTIME_SMOKE_OR_BUILD_BOUNDARY_DECISION_2026-07-21.md`
- dieses Audit: `docs/audits/KI_RECHNUNGEN_BUILD_FOUNDATION_SCOPED_COMMIT_2026-07-21.md`

## 3. Files included

- `app_main.py`
- `invoice_tool/startup_log.py`
- `pyproject.toml`
- `scripts/build_macos_app.sh`
- `resources/standalone/invoice_config.json`
- `tests/test_build_macos_cleanup.py`
- `docs/audits/KI_RECHNUNGEN_GUI_SHELL_RUNTIME_SMOKE_OR_BUILD_BOUNDARY_DECISION_2026-07-21.md`
- `docs/audits/KI_RECHNUNGEN_BUILD_FOUNDATION_SCOPED_COMMIT_2026-07-21.md`

## 4. Files explicitly excluded

- `invoice_tool/ui_profile_dialog.py` (legacy dirty)
- `invoice_tool/ui_document_rules.py` (legacy untracked)
- `invoice_tool/processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, `run.py`
- unrelated `scripts/**` (außer `build_macos_app.sh`)
- unrelated `docs/**` / `docs/audits/evidence/**` / `docs/design*` / `docs/tasks/**`
- `diagnostics/**`, `testing/**`
- `.venv*`, `profile_config.local.json`
- PDFs, reale Rechnungsordner (`Desktop/RECHNUNGEN`, `Desktop/TEST Rechnungen`)
- sonstige untracked Tests / AGENTS.md

## 5. Why Build/Foundation is Track A internal

Die Foundation liefert den Flet-Build-Einstieg (`app_main`), Startup-Logging, Flet-0.85.3-Pin, macOS-Build-Skript und generische Standalone-Defaults unter Application Support. Das ist der interne lokale App-Pfad, getrennt von produktiver Verarbeitung und Legacy-UI.

## 6. Why no processing-core change

Keine der Processing-/Routing-/Classification-/Run-Dateien ist dirty oder staged. Der Commit enthält nur Build-/Entry-/Config-/Test-/Audit-Dateien.

## 7. Why no private defaults / real invoice folders / PDFs

- `app_main.py`: keine hardcodierten Rechnungs-/Desktop-Pfade
- `startup_log.py`: nur `~/Library/Application Support/KI-Rechnungen/logs/ui-startup.log`
- `resources/standalone/invoice_config.json`: ausschließlich `$HOME/Library/Application Support/KI-Rechnungen/...`
- `pyproject.toml`: keine private/Hadi/SOMAA/AMEX/voba Defaults; Exclude-Liste hält lokale Artefakte/Tests aus dem Bundle
- `build_macos_app.sh`: bundelt nur `resources/standalone/invoice_config.json` + `office_rules.json`, keine realen Rechnungsordner/PDFs/Secrets/private Profile

## 8. Runtime smoke dependency

Voraussetzung: `GUI_SHELL_RUNTIME_SMOKE_BUILD_BOUNDARY_READY`  
Audit: `docs/audits/KI_RECHNUNGEN_GUI_SHELL_RUNTIME_SMOKE_OR_BUILD_BOUNDARY_DECISION_2026-07-21.md`  
Ergebnis dort: committed GUI Shell ist unter Flet 0.85 headless-smoke-fähig; Build/Foundation als separater Commit freigegeben.

## 9. Tests run

```text
.venv/bin/python -m pytest \
  tests/test_gui_startup.py \
  tests/test_navigation_regression_gate.py \
  tests/test_ui_architecture_repair.py \
  tests/test_ui_design_system.py \
  tests/test_profile_configuration_architecture.py \
  tests/test_internal_launcher_startup.py \
  tests/test_internal_launcher_run_controller.py \
  tests/test_internal_launcher_path_validation.py \
  tests/test_internal_launcher_result_reader.py \
  tests/test_app_paths.py \
  tests/test_build_macos_cleanup.py
```

Import-Checks:

- `.venv`: `BUILD_FOUNDATION_IMPORT_OK` (`app_main`, `startup_log`)
- `.venv-flet085`: `FLET085_GUI_IMPORT_OK`

Nicht ausgeführt: `flet build`, macOS-App-Build, GUI-Fenster, produktive Verarbeitung, PDF-Processing.

## 10. Test result

**77 passed, 35 skipped** (Skips: Flet ≥ 0.85 Padding/Border-API unter `.venv`)  
Import-Checks: OK

## 11. Remaining dirty-state summary

Nach diesem Commit bleiben erwartbar dirty/untracked:

- Legacy: `invoice_tool/ui_profile_dialog.py`, `invoice_tool/ui_document_rules.py`
- `.venv-flet085/`
- unrelated docs/scripts/testing/evidence/design
- weitere untracked Tests / AGENTS.md

## 12. Next task recommendation

`KI_RECHNUNGEN_LEGACY_UI_CLEANUP_OR_FREEZE_FOLLOWUP` — Legacy `ui_profile_dialog.py` / `ui_document_rules.py` gezielt bereinigen oder freigeben; alternativ erster interner macOS-Build-Lauf nur nach expliziter PO-Freigabe (nicht Teil dieses Commits).

## Final classification (planned)

`BUILD_FOUNDATION_COMMITTED_AND_PUSHED` (nach erfolgreichem Safe-Push)
