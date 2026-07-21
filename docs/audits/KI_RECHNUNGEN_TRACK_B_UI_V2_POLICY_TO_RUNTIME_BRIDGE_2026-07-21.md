# KI-Rechnungen Track B UI-v2 — Policy-to-Runtime Bridge

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_POLICY_TO_RUNTIME_BRIDGE_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Policy Runtime Bridge

## 1. Purpose

Create a safe Track-B-only bridge that translates UI-v2 classification/profile policy into a structured runtime-intent shape for future processing requests — without executing the processing core, processing PDFs, or mutating real invoice folders.

## 2. Files changed

| Path | Change |
|---|---|
| `invoice_tool/ui_v2/policy_runtime_bridge.py` | **new** — `RuntimePolicyIntent`, `RuntimePolicyBridgeResult`, `build_runtime_policy_intent` |
| `invoice_tool/ui_v2/processing_contract.py` | optional `policy_intent` / `policy_bridge_result` on `ProcessingRunRequest`; policy validation in `NotYetConnectedProcessingService` |
| `invoice_tool/ui_v2/processing_state.py` | `MSG_POLICY_NOT_READY`, `MSG_POLICY_BLOCKED` |
| `invoice_tool/ui_v2/pages/workspace.py` | resolve policy bridge into run request; honesty copy shows incomplete/blocked policy hints |
| `tests/test_ui_v2_policy_runtime_bridge.py` | **new** |
| `tests/test_ui_v2_processing_contract.py` | updated for policy-carrying requests |
| `tests/test_ui_v2_workspace_processing_contract.py` | request/policy bridge assertions |
| `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_POLICY_TO_RUNTIME_BRIDGE_2026-07-21.md` | this audit |

## 3. Policy bridge design

- Input: UI-v2 `ClassificationPolicy`, profile/config dicts, or draft objects with `classification_policy`
- Output: `RuntimePolicyBridgeResult` with status `ready` | `incomplete` | `blocked`
- Missing policy → `incomplete` + honest German messages
- Unsafe policy (filename-as-truth, supplier IBAN as payer evidence, etc.) → `blocked`
- Safe overlays always force: filename not SOT, supplier IBAN not payer, unknown → `unklar`/review, profile-configured evidence required
- No file IO, no PDF processing, no processing-core imports

## 4. RuntimePolicyIntent model

Fields:

1. `invoice_detection_policy`
2. `payment_evidence_policy`
3. `business_assignment_policy`
4. `review_policy`
5. `filename_policy`
6. `unknown_evidence_policy`
7. `source_of_truth_policy`

Source of truth is document content + configured profile evidence — never filename.

## 5. ProcessingRunRequest integration

`ProcessingRunRequest` gained optional:

- `policy_intent: RuntimePolicyIntent | None`
- `policy_bridge_result: RuntimePolicyBridgeResult | None`

`NotYetConnectedProcessingService`:

- folder missing → `not_configured`
- policy incomplete/missing → `not_configured` with policy messages
- policy blocked → `blocked` with policy messages
- policy ready → still `blocked` (adapter not connected)
- never emits fake results; never processes PDFs

`FutureProcessingAdapter` documents that a later bounded adapter may consume `RuntimePolicyIntent` under PO gate.

## 6. Workspace / profile behavior

- `resolve_workspace_policy_bridge(state)` maps active SaaS draft policy or safe blank defaults
- `build_processing_run_request` attaches `policy_intent` + `policy_bridge_result`
- Honesty copy can surface:
  - „Verarbeitungsregeln sind noch nicht vollständig konfiguriert.“
  - „Unklare Nachweise werden später zur Prüfung gestellt.“
- No auto-processing, no fake results, no private path defaults
- No new complex policy editor controls (remain a later gap)

## 7. Why this does not process PDFs

Bridge and contract only build/validate data objects. They never open folders, list files, call OCR/PDF code, or import the processing core. `start_run` still returns honest blocked/not_configured states.

## 8. Why this does not touch Track A

No edits to `app_main.py`, `app_internal_launcher.py`, or legacy Track-A `invoice_tool/ui_*.py` surfaces. Changes are confined to `invoice_tool/ui_v2/**`, Track-B tests, and this audit.

## 9. Why this does not touch processing-core

No edits to:

- `invoice_tool/processing.py`
- `invoice_tool/routing.py`
- `invoice_tool/routing_guards.py`
- `invoice_tool/classification.py`
- `invoice_tool/target_routing.py`
- `invoice_tool/run.py`

Bridge/contract modules do not import these modules.

## 10. Tests added / updated

**Added**

- `tests/test_ui_v2_policy_runtime_bridge.py`

**Updated**

- `tests/test_ui_v2_processing_contract.py`
- `tests/test_ui_v2_workspace_processing_contract.py`

Coverage includes: structured intent, filename never SOT, unknown → review, profile-configured evidence, supplier IBAN not payer, generic card unclear, no private defaults, no core imports, request carries intent, null service still does not process.

## 11. Tests run and results

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
  tests/test_ui_v2_policy_runtime_bridge.py \
  -q
→ 91 passed

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py -q
→ 150 passed, 44 skipped
```

No GUI window tests. No PDF processing. No builds.

## 12. Generalization confirmation

- No Hadi/SOMAA/Bismarck/AMEX/voba hardcoded defaults in bridge/contract/workspace wiring
- No private local path defaults
- No filename-as-truth behavior
- No fake payment/account/business classification results
- Unknown/incomplete policy → honest `not_configured` / `blocked` / review messaging
- Business/payment/account rules remain profile-configurable
- Supplier IBAN alone is not payer evidence
- Generic card text without configured account reference remains unclear/review
- UI wording is generic product German
- Track A untouched
- Processing/routing/classification core untouched

## 13. Remaining gaps

1. Real bounded `LocalProcessingAdapter` (PO gate; may later consume `RuntimePolicyIntent`)
2. Review/settings navigation polish
3. Policy editor controls
4. Real run result display

## 14. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_LOCAL_PROCESSING_ADAPTER_01` — design/implement a PO-gated, bounded LocalProcessingAdapter that consumes `RuntimePolicyIntent` without uncontrolled core wiring and without filename-as-truth or private defaults.
