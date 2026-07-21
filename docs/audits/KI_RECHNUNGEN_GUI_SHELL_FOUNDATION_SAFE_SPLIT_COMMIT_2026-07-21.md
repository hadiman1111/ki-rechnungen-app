# KI-Rechnungen GUI Shell Foundation — Safe Split Commit

**Task ID:** `KI_RECHNUNGEN_GUI_SHELL_FOUNDATION_SAFE_SPLIT_COMMIT_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / GUI Shell / Foundation Split

## 1. Purpose

Commit only the smallest independent GUI/Shell foundation subset:

- generic shell foundation primitives
- no GUI wiring switch
- no app_main / build / launcher integration
- no processing-core changes
- no private Hadi/SOMAA/Bismarck/AMEX/voba defaults

## 2. Files reviewed

| File | Review result |
|---|---|
| `invoice_tool/ui_theme.py` | Generic semantic tokens; depends on existing `ui_tokens` at HEAD; no private defaults |
| `invoice_tool/ui_components.py` | Generic Flet component helpers; theme-backed; no page imports; no private defaults |
| `invoice_tool/ui_shell.py` | Standalone shell layout; imports only `ui_theme` + stdlib/flet; no page modules |
| `tests/test_ui_design_system.py` | Structural/unit checks only; no windows, no macOS dialogs, no Application Support, no real invoices |

## 3. Files included

- `invoice_tool/ui_theme.py`
- `invoice_tool/ui_components.py`
- `invoice_tool/ui_shell.py`
- `tests/test_ui_design_system.py`
- `docs/audits/KI_RECHNUNGEN_GUI_SHELL_FOUNDATION_SAFE_SPLIT_COMMIT_2026-07-21.md`

## 4. Files explicitly excluded

**Dirty GUI wiring (not staged):**

- `invoice_tool/gui.py`
- `invoice_tool/ui_profile_dialog.py`
- `invoice_tool/ui_tokens.py`

**Page modules (not staged):**

- `invoice_tool/ui_workspace.py`
- `invoice_tool/ui_profiles.py`
- `invoice_tool/ui_configurations.py`
- `invoice_tool/ui_review.py`
- `invoice_tool/ui_settings.py`
- `invoice_tool/ui_filename_builder.py`
- `invoice_tool/ui_document_rules.py`

**Build / launcher / packaging (not staged):**

- `app_main.py`
- `pyproject.toml`
- `scripts/**`
- `resources/standalone/**`
- `invoice_tool/startup_log.py`

**Other dirty/untracked out of scope:**

- `docs/audits/evidence/**`, other audit/design docs
- `diagnostics/**`, `testing/**`
- `.venv*`, PDFs, real invoice folders, `profile_config.local.json`

## 5. Why foundation is generic

`ui_theme.py` exposes semantic color/spacing/typography names only.  
`ui_components.py` builds reusable controls from those tokens.  
`ui_shell.py` provides a navigation shell with callback-based `on_navigate` and no hardcoded profile/path defaults beyond the product label „KI-Rechnungen“ / placeholder „Profil“.

## 6. Why no GUI wiring switch

`gui.py` remains dirty and uncommitted. Nothing in this commit changes the active application entry path or swaps the live UI to the new shell.

## 7. Why no Build/Launcher inclusion

`app_main.py`, `pyproject.toml`, `scripts/build_macos_app.sh`, and `resources/standalone/**` stay out of the payload. Build/foundation waits until shell/foundation is safely landed.

## 8. Why no private defaults

Reviewed sources contain no Hadi/SOMAA/Bismarck/AMEX/voba paths or profile IDs. Test fixtures use generic names (`Beispiel`, `~/Beispiel`). Shell profile summary defaults to `"Profil"`.

## 9. Tests run

```bash
.venv/bin/python - <<'PY'
from invoice_tool import ui_theme, ui_components
print("UI_SHELL_FOUNDATION_IMPORT_OK")
PY

.venv/bin/python - <<'PY'
from invoice_tool import ui_shell
print("UI_SHELL_IMPORT_OK")
PY

.venv/bin/python -m pytest tests/test_ui_design_system.py -q
```

## 10. Test result

- Import foundation: `UI_SHELL_FOUNDATION_IMPORT_OK`
- Import shell: `UI_SHELL_IMPORT_OK`
- Pytest: **2 passed, 5 skipped** (Flet `< 0.85` in `.venv`; skipped tests require Flet ≥ 0.85 Padding/Border API — no window opens)

## 11. Remaining dirty-state summary

After this commit, expected remaining dirty/untracked work includes:

- GUI wiring: `gui.py`, `ui_profile_dialog.py`, `ui_tokens.py`
- Page modules: workspace/profiles/configurations/review/settings/filename/document-rules
- Build track: `app_main.py`, `pyproject.toml`, `scripts/build_macos_app.sh`, `resources/standalone/**`
- Other audits, design refs, testing harnesses, `.venv-flet085/`

## 12. Next task recommendation

**Next:** `KI_RECHNUNGEN_GUI_SHELL_PAGE_MODULES_SAFE_SPLIT` — review and commit page modules only after each module is import-isolated and free of private defaults; still without committing dirty `gui.py` wiring or build/app_main integration.
