# KI-Rechnungen — Internal Launcher Safe Tests Commit

**Task ID:** `KI_RECHNUNGEN_DIRTY_STATE_INTERNAL_LAUNCHER_SAFE_TESTS_COMMIT_01`  
**Datum:** 2026-07-21  
**Track:** A — Internal Local App Support  
**Review-Entscheidung:** `SPLIT_BUILD_LAUNCHER_INTO_TESTS_THEN_BUILD`

## 1. Purpose

Commit only der sicheren, nicht-destruktiven Unit-Tests, die bereits committedes Internal-Launcher-Verhalten verifizieren. Kein Build, kein Shell/GUI-WIP, kein produktiver Lauf.

## 2. Files reviewed

| Datei | Entscheidung |
|---|---|
| `tests/test_app_paths.py` | commit |
| `tests/test_internal_launcher_path_validation.py` | commit |
| `tests/test_internal_launcher_result_reader.py` | commit |
| `tests/test_internal_launcher_run_controller.py` | commit |
| `tests/test_internal_launcher_startup.py` | commit |
| `tests/test_internal_launcher_profile_display.py` | commit |
| `tests/test_build_macos_cleanup.py` | **nicht** commit — hängt an `scripts/build_macos_app.sh` |
| `tests/test_internal_launcher_folder_picker.py` | **nicht** commit — macOS UI/Dialog |

## 3. Why these tests are safe

1. Keine echten UI-Fenster: Startup nutzt `MagicMock`-Page, kein `ft.app()`.
2. Keine macOS-Dialoge / FilePicker.
3. Kein Zugriff auf reale `profile_config.local.json` — nur `tmp_path`-Fixtures.
4. Keine Mutation von echtem Application Support — Support-Pfade werden gemockt; der eine Read-Only-Pfad-Assert mutiert nichts.
5. Kein Zugriff auf `/Users/hadi_neu/Desktop/RECHNUNGEN`.
6. Kein `.venv-flet085` nötig — Lauf über `.venv` + pytest.
7. Keine Abhängigkeit von dirty GUI/Shell-WIP — Imports aus committedem `invoice_tool.internal_launcher` / `app_paths` / `app_internal_launcher`.
8. Keine Abhängigkeit von untracked/dirty Build-Skripten.
9. Keine privaten Defaults als Produktverhalten.
10. SOMAA-Strings nur als Test-Fixtures / Display-Fixtures, nicht als Defaults.

## 4. Why folder picker / live visual tests are excluded

- `tests/test_internal_launcher_folder_picker.py` kann macOS-UI/Dialog-Verhalten berühren.
- Live/Visual-Verify-Skripte unter `scripts/verify_internal_launcher_folder_picker_*` sind UI-/macOS-live und gehören nicht in Track-A Safe-Tests.

## 5. Why build script / app_main / pyproject are excluded

Review `BUILD_LAUNCHER_TRACK_ISOLATION_READY` / Split: Build-Foundation (`app_main.py`, `startup_log.py`, `pyproject.toml`, `scripts/build_macos_app.sh`, `resources/standalone/**`) wartet auf den späteren Build/Foundation-Commit. `test_build_macos_cleanup.py` liest das dirty Build-Skript und bleibt deshalb draußen.

## 6. Why no Shell/GUI WIP is included

Dirty/untracked Shell-Dateien (`gui.py`, `ui_*.py`, UI-V2-Audits/Scripts) gehören zu einem anderen Track und dürfen die Launcher-Test-Payload nicht kontaminieren.

## 7. Tests run

```text
.venv/bin/python -m pytest \
  tests/test_app_paths.py \
  tests/test_internal_launcher_path_validation.py \
  tests/test_internal_launcher_result_reader.py \
  tests/test_internal_launcher_run_controller.py \
  tests/test_internal_launcher_startup.py \
  tests/test_internal_launcher_profile_display.py
```

## 8. Test result

**49 passed** in ~3.2s.

## 9. Private / local fixture assessment

- `SOMAA Profil – Lokale Arbeitskopie` erscheint nur als Fixture-String in Profile-Display- und Startup-Mocks.
- `profile_config.local.json`-Namen in Tests beziehen sich ausschließlich auf `tmp_path`.
- Keine Hadi-/Privatpfade als Produkt-Default.

## 10. Remaining dirty-state summary

Nach diesem Commit bleiben erwartungsgemäß dirty/untracked:

- Shell/GUI: `gui.py`, `ui_*.py`, diverse UI-Audits
- Build/Foundation: `app_main.py`, `startup_log.py`, `pyproject.toml`, `scripts/build_macos_app.sh`, `resources/standalone/`
- Weitere Scripts, `testing/`, `.venv-flet085/`, Evidence, Design-Docs
- Ausgeschlossene Tests: folder picker, build cleanup, GUI/UI-Gates

## 11. Next task recommendation

**Track B / Build Foundation (nach Shell-Trennung laut Review):**  
Commit `app_main.py` + `startup_log.py` + `pyproject.toml` + `scripts/build_macos_app.sh` (+ optional `tests/test_build_macos_cleanup.py`) erst wenn Shell/Foundation-Voraussetzungen erfüllt sind.  
Shell/GUI-WIP weiterhin separat halten.
