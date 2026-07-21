# KI-Rechnungen — GUI Shell Runtime Smoke / Build Boundary Decision

**Task ID:** `KI_RECHNUNGEN_GUI_SHELL_RUNTIME_SMOKE_OR_BUILD_BOUNDARY_DECISION_01`  
**Datum:** 2026-07-21  
**HEAD:** `ec857225c85272e6f15bcdce9e810abb781b0179` (= `origin/main`, ahead/behind `0/0`)

## Initial classification

`READY_FOR_GUI_SHELL_RUNTIME_SMOKE_OR_BUILD_BOUNDARY_DECISION`

## Final classification

`GUI_SHELL_RUNTIME_SMOKE_BUILD_BOUNDARY_READY`

## Runtime smoke (non-destructive)

| Check | Result |
|---|---|
| Import committed GUI modules (`.venv`) | `COMMITTED_GUI_SHELL_IMPORT_OK` |
| Import committed GUI modules (`.venv-flet085`) | `COMMITTED_GUI_SHELL_IMPORT_OK_FLET085` |
| `gui.py` forbidden imports (`app_main`, `startup_log`, `ui_profile_dialog`, `ui_document_rules`, `scripts`, `resources/standalone`) | `GUI_FORBIDDEN_IMPORT_CHECK_OK` |
| Real invoice default paths in committed shell | none |
| Headless `build_ui` on `.venv` (Flet &lt; 0.85) | FAIL expected: `Padding.symmetric` missing |
| Headless `build_ui` on `.venv-flet085` (Flet 0.85.3) | `BUILD_UI_HEADLESS_SMOKE_OK_FLET085` |
| Processing entrypoint | lazy `invoice_tool.run.run_once` only; no `processing`/`routing`/`classification` module imports |
| `target_routing` | lazy read-only `target_configuration_summary` only |

## Safe tests

**`.venv` pytest (required suite):** 43 passed, 35 skipped  
Skips: `Erfordert Flet >= 0.85 für Padding/Border-Klassen-API`

**`.venv-flet085`:** `pytest` not installed (no package install performed).  
**Optional unittest:** `tests.test_navigation_regression_gate` → 8 tests OK.

**Also noted:** `tests/test_build_macos_cleanup.py` → 1 passed (Build guard available).

## Build/Foundation eligibility

| File | Status | Separately commitable? | Notes |
|---|---|---|---|
| `app_main.py` | untracked | yes | depends on committed `invoice_tool.gui.build_ui` + untracked `startup_log` |
| `invoice_tool/startup_log.py` | untracked | yes | writes under Application Support logs only |
| `pyproject.toml` | dirty | yes (scoped) | pins `flet==0.85.3`, `[tool.flet.app] module = "app_main"` |
| `scripts/build_macos_app.sh` | dirty | yes (scoped) | expects `.venv-flet085` / Flet 0.85.3 |
| `resources/standalone/invoice_config.json` | untracked | yes | `$HOME/Library/Application Support/KI-Rechnungen/...` only; no Desktop/RECHNUNGEN |

### Still blocked / out of Build-Foundation scope

- `invoice_tool/ui_profile_dialog.py` (legacy dirty) — leave dirty; do not include
- `invoice_tool/ui_document_rules.py` (legacy untracked) — leave untracked; do not include
- `.venv-flet085/` — never commit
- unrelated `docs/`, `scripts/*` audit/UI-v2 helpers, `testing/`, extra untracked tests

### Guard tests for Build/Foundation commit

1. `tests/test_gui_startup.py` (preferably under Flet ≥ 0.85)
2. `tests/test_navigation_regression_gate.py`
3. `tests/test_internal_launcher_startup.py`
4. `tests/test_internal_launcher_run_controller.py`
5. `tests/test_build_macos_cleanup.py`
6. architecture/design gates as available: `test_ui_architecture_repair`, `test_ui_design_system`, `test_profile_configuration_architecture`

## Decisions

1. Committed GUI Shell is runtime-safe enough for the **internal local app path** via **Flet 0.85** (`.venv-flet085`).
2. Committed GUI Shell remains **separate** from Build/Launcher modules.
3. Build/Foundation is **eligible as the next separate commit workstream**.
4. Manual live GUI window smoke is **optional**, not a hard blocker for Build/Foundation boundary readiness after headless smoke + safe tests.
5. Legacy `ui_profile_dialog.py` / `ui_document_rules.py`: **leave dirty/untracked for now**; revert/delete later in a dedicated legacy cleanup task.

## Exact next task

`KI_RECHNUNGEN_BUILD_FOUNDATION_SCOPED_COMMIT_01` — scoped commit of:

- `app_main.py`
- `invoice_tool/startup_log.py`
- `pyproject.toml`
- `scripts/build_macos_app.sh`
- `resources/standalone/invoice_config.json`

…with the guard tests above; exclude legacy UI and unrelated untracked trees.

## Confirmations

- No productive processing
- No real invoice changes
- No commit / no push in this task
- Only optional change: this audit doc (uncommitted)
