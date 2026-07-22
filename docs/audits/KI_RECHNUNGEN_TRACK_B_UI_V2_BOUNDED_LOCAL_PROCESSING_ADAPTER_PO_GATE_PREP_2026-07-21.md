# KI-Rechnungen Track B UI-v2 — Bounded LocalProcessingAdapter PO-Gate Prep

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_LOCAL_PROCESSING_ADAPTER_PO_GATE_PREP_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Local Processing Adapter PO-Gate  
**HEAD at prep:** `474f0ce12a10349186fd7c82afd88e6696123d79`

## 1. Purpose

Prepare the Product Owner gate for a future bounded `LocalProcessingAdapter`.

This document defines how Track-B UI-v2 may later connect safely to the existing local processing pipeline **without**:

- polluting the general product UI with private/tenant defaults,
- auto-starting productive processing,
- mutating processing-core policy,
- changing Track A,
- inventing fake payment/private results.

**This task is docs-only.** No adapter implementation, no PDF processing, no real invoice mutation.

## 2. Purpose (gate outcome)

After PO approval, a separate implementation task may replace `NotYetConnectedProcessingService` / `FutureProcessingAdapter` with a bounded local adapter that:

1. consumes `RuntimePolicyIntent` from `ProcessingRunRequest`,
2. calls the existing local pipeline only through a Track-B wrapper,
3. returns honest `ProcessingRunState` / `ProcessingResultSummary` / `ProcessingReviewItem` shapes.

## 3. Current UI-v2 contract / bridge state

Verified on HEAD `474f0ce…`:

| Component | Status |
|---|---|
| `invoice_tool/ui_v2/processing_contract.py` | present — `ProcessingRunRequest`, `ProcessingServiceProtocol`, `NotYetConnectedProcessingService`, `FutureProcessingAdapter` |
| `invoice_tool/ui_v2/processing_state.py` | present — statuses + result/review models |
| `invoice_tool/ui_v2/policy_runtime_bridge.py` | present — `RuntimePolicyIntent` / `RuntimePolicyBridgeResult` |
| Workspace wiring | `build_processing_run_request` / `apply_start_processing` call contract only |
| Productive processing | **not wired** |
| Fake results | **none** |
| Track A / processing-core | **untouched by current Track-B contract** |

Current runtime behavior:

- Missing explicit input folder / source → `not_configured`
- Policy incomplete/missing → `not_configured` (policy messages)
- Policy blocked/unsafe → `blocked` (policy messages)
- Policy ready + explicit folder → still `blocked` („Lauf-Adapter noch nicht angebunden“)
- `dry_run` defaults to `True`
- `source` must be `explicit_user_selection` for a configured request
- Results/review remain empty unless a future real adapter injects them

## 4. Future LocalProcessingAdapter boundary

### 4.1 Allowed later

A future `LocalProcessingAdapter` (Track B only) may:

1. Implement `ProcessingServiceProtocol` (`validate_request`, `start_run`, `get_status`, `get_results`).
2. Consume `ProcessingRunRequest.policy_intent` / `policy_bridge_result`.
3. Enforce bridge status before any core call:
   - `incomplete` → `not_configured`
   - `blocked` → `blocked`
   - `ready` → proceed only if all other gates pass.
4. Call existing local pipeline **only** via a thin Track-B wrapper (preferred entry: `invoice_tool.run.run_once`).
5. Map core outcomes into UI-v2 contract shapes only:
   - `ProcessingResultSummary`
   - `ProcessingReviewItem`
   - `errors: tuple[str, ...]`
6. Support an adapter-side dry / no-mutation mode first (`dry_run=True` default).
7. Require explicit user action for any non-dry productive start.
8. Keep imports of `invoice_tool.run` / `invoice_tool.processing` confined to the adapter/wrapper module — not in workspace UI widgets, not in the policy bridge.

### 4.2 Must never do automatically

