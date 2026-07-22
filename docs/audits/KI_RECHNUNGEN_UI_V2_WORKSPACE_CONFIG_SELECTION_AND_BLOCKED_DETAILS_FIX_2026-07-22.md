# KI_RECHNUNGEN_UI_V2_WORKSPACE_CONFIG_SELECTION_AND_BLOCKED_DETAILS_FIX_2026-07-22

## 1. Task ID

`KI_RECHNUNGEN_UI_V2_WORKSPACE_CONFIG_SELECTION_AND_BLOCKED_DETAILS_FIX_01`

## 2. User observation

Track-B UI-v2: After selecting input/output folders and clicking Sandbox start, the UI blocked with:

- Primary: `Sandbox-Lauf blockiert: Bitte Profil und Konfiguration prüfen.`
- Details: `Konfiguration fehlt. Bitte eine Konfiguration explizit wählen.`

Although the configurations page already showed an active profile with active configurations.

Expanded details were still a long developer/safety bullet wall.

## 3. Diagnosis

1. **Why workspace said configuration missing**  
   `build_processing_run_request` only accepted an explicit `configuration_id` argument or `state.config_list_selected_id`. The workspace start path did not resolve active configurations from the read-only snapshot.

2. **Active configurations present in app state?**  
   Yes — via `state.snapshot.configurations` (`ConfigurationsPageVM`), populated by the configurations reader / read-only backend.

3. **Connected to workspace run state?**  
   No (before fix). Workspace run readiness ignored active snapshot configurations unless the user had previously selected a row on the configurations page (`config_list_selected_id`).

4. **Selected configuration field?**  
   `state.config_list_selected_id` (configurations list selection). No dedicated workspace run-configuration field existed.

5. **Initialized?**  
   Often `None` when the user never opened/selected a configuration list row.

6. **Start gating required explicit selected configuration?**  
   Yes — sandbox gate / local adapter required a non-empty `configuration_id`.

7. **Smallest safe fix**  
   Track-B-only pure resolver (`workspace_configuration_selection.py`) + wire into workspace start/request/UI + compact blocked details (max 5 lines). No Track A, no processing-core.

8. **Why real processing remains blocked after config fix**  
   Core sandbox runner remains unbound (`sandbox_core_runner_unbound` / Core-Bridge missing). UI correctly surfaces Core-Bridge blocker once configuration is resolved.

## 4. Configuration state before fix

- Active profile visible on profiles/configurations pages.
- Active configurations present in snapshot.
- Workspace start request often had `configuration_id=None`.
- Gate reason: `blocked_missing_configuration` → user-facing “Konfiguration fehlt…”.

## 5. Configuration resolution after fix

New helper: `invoice_tool/ui_v2/workspace_configuration_selection.py`

- No active profile → `Profil fehlt. Bitte Profil vorbereiten.`
- Active profile, no active configs → `Keine aktive Konfiguration vorhanden.`
- Exactly one active (non-unmatched) config → auto-select.
- Multiple active configs → stable default = first by `sort_index` / display order; show name + `Ändern über Konfigurationen`.
- Unmatched never auto-selected as normal run target.
- Resolved id written to `config_list_selected_id` on start for visible continuity.

Workspace shows compact Lauf-Setup:

- Profil / Konfiguration / Eingang / Ausgang

## 6. Start blocker before/after

| Phase | Primary blocker (with folders + active configs) |
| --- | --- |
| Before | Configuration missing (`Konfiguration fehlt…`) |
| After | Core-Bridge / Sandbox not connected |

## 7. Details simplification

Default expanded details capped at 5 lines:

1. `Keine Originalordner wurden verwendet.`
2. `Produktive Verarbeitung ist gesperrt.`
3. `Export bleibt Vorschau.`
4. `Technischer Blocker: Core-Bridge fehlt.` (only when relevant)
5. `Konfiguration: <name or fehlt>`

Long sandbox readiness bullet wall is no longer merged into the default details panel.

## 8. Whether real processing is wired or still blocked

Still blocked. No processing-core call, no OCR/AI, no productive execution, no original-folder mutation.

## 9. Exact remaining blocker

`CORE_BRIDGE_REQUIRED_FOR_REAL_SANDBOX_EXECUTION`

User-facing:

`Sandbox nicht verbunden: Die echte Verarbeitung ist in Track B noch nicht sicher angebunden.`

## 10. Files changed

- `invoice_tool/ui_v2/workspace_configuration_selection.py` (new)
- `invoice_tool/ui_v2/pages/workspace.py`
- `tests/test_ui_v2_workspace_configuration_selection.py` (new)
- `tests/test_ui_v2_start_button_noop_and_sandbox_wiring.py`
- `tests/test_ui_v2_manual_test_ux_dense_layout.py`
- `docs/audits/KI_RECHNUNGEN_UI_V2_WORKSPACE_CONFIG_SELECTION_AND_BLOCKED_DETAILS_FIX_2026-07-22.md`

## 11. Tests run and results

Focused:

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_workspace_configuration_selection.py \
  tests/test_ui_v2_start_button_noop_and_sandbox_wiring.py \
  tests/test_ui_v2_manual_test_ux_dense_layout.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_configurations_page.py \
  tests/test_ui_v2_profiles_page.py
```

Result: **77 passed**

Full Track-B UI-v2:

```text
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Result: **468 passed, 44 skipped**

## 12. Confirmation: no Track A change

Confirmed — Track A protected files untouched.

## 13. Confirmation: no processing-core change

Confirmed — processing-core protected files untouched; no new processing-core imports.

## 14. Confirmation: no productive processing

Confirmed — `productive_execution_allowed=False`, dry-run only, productive hold preserved.

## 15. Confirmation: no original folders touched

Confirmed — no original-folder processing; sandbox confinement unchanged.

## 16. Manual next test instruction

1. Launch Track-B UI-v2.
2. Ensure an active profile with at least one active configuration exists (Configurations page).
3. Open Workspace; confirm Lauf-Setup shows Profil + Konfiguration (auto/default).
4. Choose sandbox input + output folders.
5. Click **Sandbox-Lauf starten**.
6. Expect primary blocker: **Sandbox nicht verbunden / Core-Bridge**, not “Konfiguration fehlt”.
7. Expand **Details anzeigen** — expect ≤5 short lines, no long sandbox bullet wall.
8. Confirm no fake success results and no file mutations.
