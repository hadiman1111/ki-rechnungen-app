# KI_RECHNUNGEN_GUI_SHELL_PAGE_MODULES_SAFE_SPLIT_COMMIT — 2026-07-21

Task ID: `KI_RECHNUNGEN_GUI_SHELL_PAGE_MODULES_SAFE_SPLIT_COMMIT_01`

## 1. Purpose

Sicheren Split-Commit der generischen GUI-Shell-Seitenmodule, die auf der bereits committed Shell Foundation aufbauen, ohne die App auf den neuen Shell umzuschalten und ohne Build/Launcher/Wiring.

## 2. Files reviewed

- `invoice_tool/ui_workspace.py`
- `invoice_tool/ui_profiles.py`
- `invoice_tool/ui_configurations.py`
- `invoice_tool/ui_review.py`
- `invoice_tool/ui_settings.py`
- `invoice_tool/ui_filename_builder.py`
- `invoice_tool/ui_document_rules.py` (optional candidate)
- `tests/test_ui_document_rules.py`
- `tests/test_profile_configuration_architecture.py`
- `tests/test_cfg_001_profile_ui_runtime_integration.py`

## 3. Files included

- `invoice_tool/ui_workspace.py`
- `invoice_tool/ui_profiles.py`
- `invoice_tool/ui_configurations.py`
- `invoice_tool/ui_review.py`
- `invoice_tool/ui_settings.py`
- `invoice_tool/ui_filename_builder.py`
- `tests/test_profile_configuration_architecture.py`
- `docs/audits/KI_RECHNUNGEN_GUI_SHELL_PAGE_MODULES_SAFE_SPLIT_COMMIT_2026-07-21.md`

## 4. Files explicitly excluded

- `invoice_tool/ui_document_rules.py` — explizit als LEGACY markiert; hängt an `target_routing` und an noch dirtyen `ui_tokens`-Erweiterungen (`SP_32` u. a.); nicht Teil der aktiven Shell-Navigation
- `tests/test_ui_document_rules.py` — hängt am Legacy-Modul; enthält `@requires_flet_085`-View-Build-Tests
- `tests/test_cfg_001_profile_ui_runtime_integration.py` — ruft `run_once` / Processing-Pipeline auf; kein reines Page-Modul-Test
- `invoice_tool/gui.py` — dirty Wiring, kein Switch
- `invoice_tool/ui_profile_dialog.py` — dirty Wiring
- `invoice_tool/ui_tokens.py` — dirty Token-WIP (nicht erlaubt in diesem Split)
- `app_main.py`, `invoice_tool/startup_log.py`, `pyproject.toml`, `scripts/**`, `resources/standalone/**`
- Evidence/Diagnostics/Testing-Ordner, `.venv*`, PDFs, reale Rechnungsordner, `profile_config.local.json`

## 5. Why page modules are generic

Die aufgenommenen Module sind Präsentations-/Page-Builder:

- Workspace, Profile, Konfigurationen, Review, Settings, Filename-Builder
- Abhängigkeiten: committed Foundation (`ui_theme`, `ui_components`, `ui_shell`-Kontext), `profile_store`, `configuration_model`, `scan_models`, `app_paths`
- Keine produktiven Defaults für Hadi/SOMAA/Bismarck/AMEX/voba
- Keine Hardcodes auf lokale Benutzerpfade

## 6. Why no GUI wiring switch

`gui.py` bleibt unberührt und uncommitted. Die Page-Module exportieren nur Builder-Funktionen; ohne Wiring-Änderung startet die App weiterhin den bisherigen Einstieg.

## 7. Why no Build/Launcher inclusion

`app_main.py`, `pyproject.toml`, `scripts/**`, `resources/standalone/**`, `startup_log.py` bleiben außerhalb des Payloads. Build/Foundation wartet weiter.

## 8. Why no private defaults

Scan der included Page-Module: keine Treffer für Hadi/SOMAA/Bismarck/voba oder lokale `/Users/`-Defaults. AMEX-Beispiele existieren nur in ausgeschlossenen Legacy-/Test-Fixtures, nicht als Produkt-Defaults in den committed Page-Modulen.

Hinweis: In der Working Tree existiert weiterhin dirtyes `ui_tokens.py` mit Layout-Erweiterungen; dieses Modul wurde bewusst nicht committed. Die Foundation/`ui_theme`-Abhängigkeit darauf bleibt bekannter Rest-WIP außerhalb dieses Splits.

## 9. Tests run

```text
.venv/bin/python - <<'PY'
from invoice_tool import (
    ui_workspace, ui_profiles, ui_configurations,
    ui_review, ui_settings, ui_filename_builder,
)
print("GUI_SHELL_PAGE_MODULES_IMPORT_OK")
PY

.venv/bin/python -m pytest tests/test_profile_configuration_architecture.py -q --tb=short
```

Nicht ausgeführt (unsicher / out of scope):

- `tests/test_ui_document_rules.py` (Legacy + Flet-View-Tests)
- `tests/test_cfg_001_profile_ui_runtime_integration.py` (`run_once` / Processing)

## 10. Test result

- Import-Check: `GUI_SHELL_PAGE_MODULES_IMPORT_OK`
- `tests/test_profile_configuration_architecture.py`: **23 passed**

## 11. Remaining dirty-state summary

Nach diesem Commit bleiben u. a. dirty/untracked:

- GUI-Wiring: `gui.py`, `ui_profile_dialog.py`, `ui_tokens.py`
- Build/Launcher: `app_main.py`, `startup_log.py`, `pyproject.toml`, `scripts/**`, `resources/standalone/**`
- Legacy page: `ui_document_rules.py` (+ zugehörige Tests)
- Diverse Audits/Design/Testing-Artefakte, `.venv-flet085/`

## 12. Next task recommendation

`KI_RECHNUNGEN_GUI_SHELL_TOKENS_AND_WIRING_SAFE_SPLIT` — zuerst generische Token-Lücken (`ui_tokens` ↔ `ui_theme`) schließen, danach erst kontrolliertes `gui.py`-Wiring ohne Build/Launcher-Umschaltung.
