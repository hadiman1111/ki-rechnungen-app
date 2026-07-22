# KI-Rechnungen Track B UI-v2 — LocalProcessingAdapter Output Folder and Dry Gate

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_LOCAL_PROCESSING_ADAPTER_OUTPUT_FOLDER_AND_DRY_GATE_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Local Processing Adapter Dry Gate

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_LOCAL_PROCESSING_ADAPTER_OUTPUT_FOLDER_AND_DRY_GATE_01`

## 2. Purpose

Make Track-B UI-v2 `LocalProcessingAdapter` readiness honest and safe:

1. `output_folder` must be explicit before readiness.
2. Dry/no-mutation capability must be an explicit blocking gate.
3. Productive processing stays blocked.
4. No real PDFs, no real invoice folder mutation, no processing-core edits, no Track A.

## 3. Files changed

| Path | Change |
|---|---|
| `invoice_tool/ui_v2/processing_state.py` | Gate fields + `MSG_DRY_RUN_UNAVAILABLE` |
| `invoice_tool/ui_v2/local_processing_adapter.py` | Explicit output validation + dry/execution gate |
| `invoice_tool/ui_v2/state.py` | `workspace_output_folder_override` (explicit only) |
| `invoice_tool/ui_v2/pages/workspace.py` | Wire output override; honesty copy for missing output / dry gate |
| `tests/test_ui_v2_local_processing_adapter.py` | Output + dry-gate coverage |
| `tests/test_ui_v2_workspace_processing_contract.py` | Workspace honesty for output/dry |
| `tests/test_ui_v2_processing_contract.py` | Gate fields on `ProcessingRunState` |
| `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_LOCAL_PROCESSING_ADAPTER_OUTPUT_FOLDER_AND_DRY_GATE_2026-07-21.md` | this audit |

## 4. Output-folder validation behavior

- Missing/blank `output_folder` → `not_configured` with exact message:  
  `Ausgabeordner fehlt. Bitte wähle einen Zielordner, bevor eine Verarbeitung vorbereitet wird.`
- Output comes only from explicit request field / `workspace_output_folder_override`.
- Never defaults to Desktop, `/Users/…`, SOMAA, project invoice folders, or other private paths.
- Known private path tokens (SOMAA/Bismarck/AMEX/voba/…) are rejected via string/token check only.
- Adapter does **not** create `output_folder`.
- Adapter does **not** write into `output_folder`.
- Validation performs **no filesystem IO**.

## 5. Dry/no-mutation gate behavior

Adapter exposes:

| Marker | Meaning in this task |
|---|---|
| `core_dry_run_status` | `unsupported_without_core_change` |
| `dry_run_gate` | `unsupported_without_core_change` |
| `execution_gate` | `disabled` (ready/validate), `productive_blocked` (`dry_run=False`), `unsupported_without_core_change` (dry start) |

`start_run` with `dry_run=True` after confirmation returns blocked with:

> Dry-Run ohne Dateiveränderung ist im lokalen Core noch nicht verfügbar.

No core import/call. No PDF processing. No mutation.

## 6. Core dry/no-mutation availability finding

**Finding: `CORE_DRY_GATE_REQUIRES_CORE_CHANGE` / unsupported.**

Read-only inspection of `invoice_tool/run.py` / `processing.py`:

- `run_once(source, output, …)` has **no** dry/no-mutation flag.
- It always creates `input_snapshot`, runs processing, and writes/moves outputs.
- No safe Track-B-callable dry entrypoint exists without changing processing-core.

Therefore the adapter keeps execution blocked and documents the missing boundary instead of calling core.

## 7. Workspace behavior if changed

- Added `UiV2State.workspace_output_folder_override` (default `None`).
- `build_processing_run_request` maps only that explicit override to `output_folder`.
- Default service remains `NotYetConnectedProcessingService`.
- Honesty copy surfaces missing-output and dry-unavailable messages (no fake running/completed).
- No new automatic folder dialog required for this task; no path persistence defaults.

## 8. Why this does not process real PDFs

- No import/call of processing-core.
- Dry/productive gates return blocked before any pipeline entry.
- Tests assert PDF bytes and directory listings unchanged.

## 9. Why this does not touch real invoice folders

- Validation/start paths never list/read/write folders.
- Workspace does not invent private/local invoice paths.
- Tests use synthetic temp/relative paths only.

## 10. Why this does not touch Track A

Allowed edits only under `invoice_tool/ui_v2/**`, Track-B tests, and this audit.  
Forbidden Track-A surfaces (`app_main.py`, `app_internal_launcher.py`, legacy `ui_*.py`) were not modified.

## 11. Why this does not touch processing-core

Core was inspected read-only. No safe dry API found → **no core edits**. Adapter blocks with `unsupported_without_core_change` instead of calling `run_once`.

## 12. Tests added/updated

- **Updated:** `tests/test_ui_v2_local_processing_adapter.py`
- **Updated:** `tests/test_ui_v2_workspace_processing_contract.py`
- **Updated:** `tests/test_ui_v2_processing_contract.py`

Coverage includes missing output readiness, no defaulting, no FS create/write, private token rejection without FS, dry-gate visibility/blocking, import boundary, no PDF/real-folder mutation, workspace honesty.

## 13. Tests run and results

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_local_processing_adapter.py \
  tests/test_ui_v2_processing_contract.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_policy_runtime_bridge.py

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Result: **61 passed** (focused) · **175 passed, 44 skipped** (full Track-B UI-v2 / SaaS UI-v2 suite).

## 14. Generalization confirmation

- No Hadi/SOMAA/Bismarck/AMEX/voba hardcoded defaults as invented paths
- No Desktop/`/Users`/private path defaults
- Filename is never source of truth
- No fake payment/account/business classification results
- Unknown/incomplete policy → honest `not_configured` / `blocked` / review messaging
- Business/payment/account rules remain profile-configurable via bridge intent
- Supplier IBAN alone / generic card text remain unsafe overlays in bridge
- UI wording stays generic German product copy
- Track A untouched; processing-core untouched

## 15. Remaining gaps

1. Real dry-run bridge if/when core exposes a safe dry/no-mutation mode (requires PO decision / core change)
2. Productive execution PO gate (`dry_run=False` → real wrapper/`run_once`)
3. Explicit output-folder picker UX in workspace (field exists; dialog optional later)
4. Review/settings navigation polish
5. Policy editor controls
6. Real run result display mapping

## 16. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_LOCAL_PROCESSING_ADAPTER_OUTPUT_FOLDER_PICKER_OR_CORE_DRY_PO_GATE_01`

Choose one PO path:

- **A)** Workspace output-folder picker UX (Track B only), still blocked by dry gate, or  
- **B)** PO decision for `CORE_DRY_GATE_REQUIRES_CORE_CHANGE` vs keep productive blocked until later.