1. Auto-run on app start / page open / profile load.
2. Invent private/local default folders (Hadi/SOMAA/Bismarck/etc.).
3. Hardcode payer/business/account shortcuts (AMEX/voba/private IBANs).
4. Treat filename as source of truth.
5. Treat supplier IBAN alone as payer evidence.
6. Accept generic card text without configured account reference as settled payment.
7. Emit fake payment/private result fields into UI-v2.
8. Mutate Track A launchers or legacy UI.
9. Modify processing-core policy semantics.
10. Process when `policy_bridge_result.status != "ready"`.
11. Process when `source != explicit_user_selection`.
12. Process when input/output/profile/configuration are missing.

## 5. Required explicit user inputs

Before any real (non-dry) run, all of the following are mandatory:

| Input | Rule |
|---|---|
| Explicit input folder | UI-selected path string; no private defaults |
| Explicit output folder | UI-selected path string; no private defaults |
| Selected profile | Explicit `profile_id` (and resolvable profile payload/path for wrapper) |
| Selected configuration | Explicit `configuration_id` when configuration-scoped routing is used |
| Valid `RuntimePolicyIntent` | Bridge status `ready` (not incomplete/blocked) |
| Explicit user action | CTA / confirmed start; never implicit |

Additional request constraints already in contract:

- `source == "explicit_user_selection"`
- Prefer keeping `dry_run=True` until PO approves productive mutation mode

Gap note (current workspace): `build_processing_run_request` currently sets `output_folder=None`. Future implementation must collect an explicit output folder before productive runs; until then validate must return `not_configured`.

## 6. State transitions

Required states (already in `ProcessingStatus`):

```text
idle
  → not_configured   (missing folder/profile/config/policy)
  → blocked          (unsafe policy OR safety gate OR adapter refused)
  → ready            (validate OK; dry/no-mutation preview allowed)
  → running          (explicit start accepted)
  → completed        (run finished; results/review/errors populated honestly)
  → failed           (run aborted with errors; no fake success rows)
```

Rules:

1. `validate_request` never starts productive processing.
2. `ready` means request+policy gates pass; it does **not** imply mutation already happened.
3. `running` only after explicit `start_run` with gates passed.
4. Mid-run failure → `failed` or `blocked` with errors; never silent success.
5. Unknown `run_id` → honest `idle` / `blocked`, empty results.

## 7. Result / review / error shape

### Results

Only `ProcessingResultSummary` rows:

- `document_name`
- `document_type`
- `classification_status`
- `status_label`
- optional `confidence_label`
- optional `target_hint`

**Forbidden by default in UI-v2 result rows:** raw private payment values, private account numbers, fabricated payer/business labels.

### Review

Unclear / unknown evidence → `ProcessingReviewItem`:

- `document_name`
- `reason`
- `status_label` default `"unklar"`

### Errors

Pipeline/IO/config failures → `errors: tuple[str, ...]`  
Errors must stay **separated** from review items (review = unclear evidence; errors = run/system failures).

### Mapping note

Core `ProcessResult` may contain richer fields (`konto`, `payment_field`, amounts, paths). The adapter may use them internally for routing/status mapping but must project only the bounded UI-v2 summary/review/error shapes outward.

## 8. Safety gates

Mandatory for future adapter:

1. No auto-run on app start.
2. No default private folders.
3. No hardcoded Hadi / SOMAA / Bismarck / AMEX / voba defaults.
4. Filename never source of truth (`filename_policy.filename_is_not_source_of_truth == True`).
5. Unknown evidence → review/unclear.
6. Supplier IBAN alone ≠ payer evidence.
7. Generic card text without configured account reference → review/unclear.
8. Bridge `blocked` / `incomplete` refuses start.
9. Productive mutation only when `dry_run=False` **and** PO-approved productive mode is enabled in that task.
10. Source PDFs must not be modified in place (existing `run_once` snapshot design already states this; adapter must not bypass it).

## 9. Generalization rules

1. Generic product German UI only.
2. Profile-configured evidence required for business/payment/account decisions.
3. Source of truth = document content + configured profile evidence.
4. Adapter must not bake tenant-specific routes into UI-v2 modules.
5. Policy overlays from `policy_runtime_bridge` remain authoritative for Track-B intent gating.

