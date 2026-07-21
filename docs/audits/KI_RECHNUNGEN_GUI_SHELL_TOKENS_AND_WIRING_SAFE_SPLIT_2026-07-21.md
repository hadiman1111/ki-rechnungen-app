# KI_RECHNUNGEN_GUI_SHELL_TOKENS_AND_WIRING_SAFE_SPLIT — 2026-07-21

Task ID: `KI_RECHNUNGEN_GUI_SHELL_TOKENS_AND_WIRING_SAFE_SPLIT_01`

## 1. Purpose

Kontrollierter Split-Commit der generischen Token-Kompatibilität (`ui_tokens.py`) und der GUI-Verdrahtung (`gui.py`) auf die bereits committed Shell Foundation und Page Modules — ohne Build/Launcher und ohne Processing-Core-Änderungen.

## 2. Files reviewed

- `invoice_tool/ui_tokens.py`
- `invoice_tool/ui_profile_dialog.py`
- `invoice_tool/gui.py`
- `tests/test_gui_startup.py`
- `tests/test_flet085_ui_shell_gate.py`
- `tests/test_navigation_regression_gate.py`
- `tests/test_ui_architecture_repair.py`
- committed Abhängigkeiten: `ui_theme.py`, `ui_shell.py`, `ui_components.py`, Page Modules

## 3. Files included

- `invoice_tool/ui_tokens.py`
- `invoice_tool/gui.py`
- `tests/test_navigation_regression_gate.py`
- `tests/test_ui_architecture_repair.py`
- `docs/audits/KI_RECHNUNGEN_GUI_SHELL_TOKENS_AND_WIRING_SAFE_SPLIT_2026-07-21.md`

## 4. Files explicitly excluded

- `invoice_tool/ui_profile_dialog.py` — LEGACY; nicht über Shell-Navigation erreichbar; `gui.py` importiert es nicht mehr
- `tests/test_gui_startup.py` — hängt an uncommitted/`forbidden` `app_main.py` und `ui_document_rules.py`
- `tests/test_flet085_ui_shell_gate.py` — liest `app_main.py` als aktives Modul; ohne Build-Commit nicht clean-clone-sicher
- `app_main.py`, `invoice_tool/startup_log.py`, `pyproject.toml`, `scripts/**`, `resources/standalone/**`
- `invoice_tool/ui_document_rules.py`, Evidence/Diagnostics/Testing, `.venv*`, PDFs, reale Rechnungsordner, `profile_config.local.json`

## 5. Token compatibility decision

**INCLUDE.** Committed `ui_theme.py` referenziert bereits `_t.BG`, `_t.SP_32`, `_t.APP_SHELL_WIDTH`, `_t.FOLDER_CARD_*`, `_t.CENTER_COL_WIDTH`. Diese Attribute fehlten in HEAD-`ui_tokens.py` und sind in der Working Tree generisch ergänzt (Farben/Layout-Maße, keine privaten Defaults). Ohne diesen Token-Commit bleibt die Foundation/Theme-Schicht inkonsistent.

## 6. ui_profile_dialog decision

**EXCLUDE / postpone.** Datei ist als LEGACY markiert; aktive Navigation nutzt `ui_profiles.build_profiles_view`. Änderungen sind vor allem Flet-0.85-API-Anpassungen (`ft.Border`/`ft.Padding`) am Legacy-Dialog — nicht Teil der Shell-Verdrahtung.

## 7. gui.py wiring decision

**INCLUDE.** `gui.py` verdrahtet kontrolliert auf committed Module:

- Shell: `ui_shell`, `ui_components`, `ui_theme`
- Pages: `ui_workspace`, `ui_configurations`, `ui_profiles`, `ui_review`, `ui_settings`
- Pfade/Profile: `app_paths`, `profile_store` (committed)
- Processing-Einstieg unverändert über `run_once` (lazy import), ohne Import von `ui_document_rules`, `app_main`, `startup_log`, Build-Scripts oder `resources/`

Die Shell-Umschaltung ist per Git reversibel und auf UI-Wiring begrenzt.

## 8. Why no Build/Launcher inclusion

Build/Foundation wartet weiter. `app_main.py`, `startup_log.py`, `pyproject.toml`, `scripts/**`, `resources/standalone/**` bleiben außerhalb des Payloads.

## 9. Why no private defaults

Scan von included `ui_tokens.py` / `gui.py`: keine Hadi/SOMAA/Bismarck/AMEX/voba-Produktdefaults, keine hardcoded `/Users/`-Pfade. Quell-/Zielordner kommen aus Config/`FilePicker` bzw. Application-Support-Auflösung über committed `app_paths`.

## 10. Why no processing-core change

Keine Änderungen an Processing-/Routing-/Classification-Modulen. `gui.py` ruft weiterhin `run_once(...)` auf; Report-Suche wurde an den technischen Run-Ordner (`run_dir/_runs`) angepasst — UI-Pfadfindung, kein Core-Eingriff.

## 11. Tests run

```text
# Syntaxfix (erlaubt): tests/test_ui_architecture_repair.py — dead-code Indent nach return entfernt

.venv/bin/python - <<'PY'
from invoice_tool import gui, ui_tokens
print("GUI_SHELL_TOKENS_WIRING_IMPORT_OK")
PY
# Ergebnis: OK (auch .venv-flet085)

.venv/bin/python -m pytest \
  tests/test_gui_startup.py \
  tests/test_flet085_ui_shell_gate.py \
  tests/test_navigation_regression_gate.py \
  tests/test_ui_architecture_repair.py -q --tb=line
# Ergebnis: 7 passed, 47 skipped (Flet 0.28.3 in .venv; @requires_flet_085 skipped)

.venv-flet085/bin/python -m unittest tests.test_navigation_regression_gate -v
# Ergebnis: 8 tests OK (Flet 0.85.3; pytest in .venv-flet085 nicht installiert — kein Paket-Install)

.venv-flet085/bin/python  # isolierter build_ui-Smoke ohne Fenster
# Ergebnis: FLET085_BUILD_UI_SMOKE_OK / GUI_IMPORT_BOUNDARY_OK
```

## 12. Test result

- Import-Checks: PASS
- `.venv` pytest: PASS mit Skip der Flet-0.85-Gates
- `.venv-flet085` Navigation-Regression (unittest): PASS
- Flet-0.85 `build_ui`-Smoke: PASS
- Keine GUI-Fenster, keine macOS-Dialoge, kein produktives Processing, kein 250-PDF-Lauf

## 13. Remaining dirty-state summary

Nach diesem Commit bleiben u. a. dirty/untracked außerhalb des Payloads:

- Build/Launcher: `app_main.py`, `startup_log.py`, `pyproject.toml`, `scripts/build_macos_app.sh`, weitere `scripts/**`, `resources/standalone/**`
- Legacy: `ui_profile_dialog.py`, `ui_document_rules.py`
- Tests mit Build-/Legacy-Kopplung: `test_gui_startup.py`, `test_flet085_ui_shell_gate.py`, weitere UI-V2-/Build-Tests
- Docs/Evidence/Design/Testing/`.venv-flet085/`

## 14. Next task recommendation

`KI_RECHNUNGEN_GUI_SHELL_RUNTIME_SMOKE_OR_BUILD_BOUNDARY_DECISION` — manueller/isolierter Runtime-Smoke der verdrahteten Shell **oder** getrennte Entscheidung, ob Build/`app_main`/`pyproject` als nächster Split vorbereitet wird. Legacy-`ui_profile_dialog` / `ui_document_rules` weiter ausgeschlossen, bis separat freigegeben.
