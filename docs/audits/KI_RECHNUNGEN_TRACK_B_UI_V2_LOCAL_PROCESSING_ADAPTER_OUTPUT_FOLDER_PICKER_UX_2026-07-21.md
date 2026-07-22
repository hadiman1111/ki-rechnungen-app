# KI-Rechnungen Track B UI-v2 — LocalProcessingAdapter Output Folder Picker UX

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_LOCAL_PROCESSING_ADAPTER_OUTPUT_FOLDER_PICKER_UX_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Output Folder Picker UX

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_LOCAL_PROCESSING_ADAPTER_OUTPUT_FOLDER_PICKER_UX_01`

## 2. Purpose

Implement a safe Track-B-only folder selection UX/state layer for UI-v2 so users can explicitly select input and output folders before any future processing run.

This task is UX/state readiness only:

- no productive processing
- no PDF processing
- no folder creation
- no folder scan
- no processing-core change
- no Track A change

## 3. Files changed

| Path | Change |
|---|---|
| `invoice_tool/ui_v2/state.py` | Source markers + setters for explicit input/output folder selection |
| `invoice_tool/ui_v2/pages/workspace.py` | Folder selection VM, native picker wiring, honesty copy, request wiring |
| `invoice_tool/ui_v2/components.py` | Folder selection panel/row components |
| `tests/test_ui_v2_workspace_folder_selection.py` | New non-GUI folder-selection coverage |
| `tests/test_ui_v2_workspace_processing_contract.py` | Missing-input honesty + setter → request wiring |
| `tests/test_ui_v2_workspace_empty_state.py` | Empty-state copy aligned to dual-folder wording |
| `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_LOCAL_PROCESSING_ADAPTER_OUTPUT_FOLDER_PICKER_UX_2026-07-21.md` | this audit |

## 4. Input folder state behavior

- `UiV2State.workspace_input_folder_override` defaults to `None`
- `UiV2State.workspace_input_folder_source` defaults to `unset`
- `set_workspace_input_folder` / `apply_workspace_input_folder_selection` store a path string and mark `explicit_user_selection`
- No Desktop / `/Users` / SOMAA / private invoice folder defaults
- No automatic creation, scan, or persistence of private paths

## 5. Output folder state behavior

- `UiV2State.workspace_output_folder_override` defaults to `None`
- `UiV2State.workspace_output_folder_source` defaults to `unset`
- `set_workspace_output_folder` / `apply_workspace_output_folder_selection` store a path string and mark `explicit_user_selection`
- Never defaulted; never created; never written to by this task

## 6. Folder picker / placeholder behavior

- Workspace shows an explicit Ordnerauswahl panel:
  - empty: „Kein Eingangsordner gewählt.“ / „Kein Ausgabeordner gewählt.“
  - selected: safe path display string
  - buttons: „Eingangsordner wählen“ / „Ausgabeordner wählen“
- Existing safe native picker (`choose_target_folder`) is wired to UI state only
- Picker does not scan folders, create directories, or process PDFs
- No placeholder-handler markers remain in workspace source (UX gate clean)

## 7. Request wiring behavior

- `build_processing_run_request` reads only explicit overrides
- `source` becomes `explicit_user_selection` when UI state has explicit folder selection
- Missing input → LocalProcessingAdapter `not_configured` (`MSG_MISSING_INPUT`)
- Missing output → LocalProcessingAdapter `not_configured` (`MSG_MISSING_OUTPUT`)
- Explicit test path strings are carried without filesystem touch

## 8. Dry/no-mutation gate status

Unchanged and still blocking:

- `core_dry_run_status` / `dry_run_gate` = `unsupported_without_core_change`
- Confirmed start with `dry_run=True` returns blocked with dry-run unavailable message
- Productive execution remains not released
- No processing-core dry API introduced

## 9. Workspace behavior

- Honest dual-folder empty states and pick controls
- Start status surfaces missing input/output, policy incomplete, dry-run unavailable, productive not released
- CTA remains non-productive; no fake results; no auto-run

## 10. Why this does not process real PDFs

- Folder selection writes path strings into UI state only
- Adapter validate/start paths do not import or call processing-core
- Dry/productive gates block before any pipeline entry
- Tests assert PDF bytes unchanged

## 11. Why this does not touch real invoice folders

- No directory creation, listing, or writes in selection helpers
- No private path defaults invented by workspace/state
- Tests use synthetic temp/relative path strings only

## 12. Why this does not touch Track A

Allowed edits only under `invoice_tool/ui_v2/**`, Track-B tests, and this audit.  
Forbidden Track-A surfaces (`app_main.py`, `app_internal_launcher.py`, legacy `ui_*.py`) were not modified.

## 13. Why this does not touch processing-core

No edits to `processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, or `run.py`.  
Dry gate remains `unsupported_without_core_change`.

## 14. Tests added/updated

- **Added:** `tests/test_ui_v2_workspace_folder_selection.py`
- **Updated:** `tests/test_ui_v2_workspace_processing_contract.py`
- **Updated:** `tests/test_ui_v2_workspace_empty_state.py`

## 15. Tests run and results

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_local_processing_adapter.py \
  tests/test_ui_v2_processing_contract.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_policy_runtime_bridge.py \
  tests/test_ui_v2_workspace_folder_selection.py \
  tests/test_ui_v2_workspace_empty_state.py

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Result: **86 passed** (focused) · **193 passed, 44 skipped** (full Track-B UI-v2 / SaaS UI-v2 suite).

## 16. Generalization confirmation

- No Hadi/SOMAA/Bismarck/AMEX/voba hardcoded folder defaults
- No Desktop/`/Users`/private path defaults
- Filename is never source of truth
- No fake payment/account/business classification results
- No folder scan / folder creation / PDF processing
- Unknown/incomplete policy → honest `not_configured` / `blocked` / review messaging
- Business/payment/account rules remain profile-configurable via bridge intent
- UI wording stays generic German product copy
- Track A untouched; processing-core untouched

## 17. Remaining gaps

1. Host/runtime polish for native folder dialogs in all launch contexts (state wiring already present)
2. Real dry-run bridge if/when core exposes a safe dry/no-mutation mode (requires PO / core change)
3. Productive execution PO gate
4. Review/settings navigation polish
5. Policy editor controls
6. Real run result display mapping

## 18. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_CORE_DRY_PO_GATE_OR_PRODUCTIVE_EXECUTION_HOLD_01`

PO decision required:

- keep productive/dry execution blocked until a safe core dry/no-mutation API exists, or
- explicitly authorize a separate processing-core dry-gate change (out of Track-B UX scope).
