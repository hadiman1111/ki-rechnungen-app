# KI-Rechnungen Track B UI-v2 — Bounded LocalProcessingAdapter Implementation

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_LOCAL_PROCESSING_ADAPTER_IMPLEMENTATION_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Bounded Local Processing Adapter  
**PO decision basis:** `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_LOCAL_PROCESSING_ADAPTER_PO_GATE_PREP_2026-07-21.md`

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_LOCAL_PROCESSING_ADAPTER_IMPLEMENTATION_01`

## 2. Purpose

Implement a bounded Track-B UI-v2 `LocalProcessingAdapter` that connects the UI-v2 `ProcessingServiceProtocol` to a future local pipeline wrapper only after explicit user inputs and ready `RuntimePolicyIntent` — without auto-run, private defaults, fake results, Track-A changes, or processing-core edits.

## 3. Files changed

| Path | Change |
|---|---|
| `invoice_tool/ui_v2/local_processing_adapter.py` | **new** — bounded adapter |
| `invoice_tool/ui_v2/processing_contract.py` | `user_confirmed_start` on request; factory `make_local_processing_adapter()` |
| `invoice_tool/ui_v2/processing_state.py` | `MSG_PRODUCTIVE_NOT_RELEASED` |
| `invoice_tool/ui_v2/pages/workspace.py` | CTA sets `user_confirmed_start=True`; keeps default NotYetConnected; no private profile fallback |
| `tests/test_ui_v2_local_processing_adapter.py` | **new** |
| `tests/test_ui_v2_processing_contract.py` | assert `user_confirmed_start` default |
| `tests/test_ui_v2_workspace_processing_contract.py` | CTA confirmation + output-folder honesty |
| `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_LOCAL_PROCESSING_ADAPTER_IMPLEMENTATION_2026-07-21.md` | this audit |

## 4. LocalProcessingAdapter design

- Module: `invoice_tool/ui_v2/local_processing_adapter.py`
- Implements `ProcessingServiceProtocol` (`validate_request`, `start_run`, `get_status`, `get_results`)
- Opt-in only via `UiV2State.processing_service = LocalProcessingAdapter()` or `make_local_processing_adapter()`
- Default workspace service remains `NotYetConnectedProcessingService`
- No top-level import of `invoice_tool.processing` / `run` / `routing` / `classification`
- In-memory `_runs` dict only (unused for productive rows in this task)
- Future wrapper marker: `_run_core_dry_no_mutation(...)`

## 5. Request validation behavior

`validate_request` checks structure only (no folder reads, no PDF IO):

| Missing / invalid | Status |
|---|---|
| `source != explicit_user_selection` | `not_configured` |
| input folder | `not_configured` |
| output folder | `not_configured` |
| profile_id | `not_configured` |
| configuration_id | `not_configured` |
| policy missing / incomplete | `not_configured` |
| policy blocked / unsafe | `blocked` |
| filename-as-truth flags | `blocked` |
| all gates pass | `ready` (logical readiness only) |

Never fills private defaults. Never infers from filename.

## 6. Start-run behavior

1. Re-runs `validate_request`; returns early on `not_configured` / `blocked`.
2. Requires `user_confirmed_start is True` else `blocked`.
3. Requires `dry_run is True` for this task; `dry_run=False` → `blocked` with productive-not-released message.
4. Calls `_run_core_dry_no_mutation`, which returns `blocked` without importing or calling core.
5. Emits no result/review rows and no `run_id`.

Honest blocked message (required wording present):

> Lokaler Verarbeitungsadapter ist vorbereitet, aber produktive Ausführung ist noch nicht freigegeben.

## 7. Core dry/no-mutation status

**Blocked / not implemented as a real core call.**

Reason: `invoice_tool.run.run_once` has no dry/no-mutation flag. Invoking it always snapshots sources and runs productive processing paths. Per PO-Gate `TRACK_B_WRAPPER_ONLY` and this task’s safety rule, the adapter must not call core until a safe dry API exists or a productive execution gate is approved. `_run_core_dry_no_mutation` is the documented future wrapper marker and refuses by default.

## 8. Workspace behavior if changed

- Default service unchanged: `NotYetConnectedProcessingService`
- CTA „Verarbeitung starten“ sets `user_confirmed_start=True`
- `output_folder` remains `None` until an explicit output UX exists → LocalProcessingAdapter would return `not_configured` if injected
- No new folder dialogs, no path persistence defaults, no output-folder creation, no fake result rows
- Profile id only from explicit CTA/`profile_id` argument (no silent `selected_profile_id="local"` fallback)

## 9. Why this does not process real PDFs

- No import/call of processing-core
- `start_run` ends in blocked state before any pipeline entry
- Tests assert PDF bytes and directory listings unchanged

## 10. Why this does not touch real invoice folders

- Adapter never lists/reads/writes folders
- Workspace does not invent private/local paths
- No real invoice folders staged or used in tests (temp fixtures only)

## 11. Why this does not touch Track A

Allowed edits only under `invoice_tool/ui_v2/**`, Track-B tests, and this audit doc.  
Forbidden Track-A surfaces (`app_main.py`, `app_internal_launcher.py`, legacy `ui_*.py`) were not modified.

## 12. Why this does not touch processing-core

Boundary decision remains `TRACK_B_WRAPPER_ONLY`. Core modules were inspected read-only; no dry API found → no core edits; adapter blocks instead of calling `run_once`.

## 13. Tests added/updated

- **Added:** `tests/test_ui_v2_local_processing_adapter.py`
- **Updated:** `tests/test_ui_v2_processing_contract.py`
- **Updated:** `tests/test_ui_v2_workspace_processing_contract.py`

Coverage includes required inputs, policy readiness, confirmation gate, import boundary, no FS/PDF mutation, no fake results, no private tokens, filename-not-SOT, unknown→review intent, Track-A import absence.

## 14. Tests run and results

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_local_processing_adapter.py \
  tests/test_ui_v2_processing_contract.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_policy_runtime_bridge.py

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Result: **166 passed, 44 skipped** (Track-B UI-v2 / SaaS UI-v2 suite).

## 15. Generalization confirmation

- No Hadi/SOMAA/Bismarck/AMEX/voba hardcoded defaults in changed sources
- No private local paths invented
- Filename is never source of truth (policy gate + bridge overlays)
- No fake payment/account/business classification results
- Unknown/incomplete policy → honest `not_configured` / `blocked` / review messaging
- Business/payment/account rules remain profile-configurable via bridge intent
- Supplier IBAN alone / generic card text remain unsafe overlays in bridge
- UI wording stays generic German product copy
- Track A untouched; processing-core untouched

## 16. Remaining gaps

1. Real run approval / productive execution gate (`dry_run=False` → real wrapper/`run_once`)
2. Safe core dry/no-mutation API (would require new PO decision if core change needed)
3. Explicit output-folder UX in workspace
4. Review/settings navigation polish
5. Policy editor controls
6. Real run result display mapping (`ProcessingResultSummary` / review / errors)

## 17. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_LOCAL_PROCESSING_ADAPTER_OUTPUT_FOLDER_AND_DRY_GATE_01`

Scope suggestion:

1. Explicit output-folder selection in UI-v2 workspace (no private defaults).
2. Keep LocalProcessingAdapter opt-in; validate ready only with input+output+profile+config+policy+confirmation.
3. Separate PO gate before any productive `run_once` mutation or core dry-flag change.