## 10. Track A separation

| Surface | Rule |
|---|---|
| `app_main.py` | do not touch |
| `app_internal_launcher.py` | do not touch |
| Legacy `invoice_tool/ui_*.py` Track-A UI | do not touch |
| `app_ui_v2.py` / `invoice_tool/ui_v2/**` | Track-B only surface for adapter wiring |
| Known local dirty legacy files (`ui_profile_dialog.py`, `ui_document_rules.py`) | remain local/unstaged; not part of this work |

Track-B adapter must not change Track-A behavior even if it later calls shared core helpers.

## 11. Processing-core boundary decision

### Decision: `TRACK_B_WRAPPER_ONLY`

**Preferred and selected after local inspection.**

Rationale:

1. `invoice_tool.run.run_once(source, output, *, config_path=, profile_path=)` already accepts explicit caller-supplied paths and documents „No hard-coded user paths“.
2. Core already snapshots inputs and avoids in-place source mutation.
3. Track-B can enforce `RuntimePolicyIntent` as a **preflight gate** in the wrapper before any core call.
4. Result projection into `ProcessingResultSummary` / review / errors can live entirely in Track B.
5. Adapter-side `dry_run=True` can validate + refuse mutation without requiring a core dry-run flag.
6. Profile/rules materialization for `run_once(profile_path=…)` can remain a Track-B wrapper concern (temp/profile snapshot), reusing existing `run_once` profile compilation path — without editing core modules.

### Not selected

| Option | Why not now |
|---|---|
| `CORE_COMPATIBILITY_SHIM_REQUIRED` | No proven need for a core shim; wrapper can call `run_once` and map results |
| `CORE_CHANGE_REQUIRED` | No blocker found that forces core behavior change before a bounded adapter |

### Explicit non-goals for first implementation

- Do not modify:
  - `invoice_tool/processing.py`
  - `invoice_tool/routing.py`
  - `invoice_tool/routing_guards.py`
  - `invoice_tool/classification.py`
  - `invoice_tool/target_routing.py`
  - `invoice_tool/run.py`
- Do not inject Track-B SaaS policy objects directly into core modules.
- If later inspection proves SaaS→legacy profile materialization insufficient for safe productive runs, escalate a **new PO gate** before any core change (`CORE_COMPATIBILITY_SHIM_REQUIRED` / `CORE_CHANGE_REQUIRED`).

## 12. PO decision required before implementation

**Yes — PO approval required** before implementation task starts.

PO must explicitly approve:

1. Proceed with `TRACK_B_WRAPPER_ONLY` for first adapter.
2. First implementation ships dry/no-mutation mode first (`dry_run=True` path).
3. Productive mutation (`dry_run=False` → real `run_once`) is either:
   - deferred to a follow-up PO gate, **or**
   - explicitly allowed in the implementation task with all folder/profile gates mandatory.
4. Allowed/forbidden file lists below.
5. No Track A / no processing-core edits in the implementation task unless a new PO decision revises §11.

## 13. Recommended next task title

`KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_LOCAL_PROCESSING_ADAPTER_IMPLEMENTATION_01`

### Scope (future)

- Implement bounded `LocalProcessingAdapter` under Track B UI-v2.
- Consume `RuntimePolicyIntent`.
- Explicit-user-action only.
- Dry/no-mutation mode first if possible.
- No auto-process; no private defaults; no Track A changes.
- Avoid processing-core changes unless PO revises boundary decision.

### Allowed future implementation files (proposed)

- `invoice_tool/ui_v2/processing_contract.py` (wire adapter factory / protocol fulfillment)
- `invoice_tool/ui_v2/processing_state.py` (only if small honest message helpers needed)
- `invoice_tool/ui_v2/adapters/local_processing_adapter.py` (**new**, preferred home)
- optional thin helper beside it, e.g. `invoice_tool/ui_v2/adapters/local_processing_result_mapper.py`
- `invoice_tool/ui_v2/pages/workspace.py` (explicit output folder + start wiring only as needed)
- `invoice_tool/ui_v2/state.py` (service injection only)
- `tests/test_ui_v2_local_processing_adapter.py` (**new**)
- updates to existing Track-B contract tests if needed
- audit doc for the implementation task

