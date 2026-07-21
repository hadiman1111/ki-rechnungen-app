# KI-Rechnungen Track B UI-v2 — Bounded Processing Service Contract

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_PROCESSING_SERVICE_CONTRACT_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Processing Contract

## 1. Purpose

Create a bounded, testable Track-B UI-v2 processing service contract without starting productive processing and without changing the processing/routing/classification core.

UI-v2 can now express run requests and receive honest status/results shapes while the default adapter remains not connected.

## 2. Files changed

| Path | Change |
|---|---|
| `invoice_tool/ui_v2/processing_contract.py` | **new** — request + protocol + `NotYetConnectedProcessingService` / `FutureProcessingAdapter` |
| `invoice_tool/ui_v2/processing_state.py` | **new** — status/result/review state models + honest message constants |
| `invoice_tool/ui_v2/state.py` | wiring: `processing_service`, `processing_run_state` |
| `invoice_tool/ui_v2/pages/workspace.py` | contract request/start helpers + honesty copy for idle/not_configured/blocked + CTA |
| `invoice_tool/ui_v2/components.py` | optional start CTA on workspace run panel |
| `tests/test_ui_v2_processing_contract.py` | **new** |
| `tests/test_ui_v2_workspace_processing_contract.py` | **new** |
| `tests/test_ui_v2_workspace_empty_state.py` | updated for CTA/adapter hint assertions |
| `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_PROCESSING_SERVICE_CONTRACT_2026-07-21.md` | this audit |

## 3. Contract / state design

### Request (`ProcessingRunRequest`)

- Optional `input_folder` / `output_folder` (serialized path strings)
- Optional `profile_id` / `configuration_id`
- `dry_run` defaults to `True`
- `source` must be `explicit_user_selection` for a configured request; blank default uses `unset`
- No private/local path defaults

### State (`ProcessingRunState`)

Statuses: `idle` | `not_configured` | `ready` | `running` | `completed` | `failed` | `blocked`

Also: `message`, optional `run_id`, `results`, `review_items`, `errors`.

### Result summary (`ProcessingResultSummary`)

Generic document fields only (`document_name`, `document_type`, `classification_status`, labels, optional `target_hint`). No payment/private fields by default.

### Service protocol

- `validate_request(request)`
- `start_run(request)`
- `get_status(run_id)`
- `get_results(run_id)`

### Safe default

`NotYetConnectedProcessingService` (= `NullProcessingService`):

- never processes PDFs
- never reads real folders
- returns `not_configured` / `blocked` / `idle` with honest messages
- never emits fake results or review items

`FutureProcessingAdapter` delegates to the same safe default and documents that a real bridge is a separate PO-gated task. It does **not** import `processing.py` / `run.py`.

## 4. Workspace behavior after wiring

- CTA **„Verarbeitung starten“** is present on the run panel.
- Click calls `apply_start_processing` → contract service only.
- Without folder: `not_configured`.
- With explicit folder override: `blocked` („Lauf-Adapter noch nicht angebunden“).
- No auto-run, no fake results, no automatic private folder selection.
- Results tab remains empty unless `workspace.results` already contains real payload data.
- Honesty copy covers idle / not_configured / blocked.

## 5. Why this does not process PDFs

The default service never opens folders, never lists files, never calls OCR/PDF code, and never imports the processing core. `start_run` only returns an honest state object.

## 6. Why this does not touch Track A

No edits to `app_main.py`, `app_internal_launcher.py`, or legacy `invoice_tool/ui_*.py` Track-A surfaces. Contract lives only under `invoice_tool/ui_v2/**`.

## 7. Why this does not touch processing-core

No edits to:

- `invoice_tool/processing.py`
- `invoice_tool/routing.py`
- `invoice_tool/routing_guards.py`
- `invoice_tool/classification.py`
- `invoice_tool/target_routing.py`
- `invoice_tool/run.py`

Contract modules do not import these modules.

## 8. Tests added / updated

**Added**

- `tests/test_ui_v2_processing_contract.py`
- `tests/test_ui_v2_workspace_processing_contract.py`

**Updated**

- `tests/test_ui_v2_workspace_empty_state.py`

Coverage includes: null service safety, no private defaults, honest not-connected state, workspace honesty, start handler core-isolation, no fake results, Track-A/core import boundary.

## 9. Tests run and results

```text
.venv/bin/python -m pytest \
  tests/test_saas_ui_v2_classification_policy.py \
  tests/test_saas_product_model.py \
  tests/test_saas_ui_v2_profile_store.py \
  tests/test_saas_ui_v2_profile_state.py \
  tests/test_saas_ui_v2_profile_surface.py \
  tests/test_ui_v2_workspace_empty_state.py \
  tests/test_ui_v2_processing_contract.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  -q
→ 72 passed

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py -q
→ 131 passed, 44 skipped
```

No GUI window tests. No PDF processing. No builds.

## 10. Generalization confirmation

- No Hadi/SOMAA/Bismarck/AMEX/voba hardcoded defaults in contract/workspace wiring
- No private local path defaults
- No filename-as-truth behavior
- No fake payment/account/business classification results
- Unknown/no adapter → honest not-connected / empty / review-later messaging
- Business/payment/account rules remain profile-configurable elsewhere
- UI wording is generic product German
- Track A untouched
- Processing/routing/classification core untouched

## 11. Remaining gaps

1. **GAP-P0-03:** policy-to-runtime bridge  
2. Real bounded processing adapter (PO gate; may later call core under strict bounds)  
3. Review/settings navigation polish  
4. Policy editor controls  

## 12. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_POLICY_TO_RUNTIME_BRIDGE_01` — connect classification/profile policy surfaces to runtime selection without enabling uncontrolled productive PDF processing; keep a separate follow-up for a real bounded processing adapter behind PO gate.