### Forbidden future implementation files

- `app_main.py`
- `app_internal_launcher.py`
- legacy Track-A UI modules
- `invoice_tool/processing.py`
- `invoice_tool/routing.py`
- `invoice_tool/routing_guards.py`
- `invoice_tool/classification.py`
- `invoice_tool/target_routing.py`
- `invoice_tool/run.py`
- `pyproject.toml`
- `scripts/**`
- `resources/**`
- `diagnostics/**`
- `testing/**`
- `.venv*`
- `profile_config.local.json`
- real invoice folders / PDFs

### PO approvals required in that future task

1. Confirm `TRACK_B_WRAPPER_ONLY`.
2. Confirm dry-first vs productive mutation scope.
3. Confirm explicit output-folder UX requirement.
4. Confirm no core edits.

## 14. Allowed future implementation files

See §13 proposed allow-list.

## 15. Forbidden future implementation files

See §13 forbid-list.

## 16. Tests required for future implementation

Minimum future test scope:

1. Adapter validate: missing folder/profile/output/policy → `not_configured`.
2. Unsafe / blocked policy intent → `blocked`; no core call.
3. Ready + dry_run → no mutation / no `run_once` side effects (mock/stub core entry).
4. Explicit user source required; unset source refused.
5. No private path defaults in request construction.
6. Filename-not-SOT / supplier-IBAN / generic-card gates enforced before start.
7. Result mapping emits only `ProcessingResultSummary` (+ review/errors separation).
8. No fake payment/private fields in summaries.
9. Unknown evidence maps to review/unclear items.
10. Import boundary: workspace/bridge remain free of uncontrolled core calls; wrapper is the sole call site.
11. Track A modules unchanged (path/content assertions as appropriate).
12. Failure mid-run → `failed`/`blocked` with errors; no partial fake completion rows.

Safe unit tests only; no GUI window tests; no real private invoice folders; no builds.

## 17. Commit / push status

Prepared in this docs-only task:

- Audit doc path: `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_LOCAL_PROCESSING_ADAPTER_PO_GATE_PREP_2026-07-21.md`
- Commit message (intended): `docs: bereite UI-v2 LocalProcessingAdapter PO-Gate vor`
- Payload: **only** this audit doc
- No code/test/script/resource/PDF/venv/testing/real-invoice files
- Push only if safe gates in the task brief pass

## 18. Rollback / safety behavior if adapter fails mid-run (future requirement)

Documented requirements for implementation (not implemented here):

1. On wrapper/core exception → state `failed` or `blocked`, populate `errors`, keep results honest (only verified rows).
2. Do not invent success rows for unprocessed files.
3. Do not delete or rewrite user source PDFs (rely on existing snapshot/archive semantics of `run_once`).
4. If productive mode was not entered (`dry_run=True`), ensure zero output/archive mutation.
5. UI must remain usable after failure (return to honest empty/partial state, no crash loop / auto-retry).

## 19. Preflight snapshot (this prep task)

| Check | Result |
|---|---|
| Worktree | `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App` |
| Branch | `main` |
| HEAD / origin/main | `474f0ce12a10349186fd7c82afd88e6696123d79` |
| ahead/behind | `0/0` |
| Staged files | none |
| Active git operation / locks | none |
| Actual processing-core dirty | no |
| Routing/classification dirty | no |
| Known legacy UI dirty | yes (local unstaged: `ui_profile_dialog.py`, `ui_document_rules.py`) |
| `profile_config.local.json` in status | no |
| Real invoice folders in status | no |
| UI-v2 / contract / bridge present | yes |

Initial classification:

`READY_FOR_TRACK_B_UI_V2_BOUNDED_LOCAL_PROCESSING_ADAPTER_PO_GATE_PREP`
